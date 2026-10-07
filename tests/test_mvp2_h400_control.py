"""Bounded h400 control admission and portable synthetic certificates; no real solve."""

import copy
import io
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from scripts import collect_mvp2_h400_control as collector
from scripts import mvp2_h400_control as control
from src.logic.experiment_runner import _spec_payload
from src.logic.run_integrity import write_completion
from tests.test_mvp2_h300_baseline import CGROUP, SOLVE_JOB
from tests.test_mvp2_h300_retry_driver import bash_path, shell_path
from tests.test_mvp2_h400_input import SOURCE, closed_run
from tests.test_mvp2_h400_input import prepared as prepared
from tests.test_mvp2_pair_preflight import NODE
from tests.test_mvp2_pair_solve import accept_probe


@pytest.mark.parametrize("state", ["COMPLETED", "FAILED", "TIMEOUT"])
def test_bash_control_repeat_start_only_collects_without_clone_or_sbatch(tmp_path, state):
    run = tmp_path / "mvp2-h400-s1b-test"
    audit = run / "execution"
    audit.mkdir(parents=True)
    scripts = run / "source/scripts"
    scripts.mkdir(parents=True)
    (audit / "source_commit.txt").write_text(SOURCE)
    (audit / "submission.txt").write_text("MVP2_H400_CONTROL_JOB=123\n")
    claim = tmp_path / ".mvp2-h400-control-s1b"
    claim.mkdir()
    (claim / "source.txt").write_text(SOURCE)
    (claim / "run.txt").write_text(shell_path(run))
    (scripts / "collect_mvp2_h400_control.py").write_text(
        "import argparse,json\nfrom pathlib import Path\n"
        "p=argparse.ArgumentParser();p.add_argument('--execution');"
        "p.add_argument('--output-dir');p.add_argument('--job-id');a=p.parse_args()\n"
        "o=Path(a.output_dir);o.mkdir();"
        "(o/'collection.json').write_text(json.dumps({'status':'evidence_rejected'}));"
        "(o/f'h400-control-evidence-{a.job_id}.tar.gz').write_bytes(b'fixture')\n"
    )
    commands = tmp_path / "bin"
    commands.mkdir()
    bodies = {
        "git": f'case "$*" in *rev-parse*) echo {SOURCE};; *status*) exit 0;; '
        "*) echo forbidden-git >&2; exit 91;; esac\n",
        "sacct": f"echo '123|{state}|0:0'\n",
        "sbatch": "echo forbidden-sbatch >&2; exit 92\n",
    }
    for name, content in bodies.items():
        target = commands / name
        target.write_text("#!/bin/sh\n" + content)
        target.chmod(0o755)
    driver = tmp_path / "driver.sh"
    body = (control.ROOT / "scripts/npad_mvp2_h400_control.sh").read_text()
    body = body.replace(
        "BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit", f'BASE="{shell_path(tmp_path)}"'
    ).replace("PY=/home/vrrcelestino/venv313/bin/python", f'PY="{shell_path(sys.executable)}"')
    driver.write_text(body, newline="\n")
    env = dict(os.environ, PATH=f"{commands}{os.pathsep}{os.environ['PATH']}")
    for _ in range(2):
        result = subprocess.run(
            [bash_path(), shell_path(driver), "start", SOURCE],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "no job will be submitted again" in result.stdout
        assert "TRANSFER_ARCHIVE=" in result.stdout and "forbidden" not in result.stderr
    assert len(list(run.glob("collection-*"))) == 2


@pytest.fixture
def contract(prepared, tmp_path, monkeypatch):
    run = closed_run(prepared)
    _, archive, checksum = control.inputs.collect(
        run, run / "collected", "123", accounting_text="123|COMPLETED|0:0\n"
    )
    p = control.policy()
    p.update(
        input_job_id="123",
        input_source_commit=SOURCE,
        input_archive_sha256=checksum,
        input_plan_sha256=control.sha(run / "prepared/input_plan.json"),
        input_receipt_sha256=control.sha(run / "audit/preflight/input_preflight.json"),
        implementation_sha256=control.read(run / "prepared/input_plan.json")["implementation"][
            "sha256"
        ],
    )
    monkeypatch.setattr(control, "policy", lambda: copy.deepcopy(p))
    path = tmp_path / "execution/control_plan.json"
    control.prepare(run, archive, path.parent, "123|COMPLETED|0:0\n", SOURCE)
    return run, archive, path


def resource():
    return control.allocation(SOLVE_JOB, NODE, job_id="123", node_name="r1i3n3", cgroup=CGROUP)


def test_production_contract_is_exact_and_no_repeat():
    p = control.policy()
    assert p["execution_limit"] == 42426624 and p["reference_limit"] == 25000000
    assert p["allocation_profile"]["optimization_seconds"] == 28800
    assert p["allocation_profile"]["walltime_seconds"] == 43200
    assert p["allocation_profile"]["cgroup_limit_bytes"] == 206158430208
    assert p["automatic_repeats_allowed"] is False and p["compaction_allowed"] is False


def test_derivation_changes_only_exact_size_and_provenance(contract):
    run, _, path = contract
    original = yaml.safe_load((run / "prepared/campaign.yaml").read_text())
    _, manifest = control.check_execution(path)
    actual = yaml.safe_load((path.parent / "campaign.yaml").read_text())
    assert len(manifest.experiments) == 1
    for name in ("model", "solver", "loader", "workbook"):
        assert actual["experiments"][0][name] == original["experiments"][0][name]
    assert actual["experiments"][0]["max_estimated_variables"] == 42426624
    assert original["experiments"][0]["max_estimated_variables"] == 25000000
    assert control.original_assets(contract[1].read_bytes())


@pytest.mark.parametrize(
    "field",
    [
        "status",
        "tools",
        "scope",
        "source_commit",
        "policy_identity",
        "allocation_profile",
        "automatic_repeats_allowed",
        "production_explicit_lifecycle_allowed",
        "input_archive_sha256",
    ],
)
def test_plan_mutation_rejected(contract, field):
    path = contract[2]
    record = control.read(path)
    record[field] = True if field.endswith("allowed") else "changed"
    path.write_text(json.dumps(record))
    with pytest.raises((ValueError, TypeError)):
        control.check_execution(path)


@pytest.mark.parametrize("change", ["compact", "threads", "guard", "direct", "budget", "extra"])
def test_rehashed_campaign_mutation_rejected(contract, change):
    path = contract[2]
    campaign = path.parent / "campaign.yaml"
    raw = yaml.safe_load(campaign.read_text())
    spec = raw["experiments"][0]
    if change == "compact":
        spec["solver"]["compact_python_indices"] = True
    elif change == "threads":
        spec["solver"]["threads"] = 8
    elif change == "guard":
        spec["max_estimated_variables"] += 1
    elif change == "direct":
        spec["model"]["use_direct_origin_customer"] = False
    elif change == "budget":
        spec["solver"]["time_limit"] *= 2
    else:
        raw["experiments"].append(copy.deepcopy(spec))
    campaign.write_text(yaml.safe_dump(raw))
    record = control.read(path)
    record["campaign_sha256"] = control.sha(campaign)
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="exact control derivation"):
        control.check_execution(path)


@pytest.mark.parametrize(
    "old,new",
    [
        ("CPUs/Task=4", "CPUs/Task=8"),
        ("NumTasks=1", "NumTasks=2"),
        ("TimeLimit=12:00:00", "TimeLimit=18:00:00"),
        ("mem=192G", "mem=128G"),
    ],
)
def test_wrong_allocation_rejected(old, new):
    with pytest.raises(ValueError):
        control.allocation(
            SOLVE_JOB.replace(old, new), NODE, job_id="123", node_name="r1i3n3", cgroup=CGROUP
        )


@pytest.mark.parametrize("cap", [None, 0, 206158430207, 206158430209, True])
def test_exact_finite_cgroup_required(cap):
    with pytest.raises(ValueError):
        control.allocation(
            SOLVE_JOB, NODE, job_id="123", node_name="r1i3n3", cgroup={**CGROUP, "limit_bytes": cap}
        )


@pytest.mark.parametrize(
    "licensed,solve,audit", [(True, 0, 0), (False, 0, 0), (True, 1, 1), (True, 0, 1)]
)
def test_one_probe_one_control_one_audit_and_no_duplicate(contract, licensed, solve, audit):
    path = contract[2]
    calls = []

    def runner(args, **kwargs):
        calls.append(args)
        assert kwargs["env"]["AGROLOGISTIC_SOURCE_COMMIT"] == SOURCE
        if "probe_npad_gurobi_license.py" in args[1]:
            if licensed:
                accept_probe(args)
            return SimpleNamespace(returncode=int(not licensed))
        if "run_batch_hpc.py" in args[1]:
            assert args[-2:] == ["--index", "0"] and kwargs["timeout"] == 32400
            return SimpleNamespace(returncode=solve)
        assert kwargs["timeout"] == 900
        return SimpleNamespace(returncode=audit)

    result = control.execute(path, resource(), control.tool_identity(), SOURCE, runner=runner)
    assert result == int(not licensed or solve != 0 or audit != 0)
    assert len(calls) == (3 if licensed else 1)
    with pytest.raises(ValueError, match="already started"):
        control.execute(path, resource(), control.tool_identity(), SOURCE, runner=runner)


def test_timeout_keeps_closure_without_second_control(contract):
    path = contract[2]

    def runner(args, **kwargs):
        if "probe_npad_gurobi_license.py" in args[1]:
            accept_probe(args)
            return SimpleNamespace(returncode=0)
        raise subprocess.TimeoutExpired(args, kwargs["timeout"])

    with pytest.raises(subprocess.TimeoutExpired):
        control.execute(path, resource(), control.tool_identity(), SOURCE, runner=runner)
    record = control.read(path.parent / "control_execution.json")
    assert record["status"] == "execution_exception" and record["optimization_attempted"] is True


def fake_closed(contract):
    run, _, path = contract

    def runner(args, **kwargs):
        if "probe_npad_gurobi_license.py" in args[1]:
            accept_probe(args)
        return SimpleNamespace(returncode=0)

    control.execute(path, resource(), control.tool_identity(), SOURCE, runner=runner)
    execution = path.parent
    (execution / "submission.txt").write_text("MVP2_H400_CONTROL_JOB=123\n")
    (execution / "source_commit.txt").write_text(SOURCE)
    (execution / "tool_hashes.json").write_text(json.dumps(control.tool_identity()))
    (execution / "worker_status.json").write_text(
        json.dumps(
            {
                "schema_version": "mvp2-h400-control-worker-v1",
                "job_id": "123",
                "source_commit": SOURCE,
                "phase": "complete",
                "exit_code": 0,
                "status": "completed",
            }
        )
    )
    (execution / "cgroup_observation.json").write_text(json.dumps(CGROUP))
    (execution / "scheduler").mkdir()
    (execution / "scheduler/job.txt").write_text(SOLVE_JOB)
    (execution / "scheduler/node.txt").write_text(NODE)
    (execution / "slurm-123.out").write_text("fixture only\n")
    _, manifest = control.check_execution(path)
    spec = manifest.experiments[0]
    folder = manifest.output_dir / spec.name
    folder.mkdir(parents=True)
    for n in collector.PRODUCTS:
        product = folder / n
        product.parent.mkdir(parents=True, exist_ok=True)
        product.write_text("fixture only\n")
    receipt = control.read(run / "audit/preflight/input_preflight.json")
    stages = [
        {
            "stage_role": n,
            "mip_gap": 0.01,
            "final_objective_value": 0,
            "within_mip_degradation_limit": True,
        }
        for n in ("unmet_demand", "emergency_capacity", "economic_cost")
    ]
    validation = {
        "status": "accepted",
        "failed_check_count": 0,
        "failure_samples": [],
        "families": {"fixture": {"failed": 0, "checked": 1, "max_residual": 0}},
        "mathematical_contract": {"fixture": True},
    }
    identity = control.shared._checkpoint_identity(spec)
    metadata = {
        "implementation_identity": receipt["implementation"],
        "run_identity": identity,
        "independent_validation_status": "accepted",
        "lexicographic_stages": stages,
        "mathematical_contract": validation["mathematical_contract"],
    }
    (folder / "result.json").write_text(
        json.dumps({"experiment": _spec_payload(spec), "result": {"metadata": metadata}})
    )
    (folder / "run_summary.json").write_text(json.dumps({"fixture": True}))
    (folder / "independent_validation.json").write_text(json.dumps(validation))
    (folder / "preflight.json").write_text(json.dumps(receipt["model_size"]))
    for n in control.inputs.gate.PRODUCTS[1:]:
        (folder / n).write_bytes((run / f"audit/preflight/{spec.name}/{n}").read_bytes())
    audit = control.read(folder / "model_audit.json")
    audit.update(solution={"fixture": True}, independent_validation_status="accepted")
    (folder / "model_audit.json").write_text(json.dumps(audit))
    telemetry = folder / "resources"
    (telemetry / "resource_timeseries.csv").write_text(
        "elapsed_seconds,phase,process_tree_rss_bytes,cgroup_current_bytes,"
        "cgroup_limit_bytes,observation_errors\n1,economic_cost,1024,1024,206158430208,\n"
    )
    (telemetry / "stage_progress.csv").write_text(
        "event,solver_memory_bytes\nphase_boundary,1024\n"
    )
    (telemetry / "matrix_statistics.json").write_text('{"fixture":true}')
    (telemetry / "termination.json").write_text(
        json.dumps(
            {
                "exception_type": None,
                "inspection_errors": [],
                "dropped_samples": {"resource": 0, "progress": 0},
                "samples": {"resource": 1, "progress": 1},
            }
        )
    )
    (telemetry / "runtime_capabilities.json").write_text('{"sampling_solver_api_calls":false}')
    resource_names = [
        Path(n).name
        for n in collector.PRODUCTS
        if n.startswith("resources/") and not n.endswith("manifest.json")
    ]
    (telemetry / "manifest.json").write_text(
        json.dumps(
            {
                "status": "closed",
                "artifacts": {n: control.sha(telemetry / n) for n in resource_names},
            }
        )
    )
    write_completion(folder, identity, [folder / n for n in collector.PRODUCTS])
    comparison = execution / "comparison"
    comparison.mkdir()
    for n in ("nine_results.json", "nine_results.csv", "nine_stage_gaps.csv"):
        (comparison / n).write_text("fixture only\n")
    (comparison / "nine_stage_gaps.json").write_text(
        json.dumps([{"name": spec.name, **s} for s in stages])
    )
    (comparison / "nine_audit_manifest.json").write_text(
        json.dumps(
            {
                "overall_status": "accepted",
                "selected_indices": [0],
                "accepted_instance_count": 1,
                "campaign_instance_count": 1,
                "manifest_sha256": control.sha(execution / "campaign.yaml"),
                "audit_script_sha256": control.sha(control.ROOT / "scripts/audit_nine_campaign.py"),
            }
        )
    )
    return execution, folder, spec


def test_portable_transfer_without_private_workbook(contract, tmp_path):
    execution, _, _ = fake_closed(contract)
    (execution / "gurobi.lic").write_text("DO NOT TRANSFER")
    summary, archive, checksum = collector.collect(
        execution, tmp_path / "transfer", "123", accounting_text="123|COMPLETED|0:0\n"
    )
    assert summary["status"] == "accepted", summary["acceptance_errors"]
    assert collector.review(archive, checksum)["status"] == "accepted"
    for p in tmp_path.rglob("*.xlsx"):
        p.rename(p.with_suffix(".preserved"))
    assert collector.review(archive, checksum)["status"] == "accepted"
    with tarfile.open(archive) as package:
        assert "gurobi.lic" not in package.getnames()


@pytest.mark.parametrize(
    "change", ["validation", "input", "hierarchy", "compaction", "cap", "worker"]
)
def test_rehashed_semantic_drift_is_rejected(contract, tmp_path, change):
    execution, folder, spec = fake_closed(contract)
    if change == "validation":
        p = folder / "independent_validation.json"
        r = control.read(p)
        r["failed_check_count"] = 1
    elif change == "input":
        p = folder / "model_audit.json"
        r = control.read(p)
        r["input"]["changed"] = True
    elif change == "hierarchy":
        p = folder / "result.json"
        r = control.read(p)
        r["result"]["metadata"]["lexicographic_stages"][2]["mip_gap"] = 0.999
    elif change == "compaction":
        p = folder / "resources/stage_progress.csv"
        p.write_text("event,solver_memory_bytes\npython_index_compaction,1024\n")
        r = None
        m = control.read(folder / "resources/manifest.json")
        m["artifacts"]["stage_progress.csv"] = control.sha(p)
        (folder / "resources/manifest.json").write_text(json.dumps(m))
    elif change == "cap":
        p = execution / "cgroup_observation.json"
        r = {**CGROUP, "limit_bytes": 206158430209}
    else:
        p = execution / "worker_status.json"
        r = control.read(p)
        r["phase"] = "incomplete"
    if r is not None:
        p.write_text(json.dumps(r))
    write_completion(
        folder, control.shared._checkpoint_identity(spec), [folder / n for n in collector.PRODUCTS]
    )
    summary, _, _ = collector.collect(
        execution, tmp_path / "transfer", "123", accounting_text="123|COMPLETED|0:0\n"
    )
    assert summary["status"] == "evidence_rejected"


@pytest.mark.parametrize("state", ["FAILED", "TIMEOUT", "PREEMPTED", "OUT_OF_MEMORY"])
def test_partial_failure_transferred_without_acceptance(contract, tmp_path, state):
    path = contract[2]
    (path.parent / "submission.txt").write_text("MVP2_H400_CONTROL_JOB=123\n")
    summary, archive, checksum = collector.collect(
        path.parent, tmp_path / "transfer", "123", accounting_text=f"123|{state}|1:0\n"
    )
    assert summary["status"] == "terminal_failure"
    assert collector.review(archive, checksum)["status"] == "terminal_failure_preserved"


@pytest.mark.parametrize("name", ["../escape", "/absolute", "a/../b", "a\\b", "C:escape"])
def test_archive_unsafe_names_rejected(tmp_path, name):
    archive = tmp_path / "bad.tar.gz"
    with tarfile.open(archive, "x:gz") as package:
        member = tarfile.TarInfo(name)
        member.size = 1
        package.addfile(member, io.BytesIO(b"x"))
    with pytest.raises(ValueError, match="Unsafe"):
        control.safe_payload(archive.read_bytes(), control.sha(archive))


@pytest.mark.parametrize(
    "script",
    ["submit_mvp2_h400_control.sh", "run_mvp2_h400_control.slurm", "npad_mvp2_h400_control.sh"],
)
def test_bash_control_syntax(script):
    subprocess.run([bash_path(), "-n", shell_path(control.ROOT / "scripts" / script)], check=True)


def test_driver_reference_and_all_test_paths_exist():
    body = (control.ROOT / "scripts/npad_mvp2_h400_control.sh").read_text()
    assert "CLAIM=$BASE/.mvp2-h400-control-s1b" in body
    assert 'H400_CHECKOUT="$SRC" H400_PLAN=' in body
    import re

    for path in re.findall(r"tests/[A-Za-z0-9_]+\.py", body):
        assert (control.ROOT / path).is_file()


def test_bash_worker_scheduler_failure_preserves_exit(tmp_path):
    execution, commands = tmp_path / "execution", tmp_path / "bin"
    execution.mkdir()
    commands.mkdir()
    target = commands / "scontrol"
    target.write_text("#!/bin/sh\nexit 5\n")
    target.chmod(0o755)
    env = dict(
        os.environ,
        PATH=f"{commands}{os.pathsep}{os.environ['PATH']}",
        H400_CHECKOUT=shell_path(control.ROOT),
        H400_PLAN=shell_path(execution / "control_plan.json"),
        H400_SOURCE=SOURCE,
        H400_TOOLS="{}",
        H400_PYTHON=shell_path(sys.executable),
        SLURM_JOB_ID="123",
    )
    result = subprocess.run(
        [bash_path(), shell_path(control.ROOT / "scripts/run_mvp2_h400_control.slurm")],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 5
    worker = control.read(execution / "worker_status.json")
    assert worker["exit_code"] == 5 and worker["phase"] == "scheduler_capture"
