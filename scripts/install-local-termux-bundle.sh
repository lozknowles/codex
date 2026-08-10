#!/usr/bin/env sh
set -eu

bundle_root=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
termux_prefix="${PREFIX:-/data/data/com.termux/files/usr}"
install_name="${CODEX_TERMUX_INSTALL_DIR_NAME:-codex-termux-local}"
install_root="$termux_prefix/libexec/$install_name"
command_path="$termux_prefix/bin/codex"

case "$install_name" in
  ''|*[!A-Za-z0-9._-]*)
    echo "CODEX_TERMUX_INSTALL_DIR_NAME contains unsafe characters." >&2
    exit 1
    ;;
esac

if [ "$(uname -m)" != "aarch64" ]; then
  echo "This Codex build requires an ARM64 Android device (aarch64)." >&2
  exit 1
fi

if [ -z "${TERMUX_VERSION:-}" ] || [ ! -d "$termux_prefix/bin" ]; then
  echo "Run this installer inside the current Termux app." >&2
  exit 1
fi

for required_file in bin/codex bin/codex.bin bin/libc++_shared.so; do
  if [ ! -f "$bundle_root/$required_file" ]; then
    echo "Bundle is incomplete: missing $required_file" >&2
    exit 1
  fi
done

if [ -e "$command_path" ] && [ ! -L "$command_path" ]; then
  echo "Refusing to replace the existing non-symlink command: $command_path" >&2
  exit 1
fi

staging_root="$termux_prefix/libexec/.${install_name}.new.$$"
trap 'rm -rf "$staging_root"' EXIT HUP INT TERM
rm -rf "$staging_root"
mkdir -p "$staging_root"
cp "$bundle_root/bin/codex" "$staging_root/codex"
cp "$bundle_root/bin/codex.bin" "$staging_root/codex.bin"
cp "$bundle_root/bin/libc++_shared.so" "$staging_root/libc++_shared.so"
chmod 0755 "$staging_root/codex" "$staging_root/codex.bin"
chmod 0644 "$staging_root/libc++_shared.so"

echo "Checking the new Android binary before changing the active installation..."
PREFIX="$termux_prefix" TERMUX_VERSION="$TERMUX_VERSION" \
  "$staging_root/codex" --version

if [ -d "$install_root" ]; then
  backup_root="${install_root}.previous"
  rm -rf "$backup_root"
  mv "$install_root" "$backup_root"
  echo "Previous local build retained at $backup_root"
fi
mv "$staging_root" "$install_root"

ln -sfn "../libexec/$install_name/codex" "$command_path"

echo "Installed Codex for Termux at $install_root"
"$command_path" --version
echo "Run: codex login"
echo "Then start the TUI with: codex"
