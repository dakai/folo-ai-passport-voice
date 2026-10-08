#!/usr/bin/env python3
"""Linux equivalent of the Windows forwarder (电脑端转发器).

Device → Wi-Fi UDP 33333 → ADPCM decode → buffer PCM → `voxtype
transcribe` (local offline SenseVoice) → wtype text injection.

No cloud ASR. No virtual sound card: recognition happens in-process via
the voxtype CLI, and only final text is typed into the focused window.
"""

import argparse
import asyncio
import json
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import adpcm as adpcm_mod
import asr_voxtype
import inject
from udp_transport import (
    UdpTransport, UdpError, EVENT_UUID, AUDIO_UUID)

SAMPLE_RATE = 16000
SILENCE_TIMEOUT = 2.5
ENTER_DEBOUNCE_SECONDS = 0.35
MIN_UTTERANCE_BLOCKS = 3


class Forwarder:
    def __init__(self, args, transcriber=None, typer=None,
                 key_action=None):
        self.args = args
        self.transcriber = (transcriber
                            or (lambda samples: asr_voxtype.transcribe_pcm(
                                samples, voxtype_bin=args.voxtype_bin,
                                engine=args.engine)))
        self.typer = typer or inject.type_text
        self.key_action = key_action or inject.key_action
        self.pcm_blocks = []
        self.active = False
        self.last_audio_at = 0.0
        self.last_seq = None
        self.last_enter_at = float("-inf")
        self.audio_blocks = 0
        self._transcribing = False
        self._utterance_seq = 0

    def hotkey_ready(self):
        return inject.inject_available()

    def pc_status(self):
        return {"type": "pc.status", "audioReady": True,
                "hotkeyReady": self.hotkey_ready()}

    def finish(self, cancel=False):
        self.active = False
        if cancel:
            self.pcm_blocks = []

    def _transcribe_and_type_async(self, samples, seq):
        """Run voxtype off the event loop; type text on completion."""
        self._transcribing = True

        def work():
            try:
                text = self.transcriber(samples)
            except asr_voxtype.AsrError as e:
                print(f"[asr] 识别失败: {e}", file=sys.stderr)
                return
            except Exception as e:  # ponytail: never kill the loop on ASR bugs
                print(f"[asr] 识别异常: {e}", file=sys.stderr)
                return
            finally:
                self._transcribing = False
            if seq != self._utterance_seq:
                return
            if text:
                print(f"[asr] 识别结果: {text}")
                try:
                    self.typer(text)
                except inject.InjectError as e:
                    print(f"[key] {e}", file=sys.stderr)
            else:
                print("[asr] 无语音内容,跳过输入")

        threading.Thread(target=work, name="asr_worker", daemon=True).start()

    def check_health(self, now=None):
        now = time.monotonic() if now is None else now
        if self.active and now - self.last_audio_at > SILENCE_TIMEOUT:
            print("[link] 语音通道中断,丢弃缓冲")
            self.finish(cancel=True)

    def on_event(self, payload):
        try:
            ev = json.loads(payload.decode("utf-8").strip())
        except (UnicodeDecodeError, json.JSONDecodeError):
            return
        if not isinstance(ev, dict):
            return
        name = ev.get("event", "")
        if name == "voice.start":
            if self.active:
                return
            print("[evt] 设备开始说话(voice.start)")
            self.pcm_blocks = []
            self.audio_blocks = 0
            self.last_seq = None
            self.last_audio_at = time.monotonic()
            self.active = True
        elif name == "voice.end":
            print(f"[evt] 设备结束说话(voice.end),收到音频块={self.audio_blocks}")
            self.active = False
            self._utterance_seq += 1
            blocks, self.pcm_blocks = self.pcm_blocks, []
            if len(blocks) >= MIN_UTTERANCE_BLOCKS:
                samples = [s for blk in blocks for s in blk]
                self._transcribe_and_type_async(samples, self._utterance_seq)
            elif blocks or self.audio_blocks:
                print("[asr] 音频过短,跳过识别(防空按误触)")
        elif name == "device.hello":
            print("[evt] 设备上线(device.hello)")
        elif name == "key.action" and ev.get("action") == "enter":
            now = time.monotonic()
            if now - self.last_enter_at < ENTER_DEBOUNCE_SECONDS:
                print("[evt] 忽略重复的下键回车")
                return
            self.last_enter_at = now
            stale_voice = self.active or self._transcribing
            if stale_voice:
                print("[evt] 下键对账: 先结束残留语音状态")
            self._utterance_seq += 1  # drop late ASR landing after Enter
            self.finish(cancel=True)
            while self._transcribing:
                time.sleep(0.01)
            if stale_voice:
                time.sleep(0.05)
            try:
                self.key_action("enter")
                print("[key] 回车已发送")
            except (inject.InjectError, ValueError) as e:
                print(f"[key] {e}", file=sys.stderr)

    def on_audio(self, payload):
        if self.active and len(payload) == 806 and payload[1] == 0x80:
            seq = payload[0]
            if self.last_seq is not None and not 0 < ((seq - self.last_seq) & 255) < 128:
                return
            self.last_seq = seq
            self.last_audio_at = time.monotonic()
            try:
                self.pcm_blocks.append(adpcm_mod.decode_block(payload[2:]))
            except Exception as e:
                print(f"[audio] 解码失败: {e}", file=sys.stderr)
                return
            self.audio_blocks += 1
            if self.audio_blocks == 1:
                print("[audio] 已收到设备首个音频块")

    def on_disconnect(self):
        print("[link] 设备断开,丢弃缓冲;等待 beacon 自动重连...")
        self._utterance_seq += 1
        self.finish(cancel=True)

    async def run(self):
        while True:
            transport = UdpTransport(port=self.args.port,
                                     device_wait_timeout=10 ** 9,
                                     device_ip=self.args.device_ip,
                                     auto_recover=False)
            status_task = None
            link_down = asyncio.Event()

            def on_disconnect():
                self.on_disconnect()
                link_down.set()

            try:
                await transport.scan_for_device(None, None)
                await transport.connect("udp://",
                                        on_disconnect=on_disconnect)
                await transport.start_notify(EVENT_UUID, self.on_event)
                await transport.start_notify(AUDIO_UUID, self.on_audio)
                print("[link] 就绪: 等待设备按键/音频(设备上打开「AI语音」, "
                      "按住 UP 说话)")

                async def status():
                    last_status = 0.0
                    announced_status = None
                    while True:
                        self.check_health()
                        now = time.monotonic()
                        if now - last_status >= 1.0:
                            last_status = now
                            try:
                                current_status = self.pc_status()
                                await transport.write_gatt_char(EVENT_UUID,
                                    (json.dumps(current_status) + "\n").encode())
                                if current_status != announced_status:
                                    announced_status = current_status
                                    print("[link] PC 就绪状态已发送: "
                                          f"audio={current_status['audioReady']} "
                                          f"hotkey={current_status['hotkeyReady']}")
                            except Exception as e:
                                print(f"[link] PC 状态回报失败: {e}",
                                      file=sys.stderr)
                                self.finish(cancel=True)
                                link_down.set()
                                return
                        await asyncio.sleep(0.2)

                status_task = asyncio.create_task(status())
                await link_down.wait()
                link_down.clear()
            except UdpError as e:
                print(f"[link] {e};10s 后重试", file=sys.stderr)
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                return
            finally:
                if status_task:
                    status_task.cancel()
                    try:
                        await status_task
                    except asyncio.CancelledError:
                        pass
                self.finish(cancel=True)
                try:
                    await transport.disconnect()
                except Exception:
                    pass
            await asyncio.sleep(0.5)


def load_local_config():
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, "voice-config.json")
    try:
        with open(path, encoding="utf-8-sig") as f:
            cfg = json.load(f)
        return cfg if isinstance(cfg, dict) else {}
    except Exception:
        return {}


def main(argv=None):
    cfg = load_local_config()
    ap = argparse.ArgumentParser(
        description="AI Passport Linux 语音转发器(voxtype 本地离线识别, "
                    "配置见 voice-config.json, 命令行参数优先)")
    ap.add_argument("--port", type=int,
                    default=int(cfg["udp_port"]) if str(cfg.get("udp_port") or "").strip().isdigit() else 33333)
    ap.add_argument("--device-ip",
                    default=str(cfg.get("device_ip") or ""),
                    help="设备目标IP(路由器AP隔离阻断广播时填,留空则自动探测)")
    ap.add_argument("--voxtype-bin",
                    default=str(cfg.get("voxtype_bin") or "voxtype"),
                    help="voxtype 可执行文件路径")
    ap.add_argument("--engine",
                    default=str(cfg.get("engine") or "sensevoice"),
                    help="识别引擎(默认 sensevoice, CPU 约快 2.6 倍)")
    ap.add_argument("--no-asr", action="store_true",
                    help="只收音频不识别(调试用)")
    ap.add_argument("--diagnose", action="store_true",
                    help="检查 voxtype、wtype 与端口,不收设备音频")
    args = ap.parse_args(argv)

    if args.diagnose:
        from diagnose_voice import main as diagnose
        raise SystemExit(diagnose(args))

    if args.no_asr:
        args.transcriber = None
    fwd = Forwarder(args)
    if args.no_asr:
        fwd.transcriber = lambda samples: print(
            f"[asr] 调试模式: 跳过识别({len(samples)} 采样)") or ""
    print("=" * 66)
    print("           AI Passport · Linux 语音服务已启动(本地离线识别)")
    print("=" * 66)
    print(" [使用说明]")
    print("   1. 硬件: 开机并进入「随身 AI 语音」(或「AI语音」)")
    print("   2. 焦点: 鼠标点进 Linux 输入框,识别文本自动键入")
    print("   3. 说话: 按住设备 UP 键说话,松手识别并上屏")
    print("   4. 单击 DOWN 发送回车")
    print(" [提示] 保持此窗口开启即可使用；按 Ctrl+C 或关闭此窗口退出")
    print("=" * 66)
    print(f"引擎: {args.engine}  wtype: "
          f"{'就绪' if inject.inject_available() else '未找到(先装 wtype)'}")
    try:
        asyncio.run(fwd.run())
    except KeyboardInterrupt:
        print("\n退出")


if __name__ == "__main__":
    main()
