"""Resource qualification and fail-closed checks for the isolated E1 profile."""

import copy
import io
import json
import tarfile

import pytest

from scripts import pyomo_h400_e1 as e1

CAMPAIGN = "a" * 64
SOURCE = "b" * 40


@pytest.fixture
def records():
    binding = e1.contract.reference(400)
    result = {}
    for i, case in enumerate(e1.CASES, 1):
        t = case["threads"]
        gurobi = case["solver"] == "gurobi"
        solver = "gurobipy" if gurobi else "highspy"
        options = (
            {
                "TimeLimit": 28800, "MIPGap": 0.01, "Threads": t, "Seed": 42,
                "FeasibilityTol": 1e-9, "IntFeasTol": 1e-9, "Presolve": -1,
                "Method": -1, "NodeMethod": -1, "Heuristics": 0.05, "Cuts": -1,
                "ConcurrentMIP": 1,
            }
            if gurobi else {
                "time_limit": 28800, "mip_rel_gap": 0.01, "threads": t,
                "random_seed": 42, "mip_feasibility_tolerance": 1e-9, "parallel": "on",
            }
        )
        row = {
            "job_id": f"30100{i}", "cell": case, "source_commit": SOURCE,
            "campaign_sha256": CAMPAIGN, "profile": e1.contract.PROFILE,
            "status": "observation_collected",
            "operational_receipts_closed": True, "native_result_returned": True,
            "incumbent_validation_rejected": False, "worker_affinity_logical_cpus": 16,
            "input_binding": {k: binding[k] for k in e1.INPUT_FIELDS},
            "matrix_sha256": e1.ORIGINAL_MATRIX, "bounds_sha256": e1.ORIGINAL_BOUNDS,
            "hardware_class_sha256": "c" * 64,
            "common_linear_matrix": {
                "sha256": e1.ORIGINAL_MATRIX, "variables": 42106944,
                "schema_version": "ordered-pyomo-linear-matrix-v1",
            },
            "reformulation": {
                "bounds_sha256": e1.ORIGINAL_BOUNDS,
                "policy": e1.contract.POLICY,
                "equivalence": "physical_investment_projection_and_optimal_scalar_value",
                "entire_redundant_slack_region_preserved": False,
            },
            "effective_parameters": options,
            "native_status": (
                "TerminationCondition.optimal" if gurobi else "TerminationCondition.maxTimeLimit"
            ),
            "has_usable_incumbent": gurobi,
            "classification": "validated_feasible" if gurobi else "no_usable_incumbent",
            "original_validation_status": "accepted" if gurobi else "rejected",
            "objective": 100.0 if gurobi else None, "bound": 99.5,
            "common_gap": 0.005 if gurobi else None, "quality_target_met": gurobi,
            "resource_observation": {
                "status": "timely_samples",
                "sampled_worker_tree_peak_bytes": 172052795392 if gurobi and t == 16 else 140*e1.GIB,
            },
        }
        memory = {
            "scope": "slurm_job_cgroup_v2", "job_id": row["job_id"],
            "campaign_sha256": CAMPAIGN, "source_commit": SOURCE,
            "effective_limit_bytes": e1.MEMORY_BYTES, "peak_bytes": 165*e1.GIB,
            "oom_delta": 0, "oom_kill_delta": 0, "guard_triggered": False,
            "solver_interface": "appsi_" + case["solver"],
            "solver_versions": {k: e1.contract.PACKAGES[k] for k in ("pyomo", solver)},
            "highs_native_version": None if gurobi else e1.contract.PACKAGES["highspy"],
        }
        result[case["id"]] = row, memory
    return copy.deepcopy(result)


def test_plan_limits_and_no_submission():
    planned = e1.plan()
    assert planned["profile"]["memory_mib"] == 196608
    assert len(planned["cells"]) == 4
    assert planned["gurobi_concurrent_mip"] == 1
    assert planned["submission_authorized"] is False


def test_relaxed_worker_rule_keeps_old_gate_distinct(records):
    result = e1.evaluate(records, CAMPAIGN, SOURCE)
    worst = result["cells"]["h400-w-sto-gurobi-t16-r1"]
    assert worst["baseline_worker_passed"] is False and worst["e1_worker_passed"] is True
    assert result["status"] == "e1_resource_criteria_met"
    assert result["automatic_follow_on_allowed"] is False
    assert result["cells"]["h400-w-sto-highs-t16-r1"]["outcome"] == "time_limit_without_incumbent"


@pytest.mark.parametrize("field", ["worker", "job"])
def test_both_memory_scopes_gate_progression(records, field):
    row, memory = records["h400-w-sto-gurobi-t16-r1"]
    if field == "worker":
        row["resource_observation"]["sampled_worker_tree_peak_bytes"] = (
            e1.limits()["e1_worker_peak_bytes"] + 1
        )
    else:
        memory["peak_bytes"] = e1.limits()["e1_job_peak_bytes"] + 1
    assert e1.evaluate(records, CAMPAIGN, SOURCE)["status"] == "e1_resource_criteria_rejected"


@pytest.mark.parametrize(("field", "bad"), [
    ("scope", "worker_step"),
    ("guard_triggered", True),
    ("oom_delta", 1),
    ("oom_kill_delta", 1),
    ("effective_limit_bytes", 208 * e1.GIB),
    ("job_id", "2232382"),
])
def test_memory_receipt_requires_exact_scope_and_no_oom(records, field, bad):
    records["h400-w-sto-gurobi-t16-r1"][1][field] = bad
    with pytest.raises(ValueError, match="job-cgroup receipt"):
        e1.evaluate(records, CAMPAIGN, SOURCE)


@pytest.mark.parametrize("case", ["clean", "limit_hit", "mixed_scope"])
def test_controller_specific_v1_receipts(records, case):
    for _, memory in list(records.values())[int(case == "mixed_scope"):]:
        memory.update(
            scope="slurm_job_cgroup_v1",
            failcnt_delta=int(case == "limit_hit"),
            under_oom_at_end=0,
        )
        del memory["oom_delta"]
    if case == "clean":
        assert e1.evaluate(records, CAMPAIGN, SOURCE)["status"] == "e1_resource_criteria_met"
        return
    match = "job-cgroup receipt" if case == "limit_hit" else "controller differs"
    with pytest.raises(ValueError, match=match):
        e1.evaluate(records, CAMPAIGN, SOURCE)


def test_rejects_original_campaign_or_reused_job(records):
    with pytest.raises(ValueError, match="distinct E1"):
        e1.evaluate(records, e1.ORIGINAL_CAMPAIGN, SOURCE)
    records["h400-w-sto-gurobi-t16-r1"][0]["job_id"] = "2232382"
    with pytest.raises(ValueError, match="E1 cell"):
        e1.evaluate(records, CAMPAIGN, SOURCE)


def test_rejects_concurrent_mip_variant(records):
    records["h400-w-sto-gurobi-t16-r1"][0]["effective_parameters"]["ConcurrentMIP"] = 2
    with pytest.raises(ValueError, match="native settings"):
        e1.evaluate(records, CAMPAIGN, SOURCE)


def test_rejects_changed_h400_matrix(records):
    row, _ = records["h400-w-sto-gurobi-t16-r1"]
    row["matrix_sha256"] = row["common_linear_matrix"]["sha256"] = "e" * 64
    with pytest.raises(ValueError, match="Matrix or bounds"):
        e1.evaluate(records, CAMPAIGN, SOURCE)


def test_rejects_fabricated_gap_for_censored_run(records):
    records["h400-w-sto-highs-t16-r1"][0]["common_gap"] = 0.0
    with pytest.raises(ValueError, match="censored"):
        e1.evaluate(records, CAMPAIGN, SOURCE)


def test_bundle_binds_memory_to_archive(tmp_path, records):
    for identity, (row, memory) in records.items():
        directory = tmp_path / identity
        directory.mkdir()
        archive = directory / "evidence.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            for name, data in (("campaign_observation.json", row), ("memory_receipt.json", memory)):
                raw = json.dumps(data).encode()
                member = tarfile.TarInfo(name)
                member.size = len(raw)
                tar.addfile(member, io.BytesIO(raw))
        (directory / "memory_receipt.json").write_text(json.dumps(memory))
        (directory / "collection.json").write_text(json.dumps({
            "sha256": e1.hashlib.sha256(archive.read_bytes()).hexdigest(), "observation": row
        }))
    assert e1.read_bundle(tmp_path) == records
    path = tmp_path / "h400-w-sto-gurobi-t16-r1/memory_receipt.json"
    receipt = json.loads(path.read_bytes())
    path.write_text(json.dumps({**receipt, "peak_bytes": 1}))
    with pytest.raises(ValueError, match="Archive and memory"):
        e1.read_bundle(tmp_path)
