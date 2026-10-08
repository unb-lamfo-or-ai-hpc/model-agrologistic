"""Partial/native-stop export, hostile transfers and fresh public-fixture residuals."""

import copy
import io
import json
import tarfile

import pytest

from scripts import mvp2_h300_partial as partial
from tests.test_mvp2_threads_review import review, synthetic_arm


def fixture(native="TIME_LIMIT", count=1, stage_count=1):
    assets, _implementation = synthetic_arm()
    payload = json.loads(assets["miniatures/threads-4/result.json"])["result"]
    result = partial.OptimizationResult(**payload)
    result.status = {"OPTIMAL": "optimal", "MEM_LIMIT": "error"}.get(native, "time_limit")
    result.metadata["gurobi_status_name"] = native
    result.metadata["solution_count"] = count
    result.metadata["lexicographic_stages"] = result.metadata["lexicographic_stages"][:stage_count]
    data = review.prepare_model_data(
        review.screen.fixture_data(), review.screen.spec(4, review.QUALIFICATION).model
    )
    config = review.screen.spec(4, review.QUALIFICATION).model
    expected = partial.anchor(
        data,
        config,
        source_commit="a" * 40,
        runtime_sha256="b" * 64,
        workbook_sha256="c" * 64,
        threads=4,
    )
    if not count:
        result.objective_value = None
        result.cost_breakdown = {}
        for name in partial.VECTOR_FIELDS[2:]:
            setattr(result, name, [])
    return result, data, config, expected


def synthetic_control(expected):
    """Synthetic parent receipt; not an allocation containment attestation."""
    return {
        "identity": partial.design.digest(expected),
        "root_pid": 999,
        "return_code": 0,
        "stop_reason": None,
        "error_type": None,
        "owned_group_closed": True,
        "allocation_tree_closed": False,
        "observed_transitions": [
            {"phase": phase, "observed_seconds": i}
            for i, phase in enumerate(partial.controls.PHASES)
        ],
        "application_seconds": 4,
        "production_admitted": False,
        "repeats_admitted": False,
    }


def exported(tmp_path, native="TIME_LIMIT", count=1, stage_count=1):
    result, data, config, expected = fixture(native, count, stage_count)
    directory = tmp_path / "original"
    report = partial.export_partial(directory, result, data, config, expected)
    partial.seal_control(directory, synthetic_control(expected), expected)
    return directory, data, config, expected, report


@pytest.mark.parametrize(
    "native,count,stages,disposition",
    [
        ("OPTIMAL", 1, 3, "complete_accepted_hierarchy"),
        ("OPTIMAL", 1, 1, "feasible_partial_hierarchy"),
        ("TIME_LIMIT", 1, 1, "feasible_partial_hierarchy"),
        ("MEM_LIMIT", 1, 1, "feasible_partial_hierarchy"),
        ("INTERRUPTED", 1, 1, "execution_failed"),
        ("TIME_LIMIT", 0, 0, "no_incumbent"),
        ("MEM_LIMIT", 0, 0, "no_incumbent"),
    ],
)
def test_export_and_fresh_portable_review(native, count, stages, disposition, tmp_path):
    directory, data, config, expected, report = exported(tmp_path, native, count, stages)
    assert report["classification"]["disposition"] == disposition
    assert report["classification"]["independently_feasible"] is bool(count)
    assert report["classification"]["production_admitted"] is False
    assert (directory / "incumbent.json").exists() is bool(count)
    assert not (directory / "run_completion.json").exists()
    before = {p.name: p.read_bytes() for p in directory.iterdir()}
    archive, checksum, receipt = partial.collect(
        directory, tmp_path / "transfer", "123|COMPLETED|0:0\n", "123", data, config, expected
    )
    reviewed = partial.review_transfer(archive, checksum, "123", data, config, expected)
    assert (
        reviewed
        == receipt["report"]
        == dict(
            report,
            resources=None,
            control=synthetic_control(expected),
            classification=dict(report["classification"], integrity_accepted=True),
        )
    )
    assert {p.name: p.read_bytes() for p in directory.iterdir()} == before
    if not count:
        assert reviewed["final_values"] is None
        assert reviewed["validation"]["status"] == "not_applicable_no_incumbent"
    else:
        assert reviewed["final_values"] == {
            "unmet_demand": 0,
            "emergency_capacity": 0,
            "economic_cost": 200,
        }


@pytest.mark.parametrize(
    "state,code,reason,disposition",
    [
        ("TIMEOUT", "0:15", "scheduler_time", "feasible_partial_hierarchy"),
        ("OUT_OF_MEMORY", "0:9", "scheduler_memory", "feasible_partial_hierarchy"),
        ("PREEMPTED", "0:15", "preemption", "feasible_partial_hierarchy"),
        ("CANCELLED", "0:15", "cancellation", "feasible_partial_hierarchy"),
        ("FAILED", "1:0", "time_limit", "execution_failed"),
    ],
)
def test_scheduler_censoring_separate_from_valid_vector(state, code, reason, disposition, tmp_path):
    directory, data, config, expected, _report = exported(tmp_path)
    archive, checksum, _receipt = partial.collect(
        directory, tmp_path / "transfer", f"123|{state}|{code}\n", "123", data, config, expected
    )
    classification = partial.review_transfer(archive, checksum, "123", data, config, expected)[
        "classification"
    ]
    assert classification["disposition"] == disposition
    assert classification["independently_feasible"]
    assert classification["censor_reason"] == reason


def test_stopped_stage_is_not_certified_or_imputed(tmp_path):
    result, data, config, expected = fixture(stage_count=2)
    result.metadata["lexicographic_stages"][1].update(
        status="TIME_LIMIT", objective_value=None, objective_bound=None, mip_gap=None
    )
    report = partial.export_partial(tmp_path / "run", result, data, config, expected)
    assert report["classification"]["certified_priority_prefix"] == 1
    assert len(report["stage_certificates"]) == 2
    assert report["stage_certificates"][1]["mip_gap"] is None


def test_status_and_reported_metrics_do_not_manufacture_feasibility(tmp_path):
    result, data, config, expected = fixture()
    result.flows[0]["value"] += 1
    result.metrics = {"objective_values": {"economic_cost": 0}, "accepted": True}
    report = partial.export_partial(tmp_path / "run", result, data, config, expected)
    assert report["validation"]["status"] == "rejected"
    assert report["classification"]["disposition"] == "unvalidated_incumbent"
    assert report["final_values"] is None


@pytest.mark.parametrize("count", [None, True, -1, 1.0, "1"])
def test_invalid_count_stops_before_creating_output(count, tmp_path):
    result, data, config, expected = fixture()
    result.metadata["solution_count"] = count
    with pytest.raises(ValueError):
        partial.export_partial(tmp_path / "run", result, data, config, expected)
    assert not (tmp_path / "run").exists()


def test_time_limit_without_count_does_not_export_vector(tmp_path):
    result, data, config, expected = fixture()
    result.metadata["solution_count"] = 0
    assert result.has_solution  # Existing generic property is not this collector's authority.
    with pytest.raises(ValueError):
        partial.export_partial(tmp_path / "run", result, data, config, expected)


@pytest.mark.parametrize(
    "field,value",
    [
        ("native", "LOADED"),
        ("status", "invented"),
        ("value", float("nan")),
        ("role", "unmet_demand"),
        ("bound", 1e9),
        ("gap", 0.2),
    ],
)
def test_stop_stage_and_numeric_drift_rejected(field, value, tmp_path):
    result, data, config, expected = fixture("OPTIMAL", 1, 3)
    if field == "native":
        result.metadata["gurobi_status_name"] = value
    elif field == "status":
        result.status = value
    elif field == "value":
        result.objective_value = value
    else:
        key = {"role": "stage_role", "bound": "objective_bound", "gap": "mip_gap"}[field]
        result.metadata["lexicographic_stages"][-1][key] = value
    with pytest.raises(ValueError):
        partial.export_partial(tmp_path / "run", result, data, config, expected)


def test_old_directory_and_transfer_never_overwritten(tmp_path):
    directory, data, config, expected, _report = exported(tmp_path)
    result, _data, _config, _expected = fixture()
    with pytest.raises(FileExistsError):
        partial.export_partial(directory, result, data, config, expected)
    partial.collect(
        directory, tmp_path / "transfer", "123|COMPLETED|0:0", "123", data, config, expected
    )
    with pytest.raises(FileExistsError):
        partial.collect(
            directory, tmp_path / "transfer", "123|COMPLETED|0:0", "123", data, config, expected
        )
    with pytest.raises(ValueError):
        partial.collect(
            directory, directory / "child", "123|COMPLETED|0:0", "123", data, config, expected
        )


@pytest.mark.parametrize(
    "accounting",
    [
        "123|RUNNING|0:0",
        "123.batch|COMPLETED|0:0",
        "123|COMPLETED|0:0\n123|FAILED|1:0",
        "123|COMPLETED+|0:0",
        "123|COMPLETED|garbage",
    ],
)
def test_accounting_pending_ambiguous_or_truncated_never_collects(accounting, tmp_path):
    directory, data, config, expected, _report = exported(tmp_path)
    with pytest.raises(ValueError):
        partial.collect(directory, tmp_path / "transfer", accounting, "123", data, config, expected)
    assert not (tmp_path / "transfer").exists()


def test_incomplete_terminal_run_is_packaged_without_acceptance(tmp_path):
    directory = tmp_path / "run"
    directory.mkdir()
    (directory / "observation.json").write_text('{"incomplete":true}')
    (directory / "gurobi.lic").write_text("secret must not be transferred")
    _result, data, config, expected = fixture()
    archive, checksum, record = partial.collect(
        directory, tmp_path / "transfer", "123|FAILED|1:0", "123", data, config, expected
    )
    assert record["status"] == "component_evidence_rejected"
    with tarfile.open(archive) as stream:
        assert set(stream.getnames()) == {"observation.json", "accounting.txt", "transfer.json"}
    with pytest.raises(ValueError):
        partial.review_transfer(archive, checksum, "123", data, config, expected)


@pytest.mark.parametrize(
    "field",
    [
        "data_sha256",
        "config_sha256",
        "source_commit",
        "runtime_sha256",
        "workbook_sha256",
        "threads",
    ],
)
def test_external_anchor_drift_rejects_self_consistent_transfer(field, tmp_path):
    directory, data, config, expected, _report = exported(tmp_path)
    archive, checksum, _record = partial.collect(
        directory, tmp_path / "transfer", "123|COMPLETED|0:0", "123", data, config, expected
    )
    changed = copy.deepcopy(expected)
    changed[field] = 8 if field == "threads" else "d" * len(expected[field])
    with pytest.raises(ValueError):
        partial.review_transfer(archive, checksum, "123", data, config, changed)


def repack(archive, target, mutation):
    with tarfile.open(archive) as stream:
        members = [(m.name, stream.extractfile(m).read()) for m in stream]
    members = mutation(members)
    with tarfile.open(target, "x:gz") as stream:
        for name, payload in members:
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            stream.addfile(info, io.BytesIO(payload))
    return partial.sha(target.read_bytes())


@pytest.mark.parametrize(
    "attack",
    [
        "unexpected",
        "duplicate",
        "traversal",
        "product_hash",
        "receipt_flag",
        "receipt_duplicate",
        "stale_validation",
    ],
)
def test_rehashed_hostile_archives_still_rejected(attack, tmp_path):
    directory, data, config, expected, _report = exported(tmp_path)
    archive, checksum, _record = partial.collect(
        directory, tmp_path / "transfer", "123|COMPLETED|0:0", "123", data, config, expected
    )

    def mutate(members):
        if attack in {"unexpected", "duplicate", "traversal"}:
            name = {
                "unexpected": "gurobi.lic",
                "duplicate": "observation.json",
                "traversal": "../incumbent.json",
            }[attack]
            return members + [(name, b"{}")]
        assets = dict(members)
        if attack == "product_hash":
            assets["incumbent.json"] = b"{}"
        elif attack == "receipt_duplicate":
            assets["transfer.json"] = b'{"status":"bad","status":"good"}'
        elif attack == "receipt_flag":
            receipt = json.loads(assets["transfer.json"])
            receipt["production_admitted"] = True
            assets["transfer.json"] = partial.controls.encoded(receipt)
        else:
            validation = json.loads(assets["independent_validation.json"])
            validation["families"]["usable_incumbent"]["checked"] += 1
            assets["independent_validation.json"] = partial.controls.encoded(validation)
            close = json.loads(assets["closure.json"])
            close["artifacts"]["independent_validation.json"] = partial.sha(
                assets["independent_validation.json"]
            )
            assets["closure.json"] = partial.controls.encoded(close)
            receipt = json.loads(assets["transfer.json"])
            receipt["artifacts"] = {
                n: partial.sha(v) for n, v in assets.items() if n != "transfer.json"
            }
            assets["transfer.json"] = partial.controls.encoded(receipt)
        return list(assets.items())

    new_sha = repack(archive, tmp_path / "attack.tar.gz", mutate)
    with pytest.raises((ValueError, KeyError)):
        partial.review_transfer(tmp_path / "attack.tar.gz", new_sha, "123", data, config, expected)


def test_symlink_or_hardlink_archive_member_rejected(tmp_path):
    _result, data, config, expected = fixture()
    target = tmp_path / "linked.tar.gz"
    with tarfile.open(target, "x:gz") as stream:
        info = tarfile.TarInfo("incumbent.json")
        info.type = tarfile.SYMTYPE
        info.linkname = "secret"
        stream.addfile(info)
    with pytest.raises(ValueError):
        partial.review_transfer(
            target, partial.sha(target.read_bytes()), "123", data, config, expected
        )


def test_scoped_resources_are_hash_bound_and_reduced_again(tmp_path):
    from tests.test_mvp2_h300_controls import resource_rows

    result, data, config, expected = fixture()
    partial.export_partial(
        tmp_path / "run", result, data, config, expected, resource_samples=resource_rows()
    )
    partial.seal_control(tmp_path / "run", synthetic_control(expected), expected)
    archive, checksum, _receipt = partial.collect(
        tmp_path / "run", tmp_path / "transfer", "123|COMPLETED|0:0", "123", data, config, expected
    )
    report = partial.review_transfer(archive, checksum, "123", data, config, expected)
    assert report["resources"] == partial.controls.resource_summary(resource_rows())
    assert report["resources"]["measured_lifetime_cpu_hours"] is None


@pytest.mark.parametrize("name", partial.ROW_KEYS)
def test_unallowlisted_columns_not_exported(name, tmp_path):
    result, data, config, expected = fixture()
    rows = getattr(result, name)
    if not rows:
        rows.append({"private_log": "must not be transmitted"})
    else:
        rows[0]["private_log"] = "must not be transmitted"
    with pytest.raises(ValueError):
        partial.export_partial(tmp_path / "run", result, data, config, expected)
    assert not (tmp_path / "run").exists()


@pytest.mark.parametrize("mode,count", [("pipeline_partial", 1), ("pipeline_none", 0)])
def test_real_cold_child_pipeline_to_portable_review(mode, count, tmp_path):
    import subprocess
    import sys
    import time

    from tests.test_mvp2_h300_controls import FIXTURE

    _result, data, config, expected = fixture(count=count, stage_count=0)
    identity = partial.design.digest(expected)

    process = partial.controls.spawn_owned(
        [sys.executable, str(FIXTURE), str(tmp_path / "journal"), identity, mode],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    supervised = partial.controls.supervise(
        process,
        tmp_path / "journal",
        identity,
        time.monotonic() + 45,
        caps=(30, 1, 5, 1),
        poll_seconds=0.02,
    )
    assert supervised["return_code"] == 0, process.stderr.read().decode(errors="replace")
    assert supervised["stop_reason"] is None
    partial.seal_control(tmp_path / "products", supervised, expected)
    archive, checksum, _record = partial.collect(
        tmp_path / "products",
        tmp_path / "transfer",
        "123|COMPLETED|0:0",
        "123",
        data,
        config,
        expected,
    )
    reviewed = partial.review_transfer(archive, checksum, "123", data, config, expected)
    assert reviewed["classification"]["disposition"] == (
        "feasible_partial_hierarchy" if count else "no_incumbent"
    )
    assert reviewed["classification"]["production_admitted"] is False


@pytest.mark.parametrize("reason", ["optimization_watchdog", "control_error", "live_descendants"])
def test_parent_failure_retains_vector_but_never_certifies_completion(reason, tmp_path):
    result, data, config, expected = fixture("OPTIMAL", 1, 3)
    directory = tmp_path / "run"
    partial.export_partial(directory, result, data, config, expected)
    control = synthetic_control(expected)
    control["stop_reason"] = reason
    partial.seal_control(directory, control, expected)
    archive, checksum, _receipt = partial.collect(
        directory, tmp_path / "transfer", "123|COMPLETED|0:0", "123", data, config, expected
    )
    report = partial.review_transfer(archive, checksum, "123", data, config, expected)
    assert report["classification"]["disposition"] == "execution_failed"
    assert report["classification"]["independently_feasible"]


def test_missing_parent_closure_is_rejected_even_after_worker_completion(tmp_path):
    result, data, config, expected = fixture("OPTIMAL", 1, 3)
    directory = tmp_path / "run"
    partial.export_partial(directory, result, data, config, expected)
    _archive, _checksum, receipt = partial.collect(
        directory, tmp_path / "transfer", "123|COMPLETED|0:0", "123", data, config, expected
    )
    assert receipt["status"] == "component_evidence_rejected"


def test_parent_receipt_is_write_once_and_identity_bound(tmp_path):
    directory, _data, _config, expected, _report = exported(tmp_path)
    with pytest.raises(FileExistsError):
        partial.seal_control(directory, synthetic_control(expected), expected)
    changed = synthetic_control(expected)
    changed["identity"] = "d" * 64
    with pytest.raises(ValueError):
        partial.seal_control(directory, changed, expected)


def test_accounting_size_is_bounded_before_output(tmp_path):
    directory, data, config, expected, _report = exported(tmp_path)
    with pytest.raises(ValueError):
        partial.collect(
            directory,
            tmp_path / "transfer",
            "123|COMPLETED|0:0\n" + "x" * 65536,
            "123",
            data,
            config,
            expected,
        )
    assert not (tmp_path / "transfer").exists()
