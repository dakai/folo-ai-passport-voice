# AI Passport Voice · Omarchy bar widget

<img src="https://raw.githubusercontent.com/dakai/folo-ai-passport-voice/main/docs/images/ai-passport.webp" alt="The AI Passport wearable" width="330"> <img src="https://raw.githubusercontent.com/dakai/folo-ai-passport-voice/main/docs/images/omarchy-panel.webp" alt="The panel: service state, last recognised text, and the LLM cleanup settings" width="330">

**English** · [中文](README.zh-CN.md)

The bar icon and panel for the **AI Passport** wireless microphone on Linux. Hold the top button on the device, speak, release: the recognised text is typed into the window you are in. This widget shows whether that chain is alive and configures the optional LLM cleanup that tidies the transcript before it is typed.

## Where this sits

| Piece | Location |
| --- | --- |
| Device hardware and firmware | **FoloToy AI Passport** — ESP32-C3 · 8 MB flash · no PSRAM · 240 × 320 ST7789P3 display · ES8311 codec · three physical buttons. Sources and board documentation: [FoloToy/ai-passport](https://github.com/FoloToy/ai-passport) |
| The voice feature inside the firmware | Ships inside the device firmware builds published on the [FoloToy play page](https://ai-passport.folotoy.cn/plays/438/); validated on integrated firmware `0.2.0-rc.6`. This project ships no flashable firmware |
| Computer side: Linux forwarder, `voice_tui.py`, Windows companion | [dakai/folo-ai-passport-voice](https://github.com/dakai/folo-ai-passport-voice) |
| This widget | Mirrored from `omarchy/` in the repository above — edit there, not here |

Nothing in this repository flashes the device, changes its Wi-Fi settings, or talks to it directly. The widget only reads what the forwarder reports and rewrites the forwarder's own config.

## What the widget does

One icon, no text:

| State | Icon | Colour |
| --- | --- | --- |
| Service not running | power `⏻` | 45 % opacity |
| Running, waiting for the device | microphone | grey (55 % of the bar foreground) |
| Device connected | microphone | theme green (`green` from `colors.toml`, `#9ece6a` if absent) |

A slashed microphone is deliberately unused — it reads as "muted", and there is no muted state here.

Click for the panel:

- **Service state**: running or not, whether the device is linked, the last recognised text, the last error — read from `status.json`, no journal parsing.
- **Service down**: the two commands that fix it, and the top-right button becomes Start instead of Restart.
- **Running, waiting for the device**: a reminder to open “AI 语音” on the device and hold the top button.
- **LLM cleanup switch, provider, model**: provider is a plain dropdown; the model list is a searchable picker fed by the endpoint's `GET /models` (OpenRouter serves ~300). Fetched on open, refetched when the provider or base URL changes, `↻` refreshes by hand.
- **Custom provider**: an OpenAI-compatible base URL field appears.
- **API key**: a masked field whose placeholder says where the key will go — the login keyring (`secret-tool`), never a plain file. It is passed to the configurator over stdin, so it never shows up in `ps`.

Panel text follows the desktop locale (`zh` → Chinese, `ja` → Japanese, otherwise English) and can be forced with the `language` setting. Lines the panel echoes back come from `voice_tui.py`, which the widget runs with the panel's language, so the two never mix.

## Requirements

- Linux with a wlroots compositor (Omarchy assumed; `wtype` cannot type into GNOME or KDE Wayland).
- The forwarder checkout from [dakai/folo-ai-passport-voice](https://github.com/dakai/folo-ai-passport-voice) with its systemd user unit, because the panel runs `<repoPath>/linux/voice_tui.py` for every read and write. The default is `~/Apps/folo-ai-passport-voice`; set `repoPath` when yours lives elsewhere.

## Install

```bash
omarchy plugin add https://github.com/dakai/omarchy-ai-passport-voice --enable
omarchy plugin remove dakai.ai-passport-voice     # uninstall
```

The plugin repository holds the widget only. The forwarder is installed separately from the app repository (see its Linux section) — without it the panel says it cannot find the checkout.

From an app-repository clone, `bash tools/install-omarchy-plugin.sh` copies `omarchy/` into `~/.config/omarchy/plugins/dakai.ai-passport-voice/`, validates it, rescans the shell and puts it in the right bar section. Re-running updates in place and keeps the placement.

If the icon does not appear, `omarchy restart shell` — hot reload does not rebuild the bar.

## Settings

| Key | Meaning |
| --- | --- |
| `language` | `auto` (default, follows the locale) / `en` / `ja` / `zh` |
| `repoPath` | Forwarder checkout holding `linux/voice_tui.py`. Empty means `~/Apps/folo-ai-passport-voice` |

```bash
omarchy bar set dakai.ai-passport-voice language zh
omarchy bar set dakai.ai-passport-voice repoPath "/path/to/checkout"
```

The widget keeps no state of its own: every read and write goes through `linux/voice_tui.py`, the same program as the terminal menu, so the two can never disagree. Uninstalling it leaves `voice-config.json`, the keyring entry and the forwarder service untouched.

## Self-check

```bash
omarchy-shell dakai.ai-passport-voice probe   # prints the status JSON
```

`Target not found` means the QML did not load — read the shell log for the QML error; it is not a plugin logic problem.

## License

MIT — see [LICENSE](LICENSE).
