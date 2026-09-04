"""Auditable normalization of a persisted legacy Artur benchmark instance."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.logic.artur_benchmark import AssetIntegrityError


DEMAND_KEY = ["Produto", "Cidade", "Data"]
SUPPLY_KEY = ["Produto", "Cidade", "Data"]
NODE_ATTRIBUTES = ["Latitude", "Longitude"]


@dataclass(slots=True)
class PersistedArturInstance:
    """Verified raw instance loaded from a content-addressed bundle."""

    root: Path
    manifest: dict[str, Any]
    supply: pd.DataFrame
    demand: pd.DataFrame
    warehouses: pd.DataFrame
    distances: pd.DataFrame


@dataclass(slots=True)
class NormalizedArturInstance:
    """Normalized tables and the complete transformation audit."""

    source: PersistedArturInstance
    supply: pd.DataFrame
    demand: pd.DataFrame
    warehouses: pd.DataFrame
    distances: pd.DataFrame
    audit: dict[str, Any]


def load_persisted_artur_instance(root: Path) -> PersistedArturInstance:
    """Verify every raw artifact before loading it for normalization."""

    manifest_path = root / "instance_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_files = {
        "supply.csv",
        "demand.csv",
        "warehouses.csv",
        "distances.csv",
    }
    table_files = manifest.get("table_files", {})
    if set(table_files) != expected_files:
        raise ValueError("The raw instance manifest does not declare the four required tables.")

    for filename, identity in table_files.items():
        path = root / filename
        data = path.read_bytes()
        actual_sha = hashlib.sha256(data).hexdigest()
        if len(data) != identity["size_bytes"] or actual_sha != identity["sha256"]:
            raise AssetIntegrityError(
                f"Raw instance integrity check failed for {filename}: expected "
                f"size={identity['size_bytes']} and sha256={identity['sha256']}, "
                f"got size={len(data)} and sha256={actual_sha}."
            )

    return PersistedArturInstance(
        root=root,
        manifest=manifest,
        supply=pd.read_csv(root / "supply.csv"),
        demand=pd.read_csv(root / "demand.csv"),
        warehouses=pd.read_csv(root / "warehouses.csv"),
        distances=pd.read_csv(root / "distances.csv"),
    )


def normalize_artur_instance(source: PersistedArturInstance) -> NormalizedArturInstance:
    """Apply the declared bounded-reproduction policy without changing raw evidence."""

    _require_columns(source.supply, SUPPLY_KEY + NODE_ATTRIBUTES + ["Peso (ton)"], "supply")
    _require_columns(source.demand, DEMAND_KEY + NODE_ATTRIBUTES + ["Peso (ton)"], "demand")
    _assert_consistent_attributes(source.supply, SUPPLY_KEY, NODE_ATTRIBUTES, "supply")
    _assert_consistent_demand_coordinates(source.demand)

    normalized_supply = _normalize_supply(source.supply)
    normalized_demand = _normalize_demand(source.demand)
    normalized_warehouses = source.warehouses.copy()
    normalized_distances = source.distances.copy()

    before_supply_total = _numeric_total(source.supply["Peso (ton)"])
    after_supply_total = _numeric_total(normalized_supply["Peso (ton)"])
    before_demand_total = _numeric_total(source.demand["Peso (ton)"])
    after_demand_total = _numeric_total(normalized_demand["Peso (ton)"])
    if not math.isclose(before_supply_total, after_supply_total, rel_tol=1e-12, abs_tol=1e-6):
        raise ValueError("Supply normalization failed to conserve total tonnage.")
    if not math.isclose(before_demand_total, after_demand_total, rel_tol=1e-12, abs_tol=1e-6):
        raise ValueError("Demand normalization failed to conserve finite domestic tonnage.")

    metrics = [
        _audit_row("supply", "rows", len(source.supply), len(normalized_supply)),
        _audit_row(
            "supply",
            "duplicate_key_groups",
            _duplicate_group_count(source.supply, SUPPLY_KEY),
            _duplicate_group_count(normalized_supply, SUPPLY_KEY),
        ),
        _audit_row("supply", "total_tons", before_supply_total, after_supply_total),
        _audit_row("demand", "rows", len(source.demand), len(normalized_demand)),
        _audit_row(
            "demand",
            "duplicate_typed_key_groups",
            _duplicate_group_count(_typed_demand(source.demand), DEMAND_KEY + ["Tipo_Demanda"]),
            _duplicate_group_count(normalized_demand, DEMAND_KEY + ["Tipo_Demanda"]),
        ),
        _audit_row(
            "demand",
            "finite_domestic_total_tons",
            before_demand_total,
            after_demand_total,
        ),
        _audit_row(
            "demand",
            "export_rows",
            int(pd.to_numeric(source.demand["Peso (ton)"], errors="coerce").isna().sum()),
            int((normalized_demand["Tipo_Demanda"] == "EXPORTACAO").sum()),
        ),
        _audit_row(
            "warehouses",
            "rows",
            len(source.warehouses),
            len(normalized_warehouses),
        ),
        _audit_row(
            "distances",
            "rows",
            len(source.distances),
            len(normalized_distances),
        ),
    ]
    audit = {
        "schema_version": 1,
        "instance_name": source.manifest["name"],
        "source_commit_sha": source.manifest["source_commit_sha"],
        "normalization_policy": "bounded_reproduction_v1",
        "policy_rules": {
            "supply_duplicates": "sum finite tonnage by product, city, and period",
            "finite_demand_duplicates": "sum finite tonnage by product, city, and period",
            "unbounded_export_duplicates": "retain one explicit export row per key",
            "mixed_demand_keys": "preserve separate domestic and export typed rows",
            "coordinate_conflicts": "reject instead of selecting an arbitrary coordinate",
            "raw_artifacts": "verify and preserve without modification",
        },
        "source_table_files": source.manifest["table_files"],
        "metrics": metrics,
        "conservation_checks": {
            "supply_total_tons": True,
            "finite_domestic_demand_tons": True,
            "warehouse_rows": len(source.warehouses) == len(normalized_warehouses),
            "distance_rows": len(source.distances) == len(normalized_distances),
        },
        "remaining_limitations": [
            "DISTANCE_METHOD_DIFFERS_FROM_HISTORICAL_OSRM",
            "FORECASTING_PATH_NOT_RECONSTRUCTED",
        ],
    }
    return NormalizedArturInstance(
        source=source,
        supply=normalized_supply,
        demand=normalized_demand,
        warehouses=normalized_warehouses,
        distances=normalized_distances,
        audit=audit,
    )


def persist_normalized_artur_instance(instance: NormalizedArturInstance) -> Path:
    """Write normalized tables and their transformation audit beside the raw bundle."""

    output_dir = instance.source.root / "normalized"
    output_dir.mkdir(parents=False, exist_ok=False)
    tables = {
        "supply.csv": instance.supply,
        "demand.csv": instance.demand,
        "warehouses.csv": instance.warehouses,
        "distances.csv": instance.distances,
    }
    normalized_files: dict[str, dict[str, Any]] = {}
    for filename, frame in tables.items():
        target = output_dir / filename
        frame.to_csv(target, index=False, lineterminator="\n", float_format="%.12g")
        data = target.read_bytes()
        normalized_files[filename] = {
            "rows": len(frame),
            "sha256": hashlib.sha256(data).hexdigest(),
            "size_bytes": len(data),
        }

    audit = {**instance.audit, "normalized_table_files": normalized_files}
    audit_path = output_dir / "transformation_audit.json"
    audit_path.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output_dir / "transformation_audit.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audit["metrics"][0]))
        writer.writeheader()
        writer.writerows(audit["metrics"])
    return output_dir


def _normalize_supply(frame: pd.DataFrame) -> pd.DataFrame:
    prepared = frame.copy()
    prepared["Peso (ton)"] = pd.to_numeric(prepared["Peso (ton)"], errors="raise")
    prepared["_source_order"] = range(len(prepared))
    aggregations: dict[str, str] = {
        "Latitude": "first",
        "Longitude": "first",
        "Peso (ton)": "sum",
        "_source_order": "min",
    }
    for column in prepared.columns:
        if column not in SUPPLY_KEY + list(aggregations):
            aggregations[column] = "first"
    normalized = prepared.groupby(SUPPLY_KEY, as_index=False, sort=False).agg(aggregations)
    normalized = normalized.sort_values("_source_order").drop(columns="_source_order")
    return normalized[list(frame.columns)].reset_index(drop=True)


def _normalize_demand(frame: pd.DataFrame) -> pd.DataFrame:
    prepared = _typed_demand(frame)
    prepared["_source_order"] = range(len(prepared))
    finite = prepared[prepared["Tipo_Demanda"] == "DOMESTICA"].copy()
    export = prepared[prepared["Tipo_Demanda"] == "EXPORTACAO"].copy()

    finite_agg = {
        "Latitude": "first",
        "Longitude": "first",
        "Peso (ton)": "sum",
        "Regra_Limite": "first",
        "_source_order": "min",
    }
    normalized_finite = finite.groupby(
        DEMAND_KEY + ["Tipo_Demanda"], as_index=False, sort=False
    ).agg(finite_agg)
    normalized_export = export.drop_duplicates(
        DEMAND_KEY + ["Tipo_Demanda"], keep="first"
    ).copy()
    normalized_export["Peso (ton)"] = math.nan
    normalized = pd.concat([normalized_finite, normalized_export], ignore_index=True)
    normalized = normalized.sort_values("_source_order").drop(columns="_source_order")
    columns = [
        "Produto",
        "Cidade",
        "Latitude",
        "Longitude",
        "Data",
        "Peso (ton)",
        "Tipo_Demanda",
        "Regra_Limite",
    ]
    return normalized[columns].reset_index(drop=True)


def _typed_demand(frame: pd.DataFrame) -> pd.DataFrame:
    typed = frame.copy()
    numeric = pd.to_numeric(typed["Peso (ton)"], errors="coerce")
    export = numeric.isna()
    typed["Peso (ton)"] = numeric
    typed["Tipo_Demanda"] = export.map({False: "DOMESTICA", True: "EXPORTACAO"})
    typed["Regra_Limite"] = export.map(
        {False: "FIXO", True: "AUTO_OFERTA_TOTAL_PRODUTO_PERIODO"}
    )
    return typed


def _assert_consistent_attributes(
    frame: pd.DataFrame,
    key: list[str],
    attributes: list[str],
    dataset: str,
) -> None:
    for attribute in attributes:
        conflicts = frame.groupby(key, dropna=False)[attribute].nunique(dropna=False) > 1
        if conflicts.any():
            raise ValueError(
                f"{dataset} has conflicting {attribute} values for "
                f"{int(conflicts.sum())} duplicate keys."
            )


def _assert_consistent_demand_coordinates(frame: pd.DataFrame) -> None:
    typed = _typed_demand(frame)
    _assert_consistent_attributes(
        typed,
        DEMAND_KEY + ["Tipo_Demanda"],
        NODE_ATTRIBUTES,
        "demand",
    )


def _require_columns(frame: pd.DataFrame, columns: list[str], dataset: str) -> None:
    missing = [column for column in columns if column not in frame]
    if missing:
        raise ValueError(f"{dataset} is missing required columns: {missing}")


def _numeric_total(series: pd.Series) -> float:
    return float(pd.to_numeric(series, errors="coerce").fillna(0.0).sum())


def _duplicate_group_count(frame: pd.DataFrame, key: list[str]) -> int:
    return int((frame.groupby(key, dropna=False).size() > 1).sum())


def _audit_row(dataset: str, metric: str, before: int | float, after: int | float) -> dict:
    return {
        "dataset": dataset,
        "metric": metric,
        "before": before,
        "after": after,
        "delta": after - before,
        "status": "preserved" if math.isclose(float(before), float(after)) else "transformed",
    }

