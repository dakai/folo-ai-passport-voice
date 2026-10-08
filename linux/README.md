# Linux 语音转发器(本地离线识别)

设备麦克风 → Wi-Fi UDP → `voice_forwarder.py` → voxtype SenseVoice →
`wtype` 把文字键入当前焦点窗口。无云端、无虚拟声卡, 纯标准库,
除系统工具外零依赖。

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

## 配置

`linux/voice-config.json`(gitignored, 永不提交)。
留空 `device_ip` 即自动探测, 只有广播被路由器 AP 隔离挡死
且自动探测也找不到时才需要填设备 IP(去路由器客户端列表查)。

## 排错

| 现象 | 查什么 |
|---|---|
| 日志停在 `等待设备`, 设备屏显 `等待电脑连接` | 设备没进语音应用、不在同一局域网、AP 隔离开了。先确认设备 Wi-Fi IP 与本机同网段 |
| 设备屏显 `麦克风未就绪` | 链路通了但 `pc.status` 没送达: 服务是否在跑? 日志有无 `PC 就绪状态已发送`? `wtype` 是否在 PATH? |
| `UDP 33333 BUSY` / 脚本报端口占用 | 旧实例(终端或服务)还在跑, 关掉再启 |
| `[asr] 识别失败` | `voxtype config get engine` 是否 sensevoice? 模型目录 `~/.local/share/voxtype/models/sensevoice-small/` 是否存在? |
| 文字进了错误的窗口 | `wtype` 键入焦点窗口, 先点对输入框 |
| 短按冒出单个怪字 | SenseVoice 对静音的幻觉, 短按过滤 + VAD 正常会吃掉; 检查 voxtype 侧 VAD 是否开了 |

网络分不清是转发器问题还是路由器问题时, 用 `--no-asr`
区分: 收到音频块但不识别 = 网络通, 问题在识别侧;
连音频块都没有 = 报文没到, 问题在网络侧。

## 测试

```bash
python3 -m unittest discover -s linux/tests -p "test_*.py" -v
```

17 个测试, 标准库 unittest, 伪造转写器/voxtype 二进制/按键,
不碰真实硬件。改 `linux/` 后必跑。
