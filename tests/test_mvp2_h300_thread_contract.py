"""Qualify design arithmetic and adverse records without a solver or NPAD job."""

import ast
import copy
import json

import pytest

from scripts import mvp2_h300_thread_contract as contract


def environment(threads=4):
    return {
        "threads": threads, "job_id": "future-job", "node": "captured-node",
        "job_state": "RUNNING", "partition": "intel-256", "qos": "preempt",
        "nodes": 1, "tasks": 1, "requested_cpus_per_task": 16,
        "allocated_cpus": 24, "memory_mib": 196608,
        "cgroup_limit_bytes": 192 * 1024**3, "affinity_cpu_ids": list(range(24)),
        "cpu_model": "synthetic-test-cpu", "architecture": "x86_64",
        "sockets": 2, "cores_per_socket": 12, "threads_per_core": 2,
        "node_memory_mib": 256000, "python": "3.13.15", "gurobi": "13.0.3",
        "implementation_sha256": contract.CORE,
        "runtime_sha256": "d" * 64,
        "native_thread_environment": {
            "OMP_NUM_THREADS": None, "MKL_NUM_THREADS": None, "OPENBLAS_NUM_THREADS": None,
        },
    }


def complete():
    return {
        "integrity_accepted": True, "has_incumbent": True, "residuals_accepted": True,
        "final_priority_accepted": True, "products_closed": True,
        "scheduler_state": "COMPLETED", "exit_code": "0:0", "native_stop": "completed",
        "stages": [{"role": r, "status": "optimal", "priority_accepted": True}
                   for r in contract.ROLES],
    }


def timing(threads=1):
    return {
        "disposition": "complete_accepted_hierarchy", "censor_reason": None,
        "threads": threads, "optimization_seconds": 100.0 / threads,
        "work_scope_sha256": "a" * 64, "environment_sha256": "b" * 64,
    }


def test_policy_and_budget_are_closed():
    policy = contract.policy()
    assert policy == contract.DEFAULT_POLICY
    assert contract.budget_ledger() == {
        "child_seconds": 3900, "block_seconds": 21600,
        "production_admitted": False, "repeats_admitted": False,
    }


@pytest.mark.parametrize("path,value", [
    (("large_instance_submission_allowed",), True),
    (("automatic_repeats_allowed",), True),
    (("allocation", "walltime_seconds"), 86400),
    (("budget", "optimization_seconds"), 5400),
    (("allocation", "exclusive_node"), 0),
    (("reference", "workbook_sha256"), "c" * 64),
])
def test_policy_drift_stops(path, value, tmp_path, monkeypatch):
    policy = copy.deepcopy(contract.DEFAULT_POLICY)
    parent = policy
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = value
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/mvp2_h300_thread_policy.json").write_text(json.dumps(policy))
    monkeypatch.setattr(contract, "ROOT", tmp_path)
    with pytest.raises(ValueError):
        contract.policy()
    with pytest.raises(ValueError):
        contract.budget_ledger(policy)


@pytest.mark.parametrize("threads", contract.GRID)
def test_threads_are_only_arm_difference(threads):
    candidate = contract.arm_profile(threads)
    reference = contract.arm_profile(4)
    candidate["solver"]["threads"] = 4
    assert candidate == reference
    assert candidate["solver"]["time_limit"] == 1800
    assert candidate["solver"]["soft_memory_gb"] == 128
    assert candidate["calculate_evpi_vss"] is False
    assert candidate["estimated_variables"] == 25107544


@pytest.mark.parametrize("threads", [0, 3, 32, None, True, "4", 4.0])
def test_unknown_threads_stop(threads):
    with pytest.raises(ValueError):
        contract.arm_profile(threads)


def test_homogeneous_shared_block_records_extra_allocated_cpus():
    records = [environment(t) for t in contract.ORDER]
    records[1]["affinity_cpu_ids"].reverse()
    decision = contract.homogeneous_block(records)
    assert decision["homogeneous"] is True
    assert decision["exclusive_node"] is False
    assert decision["production_admitted"] is False


@pytest.mark.parametrize("key,value", [
    ("node", "another-node"), ("job_id", "another-job"), ("cpu_model", "different-cpu"),
    ("qos", "different-qos"), ("architecture", "another-architecture"),
    ("allocated_cpus", 48), ("threads_per_core", 1), ("sockets", 1),
    ("node_memory_mib", 512000), ("affinity_cpu_ids", list(range(1, 25))),
    ("runtime_sha256", "e" * 64),
    ("native_thread_environment", {
        "OMP_NUM_THREADS": "8", "MKL_NUM_THREADS": None, "OPENBLAS_NUM_THREADS": None,
    }),
])
def test_cross_arm_environment_drift_stops(key, value):
    records = [environment(t) for t in contract.ORDER]
    records[-1][key] = value
    with pytest.raises(ValueError):
        contract.homogeneous_block(records)


@pytest.mark.parametrize("key,value", [
    ("partition", "intel-512"), ("nodes", 2), ("tasks", 2),
    ("requested_cpus_per_task", 4), ("memory_mib", 131072),
    ("cgroup_limit_bytes", 256 * 1024**3), ("cgroup_limit_bytes", None),
    ("allocated_cpus", True), ("affinity_cpu_ids", list(range(8))),
    ("affinity_cpu_ids", [0] * 24), ("affinity_cpu_ids", list(range(25))),
    ("python", "3.13.16"), ("gurobi", "13.0.4"), ("implementation_sha256", "c" * 64),
    ("job_state", "PENDING"), ("cpu_model", ""), ("node_memory_mib", 1000),
    ("runtime_sha256", None), ("native_thread_environment", {}),
])
def test_invalid_environment_stops(key, value):
    record = environment()
    record[key] = value
    with pytest.raises(ValueError):
        contract.environment_key(record)


@pytest.mark.parametrize("change", ["missing", "duplicate", "reordered"])
def test_incomplete_or_wrong_block_stops(change):
    records = [environment(t) for t in contract.ORDER]
    if change == "missing":
        records.pop()
    elif change == "duplicate":
        records[-1] = records[0]
    else:
        records.reverse()
    with pytest.raises(ValueError):
        contract.homogeneous_block(records)


def test_only_closed_certified_complete_record_is_full_acceptance():
    result = contract.observation(complete())
    assert result["disposition"] == "complete_accepted_hierarchy"
    assert result["certified_priority_prefix"] == 3
    assert result["censor_reason"] is None
    assert result["production_admitted"] is False


@pytest.mark.parametrize("reason,state,native", [
    ("time_limit", "COMPLETED", "time_limit"),
    ("memory_limit", "COMPLETED", "memory_limit"),
    ("scheduler_time", "TIMEOUT", "completed"),
    ("scheduler_memory", "OUT_OF_MEMORY", "completed"),
    ("preemption", "PREEMPTED", "interrupted"),
    ("cancellation", "CANCELLED", "interrupted"),
])
def test_censoring_does_not_erase_feasible_solution(reason, state, native):
    record = complete()
    record.update(scheduler_state=state, native_stop=native, stages=record["stages"][:1])
    result = contract.observation(record)
    assert result["disposition"] == "feasible_partial_hierarchy"
    assert result["independently_feasible"] is True
    assert result["certified_priority_prefix"] == 1
    assert result["censor_reason"] == reason


@pytest.mark.parametrize("key", ["final_priority_accepted", "products_closed"])
def test_completed_accounting_is_insufficient(key):
    record = complete()
    record[key] = False
    assert contract.observation(record)["disposition"] == "feasible_partial_hierarchy"


def test_unvalidated_incumbent_not_feasible():
    record = complete()
    record["residuals_accepted"] = False
    result = contract.observation(record)
    assert result["disposition"] == "unvalidated_incumbent"
    assert result["independently_feasible"] is False


def test_no_incumbent_not_imputed():
    record = complete()
    record.update(has_incumbent=False, residuals_accepted=False, stages=[],
                  native_stop="time_limit", final_priority_accepted=False)
    result = contract.observation(record)
    assert result["disposition"] == "no_incumbent"
    assert result["certified_priority_prefix"] == 0
    assert result["censor_reason"] == "time_limit"


def test_rejected_integrity_disables_scientific_acceptance():
    record = complete()
    record["integrity_accepted"] = False
    result = contract.observation(record)
    assert result["disposition"] == "evidence_rejected"
    assert result["independently_feasible"] is False
    assert result["certified_priority_prefix"] is None


@pytest.mark.parametrize("state", ["FAILED", "NODE_FAIL", "BOOT_FAIL"])
def test_execution_failure_is_not_complete_even_with_incumbent(state):
    record = complete()
    record["scheduler_state"] = state
    result = contract.observation(record)
    assert result["disposition"] == "execution_failed"
    assert result["independently_feasible"] is True


@pytest.mark.parametrize("change", ["stage-order", "stage-gap", "too-many", "unknown-status",
                                    "stopped-certificate", "unknown-accounting", "bool-int",
                                    "residual-without-incumbent"])
def test_contradictory_records_stop(change):
    record = complete()
    if change == "stage-order":
        record["stages"].reverse()
    elif change == "stage-gap":
        record["stages"].pop(0)
    elif change == "too-many":
        record["stages"].append(record["stages"][-1])
    elif change == "unknown-status":
        record["stages"][0]["status"] = "invented"
    elif change == "stopped-certificate":
        record["stages"][0]["status"] = "time_limit"
    elif change == "unknown-accounting":
        record["scheduler_state"] = "RUNNING"
    elif change == "bool-int":
        record["integrity_accepted"] = 1
    else:
        record["has_incumbent"] = False
    with pytest.raises(ValueError):
        contract.observation(record)


def test_metrics_use_actual_allocation_not_solver_threads():
    result = contract.resource_metrics(
        elapsed_seconds=3600, allocated_cpus=24, solver_threads=4, cpu_seconds=7200,
        application_peak_rss_bytes=60 * 1024**3, sampled_tree_peak_rss_bytes=58 * 1024**3,
        native_peak_decimal_gb=40, telemetry_max_gap_seconds=174,
    )
    assert result["allocated_core_hours"] == 24
    assert result["configured_thread_hours"] == 4
    assert result["measured_process_cpu_hours"] == 2
    assert result["average_observed_cpu_cores"] == 2
    assert result["application_peak_rss_gib"] == 60
    assert result["sampled_tree_peak_rss_gib"] == 58
    assert result["observed_native_memory_gib"] == pytest.approx(37.2529029846)
    assert result["telemetry_max_gap_seconds"] == 174


def test_missing_metrics_stay_null_not_zero():
    result = contract.resource_metrics(elapsed_seconds=0, allocated_cpus=24, solver_threads=4)
    assert result["measured_process_cpu_hours"] is None
    assert result["average_observed_cpu_cores"] is None
    assert result["application_peak_rss_gib"] is None
    assert result["allocated_core_hours"] == 0


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf"), True, "100"])
def test_invalid_measurements_stop(value):
    with pytest.raises(ValueError):
        contract.resource_metrics(elapsed_seconds=100, allocated_cpus=24, solver_threads=4,
                                  cpu_seconds=value)


def test_only_descriptive_speedup_for_same_complete_work():
    result = contract.comparable_speedup(timing(), timing(4))
    assert result == {"descriptive_speedup": 4, "descriptive_efficiency": 1,
                      "causal_claim_allowed": False}


@pytest.mark.parametrize("key,value", [
    ("disposition", "feasible_partial_hierarchy"), ("disposition", "no_incumbent"),
    ("censor_reason", "time_limit"), ("optimization_seconds", 0),
    ("work_scope_sha256", "c" * 64), ("environment_sha256", "c" * 64),
    ("threads", True),
])
def test_censored_or_unequal_timings_have_no_speedup(key, value):
    candidate = timing(4)
    candidate[key] = value
    with pytest.raises(ValueError):
        contract.comparable_speedup(timing(), candidate)


def test_contract_imports_no_execution_facilities():
    source = (contract.ROOT / "scripts/mvp2_h300_thread_contract.py").read_text()
    tree = ast.parse(source)
    imports = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    imports += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
    assert set(imports) <= {"__future__", "pathlib", "hashlib", "json", "math"}
    assert "subprocess" not in imports
    assert "gurobipy" not in imports
