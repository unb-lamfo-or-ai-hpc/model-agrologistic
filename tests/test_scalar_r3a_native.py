"""Real tiny public native integration; not h215/NPAD operational evidence."""

import os

from scripts import mvp2_scalar_r3a as r
from tests.test_excel_loader import build_tiny_golden_excel
from tests.test_gurobipy_transshipment import require_gurobi_available
from tests.test_scalar_r3a import SHA, SHAPE, plan_for, tiny_spec


def test_real_det_sto_preflight_engine_collection_and_independent_receipts(tmp_path):
    if os.environ.get("AGRO_REQUIRE_NATIVE_SOLVERS") != "1":
        require_gurobi_available()
    workbook = tmp_path / "public_tiny.xlsx"
    build_tiny_golden_excel(workbook)
    specs = [tiny_spec(workbook, mode) for mode in ("det", "sto")]
    for spec in specs:
        spec.solver.collect_resource_diagnostics = True
    plan, inventory = plan_for([r.spec_payload(s) for s in specs])
    claim = tmp_path / r.CLAIM
    claim.mkdir()
    r.r2.write(claim / "plan.json", plan)
    r.r2.write(claim / "source.json", inventory)
    for spec in specs:
        outcome = r.run_case_software(spec, claim / "cases" / spec.name, SHAPE)
        assert outcome["summary"]["independent_validation_status"] == "accepted"
        assert not outcome["execution_admitted"]
        assert (
            claim / "cases" / spec.name / "products" / spec.name / "resources/manifest.json"
        ).is_file()
    review = r.collect(claim, SHA)
    assert review["status"] == "pair_receipts_feasible"
    assert r.audit(claim / review["archive"], review["sha256"])["status"] == review["status"]
    assert all(a["has_usable_incumbent"] for a in review["arms"])
    assert not review["h300_admitted"]
