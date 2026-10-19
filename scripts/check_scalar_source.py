"""Read-only active-source closure/contract check, not scientific or HPC admission."""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check():
    files = subprocess.check_output(["git", "ls-files", "src"], cwd=ROOT, text=True).splitlines()
    for name in files:
        path = ROOT / name
        expected = subprocess.check_output(["git", "show", "HEAD:" + name], cwd=ROOT)
        if path.read_bytes().replace(b"\r\n", b"\n") != expected.replace(b"\r\n", b"\n"):
            raise ValueError("Tracked scientific source differs from HEAD: " + name)
    physical = {p.relative_to(ROOT).as_posix() for p in (ROOT / "src").rglob("*.py")}
    if physical != {p for p in files if p.endswith(".py")}:
        raise ValueError("Physical Python source inventory differs from tracked source.")
    gurobi_calls = []
    scip_calls = []
    for name in (
        "optimization_gurobipy.py",
        "optimization_gurobipy_stochastic.py",
        "optimization_scip.py",
    ):
        tree = ast.parse((ROOT / "src/logic" / name).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "setObjectiveN":
                    raise ValueError("Multiobjective execution remains in native source.")
                if node.func.attr in {"setObjective", "optimize"}:
                    (scip_calls if name == "optimization_scip.py" else gurobi_calls).append(
                        node.func.attr
                    )
    for calls in (gurobi_calls, scip_calls):
        if calls.count("setObjective") != 1 or calls.count("optimize") != 1:
            raise ValueError("Expected one scalar objective and native call per backend.")
    print("SCALAR_SOURCE=VERIFIED; ONE_OBJECTIVE_AND_CALL_PER_BACKEND; NO_HPC_ADMISSION")


if __name__ == "__main__":
    check()
