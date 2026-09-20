"""Sequential SCIP minimization with explicit, auditable priority budgets.

SCIP's native relative gap differs from the incumbent-denominator metric used
for cross-backend reporting. Both are retained. Native acceptance alone never
certifies a pass: the common relative or absolute bound test must also pass.
"""

from __future__ import annotations

import math
from time import perf_counter

ABSOLUTE_GAP = 1e-10


def common_gap(incumbent, bound):
    if not all(math.isfinite(v) for v in (incumbent, bound)):
        return None
    if abs(incumbent) <= ABSOLUTE_GAP:
        return None
    return max(0.0, incumbent - bound) / abs(incumbent)


def inherited_limit(incumbent, bound, gap, tolerance):
    """Reproduce the documented minimization-MIP priority budget explicitly."""
    return max(incumbent, bound + abs(incumbent) * gap, bound + ABSOLUTE_GAP) + tolerance


def solve_stages(model, objectives, config, tolerance, *, clock=perf_counter):
    """Stop at the first uncertified pass; share one wall-time optimization budget.

    The original SCIP solution pool is retained across freeTransform calls. SCIP
    rechecks stored solutions against each newly imposed priority constraint.
    The budget includes transformation and transitions, but not model creation.
    """
    started = clock()
    records = []
    for index, (role, expression) in enumerate(objectives):
        remaining = None if config.time_limit is None else config.time_limit - (clock() - started)
        if remaining is not None and remaining <= 0:
            break
        model.setObjective(expression, "minimize")
        remaining = None if config.time_limit is None else config.time_limit - (clock() - started)
        if remaining is not None and remaining <= 0:
            break
        # SCIP's solving clock survives some lifecycle operations. A relative
        # remaining allowance must therefore be added to its current value.
        before_solver = model.getSolvingTime()
        if remaining is not None:
            model.setParam("limits/time", before_solver + remaining)
        pass_started = clock()
        model.optimize()
        native_status = str(model.getStatus())
        has_solution = model.getNSols() > 0
        incumbent = float(model.getObjVal()) if has_solution else None
        bound = float(model.getDualbound())
        bound = bound if abs(bound) < model.infinity() else None
        gap = common_gap(incumbent, bound) if incumbent is not None and bound is not None else None
        certified = (
            has_solution
            and bound is not None
            and (
                max(0.0, incumbent - bound) <= ABSOLUTE_GAP
                or (gap is not None and gap <= config.mip_gap + 1e-12)
                # The nonnegative primary objective has the independent lower bound zero.
                or (role == "unmet_demand" and -tolerance <= incumbent <= tolerance)
            )
        )
        status = (
            "OPTIMAL"
            if certified
            else {
                "timelimit": "TIME_LIMIT",
                "memlimit": "MEM_LIMIT",
                "infeasible": "INFEASIBLE",
                "unbounded": "UNBOUNDED",
            }.get(native_status, native_status.upper())
        )
        record = {
            "stage_number": index + 1,
            "objective_name": (
                "expected_" + role if role in {"unmet_demand", "emergency_capacity"} else role
            ),
            "stage_role": role,
            "status": status,
            "scip_status": native_status,
            "objective_value": incumbent,
            "objective_bound": bound,
            "mip_gap": gap,
            "native_mip_gap": float(model.getGap()) if has_solution else None,
            "solution_count": model.getNSols(),
            "node_count": model.getNNodes(),
            "iteration_count": model.getNLPIterations(),
            "runtime_seconds": clock() - pass_started,
            "solver_runtime_seconds": model.getSolvingTime() - before_solver,
            "certified": certified,
            "configured_mip_gap": config.mip_gap,
            "configured_mip_gap_abs": ABSOLUTE_GAP,
            "terminal_transformed_variables": model.getNVars(),
            "terminal_transformed_constraints": model.getNConss(),
            "terminal_scip_memory_bytes": model.getMemUsed(),
        }
        records.append(record)
        if not certified or index == len(objectives) - 1:
            break
        limit = inherited_limit(incumbent, bound, config.mip_gap, tolerance)
        record["enforced_next_pass_limit"] = limit
        model.freeTransform()
        model.addCons(expression <= limit, name=f"priority_budget_{role}")
    return records, clock() - started
