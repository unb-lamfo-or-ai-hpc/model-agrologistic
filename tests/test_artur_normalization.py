import json
from pathlib import Path

import pandas as pd
import pytest

from src.logic.artur_benchmark import AssetIntegrityError
from src.logic.artur_instance import (
    ArturInstanceBundle,
    ArturInstanceSpec,
    persist_artur_instance,
)
from src.logic.artur_normalization import (
    load_persisted_artur_instance,
    normalize_artur_instance,
    persist_normalized_artur_instance,
)


def _persist_duplicate_bundle(tmp_path: Path) -> Path:
    spec = ArturInstanceSpec("artur_normalization_test", 1, 1, 1, 1)
    supply = pd.DataFrame(
        {
            "Produto": ["Corn", "Corn"],
            "Cidade": ["Origin", "Origin"],
            "Latitude": [-10.0, -10.0],
            "Longitude": [-50.0, -50.0],
            "Data": ["2025-01", "2025-01"],
            "Peso (ton)": [4.0, 6.0],
        }
    )
    demand = pd.DataFrame(
        {
            "Produto": ["Corn"] * 4,
            "Cidade": ["Customer"] * 4,
            "Latitude": [-11.0] * 4,
            "Longitude": [-51.0] * 4,
            "Data": ["2025-01"] * 4,
            "Peso (ton)": [3.0, 5.0, "∞", None],
        }
    )
    warehouses = pd.DataFrame(
        {
            "CDA": ["W1"],
            "Status": ["Existing"],
            "Latitude": [-12.0],
            "Longitude": [-52.0],
        }
    )
    distances = pd.DataFrame(
        {
            "arc_type": ["OD"],
            "origin": ["Origin"],
            "destination": ["W1"],
            "distance_km": [100.0],
        }
    )
    bundle = ArturInstanceBundle(
        spec=spec,
        supply=supply,
        demand=demand,
        warehouses=warehouses,
        distances=distances,
        metadata={
            "schema_version": 1,
            "name": spec.name,
            "source_commit_sha": "f" * 40,
            "warnings": [],
        },
    )
    return persist_artur_instance(bundle, tmp_path)


def test_normalization_conserves_tonnage_and_audits_duplicate_removal(tmp_path: Path):
    raw_dir = _persist_duplicate_bundle(tmp_path)
    source = load_persisted_artur_instance(raw_dir)

    normalized = normalize_artur_instance(source)

    assert len(normalized.supply) == 1
    assert normalized.supply.iloc[0]["Peso (ton)"] == pytest.approx(10.0)
    assert len(normalized.demand) == 2
    domestic = normalized.demand[normalized.demand["Tipo_Demanda"] == "DOMESTICA"]
    export = normalized.demand[normalized.demand["Tipo_Demanda"] == "EXPORTACAO"]
    assert domestic.iloc[0]["Peso (ton)"] == pytest.approx(8.0)
    assert export.iloc[0]["Regra_Limite"] == "AUTO_OFERTA_TOTAL_PRODUTO_PERIODO"
    assert pd.isna(export.iloc[0]["Peso (ton)"])
    assert all(normalized.audit["conservation_checks"].values())

    normalized_dir = persist_normalized_artur_instance(normalized)
    audit = json.loads(
        (normalized_dir / "transformation_audit.json").read_text(encoding="utf-8")
    )
    assert audit["normalization_policy"] == "bounded_reproduction_v1"
    assert audit["normalized_table_files"]["supply.csv"]["rows"] == 1
    assert (normalized_dir / "transformation_audit.csv").is_file()


def test_normalization_rejects_tampered_raw_evidence(tmp_path: Path):
    raw_dir = _persist_duplicate_bundle(tmp_path)
    with (raw_dir / "supply.csv").open("a", encoding="utf-8") as handle:
        handle.write("tampered\n")

    with pytest.raises(AssetIntegrityError, match="Raw instance integrity check failed"):
        load_persisted_artur_instance(raw_dir)


def test_normalization_rejects_conflicting_coordinates(tmp_path: Path):
    raw_dir = _persist_duplicate_bundle(tmp_path)
    source = load_persisted_artur_instance(raw_dir)
    source.supply.loc[1, "Latitude"] = -20.0

    with pytest.raises(ValueError, match="conflicting Latitude"):
        normalize_artur_instance(source)

