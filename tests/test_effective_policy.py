"""Optional policy rows and independent manual-vector checks, without optimization."""

import copy

import pyomo.environ as pyo
import pytest
from pyomo.repn import generate_standard_repn

from src.logic.effective_baseline import build_effective_model, effective_projection, identity, seal
from src.logic.effective_policy_validation import validate_effective_solution
from src.logic.parametric_scenarios import ParameterScenario, apply_scenario
from src.logic.pyomo_linear_matrix import matrix_identity
from src.logic.solution_validation import validate_solution
from tests.test_effective_baseline import baseline
from tests.test_solution_validation import analytical_solution


def scenario(data, cfg, **controls):
    return apply_scenario(
        data,
        cfg,
        ParameterScenario(
            "approved-policy",
            justification="Approved h215 policy; local software control only.",
            **controls,
        ),
    )[0]


@pytest.mark.parametrize("mode", ["det", "sto"])
def test_neutral_policy_keeps_exact_matrix(mode):
    data, cfg = baseline(mode)
    before = matrix_identity(build_effective_model(data, cfg).model)
    changed = scenario(data, cfg)
    assert matrix_identity(build_effective_model(changed, cfg).model) == before


@pytest.mark.parametrize("control", ["beta", "alpha"])
@pytest.mark.parametrize("invalid", [True, -0.01, 1.01, float("nan"), float("inf"), {}])
def test_invalid_policy_domains(control, invalid):
    with pytest.raises(ValueError):
        ParameterScenario("bad", justification="Invalid policy test.", **{control: invalid})


def test_beta_rows_are_per_scenario_not_expected_and_scale_demand_once():
    data, cfg = baseline("sto")
    changed = scenario(data, cfg, beta=0.9, multipliers={"delta_D": 2})
    built = build_effective_model(changed, cfg)
    assert len(built.model.effective_policy.service_floor) == 2
    for s in data.scenarios:
        row = built.model.effective_policy.service_floor[s, "P"]
        assert pyo.value(row.upper) == pytest.approx(2)
        repn = generate_standard_repn(row.body)
        assert all(coef == 1 for coef in repn.linear_coefs)
        assert all(var.index()[0] == s for var in repn.linear_vars)
    assert changed.unmet_demand_penalty == data.unmet_demand_penalty
    assert changed.demand_exp_s == data.demand_exp_s


def export_data(mode="det"):
    data, cfg = baseline(mode)
    data.customers.append("X")
    data.export_customers.append("X")
    data.routes_dc.add(("W", "X", "P"))
    data.dist_dc["W", "X"] = 4
    data.demand_exp["X", "P", "t"] = 10
    for s in data.scenarios:
        data.demand_exp_s[s, "X", "P", "t"] = 10
    # Recreate the frozen graph for this existing tiny fixture's extra destination.
    data.metadata.pop("_frozen_routes", None)
    data.metadata.pop("mathematical_contract", None)
    data.metadata.pop("effective_baseline", None)
    data = effective_projection(data, cfg)
    return seal(data, cfg, {"scenario_id": "baseline"}), cfg


def test_alpha_counts_only_export_deliveries_once_and_preserves_original_bounds():
    data, cfg = export_data("sto")
    original = build_effective_model(data, cfg)
    changed = scenario(data, cfg, alpha=0.5)
    built = build_effective_model(changed, cfg)
    for s in data.scenarios:
        row = built.model.effective_policy.export_ceiling[s, "P"]
        assert pyo.value(row.upper) == 5
        repn = generate_standard_repn(row.body)
        assert repn.linear_coefs == (1,)
        assert [v.index() for v in repn.linear_vars] == [(s, "W", "X", "P", "t")]
    assert len(built.model.rows) == len(original.model.rows)
    assert str(built.model.objective.expr) == str(original.model.objective.expr)
    assert changed.demand_exp_s == data.demand_exp_s


def test_indexed_policy_coverage_and_metadata_tampering():
    data, cfg = baseline("sto")
    with pytest.raises(ValueError, match="cover every product/scenario"):
        scenario(data, cfg, beta={"P": {"low": 0.9}})
    indexed = {"P": {"low": 0.9, "high": 0.95}}
    changed = scenario(data, cfg, beta=indexed)
    built = build_effective_model(changed, cfg)
    assert pyo.value(
        built.model.effective_policy.service_floor["high", "P"].upper
    ) == pytest.approx(0.5)
    changed.metadata["effective_baseline"]["specification"]["beta"]["P"]["low"] = 0.1
    with pytest.raises(ValueError, match="changed after sealing"):
        build_effective_model(changed, cfg)
    with pytest.raises(ValueError, match="named baseline"):
        ParameterScenario("baseline", beta=0, justification="Must have a new identity.")


def test_policy_identity_differs_even_when_numeric_data_are_the_same():
    data, cfg = baseline()
    low, high = scenario(data, cfg, beta=0.9), scenario(data, cfg, beta=0.95)
    assert identity(low, cfg) == identity(high, cfg)
    assert (
        low.metadata["effective_baseline"]["scenario_sha256"]
        != high.metadata["effective_baseline"]["scenario_sha256"]
    )


def analytical_effective():
    data, cfg, result = analytical_solution()
    data = seal(effective_projection(data, cfg), cfg, {"scenario_id": "baseline"})
    return data, cfg, result


def test_independent_validator_keeps_neutral_certificate_and_rejects_service_violation():
    data, cfg, result = analytical_effective()
    assert validate_effective_solution(data, cfg, result) == validate_solution(data, cfg, result)
    policy = scenario(data, cfg, beta=0.95)
    accepted = validate_effective_solution(policy, cfg, result)
    assert accepted["status"] == "accepted"
    # A physically valid plan with 10% shortage and matching economic accounting.
    altered = copy.deepcopy(result)
    altered.flows[1]["value"] = 2727
    altered.inventories = [{"warehouse": "W", "product": "P", "period": "t", "value": 303}]
    altered.unmet_demand = [{"customer": "C", "product": "P", "period": "t", "value": 303}]
    altered.emergency_capacity.append(
        {"warehouse": "W", "period": "t", "capacity_type": "static", "value": 303}
    )
    altered.cost_breakdown["transport_dc"] = 2727
    altered.cost_breakdown["storage"] = 303 * data.storage_tariff.get(("W", "P"), 0)
    altered.cost_breakdown["emergency_static"] = 303 * data.emergency_static_capacity_penalty["W"]
    altered.cost_breakdown["unmet_demand"] = 303 * data.unmet_demand_penalty["C", "P"]
    altered.objective_value = sum(altered.cost_breakdown.values())
    assert validate_solution(policy, cfg, altered)["status"] == "accepted"
    rejected = validate_effective_solution(policy, cfg, altered)
    assert rejected["status"] == "rejected"
    assert rejected["effective_policy_validation"]["rows"][0]["status"] == "violated"


def test_sparse_precision_does_not_falsely_certify_exact_full_service():
    data, cfg, result = analytical_effective()
    policy = scenario(data, cfg, beta=1)
    report = validate_effective_solution(policy, cfg, result, absolute_tolerance=1e-9)
    assert (
        report["effective_policy_validation"]["rows"][0]["status"]
        == "indeterminate_sparse_precision"
    )
    result.unmet_demand = [{"customer": "C", "product": "P", "period": "t", "value": 0}]
    assert (
        validate_effective_solution(policy, cfg, result, absolute_tolerance=1e-9)["status"]
        == "accepted"
    )


def test_zero_demand_supply_and_no_export_arcs_construct_without_new_variables():
    data, cfg = baseline()
    data.supply["O", "P", "t"] = data.demand_dom["C", "P", "t"] = 0
    data = seal(data, cfg, {"scenario_id": "baseline"})
    before = matrix_identity(build_effective_model(data, cfg).model)
    built = build_effective_model(scenario(data, cfg, beta=1, alpha=0), cfg)
    after = matrix_identity(built.model)
    assert before["variables"] == after["variables"]
    assert after["linear_constraints"] == before["linear_constraints"] + 2


def exported_solution():
    from src.logic.optimization import OptimizationResult
    from src.logic.solution_validation import COST_NAMES

    costs = dict.fromkeys(COST_NAMES, 0.0)
    costs.update(transport_od=90, transport_dc=66, unmet_demand=3000)
    return OptimizationResult(
        status="feasible",
        objective_value=3156,
        cost_breakdown=costs,
        warehouse_decisions=[
            {
                "warehouse": "W",
                "open": 1,
                "candidate_capacity": 0,
                "expand": 0,
                "expansion_capacity": 0,
                "bulkify": 0,
                "bulk_capacity": 0,
            }
        ],
        flows=[
            {
                "route_type": "OD",
                "origin": "O",
                "warehouse": "W",
                "product": "P",
                "period": "t",
                "value": 10,
            },
            {
                "route_type": "DC",
                "warehouse": "W",
                "customer": "C",
                "product": "P",
                "period": "t",
                "value": 7,
            },
            {
                "route_type": "DC",
                "warehouse": "W",
                "customer": "X",
                "product": "P",
                "period": "t",
                "value": 3,
            },
        ],
        unmet_demand=[{"customer": "C", "product": "P", "period": "t", "value": 3}],
    )


def test_independent_export_ceiling_rejects_only_the_policy_violation():
    data, cfg = export_data()
    result = exported_solution()
    assert validate_solution(data, cfg, result)["status"] == "accepted"
    strict = scenario(data, cfg, beta=0.6, alpha=0.2)
    report = validate_effective_solution(strict, cfg, result)
    assert report["base_validation_status"] == "accepted" and report["status"] == "rejected"
    rows = {r["control"]: r for r in report["effective_policy_validation"]["rows"]}
    assert rows["beta"]["status"] == "accepted"
    assert rows["alpha"]["lhs_t"] == 3 and rows["alpha"]["rhs_t"] == 2
    assert rows["alpha"]["status"] == "violated"
    assert (
        validate_effective_solution(scenario(data, cfg, beta=0.6, alpha=0.4), cfg, result)["status"]
        == "accepted"
    )


def test_readback_uses_destination_roles_and_counts_exports_once(tmp_path):
    import csv

    from scripts.summarize_effective_policy_reference import summarize

    data, _ = export_data()
    result = exported_solution()
    for name in ("flows", "unmet_demand", "inventories"):
        rows = getattr(result, name)
        columns = tuple(dict.fromkeys(key for row in rows for key in row)) or ("value",)
        with (tmp_path / f"{name}.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
    row = summarize(data, "det", tmp_path)[0]
    assert row["service_fraction"] == 0.7
    assert row["export_supply_fraction"] == 0.3
    assert row["national_balance_residual_t"] == 0


def test_independent_stochastic_policy_never_weights_constraint_tonnes():
    data, cfg = export_data("sto")
    result = exported_solution()
    for name in ("flows", "unmet_demand"):
        original = getattr(result, name)
        setattr(result, name, [{**row, "scenario": s} for s in data.scenarios for row in original])
    assert validate_solution(data, cfg, result)["status"] == "accepted"
    changed = scenario(data, cfg, alpha={"P": {"low": 0.2, "high": 0.4}})
    report = validate_effective_solution(changed, cfg, result)
    rows = {row["scenario"]: row for row in report["effective_policy_validation"]["rows"]}
    assert rows["low"]["lhs_t"] == 3 and rows["low"]["status"] == "violated"
    assert rows["high"]["lhs_t"] == 3 and rows["high"]["status"] == "accepted"
