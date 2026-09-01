# Upgrading Android Codex

Prerequisites are Python 3, Git, SSH, and the recorded Termux Rust/Clang
toolchain. Configure SSH in the operator account; do not put private keys,
passwords, tokens, or device secrets in the manifest or command history.

```bash
./scripts/android/update-codex-android check
./scripts/android/update-codex-android status
./scripts/android/update-codex-android full
```

Without Pixel arguments, `full` performs detection, isolated preparation,
classification and patching, then stops at `BUILD_INPUT_REQUIRED`. Resume with
the explicit recorded paths:

```bash
./scripts/android/update-codex-android full \
  --pixel pixel-termux \
  --remote-source /data/data/com.termux/files/home/codex-qualification-VERSION \
  --v8-archive /controlled/cache/librusty_v8...a.gz \
  --v8-binding /controlled/cache/src_binding...rs \
  --candidate /path/to/staged/codex \
  --code-host /path/to/staged/codex-code-mode-host \
  --runtime-dir /data/data/com.termux/files/home/codex-runtime-qualification-VERSION
```

This runs build, focused lock tests, and real Pixel runtime qualification. It
does not touch the active install. Review `evidence/android/VERSION/`.

Install and rollback proof require explicit authority:

```bash
./scripts/android/update-codex-android install \
  --version VERSION --pixel pixel-termux --candidate /path/to/codex \
  --code-host /path/to/codex-code-mode-host \
  --active /data/data/com.termux/files/usr/libexec/codex-termux-local/codex.bin \
  --active-host /data/data/com.termux/files/usr/libexec/codex-termux-local/codex-code-mode-host \
  --approve-install

./scripts/android/update-codex-android rollback --version VERSION --pixel pixel-termux
```

Final activation is separately approved:

```bash
./scripts/android/update-codex-android promote \
  --version VERSION --pixel pixel-termux --candidate /path/to/codex \
  --code-host /path/to/codex-code-mode-host \
  --approve-promotion
```

After final smoke tests, `record-qualified` updates the manifest. Stable tag
creation and pushing remain separate reviewed Git operations.

The state flow is:

```text
DETECTED -> SOURCE_PREPARED -> PATCHES_CLASSIFIED -> PATCHED -> BUILT
 -> RUNTIME_PASS -> SESSION_PASS -> RECONNECT_PASS -> INSTALL_PASS
 -> ROLLBACK_PASS -> QUALIFIED
```
