"""Proved bounds for candidate slack representatives, not arbitrary flow Big-M.

Nonnegative penalties allow trimming redundant slack. The formulation preserves
the projection onto physical/investment decisions and the optimal scalar value,
not every redundant unbounded slack assignment in the native formulation.
"""

import math

from src.logic.mathematical_contract import canonical_hash
from src.logic.optimization_gurobipy import _effective_shipping_capacity_expr

POLICY = "bounded_scalar_slacks_v1"


def nonnegative(value):
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError("Finite nonnegative data required for Pyomo bound proof.")
    return value


def candidate_slack_bounds(data, cfg):
    """Conservation bounds storage; hard shipping capacity bounds DD circulation."""
    for mapping in (
        data.static_capacity, data.reception_capacity, data.shipping_capacity,
        data.max_candidate_capacity, data.max_expand_capacity, data.max_bulk_capacity,
        data.initial_inventory, data.scenario_prob,
    ):
        for value in mapping.values():
            nonnegative(value)
    for value in (
        cfg.candidate_shipping_daily_factor, cfg.expansion_shipping_daily_factor,
        cfg.bulkification_shipping_daily_factor,
    ):
        nonnegative(value)
    for warehouse in data.candidate_warehouses:
        nonnegative(data.emergency_static_capacity_penalty.get(warehouse, 1000000))
        nonnegative(data.emergency_reception_capacity_penalty.get(warehouse, 1000000))
    candidate = {w: data.max_candidate_capacity.get(w, 0) for w in data.candidate_warehouses}
    expansion = {w: data.max_expand_capacity.get(w, 0) for w in data.warehouses
                 if cfg.allow_capacity_expansion and data.max_expand_capacity.get(w, 0) > 0}
    bulk = {w: data.max_bulk_capacity.get(w, 0) for w in data.bulk_eligible_warehouses
            if w in data.warehouses and cfg.allow_bulkification
            and data.max_bulk_capacity.get(w, 0) > 0}
    initial = sum(nonnegative(v) for v in data.initial_inventory.values())
    static, reception = {}, {}
    for scenario in data.scenarios:
        cumulative = initial
        for period in data.periods:
            nonnegative(cfg.operating_days(period))
            supply = sum(nonnegative(data.supply_s[scenario, o, p, period])
                         for o in data.origins for p in data.products)
            cumulative = nonnegative(cumulative + supply)
            shipping = sum(nonnegative(_effective_shipping_capacity_expr(
                data, cfg, candidate, expansion, bulk, warehouse, period,
            )) for warehouse in data.warehouses)
            inflow = nonnegative(supply + shipping)
            for warehouse in data.candidate_warehouses:
                static[scenario, warehouse, period] = cumulative
                reception[scenario, warehouse, period] = inflow
    record = {
        "policy": POLICY,
        "equivalence": "physical_investment_projection_and_optimal_scalar_value",
        "entire_redundant_slack_region_preserved": False,
        "nonnegative_candidate_slack_penalties_required": True,
        "bounds_sha256": canonical_hash({
            "static": [[*key, value] for key, value in sorted(static.items())],
            "reception": [[*key, value] for key, value in sorted(reception.items())],
        }),
        "candidate_slack_bounds": len(static) + len(reception),
        "maximum_bound": max((*static.values(), *reception.values()), default=0),
    }
    return {"static": static, "reception": reception}, record
