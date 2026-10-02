"""Build auditable scientific evidence from completed experiment artifacts."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EVIDENCE_SCHEMA_VERSION = 1
INVESTMENT_COMPONENTS = {
    "opening",
    "candidate_capacity",
    "expansion_fixed",
    "expansion_variable",
    "bulkification_fixed",
    "bulkification_variable",
}
PENALTY_COMPONENTS = {
    "unmet_demand",
    "emergency_static",
    "emergency_reception",
}
CORE_COMPARISON_METRICS = (
    "objective_value",
    "economic_cost",
    "penalty_cost",
    "penalty_cost_share",
    "domestic_service_level",
    "total_unmet_demand",
    "emergency_static_capacity",
    "emergency_reception_capacity",
    "dyn_cap",
    "turnover",
    "evpi",
    "vss",
    "runtime_seconds",
    "peak_rss_mb",
)
INVESTMENT_DECISION_METRICS = (
    "open",
    "candidate_capacity",
    "expand",
    "expansion_capacity",
    "bulkify",
    "bulk_capacity",
    "effective_static_capacity",
)
TRACEABLE_ARTIFACT_NAMES = (
    "run_summary.json",
    "result.json",
    "model_audit.json",
    "preflight.json",
    "evpi_vss_decomposition.csv",
    "scenario_performance.csv",
    "material_balance_by_scenario.csv",
    "capacity_gap_by_scenario.csv",
    "investment_saturation.csv",
)


@dataclass(frozen=True, slots=True)
class EvidenceRun:
    """One accepted gate and its completed experiment directory."""

    gate: str
    design: str
    run_dir: Path


def build_mvp_scientific_evidence(
    runs: list[EvidenceRun],
    output_dir: str | Path,
    *,
    tolerance: float = 1e-6,
) -> dict[str, Path]:
    """Consolidate results, comparisons, checks, decomposition, and provenance."""

    if len(runs) < 2:
        raise ValueError("At least two evidence runs are required.")
    gate_names = [run.gate for run in runs]
    if len(set(gate_names)) != len(gate_names):
        raise ValueError("Evidence gate names must be unique.")
    if tolerance <= 0.0:
        raise ValueError("tolerance must be positive.")

    output = Path(output_dir).resolve()
    loaded = [_load_evidence_run(run) for run in runs]
    summary_rows = [_summary_row(item) for item in loaded]
    comparison_rows = _comparison_rows(summary_rows)
    investment_rows = _investment_rows(loaded, tolerance)
    investment_change_rows = _investment_change_rows(investment_rows, tolerance)
    check_rows = _acceptance_checks(
        summary_rows,
        loaded,
        investment_rows,
        tolerance,
    )
    decomposition_rows = _decomposition_rows(loaded)
    provenance_rows = _provenance_rows(loaded)

    paths = {
        "summary_csv": output / "mvp_gate_summary.csv",
        "comparison_csv": output / "mvp_gate_comparison.csv",
        "checks_csv": output / "mvp_acceptance_checks.csv",
        "decomposition_csv": output / "mvp_evpi_vss_decomposition.csv",
        "investment_decisions_csv": output / "mvp_investment_decisions.csv",
        "investment_changes_csv": output / "mvp_investment_changes.csv",
        "provenance_csv": output / "mvp_evidence_provenance.csv",
        "report_md": output / "mvp_scientific_evidence.md",
        "manifest_json": output / "mvp_evidence_manifest.json",
    }
    _write_csv(paths["summary_csv"], summary_rows)
    _write_csv(paths["comparison_csv"], comparison_rows)
    _write_csv(paths["checks_csv"], check_rows)
    _write_csv(paths["decomposition_csv"], decomposition_rows)
    _write_csv(paths["investment_decisions_csv"], investment_rows)
    _write_csv(paths["investment_changes_csv"], investment_change_rows)
    _write_csv(paths["provenance_csv"], provenance_rows)
    _atomic_write(
        paths["report_md"],
        _markdown_report(summary_rows, comparison_rows, investment_change_rows),
    )

    blocking_failures = [
        row for row in check_rows if row["severity"] == "error" and not row["passed"]
    ]
    manifest = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),  # noqa: UP017
        "scientific_classification": ("bounded_reproduction_and_controlled_stochastic_extension"),
        "overall_status": "accepted" if not blocking_failures else "rejected",
        "tolerance": tolerance,
        "gate_order": gate_names,
        "blocking_failure_count": len(blocking_failures),
        "interpretation": {
            "economic_cost": "modeled economic cost",
            "penalty_cost": "non-observed Big-M feasibility cost",
            "evpi": "RP minus WS",
            "vss": "EEV minus RP",
            "monetary_caveat": (
                "VSS penalty components are capacity-adequacy indicators and are not "
                "observed monetary benefits."
            ),
            "probability_policy_fallback": (
                "When legacy metadata omits the declared policy, the package labels "
                "the observed probability vector without claiming its provenance."
            ),
        },
        "inputs": provenance_rows,
        "outputs": {
            key: {
                "path": path.name,
                "sha256": _sha256(path),
            }
            for key, path in paths.items()
            if key != "manifest_json"
        },
    }
    _write_json(paths["manifest_json"], manifest)
    return paths


def _load_evidence_run(run: EvidenceRun) -> dict[str, Any]:
    run_dir = run.run_dir.resolve()
    summary_path = run_dir / "run_summary.json"
    result_path = run_dir / "result.json"
    if not summary_path.is_file():
        raise FileNotFoundError(f"Run summary not found: {summary_path}")
    if not result_path.is_file():
        raise FileNotFoundError(f"Structured result not found: {result_path}")
    summary = _read_mapping(summary_path)
    result = _read_mapping(result_path)
    audit_path = run_dir / "model_audit.json"
    audit = _read_mapping(audit_path) if audit_path.is_file() else {}
    stochastic = result.get("stochastic_performance")
    if stochastic is not None and not isinstance(stochastic, dict):
        raise ValueError(f"Invalid stochastic_performance in {result_path}.")
    return {
        "run": run,
        "summary": summary,
        "result": result,
        "stochastic": stochastic,
        "audit": audit,
    }


def _summary_row(item: dict[str, Any]) -> dict[str, Any]:
    run: EvidenceRun = item["run"]
    summary = item["summary"]
    result = item["result"]
    stochastic = item["stochastic"] or {}
    result_payload = result.get("result", {})
    if not isinstance(result_payload, dict):
        raise ValueError(f"Invalid result payload for gate {run.gate}.")

    costs = result_payload.get("cost_breakdown", {})
    if not isinstance(costs, dict):
        costs = {}
    grouped = _group_costs(costs)
    decomposition = stochastic.get("decomposition", {})
    if isinstance(decomposition, dict):
        profiles = decomposition.get("cost_profiles", {})
        recourse = profiles.get("recourse_problem", {}) if isinstance(profiles, dict) else {}
        recourse_groups = recourse.get("groups", {}) if isinstance(recourse, dict) else {}
        if isinstance(recourse_groups, dict) and recourse_groups:
            grouped = {
                key: _number(recourse_groups.get(key))
                for key in ("investment", "operation", "penalty")
            }

    economic = _first_number(
        summary.get("economic_cost"), grouped["investment"] + grouped["operation"]
    )
    penalized = _first_number(summary.get("penalized_cost"), summary.get("objective_value"))
    penalty = _first_number(grouped["penalty"], None)
    if penalty is None and economic is not None and penalized is not None:
        penalty = penalized - economic

    metadata = result.get("experiment", {}).get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    material_balance, material_balance_source = _material_balance_status(
        summary,
        item["audit"],
    )
    probability_policy, probability_policy_source = _probability_policy(
        metadata,
        stochastic,
    )
    decisions = _warehouse_decisions(item)
    investment_summary = _investment_summary(decisions)
    return {
        "gate": run.gate,
        "design": run.design,
        "classification": metadata.get("comparison_status", "bounded_reproduction"),
        "run_name": summary.get("name"),
        "status": summary.get("status"),
        "scenario_count": summary.get("scenario_count"),
        "objective_value": _number(summary.get("objective_value")),
        "economic_cost": economic,
        "investment_cost": grouped["investment"],
        "operation_cost": grouped["operation"],
        "penalty_cost": penalty,
        "penalty_cost_share": _ratio(penalty, penalized),
        "domestic_service_level": _number(summary.get("domestic_service_level")),
        "minimum_scenario_service_level": _number(summary.get("minimum_scenario_service_level")),
        "maximum_scenario_service_level": _number(summary.get("maximum_scenario_service_level")),
        "total_unmet_demand": _number(summary.get("total_unmet_demand")),
        "emergency_static_capacity": _number(summary.get("emergency_static_capacity")),
        "emergency_reception_capacity": _number(summary.get("emergency_reception_capacity")),
        "capacity_adequacy_status": summary.get("capacity_adequacy_status"),
        "material_balance_ok": material_balance,
        "material_balance_source": material_balance_source,
        "dyn_cap": _number(summary.get("dyn_cap")),
        "turnover": _number(summary.get("turnover")),
        "evpi": _first_number(stochastic.get("evpi"), summary.get("evpi")),
        "vss": _first_number(stochastic.get("vss"), summary.get("vss")),
        "runtime_seconds": _number(summary.get("runtime_seconds")),
        "peak_rss_mb": _number(summary.get("peak_rss_mb")),
        "slurm_job_id": summary.get("slurm_job_id"),
        "probability_policy": probability_policy,
        "probability_policy_source": probability_policy_source,
        "forecasting_reconstructed": metadata.get("forecasting_reconstructed"),
        **investment_summary,
    }


def _material_balance_status(
    summary: dict[str, Any],
    audit: dict[str, Any],
) -> tuple[bool | None, str | None]:
    summary_value = summary.get("material_balance_ok")
    if isinstance(summary_value, bool):
        return summary_value, "run_summary"
    solution = audit.get("solution", {})
    if not isinstance(solution, dict):
        return None, None
    material_balance = solution.get("material_balance", {})
    if not isinstance(material_balance, dict):
        return None, None
    audit_value = material_balance.get("all_within_tolerance")
    if isinstance(audit_value, bool):
        return audit_value, "model_audit"
    return None, None


def _probability_policy(
    metadata: dict[str, Any],
    stochastic: dict[str, Any],
) -> tuple[str | None, str | None]:
    declared = metadata.get("probability_policy")
    if declared:
        return str(declared), "experiment_metadata"
    stochastic_metadata = stochastic.get("metadata", {})
    if not isinstance(stochastic_metadata, dict):
        return None, None
    probabilities = stochastic_metadata.get("scenario_probabilities", {})
    if not isinstance(probabilities, dict) or not probabilities:
        return None, None
    values = [_number(value) for value in probabilities.values()]
    if any(value is None for value in values):
        return None, None
    observed = [value for value in values if value is not None]
    if max(observed) - min(observed) <= 1e-12:
        return "equal_observed_weights", "stochastic_performance"
    return "explicit_observed_weights", "stochastic_performance"


def _warehouse_decisions(item: dict[str, Any]) -> list[dict[str, Any]]:
    result_payload = item["result"].get("result", {})
    if not isinstance(result_payload, dict):
        return []
    decisions = result_payload.get("warehouse_decisions", [])
    if not isinstance(decisions, list):
        return []
    return [decision for decision in decisions if isinstance(decision, dict)]


def _investment_summary(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "investment_decision_count": len(decisions),
        "candidates_opened": sum(
            bool(decision.get("is_candidate"))
            and (_number(decision.get("candidate_capacity")) or 0.0) > 1e-7
            for decision in decisions
        ),
        "candidate_capacity": sum(
            _number(decision.get("candidate_capacity")) or 0.0 for decision in decisions
        ),
        "warehouses_expanded": sum(
            (_number(decision.get("expansion_capacity")) or 0.0) > 1e-7 for decision in decisions
        ),
        "expansion_capacity": sum(
            _number(decision.get("expansion_capacity")) or 0.0 for decision in decisions
        ),
        "warehouses_bulkified": sum(
            (_number(decision.get("bulk_capacity")) or 0.0) > 1e-7 for decision in decisions
        ),
        "bulk_capacity": sum(
            _number(decision.get("bulk_capacity")) or 0.0 for decision in decisions
        ),
        "effective_static_capacity": sum(
            _number(decision.get("effective_static_capacity")) or 0.0 for decision in decisions
        ),
    }


def _group_costs(costs: dict[str, Any]) -> dict[str, float]:
    grouped = {"investment": 0.0, "operation": 0.0, "penalty": 0.0}
    for component, raw_value in costs.items():
        value = _number(raw_value)
        if value is None:
            continue
        if component in INVESTMENT_COMPONENTS:
            grouped["investment"] += value
        elif component in PENALTY_COMPONENTS:
            grouped["penalty"] += value
        else:
            grouped["operation"] += value
    return grouped


def _comparison_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for baseline, comparison in zip(rows, rows[1:], strict=False):
        for metric in CORE_COMPARISON_METRICS:
            baseline_value = _number(baseline.get(metric))
            comparison_value = _number(comparison.get(metric))
            if baseline_value is None or comparison_value is None:
                continue
            delta = comparison_value - baseline_value
            records.append(
                {
                    "baseline_gate": baseline["gate"],
                    "comparison_gate": comparison["gate"],
                    "metric": metric,
                    "baseline_value": baseline_value,
                    "comparison_value": comparison_value,
                    "delta": delta,
                    "relative_change_fraction": _ratio(delta, baseline_value),
                    "comparison_scope": (
                        "controlled_extension_not_direct_thesis_numeric_validation"
                    ),
                }
            )
    return records


def _investment_rows(
    loaded: list[dict[str, Any]],
    tolerance: float,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in loaded:
        run: EvidenceRun = item["run"]
        result = item["result"]
        metadata = result.get("experiment", {}).get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        decisions = _warehouse_decisions(item)
        warehouse_ids = [str(decision.get("warehouse", "")) for decision in decisions]
        if any(not warehouse for warehouse in warehouse_ids):
            raise ValueError(f"Gate {run.gate} contains a warehouse decision without an ID.")
        duplicates = sorted(
            warehouse for warehouse in set(warehouse_ids) if warehouse_ids.count(warehouse) > 1
        )
        if duplicates:
            raise ValueError(
                f"Gate {run.gate} contains duplicate warehouse decisions: {duplicates}."
            )
        for decision in decisions:
            candidate_capacity = _number(decision.get("candidate_capacity")) or 0.0
            expansion_capacity = _number(decision.get("expansion_capacity")) or 0.0
            bulk_capacity = _number(decision.get("bulk_capacity")) or 0.0
            records.append(
                {
                    "gate": run.gate,
                    "design": run.design,
                    "classification": metadata.get("comparison_status", "bounded_reproduction"),
                    "warehouse": str(decision["warehouse"]),
                    "is_existing": bool(decision.get("is_existing", False)),
                    "is_candidate": bool(decision.get("is_candidate", False)),
                    "open": _number(decision.get("open")) or 0.0,
                    "candidate_capacity": candidate_capacity,
                    "expand": _number(decision.get("expand")) or 0.0,
                    "expansion_capacity": expansion_capacity,
                    "bulkify": _number(decision.get("bulkify")) or 0.0,
                    "bulk_capacity": bulk_capacity,
                    "static_capacity": _number(decision.get("static_capacity")) or 0.0,
                    "effective_static_capacity": (
                        _number(decision.get("effective_static_capacity")) or 0.0
                    ),
                    "selected_for_investment": (
                        candidate_capacity > tolerance
                        or expansion_capacity > tolerance
                        or bulk_capacity > tolerance
                    ),
                }
            )
    return records


def _investment_change_rows(
    records: list[dict[str, Any]],
    tolerance: float,
) -> list[dict[str, Any]]:
    gates = list(dict.fromkeys(str(record["gate"]) for record in records))
    by_gate = {
        gate: {str(record["warehouse"]): record for record in records if record["gate"] == gate}
        for gate in gates
    }
    changes: list[dict[str, Any]] = []
    for baseline_gate, comparison_gate in zip(gates, gates[1:], strict=False):
        baseline_records = by_gate[baseline_gate]
        comparison_records = by_gate[comparison_gate]
        warehouses = sorted(set(baseline_records) | set(comparison_records))
        for warehouse in warehouses:
            baseline = baseline_records.get(warehouse, {})
            comparison = comparison_records.get(warehouse, {})
            for metric in INVESTMENT_DECISION_METRICS:
                baseline_value = _number(baseline.get(metric)) or 0.0
                comparison_value = _number(comparison.get(metric)) or 0.0
                delta = comparison_value - baseline_value
                changes.append(
                    {
                        "baseline_gate": baseline_gate,
                        "comparison_gate": comparison_gate,
                        "warehouse": warehouse,
                        "baseline_present": bool(baseline),
                        "comparison_present": bool(comparison),
                        "metric": metric,
                        "baseline_value": baseline_value,
                        "comparison_value": comparison_value,
                        "delta": delta,
                        "changed": abs(delta) > tolerance,
                        "comparison_scope": (
                            "controlled_extension_not_direct_thesis_numeric_validation"
                        ),
                    }
                )
    return changes


def _acceptance_checks(
    rows: list[dict[str, Any]],
    loaded: list[dict[str, Any]],
    investment_rows: list[dict[str, Any]],
    tolerance: float,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for row, item in zip(rows, loaded, strict=True):
        gate = row["gate"]
        _add_check(
            checks, gate, "usable_solution", row["status"] == "optimal", "error", row["status"]
        )
        expected_scenarios = {"gate_2b": 1, "gate_2c": 3, "gate_2d": 9}.get(gate)
        if expected_scenarios is not None:
            _add_check(
                checks,
                gate,
                "scenario_count",
                row["scenario_count"] == expected_scenarios,
                "error",
                row["scenario_count"],
            )
        service = row["domestic_service_level"]
        _add_check(
            checks,
            gate,
            "domestic_demand_satisfied",
            service is not None and service >= 1.0 - tolerance,
            "error",
            service,
        )
        unmet = row["total_unmet_demand"]
        _add_check(
            checks,
            gate,
            "unmet_demand_within_tolerance",
            unmet is not None and abs(unmet) <= tolerance,
            "error",
            unmet,
        )
        material_balance = row["material_balance_ok"]
        _add_check(
            checks,
            gate,
            "material_balance_reported_and_valid",
            material_balance is True,
            "error" if gate != "gate_2b" else "warning",
            material_balance,
        )
        gate_investments = [record for record in investment_rows if record["gate"] == gate]
        _add_check(
            checks,
            gate,
            "first_stage_decisions_exported",
            bool(gate_investments),
            "error",
            len(gate_investments),
        )

        stochastic = item["stochastic"]
        if stochastic:
            probabilities = stochastic.get("metadata", {}).get("scenario_probabilities", {})
            probability_sum = sum(float(value) for value in probabilities.values())
            _add_check(
                checks,
                gate,
                "scenario_probabilities_sum_to_one",
                bool(probabilities) and abs(probability_sum - 1.0) <= tolerance,
                "error",
                probability_sum,
            )
            for metric in ("evpi", "vss"):
                value = row[metric]
                _add_check(
                    checks,
                    gate,
                    f"{metric}_nonnegative",
                    value is not None and value >= -tolerance,
                    "error",
                    value,
                )

        emergency = (_number(row["emergency_static_capacity"]) or 0.0) + (
            _number(row["emergency_reception_capacity"]) or 0.0
        )
        _add_check(
            checks,
            gate,
            "emergency_capacity_interpreted_as_gap",
            True,
            "info",
            emergency,
        )
    return checks


def _decomposition_rows(loaded: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in loaded:
        stochastic = item["stochastic"]
        if not stochastic:
            continue
        run: EvidenceRun = item["run"]
        decomposition = stochastic.get("decomposition", {})
        if not isinstance(decomposition, dict):
            continue
        for profile_name, profile in decomposition.get("cost_profiles", {}).items():
            for group, value in profile.get("groups", {}).items():
                records.append(
                    _decomposition_record(run, "solution_cost_group", profile_name, group, value)
                )
            for component, value in profile.get("components", {}).items():
                records.append(
                    _decomposition_record(
                        run, "solution_cost_component", profile_name, component, value
                    )
                )
        for comparison in ("evpi", "vss"):
            for level in ("group", "component"):
                values = decomposition.get(f"{comparison}_by_{level}", {})
                for item_name, value in values.items():
                    records.append(
                        _decomposition_record(
                            run, f"{comparison}_{level}", comparison, item_name, value
                        )
                    )
        for profile_name, values in decomposition.get("physical_recourse_profiles", {}).items():
            for item_name, value in values.items():
                records.append(
                    _decomposition_record(run, "physical_recourse", profile_name, item_name, value)
                )
    return records


def _decomposition_record(
    run: EvidenceRun,
    section: str,
    comparison: str,
    item: str,
    value: Any,
) -> dict[str, Any]:
    is_penalty = item in PENALTY_COMPONENTS or item == "penalty"
    return {
        "gate": run.gate,
        "design": run.design,
        "section": section,
        "comparison": comparison,
        "item": item,
        "value": _number(value),
        "interpretation": (
            "nonobserved_big_m_feasibility_cost"
            if is_penalty and section != "physical_recourse"
            else "physical_quantity"
            if section == "physical_recourse"
            else "modeled_economic_cost"
        ),
    }


def _provenance_rows(loaded: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in loaded:
        run: EvidenceRun = item["run"]
        for name in TRACEABLE_ARTIFACT_NAMES:
            path = run.run_dir.resolve() / name
            if path.is_file():
                records.append(
                    {
                        "gate": run.gate,
                        "design": run.design,
                        "artifact": name,
                        "path": (
                            f"{run.gate}/{run.run_dir.name}/{name}"
                        ),
                        "size_bytes": path.stat().st_size,
                        "sha256": _sha256(path),
                    }
                )
    return records


def _markdown_report(
    rows: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    investment_changes: list[dict[str, Any]],
) -> str:
    lines = [
        "# MVP scientific evidence",
        "",
        "## Scientific scope",
        "",
        "Gate 2B is a bounded deterministic reproduction. Gates 2C and 2D are "
        "controlled stochastic extensions. They are not direct numerical validations "
        "of the thesis forecasting pipeline.",
        "",
        "## Gate summary",
        "",
        "| Gate | Design | Scenarios | Service | Economic cost | Penalty cost | EVPI | VSS |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {gate} | {design} | {scenarios} | {service} | {economic} | "
            "{penalty} | {evpi} | {vss} |".format(
                gate=row["gate"],
                design=row["design"],
                scenarios=row["scenario_count"],
                service=_format_number(row["domestic_service_level"], 6),
                economic=_format_number(row["economic_cost"], 2),
                penalty=_format_number(row["penalty_cost"], 2),
                evpi=_format_number(row["evpi"], 2),
                vss=_format_number(row["vss"], 2),
            )
        )

    lines.extend(
        [
            "",
            "## First-stage investment summary",
            "",
            "| Gate | Candidates opened | Candidate capacity | Expanded warehouses | "
            "Expansion capacity | Bulkified warehouses | Bulk capacity |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in rows:
        lines.append(
            "| {gate} | {opened} | {candidate} | {expanded} | {expansion} | "
            "{bulkified} | {bulk} |".format(
                gate=row["gate"],
                opened=row["candidates_opened"],
                candidate=_format_number(row["candidate_capacity"], 4),
                expanded=row["warehouses_expanded"],
                expansion=_format_number(row["expansion_capacity"], 4),
                bulkified=row["warehouses_bulkified"],
                bulk=_format_number(row["bulk_capacity"], 4),
            )
        )

    changed_by_transition: dict[tuple[str, str], set[str]] = {}
    for record in investment_changes:
        if not record["changed"]:
            continue
        transition = (
            str(record["baseline_gate"]),
            str(record["comparison_gate"]),
        )
        changed_by_transition.setdefault(transition, set()).add(str(record["warehouse"]))
    lines.extend(
        [
            "",
            "## First-stage decision stability",
            "",
            "| Baseline | Comparison | Warehouses with a changed investment decision |",
            "|---|---|---:|",
        ]
    )
    for baseline, comparison in zip(rows, rows[1:], strict=False):
        transition = (str(baseline["gate"]), str(comparison["gate"]))
        lines.append(
            f"| {transition[0]} | {transition[1]} | "
            f"{len(changed_by_transition.get(transition, set()))} |"
        )

    lines.extend(
        [
            "",
            "## Controlled comparisons",
            "",
            "| Baseline | Comparison | Metric | Delta | Relative change |",
            "|---|---|---|---:|---:|",
        ]
    )
    report_metrics = {"economic_cost", "penalty_cost", "evpi", "vss", "runtime_seconds"}
    for row in comparisons:
        if row["metric"] not in report_metrics:
            continue
        lines.append(
            "| {baseline} | {comparison} | {metric} | {delta} | {relative} |".format(
                baseline=row["baseline_gate"],
                comparison=row["comparison_gate"],
                metric=row["metric"],
                delta=_format_number(row["delta"], 4),
                relative=_format_number(row["relative_change_fraction"], 8),
            )
        )

    lines.extend(
        [
            "",
            "## Interpretation contract",
            "",
            "- Domestic service and material balance are physical acceptance criteria.",
            "- Emergency capacity is a complete-recourse slack and an "
            "infrastructure-gap indicator.",
            "- Economic cost contains modeled investment and operation components.",
            "- Penalty cost contains non-observed Big-M feasibility costs.",
            "- EVPI is RP minus WS; VSS is EEV minus RP for the minimization model.",
            "- A penalty-dominated VSS supports a qualitative robustness conclusion, "
            "not a literal monetary saving.",
            "- Equal scenario probabilities and synthetic multipliers are "
            "experimental assumptions.",
            "",
        ]
    )
    return "\n".join(lines)


def _add_check(
    checks: list[dict[str, Any]],
    gate: str,
    check: str,
    passed: bool,
    severity: str,
    observed: Any,
) -> None:
    checks.append(
        {
            "gate": gate,
            "check": check,
            "passed": bool(passed),
            "severity": severity,
            "observed": observed,
        }
    )


def _read_mapping(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON mapping in {path}.")
    return payload


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _first_number(*values: Any) -> float | None:
    for value in values:
        number = _number(value)
        if number is not None:
            return number
    return None


def _ratio(numerator: Any, denominator: Any) -> float | None:
    numerator_value = _number(numerator)
    denominator_value = _number(denominator)
    if numerator_value is None or denominator_value in (None, 0.0):
        return None
    return numerator_value / denominator_value


def _format_number(value: Any, digits: int) -> str:
    number = _number(value)
    return "" if number is None else f"{number:.{digits}f}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    if not records:
        _atomic_write(path, "")
        return
    fields = list(dict.fromkeys(key for record in records for key in record))
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    writer.writerows(records)
    _atomic_write(path, buffer.getvalue())


def _write_json(path: Path, payload: Any) -> None:
    _atomic_write(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="")
    temporary.replace(path)

