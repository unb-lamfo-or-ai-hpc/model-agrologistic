"""Native, license-free analytical checks; no large-network admission is implied."""

from copy import deepcopy
from dataclasses import replace

import pytest

from src.logic.mathematical_contract import prepare_model_data
from src.logic.model_config import ModelConfig, SolverConfig
from src.logic.optimization import solve_model
from src.logic.solution_validation import validate_solution
from tests.test_gurobipy_stochastic import two_scenario_data
from tests.test_gurobipy_transshipment import base_transshipment_data, require_gurobi_available

pytest.importorskip("pyscipopt")


def configuration(**kwargs):
    return ModelConfig(mode="sto", days_per_period=1, allow_bulkification=False, **kwargs)


def solver(**kwargs):
    return SolverConfig(
        backend="pyscipopt", solver_name="scip", time_limit=60, mip_gap=0, threads=1, **kwargs
    )


def checked(data, config):
    result = solve_model(data, config, solver())
    report = validate_solution(prepare_model_data(data, config), config, result)
    assert report["status"] == "accepted", report["failure_samples"]
    return result


@pytest.mark.parametrize("policy", ["penalty", "lexicographic"])
def test_shared_investment_and_probability_weighted_costs(policy):
    result = checked(two_scenario_data(), configuration(objective_policy=policy))
    assert result.status == "optimal"
    assert result.solver_backend == "pyscipopt"
    assert result.metrics["investment_cost"] == pytest.approx(130, abs=1e-4)
    assert result.metrics["expected_operating_cost"] == pytest.approx(170, abs=2)
    assert result.metrics["objective_values"]["economic_cost"] == pytest.approx(300, abs=1e-4)
    assert result.warehouse_decisions[0]["expansion_capacity"] == pytest.approx(60, abs=1e-4)
    assert not any(key.startswith("gurobi_") for key in result.metadata)
    if policy == "lexicographic":
        assert result.metadata["lexicographic_overall_status"] == "complete"
        assert len(result.metadata["lexicographic_stages"]) == 3
        assert result.mip_gap is None
        assert result.metadata["service_certification_status"] == "certified_zero_within_tolerance"
    else:
        assert result.objective_value == pytest.approx(300)
        assert result.metadata["objective_bound"] == pytest.approx(300)


def stochastic(data):
    data.scenarios = ["low", "high"]
    data.scenario_prob = {"low": 0.25, "high": 0.75}
    for target, source in (
        ("supply_s", "supply"),
        ("demand_dom_s", "demand_dom"),
        ("demand_exp_s", "demand_exp"),
    ):
        setattr(
            data,
            target,
            {
                (s, *key): amount
                for s in data.scenarios
                for key, amount in getattr(data, source).items()
            },
        )
    return data


@pytest.mark.parametrize("direct", [False, True])
def test_transshipment_and_direct_route_selection(direct):
    data = stochastic(
        base_transshipment_data(
            routes_dc={("W2", "C1", "soy")},
            routes_dd={("W1", "W2", "soy")},
            dist_dc={("W2", "C1"): 1},
            dist_dd={("W1", "W2"): 1},
        )
    )
    data.routes_oc = {("O1", "C1", "soy")}
    data.dist_oc = {("O1", "C1"): 0.1}
    result = checked(
        data, configuration(use_direct_origin_customer=direct, objective_policy="lexicographic")
    )
    kinds = {r["route_type"] for r in result.flows}
    assert ("OC" in kinds) == direct
    assert ("DD" in kinds) != direct


@pytest.mark.parametrize("capacity_mode", ["scalable", "fixed"])
def test_candidate_activation_with_native_indicators(capacity_mode):
    data = two_scenario_data()
    data.existing_warehouses = []
    data.candidate_warehouses = ["W1"]
    data.static_capacity = {"W1": 0}
    data.reception_capacity = {"W1": 0}
    data.shipping_capacity = {"W1": 0}
    data.max_candidate_capacity = {"W1": 100}
    data.opening_fixed_cost = {"W1": 10}
    data.candidate_capacity_cost = {"W1": 2}
    result = checked(
        data, configuration(candidate_capacity_mode=capacity_mode, allow_capacity_expansion=False)
    )
    assert result.warehouse_decisions[0]["open"] == pytest.approx(1)


def test_closed_candidate_has_no_emergency_capacity():
    data = two_scenario_data()
    data.existing_warehouses = []
    data.candidate_warehouses = ["W1"]
    data.static_capacity = {"W1": 0}
    data.reception_capacity = {"W1": 0}
    data.shipping_capacity = {"W1": 0}
    data.max_candidate_capacity = {"W1": 100}
    data.opening_fixed_cost = {"W1": 1000}
    data.candidate_capacity_cost = {"W1": 2}
    data.routes_oc = {("O1", "C1", "soy")}
    data.dist_oc = {("O1", "C1"): 1}
    data.demand_dom_s = {
        (s, "C1", "soy", "t1"): amount for (s, o, p, t), amount in data.supply_s.items()
    }
    result = checked(
        data, configuration(use_direct_origin_customer=True, allow_capacity_expansion=False)
    )
    assert result.warehouse_decisions[0]["open"] == 0
    assert not result.emergency_capacity


@pytest.mark.parametrize("days", [28, 30, 31])
def test_reception_slack_is_period_overflow_not_daily_capacity(days):
    from tests.test_mathematical_contract import tiny_data

    data = stochastic(tiny_data())
    config = ModelConfig(mode="sto", days_per_period=days)
    result = checked(data, config)
    expected = max(0, 3030 - 100 * days)
    per_scenario = {
        s: sum(
            r["value"]
            for r in result.emergency_capacity
            if r["scenario"] == s and r["capacity_type"] == "reception"
        )
        for s in data.scenarios
    }
    assert per_scenario == pytest.approx(dict.fromkeys(data.scenarios, expected))


def test_two_period_stock_and_export_upper_bound():
    data = two_scenario_data()
    data.periods = ["t1", "t2"]
    data.export_customers = ["E"]
    data.customers.append("E")
    data.routes_dc.add(("W1", "E", "soy"))
    data.dist_dc["W1", "E"] = 1
    for s in data.scenarios:
        data.supply_s[s, "O1", "soy", "t2"] = 0
        data.demand_dom_s[s, "C1", "soy", "t2"] = 20
        for t in data.periods:
            data.demand_exp_s[s, "E", "soy", t] = 5
    result = checked(data, configuration())
    assert any(r["period"] == "t2" for r in result.inventories)
    for s in data.scenarios:
        for t in data.periods:
            assert (
                sum(
                    r["value"]
                    for r in result.flows
                    if r.get("customer") == "E" and r["scenario"] == s and r["period"] == t
                )
                <= 5 + 1e-6
            )


def test_no_incumbent_is_not_reported_as_usable():
    data = two_scenario_data()
    config = configuration(allow_capacity_expansion=False, allow_emergency_static_capacity=False)
    result = solve_model(data, config, solver())
    assert result.status == "infeasible"
    assert not result.has_solution
    assert result.objective_value is None


@pytest.mark.parametrize("options", [{"Method": 2}, {"limits/time": 120}, {"limits/gap": 0.9}])
def test_unsupported_or_contract_overriding_parameters_are_rejected(options):
    with pytest.raises(ValueError, match="Unsupported SCIP"):
        solve_model(two_scenario_data(), configuration(), solver(solver_options=options))


def test_iis_is_not_silently_ignored():
    with pytest.raises(ValueError, match="IIS"):
        solve_model(two_scenario_data(), configuration(), solver(compute_iis=True))


def test_nine_scenarios_preserve_the_shared_first_stage():
    data = two_scenario_data()
    data.scenarios = [f"s{i}" for i in range(9)]
    data.scenario_prob = dict.fromkeys(data.scenarios, 1 / 9)
    data.supply_s = {(s, "O1", "soy", "t1"): 40 + i * 5 for i, s in enumerate(data.scenarios)}
    data.demand_dom_s = {(s, "C1", "soy", "t1"): 0 for s in data.scenarios}
    result = checked(data, configuration(objective_policy="lexicographic"))
    assert len(result.warehouse_decisions) == 1
    assert len(result.metrics["scenario_metrics"]) == 9
    assert result.warehouse_decisions[0]["expansion_capacity"] == pytest.approx(40, abs=1e-4)
    assert result.metadata["lexicographic_overall_status"] == "complete"


def test_bulkification_enables_daily_reception_without_creating_static_capacity():
    data = stochastic(base_transshipment_data(w1_reception=0))
    data.bulk_eligible_warehouses = ["W1"]
    data.max_bulk_capacity = {"W1": 100}
    data.bulk_fixed_cost = {"W1": 10}
    data.bulk_variable_cost = {"W1": 2}
    config = ModelConfig(
        mode="sto",
        days_per_period=1,
        objective_policy="lexicographic",
        allow_capacity_expansion=False,
        allow_bulkification=True,
    )
    result = checked(data, config)
    row = next(r for r in result.warehouse_decisions if r["warehouse"] == "W1")
    assert row["bulkify"] == pytest.approx(1)
    assert row["bulk_capacity"] == pytest.approx(100, abs=1e-4)
    assert row["effective_static_capacity"] == data.static_capacity["W1"]


def test_native_result_passes_pipeline_exports_and_receipt(tmp_path):
    import json

    from src.logic.experiment_runner import run_experiment
    from src.logic.run_integrity import verify_completion
    from tests.test_experiment_runner import experiment

    spec = replace(
        experiment("scip_analytical"),
        loader=replace(experiment().loader, include_stochastic_scenarios=True),
        model=configuration(objective_policy="lexicographic"),
        solver=solver(),
    )
    summary = run_experiment(
        spec, tmp_path, loader=lambda *_: two_scenario_data(), progress=lambda _: None
    )
    run_dir = tmp_path / spec.name
    assert summary.status == "optimal"
    independent = json.loads((run_dir / "independent_validation.json").read_text())
    assert independent["status"] == "accepted"
    result = json.loads((run_dir / "result.json").read_text())["result"]
    assert result["solver_backend"] == "pyscipopt"
    stages = result["metadata"]["lexicographic_stages"]
    assert all(r["within_mip_degradation_limit"] for r in stages)
    assert stages[0]["enforced_next_pass_limit"] == pytest.approx(stages[0]["mip_next_pass_limit"])
    assert (run_dir / "lexicographic_stages.csv").is_file()
    assert verify_completion(run_dir, result["metadata"]["run_identity"]) == (
        True,
        "current_complete_run",
    )


@pytest.mark.parametrize("policy", ["penalty", "lexicographic"])
def test_licensed_gurobi_parity_on_analytical_instance(policy):
    require_gurobi_available()
    data = two_scenario_data()
    config = configuration(objective_policy=policy)
    native = checked(data, config)
    gurobi = solve_model(
        deepcopy(data), config, replace(solver(), backend="gurobipy", solver_name="gurobi")
    )
    report = validate_solution(prepare_model_data(data, config), config, gurobi)
    assert report["status"] == "accepted", report["failure_samples"]
    if policy == "penalty":
        assert native.cost_breakdown == pytest.approx(gurobi.cost_breakdown)
        assert native.objective_value == pytest.approx(gurobi.objective_value)
    else:
        # Alternative optima may use different micro-slacks under the explicit
        # priority allowance; compare physical objectives, not artificial penalties.
        for name in ("expected_unmet_demand", "expected_emergency_capacity", "economic_cost"):
            assert native.metrics["objective_values"][name] == pytest.approx(
                gurobi.metrics["objective_values"][name], abs=1e-4
            )
        assert gurobi.metadata["lexicographic_overall_status"] == "complete"
