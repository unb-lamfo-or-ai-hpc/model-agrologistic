"""EVPI and VSS analysis for the native gurobipy stochastic model."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import fields, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.logic.model_config import ModelConfig, SolverConfig
from src.logic.model_data import ModelData
from src.logic.optimization import EVPIVSSResult, OptimizationResult
from src.logic.optimization_gurobipy import _solve_deterministic_core
from src.logic.optimization_gurobipy_stochastic import (
    solve_stochastic_model_gurobipy,
)


def calculate_evpi_vss_gurobipy(
    data: ModelData,
    model_config: ModelConfig,
    solver_config: SolverConfig,
    *,
    checkpoint_dir: str | Path | None = None,
    checkpoint_identity: str | None = None,
    resume: bool = False,
    progress: Callable[[str], None] | None = None,
) -> EVPIVSSResult:
    """Calculate RP, WS, EV, EEV, EVPI, and VSS for a minimization model.

    When ``checkpoint_dir`` is provided, every usable intermediate solution is
    written atomically. A later call with ``resume=True`` reuses only
    checkpoints carrying the same caller-provided identity.
    """

    report = progress or (lambda _message: None)
    store = _CheckpointStore.create(
        checkpoint_dir,
        identity=checkpoint_identity,
        resume=resume,
        total_steps=len(data.scenarios) + 3,
    )

    recourse_result = _solve_or_restore(
        key="rp",
        label="recourse problem (RP)",
        solve=lambda: solve_stochastic_model_gurobipy(
            data=data,
            model_config=model_config,
            solver_config=solver_config,
        ),
        store=store,
        report=report,
    )
    recourse_problem = _require_objective(recourse_result, "recourse problem")

    deterministic_config = replace(model_config, mode="det")
    expected_data = _expected_value_data(data)
    expected_value_result = _solve_or_restore(
        key="ev",
        label="expected-value problem (EV)",
        solve=lambda: _solve_deterministic_core(
            data=expected_data,
            model_config=deterministic_config,
            solver_config=solver_config,
        ),
        store=store,
        report=report,
    )
    expected_value_problem = _require_objective(
        expected_value_result,
        "expected-value problem",
    )

    expected_result = _solve_or_restore(
        key="eev",
        label="expected result of the EV solution (EEV)",
        solve=lambda: solve_stochastic_model_gurobipy(
            data=data,
            model_config=model_config,
            solver_config=solver_config,
            fixed_first_stage=expected_value_result.warehouse_decisions,
        ),
        store=store,
        report=report,
    )
    expected_result_of_ev_solution = _require_objective(
        expected_result,
        "expected result of the expected-value solution",
    )

    wait_and_see_results: dict[str, OptimizationResult] = {}
    wait_and_see = 0.0
    for index, scenario in enumerate(data.scenarios):
        scenario_result = _solve_or_restore(
            key=f"ws_{index:03d}",
            label=f"wait-and-see scenario {scenario!r}",
            solve=lambda scenario=scenario: _solve_deterministic_core(
                data=_single_scenario_data(data, scenario),
                model_config=deterministic_config,
                solver_config=solver_config,
            ),
            store=store,
            report=report,
        )
        scenario_objective = _require_objective(
            scenario_result,
            f"wait-and-see scenario {scenario!r}",
        )
        wait_and_see_results[scenario] = scenario_result
        wait_and_see += data.scenario_prob[scenario] * scenario_objective

    raw_evpi = recourse_problem - wait_and_see
    raw_vss = expected_result_of_ev_solution - recourse_problem
    tolerance = model_config.evpi_vss_tolerance
    evpi = _zero_within_tolerance(raw_evpi, tolerance)
    vss = _zero_within_tolerance(raw_vss, tolerance)

    objective_intervals = {
        "recourse_problem": _solver_objective_interval(recourse_result),
        "wait_and_see": _weighted_solver_objective_interval(
            wait_and_see_results,
            data.scenario_prob,
        ),
        "expected_value_problem": _solver_objective_interval(
            expected_value_result
        ),
        "expected_result_of_ev_solution": _solver_objective_interval(
            expected_result
        ),
    }
    evpi_interval = _difference_interval(
        objective_intervals["recourse_problem"],
        objective_intervals["wait_and_see"],
    )
    vss_interval = _difference_interval(
        objective_intervals["expected_result_of_ev_solution"],
        objective_intervals["recourse_problem"],
    )
    evpi_certification_status = _classify_nonnegative_interval(
        evpi_interval,
        tolerance,
    )
    vss_certification_status = _classify_nonnegative_interval(
        vss_interval,
        tolerance,
    )

    consistency_warnings: list[str] = []
    if evpi_certification_status == "inconsistent_negative":
        consistency_warnings.append(
            "The solver-bound EVPI interval is strictly negative. Check model "
            "consistency, objective scaling, and solver termination."
        )
    elif evpi < -tolerance:
        consistency_warnings.append(
            "The EVPI point estimate is negative, but its solver-bound interval "
            "does not certify a negative value."
        )
    if vss_certification_status == "inconsistent_negative":
        consistency_warnings.append(
            "The solver-bound VSS interval is strictly negative. Check fixed "
            "first-stage decisions, objective scaling, and solver termination."
        )
    elif vss < -tolerance:
        consistency_warnings.append(
            "The VSS point estimate is negative, but its solver-bound interval "
            "does not certify a negative value."
        )

    result = EVPIVSSResult(
        recourse_problem=recourse_problem,
        wait_and_see=wait_and_see,
        expected_value_problem=expected_value_problem,
        expected_result_of_ev_solution=expected_result_of_ev_solution,
        evpi=evpi,
        vss=vss,
        recourse_problem_result=recourse_result,
        wait_and_see_results=wait_and_see_results,
        expected_value_problem_result=expected_value_result,
        expected_result_result=expected_result,
        metadata={
            "formulation": "risk_neutral_two_stage",
            "sense": "minimize",
            "evpi_formula": "RP - WS",
            "vss_formula": "EEV - RP",
            "scenario_probabilities": dict(data.scenario_prob),
            "evpi_vss_tolerance": tolerance,
            "raw_evpi": raw_evpi,
            "raw_vss": raw_vss,
            "objective_intervals": objective_intervals,
            "evpi_interval": evpi_interval,
            "vss_interval": vss_interval,
            "evpi_certification_status": evpi_certification_status,
            "vss_certification_status": vss_certification_status,
            "consistency_warnings": consistency_warnings,
            "checkpoint_directory": str(store.path) if store else None,
            "restored_checkpoint_steps": list(store.restored_steps) if store else [],
        },
    )
    if store:
        store.finish(
            {
                "recourse_problem": recourse_problem,
                "wait_and_see": wait_and_see,
                "expected_value_problem": expected_value_problem,
                "expected_result_of_ev_solution": expected_result_of_ev_solution,
                "evpi": evpi,
                "vss": vss,
            }
        )
    return result


def _solve_or_restore(
    *,
    key: str,
    label: str,
    solve: Callable[[], OptimizationResult],
    store: _CheckpointStore | None,
    report: Callable[[str], None],
) -> OptimizationResult:
    if store:
        restored = store.load(key)
        if restored is not None:
            report(f"[EVPI/VSS] restored {label} from checkpoint")
            store.complete(key, label, restored=True)
            return restored
        store.start(key, label)

    report(f"[EVPI/VSS] solving {label}")
    result = solve()
    _require_objective(result, label)
    if store:
        store.save(key, result)
        store.complete(key, label, restored=False)
    return result


class _CheckpointStore:
    """Atomic, identity-scoped checkpoints for a multi-solve EVPI/VSS run."""

    SCHEMA_VERSION = 1

    def __init__(self, path: Path, identity: str, total_steps: int):
        self.path = path
        self.identity = identity
        self.total_steps = total_steps
        self.completed_steps: list[str] = []
        self.restored_steps: list[str] = []

    @classmethod
    def create(
        cls,
        path: str | Path | None,
        *,
        identity: str | None,
        resume: bool,
        total_steps: int,
    ) -> _CheckpointStore | None:
        if path is None:
            if resume:
                raise ValueError("resume=True requires checkpoint_dir.")
            return None
        if not identity:
            raise ValueError(
                "checkpoint_identity is required when checkpoint_dir is used."
            )

        store = cls(Path(path).resolve(), identity, total_steps)
        store.path.mkdir(parents=True, exist_ok=True)
        manifest_path = store.path / "manifest.json"
        if resume:
            if manifest_path.is_file():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if manifest.get("identity") != identity:
                    raise ValueError(
                        "EVPI/VSS checkpoints do not match the current experiment."
                    )
            else:
                store._write_manifest(manifest_path)
        else:
            store._write_manifest(manifest_path)
        return store

    def _write_manifest(self, path: Path) -> None:
        self._write_json(
            path,
            {
                "schema_version": self.SCHEMA_VERSION,
                "identity": self.identity,
                "total_steps": self.total_steps,
                "created_at_utc": _utc_now(),
            },
        )

    def load(self, key: str) -> OptimizationResult | None:
        path = self.path / f"{key}.json"
        if not path.is_file():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("identity") != self.identity:
            return None
        result = OptimizationResult(**payload["result"])
        _require_objective(result, f"checkpoint {key!r}")
        self.restored_steps.append(key)
        return result

    def save(self, key: str, result: OptimizationResult) -> None:
        payload = {
            item.name: getattr(result, item.name)
            for item in fields(result)
            if item.name != "raw_solver_result"
        }
        self._write_json(
            self.path / f"{key}.json",
            {
                "schema_version": self.SCHEMA_VERSION,
                "identity": self.identity,
                "step": key,
                "saved_at_utc": _utc_now(),
                "result": payload,
            },
        )

    def start(self, key: str, label: str) -> None:
        self._write_progress(status="running", current_step=key, label=label)

    def complete(self, key: str, label: str, *, restored: bool) -> None:
        if key not in self.completed_steps:
            self.completed_steps.append(key)
        self._write_progress(
            status="running",
            current_step=None,
            label=label,
            last_step_restored=restored,
        )

    def finish(self, metrics: dict[str, float]) -> None:
        self._write_progress(
            status="complete",
            current_step=None,
            label="EVPI/VSS complete",
            metrics=metrics,
        )

    def _write_progress(self, **values: Any) -> None:
        self._write_json(
            self.path / "progress.json",
            {
                "schema_version": self.SCHEMA_VERSION,
                "identity": self.identity,
                "total_steps": self.total_steps,
                "completed_count": len(self.completed_steps),
                "completed_steps": self.completed_steps,
                "restored_steps": self.restored_steps,
                "updated_at_utc": _utc_now(),
                **values,
            },
        )

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _expected_value_data(data: ModelData) -> ModelData:
    supply = {
        (origin, product, period): sum(
            data.scenario_prob[scenario]
            * data.supply_s[scenario, origin, product, period]
            for scenario in data.scenarios
        )
        for origin in data.origins
        for product in data.products
        for period in data.periods
    }
    demand_dom = {
        (customer, product, period): sum(
            data.scenario_prob[scenario]
            * data.demand_dom_s[scenario, customer, product, period]
            for scenario in data.scenarios
        )
        for customer in data.domestic_customers
        for product in data.products
        for period in data.periods
    }
    demand_exp = {
        (customer, product, period): sum(
            data.scenario_prob[scenario]
            * data.demand_exp_s[scenario, customer, product, period]
            for scenario in data.scenarios
        )
        for customer in data.export_customers
        for product in data.products
        for period in data.periods
    }
    return _as_deterministic_data(
        data,
        supply=supply,
        demand_dom=demand_dom,
        demand_exp=demand_exp,
        source="expected_value",
    )


def _single_scenario_data(data: ModelData, scenario: str) -> ModelData:
    supply = {
        (origin, product, period): data.supply_s[
            scenario,
            origin,
            product,
            period,
        ]
        for origin in data.origins
        for product in data.products
        for period in data.periods
    }
    demand_dom = {
        (customer, product, period): data.demand_dom_s[
            scenario,
            customer,
            product,
            period,
        ]
        for customer in data.domestic_customers
        for product in data.products
        for period in data.periods
    }
    demand_exp = {
        (customer, product, period): data.demand_exp_s[
            scenario,
            customer,
            product,
            period,
        ]
        for customer in data.export_customers
        for product in data.products
        for period in data.periods
    }
    return _as_deterministic_data(
        data,
        supply=supply,
        demand_dom=demand_dom,
        demand_exp=demand_exp,
        source=f"wait_and_see:{scenario}",
    )


def _as_deterministic_data(
    data: ModelData,
    *,
    supply: dict[tuple[str, str, str], float],
    demand_dom: dict[tuple[str, str, str], float],
    demand_exp: dict[tuple[str, str, str], float],
    source: str,
) -> ModelData:
    return replace(
        data,
        supply=supply,
        demand_dom=demand_dom,
        demand_exp=demand_exp,
        scenarios=[],
        scenario_prob={},
        supply_s={},
        demand_dom_s={},
        demand_exp_s={},
        metadata={**data.metadata, "deterministic_projection": source},
    )


def _solver_objective_interval(
    result: OptimizationResult,
) -> dict[str, float] | None:
    """Return the certified minimization interval reported by Gurobi."""

    objective = result.metadata.get("gurobi_objective_value")
    bound = result.metadata.get("gurobi_objective_bound")
    if objective is None or bound is None:
        return None

    objective_value = float(objective)
    bound_value = float(bound)
    return {
        "lower_bound": min(bound_value, objective_value),
        "upper_bound": max(bound_value, objective_value),
    }


def _weighted_solver_objective_interval(
    results: dict[str, OptimizationResult],
    probabilities: dict[str, float],
) -> dict[str, float] | None:
    """Combine scenario objective intervals with their declared probabilities."""

    lower_bound = 0.0
    upper_bound = 0.0
    for scenario, result in results.items():
        interval = _solver_objective_interval(result)
        if interval is None:
            return None
        probability = float(probabilities[scenario])
        lower_bound += probability * interval["lower_bound"]
        upper_bound += probability * interval["upper_bound"]
    return {
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
    }


def _difference_interval(
    left: dict[str, float] | None,
    right: dict[str, float] | None,
) -> dict[str, float] | None:
    """Return the interval enclosing every value of left minus right."""

    if left is None or right is None:
        return None
    return {
        "lower_bound": left["lower_bound"] - right["upper_bound"],
        "upper_bound": left["upper_bound"] - right["lower_bound"],
    }


def _classify_nonnegative_interval(
    interval: dict[str, float] | None,
    tolerance: float,
) -> str:
    """Classify a theoretically non-negative metric using solver bounds."""

    if interval is None:
        return "unavailable"
    lower_bound = interval["lower_bound"]
    upper_bound = interval["upper_bound"]
    if lower_bound > tolerance:
        return "certified_positive"
    if lower_bound >= -tolerance:
        return "certified_nonnegative"
    if upper_bound < -tolerance:
        return "inconsistent_negative"
    return "numerically_indeterminate"


def _require_objective(result: OptimizationResult, label: str) -> float:
    if not result.has_solution or result.objective_value is None:
        raise RuntimeError(
            f"Cannot calculate EVPI/VSS because the {label} did not return "
            f"a usable solution (status={result.status!r})."
        )
    return float(result.objective_value)


def _zero_within_tolerance(value: float, tolerance: float) -> float:
    return 0.0 if abs(value) <= tolerance else value
