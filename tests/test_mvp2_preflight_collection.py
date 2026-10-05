"""Failed input jobs remain auditable without receipt acceptance or submission."""

import json
import tarfile

import pytest

from scripts import collect_mvp2_pair_preflight as collector
from scripts import preflight_mvp2_resource_pair as gate
from scripts import prepare_mvp2_resource_contrasts as contrasts
from src.logic.run_integrity import file_sha256
from tests.test_mvp2_pair_preflight import inspector
from tests.test_mvp2_resource_contrasts import fixture


def run_fixture(tmp_path, *, accepted=False):
    reference, qualification = fixture(tmp_path, "h300-warehouse")
    run = tmp_path / "run"
    contrasts.prepare(reference, file_sha256(reference), 0, qualification,
                      run / "prepared", "h300-warehouse")
    audit = run / "audit"
    audit.mkdir()
    (audit / "submission.txt").write_text("MVP2_PAIR_PREFLIGHT_JOB=123\n")
    (audit / "source_commit.txt").write_text("test-only-source\n")
    (audit / "tool_hashes.json").write_text(json.dumps(gate.tool_identity()))
    (audit / "slurm-123.out").write_text("test-only traceback\n")
    if accepted:
        gate.preflight(run / "prepared/resource_contrast_plan.json", audit / "preflight",
                       {"job_id": "123"}, inspector=inspector)
    return run


def test_failed_job_packages_logs_and_partial_products_without_acceptance(tmp_path):
    run = run_fixture(tmp_path)
    folder = run / "audit/preflight/mvp2_h300_warehouse_control"
    folder.mkdir(parents=True)
    (folder / "preflight.json").write_text('{"total_variables":25107544}')
    (run / "audit/gurobi.lic").write_text("DO NOT PACKAGE")
    summary, archive, checksum = collector.collect(
        run, tmp_path / "collection", "123", accounting_text="123|FAILED|1:0|00:01:42\n"
    )
    assert summary["status"] == "terminal_failure"
    assert summary["receipt_validation_errors"]
    assert file_sha256(archive) == checksum
    with tarfile.open(archive) as package:
        assert "audit/slurm-123.out" in package.getnames()
        assert "audit/preflight/mvp2_h300_warehouse_control/preflight.json" in package.getnames()
        assert "audit/gurobi.lic" not in package.getnames()
        assert json.load(package.extractfile("collection.json"))["status"] == "terminal_failure"


@pytest.mark.parametrize("corrupt", [False, True])
def test_completed_job_requires_hash_valid_receipt(tmp_path, corrupt):
    run = run_fixture(tmp_path, accepted=True)
    if corrupt:
        (run / "audit/preflight/mvp2_h300_warehouse_control/model_audit.json").write_text("drift")
    summary, _, _ = collector.collect(
        run, tmp_path / "collection", "123", accounting_text="123|COMPLETED|0:0\n"
    )
    assert summary["status"] == ("receipt_rejected" if corrupt else "accepted")
    assert bool(summary["receipt_validation_errors"]) is corrupt


@pytest.mark.parametrize("accounting", ["123|RUNNING|0:0\n", "124|FAILED|1:0\n",
                                       "123|FAILED|1:0\n123|FAILED|1:0\n"])
def test_nonterminal_or_ambiguous_accounting_never_creates_archive(tmp_path, accounting):
    run = run_fixture(tmp_path)
    output = tmp_path / "collection"
    with pytest.raises(ValueError):
        collector.collect(run, output, "123", accounting_text=accounting)
    assert not output.exists()


def test_wrong_submission_and_existing_output_are_preserved(tmp_path):
    run = run_fixture(tmp_path)
    with pytest.raises(ValueError, match="submission"):
        collector.collect(run, tmp_path / "collection", "124", accounting_text="124|FAILED|1:0")
    output = tmp_path / "collection"
    output.mkdir()
    sentinel = output / "preserved.txt"
    sentinel.write_text("preserve")
    with pytest.raises(ValueError, match="new collection"):
        collector.collect(run, output, "123", accounting_text="123|FAILED|1:0")
    assert sentinel.read_text() == "preserve"


@pytest.mark.parametrize("change", [
    None, "missing_review", "review_hash", "plan", "snapshot", "audit_hash",
    "missing_arm", "review_id", "optimization", "within_limit", "excess", "scope",
])
def test_collector_closes_reviewed_size_evidence_only_when_bound(tmp_path, change):
    run = run_fixture(tmp_path, accepted=True)
    receipt_path = run / "audit/preflight/pair_preflight.json"
    receipt = json.loads(receipt_path.read_text())
    plan = json.loads((run / "prepared/resource_contrast_plan.json").read_text())
    review = {
        "schema_version": "mvp2-input-size-review-v1", "review_id": "test-only-review",
        "scope": "input_inspection_only", "optimization_allowed": False,
        "plan_fields": {key: plan[key] for key in (
            "case", "reference_index", "reference_manifest_sha256", "workbook_sha256")},
        "reference_limit": 14000000,
        "snapshot_fields": {"total_variables": 14054654},
        "counts": receipt["model_size"]["data_signature"]["counts"],
        "audit_sha256": {name: receipt["artifacts"][f"mvp2_h300_warehouse_control/{name}"]
                         for name in gate.PRODUCTS[1:]},
    }
    review_path = run / "audit/input_size_review.json"
    review_path.write_text(json.dumps(review))
    receipt["tools"]["docs/mvp2_h300_input_size_review.json"] = file_sha256(review_path)
    (run / "audit/tool_hashes.json").write_text(json.dumps(receipt["tools"]))
    receipt["size_checks"] = {f"mvp2_h300_warehouse_{arm}": {
        "total_variables": 14054654, "reference_limit": 14000000,
        "excess_variables": 54654, "within_reference_limit": False,
        "input_size_review": "test-only-review", "optimization_allowed": False,
        "scope": "input_inspection_only",
    } for arm in ("control", "compact")}
    size = receipt["size_checks"]["mvp2_h300_warehouse_compact"]
    if change == "missing_review":
        review_path.unlink()
    elif change == "review_hash":
        review_path.write_text("{}")
    elif change == "plan":
        review["plan_fields"]["reference_index"] = 99
    elif change == "snapshot":
        receipt["model_size"]["total_variables"] += 1
    elif change == "audit_hash":
        review["audit_sha256"]["model_audit.json"] = "changed"
    elif change == "missing_arm":
        receipt["size_checks"].pop("mvp2_h300_warehouse_compact")
    elif change == "review_id":
        size["input_size_review"] = "changed"
    elif change == "optimization":
        size["optimization_allowed"] = True
    elif change == "within_limit":
        size["within_reference_limit"] = True
    elif change == "excess":
        size["excess_variables"] = 0
    elif change == "scope":
        size["scope"] = "solve"
    if change in ("plan", "audit_hash"):
        review_path.write_text(json.dumps(review))
        receipt["tools"]["docs/mvp2_h300_input_size_review.json"] = file_sha256(review_path)
        (run / "audit/tool_hashes.json").write_text(json.dumps(receipt["tools"]))
    receipt_path.write_text(json.dumps(receipt))
    summary, _, _ = collector.collect(
        run, tmp_path / "collection", "123", accounting_text="123|COMPLETED|0:0\n"
    )
    assert summary["status"] == ("accepted" if change is None else "receipt_rejected")
