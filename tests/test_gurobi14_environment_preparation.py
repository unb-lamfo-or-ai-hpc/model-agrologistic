"""Solver-free checks of the environment preparation, not Gurobi qualification."""
import ast
import contextlib
import copy
import io
import json
import re
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/npad_gurobi14_clone.sh"
BLOCKS = re.findall(r"<<'PY'\n(.*?)\nPY", SCRIPT.read_text(), re.DOTALL)


class EnvironmentPreparation(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)
        self.original = {
            "python": "3.13.15", "python_sha256": "original-python",
            "prefix": "/home/vrrcelestino/venv313",
            "executable": "/home/vrrcelestino/venv313/bin/python",
            "conda_environment": True,
            "packages": {
                "gurobipy": {"version": "13.0.3", "files_sha256": "old"},
                "numpy": {"version": "2.5.2", "files_sha256": "numpy"},
            },
        }
        self.before = copy.deepcopy(self.original)
        self.before.update(
            prefix="/home/vrrcelestino/venv313_g14",
            executable="/home/vrrcelestino/venv313_g14/bin/python",
            python_sha256="relocated-python",
        )
        self.after = copy.deepcopy(self.before)
        self.after["packages"]["gurobipy"] = {
            "version": "14.0.0", "files_sha256": "new"
        }
        self.original_after = copy.deepcopy(self.original)

    def write_receipts(self):
        (self.directory / "pip-report.json").write_text("{}")
        for name, value in (
            ("original-before.json", self.original),
            ("original-after.json", self.original_after),
            ("clone-before.json", self.before),
            ("clone-after.json", self.after),
        ):
            (self.directory / name).write_text(json.dumps(value))

    def verify(self, block=2, version=(14, 0, 0)):
        self.write_receipts()
        fake = types.ModuleType("gurobipy")
        fake.__file__ = (
            "/home/vrrcelestino/venv313_g14/lib/python3.13/"
            "site-packages/gurobipy/__init__.py"
        )
        fake.gurobi = types.SimpleNamespace(version=lambda: version)
        with (
            patch.dict(sys.modules, {"gurobipy": fake}),
            patch.object(sys, "argv", ["environment-check", str(self.directory)]),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            # Execute only the repository-owned embedded check with a fake Gurobi module.
            exec(compile(BLOCKS[block], "embedded-environment-check", "exec"), {})  # noqa: S102

    def test_three_python_blocks_parse_without_solver_import(self):
        self.assertEqual(len(BLOCKS), 3)
        for block in BLOCKS:
            tree = ast.parse(block)
            self.assertFalse(any(
                isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr in {"Env", "Model", "optimize"}
                for n in ast.walk(tree)
            ))

    def test_only_gurobi_changes_and_python_relocation_is_allowed(self):
        self.verify()
        result = json.loads((self.directory / "environment-result.json").read_text())
        self.assertEqual(result["status"], "cloned_environment_verified")
        self.assertFalse(result["license_tested"])
        self.assertFalse(result["hpc_job_submitted"])

    def test_original_changes_are_rejected(self):
        self.original_after["packages"]["numpy"]["files_sha256"] = "changed"
        with self.assertRaises(AssertionError):
            self.verify()

    def test_same_version_other_package_byte_change_is_rejected(self):
        self.after["packages"]["numpy"]["files_sha256"] = "changed"
        with self.assertRaises(AssertionError):
            self.verify()

    def test_new_distribution_is_rejected(self):
        self.after["packages"]["unexpected"] = {"version": "1", "files_sha256": "x"}
        with self.assertRaises(AssertionError):
            self.verify()

    def test_wrong_loaded_native_version_is_rejected(self):
        with self.assertRaises(AssertionError):
            self.verify(version=(13, 0, 3))

    def test_clone_version_change_is_rejected_before_install(self):
        self.before["packages"]["numpy"]["version"] = "other"
        with self.assertRaises(AssertionError):
            self.verify(block=1)


if __name__ == "__main__":
    unittest.main()
