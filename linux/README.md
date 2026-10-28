# linux/ 目录说明

设备麦克风 → Wi-Fi UDP → `voice_forwarder.py` → voxtype SenseVoice →
(可选)LLM 整理 → `wtype` 把文字键入当前焦点窗口。无云端 ASR、无虚拟声卡,
纯标准库, 除系统工具外零依赖。

**安装、日常使用、配置、排错、测试命令都在根 [README](../README.md) 的
「Linux / Omarchy」一节** —— 用户只需要看那一处。本文件只记这个目录本身
(文件职责、约定、约束), 给读代码的人看。

## 文件

| 文件 | 职责 |
|---|---|
| `voice_forwarder.py` | 入口: UDP 收发、utterance 生命周期、调用识别与键入 |
| `udp_transport.py` | UDP 报文格式、设备发现(广播 beacon + 单播探测) |
| `adpcm.py` | IMA ADPCM 解码, 与设备端 `device/main/apps/voice/adpcm.c` 逐字节一致 |
| `asr_voxtype.py` | `voxtype transcribe` 包装: 写 WAV、解析首个空行之后的文本 |
| `inject.py` | `wtype` 键入文字、回车、清行; `--dry-run` 不启动子进程 |
| `llm_cleanup.py` | OpenAI 兼容整理: provider 目录、`PROMPT`、失败回退、4 语言消息 |
| `voice_config.py` | `voice-config.json`、`status.json`、API key、`resolve_lang` 的唯一读写与判定处 |
| `voice_tui.py` | 终端配置器; 同时是栏插件调用的 `status` / `set` / `models` / `test` 后端 |
| `install.sh` | 装 systemd user 单元(幂等, 可重复运行) |
| `ai-passport-voice.service` | 单元模板; 绑定 `graphical-session.target`, 因为 `wtype` 要 Wayland socket |
| `tests/` | 标准库 `unittest`, 伪造转写器 / voxtype 二进制 / 密钥环, LLM 只打 loopback 桩 |

## 约定与约束

- **报文契约跨语言复制。** `udp_transport.py` 实现的方法契约来自
  `device/main/apps/voice/udp_audio.c`; ADPCM 表 `K_STEP` / `K_INDEX_DELTA`
  必须与 `adpcm.c` 完全一致, 端序、半字节顺序也一样。见
  [底层接口适配](../docs/PORTING.zh-CN.md)。
- **失败回退原文。** LLM 整理的任何异常都键入识别原文 —— 丢用户说的话是唯一
  不可接受的失败。转写内容按数据处理, 不回答、不执行。
- **`voice_tui.py` 是配置的唯一写入者。** 终端菜单和栏插件调同一个程序, 所以两边
  永远一致; 其它模块只读 `voice_config.load()`。
- **改 `linux/` 后必跑测试。** 测试不允许碰真实密钥环、真实 voxtype、真实声卡,
  也不上网; 三个测试模块各自把外部依赖换成桩。

## 测试

```bash
python3 -m unittest discover -s linux/tests -p "test_*.py" -v
```

58 个测试, 只依赖标准库。CI 在 Linux 上跑同一命令。
