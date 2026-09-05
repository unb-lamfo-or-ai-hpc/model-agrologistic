"""Build an auditable solver workbook from a normalized Artur instance."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.logic.artur_benchmark import (
    AssetIntegrityError,
    load_artur_contract,
    materialize_artur_assets,
)
from src.logic.excel_loader import ExcelLoaderConfig, load_model_data_from_excel


@dataclass(frozen=True, slots=True)
class ArturSolverAdapterConfig:
    """Explicit assumptions used to bridge the legacy and current schemas."""

    expansion_max_tons: float = 10_000.0
    expansion_fixed_cost: float = 1_000.0
    expansion_variable_cost_per_ton: float = 1_050.0
    historical_expansion_reception_ratio: float = 0.20
    historical_expansion_shipping_ratio: float = 0.20
    bulkification_max_tons: float = 4_000.0
    bulkification_fixed_cost: float = 5_000.0
    bulkification_variable_cost_per_ton: float = 680.0
    unmet_demand_penalty: float = 1_000_000.0
    emergency_static_penalty: float = 1_000_000.0
    emergency_reception_penalty: float = 1_000_000.0


def build_artur_solver_workbook(
    normalized_dir: Path,
    cache_dir: Path,
    output_dir: Path,
    *,
    contract_path: Path = Path("data/manifests/mvp_data_contract.json"),
    config: ArturSolverAdapterConfig = ArturSolverAdapterConfig(),
    overwrite: bool = False,
) -> tuple[Path, Path]:
    """Verify lineage, adapt schemas, write a workbook, and validate its loader view."""

    audit = _load_verified_normalized_tables(normalized_dir)
    track = load_artur_contract(contract_path)
    materialize_artur_assets(track, cache_dir, fetch_missing=False)
    benchmark_dir = cache_dir / track["commit_sha"] / "benchmark"

    supply = pd.read_csv(normalized_dir / "supply.csv")
    demand = _adapt_demand(pd.read_csv(normalized_dir / "demand.csv"))
    warehouses = _adapt_warehouses(
        pd.read_csv(normalized_dir / "warehouses.csv"),
        pd.read_excel(benchmark_dir / "Custos_Transbordo.xlsx"),
        config,
    )
    distances = _adapt_distances(pd.read_csv(normalized_dir / "distances.csv"))
    freight = pd.read_excel(benchmark_dir / "Valor_Tonelada_km.xlsx")
    storage = pd.read_excel(benchmark_dir / "Tarifa_de_Armazenagem.xlsx")
    investment = pd.read_excel(benchmark_dir / "Custos_Investimento.xlsx")
    parameters = pd.DataFrame(
        [
            {
                "Parametro": "unmet_demand_penalty_default",
                "Valor": config.unmet_demand_penalty,
                "Fonte_Parametro": "Bounded reproduction adapter",
            },
            {
                "Parametro": "emergency_static_penalty_default",
                "Valor": config.emergency_static_penalty,
                "Fonte_Parametro": "Bounded reproduction adapter",
            },
            {
                "Parametro": "emergency_reception_penalty_default",
                "Valor": config.emergency_reception_penalty,
                "Fonte_Parametro": "Bounded reproduction adapter",
            },
            {
                "Parametro": "days_per_period_default",
                "Valor": 30,
                "Fonte_Parametro": "Historical benchmark assumption",
            },
        ]
    )
    provenance = pd.DataFrame(
        [
            {"Field": "reproduction_level", "Value": "bounded"},
            {"Field": "source_commit_sha", "Value": track["commit_sha"]},
            {"Field": "normalization_policy", "Value": audit["normalization_policy"]},
            {"Field": "distance_method", "Value": "haversine_v1_frozen"},
            {"Field": "historical_distance_method", "Value": "OSRM"},
            {"Field": "forecasting_reconstructed", "Value": False},
        ]
    )

    output_dir.mkdir(parents=True, exist_ok=overwrite)
    workbook_path = output_dir / "model_input.xlsx"
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        supply.to_excel(writer, sheet_name="Oferta", index=False)
        demand.to_excel(writer, sheet_name="Demanda", index=False)
        warehouses.to_excel(writer, sheet_name="Warehouses", index=False)
        freight.to_excel(writer, sheet_name="Frete", index=False)
        storage.to_excel(writer, sheet_name="Tarifa_Armz", index=False)
        investment.to_excel(writer, sheet_name="Custo_Invest", index=False)
        distances.to_excel(writer, sheet_name="Distancias", index=False)
        parameters.to_excel(writer, sheet_name="Parametros_Modelo", index=False)
        provenance.to_excel(writer, sheet_name="Proveniencia", index=False)

    loader_config = ExcelLoaderConfig(
        compute_haversine_distances=False,
        use_workbook_distances=True,
        include_transshipment_routes=True,
        include_direct_origin_customer_routes=False,
        candidate_cost_policy="fixed_total",
        default_unmet_demand_penalty=config.unmet_demand_penalty,
        default_emergency_static_penalty=config.emergency_static_penalty,
        default_emergency_reception_penalty=config.emergency_reception_penalty,
    )
    model_data = load_model_data_from_excel(workbook_path, loader_config)
    expected_domestic_nodes = int(
        demand.loc[demand["Tipo_Demanda"] == "DOMESTICA", "Cidade"].nunique()
    )
    expected_export_nodes = int(
        demand.loc[demand["Tipo_Demanda"] == "EXPORTACAO", "Cidade"].nunique()
    )
    if len(model_data.domestic_customers) != expected_domestic_nodes:
        raise ValueError(
            "Adapted workbook changed the normalized domestic-customer count: "
            f"expected {expected_domestic_nodes}, loaded "
            f"{len(model_data.domestic_customers)}."
        )
    if len(model_data.export_customers) != expected_export_nodes:
        raise ValueError(
            "Adapted workbook changed the normalized export-customer count: "
            f"expected {expected_export_nodes}, loaded "
            f"{len(model_data.export_customers)}."
        )
    workbook_bytes = workbook_path.read_bytes()
    adapter_audit = {
        "schema_version": 1,
        "reproduction_level": "bounded",
        "instance_name": audit["instance_name"],
        "source_commit_sha": track["commit_sha"],
        "normalization_policy": audit["normalization_policy"],
        "source_normalized_table_files": audit["normalized_table_files"],
        "workbook": {
            "path": str(workbook_path),
            "sha256": hashlib.sha256(workbook_bytes).hexdigest(),
            "size_bytes": len(workbook_bytes),
        },
        "loader_contract": {
            "compute_haversine_distances": False,
            "use_workbook_distances": True,
            "include_transshipment_routes": True,
            "include_export_routes": True,
            "include_direct_origin_customer_routes": False,
            "candidate_cost_policy": "fixed_total",
        },
        "model_data_signature": {
            "origins": len(model_data.origins),
            "warehouses": len(model_data.warehouses),
            "domestic_customers": len(model_data.domestic_customers),
            "export_customers": len(model_data.export_customers),
            "products": len(model_data.products),
            "periods": len(model_data.periods),
            "routes_od": len(model_data.routes_od),
            "routes_dc": len(model_data.routes_dc),
            "routes_dd": len(model_data.routes_dd),
            "routes_oc": len(model_data.routes_oc),
            "export_upper_bound_tons": sum(model_data.demand_exp.values()),
        },
        "adapter_assumptions": {
            "days_per_period": 30,
            "expansion_max_tons_per_existing_warehouse": config.expansion_max_tons,
            "expansion_fixed_cost": config.expansion_fixed_cost,
            "expansion_variable_cost_per_ton": config.expansion_variable_cost_per_ton,
            "historical_expansion_reception_daily_factor": (
                config.historical_expansion_reception_ratio
            ),
            "historical_expansion_shipping_daily_factor": (
                config.historical_expansion_shipping_ratio
            ),
            "bulkification_max_tons_per_eligible_warehouse": config.bulkification_max_tons,
            "bulkification_fixed_cost": config.bulkification_fixed_cost,
            "bulkification_variable_cost_per_ton": (
                config.bulkification_variable_cost_per_ton
            ),
        },
        "remaining_limitations": [
            "DISTANCE_METHOD_DIFFERS_FROM_HISTORICAL_OSRM",
            "FORECASTING_PATH_NOT_RECONSTRUCTED",
            "SOLVER_MANIFEST_MUST_ENABLE_DAILY_CAPACITY_FACTORS",
        ],
    }
    audit_path = output_dir / "adapter_audit.json"
    audit_path.write_text(
        json.dumps(adapter_audit, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return workbook_path, audit_path


def _load_verified_normalized_tables(normalized_dir: Path) -> dict[str, Any]:
    audit_path = normalized_dir / "transformation_audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    expected_files = {"supply.csv", "demand.csv", "warehouses.csv", "distances.csv"}
    identities = audit.get("normalized_table_files", {})
    if set(identities) != expected_files:
        raise ValueError("The normalization audit does not declare the four required tables.")
    for filename, identity in identities.items():
        data = (normalized_dir / filename).read_bytes()
        actual_sha = hashlib.sha256(data).hexdigest()
        if len(data) != identity["size_bytes"] or actual_sha != identity["sha256"]:
            raise AssetIntegrityError(
                f"Normalized instance integrity check failed for {filename}."
            )
    return audit


def _adapt_demand(source: pd.DataFrame) -> pd.DataFrame:
    """Complete the robust demand schema without changing normalized quantities."""

    required = {"Peso (ton)", "Tipo_Demanda", "Regra_Limite"}
    missing = sorted(required - set(source.columns))
    if missing:
        raise ValueError(f"Normalized demand is missing columns: {missing}.")

    adapted = source.copy()
    adapted["Peso_Modelo (ton)"] = pd.to_numeric(
        adapted["Peso (ton)"], errors="coerce"
    )
    return adapted


def _adapt_warehouses(
    source: pd.DataFrame,
    transshipment_costs: pd.DataFrame,
    config: ArturSolverAdapterConfig,
) -> pd.DataFrame:
    aliases = {
        "CDA": ("CDA",),
        "Status": ("Status",),
        "Município": ("Municipality", "Município"),
        "UF": ("State", "UF"),
        "Latitude": ("Latitude",),
        "Longitude": ("Longitude",),
        "Armazenador": ("Storage Provider", "Armazenador"),
        "Tipo": ("Type", "Tipo"),
        "Cap. Estática (t)": ("Static Cap. (t)", "Cap. Estática (t)"),
        "Cap. Recepção (t)": ("Recep. Cap. (t)", "Cap. Recepção (t)"),
        "Cap. Expedição (t)": ("Exped. Cap. (t)", "Cap. Expedição (t)"),
        "Cap. Estática Máxima (t)": (
            "Max Static Cap. (t)",
            "Cap. Estática Máxima (t)",
        ),
        "Custo de Abertura ($)": ("Opening Cost ($)", "Custo de Abertura ($)"),
    }
    adapted = pd.DataFrame(
        {
            target: source[_first_column(source, candidates)]
            for target, candidates in aliases.items()
        }
    )
    adapted["Status"] = adapted["Status"].replace(
        {"Existing": "Existente", "Candidate": "Candidato"}
    )
    status_cost = _transshipment_cost_by_status(transshipment_costs)
    explicit_cost = _optional_column(
        source,
        ("Transshipment Cost ($/t)", "Custo de Transbordo ($/t)"),
    )
    adapted["Custo de Transbordo ($/t)"] = (
        pd.to_numeric(source[explicit_cost], errors="raise")
        if explicit_cost is not None
        else adapted["Status"].map(
            {"Existente": status_cost["existing"], "Candidato": status_cost["candidate"]}
        )
    )
    existing = adapted["Status"] == "Existente"
    eligible = existing & adapted["Tipo"].astype(str).str.casefold().isin(
        {"convencional", "graneleiro"}
    )
    adapted["Permite_Expansao"] = existing.map({True: "SIM", False: "NAO"})
    adapted["Cap_Expansao_Maxima_Modelo (t)"] = existing.astype(float) * config.expansion_max_tons
    adapted["Custo_Fixo_Expansao ($)"] = existing.astype(float) * config.expansion_fixed_cost
    adapted["Custo_Expansao_Modelo ($/t)"] = (
        existing.astype(float) * config.expansion_variable_cost_per_ton
    )
    adapted["Permite_Granelizacao"] = eligible.map({True: "SIM", False: "NAO"})
    adapted["Cap. Granelização Máxima (t)"] = (
        eligible.astype(float) * config.bulkification_max_tons
    )
    adapted["Custo_Fixo_Granelizacao ($)"] = (
        eligible.astype(float) * config.bulkification_fixed_cost
    )
    adapted["Custo_Granelizacao_Modelo ($/t)"] = (
        eligible.astype(float) * config.bulkification_variable_cost_per_ton
    )
    return adapted


def _adapt_distances(source: pd.DataFrame) -> pd.DataFrame:
    required = {"arc_type", "origin", "destination", "distance_km"}
    missing = sorted(required - set(source.columns))
    if missing:
        raise ValueError(f"Normalized distances are missing columns: {missing}")
    return source.rename(
        columns={
            "arc_type": "Tipo_Arco",
            "origin": "Origem",
            "destination": "Destino",
            "distance_km": "Distancia_km",
        }
    )[["Tipo_Arco", "Origem", "Destino", "Distancia_km"]]


def _transshipment_cost_by_status(frame: pd.DataFrame) -> dict[str, float]:
    type_column = _first_column(frame, ("Tipo", "Type"))
    value_column = _first_column(frame, ("Transbordo/t", "Transshipment Cost ($/t)"))
    values: dict[str, float] = {}
    for _, row in frame.iterrows():
        label = str(row[type_column]).strip().casefold()
        if label.startswith("exist"):
            values["existing"] = float(row[value_column])
        elif label.startswith("candidat"):
            values["candidate"] = float(row[value_column])
    if set(values) != {"existing", "candidate"}:
        raise ValueError("Transshipment costs must define Existing and Candidate values.")
    return values


def _first_column(frame: pd.DataFrame, candidates: tuple[str, ...]) -> str:
    column = _optional_column(frame, candidates)
    if column is None:
        raise ValueError(f"Missing required source column; expected one of {candidates}.")
    return column


def _optional_column(frame: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    return next((column for column in candidates if column in frame.columns), None)
