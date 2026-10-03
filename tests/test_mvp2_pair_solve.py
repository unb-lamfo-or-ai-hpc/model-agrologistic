"""Original evidence, serial process isolation and exact positive-control resources."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from scripts import admit_mvp2_resource_pair as solve
from scripts import preflight_mvp2_resource_pair as inputs
from src.logic.run_integrity import file_sha256
from tests.test_mvp2_pair_preflight import JOB, NODE, inspector, prepared

SOLVE_JOB = JOB.replace("mem=16G", "mem=192G")


def evidence(tmp_path):
    plan = prepared(tmp_path)
    root = tmp_path / "input-audit"
    root.mkdir()
    scheduler = root / "scheduler"
    scheduler.mkdir()
    (scheduler / "job.txt").write_text(JOB)
    (scheduler / "node.txt").write_text(NODE)
    resource = inputs.allocation(JOB, NODE, job_id="123", node_name="r1i3n3")
    receipt = inputs.preflight(plan, root / "preflight", resource, inspector=inspector)
    path = root / "preflight/pair_preflight.json"
    return plan, path, solve.identity(receipt)


def execution(tmp_path):
    plan, receipt, reviewed = evidence(tmp_path)
    destination = tmp_path / "execution"
    solve.prepare(plan, receipt, reviewed, destination)
    return destination / "solve_plan.json"


def accept_probe(args):
    if "--output" not in args:
        return False
    solve.write(Path(args[-1]), {
        "schema_version": "npad-gurobi-license-capability-v1",
        "status": "accepted", "license_file": solve.LICENSE_FILE,
        "large_model_construction_allowed": True,
        "probe_variable_count": 2001, "probe_constraint_count": 2001,
        "solver_status_code": 2, "objective_value": 2001.0,
    })
    return True


def test_original_inputs_and_new_destination_only(tmp_path):
    plan, receipt, reviewed = evidence(tmp_path)
    before = {p: file_sha256(p) for p in tmp_path.rglob("*") if p.is_file()}
    destination = tmp_path / "execution"
    record = solve.prepare(plan, receipt, reviewed, destination)
    assert record["production_explicit_lifecycle_allowed"] is False
    assert record["arm_order"] == [0, 1]
    old = yaml.safe_load((plan.parent / "campaign.yaml").read_text())
    new = yaml.safe_load((destination / "campaign.yaml").read_text())
    assert new.pop("output_dir") == str(destination / "runs")
    old.pop("output_dir")
    assert old == new
    assert all(file_sha256(p) == digest for p, digest in before.items())
    solve.check_execution(destination / "solve_plan.json")
    with pytest.raises(ValueError):
        solve.prepare(plan, receipt, reviewed, destination)


@pytest.mark.parametrize("change", [
    "review", "receipt_status", "receipt_allocation", "products", "missing_product",
    "plan", "scheduler", "tools", "implementation", "dimensions",
])
def test_reject_changed_original_evidence_before_writing(tmp_path, change):
    plan, receipt, reviewed = evidence(tmp_path)
    value = solve.read(receipt)
    if change == "review":
        reviewed = "0" * 64
    elif change == "plan":
        plan.write_text("{}")
    elif change == "scheduler":
        (receipt.parent.parent / "scheduler/job.txt").write_text(JOB.replace("123", "124"))
    elif change in ("products", "missing_product"):
        path = receipt.parent / "mvp2_h215_warehouse_control/model_audit.json"
        if change == "products":
            path.write_text("changed")
        else:
            path.unlink()
    else:
        if change == "receipt_status":
            value["status"] = "rejected"
        elif change == "receipt_allocation":
            value["allocation"]["job_id"] = "wrong"
        elif change == "tools":
            value["tools"] = {}
        elif change == "implementation":
            value["implementation"] = {}
        elif change == "dimensions":
            value["model_size"]["total_variables"] += 1
        receipt.write_text(json.dumps(value))
        reviewed = solve.identity(value)
    destination = tmp_path / "execution"
    with pytest.raises((ValueError, KeyError, FileNotFoundError)):
        solve.prepare(plan, receipt, reviewed, destination)
    assert not destination.exists()


@pytest.mark.parametrize("target", ["pair/new", "input-audit/new", "historical/new",
                                   "qualification/new", "exists"])
def test_no_overlap_or_overwrite(tmp_path, target):
    plan, receipt, reviewed = evidence(tmp_path)
    destination = tmp_path / target
    if target == "exists":
        destination.mkdir()
    with pytest.raises(ValueError):
        solve.prepare(plan, receipt, reviewed, destination)


def test_json_content_identity_tolerates_line_endings_not_content(tmp_path):
    plan, receipt, reviewed = evidence(tmp_path)
    value = solve.read(receipt)
    receipt.write_text(json.dumps(value, indent=4), newline="\r\n")
    solve.check_inputs(plan, receipt, reviewed)
    value["allocation"]["effective_qos"] = "different"
    assert solve.identity(value) != reviewed


@pytest.mark.parametrize("change", ["tools", "order", "explicit", "allocation", "manifest"])
def test_recheck_execution_contract(tmp_path, change):
    path = execution(tmp_path)
    value = solve.read(path)
    if change == "manifest":
        campaign = path.parent / "campaign.yaml"
        raw = yaml.safe_load(campaign.read_text())
        raw["experiments"][0]["model"]["days_per_period"] = 31
        campaign.write_text(yaml.safe_dump(raw))
        value["campaign_sha256"] = file_sha256(campaign)
    elif change == "tools":
        value["tools"] = {}
    elif change == "order":
        value["arm_order"] = [1, 0]
    elif change == "explicit":
        value["production_explicit_lifecycle_allowed"] = True
    else:
        value["allocation_profile"]["solver_threads"] = 16
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        solve.check_execution(path)


@pytest.mark.parametrize("old,new", [
    ("JobId=123", "JobId=124"), ("RUNNING", "PENDING"),
    ("intel-256", "intel-512"), ("NumNodes=1", "NumNodes=2"),
    ("NodeList=r1i3n3", "NodeList=wrong"), ("BatchHost=r1i3n3", "BatchHost=wrong"),
    ("CPUs/Task=4", "CPUs/Task=2"), ("NumCPUs=4", "NumCPUs=2"),
    ("mem=192G", "mem=16G"), ("AllocTRES=", "UnknownTRES="),
    ("QOS=qos1", "QOS=preempt ArrayJobId=123 ArrayTaskId=0"),
    ("QOS=qos1", "QOS=preempt TRES=mem=128G"),
    ("QOS=qos1", "QOS=preempt JobId=999"),
])
def test_solve_allocation_rejects_wrong_or_ambiguous_records(old, new):
    with pytest.raises(ValueError):
        solve.allocation(SOLVE_JOB.replace(old, new), NODE, job_id="123", node_name="r1i3n3")


@pytest.mark.parametrize("node", ["NodeName=wrong RealMemory=256000",
                                  "NodeName=r1i3n3 RealMemory=128000",
                                  NODE + " NodeName=wrong RealMemory=512000"])
def test_solve_allocation_rejects_wrong_node(node):
    with pytest.raises(ValueError):
        solve.allocation(SOLVE_JOB, node, job_id="123", node_name="r1i3n3")


def test_scheduler_expansion_retains_four_solver_threads():
    value = solve.allocation(SOLVE_JOB.replace("NumCPUs=4", "NumCPUs=24"), NODE,
                             job_id="123", node_name="r1i3n3")
    assert value["allocated_cpus"] == 24 and value["cpus_per_task"] == 4
    assert value["allocated_memory_mib"] == 196608


@pytest.mark.parametrize("first_exit,audit_exit", [(0, 0), (1, 1), (0, 1)])
def test_two_fresh_processes_continue_after_reported_failure(tmp_path, first_exit, audit_exit):
    path = execution(tmp_path)
    calls = []

    def runner(args, **kwargs):
        calls.append((args, kwargs))
        if accept_probe(args):
            return SimpleNamespace(returncode=0)
        if "--index" in args:
            index = int(args[-1])
            return SimpleNamespace(returncode=first_exit if index == 0 else 0)
        return SimpleNamespace(returncode=audit_exit)

    resource = solve.allocation(SOLVE_JOB, NODE, job_id="123", node_name="r1i3n3")
    result = solve.execute(path, resource, solve.tool_identity(), "a" * 40, runner=runner)
    assert result == int(first_exit != 0 or audit_exit != 0)
    assert len(calls) == 4 and calls[1][0][-2:] == ["--index", "0"]
    assert calls[2][0][-2:] == ["--index", "1"]
    assert calls[3][0][-1] == "--require-accepted"
    assert all(c[0][0] == sys.executable for c in calls)
    assert all(c[1]["env"]["AGROLOGISTIC_SOURCE_COMMIT"] == "a" * 40 for c in calls)
    assert all("SCIPOPTDIR" not in c[1]["env"] for c in calls)
    assert all(c[1]["env"]["GRB_LICENSE_FILE"] == solve.LICENSE_FILE for c in calls)
    assert calls[0][1]["stdout"] == subprocess.DEVNULL
    assert calls[0][1]["stderr"] == subprocess.DEVNULL
    assert calls[0][1]["timeout"] == 60
    assert solve.read(path.parent / "pair_execution.json")["status"] == "both_processes_returned"
    assert "accepted" not in solve.read(path.parent / "pair_execution.json")
    with pytest.raises(ValueError):
        solve.execute(path, resource, solve.tool_identity(), "a" * 40, runner=runner)
    assert len(calls) == 4


def test_source_drift_between_arms_stops_before_second_solve(tmp_path):
    path = execution(tmp_path)
    calls = []

    def runner(args, **kwargs):
        calls.append(args)
        if accept_probe(args):
            return SimpleNamespace(returncode=0)
        Path(solve.read(path)["input_receipt"]).write_text("{}")
        return SimpleNamespace(returncode=0)

    resource = solve.allocation(SOLVE_JOB, NODE, job_id="123", node_name="r1i3n3")
    with pytest.raises(ValueError):
        solve.execute(path, resource, solve.tool_identity(), "a" * 40, runner=runner)
    assert len(calls) == 2
    assert (path.parent / "logs/arm-0-exit.json").exists()
    assert not (path.parent / "pair_execution.json").exists()


def test_worker_has_no_compute_git_or_memory_environment_dependency(tmp_path):
    bash = "C:/Program Files/Git/bin/bash.exe" if sys.platform == "win32" else shutil.which("bash")
    if not bash:
        pytest.skip("Bash unavailable")

    def shell_path(path):
        return (f"/{path.drive[0].lower()}{path.as_posix()[2:]}"
                if sys.platform == "win32" else str(path))

    fake = tmp_path / "bin"
    fake.mkdir()
    calls = tmp_path / "calls"
    bad = tmp_path / "git-called"
    for name, body in {
        "git": 'echo bad > "$BAD"; exit 127\n',
        "scontrol": 'if [ "$2" = job ]; then echo "$JOB"; else echo "$NODE"; fi\n',
        "python": ('test "$GRB_LICENSE_FILE" = '
                   '/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic\n'
                   'printf "%s\\n" "$@" > "$CALLS"\n'),
    }.items():
        p = fake / name
        p.write_text("#!/bin/bash\nset -eu\n" + body, newline="\n")
        p.chmod(0o755)
    destination = tmp_path / "execution"
    destination.mkdir()
    env = dict(os.environ, MVP2_SOLVE_CHECKOUT=shell_path(solve.ROOT),
               MVP2_SOLVE_PLAN=shell_path(destination / "solve_plan.json"),
               MVP2_SOLVE_SOURCE="a" * 40, MVP2_SOLVE_TOOLS="{}",
               MVP2_SOLVE_PYTHON=shell_path(fake / "python"), SLURM_JOB_ID="123",
               SLURMD_NODENAME="r1i3n3", JOB=SOLVE_JOB, NODE=NODE,
               CALLS=shell_path(calls), BAD=shell_path(bad))
    env.pop("SLURM_MEM_PER_NODE", None)
    command = [bash, "-c", 'export PATH="$1:/usr/bin:/bin:$PATH"; exec bash "$2"', "_",
               shell_path(fake), shell_path(solve.ROOT / "scripts/run_mvp2_resource_pair.slurm")]
    run = subprocess.run(command, env=env, capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stdout + run.stderr
    assert not bad.exists()
    assert (destination / "scheduler/job.txt").read_text().strip() == SOLVE_JOB
    assert "--job-id\n123" in calls.read_text()


@pytest.mark.parametrize("failure", ["none", "dirty", "git", "scheduler", "claimed"])
def test_submitter_test_only_first_and_no_duplicate(tmp_path, failure):
    bash = "C:/Program Files/Git/bin/bash.exe" if sys.platform == "win32" else shutil.which("bash")
    if not bash:
        pytest.skip("Bash unavailable")

    def shell_path(path):
        return (f"/{path.drive[0].lower()}{path.as_posix()[2:]}"
                if sys.platform == "win32" else str(path))

    fake = tmp_path / "bin"
    fake.mkdir()
    destination = tmp_path / "execution"
    destination.mkdir()
    if failure == "claimed":
        (destination / ".submission-claimed").mkdir()
    calls = tmp_path / "calls"
    bodies = {
        "git": ('if [ "$1" = status ]; then\n'
                ' if [ "$FAILURE" = git ]; then exit 77; fi\n'
                ' if [ "$FAILURE" = dirty ]; then echo " M file"; fi\n'
                'else echo pinned; fi\n'),
        "python": ('test "$GRB_LICENSE_FILE" = '
                   '/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic\n'
                   'if [ "${4:-}" = --tool-identity ]; then echo "{}"; fi\n'),
        "sbatch": ('test -z "${SBATCH_QOS:-}"\n'
                   'printf "%s\\n" "$*" >> "$CALLS"\n'
                   'if [ "$FAILURE" = scheduler ]; then exit 78; fi\n'
                   'if [ "$1" = --parsable ]; then echo 901; fi\n'),
    }
    for name, body in bodies.items():
        p = fake / name
        p.write_text("#!/bin/bash\nset -eu\n" + body, newline="\n")
        p.chmod(0o755)
    env = dict(os.environ, MVP2_SOLVE_CHECKOUT=shell_path(solve.ROOT),
               MVP2_SOLVE_PLAN=shell_path(destination / "solve_plan.json"),
               MVP2_SOLVE_PYTHON=shell_path(fake / "python"), FAILURE=failure,
               CALLS=shell_path(calls), SBATCH_QOS="invalid-inherited-value")
    command = [bash, "-c", 'export PATH="$1:/usr/bin:/bin:$PATH"; exec bash "$2"', "_",
               shell_path(fake), shell_path(solve.ROOT / "scripts/submit_mvp2_resource_pair.sh")]
    run = subprocess.run(command, env=env, capture_output=True, text=True, timeout=30)
    assert (run.returncode == 0) == (failure == "none"), run.stdout + run.stderr
    if failure in ("dirty", "git", "claimed"):
        assert "STOP:" in run.stderr and not calls.exists()
    elif failure == "scheduler":
        assert "--test-only" in calls.read_text() and "--parsable" not in calls.read_text()
    else:
        requests = calls.read_text().splitlines()
        assert len(requests) == 2
        for request in requests:
            assert "--mem=192G" in request and "--cpus-per-task=4" in request
            assert "--time=18:00:00" in request and "--partition=intel-256" in request
            assert "--qos" not in request and "--array" not in request
        assert "MVP2_PAIR_SOLVE_JOB=901" in (destination / "submission.txt").read_text()
        again = subprocess.run(command, env=env, capture_output=True, text=True, timeout=30)
        assert again.returncode != 0 and calls.read_text().splitlines() == requests


@pytest.mark.parametrize("failure", ["restricted", "missing_report", "timeout",
                                     "wrong_path", "wrong_size", "wrong_objective"])
def test_license_rejection_stops_before_large_build(tmp_path, monkeypatch, failure):
    path = execution(tmp_path)
    monkeypatch.setenv("GRB_LICENSE_FILE", "ssh://wrong/inherited/license")
    calls = []

    def runner(args, **kwargs):
        calls.append(args)
        assert kwargs["env"]["GRB_LICENSE_FILE"] == solve.LICENSE_FILE
        if failure == "timeout":
            raise subprocess.TimeoutExpired(args, 60)
        if failure != "missing_report":
            accept_probe(args)
            report = Path(args[-1])
            value = solve.read(report)
            if failure == "restricted":
                value.update(status="rejected", large_model_construction_allowed=False)
            elif failure == "wrong_path":
                value["license_file"] = "wrong"
            elif failure == "wrong_size":
                value["probe_variable_count"] = 2
            elif failure == "wrong_objective":
                value["objective_value"] = 0
            report.write_text(json.dumps(value))
        return SimpleNamespace(returncode=int(failure == "restricted"))

    resource = solve.allocation(SOLVE_JOB, NODE, job_id="123", node_name="r1i3n3")
    assert solve.execute(path, resource, solve.tool_identity(), "a" * 40, runner=runner) == 1
    assert len(calls) == 1
    assert not (path.parent / "runs").exists()
    assert not (path.parent / "comparison").exists()
    admission = solve.read(path.parent / "solve_admission.json")
    assert admission["status"] == "license_capability_rejected"
    assert solve.read(path.parent / "pair_execution.json")["optimization_attempted"] is False
