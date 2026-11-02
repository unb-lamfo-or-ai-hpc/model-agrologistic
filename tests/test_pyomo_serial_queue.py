"""Finite graph, held submission, source compatibility and failure ownership."""

import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


Q = module("serial_queue_unit", ROOT / "scripts/pyomo_serial_queue.py")


@pytest.fixture
def context(tmp_path, monkeypatch):
    q = Q
    queue = tmp_path / q.QUEUE.name
    queue.mkdir()
    (queue / "jobs").mkdir()
    campaign = tmp_path / ".mvp2-pyomo-scaling-native8h-v1"
    campaign.mkdir()
    monkeypatch.setattr(q, "BASE", tmp_path)
    monkeypatch.setattr(q, "CAMPAIGN", campaign)
    monkeypatch.setattr(q.os, "getuid", lambda: 123, raising=False)
    monkeypatch.setattr(q, "login", lambda: None)
    monkeypatch.setattr(q, "check_storage", lambda manifest: None)
    graph = q.schedule()
    attached = {
        "solve:" + cell: {
            "job_id": job,
            "source_commit": q.ENGINE_SHA,
            "plan_sha256": sha,
            "attached_existing": True,
        }
        for cell, (job, sha) in q.ATTACHED.items()
    }
    manifest = {"schedule": graph, "attached": attached, "controller_commit": "a" * 40}
    q.write(queue / "queue.json", manifest)
    q.write(
        queue / "prepared.json", {"queue_sha256": q.digest(queue / "queue.json"), "new_jobs": 93}
    )
    engine = SimpleNamespace(
        scheduler_arguments=lambda: [
            "--account=sxdsouza",
            "--partition=intel-256",
            "--qos=preempt",
            "--nodes=1",
            "--ntasks=1",
            "--cpus-per-task=24",
            "--mem=192G",
            "--time=12:00:00",
            "--exclusive",
            "--no-requeue",
        ],
        c=SimpleNamespace(digest=lambda x: hashlib.sha256(q.encoded(x)).hexdigest()),
        read=q.read,
        write_json=q.write,
        o=SimpleNamespace(fields=json.loads),
    )
    monkeypatch.setattr(q, "root_context", lambda *a, **k: (manifest, engine, {}))
    for node in graph["jobs"]:
        directory = q.node_directory(queue, node)
        directory.mkdir()
        if node["id"] in attached:
            q.write(directory / "job.json", attached[node["id"]])
        else:
            (directory / "batch.sh").write_text(
                q.script_text(queue, node, "a" * 40), encoding="utf-8", newline="\n"
            )
        if node["kind"] == "scientific_solve" and node["cell"] not in q.ATTACHED:
            claim = campaign / node["cell"]
            claim.mkdir()
            q.write(claim / "plan.json", {"cell": node["cell"]})
    return SimpleNamespace(q=q, queue=queue, manifest=manifest, engine=engine, graph=graph)


class Scheduler:
    def __init__(self, ctx):
        self.ctx = ctx
        self.calls = []
        self.submissions = []
        self.fail_at = None
        self.timeout_at = None
        self.external_state = "RUNNING"
        self.queue_output = "2231591\n2231593\n"
        self.release_rc = 0
        self.field_override = {}
        self.drop_external_dependencies = False

    def __call__(self, argv):
        self.calls.append(argv)
        if argv[0] == "squeue":
            assert "--array" in argv
            return SimpleNamespace(returncode=0, stdout=self.queue_output, stderr="")
        if argv[0] == "sacct":
            return SimpleNamespace(
                returncode=0, stdout=f"{argv[2]}|{self.external_state}|0:0|1|\n", stderr=""
            )
        if argv[0] == "sbatch":
            self.submissions.append(argv)
            if len(self.submissions) == self.timeout_at:
                raise subprocess.TimeoutExpired(argv, 60)
            if len(self.submissions) == self.fail_at:
                return SimpleNamespace(returncode=1, stdout="", stderr="Rejected fixture")
            return SimpleNamespace(
                returncode=0, stdout=str(10000 + len(self.submissions)), stderr=""
            )
        if argv[:2] == ["scontrol", "release"]:
            return SimpleNamespace(returncode=self.release_rc, stdout="", stderr="")
        if argv[:4] == ["scontrol", "-o", "show", "job"]:
            job_id = argv[4]
            for node in self.ctx.graph["jobs"]:
                directory = self.ctx.q.node_directory(self.ctx.queue, node)
                receipt = self.ctx.q.read(directory / "job.json")
                if receipt["job_id"] == job_id:
                    minutes = node["wall_seconds"] // 60
                    fields = {
                        "JobId": job_id,
                        "JobState": "PENDING",
                        "Priority": "0",
                        "Reason": "JobHeldUser",
                        "UserId": f"fixture({os.getuid()})",
                        "WorkDir": str(directory),
                        "Command": str(directory / "batch.sh"),
                        "Partition": "intel-256",
                        "Account": "sxdsouza",
                        "QOS": "preempt",
                        "Requeue": "0",
                        "Dependency": receipt["dependency"] or "(null)",
                        "TimeLimit": f"{minutes // 60:02}:{minutes % 60:02}:00",
                        "MinMemoryNode": str(node["memory_mib"]) + "M",
                        "NumNodes": "1",
                        "NumCPUs": str(node["requested_cpus"]),
                        "OverSubscribe": "NO",
                    }
                    fields.update(self.field_override)
                    if self.drop_external_dependencies:
                        pairs = Q.dependency_pairs(fields["Dependency"])
                        fields["Dependency"] = (
                            ",".join(
                                kind + ":" + dep
                                for kind, dep in sorted(pairs)
                                if dep not in {"2231591", "2231593"}
                            )
                            or "(null)"
                        )
                    return SimpleNamespace(returncode=0, stdout=json.dumps(fields), stderr="")
        raise AssertionError(argv)


def test_full_finite_graph_preserves_90_cells_and_two_consumed_anchors():
    plan = Q.schedule()
    assert len(plan["jobs"]) == 95
    assert len(plan["new_scientific_cells"]) == 88
    assert len({x["id"] for x in plan["original_cells"]}) == 90
    assert set(Q.ATTACHED).isdisjoint(Q.ANCHORS)


@pytest.mark.parametrize(
    "field,value",
    [
        ("seed", 0),
        ("threads", 32),
        ("native_seconds", 14400),
        ("memory_mib", 524288),
        ("mip_gap_target", 0.1),
        ("worker_logical_cpus", 32),
        ("exclusive", False),
        ("requested_cpus", 16),
        ("wall_seconds", 172800),
        ("solver", "cbc"),
    ],
)
def test_changed_scientific_contract_rejected(tmp_path, field, value):
    plan = copy.deepcopy(Q.schedule())
    plan["jobs"][0][field] = value
    path = tmp_path / "schedule.json"
    Q.write(path, plan)
    with pytest.raises(ValueError):
        Q.schedule(path)


def test_broken_serial_lane_and_cycle_rejected(tmp_path):
    plan = copy.deepcopy(Q.schedule())
    node = next(x for x in plan["jobs"] if x["kind"] == "scientific_solve" and x["parents"])
    node["parents"] = []
    path = tmp_path / "broken.json"
    Q.write(path, plan)
    with pytest.raises(ValueError):
        Q.schedule(path)
    plan["jobs"][0]["parents"] = [plan["jobs"][-1]["id"]]
    path = tmp_path / "cycle.json"
    Q.write(path, plan)
    with pytest.raises(ValueError):
        Q.schedule(path)


@pytest.mark.parametrize("identity", ["../arbitrary", "solve:../../x", "control:x;y", "solve:x_y"])
def test_unowned_node_path_rejected(identity):
    with pytest.raises(ValueError):
        Q.slug(identity)


def test_writes_exclusive_and_canonical(tmp_path):
    path = tmp_path / "record.json"
    Q.write(path, {"z": "ação", "a": 1})
    assert path.read_bytes() == Q.encoded({"a": 1, "z": "ação"})
    with pytest.raises(FileExistsError):
        Q.write(path, {})


def test_submit_only_93_new_jobs_all_held_and_attach_existing_two(context):
    scheduler = Scheduler(context)
    result = Q.submit(context.queue, "a" * 40, command=scheduler)
    assert result["new_jobs"] == 93 and not result["release_performed"]
    assert len(scheduler.submissions) == 93
    assert all(
        "--hold" in args and "--no-requeue" in args and "--kill-on-invalid-dep=yes" in args
        for args in scheduler.submissions
    )
    assert not any(args[:2] == ["scontrol", "release"] for args in scheduler.calls)
    assert not any(
        "--job-name=serial-solve__" + cell in " ".join(args)
        for cell in Q.ATTACHED
        for args in scheduler.submissions
    )
    with pytest.raises(ValueError, match="Existing submission intent"):
        Q.submit(context.queue, "a" * 40, command=scheduler)
    assert len(scheduler.submissions) == 93


@pytest.mark.parametrize("mode", ["reject", "timeout"])
def test_partial_submission_never_releases_or_retries(context, mode):
    scheduler = Scheduler(context)
    if mode == "reject":
        scheduler.fail_at = 3
    else:
        scheduler.timeout_at = 3
    with pytest.raises(ValueError):
        Q.submit(context.queue, "a" * 40, command=scheduler)
    assert not (context.queue / "submitted.json").exists()
    assert (context.queue / "submission_intent.json").is_file()
    assert len(scheduler.submissions) == 3
    assert not any(args[:2] == ["scontrol", "release"] for args in scheduler.calls)
    with pytest.raises(ValueError, match="Existing submission intent"):
        Q.submit(context.queue, "a" * 40, command=scheduler)
    assert len(scheduler.submissions) == 3


def test_current_jobs_include_expanded_arrays_and_reserve(context):
    scheduler = Scheduler(context)
    scheduler.queue_output = "\n".join("900_" + str(i) for i in range(3))
    with pytest.raises(ValueError, match="headroom"):
        Q.submit(context.queue, "a" * 40, command=scheduler)
    assert not scheduler.submissions
    assert not (context.queue / "submission_intent.json").exists()


def test_terminal_attached_jobs_not_used_as_stale_dependencies(context):
    scheduler = Scheduler(context)
    scheduler.external_state = "COMPLETED"
    Q.submit(context.queue, "a" * 40, command=scheduler)
    pilot = next(
        args for args in scheduler.submissions if "--job-name=serial-control__h300-pilots" in args
    )
    assert not any(arg.startswith("--dependency=") for arg in pilot)


@pytest.mark.parametrize("state", ["RUNNING", "COMPLETED"])
def test_removed_external_dependency_requires_proven_terminal_parent(context, state):
    scheduler = Scheduler(context)
    Q.submit(context.queue, "a" * 40, command=scheduler)
    scheduler.drop_external_dependencies = True
    scheduler.external_state = state
    if state == "RUNNING":
        with pytest.raises(ValueError, match="dependency differs"):
            Q.release(context.queue, "a" * 40, command=scheduler)
    else:
        assert Q.release(context.queue, "a" * 40, command=scheduler)["new_jobs"] == 93


def test_release_complete_graph_once_and_retain_external_jobs(context):
    scheduler = Scheduler(context)
    Q.submit(context.queue, "a" * 40, command=scheduler)
    result = Q.release(context.queue, "a" * 40, command=scheduler)
    assert result["new_jobs"] == 93
    calls = [args for args in scheduler.calls if args[:2] == ["scontrol", "release"]]
    assert len(calls) == 1 and len(calls[0][2].split(",")) == 93
    assert not set(Q.ATTACHED.values()) & set(calls[0][2].split(","))
    assert "2231591" not in calls[0][2] and "2231593" not in calls[0][2]
    with pytest.raises(ValueError, match="Existing release intent"):
        Q.release(context.queue, "a" * 40, command=scheduler)
    assert len([args for args in scheduler.calls if args[:2] == ["scontrol", "release"]]) == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("UserId", "other(999999)"),
        ("Command", "/arbitrary.sh"),
        ("Partition", "other"),
        ("QOS", "other"),
        ("Requeue", "1"),
        ("Dependency", "afterany:777"),
        ("TimeLimit", "48:00:00"),
        ("MinMemoryNode", "512G"),
        ("OverSubscribe", "YES:4"),
        ("NumCPUs", "1"),
        ("Reason", "Priority"),
        ("Priority", "100"),
        ("JobState", "RUNNING"),
    ],
)
def test_wrong_held_job_never_released(context, field, value):
    scheduler = Scheduler(context)
    Q.submit(context.queue, "a" * 40, command=scheduler)
    scheduler.field_override[field] = value
    with pytest.raises(ValueError):
        Q.release(context.queue, "a" * 40, command=scheduler)
    assert not (context.queue / "released.json").exists()
    assert not any(args[:2] == ["scontrol", "release"] for args in scheduler.calls)


def test_uncertain_release_stays_consumed_without_completion_marker(context):
    scheduler = Scheduler(context)
    Q.submit(context.queue, "a" * 40, command=scheduler)
    scheduler.release_rc = 1
    with pytest.raises(ValueError, match="uncertain"):
        Q.release(context.queue, "a" * 40, command=scheduler)
    assert (context.queue / "release_intent.json").is_file()
    assert not (context.queue / "released.json").exists()
    with pytest.raises(ValueError, match="Existing release"):
        Q.release(context.queue, "a" * 40, command=scheduler)


@pytest.mark.parametrize("quality,incumbent", [(False, False), (False, True), (True, True)])
def test_native_censoring_and_gap_miss_do_not_become_operational_failures(quality, incumbent):
    assert Q.healthy_observation(
        {
            "operational_receipts_closed": True,
            "native_result_returned": True,
            "incumbent_validation_rejected": False,
            "quality_target_met": quality,
            "has_usable_incumbent": incumbent,
        }
    )


@pytest.mark.parametrize("field", ["operational_receipts_closed", "native_result_returned"])
def test_incomplete_observation_cannot_open_stage(field):
    record = {
        "operational_receipts_closed": True,
        "native_result_returned": True,
        "incumbent_validation_rejected": False,
    }
    record[field] = False
    assert not Q.healthy_observation(record)


def test_invalid_incumbent_cannot_open_stage():
    assert not Q.healthy_observation(
        {
            "operational_receipts_closed": True,
            "native_result_returned": True,
            "incumbent_validation_rejected": True,
        }
    )


def test_compute_requires_confirmed_complete_release(context, monkeypatch):
    scheduler = Scheduler(context)
    Q.submit(context.queue, "a" * 40, command=scheduler)
    node = next(n for n in context.graph["jobs"] if n["id"] not in context.manifest["attached"])
    job = Q.read(Q.node_directory(context.queue, node) / "job.json")
    monkeypatch.setenv("SLURM_JOB_ID", job["job_id"])
    ticks = iter((0, 121))
    monkeypatch.setattr(Q.time, "monotonic", lambda: next(ticks))
    with pytest.raises(ValueError, match="Complete release"):
        Q.compute_context(context.queue, "a" * 40, node["id"])


@pytest.mark.parametrize("foreign", [False, True])
def test_compute_allocation_and_owned_job_checked_after_release(context, monkeypatch, foreign):
    scheduler = Scheduler(context)
    Q.submit(context.queue, "a" * 40, command=scheduler)
    Q.release(context.queue, "a" * 40, command=scheduler)
    node = next(n for n in context.graph["jobs"] if n["id"] not in context.manifest["attached"])
    job = Q.read(Q.node_directory(context.queue, node) / "job.json")
    monkeypatch.setenv("SLURM_JOB_ID", job["job_id"])
    scheduler.field_override = {"JobState": "RUNNING"}
    if foreign:
        scheduler.field_override["UserId"] = "other(456)"
    monkeypatch.setattr(Q, "run", scheduler)
    if foreign:
        with pytest.raises(ValueError, match="ownership"):
            Q.compute_context(context.queue, "a" * 40, node["id"])
    else:
        assert Q.compute_context(context.queue, "a" * 40, node["id"])[3] == node


def pure_contract():
    path = Path(os.environ.get("AGRO_SERIAL_TEST_ENGINE_ROOT", ROOT))
    return module("serial_contract_unit", path / "scripts/pyomo_scaling_contract.py")


def pilots(c):
    return [
        {
            "cell": c.cell(300, solver, threads, 1),
            "campaign_sha256": Q.CAMPAIGN_SHA,
            "operational_receipts_closed": True,
            "native_result_returned": True,
            "incumbent_validation_rejected": False,
            "quality_target_met": False,
            "has_usable_incumbent": False,
            "worker_affinity_logical_cpus": 16,
            "matrix_sha256": "m" * 64,
            "bounds_sha256": "b" * 64,
            "hardware_class_sha256": "h" * 64,
            "resource_observation": {
                "status": "timely_samples",
                "sampled_worker_tree_peak_bytes": 1024**3,
            },
        }
        for solver in ("gurobi", "highs")
        for threads in (1, 16)
    ]


def test_missing_four_pilot_gate_blocks_compute_health_before_any_private_build(
    context, monkeypatch
):
    engine = context.engine
    engine.c = pure_contract()
    node = next(
        n
        for n in context.graph["jobs"]
        if n.get("stage") == "h300-remaining" and n["kind"] == "scientific_solve"
    )
    directory = Q.node_directory(context.queue, node)
    monkeypatch.setattr(
        Q, "compute_context", lambda *a: (context.manifest, engine, {}, node, directory)
    )
    monkeypatch.setattr(Q, "required_pilots", lambda *a: [])
    with pytest.raises(ValueError, match="Four original pilot"):
        Q.health(context.queue, "a" * 40, node["id"])
    assert not (directory / "health.json").exists()


@pytest.mark.parametrize("bad", [None, "memory", "matrix", "hardware", "closure", "validation"])
def test_stage_uses_real_memory_and_binding_gate_without_selecting_by_quality(
    context, monkeypatch, bad
):
    engine = context.engine
    engine.c = pure_contract()
    records = pilots(engine.c)
    changed = records[1]
    if bad == "memory":
        changed["resource_observation"]["sampled_worker_tree_peak_bytes"] = 0.81 * 192 * 1024**3
    elif bad == "matrix":
        changed["matrix_sha256"] = "different"
    elif bad == "hardware":
        changed["hardware_class_sha256"] = "different"
    elif bad == "closure":
        changed["operational_receipts_closed"] = False
    elif bad == "validation":
        changed["incumbent_validation_rejected"] = True
    by_id = {row["cell"]["id"]: row for row in records}
    for cell, row in by_id.items():
        claim = Q.CAMPAIGN / cell
        claim.mkdir(exist_ok=True)
        Q.write(claim / "collection.json", {"observation": row})
    engine.archive_report = lambda claim, saved: saved["observation"]
    node = next(n for n in context.graph["jobs"] if n["id"] == "control:h300-pilots")
    directory = Q.node_directory(context.queue, node)
    monkeypatch.setattr(
        Q, "compute_context", lambda *a: (context.manifest, engine, {}, node, directory)
    )
    monkeypatch.setitem(
        sys.modules,
        "pyomo_serial_collection",
        SimpleNamespace(collect=lambda e, claim, sha, **kwargs: {"observation": by_id[claim.name]}),
    )
    rc = Q.collect_stage(context.queue, "a" * 40, node["id"])
    report = Q.read(directory / "stage_result.json")
    assert (rc == 0) is (bad is None)
    assert (report["status"] == "accepted") is (bad is None)
    assert not any(row["quality_target_met"] for row in report["rows"])


def test_final_export_keeps_all_90_cells_without_fabricated_numerical_results(context, monkeypatch):
    import csv

    scheduler = Scheduler(context)
    Q.submit(context.queue, "a" * 40, command=scheduler)
    engine = context.engine
    engine.c = pure_contract()
    engine.o.job_receipt = lambda claim, sha: Q.read(claim / "job.json")
    node = next(n for n in context.graph["jobs"] if n["kind"] == "final_consolidation")
    directory = Q.node_directory(context.queue, node)
    monkeypatch.setattr(
        Q, "compute_context", lambda *a: (context.manifest, engine, {}, node, directory)
    )
    monkeypatch.setattr(Q, "accounting", lambda *a: {"state": "CANCELLED"})
    assert Q.final(context.queue, "a" * 40, node["id"]) == 0
    with (directory / "tables/results.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 90 and len({row["id"] for row in rows}) == 90
    assert all(row["objective"] == row["common_gap"] == row["native_seconds"] == "" for row in rows)


def test_legacy_engine_accepts_new_plan_with_identical_scientific_payload(tmp_path, monkeypatch):
    path = Path(os.environ.get("AGRO_SERIAL_TEST_ENGINE_ROOT", ROOT))
    engine = module("serial_legacy_plan_engine", path / "scripts/pyomo_scaling_campaign.py")
    base = tmp_path / "audit"
    base.mkdir()
    campaign_path = base / engine.c.CAMPAIGN
    campaign_path.mkdir()
    monkeypatch.setattr(engine, "BASE", base)
    monkeypatch.setattr(Q, "CAMPAIGN", campaign_path)
    campaign = {
        "inputs": {str(p): {"workbook": str(base / f"h{p}.xlsx")} for p in engine.c.POPULATIONS}
    }
    for paths in campaign["inputs"].values():
        Path(paths["workbook"]).write_bytes(b"Public serialization fixture; not parsed or solved")
    monkeypatch.setattr(Q, "CAMPAIGN_SHA", engine.c.digest(campaign))
    monkeypatch.setattr(engine, "load_campaign", lambda *a, **k: campaign)
    for population in (300, 400, 500):
        for solver in ("gurobi", "highs"):
            item = engine.c.cell(population, solver, 8, 2)
            selection = {"included": [], "frozen_test_identity": population}
            claim = campaign_path / item["id"]
            claim.mkdir()
            plan = Q.make_run_plan(engine, campaign, item, selection, 7)
            engine.write_json(claim / "plan.json", plan)
            engine.write_json(claim / "warehouse_selection.json", selection)
            accepted, _ = engine.load_run(claim, Q.ENGINE_SHA, expensive=False)
            assert engine.c.encoded(accepted["cases"]) == engine.c.encoded(plan["cases"])
            assert accepted["source_commit"] == Q.ENGINE_SHA
            assert accepted["cell"]["seed"] == 42 and accepted["cell"]["native_seconds"] == 28800


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "no_originals",
        "no_engine_sources",
        "no_license",
        "no_exclusive",
        "wrong_affinity",
        "skipped",
        "wrong_source",
        "wrong_hash",
        "private_admitted",
        "zero_tests",
        "pytest_failure",
    ],
)
def test_public_qualification_requires_complete_original_source_runtime_and_no_skips(
    tmp_path, monkeypatch, fault
):
    public = tmp_path / "public"
    (public / "source").mkdir(parents=True)
    monkeypatch.setattr(Q, "PUBLIC", public)
    monkeypatch.setattr(Q, "ROOT", public / "source")
    monkeypatch.setattr(Q, "verify_sources", lambda *a: None)
    monkeypatch.setitem(
        sys.modules,
        "qualify_pyomo_serial",
        SimpleNamespace(NEW_EXPECTED_TESTS=7, NEW_TESTS=("one", "two")),
    )
    plan = {
        "new_expected_tests": 7,
        "new_tests": ["one", "two"],
        "expected_tests": 118,
        "source_commit": "a" * 40,
        "controller_files": {},
        "runtime": {"version": "fixed"},
    }
    result = {
        "status": "accepted",
        "pytest_exit": 0,
        "source_verified_after": True,
        "original_receipts_verified_after": True,
        "engine_sources_verified_after": True,
        "runtime_verified_after": True,
        "license_capacity_accepted": True,
        "exclusive_allocation_verified": True,
        "dependency_smoke_accepted": True,
        "affinity_logical_cpus": 16,
        "counts": {"tests": 118, "failures": 0, "errors": 0, "skipped": 0},
        "source_commit": "a" * 40,
        "private_execution_admitted": False,
    }
    if fault == "no_originals":
        result["original_receipts_verified_after"] = False
    elif fault == "no_engine_sources":
        result["engine_sources_verified_after"] = False
    elif fault == "no_license":
        result["license_capacity_accepted"] = False
    elif fault == "no_exclusive":
        result["exclusive_allocation_verified"] = False
    elif fault == "wrong_affinity":
        result["affinity_logical_cpus"] = 8
    elif fault == "skipped":
        result["counts"]["skipped"] = 1
    elif fault == "wrong_source":
        result["source_commit"] = "b" * 40
    elif fault == "private_admitted":
        result["private_execution_admitted"] = True
    elif fault == "zero_tests":
        plan["expected_tests"] = result["counts"]["tests"] = 0
    elif fault == "pytest_failure":
        result["pytest_exit"] = 1
    result["plan_sha256"] = hashlib.sha256(Q.encoded(plan)).hexdigest()
    if fault == "wrong_hash":
        result["plan_sha256"] = "wrong"
    Q.write(public / "plan.json", plan)
    Q.write(public / "result.json", result)
    engine = SimpleNamespace(environment=lambda: {"version": "fixed"})
    if fault is None:
        assert Q.verify_qualification(engine, "a" * 40)[1]["status"] == "accepted"
    else:
        with pytest.raises(ValueError):
            Q.verify_qualification(engine, "a" * 40)


def test_controller_file_allowlist_rejects_changed_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(Q, "FILES", ("module.py",))
    path = tmp_path / "module.py"
    path.write_bytes(b"fixed source\n")
    hashes = {"module.py": Q.digest(path)}
    Q.verify_sources(tmp_path, hashes)
    path.write_bytes(b"different source\n")
    with pytest.raises(ValueError, match="source drift"):
        Q.verify_sources(tmp_path, hashes)


def test_login_action_rejects_compute_even_on_correct_python(monkeypatch):
    monkeypatch.setenv("SLURM_JOB_ID", "123")
    with pytest.raises(ValueError, match="login only"):
        Q.login()


@pytest.mark.parametrize("budget", [None, 0, 31])
def test_full_queue_requires_explicit_output_budget_before_claim_creation(
    tmp_path, monkeypatch, budget
):
    monkeypatch.setattr(Q, "BASE", tmp_path)
    monkeypatch.setattr(Q, "login", lambda: None)
    queue = tmp_path / Q.QUEUE.name
    with pytest.raises(ValueError, match="usable output/archive budget"):
        Q.prepare(queue, "a" * 40, storage_budget_gib=budget)
    assert not queue.exists()


def test_storage_stop_precedes_scientific_model_construction(context, monkeypatch):
    node = next(n for n in context.graph["jobs"] if n["kind"] == "scientific_solve")
    directory = Q.node_directory(context.queue, node)
    monkeypatch.setattr(
        Q, "compute_context", lambda *a: (context.manifest, context.engine, {}, node, directory)
    )

    def stopped(manifest):
        raise ValueError("Storage reserve reached")

    monkeypatch.setattr(Q, "check_storage", stopped)
    with pytest.raises(ValueError, match="Storage reserve reached"):
        Q.health(context.queue, "a" * 40, node["id"])
    assert not (directory / "health.json").exists()
