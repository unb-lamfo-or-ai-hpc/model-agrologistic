"""Inspect receipts for the proposed, separate h400 E1 qualification."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import tarfile
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import pyomo_scaling_contract as contract

GIB = 1024**3
MEMORY_BYTES = contract.PROFILE["memory_mib"] * 1024**2
BASELINE_WORKER_PERCENT = 80
E1_WORKER_PERCENT = 85
E1_JOB_PERCENT = 90
ORIGINAL_CAMPAIGN = "3cae7c318032108caa936d70b2883f20d055066f89a78e24610f261832763b58"
ORIGINAL_JOBS = {"2232379", "2232380", "2232381", "2232382"}
ORIGINAL_MATRIX = "d90f1121a75817702db52fa0d190642433feb66d111743811fca2c653b649330"
ORIGINAL_BOUNDS = "8d0d3951b7ab2fd6e0ef1c99c088d6cf1864bffbe599f032965c9d3aab598eed"
ORIGINAL_HARDWARE = "32629b1e2a3e3eb680f7f45d987f722fbd913f557e4c3dc8a3e0902b4bae0260"
CASES = (
    contract.cell(400, "gurobi", 1, 1),
    contract.cell(400, "highs", 1, 1),
    contract.cell(400, "highs", 16, 1),
    contract.cell(400, "gurobi", 16, 1),
)
INPUT_FIELDS = (
    "workbook_sha256",
    "warehouse_selection_sha256",
    "mathematical_contract_sha256",
    "scenario_probabilities_sha256",
    "loader_sha256",
    "model_sha256",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def hex_digest(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def limits():
    return {
        "allocation_bytes": MEMORY_BYTES,
        "baseline_worker_peak_bytes": MEMORY_BYTES * BASELINE_WORKER_PERCENT // 100,
        "e1_worker_peak_bytes": MEMORY_BYTES * E1_WORKER_PERCENT // 100,
        "e1_job_peak_bytes": MEMORY_BYTES * E1_JOB_PERCENT // 100,
    }


def plan():
    return {
        "status": "proposed_e1_profile",
        "population": 400,
        "profile": contract.PROFILE,
        "limits": limits(),
        "cells": CASES,
        "gurobi_concurrent_mip": 1,
        "highs_parallel": "on",
        "submission_authorized": False,
        "automatic_follow_on_allowed": False,
    }


def terminal_outcome(row):
    termination = row["native_status"]
    require(
        termination in {"TerminationCondition.optimal", "TerminationCondition.maxTimeLimit"},
        "Unexpected solver termination.",
    )
    if row["has_usable_incumbent"] is False:
        require(
            termination == "TerminationCondition.maxTimeLimit"
            and row["classification"] == "no_usable_incumbent"
            and row["objective"] is None and row["common_gap"] is None
            and row["quality_target_met"] is False,
            "Unusable incumbent must remain a censored time-limit outcome.",
        )
        return "time_limit_without_incumbent"
    z, b, gap = (row[key] for key in ("objective", "bound", "common_gap"))
    require(
        row["has_usable_incumbent"] is True
        and row["classification"] == "validated_feasible"
        and row["original_validation_status"] == "accepted"
        and all(type(v) in {int, float} and math.isfinite(v) for v in (z, b, gap))
        and z != 0 and b <= z
        and math.isclose(gap, (z - b) / abs(z), rel_tol=1e-8, abs_tol=1e-12),
        "Validated incumbent, bound and common gap required.",
    )
    at_target = gap <= row["cell"]["mip_gap_target"]
    require(row["quality_target_met"] is at_target, "Quality target flag differs.")
    return "validated_at_target" if at_target else "validated_above_target"


def check_memory(row, memory):
    observed = row["resource_observation"]
    worker = observed["sampled_worker_tree_peak_bytes"]
    job = memory["peak_bytes"]
    require(
        observed["status"] == "timely_samples"
        and type(worker) in {int, float} and math.isfinite(worker) and worker > 0,
        "Timely worker-tree memory observation required.",
    )
    scope = memory["scope"]
    counters = {
        "slurm_job_cgroup_v1": ("failcnt_delta", "under_oom_at_end", "oom_kill_delta"),
        "slurm_job_cgroup_v2": ("oom_delta", "oom_kill_delta"),
    }
    require(
        scope in counters
        and memory["job_id"] == row["job_id"]
        and memory["campaign_sha256"] == row["campaign_sha256"]
        and memory["source_commit"] == row["source_commit"]
        and memory["effective_limit_bytes"] == MEMORY_BYTES
        and type(job) is int and job > 0
        and all(type(memory.get(key)) is int and memory[key] == 0 for key in counters[scope])
        and memory["guard_triggered"] is False,
        "Owned 192 GiB job-cgroup receipt without memory termination required.",
    )
    caps = limits()
    return {
        "job_memory_scope": scope,
        "worker_peak_bytes": worker,
        "job_peak_bytes": job,
        "baseline_worker_passed": worker <= caps["baseline_worker_peak_bytes"],
        "e1_worker_passed": worker <= caps["e1_worker_peak_bytes"],
        "e1_job_passed": job <= caps["e1_job_peak_bytes"],
    }


def evaluate(records, campaign_sha, source_sha, *, prefix=False, cases=CASES, excluded_jobs=()):
    require(
        hex_digest(campaign_sha) and campaign_sha != ORIGINAL_CAMPAIGN
        and re.fullmatch(r"[0-9a-f]{40}", source_sha) is not None,
        "A distinct E1 campaign and exact source identity are required.",
    )
    count = len(records)
    require(
        0 < count <= len(cases) if prefix else count == len(cases), "Exact h400 cells required."
    )
    expected = {cell["id"]: cell for cell in cases[:count]}
    require(set(records) == set(expected), "Records must follow the frozen h400 cell order.")
    reference = contract.reference(400)
    results, jobs, bindings = {}, set(), set()
    for identity, cell in expected.items():
        row, memory = records[identity]
        job_id = row["job_id"]
        require(
            isinstance(job_id, str) and re.fullmatch(r"[1-9][0-9]*", job_id)
            and job_id not in jobs and job_id not in ORIGINAL_JOBS and job_id not in excluded_jobs
            and row["cell"] == cell and row["source_commit"] == source_sha
            and row["campaign_sha256"] == campaign_sha
            and row["profile"] == contract.PROFILE
            and row["status"] == "observation_collected"
            and row["operational_receipts_closed"] is True
            and row["native_result_returned"] is True
            and row["incumbent_validation_rejected"] is False
            and row["worker_affinity_logical_cpus"] == 16,
            "E1 cell, allocation, affinity or original validation receipt differs.",
        )
        jobs.add(job_id)
        require(
            row["input_binding"] == {k: reference[k] for k in INPUT_FIELDS},
            "Original h400 inputs differ.",
        )
        binding = tuple(
            row[key] for key in ("matrix_sha256", "bounds_sha256", "hardware_class_sha256")
        )
        require(
            all(hex_digest(digest) for digest in binding),
            "Missing matrix, bounds or hardware digest.",
        )
        bindings.add(binding)
        matrix, reformulation = row["common_linear_matrix"], row["reformulation"]
        require(
            matrix["sha256"] == binding[0] == ORIGINAL_MATRIX
            and reformulation["bounds_sha256"] == binding[1] == ORIGINAL_BOUNDS
            and binding[2] == ORIGINAL_HARDWARE,
            "Matrix or bounds receipt differs, or historical hardware class differs.",
        )
        contract.effective_parameters(cell, {
            "pyomo_solver_interface": memory["solver_interface"],
            "solver_versions": memory["solver_versions"],
            "highs_native_version": memory.get("highs_native_version"),
            "effective_native_options": row["effective_parameters"],
            "pyomo_reformulation": reformulation,
            "common_linear_matrix": matrix,
        })
        results[identity] = {
            "job_id": job_id,
            "outcome": terminal_outcome(row),
            **check_memory(row, memory),
        }
    require(len(bindings) == 1, "Matrix, bounds or hardware differs across pilots.")
    require(
        len({result["job_memory_scope"] for result in results.values()}) == 1,
        "Memory controller differs across pilots.",
    )
    passed = all(r["e1_worker_passed"] and r["e1_job_passed"] for r in results.values())
    return {
        "status": "e1_resource_criteria_met" if passed else "e1_resource_criteria_rejected",
        "cells": results,
        "limits": limits(),
        "automatic_follow_on_allowed": False,
    }


def regular(path, root):
    require(
        path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root),
        "Expected a regular receipt under the supplied bundle.",
    )
    return path


def json_receipt(path, root):
    file = regular(path, root)
    require(file.stat().st_size <= 1024**2, "Receipt exceeds 1 MiB.")
    return json.loads(file.read_bytes())


def read_bundle(directory):
    return {cell["id"]: read_cell(directory, cell["id"]) for cell in CASES}


def read_cell(directory, identity):
    root = directory.resolve(strict=True)
    path = root / identity
    require(path.is_dir() and not path.is_symlink(), "Missing or linked E1 cell directory.")
    marker = json_receipt(path / "collection.json", root)
    memory = json_receipt(path / "memory_receipt.json", root)
    archive = regular(path / "evidence.tar.gz", root)
    with archive.open("rb") as stream:
        require(
            hashlib.file_digest(stream, "sha256").hexdigest() == marker["sha256"],
            "E1 evidence archive hash differs.",
        )
    with tarfile.open(archive, "r:gz") as tar:
        members = {name: [] for name in ("campaign_observation.json", "memory_receipt.json")}
        expanded = 0
        for count, member in enumerate(tar, 1):
            expanded += member.size
            require(
                count <= contract.PROFILE["max_regular_members"]
                and expanded <= contract.PROFILE["expanded_transfer_bytes"],
                "E1 archive exceeds its declared bounds.",
            )
            if member.name in members:
                members[member.name].append(member)
        require(
            all(
                len(items) == 1 and items[0].isfile() and items[0].size <= 1024**2
                for items in members.values()
            ),
            "Unique bounded archived observation and memory receipt required.",
        )
        with tar.extractfile(members["campaign_observation.json"][0]) as stream:
            observation = json.load(stream)
        with tar.extractfile(members["memory_receipt.json"][0]) as stream:
            require(json.load(stream) == memory, "Archive and memory receipt disagree.")
    require(observation == marker["observation"], "Archive and collection receipt disagree.")
    return observation, memory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("plan")
    review = actions.add_parser("review")
    review.add_argument("bundle", type=Path)
    review.add_argument("--campaign-sha", required=True)
    review.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    result = plan() if args.action == "plan" else evaluate(
        read_bundle(args.bundle), args.campaign_sha, args.source_sha
    )
    print(json.dumps(result, indent=2, allow_nan=False))
    return int(result["status"] == "e1_resource_criteria_rejected")


if __name__ == "__main__":
    raise SystemExit(main())
