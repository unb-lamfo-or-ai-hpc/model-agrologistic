"""Separate measured scopes and preserved partials; no new frontier-admission gate."""

import json

import pytest

from scripts import mvp2_scalar_h500_operational as m
from tests.test_scalar_h500_operational import encode, fixture, refresh_completion


@pytest.mark.parametrize("raw,expected", [("1K", 1024), ("1M", 1024**2), ("1.5G", 1.5 * 1024**3)])
def test_rss_binary_units_distinct_from_native_decimal_bytes(raw, expected):
    assert m.rss_bytes(raw) == expected


@pytest.mark.parametrize(
    "kind", ["missing", "nan", "inf", "zero", "negative", "rss", "drops", "errors"]
)
def test_incomplete_resource_evidence_never_becomes_zero_or_erases_valid_quality(kind):
    files, plan = fixture()
    prefix = "cases/" + m.c.CASE + "/products/" + m.c.CASE + "/resources/"
    if kind in {"missing", "nan", "inf", "zero", "negative"}:
        value = {"missing": "", "nan": "nan", "inf": "inf", "zero": "0", "negative": "-1"}[kind]
        files[prefix + "solver_progress.csv"] = ("solver_memory_bytes\n" + value + "\n").encode()
    else:
        telemetry = json.loads(files[prefix + "termination.json"])
        if kind == "drops":
            telemetry["dropped_samples"]["resource"] = 1
        elif kind == "errors":
            telemetry["inspection_errors"] = ["public synthetic inspection failure"]
        elif kind == "rss":
            files["accounting.txt"] = files["accounting.txt"].replace(b"1G", b"")
        files[prefix + "termination.json"] = encode(telemetry)
    refresh_completion(files)
    science = m.science_review(files, plan)
    rows = m.r.r2.accounting(files["accounting.txt"].decode(), "123")
    report = m.resource_observations(files, science, rows)
    assert not report["resource_observations_complete"]
    assert report["resource_observation_blockers"]
    assert not report["additional_execution_admitted"]
    assert science["quality_target_met"]  # Missing telemetry is not a fabricated infeasible solve.


def test_h500_does_not_invent_h600_or_reapply_h400_frontier_headroom_as_quality():
    files, plan = fixture()
    science = m.science_review(files, plan)
    science["arms"][0]["physical_diagnostics"]["peak_rss_mb"] = 170 * 1024
    rows = m.r.r2.accounting(files["accounting.txt"].decode(), "123")
    report = m.resource_observations(files, science, rows)
    assert report["resource_observations_complete"]
    assert "h500_preconditions_met" not in report and "h600_execution_admitted" not in report
    assert science["quality_target_met"] and not report["additional_execution_admitted"]


@pytest.mark.parametrize("key", ["time_limit", "threads", "mip_gap", "seed"])
def test_final_spec_drift_never_relabels_another_solver_configuration(key):
    files, plan = fixture()
    plan["cases"][0]["solver"][key] = -1
    files["plan.json"] = encode(plan)
    with pytest.raises(ValueError):
        m.c.design(files)


@pytest.mark.parametrize(
    "field", ["cache", "requests", "fallback", "routes", "normalization", "input"]
)
def test_exact_historical_h500_osrm_audit_is_not_a_flexible_input(field):
    files, _ = fixture()
    audit = json.loads(files["materialization.original.json"])
    p = audit["distance_provenance"]
    if field == "cache":
        p["osrm_cache_hit_count"] += 1
    elif field == "requests":
        p["osrm_request_count"] = 1
    elif field == "fallback":
        p["fallback_count"] = 1
    elif field == "routes":
        p["route_count_by_arc_type"]["DD"] -= 1
    elif field == "normalization":
        p["osrm_negative_distance_normalization_count"] = 4
    else:
        audit["input_workbook_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        m.c.materialization(audit)


def test_h500_contract_uses_approved_envelope_and_new_size_guard_only():
    from scripts import mvp2_scalar_h400_contract as old

    assert m.c.PROFILE == old.PROFILE
    assert m.c.MAX_VARIABLES == 70000000 and old.MAX_VARIABLES == 45000000
    assert m.CLAIM != ".mvp2-scalar-h400-8h-v1"
    assert m.c.SHAPE == {"warehouses": 500, "periods": 60, "sto_scenarios": 9}


def test_h400_predecessor_rejection_cannot_be_replaced_by_a_summary(monkeypatch, tmp_path):
    from scripts import mvp2_scalar_h400_operational as old

    path = tmp_path / "public.tar.gz"
    path.write_bytes(b"not a certificate")
    monkeypatch.setattr(old, "audit", lambda *_: {"status": "h400_forensic_partial_preserved"})
    with pytest.raises(ValueError, match="Accepted original"):
        m.c.predecessor(path)


@pytest.mark.parametrize("size,accepted", [(70000000, True), (70000001, False)])
def test_size_guard_boundary_is_enforced_in_preflight_before_a_model(monkeypatch, size, accepted):
    from dataclasses import make_dataclass
    from pathlib import Path
    from types import SimpleNamespace

    from src.logic import excel_loader, experiment_runner, mathematical_contract

    files, _ = fixture()
    selection = json.loads(files["warehouse_selection.json"])
    ids = [row["warehouse_id"] for row in selection["members"]]
    data = SimpleNamespace(
        warehouses=ids,
        existing_warehouses=ids[:146],
        candidate_warehouses=ids[146:],
        metadata={"mathematical_contract": {"version": "public_guard_fixture_only"}},
        scenario_prob={str(i): 1 / 9 for i in range(9)},
    )
    estimate = make_dataclass("PublicSize", ["period_count", "scenario_count", "total_variables"])(
        60, 9, size
    )
    monkeypatch.setattr(excel_loader, "load_model_data_from_excel", lambda *_: data)
    monkeypatch.setattr(mathematical_contract, "prepare_model_data", lambda *_: data)
    monkeypatch.setattr(experiment_runner, "estimate_model_size", lambda *_: estimate)
    monkeypatch.setattr(m.r, "spec_payload", lambda *_: {"scope": "public_guard_fixture_only"})
    spec = m.c.specs(Path("never-open-private.xlsx"))[0]
    if accepted:
        _, receipt = m.r.preflight(spec, m.c.SHAPE, selection)
        assert receipt["estimate"]["total_variables"] == 70000000
    else:
        with pytest.raises(ValueError, match="Model size exceeds frozen guard"):
            m.r.preflight(spec, m.c.SHAPE, selection)


def test_missing_resource_review_defers_complete_evidence_without_faking_infeasibility():
    files, _ = fixture()
    prefix = "cases/" + m.c.CASE + "/products/" + m.c.CASE + "/resources/"
    files[prefix + "solver_progress.csv"] = b"solver_memory_bytes\n"
    refresh_completion(files)
    report = m.portable_review(files)
    assert report["status"] == "h500_resource_review_deferred"
    assert report["quality_target_met"] and report["operational_receipts_closed"]
    assert not report["resource_observations_complete"]
    assert report["arms"][0]["classification"] == "validated_feasible"
