"""Isolated, bounded SCIP expansion without altering the running reference pilot."""

import json
import os
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from scripts import prepare_scip_expansion as expansion
from scripts import prepare_scip_pilot as pilot
from src.logic.experiment_runner import load_experiment_manifest
from src.logic.run_integrity import file_sha256
from tests.test_scip_pilot import inputs as inputs  # Reuse the full qualification fixture.


@pytest.fixture
def prepared(inputs, monkeypatch):
    reference = pilot.prepare(*inputs)
    monkeypatch.setattr(expansion, "implementation_identity", pilot.implementation_identity)
    data_root = inputs[0].parent / "data"
    digests = {}
    for population, relative in expansion.INPUT_PATHS.items():
        workbook = data_root / relative
        workbook.parent.mkdir(parents=True)
        workbook.write_bytes(
            inputs[1].read_bytes() if population == 215 else str(population).encode())
        digests[population] = file_sha256(workbook)
    monkeypatch.setattr(expansion, "FROZEN_HASHES", {p: digests[p] for p in (300, 400)})
    root = inputs[0].parent / "expansion"
    before = {p: p.read_bytes() for p in inputs[0].rglob("*") if p.is_file()}
    plan = expansion.prepare(root, data_root, reference)
    assert all(p.read_bytes() == content for p, content in before.items())
    return plan, data_root, reference


def test_prepares_five_cases_excluding_active_reference(prepared):
    plan, data_root, reference = prepared
    doc = json.loads(plan.read_text())
    assert doc["solve_indices"] == [0, 1, 2]
    assert doc["preflight_indices"] == [0, 1, 2, 3, 4]
    assert doc["max_new_concurrent_solves"] == 2
    assert [(c["population"], c["direct"]) for c in doc["cases"]] == list(expansion.CASES)
    assert (215, False) not in expansion.CASES
    for index, (population, direct) in enumerate(expansion.CASES):
        folder, manifest, _, _ = expansion.check(plan, index, "preflight")
        spec = load_experiment_manifest(manifest).experiments[0]
        assert spec.solver.backend == "pyscipopt"
        assert spec.solver.solver_options == {"limits/memory": 131072}
        assert spec.solver.time_limit == 28800
        assert spec.solver.mip_gap == 0.1
        assert not spec.solver.compute_iis
        assert not spec.calculate_evpi_vss
        assert spec.model.use_direct_origin_customer == direct
        assert spec.metadata["warehouse_population"] == population
        assert spec.model.interhub_strong_connectivity
        assert spec.max_estimated_variables == expansion.SIZE_LIMITS[population]
        assert not (folder / "runs").exists()
    with pytest.raises(FileExistsError):
        expansion.prepare(plan.parent, data_root, reference)


@pytest.mark.parametrize("index", [3, 4])
def test_400_solves_are_not_admitted(prepared, index):
    with pytest.raises(ValueError, match="subsequent resource review"):
        expansion.check(prepared[0], index, "solve")


@pytest.mark.parametrize("index", [-1, 5])
def test_invalid_index_is_rejected(prepared, index):
    with pytest.raises(ValueError, match="Unknown"):
        expansion.check(prepared[0], index, "preflight")


@pytest.mark.parametrize("field,value", [
    ("solve_indices", [0, 1, 2, 3, 4]), ("max_new_concurrent_solves", 5),
    ("active_pilot_resubmitted", True), ("implementation_identity", {"sha256": "stale"}),
    ("preflight_indices", [0]), ("tools", {}),
])
def test_mutated_plan_rejected(prepared, field, value):
    plan = prepared[0]
    doc = json.loads(plan.read_text())
    doc[field] = value
    plan.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="changed"):
        expansion.check(plan, 0, "preflight")


def test_forged_configuration_hash_does_not_change_solver_contract(prepared):
    plan = prepared[0]
    folder, manifest, _, _ = expansion.check(plan, 1, "preflight")
    doc = yaml.safe_load(manifest.read_text())
    doc["defaults"]["solver"]["solver_options"] = {"SoftMemLimit": 128}
    manifest.write_text(yaml.safe_dump(doc))
    admission = json.loads(plan.read_text())
    admission["cases"][1]["manifest_sha256"] = file_sha256(manifest)
    plan.write_text(json.dumps(admission))
    with pytest.raises(ValueError, match="outside"):
        expansion.check(plan, 1, "preflight")


def test_modified_workbook_rejected(prepared):
    plan, data_root, _ = prepared
    (data_root / expansion.INPUT_PATHS[300]).write_bytes(b"modified")
    with pytest.raises(ValueError, match="workbook changed"):
        expansion.check(plan, 1, "preflight")


def example_preflight(index, digest):
    population, direct = expansion.CASES[index]
    return {"workbook_sha256": digest, "data_signature": {"counts": {"warehouses": population}},
            "scenario_count": 9, "period_count": 60, "routes_oc": 592 if direct else 0,
            "total_variables": expansion.SIZE_LIMITS[population]}


@pytest.mark.parametrize("index", range(5))
def test_preflight_is_preserved_separately_from_run_output(prepared, index):
    plan = prepared[0]
    folder, _, doc, digest = expansion.check(plan, index, "preflight")
    path = folder / "runs" / doc["experiments"][0]["name"] / "preflight.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(example_preflight(index, digest)))
    expansion.preflight_gate(plan, index, record=True)
    snapshot = (folder / "preflight_snapshot.json").read_bytes()
    path.write_text("Later solver-generated preflight")
    if index < 3:
        expansion.preflight_gate(plan, index)
    assert (folder / "preflight_snapshot.json").read_bytes() == snapshot
    path.write_text(snapshot.decode())
    with pytest.raises(FileExistsError):
        expansion.preflight_gate(plan, index, record=True)


@pytest.mark.parametrize("field,value", [
    ("scenario_count", 3), ("period_count", 1), ("routes_oc", 0),
    ("total_variables", 30_000_000), ("workbook_sha256", "changed"),
    ("data_signature", {"counts": {"warehouses": 500}}),
])
def test_invalid_preflight_rejected(field, value):
    payload = example_preflight(0, "frozen")
    changed = deepcopy(payload)
    changed[field] = value
    with pytest.raises(ValueError, match="dimensions"):
        expansion.validate_preflight(changed, 0, "frozen")


def test_solve_requires_intact_preflight_receipt(prepared):
    with pytest.raises(FileNotFoundError):
        expansion.preflight_gate(prepared[0], 0)


def test_submission_and_worker_contract():
    scripts = Path(expansion.__file__).parent
    submit = (scripts / "submit_scip_expansion.sh").read_text()
    worker = (scripts / "run_scip_expansion.slurm").read_text()
    assert "--array=0-4%2" in submit
    assert "--array=0-2%2" in submit
    assert "aftercorr:" in submit
    assert "unset SBATCH_QOS" in submit
    assert "--qos=" not in submit + worker
    assert "git pull" not in submit + worker
    assert "pip install" not in submit + worker
    assert ".submission-claimed" in submit
    assert 'tee -a "$SCIP_EXPANSION_ROOT/submission.txt"' in submit
    assert '--check-preflight' in worker
    assert '|| solve_rc=$?' in worker


@pytest.mark.parametrize("fail_second", [False, True])
def test_actual_bash_submission_receipts_and_duplicate_guard(tmp_path, fail_second):
    """Exercise shell orchestration with fake Slurm; never contact a scheduler."""
    bash = ("C:/Program Files/Git/bin/bash.exe" if sys.platform == "win32"
            else shutil.which("bash"))
    if not bash or not Path(bash).is_file():
        pytest.skip("Bash unavailable for shell-contract test")

    def shell_path(path):
        if sys.platform != "win32":
            return str(path)
        return f"/{path.drive[0].lower()}{path.as_posix()[2:]}"

    fake = tmp_path / "bin"
    fake.mkdir()
    root = tmp_path / "campaign"
    root.mkdir()
    (fake / "git").write_text(
        '#!/bin/bash\nif [ "$1" = rev-parse ]; then printf "%s\\n" "$FAKE_SHA"; fi\n',
        encoding="utf-8", newline="\n")
    (fake / "python").write_text('#!/bin/bash\nexit 0\n', encoding="utf-8", newline="\n")
    (fake / "sbatch").write_text(
        '#!/bin/bash\nset -eu\n'
        'test -z "${SBATCH_QOS:-}"\n'
        'printf "%s " "$@" >> "$FAKE_CALLS"\nprintf "\\n" >> "$FAKE_CALLS"\n'
        'count=$(wc -l < "$FAKE_CALLS")\n'
        'if [ "$count" -eq 2 ] && [ "$FAIL_SECOND" = 1 ]; then exit 1; fi\n'
        'printf "%s\\n" "$((900 + count))"\n', encoding="utf-8", newline="\n")
    for path in fake.iterdir():
        path.chmod(0o755)
    source = Path(expansion.__file__).parent / "submit_scip_expansion.sh"
    env = dict(os.environ)
    env.update(SCIP_EXPANSION_CHECKOUT=shell_path(tmp_path),
               SCIP_PYTHON=shell_path(fake / "python"),
               SCIP_EXPANSION_ROOT=shell_path(root), SCIP_EXPANSION_SOURCE="frozen-sha",
               FAKE_SHA="frozen-sha", FAKE_CALLS=shell_path(tmp_path / "calls.txt"),
               FAIL_SECOND=str(int(fail_second)), SBATCH_QOS="invalid-inherited-qos")
    command = [bash, "-c", 'export PATH="$1:/usr/bin:/bin:$PATH"; exec bash "$2"', "_",
               shell_path(fake), shell_path(source)]
    run = subprocess.run(command, env=env, text=True, capture_output=True, timeout=60)
    assert (run.returncode != 0) == fail_second, run.stdout + run.stderr
    receipt = (root / "submission.txt").read_text()
    assert "PREFLIGHT_JOB=901" in receipt
    assert ("SOLVE_JOB=902" in receipt) == (not fail_second)
    calls = (tmp_path / "calls.txt").read_text()
    assert "--array=0-4%2" in calls
    assert "--array=0-2%2" in calls
    assert "--dependency=aftercorr:901" in calls
    assert "--qos" not in calls
    again = subprocess.run(command, env=env, text=True, capture_output=True, timeout=60)
    assert again.returncode != 0
    assert (tmp_path / "calls.txt").read_text() == calls
