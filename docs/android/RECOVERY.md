# Recovery

## Interrupted preparation or build

Run `./scripts/android/update-codex-android resume`. Inspect the recorded
source SHA, patch classification, V8 identity, and artifact hashes. Rerun the
specific failed stage; never create a marker manually.

The candidate is always an isolated worktree. Delete or recreate it only after
verifying its exact absolute path and preserving evidence. Cargo build caches
are disposable; source, staged binaries, the active install, and backups are
not.

## V8 changed

`RUSTY_V8_REFRESH_REQUIRED` means the manifest crate version/checksum does not
match the candidate lockfile. Stop. Obtain or build the exact Android archive
and generated binding through a controlled source, record their hashes and ABI
identity, then update the manifest in a reviewed commit. Never relabel an old
archive as compatible.

## Patch conflict

`REVIEW_REQUIRED` means neither forward nor reverse application is safe.
Compare the new upstream subsystem with the documented failure and semantics.
Choose `REQUIRED_ADAPTED`, `UPSTREAM_FIXED`, or `NO_LONGER_APPLICABLE` with
tests and evidence. Do not resolve a conflict merely to preserve history.

## Failed install

The install command writes temporary `codex` and `codex-code-mode-host`
binaries and moves each into place atomically. If either post-install hash
fails, it restores the recorded state. If manual recovery is required, verify
the backup hashes first, copy each to a temporary file beside the active
executable, preserve permissions, then rename it atomically. When the previous
release had no code-mode host, rollback preserves the candidate host under the
recorded recovery path and restores the previous absence without deleting the
artefact.

Never remove the known-good backup until the next release has passed install,
rollback, final promotion, and post-promotion smoke tests.
