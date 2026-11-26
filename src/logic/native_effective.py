"""Sealed effective inputs on the retained native DET/STO W construction path.

Preparation, policy assembly and vector checks do not import a native solver.
This module provides no scheduler, license probe or execution admission.
"""

from dataclasses import dataclass

from src.logic.effective_baseline import identity, validate
from src.logic.mathematical_contract import extensive_form_inputs
from src.logic.model_config import SolverConfig
from src.logic.mvp3_preparation import native_policy_rows
from src.logic.parametric_scenarios import verify_scenario_record

DEFAULT_PARAMETERS = (
    "MIPGap", "Seed", "Heuristics", "Presolve", "FeasibilityTol", "IntFeasTol",
    "ConcurrentMIP", "SoftMemLimit",
)


def reference_solver_config(*, log_file=None):
    """Fresh Rev4 settings; None leaves native MIPGap and Seed defaults untouched."""
    return SolverConfig(
        backend="gurobipy", solver_name="gurobi", time_limit=28800,
        mip_gap=None, threads=0, seed=None, tee=True, log_file=log_file,
        solver_options={"Method": -1},
    )


def check_reference_config(config):
    from src.logic.native_public_controls import PublicNativeConfig

    limit = 60 if isinstance(config, PublicNativeConfig) else 28800
    if (
        config.backend != "gurobipy"
        or config.solver_name.lower() not in {"gurobi", "gurobipy"}
        or type(config.time_limit) is not int or config.time_limit != limit
        or type(config.threads) is not int or config.threads != 0
        or config.mip_gap is not None or config.seed is not None
        or config.solver_options.get("Method") != -1
        or set(config.solver_options) - {"Method", "license_file", "GRB_LICENSE_FILE"}
        or config.compute_iis or config.compact_python_indices
    ):
        raise ValueError("Effective native inputs require the approved Rev4 automatic profile.")


@dataclass(frozen=True)
class EffectiveNativeContext:
    data: object
    config: object
    rows: tuple
    native_input_sha256: str


def prepare_effective_native(data, config, solver_config):
    """Verify original DET/STO seals before license configuration or native import.

    DET verification precedes embedding; the original DET seal must never be
    checked against an invented stochastic input or silently replaced by one.
    """
    from src.logic.native_public_controls import PublicNativeConfig, verify_public_control

    if isinstance(solver_config, PublicNativeConfig):
        verify_public_control(data, config)
    if "effective_baseline" not in data.metadata:
        return None
    check_reference_config(solver_config)
    if validate(data, config) != data.metadata["effective_baseline"].get("input_sha256"):
        raise ValueError("Effective native data changed after sealing.")
    verify_scenario_record(data, config)
    rows = native_policy_rows(data, config)
    native_data, native_config = extensive_form_inputs(data, config)
    return EffectiveNativeContext(data, config, rows, identity(native_data, native_config))


def check_native_embedding(context, data, config, solver_config):
    """The internal DET embedding retains exactly the verified input and policy."""
    current = prepare_effective_native(context.data, context.config, solver_config)
    if (
        current != context
        or identity(data, config) != context.native_input_sha256
        or data.metadata != context.data.metadata
    ):
        raise ValueError("Native embedding differs from the verified effective input.")


def attach_native_policies(model, gp, context, *, unmet, exports):
    """Unweighted full-horizon rows; shared investments remain in the old builder."""
    for row in context.rows:
        variables = unmet if row.control == "beta" else exports
        model.addConstr(
            gp.quicksum(variables[key] for key in row.terms) <= row.upper_tonnes,
            name=f"effective_{row.control}[{row.scenario},{row.product}]",
        )


def audit_reference_parameters(model, gp, config):
    """Readback is part of future execution, never a solver-free qualification."""
    check_reference_config(config)
    version = tuple(gp.gurobi.version())
    if version[0] != 14:
        raise ValueError("The effective native reference requires Gurobi 14.")
    values, defaults = {}, {}
    for name in (*DEFAULT_PARAMETERS, "Method", "Threads", "TimeLimit"):
        info = model.getParamInfo(name)
        if info is None:
            raise ValueError(f"Native parameter readback unavailable: {name}")
        values[name], defaults[name] = info[2], info[5]
        expected = {"Method": -1, "Threads": 0, "TimeLimit": config.time_limit}.get(name, info[5])
        if values[name] != expected:
            raise ValueError(f"Effective native parameter differs: {name}")
    # Infinite default limits are legitimate but are not JSON numeric values.
    from math import isfinite

    def serializable(mapping):
        return {k: v if isfinite(v) else str(v) for k, v in mapping.items()}

    return {
        "gurobi_version": list(version),
        "configured": {"Method": -1, "Threads": 0, "TimeLimit": config.time_limit},
        "effective": serializable(values), "defaults": serializable(defaults),
        "scope": "Selected parameter readback; broader telemetry is a later gate",
    }


def dense_vector_coverage(data, config, result):
    """Require full vectors, using period bitmaps instead of a second dense vector."""
    if not result.has_solution:
        return {"status": "no_usable_incumbent", "vectors": {}}
    scenarios = set(data.scenarios) if config.mode == "sto" else {None}
    periods = {t: i for i, t in enumerate(data.periods)}
    products = set(data.products)
    vectors = {}

    def check(name, actual, expected):
        seen, duplicates, extra, unique = {}, 0, 0, 0
        for group, position, valid in actual:
            if not valid:
                extra += 1
                continue
            bit = 1 << position
            previous = seen.get(group, 0)
            if previous & bit:
                duplicates += 1
            else:
                unique += 1
            seen[group] = previous | bit
        vectors[name] = {
            "expected": expected, "actual_unique": unique,
            "missing": expected - unique, "extra": extra, "duplicates": duplicates,
        }

    endpoints = {
        "OD": ("origin", "warehouse"), "DC": ("warehouse", "customer"),
        "DD": ("warehouse_from", "warehouse_to"),
    }
    routes = {kind: getattr(data, f"routes_{code}")
              for kind, code in (("OD", "od"), ("DC", "dc"), ("DD", "dd"))}

    def flows():
        for row in result.flows:
            s, kind, p, t = (row.get(k) for k in ("scenario", "route_type", "product", "period"))
            a, b = endpoints.get(kind, ("origin", "customer"))
            arc = (row.get(a), row.get(b), p)
            valid = s in scenarios and t in periods and arc in routes.get(kind, ())
            yield (s, kind, *arc), periods.get(t, 0), valid

    check("flows", flows(), len(scenarios) * len(periods) * sum(map(len, routes.values())))
    for name, field, nodes in (
        ("inventories", "warehouse", data.warehouses),
        ("unmet_demand", "customer", data.domestic_customers),
    ):
        nodes = set(nodes)
        actual = (
            ((r.get("scenario"), r.get(field), r.get("product")),
             periods.get(r.get("period"), 0),
             r.get("scenario") in scenarios and r.get(field) in nodes
             and r.get("product") in products and r.get("period") in periods)
            for r in getattr(result, name)
        )
        check(name, actual, len(scenarios) * len(nodes) * len(products) * len(periods))
    warehouses = set(data.warehouses)
    check("emergency_capacity", (
        ((r.get("scenario"), r.get("warehouse"), r.get("capacity_type")),
         periods.get(r.get("period"), 0),
         r.get("scenario") in scenarios and r.get("warehouse") in warehouses
         and r.get("capacity_type") in {"static", "reception"} and r.get("period") in periods)
        for r in result.emergency_capacity
    ), len(scenarios) * len(warehouses) * len(periods) * 2)
    check("warehouse_decisions", (
        (r.get("warehouse"), 0, r.get("warehouse") in warehouses and r.get("scenario") is None)
        for r in result.warehouse_decisions
    ), len(warehouses))
    valid = all(not (v["missing"] or v["extra"] or v["duplicates"]) for v in vectors.values())
    return {"status": "accepted" if valid else "rejected", "vectors": vectors}


def finish_effective_result(context, result):
    """Validate original-unit decisions against the original DET or STO seal."""
    from src.logic.effective_policy_validation import validate_effective_solution

    data, config = context.data, context.config
    coverage = dense_vector_coverage(data, config, result)
    result.metadata["effective_dense_coverage"] = coverage
    result.metadata["effective_input_sha256"] = data.metadata["effective_baseline"]["input_sha256"]
    result.metadata["effective_scenario_sha256"] = data.metadata["effective_baseline"].get(
        "scenario_sha256"
    )
    if coverage["status"] == "no_usable_incumbent":
        report = {"status": "no_usable_incumbent"}
    elif coverage["status"] == "rejected":
        report = {"status": "rejected", "reason": "incomplete_or_duplicate_dense_vectors"}
    else:
        report = validate_effective_solution(data, config, result)
    result.metadata["effective_validation"] = report
    return result
