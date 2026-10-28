#!/usr/bin/env bash
# Install the AI Passport voice bar widget into Omarchy.
#
#   bash omarchy/install.sh                            # from a checkout
#   curl -fsSL https://raw.githubusercontent.com/dakai/folo-ai-passport-voice/main/omarchy/install.sh | bash
#
# Idempotent: re-running updates the installed copy in place and leaves the bar
# placement alone. `omarchy plugin add <repo>` cannot do this job: it validates
# the repository root as the plugin, while this repository's root is the whole
# project and the plugin lives in omarchy/ — the standalone path clones and
# copies that one directory instead.
set -euo pipefail

PLUGIN_ID="manchunx7.ai-passport-voice"
REPO_URL="${AIPV_REPO_URL:-https://github.com/dakai/folo-ai-passport-voice}"
REF="${AIPV_REF:-main}"
DEST_ROOT="${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/plugins"
DEST="$DEST_ROOT/$PLUGIN_ID"

fail() { echo "install: $*" >&2; exit 1; }

# BASH_SOURCE is /dev/fd/63 under `curl | bash`, so "is this a checkout" is a
# question about the file, not about being sourced at all.
self="${BASH_SOURCE[0]:-}"
here=""
[[ -n $self && -f $self ]] && here="$(cd "$(dirname "$self")" && pwd)"

work=""
trap '[[ -n $work ]] && rm -rf "$work"' EXIT

if [[ -n $here && -f "$here/manifest.json" ]]; then
  src="$here"
  checkout="$(cd "$here/.." && pwd)"
else
  command -v git >/dev/null || fail "git is required: omarchy pkg add git"
  work="$(mktemp -d)"
  git clone --depth 1 --branch "$REF" --quiet "$REPO_URL" "$work/repo" \
    || fail "clone failed: $REPO_URL ($REF)"
  src="$work/repo/omarchy"
  checkout=""
  [[ -f "$src/manifest.json" ]] || fail "no omarchy/manifest.json in $REPO_URL"
fi

mkdir -p "$DEST_ROOT"
rm -rf "$DEST"
cp -r "$src" "$DEST"
chmod +x "$DEST/bin/aipv"
echo "installed $PLUGIN_ID → $DEST"

omarchy plugin validate "$DEST" || fail "validation failed; the shell will not load $PLUGIN_ID"

omarchy-shell shell rescanPlugins >/dev/null 2>&1 || true
for _ in $(seq 1 40); do
  if omarchy plugin list --json 2>/dev/null |
     jq -e --arg id "$PLUGIN_ID" 'any(.[]; .id == $id)' >/dev/null; then
    break
  fi
  sleep 0.05
done
omarchy plugin list --json | jq -e --arg id "$PLUGIN_ID" 'any(.[]; .id == $id)' >/dev/null \
  || fail "the shell did not discover $PLUGIN_ID — check the shell log for QML errors"

# A checkout outside the default path: the widget shells out to
# linux/voice_tui.py there, so hand it the path instead of letting it guess.
default_checkout="$HOME/Apps/folo-ai-passport-voice"
if [[ -n $checkout && $checkout != "$default_checkout" ]]; then
  omarchy bar set "$PLUGIN_ID" repoPath "$checkout" --json >/dev/null \
    && echo "repoPath → $checkout"
fi

if omarchy plugin list --json |
   jq -e --arg id "$PLUGIN_ID" 'map(select(.id == $id))[0].enabled == true' >/dev/null; then
  echo "already enabled"
else
  omarchy plugin enable "$PLUGIN_ID" --section right
fi

# These commands are read by the widget through the forwarder checkout; the
# plugin directory alone is not enough to run voice.
if [[ -z $checkout ]]; then
  echo
  echo "next: install the forwarder and its systemd service —"
  echo "      see the Linux section of $REPO_URL"
fi
echo
echo "If the icon does not appear, restart the shell: omarchy restart shell"
