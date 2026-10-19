"""Public P5 ledger consistency, not private residual replay or NPAD qualification."""

import json
import math
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs/evidence/s2_p5_2215308_review.json"
DATA = json.loads(LEDGER.read_text(encoding="utf-8"))
ARMS = DATA["arms"]


def test_external_anchors_and_original_flags():
    execution = DATA["execution"]
    assert execution["job_id"] == "2215308"
    assert execution["source_commit"] == "2145a043c0a532ea2322e8466d0a8d561da5c153"
    assert execution["archive_sha256"] == (
        "11f405b6fbc846a8209f93feb3b9decbdb031850134cb57b3f7ba339918830da"
    )
    assert execution["release_sha256"] == (
        "66e570a0e3b04b35aa583bd352019d0a6d23867b049479965d5f39164b4ab214"
    )
    assert execution["native_plan_sha256"] == (
        "ed303bf45c4a483cb8eae9bcf28c6ebe9329575e8749f3d95ecf554b82641058"
    )
    assert execution["source_blobs_verified_against_execution_commit"] == 677
    assert execution["five_arm_evidence_accounted"] is True
    assert execution["unrun"] == execution["unaccounted"] == []
    assert execution["validation_error"] is None
    assert execution["original_certificate_s2_closed"] is False
    assert execution["original_certificate_configuration_selected"] is False
    assert execution["fresh_private_input_revalidated_by_portable_auditor"] is False


def test_documentary_exit_is_not_execution_or_complete_hierarchy():
    decision = DATA["p5_exit_assessment"]
    assert decision["documentary_closure"] == "proposed_effective_only_after_authorized_P5_merge"
    assert decision["complete_hierarchy_arm_count"] == 0
    assert decision["independently_feasible_arm_count"] == 5
    for key in (
        "execution_permission_granted", "speedup_established",
        "causal_thread_superiority_established", "configuration_selected_for_downstream_execution",
        "additional_blocks_allowed", "repeats_admitted", "automatic_follow_on_allowed",
        "new_npad_execution_performed_in_P5", "main_sync_admitted",
    ):
        assert decision[key] is False
    assert decision["inconclusive_general_thread_ranking"] is True


def test_order_and_observed_smt_pool():
    contract = DATA["contract"]
    assert [a["threads"] for a in ARMS] == contract["order"] == [4, 1, 8, 2, 16]
    assert [a["step_id"] for a in ARMS] == [f"2215308.{i}" for i in range(5)]
    assert contract["affinity"] == list(range(8)) + list(range(32, 40))
    assert contract["allocated_logical_cpus"] == 16
    assert contract["physical_cores_observed"] == 8
    assert contract["smt_siblings_per_core_observed"] == 2
    assert contract["exclusive_node"] is False
    assert contract["production_isolation_certified"] is False


def test_unchanged_scientific_budget_and_input_scope():
    contract = DATA["contract"]
    assert contract["global_native_time_limit_seconds_per_arm"] == 3600
    assert contract["shared_late_return_export_seconds"] == 900
    assert contract["hard_arm_seconds"] == 5700
    assert contract["slurm_walltime_seconds"] == 43200
    assert contract["allocation_memory_gib"] == 192
    assert contract["solver_soft_memory_decimal_gb"] == 128
    assert contract["seed"] == 42 and contract["method_all_priorities"] == 2
    assert contract["configured_mip_gap"] == 0.1
    assert contract["compact_python_indices"] is contract["warm_start"] is False
    counts, size = DATA["input"]["counts"], DATA["input"]["size"]
    assert counts["warehouses"] == 300
    assert (counts["products"], counts["periods"], counts["scenarios"]) == (2, 60, 9)
    assert size["total_variables"] == 25107544 and size["routes_oc"] == 0


def test_new_transfer_does_not_rewrite_historical_limit():
    aggregate = DATA["resource_aggregate"]
    assert aggregate["native_inventory_members"] == 136
    assert aggregate["native_inventory_payload_bytes"] == 414969927
    assert aggregate["new_whole_block_expanded_limit_bytes"] == 1024**3
    assert aggregate["unchanged_per_arm_native_product_limit_bytes"] == 256 * 1024**2
    assert sum(a["incumbent_json_bytes"] for a in ARMS) < aggregate[
        "native_inventory_payload_bytes"
    ] < aggregate["new_whole_block_expanded_limit_bytes"]
    assert all(a["incumbent_json_bytes"] < 256 * 1024**2 for a in ARMS)


def test_preflight_keeps_the_original_failure_and_raw_report_boundary():
    preflight = DATA["preflight_existing_vector"]
    assert preflight["original_job_id"] == "2214305"
    assert preflight["original_failed_outcome_preserved"] is True
    assert preflight["changed_components"] == ["transport_dc", "transport_dd", "transport_od"]
    assert preflight["status"] == "bounded_transport_budget_order_difference"
    assert preflight["scientific_tolerances_changed"] is False
    assert preflight["original_claim_modified"] is False
    assert preflight["original_discarded_report_recovered"] is False
    assert preflight["raw_worker_report_sha256"] != preflight["fresh_report_sha256"]


@pytest.mark.parametrize("arm", ARMS, ids=lambda a: f"t{a['threads']}")
def test_arm_has_closed_control_and_native_time_censoring(arm):
    assert arm["scheduler"]["state"] == "COMPLETED"
    assert arm["scheduler"]["exit_code"] == "0:0"
    assert arm["control"]["return_code"] == 0
    assert arm["control"]["stop_reason"] is None
    assert arm["control"]["local_client_reaped"] is True
    assert arm["control"]["term"] is arm["control"]["kill"] is None
    assert arm["control"]["global_cleanup_proven"] is False
    assert arm["native"]["native_status_name"] == "TIME_LIMIT"
    assert 3600 < arm["native"]["native_runtime_seconds"] < 4500
    assert arm["economic_stage_observed"] is False
    assert [s["role"] for s in arm["stages"]] == ["unmet_demand", "emergency_capacity"]
    service, capacity = arm["stages"]
    assert (service["status"], service["pass_objective"], service["reported_gap"]) == (
        "OPTIMAL", 0, 1e100
    )
    assert (capacity["status"], capacity["retained_bound"], capacity["reported_gap"]) == (
        "TIME_LIMIT", 0, 1.0
    )


@pytest.mark.parametrize("arm", ARMS, ids=lambda a: f"t{a['threads']}")
def test_feasibility_does_not_relabel_the_conservative_prefix(arm):
    validation = arm["residual_validation"]
    assert validation["status"] == "accepted"
    assert validation["failed"] == 0 and validation["family_count"] == 32
    assert validation["absolute_tolerance"] == 1e-5
    assert validation["relative_tolerance"] == 1e-8
    assert arm["classification"]["disposition"] == "feasible_partial_hierarchy"
    assert arm["classification"]["independently_feasible"] is True
    assert arm["classification"]["certified_priority_prefix"] == 0
    assert arm["classification"]["censor_reason"] == "time_limit"
    assert arm["final_values"]["unmet_demand"] <= 1.01e-6


@pytest.mark.parametrize("arm", ARMS, ids=lambda a: f"t{a['threads']}")
def test_resource_scopes_and_arithmetic(arm):
    resources = arm["resources"]
    assert resources["root_peak_rss_gib"] == resources["root_peak_rss_kib"] / 1048576
    assert resources["sample_count"] > 800 and resources["sample_errors"] == 0
    assert 5 < resources["max_sample_gap_seconds"] < 5.34
    assert resources["continuous_coverage"] is False
    assert resources["lifetime_tree_cpu_seconds"] is None
    assert resources["root_cpu_seconds"] > 0
    assert arm["native"]["native_peak_decimal_gb"] > 0
    assert re.fullmatch(r"[0-9]+K", resources["slurm_step_max_rss_raw"])


@pytest.mark.parametrize("arm", ARMS, ids=lambda a: f"t{a['threads']}")
def test_retained_raw_report_and_product_bindings(arm):
    hashes = arm["preserved_artifact_sha256"]
    assert len(hashes) == 10
    assert all(re.fullmatch(r"[0-9a-f]{64}", value) for value in hashes.values())
    assert hashes["derived-review/worker-validation.json"] != hashes[
        "derived-review/fresh-report.json"
    ]
    assert arm["comparison"]["scientific_tolerances_changed"] is False
    assert arm["comparison"]["changed_components"] == [
        "transport_dc", "transport_dd", "transport_od"
    ]


def test_aggregates_and_candidate_are_descriptive_only():
    aggregate = DATA["resource_aggregate"]
    assert (
        sum(a["residual_validation"]["checked"] for a in ARMS)
        == aggregate["checked"] == 13511232
    )
    assert sum(a["resources"]["sample_count"] for a in ARMS) == aggregate["sample_count"] == 4227
    assert sum(a["resources"]["sample_errors"] for a in ARMS) == 0
    assert math.isclose(aggregate["allocated_logical_cpu_hours"], 16 * 22749 / 3600)
    assert math.isclose(aggregate["slurm_job_total_cpu_hours"], (13 * 3600 + 46 * 60 + 44) / 3600)
    best = min(ARMS, key=lambda a: a["final_values"]["emergency_capacity"])
    assert (
        best["threads"]
        == DATA["p5_exit_assessment"]["lowest_observed_capacity_score_threads"] == 4
    )
    assert DATA["p5_exit_assessment"]["configuration_selected_for_downstream_execution"] is False


def test_public_ledger_has_no_local_paths_credentials_or_embedded_vectors():
    text = LEDGER.read_text(encoding="utf-8")
    for marker in ("/home/", "C:/Users/", "D:/Downloads", "WLSSecret", "WLSAccessID", "gurobi.lic"):
        assert marker not in text
    assert "native/products/incumbent.json" in text  # Only sizes/hashes, not vector contents.
    assert len(text) < 40000


def test_closure_entry_points_are_consistent_and_linked():
    for name in (
        "AGENTS.md", "PROJECT_STATE.md", "docs/current_status.md", "docs/mvp2_hpc_roadmap.md",
        "docs/experiment_protocol.md", "docs/mvp2_s2_closure_campaign.md",
    ):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "mvp2_s2_p5_closure.md" in text
    report = (ROOT / "docs/mvp2_s2_p5_closure.md").read_text(encoding="utf-8")
    assert DATA["execution"]["archive_sha256"] in report
    assert "not sixteen physical cores" in report
    assert "s2_closed=false" in report
    assert "effective only" in report
