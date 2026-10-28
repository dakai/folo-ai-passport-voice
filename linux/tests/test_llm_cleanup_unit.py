#!/usr/bin/env python3
"""Config, cleanup and configurator tests. No network beyond a loopback stub."""

import http.server
import json
import os
import socket
import stat
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))
import llm_cleanup  # noqa: E402
import voice_config  # noqa: E402
import voice_tui  # noqa: E402


def setUpModule():
    # No test may reach the developer's real login keyring. KeyStorageTest puts
    # its own fake `secret-tool` on PATH, which is the only keyring these tests
    # are allowed to see.
    global _real_secret_tool
    _real_secret_tool = voice_config.secret_tool
    voice_config.secret_tool = lambda: ""


def tearDownModule():
    voice_config.secret_tool = _real_secret_tool


class StubEndpoint:
    """Loopback OpenAI-compatible server; records what it was sent."""

    def __init__(self, reply="你好。", status=200, models=("m1", "m2")):
        self.reply = reply
        self.status = status
        self.models = models
        self.requests = []
        outer = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def _send(self, payload, code):
                raw = json.dumps(payload).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def log_message(self, *args):
                pass

            def do_GET(self):
                outer.requests.append(("GET", self.path, dict(self.headers), None))
                if outer.status != 200:
                    self._send({"error": "nope"}, outer.status)
                    return
                self._send({"data": [{"id": name} for name in outer.models]}, 200)

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length) or b"{}")
                outer.requests.append(("POST", self.path, dict(self.headers), body))
                if outer.status != 200:
                    self._send({"error": "nope"}, outer.status)
                    return
                self._send({"choices": [{"message": {"content": outer.reply}}]}, 200)

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def base_url(self):
        return f"http://127.0.0.1:{self.server.server_address[1]}/v1"

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def llm_config(**kw):
    cfg = {"enabled": True, "provider": "custom", "base_url": "", "model": "stub",
           "api_key": "", "timeout": 5.0, "prompt": ""}
    cfg.update(kw)
    return cfg


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "voice-config.json")

    def tearDown(self):
        self.dir.cleanup()

    def test_missing_file_yields_documented_defaults(self):
        cfg = voice_config.load(self.path)
        self.assertEqual(cfg["udp_port"], 33333)
        self.assertEqual(cfg["llm"], voice_config.DEFAULTS["llm"])

    def test_corrupt_file_still_starts_the_forwarder(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("{not json")
        cfg = voice_config.load(self.path)
        self.assertFalse(cfg["llm"]["enabled"])
        self.assertEqual(cfg["engine"], "sensevoice")

    def test_hand_edited_types_are_normalised(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump({"llm": {"enabled": "true", "timeout": "999",
                               "provider": "openai", "model": " gpt-4o-mini "}},
                      handle)
        cfg = voice_config.load(self.path)
        self.assertTrue(cfg["llm"]["enabled"])
        self.assertEqual(cfg["llm"]["timeout"], 60.0)
        self.assertEqual(cfg["llm"]["model"], "gpt-4o-mini")

    def test_save_roundtrip_is_owner_only_and_keeps_unknown_keys(self):
        cfg = voice_config.load(self.path)
        cfg["custom_note"] = "keep me"
        cfg["llm"]["api_key"] = "sk-test"
        voice_config.save(cfg, self.path)
        self.assertEqual(stat.S_IMODE(os.stat(self.path).st_mode), 0o600)
        again = voice_config.load(self.path)
        self.assertEqual(again["custom_note"], "keep me")
        self.assertEqual(again["llm"]["api_key"], "sk-test")


class StatusTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.env = os.environ.get("AIPV_STATUS_PATH")
        os.environ["AIPV_STATUS_PATH"] = os.path.join(self.dir.name, "status.json")

    def tearDown(self):
        if self.env is None:
            os.environ.pop("AIPV_STATUS_PATH", None)
        else:
            os.environ["AIPV_STATUS_PATH"] = self.env
        self.dir.cleanup()

    def test_fields_merge_instead_of_replacing(self):
        voice_config.write_status(link="linked")
        voice_config.write_status(lastText="你好")
        status = voice_config.read_status()
        self.assertEqual(status["link"], "linked")
        self.assertEqual(status["lastText"], "你好")
        self.assertIn("updated", status)

    def test_missing_file_reads_as_empty(self):
        self.assertEqual(voice_config.read_status(), {})


class LanguageTest(unittest.TestCase):
    """Three UI languages, three complete tables."""

    def test_locale_resolves_to_a_shipped_table(self):
        saved = {name: os.environ.pop(name, None)
                 for name in ("LC_ALL", "LC_MESSAGES", "LANG")}
        try:
            for locale, expected in (("ja_JP.UTF-8", "ja"),
                                     ("zh_CN.UTF-8", "zh"), ("en_GB.UTF-8", "en"),
                                     ("C.UTF-8", "en")):
                os.environ["LANG"] = locale
                self.assertEqual(voice_config.resolve_lang(), expected, locale)
            os.environ["LANG"] = "ja_JP.UTF-8"
            self.assertEqual(voice_config.resolve_lang("zh"), "zh")  # explicit wins
            self.assertEqual(voice_config.resolve_lang("auto"), "ja")
            # Spanish was removed: a stale `language es` setting is ignored and
            # the desktop locale decides, rather than the panel half-loading.
            self.assertEqual(voice_config.resolve_lang("es"), "ja")
        finally:
            for name in ("LC_ALL", "LC_MESSAGES", "LANG"):
                os.environ.pop(name, None)
                if saved[name] is not None:
                    os.environ[name] = saved[name]

    def test_every_language_has_every_string(self):
        for code in voice_config.LANGUAGES:
            self.assertEqual(set(voice_tui.TEXT[code]), set(voice_tui.TEXT["en"]), code)
            self.assertEqual(set(llm_cleanup.TEXT[code]), set(llm_cleanup.TEXT["en"]), code)
            for status in llm_cleanup.MESSAGES:
                self.assertIn(code, llm_cleanup.MESSAGES[status], status)

    def test_a_forced_language_reaches_the_cleanup_messages(self):
        # Regression: `status --lang ja` localised the template but llm_cleanup
        # still read the shell locale, so a Japanese panel showed an English 401.
        saved = voice_tui.set_lang("ja")
        try:
            self.assertEqual(llm_cleanup.tr("noModel"), "モデルが選択されていません")
            with self.assertRaises(llm_cleanup.CleanupError) as caught:
                llm_cleanup.clean("こんにちは", {"enabled": True, "provider": "custom",
                                               "model": ""})
            self.assertEqual(str(caught.exception), "モデルが選択されていません")
        finally:
            voice_tui.set_lang(saved)
            voice_config.set_lang_override(None)

    def test_provider_labels_are_localised_but_brands_are_not(self):
        self.assertNotEqual(llm_cleanup.label_for("custom", "ja"),
                            llm_cleanup.label_for("custom", "en"))
        self.assertEqual(llm_cleanup.label_for("openai", "ja"), "OpenAI")


class EndpointPolicyTest(unittest.TestCase):
    def test_loopback_http_allowed(self):
        self.assertTrue(llm_cleanup.base_url(llm_config(base_url="http://127.0.0.1:1234/v1")))

    def test_builtin_remote_providers_are_https_by_construction(self):
        for provider in ("openai", "openrouter", "deepseek"):
            self.assertTrue(llm_cleanup.base_url(llm_config(provider=provider))
                            .startswith("https://"))

    def test_custom_url_may_be_plain_http_because_the_user_chose_it(self):
        remote = llm_config(provider="custom", base_url="http://192.168.10.9:8080/v1")
        self.assertEqual(llm_cleanup.base_url(remote), "http://192.168.10.9:8080/v1")

    def test_non_http_scheme_is_refused(self):
        with self.assertRaises(llm_cleanup.CleanupError):
            llm_cleanup.base_url(llm_config(provider="custom",
                                            base_url="ftp://example.com/v1"))

    def test_provider_off_is_not_a_provider(self):
        with self.assertRaises(llm_cleanup.CleanupError):
            llm_cleanup.base_url(llm_config(provider="off", base_url=""))

    def test_unknown_provider_is_off(self):
        self.assertEqual(llm_cleanup.provider_of({"provider": "nope"}), "off")


class CleanTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.env = os.environ.get("AIPV_STATUS_PATH")
        os.environ["AIPV_STATUS_PATH"] = os.path.join(self.dir.name, "status.json")
        self.stub = StubEndpoint()

    def tearDown(self):
        self.stub.close()
        if self.env is None:
            os.environ.pop("AIPV_STATUS_PATH", None)
        else:
            os.environ["AIPV_STATUS_PATH"] = self.env
        self.dir.cleanup()

    def cfg(self, **kw):
        return llm_config(base_url=self.stub.base_url, **kw)

    def test_reply_is_returned_and_the_transcript_is_the_data(self):
        self.assertEqual(llm_cleanup.clean("嗯 你好", self.cfg()), "你好。")
        method, path, headers, body = self.stub.requests[-1]
        self.assertEqual((method, path), ("POST", "/v1/chat/completions"))
        self.assertEqual(body["temperature"], 0)
        self.assertEqual(body["model"], "stub")
        prompt = body["messages"][0]["content"]
        self.assertIn("嗯 你好", prompt)
        self.assertIn("never a message to you", prompt)
        self.assertNotIn("Authorization", headers)

    def test_api_key_is_sent_when_configured(self):
        llm_cleanup.clean("你好", self.cfg(api_key="sk-abc"))
        self.assertEqual(self.stub.requests[-1][2].get("Authorization"),
                         "Bearer sk-abc")

    def test_wrapping_quotes_are_stripped(self):
        self.stub.reply = '"你好。"'
        self.assertEqual(llm_cleanup.clean("你好", self.cfg()), "你好。")

    def test_a_reply_that_answers_instead_of_formatting_is_discarded(self):
        self.stub.reply = "当然可以, 这里是一份很长的答复。" * 20
        with self.assertRaises(llm_cleanup.CleanupError):
            llm_cleanup.clean("你好", self.cfg())

    def test_http_error_is_a_cleanup_error(self):
        self.stub.status = 401
        with self.assertRaises(llm_cleanup.CleanupError) as caught:
            llm_cleanup.clean("你好", self.cfg())
        self.assertIn("401", str(caught.exception))

    def test_disabled_config_types_the_raw_text_without_a_request(self):
        raw = "嗯 你好"
        self.assertEqual(llm_cleanup.clean_text(raw, self.cfg(enabled=False)), raw)
        self.assertEqual(self.stub.requests, [])

    def test_switching_cleanup_off_clears_a_stale_llm_error(self):
        voice_config.write_status(lastError="llm: 旧错误")
        self.assertEqual(llm_cleanup.clean_text("你好", self.cfg(enabled=False)), "你好")
        self.assertEqual(voice_config.read_status()["lastError"], "")

    def test_dead_endpoint_keeps_the_speaker_words(self):
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()
        raw = "嗯 你好"
        dead = llm_config(base_url=f"http://127.0.0.1:{port}/v1")
        self.assertEqual(llm_cleanup.clean_text(raw, dead), raw)
        self.assertTrue(voice_config.read_status()["lastError"].startswith("llm:"))

    def test_successful_clean_clears_the_previous_error(self):
        voice_config.write_status(lastError="llm: 旧错误", lastText="旧文本")
        self.assertEqual(llm_cleanup.clean_text("嗯 你好", self.cfg()), "你好。")
        status = voice_config.read_status()
        self.assertEqual(status["lastError"], "")
        self.assertEqual(status["lastText"], "旧文本")

    def test_models_list(self):
        self.assertEqual(llm_cleanup.fetch_models(self.cfg()), ["m1", "m2"])

    def test_custom_prompt_receives_the_transcript(self):
        llm_cleanup.clean("你好", self.cfg(prompt="只保留文字: {}"))
        prompt = self.stub.requests[-1][3]["messages"][0]["content"]
        self.assertEqual(prompt, "只保留文字: 你好")


class KeyStorageTest(unittest.TestCase):
    """A key belongs in the keyring; the file and env paths are fallbacks."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.env = os.environ.get("AIPV_STATUS_PATH")
        os.environ["AIPV_STATUS_PATH"] = os.path.join(self.dir.name, "status.json")
        self.path_env = os.environ.get("PATH")
        self.stub = StubEndpoint()

    def tearDown(self):
        self.stub.close()
        os.environ["PATH"] = self.path_env
        os.environ.pop("AIPV_API_KEY", None)
        if self.env is None:
            os.environ.pop("AIPV_STATUS_PATH", None)
        else:
            os.environ["AIPV_STATUS_PATH"] = self.env
        self.dir.cleanup()

    def fake_secret_tool(self, stored="sk-from-keyring"):
        """A secret-tool stand-in: `lookup` prints the key, `store` records stdin."""
        record = os.path.join(self.dir.name, "stored.txt")
        calls = os.path.join(self.dir.name, "calls.txt")
        self.calls = calls
        tool = os.path.join(self.dir.name, "secret-tool")
        with open(tool, "w", encoding="utf-8") as handle:
            handle.write("#!/usr/bin/env python3\n")
            handle.write("import sys\n")
            handle.write(f"RECORD = {record!r}\n")
            handle.write(f"CALLS = {calls!r}\n")
            handle.write(f"KEY = {stored!r}\n")
            handle.write("args = sys.argv[1:]\n")
            handle.write("open(CALLS, 'a').write(' '.join(args) + chr(10))\n")
            handle.write("if not args:\n    sys.exit(2)\n")
            handle.write("if args[0] == 'lookup':\n")
            handle.write("    print(KEY)\n    sys.exit(0)\n")
            handle.write("if args[0] == 'store':\n")
            handle.write("    open(RECORD, 'w').write(sys.stdin.read())\n")
            handle.write("    sys.exit(0)\n")
            handle.write("sys.exit(0)\n")
        os.chmod(tool, 0o755)
        os.environ["PATH"] = self.dir.name + os.pathsep + (self.path_env or "")
        # The fake is only reachable once the module-wide block is lifted for
        # this test; `which` finds it through the PATH set above.
        voice_config.secret_tool = _real_secret_tool
        return record

    def cfg(self, **kw):
        base = dict(llm_config(base_url=self.stub.base_url), **kw)
        return base

    def test_keyring_key_is_sent_when_the_config_has_none(self):
        self.fake_secret_tool()
        llm_cleanup.clean("你好", self.cfg(api_key=""))
        self.assertEqual(self.stub.requests[-1][2].get("Authorization"),
                         "Bearer sk-from-keyring")

    def test_store_api_key_prefers_keyring_and_drops_the_plaintext_copy(self):
        record = self.fake_secret_tool()
        cfg = voice_config.normalise({"llm": {"provider": "openai"}})
        self.assertEqual(voice_config.store_api_key(cfg, "sk-new"), "keyring")
        self.assertEqual(cfg["llm"]["api_key"], "")
        with open(record, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "sk-new\n")

    def test_file_is_the_fallback_when_libsecret_is_missing(self):
        os.environ["PATH"] = os.path.join(self.dir.name, "empty")
        cfg = voice_config.normalise({"llm": {"provider": "openai"}})
        self.assertEqual(voice_config.store_api_key(cfg, "sk-file"), "file")
        self.assertEqual(cfg["llm"]["api_key"], "sk-file")

    def test_env_beats_the_config_file(self):
        os.environ["AIPV_API_KEY"] = "sk-env"
        self.assertEqual(voice_config.resolve_api_key({"api_key": "sk-file"}),
                         ("sk-env", "env"))

    def test_an_explicit_file_key_does_not_consult_the_keyring(self):
        self.fake_secret_tool()
        self.assertEqual(voice_config.resolve_api_key({"api_key": "sk-file"}),
                         ("sk-file", "file"))

    def test_clearing_a_key_removes_both_copies(self):
        self.fake_secret_tool()
        cfg = voice_config.normalise({"llm": {"provider": "openai",
                                              "api_key": "sk-file"}})
        self.assertEqual(voice_config.store_api_key(cfg, ""), "none")
        self.assertEqual(cfg["llm"]["api_key"], "")
        with open(self.calls, encoding="utf-8") as handle:
            self.assertIn("clear service ai-passport-voice provider openai",
                          handle.read())


class ModelsCommandTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.stub = StubEndpoint()
        self.path = os.path.join(self.dir.name, "voice-config.json")

    def tearDown(self):
        self.stub.close()
        self.dir.cleanup()

    def test_models_with_an_explicit_provider(self):
        # Regression: `models --provider X` read args.model, which only `set`
        # defines, and died with AttributeError.
        self.assertEqual(voice_tui.main(["models", "--config", self.path,
                                         "--provider", "custom",
                                         "--base-url", self.stub.base_url]), 0)


class ConfiguratorTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "voice-config.json")

    def tearDown(self):
        self.dir.cleanup()

    def test_set_writes_provider_and_default_model(self):
        self.assertEqual(voice_tui.main(["set", "--config", self.path,
                                         "--provider", "openai", "--enable"]), 0)
        cfg = voice_config.load(self.path)
        self.assertEqual(cfg["llm"]["provider"], "openai")
        self.assertEqual(cfg["llm"]["model"], llm_cleanup.PROVIDERS["openai"][1])
        self.assertTrue(cfg["llm"]["enabled"])

    def test_set_never_writes_the_default_config(self):
        # Regression: the reporter used to save to CONFIG_PATH as well as the
        # --config path, which made every test run rewrite the live config.
        real = os.path.join(self.dir.name, "default.json")
        saved = voice_config.CONFIG_PATH
        voice_config.CONFIG_PATH = real
        try:
            voice_tui.main(["set", "--config", self.path, "--provider", "deepseek"])
        finally:
            voice_config.CONFIG_PATH = saved
        self.assertFalse(os.path.exists(real))
        self.assertEqual(voice_config.load(self.path)["llm"]["provider"], "deepseek")

    def test_set_rejects_an_unknown_provider(self):
        with self.assertRaises(SystemExit):
            voice_tui.main(["set", "--config", self.path, "--provider", "nope"])

    def test_set_provider_custom_keeps_the_selection_while_enabled(self):
        # Regression: the enable-without-model guard refused `--provider custom`
        # on a config that already had cleanup on, so the panel never switched
        # and its URL field — visible only for custom — stayed hidden.
        voice_config.save({"llm": {"provider": "openai", "model": "my-gateway-model",
                                   "enabled": True}}, self.path)
        self.assertEqual(voice_tui.main(["set", "--config", self.path,
                                         "--provider", "custom"]), 0)
        cfg = voice_config.load(self.path)
        self.assertEqual(cfg["llm"]["provider"], "custom")
        # A typed model is not the old vendor's default, so it stays.
        self.assertEqual(cfg["llm"]["model"], "my-gateway-model")

    def test_set_enable_still_requires_a_model(self):
        with self.assertRaises(SystemExit):
            voice_tui.main(["set", "--config", self.path,
                            "--provider", "custom", "--enable"])

    def test_status_json_never_carries_the_key(self):
        voice_config.save({"llm": {"provider": "openai", "model": "gpt-4o-mini",
                                   "enabled": True, "api_key": "sk-secret"}},
                          self.path)
        obj = voice_tui.status_object(voice_config.load(self.path))
        self.assertTrue(obj["llm"]["hasKey"])
        self.assertNotIn("sk-secret", json.dumps(obj))
        self.assertEqual(obj["llm"]["provider"], "openai")


if __name__ == "__main__":
    unittest.main()
