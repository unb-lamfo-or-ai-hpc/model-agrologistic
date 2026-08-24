"""
Native gurobipy backend for agricultural logistics optimization.

This module will contain the deterministic and stochastic MILP formulations
implemented directly with the Gurobi Python API.

Current status:
- backend entry point exists;
- deterministic model not implemented yet;
- stochastic model not implemented yet.
"""

from __future__ import annotations

from src.logic.model_config import ModelConfig, SolverConfig
from src.logic.model_data import ModelData
from src.logic.optimization import (
    OptimizationBackendNotImplementedError,
    OptimizationResult,
    configure_gurobi_wls_license
)


def solve_model_gurobipy(
    data: ModelData,
    model_config: ModelConfig,
    solver_config: SolverConfig,
) -> OptimizationResult:
    """
    Solve the model using native gurobipy.

    This function is intentionally a stub at this stage.
    The deterministic engine will be implemented next.
    """

    configure_gurobi_wls_license(solver_config)

    raise OptimizationBackendNotImplementedError(
        "The native gurobipy backend is not implemented yet. "
        "Next step: implement the deterministic MILP in "
        "src/logic/optimization_gurobipy.py."
    )