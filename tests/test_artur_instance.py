import json
from pathlib import Path

import pandas as pd
import pytest

from src.logic.artur_instance import (
    ArturInstanceSpec,
    build_artur_instance,
    persist_artur_instance,
)


def _write_source_pool(root: Path, commit: str) -> tuple[dict, Path]:
    source_root = root / commit
    benchmark = source_root / "benchmark"
    lookup = source_root / "src/view/assets/data"
    benchmark.mkdir(parents=True)
    lookup.mkdir(parents=True)

    supply = pd.DataFrame(
        {
            "Produto": ["Corn"],
            "Cidade": ["Origin - GO"],
            "Latitude": [-16.0],
            "Longitude": [-49.0],
            "Data": ["2025-01"],
            "Peso (ton)": [10.0],
        }
    )
    demand = pd.DataFrame(
        {
            "Produto": ["Corn", "Corn"],
            "Cidade": ["Demand - GO", "Santos - SP"],
            "Latitude": [-16.5, -23.96],
            "Longitude": [-49.5, -46.33],
            "Data": ["2025-01", "2025-01"],
            "Peso (ton)": [8.0, "∞"],
        }
    )
    warehouses = pd.DataFrame(
        {
            "CDA": ["W1"],
            "Status": ["Existing"],
            "Latitude": [-17.0],
            "Longitude": [-48.0],
        }
    )
    supply.to_excel(benchmark / "Edited_Supply.xlsx", index=False)
    demand.to_excel(benchmark / "Edited_Demand.xlsx", index=False)
    warehouses.to_excel(benchmark / "Warehouses.xlsx", index=False)
    (benchmark / "benchmark_config.json").write_text(
        json.dumps(
            {
                "enable_feasibility_scaling": True,
                "feasibility_scaling_factor": 1.5,
            }
        ),
        encoding="utf-8",
    )
    pd.DataFrame(
        {
            "nome": ["Santos"],
            "codigo_uf": [35],
            "latitude": [-23.96],
            "longitude": [-46.33],
        }
    ).to_csv(lookup / "municipios.csv", index=False)
    pd.DataFrame({"codigo_uf": [35], "uf": ["SP"]}).to_csv(
        lookup / "estados.csv", index=False
    )
    track = {
        "commit_sha": commit,
        "reproduction_controls": {
            "python_random_seed": 42,
            "feasibility_scaling": {
                "enabled": True,
                "supply_to_demand_factor": 1.5,
            },
        },
    }
    return track, source_root


def test_builder_persists_legacy_semantics_and_frozen_proxy_distances(tmp_path: Path):
    commit = "d" * 40
    cache = tmp_path / "cache"
    track, _ = _write_source_pool(cache, commit)
    spec = ArturInstanceSpec(
        name="artur_test_i001",
        supply_nodes=1,
        domestic_demand_nodes=2,
        export_nodes=1,
        warehouses=1,
    )

    bundle = build_artur_instance(track, cache, spec)

    signature = bundle.metadata["realized_signature"]
    assert signature["supply_nodes"] == 1
    assert signature["supply_total_tons"] == pytest.approx(12.0)
    assert signature["finite_domestic_nodes"] == 1
    assert signature["unbounded_export_nodes"] == 1
    assert signature["duplicate_demand_key_groups"] == 1
    assert signature["duplicate_demand_rows"] == 2
    assert signature["distance_rows_by_arc"] == {"DC": 2, "OD": 1}
    assert bundle.metadata["distance_contract"]["historical_equivalence"] is False
    assert "LEGACY_DOMESTIC_POOL_CONTAINS_UNBOUNDED_EXPORT_ROWS" in bundle.metadata[
        "warnings"
    ]
    assert "DUPLICATE_DEMAND_KEYS_REQUIRE_NORMALIZATION_BEFORE_SOLVE" in bundle.metadata[
        "warnings"
    ]

    output_dir = persist_artur_instance(bundle, tmp_path / "outputs")
    manifest = json.loads(
        (output_dir / "instance_manifest.json").read_text(encoding="utf-8")
    )
    assert set(manifest["table_files"]) == {
        "demand.csv",
        "distances.csv",
        "supply.csv",
        "warehouses.csv",
    }
    assert all(len(record["sha256"]) == 64 for record in manifest["table_files"].values())

    with pytest.raises(FileExistsError):
        persist_artur_instance(bundle, tmp_path / "outputs")


def test_builder_rejects_synthetic_growth_outside_the_source_pool(tmp_path: Path):
    commit = "e" * 40
    cache = tmp_path / "cache"
    track, _ = _write_source_pool(cache, commit)
    spec = ArturInstanceSpec(
        name="artur_too_large",
        supply_nodes=2,
        domestic_demand_nodes=1,
        export_nodes=1,
        warehouses=1,
    )

    with pytest.raises(ValueError, match="Synthetic node generation is outside this gate"):
        build_artur_instance(track, cache, spec)

