"""Closed input admission and exact NPAD scheduler records for a resource pair."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts import preflight_mvp2_resource_pair as gate
from scripts import prepare_mvp2_resource_contrasts as contrasts
from src.logic.run_integrity import file_sha256
from tests.test_mvp2_resource_contrasts import fixture

JOB = ("JobId=123 JobState=RUNNING Partition=intel-256 NumNodes=1 "
       "NumCPUs=4 CPUs/Task=4 NodeList=r1i3n3 BatchHost=r1i3n3 "
       "AllocTRES=cpu=4,mem=16G,node=1 QOS=qos1")
NODE = "NodeName=r1i3n3 RealMemory=256000"


def prepared(tmp_path):
    reference, qualification = fixture(tmp_path, "h215-warehouse")
    contrasts.prepare(reference, file_sha256(reference), 0, qualification,
                      tmp_path / "pair", "h215-warehouse")
    return tmp_path / "pair/resource_contrast_plan.json"


def inspector(spec, output):
    """Simulate exported input products, not a solution or licensed execution."""
    folder = output / spec.name
    folder.mkdir()
    for name in gate.PRODUCTS:
        (folder / name).write_text("identical-input\n")
    (folder / "preflight.json").write_text(json.dumps({
        "scenario_count": 9, "period_count": 60, "total_variables": 14054654,
        "workbook_sha256": file_sha256(spec.workbook),
        "data_signature": {"counts": {"warehouses": 215, "scenarios": 9, "periods": 60}},
        "execution": {"run": spec.name},
    }))
    (folder / "interhub_connectivity_audit.json").write_text('{"status":"accepted"}')


def test_closed_pair_exports_inputs_and_preserves_evidence(tmp_path):
    plan = prepared(tmp_path)
    before = {p: file_sha256(p) for p in tmp_path.rglob("*") if p.is_file()}
    destination = tmp_path / "audit"
    result = gate.preflight(plan, destination, {"fixture": True}, inspector=inspector)
    assert result["status"] == "accepted"
    assert result["optimization_executed"] is False
    assert result["large_instance_submission_allowed"] is False
    assert result["model_size"]["total_variables"] == 14054654
    assert len(result["artifacts"]) == 12
    for name, digest in result["artifacts"].items():
        assert file_sha256(destination / name) == digest
    assert json.loads((destination / "pair_preflight.json").read_text()) == result
    assert all(file_sha256(p) == digest for p, digest in before.items())


@pytest.mark.parametrize("field,value", [
    ("warehouses", 300), ("scenarios", 3), ("periods", 59),
    ("total_variables", 0), ("total_variables", 43000001),
    ("workbook_sha256", "changed"), ("connectivity", "rejected"),
    ("model_audit", "different"), ("missing", "interhub_repair_edges.csv"),
    ("arm_dimensions", 14054655),
])
def test_input_failures_preserve_partial_products_without_acceptance(tmp_path, field, value):
    plan = prepared(tmp_path)

    def changed(spec, output):
        inspector(spec, output)
        folder = output / spec.name
        if field == "connectivity":
            (folder / "interhub_connectivity_audit.json").write_text(
                json.dumps({"status": value}))
        elif field == "missing":
            (folder / value).unlink()
        elif field == "model_audit":
            (folder / "model_audit.json").write_text(spec.name)
        else:
            path = folder / "preflight.json"
            record = json.loads(path.read_text())
            if field in ("warehouses", "scenarios", "periods"):
                record["data_signature"]["counts"][field] = value
            elif field == "arm_dimensions":
                if spec.name.endswith("compact"):
                    record["total_variables"] = value
            else:
                record[field] = value
            path.write_text(json.dumps(record))

    destination = tmp_path / "audit"
    with pytest.raises((ValueError, FileNotFoundError)):
        gate.preflight(plan, destination, {}, inspector=changed)
    assert destination.exists()
    assert not (destination / "pair_preflight.json").exists()


@pytest.mark.parametrize("change", [
    "campaign_hash", "reference", "workbook", "qualification", "preparer",
    "implementation", "admission", "source", "model", "solver", "destination",
])
def test_preflight_rejects_drift_and_reconstructs_both_arms(tmp_path, change):
    path = prepared(tmp_path)
    plan = json.loads(path.read_text())
    if change in ("reference", "qualification"):
        key = "reference_manifest" if change == "reference" else "qualification_report"
        Path(plan[key]).write_text("changed")
    elif change == "workbook":
        (tmp_path / "input.xlsx").write_bytes(b"changed")
    elif change == "preparer":
        plan["preparer_sha256"] = "changed"
    elif change == "implementation":
        plan["implementation"] = {}
    elif change == "admission":
        plan["large_instance_submission_allowed"] = True
    elif change == "source":
        plan["qualified_source_commit"] = "changed"
    else:
        campaign = path.parent / "campaign.yaml"
        raw = yaml.safe_load(campaign.read_text())
        if change == "model":
            raw["experiments"][0]["model"]["days_per_period"] = 31
        elif change == "solver":
            raw["experiments"][1]["solver"]["threads"] = 8
        elif change == "destination":
            raw["output_dir"] = str(tmp_path / "historical/runs")
        else:
            raw["experiments"][0]["name"] = "changed"
        campaign.write_text(yaml.safe_dump(raw))
        if change != "campaign_hash":
            plan["campaign_sha256"] = file_sha256(campaign)
    path.write_text(json.dumps(plan))
    with pytest.raises(ValueError):
        gate.check_plan(path)


@pytest.mark.parametrize("target", ["pair/new", "historical/new", "qualification/new", "exists"])
def test_preflight_rejects_protected_or_existing_destinations(tmp_path, target):
    path = prepared(tmp_path)
    destination = tmp_path / target
    if target == "exists":
        destination.mkdir()
    with pytest.raises(ValueError, match="new preflight directory"):
        gate.preflight(path, destination, {}, inspector=inspector)


def test_preflight_detects_tool_changes_before_closure(tmp_path, monkeypatch):
    plan = prepared(tmp_path)
    original = gate.tool_identity()
    calls = iter([original, {**original, "changed": "during-load"}])
    monkeypatch.setattr(gate, "tool_identity", lambda: next(calls))
    with pytest.raises(ValueError, match="tools changed"):
        gate.preflight(plan, tmp_path / "audit", {}, inspector=inspector)
    assert not (tmp_path / "audit/pair_preflight.json").exists()


@pytest.mark.parametrize("memory", ["AllocTRES=cpu=4,mem=16G,node=1",
                                    "TRES=cpu=24,mem=16384M,node=1",
                                    "TRES=mem=16G AllocTRES=mem=16384M"])
def test_exact_allocation_accepts_observed_tres_and_expanded_cpus(memory):
    text = JOB.replace("AllocTRES=cpu=4,mem=16G,node=1", memory).replace(
        "NumCPUs=4", "NumCPUs=24")
    record = gate.allocation(text, NODE, job_id="123", node_name="r1i3n3")
    assert record["allocated_memory_mib"] == 16384
    assert record["allocated_cpus"] == 24
    assert record["cpus_per_task"] == 4


@pytest.mark.parametrize("old,new", [
    ("JobId=123", "JobId=124"), ("RUNNING", "PENDING"),
    ("intel-256", "intel-512"), ("NumNodes=1", "NumNodes=2"),
    ("NodeList=r1i3n3", "NodeList=r1i3n4"),
    ("BatchHost=r1i3n3", "BatchHost=r1i3n4"),
    ("CPUs/Task=4", "CPUs/Task=2"), ("NumCPUs=4", "NumCPUs=2"),
    ("mem=16G", "mem=192G"), ("AllocTRES=", "UnknownTRES="),
    ("QOS=qos1", "QOS=qos1 ArrayJobId=123 ArrayTaskId=0"),
    ("QOS=qos1", "QOS=qos1 TRES=mem=8G"),
    ("QOS=qos1", "QOS=qos1 JobId=999"),
])
def test_allocation_rejects_incorrect_or_ambiguous_records(old, new):
    with pytest.raises(ValueError):
        gate.allocation(JOB.replace(old, new), NODE, job_id="123", node_name="r1i3n3")


@pytest.mark.parametrize("node", ["NodeName=other RealMemory=256000",
                                  "NodeName=r1i3n3 RealMemory=8000",
                                  NODE + " NodeName=other RealMemory=512000"])
def test_allocation_rejects_wrong_node(node):
    with pytest.raises(ValueError):
        gate.allocation(JOB, node, job_id="123", node_name="r1i3n3")


def test_compute_worker_needs_neither_git_nor_memory_environment(tmp_path):
    bash = "C:/Program Files/Git/bin/bash.exe" if sys.platform == "win32" else shutil.which("bash")
    if not bash:
        pytest.skip("Bash unavailable")

    def shell_path(path):
        if sys.platform == "win32":
            return f"/{path.drive[0].lower()}{path.as_posix()[2:]}"
        return str(path)

    fake = tmp_path / "bin"
    fake.mkdir()
    calls = tmp_path / "calls.txt"
    git_called = tmp_path / "git-called.txt"
    bodies = {
        "git": 'echo called > "$GIT_CALLED"; exit 127\n',
        "scontrol": 'if [ "$2" = job ]; then echo "$JOB_RECORD"; else echo "$NODE_RECORD"; fi\n',
        "python": 'printf "%s\\n" "$@" > "$CALLS"\n',
    }
    for name, body in bodies.items():
        p = fake / name
        p.write_text("#!/bin/bash\nset -eu\n" + body, newline="\n")
        p.chmod(0o755)
    audit = tmp_path / "audit"
    audit.mkdir()
    env = dict(os.environ)
    env.pop("SLURM_MEM_PER_NODE", None)
    env.update(
        MVP2_PAIR_CHECKOUT=shell_path(gate.ROOT), MVP2_PAIR_PLAN="preserved.json",
        MVP2_PAIR_AUDIT=shell_path(audit), MVP2_PAIR_SOURCE="pinned",
        MVP2_PAIR_TOOLS="{}", MVP2_PAIR_PYTHON=shell_path(fake / "python"),
        SLURM_JOB_ID="123", SLURMD_NODENAME="r1i3n3", JOB_RECORD=JOB,
        NODE_RECORD=NODE, CALLS=shell_path(calls), GIT_CALLED=shell_path(git_called),
    )
    command = [bash, "-c", 'export PATH="$1:/usr/bin:/bin:$PATH"; exec bash "$2"', "_",
               shell_path(fake), shell_path(gate.ROOT / "scripts/run_mvp2_pair_preflight.slurm")]
    run = subprocess.run(command, env=env, capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stdout + run.stderr
    assert not git_called.exists()
    assert (audit / "scheduler/job.txt").read_text().strip() == JOB
    args = calls.read_text()
    assert "--tools\n{}" in args
    assert "--job-id\n123" in args
    assert "run_batch_hpc" not in args
    assert not (audit / "preflight/pair_preflight.json").exists()
