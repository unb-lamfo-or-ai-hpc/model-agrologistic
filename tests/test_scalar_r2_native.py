"""Real small native software integration, not NPAD/WLS operational acceptance."""

import os

from scripts import mvp2_scalar_r2 as r
from tests.test_gurobipy_transshipment import require_gurobi_available
from tests.test_scalar_r2 import JOB, RAW, SHA, claim_at, fixture


def test_r2_real_math_and_products_with_mocked_transport_collect_and_replay(tmp_path, monkeypatch):
    if os.environ.get("AGRO_REQUIRE_NATIVE_SOLVERS") != "1":
        require_gurobi_available()
    files = {n: b for n, b in fixture().items() if not n.startswith("native/")}
    claim = claim_at(tmp_path, files)
    report = r.run_math(claim / "native")
    assert report["tests"] == 9
    assert report["errors"] == report["failures"] == report["skipped"] == 0
    assert report["native_solver_limit_seconds"] <= 60
    assert report["solver_threads"] == 1
    # Actual math/products, simulated scheduler/WLS receipts: no NPAD job/probe.
    monkeypatch.setattr(r, "observe", lambda *_: (r.accounting(RAW, JOB), RAW))
    receipt = r.collect(claim, SHA)
    assert receipt["status"] == "small_r2_evidence_accepted"
    replay = r.audit(claim / receipt["archive"])
    assert set(replay["closed_excel_cases"]) == {"det", "sto"}
    assert replay["independent_residual_receipts"] == "accepted"
