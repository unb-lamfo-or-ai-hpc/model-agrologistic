"""
Configuration objects for agricultural logistics optimization.

This module is intentionally solver-agnostic. It defines the execution
and mathematical configuration used by different optimization backends.

It must not import:
- gurobipy
- pyomo
- pandas
- torch
- dash
- plotly
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, TypeAlias


# ---------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------

SolverBackend: TypeAlias = Literal["gurobipy", "pyomo"]
ModelMode: TypeAlias = Literal["det", "sto"]
CandidateCapacityMode: TypeAlias = Literal["fixed", "scalable"]
TerminalInventoryPolicy: TypeAlias = Literal["free", "zero", "penalized", "target"]
RouteFilterStrategy: TypeAlias = Literal["none", "pareto", "top_k"]


VALID_SOLVER_BACKENDS = {"gurobipy", "pyomo"}
VALID_MODEL_MODES = {"det", "sto"}
VALID_CANDIDATE_CAPACITY_MODES = {"fixed", "scalable"}
VALID_TERMINAL_INVENTORY_POLICIES = {"free", "zero", "penalized", "target"}
VALID_ROUTE_FILTER_STRATEGIES = {"none", "pareto", "top_k"}


# ---------------------------------------------------------------------
# Solver configuration
# ---------------------------------------------------------------------

@dataclass(slots=True)
class SolverConfig:
    """
    Configuration for the optimization solver backend.

    Examples
    --------
    Native Gurobi:

        SolverConfig(
            backend="gurobipy",
            solver_name="gurobi",
            mip_gap=0.01,
            time_limit=3600,
        )

    Pyomo with SCIP:

        SolverConfig(
            backend="pyomo",
            solver_name="scip",
            mip_gap=0.01,
            time_limit=3600,
        )
    """

    backend: SolverBackend = "gurobipy"
    solver_name: str = "gurobi"

    mip_gap: float = 0.01
    time_limit: int | None = 3600
    threads: int | None = 0
    seed: int | None = 0

    tee: bool = False
    log_file: str | None = None

    solver_options: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.backend not in VALID_SOLVER_BACKENDS:
            raise ValueError(
                f"Invalid solver backend: {self.backend!r}. "
                f"Expected one of {sorted(VALID_SOLVER_BACKENDS)}."
            )

        if self.backend == "gurobipy" and self.solver_name.lower() not in {
            "gurobi",
            "gurobipy",
        }:
            raise ValueError(
                "When backend='gurobipy', solver_name must be 'gurobi' "
                "or 'gurobipy'."
            )

        if self.mip_gap < 0:
            raise ValueError("mip_gap must be non-negative.")

        if self.time_limit is not None and self.time_limit <= 0:
            raise ValueError("time_limit must be positive or None.")

        if self.threads is not None and self.threads < 0:
            raise ValueError("threads must be non-negative or None.")

        if self.seed is not None and self.seed < 0:
            raise ValueError("seed must be non-negative or None.")


# ---------------------------------------------------------------------
# Mathematical model configuration
# ---------------------------------------------------------------------

@dataclass(slots=True)
class ModelConfig:
    """
    Mathematical configuration of the agricultural logistics model.

    This class controls modeling choices, not raw data and not solver
    parameters.

    The same ModelConfig should be usable by both:
    - the native gurobipy backend;
    - the Pyomo backend.
    """

    # -----------------------------------------------------------------
    # Model type
    # -----------------------------------------------------------------

    mode: ModelMode = "det"

    # -----------------------------------------------------------------
    # Network structure
    # -----------------------------------------------------------------

    use_direct_origin_customer: bool = False
    use_warehouse_transshipment: bool = True

    route_filter_strategy: RouteFilterStrategy = "none"
    pareto_fraction: float = 0.20
    route_top_k: int | None = None

    # -----------------------------------------------------------------
    # Facility location and capacity decisions
    # -----------------------------------------------------------------

    candidate_capacity_mode: CandidateCapacityMode = "scalable"

    allow_capacity_expansion: bool = True
    allow_bulkification: bool = True

    # -----------------------------------------------------------------
    # Demand and emergency capacity policies
    # -----------------------------------------------------------------

    allow_unmet_domestic_demand: bool = True

    allow_emergency_static_capacity: bool = True
    allow_emergency_reception_capacity: bool = True

    # If True, static-capacity emergency slack and reception-capacity
    # emergency slack must be represented as distinct variables.
    separate_emergency_capacity_slacks: bool = True

    # -----------------------------------------------------------------
    # Inventory policy
    # -----------------------------------------------------------------

    terminal_inventory_policy: TerminalInventoryPolicy = "free"

    # Used only when terminal_inventory_policy == "penalized".
    terminal_inventory_penalty: float = 0.0

    # -----------------------------------------------------------------
    # Time conversion
    # -----------------------------------------------------------------

    # Number of operating days represented by one period.
    # This is useful for reception/shipping capacity constraints.
    days_per_period: float = 22.0

    # -----------------------------------------------------------------
    # Numerical tolerances
    # -----------------------------------------------------------------

    feasibility_tolerance: float = 1e-6
    evpi_vss_tolerance: float = 1e-6

    def __post_init__(self) -> None:
        if self.mode not in VALID_MODEL_MODES:
            raise ValueError(
                f"Invalid model mode: {self.mode!r}. "
                f"Expected one of {sorted(VALID_MODEL_MODES)}."
            )

        if self.candidate_capacity_mode not in VALID_CANDIDATE_CAPACITY_MODES:
            raise ValueError(
                f"Invalid candidate_capacity_mode: "
                f"{self.candidate_capacity_mode!r}. "
                f"Expected one of {sorted(VALID_CANDIDATE_CAPACITY_MODES)}."
            )

        if self.terminal_inventory_policy not in VALID_TERMINAL_INVENTORY_POLICIES:
            raise ValueError(
                f"Invalid terminal_inventory_policy: "
                f"{self.terminal_inventory_policy!r}. "
                f"Expected one of {sorted(VALID_TERMINAL_INVENTORY_POLICIES)}."
            )

        if self.route_filter_strategy not in VALID_ROUTE_FILTER_STRATEGIES:
            raise ValueError(
                f"Invalid route_filter_strategy: "
                f"{self.route_filter_strategy!r}. "
                f"Expected one of {sorted(VALID_ROUTE_FILTER_STRATEGIES)}."
            )

        if not 0 < self.pareto_fraction <= 1:
            raise ValueError("pareto_fraction must be in the interval (0, 1].")

        if self.route_top_k is not None and self.route_top_k <= 0:
            raise ValueError("route_top_k must be positive or None.")

        if self.route_filter_strategy == "top_k" and self.route_top_k is None:
            raise ValueError(
                "route_top_k is required when route_filter_strategy='top_k'."
            )

        if self.terminal_inventory_penalty < 0:
            raise ValueError("terminal_inventory_penalty must be non-negative.")

        if self.days_per_period <= 0:
            raise ValueError("days_per_period must be positive.")

        if self.feasibility_tolerance <= 0:
            raise ValueError("feasibility_tolerance must be positive.")

        if self.evpi_vss_tolerance <= 0:
            raise ValueError("evpi_vss_tolerance must be positive.")


# ---------------------------------------------------------------------
# Combined run configuration
# ---------------------------------------------------------------------

@dataclass(slots=True)
class RunConfig:
    """
    Complete configuration for one optimization run.

    This object combines:
    - mathematical model choices;
    - solver/backend choices;
    - optional run metadata.
    """

    model: ModelConfig = field(default_factory=ModelConfig)
    solver: SolverConfig = field(default_factory=SolverConfig)

    run_name: str = "default_run"
    output_dir: str = "outputs"
    metadata: dict[str, Any] = field(default_factory=dict)

