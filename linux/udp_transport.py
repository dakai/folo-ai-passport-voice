#!/usr/bin/env python3
"""Wi-Fi UDP transport: same wire contract as the Windows forwarder.

Binds UDP 33333, beacons for the device, learns the device address from
recvfrom, and routes EVENT/AUDIO to handlers. Linux uses `ip addr` for
broadcast enumeration (--device-ip covers AP-isolated routers).
"""

import asyncio
import ipaddress
import json
import re
import socket
import subprocess
import sys
import threading
import time

UDP_PORT = 33333

T_AUDIO = 0x01
T_EVENT = 0x02
T_BEACON = 0x03
T_PING = 0x04

SERVICE_UUID = "0000A2B0-0000-1000-8000-00805F9B34FB"
CTRL_UUID = "0000A2B1-0000-1000-8000-00805F9B34FB"
EVENT_UUID = "0000A2B2-0000-1000-8000-00805F9B34FB"
AUDIO_UUID = "0000A2B3-0000-1000-8000-00805F9B34FB"

PENDING_MAX = 64
BEACON_INTERVAL = 1.0
DEVICE_WAIT_TIMEOUT = 60.0
LINK_TIMEOUT = 12.0
BEACON_REFRESH = 30.0
RECV_TIMEOUT = 0.5
RECV_MAX = 4096
SWEEP_INTERVAL = 3.0
SWEEP_MAX_HOSTS = 512


class UdpError(Exception):
    """Wi-Fi UDP channel error (port busy, no device, send failure)."""


def _is_lan_ip(ip):
    """True for a local IPv4 candidate. Computed via ipaddress, no literals."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return addr.version == 4 and addr.is_private and not addr.is_loopback


def _private_broadcast(ip, prefix=24):
    """Directed broadcast for (ip, prefix). None when not a LAN address."""
    if not _is_lan_ip(ip):
        return None
    try:
        net = ipaddress.ip_network(f"{ip}/{prefix}", strict=False)
    except ValueError:
        return None
    return str(net.broadcast_address)


def _local_broadcast_addrs(port):
    """Directed broadcast per local subnet + limited broadcast."""
    addrs = {"255.255.255.255"}
    ips = {}
    try:
        _, _, dns_ips = socket.gethostbyname_ex(socket.gethostname())
        for i in dns_ips:
            ips.setdefault(i, 24)
    except Exception:
        pass
    try:
        out = subprocess.run(
            ["ip", "-4", "-o", "addr", "show"], capture_output=True,
            timeout=5, text=True, errors="replace").stdout or ""
        for m in re.finditer(r"\binet (\d{1,3}(?:\.\d{1,3}){3})/(\d+)", out):
            ips[m.group(1)] = int(m.group(2))
    except Exception:
        pass
    for ip, prefix in ips.items():
        bcast = _private_broadcast(ip, prefix)
        if bcast:
            addrs.add(bcast)
    return [(a, port) for a in sorted(addrs)]
def _local_ipv4_subnets():
    """Own LAN subnets as (ip, prefixlen), physical NICs only.

    Skips virtual interfaces (docker/br-/veth/tailscale): their subnets
    hold no devices but add hundreds of sweep targets per round.
    Membership is computed via ipaddress, no hardcoded ranges.
    """
    skip_prefixes = ("docker", "br-", "veth", "tailscale", "tun", "wg")
    subnets = []
    try:
        out = subprocess.run(
            ["ip", "-4", "-o", "addr", "show"], capture_output=True,
            timeout=5, text=True, errors="replace").stdout or ""
        for line in out.splitlines():
            if line.split()[1:2] and line.split()[1].startswith(skip_prefixes):
                continue
            m = re.search(r"\binet (\d{1,3}(?:\.\d{1,3}){3})/(\d+)", line)
            if m and _is_lan_ip(m.group(1)):
                subnets.append((m.group(1), int(m.group(2))))
    except Exception:
        pass
    return subnets


def _sweep_targets(port):
    """Unicast beacon targets, one per host on each local private subnet.

    Broadcast never survives AP isolation, unicast does. Enumerate hosts
    so discovery works without --device-ip. Subnets larger than
    SWEEP_MAX_HOSTS fall back to the local /24 to bound probe traffic.
    """
    targets = []
    for own_ip, prefix in _local_ipv4_subnets():
        try:
            net = ipaddress.ip_network(f"{own_ip}/{prefix}", strict=False)
            if net.num_addresses > SWEEP_MAX_HOSTS:
                net = ipaddress.ip_network(f"{own_ip}/24", strict=False)
            for host in net.hosts():
                if str(host) != own_ip:
                    targets.append((str(host), port))
        except ValueError:
            continue
    return targets


class UdpTransport:
    """Wi-Fi UDP transport (single device)."""

    def __init__(self, port=None, bind_host="0.0.0.0",
                 beacon_interval=BEACON_INTERVAL,
                 device_wait_timeout=DEVICE_WAIT_TIMEOUT,
                 link_timeout=LINK_TIMEOUT,
                 auto_recover=True,
                 device_ip=None):
        self._port = int(port) if port else UDP_PORT
        self._bind_host = bind_host
        self._beacon_interval = beacon_interval
        self._device_wait_timeout = device_wait_timeout
        self._link_timeout = link_timeout
        self._device_ip = str(device_ip).strip() if device_ip else None
        self._auto_recover = bool(auto_recover)
        self._lost_logged = False
        self._sock = None
        self._reader = None
        self._beacon_task = None
        self._loop = None
        self._stop = False
        self._on_disconnect = None
        self._evt_handler = None
        self._aud_handler = None
        self._pending = []
        self._device = None
        self._device_last = 0.0

    async def scan_for_device(self, name, timeout):
        """UDP server: return a placeholder, connect() waits for the device."""
        print(f"[udp] 服务端模式: 监听 {self._bind_host}:{self._port}, "
              f"每 {self._beacon_interval:.0f}s 广播 beacon")
        return f"udp://{self._bind_host}:{self._port}"

    async def connect(self, address, on_disconnect=None):
        """Open socket, start reader + beacons, wait for first device packet."""
        self._on_disconnect = on_disconnect
        self._loop = asyncio.get_running_loop()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.bind((self._bind_host, self._port))
        except OSError as e:
            raise UdpError(
                f"绑定 UDP {self._bind_host}:{self._port} 失败: {e}\n"
                "(确认端口未被占用、防火墙已放行入站 UDP)") from e
        self._sock = sock
        self._stop = False
        self._device = None
        self._reader = threading.Thread(target=self._read_loop,
                                        name="udp_reader", daemon=True)
        self._reader.start()
        self._beacon_task = asyncio.create_task(self._beacon_loop())
        print(f"[udp] 已监听 {self._bind_host}:{self._port}, "
              "等待设备(请在设备上进入「AI语音」)...")
        deadline = time.monotonic() + self._device_wait_timeout
        while (self._device is None and not self._stop
               and time.monotonic() < deadline):
            await asyncio.sleep(0.05)
        if self._device is None:
            await self.disconnect()
            raise UdpError(
                f"{self._device_wait_timeout:.0f}s 内没有收到设备报文:"
                "设备未开机/未进入「AI语音」/不在同一局域网"
                "(路由器 AP 隔离会挡住 beacon)")
        print(f"[udp] 发现设备 {self._device[0]}:{self._device[1]}")

    async def write_gatt_char(self, uuid, data):
        """Downlink EVENT frame (uuid ignored, no characteristics on UDP)."""
        if self._sock is None or self._device is None:
            raise UdpError("设备未连接,下行丢弃")
        if not self._sendto_device(T_EVENT, bytes(data)):
            raise UdpError("下行发送失败")

    async def start_notify(self, uuid, handler):
        """Register EVENT/AUDIO handler; flush pre-subscribe buffer when both set."""
        if uuid == EVENT_UUID:
            self._evt_handler = handler
        elif uuid == AUDIO_UUID:
            self._aud_handler = handler
        else:
            raise UdpError(f"未知特征: {uuid}(UDP 通道仅 EVENT/AUDIO 两类)")
        if self._evt_handler is not None and self._aud_handler is not None:
            pending, self._pending = self._pending, []
            for ftype, payload in pending:
                self._dispatch_frame(ftype, payload)

    async def disconnect(self):
        """Stop beacons, close socket, join reader. Idempotent."""
        self._stop = True
        if self._beacon_task is not None:
            self._beacon_task.cancel()
            try:
                await self._beacon_task
            except (asyncio.CancelledError, Exception):
                pass
            self._beacon_task = None
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
        if self._reader is not None:
            deadline = time.monotonic() + 2.0
            while self._reader.is_alive() and time.monotonic() < deadline:
                await asyncio.sleep(0.02)
            self._reader = None
        self._device = None

    def _sendto_device(self, ftype, payload):
        if self._sock is None or self._device is None:
            return False
        try:
            self._sock.sendto(bytes((ftype,)) + bytes(payload), self._device)
            return True
        except OSError as e:
            print(f"[udp] 发送失败: {e}", file=sys.stderr)
            return False

    async def _beacon_loop(self):
        targets = _local_broadcast_addrs(self._port)
        if self._device_ip and (self._device_ip, self._port) not in targets:
            targets.insert(0, (self._device_ip, self._port))
        sweep = [] if self._device_ip else _sweep_targets(self._port)
        if sweep:
            print(f"[udp] AP 隔离兼容: 逐个单播探测 {len(sweep)} 个局域网地址")
        print(f"[udp] beacon 目标: {[t[0] for t in targets]}")
        last_refresh = time.monotonic()
        last_sweep = 0.0
        pkt = bytes((T_BEACON,)) + json.dumps(
            {"v": 1, "role": "pc", "port": self._port}).encode("utf-8")
        while not self._stop:
            now = time.monotonic()
            if now - last_refresh >= BEACON_REFRESH:
                fresh = _local_broadcast_addrs(self._port)
                if self._device_ip and (self._device_ip, self._port) not in fresh:
                    fresh.insert(0, (self._device_ip, self._port))
                last_refresh = now
                if fresh != targets:
                    print(f"[udp] 网络变化,beacon 目标更新: "
                          f"{[t[0] for t in fresh]}", file=sys.stderr)
                    targets = fresh
            all_targets = list(targets)
            if self._device and self._device not in all_targets:
                all_targets.append(self._device)
            for t_ip, t_port in all_targets:
                try:
                    self._sock.sendto(pkt, (t_ip, t_port))
                except OSError as e:
                    print(f"[udp] beacon 发送失败({t_ip}): {e}", file=sys.stderr)
            # Device found or pinned: no sweep needed.
            if sweep and self._device is None and now - last_sweep >= SWEEP_INTERVAL:
                last_sweep = now
                for t_ip, t_port in sweep:
                    if self._device is not None or self._stop:
                        break
                    try:
                        self._sock.sendto(pkt, (t_ip, t_port))
                    except OSError:
                        pass
            try:
                gap = 1.0 if self._device is None else self._beacon_interval
                await asyncio.sleep(gap)
            except asyncio.CancelledError:
                return

    def _read_loop(self):
        sock = self._sock
        sock.settimeout(RECV_TIMEOUT)
        try:
            while not self._stop:
                try:
                    data, addr = sock.recvfrom(RECV_MAX)
                except socket.timeout:
                    if self._check_link():
                        break
                    continue
                except OSError:
                    if not self._stop:
                        print("[udp] socket 读取异常", file=sys.stderr)
                    break
                if self._stop or not data:
                    continue
                self._on_datagram(sock, data, addr)
        finally:
            if not self._stop and self._loop is not None:
                try:
                    self._loop.call_soon_threadsafe(self._notify_disconnect)
                except RuntimeError:
                    pass

    def _check_link(self):
        if self._device is None:
            return False
        if time.monotonic() - self._device_last <= self._link_timeout:
            if self._lost_logged:
                self._lost_logged = False
                print("[udp] 设备已恢复", file=sys.stderr)
            return False
        if not self._auto_recover:
            print(f"[udp] 设备静默超过 {self._link_timeout:.0f}s,判定断开",
                  file=sys.stderr)
            return True
        if not self._lost_logged:
            self._lost_logged = True
            print(f"[udp] 设备静默超过 {self._link_timeout:.0f}s,"
                  "保持监听等待其重连(beacon 继续发送)", file=sys.stderr)
        return False

    def _on_datagram(self, sock, data, addr):
        ftype = data[0]
        if ftype == T_BEACON:
            return
        if ftype == T_PING:
            self._note_device(addr)
            return
        if ftype not in (T_AUDIO, T_EVENT):
            print(f"[udp] 未知报文类型 0x{ftype:02x} 来自 {addr[0]}, 忽略",
                  file=sys.stderr)
            return
        self._note_device(addr)
        payload = bytes(data[1:])
        self._loop.call_soon_threadsafe(self._route_frame, ftype, payload)

    def _note_device(self, addr):
        self._device_last = time.monotonic()
        if self._device != addr:
            if self._device is not None:
                print(f"[udp] 设备地址变化 {self._device} → {addr}",
                      file=sys.stderr)
            self._device = addr

    def _route_frame(self, ftype, payload):
        if self._evt_handler is not None and self._aud_handler is not None:
            self._dispatch_frame(ftype, payload)
        elif len(self._pending) < PENDING_MAX:
            self._pending.append((ftype, payload))
        else:
            print("[udp] 订阅前消息过多, 丢弃", file=sys.stderr)

    def _dispatch_frame(self, ftype, payload):
        handler = (self._aud_handler if ftype == T_AUDIO
                   else self._evt_handler)
        if handler is None:
            return
        try:
            res = handler(payload)
            if asyncio.iscoroutine(res):
                asyncio.create_task(res).add_done_callback(
                    lambda t: (t.exception() is not None and
                               print(f"[udp] 回调协程异常: {t.exception()}",
                                     file=sys.stderr)))
        except Exception as e:
            print(f"[udp] 派发回调执行异常 (type={ftype}): {e}", file=sys.stderr)

    def _notify_disconnect(self):
        if self._on_disconnect is None:
            return
        try:
            res = self._on_disconnect()
            if asyncio.iscoroutine(res):
                asyncio.create_task(res).add_done_callback(
                    lambda t: (t.exception() is not None and
                               print(f"[udp] 断连回调协程异常: {t.exception()}",
                                     file=sys.stderr)))
        except Exception as e:
            print(f"[udp] 断连回调执行异常: {e}", file=sys.stderr)
