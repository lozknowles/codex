#!/usr/bin/env sh

# Source this file; do not execute it. Callers must set TERMUX_REPO_ROOT.
: "${TERMUX_REPO_ROOT:?TERMUX_REPO_ROOT must point to the repository root}"

termux_defaults="$TERMUX_REPO_ROOT/.env.termux.defaults"
termux_overrides="${CODEX_TERMUX_ENV_FILE:-$TERMUX_REPO_ROOT/.env.termux}"

# Preserve values supplied by the caller (including GitHub repository
# variables) so they take precedence over the checked-in defaults.
caller_target=${CODEX_TERMUX_TARGET-}
caller_android_api=${CODEX_TERMUX_ANDROID_API-}
caller_clang_target=${CODEX_TERMUX_ANDROID_CLANG_TARGET-}
caller_ndk_version=${CODEX_TERMUX_ANDROID_NDK_VERSION-}
caller_rust_version=${CODEX_TERMUX_RUST_VERSION-}
caller_build_profile=${CODEX_TERMUX_BUILD_PROFILE-}
caller_retention_days=${CODEX_TERMUX_ARTIFACT_RETENTION_DAYS-}
caller_install_name=${CODEX_TERMUX_INSTALL_DIR_NAME-}
caller_source_repository=${CODEX_TERMUX_SOURCE_REPOSITORY-}
caller_npm_package=${CODEX_TERMUX_NPM_PACKAGE-}
caller_v8_repository=${CODEX_TERMUX_V8_REPOSITORY-}

if [ ! -f "$termux_defaults" ]; then
  echo "Missing Termux defaults: $termux_defaults" >&2
  return 1
fi

set -a
# shellcheck disable=SC1090
. "$termux_defaults"
if [ -f "$termux_overrides" ]; then
  # shellcheck disable=SC1090
  . "$termux_overrides"
fi
set +a

[ -z "$caller_target" ] || CODEX_TERMUX_TARGET=$caller_target
[ -z "$caller_android_api" ] || CODEX_TERMUX_ANDROID_API=$caller_android_api
[ -z "$caller_clang_target" ] || CODEX_TERMUX_ANDROID_CLANG_TARGET=$caller_clang_target
[ -z "$caller_ndk_version" ] || CODEX_TERMUX_ANDROID_NDK_VERSION=$caller_ndk_version
[ -z "$caller_rust_version" ] || CODEX_TERMUX_RUST_VERSION=$caller_rust_version
[ -z "$caller_build_profile" ] || CODEX_TERMUX_BUILD_PROFILE=$caller_build_profile
[ -z "$caller_retention_days" ] || CODEX_TERMUX_ARTIFACT_RETENTION_DAYS=$caller_retention_days
[ -z "$caller_install_name" ] || CODEX_TERMUX_INSTALL_DIR_NAME=$caller_install_name
[ -z "$caller_source_repository" ] || CODEX_TERMUX_SOURCE_REPOSITORY=$caller_source_repository
[ -z "$caller_npm_package" ] || CODEX_TERMUX_NPM_PACKAGE=$caller_npm_package
[ -z "$caller_v8_repository" ] || CODEX_TERMUX_V8_REPOSITORY=$caller_v8_repository
export CODEX_TERMUX_TARGET CODEX_TERMUX_ANDROID_API
export CODEX_TERMUX_ANDROID_CLANG_TARGET CODEX_TERMUX_ANDROID_NDK_VERSION
export CODEX_TERMUX_RUST_VERSION CODEX_TERMUX_BUILD_PROFILE
export CODEX_TERMUX_ARTIFACT_RETENTION_DAYS CODEX_TERMUX_INSTALL_DIR_NAME
export CODEX_TERMUX_SOURCE_REPOSITORY CODEX_TERMUX_NPM_PACKAGE
export CODEX_TERMUX_V8_REPOSITORY

case "$CODEX_TERMUX_ANDROID_API" in
  ''|*[!0-9]*)
    echo "CODEX_TERMUX_ANDROID_API must be numeric." >&2
    return 1
    ;;
esac

case "$CODEX_TERMUX_TARGET" in
  aarch64-linux-android) ;;
  *)
    echo "CODEX_TERMUX_TARGET must be aarch64-linux-android for this delivery." >&2
    return 1
    ;;
esac

case "$CODEX_TERMUX_ANDROID_CLANG_TARGET" in
  ''|*[!A-Za-z0-9._-]*)
    echo "CODEX_TERMUX_ANDROID_CLANG_TARGET contains unsafe characters." >&2
    return 1
    ;;
esac

case "$CODEX_TERMUX_ANDROID_NDK_VERSION" in
  ''|*[!0-9.]*)
    echo "CODEX_TERMUX_ANDROID_NDK_VERSION must contain only digits and dots." >&2
    return 1
    ;;
esac

case "$CODEX_TERMUX_RUST_VERSION" in
  ''|*[!A-Za-z0-9._-]*)
    echo "CODEX_TERMUX_RUST_VERSION contains unsafe characters." >&2
    return 1
    ;;
esac

case "$CODEX_TERMUX_BUILD_PROFILE" in
  debug|release) ;;
  *)
    echo "CODEX_TERMUX_BUILD_PROFILE must be debug or release." >&2
    return 1
    ;;
esac

case "$CODEX_TERMUX_ARTIFACT_RETENTION_DAYS" in
  ''|*[!0-9]*)
    echo "CODEX_TERMUX_ARTIFACT_RETENTION_DAYS must be numeric." >&2
    return 1
    ;;
esac

case "$CODEX_TERMUX_INSTALL_DIR_NAME" in
  ''|*[!A-Za-z0-9._-]*)
    echo "CODEX_TERMUX_INSTALL_DIR_NAME contains unsafe characters." >&2
    return 1
    ;;
esac
