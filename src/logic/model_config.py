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
from typing import Any, Literal

# ---------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------

type SolverBackend = Literal["gurobipy", "pyomo"]
type ModelMode = Literal["det", "sto"]
type CandidateCapacityMode = Literal["fixed", "scalable"]
type TerminalInventoryPolicy = Literal["free", "zero", "penalized", "target"]
type RouteFilterStrategy = Literal["none", "pareto", "top_k"]
type ObjectivePolicy = Literal["penalty", "lexicographic"]
type CapacityCouplingPolicy = Literal["period_equivalent", "daily_factors"]


VALID_SOLVER_BACKENDS = {"gurobipy", "pyomo"}
VALID_MODEL_MODES = {"det", "sto"}
VALID_CANDIDATE_CAPACITY_MODES = {"fixed", "scalable"}
VALID_TERMINAL_INVENTORY_POLICIES = {"free", "zero", "penalized", "target"}
VALID_ROUTE_FILTER_STRATEGIES = {"none", "pareto", "top_k"}
VALID_OBJECTIVE_POLICIES = {"penalty", "lexicographic"}
VALID_CAPACITY_COUPLING_POLICIES = {"period_equivalent", "daily_factors"}


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
    compute_iis: bool = False
    iis_max_items: int = 200

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

        if self.iis_max_items <= 0:
            raise ValueError("iis_max_items must be positive.")


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

    # ``period_equivalent`` preserves the established MVP formulation.
    # ``daily_factors`` reproduces the historical SiloDSS interpretation:
    # installed capacity also changes daily reception and shipping throughput.
    capacity_coupling_policy: CapacityCouplingPolicy = "period_equivalent"
    candidate_reception_daily_factor: float = 0.20
    candidate_shipping_daily_factor: float = 0.20
    expansion_reception_daily_factor: float = 0.20
    expansion_shipping_daily_factor: float = 0.20
    bulkification_reception_daily_factor: float = 1.0
    bulkification_shipping_daily_factor: float = 1.0

    # -----------------------------------------------------------------
    # Demand and emergency capacity policies
    # -----------------------------------------------------------------

    allow_unmet_domestic_demand: bool = True

    allow_emergency_static_capacity: bool = True
    allow_emergency_reception_capacity: bool = True

    # If True, static-capacity emergency slack and reception-capacity
    # emergency slack must be represented as distinct variables.
    separate_emergency_capacity_slacks: bool = True

    # ``penalty`` preserves the single weighted-cost objective. The optional
    # ``lexicographic`` policy minimizes emergency capacity first, expected
    # unmet demand second, and economic cost third. This keeps physical
    # feasibility slacks as a last resort before maximizing service.
    objective_policy: ObjectivePolicy = "penalty"

    # -----------------------------------------------------------------
    # Inventory policy
    # -----------------------------------------------------------------

    terminal_inventory_policy: TerminalInventoryPolicy = "free"

    # Used only when terminal_inventory_policy == "penalized".
    terminal_inventory_penalty: float = 0.0

    # -----------------------------------------------------------------
    # Time conversion
    # -----------------------------------------------------------------

    # Fallback number of operating days represented by one monthly period.
    # Per-period values override this fallback when supplied.
    days_per_period: float = 30.0
    days_per_period_by_period: dict[str, float] = field(default_factory=dict)

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

        if self.objective_policy not in VALID_OBJECTIVE_POLICIES:
            raise ValueError(
                f"Invalid objective_policy: {self.objective_policy!r}. "
                f"Expected one of {sorted(VALID_OBJECTIVE_POLICIES)}."
            )

        if self.capacity_coupling_policy not in VALID_CAPACITY_COUPLING_POLICIES:
            raise ValueError(
                f"Invalid capacity_coupling_policy: "
                f"{self.capacity_coupling_policy!r}. Expected one of "
                f"{sorted(VALID_CAPACITY_COUPLING_POLICIES)}."
            )

        capacity_factors = {
            "candidate_reception_daily_factor": self.candidate_reception_daily_factor,
            "candidate_shipping_daily_factor": self.candidate_shipping_daily_factor,
            "expansion_reception_daily_factor": self.expansion_reception_daily_factor,
            "expansion_shipping_daily_factor": self.expansion_shipping_daily_factor,
            "bulkification_reception_daily_factor": (
                self.bulkification_reception_daily_factor
            ),
            "bulkification_shipping_daily_factor": (
                self.bulkification_shipping_daily_factor
            ),
        }
        invalid_capacity_factors = {
            name: value for name, value in capacity_factors.items() if value < 0
        }
        if invalid_capacity_factors:
            raise ValueError(
                "Capacity coupling factors must be non-negative: "
                f"{invalid_capacity_factors}."
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

        invalid_period_days = {
            period: days
            for period, days in self.days_per_period_by_period.items()
            if days <= 0
        }
        if invalid_period_days:
            raise ValueError(
                "days_per_period_by_period values must be positive: "
                f"{invalid_period_days}."
            )

        if self.feasibility_tolerance <= 0:
            raise ValueError("feasibility_tolerance must be positive.")

        if self.evpi_vss_tolerance <= 0:
            raise ValueError("evpi_vss_tolerance must be positive.")

    def operating_days(self, period: str) -> float:
        """Return operating days for one period, falling back to the default."""

        return float(self.days_per_period_by_period.get(period, self.days_per_period))


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
