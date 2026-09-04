import hashlib
from pathlib import Path

import pandas as pd
import pytest

from src.logic.artur_benchmark import (
    AssetIntegrityError,
    AssetSpec,
    build_artur_gold_reconciliation,
    git_blob_sha,
    iter_asset_specs,
    materialize_artur_assets,
    verify_asset,
)


def _blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def test_git_blob_sha_and_asset_verification(tmp_path: Path):
    data = b"pinned benchmark bytes\n"
    asset = tmp_path / "asset.txt"
    asset.write_bytes(data)
    spec = AssetSpec("benchmark/asset.txt", _blob_sha(data), len(data), "source_pool")

    assert git_blob_sha(data) == spec.git_blob_sha
    verify_asset(asset, spec)

    asset.write_bytes(data + b"changed")
    with pytest.raises(AssetIntegrityError, match="Integrity check failed"):
        verify_asset(asset, spec)


def test_materialize_assets_uses_pinned_commit_and_verifies_download(tmp_path: Path):
    data = b"content"
    track = {
        "repository": "https://github.com/example/research-model",
        "commit_sha": "a" * 40,
        "assets": [
            {
                "path": "benchmark/input.txt",
                "git_blob_sha": _blob_sha(data),
                "size_bytes": len(data),
            }
        ],
        "reconstruction_dependencies": [],
    }
    requested_urls: list[str] = []

    def fetcher(url: str) -> bytes:
        requested_urls.append(url)
        return data

    records = materialize_artur_assets(
        track,
        tmp_path,
        fetch_missing=True,
        fetcher=fetcher,
    )

    assert requested_urls == [
        "https://raw.githubusercontent.com/example/research-model/"
        f"{'a' * 40}/benchmark/input.txt"
    ]
    assert records[0]["status"] == "downloaded"
    assert records[0]["git_blob_sha"] == _blob_sha(data)

    records = materialize_artur_assets(track, tmp_path, fetch_missing=False)
    assert records[0]["status"] == "verified_existing"


def test_contract_rejects_unsafe_or_duplicate_asset_paths():
    base_asset = {"git_blob_sha": "b" * 40, "size_bytes": 1}
    track = {
        "assets": [{"path": "../outside.txt", **base_asset}],
        "reconstruction_dependencies": [],
    }
    with pytest.raises(ValueError, match="Unsafe asset path"):
        list(iter_asset_specs(track))

    track = {
        "assets": [{"path": "benchmark/a.txt", **base_asset}],
        "reconstruction_dependencies": [
            {"path": "benchmark/a.txt", **base_asset}
        ],
    }
    with pytest.raises(ValueError, match="Duplicate asset path"):
        list(iter_asset_specs(track))


def test_structural_reconciliation_distinguishes_preservation_and_extension(tmp_path: Path):
    commit = "c" * 40
    benchmark_dir = tmp_path / "cache" / commit / "benchmark"
    benchmark_dir.mkdir(parents=True)
    supply = pd.DataFrame(
        {
            "Produto": ["Corn", "Corn"],
            "Cidade": ["A", "A"],
            "Latitude": [-10.0, -10.0],
            "Longitude": [-50.0, -50.0],
            "Data": ["2025-01", "2025-02"],
            "Peso (ton)": [10.0, 20.0],
        }
    )
    demand = pd.DataFrame(
        {
            "Produto": ["Corn", "Corn"],
            "Cidade": ["D", "Port"],
            "Latitude": [-11.0, -12.0],
            "Longitude": [-51.0, -52.0],
            "Data": ["2025-01", "2025-01"],
            "Peso (ton)": [8.0, "∞"],
        }
    )
    warehouses = pd.DataFrame(
        {
            "CDA": ["W1"],
            "Status": ["Existing"],
            "Static Cap. (t)": [100.0],
            "Recep. Cap. (t)": [5.0],
            "Exped. Cap. (t)": [4.0],
            "Max Static Cap. (t)": [0.0],
        }
    )
    supply.to_excel(benchmark_dir / "Edited_Supply.xlsx", index=False)
    demand.to_excel(benchmark_dir / "Edited_Demand.xlsx", index=False)
    warehouses.to_excel(benchmark_dir / "Warehouses.xlsx", index=False)

    gold_demand = demand.copy()
    gold_demand.loc[1, "Peso (ton)"] = None
    gold_demand["Tipo_Demanda"] = ["DOMESTICA", "EXPORTACAO"]
    gold_warehouses = pd.DataFrame(
        {
            "CDA": ["W1", "W2"],
            "Status": ["Existente", "Candidato"],
            "Cap. Estática (t)": [100.0, 0.0],
            "Cap. Recepção (t)": [5.0, 1.0],
            "Cap. Expedição (t)": [4.0, 1.0],
            "Cap. Estática Máxima (t)": [0.0, 50.0],
        }
    )
    gold_path = tmp_path / "gold.xlsx"
    with pd.ExcelWriter(gold_path) as writer:
        supply.to_excel(writer, sheet_name="Oferta", index=False)
        gold_demand.to_excel(writer, sheet_name="Demanda", index=False)
        gold_warehouses.to_excel(writer, sheet_name="Warehouses", index=False)

    report = build_artur_gold_reconciliation(
        {"commit_sha": commit, "repository": "https://github.com/example/repo"},
        tmp_path / "cache",
        gold_path,
    )

    checks = report["lineage_checks"]
    assert checks["supply_source_rows_identical"] is True
    assert checks["demand_keys_identical"] is True
    assert checks["finite_demand_values_identical"] is True
    assert checks["artur_export_infinity_rows"] == 1
    assert checks["gold_explicit_export_rows"] == 1
    assert checks["shared_warehouse_ids"] == 1
    assert checks["gold_extension_warehouse_ids"] == 1
    assert report["reproduction_level"] == "bounded"

