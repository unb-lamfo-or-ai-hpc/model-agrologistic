"""
Pyomo backend for agricultural logistics optimization.

This module will keep a solver-neutral implementation of the same mathematical
model, allowing execution with SCIP, CBC, or Gurobi through Pyomo.

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
)


def solve_model_pyomo(
    data: ModelData,
    model_config: ModelConfig,
    solver_config: SolverConfig,
) -> OptimizationResult:
    """
    Solve the model using Pyomo.

    This function is intentionally a stub at this stage.
    The Pyomo implementation will be aligned with the gurobipy formulation.
    """

    raise OptimizationBackendNotImplementedError(
        "The Pyomo backend is not implemented yet. "
        "It will be used later to support SCIP and backend equivalence tests."
    )