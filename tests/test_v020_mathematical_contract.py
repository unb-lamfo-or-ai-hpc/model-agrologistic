from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
import yaml

from src.logic.excel_loader import (
    ExcelLoaderConfig,
    _build_penalty_rates,
    load_model_data_from_excel,
)
from src.logic.experiment_runner import load_experiment_manifest
from src.logic.model_config import ModelConfig, SolverConfig
from src.logic.model_data import ModelData
from src.logic.optimization import (
    OptimizationBackendNotImplementedError,
    solve_model,
)
from src.logic.optimization_gurobipy import (
    _origin_to_warehouse_unit_cost,
    _warehouse_to_customer_unit_cost,
    _warehouse_to_warehouse_unit_cost,
)


def test_thesis_transport_cost_equations_use_the_correct_endpoint_rates():
    data = ModelData(
        origins=["O1"],
        warehouses=["W1", "W2"],
        existing_warehouses=["W1", "W2"],
        candidate_warehouses=[],
        bulk_eligible_warehouses=[],
        customers=["C1"],
        domestic_customers=["C1"],
        export_customers=[],
        products=["soy"],
        periods=["t1"],
        dist_od={("O1", "W1"): 10.0},
        dist_dc={("W1", "C1"): 500.0},
        dist_dd={("W1", "W2"): 30.0},
        freight_origin={"O1": 2.0},
        freight_dest={"C1": 99.0},
        freight_warehouse={"W1": 3.0, "W2": 4.0},
        transshipment_cost={"W1": 5.0, "W2": 7.0},
    )
    config = ModelConfig(interhub_factor=0.8)

    assert _origin_to_warehouse_unit_cost(data, "O1", "W1", "soy") == pytest.approx(
        25.0
    )
    assert _warehouse_to_customer_unit_cost(
        data, "W1", "C1", "soy"
    ) == pytest.approx(1500.0)
    assert _warehouse_to_warehouse_unit_cost(
        data, "W1", "W2", "soy", config
    ) == pytest.approx(79.0)


def test_thesis_dynamic_unmet_penalty_is_customer_indexed():
    unmet, emergency_static, emergency_reception = _build_penalty_rates(
        config=ExcelLoaderConfig(
            compute_haversine_distances=False,
            penalty_policy="thesis_dynamic",
        ),
        warehouses=["W1", "W2"],
        domestic_customers=["C1"],
        products=["soy", "corn"],
        routes_dc={
            ("W1", "C1", "soy"),
            ("W2", "C1", "corn"),
        },
        routes_oc={("O1", "C1", "soy")},
        dist_dc={
            ("W1", "C1"): 500.0,
            ("W2", "C1"): 1000.0,
        },
        dist_oc={("O1", "C1"): 25.0},
        freight_origin={"O1": 2.0},
        freight_warehouse={"W1": 3.0, "W2": 4.0},
        expand_variable_cost={"W1": 1050.0},
        storage_tariff={("W1", "soy"): 20.0},
    )

    assert emergency_static == {
        "W1": pytest.approx(52_500.0),
        "W2": pytest.approx(52_500.0),
    }
    assert emergency_reception == emergency_static
    assert unmet == {
        ("C1", "soy"): pytest.approx(400_000.0),
        ("C1", "corn"): pytest.approx(400_000.0),
    }


def test_fixed_penalties_remain_available_for_archived_v010_replay():
    unmet, emergency_static, emergency_reception = _build_penalty_rates(
        config=ExcelLoaderConfig(
            compute_haversine_distances=False,
            penalty_policy="fixed",
            default_unmet_demand_penalty=11.0,
            default_emergency_static_penalty=22.0,
            default_emergency_reception_penalty=33.0,
        ),
        warehouses=["W1"],
        domestic_customers=["C1"],
        products=["soy"],
        routes_dc=set(),
        routes_oc=set(),
        dist_dc={},
        dist_oc={},
        freight_origin={},
        freight_warehouse={},
        expand_variable_cost={},
        storage_tariff={},
    )

    assert unmet == {("C1", "soy"): 11.0}
    assert emergency_static == {"W1": 22.0}
    assert emergency_reception == {"W1": 33.0}


def test_complete_recourse_slacks_preserve_candidate_activation():
    root = Path(__file__).resolve().parents[1]
    deterministic = (root / "src/logic/optimization_gurobipy.py").read_text(
        encoding="utf-8"
    )
    stochastic = (
        root / "src/logic/optimization_gurobipy_stochastic.py"
    ).read_text(encoding="utf-8")

    for source in (deterministic, stochastic):
        assert "GRB.INFINITY" in source
        assert "emergency_static_only_if_active" in source
        assert "emergency_reception_only_if_active" in source
        assert "inventory_big_m =" not in source


def test_v020_experiment_profiles_separate_reproduction_and_extension():
    root = Path(__file__).resolve().parents[1]
    thesis = yaml.safe_load(
        (root / "experiments/v020_thesis_compatible.yaml").read_text(
            encoding="utf-8"
        )
    )
    policy = yaml.safe_load(
        (root / "experiments/v020_policy_mvp.yaml").read_text(encoding="utf-8")
    )
    time_study = yaml.safe_load(
        (root / "experiments/v020_policy_time_limit.yaml").read_text(
            encoding="utf-8"
        )
    )
    policy_manifest = load_experiment_manifest(
        root / "experiments/v020_policy_mvp.yaml"
    )
    stochastic_three = next(
        spec
        for spec in policy_manifest.experiments
        if spec.name == "policy_sto3_p20_warehouse"
    )
    stochastic_data = load_model_data_from_excel(
        stochastic_three.workbook,
        stochastic_three.loader,
    )
    assert len(stochastic_data.scenarios) == 3
    assert sum(stochastic_data.scenario_prob.values()) == pytest.approx(1.0)

    thesis_runs = thesis["experiments"]
    assert len(thesis_runs) == 12
    assert {run["model"]["mode"] for run in thesis_runs} == {"det", "sto"}
    assert {run["model"]["interhub_factor"] for run in thesis_runs} == {
        0.8,
        1.0,
        1.2,
    }
    assert {run["model"]["use_direct_origin_customer"] for run in thesis_runs} == {
        False,
        True,
    }
    assert thesis["defaults"]["model"]["route_filter_strategy"] == "thesis_pareto"
    assert thesis["defaults"]["model"]["pareto_fraction"] == pytest.approx(0.20)
    assert thesis["defaults"]["loader"]["penalty_policy"] == "thesis_dynamic"
    assert (
        thesis["defaults"]["loader"]["required_distance_source"]
        == "osrm_primary"
    )
    assert all(
        "/solver_v020_osrm/model_input.xlsx" in run["workbook"]
        for run in thesis_runs
    )
    assert all(
        run["metadata"]["distance_authority"]
        == "osrm_primary_with_audited_haversine_fallback"
        for run in thesis_runs
    )
    stochastic_runs = [
        run for run in thesis_runs if run["model"]["mode"] == "sto"
    ]
    assert all(
        run["loader"]["stochastic_probabilities"] == [0.33, 0.34, 0.33]
        for run in stochastic_runs
    )

    policy_runs = policy["experiments"]
    assert len(policy_runs) == 18
    assert {run["model"]["mode"] for run in policy_runs} == {"det", "sto"}
    assert sorted(
        {run["model"]["pareto_fraction"] for run in policy_runs}
    ) == pytest.approx([0.15, 0.20, 0.25])
    assert {
        run["model"]["use_direct_origin_customer"] for run in policy_runs
    } == {False, True}
    assert (
        policy["defaults"]["model"]["route_filter_strategy"]
        == "connectivity_preserving_pareto"
    )
    assert (
        policy["defaults"]["model"]["connectivity_export_policy"]
        == "one_sink_per_product"
    )
    assert all(
        run["metadata"]["route_policy"] == "grouped_nearest_edge_fraction"
        for run in policy_runs
    )
    assert all(
        "full_network" not in run["name"]
        and run["metadata"]["route_policy"] != "complete_network"
        for run in policy_runs
    )

    assert [
        run["solver"]["time_limit"] for run in time_study["experiments"]
    ] == [600, 3600, 14400]
    assert time_study["defaults"]["solver"]["mip_gap"] == pytest.approx(0.0)
    assert (
        time_study["defaults"]["model"]["route_filter_strategy"]
        == "connectivity_preserving_pareto"
    )
    assert (
        time_study["defaults"]["model"]["connectivity_export_policy"]
        == "one_sink_per_product"
    )


def test_scip_remains_an_explicit_solver_neutral_provision():
    config = SolverConfig(backend="pyscipopt", solver_name="scip")
    assert config.backend == "pyscipopt"
    assert config.solver_name == "scip"
    with pytest.raises(OptimizationBackendNotImplementedError):
        solve_model(
            data=ModelData(
                origins=[],
                warehouses=[],
                existing_warehouses=[],
                candidate_warehouses=[],
                bulk_eligible_warehouses=[],
                customers=[],
                domestic_customers=[],
                export_customers=[],
                products=[],
                periods=[],
            ),
            model_config=ModelConfig(),
            solver_config=config,
            validate=False,
        )

    pyproject = tomllib.loads(
        (
            Path(__file__).resolve().parents[1] / "pyproject.toml"
        ).read_text(encoding="utf-8")
    )
    assert pyproject["project"]["optional-dependencies"]["scip"] == [
        "pyscipopt>=6.2,<7"
    ]
