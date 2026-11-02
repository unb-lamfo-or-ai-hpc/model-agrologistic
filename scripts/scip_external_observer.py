"""Batch-process observation of an owned SCIP worker; no solver API or signals."""

import csv
import io
import json
import math
import os
import time
from pathlib import Path

from src.logic.resource_telemetry import process_observation

FIELDS = (
    "elapsed_seconds", "phase", "pid", "proc_start_ticks", "process_tree_rss_bytes",
    "process_tree_cpu_seconds", "process_count", "root_native_threads",
    "inspection_seconds", "observation_errors",
)


def proc_start(pid, proc_root=Path("/proc")):
    fields = (proc_root / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()
    return int(fields[19])


class ExternalObserver:
    def __init__(self, claim, job, *, clock=time.monotonic, sleeper=time.sleep,
                 probe=process_observation, identity=proc_start):
        self.claim, self.job = claim, job
        self.clock, self.sleeper, self.probe, self.identity = clock, sleeper, probe, identity
        self.started, self.next_at = clock(), 0.0
        self.stream = (claim / "external-resource-timeseries.csv").open("x", newline="")
        self.writer = csv.DictWriter(self.stream, fieldnames=FIELDS)
        self.writer.writeheader()
        self.count, self.errors, self.entry = 0, [], None

    def tick(self, final=False):
        now = self.clock() - self.started
        if (not final and now < self.next_at) or self.count >= 9000:
            return
        self.next_at = now + 5
        control = self.claim / "control/sto"
        if not (control / "release.json").exists():
            return
        try:
            entry = json.loads((control / "entry.json").read_bytes())
            release = json.loads((control / "release.json").read_bytes())
            if (entry != release or entry["mode"] != "sto"
                    or not entry["step_id"].isdigit()
                    or any(entry[k] != v for k, v in self.job.items())):
                raise ValueError("Owned observer entry differs")
            if self.entry is not None and entry != self.entry:
                raise ValueError("Observer identity drift")
            self.entry = entry
            if self.identity(entry["pid"]) != entry["proc_start_ticks"]:
                raise ValueError("PID reused")
            observation = self.probe(entry["pid"])
            phase = "startup"
            for path in sorted(control.glob("phase-*.json")):
                event = json.loads(path.read_bytes())
                if event["entry"] != entry:
                    raise ValueError("Phase identity drift")
                phase = event["phase"]
            row = {k: observation.get(k) for k in FIELDS if k in observation}
            row.update(
                elapsed_seconds=now, phase=phase, pid=entry["pid"],
                proc_start_ticks=entry["proc_start_ticks"],
            )
            self.writer.writerow(row)
            self.stream.flush()
            self.count += 1
        except FileNotFoundError:
            # A worker may have exited before a final probe. No synthetic zero.
            pass
        except (OSError, ValueError, KeyError, IndexError) as exc:
            if len(self.errors) < 20:
                self.errors.append(type(exc).__name__)

    def sleep(self, seconds):
        self.tick()
        self.sleeper(seconds)

    def finish(self):
        try:
            self.tick(final=True)
        finally:
            self.stream.close()
        report = {
            "schema_version": "scip-external-observer-v1", "job": self.job,
            "entry": self.entry, "samples": self.count, "errors": self.errors,
            "observer_pid": os.getpid(), "sample_interval_seconds": 5,
            "max_samples": 9000, "elapsed_seconds": self.clock() - self.started,
            "scope": "Batch process samples worker process tree; no cgroup/solver memory.",
            "production_isolation_certified": False,
        }
        with (self.claim / "external-observer.json").open("x") as stream:
            json.dump(report, stream, indent=2, allow_nan=False)


def review_external(files, job):
    try:
        report = json.loads(files["external-observer.json"])
        rows = list(csv.DictReader(io.StringIO(
            files["external-resource-timeseries.csv"].decode()
        )))
        entry = json.loads(files["control/sto/entry.json"])
        if (report["schema_version"] != "scip-external-observer-v1"
                or report["job"] != job or report["entry"] != entry
                or report["samples"] != len(rows) or len(rows) > 9000):
            raise ValueError("Observer binding differs")
        times, rss = [], []
        for row in rows:
            if (int(row["pid"]) != entry["pid"]
                    or int(row["proc_start_ticks"]) != entry["proc_start_ticks"]):
                raise ValueError("Observed PID identity differs")
            elapsed = float(row["elapsed_seconds"])
            if not math.isfinite(elapsed) or elapsed < 0:
                raise ValueError("Nonfinite observer time")
            times.append(elapsed)
            if row["process_tree_rss_bytes"]:
                amount = float(row["process_tree_rss_bytes"])
                if not math.isfinite(amount) or amount < 0:
                    raise ValueError("Nonfinite observer memory")
                rss.append(amount)
        if times != sorted(times):
            raise ValueError("Unordered observer samples")
        gaps = [b - a for a, b in zip(times, times[1:], strict=False)]
        maximum = max(gaps) if gaps else None
        timely = len(rows) >= 2 and maximum <= 15 and not report["errors"]
        return {
            "status": "timely_samples" if timely else "sparse_or_incomplete",
            "samples": len(rows), "largest_interval_seconds": maximum,
            "sampled_worker_tree_peak_bytes": max(rss) if rss else None,
            "errors": report["errors"], "production_isolation_certified": False,
            "qualification": "Observed sampled scope only; no unobserved peak or causal overhead.",
        }
    except (KeyError, TypeError, ValueError):
        return {
            "status": "missing_or_rejected", "samples": 0,
            "sampled_worker_tree_peak_bytes": None, "production_isolation_certified": False,
        }
