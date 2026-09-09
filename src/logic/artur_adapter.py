"""Build an auditable solver workbook from a normalized Artur instance."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
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
    low_supply_multiplier: float = 0.80
    high_supply_multiplier: float = 1.20
    low_domestic_demand_multiplier: float = 0.80
    high_domestic_demand_multiplier: float = 1.20

    def __post_init__(self) -> None:
        if not 0.0 < self.low_supply_multiplier <= 1.0:
            raise ValueError("low_supply_multiplier must be in the interval (0, 1].")
        if self.high_supply_multiplier < 1.0:
            raise ValueError("high_supply_multiplier must be at least 1.")
        if not 0.0 < self.low_domestic_demand_multiplier <= 1.0:
            raise ValueError(
                "low_domestic_demand_multiplier must be in the interval (0, 1]."
            )
        if self.high_domestic_demand_multiplier < 1.0:
            raise ValueError(
                "high_domestic_demand_multiplier must be at least 1."
            )


def build_artur_solver_workbook(
    normalized_dir: Path,
    cache_dir: Path,
    output_dir: Path,
    *,
    contract_path: Path = Path("data/manifests/mvp_data_contract.json"),
    config: ArturSolverAdapterConfig | None = None,
    overwrite: bool = False,
) -> tuple[Path, Path]:
    """Verify lineage, adapt schemas, write a workbook, and validate its loader view."""

    config = config or ArturSolverAdapterConfig()
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
    distances = pd.concat(
        [
            _adapt_distances(pd.read_csv(normalized_dir / "distances.csv")),
            _build_direct_distances(supply, demand),
        ],
        ignore_index=True,
    )
    freight = pd.read_excel(benchmark_dir / "Valor_Tonelada_km.xlsx")
    storage = pd.read_excel(benchmark_dir / "Tarifa_de_Armazenagem.xlsx")
    investment = pd.read_excel(benchmark_dir / "Custos_Investimento.xlsx")
    initial_inventory = _build_initial_inventory(
        warehouses,
        products=list(dict.fromkeys(supply["Produto"].astype(str))),
    )
    scenarios = _build_scenario_definitions(config)
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
        initial_inventory.to_excel(
            writer, sheet_name="Estoque_Inicial", index=False
        )
        warehouses.to_excel(writer, sheet_name="Warehouses", index=False)
        freight.to_excel(writer, sheet_name="Frete", index=False)
        storage.to_excel(writer, sheet_name="Tarifa_Armz", index=False)
        investment.to_excel(writer, sheet_name="Custo_Invest", index=False)
        distances.to_excel(writer, sheet_name="Distancias", index=False)
        parameters.to_excel(writer, sheet_name="Parametros_Modelo", index=False)
        provenance.to_excel(writer, sheet_name="Proveniencia", index=False)
        scenarios.to_excel(writer, sheet_name="Cenarios", index=False)

    loader_config = ExcelLoaderConfig(
        compute_haversine_distances=False,
        use_workbook_distances=True,
        include_transshipment_routes=True,
        include_direct_origin_customer_routes=False,
        candidate_cost_policy="fixed_total",
        penalty_policy="thesis_dynamic",
        default_unmet_demand_penalty=config.unmet_demand_penalty,
        default_emergency_static_penalty=config.emergency_static_penalty,
        default_emergency_reception_penalty=config.emergency_reception_penalty,
    )
    model_data = load_model_data_from_excel(workbook_path, loader_config)
    stochastic_data = load_model_data_from_excel(
        workbook_path,
        ExcelLoaderConfig(
            compute_haversine_distances=False,
            use_workbook_distances=True,
            include_export_routes=True,
            include_transshipment_routes=True,
            include_direct_origin_customer_routes=False,
            include_stochastic_scenarios=True,
            scenario_generation_mode="cartesian",
            stochastic_combinations=(
                ("baixo", "alto"),
                ("base", "base"),
                ("alto", "baixo"),
            ),
            stochastic_probabilities=(0.33, 0.34, 0.33),
            candidate_cost_policy="fixed_total",
            penalty_policy="thesis_dynamic",
            default_unmet_demand_penalty=config.unmet_demand_penalty,
            default_emergency_static_penalty=config.emergency_static_penalty,
            default_emergency_reception_penalty=(
                config.emergency_reception_penalty
            ),
        ),
    )
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
        "reproduction_level": "thesis_compatible_bounded",
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
            "direct_distance_method": "haversine_v1_frozen",
            "candidate_cost_policy": "fixed_total",
            "penalty_policy": "thesis_dynamic",
            "initial_inventory_policy": "full_existing_static_capacity_equal_product_split",
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
            "initial_inventory_tons": sum(model_data.initial_inventory.values()),
        },
        "stochastic_extension_signature": {
            "classification": "controlled_extension",
            "scenarios": list(stochastic_data.scenarios),
            "scenario_probabilities": dict(stochastic_data.scenario_prob),
            "scenario_multipliers": stochastic_data.metadata.get(
                "scenario_multipliers", {}
            ),
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
            "scenario_multiplier_source": "thesis_case_study_design",
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


def _build_initial_inventory(
    warehouses: pd.DataFrame,
    *,
    products: list[str],
) -> pd.DataFrame:
    """Reproduce the thesis initial stock assumption for existing warehouses."""

    if not products:
        raise ValueError("Initial inventory requires at least one product.")

    existing = warehouses.loc[
        warehouses["Status"] == "Existente",
        ["CDA", "Cap. Estática (t)"],
    ].copy()
    rows = []
    for _, warehouse in existing.iterrows():
        share = float(warehouse["Cap. Estática (t)"]) / len(products)
        rows.extend(
            {
                "CDA": str(warehouse["CDA"]),
                "Produto": product,
                "Estoque Inicial (t)": share,
            }
            for product in products
        )
    return pd.DataFrame(rows)


def _build_scenario_definitions(config: ArturSolverAdapterConfig) -> pd.DataFrame:
    """Return the explicit scenario levels used by controlled extensions."""

    return pd.DataFrame(
        [
            {
                "Cenario": "base",
                "Probabilidade": 1.0,
                "Ativo": "SIM",
                "Multiplicador_Oferta": 1.0,
                "Multiplicador_Demanda_Domestica": 1.0,
                "Multiplicador_Demanda_Exportacao": 1.0,
                "Descricao": "Deterministic reference level",
                "Fonte_Parametro": "Gold workbook synthetic design",
            },
            {
                "Cenario": "baixo",
                "Probabilidade": 0.0,
                "Ativo": "NAO",
                "Multiplicador_Oferta": config.low_supply_multiplier,
                "Multiplicador_Demanda_Domestica": (
                    config.low_domestic_demand_multiplier
                ),
                "Multiplicador_Demanda_Exportacao": config.low_supply_multiplier,
                "Descricao": "Low parameter level",
                "Fonte_Parametro": "Gold workbook synthetic design",
            },
            {
                "Cenario": "alto",
                "Probabilidade": 0.0,
                "Ativo": "NAO",
                "Multiplicador_Oferta": config.high_supply_multiplier,
                "Multiplicador_Demanda_Domestica": (
                    config.high_domestic_demand_multiplier
                ),
                "Multiplicador_Demanda_Exportacao": config.high_supply_multiplier,
                "Descricao": "High parameter level",
                "Fonte_Parametro": "Gold workbook synthetic design",
            },
        ]
    )


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


def _build_direct_distances(
    supply: pd.DataFrame,
    demand: pd.DataFrame,
) -> pd.DataFrame:
    """Build the missing bounded OC matrix with the frozen Haversine method."""

    origins = supply[
        ["Cidade", "Latitude", "Longitude"]
    ].drop_duplicates(subset=["Cidade"])
    customer_columns = [
        "Cidade",
        "Tipo_Demanda",
        "Latitude",
        "Longitude",
    ]
    customers = demand[customer_columns].drop_duplicates(
        subset=["Cidade", "Tipo_Demanda"]
    )
    type_counts = customers.groupby("Cidade")["Tipo_Demanda"].nunique()
    rows = []
    for _, origin in origins.iterrows():
        for _, customer in customers.iterrows():
            city = str(customer["Cidade"])
            demand_type = str(customer["Tipo_Demanda"])
            customer_id = (
                f"{city} | {demand_type}"
                if int(type_counts.loc[city]) > 1
                else city
            )
            rows.append(
                {
                    "Tipo_Arco": "OC",
                    "Origem": str(origin["Cidade"]),
                    "Destino": customer_id,
                    "Distancia_km": _haversine_km(
                        float(origin["Latitude"]),
                        float(origin["Longitude"]),
                        float(customer["Latitude"]),
                        float(customer["Longitude"]),
                    ),
                }
            )
    return pd.DataFrame(rows)


def _haversine_km(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    """Return great-circle distance in kilometres for the bounded adapter."""

    earth_radius_km = 6371.0088
    lat_a = radians(latitude_a)
    lat_b = radians(latitude_b)
    delta_lat = lat_b - lat_a
    delta_lon = radians(longitude_b - longitude_a)
    haversine = (
        sin(delta_lat / 2.0) ** 2
        + cos(lat_a) * cos(lat_b) * sin(delta_lon / 2.0) ** 2
    )
    return 2.0 * earth_radius_km * asin(sqrt(haversine))


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
