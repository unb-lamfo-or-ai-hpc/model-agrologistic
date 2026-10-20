"""Real small native software integration, not NPAD/WLS operational acceptance."""

import os

from scripts import mvp2_scalar_r2 as r
from tests.test_gurobipy_transshipment import require_gurobi_available


def test_r2_selected_math_gate_really_exports_nine_zero_skip_cases(tmp_path):
    if os.environ.get("AGRO_REQUIRE_NATIVE_SOLVERS") != "1":
        require_gurobi_available()
    report = r.run_math(tmp_path / "native")
    assert report["tests"] == 9
    assert report["errors"] == report["failures"] == report["skipped"] == 0
    assert report["native_solver_limit_seconds"] <= 60
    assert report["solver_threads"] == 1
