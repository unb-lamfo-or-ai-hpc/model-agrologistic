"""Real historical checkpoint/order/400-row Excel integration with public fixtures."""

import json
import sys

import pandas as pd
import pytest

from scripts import mvp2_scalar_h400_operational as m
from tests.test_scalar_h400_operational import fixture
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
    book = tmp_path / "nine_population_osrm_v1/warehouses_400/model_input.xlsx"
    book.parent.mkdir(parents=True)
    frame = pd.DataFrame(
        {
            "CDA": [f"E{i}" for i in range(146)] + [f"C{i}" for i in range(1, 255)],
            "Status": ["Existente"] * 146 + ["Candidato"] * 254,
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
    with pytest.raises(ValueError, match="Population protocol differs"):
        m.r.warehouses.read_policy(
            paths["population"], paths["order"], m.o.POPULATION_SHA, m.o.ORDER_SHA, 400
        )
    claim = tmp_path / m.CLAIM
    plan = m.prepare(claim, SHA, **paths)
    assert m.load(claim, SHA) == plan
    assert plan["expected_shape"] == m.c.SHAPE and plan["cases"][0]["solver"]["threads"] == 1
    selection = m.r.r2.read(claim / "warehouse_selection.json")
    assert selection["checkpoint_derivation"] == m.r.warehouses.h400_derivation()
    assert len(selection["members"]) == 400 and selection["members"][-1]["candidate_rank"] == 254
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
        frame.loc[399, "CDA"] = "C253"
    elif kind == "substitute":
        frame.loc[399, "CDA"] = "C255"
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
            meta["target_populations"].append(400)
        elif kind == "rank":
            rows[399]["candidate_rank"] = "253"
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


def test_original_h300_derivation_bytes_and_strict_default_are_preserved(tmp_path):
    from scripts import mvp2_warehouse_receipt as w

    args = registry_files(
        tmp_path, lambda meta, _: meta.update(target_populations=list(w.HISTORICAL_CHECKPOINTS))
    )
    original = w.h300_derivation()
    assert (
        w.read_policy(*args, 300, reviewed_nested_target=300)["checkpoint_derivation"] == original
    )
    assert (
        w.read_policy(*args, 400, reviewed_nested_target=400)["checkpoint_derivation"]
        == w.h400_derivation()
    )
    assert original["reviewed_target"] == 300 and "154" in original["method"]
    for target, reviewed in ((400, 300), (300, 400), (500, 500), (400, True)):
        with pytest.raises(ValueError):
            w.read_policy(*args, target, reviewed_nested_target=reviewed)
    with pytest.raises(ValueError):
        w.read_policy(*args, 400)


def test_existing_h215_policy_gains_no_new_fields(tmp_path):
    args = registry_files(
        tmp_path,
        lambda meta, _: meta.update(target_populations=list(m.r.warehouses.HISTORICAL_CHECKPOINTS)),
    )
    assert "checkpoint_derivation" not in m.r.warehouses.read_policy(*args, 215)
