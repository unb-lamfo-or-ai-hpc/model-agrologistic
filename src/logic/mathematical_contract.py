"""Freeze the selected network and cost semantics before any reference solve.

Reception slack is period overflow in tonnes: it is added after daily
throughput has been converted to the period. It must not be multiplied by
operating days again. Separate stock and reception slacks are an intentional
extension of the historical shared-slack objective, not a neutral refactor.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from typing import Any

from src.logic.model_config import ModelConfig
from src.logic.model_data import ModelData
from src.logic.route_filtering import route_policy_signature, select_routes

MATHEMATICAL_CONTRACT_VERSION = "v020-separated-slacks-selected-penalties-v1"


def canonical_hash(payload: Any) -> str:
    """Hash JSON-compatible scientific metadata deterministically."""

    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def prepare_model_data(data: ModelData, config: ModelConfig) -> ModelData:
    """Return an immutable projection with a frozen network and penalty vector.

    RP, EV, WS, and EEV projections retain this same metadata. Scenario
    projection must never repair the graph or recalibrate Big-M separately.
    Original loader data and historical workbooks are not modified.
    """

    if config.terminal_inventory_policy != "free":
        raise ValueError(
            "The native model currently supports only terminal_inventory_policy='free'."
        )
    if config.terminal_inventory_penalty != 0.0:
        raise ValueError("A terminal inventory penalty is unsupported by the native model.")
    signature = route_policy_signature(config)
    previous = data.metadata.get("mathematical_contract", {})
    if previous.get("version") == MATHEMATICAL_CONTRACT_VERSION:
        if previous.get("route_policy") != signature:
            raise ValueError("Frozen model data cannot be reused with a different route policy.")
        return data

    routes = select_routes(data, config)
    frozen = {
        name: [list(route) for route in sorted(getattr(routes, name))]
        for name in ("od", "dc", "dd", "oc", "repair_od", "repair_dc", "repair_dd", "repair_oc")
    }
    unmet = dict(data.unmet_demand_penalty)
    static = dict(data.emergency_static_capacity_penalty)
    reception = dict(data.emergency_reception_capacity_penalty)
    penalty_scope = "input_vector"
    if data.metadata.get("penalty_policy") == "thesis_dynamic":
        reference = max(
            100.0,
            max(data.expand_variable_cost.values(), default=0.0),
            max(data.storage_tariff.values(), default=0.0),
        )
        by_customer: dict[str, list[float]] = {c: [] for c in data.domestic_customers}
        for warehouse, customer, _product in routes.dc:
            if customer in by_customer:
                by_customer[customer].append(
                    data.dist_dc[warehouse, customer] * data.freight_warehouse.get(warehouse, 0.0)
                )
        for origin, customer, _product in routes.oc:
            if customer in by_customer:
                by_customer[customer].append(
                    data.dist_oc[origin, customer] * data.freight_origin.get(origin, 0.0)
                )
        unmet = {
            (customer, product): 100.0 * max(reference, max(by_customer[customer], default=0.0))
            for customer in data.domestic_customers
            for product in data.products
        }
        static = {warehouse: 50.0 * reference for warehouse in data.warehouses}
        reception = dict(static)
        penalty_scope = "selected_routes_frozen_before_scenario_projection"

    vector = {
        "unmet": [[*key, value] for key, value in sorted(unmet.items())],
        "static": sorted(static.items()),
        "reception": sorted(reception.items()),
    }
    contract = {
        "version": MATHEMATICAL_CONTRACT_VERSION,
        "route_policy": signature,
        "selected_network_sha256": canonical_hash(frozen),
        "penalty_vector_sha256": canonical_hash(vector),
        "penalty_scope": penalty_scope,
        "emergency_static_unit": "stock_tonnes_at_warehouse_period",
        "emergency_reception_unit": "overflow_tonnes_in_period",
        "capacity_objective": "equal_weight_sum_of_stock_exceedance_and_reception_overflow",
        "historical_shared_slack_equivalent": False,
        "terminal_inventory_policy": "free",
        "penalty_vector": vector,
    }
    return replace(
        data,
        unmet_demand_penalty=unmet,
        emergency_static_capacity_penalty=static,
        emergency_reception_capacity_penalty=reception,
        metadata={**data.metadata, "mathematical_contract": contract, "_frozen_routes": frozen},
    )
