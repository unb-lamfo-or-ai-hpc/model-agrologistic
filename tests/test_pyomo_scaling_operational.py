"""Owned claims, submission uncertainty, archive integrity and resource controls."""

import copy
import csv
import hashlib
import io
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import pyomo_scaling_bootstrap as b
from scripts import pyomo_scaling_campaign as op
from scripts import pyomo_scaling_contract as c
from scripts import qualify_pyomo_scaling as q
from tests.test_pyomo_scaling_contract import pilots

SHA = "a" * 40


@pytest.fixture
def campaign(tmp_path, monkeypatch):
    monkeypatch.setattr(op, "BASE", tmp_path)
    monkeypatch.setattr(op, "login", lambda: None)
    monkeypatch.setattr(op, "verify_tools", lambda *args: None)
    directory = tmp_path / c.CAMPAIGN
    directory.mkdir()
    inputs = {
        str(p): {
            key: str(tmp_path / (str(p) + key))
            for key in ("workbook", "population", "order", "materialization")
        }
        for p in c.POPULATIONS
    }
    manifest = {"inputs": inputs, "source_commit": SHA, "profile": c.PROFILE}
    monkeypatch.setattr(op, "load_campaign", lambda *args, **kwargs: manifest)
    monkeypatch.setattr(op, "check_inputs", lambda *args: None)
    monkeypatch.setattr(op, "selection", lambda *args: {"test": "selection"})
    monkeypatch.setattr(op, "observations", lambda *args: [])
    monkeypatch.setattr(op.r, "spec_payload", lambda *args: {"test": "specification"})
    monkeypatch.setattr(c, "specification", lambda *args: None)
    monkeypatch.setattr("scripts.probe_npad_gurobi_license.check_file", lambda: None)
    return directory, manifest


def recorder(*, submission_returncode=0, submission_stdout="123456\n", probe_returncode=0):
    calls = []

    def command(argv, **kwargs):
        calls.append(argv)
        if argv[0] == "sbatch":
            if "--test-only" in argv:
                return SimpleNamespace(returncode=probe_returncode, stdout="", stderr="")
            return SimpleNamespace(
                returncode=submission_returncode, stdout=submission_stdout, stderr=""
            )
        job = argv[argv.index("-j") + 1]
        return SimpleNamespace(returncode=0, stdout=f"{job}|COMPLETED|0:0|4|1K\n", stderr="")

    return calls, command


@pytest.mark.parametrize("solver", c.SOLVERS)
def test_start_is_one_job_and_claim_is_never_reused(campaign, solver):
    directory, manifest = campaign
    identity = c.cell(300, solver, 1, 1)["id"]
    calls, command = recorder()
    result = op.start(directory, SHA, identity, True, command=command)
    claim = directory / identity
    assert result["job_id"] == "123456"
    assert len([a for a in calls if a[0] == "sbatch" and "--test-only" not in a]) == 1
    assert result["plan_sha256"] == q.digest(claim / "plan.json")
    assert op.read(claim / "campaign.json") == manifest
    assert "--exclusive" in calls[-1] and "--no-requeue" in calls[-1]
    before = list(calls)
    with pytest.raises(ValueError, match="Existing claim"):
        op.start(directory, SHA, identity, True, command=command)
    assert before == calls


@pytest.mark.parametrize("stdout,code", [("", 1), ("timeout", 0), ("1234\n1235\n", 0)])
def test_uncertain_submission_is_preserved_and_never_retried(campaign, stdout, code):
    directory, _ = campaign
    identity = c.cell(300, "highs", 16, 1)["id"]
    calls, command = recorder(submission_stdout=stdout, submission_returncode=code)
    with pytest.raises(ValueError, match="uncertain"):
        op.start(directory, SHA, identity, True, command=command)
    assert (directory / identity / "submission_intent.json").is_file()
    assert not (directory / identity / "job.json").exists()
    before = list(calls)
    with pytest.raises(ValueError, match="Existing claim"):
        op.start(directory, SHA, identity, True, command=command)
    assert calls == before


def test_scheduler_rejection_precedes_creation_of_run_claim(campaign):
    directory, _ = campaign
    identity = c.cell(300, "highs", 1, 1)["id"]
    calls, command = recorder(probe_returncode=1)
    with pytest.raises(ValueError, match="scheduler admission rejected"):
        op.start(directory, SHA, identity, True, command=command)
    assert not (directory / identity).exists() and len(calls) == 1


def test_two_active_jobs_block_a_third_submission(campaign):
    directory, _ = campaign
    for item, job in zip(c.cells()[:2], ("111", "112"), strict=True):
        claim = directory / item["id"]
        claim.mkdir()
        q.write_json(claim / "job.json", {"job_id": job})
    calls = []

    def command(argv):
        calls.append(argv)
        job = argv[argv.index("-j") + 1]
        return SimpleNamespace(returncode=0, stdout=f"{job}|RUNNING|0:0|4|\n", stderr="")

    with pytest.raises(ValueError, match="Two campaign jobs"):
        op.start(directory, SHA, c.cells()[2]["id"], True, command=command)
    assert all(call[0] == "sacct" for call in calls)


def test_uncertain_prior_claim_blocks_any_new_job(campaign):
    directory, _ = campaign
    (directory / c.cells()[0]["id"]).mkdir()
    calls, command = recorder()
    with pytest.raises(ValueError, match="Uncertain claimed"):
        op.start(directory, SHA, c.cells()[1]["id"], True, command=command)
    assert calls == []


def test_next_population_is_blocked_before_scheduler_access(campaign):
    directory, _ = campaign
    calls, command = recorder()
    with pytest.raises(ValueError, match="Four original pilot"):
        op.start(directory, SHA, c.cell(400, "highs", 1, 1)["id"], True, command=command)
    assert calls == []


def test_all_remaining_cells_are_blocked_until_current_pilots_close(campaign):
    directory, _ = campaign
    calls, command = recorder()
    with pytest.raises(ValueError, match="Four original pilot"):
        op.start(directory, SHA, c.cell(300, "highs", 4, 1)["id"], True, command=command)
    assert calls == []


def test_actual_closed_pilots_open_next_population_without_auto_submission(campaign, monkeypatch):
    directory, manifest = campaign
    observed = pilots()
    for report in observed:
        report["campaign_sha256"] = c.digest(manifest)
    monkeypatch.setattr(op, "observations", lambda *args: observed)
    calls, command = recorder()
    result = op.start(directory, SHA, c.cell(400, "highs", 1, 1)["id"], True, command=command)
    assert result["status"] == "submitted_one_cell_only"
    assert len([a for a in calls if a[0] == "sbatch" and "--test-only" not in a]) == 1


def test_lock_has_no_automatic_expiry(campaign):
    directory, _ = campaign
    (directory / "submission.lock").mkdir()
    calls, command = recorder()
    with pytest.raises(FileExistsError):
        op.start(directory, SHA, c.cells()[0]["id"], True, command=command)
    assert calls == [] and (directory / "submission.lock").is_dir()


def allocation_text(**changes):
    values = {
        "JobId": "123",
        "UserId": "user(9)",
        "NumNodes": "1",
        "NumCPUs": "64",
        "TimeLimit": "12:00:00",
        "Partition": "intel-256",
        "Account": "sxdsouza",
        "QOS": "preempt",
        "JobState": "RUNNING",
        "MinMemoryNode": "192G",
        "Shared": "0",
        "NodeList": "node01",
    }
    values.update(changes)
    return " ".join(k + "=" + v for k, v in values.items())


def test_exclusive_allocation_may_own_more_cpus_than_requested():
    record = op.allocation(allocation_text(), "123", 9)
    assert record["NumCPUs"] == "64"


@pytest.mark.parametrize(
    "fields,expected",
    [
        ({"OverSubscribe": "NO"}, True),
        ({"Shared": "0", "OverSubscribe": "NO"}, True),
        ({"Shared": "1", "OverSubscribe": "NO"}, False),
        ({}, False),
    ],
)
def test_versioned_slurm_exclusive_observations_are_not_inferred(fields, expected):
    assert op.exclusive_observed(fields) is expected


@pytest.mark.parametrize(
    "change",
    [
        {"Shared": "1"},
        {"NumCPUs": "16"},
        {"MinMemoryNode": "96G"},
        {"TimeLimit": "08:00:00"},
        {"JobId": "124"},
        {"UserId": "other(10)"},
        {"NodeList": "node[1-2]"},
        {"JobState": "PENDING"},
        {"NumNodes": "2"},
    ],
)
def test_resource_drift_blocks_worker_release(change):
    with pytest.raises(ValueError, match="allocation"):
        op.allocation(allocation_text(**change), "123", 9)


def test_bootstrap_identity_checks_cold_pinned_files_before_application_imports(
    tmp_path, monkeypatch
):
    claim = tmp_path / c.CAMPAIGN / c.cell(300, "highs", 1, 1)["id"]
    root = tmp_path / c.QUALIFICATION / "source"
    control = claim / "control/sto"
    control.mkdir(parents=True)
    source_files = {}
    for name in (op.DRIVER, op.BOOTSTRAP, "scripts/pyomo_worker_bootstrap.py"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"# public pinned source\n")
        source_files[name] = q.digest(path)
    campaign = {"source_commit": SHA, "source_root": str(root), "source_files": source_files}
    plan = {
        "source_commit": SHA,
        "source_root": str(root),
        "cell": {"id": claim.name},
        "campaign_sha256": c.digest(campaign),
    }
    q.write_json(claim.parent / "campaign.json", campaign)
    q.write_json(claim / "plan.json", plan)
    q.write_json(
        claim / "job.json",
        {"source_commit": SHA, "job_id": "123", "plan_sha256": q.digest(claim / "plan.json")},
    )
    monkeypatch.setenv("SLURM_JOB_ID", "123")
    monkeypatch.setenv("SLURM_STEP_ID", "0")
    monkeypatch.chdir(control)
    # /proc exists on the target. Mock only that OS read on Windows.
    original = Path.read_text

    def proc_text(path, *args, **kwargs):
        if str(path).replace("\\", "/").startswith("/proc/"):
            return "123 (python) " + " ".join(["1"] * 30)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", proc_text)
    entry = b.identity(claim, SHA, root, started=1, audit_base=tmp_path)
    assert entry["step_id"] == "0" and entry["proc_start_ticks"] == 1
    (root / op.DRIVER).write_bytes(b"# changed\n")
    with pytest.raises(ValueError, match="Pinned"):
        b.identity(claim, SHA, root, started=1, audit_base=tmp_path)


def test_evidence_is_streamable_and_excludes_native_scratch(tmp_path):
    (tmp_path / "file.json").write_bytes(b"{}")
    scratch = tmp_path / "control/sto/native-temporary"
    scratch.mkdir(parents=True)
    (scratch / "private.lic").write_bytes(b"Never include")
    files = op.evidence_files(tmp_path)
    assert set(files) == {"file.json"}
    assert isinstance(files["file.json"], Path)
    (tmp_path / "private.xlsx").write_bytes(b"No workbook in archive")
    with pytest.raises(ValueError, match="Forbidden"):
        op.evidence_files(tmp_path)


def test_observation_cannot_be_changed_without_breaking_archive_binding(tmp_path):
    payload = {"cell": c.cell(300, "highs", 1, 1), "status": "original"}
    data = c.encoded(payload)
    archive = tmp_path / "evidence.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        info = tarfile.TarInfo("campaign_observation.json")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    marker = {"sha256": q.digest(archive), "observation": payload}
    assert op.archive_report(tmp_path, marker) == payload
    edited = copy.deepcopy(marker)
    edited["observation"]["status"] = "manufactured"
    with pytest.raises(ValueError, match="observation differs"):
        op.archive_report(tmp_path, edited)
    with archive.open("ab") as stream:
        stream.write(b"changed")
    with pytest.raises(ValueError, match="archive differs"):
        op.archive_report(tmp_path, marker)


def test_no_qualification_or_private_job_can_run_on_login(tmp_path, monkeypatch):
    monkeypatch.delenv("SLURM_JOB_ID", raising=False)
    monkeypatch.delenv("SLURM_STEP_ID", raising=False)
    with pytest.raises(ValueError):
        q.run(tmp_path / c.QUALIFICATION, SHA)


def test_bootstrap_does_not_import_application_or_native_modules_before_release():
    import ast

    tree = ast.parse(Path(b.__file__).read_text(encoding="utf-8"))
    imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
    names = [alias.name for n in imports if isinstance(n, ast.Import) for alias in n.names]
    assert not {"pyomo", "gurobipy", "highspy", "pandas", "numpy", "scripts"} & set(names)
    assert all(
        isinstance(n, ast.Import) or not (n.module or "").startswith(("src", "scripts"))
        for n in imports
    )


def test_recording_plan_digest_uses_all_bytes(tmp_path):
    path = tmp_path / "plan.json"
    record = {"schema": c.SCHEMA}
    q.write_json(path, record)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == c.digest(record)


def test_cold_probe_command_has_no_scheduler_or_private_data_path(tmp_path):
    argv = q.probe_command("highs", 16, tmp_path / "public.json")
    assert argv[1:3] == ["-B", "-I"]
    assert "probe" in argv and "16" in argv
    assert not any("sbatch" in a or "model_input.xlsx" in a for a in argv)


def test_tables_keep_all_unstarted_cells_and_missing_values(campaign):
    directory, _ = campaign
    result = op.tables(directory, SHA, directory / "tables-v1")
    assert result["planned_cells"] == 90 and result["collected"] == 0
    with (directory / "tables-v1/results.csv").open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 90 and all(r["status"] == "not_started" for r in rows)
    assert all(r["objective"] == "" and r["common_gap_fraction"] == "" for r in rows)
    with pytest.raises(ValueError):
        op.tables(directory, SHA, directory / "tables-v1")


def test_all_input_defaults_use_original_population_and_osrm_locations():
    inputs = op.default_inputs()
    assert set(inputs) == {"300", "400", "500"}
    for population, paths in inputs.items():
        assert f"warehouses_{population}" in paths["workbook"]
        assert "nine_population_osrm_v1" in paths["materialization"]
        assert paths["population"].endswith("warehouse_population_manifest.json")
        assert paths["order"].endswith("warehouse_population_order.csv")
