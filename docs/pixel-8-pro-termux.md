# Pixel 8 Pro: local Codex CLI and TUI in Termux

This branch builds a private, direct-install Codex bundle for a Google Pixel 8
Pro. The Pixel's ARM64 processor and Android version satisfy the bundle's
`aarch64-linux-android` and API 29 requirements.

The bundle is not published to npm and does not replace the repository's
`main` branch. GitHub Actions builds it from the exact commit on
`agent/termux-phone`, records the toolchain inputs, creates a SHA-256 checksum,
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
3. Open the latest successful run for `agent/termux-phone`.
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

## 4. Sign in and run the TUI

```sh
codex --version
codex login
codex
```

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

## Build configuration

Non-secret defaults are held in `.env.termux.defaults`. For a local source
build, copy it to the ignored `.env.termux` file and change only the required
values. In GitHub Actions, repository variables with the same names take
precedence.

The V8 release repository remains an external input until its immutable assets
are mirrored into `lozknowles/codex`. Every downloaded V8 archive and binding is
verified against the SHA-256 values in
`third_party/v8/android-artifacts.toml` before compilation.
