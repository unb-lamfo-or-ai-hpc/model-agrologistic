"""Preserve certificate, unit and missing-outcome boundaries in pilot reporting."""

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_pilot_gap_and_financial_scope_match_original_certificate():
    record = json.loads(
        (ROOT / "docs/evidence/paired_pyomo_h300_gurobi_2231228_review.json").read_bytes()
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


def test_pending_companion_has_no_imputed_result_or_historical_repetition():
    text = (ROOT / "manuscript/scaling_pilot_results.qmd").read_text(encoding="utf-8")
    assert "| HiGHS / 1 / 1 | Not yet terminal | — | — | — | — | — |" in text
    assert "not an additional repetition" in text
    assert "tonne-periods" in text
    assert "not added as installed emergency capacity" in text


def test_document_hooks_require_no_external_math_runtime():
    for name in ("manuscript/_quarto.yml", "manuscript/supplement/_quarto.yml"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "html-math-method: mathml" in text
        assert "prepare_document_assets.py" in text
