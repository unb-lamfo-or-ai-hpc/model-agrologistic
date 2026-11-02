"""Terminal forensic collection, native censoring and original-byte preservation."""

import hashlib
import importlib.util
import json
import os
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


C = module("serial_collection_unit", ROOT / "scripts/pyomo_serial_collection.py")


@pytest.fixture
def case(tmp_path, monkeypatch):
    engine_root = Path(os.environ.get("AGRO_SERIAL_TEST_ENGINE_ROOT", ROOT))
    engine = module("serial_collection_legacy", engine_root / "scripts/pyomo_scaling_campaign.py")
    claim = tmp_path / "case"
    claim.mkdir()
    (claim / "control/sto").mkdir(parents=True)
    job = {"job_id": "123", "source_commit": "c" * 40, "plan_sha256": "d" * 64}
    plan = {"cell": {"id": "h300-w-sto-highs-t4-r2"}}
    campaign = {"frozen": "test"}
    engine.write_json(claim / "job.json", job)
    engine.write_json(
        claim / "control/sto/runtime.json",
        {
            "affinity_logical_cpus": list(range(16)),
            "hardware_class_sha256": "h" * 64,
        },
    )
    engine.write_json(claim / "control/sto/entry.json", {**job, "step_id": "0"})
    (claim / "product.txt").write_bytes(b"retained numerical fixture\n")
    monkeypatch.setattr(engine, "load_run", lambda *a, **k: (plan, campaign))
    monkeypatch.setattr(engine.o, "job_receipt", lambda *a: job)
    monkeypatch.setattr(
        engine,
        "review_products",
        lambda *a: {
            "native_result_returned": True,
            "objective": 100.0,
            "bound": 99.5,
            "common_gap": 0.005,
            "incumbent_validation_rejected": False,
            "has_usable_incumbent": True,
            "quality_target_met": True,
            "classification": "validated_feasible",
            "original_validation_status": "accepted",
        },
    )
    monkeypatch.setattr(engine, "operational_closure", lambda *a: (True, {"status": "complete"}))
    monkeypatch.setattr(engine, "review_external", lambda *a: {"status": "timely_samples"})

    def command(argv):
        if "--format=JobIDRaw,Start,ElapsedRaw,AllocCPUS" in argv:
            return SimpleNamespace(returncode=0, stdout="123|Unknown|0|0\n", stderr="")
        return SimpleNamespace(
            returncode=0,
            stdout=(
                "123|COMPLETED|0:0|8|\n123.batch|COMPLETED|0:0|8|20K\n123.0|COMPLETED|0:0|7|100K\n"
            ),
            stderr="",
        )

    return SimpleNamespace(engine=engine, claim=claim, command=command)


def test_streamed_archive_inventory_and_idempotent_replay(case):
    before = (case.claim / "product.txt").read_bytes()
    saved = C.collect(case.engine, case.claim, "c" * 40, command=case.command)
    assert saved["observation"]["operational_receipts_closed"] is True
    archive = case.claim / "evidence.tar.gz"
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == saved["sha256"]
    with tarfile.open(archive, "r:gz") as tar:
        inventory = json.load(tar.extractfile("inventory.json"))
        assert set(tar.getnames()) == set(inventory) | {"inventory.json"}
        for name, checksum in inventory.items():
            assert hashlib.sha256(tar.extractfile(name).read()).hexdigest() == checksum
    assert (case.claim / "product.txt").read_bytes() == before
    assert C.collect(case.engine, case.claim, "c" * 40, command=case.command) == saved


def test_corrupted_collection_marker_cannot_replace_original_archive(case):
    saved = C.collect(case.engine, case.claim, "c" * 40, command=case.command)
    original = (case.claim / "evidence.tar.gz").read_bytes()
    saved["observation"]["objective"] = 999.0
    (case.claim / "collection.json").write_text(json.dumps(saved), encoding="utf-8")
    with pytest.raises(ValueError):
        C.collect(case.engine, case.claim, "c" * 40, command=case.command)
    assert (case.claim / "evidence.tar.gz").read_bytes() == original


def test_partial_existing_archive_is_preserved(case):
    archive = case.claim / "evidence.tar.gz"
    archive.write_bytes(b"partial original fixture")
    with pytest.raises(ValueError, match="Incomplete collection"):
        C.collect(case.engine, case.claim, "c" * 40, command=case.command)
    assert archive.read_bytes() == b"partial original fixture"
    assert not (case.claim / "collection.json").exists()


def test_nonterminal_or_delayed_accounting_creates_no_archive(case):
    def command(args):
        return SimpleNamespace(returncode=0, stdout="123|RUNNING|0:0|8|\n")

    row = C.collect(case.engine, case.claim, "c" * 40, command=command)
    assert row["status"] == "nonterminal_or_accounting_pending"
    assert not (case.claim / "evidence.tar.gz").exists()
    assert not (case.claim / "terminal_accounting.json").exists()


def test_never_allocated_cancelled_job_is_not_a_solver_failure(case):
    (case.claim / "control/sto/entry.json").unlink()

    def command(args):
        if "--format=JobIDRaw,Start,ElapsedRaw,AllocCPUS" in args:
            return SimpleNamespace(returncode=0, stdout="123|Unknown|0|0\n")
        return SimpleNamespace(returncode=0, stdout="123|CANCELLED|0:0|0|\n")

    row = C.collect(case.engine, case.claim, "c" * 40, command=command)
    assert row["classification"] == "not_executed"
    assert row["objective"] is None and row["common_gap"] is None
    assert not (case.claim / "collection.json").exists()
    assert not (case.claim / "evidence.tar.gz").exists()


def test_cancelled_with_missing_batch_and_actual_allocation_waits_for_accounting(case):
    (case.claim / "control/sto/entry.json").unlink()

    def command(args):
        if "--format=JobIDRaw,Start,ElapsedRaw,AllocCPUS" in args:
            return SimpleNamespace(returncode=0, stdout="123|2026-11-01T00:00:01|1|16\n")
        return SimpleNamespace(returncode=0, stdout="123|CANCELLED|0:15|1|\n")

    row = C.collect(case.engine, case.claim, "c" * 40, command=command)
    assert row["status"] == "nonterminal_or_accounting_pending"
    assert not (case.claim / "evidence.tar.gz").exists()


def test_original_review_failure_is_archived_as_forensic_partial(case, monkeypatch):
    def reject(*args):
        raise ValueError("Invalid original validation fixture")

    monkeypatch.setattr(case.engine, "review_products", reject)
    saved = C.collect(case.engine, case.claim, "c" * 40, command=case.command)
    row = saved["observation"]
    assert row["status"] == "forensic_partial_preserved"
    assert row["review_error_kind"] == "ValueError"
    assert not row["operational_receipts_closed"] and row["objective"] is None


def test_clean_native_timeout_without_incumbent_is_retained(case, monkeypatch):
    monkeypatch.setattr(
        case.engine,
        "review_products",
        lambda *a: {
            "native_result_returned": True,
            "objective": None,
            "bound": 80.0,
            "common_gap": None,
            "incumbent_validation_rejected": False,
            "has_usable_incumbent": False,
            "quality_target_met": False,
            "classification": "no_usable_incumbent",
            "native_status": "TerminationCondition.maxTimeLimit",
        },
    )
    row = C.collect(case.engine, case.claim, "c" * 40, command=case.command)["observation"]
    assert row["status"] == "observation_collected"
    assert row["objective"] is None and row["common_gap"] is None
    assert row["native_status"].endswith("maxTimeLimit")


@pytest.mark.parametrize("name", ["secret.lic", "input.xlsx", "cache.sqlite3"])
def test_disallowed_member_prevents_archive_without_truncation(case, name):
    (case.claim / name).write_bytes(b"forbidden fixture")
    with pytest.raises(ValueError, match="Forbidden evidence"):
        C.collect(case.engine, case.claim, "c" * 40, command=case.command)
    assert (case.claim / name).is_file() and not (case.claim / "evidence.tar.gz").exists()


def test_streaming_change_preserves_partial_archive_without_completion_marker(case, monkeypatch):
    original_digest = case.engine.digest
    target = case.claim / "product.txt"
    count = 0

    def digest(path):
        nonlocal count
        if Path(path) == target:
            count += 1
            if count == 2:
                target.write_bytes(b"changed after archive streaming")
        return original_digest(path)

    monkeypatch.setattr(case.engine, "digest", digest)
    with pytest.raises(ValueError, match="Streaming evidence drift"):
        C.collect(case.engine, case.claim, "c" * 40, command=case.command)
    assert (case.claim / "evidence.tar.gz").is_file()
    assert not (case.claim / "collection.json").exists()
