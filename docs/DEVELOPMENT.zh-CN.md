# 随身语音开发与测试

本仓库只包含本功能的代码。普通用户按 [使用教程](QUICKSTART.zh-CN.md) 使用 EXE；设备固件到官网获取。本仓库不含整机入口、BSP、共享 UI 或其他应用，不提供整机 `idf.py build`。

## Windows 源码运行

在仓库根目录打开 PowerShell，准备 Python 3.11 x64：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r windows\requirements-hotkey.txt
.\.venv\Scripts\python.exe windows\hotkey_forwarder.py --diagnose
.\.venv\Scripts\python.exe windows\hotkey_forwarder.py
```

先安装 VB-CABLE、按教程设置输入法和可信局域网。将 `windows/voice-config.example.json` 复制为 `windows/voice-config.json` 并核对路径与快捷键。不要同时运行源码版与 EXE 争用 UDP 33333。

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s windows\tests -p "test_*.py" -v
```

发布的 EXE 沿用已验证的 Python 3.11.8 / sounddevice 0.5.6 / PyInstaller 6.20.0 构建。它与这里的 Windows 源码保持一致，未加入其他整机源码。驱动和输入法不打包。

## Linux 源码运行与测试

Linux 端只用标准库, 不需要 venv; 系统工具按 [根 README 的 Linux 一节](../README.md) 装好。

```bash
python3 linux/voice_forwarder.py --diagnose     # 检查 voxtype、wtype、UDP 33333
python3 linux/voice_forwarder.py                # 前台运行(先停服务, 端口只有一个)

python3 -m unittest discover -s linux/tests -p "test_*.py" -v
```

54 项: 识别分发/回车对账、voxtype 解析、wtype 注入、配置规范化、LLM 端点策略与
失败回退、状态文件、配置器子命令。LLM 相关测试只连本机 loopback 桩服务, 不出网。

配置与状态文件由 `linux/voice_config.py` 独占读写, 终端配置器 `linux/voice_tui.py`
是唯一的写入入口(栏插件也调它)。API key 走 `secret-tool` 进登录密钥环, 没有
libsecret 时回退到 0600 的配置文件; 测试用假的 `secret-tool` 脚本验证两种路径。

## 设备纯逻辑测试

在 Linux、WSL 或具备 Bash、C 编译器的环境中，从仓库根目录运行：

```bash
bash tools/test-host.sh
```

测试直接编译 `device/main/apps/voice/app_state.c`、`ui_pixel_math.c`，不需要 ESP-IDF、私有仓库或设备。它覆盖长按/松开、电脑就绪、下键、重复事件、超时与故障分支，不替代实机音频测试。

## 设备代码移植

设备端源码来源于已验证固件的 Voice 应用目录，算法和状态机未为这次拆分改写。应用模块依赖 ESP-IDF 5.5.3、FreeRTOS、LVGL 9.5，以及由宿主实现的硬件和 UI 接口。详细边界见 [PORTING](PORTING.zh-CN.md)。

如想在自己的固件集成，先接入纯状态机与协议，再提供录音、UDP、按键和显示生命周期。不要把缺少的整机文件从私有仓库复制进公开 PR；新增适配实现需独立审查发布范围。
