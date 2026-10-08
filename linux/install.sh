#!/usr/bin/env bash
# Install the Linux voice forwarder as a systemd user service.
# Idempotent: safe to re-run after moving the repo or editing the unit.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
UNIT_SRC="$REPO/linux/ai-passport-voice.service"
UNIT_NAME="ai-passport-voice.service"
UNIT_DST="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/$UNIT_NAME"
CONFIG="$REPO/linux/voice-config.json"

fail() { echo "install: $*" >&2; exit 1; }

# Conflicting forwarder already holding UDP 33333 (manual terminal run)?
if ss -ulpn 2>/dev/null | grep -q ':33333 '; then
    fail "UDP 33333 已被占用: 先停掉终端里手动运行的转发器, 再重装服务"
fi

command -v voxtype >/dev/null || fail "找不到 voxtype: 先 omarchy voxtype install 并按 README 配好 sensevoice"
command -v wtype >/dev/null || fail "找不到 wtype: 先 omarchy pkg add wtype wl-clipboard"
[[ "${XDG_SESSION_TYPE:-}" == "wayland" || -n "${WAYLAND_DISPLAY:-}" ]] \
    || fail "不在 Wayland 会话里: wtype 需要 wlroots 合成器(Hyprland/Sway)"

# First run: copy the example config so the service starts without flags.
if [[ ! -f "$CONFIG" ]]; then
    cp "$REPO/linux/voice-config.example.json" "$CONFIG"
    echo "已创建 $CONFIG (默认自动探测设备; AP 隔离严重时再填 device_ip)"
fi

mkdir -p "$(dirname "$UNIT_DST")"
# %h in the unit resolves to $HOME at start time, so the checked-in file
# only works from ~/Apps/<repo>. A moved checkout gets a rewritten copy.
if [[ "$REPO" == "$HOME/Apps/folo-ai-passport-voice" ]]; then
    cp "$UNIT_SRC" "$UNIT_DST"
else
    sed "s|%h/Apps/folo-ai-passport-voice|$REPO|" "$UNIT_SRC" > "$UNIT_DST"
    echo "仓库不在默认位置, 已写入绝对路径: $REPO"
fi

systemctl --user daemon-reload
systemctl --user enable --now "$UNIT_NAME"
echo "服务已启动: journalctl --user -u $UNIT_NAME -f  查看日志"
