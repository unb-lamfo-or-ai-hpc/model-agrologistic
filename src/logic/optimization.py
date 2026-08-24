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
from typing import Any, Literal

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
    4. default HPC secret path: /secrets/gurobi.lic.

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

    default_license_file = Path(DEFAULT_GUROBI_LICENSE_FILE)
    if default_license_file.is_file():
        os.environ["GRB_LICENSE_FILE"] = str(default_license_file)
        return str(default_license_file)

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