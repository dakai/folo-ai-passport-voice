# AI Passport 语音 · Omarchy 栏插件

<img src="https://raw.githubusercontent.com/dakai/folo-ai-passport-voice/main/docs/images/omarchy-panel.webp" alt="面板: 服务状态、最近一条上屏文字与 LLM 整理设置" width="360">

栏上只有一个图标, 不带文字。三种状态用「图标 + 颜色」两个维度区分:

| 状态 | 图标 | 颜色 |
|---|---|---|
| 服务未运行 | 电源 `⏻` | 45% 淡化 |
| 服务在跑、等设备 | 麦克风 | 灰度 (前景色 55%) |
| 设备已连接 | 麦克风 | 主题绿色 |

绿色取自当前主题 `colors.toml` 的 `green` (`Commons.Color` 只暴露
foreground/accent/urgent/muted, 所以插件自己读这一个值; 读不到回退 `#9ece6a`)。
带斜杠的麦克风 `` 故意不用: 它读作「已静音」, 而这里并没有静音状态 —
「服务没跑」用电源符号表达不会有歧义; 若以后真加静音, 斜杠麦克风留给它。

悬停有 tooltip。点开是面板:

- **服务状态**: 是否运行、设备是否已连 (读 `status.json`, 不解析 journal)、
  最近一条上屏文字、最近一次错误。
- **服务没跑时** 面板直接写出两条修复命令 (`systemctl --user start …` /
  `bash linux/install.sh`), 右上角按钮从「重启」变成「启动」。
- **服务在跑但没设备** 时提示在设备上打开「AI 语音」并按住上键说话。
- **LLM 整理开关 / provider / 模型**: provider 用普通下拉; 模型用**可搜索下拉**
  (OpenRouter 有 300 个模型, 直接输入片段过滤)。打开面板时自动按当前 provider
  取一次 `GET /models` 并缓存, 换 provider 会重取, ↻ 可手动刷新;
  自定义 provider 会多出 base_url 输入框。
- **API key**: 密码框, 占位文案直接写明存哪 —
  `API key · stored in the login keyring`。经 stdin 传给配置器 (不出现在 `ps` 里),
  存进 **登录密钥环** (`secret-tool`), 不落明文文件; 只有没装 libsecret 时才回退
  到配置文件, 那时占位文案和红色提示都会说明。
- 全部文案跟随系统 locale (zh → 中文, ja → 日本語, 其它 → English),
  可用 `language` 强制。
  面板里回显的保存/错误信息来自 `voice_tui.py`, 插件会带 `--lang` 让它们与面板
  同一语言; 模型列表取不到时每个 provider 每次会话只试一次 (↻ 可重试), 不会每次
  打开面板都重复报错。

插件自身不存设置 (除 `language` / `repoPath`), 所有读写都调用仓库里的
`linux/voice_tui.py` — 与终端菜单是同一个程序, 所以两边永远一致。

## 安装

插件市场里一条命令 (推荐):

```bash
omarchy plugin add https://github.com/dakai/omarchy-ai-passport-voice --enable
omarchy plugin remove manchunx7.ai-passport-voice     # 卸载
```

镜像只带插件本体, **不带转发器**: 面板要读 `linux/voice_tui.py`, 所以仍需先装本仓库
(根 README 的 Linux 一节), 并让 `repoPath` 指向那份 checkout。缺了它面板会提示
「未找到转发器仓库」。卸载插件不动 `voice-config.json`、密钥环和转发器服务。

### 从应用仓库装

插件本体在 `omarchy/`, 安装脚本在 `tools/` (脚本不随插件发布: 市场用
`omarchy plugin add`, 插件仓库不该带能改环境的安装器)。克隆本仓库后:

```bash
bash tools/install-omarchy-plugin.sh
```

脚本只做本地动作: 把 `omarchy/` 覆盖到
`~/.config/omarchy/plugins/manchunx7.ai-passport-voice/` → 校验 → 让 shell 重新扫描
→ 未启用时 `omarchy plugin enable … --section right`。重复运行等于更新,
不会改变栏上位置。仓库不在默认路径时它会顺手把 `repoPath` 写进插件设置,
插件才知道 `linux/voice_tui.py` 在哪。

为什么不能 `omarchy plugin add <本仓库>`: 那个命令把**仓库根目录**当插件校验,
而这里的根是整个项目、插件在 `omarchy/` 子目录 —— 市场用上面那个镜像仓库。

栏上没出现就 `omarchy restart shell`(热重载不会重建已有的栏组件)。

### 镜像

[dakai/omarchy-ai-passport-voice](https://github.com/dakai/omarchy-ai-passport-voice)
是 `omarchy/` 这一份的**只读镜像** —— 别在那里改代码, 改动一律落在本仓库, 再推上去:

```bash
git subtree push --prefix omarchy https://github.com/dakai/omarchy-ai-passport-voice.git main
```

## 设置

| 键 | 说明 |
|---|---|
| `language` | `auto`(默认, 跟 locale) / `en` / `ja` / `zh` |
| `repoPath` | 转发器仓库路径。留空用 `~/Apps/folo-ai-passport-voice` |

```bash
omarchy bar set manchunx7.ai-passport-voice language zh
omarchy bar set manchunx7.ai-passport-voice repoPath /path/to/checkout --json
```

## 自检

```bash
omarchy-shell manchunx7.ai-passport-voice probe   # 打印 status JSON
```

`Target not found` 表示 QML 没加载, 看 shell 日志里的 QML 错误, 不是插件逻辑问题。
