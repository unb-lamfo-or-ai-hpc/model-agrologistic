"""
Excel loader for agricultural logistics model data.

This module converts a structured .xlsx workbook into the canonical ModelData
object used by optimization backends.

It may import pandas/openpyxl-related libraries through pandas, because this
is an ETL module.

It must not import:
- gurobipy
- pyomo
"""

from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from src.logic.model_data import ModelData, NodeInfo


CandidateCostPolicy = Literal[
    "variable_from_total",
    "fixed_total",
]


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


@dataclass(slots=True)
class ExcelLoaderConfig:
    """
    Configuration for loading ModelData from Excel.

    The loader is deliberately independent of solver choices. It only prepares
    sets, parameters, routes, metadata, and optional Haversine distances.
    """

    include_export_routes: bool = True
    include_transshipment_routes: bool = False
    include_direct_origin_customer_routes: bool = False

    compute_haversine_distances: bool = True

    # Current Excel has "Custo de Abertura ($)" and "Cap. Estática Máxima (t)".
    #
    # variable_from_total:
    #   opening_fixed_cost[d] = 0
    #   candidate_capacity_cost[d] = total_opening_cost / max_capacity
    #
    # fixed_total:
    #   opening_fixed_cost[d] = total_opening_cost
    #   candidate_capacity_cost[d] = 0
    candidate_cost_policy: CandidateCostPolicy = "variable_from_total"

    default_unmet_demand_penalty: float = 1_000_000.0
    default_emergency_static_penalty: float = 1_000_000.0
    default_emergency_reception_penalty: float = 1_000_000.0

    default_transshipment_cost: float = 0.0


def load_model_data_from_excel(
    path: str | Path,
    config: ExcelLoaderConfig | None = None,
) -> ModelData:
    """
    Load a structured Excel workbook into ModelData.

    Parameters
    ----------
    path:
        Path to the .xlsx file.

    config:
        Optional loader configuration.

    Returns
    -------
    ModelData
        Canonical model data ready for validation and optimization.
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

    freight_by_state = _build_freight_by_state(frete)
    storage_tariff_table = _build_storage_tariff_table(tarifa)
    investment_cost_table = _build_investment_cost_table(custo_invest)

    origins, supply, origin_node_info = _load_supply(oferta)
    (
        customers,
        domestic_customers,
        export_customers,
        demand_dom,
        demand_exp,
        customer_node_info,
        unbounded_export_demand_keys,
    ) = _load_demand(demanda)

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
        reported_candidate_total_opening_cost,
    ) = _load_warehouses(
        warehouses_df=warehouses_df,
        config=config,
    )

    products = _ordered_union(
        _unique_strings(oferta["Produto"]),
        _unique_strings(demanda["Produto"]),
    )

    periods = _ordered_union(
        [_normalize_period(value) for value in oferta["Data"].tolist()],
        [_normalize_period(value) for value in demanda["Data"].tolist()],
    )

    freight_origin = {
        origin: _lookup_freight_for_city(origin, freight_by_state)
        for origin in origins
    }

    freight_dest = {
        customer: _lookup_freight_for_city(customer, freight_by_state)
        for customer in customers
    }

    transshipment_cost = {
        warehouse: config.default_transshipment_cost
        for warehouse in warehouses
    }

    storage_tariff = _expand_storage_tariffs(
        warehouses=warehouses,
        products=products,
        warehouse_node_info=warehouse_node_info,
        storage_tariff_table=storage_tariff_table,
    )

    routes_od = {
        (origin, warehouse, product)
        for origin in origins
        for warehouse in warehouses
        for product in products
    }

    route_customers = list(domestic_customers)

    if config.include_export_routes:
        route_customers = _ordered_union(route_customers, export_customers)

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
            [(origin, warehouse) for origin, warehouse, _product in routes_od],
            node_info,
        )

        dist_dc = _build_distance_matrix_from_routes(
            [(warehouse, customer) for warehouse, customer, _product in routes_dc],
            node_info,
        )

        dist_dd = _build_distance_matrix_from_routes(
            [(warehouse_from, warehouse_to) for warehouse_from, warehouse_to, _product in routes_dd],
            node_info,
        )

        dist_oc = _build_distance_matrix_from_routes(
            [(origin, customer) for origin, customer, _product in routes_oc],
            node_info,
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
        dist_od=dist_od,
        dist_dc=dist_dc,
        dist_dd=dist_dd,
        dist_oc=dist_oc,
        freight_origin=freight_origin,
        freight_dest=freight_dest,
        transshipment_cost=transshipment_cost,
        storage_tariff=storage_tariff,
        static_capacity=static_capacity,
        reception_capacity=reception_capacity,
        shipping_capacity=shipping_capacity,
        max_candidate_capacity=max_candidate_capacity,
        opening_fixed_cost=opening_fixed_cost,
        candidate_capacity_cost=candidate_capacity_cost,
        unmet_demand_penalty=unmet_demand_penalty,
        emergency_static_capacity_penalty=emergency_static_capacity_penalty,
        emergency_reception_capacity_penalty=emergency_reception_capacity_penalty,
        node_info=node_info,
        metadata={
            "source_excel": str(path),
            "loader": "excel_loader.load_model_data_from_excel",
            "candidate_cost_policy": config.candidate_cost_policy,
            "unbounded_export_demand_keys": unbounded_export_demand_keys,
            "reported_candidate_total_opening_cost": reported_candidate_total_opening_cost,
            "investment_cost_table": investment_cost_table,
        },
    )


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


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    cleaned.columns = [str(column).strip() for column in cleaned.columns]
    return cleaned


# ---------------------------------------------------------------------
# Sheet loaders
# ---------------------------------------------------------------------


def _load_supply(
    oferta: pd.DataFrame,
) -> tuple[list[str], dict[tuple[str, str, str], float], dict[str, NodeInfo]]:
    origins: list[str] = []
    supply: dict[tuple[str, str, str], float] = {}
    node_info: dict[str, NodeInfo] = {}

    for _, row in oferta.iterrows():
        product = _normalize_text(row["Produto"])
        city = _normalize_text(row["Cidade"])
        period = _normalize_period(row["Data"])
        weight, is_unbounded = _parse_quantity(row["Peso (ton)"])

        if is_unbounded:
            raise ValueError("Supply cannot be infinite/unbounded.")

        if city not in origins:
            origins.append(city)

        supply[(city, product, period)] = weight

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
) -> tuple[
    list[str],
    list[str],
    list[str],
    dict[tuple[str, str, str], float],
    dict[tuple[str, str, str], float],
    dict[str, NodeInfo],
    list[dict[str, str]],
]:
    customers: list[str] = []
    domestic_customers: list[str] = []
    export_customers: list[str] = []

    demand_dom: dict[tuple[str, str, str], float] = {}
    demand_exp: dict[tuple[str, str, str], float] = {}

    node_info: dict[str, NodeInfo] = {}
    unbounded_export_demand_keys: list[dict[str, str]] = []

    for _, row in demanda.iterrows():
        product = _normalize_text(row["Produto"])
        city = _normalize_text(row["Cidade"])
        period = _normalize_period(row["Data"])
        weight, is_unbounded = _parse_quantity(row["Peso (ton)"])

        if city not in customers:
            customers.append(city)

        if is_unbounded:
            if city not in export_customers:
                export_customers.append(city)

            unbounded_export_demand_keys.append(
                {
                    "customer": city,
                    "product": product,
                    "period": period,
                }
            )
        else:
            if city not in domestic_customers:
                domestic_customers.append(city)

            demand_dom[(city, product, period)] = weight

        if city not in node_info:
            node_info[city] = NodeInfo(
                node_id=city,
                node_type="customer",
                name=city,
                state=_state_from_city(city),
                latitude=_parse_optional_float(row["Latitude"]),
                longitude=_parse_optional_float(row["Longitude"]),
            )

    overlap = set(domestic_customers).intersection(export_customers)

    if overlap:
        raise ValueError(
            "A demand node cannot be both domestic and export in the current "
            f"Excel schema. Overlap: {sorted(overlap)}"
        )

    return (
        customers,
        domestic_customers,
        export_customers,
        demand_dom,
        demand_exp,
        node_info,
        unbounded_export_demand_keys,
    )


def _load_warehouses(
    warehouses_df: pd.DataFrame,
    config: ExcelLoaderConfig,
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
]:
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
    reported_candidate_total_opening_cost: dict[str, float] = {}

    for _, row in warehouses_df.iterrows():
        warehouse = _normalize_text(row["CDA"])
        status = _normalize_text(row["Status"])
        warehouse_type = _normalize_text(row["Tipo"])
        holder = _normalize_text(row["Armazenador"])

        if warehouse not in warehouses:
            warehouses.append(warehouse)

        is_existing = status.casefold().startswith("exist")
        is_candidate = status.casefold().startswith("candidat")

        if not is_existing and not is_candidate:
            raise ValueError(
                f"Unknown warehouse status {status!r} for warehouse {warehouse!r}."
            )

        if is_existing:
            existing_warehouses.append(warehouse)

        if is_candidate:
            candidate_warehouses.append(warehouse)

        if _is_bulk_eligible_type(warehouse_type):
            bulk_eligible_warehouses.append(warehouse)

        static_capacity[warehouse] = _parse_float(row["Cap. Estática (t)"])
        reception_capacity[warehouse] = _parse_float(row["Cap. Recepção (t)"])
        shipping_capacity[warehouse] = _parse_float(row["Cap. Expedição (t)"])

        if is_candidate:
            max_capacity = _parse_float(row["Cap. Estática Máxima (t)"])
            total_opening_cost = _parse_float(row["Custo de Abertura ($)"])

            max_candidate_capacity[warehouse] = max_capacity
            reported_candidate_total_opening_cost[warehouse] = total_opening_cost

            if config.candidate_cost_policy == "variable_from_total":
                opening_fixed_cost[warehouse] = 0.0
                candidate_capacity_cost[warehouse] = (
                    total_opening_cost / max_capacity
                    if max_capacity > 0
                    else 0.0
                )
            elif config.candidate_cost_policy == "fixed_total":
                opening_fixed_cost[warehouse] = total_opening_cost
                candidate_capacity_cost[warehouse] = 0.0
            else:
                raise ValueError(
                    f"Invalid candidate_cost_policy: {config.candidate_cost_policy!r}"
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
        reported_candidate_total_opening_cost,
    )


# ---------------------------------------------------------------------
# Cost tables
# ---------------------------------------------------------------------


def _build_freight_by_state(frete: pd.DataFrame) -> dict[str, float]:
    return {
        _normalize_text(row["Estado"]).upper(): _parse_float(row["Frete Tonelada Km"])
        for _, row in frete.iterrows()
    }


def _build_storage_tariff_table(tarifa: pd.DataFrame) -> dict[str, dict[str, float]]:
    table: dict[str, dict[str, float]] = {}

    for _, row in tarifa.iterrows():
        product = _normalize_text(row["Produto"])
        table[product] = {
            "public": _parse_float(row["Armazenar_Publico"]),
            "private": _parse_float(row["Armazenar_Privado"]),
        }

    return table


def _build_investment_cost_table(custo_invest: pd.DataFrame) -> dict[str, dict[str, float]]:
    table: dict[str, dict[str, float]] = {}

    for _, row in custo_invest.iterrows():
        investment_type = _normalize_text(row["Tipo"])
        low = _parse_float(row["Custo Baixo (R$/t)"])
        high = _parse_float(row["Custo Alto (R$/t)"])

        table[investment_type] = {
            "low": low,
            "high": high,
            "average": (low + high) / 2.0,
        }

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

            if product_table is None:
                storage_tariff[(warehouse, product)] = 0.0
            else:
                storage_tariff[(warehouse, product)] = product_table[tariff_kind]

    return storage_tariff


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
        if text not in result:
            result.append(text)

    return result


def _ordered_union(*groups: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for group in groups:
        for value in group:
            if value not in seen:
                seen.add(value)
                result.append(value)

    return result


def _normalize_text(value: Any) -> str:
    if pd.isna(value):
        return ""

    return str(value).strip()


def _normalize_period(value: Any) -> str:
    if pd.isna(value):
        raise ValueError("Period/Data cannot be empty.")

    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m")

    return str(value).strip()


def _parse_quantity(value: Any) -> tuple[float, bool]:
    if _is_infinity_token(value):
        return 0.0, True

    return _parse_float(value), False


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


def _parse_float(value: Any) -> float:
    if pd.isna(value):
        return 0.0

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


def _is_bulk_eligible_type(warehouse_type: str) -> bool:
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