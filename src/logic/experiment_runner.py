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
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

from src.logic.excel_loader import ExcelLoaderConfig, load_model_data_from_excel
from src.logic.metrics import attach_storage_metrics
from src.logic.model_config import ModelConfig, SolverConfig
from src.logic.model_data import ModelData
from src.logic.optimization import (
    EVPIVSSResult,
    OptimizationResult,
    calculate_evpi_vss,
    solve_model,
)


MANIFEST_VERSION = 1
SAFE_RUN_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass(slots=True)
class ExperimentSpec:
    """Complete, validated specification for one optimization experiment."""

    name: str
    workbook: Path
    loader: ExcelLoaderConfig = field(default_factory=ExcelLoaderConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    solver: SolverConfig = field(default_factory=SolverConfig)
    calculate_evpi_vss: bool = False
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
    objective_value: float | None
    runtime_seconds: float | None
    mip_gap: float | None
    dyn_cap: float | None
    turnover: float | None
    evpi: float | None
    vss: float | None
    output_dir: str
    started_at_utc: str
    finished_at_utc: str
    slurm_job_id: str | None = None
    slurm_array_task_id: str | None = None
    error_type: str | None = None
    error_message: str | None = None


Loader = Callable[[str | Path, ExcelLoaderConfig | None], ModelData]
Solver = Callable[..., OptimizationResult]
EVPICalculator = Callable[..., EVPIVSSResult]


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
) -> ExperimentRunSummary:
    """Execute one experiment and atomically export its structured artifacts."""

    started = datetime.now(timezone.utc)
    run_dir = Path(output_root).resolve() / spec.name
    run_dir.mkdir(parents=True, exist_ok=True)

    data = loader(spec.workbook, spec.loader)
    evpi_result: EVPIVSSResult | None = None
    if spec.calculate_evpi_vss:
        evpi_result = evpi_calculator(
            data=data,
            model_config=spec.model,
            solver_config=spec.solver,
        )
        result = evpi_result.recourse_problem_result
    else:
        result = solver(
            data=data,
            model_config=spec.model,
            solver_config=spec.solver,
        )

    if result.has_solution:
        attach_storage_metrics(data, result)

    finished = datetime.now(timezone.utc)
    _export_run_artifacts(
        spec=spec,
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
    return summary


def run_manifest(
    manifest: ExperimentManifest,
    *,
    indices: list[int] | None = None,
    output_root: str | Path | None = None,
    loader: Loader = load_model_data_from_excel,
    solver: Solver = solve_model,
    evpi_calculator: EVPICalculator = calculate_evpi_vss,
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
        try:
            summary = run_experiment(
                spec,
                root,
                loader=loader,
                solver=solver,
                evpi_calculator=evpi_calculator,
            )
        except Exception as error:
            summary = _export_failed_run(spec, root, error)
            summaries.append(summary)
            if not manifest.continue_on_error:
                raise
        else:
            summaries.append(summary)
    return summaries


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
    _write_csv(run_dir / "warehouse_decisions.csv", result.warehouse_decisions)
    _write_csv(run_dir / "flows.csv", result.flows)
    _write_csv(run_dir / "inventories.csv", result.inventories)
    _write_csv(run_dir / "unmet_demand.csv", result.unmet_demand)
    _write_csv(run_dir / "emergency_capacity.csv", result.emergency_capacity)

    storage = result.metrics.get("storage", {})
    _write_csv(run_dir / "storage_by_warehouse.csv", storage.get("warehouse_metrics", []))
    scenario_records = [
        {"scenario": scenario, **metrics}
        for scenario, metrics in storage.get("scenario_metrics", {}).items()
    ]
    _write_csv(run_dir / "storage_by_scenario.csv", scenario_records)


def _build_summary(
    *,
    spec: ExperimentSpec,
    result: OptimizationResult,
    evpi_result: EVPIVSSResult | None,
    run_dir: Path,
    started: datetime,
    finished: datetime,
) -> ExperimentRunSummary:
    return ExperimentRunSummary(
        name=spec.name,
        status=result.status,
        objective_value=result.objective_value,
        runtime_seconds=result.runtime_seconds,
        mip_gap=result.mip_gap,
        dyn_cap=_optional_float(result.metrics.get("DynCap")),
        turnover=_optional_float(result.metrics.get("Turnover")),
        evpi=evpi_result.evpi if evpi_result else None,
        vss=evpi_result.vss if evpi_result else None,
        output_dir=str(run_dir),
        started_at_utc=started.isoformat(),
        finished_at_utc=finished.isoformat(),
        slurm_job_id=os.environ.get("SLURM_JOB_ID"),
        slurm_array_task_id=os.environ.get("SLURM_ARRAY_TASK_ID"),
    )


def _export_failed_run(
    spec: ExperimentSpec,
    output_root: Path,
    error: Exception,
) -> ExperimentRunSummary:
    timestamp = datetime.now(timezone.utc).isoformat()
    run_dir = output_root / spec.name
    run_dir.mkdir(parents=True, exist_ok=True)
    summary = ExperimentRunSummary(
        name=spec.name,
        status="error",
        objective_value=None,
        runtime_seconds=None,
        mip_gap=None,
        dyn_cap=None,
        turnover=None,
        evpi=None,
        vss=None,
        output_dir=str(run_dir),
        started_at_utc=timestamp,
        finished_at_utc=timestamp,
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


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a mapping.")
    return dict(value)


def _resolve_path(value: Any, base_dir: Path) -> Path:
    path = Path(str(value))
    return path.resolve() if path.is_absolute() else (base_dir / path).resolve()

