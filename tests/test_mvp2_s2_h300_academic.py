"""No scheduler, license or native solve: closed P4 preparation qualification."""

import copy
import hashlib

import pytest

from scripts import mvp2_s2_h300_academic as p4


def plan():
    return p4.preparation("1" * 40, "2" * 64, "3" * 64, "4" * 64)


def accepted():
    return {
        "stage": "native_miniature",
        "disposition": "academic_stage_accepted",
        "native": {
            "classification": {
                "disposition": "complete_accepted_hierarchy",
                "certified_priority_prefix": 3,
                "independently_feasible": True,
                "products_closed": True,
            },
            "validation": {"status": "accepted", "failed_check_count": 0},
        },
    }


def test_exact_anchors_are_passed_to_canonical_auditor(monkeypatch):
    calls = []

    def audit(*args):
        calls.append(args)
        return accepted()

    monkeypatch.setattr(p4.academic, "audit", audit)
    assert p4.p3_entry("original.tar.gz") == accepted()
    assert calls == [
        ("original.tar.gz", p4.P3["archive"], p4.P3["source"], p4.P3["plan"], p4.P3["job"])
    ]


@pytest.mark.parametrize(
    "field,value",
    [
        ("disposition", "feasible_partial_hierarchy"),
        ("certified_priority_prefix", 2),
        ("independently_feasible", False),
        ("products_closed", False),
    ],
)
def test_incomplete_native_never_passes_entry(monkeypatch, field, value):
    record = accepted()
    record["native"]["classification"][field] = value
    monkeypatch.setattr(p4.academic, "audit", lambda *_: record)
    with pytest.raises(ValueError):
        p4.p3_entry("evidence")


@pytest.mark.parametrize(
    "field,value", [("stage", "normal"), ("disposition", "evidence_not_accepted")]
)
def test_wrong_outer_certificate(monkeypatch, field, value):
    record = accepted()
    record[field] = value
    monkeypatch.setattr(p4.academic, "audit", lambda *_: record)
    with pytest.raises(ValueError):
        p4.p3_entry("evidence")


@pytest.mark.parametrize("field,value", [("status", "rejected"), ("failed_check_count", 1)])
def test_residual_rejection(monkeypatch, field, value):
    record = accepted()
    record["native"]["validation"][field] = value
    monkeypatch.setattr(p4.academic, "audit", lambda *_: record)
    with pytest.raises(ValueError):
        p4.p3_entry("evidence")


def test_checksum_rejection_is_not_swallowed(monkeypatch):
    def reject(*_):
        raise ValueError("checksum")

    monkeypatch.setattr(p4.academic, "audit", reject)
    with pytest.raises(ValueError, match="checksum"):
        p4.p3_entry("evidence")


def test_exact_scientific_design_and_no_historical_active_hash():
    value = p4.validate_preparation(plan())
    assert [a["solver"]["threads"] for a in value["arms"]] == [4, 1, 8, 2, 16]
    assert value["allocation"]["requested_cpus_per_task"] == 16
    assert value["allocation"]["memory_mib"] == 196608
    assert value["allocation"]["walltime_seconds"] == 21600
    assert value["budget_ledger"]["block_seconds"] == 21600
    assert value["pending_obligations"] == list(p4.OBLIGATIONS)
    assert not value["h300_execution_admitted"]
    for arm in value["arms"]:
        assert "implementation_sha256" not in arm
        assert arm["execution_source_commit"] == "1" * 40
        assert not arm["solver"]["compact_python_indices"]
        assert arm["solver"]["time_limit"] == 1800
        assert arm["solver"]["soft_memory_gb"] == 128
        assert not arm["direct_origin_customer"]


@pytest.mark.parametrize(
    "key,value",
    [
        ("h300_execution_admitted", True),
        ("production_isolation_certified", True),
        ("automatic_repeats_allowed", True),
        ("pending_obligations", []),
        ("status", "accepted"),
    ],
)
def test_flags_and_removed_obligations_cannot_admit(key, value):
    record = plan()
    record[key] = value
    with pytest.raises(ValueError):
        p4.validate_preparation(record)


@pytest.mark.parametrize("threads", [False, True, 3, 32])
def test_grid_mutation_rejected(threads):
    record = plan()
    record["arms"][0]["solver"]["threads"] = threads
    with pytest.raises(ValueError):
        p4.validate_preparation(record)


@pytest.mark.parametrize("index,bad", [(0, "x" * 40), (1, "2" * 63), (2, True), (3, "")])
def test_bad_external_identities(index, bad):
    values = ["1" * 40, "2" * 64, "3" * 64, "4" * 64]
    values[index] = bad
    with pytest.raises(ValueError):
        p4.preparation(*values)


def test_detached_preparation():
    a = plan()
    b = copy.deepcopy(a)
    a["arms"][0]["solver"]["seed"] = 9
    assert plan() == b


def test_scientific_parity_and_mutation(tmp_path):
    files = {name: "" for name in (*p4.PROTECTED, "src/logic/model.py")}
    for name in files:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"frozen source")
        files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    assert p4.source_parity(tmp_path, files) == dict(sorted(files.items()))
    (tmp_path / "src/logic/model.py").write_bytes(b"changed")
    with pytest.raises(ValueError, match="drift"):
        p4.source_parity(tmp_path, files)


@pytest.mark.parametrize("change", ["extra", "missing"])
def test_scientific_inventory_rejected(tmp_path, change):
    files = {}
    for name in (*p4.PROTECTED, "src/logic/model.py"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"frozen")
        files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    if change == "extra":
        (tmp_path / "src/logic/extra.py").write_bytes(b"extra")
    else:
        (tmp_path / "src/logic/model.py").unlink()
    with pytest.raises(ValueError, match="inventory"):
        p4.source_parity(tmp_path, files)


def test_public_dispatch_denies_before_any_effect(tmp_path):
    with pytest.raises(PermissionError, match="incomplete"):
        p4.execute_h300(tmp_path, accepted=True, production_admitted=True)
    assert not list(tmp_path.iterdir())
