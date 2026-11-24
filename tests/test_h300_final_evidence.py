"""Protect scientific acceptance and censoring in the final h300 evidence."""

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence"
REPORT = json.loads((EVIDENCE / "h300_root_block1_final_2252608_20261120.json").read_text())


def test_complete_unique_block_and_separate_unexecuted_repetitions():
    rows = REPORT["observations"]
    assert {r["task"] for r in rows} == set(range(60))
    assert len({r["case"] for r in rows}) == 60
    assert {r["repetition"] for r in rows} == {1}
    assert REPORT["unsubmitted_cells"] == 120
    assert Counter(r["outcome"] for r in rows) == {
        "validated": 33,
        "native_soft_memory_limit": 7,
        "job_memory_guard": 7,
        "time_limit_no_usable_incumbent": 9,
        "cancelled_during_run": 1,
        "cancelled_before_start": 3,
    }


def test_only_accepted_certificates_supply_agricultural_and_scalar_results():
    for row in REPORT["observations"]:
        if row["outcome"] == "validated":
            assert row["validation_status"] == "accepted"
            assert row["failed_validation_checks"] == 0
            gap = (row["objective"] - row["bound"]) / abs(row["objective"])
            assert 0 <= gap <= 0.01
            assert abs(gap - row["gap_fraction"]) < 1e-9
        else:
            assert row["objective"] is None
            assert row["economic_cost"] is None
            assert row["domestic_service"] is None
        assert row["economic_gap"] is None


def test_original_errors_and_two_memory_scopes_are_preserved():
    for row in REPORT["observations"]:
        if row["outcome"] == "native_soft_memory_limit":
            assert row["original_summary_status"] == "error"
            assert row["profile"] == "heuristics_off"
            assert row["threads"] in (8, 16)
        if row["outcome"] == "job_memory_guard":
            assert row["guard_triggered"] is True
            assert row["oom_kill_delta"] == row["failcnt_delta"] == 0
            assert row["profile"] == "norel"


def test_reviewed_front_matter_and_bibliography_remain_unchanged():
    review = ROOT / "manuscript/author-review"
    prefix = (review / "main.tex").read_text(encoding="utf-8").split(r"\section{Results}", 1)[0]
    assert hashlib.sha256(prefix.encode()).hexdigest() == (
        "397c7adea8004098f7aed4a81c209c41f4e6daf20d2503910bb0b99d50c03029"
    )
    assert hashlib.sha256((review / "references.bib").read_bytes()).hexdigest() == (
        "d4215c0fdcb0ce75d7fa8092d6b088b1e1d1f7d957689230064eee01d941daa6"
    )
