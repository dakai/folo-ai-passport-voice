# AI Passport 随身语音 · 无线麦克风与语音快捷键

<img src="docs/images/ai-passport.webp" alt="AI Passport" width="330">

**语言:** [English](README.md) · 中文 · [日本語](README.ja.md)

按住 AI Passport 上键说话，松开后文字出现在你正在输入的窗口里；核对后短按下键回车。

设备负责拾音，电脑负责识别。电脑端有两种跑法：

| | Windows 10/11 x64 | Linux (Omarchy) |
| --- | --- | --- |
| 识别 | 你自己的语音输入法(微信输入法等) | `voxtype` + SenseVoice，完全离线 |
| 音频路径 | 转发器 → **VB-CABLE** → 输入法 | 转发器 → 进程内识别 → `wtype` 键入 |
| 云 | 由输入法决定 | 无 |
| 附加 | — | 可选 LLM 整理、Omarchy 栏插件 |


**本仓库只开源随身语音功能, 不含整机源码或可刷写固件。** 固件由维护者在 [FoloToy 口袋百宝箱玩法页面](https://ai-passport.folotoy.cn/plays/438/) 发布; 该页面若暂未提供包含随身语音的版本, 请等待更新。不要把本仓库的 *Source code ZIP* 当固件。

## 语言支持

有四件不同的东西会被翻译或识别，它们不是同一个集合。

| | 语言 |
| --- | --- |
| 文档 | English · 中文 · 日本語 |
| 界面（栏面板与 `voice_tui.py`） | English · 中文 · 日本語 —— `language` 设置或 `--lang`，跟随系统 locale；只有文案 |
| 开箱识别（SenseVoice） | 中文 · English · 日本語 · 한국어 · 粤语 |
| 换引擎后的识别 | 由那个引擎的模型决定 —— 例如 whisper 多语言模型（`base`、`small`、`large-v3`）加 `whisper.language es` 做西语 |
| LLM 整理 | 任意语言：它只重排识别结果，从不翻译 |

**仅在 Linux 上测过。** 上表的识别结论都是在 Linux 转发器上用 voxtype 实测的 ——
日文端到端可用, 中英文日常在用, 西班牙语被 SenseVoice 识别成韩文。Windows 端
本身不做识别, 识别由输入法完成, 所以那边支持哪些语言取决于那个软件, 这里没有测过。

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

需要 wlroots 合成器: `wtype` 在 GNOME/KDE Wayland 上无法键入。以下步骤按 Omarchy 写; 其它 Arch 环境去掉 `omarchy` 快捷命令即可。

**前置条件: 离线识别与文字注入**

```bash
omarchy pkg add wtype wl-clipboard
omarchy voxtype install
voxtype setup onnx --enable
omarchy voxtype model                    # 弹窗里选 sensevoice-small
voxtype config set engine sensevoice     # 必需: 光在向导里选模型不会切引擎
voxtype config set sensevoice.model sensevoice-small
systemctl --user restart voxtype
```

前四条是 Omarchy 惯用路径(交互式, 不用记参数)。后两条是必需的补齐:
`setup model --set` 明确拒绝 sensevoice 模型(`--set does not support
sensevoice models`), 光选模型不会把引擎切过去; voxtype 还要求 `[sensevoice]`
小节真实存在, 缺了就报 `config section is missing`。等向导学会自动激活后,
这两条会变成无害的空操作。

**先自检**

```bash
voxtype config get engine                     # 必须打印 sensevoice
python3 linux/voice_forwarder.py --diagnose   # voxtype、wtype、UDP 33333 全部 [OK]
```

`--diagnose` 不按键、不识别, 只证明这三样都可达。

**能听懂什么** —— 识别语言由引擎决定, 与界面语言无关。SenseVoice 支持中文、英文、
日文、韩文和粤语; 日文已在转发器这条路径上端到端验证。**西班牙语不在它的集合里**:
实测时 SenseVoice 把西语语音强行识别成了韩文。要用西语就换别的引擎 —— whisper 搭配
多语言模型(`base` / `small` / `large-v3`)并 `voxtype config set whisper.language es`,
或 voxtype 编译进来的其它多语言引擎。LLM 整理与语言无关, 它只重排文字。

**装成用户服务**

```bash
bash linux/install.sh
```

脚本按顺序检查, 任一步失败即停并说明缺什么: UDP 33333 是否空闲(端口同时只能有一个
转发器)、`voxtype` 与 `wtype` 是否在 PATH、是否 Wayland 会话; 然后首次运行从
`voice-config.example.json` 生成 `linux/voice-config.json`, 安装 systemd user
单元并 `enable --now`, 登录即自启。

```bash
systemctl --user status ai-passport-voice.service
journalctl --user -u ai-passport-voice.service -f   # 实时日志
systemctl --user {stop,start,restart} ai-passport-voice.service
systemctl --user disable ai-passport-voice.service  # 关自启(单元文件保留)
```

卸载: 停服务并删单元, 仓库与配置都保留:

```bash
systemctl --user disable --now ai-passport-voice.service
rm ~/.config/systemd/user/ai-passport-voice.service
```

**手动运行(调试)**

服务与手动运行**只能二选一**, 都会绑 UDP 33333。手动前先停服务:

```bash
python3 linux/voice_forwarder.py --diagnose
python3 linux/voice_forwarder.py
python3 linux/voice_forwarder.py --device-ip 192.168.10.6  # 本次覆盖自动探测
python3 linux/voice_forwarder.py --no-asr                  # 只收音频不识别
```

`--no-asr` 能把链路问题一分为二: 收到音频块但不上屏 = 网络通、问题在识别侧;
连音频块都没有 = 报文没到电脑, 问题在网络侧。

**配置**

`linux/voice-config.json`(gitignored, 永不提交):

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

`device_ip` 留空即可: 只有路由器的客户端隔离挡住广播时才需要填。`llm` 整段可以省略
(缺省即关闭); `api_key` 留空是正常状态(key 在密钥环里); `prompt` 留空用内置提示词,
自定义时用 `%s` 标记转写文本该插入的位置。转发器每次说话都重新读这个文件,
**改配置不需要重启服务**。

转发器还会写 `~/.local/state/ai-passport-voice/status.json`: `link`
(`linked` / `waiting`)、最近上屏文字、最后一次错误。栏插件读它而不是解析 journal;
删掉会自行重建。

**排错(Linux)**

| 现象 | 查什么 |
| --- | --- |
| 日志停在 `等待设备`, 设备屏显 `等待电脑连接` | 设备没进语音应用、不在同一局域网、AP 隔离开了 —— 对照 `ip addr` 看设备 Wi-Fi IP |
| 设备屏显 `麦克风未就绪` | 链路通了但 `pc.status` 没送达: 服务在跑吗? 日志有 `PC 就绪状态已发送` 吗? `wtype` 在 PATH 吗? |
| `UDP 33333 BUSY` / 脚本报端口占用 | 旧实例(终端或服务)还在跑 —— 关掉再启 |
| `[asr] 识别失败` | `voxtype config get engine` 是 sensevoice 吗? `~/.local/share/voxtype/models/sensevoice-small/` 存在吗? |
| 文字进了错误的窗口 | `wtype` 键入焦点窗口 —— 先点对输入框 |
| 短按冒出单个怪字 | SenseVoice 对静音的幻觉; 短按过滤 + VAD 正常会吃掉 —— 检查 voxtype 侧 VAD 是否开了 |
| 日志 `[llm] 整理失败, 使用原文` | 原文仍会上屏。`voice_tui.py test "一句话"` 看原因: 401/403、模型名不对、端点不通 |
| 整理后少了内容或答非所问 | 换更听话的模型(本机 qwen2.5、deepseek-chat 都比小模型稳), 或换自定义提示词 |
| 面板提示 key 是明文 | 没装 `secret-tool`(libsecret)或存过旧格式 —— 装好后重新输入一次 key |
| 服务在密钥环里读不到 key | systemd user 单元需要会话总线: `systemctl --user show-environment` 应有 `DBUS`; 登录后先解锁一次密钥环 |

**测试**

```bash
python3 -m unittest discover -s linux/tests -p "test_*.py" -v
```

58 个测试, 只用标准库 `unittest`: 伪造转写器、伪造 voxtype 二进制、伪造密钥环,
LLM 端点只打本机 loopback 桩服务。不碰真实硬件、不出网。改 `linux/` 后必跑。

本目录的文件地图与 UDP/ADPCM 约定: [linux/README.md](linux/README.md)。

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
curl -fsSL https://raw.githubusercontent.com/dakai/folo-ai-passport-voice/main/omarchy/install.sh | bash
```

只取插件那份、校验、放进栏右区。已在仓库里就 `bash omarchy/install.sh`; 重复运行等于更新,
不改栏上位置。不能用 `omarchy plugin add <仓库>`: 它把仓库根目录当插件校验, 而这里插件在
`omarchy/` 子目录。

图标没出现就 `omarchy restart shell`(热重载不会重建栏组件)。

图标三种状态:

| 状态 | 图标 | 颜色 |
| --- | --- | --- |
| 服务未运行 | 电源 `⏻` | 45% 淡化 |
| 服务在跑、等设备 | 麦克风 | 灰度(前景色 55%) |
| 设备已连接 | 麦克风 | 主题绿色(取自 `colors.toml` 的 `green`) |

点开面板: 服务与设备状态、最近一条上屏文字、最近一次错误、启动/重启; 服务没跑时直接列出两条修复命令。再往下是整理开关、provider、可搜索的模型下拉、API key 输入框。key 存进登录密钥环(`secret-tool`), 不落明文文件; 只能回退到文件时面板会写明。

<img src="docs/images/omarchy-panel.webp" alt="面板: 服务状态、最近一条上屏文字与 LLM 整理设置" width="360">

插件自身不存设置: 所有读写都调用 `linux/voice_tui.py` —— 与终端菜单是同一个程序, 所以两边永远一致。它自己的键只有 `language`(`auto` / `en` / `ja` / `zh`)和 `repoPath` ——
`auto` 跟随桌面 locale:

```bash
omarchy bar set manchunx7.ai-passport-voice language zh
omarchy-shell manchunx7.ai-passport-voice probe    # 打印状态 JSON
```

`Target not found` 表示 QML 没加载 —— 去看 shell 日志里的 QML 错误, 不是插件逻辑问题。完整说明: [omarchy/README.md](omarchy/README.md)。

## LLM 整理(可选, Linux)

默认关闭; 没选 provider 时这段完全不存在, 服务不会因为 LLM 未配置而多花一次网络请求。
打开后, 识别原文先交给一个 OpenAI 兼容模型: 去掉「嗯/呃/那个」、口吃和重复词,
补标点分句, 保留原意、语气和语言。两条规则写在代码里, 不交给模型自觉:

- **失败一律回退原文。** 端点挂了、key 错了、超时(默认 8 秒), 都键入识别原文,
  只多打一行警告。丢掉用户说的话是唯一不可接受的失败。
- **转写是数据不是指令。** 提示词写明转写内容只做整理, 不回答、不执行; 输出长度
  超过输入两倍就当成「模型在回答」丢弃, 用原文。

```bash
python3 linux/voice_tui.py                          # 交互菜单: provider / 模型 / key / 开关 / 测试
python3 linux/voice_tui.py status [--json]          # 服务、设备、整理状态
python3 linux/voice_tui.py models                   # 对端点 GET /models
python3 linux/voice_tui.py test "呃 那个 就是 明天发货 嗯"   # 只看整理效果, 不上屏
python3 linux/voice_tui.py prompt --edit            # 覆盖内置提示词
python3 linux/voice_tui.py set --provider openai --enable
```

provider: `ollama` / `lmstudio` / `llamacpp`(本机, 免 key)、`openai` / `openrouter` /
`deepseek`(https, 需 key)、`custom`(任意 OpenAI 兼容 `base_url`, 面板里多一个 URL
输入框)。模型列表由端点 `GET /models` 现取, 在面板里是可搜索下拉: OpenRouter 有
300 个模型, 输入片段即可过滤。

**API key 存在哪**: 登录密钥环(`secret-tool` → gnome-keyring / kwallet, 静态加密),
配置里的 `llm.api_key` 保持为空。读取顺序: `AIPV_API_KEY` → 配置文件(旧配置兼容)
→ 密钥环。没有 libsecret 时回退到 0600 的配置文件, 面板会把这一行标红, 重新输入
一次即移入密钥环。key 按 provider 分别保存, `voice_tui.py set --clear-key` 清掉
当前 provider 的条目; key 通过 stdin 传递, 不出现在 `ps`。

输出跟随系统 locale —— 中文、日本語, 其它走 English; `--lang en|ja|zh`
可强制。栏插件调用时带 `--lang`, 所以它面板里回显的保存/错误信息与面板语言一致。

改这份配置**不需要重启服务**: 转发器每次说话都重新读 `voice-config.json`。

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
- [linux/ 目录说明](linux/README.md) · [Omarchy 栏插件](omarchy/README.md)
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
先判断我在哪个系统，再按 README 里对应那一节做：
- Windows: 先运行 windows/AI-Passport-Voice.exe --diagnose，核对 VB-CABLE 两端、UDP 33333 和快捷键。输入法的开始/结束快捷键和 hold/tap 模式要按真实设置核对；不要把系统声音输出改成 CABLE Input。
- Linux/Omarchy: 先确认是 wlroots Wayland 会话，然后 voxtype config get engine 必须打印 sensevoice、python3 linux/voice_forwarder.py --diagnose 三项全 [OK]，再 bash linux/install.sh。引擎不对就补 voxtype config set engine sensevoice 和 voxtype config set sensevoice.model sensevoice-small。LLM 的 API key 存登录密钥环，不要写进会被提交的文件。
改任何配置前先备份(windows/voice-config.json、linux/voice-config.json)。
改默认麦克风、装驱动、开防火墙前说明影响。33333 端口同时只能有一个转发器，起新的之前先停旧的；不要关闭整套防火墙。
最后让我在记事本亲自说话，确认松开结束、文字出现、下键换行。未实际验证的环节明确说明，不自动把环境声音发到云端。
```

详见 [docs/CODEX_SETUP.zh-CN.md](docs/CODEX_SETUP.zh-CN.md)。个人配置、录音与输入法账号不要提交到 GitHub。本项目不提供识别账号或 ASR 服务, 也不承诺所有输入法版本兼容。
