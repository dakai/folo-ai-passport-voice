"""Read-only Linux bridge diagnostics. No injection, no recognition."""
import shutil
import socket
import subprocess
import sys


def main(args=None):
    print("AI Passport Voice diagnostics (Linux / UDP 33333 / voxtype)")
    print("Python:", sys.version.split()[0])
    problems = 0
    if sys.platform != "linux":
        print("[FAIL] This bridge supports Linux only.")
        problems += 1
    if shutil.which(getattr(args, "voxtype_bin", None) or "voxtype"):
        try:
            out = subprocess.run(
                [getattr(args, "voxtype_bin", None) or "voxtype",
                 "config", "get", "engine"],
                capture_output=True, text=True, timeout=10).stdout.strip()
            print(f"[OK] voxtype 可用,引擎={out or '?'}"
                  "(sensevoice 为 CPU 默认)")
            if out and out != "sensevoice":
                print("[INFO] CPU 上 sensevoice 约快 2.6 倍:"
                      " voxtype config set engine sensevoice")
        except Exception as e:
            print(f"[FAIL] voxtype 调用失败: {e}")
            problems += 1
    else:
        print("[FAIL] 找不到 voxtype: omarchy voxtype install")
        problems += 1
    if shutil.which("wtype"):
        print("[OK] wtype 可用(需 wlroots 合成器如 Hyprland/Sway)")
    else:
        print("[FAIL] 找不到 wtype: omarchy pkg add wtype wl-clipboard")
        problems += 1
    port = getattr(args, "port", None) or 33333
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", port))
        print(f"[OK] UDP {port} 可用。同时只启动一个转发器。")
    except OSError as e:
        print(f"[BUSY] UDP {port}: {e}")
        print("转发器已在运行属正常;否则关闭旧实例: "
              f"ss -ulp | grep {port}")
        problems += 1
    print("本检查不证明设备音频送达或识别准确。")
    print("用合成音频做端到端验证: 先按住说话再松手,看文本是否上屏。")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
