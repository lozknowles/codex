#!/usr/bin/env python3
"""Deterministic OpenAI Codex to Android/Termux update harness."""

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TAG_RE = re.compile(r"^refs/tags/rust-v(?P<version>\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)\^?\{?\}?$")
V8_RE = re.compile(
    r'\[\[package\]\]\s+name = "v8"\s+version = "(?P<version>[^"]+)"'
    r'.*?checksum = "(?P<checksum>[0-9a-f]{64})"',
    re.S,
)
GATES = [
    "PROVENANCE",
    "BUILD",
    "APP_SERVER",
    "AUTHENTICATED_EXECUTION",
    "ANDROID_TLS",
    "PERSISTENCE",
    "RESUME",
    "SSH_RECONNECT",
    "LOCKING",
    "INSTALL",
    "ROLLBACK",
    "PROMOTION",
]


class HarnessError(RuntimeError):
    pass


@dataclass(frozen=True, order=True)
class Version:
    major: int
    minor: int
    patch: int
    prerelease: tuple[tuple[int, Any], ...]

    @classmethod
    def parse(cls, value: str) -> "Version":
        match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?", value)
        if not match:
            raise ValueError(f"invalid version: {value}")
        pre: list[tuple[int, Any]] = []
        if match.group(4):
            for item in match.group(4).split("."):
                pre.append((0, int(item)) if item.isdigit() else (1, item))
        else:
            pre.append((2, ""))
        return cls(int(match.group(1)), int(match.group(2)), int(match.group(3)), tuple(pre))


class Harness:
    def __init__(self, root: Path, runner=subprocess.run, ssh_options: list[str] | None = None):
        self.root = root.resolve()
        self.runner = runner
        self.ssh_options = ssh_options or []
        self.manifest_path = self.root / "android" / "downstream-manifest.json"
        self.patches_path = self.root / "android" / "patches.json"
        self.manifest = self._read_json(self.manifest_path)
        self.patch_config = self._read_json(self.patches_path)

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise HarnessError(f"cannot read {path}: {exc}") from exc

    @staticmethod
    def _write_json(path: Path, value: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, path)

    def run(self, args: list[str], cwd: Path | None = None, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
        result = self.runner(args, cwd=cwd or self.root, text=True, capture_output=True, env=env)
        if check and result.returncode:
            command = " ".join(shlex.quote(part) for part in args)
            detail = (result.stderr or result.stdout).strip()
            raise HarnessError(f"command failed ({result.returncode}): {command}\n{detail}")
        return result

    def git(self, *args: str, cwd: Path | None = None, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
        return self.run(["git", *args], cwd=cwd, check=check, env=env)

    def latest_release(self, remote: str) -> tuple[str, str, str]:
        output = self.git("ls-remote", "--tags", remote, "refs/tags/rust-v*").stdout
        refs: dict[str, dict[str, str]] = {}
        for line in output.splitlines():
            if not line.strip():
                continue
            sha, ref = line.split(maxsplit=1)
            peeled = ref.endswith("^{}")
            normalized = ref[:-3] if peeled else ref
            match = TAG_RE.fullmatch(normalized)
            if not match:
                continue
            version = match.group("version")
            refs.setdefault(version, {})["peeled" if peeled else "tag"] = sha
        if not refs:
            raise HarnessError(f"no canonical rust-v tags found on {remote}")
        version = max(refs, key=Version.parse)
        sha = refs[version].get("peeled") or refs[version]["tag"]
        return f"rust-v{version}", version, sha

    def evidence_dir(self, version: str) -> Path:
        return self.root / "evidence" / "android" / version

    def state_path(self, version: str) -> Path:
        return self.evidence_dir(version) / ".state.json"

    def load_state(self, version: str) -> dict[str, Any]:
        path = self.state_path(version)
        if not path.exists():
            return {"schema_version": 1, "version": version, "stages": {}, "gates": {gate: "NOT_RUN" for gate in GATES}}
        return self._read_json(path)

    def save_state(self, version: str, state: dict[str, Any]) -> None:
        state["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        self._write_json(self.state_path(version), state)

    @staticmethod
    def sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def last_json_output(result: subprocess.CompletedProcess, stage: str) -> dict[str, Any]:
        lines = result.stdout.splitlines()
        if not lines:
            raise HarnessError(f"{stage} returned success without a JSON summary")
        try:
            return json.loads(lines[-1])
        except json.JSONDecodeError as exc:
            raise HarnessError(f"{stage} returned malformed JSON summary") from exc

    def check(self, remote: str, record: bool = False) -> dict[str, Any]:
        tag, version, sha = self.latest_release(remote)
        inspected = self.manifest["last_inspected_openai"]
        qualified = self.manifest.get("last_qualified_openai")
        comparison = Version.parse(version)
        baseline = Version.parse((qualified or inspected)["version"])
        update = comparison > baseline
        result = {
            "state": "NEW_UPSTREAM_RELEASE_AVAILABLE" if update else "UP_TO_DATE",
            "latest_tag": tag,
            "latest_version": version,
            "latest_sha": sha,
            "last_inspected": inspected["version"],
            "last_qualified": qualified["version"] if qualified else None,
            "qualification_required": update or qualified is None,
        }
        if record:
            evidence = self.evidence_dir(version) / "detection.json"
            self._write_json(evidence, {**result, "detected_at": dt.datetime.now(dt.timezone.utc).isoformat()})
        return result

    def status(self, remote: str) -> dict[str, Any]:
        result = self.check(remote)
        result["active_pixel_version"] = self.manifest["android"]["active_version"]
        result["candidate_verdict"] = self.manifest["last_candidate"]["verdict"]
        result["patches"] = [
            {"id": patch["id"], "status": "REVIEW_REQUIRED"}
            for patch in self.patch_config["patches"]
        ]
        return result

    def prepare(self, remote: str, tag: str, version: str, sha: str, work_root: Path) -> dict[str, Any]:
        dirty = self.git("status", "--porcelain", "--untracked-files=all").stdout.splitlines()
        unsafe_dirty = [line for line in dirty if not line[3:].startswith("evidence/android/")]
        if unsafe_dirty:
            raise HarnessError("harness/patch inputs must be committed before preparing a candidate")
        candidate = work_root.resolve() / version
        branch = f"qualification/android-{version.replace('.', '-')}-loz-1"
        self.git("fetch", "--no-tags", remote, "tag", tag)
        resolved = self.git("rev-parse", f"{tag}^{{}}").stdout.strip()
        if resolved != sha:
            raise HarnessError(f"tag provenance mismatch: expected {sha}, got {resolved}")
        if candidate.exists():
            actual = self.git("rev-parse", "HEAD", cwd=candidate).stdout.strip()
            if actual != sha and not self.git("merge-base", "--is-ancestor", sha, actual, cwd=candidate, check=False).returncode == 0:
                raise HarnessError(f"existing candidate has unexpected provenance: {actual}")
        else:
            candidate.parent.mkdir(parents=True, exist_ok=True)
            self.git("worktree", "add", "-b", branch, str(candidate), sha)
        state = self.load_state(version)
        state["source"] = {"tag": tag, "upstream_sha": sha, "path": str(candidate), "branch": branch}
        state["stages"]["SOURCE_PREPARED"] = True
        state["gates"]["PROVENANCE"] = "PASS"
        self.save_state(version, state)
        return state["source"]

    def inspect_v8(self, source: Path) -> dict[str, str]:
        lockfile = source / "codex-rs" / "Cargo.lock"
        match = V8_RE.search(lockfile.read_text(encoding="utf-8"))
        if not match:
            raise HarnessError(f"cannot identify v8 package in {lockfile}")
        current = match.groupdict()
        expected = self.manifest["rusty_v8"]
        current["status"] = (
            "V8_COMPATIBLE"
            if current["version"] == expected["crate_version"] and current["checksum"] == expected["crate_checksum"]
            else "RUSTY_V8_REFRESH_REQUIRED"
        )
        return current

    def classify_patch(self, source: Path, patch: Path) -> str:
        forward = self.git("apply", "--check", str(patch), cwd=source, check=False)
        if forward.returncode == 0:
            return "REQUIRED_UNCHANGED"
        reverse = self.git("apply", "--reverse", "--check", str(patch), cwd=source, check=False)
        return "UPSTREAM_FIXED" if reverse.returncode == 0 else "REVIEW_REQUIRED"

    def classify(self, source: Path, version: str, persist: bool = True) -> dict[str, Any]:
        source = source.resolve()
        if not (source / ".git").exists() and not self.git("rev-parse", "--git-dir", cwd=source, check=False).returncode == 0:
            raise HarnessError(f"not a git worktree: {source}")
        classifications = []
        with tempfile.TemporaryDirectory(prefix="codex-android-index-") as temporary:
            environment = os.environ.copy()
            environment["GIT_INDEX_FILE"] = str(Path(temporary) / "index")
            self.git("read-tree", "HEAD", cwd=source, env=environment)
            for metadata in sorted(self.patch_config["patches"], key=lambda item: item["order"]):
                patch = self.root / metadata["patch"]
                forward = self.git("apply", "--cached", "--check", str(patch), cwd=source, check=False, env=environment)
                if forward.returncode == 0:
                    status = "REQUIRED_UNCHANGED"
                    self.git("apply", "--cached", str(patch), cwd=source, env=environment)
                else:
                    reverse = self.git("apply", "--cached", "--reverse", "--check", str(patch), cwd=source, check=False, env=environment)
                    status = "UPSTREAM_FIXED" if reverse.returncode == 0 else "REVIEW_REQUIRED"
                classifications.append({
                    "id": metadata["id"],
                    "status": status,
                    "patch": metadata["patch"],
                    "removal_condition": metadata["removal_condition"],
                })
        result = {
            "version": version,
            "source_sha": self.git("rev-parse", "HEAD", cwd=source).stdout.strip(),
            "v8": self.inspect_v8(source),
            "patches": classifications,
            "verdict": "REVIEW_REQUIRED" if any(item["status"] == "REVIEW_REQUIRED" for item in classifications) else "CLASSIFIED",
        }
        if persist:
            self._write_json(self.evidence_dir(version) / "patch-classification.json", result)
            state = self.load_state(version)
            state["patch_classification"] = result
            state["stages"]["PATCHES_CLASSIFIED"] = True
            self.save_state(version, state)
        return result

    def apply_patches(self, source: Path, version: str) -> None:
        classification = self.classify(source, version)
        blocked = [item for item in classification["patches"] if item["status"] == "REVIEW_REQUIRED"]
        if blocked:
            raise HarnessError("patch review required: " + ", ".join(item["id"] for item in blocked))
        for item in classification["patches"]:
            if item["status"] == "REQUIRED_UNCHANGED":
                self.git("am", "--3way", str(self.root / item["patch"]), cwd=source)
        state = self.load_state(version)
        state["downstream_sha"] = self.git("rev-parse", "HEAD", cwd=source).stdout.strip()
        state["stages"]["PATCHED"] = True
        self.save_state(version, state)

    def adopt_source(self, source: Path, version: str) -> dict[str, Any]:
        state = self.load_state(version)
        previous_sha = state.get("downstream_sha") or state.get("source", {}).get("upstream_sha")
        if not previous_sha:
            raise HarnessError("prepare and patch the candidate before adopting an additional source commit")
        actual_sha = self.git("rev-parse", "HEAD", cwd=source).stdout.strip()
        if self.git("status", "--porcelain", "--untracked-files=no", cwd=source).stdout.strip():
            raise HarnessError("cannot adopt a dirty source tree")
        ancestry = self.git("merge-base", "--is-ancestor", previous_sha, actual_sha, cwd=source, check=False)
        if ancestry.returncode:
            raise HarnessError("adopted source must descend from the classified patch stack")
        commits = self.git(
            "log", "--format=%H %s", f"{previous_sha}..{actual_sha}", cwd=source
        ).stdout.splitlines()
        state["downstream_sha"] = actual_sha
        state["adopted_source"] = {
            "previous_sha": previous_sha,
            "sha": actual_sha,
            "commits": commits,
            "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
        self.save_state(version, state)
        return state["adopted_source"]

    def ssh_script(self, target: str, script: str, arguments: list[str], check: bool = True) -> subprocess.CompletedProcess:
        command = ["ssh", *self.ssh_options, target, "bash", "-s", "--", *arguments]
        result = self.runner(command, input=script, text=True, capture_output=True)
        if check and result.returncode:
            raise HarnessError(f"remote command failed ({result.returncode}): {(result.stderr or result.stdout).strip()}")
        return result

    def build(self, version: str, target: str, remote_source: str, v8_archive: str, v8_binding: str) -> dict[str, Any]:
        state = self.load_state(version)
        expected_sha = state.get("downstream_sha") or state.get("source", {}).get("upstream_sha")
        if not expected_sha:
            raise HarnessError("prepare and patch the candidate before build")
        script = r'''set -eu
source_dir=$1
expected_sha=$2
v8_archive=$3
v8_binding=$4
cd "$source_dir"
actual_sha=$(git rev-parse HEAD)
[ "$actual_sha" = "$expected_sha" ] || { echo "SOURCE_SHA_MISMATCH $actual_sha" >&2; exit 41; }
[ -z "$(git status --porcelain --untracked-files=no)" ] || { echo DIRTY_SOURCE >&2; exit 42; }
available_kb=$(df -Pk . | awk 'NR==2 {print $4}')
[ "$available_kb" -ge 15728640 ] || { echo "INSUFFICIENT_DISK_KB $available_kb" >&2; exit 43; }
[ -f "$v8_archive" ] && [ -f "$v8_binding" ] || { echo RUSTY_V8_REFRESH_REQUIRED >&2; exit 44; }
export RUSTY_V8_ARCHIVE="$v8_archive"
export RUSTY_V8_SRC_BINDING_PATH="$v8_binding"
export CARGO_INCREMENTAL=1 CARGO_PROFILE_RELEASE_DEBUG=0 CARGO_PROFILE_RELEASE_LTO=false
export CC_AARCH64_LINUX_ANDROID=aarch64-linux-android-clang
export CXX_AARCH64_LINUX_ANDROID=aarch64-linux-android-clang++
export AR_AARCH64_LINUX_ANDROID=llvm-ar RANLIB_AARCH64_LINUX_ANDROID=llvm-ranlib
export CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER=aarch64-linux-android-clang
clang_builtins=$(find "${PREFIX:-/data/data/com.termux/files/usr}/lib/clang" -type f -name 'libclang_rt.builtins-aarch64-android.a' | sort -V | tail -1)
[ -f "$clang_builtins" ] || { echo ANDROID_CLANG_BUILTINS_REQUIRED >&2; exit 45; }
export CARGO_TARGET_AARCH64_LINUX_ANDROID_RUSTFLAGS='-Clink-arg=-lc++_shared -Clink-arg=-Wl,-rpath,$ORIGIN'
start=$(date +%s)
cargo rustc --locked --manifest-path codex-rs/Cargo.toml --target aarch64-linux-android --release -p codex-code-mode-host --bin codex-code-mode-host -j1 -- -C "link-arg=$clang_builtins" </dev/null
cargo rustc --locked --manifest-path codex-rs/Cargo.toml --target aarch64-linux-android --release -p codex-cli --bin codex -j1 -- -C "link-arg=$clang_builtins" </dev/null
elapsed=$(($(date +%s)-start))
codex=codex-rs/target/aarch64-linux-android/release/codex
host=codex-rs/target/aarch64-linux-android/release/codex-code-mode-host
printf '{"elapsed_seconds":%s,"codex_sha256":"%s","codex_bytes":%s,"code_mode_host_sha256":"%s","code_mode_host_bytes":%s,"clang_builtins":"%s","clang_builtins_sha256":"%s","release_lto":false}\n' \
  "$elapsed" "$(sha256sum "$codex" | awk '{print $1}')" "$(wc -c < "$codex")" \
  "$(sha256sum "$host" | awk '{print $1}')" "$(wc -c < "$host")" \
  "$clang_builtins" "$(sha256sum "$clang_builtins" | awk '{print $1}')"
'''
        result = self.ssh_script(target, script, [remote_source, expected_sha, v8_archive, v8_binding])
        summary = self.last_json_output(result, "build")
        summary.update({"target": target, "source_sha": expected_sha, "built_at": dt.datetime.now(dt.timezone.utc).isoformat()})
        self._write_json(self.evidence_dir(version) / "build.json", summary)
        state["build"] = summary
        state["stages"]["BUILT"] = True
        state["gates"]["BUILD"] = "PASS"
        self.save_state(version, state)
        return summary

    def import_build(self, version: str, target: str, remote_source: str, source_sha: str, candidate: str, code_host: str) -> dict[str, Any]:
        script = r'''set -eu
source_dir=$1
expected_sha=$2
candidate=$3
code_host=$4
cd "$source_dir"
[ "$(git rev-parse HEAD)" = "$expected_sha" ] || exit 46
[ -z "$(git status --porcelain --untracked-files=no)" ] || exit 47
[ -x "$candidate" ] && [ -x "$code_host" ] || exit 48
printf '{"codex_sha256":"%s","codex_bytes":%s,"code_mode_host_sha256":"%s","code_mode_host_bytes":%s,"version":"%s"}\n' \
  "$(sha256sum "$candidate" | awk '{print $1}')" "$(wc -c < "$candidate")" \
  "$(sha256sum "$code_host" | awk '{print $1}')" "$(wc -c < "$code_host")" \
  "$($candidate --version </dev/null)"
'''
        result = self.ssh_script(target, script, [remote_source, source_sha, candidate, code_host])
        summary = self.last_json_output(result, "import-build")
        summary.update({"target": target, "source_sha": source_sha, "imported_at": dt.datetime.now(dt.timezone.utc).isoformat()})
        expected = self.manifest.get("artifacts", {})
        for key in ["codex_sha256", "code_mode_host_sha256"]:
            if expected.get(key) and expected[key] != summary[key]:
                raise HarnessError(f"imported artifact differs from manifest: {key}")
        self._write_json(self.evidence_dir(version) / "build.json", summary)
        state = self.load_state(version)
        state["source"] = {"upstream_sha": self.manifest["last_candidate"]["upstream_sha"], "path": remote_source}
        state["downstream_sha"] = source_sha
        state["build"] = summary
        state["stages"]["BUILT"] = True
        state["gates"]["PROVENANCE"] = "PASS"
        state["gates"]["BUILD"] = "PASS_IMPORTED_REVERIFIED"
        self.save_state(version, state)
        return summary

    def lock_tests(self, version: str, target: str, remote_source: str, v8_archive: str, v8_binding: str) -> None:
        state = self.load_state(version)
        expected_sha = state.get("downstream_sha") or state.get("source", {}).get("upstream_sha")
        if not expected_sha:
            raise HarnessError("prepare and patch the candidate before lock tests")
        script = r'''set -eu
source_dir=$1
expected_sha=$2
v8_archive=$3
v8_binding=$4
cd "$source_dir"
[ "$(git rev-parse HEAD)" = "$expected_sha" ] || exit 45
export RUSTY_V8_ARCHIVE="$v8_archive" RUSTY_V8_SRC_BINDING_PATH="$v8_binding"
export CARGO_INCREMENTAL=1 CARGO_PROFILE_DEV_DEBUG=0
export CC_AARCH64_LINUX_ANDROID=aarch64-linux-android-clang
export CXX_AARCH64_LINUX_ANDROID=aarch64-linux-android-clang++
export AR_AARCH64_LINUX_ANDROID=llvm-ar RANLIB_AARCH64_LINUX_ANDROID=llvm-ranlib
export CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER=aarch64-linux-android-clang
clang_builtins=$(find "${PREFIX:-/data/data/com.termux/files/usr}/lib/clang" -type f -name 'libclang_rt.builtins-aarch64-android.a' | sort -V | tail -1)
[ -f "$clang_builtins" ] || { echo ANDROID_CLANG_BUILTINS_REQUIRED >&2; exit 46; }
export CARGO_TARGET_AARCH64_LINUX_ANDROID_RUSTFLAGS="-Clink-arg=-lc++_shared -Clink-arg=-Wl,-rpath,\$ORIGIN -Clink-arg=$clang_builtins"
cargo test --locked --manifest-path codex-rs/Cargo.toml --target aarch64-linux-android -p codex-thread-store writer_locks --lib -j1 </dev/null
cargo test --locked --manifest-path codex-rs/Cargo.toml --target aarch64-linux-android -p codex-app-server-transport app_server_startup_lock_serializes_waiters --lib -j1 </dev/null
cargo test --locked --manifest-path codex-rs/Cargo.toml --target aarch64-linux-android -p codex-core resolve_installation_id --lib -j1 </dev/null
'''
        result = self.ssh_script(target, script, [remote_source, expected_sha, v8_archive, v8_binding])
        output = result.stdout + result.stderr
        test_results = [
            {
                "status": match.group("status"),
                "passed": int(match.group("passed")),
                "failed": int(match.group("failed")),
                "ignored": int(match.group("ignored")),
                "measured": int(match.group("measured")),
                "filtered_out": int(match.group("filtered")),
            }
            for match in re.finditer(
                r"test result: (?P<status>\w+)\. (?P<passed>\d+) passed; "
                r"(?P<failed>\d+) failed; (?P<ignored>\d+) ignored; "
                r"(?P<measured>\d+) measured; (?P<filtered>\d+) filtered out",
                output,
            )
        ]
        if len(test_results) != 3 or any(item["status"] != "ok" or item["failed"] for item in test_results):
            raise HarnessError("focused lock tests completed without three unambiguous passing summaries")
        log_path = self.evidence_dir(version) / "lock-tests.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(output, encoding="utf-8")
        evidence = {
            "result": "PASS",
            "target": target,
            "source_sha": expected_sha,
            "tests": ["thread-store writer locks", "app-server startup lock", "installation ID"],
            "test_results": test_results,
            "totals": {
                key: sum(item[key] for item in test_results)
                for key in ["passed", "failed", "ignored", "measured", "filtered_out"]
            },
            "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "output_sha256": hashlib.sha256(output.encode()).hexdigest(),
            "log": str(log_path.relative_to(self.root)),
        }
        self._write_json(self.evidence_dir(version) / "lock-tests.json", evidence)
        state["lock_tests"] = evidence
        state["gates"]["LOCKING"] = "PASS_FOCUSED"
        self.save_state(version, state)

    def qualify(self, version: str, target: str, candidate: str, code_host: str, runtime_dir: str) -> dict[str, Any]:
        state = self.load_state(version)
        expected = state.get("build")
        if not expected:
            raise HarnessError("a verified build record is required before qualification")
        script = r'''set -eu
candidate=$1
code_host=$2
runtime=$3
expected_codex=$4
expected_host=$5
mkdir -p "$runtime"
[ "$(sha256sum "$candidate" | awk '{print $1}')" = "$expected_codex" ] || exit 51
[ "$(sha256sum "$code_host" | awk '{print $1}')" = "$expected_host" ] || exit 52
version=$($candidate --version </dev/null)
$candidate --help </dev/null >/dev/null
$code_host --help </dev/null >/dev/null
cd "$runtime"
rm -f evergreen-ephemeral.txt evergreen-persist.txt evergreen-resume.txt
app_server_home="$runtime/app-server-home"
mkdir -p "$app_server_home"
printf '%s\n' '{"method":"initialize","id":0,"params":{"clientInfo":{"name":"loz_android_qualification","title":"loz Android qualification","version":"1"}}}' \
  | CODEX_HOME="$app_server_home" timeout 30 "$candidate" app-server > app-server.jsonl 2> app-server.stderr
grep -Eq '"id"[[:space:]]*:[[:space:]]*0' app-server.jsonl || { echo APP_SERVER_INITIALIZE_RESPONSE_MISSING >&2; exit 57; }
grep -Eq '"result"[[:space:]]*:' app-server.jsonl || { echo APP_SERVER_INITIALIZE_RESULT_MISSING >&2; exit 58; }
$candidate exec --ephemeral --skip-git-repo-check --json 'Use the shell tool to write exactly evergreen-ephemeral to evergreen-ephemeral.txt, then stop.' </dev/null > ephemeral.jsonl
[ "$(cat evergreen-ephemeral.txt)" = evergreen-ephemeral ] || exit 53
$candidate exec --skip-git-repo-check --json 'Use the shell tool to write exactly evergreen-persist to evergreen-persist.txt, then stop.' </dev/null > persist.jsonl
[ "$(cat evergreen-persist.txt)" = evergreen-persist ] || exit 54
thread_id=$(sed -n 's/.*"thread_id":"\([^"]*\)".*/\1/p' persist.jsonl | head -1)
[ -n "$thread_id" ] || { echo THREAD_ID_NOT_FOUND >&2; exit 55; }
printf '{"version":"%s","thread_id":"%s","app_server":"PASS_INITIALIZE"}\n' "$version" "$thread_id"
'''
        initial = self.ssh_script(target, script, [candidate, code_host, runtime_dir, expected["codex_sha256"], expected["code_mode_host_sha256"]])
        runtime = self.last_json_output(initial, "initial qualification")
        resume_script = r'''set -eu
candidate=$1
runtime=$2
thread_id=$3
cd "$runtime"
$candidate exec --skip-git-repo-check resume "$thread_id" --json 'Use the shell tool to write exactly evergreen-resume to evergreen-resume.txt, then stop.' </dev/null > resume.jsonl
[ "$(cat evergreen-resume.txt)" = evergreen-resume ] || exit 56
printf '{"thread_id":"%s","resume":"PASS"}\n' "$thread_id"
'''
        resumed = self.ssh_script(target, resume_script, [candidate, runtime_dir, runtime["thread_id"]])
        resume = self.last_json_output(resumed, "resume qualification")
        locking = "PASS_FOCUSED_AND_RUNTIME" if state["gates"].get("LOCKING") == "PASS_FOCUSED" else "PASS_RUNTIME_PATHS_PENDING_FOCUSED"
        gates = {
            "PROVENANCE": "PASS",
            "BUILD": "PASS",
            "APP_SERVER": "PASS",
            "AUTHENTICATED_EXECUTION": "PASS",
            "ANDROID_TLS": "PASS",
            "PERSISTENCE": "PASS",
            "RESUME": "PASS",
            "SSH_RECONNECT": "PASS",
            "LOCKING": locking,
            "INSTALL": "NOT_RUN",
            "ROLLBACK": "NOT_RUN",
            "PROMOTION": "NOT_RUN",
        }
        summary = {
            "version": version,
            "target": target,
            "thread_id": resume["thread_id"],
            "app_server": runtime["app_server"],
            "gates": gates,
            "verdict": "RUNTIME_PASS",
        }
        self._write_json(self.evidence_dir(version) / "qualification.json", summary)
        state["gates"].update(gates)
        state["stages"]["RUNTIME_PASS"] = True
        state["stages"]["SESSION_PASS"] = True
        state["stages"]["RECONNECT_PASS"] = True
        self.save_state(version, state)
        return summary

    def install(
        self,
        version: str,
        target: str,
        candidate: str,
        code_host: str,
        active: str,
        active_host: str,
        approve: bool,
    ) -> None:
        if not approve:
            raise HarnessError("install requires --approve-install")
        state = self.load_state(version)
        required = ["PROVENANCE", "BUILD", "APP_SERVER", "AUTHENTICATED_EXECUTION", "ANDROID_TLS", "PERSISTENCE", "RESUME", "SSH_RECONNECT", "LOCKING"]
        if any(not state["gates"].get(gate, "").startswith("PASS") for gate in required) or state["gates"].get("LOCKING") != "PASS_FOCUSED_AND_RUNTIME":
            raise HarnessError("all runtime qualification gates must pass before install")
        expected = state["build"]["codex_sha256"]
        expected_host = state["build"]["code_mode_host_sha256"]
        backup = f"{active}.backup-{version}"
        backup_host = f"{active_host}.backup-{version}"
        script = r'''set -eu
candidate=$1
code_host=$2
active=$3
active_host=$4
backup=$5
backup_host=$6
expected=$7
expected_host=$8
[ "$(sha256sum "$candidate" | awk '{print $1}')" = "$expected" ] || exit 61
[ "$(sha256sum "$code_host" | awk '{print $1}')" = "$expected_host" ] || exit 65
[ -f "$active" ] || exit 62
[ ! -e "$backup" ] && [ ! -e "$backup_host" ] || exit 63
old_sha=$(sha256sum "$active" | awk '{print $1}')
old_mode=$(stat -c %a "$active")
cp -p "$active" "$backup"
old_host_present=false
old_host_sha=""
old_host_mode=""
if [ -f "$active_host" ]; then
  old_host_present=true
  old_host_sha=$(sha256sum "$active_host" | awk '{print $1}')
  old_host_mode=$(stat -c %a "$active_host")
  cp -p "$active_host" "$backup_host"
fi
temporary="${active}.new.$$"
temporary_host="${active_host}.new.$$"
cp "$candidate" "$temporary"
cp "$code_host" "$temporary_host"
chmod --reference="$active" "$temporary"
chmod --reference="$active" "$temporary_host"
mv "$temporary_host" "$active_host"
mv "$temporary" "$active"
[ "$(sha256sum "$active" | awk '{print $1}')" = "$expected" ] && \
  [ "$(sha256sum "$active_host" | awk '{print $1}')" = "$expected_host" ] || {
    cp -p "$backup" "$active"
    if [ "$old_host_present" = true ]; then cp -p "$backup_host" "$active_host"; else rm -f "$active_host"; fi
    exit 64
  }
printf '{"old_codex_sha256":"%s","old_codex_mode":"%s","old_host_present":%s,"old_host_sha256":"%s","old_host_mode":"%s","codex_sha256":"%s","code_mode_host_sha256":"%s"}\n' \
  "$old_sha" "$old_mode" "$old_host_present" "$old_host_sha" "$old_host_mode" "$expected" "$expected_host"
'''
        result = self.ssh_script(
            target,
            script,
            [candidate, code_host, active, active_host, backup, backup_host, expected, expected_host],
        )
        summary = self.last_json_output(result, "install")
        summary.update(
            {
                "active": active,
                "active_host": active_host,
                "backup": backup,
                "backup_host": backup_host,
                "installed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            }
        )
        state["install"] = summary
        self._write_json(self.evidence_dir(version) / "install.json", summary)
        state["gates"]["INSTALL"] = "PASS"
        state["stages"]["INSTALL_PASS"] = True
        self.save_state(version, state)

    def rollback(self, version: str, target: str) -> None:
        state = self.load_state(version)
        install = state.get("install")
        if not install:
            raise HarnessError("no recorded installation to roll back")
        script = r'''set -eu
active=$1
backup=$2
active_host=$3
backup_host=$4
old_host_present=$5
expected=$6
expected_host=$7
[ -f "$backup" ] || exit 71
temporary="${active}.rollback.$$"
cp -p "$backup" "$temporary"
mv "$temporary" "$active"
[ "$(sha256sum "$active" | awk '{print $1}')" = "$expected" ] || exit 72
if [ "$old_host_present" = true ]; then
  [ -f "$backup_host" ] || exit 73
  temporary_host="${active_host}.rollback.$$"
  cp -p "$backup_host" "$temporary_host"
  mv "$temporary_host" "$active_host"
  [ "$(sha256sum "$active_host" | awk '{print $1}')" = "$expected_host" ] || exit 74
else
  rm -f "$active_host"
  [ ! -e "$active_host" ] || exit 75
fi
printf '{"codex_sha256":"%s","host_present":%s,"code_mode_host_sha256":"%s"}\n' "$expected" "$old_host_present" "$expected_host"
'''
        result = self.ssh_script(
            target,
            script,
            [
                install["active"],
                install["backup"],
                install["active_host"],
                install["backup_host"],
                str(install["old_host_present"]).lower(),
                install["old_codex_sha256"],
                install["old_host_sha256"],
            ],
        )
        summary = self.last_json_output(result, "rollback")
        summary["completed_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        state["rollback"] = summary
        self._write_json(self.evidence_dir(version) / "rollback.json", summary)
        state["gates"]["ROLLBACK"] = "PASS"
        state["stages"]["ROLLBACK_PASS"] = True
        self.save_state(version, state)

    def promote(self, version: str, target: str, candidate: str, code_host: str, approve: bool) -> None:
        if not approve:
            raise HarnessError("promotion requires --approve-promotion")
        state = self.load_state(version)
        if state["gates"].get("ROLLBACK") != "PASS":
            raise HarnessError("a successful rollback proof is required before promotion")
        install = state["install"]
        expected = state["build"]["codex_sha256"]
        expected_host = state["build"]["code_mode_host_sha256"]
        script = r'''set -eu
candidate=$1
code_host=$2
active=$3
active_host=$4
expected=$5
expected_host=$6
[ "$(sha256sum "$candidate" | awk '{print $1}')" = "$expected" ] || exit 81
[ "$(sha256sum "$code_host" | awk '{print $1}')" = "$expected_host" ] || exit 83
temporary="${active}.promote.$$"
temporary_host="${active_host}.promote.$$"
cp "$candidate" "$temporary"
cp "$code_host" "$temporary_host"
chmod --reference="$active" "$temporary"
chmod --reference="$active" "$temporary_host"
mv "$temporary_host" "$active_host"
mv "$temporary" "$active"
[ "$(sha256sum "$active" | awk '{print $1}')" = "$expected" ] || exit 82
 [ "$(sha256sum "$active_host" | awk '{print $1}')" = "$expected_host" ] || exit 84
"$active" --version </dev/null
'''
        result = self.ssh_script(
            target,
            script,
            [candidate, code_host, install["active"], install["active_host"], expected, expected_host],
        )
        state["promotion"] = {
            "result": "PASS",
            "version_output": result.stdout.strip(),
            "codex_sha256": expected,
            "code_mode_host_sha256": expected_host,
        }
        state["gates"]["PROMOTION"] = "PASS"
        self.save_state(version, state)

    def record_qualified(self, version: str, active_version: str, active_hash: str, downstream_sha: str) -> None:
        state = self.load_state(version)
        mandatory = [gate for gate in GATES if gate != "PROMOTION"]
        if any(not state["gates"].get(gate, "").startswith("PASS") for gate in mandatory):
            raise HarnessError("cannot update the qualified manifest until all pre-promotion gates pass")
        manifest = self._read_json(self.manifest_path)
        source = state.get("source", {})
        manifest["last_qualified_openai"] = {
            "tag": source.get("tag", f"rust-v{version}"),
            "version": version,
            "sha": source.get("upstream_sha"),
        }
        manifest["last_candidate"] = {
            "tag": source.get("tag", f"rust-v{version}"),
            "version": version,
            "upstream_sha": source.get("upstream_sha"),
            "downstream_sha": downstream_sha,
            "release": active_version,
            "verdict": "QUALIFIED",
        }
        manifest["android"]["active_version"] = active_version
        manifest["android"]["active_codex_sha256"] = active_hash
        manifest["artifacts"] = state["build"]
        manifest["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        self._write_json(self.manifest_path, manifest)
        state["gates"]["PROMOTION"] = "PASS_RECORDED"
        state["stages"]["QUALIFIED"] = True
        self.save_state(version, state)


def repository_root(script: Path) -> Path:
    resolved = script.resolve()
    for parent in resolved.parents:
        if (parent / "android" / "downstream-manifest.json").is_file():
            return parent
    return resolved.parent


def print_status(value: dict[str, Any]) -> None:
    for key, item in value.items():
        if key == "patches":
            print("Android patches:")
            for patch in item:
                print(f"  {patch['id']:<32} {patch['status']}")
        else:
            print(f"{key.replace('_', ' ').title():<32} {item}")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--root", type=Path, default=repository_root(Path(__file__)))
    result.add_argument("--remote", default="openai")
    result.add_argument("--ssh-port", type=int)
    result.add_argument("--identity-file", type=Path)
    sub = result.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    sub.add_parser("status")
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--tag")
    prepare.add_argument("--work-root", type=Path, default=Path("work/android"))
    classify = sub.add_parser("classify")
    classify.add_argument("--source", type=Path, required=True)
    classify.add_argument("--version", required=True)
    patch = sub.add_parser("patch")
    patch.add_argument("--source", type=Path, required=True)
    patch.add_argument("--version", required=True)
    adopt = sub.add_parser("adopt-source")
    adopt.add_argument("--source", type=Path, required=True)
    adopt.add_argument("--version", required=True)
    build = sub.add_parser("build")
    build.add_argument("--version", required=True)
    build.add_argument("--pixel", required=True)
    build.add_argument("--remote-source", required=True)
    build.add_argument("--v8-archive", required=True)
    build.add_argument("--v8-binding", required=True)
    imported = sub.add_parser("import-build")
    imported.add_argument("--version", required=True)
    imported.add_argument("--pixel", required=True)
    imported.add_argument("--remote-source", required=True)
    imported.add_argument("--source-sha", required=True)
    imported.add_argument("--candidate", required=True)
    imported.add_argument("--code-host", required=True)
    lock_tests = sub.add_parser("lock-tests")
    lock_tests.add_argument("--version", required=True)
    lock_tests.add_argument("--pixel", required=True)
    lock_tests.add_argument("--remote-source", required=True)
    lock_tests.add_argument("--v8-archive", required=True)
    lock_tests.add_argument("--v8-binding", required=True)
    qualify = sub.add_parser("qualify")
    qualify.add_argument("--version", required=True)
    qualify.add_argument("--pixel", required=True)
    qualify.add_argument("--candidate", required=True)
    qualify.add_argument("--code-host", required=True)
    qualify.add_argument("--runtime-dir", required=True)
    install = sub.add_parser("install")
    install.add_argument("--version", required=True)
    install.add_argument("--pixel", required=True)
    install.add_argument("--candidate", required=True)
    install.add_argument("--code-host", required=True)
    install.add_argument("--active", required=True)
    install.add_argument("--active-host", required=True)
    install.add_argument("--approve-install", action="store_true")
    rollback = sub.add_parser("rollback")
    rollback.add_argument("--version", required=True)
    rollback.add_argument("--pixel", required=True)
    promote = sub.add_parser("promote")
    promote.add_argument("--version", required=True)
    promote.add_argument("--pixel", required=True)
    promote.add_argument("--candidate", required=True)
    promote.add_argument("--code-host", required=True)
    promote.add_argument("--approve-promotion", action="store_true")
    record = sub.add_parser("record-qualified")
    record.add_argument("--version", required=True)
    record.add_argument("--active-version", required=True)
    record.add_argument("--active-hash", required=True)
    record.add_argument("--downstream-sha", required=True)
    full = sub.add_parser("full")
    full.add_argument("--work-root", type=Path, default=Path("work/android"))
    full.add_argument("--pixel")
    full.add_argument("--remote-source")
    full.add_argument("--v8-archive")
    full.add_argument("--v8-binding")
    full.add_argument("--candidate")
    full.add_argument("--code-host")
    full.add_argument("--runtime-dir")
    full.add_argument("--active")
    full.add_argument("--active-host")
    full.add_argument("--approve-install", action="store_true")
    full.add_argument("--approve-promotion", action="store_true")
    sub.add_parser("resume")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    ssh_options = []
    if args.ssh_port:
        ssh_options.extend(["-p", str(args.ssh_port)])
    if args.identity_file:
        ssh_options.extend(["-i", str(args.identity_file)])
    harness = Harness(args.root, ssh_options=ssh_options)
    try:
        if args.command == "check":
            print_status(harness.check(args.remote, record=True))
        elif args.command == "status":
            print_status(harness.status(args.remote))
        elif args.command == "prepare":
            tag, version, sha = harness.latest_release(args.remote)
            if args.tag:
                tag = args.tag
                version = tag.removeprefix("rust-v")
                harness.git("fetch", "--no-tags", args.remote, "tag", tag)
                sha = harness.git("rev-parse", f"{tag}^{{}}").stdout.strip()
            print_status(harness.prepare(args.remote, tag, version, sha, args.work_root))
        elif args.command == "classify":
            print(json.dumps(harness.classify(args.source, args.version), indent=2))
        elif args.command == "patch":
            harness.apply_patches(args.source, args.version)
            print("PATCHED")
        elif args.command == "adopt-source":
            print(json.dumps(harness.adopt_source(args.source, args.version), indent=2))
        elif args.command == "build":
            print(json.dumps(harness.build(args.version, args.pixel, args.remote_source, args.v8_archive, args.v8_binding), indent=2))
        elif args.command == "import-build":
            print(json.dumps(harness.import_build(args.version, args.pixel, args.remote_source, args.source_sha, args.candidate, args.code_host), indent=2))
        elif args.command == "lock-tests":
            harness.lock_tests(args.version, args.pixel, args.remote_source, args.v8_archive, args.v8_binding)
            print("LOCK_TESTS_PASS")
        elif args.command == "qualify":
            print(json.dumps(harness.qualify(args.version, args.pixel, args.candidate, args.code_host, args.runtime_dir), indent=2))
        elif args.command == "install":
            harness.install(
                args.version,
                args.pixel,
                args.candidate,
                args.code_host,
                args.active,
                args.active_host,
                args.approve_install,
            )
            print("INSTALL_PASS")
        elif args.command == "rollback":
            harness.rollback(args.version, args.pixel)
            print("ROLLBACK_PASS")
        elif args.command == "promote":
            harness.promote(args.version, args.pixel, args.candidate, args.code_host, args.approve_promotion)
            print("PROMOTION_PASS; stable tag remains a separate reviewed operation")
        elif args.command == "record-qualified":
            harness.record_qualified(args.version, args.active_version, args.active_hash, args.downstream_sha)
            print("QUALIFIED_RECORDED; tag creation remains a separate reviewed operation")
        elif args.command in {"full", "resume"}:
            update = harness.check(args.remote, record=True)
            print_status(update)
            if update["state"] == "UP_TO_DATE":
                return 0
            if args.command == "resume":
                state = harness.load_state(update["latest_version"])
                print(json.dumps(state, indent=2))
                return 0
            source = harness.prepare(args.remote, update["latest_tag"], update["latest_version"], update["latest_sha"], args.work_root)
            classification = harness.classify(Path(source["path"]), update["latest_version"])
            print(json.dumps(classification, indent=2))
            if classification["verdict"] == "REVIEW_REQUIRED" or classification["v8"]["status"] != "V8_COMPATIBLE":
                print("REVIEW_REQUIRED")
                return 2
            harness.apply_patches(Path(source["path"]), update["latest_version"])
            build_inputs = [args.pixel, args.remote_source, args.v8_archive, args.v8_binding, args.candidate, args.code_host, args.runtime_dir]
            if not all(build_inputs):
                print("PATCHED; BUILD_INPUT_REQUIRED (resume with full and Pixel build arguments)")
                return 3
            harness.build(update["latest_version"], args.pixel, args.remote_source, args.v8_archive, args.v8_binding)
            harness.lock_tests(update["latest_version"], args.pixel, args.remote_source, args.v8_archive, args.v8_binding)
            harness.qualify(update["latest_version"], args.pixel, args.candidate, args.code_host, args.runtime_dir)
            if not args.approve_install:
                print("RUNTIME_QUALIFIED; install requires --approve-install")
                return 0
            if not args.active or not args.active_host:
                raise HarnessError("--active and --active-host are required with --approve-install")
            harness.install(
                update["latest_version"],
                args.pixel,
                args.candidate,
                args.code_host,
                args.active,
                args.active_host,
                True,
            )
            harness.rollback(update["latest_version"], args.pixel)
            if args.approve_promotion:
                harness.promote(update["latest_version"], args.pixel, args.candidate, args.code_host, True)
            else:
                print("ROLLBACK_PASS; final promotion requires --approve-promotion")
        return 0
    except HarnessError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
