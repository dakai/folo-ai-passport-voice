#!/usr/bin/env python3
"""Wayland text injection via wtype. dry_run spawns no subprocess."""

import shutil
import subprocess

GUIDE = ("Wayland 文本注入需要 wtype: omarchy pkg add wtype wl-clipboard\n"
         "wtype 需要 wlroots 合成器(Hyprland/Sway); GNOME/KDE 请用剪贴板粘贴。")


class InjectError(Exception):
    """wtype missing or injection failed."""


def _run(cmd, dry_run=False):
    if dry_run:
        return cmd
    if shutil.which(cmd[0]) is None:
        raise InjectError(f"找不到 {cmd[0]}。{GUIDE}")
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=10)
    except subprocess.CalledProcessError as e:
        raise InjectError(f"注入失败: {e}") from e
    return cmd


def type_text(text, dry_run=False):
    """Type text at the focused input. Empty text is a no-op."""
    if not text:
        return []
    # `--` keeps leading dashes/unicode out of option parsing.
    return _run(["wtype", "--", text], dry_run=dry_run)


def key_action(action, dry_run=False):
    """action is enter|clear, the only two callers send."""
    if action == "enter":
        return _run(["wtype", "-k", "Return"], dry_run=dry_run)
    if action == "clear":
        return _run(["wtype", "-M", "ctrl", "-k", "a",
                     "-m", "ctrl", "-k", "BackSpace"], dry_run=dry_run)
    raise ValueError(f"未知按键动作 '{action}'(仅支持 enter|clear)")


def inject_available():
    """True when wtype resolves on PATH (pc.status hotkeyReady)."""
    return shutil.which("wtype") is not None
