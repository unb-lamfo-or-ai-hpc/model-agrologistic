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


def test_four_resource_only_cases(prepared):
    assert memory.CASES == ((215, False), (215, True), (300, False), (300, True))
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


@pytest.mark.parametrize("index", [-1, 4])
def test_unreviewed_case_rejected(prepared, index):
    with pytest.raises(ValueError, match="four"):
        memory.check(prepared, index)


@pytest.mark.parametrize("field,value", [
    ("scip_memory_limit_mb", 512000), ("max_concurrent_repeats", 4),
    ("baseline_jobs", []), ("partition", "intel-256"),
    ("implementation_identity", {}), ("tools", {}),
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
        memory.check(prepared, 2)


@pytest.mark.parametrize("node,partition,allocation,valid", [
    ("RealMemory=512000", "intel-512", 0, True),
    ("RealMemory=512000", "intel-512", 512000, True),
    ("RealMemory=512000", "intel-512", 196608, False),
    ("RealMemory=256000", "intel-256", 0, False),
    ("RealMemory=256000", "intel-512", 0, False),
    ("RealMemory=unknown", "intel-512", 0, False),
])
def test_scheduler_resources(node, partition, allocation, valid):
    if valid:
        memory.validate_resources(node, partition, allocation)
    else:
        with pytest.raises(ValueError, match="Require"):
            memory.validate_resources(node, partition, allocation)


@pytest.mark.parametrize("index", range(4))
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


@pytest.mark.parametrize("state", ["RUNNING", "COMPLETED", "UNKNOWN"])
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
        "sacct": 'printf "%s|\\n" "$FAKE_STATE"\n',
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
               FAKE_STATE=state, FAKE_CALLS=shell_path(calls), SBATCH_QOS="invalid-qos")
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
    assert "--partition=intel-512" in text and "--array=0-3%2" in text
    assert ("--dependency=afterany:2107034:2107114" in text) == (state == "RUNNING")
    assert "MEMORY_JOB=901" in (root / "submission.txt").read_text()
    again = subprocess.run(command, env=env, text=True, capture_output=True, timeout=60)
    assert again.returncode != 0
    assert calls.read_text() == text
