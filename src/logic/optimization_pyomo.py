"""Explicitly qualified solver-neutral scalar DET/STO Pyomo formulation.

Native reference backends remain unchanged. Candidate slack representatives use
the documented proved reformulation, selected explicitly by solver option.
"""

from collections import defaultdict
from importlib.metadata import version
from math import isfinite
from time import perf_counter
from types import SimpleNamespace

from src.logic.mathematical_contract import extensive_form_inputs, prepare_model_data
from src.logic.optimization import (
    OptimizationBackendNotImplementedError, OptimizationResult,
    project_deterministic_result, scalar_mip_gap,
)
from src.logic.optimization_gurobipy import (
    VALUE_TOL, _effective_reception_capacity_expr,
    _effective_shipping_capacity_expr, _effective_static_capacity_expr,
)
from src.logic.optimization_gurobipy_stochastic import (
    _add_first_stage_constraints, _build_investment_costs,
    _build_scenario_costs, _extract_warehouse_decisions,
)
from src.logic.pyomo_bounds import POLICY, candidate_slack_bounds
from src.logic.route_filtering import select_routes

SOLVERS = {"highs": "appsi_highs", "appsi_highs": "appsi_highs", "cbc": "cbc"}


def settings(config):
    name = config.solver_name.lower()
    if name not in SOLVERS:
        raise OptimizationBackendNotImplementedError(
            f"Pyomo interface {name!r} is not qualified; choose highs/appsi_highs/cbc."
        )
    options = dict(config.solver_options)
    if options.pop("indicator_reformulation", None) != POLICY:
        raise ValueError("Explicit indicator_reformulation='bounded_scalar_slacks_v1' required.")
    guard = options.pop("pyomo_max_variables", 200000)
    if isinstance(guard, bool) or not isinstance(guard, int) or guard <= 0:
        raise ValueError("Positive integer Pyomo variable guard required.")
    if options or config.compute_iis or config.collect_resource_diagnostics:
        raise ValueError("Unqualified Pyomo options/IIS/resource diagnostics.")
    return SOLVERS[name], guard


def build_model(data, cfg, *, max_variables=200000):
    import pyomo.environ as pyo

    data, cfg = extensive_form_inputs(data, cfg)
    data = prepare_model_data(data, cfg)
    bounds, proof = candidate_slack_bounds(data, cfg)
    routes = select_routes(data, cfg)
    candidates = list(data.candidate_warehouses)
    expansions = [w for w in data.warehouses
                  if cfg.allow_capacity_expansion and data.max_expand_capacity.get(w, 0) > 0]
    bulks = [w for w in data.bulk_eligible_warehouses
             if cfg.allow_bulkification and w in data.warehouses
             and data.max_bulk_capacity.get(w, 0) > 0]
    count = (
        2 * (len(candidates) + len(expansions) + len(bulks))
        + len(data.scenarios) * len(data.periods) * (
            len(routes.od) + len(routes.dc)
            + (len(routes.dd) if cfg.use_warehouse_transshipment else 0)
            + (len(routes.oc) if cfg.use_direct_origin_customer else 0)
            + len(data.warehouses) * len(data.products)
            + len(data.domestic_customers) * len(data.products)
            + 2 * len(data.warehouses)
        )
    )
    if count > max_variables:
        raise ValueError("Pyomo variable guard exceeded before model allocation.")
    model = pyo.ConcreteModel()
    model.rows = pyo.ConstraintList()
    q = pyo.quicksum

    def add_cons(expression, name=None):
        if expression is True:
            expression = pyo.Constraint.Feasible
        elif expression is False:
            expression = pyo.Constraint.Infeasible
        return model.rows.add(expression)

    def variables(name, keys, *, binary=False, enabled=True):
        variable = pyo.Var(
            list(keys), domain=pyo.Binary if binary else pyo.NonNegativeReals,
            bounds=(0, None if enabled else 0),
        )
        model.add_component(name, variable)
        return variable

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
    _add_first_stage_constraints(model=SimpleNamespace(addConstr=add_cons), **first_args)
    investment = _build_investment_costs(gp=pyo, **first_args)
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
                    add_cons(
                        flow_sum("OD", "out", o, p, s, t) + flow_sum("OC", "out", o, p, s, t)
                        == data.supply_s[s, o, p, t]
                    )
                for w in data.warehouses:
                    previous = (
                        data.initial_inventory.get((w, p), 0)
                        if t_index == 0
                        else inventory[s, w, p, data.periods[t_index - 1]]
                    )
                    add_cons(
                        inventory[s, w, p, t]
                        == previous
                        + flow_sum("OD", "in", w, p, s, t)
                        + flow_sum("DD", "in", w, p, s, t)
                        - flow_sum("DC", "out", w, p, s, t)
                        - flow_sum("DD", "out", w, p, s, t)
                    )
                for c in data.domestic_customers:
                    add_cons(
                        flow_sum("DC", "in", c, p, s, t)
                        + flow_sum("OC", "in", c, p, s, t)
                        + unmet[s, c, p, t]
                        == data.demand_dom_s[s, c, p, t]
                    )
                for c in data.export_customers:
                    add_cons(
                        flow_sum("DC", "in", c, p, s, t) + flow_sum("OC", "in", c, p, s, t)
                        <= data.demand_exp_s[s, c, p, t]
                    )
            for w in data.warehouses:
                add_cons(
                    q(inventory[s, w, p, t] for p in data.products)
                    <= _effective_static_capacity_expr(*capacity_args, w)
                    + emergency["static"][s, w, t]
                )
                add_cons(
                    q(
                        flow_sum("OD", "in", w, p, s, t) + flow_sum("DD", "in", w, p, s, t)
                        for p in data.products
                    )
                    <= _effective_reception_capacity_expr(*capacity_args, w, t)
                    + emergency["reception"][s, w, t]
                )
                add_cons(
                    q(
                        flow_sum("DC", "out", w, p, s, t) + flow_sum("DD", "out", w, p, s, t)
                        for p in data.products
                    )
                    <= _effective_shipping_capacity_expr(*capacity_args, w, t)
                )
                if w in first["open_candidate"]:
                    for kind in emergency:
                        add_cons(
                            emergency[kind][s, w, t]
                            <= bounds[kind][s, w, t] * first["open_candidate"][w]
                        )
    scenario_costs = _build_scenario_costs(
        gp=pyo,
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

    model.objective = pyo.Objective(expr=penalized, sense=pyo.minimize)
    return SimpleNamespace(
        model=model, data=data, cfg=cfg, first=first, flows=flows, inventory=inventory,
        unmet=unmet, emergency=emergency, investment=investment, expected=expected,
        economic=economic, penalized=penalized, primary=primary, capacity=capacity,
        scenario_costs=scenario_costs, proof=proof, variable_count=count,
    )


def finite(value):
    try:
        value = float(value)
        return value if isfinite(value) else None
    except (TypeError, ValueError):
        return None


def normalized_status(termination, usable):
    token = str(termination).split(".")[-1].lower()
    if token in {"maxtimelimit", "timelimit"}:
        return "time_limit"
    if token in {"infeasible", "unbounded"}:
        return token if not usable else "error"
    if token == "optimal":
        return "optimal" if usable else "error"
    return "feasible" if usable else "error"


def solve_model_pyomo(data, model_config, solver_config):
    """One scalar solve through the selected adapter; no fallback or warm start."""
    selected, guard = settings(solver_config)
    import pyomo.environ as pyo

    started = perf_counter()
    built = build_model(data, model_config, max_variables=guard)
    model = built.model
    adapter, result, failed = None, None, False
    try:
        if selected == "appsi_highs":
            from pyomo.contrib.appsi.solvers import Highs

            adapter = Highs()
            if not adapter.available():
                raise RuntimeError("Existing highspy installation required.")
            adapter.config.load_solution = False
            adapter.config.stream_solver = solver_config.tee
            adapter.config.time_limit = solver_config.time_limit
            adapter.config.mip_gap = solver_config.mip_gap
            if solver_config.log_file:
                adapter.config.logfile = solver_config.log_file
            adapter.highs_options.update({
                "threads": solver_config.threads or 1,
                "random_seed": solver_config.seed or 0,
                "mip_feasibility_tolerance": 1e-9,
            })
            transfer_started = perf_counter()
            adapter.set_instance(model)
            transfer_seconds = perf_counter() - transfer_started
            build_seconds = perf_counter() - started
            optimization_started = perf_counter()
            solved = adapter.solve(model)
            optimization_seconds = perf_counter() - optimization_started
            objective = finite(solved.best_feasible_objective)
            bound = finite(solved.best_objective_bound)
            usable = objective is not None
            if usable:
                adapter.load_vars()
            native_gap = finite(adapter._solver_model.getInfo().mip_gap) if usable else None
            native_runtime = finite(solved.wallclock_time)
            termination = str(solved.termination_condition)
            versions = {"pyomo": version("pyomo"), "highspy": version("highspy")}
        else:
            adapter = pyo.SolverFactory("cbc")
            if not adapter.available(exception_flag=False):
                raise RuntimeError("Existing CBC executable required.")
            adapter.options.update({
                "seconds": solver_config.time_limit or 1e20,
                "timeMode": "elapsed", "ratio": solver_config.mip_gap,
                "threads": solver_config.threads or 1,
                "randomSeed": solver_config.seed or 0,
                "randomCbcSeed": solver_config.seed or 0,
                "primalTolerance": 1e-9, "integerTolerance": 1e-9,
            })
            build_seconds = perf_counter() - started
            transfer_seconds = None
            optimization_started = perf_counter()
            kwargs = {"tee": solver_config.tee, "load_solutions": False}
            if solver_config.log_file:
                kwargs["logfile"] = solver_config.log_file
            solved = adapter.solve(model, **kwargs)
            optimization_seconds = perf_counter() - optimization_started
            termination = str(solved.solver.termination_condition)
            usable = len(solved.solution) > 0 and termination not in {
                "infeasible", "unbounded", "infeasibleOrUnbounded",
            }
            objective = None
            if usable:
                model.solutions.load_from(solved)
                objective = finite(pyo.value(model.objective))
                usable = objective is not None
            bound = finite(solved.problem.lower_bound)
            native_gap = None  # The retained CBC result API does not expose its native gap.
            native_runtime = finite(solved.solver.time)
            versions = {"pyomo": version("pyomo"), "cbc": ".".join(map(str, adapter.version()))}
        metadata = {
            "formulation": "two_stage_extensive_form",
            "objective_policy": built.cfg.objective_policy,
            "mathematical_contract": built.data.metadata.get("mathematical_contract", {}),
            "scenario_probabilities": dict(built.data.scenario_prob),
            "pyomo_reformulation": built.proof,
            "pyomo_solver_interface": selected, "solver_versions": versions,
            "solver_termination": termination, "objective_bound": bound,
            "pyomo_native_gap": native_gap,
            "requested_threads": solver_config.threads,
            "matrix": {"variables": built.variable_count, "constraints": len(model.rows)},
            "timings": {
                "model_build_seconds": build_seconds,
                "solver_transfer_seconds": transfer_seconds,
                "optimization_seconds": optimization_seconds,
                "solver_reported_runtime_seconds": native_runtime,
            },
            "qualification": (
                "Public miniature multisolver qualification; no large-input/HPC "
                "resource or production isolation certification."
            ),
        }
        result = OptimizationResult(
            status=normalized_status(termination, usable), objective_value=objective,
            solver_backend="pyomo", solver_name=solver_config.solver_name,
            model_mode=model_config.mode, runtime_seconds=build_seconds + optimization_seconds,
            metadata=metadata, mip_gap=scalar_mip_gap(objective, bound),
        )
        if not usable:
            return result
        return extract_result(built, result, model_config.mode)
    except BaseException:
        failed = True
        raise
    finally:
        cleanup_started = perf_counter()
        try:
            if adapter is not None and selected == "appsi_highs":
                native = getattr(adapter, "_solver_model", None)
                if native is not None:
                    native.clear()
                    adapter._solver_model = None
                cached = getattr(adapter, "_last_results_object", None)
                if cached is not None:
                    cached.solution_loader.invalidate()
            model.clear()
            if result is not None:
                result.metadata["native_model_lifecycle"] = [{
                    "backend": "pyomo", "status": "disposed",
                    "disposal_seconds": perf_counter() - cleanup_started,
                }]
        except Exception as exc:
            if not failed:
                raise RuntimeError("Pyomo/native cleanup failed.") from exc


def extract_result(built, result, mode):
    import pyomo.environ as pyo

    started = perf_counter()
    resolve_unreferenced(built.model)
    data, cfg = built.data, built.cfg
    first, flows = built.first, built.flows
    inventory, unmet, emergency = built.inventory, built.unmet, built.emergency
    investment, expected = built.investment, built.expected
    scenario_costs = built.scenario_costs
    metadata = result.metadata

    def value(expression):
        return float(pyo.value(expression))

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
        "expected_unmet_demand": value(built.primary),
        "expected_emergency_capacity": value(built.capacity),
        "economic_cost": value(built.economic),
        "penalized_cost": value(built.penalized),
    }
    result.objective_value = value(built.model.objective)
    bound = metadata["objective_bound"]
    result.mip_gap = scalar_mip_gap(result.objective_value, bound)
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
    metadata["timings"]["result_extraction_seconds"] = perf_counter() - started
    return project_deterministic_result(result) if mode == "det" else result


def resolve_unreferenced(model):
    """Only structurally unused variables may receive a deterministic zero."""
    import pyomo.environ as pyo
    from pyomo.core.expr.visitor import identify_variables

    used = {id(v) for v in identify_variables(model.objective.expr, include_fixed=True)}
    for row in model.rows.values():
        used.update(id(v) for v in identify_variables(row.body, include_fixed=True))
    for variable in model.component_data_objects(pyo.Var):
        if variable.value is None:
            if id(variable) in used or (variable.lb is not None and variable.lb > 0):
                raise ValueError("Referenced Pyomo primal value missing.")
            variable.set_value(0)
