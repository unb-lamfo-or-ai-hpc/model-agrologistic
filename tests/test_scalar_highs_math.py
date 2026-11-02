"""Three real HiGHS controls, including medium phases/RSS; compute or cloud only."""

import json
import platform
import resource
from time import perf_counter

import pytest

from scripts.highs_public_qualification import public_data, stochastic
from src.logic.mathematical_contract import prepare_model_data
from src.logic.model_config import ModelConfig, SolverConfig
from src.logic.optimization import solve_model
from src.logic.optimization_pyomo import PHASE_OBSERVER
from src.logic.solution_validation import validate_solution
from tests.test_pyomo_multisolver import available


def solve(data, mode):
    available("highs")
    cfg = ModelConfig(mode=mode)
    events = []
    token = PHASE_OBSERVER.set(events.append)
    try:
        result = solve_model(data, cfg, SolverConfig(
            backend="pyomo", solver_name="highs", time_limit=30, threads=1, seed=42,
            mip_gap=0, solver_options={"indicator_reformulation": "bounded_scalar_slacks_v1"},
        ))
    finally:
        PHASE_OBSERVER.reset(token)
    assert events == ["optimization", "native_return"]
    report = validate_solution(prepare_model_data(data, cfg), cfg, result)
    assert report["status"] == "accepted", report["failure_samples"]
    assert result.metadata["effective_highs_options"] == {
        "time_limit": 30.0, "mip_rel_gap": 0.0, "threads": 1,
        "random_seed": 42, "mip_feasibility_tolerance": 1e-9,
    }
    assert result.metadata["native_model_lifecycle"][0]["status"] == "disposed"
    return result


def test_public_det_hand_cost():
    assert solve(public_data(), "det").objective_value == pytest.approx(150)


def test_public_sto_unequal_weights_hand_cost():
    assert solve(stochastic(public_data()), "sto").objective_value == pytest.approx(150)


def test_public_medium_construction_transfer_native_extraction_validation_rss(tmp_path):
    started = perf_counter()
    result = solve(stochastic(public_data(origins=2500, periods=4)), "sto")
    elapsed = perf_counter() - started
    assert result.objective_value == pytest.approx(1500)
    assert result.metadata["matrix"]["variables"] >= 30000
    assert result.metadata["timings"]["solver_transfer_seconds"] >= 0
    assert elapsed < 120, "Public medium gate exceeded 120 seconds."
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_bytes = peak if platform.system() == "Darwin" else peak * 1024
    assert peak_bytes < 2 * 1024**3, "Public medium process peak exceeded 2GiB."
    record = {
        "public_generated_control": True, "private_h215_built": False,
        "scope": "Process lifetime high-water RSS; no h215 extrapolation.",
        "matrix": result.metadata["matrix"], "timings": result.metadata["timings"],
        "wall_including_validation_seconds": elapsed, "process_peak_bytes": peak_bytes,
        "objective": result.objective_value, "independent_validation": "accepted",
    }
    (tmp_path / "medium-resource-receipt.json").write_text(json.dumps(record), encoding="utf-8")
