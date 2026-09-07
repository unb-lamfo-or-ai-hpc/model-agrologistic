import csv
import hashlib
import json
from pathlib import Path

import pytest

from src.logic.scientific_plots import ScientificPlotError, build_publication_plots


def test_publication_plots_are_complete_traceable_and_deterministic(tmp_path):
    evidence = _write_evidence_package(tmp_path / "evidence")

    first = build_publication_plots(evidence, tmp_path / "plots-a", dpi=72)
    second = build_publication_plots(evidence, tmp_path / "plots-b", dpi=72)

    figure_names = {
        "gate_performance",
        "capacity_adequacy",
        "cost_structure",
        "value_of_information",
        "value_of_information_decomposition",
        "investment_capacity",
        "investment_changes",
    }
    assert set(first) == {
        "manifest_json",
        *(f"{name}_{kind}" for name in figure_names for kind in ("csv", "png", "pdf")),
    }

    manifest = json.loads(first["manifest_json"].read_text(encoding="utf-8"))
    assert manifest["evidence_status"] == "accepted"
    assert manifest["evidence_manifest"]["gate_order"] == ["gate_2b", "gate_2c", "gate_2d"]
    assert len(manifest["figures"]) == 7
    assert set(manifest["sources"]) == {
        "summary_csv",
        "checks_csv",
        "decomposition_csv",
        "investment_decisions_csv",
        "investment_changes_csv",
    }

    for name in figure_names:
        assert first[f"{name}_png"].read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        assert first[f"{name}_pdf"].read_bytes().startswith(b"%PDF")
        assert len(_read_csv(first[f"{name}_csv"])) > 0
        for kind in ("csv", "png", "pdf"):
            assert _sha256(first[f"{name}_{kind}"]) == _sha256(second[f"{name}_{kind}"])


def test_publication_plots_reject_a_nonaccepted_evidence_package(tmp_path):
    evidence = _write_evidence_package(tmp_path / "evidence", status="rejected")

    with pytest.raises(ScientificPlotError, match="not accepted"):
        build_publication_plots(evidence, tmp_path / "plots", dpi=72)


def test_publication_plots_reject_a_modified_source_table(tmp_path):
    evidence = _write_evidence_package(tmp_path / "evidence")
    with (evidence / "mvp_gate_summary.csv").open("a", encoding="utf-8") as stream:
        stream.write("tampered\n")

    with pytest.raises(ScientificPlotError, match="checksum mismatch"):
        build_publication_plots(evidence, tmp_path / "plots", dpi=72)


def test_publication_plots_reject_a_blocking_acceptance_check(tmp_path):
    evidence = _write_evidence_package(tmp_path / "evidence", failed_check=True)

    with pytest.raises(ScientificPlotError, match="blocking failure"):
        build_publication_plots(evidence, tmp_path / "plots", dpi=72)


def _write_evidence_package(
    root: Path,
    *,
    status: str = "accepted",
    failed_check: bool = False,
) -> Path:
    root.mkdir(parents=True)
    summary = [
        {
            "gate": "gate_2b",
            "domestic_service_level": 1.0,
            "minimum_scenario_service_level": "",
            "maximum_scenario_service_level": "",
            "dyn_cap": 30_800_000.0,
            "turnover": 28.7,
            "emergency_static_capacity": 0.01,
            "emergency_reception_capacity": 0.01,
            "total_unmet_demand": 0.0,
            "investment_cost": 1_000_000_000.0,
            "operation_cost": 56_000_000_000.0,
            "penalty_cost": 20_000.0,
            "penalty_cost_share": 0.00000035,
            "evpi": "",
            "vss": "",
            "candidate_capacity": 867_910.0,
            "expansion_capacity": 90_000.0,
            "bulk_capacity": 35_019.0,
        },
        {
            "gate": "gate_2c",
            "domestic_service_level": 1.0,
            "minimum_scenario_service_level": 1.0,
            "maximum_scenario_service_level": 1.0,
            "dyn_cap": 30_825_500.0,
            "turnover": 28.48,
            "emergency_static_capacity": 0.0,
            "emergency_reception_capacity": 646_645.89,
            "total_unmet_demand": 0.0,
            "investment_cost": 1_100_000_000.0,
            "operation_cost": 56_000_000_000.0,
            "penalty_cost": 646_645_890_000.0,
            "penalty_cost_share": 0.9188,
            "evpi": 14_926_230.0,
            "vss": 110_687_030_355.0,
            "candidate_capacity": 867_910.0,
            "expansion_capacity": 100_000.0,
            "bulk_capacity": 36_000.0,
        },
        {
            "gate": "gate_2d",
            "domestic_service_level": 1.0,
            "minimum_scenario_service_level": 1.0,
            "maximum_scenario_service_level": 1.0,
            "dyn_cap": 30_825_488.0,
            "turnover": 28.48,
            "emergency_static_capacity": 0.0,
            "emergency_reception_capacity": 646_645.89,
            "total_unmet_demand": 0.0,
            "investment_cost": 1_100_000_000.0,
            "operation_cost": 56_000_000_000.0,
            "penalty_cost": 646_645_890_000.0,
            "penalty_cost_share": 0.9188,
            "evpi": 15_055_956.0,
            "vss": 110_687_746_203.0,
            "candidate_capacity": 867_910.0,
            "expansion_capacity": 100_000.0,
            "bulk_capacity": 36_000.0,
        },
    ]
    checks = [
        {
            "gate": "gate_2b",
            "check": "usable_solution",
            "passed": not failed_check,
            "severity": "error",
        }
    ]
    decomposition = []
    for gate in ("gate_2c", "gate_2d"):
        for section in ("evpi_group", "vss_group"):
            for item, value in (
                ("investment", -1_000_000.0),
                ("operation", 2_000_000.0),
                ("penalty", 10_000_000.0),
            ):
                decomposition.append(
                    {
                        "gate": gate,
                        "section": section,
                        "item": item,
                        "value": value,
                        "interpretation": (
                            "nonobserved_big_m_feasibility_cost"
                            if item == "penalty"
                            else "modeled_economic_cost"
                        ),
                    }
                )
    investments = [
        {
            "gate": gate,
            "warehouse": "W1",
            "candidate_capacity": 100.0,
            "expansion_capacity": 50.0,
            "bulk_capacity": 25.0,
        }
        for gate in ("gate_2b", "gate_2c", "gate_2d")
    ]
    changes = []
    for left, right in (("gate_2b", "gate_2c"), ("gate_2c", "gate_2d")):
        for metric in (
            "open",
            "candidate_capacity",
            "expand",
            "expansion_capacity",
            "bulkify",
            "bulk_capacity",
            "effective_static_capacity",
        ):
            changes.append(
                {
                    "baseline_gate": left,
                    "comparison_gate": right,
                    "warehouse": "W1",
                    "metric": metric,
                    "changed": metric in {"expand", "expansion_capacity"},
                }
            )

    paths = {
        "summary_csv": root / "mvp_gate_summary.csv",
        "checks_csv": root / "mvp_acceptance_checks.csv",
        "decomposition_csv": root / "mvp_evpi_vss_decomposition.csv",
        "investment_decisions_csv": root / "mvp_investment_decisions.csv",
        "investment_changes_csv": root / "mvp_investment_changes.csv",
    }
    for key, rows in (
        ("summary_csv", summary),
        ("checks_csv", checks),
        ("decomposition_csv", decomposition),
        ("investment_decisions_csv", investments),
        ("investment_changes_csv", changes),
    ):
        _write_csv(paths[key], rows)

    manifest = {
        "schema_version": 1,
        "overall_status": status,
        "blocking_failure_count": 0,
        "gate_order": ["gate_2b", "gate_2c", "gate_2d"],
        "interpretation": {
            "monetary_caveat": "Big-M penalties are not observed monetary values.",
            "probability_policy_fallback": "Observed probabilities are explicitly labeled.",
        },
        "outputs": {
            key: {"path": path.name, "sha256": _sha256(path)} for key, path in paths.items()
        },
    }
    (root / "mvp_evidence_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return root


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
