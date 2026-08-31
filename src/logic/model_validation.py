"""
Validation utilities for agricultural logistics model data.

This module checks whether a ModelData instance is structurally consistent
before it is passed to an optimization backend.

It must not import:
- gurobipy
- pyomo
- pandas
- torch
- dash
- plotly
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isclose, isfinite
from typing import Mapping

from src.logic.model_config import ModelConfig
from src.logic.model_data import ModelData


@dataclass(slots=True)
class ValidationIssue:
    """One validation error or warning."""

    code: str
    message: str
    location: str | None = None

    def __str__(self) -> str:
        if self.location:
            return f"{self.code} at {self.location}: {self.message}"
        return f"{self.code}: {self.message}"


@dataclass(slots=True)
class ValidationResult:
    """Container for validation errors and warnings."""

    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def add_error(
        self,
        code: str,
        message: str,
        location: str | None = None,
    ) -> None:
        self.errors.append(ValidationIssue(code=code, message=message, location=location))

    def add_warning(
        self,
        code: str,
        message: str,
        location: str | None = None,
    ) -> None:
        self.warnings.append(ValidationIssue(code=code, message=message, location=location))


class ModelDataValidationError(ValueError):
    """Raised when model data validation fails."""


def validate_or_raise_model_data(
    data: ModelData,
    config: ModelConfig | None = None,
    *,
    require_distances: bool = True,
) -> None:
    """
    Validate model data and raise ModelDataValidationError if invalid.
    """

    result = validate_model_data(
        data=data,
        config=config,
        require_distances=require_distances,
    )

    if not result.is_valid:
        message = "Invalid ModelData:\n" + "\n".join(
            f"- {issue}" for issue in result.errors
        )
        raise ModelDataValidationError(message)


def validate_model_data(
    data: ModelData,
    config: ModelConfig | None = None,
    *,
    require_distances: bool = True,
) -> ValidationResult:
    """
    Validate a ModelData object.

    Parameters
    ----------
    data:
        Canonical model data.

    config:
        Mathematical model configuration. If None, the default ModelConfig
        is used.

    require_distances:
        If True, every declared route must have a distance entry.
        This should be True for optimization runs and may be False for early
        ETL tests.

    Returns
    -------
    ValidationResult
        Errors and warnings found during validation.
    """

    if config is None:
        config = ModelConfig()

    result = ValidationResult()

    _validate_core_sets(data, result)
    _validate_subsets(data, result)
    _validate_nonnegative_parameters(data, result)
    _validate_routes(data, result)

    if require_distances:
        _validate_distances(data, result)

    _validate_capacity_and_cost_parameters(data, config, result)
    _validate_stochastic_structure(data, config, result)
    _validate_connectivity(data, config, result)

    return result


# ---------------------------------------------------------------------
# Core set validation
# ---------------------------------------------------------------------


def _validate_core_sets(data: ModelData, result: ValidationResult) -> None:
    required_sets = {
        "origins": data.origins,
        "warehouses": data.warehouses,
        "customers": data.customers,
        "products": data.products,
        "periods": data.periods,
    }

    for name, values in required_sets.items():
        if not values:
            result.add_error(
                code="EMPTY_SET",
                message=f"{name} must not be empty.",
                location=name,
            )

        _validate_no_duplicates(name, values, result)


def _validate_no_duplicates(
    name: str,
    values: list[str],
    result: ValidationResult,
) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()

    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)

    if duplicates:
        result.add_error(
            code="DUPLICATE_VALUES",
            message=f"{name} contains duplicated values: {sorted(duplicates)}.",
            location=name,
        )


def _validate_subsets(data: ModelData, result: ValidationResult) -> None:
    _validate_subset(
        subset_name="existing_warehouses",
        subset=data.existing_warehouses,
        superset_name="warehouses",
        superset=data.warehouses,
        result=result,
    )

    _validate_subset(
        subset_name="candidate_warehouses",
        subset=data.candidate_warehouses,
        superset_name="warehouses",
        superset=data.warehouses,
        result=result,
    )

    _validate_subset(
        subset_name="bulk_eligible_warehouses",
        subset=data.bulk_eligible_warehouses,
        superset_name="warehouses",
        superset=data.warehouses,
        result=result,
    )

    _validate_subset(
        subset_name="domestic_customers",
        subset=data.domestic_customers,
        superset_name="customers",
        superset=data.customers,
        result=result,
    )

    _validate_subset(
        subset_name="export_customers",
        subset=data.export_customers,
        superset_name="customers",
        superset=data.customers,
        result=result,
    )

    overlap = set(data.domestic_customers).intersection(data.export_customers)
    if overlap:
        result.add_error(
            code="DOMESTIC_EXPORT_OVERLAP",
            message=(
                "domestic_customers and export_customers must be disjoint. "
                f"Overlap: {sorted(overlap)}."
            ),
            location="customers",
        )


def _validate_subset(
    subset_name: str,
    subset: list[str],
    superset_name: str,
    superset: list[str],
    result: ValidationResult,
) -> None:
    missing = sorted(set(subset) - set(superset))

    if missing:
        result.add_error(
            code="INVALID_SUBSET",
            message=(
                f"{subset_name} contains values not present in "
                f"{superset_name}: {missing}."
            ),
            location=subset_name,
        )


# ---------------------------------------------------------------------
# Numeric parameter validation
# ---------------------------------------------------------------------


def _validate_nonnegative_parameters(
    data: ModelData,
    result: ValidationResult,
) -> None:
    mappings: dict[str, Mapping[object, float]] = {
        "supply": data.supply,
        "demand_dom": data.demand_dom,
        "demand_exp": data.demand_exp,
        "supply_s": data.supply_s,
        "demand_dom_s": data.demand_dom_s,
        "demand_exp_s": data.demand_exp_s,
        "dist_od": data.dist_od,
        "dist_dc": data.dist_dc,
        "dist_dd": data.dist_dd,
        "dist_oc": data.dist_oc,
        "duration_od": data.duration_od,
        "duration_dc": data.duration_dc,
        "duration_dd": data.duration_dd,
        "duration_oc": data.duration_oc,
        "freight_origin": data.freight_origin,
        "freight_dest": data.freight_dest,
        "freight_warehouse": data.freight_warehouse,
        "transshipment_cost": data.transshipment_cost,
        "storage_tariff": data.storage_tariff,
        "static_capacity": data.static_capacity,
        "reception_capacity": data.reception_capacity,
        "shipping_capacity": data.shipping_capacity,
        "max_candidate_capacity": data.max_candidate_capacity,
        "opening_fixed_cost": data.opening_fixed_cost,
        "candidate_capacity_cost": data.candidate_capacity_cost,
        "max_expand_capacity": data.max_expand_capacity,
        "expand_fixed_cost": data.expand_fixed_cost,
        "expand_variable_cost": data.expand_variable_cost,
        "max_bulk_capacity": data.max_bulk_capacity,
        "bulk_fixed_cost": data.bulk_fixed_cost,
        "bulk_variable_cost": data.bulk_variable_cost,
        "initial_inventory": data.initial_inventory,
        "unmet_demand_penalty": data.unmet_demand_penalty,
        "emergency_static_capacity_penalty": data.emergency_static_capacity_penalty,
        "emergency_reception_capacity_penalty": data.emergency_reception_capacity_penalty,
    }

    for name, mapping in mappings.items():
        _validate_nonnegative_mapping(name, mapping, result)


def _validate_nonnegative_mapping(
    name: str,
    mapping: Mapping[object, float],
    result: ValidationResult,
) -> None:
    for key, value in mapping.items():
        if not _is_valid_number(value):
            result.add_error(
                code="INVALID_NUMERIC_VALUE",
                message=f"{name}[{key!r}] must be a finite number.",
                location=name,
            )
            continue

        if value < 0:
            result.add_error(
                code="NEGATIVE_VALUE",
                message=f"{name}[{key!r}] must be non-negative.",
                location=name,
            )


def _is_valid_number(value: object) -> bool:
    if isinstance(value, bool):
        return False

    if not isinstance(value, (int, float)):
        return False

    return isfinite(float(value))


# ---------------------------------------------------------------------
# Route and distance validation
# ---------------------------------------------------------------------


def _validate_routes(data: ModelData, result: ValidationResult) -> None:
    for origin, warehouse, product in data.routes_od:
        if origin not in data.origins:
            result.add_error(
                code="INVALID_ROUTE_NODE",
                message=f"Unknown origin {origin!r} in OD route.",
                location="routes_od",
            )
        if warehouse not in data.warehouses:
            result.add_error(
                code="INVALID_ROUTE_NODE",
                message=f"Unknown warehouse {warehouse!r} in OD route.",
                location="routes_od",
            )
        if product not in data.products:
            result.add_error(
                code="INVALID_ROUTE_PRODUCT",
                message=f"Unknown product {product!r} in OD route.",
                location="routes_od",
            )

    for warehouse, customer, product in data.routes_dc:
        if warehouse not in data.warehouses:
            result.add_error(
                code="INVALID_ROUTE_NODE",
                message=f"Unknown warehouse {warehouse!r} in DC route.",
                location="routes_dc",
            )
        if customer not in data.customers:
            result.add_error(
                code="INVALID_ROUTE_NODE",
                message=f"Unknown customer {customer!r} in DC route.",
                location="routes_dc",
            )
        if product not in data.products:
            result.add_error(
                code="INVALID_ROUTE_PRODUCT",
                message=f"Unknown product {product!r} in DC route.",
                location="routes_dc",
            )

    for warehouse_from, warehouse_to, product in data.routes_dd:
        if warehouse_from not in data.warehouses:
            result.add_error(
                code="INVALID_ROUTE_NODE",
                message=f"Unknown origin warehouse {warehouse_from!r} in DD route.",
                location="routes_dd",
            )
        if warehouse_to not in data.warehouses:
            result.add_error(
                code="INVALID_ROUTE_NODE",
                message=f"Unknown destination warehouse {warehouse_to!r} in DD route.",
                location="routes_dd",
            )
        if warehouse_from == warehouse_to:
            result.add_error(
                code="SELF_TRANSSHIPMENT_ROUTE",
                message=f"Warehouse-to-warehouse route cannot be self-loop: {warehouse_from!r}.",
                location="routes_dd",
            )
        if product not in data.products:
            result.add_error(
                code="INVALID_ROUTE_PRODUCT",
                message=f"Unknown product {product!r} in DD route.",
                location="routes_dd",
            )

    for origin, customer, product in data.routes_oc:
        if origin not in data.origins:
            result.add_error(
                code="INVALID_ROUTE_NODE",
                message=f"Unknown origin {origin!r} in OC route.",
                location="routes_oc",
            )
        if customer not in data.customers:
            result.add_error(
                code="INVALID_ROUTE_NODE",
                message=f"Unknown customer {customer!r} in OC route.",
                location="routes_oc",
            )
        if product not in data.products:
            result.add_error(
                code="INVALID_ROUTE_PRODUCT",
                message=f"Unknown product {product!r} in OC route.",
                location="routes_oc",
            )


def _validate_distances(data: ModelData, result: ValidationResult) -> None:
    for origin, warehouse, _product in data.routes_od:
        _require_distance(
            matrix_name="dist_od",
            matrix=data.dist_od,
            pair=(origin, warehouse),
            result=result,
        )

    for warehouse, customer, _product in data.routes_dc:
        _require_distance(
            matrix_name="dist_dc",
            matrix=data.dist_dc,
            pair=(warehouse, customer),
            result=result,
        )

    for warehouse_from, warehouse_to, _product in data.routes_dd:
        _require_distance(
            matrix_name="dist_dd",
            matrix=data.dist_dd,
            pair=(warehouse_from, warehouse_to),
            result=result,
        )

    for origin, customer, _product in data.routes_oc:
        _require_distance(
            matrix_name="dist_oc",
            matrix=data.dist_oc,
            pair=(origin, customer),
            result=result,
        )


def _require_distance(
    matrix_name: str,
    matrix: Mapping[tuple[str, str], float],
    pair: tuple[str, str],
    result: ValidationResult,
) -> None:
    if pair not in matrix:
        result.add_error(
            code="MISSING_DISTANCE",
            message=f"Missing distance for pair {pair!r}.",
            location=matrix_name,
        )


# ---------------------------------------------------------------------
# Capacity and cost validation
# ---------------------------------------------------------------------


def _validate_capacity_and_cost_parameters(
    data: ModelData,
    config: ModelConfig,
    result: ValidationResult,
) -> None:
    dd_origins = {warehouse_from for warehouse_from, _, _ in data.routes_dd}
    dd_destinations = {warehouse_to for _, warehouse_to, _ in data.routes_dd}

    for warehouse in sorted(dd_origins):
        _require_key(data.freight_warehouse, warehouse, "freight_warehouse", result)

    for warehouse in sorted(dd_destinations):
        _require_key(data.transshipment_cost, warehouse, "transshipment_cost", result)

    for warehouse in data.existing_warehouses:
        _require_key(data.static_capacity, warehouse, "static_capacity", result)
        _require_key(data.reception_capacity, warehouse, "reception_capacity", result)
        _require_key(data.shipping_capacity, warehouse, "shipping_capacity", result)

    for warehouse in data.candidate_warehouses:
        _require_key(
            data.max_candidate_capacity,
            warehouse,
            "max_candidate_capacity",
            result,
        )
        _require_key(
            data.opening_fixed_cost,
            warehouse,
            "opening_fixed_cost",
            result,
        )

        if config.candidate_capacity_mode == "scalable":
            _require_key(
                data.candidate_capacity_cost,
                warehouse,
                "candidate_capacity_cost",
                result,
            )

        max_cap = data.max_candidate_capacity.get(warehouse)
        if max_cap is not None and max_cap <= 0:
            result.add_error(
                code="INVALID_CANDIDATE_CAPACITY",
                message=(
                    f"max_candidate_capacity[{warehouse!r}] must be positive "
                    "for candidate warehouses."
                ),
                location="max_candidate_capacity",
            )

    if not config.allow_capacity_expansion and (
        data.max_expand_capacity
        or data.expand_fixed_cost
        or data.expand_variable_cost
    ):
        result.add_warning(
            code="IGNORED_EXPANSION_PARAMETERS",
            message=(
                "Expansion parameters are defined, but "
                "allow_capacity_expansion is False."
            ),
            location="expansion",
        )

    if not config.allow_bulkification and (
        data.max_bulk_capacity
        or data.bulk_fixed_cost
        or data.bulk_variable_cost
    ):
        result.add_warning(
            code="IGNORED_BULKIFICATION_PARAMETERS",
            message=(
                "Bulkification parameters are defined, but "
                "allow_bulkification is False."
            ),
            location="bulkification",
        )

    if config.allow_unmet_domestic_demand:
        for customer in data.domestic_customers:
            for product in data.products:
                if (customer, product) not in data.unmet_demand_penalty:
                    result.add_warning(
                        code="MISSING_UNMET_DEMAND_PENALTY",
                        message=(
                            f"Missing unmet demand penalty for "
                            f"customer={customer!r}, product={product!r}. "
                            "The solver backend will need a default penalty."
                        ),
                        location="unmet_demand_penalty",
                    )

    if config.allow_emergency_static_capacity:
        for warehouse in data.warehouses:
            if warehouse not in data.emergency_static_capacity_penalty:
                result.add_warning(
                    code="MISSING_EMERGENCY_STATIC_PENALTY",
                    message=(
                        f"Missing emergency static capacity penalty for "
                        f"warehouse={warehouse!r}. The solver backend will "
                        "need a default penalty."
                    ),
                    location="emergency_static_capacity_penalty",
                )

    if config.allow_emergency_reception_capacity:
        for warehouse in data.warehouses:
            if warehouse not in data.emergency_reception_capacity_penalty:
                result.add_warning(
                    code="MISSING_EMERGENCY_RECEPTION_PENALTY",
                    message=(
                        f"Missing emergency reception capacity penalty for "
                        f"warehouse={warehouse!r}. The solver backend will "
                        "need a default penalty."
                    ),
                    location="emergency_reception_capacity_penalty",
                )


def _require_key(
    mapping: Mapping[str, float],
    key: str,
    mapping_name: str,
    result: ValidationResult,
) -> None:
    if key not in mapping:
        result.add_error(
            code="MISSING_REQUIRED_PARAMETER",
            message=f"Missing {mapping_name}[{key!r}].",
            location=mapping_name,
        )


# ---------------------------------------------------------------------
# Stochastic validation
# ---------------------------------------------------------------------


def _validate_stochastic_structure(
    data: ModelData,
    config: ModelConfig,
    result: ValidationResult,
) -> None:
    if config.mode == "sto" and not data.scenarios:
        result.add_error(
            code="MISSING_SCENARIOS",
            message="Stochastic mode requires at least one scenario.",
            location="scenarios",
        )
        return

    if config.mode == "det" and data.scenarios:
        result.add_warning(
            code="STOCHASTIC_DATA_IN_DETERMINISTIC_MODE",
            message=(
                "Scenario data are present, but ModelConfig.mode is 'det'. "
                "The deterministic backend may ignore stochastic parameters."
            ),
            location="scenarios",
        )

    if not data.scenarios:
        return

    missing_prob = sorted(set(data.scenarios) - set(data.scenario_prob))
    extra_prob = sorted(set(data.scenario_prob) - set(data.scenarios))

    if missing_prob:
        result.add_error(
            code="MISSING_SCENARIO_PROBABILITY",
            message=f"Missing probabilities for scenarios: {missing_prob}.",
            location="scenario_prob",
        )

    if extra_prob:
        result.add_warning(
            code="EXTRA_SCENARIO_PROBABILITY",
            message=f"Probabilities defined for unknown scenarios: {extra_prob}.",
            location="scenario_prob",
        )

    total_prob = 0.0

    for scenario in data.scenarios:
        prob = data.scenario_prob.get(scenario)

        if prob is None:
            continue

        if not _is_valid_number(prob):
            result.add_error(
                code="INVALID_SCENARIO_PROBABILITY",
                message=f"Probability for scenario {scenario!r} is not finite.",
                location="scenario_prob",
            )
            continue

        if prob < 0:
            result.add_error(
                code="NEGATIVE_SCENARIO_PROBABILITY",
                message=f"Probability for scenario {scenario!r} is negative.",
                location="scenario_prob",
            )
            continue

        total_prob += prob

    if data.scenarios and not isclose(total_prob, 1.0, rel_tol=1e-6, abs_tol=1e-6):
        result.add_error(
            code="INVALID_SCENARIO_PROBABILITY_SUM",
            message=f"Scenario probabilities must sum to 1. Current sum is {total_prob}.",
            location="scenario_prob",
        )


# ---------------------------------------------------------------------
# Connectivity validation
# ---------------------------------------------------------------------


def _validate_connectivity(
    data: ModelData,
    config: ModelConfig,
    result: ValidationResult,
) -> None:
    positive_supply_keys = [
        key for key, value in data.supply.items()
        if value > 0
    ]

    for origin, product, period in positive_supply_keys:
        if not _has_outgoing_supply_route(data, config, origin, product):
            result.add_error(
                code="NO_SUPPLY_ROUTE",
                message=(
                    f"Positive supply at origin={origin!r}, product={product!r}, "
                    f"period={period!r}, but no outgoing route exists."
                ),
                location="routes_od/routes_oc",
            )

    positive_domestic_demand_keys = [
        key for key, value in data.demand_dom.items()
        if value > 0
    ]

    for customer, product, period in positive_domestic_demand_keys:
        if not _has_incoming_domestic_route(data, config, customer, product):
            code = "NO_DOMESTIC_DEMAND_ROUTE"
            message = (
                f"Positive domestic demand at customer={customer!r}, "
                f"product={product!r}, period={period!r}, but no incoming "
                "route exists."
            )

            if config.allow_unmet_domestic_demand:
                result.add_warning(code=code, message=message, location="routes_dc/routes_oc")
            else:
                result.add_error(code=code, message=message, location="routes_dc/routes_oc")


def _has_outgoing_supply_route(
    data: ModelData,
    config: ModelConfig,
    origin: str,
    product: str,
) -> bool:
    has_od = any(
        route_origin == origin and route_product == product
        for route_origin, _warehouse, route_product in data.routes_od
    )

    has_oc = (
        config.use_direct_origin_customer
        and any(
            route_origin == origin and route_product == product
            for route_origin, _customer, route_product in data.routes_oc
        )
    )

    return has_od or has_oc


def _has_incoming_domestic_route(
    data: ModelData,
    config: ModelConfig,
    customer: str,
    product: str,
) -> bool:
    has_dc = any(
        route_customer == customer and route_product == product
        for _warehouse, route_customer, route_product in data.routes_dc
    )

    has_oc = (
        config.use_direct_origin_customer
        and any(
            route_customer == customer and route_product == product
            for _origin, route_customer, route_product in data.routes_oc
        )
    )

    return has_dc or has_oc

