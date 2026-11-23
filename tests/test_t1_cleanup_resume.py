"""Finite existing-backup cleanup controls; temporary files and API doubles only."""

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "t1"
    / "resume_t1_verified_cleanup.py"
)
if not SCRIPT.is_file():
    SCRIPT = Path(__file__).with_name("resume_t1_verified_cleanup.py")
spec = importlib.util.spec_from_file_location("resume", SCRIPT)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


def process(name, pid, ppid, uid):
    return {
        "Name": name,
        "pid": str(pid),
        "PPid": str(ppid),
        "Uid": " ".join([str(uid)] * 4),
        "proc_directory_uid": uid,
    }


def fixture_row(path, parent, action, keeper=""):
    s = path.stat()
    return {
        "id": path.relative_to(parent).as_posix(),
        "device": str(s.st_dev),
        "inode": str(s.st_ino),
        "logical_bytes": str(s.st_size),
        "mtime_ns": str(s.st_mtime_ns),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "action": action,
        "keeper": keeper,
    }


def isolated_runtime():
    return patch.object(
        r,
        "sys",
        types.SimpleNamespace(
            platform="linux",
            flags=types.SimpleNamespace(isolated=True, no_site=True),
            dont_write_bytecode=True,
        ),
    )


class Controls(unittest.TestCase):
    def test_ssh_exception_requires_root_parent_and_exact_uid_lineage(self):
        c = process("sshd", 4, 3, 1271)
        p = process("sshd", 3, 1, 0)
        self.assertEqual(
            r.user_session_exception(c, p, 1271),
            "user_ssh_session_with_root_sshd_parent",
        )
        p["proc_directory_uid"] = 1271
        self.assertIsNone(r.user_session_exception(c, p, 1271))
        p = process("sshd", 9, 1, 0)
        self.assertIsNone(r.user_session_exception(c, p, 1271))

    def test_pam_exception_requires_same_user_systemd_parent(self):
        c = process("(sd-pam)", 4, 3, 1271)
        p = process("systemd", 3, 1, 1271)
        self.assertEqual(
            r.user_session_exception(c, p, 1271),
            "user_pam_helper_with_same_user_systemd_parent",
        )
        p["Name"] = "python"
        self.assertIsNone(r.user_session_exception(c, p, 1271))

    def test_sftp_and_other_unreadable_workloads_are_never_session_exceptions(self):
        parent = process("sshd", 3, 1, 0)
        for name in ("sftp-server", "python", "gurobi", "bash", "sshd-session"):
            self.assertIsNone(
                r.user_session_exception(process(name, 4, 3, 1271), parent, 1271)
            )
        self.assertIsNone(r.user_session_exception({"Name": "sshd"}, parent, 1271))

    def test_specific_reference_always_retains_target(self):
        row = {"id": "model-agrologistic/.pytest_cache/x", "action": "cache"}
        gate = {
            "process_references": [(r.m.PARENT / row["id"]).as_posix()],
            "references": [],
            "control_omissions": [],
        }
        self.assertEqual(r.eligible(row, gate, [], []), "specific_process_reference")

    def test_unknown_process_retains_duplicate(self):
        row = {
            "id": "model-agrologistic-hygiene-audit/h300-root-cpu-source-abc/a.py",
            "action": "duplicate",
        }
        gate = {"process_references": [], "references": [], "control_omissions": []}
        self.assertEqual(
            r.eligible(
                row, gate, [], [{"classification": "unresolved_inaccessible_process"}]
            ),
            "unresolved_inaccessible_process",
        )

    def test_known_empty_control_must_keep_exact_hash(self):
        old = {
            "id": "model-agrologistic/result.json",
            "bytes": 0,
            "sha256": hashlib.sha256(b"").hexdigest(),
            "test_fixture_path": False,
        }
        diag = {"current_control_metadata": [old]}
        with patch.object(r.probe, "control_metadata", return_value=old):
            got = r.known_omissions([old], diag)
        self.assertEqual(
            got[0]["classification"], "verified_empty_historical_output_preserved"
        )
        changed = {**old, "bytes": 1, "sha256": "0" * 64}
        with (
            patch.object(r.probe, "control_metadata", return_value=changed),
            self.assertRaises(ValueError),
        ):
            r.known_omissions([old], diag)

    def test_new_control_omission_is_not_ignored(self):
        with self.assertRaises(ValueError):
            r.known_omissions(
                [{"id": "model-agrologistic/new.json"}],
                {"current_control_metadata": []},
            )

    def test_corrupt_diagnosis_is_rejected_before_parsing(self):
        with (
            patch.object(r, "digest_path", return_value=("0" * 64, None)),
            self.assertRaises(ValueError),
        ):
            r.read_diagnosis(Path("/not-read"))

    @unittest.skipUnless(os.name == "posix", "Real dirfd/inode control runs on Linux")
    def test_sftp_blocks_before_backup_hash_or_unlink(self):
        args = types.SimpleNamespace(
            original_run=str(r.m.BASE / "run"),
            original_package=str(r.m.BASE / "package"),
            diagnosis_archive=str(r.m.BASE / "diag/diagnosis.tar.gz"),
            apply=True,
        )
        with tempfile.TemporaryDirectory() as d:
            base = Path(d) / "model-agrologistic-hygiene-audit"
            base.mkdir()
            args.original_run = str(base / "run")
            args.original_package = str(base / "package")
            args.diagnosis_archive = str(base / "diag/diagnosis.tar.gz")
            with (
                isolated_runtime(),
                patch.object(r.m, "BASE", base),
                patch.object(r.m, "queue_empty"),
                patch.object(r, "active_sftp_processes", return_value=[{"pid": "3"}]),
                patch.object(r, "digest_path") as digest,
                patch.object(r.m, "remove_one") as unlink,
                contextlib.redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(r.run(args), 3)
            digest.assert_not_called()
            unlink.assert_not_called()

    @unittest.skipUnless(
        os.name == "posix", "Real backup reuse and unlink controls run on Linux"
    )
    def test_existing_backup_reused_without_recompression(self):
        self.integration(False)

    @unittest.skipUnless(
        os.name == "posix", "Real backup corruption control runs on Linux"
    )
    def test_corrupt_existing_backup_preserves_all_sources(self):
        self.integration(True)

    @unittest.skipUnless(
        os.name == "posix", "Real post-intent ambiguity control runs on Linux"
    )
    def test_post_intent_failure_stops_before_next_file(self):
        self.integration(False, uncertain=True)

    def integration(self, corrupt, uncertain=False):
        with tempfile.TemporaryDirectory() as d:
            parent = Path(d)
            base = parent / "model-agrologistic-hygiene-audit"
            base.mkdir()
            root = parent / "model-agrologistic"
            root.mkdir()
            cache = root / ".pytest_cache" / "x"
            cache.parent.mkdir()
            cache.write_bytes(b"cache")
            dup = base / "h300-root-cpu-source-abc" / "a.py"
            dup.parent.mkdir()
            dup.write_bytes(b"same")
            keeper = root / "keeper.py"
            keeper.write_bytes(b"same")
            keep = fixture_row(keeper, parent, "keep")
            rows = [
                fixture_row(cache, parent, "cache"),
                fixture_row(dup, parent, "duplicate", keep["id"]),
                keep,
            ]
            original = base / "run"
            original.mkdir()
            package = base / "package"
            package.mkdir()
            (package / "package-manifest.json").write_bytes(b"{}")
            (package / "selection.csv").write_bytes(b"fixture")
            backup = original / "historical-files-and-cache.tar.gz"
            with patch.object(r.m, "PARENT", parent):
                r.m.make_archive(backup, rows[:2])
                r.m.verify_archive(backup, rows[:2])
            checksum = hashlib.sha256(backup.read_bytes()).hexdigest()
            receipt = {
                "sha256": checksum,
                "members": 2,
                "archive_bytes": backup.stat().st_size,
                "independent_member_hash_check": True,
            }
            files = {
                "selection.csv": b"fixture",
                "verified-backup.json": json.dumps(receipt).encode(),
                "cleanup-result.json": b'{"logical_bytes_unlinked":0}',
            }
            if corrupt:
                backup.write_bytes(b"corrupt")
            before = backup.read_bytes()
            gate = {
                "process_references": [],
                "references": [],
                "control_omissions": [],
                "process_errors": [],
            }
            args = types.SimpleNamespace(
                original_run=str(original),
                original_package=str(package),
                diagnosis_archive=str(base / "diag/retention.tar.gz"),
                apply=True,
            )
            with contextlib.ExitStack() as stack:
                stack.enter_context(isolated_runtime())
                for obj, name, val in [
                    (r.m, "PARENT", parent),
                    (r.m, "BASE", base),
                    (r, "EXPECTED_MEMBERS", 2),
                    (r, "EXPECTED_TARGETS", 2),
                    (r, "BACKUP_SHA", checksum),
                    (r, "MANIFEST_SHA", hashlib.sha256(b"{}").hexdigest()),
                ]:
                    stack.enter_context(patch.object(obj, name, val))
                stack.enter_context(patch.object(r.m, "queue_empty"))
                stack.enter_context(
                    patch.object(r, "active_sftp_processes", return_value=[])
                )
                stack.enter_context(
                    patch.object(r.m, "load_inputs", return_value=({}, rows, []))
                )
                stack.enter_context(
                    patch.object(r.probe, "read_report", return_value=(files, {}))
                )
                stack.enter_context(
                    patch.object(
                        r,
                        "read_diagnosis",
                        return_value={"current_control_metadata": []},
                    )
                )
                stack.enter_context(
                    patch.object(r.m, "dependency_gate", return_value=gate)
                )
                stack.enter_context(
                    patch.object(
                        r.m,
                        "make_archive",
                        side_effect=AssertionError("Must not rearchive"),
                    )
                )
                stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                if uncertain:

                    def fail_after_unlink(row, keeper, journal, backup_sha):
                        r.m.event(journal, {"status": "unlink_intent", "id": row["id"]})
                        cache.unlink()
                        raise OSError(
                            "directory durability acknowledgement unavailable"
                        )

                    stack.enter_context(
                        patch.object(r.m, "remove_one", side_effect=fail_after_unlink)
                    )
                if corrupt:
                    with self.assertRaises(ValueError):
                        r.run(args)
                elif uncertain:
                    self.assertEqual(r.run(args), 2)
                else:
                    self.assertEqual(r.run(args), 0)
            self.assertEqual(backup.read_bytes(), before)
            self.assertEqual(keeper.read_bytes(), b"same")
            self.assertEqual(cache.exists(), corrupt)
            self.assertEqual(dup.exists(), corrupt or uncertain)
            if uncertain:
                out = next(base.glob("t1-reuse-backup-cleanup-*"))
                result = json.loads((out / "cleanup-result.json").read_text())
                self.assertEqual(result["uncertain_outcomes"], 1)
                self.assertEqual(result["duplicate_unlinked"], 0)
                self.assertEqual(result["unprocessed"], 1)
                self.assertEqual(result["status"], "cleanup_interrupted_preserved")


if __name__ == "__main__":
    unittest.main()
