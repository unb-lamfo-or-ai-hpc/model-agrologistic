"""
Excel loader for agricultural logistics model data.

This module converts a structured .xlsx workbook into the canonical ModelData
object used by the optimization backends.

The loader is an ETL layer. It may use pandas/openpyxl, but it must not import
solver-specific packages such as gurobipy or pyomo.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from src.logic.model_data import ModelData, NodeInfo


CandidateCostPolicy = Literal["variable_from_total", "fixed_total"]
ScenarioGenerationMode = Literal["active_rows", "cartesian"]


REQUIRED_SHEETS = {
    "Oferta",
    "Demanda",
    "Warehouses",
    "Frete",
    "Tarifa_Armz",
    "Custo_Invest",
}


REQUIRED_COLUMNS = {
    "Oferta": {
        "Produto",
        "Cidade",
        "Latitude",
        "Longitude",
        "Data",
        "Peso (ton)",
    },
    "Demanda": {
        "Produto",
        "Cidade",
        "Latitude",
        "Longitude",
        "Data",
        "Peso (ton)",
    },
    "Warehouses": {
        "CDA",
        "Status",
        "Município",
        "UF",
        "Latitude",
        "Longitude",
        "Armazenador",
        "Tipo",
        "Cap. Estática (t)",
        "Cap. Recepção (t)",
        "Cap. Expedição (t)",
        "Cap. Estática Máxima (t)",
        "Custo de Abertura ($)",
    },
    "Frete": {
        "Estado",
        "Frete Tonelada Km",
    },
    "Tarifa_Armz": {
        "Produto",
        "Armazenar_Publico",
        "Armazenar_Privado",
    },
    "Custo_Invest": {
        "Tipo",
        "Custo Baixo (R$/t)",
        "Custo Alto (R$/t)",
    },
}

SCENARIO_REQUIRED_COLUMNS = {
    "Cenario",
    "Probabilidade",
    "Ativo",
}


@dataclass(slots=True)
class ExcelLoaderConfig:
    """
    Configuration for reading a model instance from Excel.
    """

    compute_haversine_distances: bool = True

    include_export_routes: bool = True
    include_transshipment_routes: bool = False
    include_direct_origin_customer_routes: bool = False

    # Opt-in preserves deterministic loading for existing callers.
    include_stochastic_scenarios: bool = False
    # ``active_rows`` reads the scenarios activated in the workbook.
    # ``cartesian`` combines user-selected supply and demand levels. The
    # explicit combinations option permits any scenario count from 1 to 9.
    scenario_generation_mode: ScenarioGenerationMode = "active_rows"
    stochastic_supply_levels: tuple[str, ...] = ("baixo", "base", "alto")
    stochastic_demand_levels: tuple[str, ...] = ("baixo", "base", "alto")
    stochastic_combinations: tuple[tuple[str, str], ...] | None = None
    stochastic_probabilities: tuple[float, ...] | None = None

    candidate_cost_policy: CandidateCostPolicy = "variable_from_total"

    demand_node_id_column: str = "ID_Demanda"
    split_overlapping_demand_nodes: bool = True

    default_unmet_demand_penalty: float = 1_000_000.0
    default_emergency_static_penalty: float = 1_000_000.0
    default_emergency_reception_penalty: float = 1_000_000.0
    default_transshipment_cost: float = 0.0


def load_model_data_from_excel(
    path: str | Path,
    config: ExcelLoaderConfig | None = None,
) -> ModelData:
    """
    Load a golden-template Excel workbook into ModelData.
    """

    if config is None:
        config = ExcelLoaderConfig()

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Excel file not found: {path}")

    sheets = pd.read_excel(path, sheet_name=None, engine="openpyxl")
    _validate_workbook_schema(sheets)

    oferta = _clean_dataframe(sheets["Oferta"])
    demanda = _clean_dataframe(sheets["Demanda"])
    warehouses_df = _clean_dataframe(sheets["Warehouses"])
    frete = _clean_dataframe(sheets["Frete"])
    tarifa = _clean_dataframe(sheets["Tarifa_Armz"])
    custo_invest = _clean_dataframe(sheets["Custo_Invest"])

    parametros_modelo = (
        _clean_dataframe(sheets["Parametros_Modelo"])
        if "Parametros_Modelo" in sheets
        else pd.DataFrame()
    )
    cenarios = (
        _clean_dataframe(sheets["Cenarios"])
        if config.include_stochastic_scenarios and "Cenarios" in sheets
        else pd.DataFrame()
    )

    loader_warnings: list[str] = []

    freight_by_state = _build_freight_by_state(frete)
    storage_tariff_table = _build_storage_tariff_table(tarifa)
    investment_cost_table = _build_investment_cost_table(custo_invest)
    parameter_table = _build_parameter_table(parametros_modelo)

    origins, supply, origin_node_info = _load_supply(oferta)

    products = _ordered_union(
        _unique_strings(oferta["Produto"]),
        _unique_strings(demanda["Produto"]),
    )

    periods = _ordered_union(
        [_normalize_period(value) for value in oferta["Data"].tolist()],
        [_normalize_period(value) for value in demanda["Data"].tolist()],
    )

    supply_total_by_product_period = _build_supply_total_by_product_period(
        origins=origins,
        products=products,
        periods=periods,
        supply=supply,
    )

    (
        customers,
        domestic_customers,
        export_customers,
        demand_dom,
        demand_exp,
        customer_node_info,
    ) = _load_demand(
        demanda=demanda,
        supply_total_by_product_period=supply_total_by_product_period,
        loader_warnings=loader_warnings,
        config=config,
    )

    scenarios: list[str] = []
    scenario_prob: dict[str, float] = {}
    supply_s: dict[tuple[str, str, str, str], float] = {}
    demand_dom_s: dict[tuple[str, str, str, str], float] = {}
    demand_exp_s: dict[tuple[str, str, str, str], float] = {}
    scenario_multipliers: dict[str, dict[str, float]] = {}

    if config.include_stochastic_scenarios:
        _validate_scenario_schema(sheets)
        (
            scenarios,
            scenario_prob,
            supply_s,
            demand_dom_s,
            demand_exp_s,
            scenario_multipliers,
        ) = _load_scenarios(
            cenarios=cenarios,
            config=config,
            origins=origins,
            domestic_customers=domestic_customers,
            export_customers=export_customers,
            products=products,
            periods=periods,
            supply=supply,
            demand_dom=demand_dom,
            demand_exp=demand_exp,
        )

    (
        warehouses,
        existing_warehouses,
        candidate_warehouses,
        bulk_eligible_warehouses,
        warehouse_node_info,
        static_capacity,
        reception_capacity,
        shipping_capacity,
        max_candidate_capacity,
        opening_fixed_cost,
        candidate_capacity_cost,
        max_expand_capacity,
        expand_fixed_cost,
        expand_variable_cost,
        max_bulk_capacity,
        bulk_fixed_cost,
        bulk_variable_cost,
        transshipment_cost,
        reported_candidate_total_opening_cost,
    ) = _load_warehouses(
        warehouses_df=warehouses_df,
        config=config,
        parameter_table=parameter_table,
        investment_cost_table=investment_cost_table,
    )

    freight_origin = {
        origin: _lookup_freight_for_city(origin, freight_by_state)
        for origin in origins
    }

    freight_dest = {
        customer: _lookup_freight_for_node(
            node_id=customer,
            node_info=customer_node_info,
            freight_by_state=freight_by_state,
        )
        for customer in customers
    }

    freight_warehouse = {
        warehouse: _lookup_freight_for_node(
            node_id=warehouse,
            node_info=warehouse_node_info,
            freight_by_state=freight_by_state,
        )
        for warehouse in warehouses
    }

    storage_tariff = _expand_storage_tariffs(
        warehouses=warehouses,
        products=products,
        warehouse_node_info=warehouse_node_info,
        storage_tariff_table=storage_tariff_table,
    )

    route_customers = list(domestic_customers)

    if config.include_export_routes:
        route_customers = _ordered_union(route_customers, export_customers)

    routes_od = {
        (origin, warehouse, product)
        for origin in origins
        for warehouse in warehouses
        for product in products
    }

    routes_dc = {
        (warehouse, customer, product)
        for warehouse in warehouses
        for customer in route_customers
        for product in products
    }

    routes_dd = set()

    if config.include_transshipment_routes:
        routes_dd = {
            (warehouse_from, warehouse_to, product)
            for warehouse_from in warehouses
            for warehouse_to in warehouses
            for product in products
            if warehouse_from != warehouse_to
        }

    routes_oc = set()

    if config.include_direct_origin_customer_routes:
        routes_oc = {
            (origin, customer, product)
            for origin in origins
            for customer in route_customers
            for product in products
        }

    node_info = {}
    node_info.update(origin_node_info)
    node_info.update(customer_node_info)
    node_info.update(warehouse_node_info)

    dist_od: dict[tuple[str, str], float] = {}
    dist_dc: dict[tuple[str, str], float] = {}
    dist_dd: dict[tuple[str, str], float] = {}
    dist_oc: dict[tuple[str, str], float] = {}

    if config.compute_haversine_distances:
        dist_od = _build_distance_matrix_from_routes(
            pairs=[(origin, warehouse) for origin, warehouse, _product in routes_od],
            node_info=node_info,
        )

        dist_dc = _build_distance_matrix_from_routes(
            pairs=[(warehouse, customer) for warehouse, customer, _product in routes_dc],
            node_info=node_info,
        )

        dist_dd = _build_distance_matrix_from_routes(
            pairs=[
                (warehouse_from, warehouse_to)
                for warehouse_from, warehouse_to, _product in routes_dd
            ],
            node_info=node_info,
        )

        dist_oc = _build_distance_matrix_from_routes(
            pairs=[(origin, customer) for origin, customer, _product in routes_oc],
            node_info=node_info,
        )

    unmet_demand_penalty = {
        (customer, product): config.default_unmet_demand_penalty
        for customer in domestic_customers
        for product in products
    }

    emergency_static_capacity_penalty = {
        warehouse: config.default_emergency_static_penalty
        for warehouse in warehouses
    }

    emergency_reception_capacity_penalty = {
        warehouse: config.default_emergency_reception_penalty
        for warehouse in warehouses
    }

    return ModelData(
        origins=origins,
        warehouses=warehouses,
        existing_warehouses=existing_warehouses,
        candidate_warehouses=candidate_warehouses,
        bulk_eligible_warehouses=bulk_eligible_warehouses,
        customers=customers,
        domestic_customers=domestic_customers,
        export_customers=export_customers,
        products=products,
        periods=periods,
        routes_od=routes_od,
        routes_dc=routes_dc,
        routes_dd=routes_dd,
        routes_oc=routes_oc,
        supply=supply,
        demand_dom=demand_dom,
        demand_exp=demand_exp,
        scenarios=scenarios,
        scenario_prob=scenario_prob,
        supply_s=supply_s,
        demand_dom_s=demand_dom_s,
        demand_exp_s=demand_exp_s,
        dist_od=dist_od,
        dist_dc=dist_dc,
        dist_dd=dist_dd,
        dist_oc=dist_oc,
        freight_origin=freight_origin,
        freight_dest=freight_dest,
        freight_warehouse=freight_warehouse,
        transshipment_cost=transshipment_cost,
        storage_tariff=storage_tariff,
        static_capacity=static_capacity,
        reception_capacity=reception_capacity,
        shipping_capacity=shipping_capacity,
        max_candidate_capacity=max_candidate_capacity,
        opening_fixed_cost=opening_fixed_cost,
        candidate_capacity_cost=candidate_capacity_cost,
        max_expand_capacity=max_expand_capacity,
        expand_fixed_cost=expand_fixed_cost,
        expand_variable_cost=expand_variable_cost,
        max_bulk_capacity=max_bulk_capacity,
        bulk_fixed_cost=bulk_fixed_cost,
        bulk_variable_cost=bulk_variable_cost,
        unmet_demand_penalty=unmet_demand_penalty,
        emergency_static_capacity_penalty=emergency_static_capacity_penalty,
        emergency_reception_capacity_penalty=emergency_reception_capacity_penalty,
        node_info=node_info,
        metadata={
            "source_excel": str(path),
            "loader": "src.logic.excel_loader.load_model_data_from_excel",
            "candidate_cost_policy": config.candidate_cost_policy,
            "reported_candidate_total_opening_cost": reported_candidate_total_opening_cost,
            "investment_cost_table": investment_cost_table,
            "parameter_table": parameter_table,
            "scenario_generation_mode": (
                config.scenario_generation_mode
                if config.include_stochastic_scenarios
                else None
            ),
            "scenario_multipliers": scenario_multipliers,
            "loader_warnings": loader_warnings,
        },
    )

def _lookup_freight_for_node(
    node_id: str,
    node_info: dict[str, NodeInfo],
    freight_by_state: dict[str, float],
) -> float:
    state = node_info[node_id].state

    if state is None:
        state = _state_from_city(node_id)

    if state is None:
        return 0.0

    if state not in freight_by_state:
        raise ValueError(f"Missing freight rate for state {state!r}, node {node_id!r}.")

    return freight_by_state[state]

# ---------------------------------------------------------------------
# Workbook schema
# ---------------------------------------------------------------------


def _validate_workbook_schema(sheets: dict[str, pd.DataFrame]) -> None:
    available_sheets = set(sheets)
    missing_sheets = sorted(REQUIRED_SHEETS - available_sheets)

    if missing_sheets:
        raise ValueError(f"Missing required Excel sheets: {missing_sheets}")

    for sheet_name, required_columns in REQUIRED_COLUMNS.items():
        columns = set(str(column).strip() for column in sheets[sheet_name].columns)
        missing_columns = sorted(required_columns - columns)

        if missing_columns:
            raise ValueError(
                f"Sheet {sheet_name!r} is missing required columns: {missing_columns}"
            )


def _validate_scenario_schema(sheets: dict[str, pd.DataFrame]) -> None:
    if "Cenarios" not in sheets:
        raise ValueError(
            "ExcelLoaderConfig.include_stochastic_scenarios requires "
            "a 'Cenarios' sheet."
        )

    columns = {str(column).strip() for column in sheets["Cenarios"].columns}
    missing_columns = sorted(SCENARIO_REQUIRED_COLUMNS - columns)

    if missing_columns:
        raise ValueError(
            "Sheet 'Cenarios' is missing required columns: "
            f"{missing_columns}"
        )

    for override_sheet in ("Oferta_Cenarios", "Demanda_Cenarios"):
        if override_sheet not in sheets:
            continue
        if not _clean_dataframe(sheets[override_sheet]).empty:
            raise ValueError(
                f"Sheet {override_sheet!r} contains scenario-specific rows, "
                "which are not supported yet. This stage reads multipliers "
                "from 'Cenarios'."
            )


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    cleaned.columns = [str(column).strip() for column in cleaned.columns]
    cleaned = cleaned.dropna(how="all")
    return cleaned


# ---------------------------------------------------------------------
# Sheet loaders
# ---------------------------------------------------------------------


def _load_scenarios(
    cenarios: pd.DataFrame,
    config: ExcelLoaderConfig,
    origins: list[str],
    domestic_customers: list[str],
    export_customers: list[str],
    products: list[str],
    periods: list[str],
    supply: dict[tuple[str, str, str], float],
    demand_dom: dict[tuple[str, str, str], float],
    demand_exp: dict[tuple[str, str, str], float],
) -> tuple[
    list[str],
    dict[str, float],
    dict[tuple[str, str, str, str], float],
    dict[tuple[str, str, str, str], float],
    dict[tuple[str, str, str, str], float],
    dict[str, dict[str, float]],
]:
    scenarios: list[str] = []
    scenario_prob: dict[str, float] = {}
    scenario_multipliers: dict[str, dict[str, float]] = {}

    supply_multiplier_column = _first_existing_dataframe_column(
        cenarios,
        ["Multiplicador_Oferta", "Multiplicador Oferta"],
    )
    domestic_multiplier_column = _first_existing_dataframe_column(
        cenarios,
        [
            "Multiplicador_Demanda_Domestica",
            "Multiplicador Demanda Domestica",
            "Multiplicador Demanda Doméstica",
        ],
    )
    export_multiplier_column = _first_existing_dataframe_column(
        cenarios,
        [
            "Multiplicador_Demanda_Exportacao",
            "Multiplicador Demanda Exportacao",
            "Multiplicador Demanda Exportação",
        ],
    )

    rows_by_level: dict[str, pd.Series] = {}
    ordered_rows: list[pd.Series] = []

    for _, row in cenarios.iterrows():
        if _is_blank_row(row, required_fields=["Cenario"]):
            continue
        level = _normalize_text(row["Cenario"])
        folded_level = _fold_text(level)
        if folded_level in rows_by_level:
            raise ValueError(f"Duplicate scenario level {level!r} in 'Cenarios'.")
        rows_by_level[folded_level] = row
        ordered_rows.append(row)

    scenario_specs: list[tuple[str, float, pd.Series, pd.Series]] = []

    if config.scenario_generation_mode == "active_rows":
        for row in ordered_rows:
            if not _is_yes(row["Ativo"]):
                continue
            scenario = _normalize_text(row["Cenario"])
            scenario_specs.append(
                (scenario, _parse_float(row["Probabilidade"]), row, row)
            )
    elif config.scenario_generation_mode == "cartesian":
        combinations = config.stochastic_combinations
        if combinations is None:
            combinations = tuple(
                (supply_level, demand_level)
                for supply_level in config.stochastic_supply_levels
                for demand_level in config.stochastic_demand_levels
            )

        if not 1 <= len(combinations) <= 9:
            raise ValueError(
                "Cartesian stochastic generation requires between 1 and 9 "
                "scenario combinations."
            )
        if len(set(combinations)) != len(combinations):
            raise ValueError("Stochastic scenario combinations must be unique.")

        probabilities = config.stochastic_probabilities
        if probabilities is None:
            probabilities = tuple(1.0 / len(combinations) for _ in combinations)
        if len(probabilities) != len(combinations):
            raise ValueError(
                "stochastic_probabilities must contain one value per "
                "scenario combination."
            )

        for (supply_level, demand_level), probability in zip(
            combinations,
            probabilities,
            strict=True,
        ):
            supply_row = rows_by_level.get(_fold_text(supply_level))
            demand_row = rows_by_level.get(_fold_text(demand_level))
            if supply_row is None:
                raise ValueError(
                    f"Unknown stochastic supply level {supply_level!r}."
                )
            if demand_row is None:
                raise ValueError(
                    f"Unknown stochastic demand level {demand_level!r}."
                )
            scenario = (
                f"oferta_{_scenario_slug(supply_level)}"
                f"__demanda_{_scenario_slug(demand_level)}"
            )
            scenario_specs.append(
                (scenario, float(probability), supply_row, demand_row)
            )
    else:
        raise ValueError(
            f"Invalid scenario_generation_mode={config.scenario_generation_mode!r}."
        )

    for scenario, probability, supply_row, demand_row in scenario_specs:
        if scenario in scenario_prob:
            raise ValueError(f"Duplicate generated scenario {scenario!r}.")

        supply_multiplier = _first_numeric_value(
            supply_row[supply_multiplier_column]
            if supply_multiplier_column is not None
            else None,
            1.0,
        )
        domestic_multiplier = _first_numeric_value(
            demand_row[domestic_multiplier_column]
            if domestic_multiplier_column is not None
            else None,
            1.0,
        )
        export_multiplier = _first_numeric_value(
            supply_row[export_multiplier_column]
            if export_multiplier_column is not None
            else None,
            supply_multiplier,
        )

        multipliers = {
            "supply": supply_multiplier,
            "domestic_demand": domestic_multiplier,
            "export_demand": export_multiplier,
        }
        if any(value < 0.0 for value in multipliers.values()):
            raise ValueError(
                f"Scenario {scenario!r} contains a negative multiplier: "
                f"{multipliers}."
            )

        scenarios.append(scenario)
        scenario_prob[scenario] = probability
        scenario_multipliers[scenario] = multipliers

    if not scenarios:
        raise ValueError(
            "No active scenarios were found in the 'Cenarios' sheet."
        )

    supply_s = {
        (scenario, origin, product, period): (
            supply.get((origin, product, period), 0.0)
            * scenario_multipliers[scenario]["supply"]
        )
        for scenario in scenarios
        for origin in origins
        for product in products
        for period in periods
    }
    demand_dom_s = {
        (scenario, customer, product, period): (
            demand_dom.get((customer, product, period), 0.0)
            * scenario_multipliers[scenario]["domestic_demand"]
        )
        for scenario in scenarios
        for customer in domestic_customers
        for product in products
        for period in periods
    }
    demand_exp_s = {
        (scenario, customer, product, period): (
            demand_exp.get((customer, product, period), 0.0)
            * scenario_multipliers[scenario]["export_demand"]
        )
        for scenario in scenarios
        for customer in export_customers
        for product in products
        for period in periods
    }

    return (
        scenarios,
        scenario_prob,
        supply_s,
        demand_dom_s,
        demand_exp_s,
        scenario_multipliers,
    )


def _load_supply(
    oferta: pd.DataFrame,
) -> tuple[list[str], dict[tuple[str, str, str], float], dict[str, NodeInfo]]:
    origins: list[str] = []
    supply: dict[tuple[str, str, str], float] = {}
    node_info: dict[str, NodeInfo] = {}

    for _, row in oferta.iterrows():
        if _is_blank_row(row, required_fields=["Produto", "Cidade", "Data"]):
            continue

        product = _normalize_text(row["Produto"])
        city = _normalize_text(row["Cidade"])
        period = _normalize_period(row["Data"])
        weight = _parse_float(row["Peso (ton)"])

        _append_unique(origins, city)
        _add_to_mapping(supply, (city, product, period), weight)

        if city not in node_info:
            node_info[city] = NodeInfo(
                node_id=city,
                node_type="origin",
                name=city,
                state=_state_from_city(city),
                latitude=_parse_optional_float(row["Latitude"]),
                longitude=_parse_optional_float(row["Longitude"]),
            )

    return origins, supply, node_info


def _load_demand(
    demanda: pd.DataFrame,
    supply_total_by_product_period: dict[tuple[str, str], float],
    loader_warnings: list[str],
    config: ExcelLoaderConfig,
) -> tuple[
    list[str],
    list[str],
    list[str],
    dict[tuple[str, str, str], float],
    dict[tuple[str, str, str], float],
    dict[str, NodeInfo],
]:
    customers: list[str] = []
    domestic_customers: list[str] = []
    export_customers: list[str] = []

    demand_dom: dict[tuple[str, str, str], float] = {}
    demand_exp: dict[tuple[str, str, str], float] = {}

    node_info: dict[str, NodeInfo] = {}

    has_new_schema = {
        "Tipo_Demanda",
        "Regra_Limite",
        "Peso_Modelo (ton)",
    }.issubset(set(demanda.columns))

    if not has_new_schema:
        loader_warnings.append(
            "Demanda sheet does not contain the full golden demand schema. "
            "Legacy demand interpretation is being used."
        )

    demand_types_by_city = _collect_demand_types_by_city(demanda, has_new_schema)

    for _, row in demanda.iterrows():
        if _is_blank_row(row, required_fields=["Produto", "Cidade", "Data"]):
            continue

        product = _normalize_text(row["Produto"])
        city = _normalize_text(row["Cidade"])
        period = _normalize_period(row["Data"])

        demand_type = _normalize_demand_type(row["Tipo_Demanda"]) if has_new_schema else ""
        limit_rule = _normalize_limit_rule(row["Regra_Limite"]) if has_new_schema else ""

        raw_weight = row["Peso (ton)"]
        raw_model_weight = row["Peso_Modelo (ton)"] if has_new_schema else None

        is_legacy_infinity = _is_infinity_token(raw_weight)

        if is_legacy_infinity:
            demand_type = "EXPORTACAO"
            limit_rule = "AUTO_OFERTA_TOTAL_PRODUTO_PERIODO"
            loader_warnings.append(
                f"Legacy infinity token found in Demanda for "
                f"({city}, {product}, {period}). Interpreted as export upper bound."
            )

        if not demand_type:
            demand_type = "DOMESTICA"

        customer_id = _resolve_customer_id(
            row=row,
            city=city,
            demand_type=demand_type,
            demand_types_by_city=demand_types_by_city,
            config=config,
        )

        _append_unique(customers, customer_id)

        if demand_type == "DOMESTICA":
            _append_unique(domestic_customers, customer_id)
            value = _first_numeric_value(raw_model_weight, raw_weight)
            _add_to_mapping(demand_dom, (customer_id, product, period), value)

        elif demand_type == "EXPORTACAO":
            _append_unique(export_customers, customer_id)

            if limit_rule == "AUTO_OFERTA_TOTAL_PRODUTO_PERIODO":
                value = supply_total_by_product_period.get((product, period), 0.0)
            else:
                value = _first_numeric_value(raw_model_weight, raw_weight)

            _add_to_mapping(demand_exp, (customer_id, product, period), value)

        else:
            raise ValueError(
                f"Invalid Tipo_Demanda={demand_type!r} for "
                f"({city}, {product}, {period})."
            )

        if customer_id not in node_info:
            node_info[customer_id] = NodeInfo(
                node_id=customer_id,
                node_type="customer",
                name=city,
                state=_state_from_city(city),
                latitude=_parse_optional_float(row["Latitude"]),
                longitude=_parse_optional_float(row["Longitude"]),
                metadata={
                    "city": city,
                    "demand_type": demand_type,
                },
            )

    return (
        customers,
        domestic_customers,
        export_customers,
        demand_dom,
        demand_exp,
        node_info,
    )


def _load_warehouses(
    warehouses_df: pd.DataFrame,
    config: ExcelLoaderConfig,
    parameter_table: dict[str, Any],
    investment_cost_table: dict[str, dict[str, float]],
) -> tuple[
    list[str],
    list[str],
    list[str],
    list[str],
    dict[str, NodeInfo],
    dict[str, float],
    dict[str, float],
    dict[str, float],
    dict[str, float],
    dict[str, float],
    dict[str, float],
    dict[str, float],
    dict[str, float],
    dict[str, float],
    dict[str, float],
    dict[str, float],
    dict[str, float],
    dict[str, float],
    dict[str, float],
]:
    del parameter_table

    warehouses: list[str] = []
    existing_warehouses: list[str] = []
    candidate_warehouses: list[str] = []
    bulk_eligible_warehouses: list[str] = []

    node_info: dict[str, NodeInfo] = {}

    static_capacity: dict[str, float] = {}
    reception_capacity: dict[str, float] = {}
    shipping_capacity: dict[str, float] = {}

    max_candidate_capacity: dict[str, float] = {}
    opening_fixed_cost: dict[str, float] = {}
    candidate_capacity_cost: dict[str, float] = {}
    max_expand_capacity: dict[str, float] = {}
    expand_fixed_cost: dict[str, float] = {}
    expand_variable_cost: dict[str, float] = {}
    max_bulk_capacity: dict[str, float] = {}
    bulk_fixed_cost: dict[str, float] = {}
    bulk_variable_cost: dict[str, float] = {}
    transshipment_cost: dict[str, float] = {}
    reported_candidate_total_opening_cost: dict[str, float] = {}

    transshipment_cost_column = _first_existing_dataframe_column(
        warehouses_df,
        [
            "Custo de Transbordo ($/t)",
            "Custo de Transbordo (R$/t)",
            "Custo Transbordo ($/t)",
            "Custo Transbordo (R$/t)",
            "Custo_Transbordo ($/t)",
            "Custo_Transbordo (R$/t)",
        ],
    )

    max_expand_capacity_column = _first_existing_dataframe_column(
        warehouses_df,
        [
            "Cap_Expansao_Maxima_Modelo (t)",
            "Cap. Expansão Máxima (t)",
            "Cap. Expansao Maxima (t)",
            "Capacidade Máxima de Expansão (t)",
        ],
    )
    expand_fixed_cost_column = _first_existing_dataframe_column(
        warehouses_df,
        [
            "Custo Fixo Expansão ($)",
            "Custo Fixo Expansao ($)",
            "Custo_Fixo_Expansao ($)",
        ],
    )
    expand_variable_cost_column = _first_existing_dataframe_column(
        warehouses_df,
        [
            "Custo_Expansao_Modelo ($/t)",
            "Custo Variável Expansão ($/t)",
            "Custo Variavel Expansao ($/t)",
            "Custo_Variavel_Expansao ($/t)",
        ],
    )
    max_bulk_capacity_column = _first_existing_dataframe_column(
        warehouses_df,
        [
            "Cap. Granelização Máxima (t)",
            "Cap. Granelizacao Maxima (t)",
            "Capacidade Máxima de Granelização (t)",
        ],
    )
    bulk_fixed_cost_column = _first_existing_dataframe_column(
        warehouses_df,
        [
            "Custo Fixo Granelização ($)",
            "Custo Fixo Granelizacao ($)",
            "Custo_Fixo_Granelizacao ($)",
        ],
    )
    bulk_variable_cost_column = _first_existing_dataframe_column(
        warehouses_df,
        [
            "Custo_Granelizacao_Modelo ($/t)",
            "Custo Variável Granelização ($/t)",
            "Custo Variavel Granelizacao ($/t)",
            "Custo_Variavel_Granelizacao ($/t)",
        ],
    )

    default_expand_variable_cost = _investment_average_cost(
        investment_cost_table,
        "expansao",
    )
    default_bulk_variable_cost = _investment_average_cost(
        investment_cost_table,
        "granelizacao",
    )

    for _, row in warehouses_df.iterrows():
        if _is_blank_row(row, required_fields=["CDA", "Status"]):
            continue

        warehouse = _normalize_text(row["CDA"])
        status = _normalize_text(row["Status"])
        warehouse_type = _normalize_text(row["Tipo"])
        holder = _normalize_text(row["Armazenador"])

        _append_unique(warehouses, warehouse)

        status_norm = status.casefold()
        is_existing = status_norm.startswith("exist")
        is_candidate = status_norm.startswith("candidat")

        if not is_existing and not is_candidate:
            raise ValueError(
                f"Unknown warehouse status {status!r} for warehouse {warehouse!r}."
            )

        if is_existing:
            _append_unique(existing_warehouses, warehouse)

        if is_candidate:
            _append_unique(candidate_warehouses, warehouse)

        if _is_bulk_eligible(row, warehouse_type):
            _append_unique(bulk_eligible_warehouses, warehouse)

        static_capacity[warehouse] = _parse_float(row["Cap. Estática (t)"])
        reception_capacity[warehouse] = _parse_float(row["Cap. Recepção (t)"])
        shipping_capacity[warehouse] = _parse_float(row["Cap. Expedição (t)"])
        transshipment_cost[warehouse] = (
            _first_numeric_value(
                row[transshipment_cost_column],
                config.default_transshipment_cost,
            )
            if transshipment_cost_column is not None
            else config.default_transshipment_cost
        )

        if is_candidate:
            max_capacity = _parse_float(row["Cap. Estática Máxima (t)"])
            reported_total_cost = _parse_float(row["Custo de Abertura ($)"])

            fixed_cost_column = _first_existing_column(
                row,
                [
                    "Custo_Fixo_Abertura_Modelo ($)",
                    "Custo Fixo de Abertura ($)",
                    "Custo_Fixo_Abertura ($)",
                ],
            )

            variable_cost_column = _first_existing_column(
                row,
                [
                    "Custo_Variavel_Capacidade_Modelo ($/t)",
                    "Custo Variável de Capacidade ($/t)",
                    "Custo_Variavel_Capacidade ($/t)",
                ],
            )

            max_candidate_capacity[warehouse] = max_capacity
            reported_candidate_total_opening_cost[warehouse] = reported_total_cost

            if fixed_cost_column is not None or variable_cost_column is not None:
                opening_fixed_cost[warehouse] = (
                    _parse_float(row[fixed_cost_column])
                    if fixed_cost_column is not None
                    else 0.0
                )
                candidate_capacity_cost[warehouse] = (
                    _parse_float(row[variable_cost_column])
                    if variable_cost_column is not None
                    else 0.0
                )

            elif config.candidate_cost_policy == "variable_from_total":
                opening_fixed_cost[warehouse] = 0.0
                candidate_capacity_cost[warehouse] = (
                    reported_total_cost / max_capacity
                    if max_capacity > 0
                    else 0.0
                )

            elif config.candidate_cost_policy == "fixed_total":
                opening_fixed_cost[warehouse] = reported_total_cost
                candidate_capacity_cost[warehouse] = 0.0

            else:
                raise ValueError(
                    f"Invalid candidate_cost_policy={config.candidate_cost_policy!r}."
                )

        expansion_allowed = _is_optional_feature_enabled(
            row,
            ["Permite_Expansao", "Permite_Expansão"],
        )

        if (
            is_existing
            and expansion_allowed
            and max_expand_capacity_column is not None
        ):
            max_expansion = _parse_float(row[max_expand_capacity_column])
            if max_expansion > 0.0:
                max_expand_capacity[warehouse] = max_expansion
                expand_fixed_cost[warehouse] = _first_numeric_value(
                    row[expand_fixed_cost_column]
                    if expand_fixed_cost_column is not None
                    else None,
                    0.0,
                )
                expand_variable_cost[warehouse] = _first_numeric_value(
                    row[expand_variable_cost_column]
                    if expand_variable_cost_column is not None
                    else None,
                    default_expand_variable_cost,
                )

        if warehouse in bulk_eligible_warehouses:
            max_bulk = (
                _parse_float(row[max_bulk_capacity_column])
                if max_bulk_capacity_column is not None
                else static_capacity[warehouse]
            )
            if max_bulk > 0.0:
                max_bulk_capacity[warehouse] = max_bulk
                bulk_fixed_cost[warehouse] = _first_numeric_value(
                    row[bulk_fixed_cost_column]
                    if bulk_fixed_cost_column is not None
                    else None,
                    0.0,
                )
                bulk_variable_cost[warehouse] = _first_numeric_value(
                    row[bulk_variable_cost_column]
                    if bulk_variable_cost_column is not None
                    else None,
                    default_bulk_variable_cost,
                )

        node_info[warehouse] = NodeInfo(
            node_id=warehouse,
            node_type="warehouse",
            name=f"{_normalize_text(row['Município'])} - {_normalize_text(row['UF'])}",
            state=_normalize_text(row["UF"]).upper(),
            municipality=_normalize_text(row["Município"]),
            latitude=_parse_optional_float(row["Latitude"]),
            longitude=_parse_optional_float(row["Longitude"]),
            metadata={
                "status": status,
                "holder": holder,
                "type": warehouse_type,
            },
        )

    return (
        warehouses,
        existing_warehouses,
        candidate_warehouses,
        bulk_eligible_warehouses,
        node_info,
        static_capacity,
        reception_capacity,
        shipping_capacity,
        max_candidate_capacity,
        opening_fixed_cost,
        candidate_capacity_cost,
        max_expand_capacity,
        expand_fixed_cost,
        expand_variable_cost,
        max_bulk_capacity,
        bulk_fixed_cost,
        bulk_variable_cost,
        transshipment_cost,
        reported_candidate_total_opening_cost,
    )


# ---------------------------------------------------------------------
# Cost and parameter tables
# ---------------------------------------------------------------------


def _build_freight_by_state(frete: pd.DataFrame) -> dict[str, float]:
    return {
        _normalize_text(row["Estado"]).upper(): _parse_float(row["Frete Tonelada Km"])
        for _, row in frete.iterrows()
        if not _is_blank_row(row, required_fields=["Estado"])
    }


def _build_storage_tariff_table(tarifa: pd.DataFrame) -> dict[str, dict[str, float]]:
    table: dict[str, dict[str, float]] = {}

    for _, row in tarifa.iterrows():
        if _is_blank_row(row, required_fields=["Produto"]):
            continue

        product = _normalize_text(row["Produto"])
        table[product] = {
            "public": _parse_float(row["Armazenar_Publico"]),
            "private": _parse_float(row["Armazenar_Privado"]),
        }

    return table


def _build_investment_cost_table(custo_invest: pd.DataFrame) -> dict[str, dict[str, float]]:
    table: dict[str, dict[str, float]] = {}

    for _, row in custo_invest.iterrows():
        if _is_blank_row(row, required_fields=["Tipo"]):
            continue

        investment_type = _normalize_text(row["Tipo"])
        low = _parse_float(row["Custo Baixo (R$/t)"])
        high = _parse_float(row["Custo Alto (R$/t)"])

        table[investment_type] = {
            "low": low,
            "high": high,
            "average": (low + high) / 2.0,
        }

    return table


def _investment_average_cost(
    investment_cost_table: dict[str, dict[str, float]],
    investment_type: str,
) -> float:
    target = _fold_text(investment_type)

    for name, costs in investment_cost_table.items():
        if target in _fold_text(name):
            return float(costs.get("average", 0.0))

    return 0.0


def _build_parameter_table(parametros_modelo: pd.DataFrame) -> dict[str, Any]:
    if parametros_modelo.empty:
        return {}

    possible_name_columns = ["Parametro", "Parâmetro", "Nome"]
    possible_value_columns = ["Valor", "Valor_Modelo", "Valor Modelo"]

    name_column = _first_existing_dataframe_column(parametros_modelo, possible_name_columns)
    value_column = _first_existing_dataframe_column(parametros_modelo, possible_value_columns)

    if name_column is None or value_column is None:
        return {}

    table: dict[str, Any] = {}

    for _, row in parametros_modelo.iterrows():
        if _is_blank_row(row, required_fields=[name_column]):
            continue

        table[_normalize_text(row[name_column])] = row[value_column]

    return table


def _expand_storage_tariffs(
    warehouses: list[str],
    products: list[str],
    warehouse_node_info: dict[str, NodeInfo],
    storage_tariff_table: dict[str, dict[str, float]],
) -> dict[tuple[str, str], float]:
    storage_tariff: dict[tuple[str, str], float] = {}

    for warehouse in warehouses:
        info = warehouse_node_info[warehouse]
        holder = str(info.metadata.get("holder", ""))

        is_public = "COMPANHIA NACIONAL DE ABASTECIMENTO" in holder.upper()
        tariff_kind = "public" if is_public else "private"

        for product in products:
            product_table = storage_tariff_table.get(product)
            if product_table is None:
                product_table = storage_tariff_table.get("Outros")

            storage_tariff[(warehouse, product)] = (
                product_table[tariff_kind]
                if product_table is not None
                else 0.0
            )

    return storage_tariff


# ---------------------------------------------------------------------
# Demand helpers
# ---------------------------------------------------------------------


def _build_supply_total_by_product_period(
    origins: list[str],
    products: list[str],
    periods: list[str],
    supply: dict[tuple[str, str, str], float],
) -> dict[tuple[str, str], float]:
    totals: dict[tuple[str, str], float] = {}

    for product in products:
        for period in periods:
            totals[(product, period)] = sum(
                supply.get((origin, product, period), 0.0)
                for origin in origins
            )

    return totals


def _normalize_demand_type(value: Any) -> str:
    text = _normalize_text(value).upper()

    if text in {"", "DOMESTICA", "DOMÉSTICA", "DOMESTIC"}:
        return "DOMESTICA"

    if text in {"EXPORTACAO", "EXPORTAÇÃO", "EXPORT", "EXPORTATION"}:
        return "EXPORTACAO"

    return text


def _normalize_limit_rule(value: Any) -> str:
    text = _normalize_text(value).upper()

    if text in {"", "FIXO", "FIXED"}:
        return "FIXO"

    if text in {
        "AUTO_OFERTA_TOTAL_PRODUTO_PERIODO",
        "AUTO_SUPPLY_TOTAL_PRODUCT_PERIOD",
    }:
        return "AUTO_OFERTA_TOTAL_PRODUTO_PERIODO"

    return text


def _collect_demand_types_by_city(
    demanda: pd.DataFrame,
    has_new_schema: bool,
) -> dict[str, set[str]]:
    demand_types_by_city: dict[str, set[str]] = {}

    for _, row in demanda.iterrows():
        if _is_blank_row(row, required_fields=["Produto", "Cidade", "Data"]):
            continue

        city = _normalize_text(row["Cidade"])

        if has_new_schema:
            demand_type = _normalize_demand_type(row["Tipo_Demanda"])
        elif _is_infinity_token(row["Peso (ton)"]):
            demand_type = "EXPORTACAO"
        else:
            demand_type = "DOMESTICA"

        demand_types_by_city.setdefault(city, set()).add(demand_type)

    return demand_types_by_city


def _resolve_customer_id(
    row: pd.Series,
    city: str,
    demand_type: str,
    demand_types_by_city: dict[str, set[str]],
    config: ExcelLoaderConfig,
) -> str:
    if config.demand_node_id_column in row.index:
        explicit_id = _normalize_text(row[config.demand_node_id_column])

        if explicit_id:
            return explicit_id

    if (
        config.split_overlapping_demand_nodes
        and len(demand_types_by_city.get(city, set())) > 1
    ):
        return f"{city} | {demand_type}"

    return city

# ---------------------------------------------------------------------
# Distance helpers
# ---------------------------------------------------------------------


def _build_distance_matrix_from_routes(
    pairs: list[tuple[str, str]],
    node_info: dict[str, NodeInfo],
) -> dict[tuple[str, str], float]:
    distances: dict[tuple[str, str], float] = {}

    for origin, destination in pairs:
        if (origin, destination) in distances:
            continue

        origin_info = node_info[origin]
        destination_info = node_info[destination]

        distances[(origin, destination)] = _haversine_km(
            origin_info.latitude,
            origin_info.longitude,
            destination_info.latitude,
            destination_info.longitude,
        )

    return distances


def _haversine_km(
    lat1: float | None,
    lon1: float | None,
    lat2: float | None,
    lon2: float | None,
) -> float:
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        raise ValueError("Cannot compute Haversine distance with missing coordinates.")

    radius_km = 6371.0088

    phi1 = radians(lat1)
    phi2 = radians(lat2)
    delta_phi = radians(lat2 - lat1)
    delta_lambda = radians(lon2 - lon1)

    a = (
        sin(delta_phi / 2.0) ** 2
        + cos(phi1) * cos(phi2) * sin(delta_lambda / 2.0) ** 2
    )

    return 2.0 * radius_km * asin(sqrt(a))


# ---------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------


def _unique_strings(values: pd.Series) -> list[str]:
    result: list[str] = []

    for value in values.tolist():
        text = _normalize_text(value)
        if text:
            _append_unique(result, text)

    return result


def _ordered_union(*groups: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for group in groups:
        for value in group:
            if value and value not in seen:
                seen.add(value)
                result.append(value)

    return result


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _add_to_mapping(
    mapping: dict[tuple[str, str, str], float],
    key: tuple[str, str, str],
    value: float,
) -> None:
    mapping[key] = mapping.get(key, 0.0) + value


def _normalize_text(value: Any) -> str:
    if pd.isna(value):
        return ""

    return str(value).strip()


def _fold_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _normalize_text(value).casefold())
    return "".join(character for character in text if not unicodedata.combining(character))


def _scenario_slug(value: Any) -> str:
    return "_".join(_fold_text(value).replace("-", " ").split())


def _normalize_period(value: Any) -> str:
    if pd.isna(value):
        raise ValueError("Period/Data cannot be empty.")

    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m")

    return str(value).strip()


def _parse_float(value: Any) -> float:
    if pd.isna(value):
        return 0.0

    if _is_infinity_token(value):
        raise ValueError("Infinity token cannot be parsed as a finite float.")

    if isinstance(value, str):
        text = value.strip()

        if not text:
            return 0.0

        if "," in text and "." not in text:
            text = text.replace(",", ".")

        return float(text)

    return float(value)


def _parse_optional_float(value: Any) -> float | None:
    if pd.isna(value):
        return None

    return _parse_float(value)


def _first_numeric_value(*values: Any) -> float:
    for value in values:
        if value is None:
            continue

        if pd.isna(value):
            continue

        if _is_infinity_token(value):
            continue

        text = str(value).strip()

        if text:
            return _parse_float(value)

    return 0.0


def _is_infinity_token(value: Any) -> bool:
    if pd.isna(value):
        return False

    text = str(value).strip().casefold()

    return text in {
        "∞",
        "inf",
        "+inf",
        "infinity",
        "+infinity",
        "infinito",
        "ilimitado",
    }


def _state_from_city(city: str) -> str | None:
    if " - " not in city:
        return None

    return city.rsplit(" - ", 1)[-1].strip().upper()


def _lookup_freight_for_city(
    city: str,
    freight_by_state: dict[str, float],
) -> float:
    state = _state_from_city(city)

    if state is None:
        return 0.0

    if state not in freight_by_state:
        raise ValueError(f"Missing freight rate for state {state!r}, city {city!r}.")

    return freight_by_state[state]


def _is_blank_row(row: pd.Series, required_fields: list[str]) -> bool:
    return all(_normalize_text(row.get(field, "")) == "" for field in required_fields)


def _first_existing_column(row: pd.Series, candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in row.index:
            return candidate

    return None


def _first_existing_dataframe_column(
    df: pd.DataFrame,
    candidates: list[str],
) -> str | None:
    for candidate in candidates:
        if candidate in df.columns:
            return candidate

    return None


def _is_yes(value: Any) -> bool:
    text = _normalize_text(value).upper()
    return text in {"SIM", "S", "YES", "Y", "TRUE", "1"}


def _is_optional_feature_enabled(row: pd.Series, candidates: list[str]) -> bool:
    column = _first_existing_column(row, candidates)
    return True if column is None else _is_yes(row[column])


def _is_bulk_eligible(row: pd.Series, warehouse_type: str) -> bool:
    explicit_column = _first_existing_column(
        row,
        [
            "Permite_Granelizacao",
            "Permite_Granelização",
            "Elegivel_Granelizacao",
            "Elegível_Granelização",
        ],
    )

    if explicit_column is not None:
        return _is_yes(row[explicit_column])

    normalized = warehouse_type.casefold()

    return any(
        token in normalized
        for token in [
            "convencional",
            "depósito",
            "deposito",
            "estrutural",
        ]
    )
