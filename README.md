# AI Passport 随身语音 · wireless microphone and voice hotkey

<img src="docs/images/ai-passport.webp" alt="AI Passport" width="330">

**Languages:** English · [中文](README.zh-CN.md) · [Español](README.es.md) · [日本語](README.ja.md)

Hold the top button on your AI Passport, speak, release. The text appears in the window you are typing in; short-press the bottom button to send Enter.

The device does the listening, the computer does the recognition. Two ways to run the computer side:

| | Windows 10/11 x64 | Linux (Omarchy) |
| --- | --- | --- |
| Recognition | your voice input method (WeChat Input Method etc.) | `voxtype` + SenseVoice, fully offline |
| Audio path | forwarder → **VB-CABLE** → input method | forwarder → ASR in-process → typed with `wtype` |
| Cloud | depends on the input method | none |
| Extras | — | optional LLM cleanup, Omarchy bar widget |


**This repository ships the voice feature, not the whole device.** There is no flashable firmware and no full ESP-IDF project here. The firmware is published by the maintainer on the [FoloToy play page](https://ai-passport.folotoy.cn/plays/438/); if that page does not yet have a build with 随身语音, wait for the update. Never treat this repository's *Source code ZIP* as firmware.

## What you need

| | Requirement |
| --- | --- |
| Device | FoloToy AI Passport, same hardware: ESP32-C3, 8 MB flash, ES8311 codec |
| Firmware | a build that includes 随身语音 (see above); installing it replaces the current play mode |
| Network | device on a **2.4 GHz** Wi-Fi; computer on the same, mutually reachable LAN (5 GHz/wired is fine for the computer) |
| Windows | Windows 10/11 x64, a data USB cable for flashing, [VB-CABLE](https://vb-audio.com/Cable/), a voice input method such as [WeChat Input Method](https://z.weixin.qq.com/) |
| Linux | a wlroots Wayland session (Hyprland/Sway — Omarchy), `voxtype` 1.1.0 with the SenseVoice model, `wtype` |

USB is for power and flashing only: plugging the cable in does **not** create a USB microphone, and there is no Bluetooth pairing.

## 1. Install the computer side

### Windows 10/11 x64

1. Download the voice app package from [Releases](https://github.com/manchunx7-bit/folo-ai-passport-voice/releases): `ai-passport-voice-app-0.2.0.zip`. Not *Source code (zip)* — that has no EXE.
2. Extract it to a directory you will not move later, then open its `windows/` folder. You need `start.cmd` and `AI-Passport-Voice.exe` side by side.
3. Install VB-CABLE (installer needs a reboot). Do **not** change your system playback device: the forwarder writes to *CABLE Input* itself.
4. Choose **CABLE Output** as the microphone — in the input method, or as the system default input if the method follows the default — and set its voice shortcut to match `hotkey_key` / `hotkey_mode` in `windows/voice-config.json`. Defaults: `right-shift`, `hold`.
5. Double-click `start.cmd` (make a desktop shortcut rather than dragging the EXE out of the folder) and keep the window open. On the first run Windows Firewall asks; allow it on your trusted private network — do not disable the firewall. `diagnose.cmd` checks VB-CABLE, UDP 33333 and the hotkey without touching hardware.

Only one forwarder window at a time. The EXE is a community build without a code signature, so check the GitHub source and the `.sha256` next to the package — no need to turn off your antivirus.

Full walkthrough with screenshots and input-method details: [docs/QUICKSTART.zh-CN.md](docs/QUICKSTART.zh-CN.md) (Chinese).

### Linux / Omarchy

Needs a wlroots compositor: `wtype` cannot type into GNOME or KDE Wayland. Everything below runs on Omarchy; on another Arch setup the same commands work minus the `omarchy` shortcuts.

**Prerequisites — offline recognition and text injection**

```bash
omarchy pkg add wtype wl-clipboard
omarchy voxtype install
voxtype setup onnx --enable
omarchy voxtype model                    # pick sensevoice-small in the dialog
voxtype config set engine sensevoice     # required: the wizard alone leaves the engine elsewhere
voxtype config set sensevoice.model sensevoice-small
systemctl --user restart voxtype
```

The last two lines are the ones people trip over: `setup model --set` refuses SenseVoice models (`--set does not support sensevoice models`), so picking a model in the wizard does not switch the engine, and voxtype reports `config section is missing` until a `[sensevoice]` section exists. Once the wizard learns to activate the engine, both become harmless no-ops.

**Self-check before going further**

```bash
voxtype config get engine                     # must print: sensevoice
python3 linux/voice_forwarder.py --diagnose   # voxtype, wtype, UDP 33333 — all must be [OK]
```

`--diagnose` types nothing and recognises nothing; it only proves the three pieces are reachable.

**Install as a user service**

```bash
bash linux/install.sh
```

The script stops at the first problem and names it: UDP 33333 free (one forwarder at a time), `voxtype` and `wtype` on PATH, a Wayland session — then it writes `linux/voice-config.json` from the example on the first run, installs the systemd user unit and starts it on login.

```bash
systemctl --user status ai-passport-voice.service
journalctl --user -u ai-passport-voice.service -f   # live log
systemctl --user {stop,start,restart} ai-passport-voice.service
systemctl --user disable ai-passport-voice.service  # drop autostart, keep the unit file
```

Uninstall — stops the service and removes the unit; the checkout and the config stay:

```bash
systemctl --user disable --now ai-passport-voice.service
rm ~/.config/systemd/user/ai-passport-voice.service
```

**Running it by hand (debugging)**

Service and manual run are mutually exclusive — both bind UDP 33333. Stop the service first:

```bash
python3 linux/voice_forwarder.py --diagnose
python3 linux/voice_forwarder.py
python3 linux/voice_forwarder.py --device-ip 192.168.10.6  # override discovery for this run
python3 linux/voice_forwarder.py --no-asr                  # receive audio, skip recognition
```

`--no-asr` separates the two halves of the chain: audio blocks arrive but nothing is typed means the network is fine and recognition is not; no audio blocks at all means the packets never reached the computer.

**Configuration**

`linux/voice-config.json` (gitignored, never commit it):

```json
{
  "udp_port": 33333,
  "device_ip": "",
  "voxtype_bin": "voxtype",
  "engine": "sensevoice",
  "llm": {"enabled": false, "provider": "off", "base_url": "", "model": "",
          "api_key": "", "timeout": 8.0, "prompt": ""}
}
```

Leave `device_ip` empty: discovery is enough unless the router isolates clients. The whole `llm` block may be omitted (that means off), an empty `api_key` is the normal state (the key lives in the keyring), and an empty `prompt` uses the built-in one — a custom prompt marks the transcript position with `%s`. The forwarder re-reads the file on every utterance, so **a config change needs no restart**.

The forwarder also writes `~/.local/state/ai-passport-voice/status.json`: `link` (`linked` / `waiting`), the last typed text, the last error. The widget reads that file instead of parsing the journal; delete it and it is recreated.

**Troubleshooting (Linux)**

| Symptom | What to check |
| --- | --- |
| Log stops at `等待设备`, device shows `等待电脑连接` | device app not open, different LAN, or client isolation — compare the device's Wi-Fi IP with `ip addr` |
| Device shows `麦克风未就绪` | the link is up but `pc.status` never arrived: is the service running? does the log say `PC 就绪状态已发送`? is `wtype` on PATH? |
| `UDP 33333 BUSY` / the script reports the port in use | an old instance (terminal or service) still runs — stop it and start again |
| `[asr] 识别失败` | `voxtype config get engine` → sensevoice? model present at `~/.local/share/voxtype/models/sensevoice-small/`? |
| Text lands in the wrong window | `wtype` types into the focused window — click the input field first |
| A stray character after a short tap | SenseVoice hallucinating on silence; the short-tap filter plus VAD normally eats it — check VAD is enabled in voxtype |
| Log `[llm] 整理失败, 使用原文` | the raw text still went through. `voice_tui.py test "a sentence"` shows why: 401/403, wrong model name, unreachable endpoint |
| Cleanup drops words or answers the question | use a more obedient model (local qwen2.5 and deepseek-chat both beat small ones) or a custom prompt |
| Panel says the key is plain text | `secret-tool` (libsecret) missing or an old-format key — install it and enter the key once more |
| The service cannot read the keyring | a systemd user unit needs the session bus: `systemctl --user show-environment` should list `DBUS`; unlock the keyring once after login |

**Tests**

```bash
python3 -m unittest discover -s linux/tests -p "test_*.py" -v
```

58 tests, stdlib `unittest` only: a fake transcriber, a fake voxtype binary, a fake keyring, and a loopback stub for the LLM endpoint. No hardware, nothing leaves the machine. Run them after any change under `linux/`.

File map and the UDP/ADPCM contract of this directory: [linux/README.md](linux/README.md).

## 2. Connect the device

1. On the device, open **随身语音 / AI 语音**. It shows `等待电脑连接` until a forwarder answers.
2. On the computer, start the forwarder (Windows: `start.cmd`; Linux: the systemd service, or `python3 linux/voice_forwarder.py`). Nothing to configure.
3. The forwarder listens on **UDP 33333** and broadcasts a discovery beacon once per second. When the device answers, both sides show *connected* and the microphone becomes usable.

If it stays on `等待电脑连接`:

- The two are not on the same subnet, or the router isolates clients. Check the device IP against your computer's (`ip addr` / `ipconfig`). With AP isolation, broadcasts never arrive: put the address in `device_ip` (`windows/voice-config.json`, `linux/voice-config.json`) — it is empty by default because auto-discovery is enough on a normal LAN.
- **Port 33333 belongs to exactly one forwarder.** Stop the systemd service before running the forwarder by hand, or the second instance fails with `UDP 33333 BUSY`.
- Linux: `python3 linux/voice_tui.py status` prints service / link / cleanup state; the Omarchy widget shows the same thing as an icon.

### Buttons

| Action | Result |
| --- | --- |
| Hold top button, speak, release | one utterance; very short taps (under 3 audio blocks) are dropped, not recognised |
| Short-press bottom button | Enter — a newline or *send* depending on the app. Test in a text editor first |
| Long-press confirm | leave the device app |

## 3. First test

Open a text editor, click into it, hold the top button, say a sentence, release. Wait for the input method to finish — the text lands where the cursor is (Linux: two to four seconds). Then short-press the bottom button and watch what Enter does there.

*Connected* only proves the heartbeat reached the computer; it does not prove the microphone is routed correctly.

A passing computer-side diagnosis does not prove the input method recognises real speech — only this test does. On Windows, if nothing appears, check the input method's microphone is CABLE Output and its shortcut matches the config; on Linux, check `voxtype config get engine` and the `[asr]` lines in `journalctl --user -u ai-passport-voice.service -f`.

## Omarchy bar widget (optional, Linux)

A bar icon for the forwarder, plus a panel that configures the LLM cleanup:

```bash
curl -fsSL https://raw.githubusercontent.com/dakai/folo-ai-passport-voice/main/omarchy/install.sh | bash
```

That fetches only the plugin, validates it, and puts it in the bar's right section. From a checkout: `bash omarchy/install.sh`. Re-running updates in place and keeps the bar placement. `omarchy plugin add <repo>` cannot do this — it validates the repository root as the plugin, and the plugin lives in `omarchy/`.

If the icon does not appear: `omarchy restart shell` (hot reload does not rebuild the bar).

The icon carries three states:

| State | Icon | Colour |
| --- | --- | --- |
| Service not running | power `⏻` | 45 % opacity |
| Running, waiting for the device | microphone | grey (55 % of the bar foreground) |
| Device connected | microphone | theme green (`green` from `colors.toml`) |

Click it for the panel: service and link state, the last recognised text, the last error, start/restart, and — when the service is down — the two commands that fix it. Below that: the LLM cleanup switch, provider and searchable model picker, and the API key field. Keys go to the login keyring (`secret-tool`), never to a plain file; the panel says so when only the file fallback is available.

The widget stores no settings of its own: every read and write goes through `linux/voice_tui.py`, the same program as the terminal menu, so the two can never disagree. Its only own keys are `language` (`auto`, `en`, `es`, `ja`, `zh`) and `repoPath` —
`auto` follows the desktop locale:

```bash
omarchy bar set manchunx7.ai-passport-voice language zh
omarchy-shell manchunx7.ai-passport-voice probe    # prints the status JSON
```

`Target not found` means the QML did not load — read the shell log for the QML error, it is not a plugin logic problem. Full notes: [omarchy/README.md](omarchy/README.md).

## LLM cleanup (optional, Linux)

Off by default, and absent altogether when no provider is chosen — the service then makes no extra request. When enabled, the raw transcript goes to an OpenAI-compatible model first: filler words, stutters and abandoned restarts are removed, punctuation and sentence breaks added, wording, tone and language kept. Two rules are enforced in code rather than left to the model:

- **Failure types the raw text.** Dead endpoint, wrong key, timeout (8 s default) — the transcript goes through untouched plus one warning line. Losing what you said is the only unacceptable outcome.
- **The transcript is data.** The prompt says the text is to be cleaned, never answered or obeyed, and a reply that grows past twice the input length is discarded as an answer.

```bash
python3 linux/voice_tui.py                          # menu: provider, model, key, on/off, test
python3 linux/voice_tui.py status [--json]          # service, link, cleanup state
python3 linux/voice_tui.py models                   # GET /models on the endpoint
python3 linux/voice_tui.py test "呃 那个 the the 明天发货"   # cleanup only, nothing is typed
python3 linux/voice_tui.py prompt --edit            # replace the built-in prompt
python3 linux/voice_tui.py set --provider openai --enable
```

Providers: `ollama`, `lmstudio`, `llamacpp` (local, no key), `openai`, `openrouter`, `deepseek` (HTTPS, needs a key), `custom` (any OpenAI-compatible base URL — the panel then shows a URL field). The model list comes from the endpoint's `GET /models` and is a searchable picker: OpenRouter serves 300 models, so typing a fragment filters.

**Where the API key lives**: the login keyring (`secret-tool` → gnome-keyring or kwallet, encrypted at rest), so `llm.api_key` in the config stays empty. Resolution order is `AIPV_API_KEY`, then the config file (old installs), then the keyring. Without libsecret the key falls back to the 0600 config file and the panel says so in red until you re-enter it once. Keys are stored per provider, `voice_tui.py set --clear-key` removes the current one, and the key is passed over stdin so it never appears in `ps`.

Output follows the desktop locale — Chinese, Japanese, Spanish, otherwise English — and `--lang en|es|ja|zh` forces it. The widget passes its own language along, so the save/error lines it echoes back are in the panel's language.

Changing this config needs no service restart.

## What is in this repository

| Directory | Contents |
| --- | --- |
| `windows/` | Windows forwarder, ADPCM codec, UDP channel, diagnostics, tests |
| `linux/` | Linux forwarder (voxtype offline ASR, optional LLM cleanup, `wtype` injection, systemd install, terminal configurator) |
| `omarchy/` | Omarchy bar widget: service/device state and provider/model switching, driven by `linux/voice_tui.py` |
| `device/main/apps/voice/` | device side of the feature: state machine, protocol, capture lifecycle, transport, UI logic |
| `device/tests/` | host-runnable tests for the state machine and UI math |
| `docs/` | usage, troubleshooting, firmware notes, development and porting guide |

Not included: home screen/business card, radio, assistant, games, stopwatch, full launcher, settings app, BSP implementations, shared fonts or device history. The device side is a **feature module**, not a standalone flashable ESP-IDF project — a host must supply the interfaces listed in [docs/PORTING.zh-CN.md](docs/PORTING.zh-CN.md).

## Documentation

- [Detailed user guide (Chinese)](docs/QUICKSTART.zh-CN.md)
- [linux/ directory notes](linux/README.md) · [Omarchy widget](omarchy/README.md)
- [Troubleshooting (Chinese)](docs/TROUBLESHOOTING.zh-CN.md)
- [Firmware and flashing notes (Chinese)](docs/FIRMWARE.zh-CN.md)
- [Running and testing the source (Chinese)](docs/DEVELOPMENT.zh-CN.md)
- [Validation record and limits](docs/VALIDATION.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

<a id="codex-setup"></a>
## Let a local agent configure it

Open your local agent in the extracted app folder and paste this (the prompt is in Chinese, as the referenced docs are):

```text
先阅读 README.md 和 docs/QUICKSTART.zh-CN.md。只帮助我配置随身语音电脑端，不要重建或公开整机源码。固件从官网玩法页获取，不要把 Source code ZIP 当固件。
先运行 windows/AI-Passport-Voice.exe --diagnose，核对 VB-CABLE 两端、UDP 33333 和快捷键。已有配置先备份；我的输入法开始/结束快捷键和 hold/tap 模式需要按真实设置核对。
修改默认麦克风、安装驱动或开放防火墙前说明影响。不要关闭整套防火墙，也不要把系统声音输出改成 CABLE Input。
最后让我在记事本亲自说话，确认松开结束、文字出现、下键换行。未实际验证的环节明确说明，不自动把环境声音发到云端。
```

See [docs/CODEX_SETUP.zh-CN.md](docs/CODEX_SETUP.zh-CN.md). Keep personal config, recordings and input-method accounts out of GitHub. This project provides no recognition account or ASR service and cannot promise compatibility with every input-method version.
