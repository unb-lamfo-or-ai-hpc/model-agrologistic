from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from src.logic.scientific_results import (
    ScientificResultsError,
    _flow_distance,
    _normalize_exported_loader_values,
    build_scientific_results_presentation,
)


def test_reader_facing_package_preserves_experimental_meaning(tmp_path: Path) -> None:
    policy_root = tmp_path / "policy"
    baseline_root = tmp_path / "baseline"
    stochastic_root = tmp_path / "stochastic"
    for strategy, parameter in (("pareto", 0.05), ("top_k", 10)):
        for direct in (False, True):
            suffix = "direct" if direct else "warehouse"
            _write_run(
                policy_root / f"{strategy}_{suffix}",
                name=f"{strategy}_{suffix}",
                mode="det",
                strategy=strategy,
                parameter=parameter,
                direct=direct,
                inventory_shift=5.0 if direct else 0.0,
            )
    _write_run(
        baseline_root / "bounded_det",
        name="bounded_det",
        mode="det",
        strategy="none",
        parameter=None,
        direct=False,
    )
    _write_run(
        stochastic_root / "bounded_sto_3_evpi_vss",
        name="bounded_sto_3_evpi_vss",
        mode="sto",
        strategy="none",
        parameter=None,
        direct=False,
        scenario_count=3,
    )

    distances = SimpleNamespace(
        dist_od={("O1", "W1"): 10.0},
        dist_dc={("W1", "C1"): 20.0},
        dist_dd={("W1", "W2"): 5.0},
        dist_oc={("O1", "C1"): 25.0},
    )
    output = tmp_path / "presentation"
    paths = build_scientific_results_presentation(
        deterministic_policy_dir=policy_root,
        deterministic_baseline_dir=baseline_root,
        stochastic_extension_dir=stochastic_root,
        output_dir=output,
        dpi=72,
        data_loader=lambda run: distances,
    )

    manifest = json.loads(paths["manifest_json"].read_text(encoding="utf-8"))
    assert len(manifest["figures"]) == 10
    assert "not equivalent" in manifest["scientific_scope"]["network_policy"]
    assert all(path.is_file() and path.stat().st_size > 0 for path in paths.values())

    deterministic = pd.read_csv(paths["deterministic_configuration_summary_csv"])
    assert set(deterministic["route_filter"]) == {"pareto", "top_k"}
    assert set(deterministic["direct_arcs"]) == {False, True}
    assert not deterministic["configuration"].str.contains("alpha", case=False).any()

    stochastic = pd.read_csv(paths["stochastic_configuration_summary_csv"])
    assert set(stochastic["row_scope"]) == {
        "scenario",
        "probability_weighted_expected",
    }
    assert "Probability-weighted expected" in set(stochastic["scenario"])

    robustness = pd.read_csv(paths["objective_robustness_csv"])
    row = robustness.loc[
        robustness["design"] == "3-scenario stochastic design"
    ].iloc[0]
    assert row["expected"] == 520.0
    assert row["minimum"] == 420.0
    assert row["maximum"] == 620.0

    transport = pd.read_csv(paths["deterministic_transport_work_csv"])
    assert "typed_customer_alias" in set(transport["distance_resolution"])


def test_typed_customer_alias_rejects_ambiguous_distances() -> None:
    distances = SimpleNamespace(
        dist_dc={
            ("W1", "C1"): 10.0,
            ("W1", "C1 | EXPORTACAO"): 20.0,
        }
    )
    flow = {
        "warehouse": "W1",
        "customer": "C1 | DOMESTICA",
    }

    with pytest.raises(ScientificResultsError, match="unambiguous DC distance"):
        _flow_distance(distances, flow, "DC")


def test_exported_stochastic_loader_sequences_are_restored_as_tuples() -> None:
    exported = json.loads(
        json.dumps(
            {
                "stochastic_supply_levels": ["baixo", "base", "alto"],
                "stochastic_demand_levels": ["baixo", "base", "alto"],
                "stochastic_combinations": [
                    ["baixo", "alto"],
                    ["base", "base"],
                    ["alto", "baixo"],
                ],
                "stochastic_probabilities": [1 / 3, 1 / 3, 1 / 3],
            }
        )
    )

    restored = _normalize_exported_loader_values(exported)

    assert restored["stochastic_supply_levels"] == ("baixo", "base", "alto")
    assert restored["stochastic_demand_levels"] == ("baixo", "base", "alto")
    assert restored["stochastic_combinations"] == (
        ("baixo", "alto"),
        ("base", "base"),
        ("alto", "baixo"),
    )
    assert len(set(restored["stochastic_combinations"])) == 3
    assert restored["stochastic_probabilities"] == pytest.approx(
        (1 / 3, 1 / 3, 1 / 3)
    )


def _write_run(
    run_dir: Path,
    *,
    name: str,
    mode: str,
    strategy: str,
    parameter: float | int | None,
    direct: bool,
    scenario_count: int = 1,
    inventory_shift: float = 0.0,
) -> None:
    run_dir.mkdir(parents=True)
    model = {
        "mode": mode,
        "route_filter_strategy": strategy,
        "use_direct_origin_customer": direct,
    }
    if strategy == "pareto":
        model["pareto_fraction"] = parameter
    if strategy == "top_k":
        model["route_top_k"] = parameter

    scenarios = (
        ["oferta_baixo__demanda_alto", "oferta_alto__demanda_baixo"]
        if mode == "sto"
        else [None]
    )
    flows = []
    inventories = []
    warehouse_metrics = []
    scenario_metrics = {}
    performance = []
    for index, scenario in enumerate(scenarios):
        scenario_fields = {} if scenario is None else {"scenario": scenario}
        flows.extend(
            [
                {
                    **scenario_fields,
                    "route_type": "OD",
                    "origin": "O1",
                    "warehouse": "W1",
                    "product": "Soy",
                    "period": "2025-01",
                    "value": 10.0,
                },
                {
                    **scenario_fields,
                    "route_type": "DC",
                    "warehouse": "W1",
                    "customer": "C1 | DOMESTICA",
                    "customer_type": "domestic",
                    "product": "Soy",
                    "period": "2025-01",
                    "value": 8.0,
                },
            ]
        )
        if direct:
            flows.append(
                {
                    **scenario_fields,
                    "route_type": "OC",
                    "origin": "O1",
                    "customer": "C1 | DOMESTICA",
                    "customer_type": "domestic",
                    "product": "Soy",
                    "period": "2025-01",
                    "value": 2.0,
                }
            )
        inventories.extend(
            {
                **scenario_fields,
                "warehouse": "W1",
                "product": "Soy",
                "period": period,
                "value": value + inventory_shift + index,
            }
            for period, value in (("2025-01", 4.0), ("2025-02", 6.0))
        )
        warehouse_metrics.append(
            {
                **scenario_fields,
                "warehouse": "W1",
                "dynamic_capacity": 100.0 + index,
                "turnover": 2.0 + index,
                "total_outbound": 8.0,
                "terminal_inventory": 6.0,
                "effective_static_capacity": 50.0,
            }
        )
        if scenario is not None:
            scenario_metrics[scenario] = {
                "probability": 0.5,
                "operating_cost": 400.0 + 200.0 * index,
            }
            performance.append(
                {
                    "scenario": scenario,
                    "probability": 0.5,
                    "domestic_service_level": 1.0,
                    "dynamic_capacity": 100.0 + index,
                    "turnover": 2.0 + index,
                    "emergency_static_capacity": 0.0,
                    "emergency_reception_capacity": 0.0,
                }
            )

    costs = {
        "opening": 20.0,
        "candidate_capacity": 0.0,
        "expansion_fixed": 0.0,
        "expansion_variable": 0.0,
        "bulkification_fixed": 0.0,
        "bulkification_variable": 0.0,
        "transport_od": 100.0,
        "transport_dc": 50.0,
        "transport_oc": 10.0 if direct else 0.0,
        "transport_dd": 5.0,
        "storage": 25.0,
        "unmet_demand": 0.0,
        "emergency_static": 0.0,
        "emergency_reception": 0.0,
    }
    economic_cost = sum(costs.values())
    result = {
        "status": "optimal",
        "model_mode": mode,
        "cost_breakdown": costs,
        "warehouse_decisions": [
            {
                "warehouse": "W1",
                "open": 1.0,
                "candidate_capacity": 1000.0,
                "expand": 0.0,
                "expansion_capacity": 0.0,
                "bulkify": 0.0,
                "bulk_capacity": 0.0,
            }
        ],
        "flows": flows,
        "inventories": inventories,
        "metrics": {
            "objective_values": {
                "economic_cost": economic_cost,
                "penalized_cost": economic_cost,
                "investment_cost": 20.0,
            },
            "scenario_metrics": scenario_metrics,
            "storage": {"warehouse_metrics": warehouse_metrics},
        },
        "metadata": {
            "scenario_probabilities": {
                scenario: 0.5 for scenario in scenarios if scenario is not None
            }
        },
    }
    stochastic = None
    if mode == "sto":
        stochastic = {
            "recourse_problem": 520.0,
            "wait_and_see": 500.0,
            "expected_value_problem": 490.0,
            "expected_result_of_ev_solution": 550.0,
            "evpi": 20.0,
            "vss": 30.0,
            "decomposition": {
                "vss_by_group": {
                    "investment": -5.0,
                    "operation": 10.0,
                    "penalty": 25.0,
                }
            },
        }
    payload = {
        "schema_version": 1,
        "experiment": {
            "name": name,
            "workbook": str(run_dir / "input.xlsx"),
            "workbook_sha256": "synthetic-workbook",
            "model": model,
            "loader": {},
        },
        "result": result,
        "stochastic_performance": stochastic,
    }
    (run_dir / "result.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    (run_dir / "run_summary.json").write_text(
        json.dumps(
            {
                "scenario_count": scenario_count,
                "domestic_service_level": 1.0,
                "minimum_scenario_service_level": 1.0,
                "dyn_cap": 100.0,
                "turnover": 2.0,
                "total_emergency_capacity": 0.0,
                "emergency_static_capacity": 0.0,
                "emergency_reception_capacity": 0.0,
                "runtime_seconds": 1.0,
                "peak_rss_mb": 100.0,
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "preflight.json").write_text(
        json.dumps(
            {
                "total_variables": 100,
                "routes_od": 1,
                "routes_dc": 1,
                "routes_dd": 1,
                "routes_oc": int(direct),
            }
        ),
        encoding="utf-8",
    )
    pd.DataFrame(warehouse_metrics).to_csv(
        run_dir / "storage_by_warehouse.csv", index=False
    )
    if performance:
        pd.DataFrame(performance).to_csv(
            run_dir / "scenario_performance.csv", index=False
        )

