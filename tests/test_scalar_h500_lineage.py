"""Real historical checkpoint/order/500-row Excel integration with public fixtures."""

import json
import sys

import pandas as pd
import pytest

from scripts import mvp2_scalar_h500_operational as m
from tests.test_scalar_h500_operational import fixture
from tests.test_scalar_r3a import SHA
from tests.test_warehouse_receipt import registry_files


def inputs(tmp_path, monkeypatch, mutation=None):
    def historical(meta, rows):
        meta["target_populations"] = list(m.r.warehouses.HISTORICAL_CHECKPOINTS)
        if mutation:
            mutation(meta, rows)

    manifest, order, msha, osha = registry_files(tmp_path, historical)
    monkeypatch.setattr(m.o, "POPULATION_SHA", msha)
    monkeypatch.setattr(m.o, "ORDER_SHA", osha)
    book = tmp_path / "nine_population_osrm_v1/warehouses_500/model_input.xlsx"
    book.parent.mkdir(parents=True)
    frame = pd.DataFrame(
        {
            "CDA": [f"E{i}" for i in range(146)] + [f"C{i}" for i in range(1, 355)],
            "Status": ["Existente"] * 146 + ["Candidato"] * 354,
        }
    )
    frame.to_excel(book, sheet_name="Warehouses", index=False)
    monkeypatch.setattr(m.c, "WORKBOOK_SHA", m.r.file_hash(book))
    files, plan = fixture()
    audit = book.with_name("osrm_materialization_audit.json")
    audit.write_bytes(files["materialization.original.json"])
    monkeypatch.setattr(m.c, "predecessor", lambda _: plan["predecessor"])
    monkeypatch.setattr(m.r.r2, "source_inventory", lambda _: json.loads(files["source.json"]))
    monkeypatch.setattr(m.r.r2, "verify_source", lambda *_: None)
    monkeypatch.setattr(m.shutil, "which", lambda _: sys.executable)
    return dict(
        workbook=book,
        population=manifest,
        order=order,
        materialization_path=audit,
        predecessor=None,
    )


def test_real_historical_four_hundred_chain_prepares_and_loads_without_rewriting(
    tmp_path, monkeypatch
):
    paths = inputs(tmp_path, monkeypatch)
    originals = {k: p.read_bytes() for k, p in paths.items() if p is not None}
    claim = tmp_path / m.CLAIM
    plan = m.prepare(claim, SHA, **paths)
    assert m.load(claim, SHA) == plan
    assert plan["expected_shape"] == m.c.SHAPE and plan["cases"][0]["solver"]["threads"] == 1
    selection = m.r.r2.read(claim / "warehouse_selection.json")
    assert "checkpoint_derivation" not in selection
    assert len(selection["members"]) == 500 and selection["members"][-1]["candidate_rank"] == 354
    assert originals == {k: p.read_bytes() for k, p in paths.items() if p is not None}
    assert not (claim / "submission_intent.json").exists()
    assert not (claim / "job.json").exists()


@pytest.mark.parametrize("kind", ["missing", "duplicate", "substitute", "role", "empty", "sheet"])
def test_real_excel_mismatch_fails_before_claim_and_submission(tmp_path, monkeypatch, kind):
    paths = inputs(tmp_path, monkeypatch)
    frame = pd.read_excel(paths["workbook"], sheet_name="Warehouses")
    if kind == "missing":
        frame = frame.iloc[:-1]
    elif kind == "duplicate":
        frame.loc[499, "CDA"] = "C353"
    elif kind == "substitute":
        frame.loc[399, "CDA"] = "C355"
    elif kind == "role":
        frame.loc[399, "Status"] = "Existente"
    elif kind == "empty":
        frame.loc[399, "CDA"] = None
    frame.to_excel(
        paths["workbook"], sheet_name="Wrong" if kind == "sheet" else "Warehouses", index=False
    )
    monkeypatch.setattr(m.c, "WORKBOOK_SHA", m.r.file_hash(paths["workbook"]))
    audit = m.r.r2.read(paths["materialization_path"])
    audit["output_workbook_sha256"] = m.c.WORKBOOK_SHA
    paths["materialization_path"].write_bytes(m.r.r2.encoded(audit))
    claim = tmp_path / m.CLAIM
    with pytest.raises(ValueError):
        m.prepare(claim, SHA, **paths)
    assert not claim.exists()


@pytest.mark.parametrize("kind", ["schema", "checkpoints", "rank", "anchor"])
def test_historical_protocol_drift_rejected(tmp_path, monkeypatch, kind):
    def mutation(meta, rows):
        if kind == "schema":
            meta["schema_version"] = 2
        elif kind == "checkpoints":
            meta["target_populations"].remove(500)
        elif kind == "rank":
            rows[499]["candidate_rank"] = "353"
        elif kind == "anchor":
            rows[399]["selection_stratum"] = "canonical_gold_anchor"

    paths = inputs(tmp_path, monkeypatch, mutation)
    claim = tmp_path / m.CLAIM
    with pytest.raises(ValueError):
        m.prepare(claim, SHA, **paths)
    assert not claim.exists()


@pytest.mark.parametrize(
    "kind", ["absent", "directory", "wrong_hash", "audit_hash", "audit_provider", "audit_fallback"]
)
def test_wrong_path_hash_or_osrm_audit_never_creates_claim(tmp_path, monkeypatch, kind):
    paths = inputs(tmp_path, monkeypatch)
    if kind == "absent":
        paths["workbook"] = tmp_path / "missing.xlsx"
    elif kind == "directory":
        paths["workbook"] = tmp_path
    elif kind == "wrong_hash":
        monkeypatch.setattr(m.c, "WORKBOOK_SHA", "0" * 64)
    else:
        audit = m.r.r2.read(paths["materialization_path"])
        if kind == "audit_hash":
            audit["output_workbook_sha256"] = "0" * 64
        elif kind == "audit_provider":
            audit["distance_provenance"]["provider"] = "haversine"
        else:
            audit["distance_provenance"]["fallback_count"] = 1
        paths["materialization_path"].write_bytes(m.r.r2.encoded(audit))
    claim = tmp_path / m.CLAIM
    with pytest.raises(ValueError):
        m.prepare(claim, SHA, **paths)
    assert not claim.exists()


def test_registered_h500_uses_strict_original_checkpoint_without_new_fields(tmp_path):
    from scripts import mvp2_warehouse_receipt as w

    args = registry_files(
        tmp_path, lambda meta, _: meta.update(target_populations=list(w.HISTORICAL_CHECKPOINTS))
    )
    old = w.h300_derivation()
    selection = w.read_policy(*args, 500)
    assert "checkpoint_derivation" not in selection
    assert len(selection["members"]) == 500 and old["reviewed_target"] == 300
    with pytest.raises(ValueError):
        w.read_policy(*args, 500, reviewed_nested_target=500)
