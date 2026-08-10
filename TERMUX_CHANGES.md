# Loz Termux delivery changes

This file records the changes made for the private Pixel 8 Pro CLI/TUI build.

## Branch and delivery isolation

- Created `agent/termux-phone` from Ed's `rebroad/termux` commit
  `f155c6b156b7cd4a31ad6186d4f3460671896d4b`.
- Left `main` unchanged; its Raspberry Pi/ARMv7 release flow is not used.
- Added `termux-local-build`, scoped to the isolated Termux branches and manual
  dispatch.
- Added a direct `.tar.gz` bundle so no npm publication token, package scope or
  public release is required.

## Portability and hardcoding

- Added `.env.termux.defaults` as the single non-secret configuration source.
- Added ignored `.env.termux` local overrides and matching GitHub repository
  variable overrides.
- Externalised Android target/API/NDK, Rust version, build profile, artifact
  retention, install directory, source repository, npm compatibility package
  and V8 artifact repository where the toolchain permits it.
- Updated the V8 fetcher to accept the configured repository while retaining
  the audited release tag and SHA-256 values from the manifest.
- Replaced the source-build install script's hardcoded npm installation path
  with the package name read from `package.json`.

## Build and supply-chain controls

- Checkout and artifact actions remain pinned to commit SHAs.
- The workflow verifies that the checkout matches `GITHUB_SHA`.
- Cargo uses `--locked` and the recorded Rust/NDK versions.
- V8 archive and generated binding downloads are checksum verified.
- The resulting bundle is stripped, checksummed and supplied with
  `BUILD-INFO.txt` containing the exact source and toolchain inputs.
- The private launcher disables third-party automatic update prompts by
  default; `CODEX_TERMUX_CHECK_FOR_UPDATES=1` is an explicit opt-in.

## Defect repairs

- Repaired `verify-patches.sh` so the launcher lifecycle change using
  `exitCode` does not falsely report that dynamic subcommand routing is absent.
- Prevented `--release-tag` from silently selecting an artifact while retaining
  checksums belonging to a different tag.
- Added strict install-directory validation before any replacement or removal.
- Added atomic staging for installation, preservation of the previous local
  bundle, and guarded symlink creation/removal.
- Added a launcher that supplies `CODEX_SELF_EXE`, a safe local library path and
  the private-build update policy.
- Made the launcher resolve its installed symlink before locating `codex.bin`
  and `libc++_shared.so`; the delivery simulation caught the original path bug.

## Pixel installation documentation

- Added `docs/pixel-8-pro-termux.md` with preparation, download, checksum,
  installation, authentication, TUI usage, repository location and uninstall
  instructions.
