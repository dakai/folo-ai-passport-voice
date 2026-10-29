# AI Passport 语音 · Omarchy 栏插件

<img src="https://raw.githubusercontent.com/dakai/folo-ai-passport-voice/main/docs/images/ai-passport.webp" alt="AI Passport 随身设备" width="330"> <img src="https://raw.githubusercontent.com/dakai/folo-ai-passport-voice/main/docs/images/omarchy-panel.webp" alt="面板: 服务状态、最近一条上屏文字与 LLM 整理设置" width="330">

[English](README.md) · **中文**

Linux 上 **AI Passport** 无线麦克风的栏图标与面板。按住设备上键说话, 松手, 识别文字就落在
当前窗口里。这个插件显示这条链路是否活着, 并配置可选的 LLM 整理 —— 上屏前把口语顺一遍。

## 它在哪个位置

| 部分 | 位置 |
| --- | --- |
| 设备硬件与固件 | **FoloToy AI Passport** —— ESP32-C3 · 8 MB Flash · 无 PSRAM · 240 × 320 ST7789P3 屏 · ES8311 编解码 · 三个实体按键。源码与板级文档: [FoloToy/ai-passport](https://github.com/FoloToy/ai-passport) |
| 固件里的语音功能 | 随设备固件一起发布, 入口是 [FoloToy 玩法页](https://ai-passport.folotoy.cn/plays/438/); 已在集成固件 `0.2.0-rc.6` 上验证。本项目不含可刷写的固件 |
| 电脑端: Linux 转发器、`voice_tui.py`、Windows 配套 | [dakai/folo-ai-passport-voice](https://github.com/dakai/folo-ai-passport-voice) |
| 本插件 | 由上面仓库的 `omarchy/` 镜像而来 —— 改动请落在那边, 不要在这里改 |

本仓库不刷机、不改设备的 Wi-Fi, 也不直接和设备通信。插件只读转发器报告的状态、
只写转发器自己的配置。

## 插件做什么

栏上只有一个图标, 不带文字:

| 状态 | 图标 | 颜色 |
| --- | --- | --- |
| 服务未运行 | 电源 `⏻` | 45% 淡化 |
| 服务在跑、等设备 | 麦克风 | 灰度 (前景色 55%) |
| 设备已连接 | 麦克风 | 主题绿色 (`colors.toml` 的 `green`, 读不到回退 `#9ece6a`) |

带斜杠的麦克风故意不用 —— 它读作「已静音」, 而这里没有静音状态。

点开是面板:

- **服务状态**: 是否运行、设备是否已连、最近一条上屏文字、最近一次错误 —— 读
  `status.json`, 不解析 journal。
- **服务没跑**: 直接写出两条修复命令, 右上角按钮从「重启」变成「启动」。
- **在跑但没设备**: 提示到设备上打开「AI 语音」并按住上键说话。
- **LLM 整理开关 / provider / 模型**: provider 是普通下拉; 模型是**可搜索下拉**,
  由端点的 `GET /models` 填充 (OpenRouter 有 300 个)。打开面板取一次, 换 provider
  或 base URL 会重取, `↻` 可手动刷新。
- **自定义 provider**: 多出 OpenAI 兼容的 base URL 输入框。
- **API key**: 密码框, 占位文案写明存哪 —— 登录密钥环 (`secret-tool`), 不落明文文件;
  经 stdin 传给配置器, 不出现在 `ps` 里。

面板文案跟随系统 locale (zh → 中文, ja → 日本語, 其它 → English), 可用 `language`
强制。面板里回显的保存/错误信息来自 `voice_tui.py`, 插件调用时带上面板语言, 两边不会混。

## 前提

- Linux + wlroots 合成器 (按 Omarchy 写; `wtype` 在 GNOME/KDE Wayland 上无法键入)。
- [dakai/folo-ai-passport-voice](https://github.com/dakai/folo-ai-passport-voice) 的
  checkout 与它的 systemd user 单元 —— 面板每次读写都跑 `<repoPath>/linux/voice_tui.py`。
  默认路径 `~/Apps/folo-ai-passport-voice`, 放在别处就把 `repoPath` 指过去。

## 安装

```bash
omarchy plugin add https://github.com/dakai/omarchy-ai-passport-voice --enable
omarchy plugin remove dakai.ai-passport-voice     # 卸载
```

插件仓库只带插件本体, 转发器要从应用仓库单独装 (见那边的 Linux 一节);
没有它面板会提示找不到 checkout。

在应用仓库的 clone 里, `bash tools/install-omarchy-plugin.sh` 会把 `omarchy/` 覆盖到
`~/.config/omarchy/plugins/dakai.ai-passport-voice/`, 校验、让 shell 重新扫描,
放进栏右区; 重复运行等于更新, 不改栏上位置。

图标没出现就 `omarchy restart shell` —— 热重载不会重建已有的栏组件。

## 设置

| 键 | 说明 |
| --- | --- |
| `language` | `auto`(默认, 跟 locale) / `en` / `ja` / `zh` |
| `repoPath` | 转发器仓库路径, 里面要有 `linux/voice_tui.py`。留空用 `~/Apps/folo-ai-passport-voice` |

```bash
omarchy bar set dakai.ai-passport-voice language zh
omarchy bar set dakai.ai-passport-voice repoPath "/path/to/checkout"
```

插件自身不存状态: 所有读写都调用 `linux/voice_tui.py` —— 与终端菜单是同一个程序,
所以两边永远一致。卸载插件不动 `voice-config.json`、密钥环和转发器服务。

## 自检

```bash
omarchy-shell dakai.ai-passport-voice probe   # 打印 status JSON
```

`Target not found` 表示 QML 没加载, 看 shell 日志里的 QML 错误, 不是插件逻辑问题。

## 许可

MIT —— 见 [LICENSE](LICENSE)。
