"""Independent supervisor observation, public process fixtures, no HPC."""

import json
import subprocess
import sys

import pytest

from scripts import scip_external_observer as m

JOB = {"job_id": "123", "source_commit": "a" * 40, "plan_sha256": "b" * 64}


def files_at(tmp_path, pid=999, ticks=42):
    control = tmp_path / "control/sto"
    control.mkdir(parents=True)
    entry = dict(JOB, mode="sto", step_id="0", pid=pid, proc_start_ticks=ticks)
    for name in ("entry.json", "release.json"):
        (control / name).write_text(json.dumps(entry))
    return entry


def test_independent_ticks_and_replay_preserve_nulls_and_scope(tmp_path):
    files_at(tmp_path)
    now = [0.0]
    observer = m.ExternalObserver(
        tmp_path, JOB, clock=lambda: now[0], sleeper=lambda _: None,
        identity=lambda _: 42,
        probe=lambda _: {"process_tree_rss_bytes": 100, "inspection_seconds": 0.01},
    )
    observer.tick()
    now[0] = 5.1
    observer.tick()
    observer.finish()
    files = {p.relative_to(tmp_path).as_posix(): p.read_bytes()
             for p in tmp_path.rglob("*") if p.is_file()}
    report = m.review_external(files, JOB)
    assert report["status"] == "timely_samples"
    assert report["sampled_worker_tree_peak_bytes"] == 100
    assert not report["production_isolation_certified"]
    receipt = json.loads(files["external-observer.json"])
    assert receipt["observer_pid"] != 999
    assert "cgroup" not in next(iter(
        files["external-resource-timeseries.csv"].decode().splitlines()
    ))


def test_pid_reuse_and_entry_drift_are_never_sampled(tmp_path):
    files_at(tmp_path)
    observer = m.ExternalObserver(tmp_path, JOB, identity=lambda _: 43)
    observer.tick()
    observer.finish()
    report = json.loads((tmp_path / "external-observer.json").read_bytes())
    assert report["samples"] == 0 and report["errors"] == ["ValueError", "ValueError"]


def test_sparse_intervals_are_preserved_without_feasibility_inference(tmp_path):
    files_at(tmp_path)
    now = [0.0]
    observer = m.ExternalObserver(
        tmp_path, JOB, clock=lambda: now[0], identity=lambda _: 42,
        probe=lambda _: {"process_tree_rss_bytes": None},
    )
    observer.tick()
    now[0] = 100
    observer.finish()
    files = {p.relative_to(tmp_path).as_posix(): p.read_bytes()
             for p in tmp_path.rglob("*") if p.is_file()}
    report = m.review_external(files, JOB)
    assert report["status"] == "sparse_or_incomplete"
    assert report["largest_interval_seconds"] == 100
    assert report["sampled_worker_tree_peak_bytes"] is None


@pytest.mark.skipif(sys.platform != "linux", reason="Public Linux /proc observation")
def test_real_separate_process_is_sampled_without_solver_api(tmp_path):
    child = subprocess.Popen([sys.executable, "-B", "-c", "import time;time.sleep(3)"])
    try:
        files_at(tmp_path, child.pid, m.proc_start(child.pid))
        observer = m.ExternalObserver(tmp_path, JOB)
        observer.tick()
        observer.finish()
        report = json.loads((tmp_path / "external-observer.json").read_bytes())
        assert report["samples"] >= 1 and not report["errors"]
        assert report["observer_pid"] != child.pid
    finally:
        child.terminate()
        child.wait(timeout=5)
