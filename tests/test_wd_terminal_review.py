"""Read-only terminal evidence and review-publication consistency; no optimizer."""
import copy
import json
from pathlib import Path

import pytest

from scripts import build_wd_manuscript as b

ROOT = Path(__file__).resolve().parents[1]


def record():
    return json.loads((ROOT / b.RECEIPT).read_bytes())


def test_original_terminal_quality_and_comparison_intervals():
    r = record()
    for mode in ("det", "sto"):
        w, d = r["records"]["W"][mode], r["records"]["D"][mode]
        assert 0 <= d["common_gap"] <= 0.01
        assert d["objective"] < w["bound"]
        lo, hi = r["comparisons"][mode]["exact_penalized_optimum_reduction_percent_interval"]
        assert lo == pytest.approx(100 * (1 - d["objective"] / w["bound"]))
        assert hi == pytest.approx(100 * (1 - d["bound"] / w["objective"]))
        assert 0 < lo <= hi < 100
        assert d["validation_absolute_tolerance"] == 1e-5
        assert d["validation_relative_tolerance"] == 1e-8
        assert w["warehouse_selection_sha256"] == d["warehouse_selection_sha256"]
        assert w["penalty_vector_sha256"] == d["penalty_vector_sha256"]
        physical_d = d["diagnostics"]["physical_diagnostics"]
        physical_w = w["diagnostics"]["physical_diagnostics"]
        assert physical_d["domestic_service_level"] < physical_w["domestic_service_level"]
    assert not r["remaining_experiment_required_for_this_bounded_W_D_phase"]
    assert not r["repeats_admitted"] and not r["automatic_follow_on_allowed"]


def test_frozen_wd_table_and_interpretation():
    text = b.results(record())
    assert (ROOT / "manuscript/wd_results.qmd").read_text(encoding="utf-8") == text
    for phrase in (
        "service falls", "shortage increases", "not statistical confidence",
        "historical control", "not a fresh private-input", "no-slack", "S6-B remain",
    ):
        assert phrase in text
    article = (ROOT / "manuscript/index.qmd").read_text(encoding="utf-8")
    assert "{{< include wd_results.qmd >}}" in article


def test_rejected_original_is_not_publishable_as_accepted():
    r = copy.deepcopy(record())
    r["records"]["D"]["sto"]["common_gap"] = 0.02
    with pytest.raises(AssertionError):
        b.results(r)


def test_pages_build_includes_current_supplement_dependencies():
    text = (ROOT / ".github/workflows/manuscript-pages.yml").read_text()
    for required in (
        "--publication", "publish_reviewed_snapshot", "refs/heads/main", "pdfpages",
        "eso-pic", "librsvg2-bin", "pip install", "build_wd_manuscript --check",
        "build_s6a_assets", "--rendered", "published-s6a-review-package",
    ):
        assert required in text
    assert "default: false" in text


def test_main_ancestry_gate_is_substantive_not_fabricated_status():
    text = (ROOT / ".github/workflows/branch-sync.yml").read_text()
    assert "check-branch:" in text
    assert "git merge-base --is-ancestor origin/main HEAD" in text
    assert 'test "$HEAD_BRANCH" = develop' in text
    assert "persist-credentials: false" in text
