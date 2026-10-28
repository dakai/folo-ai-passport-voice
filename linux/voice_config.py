#!/usr/bin/env python3
"""The one owner of voice-config.json and the forwarder's status file.

Three callers share this module: the forwarder (reads config at startup and
re-reads the LLM block per utterance), the terminal configurator
(`voice_tui.py`), and the Omarchy plugin (which drives that configurator).
A second copy of the format in any of them is how the three would drift.

`voice-config.json` is gitignored and may hold an API key, so it is written
atomically and 0600. `status.json` is advisory: the forwarder publishes one
small JSON object there for the configurator and the bar widget to read, and
nothing depends on it being fresh.
"""

import json
import os
import shutil
import subprocess
import tempfile
import time

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE, "voice-config.json")
EXAMPLE_PATH = os.path.join(BASE, "voice-config.example.json")

STATE_DIR = os.path.join(
    os.environ.get("XDG_STATE_HOME")
    or os.path.join(os.path.expanduser("~"), ".local", "state"),
    "ai-passport-voice")
STATUS_PATH = os.path.join(STATE_DIR, "status.json")

SERVICE_UNIT = "ai-passport-voice.service"

# Schema name for the login keyring entry, so a key stored here is visibly this
# program's and can be inspected or removed with `secret-tool` alone.
KEYRING_SERVICE = "ai-passport-voice"
KEYRING_TIMEOUT = 5.0

DEFAULTS = {
    "udp_port": 33333,
    "device_ip": "",
    "voxtype_bin": "voxtype",
    "engine": "sensevoice",
    "llm": {
        "enabled": False,
        "provider": "off",
        "base_url": "",
        "model": "",
        "api_key": "",
        "timeout": 8.0,
        "prompt": "",
    },
}

LLM_KEYS = tuple(DEFAULTS["llm"])


def _merge(base, override):
    """Recursive merge that keeps `base` intact and ignores non-dict junk."""
    out = dict(base)
    for key, value in (override or {}).items():
        if isinstance(base.get(key), dict):
            if isinstance(value, dict):
                out[key] = _merge(base[key], value)
        else:
            out[key] = value
    return out


def as_bool(value, fallback=False):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return fallback


def _as_timeout(value):
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return DEFAULTS["llm"]["timeout"]
    return max(1.0, min(60.0, seconds))


def normalise(cfg):
    """Coerce a loaded config into the documented shape.

    A hand-edited file is a normal input here: "true" strings, a numeric
    timeout as text and a missing llm block all have to end up usable rather
    than crashing the forwarder at startup.
    """
    merged = _merge(DEFAULTS, cfg if isinstance(cfg, dict) else {})
    llm = dict(merged["llm"])
    llm["enabled"] = as_bool(llm.get("enabled"))
    for key in ("provider", "base_url", "model", "api_key", "prompt"):
        llm[key] = str(llm.get(key) or "").strip()
    llm["timeout"] = _as_timeout(llm.get("timeout"))
    merged["llm"] = {key: llm[key] for key in LLM_KEYS}
    return merged


def load(path=None):
    """Read the config, or the defaults when it is absent or unreadable.

    Corrupt JSON must not stop the forwarder: a broken hand edit has to leave
    dictation working with cleanup off, which is what the defaults are.
    """
    path = path or CONFIG_PATH
    try:
        with open(path, encoding="utf-8-sig") as handle:
            raw = json.load(handle)
    except FileNotFoundError:
        return normalise({})
    except (OSError, ValueError):
        return normalise({})
    return normalise(raw)


def save(cfg, path=None):
    """Write the config atomically, readable only by its owner (it may hold a key)."""
    path = path or CONFIG_PATH
    payload = json.dumps(normalise(cfg), indent=2, ensure_ascii=False) + "\n"
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    handle, temp = tempfile.mkstemp(dir=directory, prefix=".voice-config-",
                                    suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            out.write(payload)
            out.flush()
            os.fsync(out.fileno())
        os.chmod(temp, 0o600)
        os.replace(temp, path)
    except BaseException:
        try:
            os.unlink(temp)
        except OSError:
            pass
        raise
    return path


# ---------------------------------------------------------------- api key
#
# A key belongs in the login keyring, not in a text file: the file is readable
# by anything running as this user (a stray `cat`, a backup, a pasted dotfile).
# `secret-tool` is the libsecret CLI, so this stays dependency-free while the
# secret lives in gnome-keyring/kwallet and is encrypted at rest.
#
# Resolution order is env -> config file -> keyring. Explicit wins: a key typed
# into the file still works (an old config keeps working), and a test that
# injects a key never touches the user's keyring.

def secret_tool():
    """Path to secret-tool, or "" when libsecret is not installed."""
    return shutil.which("secret-tool") or ""


def _secret_env():
    """The minimum environment secret-tool needs to reach the session bus.

    The forwarder runs under systemd, so PATH may be minimal; the bus address
    and runtime dir are the two variables a keyring lookup actually needs.
    """
    # LC_ALL: secret-tool refuses a non-ASCII label when the child inherits the
    # C locale, which is what a systemd unit starts with.
    env = {"HOME": os.environ.get("HOME", ""), "PATH": "/usr/bin:/bin",
           "LC_ALL": "C.UTF-8"}
    for name in ("DBUS_SESSION_BUS_ADDRESS", "XDG_RUNTIME_DIR"):
        value = os.environ.get(name)
        if value:
            env[name] = value
    return env


def _secret(args, stdin_text=None):
    tool = secret_tool()
    if not tool:
        return None
    try:
        return subprocess.run([tool] + args, capture_output=True, text=True,
                              timeout=KEYRING_TIMEOUT, env=_secret_env(),
                              input=stdin_text)
    except (OSError, subprocess.SubprocessError):
        return None


def provider_key(provider):
    return str(provider or "off").strip() or "off"


def keyring_lookup(provider):
    """The stored key for this provider, or "" (missing key is not an error)."""
    done = _secret(["lookup", "service", KEYRING_SERVICE,
                    "provider", provider_key(provider)])
    if done is None or done.returncode != 0:
        return ""
    return (done.stdout or "").strip()


def keyring_store(provider, key):
    """True when the key landed in the keyring."""
    done = _secret(["store", "--label", f"AI Passport voice ({provider_key(provider)})",
                    "service", KEYRING_SERVICE, "provider", provider_key(provider)],
                   stdin_text=key + "\n")
    return done is not None and done.returncode == 0


def keyring_clear(provider):
    done = _secret(["clear", "service", KEYRING_SERVICE,
                    "provider", provider_key(provider)])
    return done is not None and done.returncode == 0


def resolve_api_key(llm):
    """(key, storage) where storage is env | file | keyring | none."""
    env_key = os.environ.get("AIPV_API_KEY", "").strip()
    if env_key:
        return env_key, "env"
    file_key = str((llm or {}).get("api_key") or "").strip()
    if file_key:
        return file_key, "file"
    key = keyring_lookup((llm or {}).get("provider"))
    return (key, "keyring") if key else ("", "none")


def store_api_key(cfg, key):
    """Put the key where it belongs and drop any plaintext copy.

    Returns the storage that took it: keyring, file, or none (cleared). The
    caller saves the config, so the file copy removal lands in the same write.
    """
    provider = (cfg.get("llm") or {}).get("provider")
    key = (key or "").strip()
    if not key:
        keyring_clear(provider)
        cfg["llm"]["api_key"] = ""
        return "none"
    if keyring_store(provider, key):
        cfg["llm"]["api_key"] = ""
        return "keyring"
    cfg["llm"]["api_key"] = key
    return "file"


# Languages with a full string table. Adding one means adding a table to
# voice_tui.TEXT, llm_cleanup.TEXT/MESSAGES and omarchy/I18n.js STRINGS;
# `language` in the widget settings takes "auto" plus these codes.
LANGUAGES = ("en", "es", "ja", "zh")


# Pinned by the configurator when --lang or the widget forces a language, so
# every module that speaks to the user — including llm_cleanup, which has no
# flag of its own — uses the same one. Stays None in the forwarder, where the
# journal should follow the machine's locale.
_LANG_OVERRIDE = None


def set_lang_override(code):
    """Pin this process's UI language; an unknown code clears the pin."""
    global _LANG_OVERRIDE
    _LANG_OVERRIDE = code if code in LANGUAGES else None


def resolve_lang(value="auto"):
    """The language this project speaks with this machine.

    An explicit code wins, then a pinned override, then the locale. Only the
    language part of the locale is used, so zh_CN.UTF-8, es_419 and ja_JP map
    to their tables and anything else (C, POSIX, a language without a table)
    falls back to English.

    Shared by the configurator and the cleanup messages so one desktop does not
    end up with half a panel in each language.
    """
    if value in LANGUAGES:
        return value
    if _LANG_OVERRIDE:
        return _LANG_OVERRIDE
    probe = ""
    for name in ("LC_ALL", "LC_MESSAGES", "LANG"):
        candidate = os.environ.get(name, "")
        if candidate:
            probe = candidate.lower()
            break
    head = probe.split(".")[0].split("_")[0].split("-")[0]
    return head if head in LANGUAGES else "en"


def status_path():
    """The default status file, or the test override."""
    return os.environ.get("AIPV_STATUS_PATH") or STATUS_PATH


def write_status(**fields):
    """Merge fields into status.json; never raise on the forwarder's hot path."""
    path = status_path()
    current = read_status(path)
    current.update(fields)
    current["updated"] = round(time.time(), 3)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        temp = path + ".tmp"
        with open(temp, "w", encoding="utf-8") as handle:
            json.dump(current, handle, ensure_ascii=False)
        os.replace(temp, path)
    except OSError:
        pass


def read_status(path=None):
    path = path or status_path()
    try:
        with open(path, encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}
