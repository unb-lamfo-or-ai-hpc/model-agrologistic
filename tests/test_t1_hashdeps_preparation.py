"""T1 controls with temporary files/API doubles only; no NPAD or optimizer."""

import importlib.util
import os
import stat
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "t1" / "verify_hash_dependencies.py"
if not SCRIPT.is_file():
    SCRIPT = Path(__file__).with_name("verify_hash_dependencies.py")
spec = importlib.util.spec_from_file_location("t1_hashdeps", SCRIPT)
m = importlib.util.module_from_spec(spec)
BEFORE_IMPORT = set(sys.modules)
spec.loader.exec_module(m)
SOLVER_MODULES_ADDED = {
    name
    for name in set(sys.modules) - BEFORE_IMPORT
    if name.startswith(("gurobipy", "pyomo", "highspy"))
}


def row(path):
    q = path.stat()
    return {
        "root": "model-agrologistic",
        "relative_path": path.name,
        "device": str(q.st_dev),
        "inode": str(q.st_ino),
        "logical_bytes": str(q.st_size),
        "mtime_ns": str(q.st_mtime_ns),
    }


class Controls(unittest.TestCase):
    def test_path_allowlist(self):
        for root, rel in [
            ("other-project", "x"),
            ("model-agrologistic", "../outside"),
            ("model-agrologistic", "/absolute"),
            ("model-agrologistic", "secrets/gurobi.lic"),
            ("model-agrologistic", ".git/config"),
            ("model-agrologistic", ".env"),
        ]:
            with self.subTest(root=root, rel=rel), self.assertRaises(ValueError):
                m.source_path({"root": root, "relative_path": rel})

    def test_metadata_change_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "result.json"
            p.write_bytes(b"original")
            r = row(p)
            p.write_bytes(b"changed, longer")
            fd = os.open(p, os.O_RDONLY)
            with patch.object(m, "open_source", return_value=(fd, os.fstat(fd), p)):
                value, status, count = m.stable_read(r)
            self.assertIsNone(value)
            self.assertEqual(status, "changed_since_inventory")
            self.assertEqual(count, 0)

    def test_stable_hash_does_not_modify_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "result.json"
            original = b'{"status":"retained"}'
            p.write_bytes(original)
            r = row(p)
            before = p.stat()
            fd = os.open(p, os.O_RDONLY)
            with patch.object(m, "open_source", return_value=(fd, os.fstat(fd), p)):
                value, status, count = m.stable_read(r)
            self.assertEqual(status, "stable")
            self.assertEqual(value, m.hashlib.sha256(original).hexdigest())
            self.assertEqual(count, len(original))
            self.assertEqual(p.read_bytes(), original)
            self.assertEqual(p.stat().st_mtime_ns, before.st_mtime_ns)

    def test_change_during_read_is_not_a_stable_hash(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "result.json"
            p.write_bytes(b"original")
            r = row(p)
            fd = os.open(p, os.O_RDONLY)
            real_read = os.read
            changed = False

            def mutate(handle, n):
                nonlocal changed
                value = real_read(handle, n)
                if not changed:
                    p.write_bytes(b"longer replacement")
                    changed = True
                return value

            with (
                patch.object(m, "open_source", return_value=(fd, os.fstat(fd), p)),
                patch.object(m.os, "read", side_effect=mutate),
            ):
                value, status, _ = m.stable_read(r)
            self.assertIsNone(value)
            self.assertNotEqual(status, "stable")

    def test_large_source_is_not_read(self):
        fake = types.SimpleNamespace(
            st_dev=1, st_ino=2, st_size=m.MAX_SOURCE_FILE + 1, st_mtime_ns=3, st_ctime_ns=4
        )
        r = {"device": "1", "inode": "2", "logical_bytes": str(fake.st_size), "mtime_ns": "3"}
        with (
            patch.object(m, "open_source", return_value=(19, fake, Path("not-opened"))),
            patch.object(m.os, "read") as read,
            patch.object(m.os, "close") as close,
        ):
            value, status, count = m.stable_read(r)
        self.assertIsNone(value)
        self.assertEqual(status, "source_size_guard")
        self.assertEqual(count, 0)
        read.assert_not_called()
        close.assert_called_once_with(19)

    def test_directory_walk_and_file_open_use_no_follow(self):
        fake = types.SimpleNamespace(st_mode=stat.S_IFREG)
        with (
            patch.object(m.sys, "platform", "linux"),
            patch.object(m.os, "O_DIRECTORY", 0x10000, create=True),
            patch.object(m.os, "O_NONBLOCK", 0x40000, create=True),
            patch.object(m.os, "O_NOFOLLOW", 0x20000, create=True),
            patch.object(m.os, "open", side_effect=[10, 11, 12]) as op,
            patch.object(m.os, "close") as close,
            patch.object(m.os, "fstat", return_value=fake),
        ):
            fd, _, _ = m.open_source(
                {"root": "model-agrologistic", "relative_path": "data/result.json"}
            )
        self.assertEqual(fd, 12)
        self.assertTrue(all(c.args[1] & 0x20000 for c in op.call_args_list))
        self.assertEqual(op.call_args_list[1].kwargs["dir_fd"], 10)
        self.assertEqual(op.call_args_list[2].kwargs["dir_fd"], 11)
        self.assertEqual([c.args[0] for c in close.call_args_list], [10, 11])

    def test_incomplete_final_journal_is_preserved_and_not_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "readback-test"
            p.mkdir()
            f = p / "hashes.jsonl"
            raw = b'{"id":"retained"}\n{"id":"truncated"'
            f.write_bytes(raw)
            done, incomplete = m.completed_records(Path(d))
            self.assertEqual(done, {"retained"})
            self.assertEqual(incomplete, ["readback-test/hashes.jsonl"])
            self.assertEqual(f.read_bytes(), raw)

    def test_complete_journals_preserve_failed_reads_without_retry(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "readback-test"
            p.mkdir()
            (p / "hashes.jsonl").write_text('{"id":"failed","status":"unreadable"}\n')
            done, incomplete = m.completed_records(Path(d))
            self.assertEqual(done, {"failed"})
            self.assertFalse(incomplete)

    def test_only_readonly_scheduler_commands(self):
        for name in ("sbatch", "scontrol-update", "scancel", "pip", "conda", "bash"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                m.command([name])

    def test_existing_nonempty_workspace_is_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            audit = Path(d)
            out = audit / "workspace"
            out.mkdir()
            (out / "existing").write_bytes(b"original")
            args = types.SimpleNamespace(workspace=out)
            with (
                patch.object(m, "BASE", audit),
                self.assertRaisesRegex(ValueError, "preserve_existing"),
            ):
                m.prepare(args)
            self.assertEqual((out / "existing").read_bytes(), b"original")

    def test_workspace_cannot_escape_audit_parent(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            audit = p / "audit"
            audit.mkdir()
            unrelated = p / "outside"
            unrelated.mkdir()
            with patch.object(m, "BASE", audit), self.assertRaises(ValueError):
                m.workspace(unrelated)

    def test_control_path_intersection_is_component_aware(self):
        self.assertTrue(m.intersects("/audit/claim/a", "/audit/claim"))
        self.assertTrue(m.has_reference("/audit/claim/a", {"/audit/claim"}))
        self.assertFalse(m.has_reference("/audit/claim-other/a", {"/audit/claim"}))
        self.assertFalse(m.intersects("/audit/claim-other/a", "/audit/claim"))

    def test_json_encoding_failure_does_not_create_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "receipt.json"
            with self.assertRaises(ValueError):
                m.publish(p, {"unrepresentable": float("inf")})
            self.assertFalse(p.exists())

    @unittest.skipUnless(sys.platform == "linux", "POSIX kernel check runs in Linux CI")
    def test_linux_kernel_refuses_intermediate_and_final_symlinks(self):
        with tempfile.TemporaryDirectory() as d:
            parent = Path(d)
            root = parent / "model-agrologistic"
            root.mkdir()
            outside = parent / "outside"
            outside.mkdir()
            original = outside / "original.json"
            original.write_bytes(b"retained")
            (root / "folder").symlink_to(outside, target_is_directory=True)
            (root / "file.json").symlink_to(original)
            with patch.object(m, "PARENT", parent):
                for relative in ("folder/original.json", "file.json"):
                    with self.subTest(relative=relative), self.assertRaises(OSError):
                        m.open_source({"root": "model-agrologistic", "relative_path": relative})
                regular = root / "regular.json"
                regular.write_bytes(b"unchanged")
                value, status, count = m.stable_read(row(regular))
                self.assertEqual(status, "stable")
                self.assertEqual(count, 9)
                self.assertEqual(value, m.hashlib.sha256(b"unchanged").hexdigest())
            self.assertEqual(original.read_bytes(), b"retained")

    def test_module_import_does_not_load_solvers(self):
        self.assertFalse(SOLVER_MODULES_ADDED)


if __name__ == "__main__":
    unittest.main()
