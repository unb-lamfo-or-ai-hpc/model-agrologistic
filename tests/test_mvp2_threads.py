"""Fail-closed S2 qualification without claiming licensed CI observations."""

import json
import os
import subprocess
import tarfile
from dataclasses import asdict
from types import SimpleNamespace

import pytest

from scripts import mvp2_threads as screen

SOURCE = "a" * 40
JOB = ("JobId=123 JobState=RUNNING Partition=intel-256 NumNodes=1 NumTasks=1 "
       "NodeList=r1i3n3 BatchHost=r1i3n3 CPUs/Task=16 NumCPUs=16 TRES=cpu=16,mem=16G")
NODE = "NodeName=r1i3n3 RealMemory=256000"
CGROUP = {"limit_bytes": 16 * 1024**3}


def admitted():
    return screen.allocation(JOB, NODE, "123", "r1i3n3", CGROUP, 16)


@pytest.mark.parametrize("threads", [1, 2, 4, 8, 16])
def test_thread_is_the_only_configuration_difference(threads, tmp_path):
    candidate = asdict(screen.spec(threads, tmp_path))
    reference = asdict(screen.spec(4, tmp_path))
    candidate["name"] = reference["name"]
    candidate["solver"]["threads"] = 4
    assert candidate == reference
    assert candidate["calculate_evpi_vss"] is False
    assert candidate["solver"]["compact_python_indices"] is False
    assert candidate["max_estimated_variables"] == 100000


@pytest.mark.parametrize("threads", [0, 3, 32, -1, None, True, "4"])
def test_unqualified_thread_counts_stop(threads, tmp_path):
    with pytest.raises(ValueError):
        screen.spec(threads, tmp_path)


@pytest.mark.parametrize("old,new", [
    ("RUNNING", "PENDING"), ("intel-256", "intel-512"), ("NumNodes=1", "NumNodes=2"),
    ("NumTasks=1", "NumTasks=2"), ("BatchHost=r1i3n3", "BatchHost=other"),
    ("CPUs/Task=16", "CPUs/Task=4"), ("NumCPUs=16", "NumCPUs=4"),
    ("mem=16G", "mem=192G"), ("JobId=123", "JobId=124"),
])
def test_allocation_drift_stops(old, new):
    with pytest.raises(ValueError):
        screen.allocation(JOB.replace(old, new), NODE, "123", "r1i3n3", CGROUP, 16)


@pytest.mark.parametrize("extra", [" ArrayJobId=12", " ArrayTaskId=0", " JobId=124"])
def test_array_or_ambiguous_records_stop(extra):
    with pytest.raises(ValueError):
        screen.allocation(JOB + extra, NODE, "123", "r1i3n3", CGROUP, 16)


@pytest.mark.parametrize("limit", [None, True, 1, 2**63])
def test_missing_unlimited_or_insufficient_cgroup_stops(limit):
    with pytest.raises(ValueError):
        screen.allocation(JOB, NODE, "123", "r1i3n3", {"limit_bytes": limit}, 16)


def test_affinity_is_not_inferred_from_allocated_cpus():
    assert admitted()["accessible_cpus"] == 16
    with pytest.raises(ValueError):
        screen.allocation(JOB, NODE, "123", "r1i3n3", CGROUP, 8)


def test_prepare_binds_source_runtime_tools_and_no_production(tmp_path):
    output = tmp_path / "qualification"
    record = screen.prepare(output, SOURCE)
    assert screen.check(output) == record
    assert record["large_instance_submission_allowed"] is False
    assert record["policy"]["proposed_reference"]["status"] == "proposal_not_admitted"
    with pytest.raises(FileExistsError):
        screen.prepare(output, SOURCE)


@pytest.mark.parametrize("field,value", [
    ("source_commit", "moving-branch"), ("tools", {}), ("implementation", {}),
    ("large_instance_submission_allowed", True),
])
def test_plan_drift_stops(tmp_path, field, value):
    output = tmp_path / "qualification"
    record = screen.prepare(output, SOURCE)
    record[field] = value
    (output / "plan.json").write_text(json.dumps(record))
    with pytest.raises(ValueError):
        screen.check(output)


def test_prepare_cannot_overlap_source():
    with pytest.raises(ValueError):
        screen.prepare(screen.ROOT / "should-not-exist", SOURCE)


def fixture_arm(output, threads):
    folder = output / "miniatures" / f"threads-{threads}"
    folder.mkdir(parents=True)
    summary = {"status": "optimal", "independent_validation_status": "accepted",
               "lexicographic_completed_stage_count": 3, "lexicographic_overall_status": "complete"}
    (folder / "run_summary.json").write_text(json.dumps(summary))
    settings = {role: {"Threads": threads, "Method": 2, "MIPGap": 0.1,
                       "TimeLimit": 60, "SoftMemLimit": 1, "NumericFocus": 1}
                for role in screen.ROLES}
    (folder / "solver_diagnostics.json").write_text(json.dumps(
        {"effective_stage_parameters": settings}))
    stages = [{"stage_role": role, "objective_value": 0, "final_objective_value": 0,
               "mip_gap": 0, "within_mip_degradation_limit": True} for role in screen.ROLES]
    (folder / "result.json").write_text(json.dumps(
        {"result": {"metadata": {"lexicographic_stages": stages}}}))
    (folder / "independent_validation.json").write_text(json.dumps({"status": "accepted"}))
    return folder


def test_verify_arm_requires_closed_products(monkeypatch, tmp_path):
    fixture_arm(tmp_path, 4)
    monkeypatch.setattr(screen, "verify_completion", lambda *_: (False, "changed"))
    with pytest.raises(ValueError, match="changed"):
        screen.verify_arm(tmp_path, 4)


@pytest.mark.parametrize("key,value", [
    ("status", "time_limit"), ("independent_validation_status", "rejected"),
    ("lexicographic_completed_stage_count", 2), ("lexicographic_overall_status", "partial"),
])
def test_partial_hierarchy_is_not_miniature_acceptance(monkeypatch, tmp_path, key, value):
    folder = fixture_arm(tmp_path, 4)
    monkeypatch.setattr(screen, "verify_completion", lambda *_: (True, "complete"))
    summary = screen.pair.read(folder / "run_summary.json")
    summary[key] = value
    (folder / "run_summary.json").write_text(json.dumps(summary))
    with pytest.raises(ValueError):
        screen.verify_arm(tmp_path, 4)


@pytest.mark.parametrize("key,value", [
    ("Threads", 1), ("Method", 0), ("MIPGap", 0), ("TimeLimit", 1800),
    ("SoftMemLimit", 128), ("NumericFocus", 0),
])
def test_observed_stage_parameter_drift_stops(monkeypatch, tmp_path, key, value):
    folder = fixture_arm(tmp_path, 4)
    monkeypatch.setattr(screen, "verify_completion", lambda *_: (True, "complete"))
    diagnostics = screen.pair.read(folder / "solver_diagnostics.json")
    diagnostics["effective_stage_parameters"][screen.ROLES[0]][key] = value
    (folder / "solver_diagnostics.json").write_text(json.dumps(diagnostics))
    with pytest.raises(ValueError):
        screen.verify_arm(tmp_path, 4)


def test_collector_packages_failure_without_credentials_or_unlisted_json(tmp_path):
    output = tmp_path / "qualification"
    screen.prepare(output, SOURCE)
    screen.pair.write(output / "submission.json", {"job_id": "123", "source_commit": SOURCE})
    (output / "license-secret.json").write_text("DO-NOT-EXPORT")
    fixture_arm(output, 4)
    (output / "miniatures/threads-4/unlisted.json").write_text("DO-NOT-EXPORT")
    destination = tmp_path / "collection"
    assert screen.collect(output, "123|FAILED|1:0|00:00:05|\n", destination) == 1
    with tarfile.open(destination / "threads-qualification-evidence-123.tar.gz") as stream:
        assert "license-secret.json" not in stream.getnames()
        assert "miniatures/threads-4/unlisted.json" not in stream.getnames()
        receipt = json.load(stream.extractfile("collection.json"))
        assert receipt["status"] == "evidence_rejected"
        assert receipt["large_instance_submission_allowed"] is False


def test_nonterminal_accounting_cannot_create_collection(tmp_path):
    output = tmp_path / "qualification"
    screen.prepare(output, SOURCE)
    screen.pair.write(output / "submission.json", {"job_id": "123", "source_commit": SOURCE})
    destination = tmp_path / "collection"
    with pytest.raises(ValueError):
        screen.collect(output, "123|RUNNING|0:0|\n", destination)
    assert not destination.exists()


def test_durable_driver_uses_no_compute_git_or_large_runner():
    driver = (screen.ROOT / "scripts/npad_mvp2_threads.sh").read_text()
    worker = (screen.ROOT / "scripts/run_mvp2_threads.slurm").read_text()
    assert '--cpus-per-task=16 --mem=16G --time=00:30:00' in driver
    assert 'mkdir "$CLAIM"' in driver and 'mkdir "$S2_OUTPUT/.submission-claimed"' in driver
    assert "--test-only" in driver and "hash-object" in driver and "pip install" not in driver
    assert "git " not in worker and "run_batch_hpc" not in worker
    assert "large_instance_submission_allowed" in (screen.ROOT / screen.POLICY).read_text()


def mocked_worker(monkeypatch, tmp_path):
    output = tmp_path / "qualification"
    screen.prepare(output, SOURCE)
    (output / "scheduler").mkdir()
    (output / "scheduler/job.txt").write_text(JOB)
    (output / "scheduler/node.txt").write_text(NODE)
    monkeypatch.setattr(screen, "cgroup_memory", lambda: CGROUP)
    monkeypatch.setattr(screen.os, "sched_getaffinity", lambda _: set(range(16)), raising=False)
    monkeypatch.setattr(screen, "verify_arm", lambda *_: {
        "status": "optimal", "independent_validation_status": "accepted"})
    return output


def test_fresh_children_and_license_gate_preserve_order(monkeypatch, tmp_path):
    output = mocked_worker(monkeypatch, tmp_path)
    calls = []

    def runner(command, **kwargs):
        calls.append((command, kwargs))
        if len(calls) == 1:
            screen.pair.write(output / "license.json", {"status": "accepted"})
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(screen.baseline, "license_accepted", lambda _: True)
    assert screen.execute(output, "123", "r1i3n3", runner) == 0
    assert [int(cmd[-1]) for cmd, _ in calls[1:]] == [4, 1, 8, 2, 16]
    assert all(kwargs["timeout"] == 180 for _, kwargs in calls[1:])
    receipt = screen.pair.read(output / "qualification.json")
    assert receipt["performance_acceptance"] is False
    with pytest.raises(FileExistsError):
        screen.execute(output, "123", "r1i3n3", runner)


def test_license_failure_never_starts_thread_grid(monkeypatch, tmp_path):
    output = mocked_worker(monkeypatch, tmp_path)
    calls = []

    def runner(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=1)

    with pytest.raises(ValueError, match="license"):
        screen.execute(output, "123", "r1i3n3", runner)
    assert len(calls) == 1
    assert not (output / "qualification.json").exists()


def test_failed_child_stops_remaining_grid(monkeypatch, tmp_path):
    output = mocked_worker(monkeypatch, tmp_path)
    calls = []
    monkeypatch.setattr(screen.baseline, "license_accepted", lambda _: True)

    def runner(command, **kwargs):
        calls.append(command)
        if len(calls) == 1:
            screen.pair.write(output / "license.json", {"status": "accepted"})
        return SimpleNamespace(returncode=1 if len(calls) == 3 else 0)

    with pytest.raises(ValueError, match="threads=1"):
        screen.execute(output, "123", "r1i3n3", runner)
    assert len(calls) == 3
    assert not (output / "qualification.json").exists()


def test_service_certificate_is_not_implied_by_optimal(monkeypatch, tmp_path):
    folder = fixture_arm(tmp_path, 4)
    monkeypatch.setattr(screen, "verify_completion", lambda *_: (True, "complete"))
    result = screen.pair.read(folder / "result.json")
    result["result"]["metadata"]["lexicographic_stages"][0]["final_objective_value"] = 1
    (folder / "result.json").write_text(json.dumps(result))
    with pytest.raises(ValueError, match="audit rejected"):
        screen.verify_arm(tmp_path, 4)


@pytest.mark.parametrize("alter_worker", [False, True])
def test_terminal_collector_rechecks_worker_and_product_hashes(monkeypatch, tmp_path, alter_worker):
    output = mocked_worker(monkeypatch, tmp_path)
    monkeypatch.setattr(screen.baseline, "license_accepted", lambda _: True)

    def runner(command, **kwargs):
        if "--threads" not in command:
            screen.pair.write(output / "license.json", {"status": "accepted"})
        return SimpleNamespace(returncode=0)

    screen.execute(output, "123", "r1i3n3", runner)
    screen.pair.write(output / "submission.json", {"job_id": "123", "source_commit": SOURCE})
    screen.pair.write(output / "worker_status.json", {
        "job_id": "123", "status": "failed" if alter_worker else "completed", "exit_code": 0})
    destination = tmp_path / "collection"
    assert screen.collect(output, "123|COMPLETED|0:0|00:00:05|\n", destination) == int(alter_worker)
    with tarfile.open(destination / "threads-qualification-evidence-123.tar.gz") as stream:
        receipt = json.load(stream.extractfile("collection.json"))
        assert receipt["status"] == ("evidence_rejected" if alter_worker else "accepted")
        assert all(screen.transfer.digest(stream.extractfile(name).read()) == digest
                   for name, digest in receipt["artifacts"].items())


@pytest.mark.skipif(os.name == "nt", reason="Bash syntax is qualified on Linux CI and NPAD")
def test_linux_driver_and_worker_bash_syntax():
    for name in ("npad_mvp2_threads.sh", "run_mvp2_threads.slurm"):
        subprocess.run(["bash", "-n", str(screen.ROOT / "scripts" / name)], check=True)
