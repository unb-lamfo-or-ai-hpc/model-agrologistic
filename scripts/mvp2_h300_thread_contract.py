"""Solver-free S2 design qualification; no executor or admission is provided."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROLES = ("unmet_demand", "emergency_capacity", "economic_cost")
GRID = (1, 2, 4, 8, 16)
ORDER = (4, 1, 8, 2, 16)
CORE = "b4de41ade0b3c55f8f20a66480cffa275421f8157444b1db3000a9eb50f2d351"
WORKBOOK = "7761cce77cf93dcba2f617714f0117c1f2ead4de0c3f27149daceba447e0c7d1"
DEFAULT_POLICY = {
    "schema_version": "mvp2-h300-thread-design-v1",
    "status": "design_qualified_execution_closed",
    "large_instance_submission_allowed": False,
    "automatic_repeats_allowed": False,
    "base_develop": "1181eb1d03de1990f5e02d99bda0ef0a93563a47",
    "grid": list(GRID), "order": list(ORDER),
    "reference": {
        "case": "h300-warehouse-control", "input_job": "2198085",
        "input_source": "3957f84ff49ac500eecf25b85e6b710b4b3b1010",
        "input_archive_sha256":
            "97395d29b802e558d3ac88db8c8e74cf3447d165782530a9c8d7cafd59f106fb",
        "pair_job": "2199525",
        "pair_source": "0e663c8bd8d9c5c4b27dbb09db3f1375ad52257d",
        "pair_archive_sha256":
            "5e52e56887dcb57b9c6209fb884129bf85cc322779fc17c2279c589519d4c1d9",
        "miniature_job": "2202239",
        "miniature_archive_sha256":
            "985002c13784ba071054e4c0db412cb41eefa60366f777866ce3eb3d52b586b2",
        "workbook_sha256": WORKBOOK, "implementation_sha256": CORE,
    },
    "allocation": {
        "partition": "intel-256", "nodes": 1, "tasks": 1,
        "requested_cpus_per_task": 16, "memory_mib": 196608,
        "exclusive_node": False, "walltime_seconds": 21600,
    },
    "budget": {
        "build_seconds": 900, "optimization_seconds": 1800,
        "export_validation_seconds": 900, "cleanup_grace_seconds": 300,
        "child_watchdog_seconds": 3900, "admission_seconds": 600,
        "block_audit_seconds": 900, "terminal_reserve_seconds": 600,
    },
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()


def policy():
    """Keep this design immutable, including booleans versus integer lookalikes."""
    value = json.loads((ROOT / "docs/mvp2_h300_thread_policy.json").read_text())
    require(digest(value) == digest(DEFAULT_POLICY), "Unqualified design-policy change.")
    return value


def budget_ledger(value=None):
    """Arithmetic headroom is a design cap, not measured sufficiency or admission."""
    value = policy() if value is None else value
    require(digest(value) == digest(DEFAULT_POLICY), "Unqualified budget change.")
    b = value["budget"]
    child = sum(b[k] for k in (
        "build_seconds", "optimization_seconds", "export_validation_seconds",
        "cleanup_grace_seconds",
    ))
    block = len(GRID) * child + sum(b[k] for k in (
        "admission_seconds", "block_audit_seconds", "terminal_reserve_seconds",
    ))
    require(child == b["child_watchdog_seconds"], "Child watchdog arithmetic mismatch.")
    require(block <= value["allocation"]["walltime_seconds"], "Slurm headroom exhausted.")
    return {"child_seconds": child, "block_seconds": block,
            "production_admitted": False, "repeats_admitted": False}


def arm_profile(threads):
    """Describe scientific invariants without constructing an ExperimentSpec/model."""
    require(type(threads) is int and threads in GRID, "Unqualified Threads.")
    return {
        "case": "h300-warehouse-control", "workbook_sha256": WORKBOOK,
        "implementation_sha256": CORE, "warehouses": 300, "scenarios": 9,
        "periods": 60, "products": 2, "direct_origin_customer": False,
        "estimated_variables": 25107544, "mode": "sto",
        "objective_policy": "lexicographic", "hierarchy": list(ROLES),
        "calculate_evpi_vss": False, "warm_start": False,
        "solver": {
            "backend": "gurobi", "threads": threads, "seed": 42,
            "time_limit": 1800, "soft_memory_gb": 128,
            "mip_gap": 0.1, "numeric_focus": 1,
            "compact_python_indices": False,
            "multiobjective_stage_options": {role: {"Method": 2} for role in ROLES},
        },
    }


def positive_int(value, name):
    require(type(value) is int and value > 0, f"Invalid {name}.")
    return value


def number(value, name, *, nullable=False):
    if value is None and nullable:
        return None
    require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
            f"Invalid {name}.")
    return value


def environment_key(record):
    """Validate a normalized capture, NOT authenticate scheduler text or a receipt."""
    require(record["partition"] == "intel-256", "Wrong partition.")
    require(record["job_state"] == "RUNNING", "Allocation not running at capture.")
    for name, expected in (("nodes", 1), ("tasks", 1), ("requested_cpus_per_task", 16),
                           ("memory_mib", 196608), ("cgroup_limit_bytes", 192 * 1024**3)):
        require(type(record[name]) is int and record[name] == expected, f"Wrong {name}.")
    cpus = positive_int(record["allocated_cpus"], "allocated CPUs")
    affinity = record["affinity_cpu_ids"]
    require(isinstance(affinity, list) and len(affinity) >= 16
            and all(type(cpu) is int and cpu >= 0 for cpu in affinity)
            and len(set(affinity)) == len(affinity) and len(affinity) <= cpus,
            "Invalid accessible affinity CPUs.")
    require(cpus >= 16, "Insufficient allocated CPUs.")
    for name in ("job_id", "node", "cpu_model", "architecture", "qos"):
        require(isinstance(record[name], str) and bool(record[name].strip()),
                f"Missing {name}.")
    for name in ("sockets", "cores_per_socket", "threads_per_core", "node_memory_mib"):
        positive_int(record[name], name)
    require(record["node_memory_mib"] >= record["memory_mib"], "Impossible node memory.")
    require(record["python"] == "3.13.15" and record["gurobi"] == "13.0.3"
            and record["implementation_sha256"] == CORE, "Runtime/core drift.")
    require(isinstance(record["runtime_sha256"], str) and len(record["runtime_sha256"]) == 64
            and all(c in "0123456789abcdef" for c in record["runtime_sha256"]),
            "Missing full dependency/runtime fingerprint.")
    require(isinstance(record["native_thread_environment"], dict)
            and set(record["native_thread_environment"]) == {
                "OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
            }
            and all(v is None or isinstance(v, str)
                    for v in record["native_thread_environment"].values()),
            "Missing native-library thread environment capture.")
    key = {k: record[k] for k in (
        "job_id", "node", "partition", "qos", "cpu_model", "architecture",
        "sockets", "cores_per_socket", "threads_per_core", "allocated_cpus",
        "memory_mib", "cgroup_limit_bytes", "node_memory_mib", "python", "gurobi",
        "implementation_sha256", "runtime_sha256", "native_thread_environment",
    )}
    key["affinity_cpu_ids"] = sorted(affinity)
    return digest(key)


def homogeneous_block(records):
    """One cold sequential block, not five incomparable allocations or replicates."""
    require(isinstance(records, list) and len(records) == len(GRID), "Incomplete block.")
    require([r["threads"] for r in records] == list(ORDER), "Wrong block order.")
    require(all(type(r["threads"]) is int for r in records), "Invalid Threads type.")
    keys = [environment_key(r) for r in records]
    require(len(set(keys)) == 1, "Nonhomogeneous environment/affinity/runtime.")
    return {"environment_sha256": keys[0], "homogeneous": True,
            "exclusive_node": False, "production_admitted": False}


def observation(record):
    """Classify a hypothetical normalized record; this is not an evidence verifier.

    Integrity, residual and priority booleans must come from a future qualified
    hash-bound collector/validator. They cannot authorize execution or certify
    an arbitrary uploaded JSON. Censoring and feasibility are separate axes.
    """
    for name in ("integrity_accepted", "has_incumbent", "residuals_accepted",
                 "final_priority_accepted", "products_closed"):
        require(type(record[name]) is bool, f"Invalid {name} flag.")
    stages = record["stages"]
    require(isinstance(stages, list) and len(stages) <= 3, "Invalid stages.")
    require([s["role"] for s in stages] == list(ROLES[:len(stages)]), "Stage order/gap.")
    for s in stages:
        require(s["status"] in {"optimal", "time_limit", "memory_limit", "interrupted"},
                "Unknown stage status.")
        require(type(s["priority_accepted"]) is bool, "Invalid priority flag.")
        require(not s["priority_accepted"] or s["status"] == "optimal",
                "Unqualified stopped-stage certificate.")
    for name in ("scheduler_state", "native_stop"):
        require(isinstance(record[name], str), f"Invalid {name}.")
    require(record["scheduler_state"] in {
        "COMPLETED", "TIMEOUT", "OUT_OF_MEMORY", "PREEMPTED", "CANCELLED", "FAILED",
        "NODE_FAIL", "BOOT_FAIL",
    }, "Nonterminal/unknown accounting.")
    require(record["native_stop"] in {
        "completed", "time_limit", "memory_limit", "no_incumbent", "error", "interrupted",
    }, "Unknown native stop.")
    require(isinstance(record["exit_code"], str), "Invalid exit code.")
    require(not record["residuals_accepted"] or record["has_incumbent"],
            "Residual certificate without incumbent.")
    reason = {
        "TIMEOUT": "scheduler_time", "OUT_OF_MEMORY": "scheduler_memory",
        "PREEMPTED": "preemption", "CANCELLED": "cancellation",
    }.get(record["scheduler_state"])
    if reason is None and record["native_stop"] in {"time_limit", "memory_limit"}:
        reason = record["native_stop"]
    prefix = 0
    for s in stages:
        if not s["priority_accepted"]:
            break
        prefix += 1
    feasible = record["has_incumbent"] and record["residuals_accepted"]
    clean = record["scheduler_state"] == "COMPLETED" and record["exit_code"] == "0:0"
    complete = (clean and record["native_stop"] == "completed" and feasible
                and prefix == 3 and record["final_priority_accepted"]
                and record["products_closed"] and reason is None)
    if not record["integrity_accepted"]:
        disposition = "evidence_rejected"
        feasible = False
    elif complete:
        disposition = "complete_accepted_hierarchy"
    elif record["scheduler_state"] in {"FAILED", "NODE_FAIL", "BOOT_FAIL"} or (
        not clean and reason is None
    ) or record["native_stop"] in {"error", "interrupted"} and reason is None:
        disposition = "execution_failed"
    elif feasible:
        disposition = "feasible_partial_hierarchy"
    elif record["has_incumbent"]:
        disposition = "unvalidated_incumbent"
    else:
        disposition = "no_incumbent"
    return {"disposition": disposition, "independently_feasible": feasible,
            "certified_priority_prefix": prefix if record["integrity_accepted"] else None,
            "censor_reason": reason, "products_closed": record["products_closed"],
            "production_admitted": False, "repeats_admitted": False}


def resource_metrics(*, elapsed_seconds, allocated_cpus, solver_threads,
                     cpu_seconds=None, application_peak_rss_bytes=None,
                     sampled_tree_peak_rss_bytes=None, native_peak_decimal_gb=None,
                     telemetry_max_gap_seconds=None):
    """Keep reservation cost, measured CPU, sampled RSS and native GB distinct."""
    elapsed = number(elapsed_seconds, "elapsed")
    allocated = positive_int(allocated_cpus, "allocated CPUs")
    require(type(solver_threads) is int and solver_threads in GRID, "Invalid solver threads.")
    require(allocated >= solver_threads, "Insufficient allocated CPUs.")
    cpu = number(cpu_seconds, "measured process-tree CPU", nullable=True)
    app = number(application_peak_rss_bytes, "application high-water RSS", nullable=True)
    tree = number(sampled_tree_peak_rss_bytes, "sampled tree RSS", nullable=True)
    native = number(native_peak_decimal_gb, "observed native GB", nullable=True)
    gap = number(telemetry_max_gap_seconds, "maximum telemetry gap", nullable=True)
    return {
        "allocated_core_hours": allocated * elapsed / 3600,
        "configured_thread_hours": solver_threads * elapsed / 3600,
        "measured_process_cpu_hours": None if cpu is None else cpu / 3600,
        "average_observed_cpu_cores": None if cpu is None or elapsed == 0 else cpu / elapsed,
        "application_peak_rss_gib": None if app is None else app / 1024**3,
        "sampled_tree_peak_rss_gib": None if tree is None else tree / 1024**3,
        "observed_native_memory_gib": None if native is None else native * 10**9 / 1024**3,
        "telemetry_max_gap_seconds": gap,
    }


def comparable_speedup(reference, candidate):
    """No ratios for censored/partial/unequal-work or mismatched environment records."""
    for record in (reference, candidate):
        require(record["disposition"] == "complete_accepted_hierarchy"
                and record["censor_reason"] is None, "Incomplete/censored timing.")
        require(type(record["threads"]) is int and record["threads"] in GRID,
                "Invalid thread count.")
        require(number(record["optimization_seconds"], "optimization time") > 0,
                "Zero optimization time.")
    require(reference["threads"] == 1, "T1 reference required.")
    for key in ("work_scope_sha256", "environment_sha256"):
        require(isinstance(reference[key], str) and len(reference[key]) == 64
                and all(c in "0123456789abcdef" for c in reference[key])
                and candidate[key] == reference[key], f"Different/missing {key}.")
    speedup = reference["optimization_seconds"] / candidate["optimization_seconds"]
    return {"descriptive_speedup": speedup,
            "descriptive_efficiency": speedup / candidate["threads"],
            "causal_claim_allowed": False}
