"""Closed post-S2 h400 candidate: real public Excel, no licensed/cluster execution."""

import copy
import gzip
import io
import json
import os
import subprocess
import sys
import tarfile
from dataclasses import asdict
from pathlib import Path

import pytest
import yaml

from scripts import mvp2_h400_post_s2 as q
from src.logic import experiment_runner as runner
from src.logic import optimization
from tests.test_mvp2_s2_p4_input_contract import public_input  # noqa: F401

SOURCE = "a" * 40


@pytest.fixture
def real_input(public_input, monkeypatch):  # noqa: F811
    reference, _manifest, _data, _review = public_input
    raw = yaml.safe_load(reference.read_text())
    raw["experiments"] = [raw["experiments"][0]]
    spec = raw["experiments"][0]
    spec["model"]["use_direct_origin_customer"] = True
    spec["loader"]["include_direct_origin_customer_routes"] = True
    spec["metadata"] = {"warehouse_population": 400}
    spec["max_estimated_variables"] = 25000000
    spec["solver"] = asdict(q.solver_profile())
    reference.write_text(yaml.safe_dump(raw), encoding="utf-8")
    loaded = runner.load_experiment_manifest(reference).experiments[0]
    from src.logic.excel_loader import load_model_data_from_excel
    from src.logic.mathematical_contract import prepare_model_data

    data = prepare_model_data(
        load_model_data_from_excel(loaded.workbook, loaded.loader), loaded.model
    )
    policy = q.products.read(q.ROOT / "docs/mvp2_h400_input_policy.json")
    policy.update(
        reference_manifest_sha256=q.products.sha_file(reference),
        workbook_sha256=q.products.sha_file(loaded.workbook),
        counts=runner._data_signature(data)["counts"],
        snapshot_fields=asdict(runner.estimate_model_size(data, loaded.model)),
    )
    q.products.publish(reference.parent / "docs/mvp2_h400_input_policy.json", policy)
    monkeypatch.setattr(q, "ROOT", reference.parent)
    monkeypatch.setattr(q, "evidence_basis", lambda: {"fixture_only": True})
    monkeypatch.setattr(runner, "solve_model", lambda *a, **k: pytest.fail("solver called"))
    monkeypatch.setattr(optimization, "solve_model", lambda *a, **k: pytest.fail("solver called"))
    return reference, data


def fixture_plan(identity):
    return {
        "schema_version": "h400-post-s2-plan-v1",
        "source_commit": SOURCE,
        "source_files": {"src/logic/model_config.py": "1" * 64},
        "proposal": q.proposal(),
        "input": identity,
        "plan_scope": "software_preparation_not_live_admission",
    }


def test_basis_and_budget_preserve_s1_not_one_hour_s2():
    assert q.evidence_basis() == {"s1_job": "2200384", "s2_job": "2215308"}
    profile = q.solver_profile()
    assert (profile.threads, profile.time_limit, profile.seed, profile.mip_gap) == (
        4,
        28800,
        42,
        0.1,
    )
    assert profile.solver_options == {"SoftMemLimit": 128, "NumericFocus": 1}
    assert all(opts == {"Method": 2} for opts in profile.multiobjective_stage_options.values())
    value = q.proposal()
    assert value["variable_guard"] == 42426624
    assert value["allocation_proposal"]["logical_cpus"] == 16
    assert value["allocation_proposal"]["memory_mib"] == 196608
    budget = value["budget_proposal"]
    phases = sum(
        budget[k]
        for k in (
            "build_seconds",
            "global_native_seconds",
            "shared_late_return_and_export_seconds",
            "cleanup_seconds",
        )
    )
    assert phases == 31800 <= budget["worker_hard_seconds"] == 32400
    assert (
        budget["worker_hard_seconds"]
        + budget["fresh_admission_seconds"]
        + budget["independent_review_seconds"]
        + budget["stop_and_collection_reserve_seconds"]
        == budget["minimum_wall_seconds"]
        == 35100
    )
    assert (
        budget["minimum_wall_seconds"] < value["allocation_proposal"]["walltime_seconds"] == 43200
    )
    assert set(value["pending_obligations"]) == set(q.OBLIGATIONS)
    assert all(value[k] is False for k in q.FLAGS)


def test_actual_slotted_experiment_and_excel_with_metadata_nan(real_input):
    reference, data = real_input
    identity = q.fresh_input(reference)
    spec = runner.load_experiment_manifest(reference).experiments[0]
    assert isinstance(spec, runner.ExperimentSpec) and not hasattr(spec, "resume")
    assert identity["counts"]["warehouses"] == len(data.warehouses)
    assert identity["size"]["routes_oc"] > 0
    assert identity["private_paths_published"] is False
    assert str(reference.parent) not in json.dumps(identity)
    assert q.validate_plan(fixture_plan(identity))["input"] == identity


@pytest.mark.parametrize(
    "change",
    [
        "duplicate",
        "missing",
        "evpi",
        "resume",
        "guard",
        "threads",
        "budget",
        "gap",
        "seed",
        "compact",
        "iis",
        "memory",
        "stage_time",
        "method",
        "workbook",
        "reference",
        "loader_direct",
    ],
)
def test_real_input_drift_is_rejected_before_model_construction(real_input, monkeypatch, change):
    reference, _data = real_input
    manifest = runner.load_experiment_manifest(reference)
    spec = manifest.experiments[0]
    if change == "duplicate":
        manifest.experiments.append(copy.deepcopy(spec))
    elif change == "missing":
        spec.model.use_direct_origin_customer = False
    elif change in {"evpi", "resume"}:
        setattr(spec, "calculate_evpi_vss" if change == "evpi" else "resume_evpi_vss", True)
    elif change == "guard":
        spec.max_estimated_variables += 1
    elif change == "loader_direct":
        spec.loader.include_direct_origin_customer_routes = False
    elif change in {"threads", "budget", "gap", "seed", "compact", "iis"}:
        fields = {
            "threads": ("threads", 8),
            "budget": ("time_limit", 3600),
            "gap": ("mip_gap", 0.2),
            "seed": ("seed", 3),
            "compact": ("compact_python_indices", True),
            "iis": ("compute_iis", True),
        }
        name, value = fields[change]
        setattr(spec.solver, name, value)
    elif change == "memory":
        spec.solver.solver_options["SoftMemLimit"] = 129
    elif change in {"stage_time", "method"}:
        spec.solver.multiobjective_stage_options["unmet_demand"][
            "TimeLimit" if change == "stage_time" else "Method"
        ] = 5
    else:
        path = reference if change == "reference" else spec.workbook
        with path.open("ab") as output:
            output.write(b"drift")
    monkeypatch.setattr(runner, "load_experiment_manifest", lambda *a: manifest)
    with pytest.raises(ValueError):
        q.fresh_input(reference)


def test_new_isolated_preparation_and_repeat_preservation(real_input, tmp_path, monkeypatch):
    reference, _data = real_input
    monkeypatch.setattr(q, "evidence_basis", lambda: {})
    files = {"src/logic/model_config.py": "1" * 64}
    monkeypatch.setattr(q.source, "source_files", lambda *a: copy.deepcopy(files))
    output = tmp_path.parent / (tmp_path.name + "-output")
    output.mkdir()
    target = output / "proposal"
    try:
        value = q.prepare(SOURCE, reference, target)
        original = (target / "plan.json").read_bytes()
        assert q.products.read(target / "plan.json") == value
        with pytest.raises(ValueError, match="isolated"):
            q.prepare(SOURCE, reference, target)
        assert (target / "plan.json").read_bytes() == original
    finally:
        # Only fixture-owned files; no historical run or claim.
        if (target / "plan.json").exists():
            (target / "plan.json").unlink()
        if target.exists():
            target.rmdir()
        output.rmdir()


@pytest.mark.parametrize("field", list(q.FLAGS))
def test_receipt_cannot_upgrade_permission(real_input, field):
    value = fixture_plan(q.fresh_input(real_input[0]))
    value["proposal"][field] = True
    with pytest.raises(ValueError, match="proposal"):
        q.validate_plan(value)


@pytest.mark.parametrize("value", [1, None, "false"])
def test_boolean_permission_type_is_not_coerced(real_input, value):
    plan = fixture_plan(q.fresh_input(real_input[0]))
    plan["proposal"]["h400_execution_admitted"] = value
    with pytest.raises(ValueError, match="proposal"):
        q.validate_plan(plan)


@pytest.mark.parametrize(
    "field", ["source_commit", "source_files", "counts", "size", "hash", "path", "extra", "scope"]
)
def test_plan_drift_stays_closed(real_input, field):
    value = fixture_plan(q.fresh_input(real_input[0]))
    if field == "source_commit":
        value[field] = "short"
    elif field == "source_files":
        value[field] = {"../escape": "1" * 64}
    elif field in {"counts", "size"}:
        key = next(iter(value["input"][field]))
        value["input"][field][key] += 1
    elif field == "hash":
        value["input"]["reference_sha256"] = "0" * 64
    elif field == "path":
        value["input"]["private_paths_published"] = True
    elif field == "extra":
        value["execution_admitted"] = True
    else:
        value["plan_scope"] = "live_admitted"
    with pytest.raises(ValueError):
        q.validate_plan(value)


def test_metadata_only_carrier_round_trip_no_live_evidence_claim(real_input, tmp_path):
    plan = tmp_path / "plan.json"
    q.products.publish(plan, fixture_plan(q.fresh_input(real_input[0])))
    archive = tmp_path / "proposal.tar.gz"
    checksum = q.pack(plan, archive)
    result = q.audit(archive, checksum)
    assert result["status"] == "proposal_integrity_replayed_not_live_qualified"
    assert all(result[k] is False for k in q.FLAGS)
    with tarfile.open(archive) as stream:
        assert stream.getnames() == ["plan.json"]
    with pytest.raises(ValueError):
        q.audit(archive, "0" * 64)
    with pytest.raises(ValueError):
        q.pack(plan, archive)


@pytest.mark.parametrize("mode", ["escape", "duplicate", "link", "extra", "trailing", "bomb"])
def test_untrusted_carrier_is_bounded_and_not_extracted(real_input, tmp_path, mode):
    raw = b"".join(q.products.chunks(fixture_plan(q.fresh_input(real_input[0]))))
    content = io.BytesIO()
    with tarfile.open(fileobj=content, mode="w", format=tarfile.USTAR_FORMAT) as stream:
        member = tarfile.TarInfo("../plan.json" if mode == "escape" else "plan.json")
        member.size, member.mode = len(raw), 0o600
        if mode == "link":
            member.type, member.linkname, member.size = tarfile.SYMTYPE, "secret", 0
        stream.addfile(member, io.BytesIO(raw))
        if mode in {"duplicate", "extra"}:
            member = tarfile.TarInfo("plan.json" if mode == "duplicate" else "private-workbook")
            member.size = len(raw)
            stream.addfile(member, io.BytesIO(raw))
    expanded = content.getvalue()
    if mode == "trailing":
        expanded += b"hidden"
    if mode == "bomb":
        expanded += b"\0" * q.products.METADATA
    archive = tmp_path / "bad.tar.gz"
    archive.write_bytes(gzip.compress(expanded))
    with pytest.raises(ValueError):
        q.audit(archive, q.products.sha_file(archive))
    assert not (tmp_path / "private-workbook").exists()


@pytest.mark.parametrize("action", ["start", "batch", "worker", "resume"])
def test_public_execution_paths_deny_before_any_effect(tmp_path, monkeypatch, action):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(q, "evidence_basis", lambda: pytest.fail("input access before denial"))
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("external command"))
    with pytest.raises(PermissionError, match="remain closed"):
        q.main([action])
    assert not list(tmp_path.iterdir())


def test_proposal_import_and_cli_do_not_load_native_solver():
    code = (
        "import sys;from scripts import mvp2_h400_post_s2 as q;"
        "q.main(['describe']);assert 'gurobipy' not in sys.modules"
    )
    done = subprocess.run(
        [sys.executable, "-B", "-c", code], cwd=q.ROOT, capture_output=True, text=True, check=True
    )
    assert json.loads(done.stdout)["h400_execution_admitted"] is False


def test_wrapper_has_no_scheduler_or_license_or_package_install():
    text = (q.ROOT / "scripts/qualify_h400_post_s2.sh").read_text()
    for forbidden in ("sbatch", "srun", "scancel", "pip install", "GRB_LICENSE_FILE", "curl "):
        assert forbidden not in text
    assert "set -euo pipefail" in text and '"$PY" -B -I' in text


def test_h500_is_conditional_even_after_a_positive_h400_fixture():
    value = q.proposal()
    assert value["h500_execution_admitted"] is False
    assert value["pending_obligations"]
    assert value["selection"].endswith("not_proven_winner")
    assert (
        value["acceptance_policy"]["h400_success_necessary_not_sufficient_for_h500_admission"]
        is True
    )
    assert Path(q.__file__).name == "mvp2_h400_post_s2.py"


def test_changed_public_basis_cannot_validate_a_plan(tmp_path, monkeypatch):
    original = q.products.sha_file
    monkeypatch.setattr(
        q.products,
        "sha_file",
        lambda path: (
            "0" * 64 if Path(path).name == "mvp2_h400_input_policy.json" else original(path)
        ),
    )
    with pytest.raises(ValueError, match="evidence anchor"):
        q.validate_plan({})


@pytest.mark.skipif(sys.platform != "linux", reason="Actual Bash qualification runs on Linux CI")
@pytest.mark.parametrize("action", ["describe", "start", "batch", "worker", "resume"])
def test_actual_bash_wrapper_closed_actions(action):
    done = subprocess.run(
        ["bash", str(q.ROOT / "scripts/qualify_h400_post_s2.sh"), action],
        cwd=q.ROOT,
        env={**os.environ, "H400_QUALIFICATION_PYTHON": sys.executable},
        capture_output=True,
        text=True,
        check=False,
    )
    if action == "describe":
        assert done.returncode == 0 and json.loads(done.stdout)["h400_execution_admitted"] is False
    else:
        assert done.returncode == 2 and "CLOSED" in done.stderr
