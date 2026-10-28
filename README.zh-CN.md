# AI Passport 随身语音 · 无线麦克风与语音快捷键

<img src="https://ai-passport.folotoy.cn/api/media/plays/community-1353f966/gallery/0.webp?v=3715-4" alt="AI Passport" width="330">

**语言:** [English](README.md) · 中文 · [Español](README.es.md) · [日本語](README.ja.md)

按住 AI Passport 上键说话，松开后文字出现在你正在输入的窗口里；核对后短按下键回车。

设备负责拾音，电脑负责识别。电脑端有两种跑法：

| | Windows 10/11 x64 | Linux (Omarchy) |
| --- | --- | --- |
| 识别 | 你自己的语音输入法(微信输入法等) | `voxtype` + SenseVoice，完全离线 |
| 音频路径 | 转发器 → **VB-CABLE** → 输入法 | 转发器 → 进程内识别 → `wtype` 键入 |
| 云 | 由输入法决定 | 无 |
| 附加 | — | 可选 LLM 整理、Omarchy 栏插件 |


**本仓库只开源随身语音功能, 不含整机源码或可刷写固件。** 固件由维护者在 [FoloToy 口袋百宝箱玩法页面](https://ai-passport.folotoy.cn/plays/438/) 发布; 该页面若暂未提供包含随身语音的版本, 请等待更新。不要把本仓库的 *Source code ZIP* 当固件。

## 需要什么

| | 要求 |
| --- | --- |
| 设备 | FoloToy AI Passport 同款硬件: ESP32-C3、8 MB Flash、ES8311 |
| 固件 | 包含“随身语音”的版本(见上); 安装会替换设备当前玩法 |
| 网络 | 设备接 **2.4 GHz** Wi-Fi; 电脑与设备在同一可互通的局域网(电脑用 5 GHz 或网线都行) |
| Windows | Windows 10/11 x64、数据 USB 线(刷机用)、[VB-CABLE](https://vb-audio.com/Cable/)、[微信输入法](https://z.weixin.qq.com/)等语音输入法 |
| Linux | wlroots Wayland 会话(Hyprland/Sway, 如 Omarchy)、`voxtype` 1.1.0 + SenseVoice 模型、`wtype` |

USB 只用于供电和烧录: 插上 USB **不会**让设备变成 USB 麦克风, 也不需要蓝牙配对。

## 一、安装电脑端

### Windows 10/11 x64

1. 在 [Releases](https://github.com/manchunx7-bit/folo-ai-passport-voice/releases) 下载语音应用包 `ai-passport-voice-app-0.2.0.zip`。不要选 *Source code (zip)* —— 里面没有 EXE。
2. 解压到一个以后不会移动的目录, 打开里面的 `windows/` 文件夹; `start.cmd` 和 `AI-Passport-Voice.exe` 必须在一起。
3. 安装 VB-CABLE(装完要重启)。**不要**改系统播放设备: 转发器自己把声音写进 *CABLE Input*。
4. 麦克风选 **CABLE Output** —— 在输入法里选, 或把系统默认输入设为 CABLE Output 让输入法跟随(系统默认播放保持原来的扬声器)。语音快捷键要与 `windows/voice-config.json` 里的 `hotkey_key`、`hotkey_mode` 一致(默认 `right-shift`、`hold`)。
5. 双击 `start.cmd`(要桌面图标就右键创建快捷方式, 不要把 EXE 拖出来), 窗口保持开启; 首次出现防火墙提示时在信任的专用网络允许, 不要关闭防火墙。`diagnose.cmd` 只检查 VB-CABLE、UDP 33333 与快捷键, 不碰硬件。

同一时间只运行一个转发窗口。EXE 是社区发布的未签名版本, 核对 GitHub 来源与包旁的 `.sha256` 即可, 不必关闭安全软件。

带截图和输入法细节的完整教程: [docs/QUICKSTART.zh-CN.md](docs/QUICKSTART.zh-CN.md)。

### Linux / Omarchy

需要 wlroots 合成器: `wtype` 在 GNOME/KDE Wayland 上无法键入。Omarchy 上按顺序:

```bash
omarchy pkg add wtype wl-clipboard
omarchy voxtype install
voxtype setup onnx --enable
omarchy voxtype model                    # 弹窗里选 sensevoice-small
voxtype config set engine sensevoice     # 必需: 光在向导里选模型不会切引擎
voxtype config set sensevoice.model sensevoice-small
systemctl --user restart voxtype
```

两项自检都过, 再把转发器装成用户服务:

```bash
voxtype config get engine                 # 必须打印 sensevoice
python3 linux/voice_forwarder.py --diagnose   # voxtype + wtype + UDP 33333, 全部 [OK]
bash linux/install.sh                     # systemd user 单元, 登录即自启
```

细节、选项与排错: [linux/README.md](linux/README.md)。

## 二、连接设备

1. 设备上打开 **随身语音 / AI 语音**, 屏幕显示 `等待电脑连接` 直到有转发器应答。
2. 电脑上启动转发器(Windows: `start.cmd`; Linux: systemd 服务, 或 `python3 linux/voice_forwarder.py`)。无需任何配置。
3. 转发器监听 **UDP 33333**, 每秒广播一次发现报文; 设备应答后两边都显示已连接, 麦克风才可用。

一直停在 `等待电脑连接` 时:

- 两者不在同一网段, 或路由器开了客户端隔离。对照电脑的 IP(`ip addr` / `ipconfig`)看设备 IP。隔离会挡掉广播: 把地址填进 `device_ip`(`windows/voice-config.json`、`linux/voice-config.json`)。该字段默认为空, 因为正常局域网自动探测就够。
- **33333 端口同时只能有一个转发器。** 手动跑之前先停服务, 否则第二个实例报 `UDP 33333 BUSY`。
- Linux: `python3 linux/voice_tui.py status` 打印服务/链路/整理状态; Omarchy 栏插件用图标显示同样的信息。

### 按键

| 动作 | 结果 |
| --- | --- |
| 按住上键说话, 松开 | 一次语音; 极短误触(少于 3 个音频块)直接丢弃, 不识别 |
| 短按下键 | 回车 —— 是换行还是发送由当前软件决定。先在记事本试 |
| 长按确定 | 退出设备应用 |

## 三、首次验收

打开记事本, 点进正文, 按住上键说一句, 松手, 等输入法完成识别 —— 文字落在光标处(Linux 侧 2–4 秒)。再短按下键, 看回车在当前软件里做了什么。

“电脑已连接”只证明网络心跳到达, 不证明输入法已经选对麦克风。

电脑端诊断通过不等于输入法真实识别已验收 —— 只有这一步能证明。Windows 上没出字, 先查输入法麦克风是否为 CABLE Output、快捷键是否与配置一致; Linux 上查 `voxtype config get engine` 和 `journalctl --user -u ai-passport-voice.service -f` 里的 `[asr]` 行。

## Omarchy 栏插件(可选, Linux)

栏上一个图标显示转发器状态, 点开是面板, 顺手配 LLM 整理:

```bash
bash omarchy/install.sh      # 同步到 ~/.config/omarchy/plugins/ 并放进栏右区
omarchy restart shell        # 图标没出现才需要; 热重载不会重建栏组件
```

图标三种状态:

| 状态 | 图标 | 颜色 |
| --- | --- | --- |
| 服务未运行 | 电源 `⏻` | 45% 淡化 |
| 服务在跑、等设备 | 麦克风 | 灰度(前景色 55%) |
| 设备已连接 | 麦克风 | 主题绿色(取自 `colors.toml` 的 `green`) |

点开面板: 服务与设备状态、最近一条上屏文字、最近一次错误、启动/重启; 服务没跑时直接列出两条修复命令。再往下是整理开关、provider、可搜索的模型下拉、API key 输入框。key 存进登录密钥环(`secret-tool`), 不落明文文件; 只能回退到文件时面板会写明。

插件自身不存设置: 所有读写都调用 `linux/voice_tui.py` —— 与终端菜单是同一个程序, 所以两边永远一致。它自己的键只有 `language`(`auto` / `en` / `es` / `ja` / `zh`)和 `repoPath` ——
`auto` 跟随桌面 locale:

```bash
omarchy bar set manchunx7.ai-passport-voice language zh
omarchy-shell manchunx7.ai-passport-voice probe    # 打印状态 JSON
```

`Target not found` 表示 QML 没加载 —— 去看 shell 日志里的 QML 错误, 不是插件逻辑问题。完整说明: [omarchy/README.md](omarchy/README.md)。

## LLM 整理(可选, Linux)

默认关闭。打开后识别原文先交给一个 OpenAI 兼容模型: 去掉「嗯/呃/那个」、口吃和重复词, 补标点分句, 保留原意和语言。任何失败(超时、key 错、端点不通)都键入识别原文 —— 丢掉用户说的话是唯一不可接受的失败。

```bash
python3 linux/voice_tui.py          # 菜单: provider / 模型 / key / 开关 / 测试
python3 linux/voice_tui.py test "呃 那个 the the 明天发货"   # 只看整理效果, 不上屏
```

provider: `ollama`、`lmstudio`、`llamacpp`(本机, 免 key)、`openai`、`openrouter`、`deepseek`(需 key)、`custom`(任意 OpenAI 兼容 base URL)。改配置无需重启服务。

## 仓库内容

| 目录 | 内容 |
| --- | --- |
| `windows/` | Windows 转发器、ADPCM 编解码、UDP 通道、诊断与测试 |
| `linux/` | Linux 转发器(voxtype 离线识别、可选 LLM 整理、`wtype` 键入、systemd 安装、终端配置器) |
| `omarchy/` | Omarchy 栏插件: 服务/设备状态与 provider/模型切换, 调用 `linux/voice_tui.py` |
| `device/main/apps/voice/` | 设备端功能模块: 状态机、协议、录音生命周期、传输、界面业务代码 |
| `device/tests/` | 状态机与界面数学的主机可运行测试 |
| `docs/` | 使用、排错、固件入口、开发与底层接口适配说明 |

不包含: 首页/名片、收音机、小智、游戏、秒表、整机启动器、设置页、BSP 实现、共享字体或整机历史。设备端是**功能模块源码**, 不是单独可刷写的 ESP-IDF 工程; 宿主接口见 [docs/PORTING.zh-CN.md](docs/PORTING.zh-CN.md)。

## 文档

- [详细使用教程](docs/QUICKSTART.zh-CN.md)
- [Linux 转发器](linux/README.md) · [Omarchy 栏插件](omarchy/README.md)
- [常见故障排查](docs/TROUBLESHOOTING.zh-CN.md)
- [官网固件与刷写注意](docs/FIRMWARE.zh-CN.md)
- [源码运行与测试](docs/DEVELOPMENT.zh-CN.md)
- [验证记录及限制](docs/VALIDATION.md)
- [第三方来源](THIRD_PARTY_NOTICES.md)

<a id="codex-setup"></a>
## 让本地 Codex 帮忙配置

在解压后的应用包目录打开本地 Codex, 复制:

```text
先阅读 README.md 和 docs/QUICKSTART.zh-CN.md。只帮助我配置随身语音电脑端，不要重建或公开整机源码。固件从官网玩法页获取，不要把 Source code ZIP 当固件。
先运行 windows/AI-Passport-Voice.exe --diagnose，核对 VB-CABLE 两端、UDP 33333 和快捷键。已有配置先备份；我的输入法开始/结束快捷键和 hold/tap 模式需要按真实设置核对。
修改默认麦克风、安装驱动或开放防火墙前说明影响。不要关闭整套防火墙，也不要把系统声音输出改成 CABLE Input。
最后让我在记事本亲自说话，确认松开结束、文字出现、下键换行。未实际验证的环节明确说明，不自动把环境声音发到云端。
```

详见 [docs/CODEX_SETUP.zh-CN.md](docs/CODEX_SETUP.zh-CN.md)。个人配置、录音与输入法账号不要提交到 GitHub。本项目不提供识别账号或 ASR 服务, 也不承诺所有输入法版本兼容。
