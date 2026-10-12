#!/usr/bin/env bash
# Installs Bodega for the current user and adds it to your app menu.
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
# The program goes in ~/.local/opt. Your gear lives in ~/.local/share/bodega: never install there.
DEST="$HOME/.local/opt/bodega"
DATA="${BODEGA_DATA_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/bodega}"
# never let the program folder and the data folder overlap, either way round
case "$DEST/" in "$DATA"/*) echo "Refusing to install inside Bodega's data folder ($DATA)."; exit 1 ;; esac
case "$DATA/" in "$DEST"/*) echo "Bodega's data folder ($DATA) is inside $DEST. Move it first."; exit 1 ;; esac
if [ -e "$DEST/gear.json" ] || [ -d "$DEST/rentals" ]; then
  echo "$DEST holds Bodega data, not the program. Move it first."; exit 1
fi
rm -rf "$DEST"
mkdir -p "$DEST" "$HOME/.local/share/applications"
cp -R "$SRC"/. "$DEST"/
# the menu entry: the path quoted, and escaped for sed (a home folder can hold spaces, | or &)
SAFE_DEST=$(printf '%s' "$DEST" | sed -e 's/[\\/&|]/\\&/g')
sed "s|BODEGA_DIR|$SAFE_DEST|g" "$SRC/bodega.desktop" > "$HOME/.local/share/applications/bodega.desktop"
chmod +x "$DEST/Bodega"
echo "Bodega installed. Find it in your app menu, or run: $DEST/Bodega"
