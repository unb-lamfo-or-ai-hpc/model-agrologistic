"""Reproducible experiment execution and structured result export for HPC."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import platform
import re
import sys
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

from src.logic.excel_loader import ExcelLoaderConfig, load_model_data_from_excel
from src.logic.metrics import attach_storage_metrics
from src.logic.model_audit import build_model_audit
from src.logic.model_config import ModelConfig, SolverConfig
from src.logic.model_data import ModelData
from src.logic.optimization import (
    EVPIVSSResult,
    OptimizationResult,
    calculate_evpi_vss,
    solve_model,
)
from src.logic.route_filtering import select_routes


MANIFEST_VERSION = 1
SAFE_RUN_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
SERVICE_POLICY_COMPARISON_METRICS = (
    "domestic_service_level",
    "minimum_scenario_service_level",
    "maximum_scenario_service_level",
    "total_unmet_demand",
    "total_emergency_capacity",
    "economic_cost",
    "penalized_cost",
    "dyn_cap",
    "turnover",
    "runtime_seconds",
    "peak_rss_mb",
)


@dataclass(slots=True)
class ExperimentSpec:
    """Complete, validated specification for one optimization experiment."""

    name: str
    workbook: Path
    loader: ExcelLoaderConfig = field(default_factory=ExcelLoaderConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    solver: SolverConfig = field(default_factory=SolverConfig)
    calculate_evpi_vss: bool = False
    resume_evpi_vss: bool = False
    max_estimated_variables: int | None = 2_000_000
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not SAFE_RUN_NAME.fullmatch(self.name):
            raise ValueError(
                "Experiment name must start with an alphanumeric character and "
                "contain only letters, numbers, '.', '_', or '-'."
            )
        if self.model.mode == "sto" and not self.loader.include_stochastic_scenarios:
            raise ValueError(
                "Stochastic experiments require "
                "loader.include_stochastic_scenarios=true."
            )
        if self.calculate_evpi_vss and self.model.mode != "sto":
            raise ValueError("EVPI/VSS can only be requested for stochastic runs.")
        if self.calculate_evpi_vss and self.model.objective_policy != "penalty":
            raise ValueError(
                "EVPI/VSS requires objective_policy='penalty' because its "
                "values compare scalar monetary objectives."
            )
        if self.resume_evpi_vss and not self.calculate_evpi_vss:
            raise ValueError(
                "resume_evpi_vss requires calculate_evpi_vss=true."
            )
        if self.max_estimated_variables is not None and self.max_estimated_variables <= 0:
            raise ValueError("max_estimated_variables must be positive or null.")


@dataclass(slots=True)
class ExperimentManifest:
    """Collection of experiments loaded from one versioned YAML manifest."""

    experiments: list[ExperimentSpec]
    output_dir: Path
    continue_on_error: bool = False
    source_path: Path | None = None


@dataclass(slots=True)
class ExperimentRunSummary:
    """Small, CSV-friendly outcome record for one experiment."""

    name: str
    status: str
    objective_policy: str
    comparison_group: str | None
    campaign_gate: str | None
    scenario_count: int | None
    objective_value: float | None
    economic_cost: float | None
    penalized_cost: float | None
    runtime_seconds: float | None
    peak_rss_mb: float | None
    mip_gap: float | None
    dyn_cap: float | None
    turnover: float | None
    total_unmet_demand: float | None
    total_domestic_demand: float | None
    served_domestic_demand: float | None
    domestic_service_level: float | None
    minimum_scenario_service_level: float | None
    maximum_scenario_service_level: float | None
    total_direct_flow: float | None
    emergency_static_capacity: float | None
    emergency_reception_capacity: float | None
    total_emergency_capacity: float | None
    evpi: float | None
    vss: float | None
    output_dir: str
    started_at_utc: str
    finished_at_utc: str
    slurm_job_id: str | None = None
    slurm_array_task_id: str | None = None
    error_type: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class ModelSizeEstimate:
    """Pre-solve route and variable counts used by the HPC safety guard."""

    scenario_count: int
    period_count: int
    routes_od: int
    routes_dc: int
    routes_dd: int
    routes_oc: int
    flow_variables: int
    inventory_variables: int
    unmet_demand_variables: int
    emergency_capacity_variables: int
    investment_variables: int
    total_variables: int


Loader = Callable[[str | Path, ExcelLoaderConfig | None], ModelData]
Solver = Callable[..., OptimizationResult]
EVPICalculator = Callable[..., EVPIVSSResult]
Progress = Callable[[str], None]


def load_experiment_manifest(path: str | Path) -> ExperimentManifest:
    """Load and validate a version-1 YAML experiment manifest."""

    manifest_path = Path(path).resolve()
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Experiment manifest not found: {manifest_path}")

    raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Experiment manifest root must be a mapping.")
    if raw.get("version") != MANIFEST_VERSION:
        raise ValueError(
            f"Unsupported manifest version {raw.get('version')!r}; "
            f"expected {MANIFEST_VERSION}."
        )

    defaults = _mapping(raw.get("defaults", {}), "defaults")
    raw_experiments = raw.get("experiments")
    if not isinstance(raw_experiments, list) or not raw_experiments:
        raise ValueError("Manifest must define a non-empty experiments list.")

    experiments = [
        _parse_experiment(item, defaults, manifest_path.parent)
        for item in raw_experiments
    ]
    names = [experiment.name for experiment in experiments]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise ValueError(f"Experiment names must be unique; duplicates: {duplicates}.")
    _validate_service_policy_groups(experiments)

    output_dir = _resolve_path(
        raw.get("output_dir", "data/results/hpc"),
        manifest_path.parent,
    )
    return ExperimentManifest(
        experiments=experiments,
        output_dir=output_dir,
        continue_on_error=bool(raw.get("continue_on_error", False)),
        source_path=manifest_path,
    )


def run_experiment(
    spec: ExperimentSpec,
    output_root: str | Path,
    *,
    loader: Loader = load_model_data_from_excel,
    solver: Solver = solve_model,
    evpi_calculator: EVPICalculator = calculate_evpi_vss,
    progress: Progress = print,
) -> ExperimentRunSummary:
    """Execute one experiment and atomically export its structured artifacts."""

    started = datetime.now(timezone.utc)
    run_dir = Path(output_root).resolve() / spec.name
    run_dir.mkdir(parents=True, exist_ok=True)

    progress(f"[{spec.name}] loading {spec.workbook}")
    data = loader(spec.workbook, spec.loader)
    _write_json(
        run_dir / "model_audit.json",
        build_model_audit(data, spec.model),
    )
    estimate = estimate_model_size(data, spec.model)
    _write_json(run_dir / "preflight.json", asdict(estimate))
    progress(_preflight_message(spec, estimate))
    _enforce_size_limit(spec, estimate)

    evpi_result: EVPIVSSResult | None = None
    progress(f"[{spec.name}] building and solving model")
    if spec.calculate_evpi_vss:
        evpi_result = evpi_calculator(
            data=data,
            model_config=spec.model,
            solver_config=spec.solver,
            checkpoint_dir=run_dir / "evpi_vss_checkpoints",
            checkpoint_identity=_checkpoint_identity(spec),
            resume=spec.resume_evpi_vss,
            progress=progress,
        )
        result = evpi_result.recourse_problem_result
    else:
        result = solver(
            data=data,
            model_config=spec.model,
            solver_config=spec.solver,
        )

    if result.has_solution:
        progress(f"[{spec.name}] calculating DynCap and Turnover")
        attach_storage_metrics(data, result)

    finished = datetime.now(timezone.utc)
    progress(f"[{spec.name}] exporting structured artifacts")
    _export_run_artifacts(
        spec=spec,
        data=data,
        result=result,
        evpi_result=evpi_result,
        run_dir=run_dir,
        started=started,
        finished=finished,
    )
    summary = _build_summary(
        spec=spec,
        result=result,
        evpi_result=evpi_result,
        run_dir=run_dir,
        started=started,
        finished=finished,
    )
    _write_json(run_dir / "run_summary.json", asdict(summary))
    progress(f"[{spec.name}] finished with status={summary.status}")
    return summary


def inspect_experiment(
    spec: ExperimentSpec,
    output_root: str | Path,
    *,
    loader: Loader = load_model_data_from_excel,
    progress: Progress = print,
) -> ModelSizeEstimate:
    """Load an instance and export its model-size estimate without solving."""

    run_dir = Path(output_root).resolve() / spec.name
    progress(f"[{spec.name}] loading {spec.workbook}")
    data = loader(spec.workbook, spec.loader)
    _write_json(
        run_dir / "model_audit.json",
        build_model_audit(data, spec.model),
    )
    estimate = estimate_model_size(data, spec.model)
    _write_json(run_dir / "preflight.json", asdict(estimate))
    progress(_preflight_message(spec, estimate))
    return estimate


def audit_existing_run(
    spec: ExperimentSpec,
    output_root: str | Path,
    *,
    loader: Loader = load_model_data_from_excel,
    progress: Progress = print,
) -> Path:
    """Audit an existing structured result without solving the model again."""

    run_dir = Path(output_root).resolve() / spec.name
    result_path = run_dir / "result.json"
    if not result_path.is_file():
        raise FileNotFoundError(f"Structured result not found: {result_path}")

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    experiment_payload = payload.get("experiment", {})
    expected_payload = json.loads(json.dumps(_spec_payload(spec)))
    mismatches = [
        key
        for key in ("workbook_sha256", "loader", "model")
        if experiment_payload.get(key) != expected_payload.get(key)
    ]
    if mismatches:
        raise ValueError(
            "Existing result is incompatible with the selected experiment "
            f"for: {', '.join(mismatches)}."
        )

    result_payload = payload.get("result")
    if not isinstance(result_payload, dict):
        raise ValueError(f"Invalid result payload in {result_path}.")
    result_fields = {item.name for item in fields(OptimizationResult)}
    result = OptimizationResult(
        **{
            key: value
            for key, value in result_payload.items()
            if key in result_fields and key != "raw_solver_result"
        }
    )

    progress(f"[{spec.name}] loading {spec.workbook}")
    data = loader(spec.workbook, spec.loader)
    audit_path = run_dir / "model_audit.json"
    _write_json(audit_path, build_model_audit(data, spec.model, result))
    progress(f"[{spec.name}] audit -> {audit_path}")
    return audit_path


def estimate_model_size(data: ModelData, config: ModelConfig) -> ModelSizeEstimate:
    """Estimate variables created by the native deterministic/extensive form."""

    routes = select_routes(data, config)
    scenarios = len(data.scenarios) if config.mode == "sto" else 1
    periods = len(data.periods)
    flow_variables = scenarios * periods * (
        len(routes.od) + len(routes.dc) + len(routes.dd) + len(routes.oc)
    )
    inventory_variables = (
        scenarios * len(data.warehouses) * len(data.products) * periods
    )
    unmet_variables = (
        scenarios * len(data.domestic_customers) * len(data.products) * periods
    )
    emergency_variables = scenarios * len(data.warehouses) * periods * 2
    expansion_count = sum(
        config.allow_capacity_expansion
        and data.max_expand_capacity.get(warehouse, 0.0) > 0.0
        for warehouse in data.existing_warehouses
    )
    bulk_count = sum(
        config.allow_bulkification
        and data.max_bulk_capacity.get(warehouse, 0.0) > 0.0
        for warehouse in data.bulk_eligible_warehouses
    )
    investment_variables = 2 * (
        len(data.candidate_warehouses) + expansion_count + bulk_count
    )
    total_variables = (
        flow_variables
        + inventory_variables
        + unmet_variables
        + emergency_variables
        + investment_variables
    )
    return ModelSizeEstimate(
        scenario_count=scenarios,
        period_count=periods,
        routes_od=len(routes.od),
        routes_dc=len(routes.dc),
        routes_dd=len(routes.dd),
        routes_oc=len(routes.oc),
        flow_variables=flow_variables,
        inventory_variables=inventory_variables,
        unmet_demand_variables=unmet_variables,
        emergency_capacity_variables=emergency_variables,
        investment_variables=investment_variables,
        total_variables=total_variables,
    )


def run_manifest(
    manifest: ExperimentManifest,
    *,
    indices: list[int] | None = None,
    output_root: str | Path | None = None,
    loader: Loader = load_model_data_from_excel,
    solver: Solver = solve_model,
    evpi_calculator: EVPICalculator = calculate_evpi_vss,
    progress: Progress = print,
) -> list[ExperimentRunSummary]:
    """Execute all or selected manifest entries, optionally continuing on errors."""

    selected = indices if indices is not None else list(range(len(manifest.experiments)))
    invalid = [index for index in selected if index < 0 or index >= len(manifest.experiments)]
    if invalid:
        raise IndexError(
            f"Experiment indices out of range: {invalid}; valid range is "
            f"0..{len(manifest.experiments) - 1}."
        )

    root = Path(output_root).resolve() if output_root else manifest.output_dir
    summaries: list[ExperimentRunSummary] = []
    for index in selected:
        spec = manifest.experiments[index]
        run_started = datetime.now(timezone.utc)
        try:
            summary = run_experiment(
                spec,
                root,
                loader=loader,
                solver=solver,
                evpi_calculator=evpi_calculator,
                progress=progress,
            )
        except Exception as error:
            summary = _export_failed_run(
                spec,
                root,
                error,
                started=run_started,
            )
            summaries.append(summary)
            if not manifest.continue_on_error:
                raise
        else:
            summaries.append(summary)
    return summaries


def inspect_manifest(
    manifest: ExperimentManifest,
    *,
    indices: list[int] | None = None,
    output_root: str | Path | None = None,
    loader: Loader = load_model_data_from_excel,
    progress: Progress = print,
) -> list[ModelSizeEstimate]:
    """Preflight all or selected manifest entries without importing a solver."""

    selected = indices if indices is not None else list(range(len(manifest.experiments)))
    invalid = [index for index in selected if index < 0 or index >= len(manifest.experiments)]
    if invalid:
        raise IndexError(
            f"Experiment indices out of range: {invalid}; valid range is "
            f"0..{len(manifest.experiments) - 1}."
        )
    root = Path(output_root).resolve() if output_root else manifest.output_dir
    return [
        inspect_experiment(
            manifest.experiments[index],
            root,
            loader=loader,
            progress=progress,
        )
        for index in selected
    ]


def aggregate_experiment_summaries(output_root: str | Path) -> Path:
    """Combine per-run summaries after local or Slurm-array execution."""

    root = Path(output_root).resolve()
    records: list[dict[str, Any]] = []
    for path in sorted(root.glob("*/run_summary.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            records.append(payload)
    target = root / "batch_summary.csv"
    _write_csv(target, records)
    return target


def aggregate_service_policy_comparisons(
    output_root: str | Path,
) -> Path | None:
    """Export paired penalty-versus-lexicographic campaign diagnostics."""

    root = Path(output_root).resolve()
    groups: dict[str, dict[str, dict[str, Any]]] = {}
    for path in sorted(root.glob("*/run_summary.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue
        group = payload.get("comparison_group")
        policy = payload.get("objective_policy")
        if not group or policy not in {"penalty", "lexicographic"}:
            continue
        policy_runs = groups.setdefault(str(group), {})
        if policy in policy_runs:
            raise ValueError(
                f"Comparison group {group!r} contains more than one "
                f"{policy!r} run."
            )
        policy_runs[str(policy)] = payload

    if not groups:
        return None

    records = [
        _service_policy_comparison_record(group, policy_runs)
        for group, policy_runs in sorted(groups.items())
    ]
    csv_target = root / "service_policy_comparison.csv"
    json_target = root / "service_policy_comparison.json"
    _write_csv(csv_target, records)
    _write_json(
        json_target,
        {
            "schema_version": 1,
            "delta_convention": "lexicographic_minus_penalty",
            "comparisons": records,
        },
    )
    return csv_target


def _service_policy_comparison_record(
    group: str,
    policy_runs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    penalty = policy_runs.get("penalty")
    lexicographic = policy_runs.get("lexicographic")
    present = [record for record in (penalty, lexicographic) if record]
    scenario_counts = {
        int(record["scenario_count"])
        for record in present
        if record.get("scenario_count") is not None
    }

    if penalty is None or lexicographic is None:
        pair_status = "pending"
    elif penalty.get("status") == "optimal" and lexicographic.get("status") == "optimal":
        pair_status = "optimal"
    elif all(record.get("domestic_service_level") is not None for record in present):
        pair_status = "usable_nonoptimal"
    else:
        pair_status = "failed"

    record: dict[str, Any] = {
        "comparison_group": group,
        "campaign_gate": next(
            (
                item.get("campaign_gate")
                for item in present
                if item.get("campaign_gate") is not None
            ),
            None,
        ),
        "pair_status": pair_status,
        "scenario_count": (
            next(iter(scenario_counts)) if len(scenario_counts) == 1 else None
        ),
        "scenario_count_consistent": len(scenario_counts) <= 1,
        "penalty_name": penalty.get("name") if penalty else None,
        "penalty_status": penalty.get("status") if penalty else None,
        "lexicographic_name": (
            lexicographic.get("name") if lexicographic else None
        ),
        "lexicographic_status": (
            lexicographic.get("status") if lexicographic else None
        ),
    }
    for metric in SERVICE_POLICY_COMPARISON_METRICS:
        penalty_value = penalty.get(metric) if penalty else None
        lexicographic_value = lexicographic.get(metric) if lexicographic else None
        record[f"penalty_{metric}"] = penalty_value
        record[f"lexicographic_{metric}"] = lexicographic_value
        record[f"delta_{metric}"] = _numeric_delta(
            lexicographic_value,
            penalty_value,
        )

    service_delta = record["delta_domestic_service_level"]
    record["delta_service_percentage_points"] = (
        100.0 * service_delta if service_delta is not None else None
    )
    record["unmet_demand_reduction_fraction"] = _reduction_fraction(
        record["penalty_total_unmet_demand"],
        record["lexicographic_total_unmet_demand"],
    )
    record["emergency_capacity_ratio"] = _ratio(
        record["lexicographic_total_emergency_capacity"],
        record["penalty_total_emergency_capacity"],
    )
    record["economic_cost_change_fraction"] = _change_fraction(
        record["lexicographic_economic_cost"],
        record["penalty_economic_cost"],
    )
    record["penalized_cost_change_fraction"] = _change_fraction(
        record["lexicographic_penalized_cost"],
        record["penalty_penalized_cost"],
    )
    record["runtime_ratio"] = _ratio(
        record["lexicographic_runtime_seconds"],
        record["penalty_runtime_seconds"],
    )
    return record


def _parse_experiment(
    raw: Any,
    defaults: dict[str, Any],
    base_dir: Path,
) -> ExperimentSpec:
    item = _mapping(raw, "experiment")
    if "name" not in item or "workbook" not in item:
        raise ValueError("Each experiment requires name and workbook fields.")

    loader_values = {
        **_mapping(defaults.get("loader", {}), "defaults.loader"),
        **_mapping(item.get("loader", {}), "experiment.loader"),
    }
    _normalize_loader_sequences(loader_values)
    model_values = {
        **_mapping(defaults.get("model", {}), "defaults.model"),
        **_mapping(item.get("model", {}), "experiment.model"),
    }
    solver_values = {
        **_mapping(defaults.get("solver", {}), "defaults.solver"),
        **_mapping(item.get("solver", {}), "experiment.solver"),
    }

    try:
        return ExperimentSpec(
            name=str(item["name"]),
            workbook=_resolve_path(item["workbook"], base_dir),
            loader=ExcelLoaderConfig(**loader_values),
            model=ModelConfig(**model_values),
            solver=SolverConfig(**solver_values),
            calculate_evpi_vss=bool(item.get("calculate_evpi_vss", False)),
            resume_evpi_vss=bool(item.get("resume_evpi_vss", False)),
            max_estimated_variables=_optional_int(
                item.get(
                    "max_estimated_variables",
                    defaults.get("max_estimated_variables", 2_000_000),
                )
            ),
            metadata=_mapping(item.get("metadata", {}), "experiment.metadata"),
        )
    except TypeError as error:
        raise ValueError(f"Invalid experiment configuration: {error}") from error


def _normalize_loader_sequences(values: dict[str, Any]) -> None:
    for key in ("stochastic_supply_levels", "stochastic_demand_levels"):
        if key in values:
            values[key] = tuple(str(value) for value in values[key])
    if values.get("stochastic_combinations") is not None:
        values["stochastic_combinations"] = tuple(
            tuple(str(level) for level in combination)
            for combination in values["stochastic_combinations"]
        )
    if values.get("stochastic_probabilities") is not None:
        values["stochastic_probabilities"] = tuple(
            float(value) for value in values["stochastic_probabilities"]
        )


def _validate_service_policy_groups(experiments: list[ExperimentSpec]) -> None:
    groups: dict[str, list[ExperimentSpec]] = {}
    for spec in experiments:
        group = _metadata_text(spec, "comparison_group")
        if group is not None:
            groups.setdefault(group, []).append(spec)

    for group, pair in groups.items():
        policies = {spec.model.objective_policy for spec in pair}
        if len(pair) != 2 or policies != {"penalty", "lexicographic"}:
            raise ValueError(
                f"Service-policy comparison group {group!r} must contain "
                "exactly one penalty run and one lexicographic run."
            )
        left, right = pair
        if _comparison_contract(left) != _comparison_contract(right):
            raise ValueError(
                f"Service-policy comparison group {group!r} changes settings "
                "other than objective_policy."
            )


def _comparison_contract(spec: ExperimentSpec) -> dict[str, Any]:
    model = asdict(spec.model)
    model.pop("objective_policy")
    return {
        "workbook": str(spec.workbook),
        "loader": asdict(spec.loader),
        "model": model,
        "solver": asdict(spec.solver),
        "calculate_evpi_vss": spec.calculate_evpi_vss,
        "max_estimated_variables": spec.max_estimated_variables,
    }


def _export_run_artifacts(
    *,
    spec: ExperimentSpec,
    data: ModelData,
    result: OptimizationResult,
    evpi_result: EVPIVSSResult | None,
    run_dir: Path,
    started: datetime,
    finished: datetime,
) -> None:
    payload = {
        "schema_version": 1,
        "experiment": _spec_payload(spec),
        "execution": {
            "started_at_utc": started.isoformat(),
            "finished_at_utc": finished.isoformat(),
            **_execution_context(),
        },
        "result": _result_payload(result),
        "stochastic_performance": _evpi_payload(evpi_result),
    }
    _write_json(run_dir / "result.json", payload)
    _write_json(
        run_dir / "model_audit.json",
        build_model_audit(data, spec.model, result),
    )
    _write_csv(run_dir / "warehouse_decisions.csv", result.warehouse_decisions)
    _write_csv(run_dir / "flows.csv", result.flows)
    _write_csv(run_dir / "inventories.csv", result.inventories)
    _write_csv(run_dir / "unmet_demand.csv", result.unmet_demand)
    _write_csv(run_dir / "emergency_capacity.csv", result.emergency_capacity)
    _write_csv(
        run_dir / "scenario_performance.csv",
        _scenario_performance_records(result),
    )

    storage = result.metrics.get("storage", {})
    _write_csv(run_dir / "storage_by_warehouse.csv", storage.get("warehouse_metrics", []))
    scenario_records = [
        {"scenario": scenario, **metrics}
        for scenario, metrics in storage.get("scenario_metrics", {}).items()
    ]
    _write_csv(run_dir / "storage_by_scenario.csv", scenario_records)
    if result.metadata.get("iis_computed") is not None:
        _write_json(
            run_dir / "infeasibility.json",
            {
                key: value
                for key, value in result.metadata.items()
                if key.startswith("iis_")
            },
        )


def _build_summary(
    *,
    spec: ExperimentSpec,
    result: OptimizationResult,
    evpi_result: EVPIVSSResult | None,
    run_dir: Path,
    started: datetime,
    finished: datetime,
) -> ExperimentRunSummary:
    (
        total_domestic_demand,
        served_domestic_demand,
        domestic_service_level,
    ) = _domestic_service_metrics(result)
    scenario_records = _scenario_performance_records(result)
    scenario_service_levels = [
        float(record["domestic_service_level"])
        for record in scenario_records
        if record.get("domestic_service_level") is not None
    ]
    objective_values = result.metrics.get("objective_values", {})
    gurobi_status_name = result.metadata.get("gurobi_status_name")
    return ExperimentRunSummary(
        name=spec.name,
        status=result.status,
        objective_policy=spec.model.objective_policy,
        comparison_group=_metadata_text(spec, "comparison_group"),
        campaign_gate=_metadata_text(spec, "campaign_gate"),
        scenario_count=(
            len(scenario_records) if scenario_records else 1
        ),
        objective_value=result.objective_value,
        economic_cost=_optional_float(objective_values.get("economic_cost")),
        penalized_cost=_optional_float(objective_values.get("penalized_cost")),
        runtime_seconds=result.runtime_seconds,
        peak_rss_mb=_peak_rss_mb(),
        mip_gap=result.mip_gap,
        dyn_cap=_optional_float(result.metrics.get("DynCap")),
        turnover=_optional_float(result.metrics.get("Turnover")),
        total_unmet_demand=_weighted_record_total(
            result, result.unmet_demand
        ),
        total_domestic_demand=total_domestic_demand,
        served_domestic_demand=served_domestic_demand,
        domestic_service_level=domestic_service_level,
        minimum_scenario_service_level=(
            min(scenario_service_levels) if scenario_service_levels else None
        ),
        maximum_scenario_service_level=(
            max(scenario_service_levels) if scenario_service_levels else None
        ),
        total_direct_flow=_weighted_record_total(
            result,
            result.flows,
            route_type="OC",
        ),
        emergency_static_capacity=_weighted_record_total(
            result,
            result.emergency_capacity,
            capacity_type="static",
        ),
        emergency_reception_capacity=_weighted_record_total(
            result,
            result.emergency_capacity,
            capacity_type="reception",
        ),
        total_emergency_capacity=_weighted_record_total(
            result, result.emergency_capacity
        ),
        evpi=evpi_result.evpi if evpi_result else None,
        vss=evpi_result.vss if evpi_result else None,
        output_dir=str(run_dir),
        started_at_utc=started.isoformat(),
        finished_at_utc=finished.isoformat(),
        slurm_job_id=os.environ.get("SLURM_JOB_ID"),
        slurm_array_task_id=os.environ.get("SLURM_ARRAY_TASK_ID"),
        error_type=(
            "GurobiTermination"
            if result.status == "error" and gurobi_status_name
            else None
        ),
        error_message=(
            f"Gurobi terminated with {gurobi_status_name} and no usable solution."
            if result.status == "error" and gurobi_status_name
            else None
        ),
    )


def _export_failed_run(
    spec: ExperimentSpec,
    output_root: Path,
    error: Exception,
    *,
    started: datetime,
) -> ExperimentRunSummary:
    finished = datetime.now(timezone.utc)
    run_dir = output_root / spec.name
    run_dir.mkdir(parents=True, exist_ok=True)
    summary = ExperimentRunSummary(
        name=spec.name,
        status="error",
        objective_policy=spec.model.objective_policy,
        comparison_group=_metadata_text(spec, "comparison_group"),
        campaign_gate=_metadata_text(spec, "campaign_gate"),
        scenario_count=_configured_scenario_count(spec),
        objective_value=None,
        economic_cost=None,
        penalized_cost=None,
        runtime_seconds=(finished - started).total_seconds(),
        peak_rss_mb=_peak_rss_mb(),
        mip_gap=None,
        dyn_cap=None,
        turnover=None,
        total_unmet_demand=None,
        total_domestic_demand=None,
        served_domestic_demand=None,
        domestic_service_level=None,
        minimum_scenario_service_level=None,
        maximum_scenario_service_level=None,
        total_direct_flow=None,
        emergency_static_capacity=None,
        emergency_reception_capacity=None,
        total_emergency_capacity=None,
        evpi=None,
        vss=None,
        output_dir=str(run_dir),
        started_at_utc=started.isoformat(),
        finished_at_utc=finished.isoformat(),
        slurm_job_id=os.environ.get("SLURM_JOB_ID"),
        slurm_array_task_id=os.environ.get("SLURM_ARRAY_TASK_ID"),
        error_type=type(error).__name__,
        error_message=str(error),
    )
    _write_json(run_dir / "run_summary.json", asdict(summary))
    return summary


def _spec_payload(spec: ExperimentSpec) -> dict[str, Any]:
    return {
        "name": spec.name,
        "workbook": str(spec.workbook),
        "workbook_sha256": _file_sha256(spec.workbook),
        "loader": asdict(spec.loader),
        "model": asdict(spec.model),
        "solver": asdict(spec.solver),
        "calculate_evpi_vss": spec.calculate_evpi_vss,
        "resume_evpi_vss": spec.resume_evpi_vss,
        "max_estimated_variables": spec.max_estimated_variables,
        "metadata": spec.metadata,
    }


def _result_payload(result: OptimizationResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "objective_value": result.objective_value,
        "solver_backend": result.solver_backend,
        "solver_name": result.solver_name,
        "model_mode": result.model_mode,
        "runtime_seconds": result.runtime_seconds,
        "mip_gap": result.mip_gap,
        "cost_breakdown": result.cost_breakdown,
        "warehouse_decisions": result.warehouse_decisions,
        "flows": result.flows,
        "inventories": result.inventories,
        "unmet_demand": result.unmet_demand,
        "emergency_capacity": result.emergency_capacity,
        "metrics": result.metrics,
        "metadata": result.metadata,
    }


def _evpi_payload(result: EVPIVSSResult | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "recourse_problem": result.recourse_problem,
        "wait_and_see": result.wait_and_see,
        "expected_value_problem": result.expected_value_problem,
        "expected_result_of_ev_solution": result.expected_result_of_ev_solution,
        "evpi": result.evpi,
        "vss": result.vss,
        "metadata": result.metadata,
    }


def _write_json(path: Path, payload: Any) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    _atomic_write_text(path, text + "\n")


def _write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    if not records:
        _atomic_write_text(path, "")
        return
    fieldnames = list(dict.fromkeys(key for record in records for key in record))
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for record in records:
        writer.writerow({key: _csv_value(record.get(key)) for key in fieldnames})
    _atomic_write_text(path, buffer.getvalue())


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="")
    temporary.replace(path)


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)


def _numeric_delta(left: Any, right: Any) -> float | None:
    if left is None or right is None:
        return None
    try:
        return float(left) - float(right)
    except (TypeError, ValueError):
        return None


def _ratio(numerator: Any, denominator: Any) -> float | None:
    if numerator is None or denominator is None:
        return None
    try:
        denominator_value = float(denominator)
        if denominator_value == 0.0:
            return None
        return float(numerator) / denominator_value
    except (TypeError, ValueError):
        return None


def _change_fraction(value: Any, baseline: Any) -> float | None:
    ratio = _ratio(value, baseline)
    return None if ratio is None else ratio - 1.0


def _reduction_fraction(baseline: Any, value: Any) -> float | None:
    change = _change_fraction(value, baseline)
    return None if change is None else -change


def _metadata_text(spec: ExperimentSpec, key: str) -> str | None:
    value = spec.metadata.get(key)
    return None if value is None else str(value)


def _configured_scenario_count(spec: ExperimentSpec) -> int | None:
    if spec.model.mode == "det":
        return 1
    if spec.loader.stochastic_combinations is not None:
        return len(spec.loader.stochastic_combinations)
    if spec.loader.scenario_generation_mode == "cartesian":
        return (
            len(spec.loader.stochastic_supply_levels)
            * len(spec.loader.stochastic_demand_levels)
        )
    return None


def _weighted_record_total(
    result: OptimizationResult,
    records: list[dict[str, Any]],
    **filters: Any,
) -> float | None:
    if not result.has_solution:
        return None

    probabilities = result.metadata.get("scenario_probabilities", {})
    scenario_metrics = result.metrics.get("scenario_metrics", {})
    total = 0.0
    for record in records:
        if any(record.get(key) != value for key, value in filters.items()):
            continue
        scenario = record.get("scenario")
        probability = 1.0
        if scenario is not None:
            probability = probabilities.get(
                scenario,
                scenario_metrics.get(scenario, {}).get("probability", 1.0),
            )
        total += float(record.get("value", 0.0)) * float(probability)
    return total


def _scenario_performance_records(
    result: OptimizationResult,
) -> list[dict[str, Any]]:
    """Build unweighted operational diagnostics for each stochastic scenario."""

    probabilities = result.metadata.get("scenario_probabilities", {})
    scenario_metrics = result.metrics.get("scenario_metrics", {})
    storage_metrics = result.metrics.get("storage", {}).get(
        "scenario_metrics",
        {},
    )
    record_scenarios = [
        record["scenario"]
        for records in (
            result.flows,
            result.unmet_demand,
            result.emergency_capacity,
        )
        for record in records
        if record.get("scenario") is not None
    ]
    if (
        result.model_mode != "sto"
        and not probabilities
        and not scenario_metrics
        and not record_scenarios
    ):
        return []
    scenarios = list(
        dict.fromkeys(
            [
                *probabilities,
                *scenario_metrics,
                *storage_metrics,
                *record_scenarios,
            ]
        )
    )

    records: list[dict[str, Any]] = []
    for scenario in scenarios:
        served = _scenario_record_total(
            result.flows,
            scenario,
            customer_type="domestic",
        )
        unmet = _scenario_record_total(result.unmet_demand, scenario)
        total_demand = served + unmet
        emergency_static = _scenario_record_total(
            result.emergency_capacity,
            scenario,
            capacity_type="static",
        )
        emergency_reception = _scenario_record_total(
            result.emergency_capacity,
            scenario,
            capacity_type="reception",
        )
        core = scenario_metrics.get(scenario, {})
        storage = storage_metrics.get(scenario, {})
        records.append(
            {
                "scenario": scenario,
                "probability": probabilities.get(
                    scenario,
                    core.get("probability"),
                ),
                "operating_cost": core.get("operating_cost"),
                "total_flow": core.get("total_flow"),
                "total_direct_flow": _scenario_record_total(
                    result.flows,
                    scenario,
                    route_type="OC",
                ),
                "total_domestic_demand": total_demand,
                "served_domestic_demand": served,
                "total_unmet_demand": unmet,
                "domestic_service_level": (
                    served / total_demand if total_demand > 0.0 else 1.0
                ),
                "emergency_static_capacity": emergency_static,
                "emergency_reception_capacity": emergency_reception,
                "total_emergency_capacity": (
                    emergency_static + emergency_reception
                ),
                "dynamic_capacity": storage.get("dynamic_capacity"),
                "turnover": storage.get("turnover"),
            }
        )
    return records


def _scenario_record_total(
    records: list[dict[str, Any]],
    scenario: Any,
    **filters: Any,
) -> float:
    return sum(
        float(record.get("value", 0.0))
        for record in records
        if record.get("scenario") == scenario
        and all(record.get(key) == value for key, value in filters.items())
    )


def _domestic_service_metrics(
    result: OptimizationResult,
) -> tuple[float | None, float | None, float | None]:
    if not result.has_solution:
        return None, None, None

    served = _weighted_record_total(
        result,
        result.flows,
        customer_type="domestic",
    )
    unmet = _weighted_record_total(result, result.unmet_demand)
    assert served is not None
    assert unmet is not None
    total = served + unmet
    service_level = served / total if total > 0.0 else 1.0
    return total, served, service_level


def _preflight_message(
    spec: ExperimentSpec,
    estimate: ModelSizeEstimate,
) -> str:
    return (
        f"[{spec.name}] preflight: scenarios={estimate.scenario_count}, "
        f"periods={estimate.period_count}, "
        f"routes(OD/DC/DD/OC)={estimate.routes_od}/{estimate.routes_dc}/"
        f"{estimate.routes_dd}/{estimate.routes_oc}, "
        f"estimated_variables={estimate.total_variables:,}"
    )


def _enforce_size_limit(
    spec: ExperimentSpec,
    estimate: ModelSizeEstimate,
) -> None:
    limit = spec.max_estimated_variables
    if limit is None or estimate.total_variables <= limit:
        return
    raise ValueError(
        f"Experiment {spec.name!r} is estimated to create "
        f"{estimate.total_variables:,} variables, above its safety limit of "
        f"{limit:,}. Apply route_filter_strategy='top_k' or 'pareto', reduce "
        "the scenario set, or explicitly set max_estimated_variables=null."
    )


def _execution_context() -> dict[str, Any]:
    return {
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python_version": sys.version,
        "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "slurm_array_job_id": os.environ.get("SLURM_ARRAY_JOB_ID"),
        "slurm_array_task_id": os.environ.get("SLURM_ARRAY_TASK_ID"),
    }


def _file_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _checkpoint_identity(spec: ExperimentSpec) -> str:
    """Bind resumable checkpoints to the workbook and complete run contract."""

    payload = _spec_payload(spec)
    payload.pop("resume_evpi_vss", None)
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _peak_rss_mb() -> float | None:
    """Return peak resident memory for the current process when available."""

    try:
        import resource
    except ImportError:
        return None

    peak = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    divisor = 1024.0 * 1024.0 if sys.platform == "darwin" else 1024.0
    return peak / divisor


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a mapping.")
    return dict(value)


def _resolve_path(value: Any, base_dir: Path) -> Path:
    path = Path(str(value))
    return path.resolve() if path.is_absolute() else (base_dir / path).resolve()
