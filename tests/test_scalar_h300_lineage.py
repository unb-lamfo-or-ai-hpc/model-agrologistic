"""Real historical-shape manifest/order/XLSX preparation; no solver or scheduler.

The identifiers are public synthetic fixtures, not private NPAD evidence. Only
external source/tool identity and predecessor replay are substituted: selection,
Excel membership, original OSRM audit, preparation, load and design replay run.
"""

import json
import sys

import pandas as pd
import pytest

from scripts import mvp2_scalar_h300_operational as m
from scripts import mvp2_warehouse_receipt as w
from tests.test_scalar_h300 import SHA, sample_files
from tests.test_scalar_h300_operational import audit_fixture
from tests.test_warehouse_receipt import registry_files


def historical_inputs(tmp_path, monkeypatch, *, manifest_change=None, row_change=None):
    def mutate(meta, rows):
        meta.update(
            target_populations=list(w.HISTORICAL_CHECKPOINTS),
            selection_seed="model-agrologistic-v020-warehouse-population-v1",
            selection_method=(
                "nested deterministic proportional strata over state, warehouse type, "
                "and static-capacity quartile"
            ),
        )
        for row in rows:
            rank = float(row["candidate_rank"]) if row["candidate_rank"] else None
            row["first_population_total"] = (
                215
                if row["population_role"] == "existing" or (rank and rank <= 69)
                else 500
                if rank
                else ""
            )
        if manifest_change:
            manifest_change(meta)
        if row_change:
            row_change(rows)

    manifest, order, msha, osha = registry_files(tmp_path, mutate)
    monkeypatch.setattr(m.o, "POPULATION_SHA", msha)
    monkeypatch.setattr(m.o, "ORDER_SHA", osha)
    workbook = tmp_path / "nine_population_osrm_v1/warehouses_300/model_input.xlsx"
    workbook.parent.mkdir(parents=True)
    frame = pd.DataFrame(
        {
            "CDA": [f"E{i}" for i in range(146)] + [f"C{i}" for i in range(1, 155)],
            "Status": ["Existente"] * 146 + ["Candidato"] * 154,
        }
    )
    frame.to_excel(workbook, sheet_name="Warehouses", index=False)
    monkeypatch.setattr(m.h, "WORKBOOK_SHA", m.r.file_hash(workbook))
    audit = workbook.with_name("osrm_materialization_audit.json")
    m.r.r2.write(audit, audit_fixture())
    files = sample_files()
    monkeypatch.setattr(m.h, "verify_h215", lambda _: json.loads(files["plan.json"])["predecessor"])
    monkeypatch.setattr(m.r.r2, "source_inventory", lambda _: json.loads(files["source.json"]))
    monkeypatch.setattr(m.r.r2, "verify_source", lambda *_: None)
    monkeypatch.setattr(m.shutil, "which", lambda _: sys.executable)
    return dict(
        workbook=workbook,
        population=manifest,
        order=order,
        materialization_path=audit,
        predecessor=None,
    )


@pytest.mark.parametrize("operational", [False, True])
def test_real_historical_chain_prepare_load_and_portable_replay(tmp_path, monkeypatch, operational):
    paths = historical_inputs(tmp_path, monkeypatch)
    originals = {k: p.read_bytes() for k, p in paths.items() if p is not None}
    # Reproduce the old failure with the *real reader*, not a mocked return value.
    with pytest.raises(ValueError, match="Population protocol differs"):
        w.read_policy(paths["population"], paths["order"], m.o.POPULATION_SHA, m.o.ORDER_SHA, 300)
    claim = tmp_path / (m.CLAIM if operational else m.h.CLAIM)
    if operational:
        plan = m.prepare(claim, SHA, **paths)
        assert m.load(claim, SHA) == plan
        files = {
            n: (claim / n).read_bytes()
            for n in ("plan.json", "source.json", "warehouse_selection.json")
        }
        assert m.design_review(files)["thread_order"] == [4, 1, 8, 2, 16]
    else:
        args = {k: v for k, v in paths.items() if k != "materialization_path"}
        m.h.prepare(claim, SHA, **args)
        collected = m.h.collect(claim)
        assert m.h.audit(claim / m.h.ARCHIVE, collected["sha256"])["thread_order"] == [
            4,
            1,
            8,
            2,
            16,
        ]
    selection = m.r.r2.read(claim / "warehouse_selection.json")
    assert selection["checkpoint_derivation"] == w.h300_derivation()
    assert selection["members"][-1]["candidate_rank"] == 154
    assert len(selection["materialized_membership"]["ordered_ids"]) == 300
    assert originals == {k: p.read_bytes() for k, p in paths.items() if p is not None}
    assert not (claim / "submission_intent.json").exists()


@pytest.mark.parametrize("target,reviewed", [(300, None), (400, 300), (500, 300), (300, True)])
def test_extension_is_explicit_h300_only(tmp_path, target, reviewed):
    args = registry_files(
        tmp_path, lambda meta, _: meta.update(target_populations=list(w.HISTORICAL_CHECKPOINTS))
    )
    with pytest.raises(ValueError):
        w.read_policy(*args, target, reviewed_nested_target=reviewed)


def test_h215_original_policy_bytes_do_not_gain_extension_fields(tmp_path):
    args = registry_files(
        tmp_path, lambda meta, _: meta.update(target_populations=list(w.HISTORICAL_CHECKPOINTS))
    )
    policy = w.read_policy(*args, 215)
    assert "checkpoint_derivation" not in policy
    assert "materialized_membership" not in policy
    assert len(policy["members"]) == 215


@pytest.mark.parametrize("kind", ["missing", "duplicate", "substitute", "role", "empty", "sheet"])
def test_real_excel_membership_mismatch_stops_before_claim_or_submission(
    tmp_path, monkeypatch, kind
):
    paths = historical_inputs(tmp_path, monkeypatch)
    frame = pd.read_excel(paths["workbook"], sheet_name="Warehouses")
    if kind == "missing":
        frame = frame.iloc[:-1]
    elif kind == "duplicate":
        frame.loc[299, "CDA"] = "C153"
    elif kind == "substitute":
        frame.loc[299, "CDA"] = "C155"
    elif kind == "role":
        frame.loc[299, "Status"] = "Existente"
    elif kind == "empty":
        frame.loc[299, "CDA"] = None
    frame.to_excel(
        paths["workbook"], sheet_name="Wrong" if kind == "sheet" else "Warehouses", index=False
    )
    monkeypatch.setattr(m.h, "WORKBOOK_SHA", m.r.file_hash(paths["workbook"]))
    paths["materialization_path"].write_bytes(m.r.r2.encoded(audit_fixture()))
    from scripts import probe_npad_gurobi_license as probe

    monkeypatch.setattr(probe, "check_file", lambda: None)
    monkeypatch.delenv("SLURM_JOB_ID", raising=False)
    claim = tmp_path / m.CLAIM
    with pytest.raises(ValueError):
        m.start(claim, SHA, True, paths, command=lambda *_: pytest.fail("No sbatch"))
    assert not claim.exists()


@pytest.mark.parametrize(
    "kind", ["manifest_hash", "order_hash", "checkpoints", "schema", "rank", "anchor"]
)
def test_population_drift_still_rejected_before_claim(tmp_path, monkeypatch, kind):
    paths = historical_inputs(
        tmp_path,
        monkeypatch,
        manifest_change=(lambda meta: meta.update(target_populations=[215, 300, 500]))
        if kind == "checkpoints"
        else (lambda meta: meta.update(schema_version=2))
        if kind == "schema"
        else None,
        row_change=(lambda rows: rows[299].update(candidate_rank="155"))
        if kind == "rank"
        else (lambda rows: rows[146].update(selection_stratum="GO|Silo|Q1"))
        if kind == "anchor"
        else None,
    )
    if kind in {"manifest_hash", "order_hash"}:
        p = paths["population" if kind == "manifest_hash" else "order"]
        p.write_bytes(p.read_bytes() + b" ")
    claim = tmp_path / m.CLAIM
    with pytest.raises(ValueError):
        m.prepare(claim, SHA, **paths)
    assert not claim.exists()


@pytest.mark.parametrize("kind", ["derivation", "workbook", "ids"])
def test_rehashed_portable_derivation_tampering_is_rejected(kind):
    files = sample_files()
    policy = json.loads(files["warehouse_selection.json"])
    if kind == "derivation":
        policy["checkpoint_derivation"]["candidate_rank_changed"] = True
    elif kind == "workbook":
        policy["materialized_membership"]["workbook_sha256"] = "0" * 64
    else:
        policy["materialized_membership"]["ordered_ids"][-1] = "substitution"
    files["warehouse_selection.json"] = m.r.r2.encoded(policy)
    plan = json.loads(files["plan.json"])
    plan["warehouse_selection_sha256"] = m.r.r2.digest(files["warehouse_selection.json"])
    files["plan.json"] = m.r.r2.encoded(plan)
    with pytest.raises(ValueError, match="checkpoint/materialized"):
        m.h.review(files)


def test_ordered_excel_membership_is_not_confused_with_rank_order(tmp_path, monkeypatch):
    paths = historical_inputs(tmp_path, monkeypatch)
    frame = pd.read_excel(paths["workbook"], sheet_name="Warehouses").iloc[::-1]
    frame.to_excel(paths["workbook"], sheet_name="Warehouses", index=False)
    selected = m.h.read_selection(paths["workbook"], paths["population"], paths["order"])
    assert selected["materialized_membership"]["ordered_ids"][0] == "C154"
    assert selected["members"][0]["warehouse_id"] == "E0"


def test_existing_claim_reentry_never_recomputes_population_or_resubmits(tmp_path, monkeypatch):
    claim = tmp_path / m.CLAIM
    claim.mkdir()
    (claim / "preserved").write_bytes(b"historical")
    monkeypatch.setattr(m, "load", lambda *_: {})
    monkeypatch.setattr(m.o, "job_receipt", lambda *_: {"job_id": "old"})
    monkeypatch.setattr(m, "prepare", lambda *_a, **_k: pytest.fail("No second preparation"))
    monkeypatch.delenv("SLURM_JOB_ID", raising=False)
    assert (
        m.start(claim, SHA, True, {}, command=lambda *_: pytest.fail("No sbatch"))["status"]
        == "existing_claim_collect_only"
    )
    assert (claim / "preserved").read_bytes() == b"historical"


def test_wrappers_include_real_lineage_regression():
    for name in ("npad_scalar_h300_30h.sh", "npad_scalar_h300_prepare.sh"):
        assert "tests/test_scalar_h300_lineage.py" in (m.ROOT / "scripts" / name).read_text()
