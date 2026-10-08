"""S2 runtime components; no production entry point, submission or admission."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from pathlib import Path

from scripts import mvp2_h300_thread_contract as design

PHASES = ("build", "optimization", "export_validation", "cleanup")
CAPS = (900, 1800, 900, 300)


def encoded(value):
    return (json.dumps(value, sort_keys=True, allow_nan=False) + "\n").encode()


def read_json(path):
    """Reject nonfinite JSON and duplicate keys, including nested objects."""
    return decode_json(Path(path).read_bytes())


def decode_json(payload):
    """The same strict decoder is used for on-disk and portable products."""

    def pairs(items):
        result = {}
        for key, value in items:
            design.require(key not in result, "Duplicate JSON key.")
            result[key] = value
        return result

    def constant(_value):
        raise ValueError("Nonfinite JSON value.")

    return json.loads(payload, object_pairs_hook=pairs, parse_constant=constant)


def write_once(path, value):
    """Exclusive publication: a interrupted receipt is never silently replaced."""
    path = Path(path)
    design.require(not path.is_symlink(), "Linked receipt.")
    payload = encoded(value)
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


class PhaseJournal:
    """Four ordered phase files; publish by rename only after flushing each event."""

    def __init__(self, directory, identity):
        design.require(
            isinstance(identity, str)
            and len(identity) == 64
            and all(c in "0123456789abcdef" for c in identity),
            "Bad identity.",
        )
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=False)
        self.identity = identity
        self.index = 0

    def enter(self, phase):
        design.require(
            self.index < 4 and PHASES[self.index] == phase, "Repeated/out-of-order phase."
        )
        target = self.directory / f"phase-{self.index}.json"
        temporary = target.with_suffix(".pending")
        write_once(temporary, {"identity": self.identity, "index": self.index, "phase": phase})
        design.require(not target.exists(), "Phase already published.")
        temporary.rename(target)
        self.index += 1

    def failure_cleanup(self):
        write_once(
            self.directory / "failure-cleanup.json",
            {
                "identity": self.identity,
                "after_phase_count": self.index,
                "phase": "cleanup_after_failure",
            },
        )


def phase_events(directory, identity):
    """Read only contiguous fixed names; child timestamps never set parent deadlines."""
    directory = Path(directory)
    design.require(not directory.is_symlink(), "Linked phase directory.")
    events = []
    for index, phase in enumerate(PHASES):
        path = directory / f"phase-{index}.json"
        design.require(not path.is_symlink(), "Linked phase event.")
        if not path.exists():
            design.require(
                not any((directory / f"phase-{i}.json").exists() for i in range(index + 1, 4)),
                "Phase journal has a hole.",
            )
            break
        design.require(path.stat().st_size <= 1024, "Oversized phase event.")
        value = read_json(path)
        design.require(
            value == {"identity": identity, "index": index, "phase": phase},
            "Phase identity/schema drift.",
        )
        events.append(phase)
    return events


def failure_cleanup_event(directory, identity, events):
    path = Path(directory) / "failure-cleanup.json"
    design.require(not path.is_symlink(), "Linked failure cleanup event.")
    if not path.exists():
        return False
    design.require(path.stat().st_size <= 1024, "Oversized failure event.")
    design.require(
        1 <= len(events) <= 3
        and read_json(path)
        == {
            "identity": identity,
            "after_phase_count": len(events),
            "phase": "cleanup_after_failure",
        },
        "Invalid failure cleanup transition.",
    )
    return True


def run_phases(journal, build, optimize, export, cleanup):
    """Observable callbacks; parent supervision, not this cooperative worker, enforces caps."""
    try:
        journal.enter("build")
        model = build()
        journal.enter("optimization")
        result = optimize(model)
        journal.enter("export_validation")
        return export(result)
    finally:
        # Failure may leave an incomplete ordered journal; do not forge skipped phases.
        try:
            if journal.index == 3:
                journal.enter("cleanup")
            elif journal.index < 3:
                journal.failure_cleanup()
        finally:
            cleanup()


class Deadlines:
    """Parent monotonic clock; observed transitions cannot reset a phase or child cap."""

    def __init__(self, started, block_deadline, *, caps=CAPS):
        design.number(started, "monotonic start")
        design.number(block_deadline, "block deadline")
        design.require(
            len(caps) == 4 and all(design.number(v, "phase cap") > 0 for v in caps),
            "Invalid phase caps.",
        )
        self.started = self.last = self.phase_started = started
        self.caps = tuple(caps)
        self.hard = min(started + sum(caps), block_deadline)
        self.seen = []
        self.transitions = []
        self.aborted = False

    def observe(self, now, events, *, aborted=False):
        design.number(now, "monotonic observation")
        design.require(now >= self.last, "Monotonic clock went backwards.")
        self.last = now
        design.require(type(aborted) is bool and (not self.aborted or aborted), "Cleanup rollback.")
        design.require(not self.aborted or events == self.seen, "Phase after aborted cleanup.")
        design.require(
            events == list(PHASES[: len(events)])
            and len(events) <= 4
            and events[: len(self.seen)] == self.seen,
            "Phase rollback/order drift.",
        )
        # Check the OLD phase before consuming newly visible transitions. A late
        # export event cannot hide an optimization overrun between polls.
        old_index = 3 if self.aborted else max(0, len(self.seen) - 1)
        if now >= self.hard:
            return "child_or_block_watchdog"
        if now - self.phase_started >= self.caps[old_index]:
            return f"{PHASES[old_index]}_watchdog"
        if len(events) > len(self.seen):
            self.transitions.extend(
                {"phase": p, "observed_seconds": now - self.started}
                for p in events[len(self.seen) :]
            )
            # First build event does not grant a new build window.
            if len(events) > 1:
                self.phase_started = now
            self.seen = list(events)
        if aborted and not self.aborted:
            design.require(1 <= len(events) <= 3, "Invalid aborted phase.")
            self.phase_started = now
            self.aborted = True
            self.transitions.append(
                {"phase": "cleanup_after_failure", "observed_seconds": now - self.started}
            )
        return None


def spawn_owned(command, **kwargs):
    """No shell; POSIX children own a new session/group for bounded group teardown.

    This low-level component has no scheduler, solver or production command.
    The caller is responsible for supplying a separately qualified worker.
    """
    design.require(
        isinstance(command, list) and command and all(isinstance(v, str) for v in command),
        "Explicit argv required.",
    )
    design.require(
        not any(k in kwargs for k in ("shell", "start_new_session", "process_group")),
        "Cannot replace ownership controls.",
    )
    started = time.monotonic()
    process = subprocess.Popen(command, shell=False, start_new_session=os.name == "posix", **kwargs)
    process._s2_owned_group = os.name == "posix"
    process._s2_started = started
    return process


def group_alive(process):
    if not getattr(process, "_s2_owned_group", False):
        return process.poll() is None
    try:
        os.killpg(process.pid, 0)
        return True
    except ProcessLookupError:
        return False


def stop_owned(process, grace, *, clock=time.monotonic, pause=time.sleep):
    """Escalate only this child's owned group; reap root, retain uncertain tree closure."""
    design.number(grace, "cleanup grace")
    grouped = getattr(process, "_s2_owned_group", False)

    def send(sig):
        try:
            if grouped:
                os.killpg(process.pid, sig)
            elif process.poll() is None:
                process.terminate() if sig == signal.SIGTERM else process.kill()
        except ProcessLookupError:
            pass

    send(signal.SIGTERM)
    deadline = clock() + grace
    while group_alive(process) and clock() < deadline:
        process.poll()
        pause(min(0.02, max(0, deadline - clock())))
    if group_alive(process):
        send(signal.SIGKILL if os.name == "posix" else signal.SIGTERM)
        if os.name != "posix" and process.poll() is None:
            process.kill()
    process.wait(timeout=2)
    # Windows root exit cannot establish descendant closure. POSIX zombies or
    # escaped sessions cannot establish a reusable production allocation either.
    return grouped and not group_alive(process)


def supervise(
    process,
    directory,
    identity,
    block_deadline,
    *,
    caps=CAPS,
    poll_seconds=0.05,
    clock=time.monotonic,
    pause=time.sleep,
):
    """Enforce observed phase and child/block deadlines, including corrupt journals."""
    design.require(hasattr(process, "_s2_owned_group"), "Refuse an unowned process.")
    started = process._s2_started
    try:
        design.require(
            type(poll_seconds) in (int, float) and 0 < poll_seconds <= 1,
            "Bound the polling interval.",
        )
        guard = Deadlines(started, block_deadline, caps=caps)
    except BaseException:
        stop_owned(process, 0)
        raise
    reason, error_type = None, None
    tree_closed = False
    try:
        while True:
            events = phase_events(directory, identity)
            aborted = failure_cleanup_event(directory, identity, events)
            reason = guard.observe(clock(), events, aborted=aborted)
            code = process.poll()
            if reason or code is not None:
                break
            pause(min(poll_seconds, max(0, guard.hard - clock())))
        if reason is None and code == 0 and len(events) != 4:
            reason = "incomplete_phase_journal"
        if reason is None and code != 0:
            reason = "child_failure"
        if reason is None and group_alive(process):
            reason = "live_descendants"
    except BaseException as error:
        reason, error_type = "control_error", type(error).__name__
        if isinstance(error, (KeyboardInterrupt, SystemExit)):
            raise
    finally:
        tree_closed = stop_owned(process, min(caps[3], max(0, guard.hard - clock())))
    return {
        "identity": identity,
        "root_pid": process.pid,
        "return_code": process.returncode,
        "stop_reason": reason,
        "error_type": error_type,
        "owned_group_closed": tree_closed,
        "allocation_tree_closed": False,
        "observed_transitions": guard.transitions,
        "application_seconds": clock() - started,
        "production_admitted": False,
        "repeats_admitted": False,
    }


class BlockLedger:
    """One-shot software lifecycle ledger, NOT a scheduler/license admission certificate."""

    def __init__(self, directory, environment, started):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=False)
        self.environment = design.environment_key(environment)
        self.started = self.last = design.number(started, "block start")
        self.finished = []
        self.active = None
        self.stopped = False

    def begin(self, threads, environment, now):
        design.number(now, "block clock")
        design.require(now >= self.last, "Block clock rollback.")
        self.last = now
        design.require(
            not self.stopped and self.active is None and len(self.finished) < 5,
            "Stopped/overlapping/exhausted block.",
        )
        design.require(
            type(threads) is int and threads == design.ORDER[len(self.finished)],
            "Repeat or order drift.",
        )
        try:
            design.require(
                design.environment_key(environment) == self.environment, "Environment drift."
            )
            design.require(
                now - self.started + 3900 + 900 + 600 <= 21600,
                "Insufficient remaining block headroom.",
            )
            write_once(
                self.directory / f"claim-{threads}.json",
                {
                    "threads": threads,
                    "environment_sha256": self.environment,
                    "production_admitted": False,
                    "repeats_admitted": False,
                },
            )
        except Exception:
            self.stopped = True
            raise
        self.active = threads

    def finish(self, control, collection, now):
        design.number(now, "block clock")
        design.require(self.active is not None and now >= self.last, "No active child/clock drift.")
        self.last = now
        # Only normal native censoring may proceed; forged/missing closure never does.
        proceed = (
            control["return_code"] == 0
            and control["stop_reason"] is None
            and control["owned_group_closed"] is True
            and control["allocation_tree_closed"] is True
            and collection["integrity_accepted"] is True
            and collection["products_closed"] is True
            and collection["censor_reason"] in {None, "time_limit", "memory_limit"}
            and collection["disposition"]
            in {"complete_accepted_hierarchy", "feasible_partial_hierarchy", "no_incumbent"}
        )
        write_once(
            self.directory / f"closed-{self.active}.json",
            {
                "threads": self.active,
                "control": control,
                "collection": collection,
                "continue_to_distinct_arm": proceed,
                "production_admitted": False,
            },
        )
        self.finished.append(self.active)
        self.active = None
        self.stopped = not proceed
        return proceed

    def not_executed(self):
        return [t for t in design.ORDER if t not in self.finished and t != self.active]


def execute_h300(*_args, **_kwargs):
    """An explicit hard gate, independent of caller-provided accepted flags."""
    design.policy()
    raise PermissionError("H300 production and repeats remain closed; no job is admitted.")


RESOURCE_FIELDS = (
    "elapsed_seconds",
    "phase",
    "process_tree_rss_bytes",
    "process_tree_cpu_seconds",
    "cgroup_current_bytes",
    "application_peak_rss_bytes",
    "native_peak_decimal_gb",
    "observation_errors",
)


def resource_summary(samples):
    """Reduce scope-specific observations; live-tree CPU counters are NOT lifetime usage."""
    design.require(isinstance(samples, list) and len(samples) <= 5000, "Unbounded samples.")
    last = -1
    errors = 0
    gaps = []
    phases = []
    peaks = dict.fromkeys(RESOURCE_FIELDS[2:-1])
    for row in samples:
        design.require(
            set(row) == set(RESOURCE_FIELDS) and row["phase"] in PHASES,
            "Resource observation schema/phase drift.",
        )
        stamp = design.number(row["elapsed_seconds"], "sample clock")
        design.require(stamp >= last, "Sample clock rollback.")
        if last >= 0:
            gaps.append(stamp - last)
        last = stamp
        if row["phase"] not in phases:
            phases.append(row["phase"])
        design.require(
            type(row["observation_errors"]) is int and row["observation_errors"] >= 0,
            "Invalid inspection error count.",
        )
        errors += row["observation_errors"]
        for key in peaks:
            value = design.number(row[key], key, nullable=True)
            if value is not None:
                peaks[key] = value if peaks[key] is None else max(peaks[key], value)

    def gib(key):
        return None if peaks[key] is None else peaks[key] / 1024**3

    return {
        "samples": len(samples),
        "covered_phases": phases,
        "inspection_errors": errors,
        "maximum_sample_gap_seconds": max(gaps) if gaps else None,
        "sampled_tree_peak_rss_gib": gib("process_tree_rss_bytes"),
        "sampled_cgroup_peak_gib": gib("cgroup_current_bytes"),
        "observed_application_highwater_rss_gib": gib("application_peak_rss_bytes"),
        "observed_native_memory_gib": None
        if peaks["native_peak_decimal_gb"] is None
        else peaks["native_peak_decimal_gb"] * 10**9 / 1024**3,
        "last_live_tree_cpu_seconds": samples[-1]["process_tree_cpu_seconds"] if samples else None,
        "measured_lifetime_cpu_hours": None,
        "continuous_peak_coverage_proven": False,
    }
