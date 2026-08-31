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

## Execution update: verified V8 artifact and native-build attempt

Authenticated access was restored over SSH on port `8022`. The isolated
qualification checkout reported Android 17, `aarch64`, Pixel 8 Pro, Rust and
Cargo `1.97.1`, Clang `21.1.8`, and `protoc` 35.1. The historical
`~/codex-termux` checkout was not modified.

The requested archive and binding were obtained from `rebroad/rusty_v8`
release `rusty-v8-v150.4.0` and verified against its release checksum asset:

```text
librusty_v8_ptrcomp_sandbox_release_aarch64-linux-android.a.gz
SHA256 54179034104bee6e68c7a83c304dddbaad797d2c65853318e7551a654a0a2b39
src_binding_ptrcomp_sandbox_release_aarch64-linux-android.rs
SHA256 639421ae6a0d125dde076cdb4c5d5b3afc9e3ce764acad4a772b7182ea77da66
```

Both `RUSTY_V8_ARCHIVE` and `RUSTY_V8_SRC_BINDING_PATH` overrides were
accepted by Rusty V8. Full workspace `cargo check -j1` passed the V8 step and
completed, with only existing TUI warnings. The focused protocol test remains
**PASS: 37 passed, 0 failed**.

The historical target-specific Clang/linker configuration was tested for the
native build. It avoided the earlier V8/linker failure, but the build stopped
with `No space left on device` before producing `codex`. The generated target
directory was removed only from the disposable qualification checkout. No
candidate binary, install, launch, session interaction, reconnect, or rollback
test was performed. Android TLS runtime behavior remains **UNPROVEN**.

This remains **PARTIALLY_QUALIFIED / BLOCKED**, not a Pixel regression. The
checksum-pinned Rebroad-hosted artifact is a temporary qualification input,
not yet a controlled release artifact.

## Execution update: native binaries produced

The target-specific Termux linker configuration was retried after freeing
only the generated target directory from the disposable checkout. With
`CARGO_INCREMENTAL=0`, `CARGO_PROFILE_DEV_DEBUG=0`, `-j2`, and the verified V8
overrides, both native targets built successfully in the isolated checkout:

```text
codex                  669645208 bytes
SHA256 054818a14695e84c86bec94395764e48d0948e8d7529eae6313c81ab94083b96
codex-code-mode-host   169650064 bytes
SHA256 1f86892fc6517e606034b4f87a5fa048c1fec6b23b7782b2b4933b7afd8aeac2
```

`codex --version` reported `codex-cli 0.152.0-alpha.4`; `codex --help` and
`codex-code-mode-host --help` both passed. The binaries were not installed or
copied over the active Termux Codex. Full login, live session interaction,
disconnect/reconnect, logical-session resume, Android TLS runtime, and
install/rollback remain unqualified. Final status is therefore
**PARTIALLY_QUALIFIED**, with release promotion still **BLOCKED**.

## Runtime qualification update: candidate initialization failure

The exact candidate hash was rechecked before runtime testing:

```text
/data/data/com.termux/files/home/codex-qualification-0.152/codex-rs/target/aarch64-linux-android/debug/codex
SHA256 054818a14695e84c86bec94395764e48d0948e8d7529eae6313c81ab94083b96
```

The candidate was invoked against the disposable repository
`/data/data/com.termux/files/home/codex-runtime-qualification-0.152`.
Both normal and `--ephemeral` non-interactive execution failed before any
network or authentication request:

```text
Error: failed to initialize in-process app-server client: lock() not supported
```

The unchanged active Termux Codex (`/data/data/com.termux/files/usr/bin/codex`,
`codex-cli 0.146.0`) reached its authenticated execution path in the same
repository. This identifies a candidate Android/Termux runtime incompatibility
before TLS/authentication, not an SSH or credential failure. No credentials
were printed and the active installation was not modified.

Candidate interaction, second interaction, SSH reconnect/resume, connectivity
interruption, installation, and rollback were not run. `ANDROID_TLS_RUNTIME`
is **FAIL_PRE_AUTH_APP_SERVER_INIT**. Stable release promotion remains blocked.

## Pixel runtime qualification update: Android lock compatibility

The follow-up branch `qualification/pixel-0.152-loz.2` contains three narrow
Android compatibility fixes, committed as `4902a7fc1`, `5c567feba`, and
`5db8949c1`. They replace Android-unsupported standard-library file locks at
app-server startup, installation-ID initialization, and thread-store
coordination with Unix `flock`; non-Unix behavior is unchanged, and
nonblocking writer conflicts still map to `TryLockError::WouldBlock`.

The rebuilt Pixel candidate from `5db8949c1` passed version/help smoke checks
and real ephemeral execution. It created a thread, used the shell to write
`candidate-marker.txt` containing `candidate-loz`, and exited 0. A persisted
session then wrote `resume-start.txt` containing `start-loz`; `codex exec
resume <session-id>` reconnected to that same session, wrote
`resume-followup.txt` containing `resumed-loz`, and exited 0. A separate
candidate install was staged at `~/codex-candidate-install-loz.2`; the active
Termux installation remained `codex-cli 0.146.0` and was not replaced.

Candidate artifacts:

```text
codex                  669200352 bytes
SHA256 06d75b8dcf20ee2a6e1bbc0e3b8096134910646454751086ec30fccc26ab92ba
codex-code-mode-host   169650064 bytes
SHA256 b9956f2138b5a231ac0ce9a7311a94f2318c1cc302c532ac65468c8ef58dbb79
```

The focused Rust tests were not run because the Pixel offline cache lacks the
`assert_matches` dev dependency. Runtime lock serialization and persistence
were exercised successfully, but disconnect/reconnect across a live network
interruption, native Android TLS beyond the authenticated execution path, and
full desktop qualification remain incomplete. Status is
**PARTIALLY_QUALIFIED**; no stable release tag is justified.
