"""Real public HiGHS lifecycle through controlled Slurm transport and collection."""

import os
import subprocess
import threading
import time
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from scripts import pyomo_scaling_campaign as op
from scripts import pyomo_scaling_contract as c
from scripts import pyomo_worker_bootstrap as boot
from scripts import qualify_pyomo_scaling as q
from tests.test_excel_loader import build_tiny_golden_excel
from tests.test_pyomo_scaling_operational import SHA, allocation_text
from tests.test_pyomo_scaling_parallel import require_native
from tests.test_scalar_r3a import tiny_selection, tiny_spec


def test_real_case_supervised_step_validation_streamed_collection_and_idempotence(
    tmp_path, monkeypatch
):
    if os.name == "nt":
        tmp_path = Path("\\\\?\\" + str(tmp_path.resolve()))
    require_native()
    local_site = os.environ.get("SCALING_LOCAL_TEST_SITE")
    if local_site:
        monkeypatch.syspath_prepend(local_site)
    import highspy

    highspy.Highs.resetGlobalScheduler(True)
    workbook = tmp_path / "public.xlsx"
    build_tiny_golden_excel(workbook)
    item = c.cell(300, "highs", 4, 1)
    original = tiny_spec(workbook, "sto")
    spec = replace(
        original,
        name=item["id"],
        max_estimated_variables=30000000,
        loader=replace(
            original.loader,
            scenario_generation_mode="cartesian",
            penalty_policy="fixed",
            default_unmet_demand_penalty=90000,
            default_emergency_static_penalty=45000,
            default_emergency_reception_penalty=45000,
        ),
        solver=replace(
            original.solver,
            backend="pyomo",
            solver_name="highs",
            threads=4,
            time_limit=28800,
            mip_gap=0.01,
            seed=42,
            collect_resource_diagnostics=False,
            solver_options={
                "indicator_reformulation": c.POLICY,
                "pyomo_max_variables": 30000000,
                "highs_parallel": "on",
            },
        ),
    )
    shape = {"warehouses": 2, "periods": 2, "sto_scenarios": 9}
    selected = tiny_selection()
    _, original_receipt = op.r.preflight(spec, shape, selected)
    claim = tmp_path / c.CAMPAIGN / item["id"]
    claim.mkdir(parents=True)
    plan = {"cell": item, "source_commit": SHA, "cases": [op.r.spec_payload(spec)]}
    plan = op.r.strict_json(c.encoded(plan))
    campaign = {
        "runtime": {},
        "source_files": {},
        "profile": c.PROFILE,
        "inputs": {"300": {"workbook": str(workbook)}},
    }
    q.write_json(claim / "plan.json", plan)
    q.write_json(claim / "campaign.json", campaign)
    q.write_json(claim.parent / "campaign.json", campaign)
    q.write_json(claim / "warehouse_selection.json", selected)
    job = {"job_id": "123", "source_commit": SHA, "plan_sha256": q.digest(claim / "plan.json")}
    q.write_json(claim / "job.json", job)
    monkeypatch.setattr(op, "load_run", lambda *args, **kwargs: (plan, campaign))
    monkeypatch.setattr(op, "load_campaign", lambda *args, **kwargs: campaign)
    monkeypatch.setattr(op, "environment", lambda: {})
    monkeypatch.setattr(op, "verify_source", lambda *args: None)
    monkeypatch.setattr(op, "check_inputs", lambda *args: None)
    monkeypatch.setattr(
        op,
        "cpu_topology",
        lambda *args: {"physical_cores": 16, "logical_threads_per_core": [1] * 16},
    )
    monkeypatch.setattr(op.o, "verify_tools", lambda *args: None)
    monkeypatch.setattr(op, "verify_tools", lambda *args: None)
    monkeypatch.setattr(op, "login", lambda: None)
    monkeypatch.setattr(op.os, "getuid", lambda: 9, raising=False)
    monkeypatch.setattr(op.os, "sched_getaffinity", lambda _: set(range(16)), raising=False)
    monkeypatch.setattr(boot, "proc_start", lambda _: 123)
    monkeypatch.setattr(c, "specification", lambda *args: spec)
    monkeypatch.setenv("SLURM_JOB_ID", "123")
    monkeypatch.setenv("SLURM_STEP_ID", "0")
    monkeypatch.setattr(
        "scripts.mvp2_scalar_wd_h215_operational.hardware_observation",
        lambda: {"machine": "public-test", "cpu_model": {"model": "public"}},
    )

    def input_check(population, receipt):
        for key in (
            "mathematical_contract",
            "warehouse_selection",
            "effective_scenario_probabilities",
        ):
            assert c.digest(receipt[key]) == c.digest(original_receipt[key])
        return {"public_fixture": True}

    monkeypatch.setattr(c, "input_certificate", input_check)
    engine = op.r.run_case_software

    def tiny_engine(specification, directory, expectations, selection, **kwargs):
        assert expectations == {"warehouses": 300, "periods": 60, "sto_scenarios": 9}
        return engine(specification, directory, shape, selection, **kwargs)

    monkeypatch.setattr(op.r, "run_case_software", tiny_engine)
    raw = (
        "123|COMPLETED|0:0|100|\n123.batch|COMPLETED|0:0|100|123K\n"
        "123.extern|COMPLETED|0:0|100|1K\n123.0|COMPLETED|0:0|30|123K\n"
    )

    def command(argv, **kwargs):
        if argv[0] == "scontrol" and "job" in argv:
            value = allocation_text()
        elif argv[0] == "scontrol" and "step" in argv:
            value = "StepId=123.0 UserId=9 CPUs=16 Nodes=1 Tasks=1 State=RUNNING NodeList=node01"
        elif argv[0] == "sacct":
            value = raw
        else:
            raise AssertionError("No live scheduler or cancellation allowed")
        return SimpleNamespace(returncode=0, stdout=value, stderr="")

    worker_errors = []

    class LocalProcess:
        returncode = None

        def __init__(self, argv, **kwargs):
            assert "--cpus-per-task=16" in argv and "-S" in argv
            self.error = None

            def run():
                try:
                    control = claim / "control/sto"
                    monkeypatch.chdir(control)
                    entry = {
                        **job,
                        "mode": "sto",
                        "step_id": "0",
                        "pid": os.getpid(),
                        "proc_start_ticks": 123,
                        "started_monotonic": time.monotonic(),
                    }
                    boot.publish(control / "entry.json", entry)
                    boot.publish(
                        control / "phase-00.json",
                        {"entry": entry, "phase": "input_build", "elapsed_seconds": 0.0},
                    )
                    recorder = boot.Recorder(control, entry)
                    recorder.stage("bootstrap_identity", lambda: None)
                    boot.publish(
                        control / "bootstrap.json",
                        {
                            "entry": entry,
                            "schema_version": "pyomo-bootstrap-v1",
                            "isolated": True,
                            "no_site": True,
                            "no_user_site": True,
                            "native_or_application_loaded_before_release": False,
                            "full_provenance_pending": True,
                        },
                    )
                    recorder.stage("exact_release", lambda: boot.release(control, entry))
                    recorder.stage("site_initialization", lambda: None)
                    recorder.stage("driver_import", lambda: None)
                    op.worker(claim, SHA, entry=entry, startup=recorder)
                    self.returncode = 0
                except Exception as error:
                    import traceback

                    worker_errors.append(traceback.format_exc())
                    self.error, self.returncode = error, 1

            self.thread = threading.Thread(target=run)
            self.thread.start()

        def poll(self):
            return self.returncode

        def wait(self, timeout):
            self.thread.join(timeout)
            if self.thread.is_alive():
                raise subprocess.TimeoutExpired("public_worker", timeout)
            if self.error:
                raise self.error
            return self.returncode

    class Observer:
        def __init__(self, *args):
            pass

        def sleep(self, seconds):
            time.sleep(min(seconds, 0.05))

        def finish(self):
            pass  # No fabricated resource samples or production-isolation claim.

    supervisor = op.o.supervise

    def controlled(*args, **kwargs):
        kwargs.update(
            command=command,
            popen=LocalProcess,
            reviewer=lambda claim, sha, mode, remaining: op.review_products(claim, plan),
        )
        return supervisor(*args, **kwargs)

    monkeypatch.setattr(op.o, "supervise", controlled)
    monkeypatch.setattr(op, "ExternalObserver", Observer)
    monkeypatch.setattr(op.r.r2, "command", command)
    assert op.batch(claim, SHA) == 0, (op.read(claim / "batch_outcome.json"), worker_errors)
    report = op.collect(claim, SHA, command=command)
    assert report["observation"]["operational_receipts_closed"], report
    assert report["observation"]["quality_target_met"]
    assert report["observation"]["effective_parameters"]["parallel"] == "on"
    assert report["observation"]["resource_observation"]["status"] == "missing_or_rejected"
    assert op.collect(claim, SHA, command=command) == report
    with tarfile_open(claim / "evidence.tar.gz") as archive:
        inventory = op.r.strict_json(archive.extractfile("inventory.json").read())
        for member in archive:
            if member.name != "inventory.json":
                assert op.r.r2.digest(archive.extractfile(member).read()) == inventory[member.name]
    monkeypatch.chdir(tmp_path)
    highspy.Highs.resetGlobalScheduler(True)


def tarfile_open(path):
    import tarfile

    return tarfile.open(path, "r:gz")
