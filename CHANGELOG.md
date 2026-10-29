# 更新日志

## 未发布

- 插件 id 改为 `dakai.ai-passport-voice`(manifest 的 `author` 也改成 `dakai`), 与 GitHub
  账号一致; 旧的 `manchunx7.*` 是安装身份, 所以 `tools/install-omarchy-plugin.sh` 会删掉
  旧目录、把 `language` / `repoPath` 搬到新 id 上再启用, 文档里的 `bar set` / `plugin
  remove` / `probe` 命令同步更新。
- 修掉 `omarchy bar set … --json` 的用法: 那个参数要求值本身是 JSON, 传普通字符串会被
  拒 (`invalid JSON value`), 所以安装脚本里的 `repoPath` 与迁移来的设置其实从没写进去过;
  现在按纯字符串传。
- 安全: 设备协议没有认证, 所以转发器现在**只认一个对端** —— `device_ip` 填了就只接受
  这个地址 (`--bind` 可再限定网卡); 没填则第一次上报的对端被锁定, 别的主机的报文
  (包括回车)直接丢弃并记日志, 同 IP 换端口仍认。首个应答可被抢的窗口写进了 README
  的「安全模型」。状态文件改成本目录 0700 / 文件 0600 (旧的可读文件下次写入即收紧),
  服务单元加 `UMask=0077`; 键入文字改经 stdin (`wtype -`), 不再出现在进程参数里。
- Omarchy 栏插件提交到社区市场 (omacom/omarchy-plugin-marketplace#13150): 市场只认
  「仓库根目录即插件」, 所以另建只读镜像 `dakai/omarchy-ai-passport-voice`, 由
  `git subtree push --prefix omarchy` 同步, 本仓库仍是唯一来源。镜像只含插件本体 ——
  面板要读 `linux/voice_tui.py`, 转发器仍要装本仓库; 卸载不动配置、密钥环和服务。
  插件仓库的主 README 改为英文、另附 `README.zh-CN.md`, 并在开头写清它属于哪台设备
  与哪份固件 (FoloToy AI Passport 硬件 + 玩法页固件, 已在 `0.2.0-rc.6` 上验证),
  附设备与面板截图。
- Linux 转发器新增可选 **LLM 整理**: 识别原文先去掉口头语/口吃并补标点再键入,
  默认关闭; 失败一律回退原文, 转写内容按数据处理(不回答、不执行)。
- 新增 `linux/voice_tui.py` 终端配置器: 选 provider/模型/key、开关整理、试跑一句;
  `status --json` / `set` / `models` 子命令供插件调用。
- 新增 `linux/voice_config.py`: `voice-config.json` 与 `~/.local/state/ai-passport-voice/status.json`
  的唯一读写者(配置 600 权限, 原子写入)。
- 新增 `omarchy/` 栏插件: 麦克风图标显示服务/设备状态, 点开可重启服务、
  切换 provider 与模型。插件不存设置, 全部经 `voice_tui.py`。
- API key 默认存入登录密钥环 (`secret-tool`), 配置文件不再保留明文; 无 libsecret
  时回退到 0600 文件并在面板标红提示。读取顺序: `AIPV_API_KEY` → 配置文件 → 密钥环。
- 栏插件只显示麦克风图标 (不再带文字); 面板文案跟随系统 locale (zh/English),
  可用 `language` 覆盖。服务未运行时面板直接给出启动命令, 按钮由「重启」变为「启动」。
- 模型选择改为可搜索下拉, 面板打开时按当前 provider 自动取一次模型列表
  (OpenRouter 300 个模型可直接过滤); API key 输入框占位文案写明存入密钥环。
- 修正 `voice_tui.py models --provider X` 的 AttributeError (引用了只有 `set` 才有的参数)。
- `voice_tui.py` 全部输出与 `llm_cleanup` 的错误/日志跟随系统 locale (zh/English),
  `--lang` 可强制; 栏插件调用时传 `--lang`, 面板里回显的
  "Key: 已存入登录密钥环" 一类信息不再与面板语言混用。
- 模型列表取失败后按 provider 记住到本次会话结束 (↻ 或换 provider 才重试),
  避免每次打开面板都重复一次被拒的请求。
- 栏图标状态改为「图标 + 颜色」: 服务没跑用电源符号(淡化), 等设备用灰度麦克风,
  设备已连用主题绿色麦克风; 不再用带斜杠的麦克风 (那是「静音」的语义)。
  面板在等设备时提示到设备上打开「AI 语音」。
- 撤掉 `README.es.md`: 西语识别并不成立(见下), 与其让西语文档暗示支持, 不如只留
  实测过的三份。根 README 新增「语言支持」一节, 分列文档、界面、识别、整理四个集合,
  并注明**只在 Linux 上测过**、Windows 端识别由输入法决定。
- LLM 整理提示词的填充词示例补上西语与日语(`este/bueno/o sea/pues`、`えーと/あの/その/まあ`),
  之前只列了中英; 识别语言本身仍由 ASR 引擎决定。
- README 的 Linux 一节写清「能听懂什么」: SenseVoice 覆盖中文、英文、日文、韩文、粤语
  (日文已实测), 西语需换 whisper 等多语言引擎 —— 界面语言与识别语言是两件事。
- Omarchy 插件的安装不再走「下载即执行」: 脚本移到 `tools/install-omarchy-plugin.sh`,
  必须在本仓库的 clone 里运行 (转发器本来也需要这份 clone), 就先拷贝 `omarchy/`、
  校验、再启用, 重复运行等于更新。插件本体与市场用的镜像仓库里不含安装器 ——
  市场那条路径是 `omarchy plugin add …`。
- 界面语言去掉西班牙语, 只留 **English / 中文 / 日本語**(`en` / `ja` / `zh` +
  `auto`): 识别本来就没有西语, 四套字符串表维护不起。旧配置里残留的
  `language: es` 或 `--lang es` 会被忽略并回退到系统 locale, 不会半截加载。
- 界面语言新增 **日语**: 终端配置器、LLM 整理的消息、Omarchy 面板
  都跟随 locale (zh / ja, 其它回退英文), `--lang` 与面板 `language`
  可强制; 三种语言的字符串表由测试保证 key 一致。
- Linux 的安装、配置、排错与测试说明从 `linux/README.md` 并入根 README
  (三种语言同步); `linux/README.md` 只留目录本身: 文件职责、报文约定、约束。
- README 改为以「安装 + 连接设备 + Omarchy 插件」为主线, 并新增
  `README.zh-CN.md`、`README.ja.md`(三份互相链接; 西语 README 已撤)。
- Linux 测试 17 → 54 项, 覆盖配置规范化、端点策略、失败回退、状态文件、key 存储与配置器。

## 0.2.0-app.1 · 2026-10-06

- 将随身语音拆分为独立项目，仅公开本功能设备业务代码、Windows 配套程序、测试和教程。
- Windows 应用包不再携带整机固件、其他应用源码或旧整机历史；固件获取入口改为官网玩法页。
- 保留已验证的按住录音、松开释放、下键 Enter、残留状态对账和重复回车保护，不为本次拆分改变设备逻辑。
- 明确普通使用与开发者移植的区别，新增宿主接口说明及应用范围检查。

本版本是应用项目发布，不是新的整机固件。适配验证基于已测试的集成固件 0.2.0-rc.6；具体边界见 docs/VALIDATION.md。
