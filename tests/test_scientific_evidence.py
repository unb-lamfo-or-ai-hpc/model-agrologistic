import csv
import json
from pathlib import Path

import pytest

from src.logic.scientific_evidence import (
    EvidenceRun,
    build_mvp_scientific_evidence,
)


def test_evidence_package_consolidates_gates_and_decomposition(tmp_path):
    runs = [
        _write_run(tmp_path, "gate_2b", 1, stochastic=False),
        _write_run(tmp_path, "gate_2c", 3, stochastic=True, evpi=4.0, vss=20.0),
        _write_run(tmp_path, "gate_2d", 9, stochastic=True, evpi=5.0, vss=21.0),
    ]

    paths = build_mvp_scientific_evidence(runs, tmp_path / "evidence")

    assert set(paths) == {
        "summary_csv",
        "comparison_csv",
        "checks_csv",
        "decomposition_csv",
        "investment_decisions_csv",
        "investment_changes_csv",
        "provenance_csv",
        "report_md",
        "manifest_json",
    }
    summary = _read_csv(paths["summary_csv"])
    assert [row["gate"] for row in summary] == ["gate_2b", "gate_2c", "gate_2d"]
    assert [int(row["scenario_count"]) for row in summary] == [1, 3, 9]
    assert float(summary[2]["evpi"]) == pytest.approx(5.0)
    assert float(summary[2]["vss"]) == pytest.approx(21.0)
    assert float(summary[2]["penalty_cost"]) == pytest.approx(900.0)
    assert float(summary[2]["penalty_cost_share"]) == pytest.approx(0.9)
    assert int(summary[2]["candidates_opened"]) == 1
    assert float(summary[2]["candidate_capacity"]) == pytest.approx(90.0)
    assert summary[1]["probability_policy"] == "equal_observed_weights"
    assert summary[1]["probability_policy_source"] == "stochastic_performance"
    assert summary[0]["material_balance_ok"] == "True"
    assert summary[0]["material_balance_source"] == "model_audit"

    comparisons = _read_csv(paths["comparison_csv"])
    gate_2d_evpi = next(
        row
        for row in comparisons
        if row["baseline_gate"] == "gate_2c"
        and row["comparison_gate"] == "gate_2d"
        and row["metric"] == "evpi"
    )
    assert float(gate_2d_evpi["delta"]) == pytest.approx(1.0)

    investments = _read_csv(paths["investment_decisions_csv"])
    assert len(investments) == 3
    assert all(row["warehouse"] == "W1" for row in investments)
    changes = _read_csv(paths["investment_changes_csv"])
    candidate_change = next(
        row
        for row in changes
        if row["baseline_gate"] == "gate_2c"
        and row["comparison_gate"] == "gate_2d"
        and row["metric"] == "candidate_capacity"
    )
    assert float(candidate_change["delta"]) == pytest.approx(10.0)
    assert candidate_change["changed"] == "True"

    decomposition = _read_csv(paths["decomposition_csv"])
    penalty = next(
        row
        for row in decomposition
        if row["gate"] == "gate_2d" and row["section"] == "vss_group" and row["item"] == "penalty"
    )
    assert penalty["interpretation"] == "nonobserved_big_m_feasibility_cost"

    checks = _read_csv(paths["checks_csv"])
    assert all(row["passed"] == "True" for row in checks)
    manifest = json.loads(paths["manifest_json"].read_text(encoding="utf-8"))
    assert manifest["overall_status"] == "accepted"
    assert manifest["gate_order"] == ["gate_2b", "gate_2c", "gate_2d"]
    assert manifest["blocking_failure_count"] == 0
    assert manifest["inputs"]
    assert all(len(record["sha256"]) == 64 for record in manifest["inputs"])
    assert all(not Path(record["path"]).is_absolute() for record in manifest["inputs"])
    assert all(
        record["path"].split("/", maxsplit=1)[0] == record["gate"]
        for record in manifest["inputs"]
    )
    assert "controlled stochastic extensions" in paths["report_md"].read_text(encoding="utf-8")


def test_evidence_manifest_rejects_a_failed_physical_gate(tmp_path):
    gate_2b = _write_run(tmp_path, "gate_2b", 1, stochastic=False)
    gate_2c = _write_run(
        tmp_path,
        "gate_2c",
        3,
        stochastic=True,
        service=0.95,
        unmet=5.0,
    )

    paths = build_mvp_scientific_evidence(
        [gate_2b, gate_2c],
        tmp_path / "evidence",
    )

    manifest = json.loads(paths["manifest_json"].read_text(encoding="utf-8"))
    assert manifest["overall_status"] == "rejected"
    assert manifest["blocking_failure_count"] == 2
    failed = [row for row in _read_csv(paths["checks_csv"]) if row["passed"] == "False"]
    assert {row["check"] for row in failed} == {
        "domestic_demand_satisfied",
        "unmet_demand_within_tolerance",
    }


def test_evidence_requires_structured_result(tmp_path):
    run_dir = tmp_path / "incomplete"
    run_dir.mkdir()
    (run_dir / "run_summary.json").write_text("{}", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="Structured result not found"):
        build_mvp_scientific_evidence(
            [
                EvidenceRun("one", "test", run_dir),
                EvidenceRun("two", "test", run_dir),
            ],
            tmp_path / "evidence",
        )


def _write_run(
    root: Path,
    gate: str,
    scenario_count: int,
    *,
    stochastic: bool,
    service: float = 1.0,
    unmet: float = 0.0,
    evpi: float = 3.0,
    vss: float = 15.0,
) -> EvidenceRun:
    run_dir = root / gate
    run_dir.mkdir()
    summary = {
        "name": f"{gate}_run",
        "status": "optimal",
        "scenario_count": scenario_count,
        "objective_value": 1000.0,
        "economic_cost": 100.0,
        "penalized_cost": 1000.0,
        "domestic_service_level": service,
        "minimum_scenario_service_level": service if stochastic else None,
        "maximum_scenario_service_level": service if stochastic else None,
        "total_unmet_demand": unmet,
        "emergency_static_capacity": 0.0,
        "emergency_reception_capacity": 0.0009,
        "capacity_adequacy_status": "emergency_capacity_required",
        "material_balance_ok": None if gate == "gate_2b" else True,
        "dyn_cap": 25.0,
        "turnover": 2.5,
        "evpi": evpi if stochastic else None,
        "vss": vss if stochastic else None,
        "runtime_seconds": float(scenario_count),
        "peak_rss_mb": 128.0,
        "slurm_job_id": "123",
    }
    stochastic_performance = None
    if stochastic:
        probabilities = {
            f"scenario_{index}": 1.0 / scenario_count for index in range(scenario_count)
        }
        stochastic_performance = {
            "recourse_problem": 1000.0,
            "wait_and_see": 1000.0 - evpi,
            "expected_value_problem": 90.0,
            "expected_result_of_ev_solution": 1000.0 + vss,
            "evpi": evpi,
            "vss": vss,
            "metadata": {"scenario_probabilities": probabilities},
            "decomposition": {
                "cost_profiles": {
                    "recourse_problem": {
                        "groups": {
                            "investment": 40.0,
                            "operation": 60.0,
                            "penalty": 900.0,
                        },
                        "components": {
                            "opening": 40.0,
                            "storage": 60.0,
                            "emergency_reception": 900.0,
                        },
                    }
                },
                "evpi_by_group": {
                    "investment": evpi,
                    "operation": 0.0,
                    "penalty": 0.0,
                },
                "vss_by_group": {
                    "investment": -1.0,
                    "operation": -2.0,
                    "penalty": vss + 3.0,
                },
                "physical_recourse_profiles": {
                    "recourse_problem": {
                        "emergency_reception_tons_over_periods": 0.0009,
                        "emergency_static_tons_over_periods": 0.0,
                        "unmet_demand_tons": unmet,
                    }
                },
            },
        }
    result = {
        "experiment": {
            "metadata": {
                "comparison_status": (
                    "controlled_extension" if stochastic else "bounded_reproduction"
                ),
                "probability_policy": ("equal_experimental_weights" if gate == "gate_2d" else None),
                "forecasting_reconstructed": False,
            }
        },
        "result": {
            "cost_breakdown": {
                "opening": 40.0,
                "storage": 60.0,
                "emergency_reception": 900.0,
            },
            "warehouse_decisions": [
                {
                    "warehouse": "W1",
                    "is_existing": False,
                    "is_candidate": True,
                    "open": 1.0,
                    "candidate_capacity": {
                        "gate_2b": 70.0,
                        "gate_2c": 80.0,
                        "gate_2d": 90.0,
                    }[gate],
                    "expand": 0.0,
                    "expansion_capacity": 0.0,
                    "bulkify": 0.0,
                    "bulk_capacity": 0.0,
                    "static_capacity": 0.0,
                    "effective_static_capacity": {
                        "gate_2b": 70.0,
                        "gate_2c": 80.0,
                        "gate_2d": 90.0,
                    }[gate],
                }
            ],
        },
        "stochastic_performance": stochastic_performance,
    }
    (run_dir / "run_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (run_dir / "result.json").write_text(json.dumps(result), encoding="utf-8")
    (run_dir / "model_audit.json").write_text(
        json.dumps({"solution": {"material_balance": {"all_within_tolerance": True}}}),
        encoding="utf-8",
    )
    return EvidenceRun(gate, gate, run_dir)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))

