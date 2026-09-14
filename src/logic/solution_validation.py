"""Independently reconstruct the MILP constraints from input and sparse output.

No solver expression, model object, or optimization helper is used here.
Missing sparse continuous records mean zero; missing first-stage decisions
do not. Tolerances are local to each constraint, not national total volumes.

Passing these checks supports implementation consistency of the exported
incumbent. It does not establish global optimality, empirical adequacy of the
input assumptions, or numerical replication of a historical case study.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from src.logic.model_config import ModelConfig
from src.logic.model_data import ModelData
from src.logic.optimization import OptimizationResult

VALIDATION_VERSION = "v020-independent-residuals-v1"
COST_NAMES = (
    "opening",
    "candidate_capacity",
    "expansion_fixed",
    "expansion_variable",
    "bulkification_fixed",
    "bulkification_variable",
    "transport_od",
    "transport_dc",
    "transport_dd",
    "transport_oc",
    "storage",
    "unmet_demand",
    "emergency_static",
    "emergency_reception",
)


def validate_solution(
    data: ModelData,
    config: ModelConfig,
    result: OptimizationResult,
    *,
    absolute_tolerance: float = 1e-5,
    relative_tolerance: float = 1e-8,
    sample_limit: int = 30,
) -> dict[str, Any]:
    """Return reproducible residual evidence; never infer feasibility from status."""

    if not all(math.isfinite(v) and v > 0 for v in (absolute_tolerance, relative_tolerance)):
        raise ValueError("Validation tolerances must be positive and finite.")
    if sample_limit < 1:
        raise ValueError("sample_limit must be positive.")
    families: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []

    def check(family, key, lhs, rhs=0.0, relation="eq", rounding_budget=0.0):
        stats = families.setdefault(family, {"checked": 0, "failed": 0, "max_residual": 0.0})
        stats["checked"] += 1
        finite = math.isfinite(lhs) and math.isfinite(rhs)
        tolerance = (
            absolute_tolerance + rounding_budget + relative_tolerance * max(abs(lhs), abs(rhs))
        )
        residual = abs(lhs - rhs) if relation == "eq" else max(0.0, lhs - rhs)
        passed = finite and residual <= tolerance
        if finite:
            stats["max_residual"] = max(stats["max_residual"], residual)
        if not passed:
            stats["failed"] += 1
            if len(failures) < sample_limit:
                failures.append(
                    {
                        "family": family,
                        "key": list(key) if isinstance(key, tuple) else key,
                        "lhs": lhs if math.isfinite(lhs) else str(lhs),
                        "rhs": rhs if math.isfinite(rhs) else str(rhs),
                        "relation": relation,
                        "tolerance": tolerance if finite else None,
                    }
                )
        return passed

    def number(value, key):
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = math.nan
        check("finite_nonnegative", key, -value, 0.0, "le")
        return value if math.isfinite(value) else 0.0

    check("usable_incumbent", "result", float(result.has_solution), 1.0)
    scenarios = list(data.scenarios) if config.mode == "sto" else [None]
    probabilities = data.scenario_prob if config.mode == "sto" else {None: 1.0}
    check("scenario_set", "nonempty", float(bool(scenarios)), 1.0)
    weights = {s: number(probabilities.get(s, math.nan), ("probability", s)) for s in scenarios}
    check("probabilities", "sum", sum(weights.values()), 1.0)
    periods, products = set(data.periods), set(data.products)
    warehouses = set(data.warehouses)
    incoming, outgoing, supplied, delivered = (defaultdict(float) for _ in range(4))
    costs = dict.fromkeys(COST_NAMES, 0.0)
    frozen = data.metadata.get("_frozen_routes", {})
    check("frozen_network", "present", float(bool(frozen)), 1.0)
    routes = {
        kind.upper(): {tuple(k) for k in frozen.get(kind, [])} for kind in ("od", "dc", "dd", "oc")
    }
    seen = set()
    for row in result.flows:
        kind, s, p, t = (row.get(k) for k in ("route_type", "scenario", "product", "period"))
        a, b = {
            "OD": (row.get("origin"), row.get("warehouse")),
            "DC": (row.get("warehouse"), row.get("customer")),
            "DD": (row.get("warehouse_from"), row.get("warehouse_to")),
            "OC": (row.get("origin"), row.get("customer")),
        }.get(kind, (None, None))
        key = (s, kind, a, b, p, t)
        valid = (
            s in weights and p in products and t in periods and (a, b, p) in routes.get(kind, set())
        )
        check("flow_indices", key, float(valid), 1.0)
        check("duplicate_flow", key, float(key in seen), 0.0)
        seen.add(key)
        value = number(row.get("value"), key)
        if not valid:
            continue
        if kind in ("OD", "OC"):
            supplied[s, a, p, t] += value
        if kind in ("OD", "DD"):
            incoming[s, b, p, t] += value
        if kind in ("DC", "DD"):
            outgoing[s, a, p, t] += value
        if kind in ("DC", "OC"):
            delivered[s, b, p, t] += value
        distances = getattr(data, "dist_" + kind.lower())
        distance = number(distances.get((a, b), math.nan), ("distance", a, b))
        freight = data.freight_origin if kind in ("OD", "OC") else data.freight_warehouse
        unit = distance * freight.get(a, 0.0) * (config.interhub_factor if kind == "DD" else 1.0)
        if kind in ("OD", "DD"):
            unit += data.transshipment_cost.get(b, 0.0)
        costs["transport_" + kind.lower()] += weights[s] * value * unit

    def sparse(rows, label, fields, domains):
        values = {}
        for row in rows:
            key = tuple(row.get(f) for f in fields)
            valid = all(k in domain for k, domain in zip(key, domains, strict=True))
            check("record_indices", (label, *key), float(valid), 1.0)
            check("duplicate_record", (label, *key), float(key in values), 0.0)
            value = number(row.get("value"), (label, *key))
            if valid:
                values[key] = value
        return values

    inventory = sparse(
        result.inventories,
        "inventory",
        ("scenario", "warehouse", "product", "period"),
        (weights, warehouses, products, periods),
    )
    unmet = sparse(
        result.unmet_demand,
        "unmet",
        ("scenario", "customer", "product", "period"),
        (weights, set(data.domestic_customers), products, periods),
    )
    emergency = sparse(
        result.emergency_capacity,
        "emergency",
        ("scenario", "warehouse", "period", "capacity_type"),
        (weights, warehouses, periods, {"static", "reception"}),
    )
    decisions = {}
    fields = (
        "open",
        "candidate_capacity",
        "expand",
        "expansion_capacity",
        "bulkify",
        "bulk_capacity",
    )
    for row in result.warehouse_decisions:
        w = row.get("warehouse")
        check("decision_indices", w, float(w in warehouses and row.get("scenario") is None), 1.0)
        check("duplicate_decision", w, float(w in decisions), 0.0)
        decisions[w] = {f: number(row.get(f, math.nan), (w, f)) for f in fields}

    for w in data.warehouses:
        check("decision_complete", w, float(w in decisions), 1.0)
        d = decisions.get(w, dict.fromkeys(fields, 0.0))
        opened, candidate, expanded, expansion, bulkified, bulk = (d[f] for f in fields)
        for f in ("open", "expand", "bulkify"):
            check("binary_decision", (w, f), d[f], round(d[f]))
            check("binary_upper", (w, f), d[f], 1.0, "le")
        if w in data.existing_warehouses:
            check("existing_active", w, opened, 1.0)
        if w in data.candidate_warehouses:
            check(
                "candidate_activation",
                w,
                candidate,
                data.max_candidate_capacity.get(w, 0.0) * opened,
                "eq" if config.candidate_capacity_mode == "fixed" else "le",
            )
            for base in (data.static_capacity, data.reception_capacity, data.shipping_capacity):
                check("candidate_zero_base", w, base.get(w, 0.0), 0.0)
            costs["opening"] += opened * data.opening_fixed_cost.get(w, 0.0)
            if config.candidate_capacity_mode == "scalable":
                costs["candidate_capacity"] += candidate * data.candidate_capacity_cost.get(w, 0.0)
        else:
            check("noncandidate_capacity", w, candidate, 0.0)
        eligible_expand = (
            config.allow_capacity_expansion and data.max_expand_capacity.get(w, 0.0) > 0
        )
        eligible_bulk = (
            config.allow_bulkification
            and w in data.bulk_eligible_warehouses
            and data.max_bulk_capacity.get(w, 0.0) > 0
        )
        check("expansion_eligibility", w, expanded, float(eligible_expand), "le")
        check("bulkification_eligibility", w, bulkified, float(eligible_bulk), "le")
        check(
            "expansion_bound", w, expansion, data.max_expand_capacity.get(w, 0.0) * expanded, "le"
        )
        check("bulkification_bound", w, bulk, data.max_bulk_capacity.get(w, 0.0) * bulkified, "le")
        check("investment_activation", w, expanded + bulkified, opened, "le")
        costs["expansion_fixed"] += expanded * data.expand_fixed_cost.get(w, 0.0)
        costs["expansion_variable"] += expansion * data.expand_variable_cost.get(w, 0.0)
        costs["bulkification_fixed"] += bulkified * data.bulk_fixed_cost.get(w, 0.0)
        costs["bulkification_variable"] += bulk * data.bulk_variable_cost.get(w, 0.0)
        nominal_static = data.static_capacity.get(w, 0.0) + candidate + expansion
        if config.capacity_coupling_policy == "period_equivalent":
            nominal_static += bulk
        for s in scenarios:
            for t in data.periods:
                stock = sum(inventory.get((s, w, p, t), 0.0) for p in data.products)
                inbound = sum(incoming[s, w, p, t] for p in data.products)
                outbound = sum(outgoing[s, w, p, t] for p in data.products)
                es = emergency.get((s, w, t, "static"), 0.0)
                er = emergency.get((s, w, t, "reception"), 0.0)
                if not config.allow_emergency_static_capacity:
                    check("disabled_static_slack", (s, w, t), es, 0.0)
                if not config.allow_emergency_reception_capacity:
                    check("disabled_reception_slack", (s, w, t), er, 0.0)
                if opened < 0.5:
                    check(
                        "closed_facility_operation", (s, w, t), stock + inbound + outbound + es + er
                    )
                days = config.operating_days(t)
                reception = data.reception_capacity.get(w, 0.0) * days
                shipping = data.shipping_capacity.get(w, 0.0) * days
                if config.capacity_coupling_policy == "period_equivalent":
                    reception += candidate
                    shipping += candidate
                else:
                    reception += days * (
                        candidate * config.candidate_reception_daily_factor
                        + expansion * config.expansion_reception_daily_factor
                        + bulk * config.bulkification_reception_daily_factor
                    )
                    shipping += days * (
                        candidate * config.candidate_shipping_daily_factor
                        + expansion * config.expansion_shipping_daily_factor
                        + bulk * config.bulkification_shipping_daily_factor
                    )
                check("static_capacity", (s, w, t), stock, nominal_static + es, "le")
                check("reception_capacity", (s, w, t), inbound, reception + er, "le")
                check("shipping_capacity", (s, w, t), outbound, shipping, "le")
                costs["emergency_static"] += (
                    weights[s] * es * data.emergency_static_capacity_penalty.get(w, 1e6)
                )
                costs["emergency_reception"] += (
                    weights[s] * er * data.emergency_reception_capacity_penalty.get(w, 1e6)
                )
            for p in data.products:
                previous = data.initial_inventory.get((w, p), 0.0)
                for t in data.periods:
                    current = inventory.get((s, w, p, t), 0.0)
                    check(
                        "inventory_balance",
                        (s, w, p, t),
                        current,
                        previous + incoming[s, w, p, t] - outgoing[s, w, p, t],
                    )
                    costs["storage"] += weights[s] * current * data.storage_tariff.get((w, p), 0.0)
                    previous = current

    def input_value(name, s, node, p, t):
        mapping = getattr(data, name + ("_s" if s is not None else ""))
        key = (s, node, p, t) if s is not None else (node, p, t)
        return number(mapping.get(key, 0.0), (name, *key))

    service = []
    for s in scenarios:
        demand_total, served_total, unmet_total = 0.0, 0.0, 0.0
        for o in data.origins:
            for p in data.products:
                for t in data.periods:
                    check(
                        "supply_balance",
                        (s, o, p, t),
                        supplied[s, o, p, t],
                        input_value("supply", s, o, p, t),
                    )
        for c in data.customers:
            for p in data.products:
                for t in data.periods:
                    if c in data.domestic_customers:
                        target = input_value("demand_dom", s, c, p, t)
                        shortage = unmet.get((s, c, p, t), 0.0)
                        arrival = delivered[s, c, p, t]
                        check("domestic_balance", (s, c, p, t), arrival + shortage, target)
                        if not config.allow_unmet_domestic_demand:
                            check("disabled_shortage", (s, c, p, t), shortage)
                        demand_total += target
                        served_total += arrival
                        unmet_total += shortage
                        costs["unmet_demand"] += (
                            weights[s] * shortage * data.unmet_demand_penalty.get((c, p), 1e6)
                        )
                    else:
                        check(
                            "export_bound",
                            (s, c, p, t),
                            delivered[s, c, p, t],
                            input_value("demand_exp", s, c, p, t),
                            "le",
                        )
        service.append(
            {
                "scenario": s,
                "probability": weights[s],
                "input_demand_tons": demand_total,
                "served_tons": served_total,
                "unmet_tons": unmet_total,
                "service_level": served_total / demand_total if demand_total > 0 else None,
            }
        )
    # Native sparse exports omit values <= 1e-7. A conservative, explicit
    # coefficient-based budget bounds their possible monetary contribution.
    # Investment records are dense and receive no such allowance.
    budgets = dict.fromkeys(COST_NAMES, 0.0)
    count_periods = len(data.periods)
    for kind, arcs in routes.items():
        distance_map = getattr(data, "dist_" + kind.lower())
        for a, b, _p in arcs:
            freight = data.freight_origin if kind in ("OD", "OC") else data.freight_warehouse
            unit = distance_map.get((a, b), 0.0) * freight.get(a, 0.0)
            if kind == "DD":
                unit *= config.interhub_factor
            if kind in ("OD", "DD"):
                unit += data.transshipment_cost.get(b, 0.0)
            budgets["transport_" + kind.lower()] += abs(unit) * count_periods * 1e-7
    budgets["storage"] = (
        sum(
            abs(data.storage_tariff.get((w, p), 0.0))
            for w in data.warehouses
            for p in data.products
        )
        * count_periods
        * 1e-7
    )
    budgets["unmet_demand"] = (
        sum(
            abs(data.unmet_demand_penalty.get((c, p), 1e6))
            for c in data.domestic_customers
            for p in data.products
        )
        * count_periods
        * 1e-7
    )
    for kind in ("static", "reception"):
        rates = getattr(data, "emergency_" + kind + "_capacity_penalty")
        budgets["emergency_" + kind] = (
            sum(abs(rates.get(w, 1e6)) for w in data.warehouses) * count_periods * 1e-7
        )
    for component in COST_NAMES:
        reported = result.cost_breakdown.get(component, math.nan)
        check(
            "cost_reconstruction",
            component,
            float(reported),
            costs[component],
            rounding_budget=budgets[component],
        )
    objective = (
        sum(costs.values())
        if config.objective_policy == "penalty"
        else sum(weights[s] * v for (s, _c, _p, _t), v in unmet.items())
    )
    check(
        "objective_reconstruction",
        "objective",
        float(result.objective_value) if result.objective_value is not None else math.nan,
        objective,
        rounding_budget=sum(budgets.values()) if config.objective_policy == "penalty" else 0.0,
    )
    failed = sum(stats["failed"] for stats in families.values())
    return {
        "schema_version": 1,
        "validator_version": VALIDATION_VERSION,
        "status": "accepted" if not failed else "rejected",
        "failed_check_count": failed,
        "absolute_tolerance": absolute_tolerance,
        "relative_tolerance": relative_tolerance,
        "families": families,
        "failure_samples": failures,
        "sample_limit": sample_limit,
        "reconstructed_costs": costs,
        "sparse_export_value_threshold": 1e-7,
        "cost_reconstruction_sparse_rounding_budgets": budgets,
        "service_by_scenario": service,
        "mathematical_contract": data.metadata.get("mathematical_contract", {}),
        "scope": "primal_feasibility_and_costs_not_global_optimality_or_historical_replication",
    }
