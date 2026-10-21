"""Prospective h500 gate: separately scoped observed memory, never an execution flag."""

import json

import pytest

from scripts import mvp2_scalar_h400_operational as m
from tests.test_scalar_h400_operational import encode, fixture, refresh_completion


@pytest.mark.parametrize(
    "raw,expected", [("1K", 1024), ("1M", 1024**2), ("1.5G", 1.5 * 1024**3), ("1T", 1024**4)]
)
def test_slurm_binary_units_distinct_from_native_decimal_bytes(raw, expected):
    assert m.rss_bytes(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "1", "nanG", "-1G", "infG", "1GiB"])
def test_unknown_rss_never_becomes_zero(raw):
    with pytest.raises(ValueError):
        m.rss_bytes(raw)


@pytest.mark.parametrize("scope", ["application", "slurm", "native"])
def test_at_limit_allowed_and_above_limit_blocks_only_h500(scope):
    files, plan = fixture()
    science = m.science_review(files, plan)
    rows = m.r.r2.accounting(files["accounting.txt"].decode(), "123")
    if scope == "application":
        science["arms"][0]["physical_diagnostics"]["peak_rss_mb"] = (
            m.c.ELIGIBILITY["os_rss_max_bytes"] / 1024**2
        )
    elif scope == "slurm":
        rows[-1]["max_rss_raw"] = "153.6G"
    else:
        prefix = "cases/" + m.c.CASE + "/products/" + m.c.CASE + "/resources/"
        files[prefix + "solver_progress.csv"] = b"solver_memory_bytes\n128000000000\n"
    assert m.h500_preconditions(files, science, rows, True)["h500_preconditions_met"]
    if scope == "application":
        science["arms"][0]["physical_diagnostics"]["peak_rss_mb"] += 1
    elif scope == "slurm":
        rows[-1]["max_rss_raw"] = "154G"
    else:
        files[prefix + "solver_progress.csv"] = b"solver_memory_bytes\n128000000001\n"
    report = m.h500_preconditions(files, science, rows, True)
    assert not report["h500_preconditions_met"] and not report["h500_execution_admitted"]
    assert science["quality_target_met"]


@pytest.mark.parametrize(
    "kind",
    [
        "missing",
        "nan",
        "infinite",
        "negative",
        "zero",
        "dropped",
        "errors",
        "rss",
        "softmem",
        "quality",
        "closure",
    ],
)
def test_missing_partial_or_failed_evidence_defers_h500(kind):
    files, plan = fixture()
    science = m.science_review(files, plan)
    rows = m.r.r2.accounting(files["accounting.txt"].decode(), "123")
    prefix = "cases/" + m.c.CASE + "/products/" + m.c.CASE + "/resources/"
    if kind in {"missing", "nan", "infinite", "negative", "zero"}:
        values = {"missing": "", "nan": "nan", "infinite": "inf", "negative": "-1", "zero": "0"}
        files[prefix + "solver_progress.csv"] = (
            "solver_memory_bytes\n" + values[kind] + "\n"
        ).encode()
    elif kind in {"dropped", "errors"}:
        telemetry = json.loads(files[prefix + "termination.json"])
        if kind == "dropped":
            telemetry["dropped_samples"]["resource"] = 1
        else:
            telemetry["inspection_errors"] = ["unavailable"]
        files[prefix + "termination.json"] = encode(telemetry)
    elif kind == "rss":
        rows[-1]["max_rss_raw"] = None
    elif kind == "softmem":
        terminal = json.loads(files["control/t1/native_terminal.json"])
        terminal["status_code"] = 17
        files["control/t1/native_terminal.json"] = encode(terminal)
    elif kind == "quality":
        science["quality_target_met"] = False
    report = m.h500_preconditions(files, science, rows, kind != "closure")
    assert not report["h500_preconditions_met"]
    assert report["h500_blockers"] and not report["h500_execution_admitted"]


def test_resource_limit_does_not_reject_original_feasibility():
    files, _ = fixture()
    prefix = "cases/" + m.c.CASE + "/products/" + m.c.CASE + "/"
    summary = json.loads(files[prefix + "run_summary.json"])
    summary["peak_rss_mb"] = 160 * 1024
    files[prefix + "run_summary.json"] = encode(summary)
    refresh_completion(files)
    plan = json.loads(files["plan.json"])
    files["control/t1/review.json"] = encode(m.science_review(files, plan)["arms"][0])
    report = m.portable_review(files)
    assert report["operational_receipts_closed"] and report["quality_target_met"]
    assert report["status"] == "h400_quality_target_met"
    assert not report["h500_preconditions_met"] and not report["h500_execution_admitted"]
