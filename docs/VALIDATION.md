# 随身语音验证边界

本次仅拆分仓库和文档，没有改变设备业务代码或 Windows 程序。独立项目不是新的整机固件版本。

在已验证的集成固件 `0.2.0-rc.6` 上，Windows EXE 与实机完成 3 轮按住上键、松开、下键测试：12 个系统注入键事件顺序正确，语音键释放 47–93 ms，Enter 16–47 ms。测试拦截键事件，未向用户当前窗口提交文字。这不是输入法识别准确率测试。

Windows 转发器 15 项单测覆盖 hold/tap、结束释放、残留状态对账、重复 Enter、音频失败回退等。设备纯状态机与界面数学通过 host 测试。新的应用目录再次独立运行这些测试；GitHub Actions 记录对应提交结果。

PC EXE 来自 Python 3.11.8、sounddevice 0.5.6、PyInstaller 6.20.0，源码与本项目 Windows 文件一致；EXE 的 `--help`、`--diagnose` 已检查。

**未验收：** 新电脑从零安装、其他输入法/系统版本、真实字错误率、长时运行、用户自定义宿主的整机编译及音质。本仓库不分发整机 BIN，不宣称这里的模块可直接刷机。

## 2026-10-28 · Linux LLM 整理与 Omarchy 栏插件

- `python3 -m unittest discover -s linux/tests` 46 项通过(Windows/设备测试本次未改动)。
- `tools/check_scope.py` 通过; `omarchy plugin validate` 通过。
- 插件装入本机 Omarchy 后 shell 热加载无 QML 报错, `omarchy-shell manchunx7.ai-passport-voice probe`
  返回真实状态 JSON; 面板截图确认服务状态、最近文字、provider/模型取自同一份配置。
- 配置器 `set` 写盘后 `probe` 立即反映; `set --enable` 在未选 provider 时按预期拒绝。
- 2026-10-28 复验: 栏图标无文字; 面板文案在 `LANG=en_US` 下全英文、`language=zh`
  下全中文 (含 provider 标签); 停服后面板显示两条启动命令且按钮变为「启动」;
  执行 `bin/aipv service start` 后状态回到运行中。
- key 存储: `set --api-key -` 写入登录密钥环, 配置文件 `llm.api_key` 保持空,
  `status --json` 报 `keyStorage: keyring`; `systemd-run --user` 起的进程能读到同一
  key (证明 systemd user 单元环境里有会话总线)。
- 2026-10-28 复验(二): OpenRouter 免 key `models` 返回 300 条; 面板打开即自动取列表
  并显示 "300 models", 模型触发器显示当前模型; key 占位文案为
  "API key · stored in the login keyring"; `models --provider X` 的 AttributeError 已修
  并有回归测试 (54 项通过)。
- 2026-10-28 复验(三): `LANG=en_US` 下 `status`/`set`/`models` 与清理错误全英文,
  `LANG=zh_CN` 下全中文; `--lang` 覆盖生效; 插件等价调用
  `bin/aipv set --api-key - --lang en|zh` 分别输出
  "Key: stored in the login keyring" / "Key: 已存入登录密钥环"; 面板截图里模型列表
  的 401 也已是英文。测试期间误改的本机 `voice-config.json` (model 被写成 test-model)
  已按原值 `auto/deepseek-v4.1-flash` 恢复。
- 2026-10-28 复验(四): 栏图标三态截图确认 — 停服后为淡化的电源符号; 服务在跑无设备
  为前景色麦克风; 把 `status.json` 的 `link` 临时改为 `linked` 后为绿色麦克风
  (取自主题 `colors.toml` 的 `green`), 随后重启服务恢复。面板在等设备时显示
  "Open “AI voice” on the device…" 提示。
- 2026-10-28 复验(五): 界面语言扩到四种。`status --lang es|ja` 与 `LANG=ja_JP.UTF-8`
  都输出对应语言; 面板 `language` 设为 `es` / `ja` 后截图确认整块面板(含 provider
  标签与取模型失败的 401)同语言。顺带修掉一个混合语言缺陷: `llm_cleanup` 只读
  环境 locale, `--lang es` 时模板是西语、错误详情却是英文 — 现在
  `voice_config` 有进程级语言覆盖, 回归测试
  `test_a_forced_language_reaches_the_cleanup_messages` 覆盖。
- **未验收**: 真实设备一句完整语音经 LLM 整理后上屏; 面板内下拉/按钮的鼠标点击、
  搜索框过滤与键盘路径 (桌面持续被占用, 合成指针坐标无法核对 — `hyprctl cursorpos`
  与合成移动互相干扰; 可搜索下拉本身是 shell 自带 `qs.Ui.SearchableDropdown`);
  各 provider 真 key 的返回质量。
