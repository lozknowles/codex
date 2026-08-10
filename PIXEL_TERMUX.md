# Pixel 8 Pro: native Codex CLI and TUI in Termux

This branch builds a private, direct-install Codex bundle for a Google Pixel 8
Pro. The Pixel's ARM64 processor and Android version satisfy the bundle's
`aarch64-linux-android` and API 29 requirements.

The bundle is not published to npm and does not replace the repository's
`main` branch. GitHub Actions builds it from the exact commit on
`agent/termux-phone-v150`, records the toolchain inputs, creates a SHA-256 checksum,
and retains the downloadable artifact for the configured retention period.

## 1. Prepare Termux

Use a current Termux installation from F-Droid or the official Termux GitHub
releases, rather than the obsolete Google Play build. In Termux run:

```sh
pkg update
pkg upgrade -y
pkg install -y git openssh ripgrep tar unzip coreutils
termux-setup-storage
```

Android will ask for storage access. Grant it if you want to install the bundle
from the phone's Downloads folder or work on files in shared storage.

## 2. Download the build

1. Open `lozknowles/codex` on GitHub.
2. Open **Actions** and select **termux-local-build**.
3. Open the latest successful run for `agent/termux-phone-v150`.
4. Download the `codex-termux-pixel-arm64-...` artifact on the Pixel.

GitHub downloads an outer ZIP containing the `.tar.gz` bundle and its
`.sha256` file.

## 3. Verify and install

In Termux:

```sh
cd ~/storage/downloads
mkdir -p codex-phone-build
cd codex-phone-build
unzip ../codex-termux-pixel-arm64-*.zip
sha256sum -c codex-termux-pixel-arm64-*.tar.gz.sha256
tar -xzf codex-termux-pixel-arm64-*.tar.gz
cd codex-termux-pixel-arm64-*/
sh install.sh
```

The installer places the build under
`$PREFIX/libexec/codex-termux-local/` and creates
`$PREFIX/bin/codex` as a symlink. It refuses to replace an existing regular
file at that command path. An earlier local bundle is retained as
`$PREFIX/libexec/codex-termux-local.previous/`.

Before changing the active installation, the installer launches the staged
Android binary with `--version`. A binary that cannot start on the phone is
rejected while the existing installation remains active.

## 4. Sign in and run the TUI

```sh
codex --version
codex login
codex
```

Opening the Android browser is the expected ChatGPT OAuth flow. If the local
browser callback is ever blocked, use `codex login --device-auth` instead.

The launcher sets the native executable and library paths required by Android.
It also disables automatic update prompts because this is a private build, not
an npm release. To opt back into update checks for diagnostics:

```sh
CODEX_TERMUX_CHECK_FOR_UPDATES=1 codex
```

## 5. Work with repositories

Keep normal Git repositories under the Termux home directory for the best Unix
filesystem behaviour:

```sh
mkdir -p ~/src
cd ~/src
git clone https://github.com/OWNER/REPOSITORY.git
cd REPOSITORY
codex
```

Shared Android storage is suitable for importing and exporting files but does
not preserve every Unix permission and locking behaviour expected by developer
tools.

## Uninstall

From the extracted bundle directory:

```sh
sh uninstall.sh
```

The uninstaller removes only the symlink when it still points to this local
installation. It does not remove an unrelated `codex` command.

## Roll back the upgrade

The upgrade installer retains the replaced working build. From the newly
extracted bundle directory, swap back with:

```sh
sh rollback.sh
```

The script verifies the restored command and retains the replaced build as the
new `.previous` version, so the same command can swap between the two builds.

## Build configuration

Non-secret defaults are held in `.env.termux.defaults`. An ignored
`.env.termux` file can override them for local validation. In GitHub Actions,
repository variables with the same names take precedence.

The Codex source comes from current `openai/codex`; the Android V8 `150.4.0`
archive and binding come from `rebroad/rusty_v8`. Every downloaded V8 input is
verified against the independently calculated SHA-256 values in
`third_party/v8/android-artifacts.toml` before compilation. The older working
Pixel artifact remains available as the rollback until this branch passes its
on-device acceptance test.
