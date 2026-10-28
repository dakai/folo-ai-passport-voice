#!/usr/bin/env bash
# Install this plugin into the live Omarchy shell and enable it in the bar.
#
# Run from the repo checkout: bash omarchy/install.sh
# Idempotent: re-running replaces the installed copy and re-enables it.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
id="manchunx7.ai-passport-voice"
dest="${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/plugins/$id"

fail() { echo "install: $*" >&2; exit 1; }

command -v omarchy >/dev/null || fail "找不到 omarchy: 这是 Omarchy 专用插件"
[[ -f "$here/../linux/voice_tui.py" ]] \
  || fail "install.sh 必须从仓库的 omarchy/ 目录运行 (找不到 ../linux/voice_tui.py)"

mkdir -p "$dest"
# --delete matters: a renamed file left behind would still be loaded.
rsync -a --delete --exclude '__pycache__' --exclude '*.pyc' "$here/" "$dest/"
chmod +x "$dest/bin/aipv" "$dest/install.sh"

omarchy plugin validate "$dest"
omarchy-shell shell rescanPlugins >/dev/null 2>&1 || true
omarchy plugin enable "$id" --section right
echo "已启用 $id; 栏上没有出现就执行: omarchy restart shell"
