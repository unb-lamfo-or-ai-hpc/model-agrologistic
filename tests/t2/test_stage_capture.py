"""Capture safety controls using disposable SQLite databases, never a solver."""

import hashlib
import importlib.util
import io
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "capture_t2", ROOT / "scripts/t2/stage_offline_reconciliation.py"
)
CAP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CAP)


class CaptureControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def source(self):
        p = self.root / "policy-pairs-v020.sqlite3"
        conn = sqlite3.connect(p)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE sample(id INTEGER PRIMARY KEY, distance REAL)")
        conn.execute("INSERT INTO sample VALUES(1,1000)")
        conn.commit()
        conn.close()
        self.assertFalse(Path(str(p) + "-wal").exists())
        return p

    def capture(self, source):
        image = self.root / "captured-main.sqlite3"
        sha = hashlib.sha256(source.read_bytes()[:100]).hexdigest()
        return image, CAP.capture_image(source, image, sha)

    def test_capture_preserves_source_and_uncertainty(self):
        source = self.source()
        raw = source.read_bytes()
        image, review = self.capture(source)
        self.assertEqual(raw, source.read_bytes())
        self.assertEqual(raw, image.read_bytes())
        self.assertFalse(review["source_engine_opened"])
        self.assertFalse(review["source_consistency_certified"])

    def test_any_source_sidecar_withholds_capture(self):
        source = self.source()
        for suffix in ("-wal", "-shm", "-journal"):
            p = Path(str(source) + suffix)
            p.write_bytes(b"observed")
            with (
                self.subTest(suffix=suffix),
                self.assertRaisesRegex(ValueError, "withheld"),
            ):
                self.capture(source)
            p.unlink()
        self.assertFalse((self.root / "captured-main.sqlite3").exists())

    def test_header_change_rejected(self):
        source = self.source()
        with self.assertRaisesRegex(ValueError, "header changed"):
            CAP.capture_image(source, self.root / "captured-main.sqlite3", "0" * 64)

    def test_second_read_change_is_not_accepted(self):
        source = self.source()
        original = CAP.T2.read_stable
        count = 0

        def changed(path, **kwargs):
            nonlocal count
            raw = original(path, **kwargs)
            count += 1
            return raw if count == 1 else raw + b"x"

        with patch.object(CAP.T2, "read_stable", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "between capture reads"):
                self.capture(source)

    def test_backup_connects_only_to_private_image_and_new_target(self):
        source = self.source()
        image, review = self.capture(source)
        target = self.root / "offline-backup.sqlite3"
        connect = sqlite3.connect
        calls = []

        def observed(path, **kwargs):
            calls.append(str(path))
            self.assertNotEqual(str(path), str(source))
            return connect(path, **kwargs)

        with patch.object(CAP.sqlite3, "connect", side_effect=observed):
            sha = CAP.offline_backup(image, review["captured_image_sha256"], target)
        self.assertIn("immutable=1", calls[0])
        self.assertTrue(calls[0].startswith(image.as_uri()))
        self.assertEqual(sha, hashlib.sha256(target.read_bytes()).hexdigest())
        db = connect(target)
        self.assertEqual(
            db.execute("SELECT distance FROM sample").fetchone(), (1000.0,)
        )
        self.assertEqual(db.execute("PRAGMA journal_mode").fetchone(), ("delete",))
        db.close()
        self.assertFalse(Path(str(source) + "-shm").exists())

    def test_existing_backup_is_preserved(self):
        source = self.source()
        image, review = self.capture(source)
        target = self.root / "offline-backup.sqlite3"
        target.write_bytes(b"preserve")
        with self.assertRaisesRegex(ValueError, "paths"):
            CAP.offline_backup(image, review["captured_image_sha256"], target)
        self.assertEqual(target.read_bytes(), b"preserve")

    def test_private_backup_deadline_is_enforced(self):
        source = self.source()
        image, review = self.capture(source)
        with self.assertRaisesRegex(ValueError, "deadline"):
            CAP.offline_backup(
                image,
                review["captured_image_sha256"],
                self.root / "offline-backup.sqlite3",
                deadline_seconds=-1,
            )

    def test_wrong_transfer_digest_stops_before_extraction(self):
        p = self.root / "inputs.tar.gz"
        p.write_bytes(b"wrong archive")
        out = self.root / "output"
        out.mkdir()
        with self.assertRaisesRegex(ValueError, "SHA"):
            CAP.stage_inputs(p, "0" * 64, out)
        self.assertEqual(list(out.iterdir()), [])

    def test_failed_capture_reports_preserve_partial_image(self):
        image = self.root / "captured-main.sqlite3"
        image.write_bytes(b"partial")
        with patch("sys.stdout", new_callable=io.StringIO):
            CAP.finalize(self.root, {"status": "verification_failed"})
        self.assertEqual(image.read_bytes(), b"partial")
        self.assertTrue(
            (self.root / "t2-offline-reconciliation-readback.tar.gz").exists()
        )

    def test_bootstrap_pins_match_the_current_reviewed_sources(self):
        helper = ROOT / "scripts/t2/reconcile_inputs.py"
        controller = ROOT / "scripts/t2/stage_offline_reconciliation.py"
        bootstrap = (ROOT / "scripts/t2/npad_t2_stage.sh").read_text()
        verify = (ROOT / "scripts/t2/npad_t2_verify.sh").read_text()
        helper_sha = hashlib.sha256(helper.read_bytes()).hexdigest()
        controller_sha = hashlib.sha256(controller.read_bytes()).hexdigest()
        self.assertIn("HELPER=" + helper_sha, bootstrap)
        self.assertIn("CONTROLLER=" + controller_sha, bootstrap)
        self.assertIn("EXPECTED=" + helper_sha, verify)
        self.assertEqual(CAP.HELPER_SHA, helper_sha)

    def test_new_capture_paths_keep_solver_free_routing(self):
        spec = importlib.util.spec_from_file_location(
            "capture_scope", ROOT / "scripts/effective_ci_scope.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        paths = [
            "scripts/t2/stage_offline_reconciliation.py",
            "scripts/t2/npad_t2_stage.sh",
            "tests/t2/test_stage_capture.py",
        ]
        self.assertTrue(module.classify(paths)["data_only"])
        self.assertFalse(module.classify(paths + ["src/logic/osrm.py"])["data_only"])

    def test_metadata_change_with_identical_bytes_is_rejected(self):
        import os

        source = self.source()
        original = CAP.T2.read_stable
        count = 0

        def touched(path, **kwargs):
            nonlocal count
            raw = original(path, **kwargs)
            count += 1
            if count == 2:
                st = source.stat()
                os.utime(source, ns=(st.st_atime_ns, st.st_mtime_ns + 1000000000))
            return raw

        with patch.object(CAP.T2, "read_stable", side_effect=touched):
            with self.assertRaisesRegex(ValueError, "metadata changed"):
                self.capture(source)


if __name__ == "__main__":
    unittest.main()
