"""Local file/Slurm-text controls only; no solver or scheduler execution."""

import contextlib
import hashlib
import importlib.util
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/collect_h300_mvp2_closeout.py"
SPEC = importlib.util.spec_from_file_location("closeout", SCRIPT)
COLLECTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COLLECTOR)


class CloseoutControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.claim = self.base / ".mvp2-h300-gurobi-root-cpu-v2"
        self.claim.mkdir()
        rows = [
            {"id": f"cell-{i}", "repetition": i // 60 + 1,
             "options": {"Method": 1}, "profile": "standard", "threads": 1}
            for i in range(180)
        ]
        plan = json.dumps({"source": COLLECTOR.SOURCE, "rows": rows}).encode()
        (self.claim / "plan.json").write_bytes(plan)
        self.plan_hash = hashlib.sha256(plan).hexdigest()
        (self.claim / "block-1.json").write_text('{"array_job":"2252608"}')
        vectors = self.claim / "cell-0/case/products/cell-0/flows.csv"
        vectors.parent.mkdir(parents=True)
        vectors.write_bytes(b"origin,destination,tonnes\na,b,7\n")
        self.originals = {
            p.relative_to(self.claim).as_posix(): p.read_bytes()
            for p in self.claim.rglob("*") if p.is_file()
        }
        failures = {6, 17, 19, 21, 24, 44, 54}
        self.accounting = "".join(
            f"2252608_{i}|{3000000+i}|"
            f"{'CANCELLED by 1271' if i >= 56 else 'FAILED' if i in failures else 'COMPLETED'}|"
            f"{'0:15' if i >= 56 else '1:0' if i in failures else '0:0'}|123|1K|64|192G|node\n"
            for i in range(60)
        )

    def run_report(self, accounting=None):
        output = io.StringIO()
        with patch.object(COLLECTOR, "PLAN_SHA", self.plan_hash), \
             patch.object(COLLECTOR.shutil, "disk_usage", return_value=SimpleNamespace(free=100 * 1024**3)), \
             patch.object(COLLECTOR.subprocess, "check_output", return_value=accounting or self.accounting) as command, \
             contextlib.redirect_stdout(output):
            COLLECTOR.report(self.base)
        self.assertEqual(command.call_count, 1)
        self.assertEqual(command.call_args.args[0][:3], ["sacct", "-j", "2252608"])
        return output.getvalue()

    def test_full_snapshot_includes_vectors_and_retains_all_source_bytes(self):
        self.run_report()
        bundle = next(self.base.glob("h300-2252608-closeout-*/*.tar.gz"))
        sidecar = bundle.with_suffix(".gz.sha256").read_text().split()[0]
        self.assertEqual(sidecar, hashlib.sha256(bundle.read_bytes()).hexdigest())
        with tarfile.open(bundle) as archive:
            manifest = json.load(archive.extractfile("inventory.json"))
            self.assertEqual(manifest["terminal_tasks"], 60)
            self.assertEqual(manifest["original_files"], len(self.originals))
            for name, digest in manifest["files_sha256"].items():
                self.assertEqual(hashlib.sha256(archive.extractfile(name).read()).hexdigest(), digest)
            self.assertIn("claim/cell-0/case/products/cell-0/flows.csv", archive.getnames())
            for name, original in self.originals.items():
                self.assertEqual(archive.extractfile("claim/" + name).read(), original)
                self.assertEqual((self.claim / name).read_bytes(), original)

    def test_running_task_blocks_collection_before_any_output_directory(self):
        accounting = self.accounting.replace("CANCELLED by 1271", "RUNNING", 1)
        with self.assertRaisesRegex(SystemExit, "ativas"):
            self.run_report(accounting)
        self.assertFalse(list(self.base.glob("h300-2252608-closeout-*")))

    def test_missing_terminal_task_blocks_collection(self):
        with self.assertRaisesRegex(SystemExit, "ativas"):
            self.run_report("\n".join(self.accounting.splitlines()[:-1]))
        self.assertFalse(list(self.base.glob("h300-2252608-closeout-*")))

    def test_duplicate_task_is_rejected(self):
        with self.assertRaisesRegex(SystemExit, "repetido"):
            self.run_report(self.accounting + self.accounting.splitlines()[0] + "\n")

    def test_plan_drift_is_rejected_before_scheduler_query(self):
        (self.claim / "plan.json").write_text("{}")
        with patch.object(COLLECTOR.subprocess, "check_output") as command, \
             self.assertRaisesRegex(SystemExit, "Identidade"):
            COLLECTOR.report(self.base)
        command.assert_not_called()


if __name__ == "__main__":
    unittest.main()
