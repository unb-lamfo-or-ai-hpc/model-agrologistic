"""Native PySCIPOpt two-stage extensive form with separately gated qualification.

Shared investment/capacity/cost helpers are algebraic: no Gurobi environment or
solver is instantiated. Recourse constraints, indicators, solve orchestration
and extraction are native SCIP. The independent solution validator remains a
separate reconstruction of the mathematical contract.
"""

from __future__ import annotations

from collections import defaultdict
from time import perf_counter
from types import SimpleNamespace

from src.logic.mathematical_contract import extensive_form_inputs, prepare_model_data
from src.logic.model_lifecycle import managed_model_solve, own_model
from src.logic.optimization import OptimizationResult, project_deterministic_result, scalar_mip_gap
from src.logic.optimization_gurobipy import (
    VALUE_TOL,
    _effective_reception_capacity_expr,
    _effective_shipping_capacity_expr,
    _effective_static_capacity_expr,
)
from src.logic.optimization_gurobipy_stochastic import (
    _add_first_stage_constraints,
    _build_investment_costs,
    _build_scenario_costs,
    _extract_warehouse_decisions,
)
from src.logic.resource_telemetry import install_scip_events, observed_matrix, phase
from src.logic.route_filtering import select_routes


def _configure(model, config, feasibility_tolerance):
    if config.compute_iis:
        raise ValueError("SCIP IIS export is not qualified; set compute_iis=false.")
    # In particular, never reinterpret Gurobi Method, SoftMemLimit or MIPGap.
    allowed = {"limits/memory", "lp/initalgorithm", "lp/resolvealgorithm", "presolving/maxrounds"}
    unknown = set(config.solver_options) - allowed
    if unknown:
        raise ValueError(f"Unsupported SCIP options: {sorted(unknown)}")
    model.hideOutput(not config.tee)
    if config.log_file:
        model.setLogfile(config.log_file)
    model.setParam("limits/gap", config.mip_gap)
    model.setParam("limits/absgap", 1e-10)
    model.setParam("timing/clocktype", 2)  # Wall clock, matching the global budget.
    model.setParam("numerics/feastol", min(1e-9, feasibility_tolerance / 100))
    model.setParam("randomization/randomseedshift", config.seed or 0)
    # optimize() is the sequential SCIP driver, not solveConcurrent(). These
    # settings are ceilings, not a claim of effective parallel search or LPs.
    model.setParam("parallel/maxnthreads", config.threads or 1)
    model.setParam("lp/threads", config.threads or 1)
    for name, value in config.solver_options.items():
        model.setParam(name, value)


@managed_model_solve
def solve_model_scip(data, model_config, solver_config):
    """One scalar extensive form, including the deterministic one-scenario case."""
    data, cfg = extensive_form_inputs(data, model_config)
    import pyscipopt as scip

    started = perf_counter()
    data = prepare_model_data(data, cfg)
    model = own_model(scip.Model("agrologistic_stochastic"), "pyscipopt")
    _configure(model, solver_config, cfg.feasibility_tolerance)
    scalar_progress = install_scip_events(model)
    q = scip.quicksum
    routes = select_routes(data, cfg)
    candidates = list(data.candidate_warehouses)
    expansions = [
        w
        for w in data.warehouses
        if cfg.allow_capacity_expansion and data.max_expand_capacity.get(w, 0) > 0
    ]
    bulks = [
        w
        for w in data.bulk_eligible_warehouses
        if cfg.allow_bulkification and w in data.warehouses and data.max_bulk_capacity.get(w, 0) > 0
    ]

    def variables(name, keys, *, binary=False, enabled=True):
        return {
            key: model.addVar(
                name=f"{name}[{key}]", vtype="B" if binary else "C", lb=0, ub=None if enabled else 0
            )
            for key in keys
        }

    first = {
        "open_candidate": variables("open", candidates, binary=True),
        "candidate_capacity": variables("candidate", candidates),
        "expand_warehouse": variables("expand", expansions, binary=True),
        "expand_capacity": variables("expansion", expansions),
        "bulkify_warehouse": variables("bulkify", bulks, binary=True),
        "bulk_capacity": variables("bulk", bulks),
    }
    first_args = dict(
        data=data,
        model_config=cfg,
        candidate_warehouses=candidates,
        expansion_warehouses=expansions,
        bulkification_warehouses=bulks,
        **first,
    )
    _add_first_stage_constraints(model=SimpleNamespace(addConstr=model.addCons), **first_args)
    investment = _build_investment_costs(gp=scip, **first_args)
    arc_sets = {
        "OD": sorted(routes.od),
        "DC": sorted(routes.dc),
        "DD": sorted(routes.dd) if cfg.use_warehouse_transshipment else [],
        "OC": sorted(routes.oc) if cfg.use_direct_origin_customer else [],
    }
    flows = {
        kind: variables(
            kind,
            ((s, a, b, p, t) for s in data.scenarios for a, b, p in arcs for t in data.periods),
        )
        for kind, arcs in arc_sets.items()
    }
    inventory = variables(
        "inventory",
        (
            (s, w, p, t)
            for s in data.scenarios
            for w in data.warehouses
            for p in data.products
            for t in data.periods
        ),
    )
    unmet = variables(
        "unmet",
        (
            (s, c, p, t)
            for s in data.scenarios
            for c in data.domestic_customers
            for p in data.products
            for t in data.periods
        ),
        enabled=cfg.allow_unmet_domestic_demand,
    )
    emergency = {
        kind: variables(
            kind,
            ((s, w, t) for s in data.scenarios for w in data.warehouses for t in data.periods),
            enabled=enabled,
        )
        for kind, enabled in (
            ("static", cfg.allow_emergency_static_capacity),
            ("reception", cfg.allow_emergency_reception_capacity),
        )
    }
    # Index the selected physical graph once, not all scenario-period variables.
    adjacency = defaultdict(list)
    for kind, arcs in arc_sets.items():
        for a, b, p in arcs:
            adjacency[kind, "out", a, p].append((a, b, p))
            adjacency[kind, "in", b, p].append((a, b, p))

    def flow_sum(kind, direction, node, p, s, t):
        return q(
            flows[kind][s, a, b, product, t]
            for a, b, product in adjacency[kind, direction, node, p]
        )

    capacity_args = (
        data,
        cfg,
        first["candidate_capacity"],
        first["expand_capacity"],
        first["bulk_capacity"],
    )
    for s in data.scenarios:
        for t_index, t in enumerate(data.periods):
            for p in data.products:
                for o in data.origins:
                    model.addCons(
                        flow_sum("OD", "out", o, p, s, t) + flow_sum("OC", "out", o, p, s, t)
                        == data.supply_s[s, o, p, t]
                    )
                for w in data.warehouses:
                    previous = (
                        data.initial_inventory.get((w, p), 0)
                        if t_index == 0
                        else inventory[s, w, p, data.periods[t_index - 1]]
                    )
                    model.addCons(
                        inventory[s, w, p, t]
                        == previous
                        + flow_sum("OD", "in", w, p, s, t)
                        + flow_sum("DD", "in", w, p, s, t)
                        - flow_sum("DC", "out", w, p, s, t)
                        - flow_sum("DD", "out", w, p, s, t)
                    )
                for c in data.domestic_customers:
                    model.addCons(
                        flow_sum("DC", "in", c, p, s, t)
                        + flow_sum("OC", "in", c, p, s, t)
                        + unmet[s, c, p, t]
                        == data.demand_dom_s[s, c, p, t]
                    )
                for c in data.export_customers:
                    model.addCons(
                        flow_sum("DC", "in", c, p, s, t) + flow_sum("OC", "in", c, p, s, t)
                        <= data.demand_exp_s[s, c, p, t]
                    )
            for w in data.warehouses:
                model.addCons(
                    q(inventory[s, w, p, t] for p in data.products)
                    <= _effective_static_capacity_expr(*capacity_args, w)
                    + emergency["static"][s, w, t]
                )
                model.addCons(
                    q(
                        flow_sum("OD", "in", w, p, s, t) + flow_sum("DD", "in", w, p, s, t)
                        for p in data.products
                    )
                    <= _effective_reception_capacity_expr(*capacity_args, w, t)
                    + emergency["reception"][s, w, t]
                )
                model.addCons(
                    q(
                        flow_sum("DC", "out", w, p, s, t) + flow_sum("DD", "out", w, p, s, t)
                        for p in data.products
                    )
                    <= _effective_shipping_capacity_expr(*capacity_args, w, t)
                )
                if w in first["open_candidate"]:
                    for kind in emergency:
                        # Nonnegativity makes slack <= 0 equivalent to slack = 0.
                        model.addConsIndicator(
                            emergency[kind][s, w, t] <= 0,
                            binvar=first["open_candidate"][w],
                            activeone=False,
                        )
    scenario_costs = _build_scenario_costs(
        gp=scip,
        data=data,
        model_config=cfg,
        scenarios=data.scenarios,
        **{f"{kind.lower()}_keys": mapping.keys() for kind, mapping in flows.items()},
        inventory_keys=inventory.keys(),
        unmet_keys=unmet.keys(),
        emergency_keys=emergency["static"].keys(),
        **{f"flow_{kind.lower()}": mapping for kind, mapping in flows.items()},
        inventory=inventory,
        unmet_demand=unmet,
        emergency_static_capacity=emergency["static"],
        emergency_reception_capacity=emergency["reception"],
    )
    expected = {
        name: q(
            data.scenario_prob[s] * components[name] for s, components in scenario_costs.items()
        )
        for name in next(iter(scenario_costs.values()))
    }
    penalties = {"unmet_demand", "emergency_static", "emergency_reception"}
    economic = q(investment.values()) + q(
        expr for name, expr in expected.items() if name not in penalties
    )
    penalized = q(investment.values()) + q(expected.values())
    primary = q(data.scenario_prob[s] * var for (s, c, p, t), var in unmet.items())
    capacity = q(
        data.scenario_prob[s] * var
        for mapping in emergency.values()
        for (s, w, t), var in mapping.items()
    )
    model.setObjective(penalized, "minimize")
    observed_matrix(model, "pyscipopt")
    build_seconds = perf_counter() - started
    if solver_config.time_limit is not None:
        model.setParam("limits/time", solver_config.time_limit)
    phase("optimization")
    optimization_started = perf_counter()
    model.optimize()
    optimization_seconds = perf_counter() - optimization_started
    native_status = str(model.getStatus())
    has_solution = model.getNSols() > 0
    status = _scalar_status(native_status, has_solution)
    metadata = {
        "formulation": "two_stage_extensive_form",
        "objective_policy": cfg.objective_policy,
        "mathematical_contract": data.metadata.get("mathematical_contract", {}),
        "scenario_probabilities": dict(data.scenario_prob),
        "scip_status": native_status,
        "scip_version": ".".join(
            str(v)
            for v in (model.getMajorVersion(), model.getMinorVersion(), model.getTechVersion())
        ),
        "pyscipopt_version": scip.__version__,
        "solution_count": model.getNSols(),
        **scalar_progress,
        "solve_driver": "scalar_optimize",
        "requested_threads": solver_config.threads,
        "effective_scip_parameters": {
            name: model.getParam(name)
            for name in (
                "limits/gap",
                "limits/absgap",
                "limits/memory",
                "parallel/maxnthreads",
                "lp/threads",
                "numerics/feastol",
            )
        },
        "timings": {
            "model_build_seconds": build_seconds,
            "optimization_seconds": optimization_seconds,
            "solver_reported_runtime_seconds": float(model.getSolvingTime()),
        },
        "objective_bound": _finite_bound(model.getDualbound(), model.infinity()),
        "qualification": (
            "Native SCIP backend; large-network and cross-backend qualification "
            "remain separate gates."
        ),
    }
    result = OptimizationResult(
        status=status,
        solver_backend="pyscipopt",
        solver_name="scip",
        model_mode=model_config.mode,
        runtime_seconds=build_seconds + optimization_seconds,
        mip_gap=None,
        metadata=metadata,
    )
    if not has_solution:
        return result
    extraction_started = perf_counter()
    phase("result_extraction")
    sol = model.getBestSol()

    def value(expression):
        return (
            float(expression)
            if isinstance(expression, (int, float))
            else float(model.getSolVal(sol, expression))
        )

    # Only the small first-stage maps need wrappers for the shared row formatter.
    wrapped_first = {
        name: {key: SimpleNamespace(X=value(var)) for key, var in mapping.items()}
        for name, mapping in first.items()
    }
    result.warehouse_decisions = _extract_warehouse_decisions(
        data=data, model_config=cfg, **wrapped_first
    )
    for kind, mapping in flows.items():
        for (s, a, b, p, t), var in mapping.items():
            amount = value(var)
            if amount <= VALUE_TOL:
                continue
            row = dict(scenario=s, route_type=kind, product=p, period=t, value=amount)
            if kind == "DD":
                row.update(warehouse_from=a, warehouse_to=b)
            elif kind == "OD":
                row.update(origin=a, warehouse=b, customer=None)
            else:
                row.update(
                    origin=a if kind == "OC" else None,
                    warehouse=a if kind == "DC" else None,
                    customer=b,
                    customer_type="export" if b in data.export_customers else "domestic",
                )
            result.flows.append(row)
    for mapping, fields, destination in (
        (inventory, ("scenario", "warehouse", "product", "period"), result.inventories),
        (unmet, ("scenario", "customer", "product", "period"), result.unmet_demand),
    ):
        for key, var in mapping.items():
            amount = value(var)
            if amount > VALUE_TOL:
                destination.append(dict(zip(fields, key, strict=True)) | {"value": amount})
    for kind, mapping in emergency.items():
        for (s, w, t), var in mapping.items():
            amount = value(var)
            if amount > VALUE_TOL:
                result.emergency_capacity.append(
                    dict(scenario=s, warehouse=w, period=t, capacity_type=kind, value=amount)
                )
    result.cost_breakdown = {name: value(expr) for name, expr in (investment | expected).items()}
    objective_values = {
        "expected_unmet_demand": value(primary),
        "expected_emergency_capacity": value(capacity),
        "economic_cost": value(economic),
        "penalized_cost": value(penalized),
    }
    result.objective_value = float(model.getObjVal())
    bound = metadata["objective_bound"]
    result.mip_gap = scalar_mip_gap(result.objective_value, bound)
    metadata["scip_native_gap"] = _finite_bound(model.getGap(), model.infinity())
    scenario_metrics = {
        s: {
            "probability": data.scenario_prob[s],
            "operating_cost": sum(value(expr) for expr in components.values()),
            "total_flow": sum(r["value"] for r in result.flows if r["scenario"] == s),
            "total_unmet_demand": sum(
                r["value"] for r in result.unmet_demand if r["scenario"] == s
            ),
            "total_emergency_capacity": sum(
                r["value"] for r in result.emergency_capacity if r["scenario"] == s
            ),
        }
        for s, components in scenario_costs.items()
    }
    result.metrics.update(
        objective_values=objective_values,
        scenario_metrics=scenario_metrics,
        investment_cost=sum(value(expr) for expr in investment.values()),
        expected_operating_cost=sum(value(expr) for expr in expected.values()),
    )
    metadata["timings"]["result_extraction_seconds"] = perf_counter() - extraction_started
    return project_deterministic_result(result) if model_config.mode == "det" else result


def _finite_bound(value, infinity=None):
    from math import isfinite

    value = float(value)
    return value if isfinite(value) and (infinity is None or abs(value) < infinity) else None


def _scalar_status(native_status, has_solution):
    if not has_solution:
        return {
            "infeasible": "infeasible",
            "unbounded": "unbounded",
            "timelimit": "time_limit",
        }.get(native_status, "error")
    return (
        "optimal"
        if native_status == "optimal"
        else ("time_limit" if native_status == "timelimit" else "feasible")
    )
