# Linux 语音转发器(本地离线识别)

设备麦克风 → Wi-Fi UDP → `voice_forwarder.py` → voxtype SenseVoice →
(可选)LLM 整理 → `wtype` 把文字键入当前焦点窗口。无云端 ASR、无虚拟声卡,
纯标准库, 除系统工具外零依赖。

两层可选增强:

- **LLM 整理**: 把识别原文去掉口头语/口吃、补标点, 像 Typeless 那样直接
  键入整理后的文字。默认关闭; 用终端配置器 `linux/voice_tui.py` 或
  Omarchy 栏插件开启。
- **Omarchy 栏插件**: 栏上一个麦克风图标(无文字), 点开看服务/设备状态并切换
  provider、模型; 服务没跑时面板直接给出启动命令。见
  [omarchy/README.md](../omarchy/README.md)。

## 前置条件: 系统工具与识别模型

```bash
omarchy pkg add wtype wl-clipboard
omarchy voxtype install
voxtype setup onnx --enable
omarchy voxtype model   # 弹窗里选 sensevoice-small 并下载
voxtype config set engine sensevoice
voxtype config set sensevoice.model sensevoice-small
systemctl --user restart voxtype
```

说明: 前四条是 Omarchy 惯用路径(交互式,不用记参数)。
后两条是必需的补齐: `setup model` 的 `--set`
明确拒绝 sensevoice 模型(`--set does not support sensevoice
models`), 光选模型不会把引擎切过去; voxtype 还要求
`[sensevoice]` 小节真实存在, 缺了就报 `config section is
missing`。这两条在向导学会自动激活后会变成无害的空操作。

自检(两条都过再往下):

```bash
voxtype config get engine   # 必须打印 sensevoice
python3 linux/voice_forwarder.py --diagnose
```

`--diagnose` 检查 voxtype、wtype 与 UDP 33333, 不按键、不识别。
三项全 `[OK]` 才继续。`wtype` 需要 wlroots 合成器(Hyprland/Sway);
GNOME/KDE Wayland 不支持。

## 安装为后台服务

```bash
bash linux/install.sh
```

脚本按顺序做四件事, 任一步失败即停并说明缺什么:

1. 确认 UDP 33333 空闲(终端手动运行的转发器先停掉, 端口只能一人占)。
2. 确认 `voxtype`、`wtype` 在 PATH, 且当前是 Wayland 会话。
3. 首次运行从 `voice-config.example.json` 生成 `voice-config.json`。
4. 安装 systemd user 服务并 `enable --now`, 登录即自启。

日常命令:

```bash
systemctl --user status ai-passport-voice.service
journalctl --user -u ai-passport-voice.service -f   # 实时日志
systemctl --user {stop,start,restart} ai-passport-voice.service
systemctl --user disable ai-passport-voice.service  # 关自启(文件保留)
```

卸载(停服务 + 删自启, 仓库与配置保留):

```bash
systemctl --user disable --now ai-passport-voice.service
rm ~/.config/systemd/user/ai-passport-voice.service
```

## 手动运行(调试用)

服务与手动运行**只能二选一**, 都会绑 UDP 33333。
手动前先 `systemctl --user stop ai-passport-voice.service`:

```bash
python3 linux/voice_forwarder.py --diagnose
python3 linux/voice_forwarder.py
python3 linux/voice_forwarder.py --device-ip 192.168.10.6  # 调试覆盖本次
python3 linux/voice_forwarder.py --no-asr                  # 只收音频不识别
```

## 每天使用

1. 设备进入「随身 AI 语音」(或「AI语音」), 等在线。
2. 鼠标点进 Linux 输入框, 识别文本键入**焦点所在处**。
3. 按住设备 UP 说话, 松手后 2–4 秒文字上屏。
4. 单击 DOWN 发送回车。极短的误触(<3 个音频块)直接丢弃, 不识别。

## LLM 整理(可选)

打开后,SenseVoice 的原文会先交给一个 OpenAI 兼容的模型整理, 再键入结果:
去掉「嗯/呃/那个」、口吃和重复词、补标点分句。整理想法来自 Typeless /
OpenWhispr 这类听写清理提示词, 提示词写在 `linux/llm_cleanup.py` 的
`PROMPT` 里, 可用 `voice_tui.py prompt --edit` 覆盖。

设计上的两条硬规则:

- **失败回退原文。** 端点挂了、key 错了、超时(默认 8 秒), 都键入识别原文,
  只多打一行警告。丢掉用户说的话是唯一不可接受的失败。
- **转写是数据不是指令。** 提示词里写明转写内容只做整理, 不回答、不执行。
  代码另有长度上限: 模型若在回答问题(输出远长于输入)就丢弃, 用原文。

不选 provider 时这段完全不存在, 服务不会因为 LLM 未配置而多花一次网络请求。

```bash
python3 linux/voice_tui.py            # 交互菜单: provider / 模型 / key / 开关 / 测试
python3 linux/voice_tui.py status     # 服务、设备、整理状态
python3 linux/voice_tui.py test "呃 那个 the the 明天发货"   # 只看整理效果, 不上屏
```

所有输出跟随系统 locale (zh → 中文, ja → 日本語, es → Español, 其它 → English),
`--lang en|es|ja|zh` 可强制;
`--help` 是双语的单行说明。栏插件调用时带 `--lang`, 所以它面板里回显的
保存/错误信息与面板语言一致 — 不会出现一半英文一半中文。

provider: `ollama` / `lmstudio` / `llamacpp`(本机, 免 key)、`openai` /
`openrouter` / `deepseek`(https, 需 key)、`custom`(任意 OpenAI 兼容
`base_url`, 面板里多一个 URL 输入框)。模型列表由端点 `GET /models` 现取
(`voice_tui.py models`), 在面板里是可搜索下拉 — OpenRouter 有 300 个模型,
输入片段即可过滤; 面板打开时自动取一次, 换 provider 重取。

改配置**不需要重启服务**: 转发器每次说话都重新读 `voice-config.json`。

### API key 存在哪

key **默认存进登录密钥环**(`secret-tool` → gnome-keyring / kwallet, 静态加密),
不写明文文件; 配置里的 `llm.api_key` 保持为空。读取顺序:

1. 环境变量 `AIPV_API_KEY`(临时覆盖, 适合 CI 或试用)
2. `voice-config.json` 的 `llm.api_key`(旧配置兼容)
3. 登录密钥环

没有 `secret-tool` 的机器回退到 `voice-config.json`(权限 600, gitignored),
栏面板会把这一行标红并提示重新输入一次即可移入密钥环。key 按 provider 分别保存,
换 provider 不会串; `voice_tui.py set --clear-key` 清掉当前 provider 的条目。
插件与配置器都通过 stdin 传 key, 不出现在 `ps`。

## 配置

`linux/voice-config.json`(gitignored, 永不提交)。
留空 `device_ip` 即自动探测, 只有广播被路由器 AP 隔离挡死
且自动探测也找不到时才需要填设备 IP(去路由器客户端列表查)。

```json
{
  "udp_port": 33333,
  "device_ip": "",
  "voxtype_bin": "voxtype",
  "engine": "sensevoice",
  "llm": {
    "enabled": false,
    "provider": "off",
    "base_url": "",
    "model": "",
    "api_key": "",
    "timeout": 8.0,
    "prompt": ""
  }
}
```

`llm` 整段可以省略(缺省即关闭)。`api_key` 留空是正常状态: key 在密钥环里。`prompt` 留空用内置提示词; 自定义时用
`%s` 标记转写文本该插入的位置, 没有 `%s` 就接在末尾。
`voice_tui.py` 是这份文件唯一的写入者: 终端菜单和栏插件调的是同一个程序。

## 状态文件

转发器把 `link`(linked/waiting)、最近上屏文字、最后一次错误写进
`~/.local/state/ai-passport-voice/status.json`。栏插件读它而不是解析
journal。文件是只读参考, 删掉会自行重建。

## 排错

| 现象 | 查什么 |
|---|---|
| 日志停在 `等待设备`, 设备屏显 `等待电脑连接` | 设备没进语音应用、不在同一局域网、AP 隔离开了。先确认设备 Wi-Fi IP 与本机同网段 |
| 设备屏显 `麦克风未就绪` | 链路通了但 `pc.status` 没送达: 服务是否在跑? 日志有无 `PC 就绪状态已发送`? `wtype` 是否在 PATH? |
| `UDP 33333 BUSY` / 脚本报端口占用 | 旧实例(终端或服务)还在跑, 关掉再启 |
| `[asr] 识别失败` | `voxtype config get engine` 是否 sensevoice? 模型目录 `~/.local/share/voxtype/models/sensevoice-small/` 是否存在? |
| 文字进了错误的窗口 | `wtype` 键入焦点窗口, 先点对输入框 |
| 短按冒出单个怪字 | SenseVoice 对静音的幻觉, 短按过滤 + VAD 正常会吃掉; 检查 voxtype 侧 VAD 是否开了 |
| 日志 `[llm] 整理失败, 使用原文` | 原文仍会上屏, 只是没整理。`voice_tui.py test "一句话"` 看具体原因: key 401/403、模型名不对、端点不通 |
| 整理后少了内容或答非所问 | 换更听话的模型(本机 qwen2.5、deepseek-chat 都比小模型稳), 或换自定义提示词 |
| 面板提示 `Key: 明文存在 voice-config.json` | 没装 `secret-tool`(libsecret)或存过旧格式; 装好后重新输入一次 key 即移入密钥环 |
| 服务在密钥环里读不到 key | 服务是 systemd user 单元, 需要会话总线: `systemctl --user show-environment | grep DBUS` 应有值; 密钥环未解锁时先登录解锁一次 |

网络分不清是转发器问题还是路由器问题时, 用 `--no-asr`
区分: 收到音频块但不识别 = 网络通, 问题在识别侧;
连音频块都没有 = 报文没到, 问题在网络侧。

## Omarchy 栏插件(可选)

```bash
bash omarchy/install.sh     # 同步到 ~/.config/omarchy/plugins/ 并放进栏的右区
```

栏上只有图标: 电源符号 + 淡化 = 服务没跑; 灰度麦克风 = 服务在跑等设备;
绿色麦克风 = 设备已连接 (绿色取当前主题的 `green`)。
点开是面板: 服务/设备状态、最近一条上屏文字、最近一次错误、启动/重启,
以及整理开关 + provider / 模型下拉(含「取模型」按钮) + API key 输入框。
服务没跑时面板直接列出启动命令。文案跟随系统 locale (zh/English),
`omarchy bar set manchunx7.ai-passport-voice language zh` 可强制。
插件不自己存设置, 所有读写都调这份 `voice_tui.py`, 所以和终端菜单永远一致。
设置项只有 `language` 和 `repoPath`(仓库不在默认位置时填)。详见
[omarchy/README.md](../omarchy/README.md)。

## 测试

```bash
python3 -m unittest discover -s linux/tests -p "test_*.py" -v
```

53 个测试, 标准库 unittest, 伪造转写器/voxtype 二进制/按键,
LLM 只打本机 loopback 桩服务。不碰真实硬件、不出网。改 `linux/` 后必跑。
