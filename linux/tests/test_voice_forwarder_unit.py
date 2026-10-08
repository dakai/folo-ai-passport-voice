#!/usr/bin/env python3
"""Linux forwarder dispatch + voxtype/inject unit tests (no hardware)."""

import argparse
import json
import os
import stat
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))
import asr_voxtype  # noqa: E402
import inject  # noqa: E402
import udp_transport as u  # noqa: E402
import voice_forwarder as v  # noqa: E402


def make_args(**kw):
    d = dict(port=33333, device_ip="", voxtype_bin="voxtype",
             engine="sensevoice")
    d.update(kw)
    return argparse.Namespace(**d)


def block(seq=0):
    import adpcm
    return bytes((seq, 0x80)) + adpcm.encode_block(
        __import__("adpcm").AdpcmState(), [0] * 1600)


class ForwarderDispatchTest(unittest.TestCase):
    def setUp(self):
        self.typed = []
        self.keys = []
        self.fwd = v.Forwarder(
            make_args(), transcriber=lambda samples: "你好",
            typer=self.typed.append, key_action=self.keys.append)

    @staticmethod
    def event(name, **fields):
        return (json.dumps({"event": name, **fields}) + "\n").encode("utf-8")

    def run_utterance(self, n=3):
        self.fwd.on_event(self.event("voice.start"))
        for i in range(n):
            self.fwd.on_audio(block(i))
        self.fwd.on_event(self.event("voice.end"))
        deadline = time.monotonic() + 5
        while not self.typed and time.monotonic() < deadline:
            time.sleep(0.01)

    def test_voice_end_transcribes_and_types(self):
        self.run_utterance()
        self.assertEqual(self.typed, ["你好"])

    def test_short_tap_skips_asr(self):
        seen = []
        self.fwd.on_event(self.event("voice.start"))
        self.fwd.on_audio(block(0))
        self.fwd.on_event(self.event("voice.end"))
        time.sleep(0.2)
        self.assertEqual(seen, [])
        self.assertEqual(self.typed, [])

    def test_enter_releases_stale_voice_then_injects_once(self):
        self.fwd.on_event(self.event("voice.start"))
        self.fwd.on_event(self.event("key.action", action="enter"))
        deadline = time.monotonic() + 2
        while not self.keys and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertEqual(self.keys, ["enter"])
        self.assertFalse(self.fwd.active)
        self.assertEqual(self.typed, [])

    def test_late_asr_after_enter_is_dropped(self):
        gate = threading_gate = __import__("threading").Event()
        slow = lambda samples: (gate.wait(5), "迟到")[1]
        fwd = v.Forwarder(make_args(), transcriber=slow,
                          typer=self.typed.append,
                          key_action=self.keys.append)
        fwd.on_event(self.event("voice.start"))
        for i in range(3):
            fwd.on_audio(block(i))
        fwd.on_event(self.event("voice.end"))
        fwd.on_event(self.event("key.action", action="enter"))
        gate.set()
        deadline = time.monotonic() + 2
        while not self.keys and time.monotonic() < deadline:
            time.sleep(0.01)
        time.sleep(0.3)
        self.assertEqual(self.typed, [])

    def test_duplicate_and_late_audio_ignored(self):
        self.fwd.on_event(self.event("voice.start"))
        self.fwd.on_audio(block(5))
        self.fwd.on_audio(block(5))
        self.fwd.on_audio(block(4))
        self.assertEqual(self.fwd.audio_blocks, 1)

    def test_malformed_events_ignored(self):
        for payload in (b"null", b"[]", b"garbage", b'"voice.start"'):
            self.fwd.on_event(payload)
        self.assertFalse(self.fwd.active)

    def test_silence_timeout_discards_buffer(self):
        self.fwd.on_event(self.event("voice.start"))
        self.fwd.on_audio(block(0))
        self.fwd.check_health(now=self.fwd.last_audio_at + 3.0)
        self.assertFalse(self.fwd.active)
        self.assertEqual(self.fwd.pcm_blocks, [])

    def test_pc_status_reports_text_ready(self):
        st = self.fwd.pc_status()
        self.assertEqual(st["type"], "pc.status")
        self.assertTrue(st["audioReady"])


class AsrVoxtypeTest(unittest.TestCase):
    def fake_voxtype(self, stdout_text):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "voxtype")
        with open(path, "w", encoding="utf-8") as f:
            f.write("#!/usr/bin/env python3\nimport sys\n")
            f.write(f"sys.stdout.write({stdout_text!r})\n")
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
        return path

    def test_transcript_after_first_blank_line(self):
        out = ("Loading audio file: \"/tmp/x.wav\"\n"
               "2026-01-01T00:00:00Z  INFO model loaded\n\n你好世界\n")
        self.assertEqual(asr_voxtype.parse_transcribe_output(out), "你好世界")

    def test_vad_skip_yields_empty(self):
        out = ("Processing 32000 samples...\n\n"
               "No speech detected, skipping transcription.\n")
        self.assertEqual(asr_voxtype.parse_transcribe_output(out), "")

    def test_transcribe_wav_uses_fake_binary(self):
        binpath = self.fake_voxtype("INFO line\n\n测试文本\n")
        fd, wav = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            asr_voxtype.write_wav(wav, [0] * 1600)
            self.assertEqual(
                asr_voxtype.transcribe_wav(wav, voxtype_bin=binpath), "测试文本")
        finally:
            os.unlink(wav)

    def test_transcribe_wav_raises_on_nonzero_exit(self):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "voxtype")
        with open(path, "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\nexit 1\n")
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
        fd, wav = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            asr_voxtype.write_wav(wav, [0] * 1600)
            with self.assertRaises(asr_voxtype.AsrError):
                asr_voxtype.transcribe_wav(wav, voxtype_bin=path)
        finally:
            os.unlink(wav)

    def test_empty_pcm_skips_subprocess(self):
        self.assertEqual(
            asr_voxtype.transcribe_pcm([], voxtype_bin="/nonexistent"), "")

    def test_wav_roundtrip_sample_values(self):
        import wave
        fd, wav = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            asr_voxtype.write_wav(wav, [0, 1000, -1000, 32767, -32768])
            with wave.open(wav, "rb") as w:
                self.assertEqual(
                    (w.getnchannels(), w.getsampwidth(), w.getframerate()),
                    (1, 2, 16000))
        finally:
            os.unlink(wav)


class InjectTest(unittest.TestCase):
    def test_dry_run_spawns_no_subprocess(self):
        self.assertEqual(inject.type_text("你好", dry_run=True),
                         ["wtype", "--", "你好"])
        self.assertEqual(inject.key_action("enter", dry_run=True),
                         ["wtype", "-k", "Return"])
        self.assertEqual(inject.type_text("", dry_run=True), [])

    def test_unknown_action_rejected(self):
        with self.assertRaises(ValueError):
            inject.key_action("space", dry_run=True)

    def test_beacon_broadcast_addrs(self):
        addrs = [a for a, _ in u._local_broadcast_addrs(33333)]
        self.assertIn("255.255.255.255", addrs)

    def test_sweep_targets_cover_subnet_without_self(self):
        targets = u._sweep_targets(33333)
        ips = [a for a, _ in targets]
        self.assertGreater(len(ips), 0)
        self.assertNotIn("255.255.255.255", ips)
        self.assertFalse(any(ip.endswith(".255") and ip.count(".") == 3
                             and len(targets) < 300 for ip in ips))
        for own, _ in u._local_ipv4_subnets():
            self.assertNotIn(own, ips)


if __name__ == "__main__":
    unittest.main()
