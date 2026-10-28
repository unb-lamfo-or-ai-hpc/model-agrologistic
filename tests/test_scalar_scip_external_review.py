"""Public controls for redacted negative SCIP evidence; no private data or solver."""

import copy
import json
from pathlib import Path

import pytest

from scripts import review_scalar_scip_h215_evidence as m

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "docs/evidence/scalar_scip_h215_w_2225638_review.json"


@pytest.fixture
def public_negative(monkeypatch):
    record = json.loads(RECORD.read_text())
    keys = (
        "classification", "quality_target_met", "has_usable_incumbent",
        "original_validation_status", "objective", "bound", "common_gap", "native_gap",
        "native_status", "timings", "economic_cost", "penalized_total", "interpretation",
        "status", "operational_receipts_closed", "operational_error_kind",
        "source_commit", "job_id", "accounting", "production_isolation_certified",
    )
    replay = {key: record[key] for key in keys}
    replay.update(m.original.closed())
    files = {}

    def put(name, value):
        files[name] = json.dumps(value, allow_nan=False).encode()

    files["plan.json"] = b'{"fixture":"public"}'
    monkeypatch.setattr(m, "PLAN", m.digest(files["plan.json"]))
    put("review.json", replay)
    put("control/sto/native_terminal.json", {
        "solution_count": 0, "status": "timelimit", "time_limit_seconds": 14400,
        "runtime_seconds": record["timings"]["solver_reported_runtime_seconds"],
    })
    put(m.PRODUCT + "independent_validation.json", {
        "status": "rejected", "failed_check_count": 41066,
        "families": {"usable_incumbent": {"failed": 1}},
        "absolute_tolerance": 1e-5, "relative_tolerance": 1e-8,
    })
    files["control/sto/scip-native.log"] = (
        b"time limit reached (0 solutions)\nSolving Nodes : 1\n"
        b"Presolving Time: 608.24\n"
        b"12708003 variables (92 bin, 0 int, 12707911 cont)"
    )
    files[m.PRODUCT + "resources/resource_timeseries.csv"] = (
        b"elapsed_seconds,process_tree_rss_bytes,inspection_seconds\n"
        b"0,100,0.01\n14415,200,14414\n"
    )
    put(m.PRODUCT + "resources/termination.json", {
        "execution_status": "time_limit", "exception_type": None,
        "inspection_errors": [], "samples": {"resource": 2}, "sampler_work_seconds": 14414.01,
    })
    put("control/sto/runtime.json", {
        "native": record["backend"], "solver_threads": 4, "affinity_logical_cpus": list(range(16)),
    })
    put(m.PRODUCT + "resources/matrix_statistics.json", {
        "observations": record["matrix_observations"],
    })
    # Deliberately misleading placeholders must never become output observations.
    put(m.PRODUCT + "run_summary.json", {
        "minimum_scenario_service_level": 1.0, "penalty_cost_share": 0.0,
        "economic_cost": 999, "domestic_service_level": 1.0,
    })
    return files, replay


def test_no_incumbent_defaults_never_become_physical_or_economic_results(public_negative):
    files, replay = public_negative
    report = m.summarize(files, replay)
    assert report["physical_diagnostics"] is None
    assert report["objective"] is None and report["economic_cost"] is None
    assert report["native_gap"] is None and report["common_gap"] is None
    assert report["operational_receipts_closed"] and not report["quality_target_met"]
    assert report["resource_observations"]["largest_resource_sample_interval_seconds"] == 14415
    assert "not demonstrated overhead" in report["resource_observations"]["qualification"]
    assert report["resource_observations"]["slurm_step_max_rss_bytes"] == 95451942912
    assert not report["native_log_observations"]["root_lp_completion_proven"]
    assert all(report[key] is False for key in m.original.closed())


@pytest.mark.parametrize("key,value", [
    ("objective", 0), ("economic_cost", 1), ("common_gap", 0), ("native_gap", 0),
    ("job_id", "9999999"), ("quality_target_met", True),
    ("has_usable_incumbent", True), ("highs_execution_admitted", True),
])
def test_forged_acceptance_or_follow_on_is_rejected(public_negative, key, value):
    files, replay = public_negative
    replay = copy.deepcopy(replay)
    replay[key] = value
    files["review.json"] = json.dumps(replay).encode()
    with pytest.raises(ValueError):
        m.summarize(files, replay)


@pytest.mark.parametrize("name,change", [
    ("control/sto/native_terminal.json", {"solution_count": 1}),
    (m.PRODUCT + "independent_validation.json", {"status": "accepted"}),
    (m.PRODUCT + "resources/termination.json", {"exception_type": "MemoryError"}),
])
def test_conflicting_original_terminal_records_are_rejected(public_negative, name, change):
    files, replay = public_negative
    value = json.loads(files[name])
    value.update(change)
    files[name] = json.dumps(value).encode()
    with pytest.raises(ValueError):
        m.summarize(files, replay)


def test_native_log_and_resource_fabrications_are_rejected(public_negative):
    files, replay = public_negative
    log = files["control/sto/scip-native.log"]
    files["control/sto/scip-native.log"] = log.replace(b"(0 solutions)", b"(1 solutions)")
    with pytest.raises(ValueError, match="Native log"):
        m.summarize(files, replay)
    files["control/sto/scip-native.log"] = log
    path = m.PRODUCT + "resources/resource_timeseries.csv"
    files[path] = files[path].replace(b"14415,200", b"nan,200")
    with pytest.raises(ValueError, match="sample time"):
        m.summarize(files, replay)


def test_original_source_snapshot_must_match_every_file(tmp_path):
    expected = {}
    for index in range(562):
        name = f"public-{index}.txt"
        raw = f"public original {index}".encode()
        (tmp_path / name).write_bytes(raw)
        expected[name] = m.digest(raw)
    files = {"source.json": json.dumps({
        "source_commit": m.SOURCE, "files": expected,
    }).encode()}
    assert m.verify_source(files, tmp_path)["trusted_original_files_matched"] == 562
    (tmp_path / "public-0.txt").write_text("tampered")
    with pytest.raises(ValueError, match="source bytes"):
        m.verify_source(files, tmp_path)


def test_redacted_original_and_manuscript_never_promote_negative_observation():
    record = json.loads(RECORD.read_text())
    assert record["members"] == 111 and record["inventory_digests_matched"] == 110
    assert record["source_inventory_verified"] and record["trusted_original_files_matched"] == 562
    assert record["archive_sha256"] == m.ARCHIVE_SHA
    assert record["original_validation_failed_checks"] == 41066
    text = json.dumps(record)
    for forbidden in ("/home/", "npad.internal", "35.0287", "license"):
        assert forbidden not in text
    status = json.loads((ROOT / "manuscript/open_source_comparison_status.json").read_text())
    assert len(status["observations"]) == 1
    assert status["observations"][0]["objective"] is None
    assert status["longer_scip"]["requested"] and not status["longer_scip"]["execution_admitted"]
