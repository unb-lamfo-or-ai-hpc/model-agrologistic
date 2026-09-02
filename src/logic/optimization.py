"""
Optimization facade for agricultural logistics models.

This module provides the public entry point for solving ModelData instances.
It dispatches the optimization run to the selected backend:

- gurobipy: native Gurobi implementation;
- pyomo: solver-neutral implementation, including SCIP.

The facade is responsible for:
- validating ModelData before solving;
- selecting the backend;
- returning a common OptimizationResult object.

It must not build solver-specific models directly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal

from src.logic.model_config import ModelConfig, RunConfig, SolverConfig
from src.logic.model_data import ModelData
from src.logic.model_validation import validate_or_raise_model_data


OptimizationStatus = Literal[
    "optimal",
    "feasible",
    "infeasible",
    "unbounded",
    "time_limit",
    "not_implemented",
    "error",
]

DEFAULT_GUROBI_LICENSE_FILE = "/secrets/gurobi.lic"
PROJECT_GUROBI_LICENSE_RELATIVE_PATH = Path("secrets/gurobi.lic")
GUROBI_SOLVER_NAMES = {"gurobi", "gurobipy"}


def uses_gurobi(solver_config: SolverConfig) -> bool:
    """
    Return True if the selected backend/solver requires Gurobi.

    This covers both:
    - native gurobipy backend;
    - Pyomo using Gurobi as solver.
    """

    return (
        solver_config.backend == "gurobipy"
        or solver_config.solver_name.lower() in GUROBI_SOLVER_NAMES
    )


def configure_gurobi_wls_license(solver_config: SolverConfig) -> str | None:
    """
    Configure the Gurobi WLS license file location.

    Priority order:
    1. solver_config.solver_options["GRB_LICENSE_FILE"];
    2. solver_config.solver_options["license_file"];
    3. existing GRB_LICENSE_FILE environment variable;
    4. default HPC secret path: /secrets/gurobi.lic;
    5. secrets/gurobi.lic relative to the working directory or project root.

    Returns
    -------
    str | None
        The configured license path, or None if no license file was found.
    """

    explicit_license_file = (
        solver_config.solver_options.get("GRB_LICENSE_FILE")
        or solver_config.solver_options.get("license_file")
    )

    if explicit_license_file:
        license_path = str(explicit_license_file)
        os.environ["GRB_LICENSE_FILE"] = license_path
        return license_path

    existing_license_file = os.environ.get("GRB_LICENSE_FILE")
    if existing_license_file:
        return existing_license_file

    project_root = Path(__file__).resolve().parents[2]
    default_candidates = (
        Path(DEFAULT_GUROBI_LICENSE_FILE),
        Path.cwd() / PROJECT_GUROBI_LICENSE_RELATIVE_PATH,
        project_root / PROJECT_GUROBI_LICENSE_RELATIVE_PATH,
    )

    for candidate in default_candidates:
        if not candidate.is_file():
            continue

        license_path = str(candidate.resolve())
        os.environ["GRB_LICENSE_FILE"] = license_path
        return license_path

    return None


class OptimizationBackendNotImplementedError(NotImplementedError):
    """Raised when a selected optimization backend is not implemented yet."""


@dataclass(slots=True)
class OptimizationResult:
    """
    Common result object returned by all optimization backends.

    The goal is to make downstream code independent of whether the model
    was solved by gurobipy or Pyomo.
    """

    status: OptimizationStatus

    objective_value: float | None = None
    solver_backend: str | None = None
    solver_name: str | None = None
    model_mode: str | None = None

    runtime_seconds: float | None = None
    mip_gap: float | None = None

    # Structured outputs for post-processing, HPC, and GNN export.
    cost_breakdown: dict[str, float] = field(default_factory=dict)
    warehouse_decisions: list[dict[str, Any]] = field(default_factory=list)
    flows: list[dict[str, Any]] = field(default_factory=list)
    inventories: list[dict[str, Any]] = field(default_factory=list)
    unmet_demand: list[dict[str, Any]] = field(default_factory=list)
    emergency_capacity: list[dict[str, Any]] = field(default_factory=list)

    # KPIs: DynCap, Turnover, EVPI, VSS, scenario metrics, etc.
    metrics: dict[str, Any] = field(default_factory=dict)

    # Backend-specific payload. This should not be required by normal users,
    # but it is useful for debugging and solver-level analysis.
    raw_solver_result: Any | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def has_solution(self) -> bool:
        """Return True if the result contains a usable feasible solution."""
        return self.status in {"optimal", "feasible", "time_limit"}


@dataclass(slots=True)
class EVPIVSSResult:
    """Economic value metrics and the optimization runs used to compute them."""

    recourse_problem: float
    wait_and_see: float
    expected_value_problem: float
    expected_result_of_ev_solution: float
    evpi: float
    vss: float

    recourse_problem_result: OptimizationResult
    wait_and_see_results: dict[str, OptimizationResult]
    expected_value_problem_result: OptimizationResult
    expected_result_result: OptimizationResult

    metadata: dict[str, Any] = field(default_factory=dict)


def solve_model(
    data: ModelData,
    model_config: ModelConfig | None = None,
    solver_config: SolverConfig | None = None,
    *,
    run_config: RunConfig | None = None,
    validate: bool = True,
    require_distances: bool = True,
) -> OptimizationResult:
    """
    Solve an agricultural logistics optimization model.

    Parameters
    ----------
    data:
        Canonical model data.

    model_config:
        Mathematical configuration. Ignored if run_config is provided.

    solver_config:
        Solver/backend configuration. Ignored if run_config is provided.

    run_config:
        Combined run configuration. If provided, do not also provide
        model_config or solver_config.

    validate:
        If True, validate ModelData before dispatching to a backend.

    require_distances:
        If True, every declared route must have a distance entry.

    Returns
    -------
    OptimizationResult
        Common result object independent of backend.
    """

    if run_config is not None and (
        model_config is not None or solver_config is not None
    ):
        raise ValueError(
            "Provide either run_config or model_config/solver_config, not both."
        )

    if run_config is not None:
        model_config = run_config.model
        solver_config = run_config.solver
    else:
        if model_config is None:
            model_config = ModelConfig()
        if solver_config is None:
            solver_config = SolverConfig()

    if validate:
        validate_or_raise_model_data(
            data=data,
            config=model_config,
            require_distances=require_distances,
        )

    if uses_gurobi(solver_config):
        configure_gurobi_wls_license(solver_config)

    if solver_config.backend == "gurobipy":
        from src.logic.optimization_gurobipy import solve_model_gurobipy

        return solve_model_gurobipy(
            data=data,
            model_config=model_config,
            solver_config=solver_config,
        )

    if solver_config.backend == "pyomo":
        from src.logic.optimization_pyomo import solve_model_pyomo

        return solve_model_pyomo(
            data=data,
            model_config=model_config,
            solver_config=solver_config,
        )

    raise ValueError(f"Unknown solver backend: {solver_config.backend!r}")


def calculate_evpi_vss(
    data: ModelData,
    model_config: ModelConfig | None = None,
    solver_config: SolverConfig | None = None,
    *,
    validate: bool = True,
    require_distances: bool = True,
    checkpoint_dir: str | Path | None = None,
    checkpoint_identity: str | None = None,
    resume: bool = False,
    progress: Callable[[str], None] | None = None,
) -> EVPIVSSResult:
    """Calculate EVPI and VSS for a two-stage stochastic model.

    Intermediate solutions can be checkpointed and safely restored by
    providing ``checkpoint_dir``, a stable ``checkpoint_identity``, and
    ``resume=True`` on the continuation call.
    """

    if model_config is None:
        model_config = ModelConfig(mode="sto")
    if solver_config is None:
        solver_config = SolverConfig()

    if model_config.mode != "sto":
        raise ValueError("EVPI/VSS calculation requires ModelConfig(mode='sto').")

    if validate:
        validate_or_raise_model_data(
            data=data,
            config=model_config,
            require_distances=require_distances,
        )

    if solver_config.backend != "gurobipy":
        raise OptimizationBackendNotImplementedError(
            "EVPI/VSS is currently implemented for the native gurobipy "
            "backend only."
        )

    configure_gurobi_wls_license(solver_config)

    from src.logic.stochastic_analysis_gurobipy import (
        calculate_evpi_vss_gurobipy,
    )

    return calculate_evpi_vss_gurobipy(
        data=data,
        model_config=model_config,
        solver_config=solver_config,
        checkpoint_dir=checkpoint_dir,
        checkpoint_identity=checkpoint_identity,
        resume=resume,
        progress=progress,
    )


