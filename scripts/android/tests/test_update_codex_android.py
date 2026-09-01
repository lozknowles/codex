import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "update_codex_android.py"
SPEC = importlib.util.spec_from_file_location("update_codex_android", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class FakeRunner:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def __call__(self, args, **kwargs):
        self.calls.append((args, kwargs))
        if not self.results:
            raise AssertionError(f"unexpected command: {args}")
        return self.results.pop(0)


def completed(stdout="", stderr="", returncode=0):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


class HarnessTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "android").mkdir()
        (self.root / "android" / "patches.json").write_text(
            json.dumps({"schema_version": 1, "patches": []}), encoding="utf-8"
        )
        self.manifest = {
            "last_inspected_openai": {
                "tag": "rust-v0.152.0-alpha.4",
                "version": "0.152.0-alpha.4",
                "sha": "a" * 40,
            },
            "last_qualified_openai": None,
            "last_candidate": {"verdict": "PARTIALLY_QUALIFIED"},
            "android": {"active_version": "0.146.0"},
            "rusty_v8": {"crate_version": "150.4.0", "crate_checksum": "1" * 64},
            "artifacts": {},
        }
        self.write_manifest()

    def tearDown(self):
        self.temp.cleanup()

    def write_manifest(self):
        (self.root / "android" / "downstream-manifest.json").write_text(
            json.dumps(self.manifest), encoding="utf-8"
        )

    def harness(self, runner=subprocess.run):
        return MODULE.Harness(self.root, runner=runner)

    def test_semver_orders_prereleases_and_stable(self):
        versions = ["0.153.0-alpha.10", "0.153.0", "0.153.0-alpha.2", "0.152.9"]
        self.assertEqual(max(versions, key=MODULE.Version.parse), "0.153.0")
        self.assertGreater(
            MODULE.Version.parse("0.153.0-alpha.10"),
            MODULE.Version.parse("0.153.0-alpha.2"),
        )

    def test_latest_release_uses_peeled_sha_and_ignores_malformed_tags(self):
        output = "\n".join(
            [
                f"{'1' * 40}\trefs/tags/rust-v0.153.0-alpha.2",
                f"{'2' * 40}\trefs/tags/rust-v0.153.0-alpha.2^{{}}",
                f"{'3' * 40}\trefs/tags/rust-vrust-v9.0.0",
                f"{'4' * 40}\trefs/tags/rust-v0.152.0",
            ]
        )
        harness = self.harness(FakeRunner([completed(output)]))
        self.assertEqual(
            harness.latest_release("openai"),
            ("rust-v0.153.0-alpha.2", "0.153.0-alpha.2", "2" * 40),
        )

    def test_check_reports_up_to_date(self):
        self.manifest["last_qualified_openai"] = self.manifest["last_inspected_openai"]
        self.write_manifest()
        output = f"{'a' * 40}\trefs/tags/rust-v0.152.0-alpha.4"
        result = self.harness(FakeRunner([completed(output)])).check("openai")
        self.assertEqual(result["state"], "UP_TO_DATE")
        self.assertFalse(result["qualification_required"])

    def test_check_reports_newer_upstream(self):
        output = f"{'b' * 40}\trefs/tags/rust-v0.153.0"
        result = self.harness(FakeRunner([completed(output)])).check("openai")
        self.assertEqual(result["state"], "NEW_UPSTREAM_RELEASE_AVAILABLE")
        self.assertTrue(result["qualification_required"])

    def write_v8_lock(self, version="150.4.0", checksum=None):
        checksum = checksum or "1" * 64
        source = self.root / "source" / "codex-rs"
        source.mkdir(parents=True, exist_ok=True)
        (source / "Cargo.lock").write_text(
            f'[[package]]\nname = "v8"\nversion = "{version}"\nsource = "registry"\nchecksum = "{checksum}"\n',
            encoding="utf-8",
        )
        return source.parent

    def test_v8_unchanged_is_compatible(self):
        self.assertEqual(self.harness().inspect_v8(self.write_v8_lock())["status"], "V8_COMPATIBLE")

    def test_v8_change_requires_refresh(self):
        result = self.harness().inspect_v8(self.write_v8_lock(version="151.0.0"))
        self.assertEqual(result["status"], "RUSTY_V8_REFRESH_REQUIRED")

    def init_git_fixture(self):
        repo = self.root / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Harness Test"], cwd=repo, check=True)
        file = repo / "value.txt"
        file.write_text("old\n", encoding="utf-8")
        subprocess.run(["git", "add", "value.txt"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=repo, check=True)
        file.write_text("new\n", encoding="utf-8")
        patch = self.root / "change.patch"
        patch.write_text(
            subprocess.run(["git", "diff"], cwd=repo, check=True, text=True, capture_output=True).stdout,
            encoding="utf-8",
        )
        subprocess.run(["git", "checkout", "--", "value.txt"], cwd=repo, check=True)
        return repo, file, patch

    def test_clean_patch_is_required_unchanged(self):
        repo, _, patch = self.init_git_fixture()
        self.assertEqual(self.harness().classify_patch(repo, patch), "REQUIRED_UNCHANGED")

    def test_already_applied_patch_is_upstream_fixed(self):
        repo, file, patch = self.init_git_fixture()
        file.write_text("new\n", encoding="utf-8")
        self.assertEqual(self.harness().classify_patch(repo, patch), "UPSTREAM_FIXED")

    def test_patch_conflict_requires_review(self):
        repo, file, patch = self.init_git_fixture()
        file.write_text("different\n", encoding="utf-8")
        self.assertEqual(self.harness().classify_patch(repo, patch), "REVIEW_REQUIRED")

    def test_adopt_source_accepts_clean_descendant(self):
        repo, file, _ = self.init_git_fixture()
        base = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo, check=True, text=True, capture_output=True
        ).stdout.strip()
        file.write_text("adopted\n", encoding="utf-8")
        subprocess.run(["git", "add", "value.txt"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-qm", "adopted source"], cwd=repo, check=True)
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo, check=True, text=True, capture_output=True
        ).stdout.strip()
        harness = self.harness()
        state = harness.load_state("0.153.0")
        state["downstream_sha"] = base
        harness.save_state("0.153.0", state)

        adopted = harness.adopt_source(repo, "0.153.0")

        self.assertEqual(adopted["sha"], head)
        self.assertIn("adopted source", adopted["commits"][0])

    def test_adopt_source_rejects_dirty_tree(self):
        repo, file, _ = self.init_git_fixture()
        base = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo, check=True, text=True, capture_output=True
        ).stdout.strip()
        file.write_text("dirty\n", encoding="utf-8")
        harness = self.harness()
        state = harness.load_state("0.153.0")
        state["downstream_sha"] = base
        harness.save_state("0.153.0", state)

        with self.assertRaisesRegex(MODULE.HarnessError, "dirty"):
            harness.adopt_source(repo, "0.153.0")

    def test_interrupted_state_round_trip(self):
        harness = self.harness()
        state = harness.load_state("0.153.0")
        state["stages"]["BUILT"] = True
        state["build"] = {"codex_sha256": "c" * 64}
        harness.save_state("0.153.0", state)
        self.assertEqual(harness.load_state("0.153.0")["build"]["codex_sha256"], "c" * 64)

    def test_install_is_fail_closed_without_approval(self):
        with self.assertRaisesRegex(MODULE.HarnessError, "approve-install"):
            self.harness().install(
                "0.153.0",
                "pixel",
                "/candidate",
                "/candidate-host",
                "/active",
                "/active-host",
                False,
            )

    def test_install_records_both_candidate_artifacts(self):
        remote_summary = {
            "old_codex_sha256": "a" * 64,
            "old_codex_mode": "755",
            "old_host_present": False,
            "old_host_sha256": "",
            "old_host_mode": "",
            "codex_sha256": "c" * 64,
            "code_mode_host_sha256": "d" * 64,
        }
        harness = self.harness(FakeRunner([completed(stdout=json.dumps(remote_summary) + "\n")]))
        state = harness.load_state("0.153.0")
        state["build"] = {"codex_sha256": "c" * 64, "code_mode_host_sha256": "d" * 64}
        state["gates"].update(
            {
                "PROVENANCE": "PASS",
                "BUILD": "PASS",
                "APP_SERVER": "PASS",
                "AUTHENTICATED_EXECUTION": "PASS",
                "ANDROID_TLS": "PASS",
                "PERSISTENCE": "PASS",
                "RESUME": "PASS",
                "SSH_RECONNECT": "PASS",
                "LOCKING": "PASS_FOCUSED_AND_RUNTIME",
            }
        )
        harness.save_state("0.153.0", state)

        harness.install(
            "0.153.0", "pixel", "/candidate", "/candidate-host", "/active", "/active-host", True
        )

        install = harness.load_state("0.153.0")["install"]
        self.assertEqual(install["code_mode_host_sha256"], "d" * 64)
        self.assertEqual(harness.runner.calls[0][0][-8:], [
            "/candidate",
            "/candidate-host",
            "/active",
            "/active-host",
            "/active.backup-0.153.0",
            "/active-host.backup-0.153.0",
            "c" * 64,
            "d" * 64,
        ])

    def test_rollback_removes_new_host_when_previous_install_had_none(self):
        harness = self.harness(
            FakeRunner(
                [
                    completed(
                        stdout=json.dumps(
                            {"codex_sha256": "a" * 64, "host_present": False, "code_mode_host_sha256": ""}
                        )
                        + "\n"
                    )
                ]
            )
        )
        state = harness.load_state("0.153.0")
        state["install"] = {
            "active": "/active",
            "active_host": "/active-host",
            "backup": "/backup",
            "backup_host": "/backup-host",
            "old_host_present": False,
            "old_codex_sha256": "a" * 64,
            "old_host_sha256": "",
        }
        harness.save_state("0.153.0", state)

        harness.rollback("0.153.0", "pixel")

        self.assertIn('rm -f "$active_host"', harness.runner.calls[0][1]["input"])
        self.assertEqual(harness.load_state("0.153.0")["gates"]["ROLLBACK"], "PASS")

    def test_build_failure_does_not_mark_build_pass(self):
        harness = self.harness(FakeRunner([completed(stderr="compile failed", returncode=1)]))
        state = harness.load_state("0.153.0")
        state["source"] = {"upstream_sha": "a" * 40}
        harness.save_state("0.153.0", state)
        with self.assertRaisesRegex(MODULE.HarnessError, "compile failed"):
            harness.build("0.153.0", "pixel", "/source", "/v8", "/binding")
        self.assertEqual(harness.load_state("0.153.0")["gates"]["BUILD"], "NOT_RUN")

    def test_build_disables_release_lto_for_pixel_memory_bound(self):
        summary = {
            "elapsed_seconds": 1,
            "codex_sha256": "c" * 64,
            "codex_bytes": 10,
            "code_mode_host_sha256": "d" * 64,
            "code_mode_host_bytes": 11,
            "clang_builtins": "/builtins.a",
            "clang_builtins_sha256": "e" * 64,
            "release_lto": False,
        }
        harness = self.harness(FakeRunner([completed(stdout=json.dumps(summary) + "\n")]))
        state = harness.load_state("0.153.0")
        state["source"] = {"upstream_sha": "a" * 40}
        harness.save_state("0.153.0", state)

        result = harness.build("0.153.0", "pixel", "/source", "/v8", "/binding")

        self.assertFalse(result["release_lto"])
        self.assertIn("CARGO_PROFILE_RELEASE_LTO=false", harness.runner.calls[0][1]["input"])

    def test_lock_tests_record_exact_counts_and_log(self):
        summaries = "\n".join(
            [
                "test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 17 filtered out",
                "test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 8 filtered out",
                "test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 201 filtered out",
            ]
        )
        harness = self.harness(FakeRunner([completed(stdout=summaries)]))
        state = harness.load_state("0.153.0")
        state["source"] = {"upstream_sha": "a" * 40}
        harness.save_state("0.153.0", state)

        harness.lock_tests("0.153.0", "pixel", "/source", "/v8", "/binding")

        evidence = json.loads(
            (self.root / "evidence" / "android" / "0.153.0" / "lock-tests.json").read_text()
        )
        self.assertEqual(evidence["totals"]["passed"], 5)
        self.assertEqual(evidence["totals"]["failed"], 0)
        self.assertTrue((self.root / evidence["log"]).is_file())

    def test_qualification_runs_real_app_server_initialize(self):
        harness = self.harness(
            FakeRunner(
                [
                    completed(stdout='{"version":"codex-cli 0.153.0","thread_id":"thread-1","app_server":"PASS_INITIALIZE"}\n'),
                    completed(stdout='{"thread_id":"thread-1","resume":"PASS"}\n'),
                ]
            )
        )
        state = harness.load_state("0.153.0")
        state["build"] = {"codex_sha256": "c" * 64, "code_mode_host_sha256": "d" * 64}
        harness.save_state("0.153.0", state)

        result = harness.qualify("0.153.0", "pixel", "/candidate", "/host", "/runtime")

        first_script = harness.runner.calls[0][1]["input"]
        self.assertIn('"method":"initialize"', first_script)
        self.assertIn("app-server", first_script)
        self.assertEqual(result["app_server"], "PASS_INITIALIZE")

    def test_qualification_failure_does_not_mark_runtime_pass(self):
        harness = self.harness(FakeRunner([completed(stderr="runtime failed", returncode=1)]))
        state = harness.load_state("0.153.0")
        state["build"] = {"codex_sha256": "c" * 64, "code_mode_host_sha256": "d" * 64}
        harness.save_state("0.153.0", state)
        with self.assertRaisesRegex(MODULE.HarnessError, "runtime failed"):
            harness.qualify("0.153.0", "pixel", "/candidate", "/host", "/runtime")
        self.assertNotIn("RUNTIME_PASS", harness.load_state("0.153.0")["stages"])

    def test_success_without_summary_is_a_controlled_failure(self):
        with self.assertRaisesRegex(MODULE.HarnessError, "without a JSON summary"):
            self.harness().last_json_output(completed(), "qualification")

    def test_manifest_update_requires_all_gates(self):
        with self.assertRaisesRegex(MODULE.HarnessError, "all pre-promotion gates"):
            self.harness().record_qualified("0.153.0", "0.153.0-loz.android.1", "c" * 64, "d" * 40)

    def test_manifest_update_after_install_and_rollback(self):
        harness = self.harness()
        state = harness.load_state("0.153.0")
        state["source"] = {"tag": "rust-v0.153.0", "upstream_sha": "a" * 40}
        state["build"] = {"codex_sha256": "c" * 64, "code_mode_host_sha256": "e" * 64}
        state["gates"].update({gate: "PASS" for gate in MODULE.GATES if gate != "PROMOTION"})
        harness.save_state("0.153.0", state)
        harness.record_qualified("0.153.0", "0.153.0-loz.android.1", "c" * 64, "d" * 40)
        updated = json.loads((self.root / "android" / "downstream-manifest.json").read_text())
        self.assertEqual(updated["last_qualified_openai"]["version"], "0.153.0")
        self.assertEqual(updated["android"]["active_version"], "0.153.0-loz.android.1")

    def test_no_command_creates_a_stable_tag(self):
        commands = {action.dest: action for action in MODULE.parser()._actions if action.dest == "command"}
        choices = set(commands["command"].choices)
        self.assertNotIn("tag", choices)
        self.assertNotIn("publish", choices)


if __name__ == "__main__":
    unittest.main()
