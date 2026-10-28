#!/usr/bin/env bash
# Install the AI Passport voice bar widget into Omarchy from a checkout.
#
#   bash tools/install-omarchy-plugin.sh
#
# The plugin payload is omarchy/, which is also mirrored to its own repository
# for the Omarchy plugin marketplace. This installer lives outside that
# directory on purpose: the marketplace installs the plugin with
# `omarchy plugin add`, and a plugin repository should not ship a script that
# modifies the user's environment. There is no download-and-execute path —
# run it from a clone of this repository, which the forwarder needs anyway.
#
# Idempotent: re-running updates the installed copy in place and leaves the bar
# placement alone.
set -euo pipefail

PLUGIN_ID="manchunx7.ai-passport-voice"
DEST_ROOT="${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/plugins"
DEST="$DEST_ROOT/$PLUGIN_ID"

fail() { echo "install: $*" >&2; exit 1; }

# The plugin sits next to this script's parent; a copy of the script alone
# cannot install anything, so say that instead of cloning something.
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
checkout="$(cd "$here/.." && pwd)"
src="$checkout/omarchy"
[[ -f "$src/manifest.json" ]] || fail "no omarchy/manifest.json next to $here — run this from a checkout"

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

echo
echo "If the icon does not appear, restart the shell: omarchy restart shell"
