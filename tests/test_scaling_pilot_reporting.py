"""Preserve certificate, unit and missing-outcome boundaries in pilot reporting."""

import csv
import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("solver,job", [("gurobi", "2231228"), ("highs", "2231226")])
def test_pilot_gap_and_financial_scope_match_original_certificate(solver, job):
    record = json.loads(
        (ROOT / f"docs/evidence/paired_pyomo_h300_{solver}_{job}_review.json").read_bytes()
    )
    row = record["observation"]
    gap = (row["objective"] - row["bound"]) / abs(row["objective"])
    assert math.isclose(gap, row["common_gap"], rel_tol=1e-10)
    assert 0 <= gap <= row["cell"]["mip_gap_target"]
    costs = record["original_validation"]["reconstructed_costs"]
    penalties = {"unmet_demand", "emergency_reception", "emergency_static"}
    assert math.isclose(sum(costs.values()), row["objective"], rel_tol=1e-10)
    assert math.isclose(
        sum(value for name, value in costs.items() if name not in penalties),
        row["economic_cost"], rel_tol=1e-10,
    )
    text = (ROOT / "manuscript/scaling_pilot_results.qmd").read_text(encoding="utf-8")
    for value in (
        f"{100 * gap:.6f}",
        f"{row['timings']['solver_reported_runtime_seconds'] / 60:.3f}",
        f"{row['timings']['end_to_end_seconds'] / 60:.3f}",
        f"{row['resource_observation']['sampled_worker_tree_peak_bytes'] / 1024**3:.3f}",
    ):
        assert value in text


def test_pair_retains_cohort_and_dimensional_boundaries():
    text = (ROOT / "manuscript/scaling_pilot_results.qmd").read_text(encoding="utf-8")
    assert "| HiGHS / 1 / 1 | 9.289359 | 0.006879 | 401.435 |" in text
    assert "same frozen workbook" in text
    assert "within the h300 repetition grid" in text
    assert "tonne-periods" in text
    assert "not added as installed emergency capacity" in text


def test_document_hooks_require_no_external_math_runtime():
    for name in ("manuscript/_quarto.yml", "manuscript/supplement/_quarto.yml"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "html-math-method: mathml" in text
        assert "prepare_document_assets.py" in text


@pytest.mark.parametrize("solver", ["gurobi", "highs"])
def test_paired_map_retains_each_original_investment(solver):
    case = f"h300_w_sto_{solver}_t1_r1"
    definition = json.loads((ROOT / f"manuscript/maps/{case}.json").read_bytes())
    facilities = {
        f["id"]: f for n in definition["nodes"] for f in n["facilities"]
        if f["kind"] == "warehouse"
    }
    path = ROOT / f"manuscript/supplement/investments/{case}.csv"
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert set(facilities) == {row["warehouse"] for row in rows}
    for row in rows:
        facility = facilities[row["warehouse"]]
        expected = [flag for flag, key in (
            ("opened", "open"), ("expanded", "expand"), ("bulkified", "bulkify")
        ) if int(row[key]) == 1]
        assert facility["decision_flags"] == expected
        for field in ("candidate_capacity", "expansion_capacity", "bulk_capacity"):
            assert facility["investment"][field] == float(row[field + "_t"])
