"""Public metadata controls; no installed scientific package is imported."""
import importlib.util
import json
import tempfile
import types
import unittest
from pathlib import Path, PurePosixPath
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "g14_shared_inventory", ROOT / "scripts/gurobi14_h215_compat.py"
)
c = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(c)


class SharedInventory(unittest.TestCase):
    def test_approved_inventory_has_all_106_versions_and_historical_provenance(self):
        expected = c.read(c.APPROVED_INVENTORY)
        self.assertEqual(len(expected["packages"]), 106)
        self.assertEqual(expected["packages"]["gurobipy"], "14.0.0")
        self.assertEqual(expected["source_archive_sha256"],
                         "a79e0872b4d5bcede1f7094a02096dba8ba917598f13d503cfc0dae8f5f50988")
        self.assertNotEqual(c.CLAIM.name, ".mvp3-gurobi14-h215-compat-v1")
        self.assertEqual(c.ENV_CLAIM.name, ".mvp3-gurobi14-environment-v1")

    def capture(self, transform=None):
        expected = c.read(c.APPROVED_INVENTORY)
        packages = {key: {"version": version, "metadata_sha256": "a" * 64}
                    for key, version in expected["packages"].items()}
        if transform:
            transform(packages)
        def read(path):
            return ({"python": "3.13.15", "python_sha256": "b" * 64}
                    if Path(path).name == "clone-after.json" else expected)
        with (
            patch.object(c, "read", side_effect=read),
            patch.object(c.platform, "python_version", return_value="3.13.15"),
            patch.object(c.sys, "prefix", expected["prefix"]),
            patch.object(c, "PYTHON", PurePosixPath(expected["prefix"]) / "bin/python"),
            patch.object(c, "digest", return_value="b" * 64),
            patch.object(c, "distribution_inventory", return_value=packages),
        ):
            return c.runtime_snapshot()

    def test_exact_approved_inventory_is_a_new_receipt_and_does_not_write_history(self):
        result = self.capture()
        self.assertEqual(result["distribution_count"], 106)
        self.assertTrue(result["original_69_package_baseline_preserved"])
        self.assertEqual(result["packages"]["gurobipy"]["version"], "14.0.0")
        self.assertIn("not all installed package bytes", result["scope"])

    def test_equal_count_with_a_different_package_is_rejected(self):
        def replace(packages):
            packages["unapproved-package"] = packages.pop("numpy")
        with self.assertRaisesRegex(c.CompatibilityError, "versions_changed"):
            self.capture(replace)

    def test_added_removed_or_changed_versions_are_rejected(self):
        def add(packages):
            packages["unapproved-package"] = {"version": "1", "metadata_sha256": "a" * 64}
        def remove(packages):
            packages.pop("numpy")
        def change(packages):
            packages["gurobipy"]["version"] = "14.0.1"
        for transform in (add, remove, change):
            with self.subTest(transform=transform.__name__):
                with self.assertRaisesRegex(c.CompatibilityError, "versions_changed"):
                    self.capture(transform)

    def test_distribution_metadata_is_read_without_imports_and_duplicates_fail(self):
        distribution = types.SimpleNamespace(
            metadata={"Name": "Some_Package"}, version="1",
            read_text=lambda name: "Name: Some_Package\nVersion: 1\n",
        )
        with patch.object(c.importlib.metadata, "distributions", return_value=[distribution]):
            result = c.distribution_inventory()
        self.assertEqual(set(result), {"some-package"})
        self.assertEqual(len(result["some-package"]["metadata_sha256"]), 64)
        with (
            patch.object(c.importlib.metadata, "distributions",
                         return_value=[distribution, distribution]),
            self.assertRaisesRegex(c.CompatibilityError, "duplicate_distribution"),
        ):
            c.distribution_inventory()

    def test_missing_distribution_metadata_fails(self):
        distribution = types.SimpleNamespace(
            metadata={"Name": "Some_Package"}, version="1", read_text=lambda name: None,
        )
        with (
            patch.object(c.importlib.metadata, "distributions", return_value=[distribution]),
            self.assertRaisesRegex(c.CompatibilityError, "missing_distribution"),
        ):
            c.distribution_inventory()

    def test_same_versions_with_metadata_drift_fail_without_overwriting_snapshot(self):
        frozen = self.capture()
        changed = json.loads(json.dumps(frozen))
        changed["packages"]["numpy"]["metadata_sha256"] = "c" * 64
        with tempfile.TemporaryDirectory() as directory:
            claim = Path(directory)
            c.publish(claim / "runtime-baseline.json", frozen)
            before = (claim / "runtime-baseline.json").read_bytes()
            with (
                patch.object(c, "CLAIM", claim),
                patch.object(c, "runtime_snapshot", return_value=changed),
                self.assertRaisesRegex(c.CompatibilityError, "shared_runtime_metadata_changed"),
            ):
                c.verify_runtime_snapshot()
            self.assertEqual((claim / "runtime-baseline.json").read_bytes(), before)

    def test_prepare_seals_new_baseline_and_load_checks_without_touching_history(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root, original, inputs = base / "source", base / "original-env", base / "inputs"
            for folder in (root, original, inputs):
                folder.mkdir()
            (root / "retained.py").write_bytes(b"# immutable source\n")
            (original / "clone-after.json").write_bytes(b'{"historical_count":69}\n')
            (inputs / "input.xlsx").write_bytes(b"hash-only fixture; not a real model")
            before = (original / "clone-after.json").read_bytes()
            claim = base / "new-v2"
            spec = types.SimpleNamespace(
                archive=base / "source.tar.gz", source_sha="f" * 40,
                archive_sha256="e" * 64, expected_license_id=2376504,
            )
            runtime = {"baseline_id": "test-shared106", "distribution_count": 106}
            with (
                patch.dict(c.os.environ, {}, clear=True),
                patch.object(c, "BASE", base), patch.object(c, "ROOT", root),
                patch.object(c, "CLAIM", claim), patch.object(c, "ENV_CLAIM", original),
                patch.object(c, "INPUT_ROOT", inputs),
                patch.object(c, "INPUTS", {"model_input.xlsx": (
                    "input.xlsx", c.digest(inputs / "input.xlsx"))}),
                patch.object(c, "source_inventory", return_value={
                    "retained.py": c.digest(root / "retained.py")}),
                patch.object(c, "environment_receipt", return_value={
                    "clone-after.json": c.digest(original / "clone-after.json")}),
                patch.object(c, "runtime_snapshot", return_value=runtime) as capture,
            ):
                report = c.prepare(spec)
                self.assertEqual(report["new_jobs"], 0)
                plan = c.load_plan(spec.source_sha)
                self.assertEqual(plan["optimization_parameters"], {"TimeLimit": 300})
                self.assertEqual(plan["runtime_baseline_sha256"],
                                 c.digest(claim / "runtime-baseline.json"))
                self.assertEqual(plan["predecessor_job_id"], "2278573")
                self.assertEqual(c.verify_runtime_snapshot(), runtime)
                capture.reset_mock()
                with self.assertRaisesRegex(c.CompatibilityError, "preserve_existing"):
                    c.prepare(spec)
                capture.assert_not_called()
                with (claim / "runtime-baseline.json").open("ab") as stream:
                    stream.write(b" ")
                with self.assertRaisesRegex(c.CompatibilityError, "runtime_baseline_receipt"):
                    c.load_plan(spec.source_sha)
            self.assertEqual((original / "clone-after.json").read_bytes(), before)

    def test_runtime_snapshot_is_checked_before_input_preparation_and_after_validation(self):
        text = (ROOT / "scripts/gurobi14_h215_compat.py").read_text()
        run = text.split("def run(", 1)[1].split("\ndef collect(", 1)[0]
        self.assertEqual(run.count("verify_runtime_snapshot()"), 2)
        self.assertLess(run.index("verify_runtime_snapshot()"), run.index("scientific_input()"))
        self.assertGreater(run.rindex("verify_runtime_snapshot()"),
                           run.index("validate_solution("))


if __name__ == "__main__":
    unittest.main()
