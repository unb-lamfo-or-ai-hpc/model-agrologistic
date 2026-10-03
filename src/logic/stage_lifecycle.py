"""Small-instance qualification of explicit minimization-MIP priority locks.

This experimental driver is not selected by the production backends. Its
factory is limited to 100000 original variables until licensed parity and
resource evidence qualify a production adapter. LP-native hierarchical
reduced-cost degradation is not asserted equivalent to these MIP lock rows.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from math import isfinite
from time import perf_counter
from typing import Any

from src.logic.resource_telemetry import event, observed_matrix, phase
from src.logic.scip_lexicographic import ABSOLUTE_GAP, common_gap, inherited_limit


@dataclass
class StageBundle:
    model: Any
    objectives: dict[str, Any]
    coefficient_fingerprint: str
    extract: Callable[[], dict]


def compare_lifecycle(factory, backend, config, roles, tolerance, *, mode, clock=perf_counter):
    """Reuse or cold rebuild; one wall budget includes rebuild and transitions.

    The caller supplies a canonical coefficient/objective fingerprint generated
    independently from the native solver. No model copy or full warm start is
    held while a previous model is disposed. Failure always releases ownership.
    """
    if mode not in {"reuse", "rebuild"} or backend not in {"gurobipy", "pyscipopt"}:
        raise ValueError("Unsupported stage lifecycle or native backend.")
    if not roles or len(set(roles)) != len(roles):
        raise ValueError("Stage roles must be nonempty and unique.")
    if config.solver_options or config.multiobjective_stage_options:
        raise ValueError("Solver profiles are not qualified by this miniature driver.")
    started = clock()
    bundle, fingerprint = None, None
    locks, records, outcome = {}, [], None
    build_seconds, disposal_seconds = 0.0, 0.0

    def dispose():
        nonlocal bundle, disposal_seconds
        if bundle is None:
            return
        mark = clock()
        model = bundle.model
        bundle = None  # Do not retain a disposed model through a failed cleanup.
        if backend == "gurobipy":
            model.dispose()
        else:
            model.freeProb()
        disposal_seconds += clock() - mark
        event("stage_model_disposal")

    try:
        for index, role in enumerate(roles, 1):
            if config.time_limit is not None and clock() - started >= config.time_limit:
                break
            if bundle is None:
                phase("stage_model_build")
                mark = clock()
                bundle = factory()
                build_seconds += clock() - mark
                if not bundle.coefficient_fingerprint:
                    raise ValueError("A canonical coefficient fingerprint is required.")
                if fingerprint is not None and fingerprint != bundle.coefficient_fingerprint:
                    raise ValueError("Rebuilt coefficient/objective fingerprint changed.")
                fingerprint = bundle.coefficient_fingerprint
                model = bundle.model
                if backend == "gurobipy":
                    model.update()
                    size, integers = model.NumVars, model.NumIntVars
                    model.NumObj = 1
                else:
                    size = model.getNVars()
                    integers = model.getNBinVars() + model.getNIntVars() + model.getNImplVars()
                if size > 100000:
                    raise ValueError("Production-size explicit lifecycle is not yet qualified.")
                if integers == 0:
                    raise ValueError("Qualification requires an original MIP, not LP degradation.")
                if backend == "gurobipy":
                    model.Params.Threads = config.threads or 0
                    model.Params.Seed = config.seed or 0
                else:
                    model.setParam("lp/threads", config.threads or 0)
                    model.setParam("randomization/randomseedshift", config.seed or 0)
                for prior, limit in locks.items():
                    if backend == "gurobipy":
                        model.addConstr(
                            bundle.objectives[prior] <= limit, name="priority_budget_" + prior
                        )
                    else:
                        model.addCons(
                            bundle.objectives[prior] <= limit, name="priority_budget_" + prior
                        )
                observed_matrix(model, backend)
            model = bundle.model
            remaining = (
                None if config.time_limit is None else config.time_limit - (clock() - started)
            )
            if remaining is not None and remaining <= 0:
                break
            phase(f"explicit_optimization_stage_{index}")
            expression = bundle.objectives[role]
            if backend == "gurobipy":
                model.setObjective(expression)
                model.Params.MIPGap = config.mip_gap
                model.Params.MIPGapAbs = ABSOLUTE_GAP
                if remaining is not None:
                    model.Params.TimeLimit = remaining
            else:
                model.setObjective(expression, "minimize")
                model.setParam("limits/gap", config.mip_gap)
                model.setParam("limits/absgap", ABSOLUTE_GAP)
                if remaining is not None:
                    model.setParam("limits/time", model.getSolvingTime() + remaining)
            mark = clock()
            model.optimize()
            if backend == "gurobipy":
                exists, status = model.SolCount > 0, str(model.Status)
                incumbent = float(model.ObjVal) if exists else None
                bound = float(model.ObjBound)
            else:
                exists, status = model.getNSols() > 0, str(model.getStatus())
                incumbent = float(model.getObjVal()) if exists else None
                bound = float(model.getDualbound())
                if abs(bound) >= model.infinity():
                    bound = None
            gap = common_gap(incumbent, bound) if exists and bound is not None else None
            valid_pair = (
                exists
                and bound is not None
                and isfinite(incumbent)
                and isfinite(bound)
                and bound <= incumbent + 1e-7
            )
            certified = valid_pair and (
                (role == "unmet_demand" and -tolerance <= incumbent <= tolerance)
                or max(0, incumbent - bound) <= ABSOLUTE_GAP
                or (gap is not None and gap <= config.mip_gap + 1e-12)
            )
            record = {
                "stage_number": index,
                "stage_role": role,
                "native_status": status,
                "incumbent": incumbent,
                "bound": bound,
                "mip_gap": gap,
                "certified": certified,
                "optimization_seconds": clock() - mark,
            }
            records.append(record)
            outcome = bundle.extract() if exists else None
            if not certified or index == len(roles):
                break
            limit = inherited_limit(incumbent, bound, config.mip_gap, tolerance)
            locks[role] = record["next_pass_limit"] = limit
            if mode == "rebuild":
                dispose()
            else:
                if backend == "pyscipopt":
                    model.freeTransform()
                    model.addCons(expression <= limit, name="priority_budget_" + role)
                else:
                    model.addConstr(expression <= limit, name="priority_budget_" + role)
    finally:
        dispose()
    return {
        "schema_version": "stage-lifecycle-qualification-v1",
        "mode": mode,
        "coefficient_fingerprint": fingerprint,
        "stages": records,
        "final_values": outcome,
        "model_build_seconds": build_seconds,
        "model_disposal_seconds": disposal_seconds,
        "end_to_end_seconds": clock() - started,
        "warm_start_policy": "cold_rebuild_no_transfer" if mode == "rebuild" else "native_reuse",
        "status": "complete"
        if len(records) == len(roles) and all(r["certified"] for r in records)
        else "partial",
        "scope": "small_original_mip_qualification_only",
    }
