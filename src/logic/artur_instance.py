"""Build persistent deterministic instances from Artur's pinned source pool."""

from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd


PORTS_POOL = (
    "Santos - SP",
    "Paranaguá - PR",
    "Rio Grande - RS",
    "São Francisco do Sul - SC",
    "Vitória - ES",
    "Itaqui - MA",
    "Suape - PE",
    "Pecém - CE",
    "Porto Alegre - RS",
    "Salvador - BA",
)


@dataclass(frozen=True, slots=True)
class ArturInstanceSpec:
    """Versioned request for one legacy benchmark iteration."""

    name: str
    supply_nodes: int
    domestic_demand_nodes: int
    export_nodes: int
    warehouses: int
    distance_method: str = "haversine_v1"

    def __post_init__(self) -> None:
        safe_characters = "abcdefghijklmnopqrstuvwxyz0123456789_-"
        if not self.name or any(char not in safe_characters for char in self.name):
            raise ValueError("Instance names must use lowercase letters, numbers, '_' or '-'.")
        sizes = (
            self.supply_nodes,
            self.domestic_demand_nodes,
            self.export_nodes,
            self.warehouses,
        )
        if any(size <= 0 for size in sizes):
            raise ValueError("All requested instance sizes must be positive.")
        if self.distance_method != "haversine_v1":
            raise ValueError("Only the reproducible haversine_v1 distance method is supported.")


@dataclass(slots=True)
class ArturInstanceBundle:
    """Generated tables and metadata before persistence."""

    spec: ArturInstanceSpec
    supply: pd.DataFrame
    demand: pd.DataFrame
    warehouses: pd.DataFrame
    distances: pd.DataFrame
    metadata: dict[str, Any]


def load_artur_instance_spec(path: Path, name: str) -> ArturInstanceSpec:
    """Load one named instance specification from the versioned manifest."""

    manifest = json.loads(path.read_text(encoding="utf-8"))
    try:
        payload = manifest["instances"][name]
    except KeyError as exc:
        raise ValueError(f"Unknown Artur instance: {name}") from exc
    return ArturInstanceSpec(name=name, **payload)


def build_artur_instance(
    track: dict[str, Any],
    cache_dir: Path,
    spec: ArturInstanceSpec,
) -> ArturInstanceBundle:
    """Reproduce one legacy sampling iteration and freeze proxy route distances."""

    commit_sha = track["commit_sha"]
    root = cache_dir / commit_sha
    benchmark = root / "benchmark"
    source_supply = pd.read_excel(benchmark / "Edited_Supply.xlsx")
    source_demand = pd.read_excel(benchmark / "Edited_Demand.xlsx")
    source_warehouses = pd.read_excel(benchmark / "Warehouses.xlsx")
    config = json.loads((benchmark / "benchmark_config.json").read_text(encoding="utf-8"))

    _ensure_source_pool_bounds(source_supply, source_demand, source_warehouses, spec)
    random.seed(track.get("reproduction_controls", {}).get("python_random_seed", 42))

    supply_cities = random.sample(
        source_supply["Cidade"].drop_duplicates().tolist(), spec.supply_nodes
    )
    demand_pool = source_demand["Cidade"].drop_duplicates().tolist()
    sampled_demand_cities = random.sample(demand_pool, spec.domestic_demand_nodes)
    periods = sorted(source_supply["Data"].dropna().astype(str).unique().tolist())
    products = sorted(source_supply["Produto"].dropna().astype(str).unique().tolist())

    supply = source_supply[source_supply["Cidade"].isin(supply_cities)].copy()
    supply = supply[supply["Data"].astype(str).isin(periods)].copy()
    sampled_demand = source_demand[
        source_demand["Cidade"].isin(sampled_demand_cities)
    ].copy()
    sampled_demand = sampled_demand[
        sampled_demand["Data"].astype(str).isin(periods)
    ].copy()
    export_demand = _build_export_demand(
        root,
        ports=PORTS_POOL[: spec.export_nodes],
        products=products,
        periods=periods,
    )
    demand = pd.concat([sampled_demand, export_demand], ignore_index=True)
    warehouses = source_warehouses.sample(n=spec.warehouses, random_state=42).copy()

    supply["Peso (ton)"] = pd.to_numeric(supply["Peso (ton)"], errors="coerce")
    numeric_demand = demand.copy()
    numeric_demand["Peso (ton)"] = pd.to_numeric(
        numeric_demand["Peso (ton)"], errors="coerce"
    )
    scaling = track.get("reproduction_controls", {}).get("feasibility_scaling", {})
    if scaling.get("enabled", config.get("enable_feasibility_scaling", False)):
        factor = float(
            scaling.get(
                "supply_to_demand_factor",
                config.get("feasibility_scaling_factor", 1.5),
            )
        )
        _scale_supply_for_feasibility(supply, numeric_demand, products, periods, factor)

    distances = _build_haversine_distances(supply, demand, warehouses)
    realized = _realized_signature(supply, demand, warehouses, distances)
    warnings = _legacy_semantic_warnings(
        supply,
        sampled_demand,
        export_demand,
        demand,
    )
    metadata = {
        "schema_version": 1,
        "name": spec.name,
        "source_commit_sha": commit_sha,
        "generator_semantics": "pinned_legacy_sampling_without_forecasting",
        "requested_sizes": asdict(spec),
        "sampled_nodes": {
            "supply": supply_cities,
            "legacy_domestic_pool": sampled_demand_cities,
            "generated_export": list(PORTS_POOL[: spec.export_nodes]),
            "warehouses": warehouses["CDA"].astype(str).tolist(),
        },
        "realized_signature": realized,
        "distance_contract": {
            "method": spec.distance_method,
            "earth_radius_km": 6371.0088,
            "rounding_decimals": 2,
            "historical_method": "OSRM",
            "historical_equivalence": False,
        },
        "forecasting_reconstructed": False,
        "warnings": warnings,
    }
    return ArturInstanceBundle(spec, supply, demand, warehouses, distances, metadata)


def persist_artur_instance(bundle: ArturInstanceBundle, output_root: Path) -> Path:
    """Persist immutable input tables and a content-addressed instance manifest."""

    output_dir = output_root / bundle.spec.name
    output_dir.mkdir(parents=True, exist_ok=False)
    tables = {
        "supply.csv": bundle.supply,
        "demand.csv": bundle.demand,
        "warehouses.csv": bundle.warehouses,
        "distances.csv": bundle.distances,
    }
    table_files: dict[str, dict[str, Any]] = {}
    for filename, frame in tables.items():
        target = output_dir / filename
        frame.to_csv(target, index=False, lineterminator="\n", float_format="%.12g")
        data = target.read_bytes()
        table_files[filename] = {
            "rows": len(frame),
            "sha256": hashlib.sha256(data).hexdigest(),
            "size_bytes": len(data),
        }

    manifest = {**bundle.metadata, "table_files": table_files}
    manifest_bytes = (
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    ).encode()
    (output_dir / "instance_manifest.json").write_bytes(manifest_bytes)
    return output_dir


def _ensure_source_pool_bounds(
    supply: pd.DataFrame,
    demand: pd.DataFrame,
    warehouses: pd.DataFrame,
    spec: ArturInstanceSpec,
) -> None:
    limits = {
        "supply_nodes": supply["Cidade"].nunique(),
        "domestic_demand_nodes": demand["Cidade"].nunique(),
        "export_nodes": len(PORTS_POOL),
        "warehouses": len(warehouses),
    }
    requested = asdict(spec)
    for field, limit in limits.items():
        if requested[field] > limit:
            raise ValueError(
                f"{field}={requested[field]} exceeds the source-pool limit {limit}. "
                "Synthetic node generation is outside this gate."
            )


def _build_export_demand(
    root: Path,
    *,
    ports: tuple[str, ...],
    products: list[str],
    periods: list[str],
) -> pd.DataFrame:
    municipalities = pd.read_csv(root / "src/view/assets/data/municipios.csv")
    states = pd.read_csv(root / "src/view/assets/data/estados.csv")
    states = states.rename(columns={"\ufeffcodigo_uf": "codigo_uf"})
    cities = municipalities.merge(states[["codigo_uf", "uf"]], on="codigo_uf", how="left")
    cities["Cidade_UF"] = cities["nome"] + " - " + cities["uf"]

    rows: list[dict[str, Any]] = []
    for port in ports:
        match = cities[cities["Cidade_UF"] == port]
        if match.empty:
            latitude, longitude = -23.96, -46.33
        else:
            latitude = float(match.iloc[0]["latitude"])
            longitude = float(match.iloc[0]["longitude"])
        for product in products:
            for period in periods:
                rows.append(
                    {
                        "Produto": product,
                        "Cidade": port,
                        "Latitude": latitude,
                        "Longitude": longitude,
                        "Data": period,
                        "Peso (ton)": math.nan,
                    }
                )
    return pd.DataFrame(rows)


def _scale_supply_for_feasibility(
    supply: pd.DataFrame,
    demand: pd.DataFrame,
    products: list[str],
    periods: list[str],
    factor: float,
) -> None:
    for product in products:
        for period in periods:
            demand_mask = (demand["Produto"] == product) & (demand["Data"].astype(str) == period)
            supply_mask = (supply["Produto"] == product) & (supply["Data"].astype(str) == period)
            demand_total = demand.loc[demand_mask, "Peso (ton)"].dropna().sum()
            supply_total = supply.loc[supply_mask, "Peso (ton)"].sum()
            required = demand_total * factor
            if supply_total >= required:
                continue
            count = int(supply_mask.sum())
            if supply_total > 1e-4:
                scaled_values = (
                    supply.loc[supply_mask, "Peso (ton)"] * (required / supply_total)
                ).round(2)
                supply["Peso (ton)"] = supply["Peso (ton)"].mask(
                    supply_mask, scaled_values
                )
            elif count:
                supply["Peso (ton)"] = supply["Peso (ton)"].mask(
                    supply_mask, round(required / count, 2)
                )


def _build_haversine_distances(
    supply: pd.DataFrame,
    demand: pd.DataFrame,
    warehouses: pd.DataFrame,
) -> pd.DataFrame:
    origins = supply[["Cidade", "Latitude", "Longitude"]].drop_duplicates()
    customers = demand[["Cidade", "Latitude", "Longitude"]].drop_duplicates()
    warehouse_nodes = warehouses[["CDA", "Latitude", "Longitude"]].drop_duplicates()
    records: list[dict[str, Any]] = []

    def append_pairs(arc_type: str, left: pd.DataFrame, right: pd.DataFrame) -> None:
        left_id, right_id = left.columns[0], right.columns[0]
        for left_row in left.itertuples(index=False, name=None):
            for right_row in right.itertuples(index=False, name=None):
                if arc_type == "DD" and str(left_row[0]) == str(right_row[0]):
                    continue
                records.append(
                    {
                        "arc_type": arc_type,
                        "origin": str(left_row[0]),
                        "destination": str(right_row[0]),
                        "distance_km": round(
                            _haversine_km(
                                float(left_row[1]),
                                float(left_row[2]),
                                float(right_row[1]),
                                float(right_row[2]),
                            ),
                            2,
                        ),
                        "origin_field": left_id,
                        "destination_field": right_id,
                    }
                )

    append_pairs("OD", origins, warehouse_nodes)
    append_pairs("DC", warehouse_nodes, customers)
    append_pairs("DD", warehouse_nodes, warehouse_nodes)
    return pd.DataFrame(records)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    value = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(value))


def _realized_signature(
    supply: pd.DataFrame,
    demand: pd.DataFrame,
    warehouses: pd.DataFrame,
    distances: pd.DataFrame,
) -> dict[str, Any]:
    demand_values = pd.to_numeric(demand["Peso (ton)"], errors="coerce")
    finite = demand_values.notna()
    key_columns = ["Produto", "Cidade", "Data"]
    supply_group_sizes = supply.groupby(key_columns, dropna=False).size()
    demand_group_sizes = demand.groupby(key_columns, dropna=False).size()
    return {
        "supply_rows": len(supply),
        "supply_nodes": int(supply["Cidade"].nunique()),
        "supply_total_tons": float(supply["Peso (ton)"].sum()),
        "duplicate_supply_key_groups": int((supply_group_sizes > 1).sum()),
        "duplicate_supply_rows": int(supply.duplicated(key_columns, keep=False).sum()),
        "demand_rows": len(demand),
        "demand_nodes": int(demand["Cidade"].nunique()),
        "finite_domestic_nodes": int(demand.loc[finite, "Cidade"].nunique()),
        "unbounded_export_nodes": int(demand.loc[~finite, "Cidade"].nunique()),
        "finite_domestic_demand_tons": float(demand_values.loc[finite].sum()),
        "duplicate_demand_key_groups": int((demand_group_sizes > 1).sum()),
        "duplicate_demand_rows": int(demand.duplicated(key_columns, keep=False).sum()),
        "warehouse_rows": len(warehouses),
        "existing_warehouses": int((warehouses["Status"] == "Existing").sum()),
        "candidate_warehouses": int((warehouses["Status"] == "Candidate").sum()),
        "distance_rows": len(distances),
        "distance_rows_by_arc": distances["arc_type"].value_counts().sort_index().to_dict(),
    }


def _legacy_semantic_warnings(
    supply: pd.DataFrame,
    sampled_demand: pd.DataFrame,
    export_demand: pd.DataFrame,
    combined_demand: pd.DataFrame,
) -> list[str]:
    warnings = ["DISTANCE_METHOD_DIFFERS_FROM_HISTORICAL_OSRM"]
    key_columns = ["Produto", "Cidade", "Data"]
    if supply.duplicated(key_columns, keep=False).any():
        warnings.append("DUPLICATE_SUPPLY_KEYS_REQUIRE_NORMALIZATION_BEFORE_SOLVE")
    sampled_values = pd.to_numeric(sampled_demand["Peso (ton)"], errors="coerce")
    if sampled_values.isna().any():
        warnings.append("LEGACY_DOMESTIC_POOL_CONTAINS_UNBOUNDED_EXPORT_ROWS")
    overlap = set(sampled_demand["Cidade"]) & set(export_demand["Cidade"])
    if overlap:
        warnings.append("GENERATED_EXPORT_DUPLICATES_SAMPLED_DEMAND_NODE")
    if combined_demand.duplicated(key_columns, keep=False).any():
        warnings.append("DUPLICATE_DEMAND_KEYS_REQUIRE_NORMALIZATION_BEFORE_SOLVE")
    warnings.append("FORECASTING_PATH_NOT_RECONSTRUCTED")
    return warnings

