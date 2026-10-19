"""Reproducible experiment execution and structured result export for HPC.

Separate data loading, primary optimization, post-optimality and artifact
processing. Solver status, independent residual checks and completed scientific
references are distinct observations. Completion markers bind closed artifacts
to the current identity; aggregation must not silently promote stale evidence.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import platform
import re
import site
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass, field, fields
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from time import perf_counter
from typing import Any

import yaml

from src.logic.excel_loader import ExcelLoaderConfig, load_model_data_from_excel
from src.logic.mathematical_contract import prepare_model_data
from src.logic.metrics import attach_storage_metrics
from src.logic.model_audit import build_model_audit
from src.logic.model_config import ModelConfig, SolverConfig
from src.logic.model_data import ModelData
from src.logic.optimization import OptimizationResult, solve_model
from src.logic.resource_telemetry import CURRENT, phase, resource_run
from src.logic.route_filtering import select_routes
from src.logic.run_integrity import implementation_identity, verify_completion, write_completion
from src.logic.solution_validation import validate_solution

MANIFEST_VERSION = 2
SAFE_RUN_NAME = re.compile("^[A-Za-z0-9][A-Za-z0-9._-]*$")
PENALTY_COST_COMPONENTS = frozenset({"unmet_demand", "emergency_static", "emergency_reception"})


@dataclass(slots=True)
class ExperimentSpec:
    """Complete, validated specification for one optimization experiment."""

    name: str
    workbook: Path
    loader: ExcelLoaderConfig = field(default_factory=ExcelLoaderConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    solver: SolverConfig = field(default_factory=SolverConfig)
    max_estimated_variables: int | None = 2000000
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not SAFE_RUN_NAME.fullmatch(self.name):
            raise ValueError(
                "Experiment name must start with an alphanumeric character and "
                "contain only letters, numbers, '.', '_', or '-'."
            )
        if self.model.mode == "sto" and (not self.loader.include_stochastic_scenarios):
            raise ValueError(
                "Stochastic experiments require loader.include_stochastic_scenarios=true."
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
    objective_bound: float | None
    economic_cost: float | None
    penalized_cost: float | None
    runtime_seconds: float | None
    data_read_seconds: float | None
    model_build_seconds: float | None
    optimization_seconds: float | None
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
    capacity_adequacy_status: str | None
    material_balance_ok: bool | None
    penalty_cost_share: float | None
    output_dir: str
    started_at_utc: str
    finished_at_utc: str
    slurm_job_id: str | None = None
    slurm_array_task_id: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    independent_validation_status: str | None = None
    end_to_end_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class ModelSizeEstimate:
    """Pre-solve route and variable counts used by the HPC safety guard."""

    scenario_count: int
    period_count: int
    routes_od: int
    routes_dc: int
    routes_dd: int
    routes_oc: int
    base_routes_od: int
    base_routes_dc: int
    base_routes_dd: int
    base_routes_oc: int
    repair_routes_od: int
    repair_routes_dc: int
    repair_routes_dd: int
    repair_routes_oc: int
    flow_variables: int
    inventory_variables: int
    unmet_demand_variables: int
    emergency_capacity_variables: int
    investment_variables: int
    total_variables: int


Loader = Callable[[str | Path, ExcelLoaderConfig | None], ModelData]
Solver = Callable[..., OptimizationResult]
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
            f"Unsupported manifest version {raw.get('version')!r}; expected {MANIFEST_VERSION}."
        )
    defaults = _mapping(raw.get("defaults", {}), "defaults")
    raw_experiments = raw.get("experiments")
    if not isinstance(raw_experiments, list) or not raw_experiments:
        raise ValueError("Manifest must define a non-empty experiments list.")
    experiments = [
        _parse_experiment(item, defaults, manifest_path.parent) for item in raw_experiments
    ]
    names = [experiment.name for experiment in experiments]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise ValueError(f"Experiment names must be unique; duplicates: {duplicates}.")
    output_dir = _resolve_path(raw.get("output_dir", "data/results/hpc"), manifest_path.parent)
    return ExperimentManifest(
        experiments=experiments,
        output_dir=output_dir,
        continue_on_error=bool(raw.get("continue_on_error", False)),
        source_path=manifest_path,
    )


@resource_run
def run_experiment(
    spec: ExperimentSpec,
    output_root: str | Path,
    *,
    loader: Loader = load_model_data_from_excel,
    solver: Solver = solve_model,
    progress: Progress = print,
) -> ExperimentRunSummary:
    """Execute one experiment and atomically export its structured artifacts."""
    started = datetime.now(UTC)
    wall_started = perf_counter()
    run_dir = Path(output_root).resolve() / spec.name
    run_dir.mkdir(parents=True, exist_ok=True)
    identity = _checkpoint_identity(spec)
    _write_json(run_dir / "run_completion.json", {"status": "running", "run_identity": identity})
    progress(f"[{spec.name}] loading {spec.workbook}")
    phase("data_read")
    data_read_started_at = perf_counter()
    data = loader(spec.workbook, spec.loader)
    data_read_seconds = perf_counter() - data_read_started_at
    data = prepare_model_data(data, spec.model)
    if spec.model.interhub_strong_connectivity:
        from src.logic.interhub_connectivity import write_interhub_audit

        write_interhub_audit(data.metadata["interhub_connectivity"], run_dir)
    _write_json(run_dir / "model_audit.json", build_model_audit(data, spec.model))
    estimate = estimate_model_size(data, spec.model)
    _write_json(run_dir / "preflight.json", _preflight_payload(spec, data, estimate))
    progress(_preflight_message(spec, estimate))
    _enforce_size_limit(spec, estimate)
    solve_started = perf_counter()
    progress(f"[{spec.name}] building and solving model")
    result = solver(data=data, model_config=spec.model, solver_config=spec.solver)
    timings = result.metadata.setdefault("timings", {})
    timings["data_read_seconds"] = data_read_seconds
    timings["solve_sequence_wall_seconds"] = perf_counter() - solve_started
    result.metadata["run_identity"] = identity
    result.metadata["implementation_identity"] = implementation_identity()
    result.metadata["mathematical_contract"] = data.metadata["mathematical_contract"]
    validation_started = perf_counter()
    phase("independent_validation")
    independent = validate_solution(data, spec.model, result)
    timings["independent_validation_seconds"] = perf_counter() - validation_started
    result.metadata["independent_validation_status"] = independent["status"]
    _write_json(run_dir / "independent_validation.json", independent)
    if result.has_solution:
        progress(f"[{spec.name}] calculating DynCap and Turnover")
        attach_storage_metrics(data, result)
    finished = datetime.now(UTC)
    progress(f"[{spec.name}] exporting structured artifacts")
    export_started = perf_counter()
    phase("artifact_export")
    audit = _export_run_artifacts(
        spec=spec, data=data, result=result, run_dir=run_dir, started=started, finished=finished
    )
    timings["artifact_export_seconds"] = perf_counter() - export_started
    timings["end_to_end_seconds"] = perf_counter() - wall_started
    finished = datetime.now(UTC)
    payload = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    payload["result"]["metadata"] = result.metadata
    payload["execution"]["finished_at_utc"] = finished.isoformat()
    _write_json(run_dir / "result.json", payload)
    summary = _build_summary(
        spec=spec, result=result, run_dir=run_dir, started=started, finished=finished, audit=audit
    )
    summary.independent_validation_status = independent["status"]
    summary.end_to_end_seconds = timings["end_to_end_seconds"]
    _write_json(run_dir / "run_summary.json", asdict(summary))
    if (resource_session := CURRENT.get()) is not None:
        resource_session.finish(summary.status)
    artifacts = sorted(
        p for p in run_dir.rglob("*") if p.is_file() and p.name != "run_completion.json"
    )
    write_completion(run_dir, identity, artifacts)
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
    if run_dir.exists():
        raise FileExistsError("Preserve existing evidence; choose a fresh inspection directory.")
    progress(f"[{spec.name}] loading {spec.workbook}")
    data = loader(spec.workbook, spec.loader)
    data = prepare_model_data(data, spec.model)
    if spec.model.interhub_strong_connectivity:
        from src.logic.interhub_connectivity import write_interhub_audit

        write_interhub_audit(data.metadata["interhub_connectivity"], run_dir)
    _write_json(run_dir / "model_audit.json", build_model_audit(data, spec.model))
    estimate = estimate_model_size(data, spec.model)
    _write_json(run_dir / "preflight.json", _preflight_payload(spec, data, estimate))
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
    if payload.get("schema_version") != 2:
        raise ValueError("Historical result schema cannot be relabeled as a scalar re-audit.")
    experiment_payload = payload.get("experiment", {})
    expected_payload = json.loads(json.dumps(_spec_payload(spec)))
    mismatches = [
        key
        for key in ("workbook_sha256", "loader", "model")
        if experiment_payload.get(key) != expected_payload.get(key)
    ]
    if mismatches:
        raise ValueError(
            "Existing result is incompatible with the selected experiment for: "
            f"{', '.join(mismatches)}."
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
    saved_identity = result.metadata.get("run_identity")
    if saved_identity and saved_identity != _checkpoint_identity(spec):
        raise ValueError("Existing result uses a different implementation or execution contract.")
    progress(f"[{spec.name}] loading {spec.workbook}")
    data = loader(spec.workbook, spec.loader)
    if saved_identity:
        data = prepare_model_data(data, spec.model)
    from uuid import uuid4

    audit_dir = run_dir / ("scalar_reaudit_" + uuid4().hex)
    audit_dir.mkdir(exist_ok=False)
    audit_path = audit_dir / "model_audit.json"
    _write_json(audit_path, build_model_audit(data, spec.model, result))
    retrospective = validate_solution(prepare_model_data(data, spec.model), spec.model, result)
    retrospective["qualification"] = (
        "Retrospective check against the selected current contract; "
        "original solve provenance is retained. "
        "This does not create a current-run completion certificate."
    )
    retrospective["original_result_sha256"] = _file_sha256(result_path)
    _write_json(audit_dir / "independent_validation_reaudit.json", retrospective)
    progress(f"[{spec.name}] audit -> {audit_path}")
    return audit_path


def estimate_model_size(data: ModelData, config: ModelConfig) -> ModelSizeEstimate:
    """Estimate variables created by the native deterministic/extensive form."""
    routes = select_routes(data, config)
    scenarios = len(data.scenarios) if config.mode == "sto" else 1
    periods = len(data.periods)
    flow_variables = (
        scenarios * periods * (len(routes.od) + len(routes.dc) + len(routes.dd) + len(routes.oc))
    )
    inventory_variables = scenarios * len(data.warehouses) * len(data.products) * periods
    unmet_variables = scenarios * len(data.domestic_customers) * len(data.products) * periods
    emergency_variables = scenarios * len(data.warehouses) * periods * 2
    expansion_count = sum(
        config.allow_capacity_expansion and data.max_expand_capacity.get(warehouse, 0.0) > 0.0
        for warehouse in data.existing_warehouses
    )
    bulk_count = sum(
        config.allow_bulkification and data.max_bulk_capacity.get(warehouse, 0.0) > 0.0
        for warehouse in data.bulk_eligible_warehouses
    )
    investment_variables = 2 * (len(data.candidate_warehouses) + expansion_count + bulk_count)
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
        base_routes_od=len(routes.od) - len(routes.repair_od),
        base_routes_dc=len(routes.dc) - len(routes.repair_dc),
        base_routes_dd=len(routes.dd) - len(routes.repair_dd),
        base_routes_oc=len(routes.oc) - len(routes.repair_oc),
        repair_routes_od=len(routes.repair_od),
        repair_routes_dc=len(routes.repair_dc),
        repair_routes_dd=len(routes.repair_dd),
        repair_routes_oc=len(routes.repair_oc),
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
    progress: Progress = print,
) -> list[ExperimentRunSummary]:
    """Execute all or selected manifest entries, optionally continuing on errors."""
    selected = indices if indices is not None else list(range(len(manifest.experiments)))
    invalid = [index for index in selected if index < 0 or index >= len(manifest.experiments)]
    if invalid:
        raise IndexError(
            f"Experiment indices out of range: {invalid}; "
            f"valid range is 0..{len(manifest.experiments) - 1}."
        )
    root = Path(output_root).resolve() if output_root else manifest.output_dir
    summaries: list[ExperimentRunSummary] = []
    for index in selected:
        spec = manifest.experiments[index]
        if (root / spec.name).exists():
            raise FileExistsError("Preserve existing run; no retry or overwrite is admitted.")
        run_started = datetime.now(UTC)
        try:
            summary = run_experiment(spec, root, loader=loader, solver=solver, progress=progress)
        except Exception as error:
            summary = _export_failed_run(spec, root, error, started=run_started)
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
            f"Experiment indices out of range: {invalid}; "
            f"valid range is 0..{len(manifest.experiments) - 1}."
        )
    root = Path(output_root).resolve() if output_root else manifest.output_dir
    return [
        inspect_experiment(manifest.experiments[index], root, loader=loader, progress=progress)
        for index in selected
    ]


def _aggregation_eligibility(root, manifest):
    if manifest is None:
        return None
    accepted, records = (set(), [])
    expected = {spec.name: spec for spec in manifest.experiments}
    for path in sorted(root.glob("*/run_summary.json")):
        name = path.parent.name
        if name not in expected:
            valid, reason = (False, "not_in_selected_manifest")
        else:
            valid, reason = verify_completion(path.parent, _checkpoint_identity(expected[name]))
        records.append({"name": name, "included": valid, "reason": reason})
        if valid:
            accepted.add(name)
    _write_json(
        root / "aggregation_audit.json",
        {
            "schema_version": 1,
            "mode": "current_contract_only",
            "runs": records,
            "excluded_count": sum(not row["included"] for row in records),
        },
    )
    return accepted


def aggregate_experiment_summaries(
    output_root: str | Path, *, manifest: ExperimentManifest | None = None
) -> Path:
    """Combine per-run summaries after local or Slurm-array execution."""
    root = Path(output_root).resolve()
    records: list[dict[str, Any]] = []
    eligibility = _aggregation_eligibility(root, manifest)
    for path in sorted(root.glob("*/run_summary.json")):
        if eligibility is not None and path.parent.name not in eligibility:
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            records.append(payload)
    target = root / "batch_summary.csv"
    _write_csv(target, records)
    return target


def _parse_experiment(raw: Any, defaults: dict[str, Any], base_dir: Path) -> ExperimentSpec:
    item = _mapping(raw, "experiment")
    allowed = {
        "name",
        "workbook",
        "loader",
        "model",
        "solver",
        "max_estimated_variables",
        "metadata",
    }
    if set(item) - allowed or set(defaults) - (allowed - {"name", "workbook"}):
        raise ValueError("Unsupported or archived experiment fields; use the scalar v2 contract.")
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
            max_estimated_variables=_optional_int(
                item.get(
                    "max_estimated_variables", defaults.get("max_estimated_variables", 2000000)
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


def _export_run_artifacts(
    *,
    spec: ExperimentSpec,
    data: ModelData,
    result: OptimizationResult,
    run_dir: Path,
    started: datetime,
    finished: datetime,
) -> dict[str, Any]:
    payload = {
        "schema_version": 2,
        "experiment": _spec_payload(spec),
        "execution": {
            "started_at_utc": started.isoformat(),
            "finished_at_utc": finished.isoformat(),
            **_execution_context(),
        },
        "result": _result_payload(result),
    }
    _write_json(run_dir / "result.json", payload)
    audit = build_model_audit(data, spec.model, result)
    _write_json(run_dir / "model_audit.json", audit)
    _write_csv(run_dir / "warehouse_decisions.csv", result.warehouse_decisions)
    _write_csv(run_dir / "flows.csv", result.flows)
    _write_csv(run_dir / "inventories.csv", result.inventories)
    _write_csv(run_dir / "unmet_demand.csv", result.unmet_demand)
    _write_csv(run_dir / "emergency_capacity.csv", result.emergency_capacity)
    _write_csv(run_dir / "scenario_performance.csv", _scenario_performance_records(result))
    solution_audit = audit.get("solution", {})
    _write_csv(
        run_dir / "material_balance_by_scenario.csv",
        solution_audit.get("material_balance", {}).get("by_scenario", []),
    )
    _write_csv(
        run_dir / "capacity_gap_by_scenario.csv",
        solution_audit.get("capacity_adequacy", {}).get("by_scenario", []),
    )
    _write_csv(
        run_dir / "investment_saturation.csv",
        [
            {"investment_type": investment_type, **values}
            for investment_type, values in solution_audit.get("investment_saturation", {}).items()
        ],
    )
    _write_csv(
        run_dir / "emergency_capacity_daily.csv",
        _emergency_capacity_daily_records(result, spec.model),
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
            {key: value for key, value in result.metadata.items() if key.startswith("iis_")},
        )
    return audit


def _build_summary(
    *,
    spec: ExperimentSpec,
    result: OptimizationResult,
    run_dir: Path,
    started: datetime,
    finished: datetime,
    audit: dict[str, Any],
) -> ExperimentRunSummary:
    total_domestic_demand, served_domestic_demand, domestic_service_level = (
        _domestic_service_metrics(result)
    )
    scenario_records = _scenario_performance_records(result)
    scenario_service_levels = [
        float(record["domestic_service_level"])
        for record in scenario_records
        if record.get("domestic_service_level") is not None
    ]
    objective_values = result.metrics.get("objective_values", {})
    timings = result.metadata.get("timings", {})
    gurobi_status_name = result.metadata.get("gurobi_status_name")
    solution_audit = audit.get("solution", {})
    material_balance = solution_audit.get("material_balance", {})
    capacity_adequacy = solution_audit.get("capacity_adequacy", {})
    cost_shares = solution_audit.get("cost_component_shares", {})
    penalty_cost_share = sum(
        float(cost_shares.get(component) or 0.0) for component in PENALTY_COST_COMPONENTS
    )
    return ExperimentRunSummary(
        name=spec.name,
        status=result.status,
        objective_policy=spec.model.objective_policy,
        comparison_group=_metadata_text(spec, "comparison_group"),
        campaign_gate=_metadata_text(spec, "campaign_gate"),
        scenario_count=len(scenario_records) if scenario_records else 1,
        objective_value=result.objective_value,
        objective_bound=_optional_float(
            result.metadata.get("objective_bound", result.metadata.get("gurobi_objective_bound"))
        ),
        economic_cost=_optional_float(objective_values.get("economic_cost")),
        penalized_cost=_optional_float(objective_values.get("penalized_cost")),
        runtime_seconds=result.runtime_seconds,
        data_read_seconds=_optional_float(timings.get("data_read_seconds")),
        model_build_seconds=_optional_float(timings.get("model_build_seconds")),
        optimization_seconds=_optional_float(timings.get("optimization_seconds")),
        peak_rss_mb=_peak_rss_mb(),
        mip_gap=result.mip_gap,
        dyn_cap=_optional_float(result.metrics.get("DynCap")),
        turnover=_optional_float(result.metrics.get("Turnover")),
        total_unmet_demand=_weighted_record_total(result, result.unmet_demand),
        total_domestic_demand=total_domestic_demand,
        served_domestic_demand=served_domestic_demand,
        domestic_service_level=domestic_service_level,
        minimum_scenario_service_level=min(scenario_service_levels)
        if scenario_service_levels
        else None,
        maximum_scenario_service_level=max(scenario_service_levels)
        if scenario_service_levels
        else None,
        total_direct_flow=_weighted_record_total(result, result.flows, route_type="OC"),
        emergency_static_capacity=_weighted_record_total(
            result, result.emergency_capacity, capacity_type="static"
        ),
        emergency_reception_capacity=_weighted_record_total(
            result, result.emergency_capacity, capacity_type="reception"
        ),
        total_emergency_capacity=_weighted_record_total(result, result.emergency_capacity),
        capacity_adequacy_status=capacity_adequacy.get("status"),
        material_balance_ok=material_balance.get("all_within_tolerance"),
        penalty_cost_share=penalty_cost_share,
        output_dir=str(run_dir),
        started_at_utc=started.isoformat(),
        finished_at_utc=finished.isoformat(),
        slurm_job_id=os.environ.get("SLURM_JOB_ID"),
        slurm_array_task_id=os.environ.get("SLURM_ARRAY_TASK_ID"),
        error_type="GurobiTermination" if result.status == "error" and gurobi_status_name else None,
        error_message=f"Gurobi terminated with {gurobi_status_name} and no usable solution."
        if result.status == "error" and gurobi_status_name
        else None,
    )


def _export_failed_run(
    spec: ExperimentSpec, output_root: Path, error: Exception, *, started: datetime
) -> ExperimentRunSummary:
    finished = datetime.now(UTC)
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
        objective_bound=None,
        economic_cost=None,
        penalized_cost=None,
        runtime_seconds=(finished - started).total_seconds(),
        data_read_seconds=None,
        model_build_seconds=None,
        optimization_seconds=None,
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
        capacity_adequacy_status=None,
        material_balance_ok=None,
        penalty_cost_share=None,
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
        "max_estimated_variables": spec.max_estimated_variables,
        "metadata": spec.metadata,
    }


def _result_payload(result: OptimizationResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "objective_value": result.objective_value,
        "objective_bound": result.metadata.get(
            "objective_bound", result.metadata.get("gurobi_objective_bound")
        ),
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


def _metadata_text(spec: ExperimentSpec, key: str) -> str | None:
    value = spec.metadata.get(key)
    return None if value is None else str(value)


def _configured_scenario_count(spec: ExperimentSpec) -> int | None:
    if spec.model.mode == "det":
        return 1
    if spec.loader.stochastic_combinations is not None:
        return len(spec.loader.stochastic_combinations)
    if spec.loader.scenario_generation_mode == "cartesian":
        return len(spec.loader.stochastic_supply_levels) * len(spec.loader.stochastic_demand_levels)
    return None


def _weighted_record_total(
    result: OptimizationResult, records: list[dict[str, Any]], **filters: Any
) -> float | None:
    if not result.has_solution:
        return None
    probabilities = result.metadata.get("scenario_probabilities", {})
    scenario_metrics = result.metrics.get("scenario_metrics", {})
    total = 0.0
    for record in records:
        if any((record.get(key) != value for key, value in filters.items())):
            continue
        scenario = record.get("scenario")
        probability = 1.0
        if scenario is not None:
            probability = probabilities.get(
                scenario, scenario_metrics.get(scenario, {}).get("probability", 1.0)
            )
        total += float(record.get("value", 0.0)) * float(probability)
    return total


def _emergency_capacity_daily_records(
    result: OptimizationResult, config: ModelConfig
) -> list[dict[str, Any]]:
    """Add period length and daily-equivalent values to emergency records."""
    records: list[dict[str, Any]] = []
    for record in result.emergency_capacity:
        period = str(record.get("period"))
        days = float(config.operating_days(period))
        value = float(record.get("value", 0.0))
        records.append(
            {
                **record,
                "days_in_period": days,
                "value_tons_per_day": value / days
                if record.get("capacity_type") == "reception" and days > 0.0
                else None,
            }
        )
    return records


def _scenario_performance_records(result: OptimizationResult) -> list[dict[str, Any]]:
    """Build unweighted operational diagnostics for each stochastic scenario."""
    probabilities = result.metadata.get("scenario_probabilities", {})
    scenario_metrics = result.metrics.get("scenario_metrics", {})
    storage_metrics = result.metrics.get("storage", {}).get("scenario_metrics", {})
    record_scenarios = [
        record["scenario"]
        for records in (result.flows, result.unmet_demand, result.emergency_capacity)
        for record in records
        if record.get("scenario") is not None
    ]
    if (
        result.model_mode != "sto"
        and (not probabilities)
        and (not scenario_metrics)
        and (not record_scenarios)
    ):
        return []
    scenarios = list(
        dict.fromkeys([*probabilities, *scenario_metrics, *storage_metrics, *record_scenarios])
    )
    records: list[dict[str, Any]] = []
    for scenario in scenarios:
        served = _scenario_record_total(result.flows, scenario, customer_type="domestic")
        unmet = _scenario_record_total(result.unmet_demand, scenario)
        total_demand = served + unmet
        emergency_static = _scenario_record_total(
            result.emergency_capacity, scenario, capacity_type="static"
        )
        emergency_reception = _scenario_record_total(
            result.emergency_capacity, scenario, capacity_type="reception"
        )
        core = scenario_metrics.get(scenario, {})
        storage = storage_metrics.get(scenario, {})
        records.append(
            {
                "scenario": scenario,
                "probability": probabilities.get(scenario, core.get("probability")),
                "operating_cost": core.get("operating_cost"),
                "total_flow": core.get("total_flow"),
                "total_direct_flow": _scenario_record_total(
                    result.flows, scenario, route_type="OC"
                ),
                "total_domestic_demand": total_demand,
                "served_domestic_demand": served,
                "total_unmet_demand": unmet,
                "domestic_service_level": served / total_demand if total_demand > 0.0 else 1.0,
                "emergency_static_capacity": emergency_static,
                "emergency_reception_capacity": emergency_reception,
                "total_emergency_capacity": emergency_static + emergency_reception,
                "dynamic_capacity": storage.get("dynamic_capacity"),
                "turnover": storage.get("turnover"),
            }
        )
    return records


def _scenario_record_total(records: list[dict[str, Any]], scenario: Any, **filters: Any) -> float:
    return sum(
        float(record.get("value", 0.0))
        for record in records
        if record.get("scenario") == scenario
        and all((record.get(key) == value for key, value in filters.items()))
    )


def _domestic_service_metrics(
    result: OptimizationResult,
) -> tuple[float | None, float | None, float | None]:
    if not result.has_solution:
        return (None, None, None)
    served = _weighted_record_total(result, result.flows, customer_type="domestic")
    unmet = _weighted_record_total(result, result.unmet_demand)
    assert served is not None
    assert unmet is not None
    total = served + unmet
    service_level = served / total if total > 0.0 else 1.0
    return (total, served, service_level)


def _preflight_message(spec: ExperimentSpec, estimate: ModelSizeEstimate) -> str:
    return (
        f"[{spec.name}] preflight: scenarios={estimate.scenario_count}, "
        f"periods={estimate.period_count}, "
        f"routes(OD/DC/DD/OC)={estimate.routes_od}/{estimate.routes_dc}/"
        f"{estimate.routes_dd}/{estimate.routes_oc}, "
        f"repairs(OD/DC/DD/OC)={estimate.repair_routes_od}/{estimate.repair_routes_dc}/"
        f"{estimate.repair_routes_dd}/{estimate.repair_routes_oc}, "
        f"estimated_variables={estimate.total_variables:,}"
    )


def _preflight_payload(
    spec: ExperimentSpec, data: ModelData, estimate: ModelSizeEstimate
) -> dict[str, Any]:
    """Build a human-auditable fingerprint without changing size fields."""
    return {
        **asdict(estimate),
        "schema_version": 1,
        "workbook_sha256": _file_sha256(spec.workbook),
        "data_signature": _data_signature(data),
        "execution": _execution_context(),
    }


def _data_signature(data: ModelData) -> dict[str, Any]:
    stochastic_totals = {
        scenario: {
            "supply": sum(
                (
                    value
                    for (record_scenario, *_), value in data.supply_s.items()
                    if record_scenario == scenario
                )
            ),
            "domestic_demand": sum(
                (
                    value
                    for (record_scenario, *_), value in data.demand_dom_s.items()
                    if record_scenario == scenario
                )
            ),
            "export_upper_bound": sum(
                (
                    value
                    for (record_scenario, *_), value in data.demand_exp_s.items()
                    if record_scenario == scenario
                )
            ),
        }
        for scenario in data.scenarios
    }
    return {
        "counts": {
            "origins": len(data.origins),
            "warehouses": len(data.warehouses),
            "existing_warehouses": len(data.existing_warehouses),
            "candidate_warehouses": len(data.candidate_warehouses),
            "domestic_customers": len(data.domestic_customers),
            "export_customers": len(data.export_customers),
            "products": len(data.products),
            "periods": len(data.periods),
            "scenarios": len(data.scenarios),
        },
        "deterministic_totals": {
            "supply": sum(data.supply.values()),
            "domestic_demand": sum(data.demand_dom.values()),
            "export_upper_bound": sum(data.demand_exp.values()),
        },
        "stochastic_totals_by_scenario": stochastic_totals,
        "loader_warning_count": len(data.metadata.get("loader_warnings", [])),
    }


def _enforce_size_limit(spec: ExperimentSpec, estimate: ModelSizeEstimate) -> None:
    limit = spec.max_estimated_variables
    if limit is None or estimate.total_variables <= limit:
        return
    raise ValueError(
        f"Experiment {spec.name!r} is estimated to create {estimate.total_variables:,} "
        f"variables, above its safety limit of {limit:,}. "
        "Review the size and input contract before explicit admission; "
        "do not silently change routes, scenarios or the safety guard."
    )


def _execution_context() -> dict[str, Any]:
    return {
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python_version": sys.version,
        "python_executable": sys.executable,
        "python_prefix": sys.prefix,
        "python_no_user_site": os.environ.get("PYTHONNOUSERSITE"),
        "user_site_enabled": site.ENABLE_USER_SITE,
        "package_versions": {
            distribution: _installed_version(distribution)
            for distribution in (
                "model-agrologistic",
                "numpy",
                "pandas",
                "openpyxl",
                "gurobipy",
                "PyYAML",
            )
        },
        "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "slurm_array_job_id": os.environ.get("SLURM_ARRAY_JOB_ID"),
        "slurm_array_task_id": os.environ.get("SLURM_ARRAY_TASK_ID"),
        "slurm_partition": os.environ.get("SLURM_JOB_PARTITION"),
        "slurm_cpus_per_task": os.environ.get("SLURM_CPUS_PER_TASK"),
        "slurm_mem_per_node_mb": os.environ.get("SLURM_MEM_PER_NODE"),
        "source_commit_declared": os.environ.get("AGROLOGISTIC_SOURCE_COMMIT"),
        "source_commit_authority": "submission_environment_not_independently_verified",
        "memory_measurement_scope": "process_lifetime_high_water_mark",
    }


def _installed_version(distribution: str) -> str | None:
    try:
        return version(distribution)
    except PackageNotFoundError:
        return None


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
    payload["implementation"] = implementation_identity()["sha256"]
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
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
