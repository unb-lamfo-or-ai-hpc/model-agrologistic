"""Native construction and export controls using symbolic values, never a solver."""

import copy
import json
from dataclasses import asdict, replace
from types import SimpleNamespace

import pyomo.environ as pyo
import pytest
from pyomo.repn import generate_standard_repn

from src.logic.effective_baseline import build_effective_model, effective_projection, seal
from src.logic.mathematical_contract import extensive_form_inputs, prepare_model_data
from src.logic.model_config import SolverConfig
from src.logic.native_effective import (
    DEFAULT_PARAMETERS,
    audit_reference_parameters,
    check_native_embedding,
    dense_vector_coverage,
    finish_effective_result,
    prepare_effective_native,
    reference_solver_config,
)
from src.logic.optimization import OptimizationResult, project_deterministic_result
from src.logic.optimization_gurobipy import _apply_solver_parameters
from src.logic.optimization_gurobipy_stochastic import populate_native_model
from src.logic.parametric_scenarios import ParameterScenario, apply_scenario
from tests.test_effective_policy import export_data


class Variables(dict):
    def sum(self, *pattern):
        return pyo.quicksum(v for k, v in self.items()
                            if all(a == "*" or a == b for a, b in zip(pattern, k, strict=True)))


class SymbolicNativeModel:
    """Record the native construction API as expressions; no optimize method exists."""

    def __init__(self):
        self.symbolic = pyo.ConcreteModel()
        self.symbolic.rows = pyo.ConstraintList()
        self.variables, self.constraints, self.indicators = {}, {}, {}

    def addVars(self, keys, *, vtype, name, lb=0, ub=float("inf")):
        domain = pyo.Binary if vtype == "B" else pyo.NonNegativeReals
        component = pyo.Var(list(keys), domain=domain, initialize=0,
                            bounds=(lb, None if ub == float("inf") else ub))
        self.symbolic.add_component(name, component)
        self.variables[name] = Variables(component.items())
        return self.variables[name]

    def addConstr(self, expression, *, name):
        if expression is True:
            expression = pyo.Constraint.Feasible
        elif expression is False:
            expression = pyo.Constraint.Infeasible
        self.constraints[name] = self.symbolic.rows.add(expression)

    def addGenConstrIndicator(self, binary, active, expression, *, name):
        self.indicators[name] = (binary, active, expression)

    def setObjective(self, expression, sense):
        assert sense == 1
        self.symbolic.objective = pyo.Objective(expr=expression)


GRB = SimpleNamespace(BINARY="B", CONTINUOUS="C", INFINITY=float("inf"), MINIMIZE=1)
GP = SimpleNamespace(quicksum=pyo.quicksum)


def construct(data, cfg, *, effective=True):
    solver = reference_solver_config()
    context = prepare_effective_native(data, cfg, solver) if effective else None
    native_data, native_cfg = extensive_form_inputs(data, cfg)
    native_data = prepare_model_data(native_data, native_cfg)
    model = SymbolicNativeModel()
    built = populate_native_model(GP, GRB, model, native_data, native_cfg, solver,
                                  effective_context=context)
    return model, built, context, native_data, native_cfg


def investment_data(mode):
    """Two products, two periods and nine unequal STO realizations with shared assets."""
    data, cfg = export_data(mode)
    for key in ("effective_baseline", "mathematical_contract", "_frozen_routes"):
        data.metadata.pop(key, None)
    data.warehouses.append("N")
    data.candidate_warehouses.append("N")
    data.bulk_eligible_warehouses.append("W")
    data.products.append("Q")
    data.periods.append("t2")
    for name in ("static_capacity", "reception_capacity", "shipping_capacity",
                 "emergency_static_capacity_penalty", "emergency_reception_capacity_penalty"):
        getattr(data, name)["N"] = 0
    data.static_capacity["W"] = 100
    data.max_candidate_capacity["N"] = 50
    data.max_expand_capacity["W"] = 25
    data.max_bulk_capacity["W"] = 40
    data.opening_fixed_cost["N"] = 0
    data.candidate_capacity_cost["N"] = 1250
    data.freight_warehouse["N"] = data.freight_warehouse["W"]
    data.expand_fixed_cost["W"] = data.bulk_fixed_cost["W"] = 0
    data.expand_variable_cost["W"], data.bulk_variable_cost["W"] = 900, 520
    data.unmet_demand_penalty["C", "Q"] = data.unmet_demand_penalty["C", "P"]
    for code, pairs in (
        ("od", [("O", "W"), ("O", "N")]),
        ("dc", [("W", "C"), ("N", "C"), ("W", "X"), ("N", "X")]),
        ("dd", [("W", "N"), ("N", "W")]),
    ):
        setattr(data, f"routes_{code}", {(a, b, p) for a, b in pairs for p in data.products})
        setattr(data, f"dist_{code}", {(a, b): i + 1 for i, (a, b) in enumerate(pairs)})
    for name, nodes in (("supply", data.origins), ("demand_dom", data.domestic_customers),
                        ("demand_exp", data.export_customers)):
        values = {(n, p, t): 10 + i * 7 + j * 3 for n in nodes
                  for i, p in enumerate(data.products) for j, t in enumerate(data.periods)}
        setattr(data, name, values)
    if mode == "sto":
        data.scenarios = [f"s{i}" for i in range(9)]
        data.scenario_prob = dict.fromkeys(data.scenarios, 1 / 9)
        for name in ("supply", "demand_dom", "demand_exp"):
            setattr(data, name + "_s", {(s, *k): v * (i + 1)
                    for i, s in enumerate(data.scenarios) for k, v in getattr(data, name).items()})
    return seal(effective_projection(data, cfg), cfg, {"scenario_id": "baseline"}), cfg


def transformed(data, cfg, *, k=1, beta=None, alpha=None):
    return apply_scenario(data, cfg, ParameterScenario(
        "native-software-control", {"candidate_limit": k, "expansion_limit": k},
        beta=beta, alpha=alpha, justification="Local algebra/export control; no execution.",
    ))[0]


ALIASES = {"open": "open_candidate", "candidate": "candidate_capacity",
           "expand": "expand_warehouse",
           "expansion": "expand_capacity", "bulkify": "bulkify_warehouse", "bulk": "bulk_capacity",
           "OD": "flow_od", "DC": "flow_dc", "DD": "flow_dd", "OC": "flow_oc",
           "unmet": "unmet_demand", "static": "emergency_static_capacity",
           "reception": "emergency_reception_capacity"}


def coefficients(expression):
    repn = generate_standard_repn(expression)
    values = {}
    for var, coef in zip(repn.linear_vars, repn.linear_coefs, strict=True):
        family = var.parent_component().local_name
        index = var.index()
        key = (ALIASES.get(family, family), index if isinstance(index, tuple) else (index,))
        values[key] = float(coef)
    return values, float(repn.constant or 0)


def constraint_signature(row):
    terms, constant = coefficients(row.body)
    lower = None if row.lower is None else float(pyo.value(row.lower)) - constant
    upper = None if row.upper is None else float(pyo.value(row.upper)) - constant
    if lower is not None and upper is None:
        terms, lower, upper = {k: -v for k, v in terms.items()}, None, -lower
    if lower == upper and terms and terms[min(terms)] < 0:
        terms, lower, upper = {k: -v for k, v in terms.items()}, -upper, -lower
    return sorted(terms.items()), lower, upper


@pytest.mark.parametrize("mode", ["det", "sto"])
def test_native_neutral_linear_algebra_matches_independent_pyomo_builder(mode):
    data, cfg = export_data(mode)  # No candidate indicators in this comparison.
    model, _, _, _, _ = construct(data, cfg)
    reference = build_effective_model(data, cfg).model
    assert sorted(map(constraint_signature, model.constraints.values()), key=str) == sorted(
        (constraint_signature(c) for c in reference.rows.values()), key=str)
    assert coefficients(model.symbolic.objective.expr) == coefficients(reference.objective.expr)
    assert model.indicators == {}


@pytest.mark.parametrize("mode", ["det", "sto"])
def test_neutral_context_preserves_all_native_rows_domains_costs_and_indicators(mode):
    data, cfg = investment_data(mode)
    original = copy.deepcopy(data)
    effective, _, _, _, _ = construct(data, cfg)
    historical = copy.deepcopy(data)
    historical.metadata.pop("effective_baseline")
    old, _, _, _, _ = construct(historical, cfg, effective=False)
    assert {k: constraint_signature(v) for k, v in effective.constraints.items()} == {
        k: constraint_signature(v) for k, v in old.constraints.items()}
    assert coefficients(effective.symbolic.objective.expr) == coefficients(
        old.symbolic.objective.expr)
    assert [(k, v[1], str(v[2])) for k, v in effective.indicators.items()] == [
        (k, v[1], str(v[2])) for k, v in old.indicators.items()]
    assert all(v.is_binary() for v in effective.variables["open_candidate"].values())
    assert data == original


@pytest.mark.parametrize("mode", ["det", "sto"])
@pytest.mark.parametrize("k", [1.25, 1.5, 2])
def test_native_k_changes_only_two_activation_coefficients_and_never_tonne_prices(mode, k):
    data, cfg = investment_data(mode)
    before, _, _, _, _ = construct(data, cfg)
    changed = transformed(data, cfg, k=k)
    after, built, _, _, _ = construct(changed, cfg)
    differences = {name for name in before.constraints
                   if constraint_signature(before.constraints[name])
                   != constraint_signature(after.constraints[name])}
    assert differences == {"candidate_scalable_capacity[N]", "expansion_capacity[W]"}
    assert coefficients(after.symbolic.objective.expr) == coefficients(
        before.symbolic.objective.expr)
    costs, _ = coefficients(after.symbolic.objective.expr)
    assert costs["candidate_capacity", ("N",)] == 1250
    assert costs["expand_capacity", ("W",)] == 900
    built.candidate_capacity["N"].set_value(40)
    built.expand_capacity["W"].set_value(10)
    assert pyo.value(sum(built.investment_costs.values())) == 40 * 1250 + 10 * 900
    assert changed.max_expand_capacity["W"] == k * 0.25 * data.static_capacity["W"]
    assert len(after.variables["candidate_capacity"]) == 1  # Shared across all scenarios.
    for _binary, active, expression in after.indicators.values():
        assert active is False and expression.arg(1) == 0


@pytest.mark.parametrize("mode", ["det", "sto"])
def test_native_policies_are_full_horizon_product_scenario_rows_without_probabilities(mode):
    data, cfg = investment_data(mode)
    scenarios = data.scenarios if mode == "sto" else ["deterministic"]
    beta = {p: {s: 0.9 + i / 100 for i, s in enumerate(scenarios)} for p in data.products}
    changed = transformed(data, cfg, beta=beta, alpha=0.5)
    model, _, context, _, _ = construct(changed, cfg)
    rows = {n: c for n, c in model.constraints.items() if n.startswith("effective_")}
    assert len(rows) == len(data.products) * len(scenarios) * 2
    reference = build_effective_model(changed, cfg).model.effective_policy
    for row in context.rows:
        actual = rows[f"effective_{row.control}[{row.scenario},{row.product}]"]
        block = reference.service_floor if row.control == "beta" else reference.export_ceiling
        assert constraint_signature(actual) == constraint_signature(
            block[row.scenario, row.product])
        assert set(coefficients(actual.body)[0].values()) == {1}
        if row.control == "beta":
            assert len(coefficients(actual.body)[0]) == (
                len(data.domestic_customers) * len(data.periods))
        else:
            assert len(coefficients(actual.body)[0]) == 2 * len(data.periods)
    assert all(f"export_upper_bound[{s},X,{p},{t}]" in model.constraints
               for s in scenarios for p in data.products for t in data.periods)


def test_disabled_and_zero_policies_have_different_native_rows():
    data, cfg = export_data()
    neutral, *_ = construct(data, cfg)
    zero, *_ = construct(transformed(data, cfg, beta=0, alpha=0), cfg)
    assert not any(n.startswith("effective_") for n in neutral.constraints)
    assert zero.constraints["effective_alpha[deterministic,P]"].upper == 0
    assert zero.constraints["effective_beta[deterministic,P]"].upper == 10


@pytest.mark.parametrize("mode", ["det", "sto"])
def test_seals_and_det_embedding_reject_drift_before_native_construction(mode):
    data, cfg = export_data(mode)
    changed = transformed(data, cfg, beta=0.9)
    solver = reference_solver_config()
    context = prepare_effective_native(changed, cfg, solver)
    native_data, native_cfg = extensive_form_inputs(changed, cfg)
    altered = copy.deepcopy(native_data)
    altered.supply_s[next(iter(altered.supply_s))] += 1
    with pytest.raises(ValueError, match="embedding differs"):
        check_native_embedding(context, altered, native_cfg, solver)
    changed.metadata["effective_baseline"]["specification"]["beta"] = 0.1
    with pytest.raises(ValueError, match="changed after sealing"):
        prepare_effective_native(changed, cfg, solver)


@pytest.mark.parametrize("override", [
    {"threads": 1}, {"seed": 42}, {"mip_gap": 0.01}, {"time_limit": 60},
    {"solver_options": {"Method": 2}}, {"solver_options": {"Method": -1, "MIPFocus": 1}},
    {"compact_python_indices": True}, {"compute_iis": True},
])
def test_historical_or_tuned_profiles_are_rejected_before_import(override):
    data, cfg = export_data()
    with pytest.raises(ValueError, match="Rev4 automatic"):
        prepare_effective_native(data, cfg, replace(reference_solver_config(), **override))


def test_reference_parameter_application_does_not_assign_mipgap_or_seed():
    assigned = {}

    class Parameters:
        def __setattr__(self, name, value):
            assigned[name] = value

    native = SimpleNamespace(Params=Parameters(), setParam=lambda n, v: assigned.update({n: v}))
    _apply_solver_parameters(native, reference_solver_config())
    assert assigned == {"TimeLimit": 28800, "Threads": 0, "Method": -1, "OutputFlag": 1}
    # Existing callers keep their historical explicit profile and defaults.
    assigned.clear()
    _apply_solver_parameters(native, SolverConfig(mip_gap=0.01, seed=42, threads=4))
    assert assigned["MIPGap"] == 0.01 and assigned["Seed"] == 42 and assigned["Threads"] == 4


def test_parameter_readback_rejects_default_drift_and_serializes_infinite_limits():
    defaults = dict.fromkeys(DEFAULT_PARAMETERS, 0)
    defaults.update(MIPGap=1e-4, Seed=0, SoftMemLimit=float("inf"), Method=-1,
                    Threads=0, TimeLimit=float("inf"))
    effective = {**defaults, "TimeLimit": 28800}
    model = SimpleNamespace(getParamInfo=lambda n: (n, float, effective[n], 0, 1e100, defaults[n]))
    gp = SimpleNamespace(gurobi=SimpleNamespace(version=lambda: (14, 0, 0)))
    audit = audit_reference_parameters(model, gp, reference_solver_config())
    json.dumps(audit, allow_nan=False)
    effective["Seed"] = 42
    with pytest.raises(ValueError, match="Seed"):
        audit_reference_parameters(model, gp, reference_solver_config())


def extracted_plan(mode, monkeypatch):
    from src.logic import optimization_gurobipy_stochastic as core

    data, cfg = export_data(mode)
    changed = transformed(data, cfg, beta=0.6, alpha=0.4)
    model, built, context, native_data, native_cfg = construct(changed, cfg)
    for s in native_data.scenarios:
        built.flow_od[s, "O", "W", "P", "t"].set_value(10)
        built.flow_dc[s, "W", "C", "P", "t"].set_value(7)
        built.flow_dc[s, "W", "X", "P", "t"].set_value(3)
        built.unmet_demand[s, "C", "P", "t"].set_value(3)
    monkeypatch.setattr(core, "_value", lambda v: float(pyo.value(v)))
    monkeypatch.setattr(core, "_expression_value", lambda v: float(pyo.value(v)))
    args = {name: getattr(built, name) for name in (
        "flow_od", "flow_dc", "flow_oc", "flow_dd", "inventory", "unmet_demand",
        "emergency_static_capacity", "emergency_reception_capacity", "open_candidate",
        "candidate_capacity", "expand_warehouse", "expand_capacity", "bulkify_warehouse",
        "bulk_capacity", "investment_costs", "expected_costs", "scenario_costs",
    )}
    objective = float(pyo.value(model.symbolic.objective.expr))
    result = core._extract_stochastic_result(
        data=native_data, model_config=native_cfg, solver_config=reference_solver_config(),
        model=SimpleNamespace(ObjVal=objective, ObjBound=objective), GRB=GRB,
        status="feasible", runtime_seconds=0, metadata={"objective_bound": objective}, **args,
    )
    if mode == "det":
        project_deterministic_result(result)
    return context, finish_effective_result(context, result)


@pytest.mark.parametrize("mode", ["det", "sto"])
def test_dense_native_export_includes_zeros_and_reconciles_independent_costs(mode, monkeypatch):
    context, result = extracted_plan(mode, monkeypatch)
    assert result.metadata["effective_dense_coverage"]["status"] == "accepted"
    assert result.metadata["effective_validation"]["status"] == "accepted"
    assert result.inventories and all(r["value"] == 0 for r in result.inventories)
    assert result.emergency_capacity and all(r["value"] == 0 for r in result.emergency_capacity)
    assert result.objective_value == 3156
    # Binary64-safe JSON round-trip; display rounding never enters the validator.
    restored = OptimizationResult(**json.loads(json.dumps(asdict(result), allow_nan=False)))
    finish_effective_result(context, restored)
    assert restored.metadata["effective_validation"]["status"] == "accepted"


@pytest.mark.parametrize("mode", ["det", "sto"])
@pytest.mark.parametrize("defect", ["missing_zero", "duplicate", "invalid_period"])
def test_incomplete_dense_vectors_are_rejected_instead_of_imputing_zero(mode, defect, monkeypatch):
    context, result = extracted_plan(mode, monkeypatch)
    if defect == "missing_zero":
        result.inventories.pop()
    elif defect == "duplicate":
        result.unmet_demand.append(dict(result.unmet_demand[0]))
    else:
        result.flows[0]["period"] = "unrecorded"
    assert dense_vector_coverage(context.data, context.config, result)["status"] == "rejected"
    finish_effective_result(context, result)
    assert result.metadata["effective_validation"]["status"] == "rejected"


def test_no_incumbent_has_no_fabricated_vectors_gap_or_validation():
    data, cfg = export_data()
    context = prepare_effective_native(data, cfg, reference_solver_config())
    result = finish_effective_result(context, OptimizationResult(status="time_limit"))
    assert result.objective_value is None and result.mip_gap is None and result.flows == []
    assert result.metadata["effective_validation"] == {"status": "no_usable_incumbent"}
