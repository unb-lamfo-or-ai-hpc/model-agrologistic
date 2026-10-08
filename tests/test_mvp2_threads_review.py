"""Portable review regressions use synthetic public solutions, never licensed evidence."""

import copy
import io
import json
import tarfile

import pytest

from scripts import review_mvp2_threads as review
from src.logic.solution_validation import COST_NAMES


def encoded(value):
    return json.dumps(value).encode()


def synthetic_arm():
    threads = 4
    screen = review.screen
    implementation = screen.implementation_identity()
    spec = screen.spec(threads, review.QUALIFICATION)
    experiment = json.loads(json.dumps(review._spec_payload(spec)))
    experiment["workbook"] = (review.QUALIFICATION / "analytical-fixture").as_posix()
    payload = copy.deepcopy(experiment)
    payload.pop("resume_evpi_vss")
    payload["implementation"] = implementation["sha256"]
    identity = screen.transfer.digest(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    )
    flows, inventories = [], []
    for scenario, supply, demand in [("base", 40, 20), ("otimista", 100, 50)]:
        flows.extend(
            [
                {
                    "route_type": "OD",
                    "scenario": scenario,
                    "origin": "O1",
                    "warehouse": "W1",
                    "product": "soy",
                    "period": "t1",
                    "value": supply,
                },
                {
                    "route_type": "DC",
                    "scenario": scenario,
                    "warehouse": "W1",
                    "customer": "C1",
                    "product": "soy",
                    "period": "t1",
                    "value": demand,
                },
            ]
        )
        inventories.append(
            {
                "scenario": scenario,
                "warehouse": "W1",
                "product": "soy",
                "period": "t1",
                "value": supply - demand,
            }
        )
    costs = dict.fromkeys(COST_NAMES, 0.0)
    costs.update(
        expansion_fixed=10, expansion_variable=20, transport_od=85, transport_dc=42.5, storage=42.5
    )
    stages = review.stage_degradation_records(
        [
            {
                "stage_role": role,
                "objective_value": 200 if role == "economic_cost" else 0,
                "objective_bound": 200 if role == "economic_cost" else 0,
                "mip_gap": 0,
                "status": "OPTIMAL",
                "status_code": 2,
            }
            for role in screen.ROLES
        ],
        {"unmet_demand": 0, "emergency_capacity": 0, "economic_cost": 200},
        mip_gap=0.1,
        mip_gap_abs=1e-10,
        objective_abs_tol=spec.model.feasibility_tolerance,
    )
    result = review.OptimizationResult(
        status="optimal",
        objective_value=0,
        cost_breakdown=costs,
        warehouse_decisions=[
            {
                "warehouse": "W1",
                "open": 1,
                "candidate_capacity": 0,
                "expand": 1,
                "expansion_capacity": 10,
                "bulkify": 0,
                "bulk_capacity": 0,
                "effective_static_capacity": 50,
            }
        ],
        flows=flows,
        inventories=inventories,
        metrics={
            "objective_values": {"unmet_demand": 0, "emergency_capacity": 0, "economic_cost": 200}
        },
        metadata={
            "implementation_identity": implementation,
            "run_identity": identity,
            "lexicographic_stages": stages,
        },
    )
    validation = review.validate_solution(
        review.prepare_model_data(screen.fixture_data(), spec.model), spec.model, result
    )
    assert validation["status"] == "accepted"
    result_payload = {
        k: getattr(result, k)
        for k in (
            "status",
            "objective_value",
            "cost_breakdown",
            "warehouse_decisions",
            "flows",
            "inventories",
            "unmet_demand",
            "emergency_capacity",
            "metrics",
            "metadata",
        )
    }
    prefix = "miniatures/threads-4/"
    assets = {prefix + n: b"{}" for n in screen.PRODUCTS if n != "run_completion.json"}
    assets[prefix + "result.json"] = encoded(
        {
            "experiment": experiment,
            "result": result_payload,
            "execution": {
                "slurm_job_id": review.JOB,
                "source_commit_declared": review.SOURCE,
                "slurm_array_job_id": None,
                "slurm_array_task_id": None,
            },
        }
    )
    assets[prefix + "independent_validation.json"] = encoded(validation)
    assets[prefix + "run_summary.json"] = encoded(
        {
            "status": "optimal",
            "independent_validation_status": "accepted",
            "lexicographic_completed_stage_count": 3,
            "lexicographic_overall_status": "complete",
            "optimization_seconds": 0.1,
            "end_to_end_seconds": 0.2,
            "total_unmet_demand": 0,
            "total_emergency_capacity": 0,
            "economic_cost": 200,
        }
    )
    assets[prefix + "solver_diagnostics.json"] = encoded(
        {
            "effective_stage_parameters": {
                role: {
                    "Threads": 4,
                    "Method": 2,
                    "TimeLimit": 60,
                    "SoftMemLimit": 1,
                    "MIPGap": 0.1,
                    "MIPGapAbs": 1e-10,
                    "NumericFocus": 1,
                }
                for role in screen.ROLES
            }
        }
    )
    assets[prefix + "resources/resource_timeseries.csv"] = (
        b"observation_errors,cgroup_limit_bytes\n,17179869184\n"
    )
    assets[prefix + "resources/stage_progress.csv"] = b"event\nMULTIOBJ\n"
    assets[prefix + "resources/termination.json"] = encoded(
        {
            "execution_status": "optimal",
            "exception_type": None,
            "dropped_samples": {"resource": 0, "progress": 0},
            "inspection_errors": [],
            "samples": {"resource": 1, "progress": 1},
        }
    )
    manifest_names = [
        "runtime_capabilities.json",
        "allocation_receipt.json",
        "matrix_statistics.json",
        "resource_timeseries.csv",
        "stage_progress.csv",
        "termination.json",
    ]
    assets[prefix + "resources/manifest.json"] = encoded(
        {
            "status": "closed",
            "artifacts": {
                n: screen.transfer.digest(assets[prefix + "resources/" + n]) for n in manifest_names
            },
        }
    )
    close_arm(assets, identity)
    return assets, implementation


def close_arm(assets, identity=None):
    prefix = "miniatures/threads-4/"
    if identity is None:
        identity = json.loads(assets[prefix + "run_completion.json"])["run_identity"]
    assets[prefix + "run_completion.json"] = encoded(
        {
            "schema_version": 1,
            "status": "complete",
            "run_identity": identity,
            "artifacts": {
                n: review.screen.transfer.digest(assets[prefix + n])
                for n in review.screen.PRODUCTS
                if n != "run_completion.json"
            },
        }
    )


def test_public_solution_revalidated_without_solver_or_local_runtime_relabelling():
    assets, implementation = synthetic_arm()
    result = review.review_arm(assets, 4, implementation)
    assert result["status"] == "accepted" and result["residual_families"] == 29
    assert result["economic_cost"] == 200


@pytest.mark.parametrize("drift", ["spec", "runtime", "residual", "stage", "settings", "telemetry"])
def test_resealed_but_semantically_changed_products_rejected(drift):
    assets, implementation = synthetic_arm()
    name = "miniatures/threads-4/" + (
        "solver_diagnostics.json"
        if drift == "settings"
        else "resources/termination.json"
        if drift == "telemetry"
        else "result.json"
    )
    value = json.loads(assets[name])
    if drift == "spec":
        value["experiment"]["solver"]["threads"] = 8
    elif drift == "runtime":
        value["result"]["metadata"]["implementation_identity"]["python"] = "changed"
    elif drift == "residual":
        value["result"]["flows"][0]["value"] = 39
    elif drift == "stage":
        value["result"]["metadata"]["lexicographic_stages"][0]["status"] = "TIME_LIMIT"
    elif drift == "settings":
        value["effective_stage_parameters"]["economic_cost"]["Threads"] = 8
    else:
        value["inspection_errors"] = ["missing observation"]
    assets[name] = encoded(value)
    close_arm(assets)
    with pytest.raises(ValueError):
        review.review_arm(assets, 4, implementation)


@pytest.mark.parametrize("name", ["../escape", "/absolute", "a\\b", "a//b", "C:secret"])
def test_archive_member_paths_rejected(tmp_path, name):
    archive = tmp_path / "test.tar.gz"
    with tarfile.open(archive, "w:gz") as package:
        member = tarfile.TarInfo(name)
        member.size = 1
        package.addfile(member, io.BytesIO(b"x"))
    with pytest.raises(ValueError, match="Unsafe"):
        review.safe_assets(archive, review.screen.file_sha256(archive))


@pytest.mark.parametrize("kind", ["duplicate", "link", "size"])
def test_ambiguous_or_unbounded_archive_rejected(tmp_path, kind):
    archive = tmp_path / "test.tar.gz"
    with tarfile.open(archive, "w:gz") as package:
        member = tarfile.TarInfo("safe")
        if kind == "link":
            member.type = tarfile.SYMTYPE
            member.linkname = "secret"
            package.addfile(member)
        elif kind == "size":
            member.size = 1_000_001
            package.addfile(member, io.BytesIO(b"x" * member.size))
        else:
            member.size = 1
            package.addfile(member, io.BytesIO(b"x"))
            package.addfile(member, io.BytesIO(b"x"))
    with pytest.raises(ValueError):
        review.safe_assets(archive, review.screen.file_sha256(archive))


def test_transfer_cannot_trust_only_declared_acceptance_or_ignore_extra_files():
    with pytest.raises(ValueError, match="allowlist"):
        review.review_assets(
            {
                "collection.json": encoded({"status": "accepted", "artifacts": {}}),
                "secret.json": b"not allowed",
            }
        )
    with pytest.raises(ValueError, match="hash"):
        review.hash_catalog({"product": b"changed"}, {"product": "0" * 64})
