# Pixel / Termux qualification record: OpenAI 0.152 downstream

Status: **PARTIALLY_QUALIFIED**; release promotion remains **BLOCKED**.

## Scope and provenance

The qualification subject is candidate commit
`af4415ad959df8d87051371ff9cac1993d2d7fed`, tagged
`v0.152.0-alpha.4-loz.1-rc1`. It is based on OpenAI
`7ac2dff554323b17d5f622b7aca236ca75c93259` (`0.152.0-alpha.4`). The moving
OpenAI `latest-alpha-cli` reference has since advanced to
`d2a6bad21bbda8098520f5605ba523ff10e94` (`0.152.0-alpha.6`); that newer
reference was not substituted into this qualification.

The preserved Pixel contract is **NATIVE_TERMUX**: a native ARM64 Termux
binary, installed from a versioned tarball with a checksum, a guarded
`$PREFIX/bin/codex` pointer, retained previous version, startup/version check,
login, and TUI operation. The prior records do not establish that Pixel was
used as an OpenAI remote-control client, so remote-control parity is not
claimed here.

Preserved references are `agent/termux-phone` at
`893dc78ec627b6f1b20df9ccd787d728ef320274` and
`agent/termux-phone-v150` at `8b364ca371d2b3c82093806c7e72a8c53f6d90c6`.
Their GitHub Actions native-build evidence includes successful runs
`31421824409` and `31433637048`, respectively. Those runs qualify the
historical branch revisions, not this OpenAI 0.152 candidate.

## Current access evidence

| Check | Result | Evidence / boundary |
|---|---|---|
| Pixel private reachability | PASS | Tailscale `100.100.97.118`; `tailscale ping` returned 5–51 ms |
| Termux SSH transport | PASS | SSH service responds on the user-confirmed port `8022` |
| Termux authentication | BLOCKED | available key/password did not authenticate |
| Authenticated Termux shell | BLOCKED | `Permission denied (publickey,password,keyboard-interactive)` |
| ADB transport | BLOCKED | `adb devices -l` was empty on hpubuntu |
| Pixel environment/toolchain inspection | BLOCKED | no authenticated shell or ADB device |

The host key was accepted only into a temporary known-hosts file. No Pixel
configuration, credentials, listener, or installation was changed.

## Qualification matrix

| Scenario | Result | Note |
|---|---|---|
| Pair/connect | BLOCKED | no authenticated Pixel execution path; remote-client use was not previously established |
| Start or attach a session | BLOCKED | no authenticated Pixel execution path |
| Basic command/session interaction | BLOCKED | no authenticated Pixel execution path |
| Disconnect and reconnect | NOT_RUN | no live session |
| Resume same logical session | NOT_RUN | no live session |
| Duplicate reconnect protection | NOT_RUN | no live session |
| Restart recovery | NOT_RUN | no live session |
| Android TLS runtime behavior | UNPROVEN | 23-line alignment is present, but no Android runtime was reached |
| Native ARM64 compile of candidate | BLOCKED | Cargo/rustc unavailable on local and hpubuntu builders |
| Candidate launch / TUI smoke test | BLOCKED | no candidate artifact and no authenticated Pixel shell |
| Install, update, rollback | NOT_RUN | no candidate artifact |

No native ARM64 build failure was observed; the build was not reached. This is
therefore not evidence of a Pixel regression.

## Conclusion

Architecture retained: **NATIVE_TERMUX**. Final Pixel status:
**PARTIALLY_QUALIFIED / BLOCKED**. The previous native Termux workflow and
operational knowledge remain preserved, while the current OpenAI-based
candidate has not been falsely marked Android-qualified.

Next qualification action: restore authenticated SSH access on port `8022` or
an approved ADB path, then inspect the Termux environment before attempting a
native build and the documented install/start/rollback sequence.

## Execution update: qualified descendant

The qualification branch now contains the justified build configuration fix
at `393d25d19a91958ee4152fb2770fcee2b231919f`. It uses the trusted Termux
`protoc` on Android while preserving vendored protoc for desktop builds.

With that fix, `cargo check -j1` passed the code-mode protocol, core,
app-server, transport, and TUI portions of the workspace. It then stopped at
Rusty V8 `v150.4.0`, requesting the official prebuilt artifact
`librusty_v8_ptrcomp_sandbox_release_aarch64-linux-android.a.gz`; the official
release URL returned HTTP 404. Termux has Clang, CMake, Make, Python,
pkg-config, and OpenSSL, but no `gn` or `ninja`, so a source V8 build was not
attempted. No V8 artifact was downloaded or substituted.

This is classified as **BUILD_CONFIGURATION_ONLY / UNQUALIFIED**. It is not
evidence of a semantic runtime regression. Candidate artifact generation,
launch, interaction, reconnect, and rollback remain blocked.

The focused `codex-code-mode-protocol` test completed on the Pixel with
**37 passed, 0 failed** in 0.15 seconds after the build configuration fix.
This validates the protoc path and protocol crate on Android, not the complete
Codex binary or runtime.
