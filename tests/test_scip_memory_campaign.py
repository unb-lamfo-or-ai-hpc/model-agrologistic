"""A resource-only repeat must preserve the qualified mathematical contract."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts import prepare_scip_memory_campaign as memory
from scripts import prepare_scip_pilot as pilot
from scripts import validate_scip_memory_resources as resources
from src.logic.experiment_runner import load_experiment_manifest
from src.logic.run_integrity import file_sha256
from tests.test_scip_pilot import inputs as inputs


@pytest.fixture
def prepared(inputs, monkeypatch):
    reference = pilot.prepare(*inputs)
    monkeypatch.setattr(memory, "implementation_identity", pilot.implementation_identity)
    data_root = inputs[0].parent / "data"
    for population in (215, 300):
        workbook = data_root / memory.baseline.INPUT_PATHS[population]
        workbook.parent.mkdir(parents=True)
        workbook.write_bytes(inputs[1].read_bytes() if population == 215 else b"300")
    monkeypatch.setitem(memory.baseline.FROZEN_HASHES, 300, file_sha256(workbook))
    before = {p: p.read_bytes() for p in inputs[0].rglob("*") if p.is_file()}
    plan = memory.prepare(inputs[0].parent / "repeat", data_root, reference)
    assert all(p.read_bytes() == content for p, content in before.items())
    return plan


def test_two_300_hub_resource_only_cases(prepared):
    assert memory.CASES == ((300, False), (300, True))
    plan = json.loads(prepared.read_text())
    assert set(plan["inputs"]) == {"300"}
    assert plan["baseline_jobs"] == ["2107114_1", "2107114_2"]
    assert len(plan["cases"]) == 2
    assert {"scripts/run_batch_hpc.py", "scripts/audit_nine_campaign.py"} <= set(plan["tools"])
    for index, (population, direct) in enumerate(memory.CASES):
        folder, _, _ = memory.check(prepared, index)
        spec = load_experiment_manifest(folder / "campaign.yaml").experiments[0]
        assert spec.solver.backend == "pyscipopt"
        assert spec.solver.solver_options == {"limits/memory": 393216}
        assert spec.solver.time_limit == 28800
        assert spec.solver.mip_gap == 0.1
        assert spec.solver.threads == 4
        assert not spec.calculate_evpi_vss
        assert spec.model.use_direct_origin_customer == direct
        assert spec.model.interhub_strong_connectivity
        assert spec.metadata["warehouse_population"] == population
        assert not (folder / "runs").exists()


@pytest.mark.parametrize("index", [-1, 2, 3, 4])
def test_unreviewed_case_rejected(prepared, index):
    with pytest.raises(ValueError, match="two"):
        memory.check(prepared, index)


@pytest.mark.parametrize("field,value", [
    ("scip_memory_limit_mb", 512000), ("max_concurrent_repeats", 4),
    ("baseline_jobs", []), ("partition", "intel-256"),
    ("implementation_identity", {}), ("tools", {}),
    ("schema_version", "scip-memory-repeat-v1"),
    ("baseline_jobs", ["2107034", "2107114"]),
])
def test_changed_contract_rejected(prepared, field, value):
    data = json.loads(prepared.read_text())
    data[field] = value
    prepared.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="changed"):
        memory.check(prepared, 0)


def test_forged_manifest_hash_cannot_raise_memory(prepared):
    folder, doc, _ = memory.check(prepared, 0)
    manifest = folder / "campaign.yaml"
    doc["defaults"]["solver"]["solver_options"]["limits/memory"] = 512000
    manifest.write_text(yaml.safe_dump(doc))
    data = json.loads(prepared.read_text())
    data["cases"][0]["manifest_sha256"] = file_sha256(manifest)
    prepared.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="exceeds"):
        memory.check(prepared, 0)


def test_changed_workbook_rejected(prepared):
    item = json.loads(prepared.read_text())["inputs"]["300"]
    Path(item["path"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="workbook changed"):
        memory.check(prepared, 0)


JOB_RECORD = """JobId=2107702 ArrayJobId=2107702 ArrayTaskId=1
   JobState=RUNNING Partition=intel-512 QOS=preempt
   NodeList=r1i3n16 BatchHost=r1i3n16 NumNodes=1 NumCPUs=64 CPUs/Task=4
   TRES=cpu=64,mem=500G,node=1,billing=64
   MinMemoryNode=0 OverSubscribe=NO
"""
OTHER_JOB = JOB_RECORD.replace("JobId=2107702 ArrayJobId", "JobId=2107703 ArrayJobId").replace(
    "ArrayTaskId=1", "ArrayTaskId=0").replace("r1i3n16", "r1i3n14")
NODE_RECORD = "NodeName=r1i3n16 RealMemory=512000 AllocMem=512000 FreeMem=254360"


def validate_allocation(job=JOB_RECORD, node=NODE_RECORD):
    return resources.validate_resources(job, node, job_id="2107702", array_id="2107702",
                                        task_id="1", node_name="r1i3n16")


def test_actual_npad_array_record_selection():
    for text in (JOB_RECORD, OTHER_JOB + JOB_RECORD, JOB_RECORD + OTHER_JOB):
        result = validate_allocation(text)
        assert result["allocated_memory_mib"] == 512000
        assert result["nominal_headroom_mib"] == 118784
        assert result["node"] == "r1i3n16"
    assert validate_allocation(JOB_RECORD.replace("TRES=", "AllocTRES="))["status"] == "accepted"


@pytest.mark.parametrize("old,new", [
    ("mem=500G", "mem=192G"), ("mem=500G", "mem=unknown"),
    ("mem=500G", "mem=500G,mem=500G"), ("TRES=", "ReqTRES="),
    ("Partition=intel-512", "Partition=intel-256"), ("NumNodes=1", "NumNodes=2"),
    ("CPUs/Task=4", "CPUs/Task=1"), ("OverSubscribe=NO", "OverSubscribe=YES"),
    ("MinMemoryNode=0", "MinMemoryNode=196608"), ("JobState=RUNNING", "JobState=PENDING"),
    ("NodeList=r1i3n16", "NodeList=r1i3n14"), ("ArrayTaskId=1", "ArrayTaskId=0"),
])
def test_bad_allocation_rejected(old, new):
    with pytest.raises(ValueError):
        validate_allocation(JOB_RECORD.replace(old, new))


def test_ambiguous_or_missing_records_rejected():
    for text in ("", OTHER_JOB, JOB_RECORD + JOB_RECORD,
                 JOB_RECORD + " AllocTRES=cpu=64,mem=192G,node=1"):
        with pytest.raises(ValueError):
            validate_allocation(text)
    for text in ("", NODE_RECORD + "\n" + NODE_RECORD,
                 NODE_RECORD.replace("512000", "256000")):
        with pytest.raises(ValueError):
            validate_allocation(node=text)


@pytest.mark.parametrize("index", range(2))
def test_preflight(prepared, index):
    _, _, digest = memory.check(prepared, index)
    population, direct = memory.CASES[index]
    payload = {"workbook_sha256": digest, "data_signature": {"counts": {"warehouses": population}},
               "scenario_count": 9, "period_count": 60, "routes_oc": 592 if direct else 0,
               "total_variables": memory.baseline.SIZE_LIMITS[population]}
    memory.validate_preflight(payload, index, digest)
    payload["total_variables"] += 1
    with pytest.raises(ValueError, match="Preflight"):
        memory.validate_preflight(payload, index, digest)


def test_native_scip_accepts_extended_parameter():
    scip = pytest.importorskip("pyscipopt")
    model = scip.Model()
    model.setParam("limits/memory", memory.MEMORY_MB)
    assert model.getParam("limits/memory") == memory.MEMORY_MB
    model.freeProb()


@pytest.mark.parametrize("state", ["RUNNING", "COMPLETED", "FAILED", "UNKNOWN"])
def test_bash_dependencies_all_memory_and_duplicate_guard(tmp_path, state):
    """Use fake Slurm commands; never submit to a real scheduler."""
    bash = "C:/Program Files/Git/bin/bash.exe" if sys.platform == "win32" else shutil.which("bash")
    if not bash or not Path(bash).is_file():
        pytest.skip("Bash unavailable")

    def shell_path(path):
        if sys.platform == "win32":
            return f"/{path.drive[0].lower()}{path.as_posix()[2:]}"
        return str(path)

    fake = tmp_path / "bin"
    fake.mkdir()
    root = tmp_path / "campaign"
    root.mkdir()
    scripts = {
        "git": 'if [ "$1" = rev-parse ]; then echo frozen; fi\n',
        "python": 'exit 0\n',
        "sacct": 'printf "%s " "$@" >> "$FAKE_QUERIES"\nprintf "\\n" >> "$FAKE_QUERIES"\n'
                 'printf "%s|\\n" "$FAKE_STATE"\n',
        "sbatch": 'test -z "${SBATCH_QOS:-}"\n'
                  'printf "%s " "$@" >> "$FAKE_CALLS"\nprintf "\\n" >> "$FAKE_CALLS"\n'
                  'if [ "$1" = --parsable ]; then echo 901; fi\n',
    }
    for name, body in scripts.items():
        path = fake / name
        path.write_text("#!/bin/bash\nset -eu\n" + body, newline="\n")
        path.chmod(0o755)
    env = dict(os.environ)
    calls = tmp_path / "calls.txt"
    env.update(SCIP_MEMORY_CHECKOUT=shell_path(tmp_path), SCIP_MEMORY_ROOT=shell_path(root),
               SCIP_MEMORY_SOURCE="frozen", SCIP_PYTHON=shell_path(fake / "python"),
               FAKE_STATE=state, FAKE_CALLS=shell_path(calls), SBATCH_QOS="invalid-qos",
               FAKE_QUERIES=shell_path(tmp_path / "queries.txt"))
    source = Path(memory.__file__).parent / "submit_scip_memory_campaign.sh"
    command = [bash, "-c", 'export PATH="$1:/usr/bin:/bin:$PATH"; exec bash "$2"', "_",
               shell_path(fake), shell_path(source)]
    run = subprocess.run(command, env=env, text=True, capture_output=True, timeout=60)
    assert (run.returncode == 0) == (state != "UNKNOWN"), run.stdout + run.stderr
    if state == "UNKNOWN":
        assert not calls.exists()
        return
    text = calls.read_text()
    assert text.count("--parsable") == 1
    assert "--mem=0" in text and "--exclusive" in text
    assert "--partition=intel-512" in text and "--array=0-1%2" in text
    assert ("--dependency=afterany:2107114_1:2107114_2" in text) == (state == "RUNNING")
    queries = (tmp_path / "queries.txt").read_text()
    assert "2107034" not in queries and "2107114_0" not in queries
    assert "-j 2107114_1 " in queries and "-j 2107114_2 " in queries
    assert "MEMORY_JOB=901" in (root / "submission.txt").read_text()
    again = subprocess.run(command, env=env, text=True, capture_output=True, timeout=60)
    assert again.returncode != 0
    assert calls.read_text() == text


@pytest.mark.parametrize("reject_contract,bad_allocation", [(False, False), (True, False),
                                                          (False, True)])
def test_compute_worker_without_git(tmp_path, reject_contract, bad_allocation):
    """Run real Bash AND resource-check Python; mock only scheduler and solver calls."""
    bash = "C:/Program Files/Git/bin/bash.exe" if sys.platform == "win32" else shutil.which("bash")
    if not bash or not Path(bash).is_file():
        pytest.skip("Bash unavailable")

    def shell_path(path):
        if sys.platform == "win32":
            return f"/{path.drive[0].lower()}{path.as_posix()[2:]}"
        return str(path)

    fake = tmp_path / "bin"
    fake.mkdir()
    root = tmp_path / "campaign"
    folder = root / "case-1"
    folder.mkdir(parents=True)
    scripts = {
        "git": 'echo called > "$FAKE_GIT_CALLED"\nexit 127\n',
        "python": 'printf "%s " "$@" >> "$FAKE_CALLS"\nprintf "\\n" >> "$FAKE_CALLS"\n'
                  'if [ "$1" = scripts/validate_scip_memory_resources.py ]; then '
                  'exec "$REAL_PYTHON" "$@"; fi\n'
                  'if [ "$REJECT_CONTRACT" = 1 ] && '
                  '[ "$1" = scripts/prepare_scip_memory_campaign.py ]; then exit 72; fi\n',
        "scontrol": 'if [ "$2" = job ]; then cat "$JOB_FIXTURE"; '
                    'else cat "$NODE_FIXTURE"; fi\n',
        "hostname": 'echo fake-compute-node\n',
    }
    for name, body in scripts.items():
        path = fake / name
        path.write_text("#!/bin/bash\nset -eu\n" + body, newline="\n")
        path.chmod(0o755)
    calls = tmp_path / "calls.txt"
    git_marker = tmp_path / "git-called.txt"
    job_fixture = tmp_path / "job.txt"
    job_fixture.write_text(OTHER_JOB + JOB_RECORD.replace("mem=500G", "mem=192G")
                           if bad_allocation else OTHER_JOB + JOB_RECORD)
    node_fixture = tmp_path / "node.txt"
    node_fixture.write_text(NODE_RECORD)
    env = dict(os.environ)
    env.pop("SLURM_MEM_PER_NODE", None)
    env.update(SCIP_MEMORY_CHECKOUT=shell_path(memory.ROOT), SCIP_MEMORY_ROOT=shell_path(root),
               SCIP_MEMORY_SOURCE="frozen", SCIP_PYTHON=shell_path(fake / "python"),
               SLURM_ARRAY_TASK_ID="1", SLURM_ARRAY_JOB_ID="2107702",
               SLURM_JOB_NUM_NODES="1", SLURM_CPUS_PER_TASK="4",
               SLURM_JOB_ID="2107702", SLURMD_NODENAME="r1i3n16",
               SLURM_JOB_PARTITION="intel-512", FAKE_CALLS=shell_path(calls),
               REAL_PYTHON=shell_path(Path(sys.executable)),
               JOB_FIXTURE=shell_path(job_fixture), NODE_FIXTURE=shell_path(node_fixture),
               FAKE_GIT_CALLED=shell_path(git_marker), REJECT_CONTRACT=str(int(reject_contract)))
    source = Path(memory.__file__).parent / "run_scip_memory_campaign.slurm"
    command = [bash, "-c", 'export PATH="$1:/usr/bin:/bin:$PATH"; exec bash "$2"', "_",
               shell_path(fake), shell_path(source)]
    run = subprocess.run(command, env=env, text=True, capture_output=True, timeout=60)
    assert not git_marker.exists(), run.stdout + run.stderr
    expected_success = not reject_contract and not bad_allocation
    assert (run.returncode == 0) == expected_success, run.stdout + run.stderr
    text = calls.read_text()
    if reject_contract or bad_allocation:
        assert "scripts/run_batch_hpc.py" not in text
        assert (folder / ".execution-claimed").exists() == (not reject_contract)
        assert not (folder / "scheduler_resource_audit.json").exists()
    else:
        assert "--dry-run" in text and "--preflight" in text
        assert text.count("scripts/run_batch_hpc.py") == 2
        assert "scripts/audit_nine_campaign.py" in text
        assert "solve_exit_code=0 audit_exit_code=0" in run.stdout
        assert (folder / "scheduler_node.txt").exists()
        assert "memory_env=unset" in run.stdout
        assert "SCIP FULL-NODE RESOURCE CONTRACT: ACCEPTED" in run.stdout
        assert json.loads((folder / "scheduler_resource_audit.json").read_text())[
            "allocated_memory_mib"] == 512000
