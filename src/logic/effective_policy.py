"""Approved optional horizon policies on the existing effective Pyomo model."""

from collections import defaultdict
from math import fsum


def attach_policy_constraints(built, controls, record):
    import pyomo.environ as pyo

    data, model = built.data, built.model
    if built.cfg.use_direct_origin_customer:
        raise ValueError("Effective service/export policies require W topology.")
    model.effective_policy = block = pyo.Block()

    def expression(lhs, rhs):
        expr = lhs <= rhs
        return (
            pyo.Constraint.Feasible
            if expr is True
            else (pyo.Constraint.Infeasible if expr is False else expr)
        )

    def service_rule(_block, s, p):
        demand = fsum(
            data.demand_dom_s[s, c, p, t] for c in data.domestic_customers for t in data.periods
        )
        unmet = pyo.quicksum(
            built.unmet[s, c, p, t] for c in data.domestic_customers for t in data.periods
        )
        return expression(unmet, (1 - controls["beta"][s, p]) * demand)

    exported = defaultdict(list)
    if controls["alpha"]:
        destinations = set(data.export_customers)
        for (s, _w, c, p, _t), variable in built.flows["DC"].items():
            if c in destinations:
                exported[s, p].append(variable)

    def export_rule(_block, s, p):
        supply = fsum(data.supply_s[s, o, p, t] for o in data.origins for t in data.periods)
        return expression(pyo.quicksum(exported[s, p]), controls["alpha"][s, p] * supply)

    block.service_floor = pyo.Constraint(list(controls["beta"]), rule=service_rule)
    block.export_ceiling = pyo.Constraint(list(controls["alpha"]), rule=export_rule)
    built.effective_policy_receipt = {
        "scenario_sha256": record["scenario_sha256"],
        "service_rows": len(block.service_floor),
        "export_rows": len(block.export_ceiling),
        "scope": "Unweighted per-product/scenario totals over the full horizon; W only",
        "objective": "Existing scalar objective unchanged",
    }
