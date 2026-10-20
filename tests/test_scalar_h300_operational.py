"""Complete h300 operational transport/adverse tests; no Slurm, license or solve."""

import io
import json
import sys
import tarfile
from types import SimpleNamespace

import pytest

from scripts import mvp2_scalar_h300_operational as m
from src.logic.mathematical_contract import canonical_hash
from tests.test_scalar_h300 import sample_files
from tests.test_scalar_r3a import SHA
from tests.test_scalar_r3a_operational import allocation_text, events, science_files


def audit_fixture():
    return {
        "schema_version": 1,
        "output_workbook_sha256": m.h.WORKBOOK_SHA,
        "distance_status": "osrm_authoritative",
        "distance_provenance": {
            "provider": "osrm",
            "profile": "driving",
            "dataset_id": m.o.DATASET,
            "route_count": 113269,
            "route_count_by_source": {"osrm": 113269},
            "route_count_by_arc_type": {"DD": 89700, "OD": 11100, "DC": 11100, "OC": 1369},
            "fallback_count": 0,
            "osrm_request_count": 0,
            "osrm_cache_miss_count": 0,
            "osrm_cache_write_count": 0,
        },
    }


def hardware_fixture():
    return {
        "host": "r1i3n5",
        "cpu_model": {"model name": "public transport fixture"},
        "affinity_logical_cpus": list(range(16)),
        "physical_cores_observed": 8,
        "topology": [{"logical_cpu": i, "socket": 0, "core": i % 8} for i in range(16)],
    }


def fixture():
    """Synthetic transport certificates; real mathematics is tested separately."""
    files = sample_files()
    policy = json.loads(files["warehouse_selection.json"])
    policy.update(
        schema_version="warehouse-selection-policy-v1", criterion="Frozen public transport ranking"
    )
    files["warehouse_selection.json"] = m.r.r2.encoded(policy)
    p = json.loads(files["plan.json"])
    p.update(
        schema_version=m.SCHEMA,
        status=m.STATUS,
        resources=m.PROFILE,
        source_root=str(m.ROOT),
        python=sys.executable,
        python_sha256="b" * 64,
        tools=dict.fromkeys(m.o.TOOLS, sys.executable),
        tool_sha256=dict.fromkeys(m.o.TOOLS, "b" * 64),
        materialization_original_sha256=m.r.r2.digest(m.r.r2.encoded(audit_fixture())),
        warehouse_selection_sha256=m.r.r2.digest(files["warehouse_selection.json"]),
    )
    files["plan.json"] = m.r.r2.encoded(p)
    files["materialization.original.json"] = m.r.r2.encoded(audit_fixture())
    job = {"job_id": "123", "source_commit": SHA, "plan_sha256": m.r.r2.digest(files["plan.json"])}
    files["job.json"] = files["batch_entry.json"] = m.r.r2.encoded(job)
    allocated_raw = allocation_text(TimeLimit="1-06:00:00")
    files["allocation_query.json"] = m.r.r2.encoded({"returncode": 0, "stdout": allocated_raw})
    files["allocation.json"] = m.r.r2.encoded(m.allocation(allocated_raw, "123", 1271))
    files["hardware.json"] = m.r.r2.encoded(hardware_fixture())
    old, _ = science_files()
    population = json.loads(files["warehouse_selection.json"])
    ids = [x["warehouse_id"] for x in population["members"]]
    pop = m.r.warehouses.membership_receipt(
        SimpleNamespace(
            warehouses=ids, existing_warehouses=ids[:146], candidate_warehouses=ids[146:]
        ),
        population,
    )
    vector = {
        "unmet": [[f"C{i}", "P1", 90000.0] for i in range(54)],
        "static": [[v, 45000.0] for v in ids],
        "reception": [[v, 45000.0] for v in ids],
    }
    contract = {
        "penalty_vector": vector,
        "penalty_vector_sha256": canonical_hash(vector),
        "emergency_static_unit": "stock_tonnes_at_warehouse_period",
        "emergency_reception_unit": "overflow_tonnes_in_period",
    }
    for i, (arm, spec) in enumerate(zip(m.ARMS, p["cases"], strict=True)):
        prefix = "cases/" + spec["name"]
        base = prefix + "/products/" + spec["name"] + "/"
        old_base = "cases/tiny_sto/products/tiny_sto/"
        for name in (
            "result.json",
            "independent_validation.json",
            "run_summary.json",
            "model_audit.json",
            "preflight.json",
        ):
            files[base + name] = old[old_base + name]
        result = json.loads(files[base + "result.json"])
        result["experiment"] = spec
        result["result"]["objective_bound"] = 99.5
        result["result"]["metadata"].update(objective_bound=99.5, gurobi_native_gap=0.005)
        files[base + "result.json"] = m.r.r2.encoded(result)
        files[base + "run_completion.json"] = m.r.r2.encoded(
            {
                "status": "complete",
                "run_identity": result["result"]["metadata"]["run_identity"],
                "artifacts": {
                    n.removeprefix(base): m.r.r2.digest(b)
                    for n, b in files.items()
                    if n.startswith(base)
                },
            }
        )
        files[prefix + "/warehouses_used.json"] = m.r.r2.encoded(pop)
        files[prefix + "/warehouses_used.csv"] = m.r.warehouses.csv_bytes(pop["included"])
        files[prefix + "/input_receipt.json"] = m.r.r2.encoded(
            {
                "experiment": spec,
                "shape": m.h.SHAPE,
                "warehouse_selection": pop,
                "effective_scenario_probabilities": {f"s{k}": 1 / 9 for k in range(9)},
                "mathematical_contract": contract,
                "frozen_penalty_review": m.h.penalty_receipt(contract, warehouse_ids=ids),
            }
        )
        control = "control/" + arm + "/"
        entry = {**job, "step_id": str(i), "mode": arm, "started_monotonic": 0}
        files[control + "entry.json"] = files[control + "release.json"] = m.r.r2.encoded(entry)
        files[control + "step_query.json"] = m.r.r2.encoded(
            {
                "returncode": 0,
                "stdout": (
                    f"StepId=123.{i} UserId=1271 CPUs=24 Nodes=1 Tasks=1 "
                    "State=RUNNING NodeList=r1i3n5"
                ),
            }
        )
        ev = events(entry)
        for k, e in enumerate(ev):
            files[control + f"phase-{k:02d}.json"] = m.r.r2.encoded(e)
        files[control + "controller.json"] = m.r.r2.encoded(
            {
                "status": "closed_feasible_arm",
                "local_client_reaped": True,
                "step_id": str(i),
                "usage": m.o.phase_usage(ev, 30),
                "product_review_seconds": 1,
            }
        )
        files[control + "license_capability.json"] = m.r.r2.encoded(
            {
                "status": "accepted",
                "license_file": "/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic",
                "probe_variable_count": 2001,
                "probe_constraint_count": 2001,
                "objective_value": 2001,
                "gurobi_version": [13, 0, 3],
            }
        )
        files[control + "runtime.json"] = m.r.r2.encoded(
            {
                **hardware_fixture(),
                "python": "3.13.15",
                "python_sha256": "b" * 64,
                "gurobi_version": [13, 0, 3],
                "solver_threads": m.h.ORDER[i],
                "slurm_step_allocated_cpus": 24,
                "worker_affinity_logical_cpus": 16,
            }
        )
        files[control + "native_terminal.json"] = m.r.r2.encoded(
            {
                "entry": entry,
                "status_code": 9,
                "solution_count": 1,
                "runtime_seconds": 3600.5,
                "time_limit_seconds": 14400,
                "objective": 100.0,
            }
        )
    files["batch_outcome.json"] = m.r.r2.encoded(
        {
            "status": "block_returned",
            "completed_arms": list(m.ARMS),
            "unrun": [],
            "source_verified_after": True,
        }
    )
    files["accounting.txt"] = (
        "123|COMPLETED|0:0|200|\n123.batch|COMPLETED|0:0|200|12K\n"
        "123.extern|COMPLETED|0:0|200|1K\n"
        + "".join(f"123.{i}|COMPLETED|0:0|30|1K\n" for i in range(5))
    ).encode()
    reviewed = m.science_review(files, p)
    for arm, chosen in zip(m.ARMS, reviewed["arms"], strict=True):
        files["control/" + arm + "/review.json"] = m.r.r2.encoded(chosen)
    return files, p


def materialize(tmp_path, monkeypatch):
    files, p = fixture()
    claim = tmp_path / m.CLAIM
    claim.mkdir()
    for name, data in files.items():
        if name == "accounting.txt":
            continue
        target = claim / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    monkeypatch.setattr(m, "load", lambda *_: p)
    return claim, files, p


def test_full_five_arm_portable_block_preserves_scalar_metrics_and_no_follow_on():
    files, _ = fixture()
    report = m.portable_review(files)
    assert report["status"] == "block_quality_target_met" and report["operational_receipts_closed"]
    assert [a["threads"] for a in report["arms"]] == list(m.h.ORDER)
    assert report["penalty_rates"] == m.h.RATES
    assert all(report[k] is False for k in m.r.closed())


@pytest.mark.parametrize("wall", ["1-06:00:00", "30:00:00"])
def test_slurm30_hour_formats(wall):
    assert m.allocation(allocation_text(TimeLimit=wall), "123", 1271)["TimeLimit"] == wall


@pytest.mark.parametrize(
    "changes",
    [
        {"TimeLimit": "14:00:00"},
        {"TimeLimit": "2-00:00:00"},
        {"TimeLimit": "1-30:00:00"},
        {"NumCPUs": "16"},
        {"UserId": "other(2)"},
        {"MinMemoryNode": "256G"},
        {"TRES": "cpu=24,mem=8G,node=1"},
        {"NodeList": "r1,r2"},
        {"QOS": "normal"},
    ],
)
def test_wrong_allocation_fails_closed(changes):
    with pytest.raises(ValueError):
        m.allocation(
            allocation_text(TimeLimit="1-06:00:00", **changes)
            if "TimeLimit" not in changes
            else allocation_text(**changes),
            "123",
            1271,
        )


@pytest.mark.parametrize(
    "name",
    [
        "allocation_query.json",
        "hardware.json",
        "control/t4/release.json",
        "control/t1/controller.json",
        "control/t8/license_capability.json",
        "control/t2/phase-01.json",
        "control/t16/runtime.json",
        "batch_outcome.json",
        "control/t4/review.json",
        "control/t16/native_terminal.json",
    ],
)
def test_missing_operational_receipt_is_forensic_not_success(name):
    files, _ = fixture()
    del files[name]
    report = m.portable_review(files)
    assert report["status"] == "forensic_partial_block_preserved"
    assert not report["operational_receipts_closed"]


@pytest.mark.parametrize(
    "change",
    [
        "affinity",
        "python",
        "version",
        "threads",
        "step_cpu",
        "owner",
        "phase",
        "budget",
        "cancel",
        "extra_step",
    ],
)
def test_runtime_phase_accounting_and_ownership_drift_not_promoted(change):
    files, _ = fixture()
    name = "control/t1/runtime.json"
    data = json.loads(files[name])
    if change == "affinity":
        data["affinity_logical_cpus"][0] = 99
    elif change == "python":
        data["python"] = "3.12.1"
    elif change == "version":
        data["gurobi_version"] = [13, 0, 4]
    elif change == "threads":
        data["solver_threads"] = 4
    elif change in {"step_cpu", "owner"}:
        name = "control/t1/step_query.json"
        data = json.loads(files[name])
        data["stdout"] = (
            data["stdout"].replace("CPUs=24", "CPUs=16")
            if change == "step_cpu"
            else data["stdout"].replace("UserId=1271", "UserId=2")
        )
    elif change == "phase":
        name = "control/t1/phase-01.json"
        data = json.loads(files[name])
        data["entry"]["job_id"] = "9"
    elif change == "budget":
        name = "control/t1/controller.json"
        data = json.loads(files[name])
        data["product_review_seconds"] = 1801
    else:
        files["accounting.txt"] = (
            files["accounting.txt"].replace(b"123.1|COMPLETED|0:0", b"123.1|CANCELLED by 1271|0:9")
            if change == "cancel"
            else files["accounting.txt"] + b"123.5|COMPLETED|0:0|1|1K\n"
        )
    files[name] = m.r.r2.encoded(data)
    assert not m.portable_review(files)["operational_receipts_closed"]


def test_penalty_drift_preserved_as_rejected_arm_not_reweighted():
    files, _ = fixture()
    name = "cases/scalar_h300_t4/input_receipt.json"
    data = json.loads(files[name])
    data["mathematical_contract"]["penalty_vector"]["unmet"][0][-1] = 90001
    data["mathematical_contract"]["penalty_vector_sha256"] = canonical_hash(
        data["mathematical_contract"]["penalty_vector"]
    )
    files[name] = m.r.r2.encoded(data)
    report = m.portable_review(files)
    assert not report["quality_target_met"] and len(report["arms"]) == 4
    assert report["missing_or_rejected"]


def test_terminal_collect_and_repeat_audit_are_immutable(tmp_path, monkeypatch):
    claim, files, _ = materialize(tmp_path, monkeypatch)

    def command(*_):
        return SimpleNamespace(returncode=0, stdout=files["accounting.txt"].decode())

    first = m.collect(claim, SHA, command=command)
    raw = (claim / m.ARCHIVE).read_bytes()
    assert m.collect(claim, SHA, command=lambda *_: pytest.fail("No second query")) == first
    assert (claim / m.ARCHIVE).read_bytes() == raw
    assert m.audit(claim / m.ARCHIVE, first["sha256"])["status"] == first["status"]


def test_missing_or_running_launched_accounting_waits_without_archive(tmp_path, monkeypatch):
    claim, files, _ = materialize(tmp_path, monkeypatch)
    for raw in (
        files["accounting.txt"].decode().replace("123.4|COMPLETED|0:0|30|1K\n", ""),
        files["accounting.txt"].decode().replace("123.4|COMPLETED", "123.4|RUNNING"),
    ):
        assert (
            m.collect(
                claim, SHA, command=lambda *_, text=raw: SimpleNamespace(returncode=0, stdout=text)
            )["status"]
            == "nonterminal_or_accounting_pending"
        )
    assert not (claim / m.ARCHIVE).exists()


def test_early_failed_batch_can_collect_forensic_without_cases(tmp_path, monkeypatch):
    claim, files, _ = materialize(tmp_path, monkeypatch)
    # Preserve the synthetic directories but supply a terminal failed root. No
    # successful controller or objective can turn the scheduler failure green.
    raw = files["accounting.txt"].decode().replace("123|COMPLETED|0:0", "123|FAILED|2:0")
    report = m.collect(claim, SHA, command=lambda *_: SimpleNamespace(returncode=0, stdout=raw))
    assert report["status"] == "forensic_partial_block_preserved"


@pytest.mark.parametrize("field", ["output", "dataset", "fallback", "routes"])
def test_materialization_drift_rejected(field):
    data = audit_fixture()
    if field == "output":
        data["output_workbook_sha256"] = "0" * 64
    elif field == "dataset":
        data["distance_provenance"]["dataset_id"] = "different"
    elif field == "fallback":
        data["distance_provenance"]["fallback_count"] = 1
    else:
        data["distance_provenance"]["route_count"] -= 1
    with pytest.raises(ValueError):
        m.materialization(data)


def test_original_h300_cache_misses_are_not_mislabelled_as_new_requests():
    data = audit_fixture()
    data["distance_provenance"].update(
        osrm_request_count=20, osrm_cache_miss_count=20, osrm_cache_write_count=20
    )
    assert m.materialization(data) == data
    data["distance_provenance"]["osrm_cache_miss_count"] = -1
    with pytest.raises(ValueError):
        m.materialization(data)


def test_start_requires_human_ack_before_any_tool_or_claim(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "prepare", lambda *_a, **_k: pytest.fail("No preparation"))
    with pytest.raises(ValueError, match="acknowledgement"):
        m.start(tmp_path / m.CLAIM, SHA, False, {}, command=lambda *_: pytest.fail("No sbatch"))


@pytest.mark.parametrize(
    "response", ["", "Submitted batch job 123", "123\n124", "123;cluster\nERROR"]
)
def test_uncertain_submission_consumes_slot_without_repeat(tmp_path, monkeypatch, response):
    claim = tmp_path / m.CLAIM

    def prepare(c, *_a, **_kw):
        c.mkdir()
        m.r.r2.write(c / "plan.json", {"source_commit": SHA})
        return {"source_commit": SHA}

    monkeypatch.setattr(m, "prepare", prepare)
    from scripts import probe_npad_gurobi_license as license_probe

    monkeypatch.setattr(license_probe, "check_file", lambda: None)
    monkeypatch.delenv("SLURM_JOB_ID", raising=False)
    with pytest.raises(ValueError, match="Submission uncertain"):
        m.start(
            claim,
            SHA,
            True,
            {},
            command=lambda *_: SimpleNamespace(returncode=0, stdout=response, stderr=""),
        )
    assert (claim / "submission_intent.json").exists() and not (claim / "job.json").exists()


def test_only_startup_metadata_uses_wls_no_secret_in_wrapper():
    text = (m.ROOT / "scripts/npad_scalar_h300_30h.sh").read_text()
    assert (
        "export GRB_LICENSE_FILE=/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic" in text
    )
    assert "POST_REGRESSION_RAW_SOURCE=VERIFIED" in text
    assert "tests/test_scalar_h300_operational.py" in text
    assert "pip install" not in text and "scancel " not in text


@pytest.mark.parametrize("member", ["../outside", "/absolute", "plan.json"])
def test_archive_traversal_or_duplicate_rejected(tmp_path, monkeypatch, member):
    claim, files, _ = materialize(tmp_path, monkeypatch)
    saved = m.collect(
        claim,
        SHA,
        command=lambda *_: SimpleNamespace(returncode=0, stdout=files["accounting.txt"].decode()),
    )
    target = tmp_path / "bad.tar.gz"
    with tarfile.open(claim / m.ARCHIVE) as source, tarfile.open(target, "w:gz") as out:
        for row in source:
            out.addfile(row, source.extractfile(row))
        row = tarfile.TarInfo(member)
        row.size = 2
        out.addfile(row, io.BytesIO(b"{}"))
    with pytest.raises(ValueError, match="Unsafe/duplicate"):
        m.audit(target, m.r.file_hash(target))
    assert saved["sha256"] == m.r.file_hash(claim / m.ARCHIVE)


def test_input_reviewer_failure_prevents_original_runner_and_preserves_observed_list(tmp_path):
    from dataclasses import replace

    from tests.test_excel_loader import build_tiny_golden_excel
    from tests.test_scalar_r3a import SHAPE, tiny_selection, tiny_spec

    workbook = tmp_path / "public.xlsx"
    build_tiny_golden_excel(workbook)
    spec = tiny_spec(workbook, "sto")
    spec = replace(spec, max_estimated_variables=10000)
    target = tmp_path / "case"
    with pytest.raises(ValueError):
        m.r.run_case_software(
            spec,
            target,
            SHAPE,
            tiny_selection(),
            input_reviewer=m.input_reviewer,
            runner=lambda *_a, **_k: pytest.fail("No optimizer before rate gate"),
        )
    assert (target / "warehouses_observed.csv").is_file()
    assert m.r.r2.read(target / "case_outcome.json")["status"] == "case_failed"
    assert not (target / "products").exists()


def test_batch_stops_after_technical_failure_and_preserves_unrun(tmp_path, monkeypatch):
    files, plan = fixture()
    claim = tmp_path / m.CLAIM
    claim.mkdir()
    (claim / "plan.json").write_bytes(files["plan.json"])
    (claim / "job.json").write_bytes(files["job.json"])
    monkeypatch.setattr(m, "load", lambda *_: plan)
    monkeypatch.setattr(m.o, "verify_tools", lambda *_: None)
    monkeypatch.setattr(m.os, "getuid", lambda: 1271, raising=False)
    monkeypatch.setattr(m.os, "sched_getaffinity", lambda _: set(range(16)), raising=False)
    monkeypatch.setenv("SLURM_JOB_ID", "123")
    monkeypatch.setattr(m, "hardware", lambda _: hardware_fixture())
    monkeypatch.setattr(
        m.r.r2,
        "command",
        lambda *_: SimpleNamespace(
            returncode=0, stdout=allocation_text(TimeLimit="1-06:00:00"), stderr=""
        ),
    )
    seen = []

    def supervised(_c, _s, arm, _a, _j):
        seen.append(arm)
        return {"next_arm_allowed": arm != "t8"}

    monkeypatch.setattr(m, "supervise", supervised)
    assert m.batch(claim, SHA) == 1
    outcome = m.r.r2.read(claim / "batch_outcome.json")
    assert seen == ["t4", "t1", "t8"]
    assert outcome["completed_arms"] == ["t4", "t1"]
    assert outcome["unrun"] == ["t2", "t16"]


def test_worker_common_pool_failure_precedes_license_or_optimizer(tmp_path, monkeypatch):
    claim, _, plan = materialize(tmp_path, monkeypatch)
    # Fresh control is normally parent-owned; use a new public fixture arm slot.
    control = claim / "control" / "unbound"
    control.mkdir()
    monkeypatch.setattr(m, "ARMS", ("unbound",))
    monkeypatch.setattr(m.o, "verify_tools", lambda *_: None)
    monkeypatch.setenv("SLURM_JOB_ID", "123")
    monkeypatch.setenv("SLURM_STEP_ID", "0")
    monkeypatch.setattr(m.os, "sched_getaffinity", lambda _: {0}, raising=False)
    from scripts import probe_npad_gurobi_license as probe

    monkeypatch.setattr(
        probe, "probe", lambda: pytest.fail("No capability before common-pool proof")
    )
    publish = m.o.publish

    def release(path, value):
        publish(path, value)
        if path.name == "entry.json":
            publish(path.parent / "release.json", value)

    monkeypatch.setattr(m.o, "publish", release)
    with pytest.raises(ValueError, match="Common CPU pool unavailable"):
        m.worker(claim, SHA, "unbound")


def test_timeout_submission_preserves_intent_and_cannot_resubmit(tmp_path, monkeypatch):
    import subprocess

    claim = tmp_path / m.CLAIM

    def prepare(c, *_a, **_kw):
        c.mkdir()
        return {"source_commit": SHA}

    monkeypatch.setattr(m, "prepare", prepare)
    from scripts import probe_npad_gurobi_license as probe

    monkeypatch.setattr(probe, "check_file", lambda: None)
    monkeypatch.delenv("SLURM_JOB_ID", raising=False)

    def timeout(*_):
        raise subprocess.TimeoutExpired("sbatch", 30)

    with pytest.raises(subprocess.TimeoutExpired):
        m.start(claim, SHA, True, {}, command=timeout)
    assert (claim / "submission_intent.json").exists()
    monkeypatch.setattr(m, "load", lambda *_: {})
    with pytest.raises(ValueError, match="Regular unlinked"):
        m.start(claim, SHA, True, {}, command=lambda *_: pytest.fail("No second sbatch"))


def test_complete_operational_prepare_load_and_original_audit_binding(tmp_path, monkeypatch):
    fixture_files, _ = fixture()
    workbook = tmp_path / "hash_only_public.xlsx"
    workbook.write_bytes(b"Public hash preparation fixture, no Excel ETL")
    monkeypatch.setattr(m.h, "WORKBOOK_SHA", m.r.file_hash(workbook))
    audit_path = tmp_path / "materialization.json"
    m.r.r2.write(audit_path, audit_fixture())
    policy = json.loads(fixture_files["warehouse_selection.json"])
    monkeypatch.setattr(m.r.warehouses, "read_policy", lambda *_: policy)
    monkeypatch.setattr(
        m.h, "verify_h215", lambda _: json.loads(fixture_files["plan.json"])["predecessor"]
    )
    monkeypatch.setattr(
        m.r.r2, "source_inventory", lambda _: json.loads(fixture_files["source.json"])
    )
    monkeypatch.setattr(m.r.r2, "verify_source", lambda *_: None)
    monkeypatch.setattr(m.shutil, "which", lambda _: sys.executable)
    claim = tmp_path / m.CLAIM
    plan = m.prepare(claim, SHA, workbook, None, None, audit_path, None)
    assert plan == m.load(claim, SHA)
    assert (claim / "materialization.original.json").read_bytes() == audit_path.read_bytes()
    with pytest.raises(ValueError, match="Fresh exclusive"):
        m.prepare(claim, SHA, workbook, None, None, audit_path, None)
    (claim / "materialization.original.json").write_bytes(b"mutated")
    with pytest.raises(ValueError, match="Audit drift"):
        m.load(claim, SHA)
