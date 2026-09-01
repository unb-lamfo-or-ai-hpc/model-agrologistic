"""EVPI and VSS analysis for the native gurobipy stochastic model."""

from __future__ import annotations

from dataclasses import replace

from src.logic.model_config import ModelConfig, SolverConfig
from src.logic.model_data import ModelData
from src.logic.optimization import EVPIVSSResult, OptimizationResult
from src.logic.optimization_gurobipy import _solve_deterministic_core
from src.logic.optimization_gurobipy_stochastic import (
    solve_stochastic_model_gurobipy,
)


def calculate_evpi_vss_gurobipy(
    data: ModelData,
    model_config: ModelConfig,
    solver_config: SolverConfig,
) -> EVPIVSSResult:
    """Calculate RP, WS, EV, EEV, EVPI, and VSS for a minimization model."""

    recourse_result = solve_stochastic_model_gurobipy(
        data=data,
        model_config=model_config,
        solver_config=solver_config,
    )
    recourse_problem = _require_objective(recourse_result, "recourse problem")

    deterministic_config = replace(model_config, mode="det")
    expected_data = _expected_value_data(data)
    expected_value_result = _solve_deterministic_core(
        data=expected_data,
        model_config=deterministic_config,
        solver_config=solver_config,
    )
    expected_value_problem = _require_objective(
        expected_value_result,
        "expected-value problem",
    )

    expected_result = solve_stochastic_model_gurobipy(
        data=data,
        model_config=model_config,
        solver_config=solver_config,
        fixed_first_stage=expected_value_result.warehouse_decisions,
    )
    expected_result_of_ev_solution = _require_objective(
        expected_result,
        "expected result of the expected-value solution",
    )

    wait_and_see_results: dict[str, OptimizationResult] = {}
    wait_and_see = 0.0
    for scenario in data.scenarios:
        scenario_result = _solve_deterministic_core(
            data=_single_scenario_data(data, scenario),
            model_config=deterministic_config,
            solver_config=solver_config,
        )
        scenario_objective = _require_objective(
            scenario_result,
            f"wait-and-see scenario {scenario!r}",
        )
        wait_and_see_results[scenario] = scenario_result
        wait_and_see += data.scenario_prob[scenario] * scenario_objective

    raw_evpi = recourse_problem - wait_and_see
    raw_vss = expected_result_of_ev_solution - recourse_problem
    tolerance = model_config.evpi_vss_tolerance
    evpi = _zero_within_tolerance(raw_evpi, tolerance)
    vss = _zero_within_tolerance(raw_vss, tolerance)

    consistency_warnings: list[str] = []
    if evpi < -tolerance:
        consistency_warnings.append(
            "EVPI is negative beyond the configured tolerance. Check solver "
            "optimality gaps and numerical settings."
        )
    if vss < -tolerance:
        consistency_warnings.append(
            "VSS is negative beyond the configured tolerance. Check solver "
            "optimality gaps and numerical settings."
        )

    return EVPIVSSResult(
        recourse_problem=recourse_problem,
        wait_and_see=wait_and_see,
        expected_value_problem=expected_value_problem,
        expected_result_of_ev_solution=expected_result_of_ev_solution,
        evpi=evpi,
        vss=vss,
        recourse_problem_result=recourse_result,
        wait_and_see_results=wait_and_see_results,
        expected_value_problem_result=expected_value_result,
        expected_result_result=expected_result,
        metadata={
            "formulation": "risk_neutral_two_stage",
            "sense": "minimize",
            "evpi_formula": "RP - WS",
            "vss_formula": "EEV - RP",
            "scenario_probabilities": dict(data.scenario_prob),
            "evpi_vss_tolerance": tolerance,
            "raw_evpi": raw_evpi,
            "raw_vss": raw_vss,
            "consistency_warnings": consistency_warnings,
        },
    )


def _expected_value_data(data: ModelData) -> ModelData:
    supply = {
        (origin, product, period): sum(
            data.scenario_prob[scenario]
            * data.supply_s[scenario, origin, product, period]
            for scenario in data.scenarios
        )
        for origin in data.origins
        for product in data.products
        for period in data.periods
    }
    demand_dom = {
        (customer, product, period): sum(
            data.scenario_prob[scenario]
            * data.demand_dom_s[scenario, customer, product, period]
            for scenario in data.scenarios
        )
        for customer in data.domestic_customers
        for product in data.products
        for period in data.periods
    }
    demand_exp = {
        (customer, product, period): sum(
            data.scenario_prob[scenario]
            * data.demand_exp_s[scenario, customer, product, period]
            for scenario in data.scenarios
        )
        for customer in data.export_customers
        for product in data.products
        for period in data.periods
    }
    return _as_deterministic_data(
        data,
        supply=supply,
        demand_dom=demand_dom,
        demand_exp=demand_exp,
        source="expected_value",
    )


def _single_scenario_data(data: ModelData, scenario: str) -> ModelData:
    supply = {
        (origin, product, period): data.supply_s[
            scenario,
            origin,
            product,
            period,
        ]
        for origin in data.origins
        for product in data.products
        for period in data.periods
    }
    demand_dom = {
        (customer, product, period): data.demand_dom_s[
            scenario,
            customer,
            product,
            period,
        ]
        for customer in data.domestic_customers
        for product in data.products
        for period in data.periods
    }
    demand_exp = {
        (customer, product, period): data.demand_exp_s[
            scenario,
            customer,
            product,
            period,
        ]
        for customer in data.export_customers
        for product in data.products
        for period in data.periods
    }
    return _as_deterministic_data(
        data,
        supply=supply,
        demand_dom=demand_dom,
        demand_exp=demand_exp,
        source=f"wait_and_see:{scenario}",
    )


def _as_deterministic_data(
    data: ModelData,
    *,
    supply: dict[tuple[str, str, str], float],
    demand_dom: dict[tuple[str, str, str], float],
    demand_exp: dict[tuple[str, str, str], float],
    source: str,
) -> ModelData:
    return replace(
        data,
        supply=supply,
        demand_dom=demand_dom,
        demand_exp=demand_exp,
        scenarios=[],
        scenario_prob={},
        supply_s={},
        demand_dom_s={},
        demand_exp_s={},
        metadata={**data.metadata, "deterministic_projection": source},
    )


def _require_objective(result: OptimizationResult, label: str) -> float:
    if not result.has_solution or result.objective_value is None:
        raise RuntimeError(
            f"Cannot calculate EVPI/VSS because the {label} did not return "
            f"a usable solution (status={result.status!r})."
        )
    return float(result.objective_value)


def _zero_within_tolerance(value: float, tolerance: float) -> float:
    return 0.0 if abs(value) <= tolerance else value
