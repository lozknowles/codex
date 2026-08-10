# Pixel / Termux change record

This file records the complete delivery delta carried by
`agent/termux-phone-v150` over the exact `openai/codex` main commit from which
the branch was created.

## Lineage correction

- Replaced the stale `rebroad/termux` source base (Codex `0.146.0`, V8
  `149.2.0`) with current `openai/codex` main (V8 `150.4.0`).
- Did not merge the stale `rebroad/codex` main branch or its product changes.
- Kept the previously working `agent/termux-phone` artifact as the known-good
  Pixel rollback rather than modifying that branch.

## Android V8 input

- Switched the Android V8 producer from `DioNanos/codex-termux` to Ed's
  `rebroad/rusty_v8` release `rusty-v8-v150.4.0`.
- Downloaded and independently inspected the ARM64 archive: it is a valid gzip
  containing a 175,855,012-byte ar archive with 1,875 object members.
- Pinned the independently calculated SHA-256 values for both the static
  archive and generated Rust binding in
  `third_party/v8/android-artifacts.toml`.
- Made the consumer reject a release tag that does not exactly equal
  `rusty-v8-v<resolved Cargo.lock version>`.
- Retained an optional repository mirror override, but any mirror must provide
  byte-identical assets matching the pinned hashes.
- Invalid cached or downloaded assets are deleted and cannot reach Cargo.

## Build and configuration

- Added the isolated `termux-local-build` workflow for
  `agent/termux-phone-v150` and manual dispatch.
- Kept GitHub checkout and artifact actions pinned to immutable commit SHAs.
- The workflow verifies its source commit, uses Cargo `--locked`, installs the
  Rust target selected by the repository's own `rust-toolchain.toml`, and
  records Rust, NDK, Android API and V8 provenance in `BUILD-INFO.txt`.
- Removed redundant hardcoded Rust version, compiler triple, repository name
  and npm package settings. The compiler triple is derived from the Rust target
  and Android API, and the V8 repository/tag live with their audited hashes.
- Centralised the remaining non-secret Android build settings in
  `.env.termux.defaults`, with an ignored `.env.termux` override supported for
  local experimentation.
- Produces a stripped direct-install tarball and a SHA-256 sidecar; no npm token
  or package publication is involved.

## Installation safety

- Installs under `$PREFIX/libexec/codex-termux-local` and exposes
  `$PREFIX/bin/codex` through a guarded symlink.
- Refuses to replace an unrelated regular file at `$PREFIX/bin/codex` before
  changing the active installation.
- Stages the complete bundle and runs `codex --version` against the staged
  Android binary before replacing the working version.
- Retains the replaced version as `codex-termux-local.previous`.
- Adds `rollback.sh`, which swaps current and previous installations, tests the
  restored command and automatically swaps back if that test fails.
- Keeps uninstall scoped to the exact validated installation name and removes
  the command symlink only when it points at this bundle.

## Runtime launcher

- Resolves the installed symlink before locating the native binary and bundled
  `libc++_shared.so`.
- Sets `CODEX_SELF_EXE` to the native ELF and supplies a sanitised
  `LD_LIBRARY_PATH` containing the bundle directory.
- Disables unrelated automatic update prompts for this private artifact by
  default; `CODEX_TERMUX_CHECK_FOR_UPDATES=1` is the explicit diagnostic opt-in.

## Validation

- Shell syntax, Python syntax, manifest/version/tag validation and a simulated
  Termux install/launch/rollback/uninstall lifecycle are checked locally and in
  GitHub Actions before the Android compilation begins.
- The real ARM64 Android compile and bundle staging run in GitHub Actions; the
  final acceptance gate remains launching the upgraded CLI/TUI on the Pixel.
