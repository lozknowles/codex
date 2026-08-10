#!/usr/bin/env sh
set -eu

launcher_path=$0
while [ -L "$launcher_path" ]; do
  launcher_dir=$(CDPATH='' cd -- "$(dirname -- "$launcher_path")" && pwd)
  launcher_target=$(readlink "$launcher_path")
  case "$launcher_target" in
    /*) launcher_path=$launcher_target ;;
    *) launcher_path="$launcher_dir/$launcher_target" ;;
  esac
done
script_dir=$(CDPATH='' cd -- "$(dirname -- "$launcher_path")" && pwd)
termux_prefix="${PREFIX:-/data/data/com.termux/files/usr}"

sanitize_ld_library_path() {
  old_library_path="${LD_LIBRARY_PATH:-}"
  old_ifs=$IFS
  IFS=:
  sanitized=""
  for entry in $old_library_path; do
    [ -n "$entry" ] || continue
    case "$entry" in
      "$termux_prefix/lib"|"$termux_prefix/libexec"|/data/data/com.termux/files/usr/lib|/data/data/com.termux/files/usr/libexec)
        continue
        ;;
    esac
    if [ -z "$sanitized" ]; then
      sanitized=$entry
    else
      sanitized="$sanitized:$entry"
    fi
  done
  IFS=$old_ifs

  if [ -n "$sanitized" ]; then
    printf '%s:%s' "$script_dir" "$sanitized"
  else
    printf '%s' "$script_dir"
  fi
}

export CODEX_SELF_EXE="$script_dir/codex.bin"
export CODEX_TERMUX_LOCAL_BUILD=1
LD_LIBRARY_PATH=$(sanitize_ld_library_path)
export LD_LIBRARY_PATH

# This is a private build artifact rather than a published release channel.
# Prevent it from offering an update from an unrelated third-party package.
if [ "${CODEX_TERMUX_CHECK_FOR_UPDATES:-0}" != "1" ]; then
  set -- -c check_for_update_on_startup=false "$@"
fi

exec "$script_dir/codex.bin" "$@"
