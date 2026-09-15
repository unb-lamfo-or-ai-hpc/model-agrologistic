"""Conservative scheduler observations and metadata-only deposit planning."""

import json
import subprocess

import pytest

from scripts.collect_npad_readiness import (
    capture,
    file_record,
    resource_observations,
    scheduler_test_commands,
)
from scripts.plan_zenodo_deposit import KNOWN_INVALID_500, build_plan

SOURCE = {"source_file": "Warehouses_Existing_Candidate_All.xlsx", "source_sha256": "a" * 64}


def test_scheduler_commands_never_submit():
    commands = scheduler_test_commands("sxdsouza", "intel-256", "qos1", 25)
    assert len(commands) == 2
    assert all(c[:2] == ["sbatch", "--test-only"] for c in commands)
    assert all("--time=12:00:00" in c for c in commands)
    assert "--cpus-per-task=25" in commands[1]
    assert len(scheduler_test_commands("a", "p", "q", None)) == 1


def item(path, digest="b" * 64, size=10):
    return {"path": path, "size_bytes": size, "sha256": digest,
            "approved_for_upload": True, "status": "review_rights_and_contents"}


def test_partition_allow_all_does_not_authorize_user_qos():
    report = resource_observations(
        "ufrn|sxdsouza||preempt||\n", "AllowQos=ALL MaxMemPerCPU=8000",
        account="sxdsouza", partition="intel-256", qos="qos1")
    assert report["qos_explicitly_observed"] is False
    assert report["arithmetic_minimum_allocated_cpus"] == 25
    assert report["solver_threads"] == 4
    assert report["allocation_review_required"] is True


def test_unrelated_association_is_not_used():
    report = resource_observations(
        "ufrn|other||qos1||\nufrn|sxdsouza|gpu|qos1||\n", "",
        account="sxdsouza", partition="intel-256", qos="qos1")
    assert report["qos_explicitly_observed"] is False
    assert report["arithmetic_minimum_allocated_cpus"] is None


def test_explicit_qos_still_requires_scheduler_check():
    report = resource_observations(
        "ufrn|sxdsouza||preempt,qos1||", "MaxMemPerCPU=64000",
        account="sxdsouza", partition="intel-256", qos="qos1")
    assert report["qos_explicitly_observed"] is True
    assert "confirmation" in report["qos_qualification"]


def test_command_missing_is_retained(monkeypatch):
    def missing(*args, **kwargs):
        raise FileNotFoundError("sacctmgr missing")
    monkeypatch.setattr(subprocess, "run", missing)
    assert capture(["sacctmgr"])["return_code"] is None


def test_file_hash_and_mismatch(tmp_path):
    f = tmp_path / "source.xlsx"
    assert file_record(f)["exists"] is False
    f.write_bytes(b"fixture")
    assert file_record(f, "a" * 64)["matches_expected_sha256"] is False
    assert file_record(f, file_record(f)["sha256"])["matches_expected_sha256"] is True


def test_plan_requires_review_even_when_inventory_claims_approval():
    plan = build_plan({"files": [item("templates/source.xlsx", "a" * 64),
                                 item("processed/copy.xlsx", "a" * 64)]}, SOURCE)
    assert plan["file_count"] == 2 and plan["total_bytes"] == 20
    assert plan["duplicate_hash_groups"] == 1
    assert plan["population_source_status"] == "hash_present_rights_pending"
    assert plan["publication_authorized"] is False
    assert all(not r["approved_for_upload"] for r in plan["files"])
    assert all(r["same_hash_file_count"] == 2 for r in plan["files"])


@pytest.mark.parametrize("path", ["../bad", "/absolute", "C:/data", "a\\b", "./x", "a//b"])
def test_unsafe_paths_rejected(path):
    with pytest.raises(ValueError):
        build_plan({"files": [item(path)]}, SOURCE)


def test_duplicate_paths_rejected():
    with pytest.raises(ValueError):
        build_plan({"files": [item("x"), item("x")]}, SOURCE)


@pytest.mark.parametrize("size", [-1, 2.1, True])
def test_invalid_sizes_rejected(size):
    with pytest.raises(ValueError):
        build_plan({"files": [item("x", size=size)]}, SOURCE)


@pytest.mark.parametrize("path,package", [
    (".env.production", "excluded"), ("secrets/key.json", "excluded"),
    ("results/validation/quality/dist/project.whl", "excluded"),
    ("results/validation/pr25-final/run.json", "validation_evidence"),
    ("results/hpc/nine-connectivity-run/a.json", "campaign_in_progress"),
    ("results/releases/v1/SHA256SUMS", "historical_release"),
    ("results/reproducibility/plots/a.png", "publication_outputs"),
])
def test_package_classification(path, package):
    plan = build_plan({"files": [item(path)]}, SOURCE)
    assert plan["files"][0]["proposed_package"] == package


def test_known_invalid_hash_cannot_become_valid_input_by_renaming():
    plan = build_plan({"files": [item("templates/renamed.xlsx", KNOWN_INVALID_500)]}, SOURCE)
    assert plan["files"][0]["review_status"] == "blocked_for_validated_input_publication"
    assert plan["population_source_status"] == "missing_expected_source_hash"


def test_empty_inventory_is_a_valid_empty_draft():
    plan = build_plan({"files": []}, SOURCE)
    assert plan["file_count"] == 0
    assert plan["status"] == "draft_only"
    json.dumps(plan, allow_nan=False)
