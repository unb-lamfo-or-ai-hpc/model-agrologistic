"""Independent original-unit validation of optional effective service/export policies.

No Pyomo model or policy-construction helper is read. Retained physical/cost
validation is composed with product/scenario sums from exported vectors.
"""

from math import fsum, isfinite

from src.logic.effective_baseline import identity
from src.logic.parametric_scenarios import verify_scenario_record
from src.logic.solution_validation import validate_solution


def validate_effective_solution(
    data, config, result, *, absolute_tolerance=1e-5, relative_tolerance=1e-8, sample_limit=30
):
    if identity(data, config) != data.metadata.get("effective_baseline", {}).get("input_sha256"):
        raise ValueError("Effective data changed after sealing.")
    verify_scenario_record(data, config)  # integrity only; no construction math reused
    spec = data.metadata["effective_baseline"].get("specification", {})
    base = validate_solution(
        data,
        config,
        result,
        absolute_tolerance=absolute_tolerance,
        relative_tolerance=relative_tolerance,
        sample_limit=sample_limit,
    )
    if spec.get("beta") is None and spec.get("alpha") is None:
        return base
    if base["status"] != "accepted":
        return {**base, "effective_policy_validation": {"status": "invalid_base_solution"}}
    if not result.has_solution:
        return {**base, "effective_policy_validation": {"status": "no_usable_incumbent"}}
    # Nonnegative values omitted below the retained export threshold can only
    # increase these left-hand sides. Do not certify an ambiguous near-bound row.
    threshold = base["sparse_export_value_threshold"]
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not isfinite(threshold)
        or threshold < 0
    ):
        raise ValueError("Invalid sparse export threshold.")
    scenarios = data.scenarios if config.mode == "sto" else ["deterministic"]
    records = []
    for s in scenarios:
        vector_s = s if config.mode == "sto" else None
        for p in data.products:
            for control in ("beta", "alpha"):
                value = spec.get(control)
                if value is None:
                    continue
                fraction = value[p][s] if isinstance(value, dict) else value
                if control == "beta":
                    terms = [
                        row["value"]
                        for row in result.unmet_demand
                        if row.get("scenario") == vector_s
                        and row["product"] == p
                        and row["customer"] in data.domestic_customers
                    ]
                    amount = fsum(
                        (
                            data.demand_dom_s[s, c, p, t]
                            if config.mode == "sto"
                            else data.demand_dom[c, p, t]
                        )
                        for c in data.domestic_customers
                        for t in data.periods
                    )
                    rhs = (1 - fraction) * amount
                    possible = len(data.domestic_customers) * len(data.periods)
                else:
                    terms = [
                        row["value"]
                        for row in result.flows
                        if row.get("scenario") == vector_s
                        and row["product"] == p
                        and row["route_type"] == "DC"
                        and row["customer"] in data.export_customers
                    ]
                    amount = fsum(
                        (
                            data.supply_s[s, o, p, t]
                            if config.mode == "sto"
                            else data.supply[o, p, t]
                        )
                        for o in data.origins
                        for t in data.periods
                    )
                    rhs = fraction * amount
                    possible = sum(
                        1
                        for _w, c, product in data.metadata["_frozen_routes"]["dc"]
                        if c in data.export_customers and product == p
                    ) * len(data.periods)
                lhs = fsum(terms)
                omission = max(0, possible - len(terms)) * threshold
                tolerance = absolute_tolerance + relative_tolerance * max(abs(lhs), abs(rhs))
                status = (
                    "violated"
                    if lhs > rhs + tolerance
                    else "indeterminate_sparse_precision"
                    if lhs + omission > rhs + tolerance
                    else "accepted"
                )
                records.append(
                    {
                        "control": control,
                        "scenario": s,
                        "product": p,
                        "fraction": fraction,
                        "lhs_t": lhs,
                        "rhs_t": rhs,
                        "tolerance_t": tolerance,
                        "omission_upper_t": omission,
                        "status": status,
                    }
                )
    failures = sum(row["status"] != "accepted" for row in records)
    return {
        **base,
        "base_validation_status": base["status"],
        "status": "accepted" if base["status"] == "accepted" and not failures else "rejected",
        "failed_check_count": base["failed_check_count"] + failures,
        "effective_policy_validation": {
            "status": "accepted" if not failures else "rejected",
            "rows": records,
            "scenario_sha256": data.metadata["effective_baseline"]["scenario_sha256"],
            "scope": "Independent horizon sums; not optimality or empirical-service acceptance",
        },
    }
