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

PLUGIN_ID="dakai.ai-passport-voice"
# The plugin was published under the author's old handle first; an installed
# copy under that id is migrated below rather than left behind.
LEGACY_ID="manchunx7.ai-passport-voice"
DEST_ROOT="${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/plugins"
DEST="$DEST_ROOT/$PLUGIN_ID"
SHELL_JSON="${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/shell.json"

fail() { echo "install: $*" >&2; exit 1; }

# The plugin sits next to this script's parent; a copy of the script alone
# cannot install anything, so say that instead of cloning something.
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
checkout="$(cd "$here/.." && pwd)"
src="$checkout/omarchy"
[[ -f "$src/manifest.json" ]] || fail "no omarchy/manifest.json next to $here — run this from a checkout"

mkdir -p "$DEST_ROOT"

# Migration: carry the old widget's settings (language, repoPath) across, then
# drop the old copy so the bar keeps one widget, not a dead entry.
legacy_settings=()
if [[ -e "$DEST_ROOT/$LEGACY_ID" || -L "$DEST_ROOT/$LEGACY_ID" ]]; then
  while IFS=$'\t' read -r key value; do
    [[ -n $key ]] && legacy_settings+=("$key" "$value")
  done < <(jq -r --arg id "$LEGACY_ID" '
    [.bar.layout // {} | .[]? | .[]?
      | select(type == "object" and .id == $id)][0] // {}
    | to_entries[]
    | select(.key != "id" and .key != "hidden")
    | select((.value | type) == "string" or (.value | type) == "number"
             or (.value | type) == "boolean")
    | "\(.key)\t\(.value)"' "$SHELL_JSON" 2>/dev/null || true)
  omarchy-shell shell setPluginEnabled "$LEGACY_ID" false >/dev/null 2>&1 || true
  rm -rf "$DEST_ROOT/$LEGACY_ID"
  echo "migrated: removed the old $LEGACY_ID directory"
fi

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
  omarchy bar set "$PLUGIN_ID" repoPath "$checkout" >/dev/null \
    && echo "repoPath → $checkout"
fi

if omarchy plugin list --json |
   jq -e --arg id "$PLUGIN_ID" 'map(select(.id == $id))[0].enabled == true' >/dev/null; then
  echo "already enabled"
else
  omarchy plugin enable "$PLUGIN_ID" --section right
fi

# Settings can only be set on a widget the bar carries, so this waits for the
# enable above. Array is key,value pairs.
if (( ${#legacy_settings[@]} )); then
  for ((i = 0; i < ${#legacy_settings[@]}; i += 2)); do
    omarchy bar set "$PLUGIN_ID" "${legacy_settings[i]}" "${legacy_settings[i+1]}" \
      >/dev/null 2>&1 || true
  done
  echo "migrated: carried over $(( ${#legacy_settings[@]} / 2 )) setting(s)"
fi

echo
echo "If the icon does not appear, restart the shell: omarchy restart shell"
