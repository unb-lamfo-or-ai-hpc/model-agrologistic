"""Closed h300 input/penalty/predecessor/collection qualification, no solver or Slurm."""

import io
import json
import subprocess
import tarfile
from dataclasses import asdict, replace

import pytest

from scripts import mvp2_scalar_h300 as h
from src.logic.mathematical_contract import canonical_hash
from tests.test_excel_loader import build_tiny_golden_excel
from tests.test_scalar_r3a import SHA, tiny_selection, tiny_spec


def contract():
    vector = {
        "unmet": [["C1", "P1", 90000.0]],
        "static": [["W1", 45000.0], ["W2", 45000.0]],
        "reception": [["W1", 45000.0], ["W2", 45000.0]],
    }
    return {
        "penalty_vector": vector,
        "penalty_vector_sha256": canonical_hash(vector),
        "emergency_static_unit": "stock_tonnes_at_warehouse_period",
        "emergency_reception_unit": "overflow_tonnes_in_period",
    }


def test_actual_rate_check_covers_all_rows_identifiers_and_units():
    result = h.penalty_receipt(contract(), warehouse_ids=["W1", "W2"], demand_pairs={("C1", "P1")})
    assert result["rates"] == h.RATES
    assert result["family_counts"] == {"unmet": 1, "static": 2, "reception": 2}
    assert all(result[k] is False for k in h.r.closed())


@pytest.mark.parametrize("family", list(h.RATES))
@pytest.mark.parametrize("value", [0, -1, 1e6, float("nan"), float("inf"), "45000", True])
def test_changed_effective_coefficients_rejected_even_with_new_hash(family, value):
    c = contract()
    c["penalty_vector"][family][0][-1] = value
    if isinstance(value, float) and not value < float("inf"):
        with pytest.raises(ValueError):
            canonical_hash(c["penalty_vector"])
        return
    c["penalty_vector_sha256"] = canonical_hash(c["penalty_vector"])
    with pytest.raises(ValueError):
        h.penalty_receipt(c)


@pytest.mark.parametrize("family", list(h.RATES))
@pytest.mark.parametrize("change", ["empty", "duplicate", "missing_id", "width"])
def test_empty_duplicate_missing_or_malformed_rows_rejected(family, change):
    c = contract()
    rows = c["penalty_vector"][family]
    if change == "empty":
        rows.clear()
    elif change == "duplicate":
        rows.append(rows[0][:])
    elif change == "missing_id":
        rows[0][0] = ""
    else:
        rows[0].append(0)
    c["penalty_vector_sha256"] = canonical_hash(c["penalty_vector"])
    with pytest.raises(ValueError):
        h.penalty_receipt(c)


@pytest.mark.parametrize(
    "change", ["hash", "storage_unit", "reception_unit", "warehouse", "demand"]
)
def test_penalty_hash_units_or_identifier_coverage_drift_rejected(change):
    c = contract()
    ids, pairs = ["W1", "W2"], {("C1", "P1")}
    if change == "hash":
        c["penalty_vector_sha256"] = "0" * 64
    elif change.endswith("unit"):
        key = "emergency_static_unit" if change == "storage_unit" else "emergency_reception_unit"
        c[key] = "tonnes_per_day"
    elif change == "warehouse":
        ids.append("W3")
    else:
        pairs.add(("C2", "P1"))
    with pytest.raises(ValueError):
        h.penalty_receipt(c, warehouse_ids=ids, demand_pairs=pairs)


def test_five_full_configurations_differ_only_in_name_and_threads():
    cases = h.specs("absent_private_input.xlsx")
    assert [s.solver.threads for s in cases] == list(h.ORDER)
    baseline = None
    for spec in cases:
        assert spec.model.mode == "sto" and spec.solver.time_limit == 14400
        assert spec.max_estimated_variables == h.MAX_VARIABLES > 25107544
        payload = asdict(spec)
        payload.pop("name")
        payload["solver"].pop("threads")
        if baseline is None:
            baseline = payload
        assert baseline == payload


def test_budget_retains_all_phase_windows_in_one_allocation_below_48h():
    p = h.proposal()
    assert p["five_arm_minimum_seconds"] == 96300 > 24 * 3600
    assert p["reserved_logical_cpu_hours_total"] == 720
    assert len(p["blocks"]) == 1
    assert [t for b in p["blocks"] for t in b["threads"]] == list(h.ORDER)
    for b in p["blocks"]:
        assert b["planned_seconds"] + b["reserve_seconds"] == b["slurm_wall_seconds"]
        assert b["reserve_seconds"] == 11700
        assert b["slurm_wall_seconds"] == 30 * 3600 < 48 * 3600
    assert all(p[k] is False for k in h.r.closed())


@pytest.mark.parametrize("action", ["start", "batch", "worker", "resume", "repeat", "h400"])
def test_no_execution_entry_point(action, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_k: pytest.fail("No subprocess allowed"))
    with pytest.raises(SystemExit) as exc:
        h.main([action])
    assert exc.value.code == 2


def sample_files():
    population = {
        "target_population": 300,
        "population_manifest_sha256": h.previous.POPULATION_SHA,
        "population_order_sha256": h.previous.ORDER_SHA,
        "selection_method": "deterministic nested ranking",
        "selection_seed": "frozen_seed",
        "members": [
            {
                "warehouse_id": f"W{i}",
                "population_role": "existing" if i < 146 else "candidate",
                "candidate_rank": None if i < 146 else i - 145,
                "selection_stratum": "protected_existing"
                if i < 146
                else ("canonical_gold_anchor" if i < 215 else "frozen_extension"),
            }
            for i in range(300)
        ],
    }
    source = {"source_commit": SHA, "files": {}}
    cases = []
    for s in h.specs("/private/absent/model_input.xlsx"):
        cases.append(
            {
                "name": s.name,
                "workbook": str(s.workbook),
                "workbook_sha256": h.WORKBOOK_SHA,
                "loader": asdict(s.loader),
                "model": asdict(s.model),
                "solver": asdict(s.solver),
                "max_estimated_variables": s.max_estimated_variables,
                "metadata": s.metadata,
            }
        )
    plan = {
        "schema_version": "scalar-h300-preparation-v1",
        "status": "prepared_optimization_closed",
        "source_commit": SHA,
        "source_inventory_sha256": h.r.r2.digest(h.r.r2.encoded(source)),
        "warehouse_selection_sha256": h.r.r2.digest(h.r.r2.encoded(population)),
        "predecessor": {
            "archive_sha256": h.H215_SHA,
            "source_commit": h.H215_SOURCE,
            "plan_sha256": h.H215_PLAN,
            "job_id": "2217990",
            "status": "accepted_scalar_h215_success",
            "rates": h.RATES,
            **h.r.closed(),
        },
        "expected_shape": h.SHAPE,
        "frozen_rates": h.RATES,
        "resources": h.proposal(),
        "cases": cases,
        **h.r.closed(),
    }
    return {
        "plan.json": h.r.r2.encoded(plan),
        "source.json": h.r.r2.encoded(source),
        "warehouse_selection.json": h.r.r2.encoded(population),
    }


def materialize(tmp_path):
    claim = tmp_path / h.CLAIM
    claim.mkdir()
    for n, b in sample_files().items():
        (claim / n).write_bytes(b)
    return claim


def test_portable_plan_replay_needs_no_private_workbook_or_scheduler(tmp_path, monkeypatch):
    claim = materialize(tmp_path)
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_k: pytest.fail("No subprocess allowed"))
    first = h.collect(claim)
    archive = claim / first["archive"]
    original = archive.read_bytes()
    assert h.collect(claim) == first
    assert archive.read_bytes() == original
    assert h.audit(archive, first["sha256"])["status"] == first["status"]
    assert all(first[k] is False for k in h.r.closed())
    with tarfile.open(archive) as t:
        assert sorted(t.getnames()) == [
            "inventory.json",
            "plan.json",
            "source.json",
            "warehouse_selection.json",
        ]


@pytest.mark.parametrize(
    "change",
    [
        "rate",
        "time",
        "threads",
        "loader",
        "model",
        "size",
        "order",
        "source",
        "parent",
        "population",
        "admission",
    ],
)
def test_full_plan_tampering_is_rejected(change):
    files = sample_files()
    p = json.loads(files["plan.json"])
    if change == "rate":
        p["frozen_rates"] = {**p["frozen_rates"], "unmet": 1e6}
    elif change in {"time", "threads"}:
        p["cases"][0]["solver"]["time_limit" if change == "time" else "threads"] = 99
    elif change == "loader":
        p["cases"][0]["loader"]["penalty_policy"] = "fixed"
    elif change == "model":
        p["cases"][0]["model"]["use_direct_origin_customer"] = True
    elif change == "size":
        p["cases"][0]["max_estimated_variables"] = 10**9
    elif change == "order":
        p["cases"].reverse()
    elif change == "source":
        p["source_inventory_sha256"] = "0" * 64
    elif change == "parent":
        p["predecessor"]["plan_sha256"] = "0" * 64
    elif change == "population":
        p["warehouse_selection_sha256"] = "0" * 64
    else:
        p["execution_admitted"] = True
    files["plan.json"] = h.r.r2.encoded(p)
    with pytest.raises(ValueError):
        h.review(files)


@pytest.mark.parametrize("member", ["../outside", "job.json", "/absolute", "plan.json"])
def test_archive_extra_traversal_and_duplicate_rejected(tmp_path, member):
    claim = materialize(tmp_path)
    saved = h.collect(claim)
    out = tmp_path / "bad.tar.gz"
    with tarfile.open(claim / saved["archive"]) as src, tarfile.open(out, "w:gz") as dest:
        for m in src:
            dest.addfile(m, src.extractfile(m))
        m = tarfile.TarInfo(member)
        m.size = 2
        dest.addfile(m, io.BytesIO(b"{}"))
    with pytest.raises(ValueError):
        h.audit(out, h.r.file_hash(out))


def test_collection_rejects_drift_and_oversize_without_truncation(tmp_path, monkeypatch):
    claim = materialize(tmp_path)
    monkeypatch.setattr(h, "MAX_BYTES", 1)
    with pytest.raises(ValueError, match="cap"):
        h.collect(claim)
    assert not (claim / h.ARCHIVE).exists()


def test_prepare_rejects_wrong_hash_and_consumed_claim_before_any_subprocess(tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_k: pytest.fail("No subprocess allowed"))
    claim = tmp_path / h.CLAIM
    workbook = tmp_path / "wrong.xlsx"
    workbook.write_bytes(b"wrong")
    with pytest.raises(ValueError, match="workbook hash"):
        h.prepare(claim, SHA, workbook, None, None, None)
    assert not claim.exists()
    claim.mkdir()
    with pytest.raises(ValueError, match="Fresh dedicated"):
        h.prepare(claim, SHA, workbook, None, None, None)


def test_predecessor_rejects_unrelated_bytes_before_auditor(tmp_path, monkeypatch):
    p = tmp_path / "predecessor.tar.gz"
    p.write_bytes(b"not accepted")
    monkeypatch.setattr(h.previous, "audit", lambda *_: pytest.fail("Hash must stop first"))
    with pytest.raises(ValueError, match="h215 hash"):
        h.verify_h215(p)


def test_complete_prepare_collect_audit_and_exclusive_reentry(tmp_path, monkeypatch):
    files = sample_files()
    workbook = tmp_path / "public.xlsx"
    workbook.write_bytes(b"public hash-only preparation fixture, not Excel ETL")
    monkeypatch.setattr(h, "WORKBOOK_SHA", h.r.file_hash(workbook))
    monkeypatch.setattr(
        h.r.warehouses, "read_policy", lambda *_: json.loads(files["warehouse_selection.json"])
    )
    monkeypatch.setattr(h, "verify_h215", lambda _: json.loads(files["plan.json"])["predecessor"])
    monkeypatch.setattr(h.r.r2, "source_inventory", lambda _: json.loads(files["source.json"]))
    monkeypatch.setattr(h.r.r2, "verify_source", lambda *_: None)
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_k: pytest.fail("No subprocess allowed"))
    claim = tmp_path / h.CLAIM
    result = h.prepare(claim, SHA, workbook, None, None, None)
    assert result["status"] == "prepared_optimization_closed"
    original = (claim / "plan.json").read_bytes()
    saved = h.collect(claim)
    assert h.audit(claim / saved["archive"], saved["sha256"])["thread_order"] == list(h.ORDER)
    with pytest.raises(ValueError, match="Fresh dedicated"):
        h.prepare(claim, SHA, workbook, None, None, None)
    assert (claim / "plan.json").read_bytes() == original


def test_mutated_collected_archive_is_rejected_without_replacement(tmp_path):
    claim = materialize(tmp_path)
    saved = h.collect(claim)
    archive = claim / saved["archive"]
    corrupt = archive.read_bytes() + b"mutation"
    archive.write_bytes(corrupt)
    with pytest.raises(ValueError, match="collection changed"):
        h.collect(claim)
    assert archive.read_bytes() == corrupt


@pytest.mark.parametrize("change", ["shape", "probabilities", "membership"])
def test_real_excel_negative_gates_stop_before_solver(tmp_path, monkeypatch, change):
    workbook = tmp_path / "tiny.xlsx"
    build_tiny_golden_excel(workbook)
    spec = tiny_spec(workbook, "sto")
    spec = replace(
        spec,
        loader=replace(spec.loader, scenario_generation_mode="cartesian"),
        max_estimated_variables=10000,
    )
    shape = {"warehouses": 2, "periods": 2, "sto_scenarios": 9}
    policy = tiny_selection()
    if change == "shape":
        shape["warehouses"] = 300
    elif change == "probabilities":
        spec = replace(spec, loader=replace(spec.loader, scenario_generation_mode="active_rows"))
    else:
        policy["members"][1]["warehouse_id"] = "unselected"
    monkeypatch.setattr(h, "SHAPE", shape)
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_k: pytest.fail("No solver/scheduler"))
    with pytest.raises(ValueError):
        h.preflight(spec, policy)


def test_real_public_excel_preflight_checks_coefficients_before_any_solver(tmp_path, monkeypatch):
    workbook = tmp_path / "tiny.xlsx"
    build_tiny_golden_excel(workbook)
    spec = tiny_spec(workbook, "sto")
    # Fixed tiny rates test the real loader/route/vector seam, not a claim that
    # the public fixture is the actual private h300 instance or its dynamic base.
    spec = replace(
        spec,
        loader=replace(
            spec.loader,
            scenario_generation_mode="cartesian",
            penalty_policy="fixed",
            default_unmet_demand_penalty=90000,
            default_emergency_static_penalty=45000,
            default_emergency_reception_penalty=45000,
        ),
        max_estimated_variables=10000,
    )
    monkeypatch.setattr(h, "SHAPE", {"warehouses": 2, "periods": 2, "sto_scenarios": 9})
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_k: pytest.fail("No solver/scheduler"))
    _, receipt = h.preflight(spec, tiny_selection())
    assert receipt["frozen_penalty_review"]["rates"] == h.RATES
    assert receipt["estimate"]["scenario_count"] == 9
    assert len(receipt["warehouse_selection"]["included"]) == 2
    with pytest.raises(ValueError, match="penalty drift"):
        h.preflight(
            replace(spec, loader=replace(spec.loader, default_unmet_demand_penalty=90001)),
            tiny_selection(),
        )


def test_declared_closed_wrapper_has_no_scheduler_or_solver_command():
    text = (h.ROOT / "scripts/npad_scalar_h300_prepare.sh").read_text()
    assert "Preparation only" in text
    assert "sbatch " not in text and "srun " not in text and "GRB_LICENSE_FILE=" not in text
    assert "tests/test_scalar_h300.py" in text
