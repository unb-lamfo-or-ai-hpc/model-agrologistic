"""Missing Excel annotations and full solver-free observation lifecycle integration."""

import json
import math
from dataclasses import fields, replace
from pathlib import Path

import pandas as pd
import pytest

from scripts import mvp2_s2_h300_runtime as r
from scripts import mvp2_s2_p4_admission as a
from scripts import mvp2_s2_p4_observation as o
from src.logic import excel_loader, mathematical_contract
from src.logic.run_integrity import scientific_identity
from tests import test_mvp2_s2_p4_input_contract as input_tests
from tests.test_mvp2_s2_p4_admission import accounting, environment, records

public_input = input_tests.public_input


@pytest.fixture
def missing_input(public_input, monkeypatch):
    reference, manifest, _, review = public_input
    spec = manifest.experiments[2]
    sheets = pd.read_excel(spec.workbook, sheet_name=None)
    sheets["Parametros_Modelo"] = pd.concat(
        [
            sheets["Parametros_Modelo"],
            pd.DataFrame([{"Parametro": "unused_annotation", "Valor": None}]),
        ],
        ignore_index=True,
    )
    with pd.ExcelWriter(spec.workbook, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name, index=False)
    monkeypatch.setattr(r.d, "WORKBOOK", a.p.sha_file(spec.workbook))
    original = mathematical_contract.prepare_model_data(
        excel_loader.load_model_data_from_excel(spec.workbook, spec.loader), spec.model
    )
    assert math.isnan(original.metadata["parameter_table"]["unused_annotation"])
    return reference, manifest, original, review


def test_real_excel_blank_reproduces_old_hash_failure_without_numeric_change(missing_input):
    reference, manifest, original, review = missing_input
    with pytest.raises(ValueError, match="Out of range float"):
        scientific_identity(original)
    data, config, identity = r._input(reference)
    assert data is not original
    for field in fields(data):
        if field.name != "metadata":
            assert getattr(data, field.name) == getattr(original, field.name)
    assert data.metadata["parameter_table"]["unused_annotation"] == {r.METADATA_NAN: True}
    assert math.isnan(original.metadata["parameter_table"]["unused_annotation"])
    assert identity["data_sha256"] == scientific_identity(data)
    assert identity["config_sha256"] == scientific_identity(config)
    assert config == manifest.experiments[2].model
    assert identity["counts"] == review["counts"] and identity["size"] == review["snapshot_fields"]
    anchor = r.partial.anchor(
        data,
        config,
        source_commit="b" * 40,
        runtime_sha256="c" * 64,
        workbook_sha256=r.d.WORKBOOK,
        threads=4,
    )
    assert anchor["data_sha256"] == identity["data_sha256"]


def test_finite_identity_and_metadata_unchanged(public_input):
    reference, _, original, _ = public_input
    data, _, identity = r._input(reference)
    assert data == original and data.metadata == original.metadata
    assert identity["data_sha256"] == scientific_identity(original)


@pytest.mark.parametrize("value", [None, 0.0, "NaN", "nan", False, {"missing": True}])
def test_missing_marker_distinguishes_null_zero_text_and_other_annotations(missing_input, value):
    _, _, original, _ = missing_input
    other = replace(
        original, metadata={**original.metadata, "parameter_table": {"unused_annotation": value}}
    )
    assert scientific_identity(r._identity_view(original)) != scientific_identity(
        r._identity_view(other)
    )


def test_missing_annotation_identity_is_order_independent_and_sensitive(missing_input):
    _, _, original, _ = missing_input
    left = replace(original, metadata={**original.metadata, "extra": {"b": float("nan"), "a": 1}})
    right = replace(original, metadata={"extra": {"a": 1, "b": float("nan")}, **original.metadata})
    assert scientific_identity(r._identity_view(left)) == scientific_identity(
        r._identity_view(right)
    )
    changed = replace(right, metadata={**right.metadata, "extra": {"a": 2, "b": float("nan")}})
    assert scientific_identity(r._identity_view(left)) != scientific_identity(
        r._identity_view(changed)
    )


@pytest.mark.parametrize("value", [float("inf"), -float("inf")])
def test_infinite_annotations_are_rejected_not_relabelled_missing(missing_input, value):
    _, _, data, _ = missing_input
    with pytest.raises(ValueError, match="Infinite input annotation"):
        r._identity_view(replace(data, metadata={"bad": value}))


@pytest.mark.parametrize("nested", [False, True])
def test_reserved_marker_collision_is_rejected(missing_input, nested):
    _, _, data, _ = missing_input
    marker = {r.METADATA_NAN: True}
    with pytest.raises(ValueError, match="Reserved input annotation"):
        r._identity_view(replace(data, metadata={"nested": marker} if nested else marker))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
@pytest.mark.parametrize("field", ["supply", "scenario_prob", "static_capacity", "storage_tariff"])
def test_nonfinite_numeric_inputs_still_fail_strict_identity(missing_input, field, value):
    _, _, original, _ = missing_input
    mapping = dict(getattr(original, field))
    mapping[next(iter(mapping))] = value
    with pytest.raises(ValueError, match="Out of range float"):
        scientific_identity(r._identity_view(replace(original, **{field: mapping})))


def test_nonfinite_coordinates_and_config_still_reject(missing_input):
    _, manifest, original, _ = missing_input
    nodes = dict(original.node_info)
    key = next(iter(nodes))
    nodes[key] = replace(nodes[key], latitude=float("nan"))
    with pytest.raises(ValueError, match="Out of range float"):
        scientific_identity(r._identity_view(replace(original, node_info=nodes)))
    with pytest.raises(ValueError, match="Out of range float"):
        scientific_identity(replace(manifest.experiments[2].model, days_per_period=float("nan")))


@pytest.mark.parametrize(
    "outcome",
    [
        "complete",
        "early_batch_failure",
        "input_drift",
        "invalid_coefficient",
        "infinite_annotation",
        "marker_collision",
    ],
)
def test_real_input_plan_prepare_recheck_batch_and_terminal_replay(
    missing_input, tmp_path, monkeypatch, outcome
):
    reference, _, original, review = missing_input
    checkout = tmp_path / "source"
    actual_root = Path(o.__file__).resolve().parents[1]
    names = {
        p.relative_to(actual_root).as_posix()
        for p in (actual_root / "src").rglob("*")
        if p.is_file()
    }
    names |= set(r.entry.PROTECTED) | set(a.TRANSPORT) | {r.source.ENTRY}
    for name in names:
        target = checkout / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((actual_root / name).read_bytes())
    review_path = checkout / "docs/mvp2_h300_input_size_review.json"
    review_path.write_text(json.dumps(review), encoding="utf-8")
    files = {
        p.relative_to(checkout).as_posix(): a.p.sha_file(p)
        for p in checkout.rglob("*")
        if p.is_file()
    }
    runtime = {"python_version": "3.13.15", "distributions": {"gurobipy": "13.0.3"}}
    # External P3 carrier and runtime observations are doubles; source parity,
    # real input, plan, claim, recheck, transport hashes and all replay are real.
    monkeypatch.setattr(r, "_p3_files", lambda path: files)
    monkeypatch.setattr(r, "ROOT", checkout)
    monkeypatch.setattr(a, "ROOT", checkout)
    monkeypatch.setattr(o, "ROOT", checkout)
    base = tmp_path / "cluster-simulation"
    base.mkdir()
    monkeypatch.setattr(o, "BASE", base)
    monkeypatch.setattr(o, "REFERENCE", reference)
    (base / "old-bootstrap").mkdir()
    (base / "old-bootstrap/evidence").write_bytes(b"preserved")
    calls = []

    def source_files(root, commit):
        r.source.verify_tree(root, files)
        return files

    def planner(commit, root, p3, ref):
        return r._plan(commit, root, p3, ref, files=source_files, runtime=lambda: runtime)

    def prepare(*args):
        return a.prepare(*args, planner=planner)

    def command(argv, **kwargs):
        calls.append(argv[0])
        return {"status": "complete", "returncode": 0}, b"123\n"

    if outcome in {"invalid_coefficient", "infinite_annotation", "marker_collision"}:
        if outcome == "invalid_coefficient":
            original.supply[next(iter(original.supply))] = float("nan")
        elif outcome == "infinite_annotation":
            original.metadata["bad"] = float("inf")
        else:
            original.metadata[r.METADATA_NAN] = True
        monkeypatch.setattr(excel_loader, "load_model_data_from_excel", lambda *args: original)
        with pytest.raises(ValueError):
            o.start("b" * 40, acknowledged=True, prepare=prepare, command=command)
        assert calls == []
        assert not (base / a.CLAIM).exists() and not (base / o.CLAIM).exists()
        assert (base / "old-bootstrap/evidence").read_bytes() == b"preserved"
        return

    result = o.start("b" * 40, acknowledged=True, prepare=prepare, command=command)
    assert result["job_id"] == "123" and calls == ["sbatch"]
    target, receipt, plan = o.load(base / o.CLAIM, "b" * 40)
    if outcome == "input_drift":
        with reference.open("ab") as stream:
            stream.write(b"drift")
    monkeypatch.setenv("SLURM_JOB_ID", "123")

    def observer(path, digest, job, **kwargs):
        a.p.publish(path / "job.json", {"job_id": job, "admission_plan_sha256": digest})
        code = a._observe_worker(
            path,
            recheck=lambda p, root, ref: r._recheck(p, root, ref, runtime=lambda: runtime),
            environment=lambda p, j: environment(plan),
            probe=lambda: {"status": "accepted", "gurobi_version": [13, 0, 3]},
        )
        supervision = records(plan)["supervision.json"]
        supervision.update(return_code=code, status="complete" if code == 0 else "worker_failed")
        a.p.publish(path / "supervision.json", supervision)
        return supervision

    def verify(root, inventory):
        if outcome == "early_batch_failure":
            raise OSError("simulated source failure")
        r.source.verify_tree(root, inventory)

    assert o.batch(target, "b" * 40, observer=observer, verify=verify) == (
        0 if outcome == "complete" else 2
    )

    def collect_command(*args, **kwargs):
        return {"status": "complete", "returncode": 0}, accounting().encode()

    collected = o.collect("b" * 40, command=collect_command)
    assert collected["status"] == (
        "prerequisites_observed_execution_closed"
        if outcome == "complete"
        else "negative_or_incomplete_evidence_preserved"
    )
    assert (
        o.audit(
            Path(collected["download"]), collected["sha256"], "b" * 40, a.d.digest(receipt), "123"
        )["status"]
        == collected["status"]
    )
    assert o.collect("b" * 40, command=collect_command) == collected
    assert (
        o.start(
            "b" * 40, acknowledged=True, command=lambda *args, **kwargs: pytest.fail("resubmit")
        )["status"]
        == "existing_job_collect_only"
    )
    assert (base / "old-bootstrap/evidence").read_bytes() == b"preserved"
    assert not (base / r.CLAIM).exists() and calls == ["sbatch"]
