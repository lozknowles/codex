#!/usr/bin/env sh
set -eu

termux_prefix="${PREFIX:-/data/data/com.termux/files/usr}"
install_name="${CODEX_TERMUX_INSTALL_DIR_NAME:-codex-termux-local}"
install_root="$termux_prefix/libexec/$install_name"
previous_root="${install_root}.previous"
swap_root="$termux_prefix/libexec/.${install_name}.rollback.$$"
command_path="$termux_prefix/bin/codex"
expected_target="../libexec/$install_name/codex"

case "$install_name" in
  ''|*[!A-Za-z0-9._-]*)
    echo "CODEX_TERMUX_INSTALL_DIR_NAME contains unsafe characters." >&2
    exit 1
    ;;
esac

if [ -e "$command_path" ] && [ ! -L "$command_path" ]; then
  echo "Refusing to replace the existing non-symlink command: $command_path" >&2
  exit 1
fi

if [ ! -d "$install_root" ] || [ ! -d "$previous_root" ]; then
  echo "Both current and previous local installations are required for rollback." >&2
  exit 1
fi

trap 'if [ -d "$swap_root" ]; then mv "$swap_root" "$install_root"; fi' EXIT HUP INT TERM
mv "$install_root" "$swap_root"
mv "$previous_root" "$install_root"
mv "$swap_root" "$previous_root"
trap - EXIT HUP INT TERM

ln -sfn "$expected_target" "$command_path"

if "$command_path" --version; then
  echo "Rolled back Codex. The replaced build is retained at $previous_root"
  exit 0
fi

echo "The previous build did not start; restoring the newer build." >&2
mv "$install_root" "$swap_root"
mv "$previous_root" "$install_root"
mv "$swap_root" "$previous_root"
"$command_path" --version || true
exit 1
