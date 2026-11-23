"""Temporary report/proc metadata controls, without source pruning or solvers."""

import hashlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "t1"
    / "inspect_t1_cleanup_retention.py"
)
if not SCRIPT.is_file():
    SCRIPT = Path(__file__).with_name("inspect_t1_cleanup_retention.py")
spec = importlib.util.spec_from_file_location("probe", SCRIPT)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class Controls(unittest.TestCase):
    def test_non_path_and_root_counterfactual_no_longer_match(self):
        self.assertFalse(
            p.prefix_matches(
                "model-agrologistic/.ruff_cache/x", ["", "/", "pipe:[123]"]
            )
        )
        self.assertTrue(
            p.prefix_matches(
                "model-agrologistic/data/x",
                [(p.m.PARENT / "model-agrologistic/data").as_posix()],
            )
        )

    def test_proc_pid_is_validated_before_filesystem_access(self):
        with patch.object(Path, "stat") as stat, self.assertRaises(ValueError):
            p.process_metadata("../123")
        stat.assert_not_called()

    def test_empty_historical_control_is_reported_without_content_edit(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "result.json"
            f.write_bytes(b"")
            with patch.object(p.m, "opened", side_effect=lambda name: f.open("rb")):
                result = p.control_metadata({"id": "model-agrologistic/result.json"})
            self.assertEqual(
                result["current_status"], "empty_original_preserved_no_encoded_paths"
            )
            self.assertEqual(result["sha256"], hashlib.sha256(b"").hexdigest())
            self.assertEqual(f.read_bytes(), b"")

    def test_invalid_nonempty_control_is_not_silently_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "result.json"
            f.write_bytes(b"broken")
            with patch.object(p.m, "opened", side_effect=lambda name: f.open("rb")):
                result = p.control_metadata({"id": "model-agrologistic/result.json"})
            self.assertEqual(
                result["current_status"], "nonempty_invalid_json_preserved"
            )
            self.assertEqual(f.read_bytes(), b"broken")

    def test_changed_control_is_retained_as_read_error(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "result.json"
            f.write_bytes(b"{}")
            with (
                patch.object(p.m, "opened", side_effect=lambda name: f.open("rb")),
                patch.object(p.m, "identity", side_effect=[(1, 2, 3, 4), (1, 2, 4, 5)]),
            ):
                result = p.control_metadata({"id": "model-agrologistic/result.json"})
            self.assertEqual(result["current_status"], "read_error_preserved")

    def test_report_fixture_verifies_ledger_and_rejects_corruption(self):
        import tarfile

        payload = b'{"status":"retained"}'
        name = "actions.jsonl"
        ledger = (hashlib.sha256(payload).hexdigest() + "  " + name + "\n").encode()
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as t:
            for n, data in [(name, payload), ("REPORT_SHA256SUMS", ledger)]:
                info = tarfile.TarInfo(n)
                info.size = len(data)
                t.addfile(info, io.BytesIO(data))
        raw = buf.getvalue()
        with (
            patch.object(p, "REPORT_SHA", hashlib.sha256(raw).hexdigest()),
            patch.object(p.m, "opened", return_value=io.BytesIO(raw)),
        ):
            files, _ = p.read_report(p.m.PARENT / "model-agrologistic/report.tar.gz")
        self.assertEqual(files[name], payload)
        with (
            patch.object(p, "REPORT_SHA", "0" * 64),
            patch.object(p.m, "opened", return_value=io.BytesIO(raw)),
            self.assertRaises(ValueError),
        ):
            p.read_report(p.m.PARENT / "model-agrologistic/report.tar.gz")


if __name__ == "__main__":
    unittest.main()
