"""Effective-model Gurobi bridge for separately authorized executions.

The public qualification uses this SAME construction/export/validation path.
This module has no scheduler, file-input or submission interface.
"""

import math

from src.logic.effective_baseline import build_effective_model
from src.logic.effective_policy_validation import validate_effective_solution
from src.logic.optimization import OptimizationResult
from src.logic.optimization_pyomo import extract_result, finite, normalized_status
from src.logic.pyomo_linear_matrix import matrix_identity


def settings(*, threads, native_seconds, mip_gap, diagnostic_infeasible=False):
    if (
        isinstance(threads, bool)
        or threads not in (1, 4)
        or isinstance(native_seconds, bool)
        or not isinstance(native_seconds, (int, float))
        or not math.isfinite(native_seconds)
        or not 0 < native_seconds <= 28800
        or isinstance(mip_gap, bool)
        or not isinstance(mip_gap, (int, float))
        or not math.isfinite(mip_gap)
        or not 0 <= mip_gap <= 0.01
    ):
        raise ValueError("Unqualified effective Gurobi profile.")
    return {
        "TimeLimit": native_seconds,
        "MIPGap": mip_gap,
        "Threads": threads,
        "Seed": 42,
        "FeasibilityTol": 1e-9,
        "IntFeasTol": 1e-9,
        "ConcurrentMIP": 1,
        "Method": -1,
        "DualReductions": 0 if diagnostic_infeasible else 1,
        "OutputFlag": 0,
    }


def export_effective_solution(built, data, cfg, result):
    """Reuse retained extraction, adding dense policy-critical records including zeros."""
    import pyomo.environ as pyo

    result = extract_result(built, result, cfg.mode)
    result.unmet_demand = []
    for (s, c, p, t), var in built.unmet.items():
        row = {"customer": c, "product": p, "period": t, "value": float(pyo.value(var))}
        if cfg.mode == "sto":
            row["scenario"] = s
        result.unmet_demand.append(row)
    result.flows = [
        row
        for row in result.flows
        if not (row["route_type"] == "DC" and row["customer"] in data.export_customers)
    ]
    for (s, w, c, p, t), var in built.flows["DC"].items():
        if c not in data.export_customers:
            continue
        row = {
            "route_type": "DC",
            "warehouse": w,
            "customer": c,
            "product": p,
            "period": t,
            "value": float(pyo.value(var)),
            "customer_type": "export",
        }
        if cfg.mode == "sto":
            row["scenario"] = s
        result.flows.append(row)
    result.metadata["effective_validation"] = validate_effective_solution(data, cfg, result)
    result.metadata["effective_scenario_sha256"] = data.metadata["effective_baseline"].get(
        "scenario_sha256"
    )
    result.metadata["policy_critical_export"] = "Dense unmet and WD export rows, including zeros"
    return result


def solve_effective_gurobi(data, cfg, profile, *, max_variables):
    """No implicit execution: caller supplies reviewed limits and compute admission."""
    expected = settings(
        threads=profile.get("Threads"),
        native_seconds=profile.get("TimeLimit"),
        mip_gap=profile.get("MIPGap"),
        diagnostic_infeasible=profile.get("DualReductions") == 0,
    )
    if profile != expected:
        raise ValueError("Only the declared effective profile is qualified.")
    built = build_effective_model(data, cfg, max_variables=max_variables)
    adapter, result = None, None
    try:
        from pyomo.contrib.appsi.solvers import Gurobi

        adapter = Gurobi()
        common_matrix = matrix_identity(built.model)
        adapter.config.load_solution = False
        adapter.config.stream_solver = False
        adapter.config.time_limit = profile["TimeLimit"]
        adapter.config.mip_gap = profile["MIPGap"]
        adapter.gurobi_options.update(profile)
        adapter.set_instance(built.model)
        solved = adapter.solve(built.model)
        native = adapter._solver_model
        usable = native.SolCount > 0
        status = normalized_status(solved.termination_condition, usable)
        effective = {name: native.getParamInfo(name)[2] for name in profile}
        if effective != profile:
            raise ValueError("Native effective parameters differ from the declared profile.")
        result = OptimizationResult(
            status=status,
            solver_backend="pyomo",
            solver_name="gurobi",
            model_mode=cfg.mode,
            metadata={
                "objective_bound": finite(solved.best_objective_bound),
                "timings": {},
                "effective_native_options": effective,
                "native_solution_count": native.SolCount,
                "common_linear_matrix": common_matrix,
                "native_runtime_seconds": finite(native.Runtime),
                "native_status_code": native.Status,
                "native_counters": {
                    "nodes": finite(native.NodeCount),
                    "lp_iterations": finite(native.IterCount),
                },
            },
        )
        if not usable:
            return result
        adapter.load_vars()
        return export_effective_solution(built, data, cfg, result)
    finally:
        native = getattr(adapter, "_solver_model", None)
        if native is not None:
            native.dispose()
            adapter._solver_model = None
        cached = getattr(adapter, "_last_results_object", None)
        if cached is not None:
            cached.solution_loader.invalidate()
        built.model.clear()
        if result is not None:
            result.metadata["native_model_lifecycle"] = "disposed_and_model_cleared"
