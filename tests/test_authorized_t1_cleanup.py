"""File-custody controls: temporary directories only, no solver or NPAD calls."""

import hashlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = (
    Path(__file__).resolve().parents[1] / "scripts" / "t1" / "authorized_t1_cleanup.py"
)
if not SCRIPT.is_file():
    SCRIPT = Path(__file__).with_name("authorized_t1_cleanup.py")
s = importlib.util.spec_from_file_location("clean", SCRIPT)
m = importlib.util.module_from_spec(s)
s.loader.exec_module(m)


def row(path, root, action="archive"):
    st = path.stat()
    return {
        "id": path.relative_to(root).as_posix(),
        "device": str(st.st_dev),
        "inode": str(st.st_ino),
        "logical_bytes": str(st.st_size),
        "mtime_ns": str(st.st_mtime_ns),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "action": action,
        "keeper": "",
    }


class Controls(unittest.TestCase):
    def test_reject_escape_credentials_environment(self):
        for x in (
            "../file",
            "/home/file",
            "other/file",
            "model-agrologistic/../x",
            "model-agrologistic/secrets/gurobi.lic",
            "model-agrologistic/venv313_g14/lib/x",
            "model-agrologistic/.git/config",
            "model-agrologistic/.env",
            "model-agrologistic/a//b",
        ):
            with self.subTest(x=x), self.assertRaises(ValueError):
                m.path_parts(x)

    def test_cache_boundaries(self):
        self.assertTrue(m.cache_path("model-agrologistic/.ruff_cache/1/x"))
        self.assertTrue(m.cache_path("model-agrologistic/src/__pycache__/x.pyc"))
        self.assertFalse(m.cache_path("model-agrologistic/data/cache.sqlite3"))

    def test_scientific_duplicates_protected(self):
        for x in (
            "model-agrologistic/data/results.csv",
            "model-agrologistic-hygiene-audit/.mvp2-claim/source/a.py",
            "model-agrologistic-hygiene-audit/s2-case-driver-123/data/x.py",
            "model-agrologistic-hygiene-audit/s2-case-driver-123/results/flows.csv",
            "model-agrologistic-hygiene-audit/s2-case-driver-123/job.json",
            "osrm-agrologistic/source.tar.gz",
        ):
            with self.subTest(x=x):
                self.assertFalse(m.disposable_path(x))
        self.assertTrue(
            m.disposable_path(
                "model-agrologistic-hygiene-audit/h300-root-cpu-source-abc/scripts/x.py"
            )
        )

    @unittest.skipUnless(os.name == "posix", "Linux no-follow check in CI")
    def test_no_follow_source_intermediate_final(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            r = root / "model-agrologistic"
            r.mkdir()
            (root / "outside").write_bytes(b"retained")
            (r / "link").symlink_to(root / "outside")
            (r / "dir").symlink_to(root, target_is_directory=True)
            with patch.object(m, "PARENT", root):
                for name in (
                    "model-agrologistic/link",
                    "model-agrologistic/dir/outside",
                ):
                    with self.subTest(name=name), self.assertRaises(OSError):
                        m.opened(name)
            self.assertEqual((root / "outside").read_bytes(), b"retained")

    @unittest.skipUnless(os.name == "posix", "Uses POSIX directory descriptors")
    def test_backup_member_hash_and_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            r = root / "model-agrologistic"
            r.mkdir()
            f = r / "old.txt"
            f.write_bytes(b"historical bytes\n" * 100)
            rr = row(f, root)
            archive = root / "backup.tar.gz"
            with patch.object(m, "PARENT", root):
                m.make_archive(archive, [rr])
                self.assertEqual(m.verify_archive(archive, [rr]), {rr["id"]})
            import tarfile

            with tarfile.open(archive) as t:
                self.assertEqual(t.extractfile(rr["id"]).read(), f.read_bytes())
            self.assertEqual(f.read_bytes(), b"historical bytes\n" * 100)

    @unittest.skipUnless(os.name == "posix", "Uses POSIX directory descriptors")
    def test_changed_source_never_unlinked(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            r = root / "model-agrologistic"
            r.mkdir()
            f = r / "old.txt"
            f.write_bytes(b"old")
            rr = row(f, root)
            f.write_bytes(b"new longer")
            with patch.object(m, "PARENT", root), self.assertRaises(ValueError):
                m.remove_one(rr, None, io.StringIO(), "backup")
            self.assertTrue(f.exists())

    @unittest.skipUnless(os.name == "posix", "Uses POSIX directory descriptors")
    def test_keeper_changed_target_retained(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            r = root / "model-agrologistic"
            r.mkdir()
            f = r / "copy"
            k = r / "keeper"
            f.write_bytes(b"same")
            k.write_bytes(b"same")
            rr, kk = row(f, root), row(k, root)
            k.write_bytes(b"changed")
            with patch.object(m, "PARENT", root), self.assertRaises(ValueError):
                m.remove_one(rr, kk, io.StringIO(), "backup")
            self.assertTrue(f.exists())

    @unittest.skipUnless(os.name == "posix", "Uses POSIX directory descriptors")
    def test_unlink_is_one_file_and_preserves_keeper(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            r = root / "model-agrologistic"
            r.mkdir()
            f = r / "copy"
            k = r / "keeper"
            f.write_bytes(b"same")
            k.write_bytes(b"same")
            rr, kk = row(f, root), row(k, root)
            with (
                (root / "actions").open("w") as journal,
                patch.object(m, "PARENT", root),
            ):
                m.remove_one(rr, kk, journal, "verified-sha")
            self.assertFalse(f.exists())
            self.assertEqual(k.read_bytes(), b"same")
            self.assertTrue(r.exists())
            actions = [
                json.loads(x) for x in (root / "actions").read_text().splitlines()
            ]
            self.assertEqual(
                [x["status"] for x in actions], ["unlink_intent", "unlinked"]
            )

    @unittest.skipUnless(os.name == "posix", "Uses POSIX directory descriptors")
    def test_modified_archive_fails_independent_member_check(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            r = root / "model-agrologistic"
            r.mkdir()
            f = r / "old.txt"
            f.write_bytes(b"retained")
            rr = row(f, root)
            archive = root / "backup.tar.gz"
            with patch.object(m, "PARENT", root):
                m.make_archive(archive, [rr])
                rr["sha256"] = "0" * 64
                with self.assertRaises(ValueError):
                    m.verify_archive(archive, [rr])
            self.assertTrue(f.exists())

    def test_scheduler_nonempty_refused_without_mutation(self):
        from types import SimpleNamespace

        with (
            patch.object(m.os, "getuid", return_value=1271, create=True),
            patch.object(
                m.subprocess,
                "run",
                return_value=SimpleNamespace(returncode=0, stdout="123|RUNNING\n"),
            ) as cmd,
        ):
            with self.assertRaises(ValueError):
                m.queue_empty()
            self.assertEqual(cmd.call_args.args[0][0], "squeue")

    def test_reference_components(self):
        self.assertTrue(
            m.referenced(
                "model-agrologistic/data/x",
                [(m.PARENT / "model-agrologistic/data").as_posix()],
            )
        )
        self.assertFalse(
            m.referenced(
                "model-agrologistic/database/x",
                [(m.PARENT / "model-agrologistic/data").as_posix()],
            )
        )

    def test_empty_and_root_never_block_all_targets(self):
        for value in ("", "/", "pipe:[123]", "anon_inode:inotify", None):
            with self.subTest(value=value):
                self.assertFalse(
                    m.referenced("model-agrologistic/.ruff_cache/x", [value])
                )

    def test_canonical_reference_keeps_root_and_rejects_ambiguous_paths(self):
        self.assertEqual(m.canonical_reference("/"), "/")
        self.assertIsNone(m.canonical_reference(""))
        self.assertIsNone(m.canonical_reference("//host/path"))
        self.assertIsNone(m.canonical_reference("/a/../b"))
        self.assertEqual(m.canonical_reference("/a/b/"), "/a/b")

    def test_broad_process_directories_remain_typed_and_nonblocking(self):
        for value in (
            "/",
            m.PARENT.as_posix(),
            (m.PARENT / "model-agrologistic").as_posix(),
        ):
            for kind in ("proc_cwd", "proc_fd"):
                r = m.process_reference(kind, 123, value, "directory")
                self.assertEqual(r["path"], value)
                self.assertEqual(r["pid"], "123")
                self.assertEqual(r["kind"], kind)
                self.assertEqual(r["scope"], "broad_directory")
                self.assertFalse(r["blocks_target_prefix"])

    def test_specific_open_target_still_blocks(self):
        value = (m.PARENT / "model-agrologistic/.ruff_cache/x").as_posix()
        r = m.process_reference("proc_fd", 123, value, "file")
        self.assertTrue(r["blocks_target_prefix"])
        self.assertTrue(m.referenced("model-agrologistic/.ruff_cache/x", [r["path"]]))

    def test_specific_working_directory_still_blocks(self):
        value = (m.PARENT / "model-agrologistic/scripts/work").as_posix()
        r = m.process_reference("proc_cwd", 123, value, "directory")
        self.assertTrue(
            m.referenced("model-agrologistic/scripts/work/x.py", [r["path"]])
        )

    def test_nonfilesystem_and_outside_process_refs_not_admitted(self):
        for value in (
            "socket:[12]",
            "anon_inode:inotify",
            "/usr/bin/bash",
            "/dev/null",
        ):
            r = m.process_reference("proc_fd", 123, value, "other")
            self.assertFalse(r["blocks_target_prefix"])

    def test_outcome_distinguishes_backup_only_and_partial_cleanup(self):
        self.assertEqual(
            m.cleanup_outcome(
                {"cache_unlinked": 0, "duplicate_unlinked": 0, "retained": 8449}
            ),
            "backup_verified_cleanup_withheld",
        )
        self.assertEqual(
            m.cleanup_outcome(
                {"cache_unlinked": 1, "duplicate_unlinked": 0, "retained": 8448}
            ),
            "backup_verified_cleanup_partial",
        )
        self.assertEqual(
            m.cleanup_outcome(
                {"cache_unlinked": 338, "duplicate_unlinked": 8111, "retained": 0}
            ),
            "bounded_cleanup_completed",
        )


if __name__ == "__main__":
    unittest.main()
