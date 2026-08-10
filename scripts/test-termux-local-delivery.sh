#!/usr/bin/env sh
set -eu

repo_root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
test_root=$(mktemp -d "${TMPDIR:-/tmp}/codex-termux-delivery.XXXXXX")
trap 'rm -rf "$test_root"' EXIT HUP INT TERM

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

echo "Testing environment defaults and caller overrides..."
TERMUX_REPO_ROOT=$repo_root
CODEX_TERMUX_ANDROID_API=35
export TERMUX_REPO_ROOT CODEX_TERMUX_ANDROID_API
# shellcheck disable=SC1091
. "$repo_root/scripts/load-termux-env.sh"
[ "$CODEX_TERMUX_ANDROID_API" = 35 ] || fail "caller override was not preserved"
[ "$CODEX_TERMUX_TARGET" = aarch64-linux-android ] || fail "target default was not loaded"

echo "Testing V8 repository validation..."
if CODEX_TERMUX_V8_REPOSITORY=invalid python3 "$repo_root/scripts/fetch_rusty_v8_android.py" \
  --output-dir "$test_root/v8" >"$test_root/v8.out" 2>"$test_root/v8.err"; then
  fail "invalid V8 repository was accepted"
fi
grep -q 'owner/repository syntax' "$test_root/v8.err" || fail "unexpected V8 validation error"

echo "Testing Pixel-style install, launcher and uninstall..."
bundle="$test_root/bundle"
prefix="$test_root/prefix"
fake_path="$test_root/fake-path"
mkdir -p "$bundle/bin" "$prefix/bin" "$prefix/libexec" "$fake_path"
cp "$repo_root/scripts/termux-local-launcher.sh" "$bundle/bin/codex"
cp "$repo_root/scripts/install-local-termux-bundle.sh" "$bundle/install.sh"
cp "$repo_root/scripts/uninstall-local-termux.sh" "$bundle/uninstall.sh"
printf '%s\n' 'test libc++ payload' > "$bundle/bin/libc++_shared.so"

printf '%s\n' \
  '#!/usr/bin/env sh' \
  'printf '\''self=%s\n'\'' "${CODEX_SELF_EXE:-}" >> "$CODEX_TERMUX_TEST_LOG"' \
  'printf '\''updates=%s\n'\'' "${CODEX_TERMUX_CHECK_FOR_UPDATES:-0}" >> "$CODEX_TERMUX_TEST_LOG"' \
  'printf '\''args=%s\n'\'' "$*" >> "$CODEX_TERMUX_TEST_LOG"' \
  > "$bundle/bin/codex.bin"
printf '%s\n' '#!/usr/bin/env sh' "printf '%s\\n' aarch64" > "$fake_path/uname"
chmod 0755 "$bundle/bin/codex" "$bundle/bin/codex.bin" "$bundle/install.sh" \
  "$bundle/uninstall.sh" "$fake_path/uname"

test_log="$test_root/launcher.log"
PATH="$fake_path:$PATH" PREFIX="$prefix" TERMUX_VERSION=test \
  CODEX_TERMUX_TEST_LOG="$test_log" sh "$bundle/install.sh"

[ -L "$prefix/bin/codex" ] || fail "codex command symlink was not installed"
[ -x "$prefix/libexec/codex-termux-local/codex.bin" ] || fail "native binary was not installed"
grep -q 'check_for_update_on_startup=false --version' "$test_log" \
  || fail "private-build update policy was not passed to Codex"
grep -q "self=$prefix/libexec/codex-termux-local/codex.bin" "$test_log" \
  || fail "CODEX_SELF_EXE does not point to the native binary"

PREFIX="$prefix" sh "$bundle/uninstall.sh"
[ ! -e "$prefix/bin/codex" ] || fail "codex command symlink was not removed"
[ ! -d "$prefix/libexec/codex-termux-local" ] || fail "install directory was not removed"

echo "Termux local delivery tests passed."
