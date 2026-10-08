# Repository Guidelines

## Project Overview

This repo contains the voice feature only. It converts the AI Passport button and microphone to a wireless hotkey and wireless microphone. It performs no ASR. The Windows input method performs recognition.

## Architecture & Data Flow

Two trees share one UDP protocol and one ADPCM codec. Keep both sides byte-identical.

Device module `device/main/apps/voice/` runs as a guest in host firmware. It is not a standalone ESP-IDF project. Producers post events to one static queue. One worker task reduces events to actions. A separate audio pipeline streams ADPCM over UDP.

Flow on device:

- Button callback, UDP RX task, audio workers, and sound worker post to `app_events.c`.
- `voice_worker_task` in `app_voice.cc` pulls events and calls `app_state_reduce()` in `app_state.c`.
- The reducer returns an action list with a maximum of `APP_ACT_MAX` entries.
- Executors start or stop capture, send uplink JSON, play tones, and render a UI snapshot.
- `audio_streamer.c` captures audio, encodes ADPCM, and sends UDP frames. A session token cancels stale sessions.

Flow on Windows:

- `windows/hotkey_forwarder.py` runs an asyncio `Forwarder` loop.
- `windows/udp_transport.py` receives events and audio on UDP port 33333.
- `KeyInjector` injects keys through ctypes `SendInput`.
- `AudioSink` decodes ADPCM and writes PCM to VB-Cable.
- `windows/diagnose_voice.py` probes OS, hotkey syntax, UDP port state, and cable endpoints.

Shared wire contracts:

- UDP port 33333 for beacons, pings, events, and audio.
- ADPCM block is 804 bytes. The header holds 4 bytes. The payload holds 800 bytes for 1600 samples. One block covers 100 ms at 16 kHz. The nibble order places the low nibble first.
- Tables `K_STEP[89]` and `K_INDEX_DELTA[16]` in `device/main/apps/voice/adpcm.c` and `windows/adpcm.py` must match exactly.

## Key Directories

| Directory | Purpose |
|---|---|
| `windows/` | Python companion: forwarder, UDP transport, ADPCM codec, diagnostics, launchers |
| `windows/tests/` | Python unit tests, stdlib unittest only |
| `linux/` | Linux forwarder: voxtype offline ASR, wtype injection, shared UDP/ADPCM |
| `linux/tests/` | Linux unit tests, stdlib unittest only |
| `device/main/apps/voice/` | Device voice module, C and C++ source snapshot |
| `device/tests/` | Host-compilable C tests for pure logic files |
| `tools/` | Scope gate and host test runner |
| `docs/` | Chinese user and developer docs plus `VALIDATION.md` |
| `licenses/` | License texts for Python, sounddevice, CFFI, PyInstaller |
| `.github/workflows/` | Sole CI workflow |

No `scripts/` directory exists. Utilities live in `tools/` and `windows/`.

## Development Commands

Run Windows tests on Windows with Python 3.11:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r windows\requirements-hotkey.txt
.\.venv\Scripts\python.exe -m unittest discover -s windows\tests -p "test_*.py" -v
```

Run the Windows forwarder from source:

```powershell
.\.venv\Scripts\python.exe windows\hotkey_forwarder.py --diagnose
.\.venv\Scripts\python.exe windows\hotkey_forwarder.py
```

Run Linux tests on Linux (stdlib only, no dependencies):

```bash
python3 -m unittest discover -s linux/tests -p "test_*.py" -v
```

Run the Linux forwarder from source (needs voxtype + wtype):

```bash
python3 linux/voice_forwarder.py --diagnose
python3 linux/voice_forwarder.py
```

Run device host tests from the repo root on Linux, WSL, or any host with Bash and a C compiler:

```bash
bash tools/test-host.sh
```

Run the scope gate from the repo root:

```bash
python3 tools/check_scope.py
```

CI in `.github/workflows/checks.yml` runs three jobs. The `windows` job installs requirements and runs unittest discovery. The `linux` job runs Linux unittest discovery. The `scope-and-host` job runs `check_scope.py` and `test-host.sh`.

## Code Conventions & Common Patterns

- Name device state code with `app_` prefix and `APP_` macros. See `device/main/apps/voice/app_types.h`, `app_state.c`, `app_events.c`.
- Keep shared types host-safe. `app_types.h` includes no ESP-IDF headers. It compiles on the host for tests.
- Use one pure reducer on device. `app_state_reduce()` maps one state plus one event to actions. It allocates no memory. It calls no ESP APIs.
- Use fixed-size structs and static queues. The event queue depth is 8. `post()` drops events when full. `post_important()` waits for space for approval events.
- Size action buffers for the longest path. `APP_ACT_MAX` is 6. Full buffers drop tail actions without a log.
- Hold the LVGL lock in the caller of `app_ui_render()`. Only the voice task writes the UI.
- Gate stream start on tone completion. `APP_EV_TONE_DONE` signals readiness. `APP_TONE_PENDING_TIMEOUT_MS` provides fallback.
- Isolate sessions with tokens in `audio_streamer.c`. Cancel stops capture, clears the ring, and drops in-flight frames.
- Guard JSON depth in `app_protocol.c` against stack overflow.
- Mirror transport contracts across languages. `windows/udp_transport.py` implements the same method contract as `device/main/apps/voice/udp_audio.c`.
- Keep Python entry code in `hotkey_forwarder.py`. Use asyncio for the loop. Use threads plus queues for key injection and audio output.
- Copy `windows/voice-config.example.json` to `windows/voice-config.json` for local runs. Never commit the copy. `check_scope.py` rejects it.

## Important Files

- `windows/hotkey_forwarder.py`: companion entry point, `Forwarder`, `KeyInjector`, `AudioSink`, config load, CLI flags.
- `windows/udp_transport.py`: Python side of the UDP wire spec with port and frame-type constants.
- `windows/adpcm.py`: Python IMA ADPCM codec. Align it with `device/main/apps/voice/adpcm.c`.
- `windows/diagnose_voice.py`: read-only bridge diagnostics.
- `linux/voice_forwarder.py`: Linux entry point, `Forwarder`, voxtype ASR thread, wtype injection.
- `linux/asr_voxtype.py`: `voxtype transcribe` wrapper, WAV writer, first-blank-line parser.
- `linux/inject.py`: wtype text and enter/clear injection with dry-run support.
- `linux/udp_transport.py`: Linux side of the UDP wire spec, `ip addr` broadcast enumeration.
- `device/main/apps/voice/app_voice.cc`: device entry point, lifecycle, `g_voice_app`, worker task.
- `device/main/apps/voice/app_state.c`: pure reducer under host test.
- `device/main/apps/voice/app_types.h`: shared enums, structs, timeout constants.
- `device/main/apps/voice/app_protocol.c`: cJSON uplink and downlink handling.
- `device/main/apps/voice/audio_streamer.c`: capture, encode, and send pipeline.
- `device/main/apps/voice/udp_audio.c`: device side UDP channel.
- `device/main/apps/voice/ui_pixel_math.c`: pure UI math under host test.
- `tools/check_scope.py`: fail-closed allowlist, secret, binary, and link gate.
- `tools/test-host.sh`: host C test runner with `-std=c11 -Wall -Wextra -Werror`.
- `PUBLIC_FILES.json`: explicit tracked-file allowlist. Add each new file here or CI fails.
- `docs/DEVELOPMENT.zh-CN.md`: canonical local run and test commands.
- `docs/PORTING.zh-CN.md`: host-interface boundary for reuse of the voice module.
- `docs/VALIDATION.md`: validation boundary and explicit unverified items.

Stale names persist in comments. Python files still say `companion/`. Some C comments still say `Mac`, `BLE`, or point to an out-of-repo design doc. Trust `windows/`, Wi-Fi UDP, and this file instead.

## Runtime/Tooling Preferences

- Use Python 3.11 for the companion. The released EXE uses Python 3.11.8.
- Install one pinned dependency: `sounddevice==0.5.6` from `windows/requirements-hotkey.txt`.
- Install VB-CABLE separately. The repo bundles no driver and no input method.
- Build the EXE externally with PyInstaller 6.20.0. The repo holds no spec file and no packaging script.
- Compile host C tests with `${CC:-cc}` in C11 mode with warnings as errors.
- Treat ESP-IDF 5.5.3, FreeRTOS, and LVGL 9.5 as host-provided. This repo offers no full `idf.py build`.
- Require no lint, type check, or lockfile tooling. CI checks scope plus tests only.
- Linux forwarder needs system tools, not pip: `voxtype` 1.1.0 with SenseVoice model plus `wtype wl-clipboard` on a wlroots compositor.

## Testing & QA

Three suites share no harness. Windows tests run only on Windows CI. Linux and C tests run on Linux CI.

Windows suite:

- Framework is stdlib `unittest` plus `unittest.mock`. No pytest exists.
- Files are `windows/tests/test_hotkey_forwarder_unit.py` with 11 tests and `windows/tests/test_hotkey_release.py` with 4 tests.
- Tests patch `h._send_key` to capture injected keys. They fake `sounddevice` through `sys.modules`. They patch threads and clocks. They never touch real hardware.
- Covered areas include hold and tap modes, Enter debounce, stale-state reconciliation, audio-ready gating, drain before release, duplicate audio dedup, disconnect paths, malformed payloads, portable config resolution, and endpoint fallback.


Linux suite:

- File is `linux/tests/test_voice_forwarder_unit.py` with 17 tests, stdlib unittest only.
- Tests inject fake transcriber, typer, and key-action callables. They fake the voxtype binary with a Python stub script. They never touch real hardware.
- Covered areas include voice-end transcription, short-tap skip, Enter reconciliation, late-ASR drop, duplicate audio dedup, silence timeout, WAV format, parser edge cases, dry-run injection, and broadcast enumeration.

Device suite:
- Files are `device/tests/test_voice_remote.c` and `device/tests/test_ui_pixel_math.c`.
- The runner compiles `app_state.c` and `ui_pixel_math.c` on the host and runs both binaries.
- Tests assert exact action counts per transition. An extra or missing emit fails the test.
- `test_ui_pixel_math.c` covers the full public surface of its module.

Known gaps:

- `windows/adpcm.py` has no tests in this repo. Referenced vector files `tests/test_adpcm.py` and `tests/test_adpcm.c` do not exist here. Cross-language drift stays undetected.
- `windows/udp_transport.py` has no tests.
- Real key injection, real audio endpoints, `main()`, and long-run behavior have no automated tests. `docs/VALIDATION.md` records hardware evidence and lists unverified items.
- Adding any file requires an update to `PUBLIC_FILES.json`. `tools/check_scope.py` compares tracked files against that list and fails closed.
