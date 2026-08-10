#!/usr/bin/env sh
set -eu

termux_prefix="${PREFIX:-/data/data/com.termux/files/usr}"
install_name="${CODEX_TERMUX_INSTALL_DIR_NAME:-codex-termux-local}"
install_root="$termux_prefix/libexec/$install_name"
command_path="$termux_prefix/bin/codex"
expected_target="../libexec/$install_name/codex"

case "$install_name" in
  ''|*[!A-Za-z0-9._-]*)
    echo "CODEX_TERMUX_INSTALL_DIR_NAME contains unsafe characters." >&2
    exit 1
    ;;
esac

if [ -L "$command_path" ] && [ "$(readlink "$command_path")" = "$expected_target" ]; then
  rm "$command_path"
fi

if [ -d "$install_root" ]; then
  rm -rf "$install_root"
fi

echo "Removed the local Codex Termux build."
if [ -d "${install_root}.previous" ]; then
  echo "A previous build remains at ${install_root}.previous"
fi
