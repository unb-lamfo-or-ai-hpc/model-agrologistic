"""Protect partial evidence and licensing boundaries in the review manuscript."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "manuscript"


def test_running_retry_is_not_a_completed_observation():
    snapshot = json.loads((MANUSCRIPT / "results_snapshot.json").read_text())
    current = next(row for row in snapshot["jobs"] if row["job"] == "2091731")
    assert current["status"] == "RUNNING"
    assert current["elapsed_seconds"] is None
    assert current["max_rss_kib"] is None
    assert current["economic_gap_fraction"] is None
    assert snapshot["pending_final_job_outcome"] is None
    assert not snapshot["frozen_cost_and_warehouse_exports_available"]


def test_mit_preserves_third_party_boundaries():
    assert (ROOT / "LICENSE").read_text().startswith("MIT License")
    assert 'license = "MIT"' in (ROOT / "pyproject.toml").read_text()
    notice = (ROOT / "LICENSING.md").read_text()
    assert "ODbL" in notice and "GPLv3" in notice
    assert "blanket relicensing" in notice


def test_review_has_real_figures_and_explicit_missing_exports():
    text = (MANUSCRIPT / "index.qmd").read_text(encoding="utf-8")
    for name in ("validation-coverage", "routing-growth", "retry-resources",
                 "incomplete-economic-gaps"):
        assert f"figures/{name}.png" in text
        assert (MANUSCRIPT / "figures" / f"{name}.png").is_file()
    assert "NR means not reported" in text
    assert "{#tbl-figure-inventory}" in text
    assert "Reserved final-retry result" in text
