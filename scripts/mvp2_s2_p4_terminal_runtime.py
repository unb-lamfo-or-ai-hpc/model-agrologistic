"""Versioned P4 terminal integration; old runtime/claims/certificates stay intact.

The maintainer approved sharing the existing export reserve on 17 October 2026.
Only the separately reviewed human release can dispatch these private seams.
Only the approved global TimeLimit changes; formulation and residual evaluation do not.
"""

from __future__ import annotations

import os
import platform
import re
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

from scripts import mvp2_s2_h300_runtime as old
from scripts import mvp2_s2_p4_diagnostics as diag

p, d, c = old.products, old.d, old.c
ROOT = Path(__file__).resolve().parents[1]
CLAIM = ".mvp2-s2-p4-terminal-v1"
CONTRACT = {
    "schema_version": "s2-p4-shared-return-export-v1",
    "native_time_limit_seconds": 3600,
    "build_seconds": 900,
    "return_excess_and_export_seconds": 900,
    "cleanup_seconds": 300,
    "arm_seconds": 5700,
    "minimum_ledger_seconds": 30600,
    "block_seconds": 43200,
    "sample_cap": 1200,
    "stop_reserve_inside_arm_seconds": 30,
    "production_isolation_certified": False,
    "repeats_admitted": False,
}


class SharedDeadlines:
    """Observed monotonic windows; native return excess borrows export time only."""

    def __init__(self, started, block_deadline):
        for value in (started, block_deadline):
            d.number(value, "monotonic bound")
        self.started = self.last = self.phase_started = started
        self.hard = min(started + 5700, block_deadline)
        self.seen, self.transitions = [], []
        self.aborted = False
        self.optimization_started = self.export_deadline = None

    def observe(self, now, events, *, aborted=False):
        d.number(now, "monotonic observation")
        d.require(now >= self.last, "Monotonic clock rollback.")
        self.last = now
        d.require(type(aborted) is bool and (not self.aborted or aborted), "Cleanup rollback.")
        d.require(not self.aborted or events == self.seen, "Phase after aborted cleanup.")
        d.require(
            type(events) is list
            and events == list(c.PHASES[: len(events)])
            and len(events) <= 4
            and events[: len(self.seen)] == self.seen,
            "Phase rollback/order drift.",
        )
        if now >= self.hard:
            return "child_or_block_watchdog"
        index = 3 if self.aborted else max(0, len(self.seen) - 1)
        if index == 0 and now - self.phase_started >= 900:
            return "build_watchdog"
        if index == 1 and now >= self.optimization_started + 4500:
            return "return_export_watchdog"
        if index == 2 and now >= self.export_deadline:
            return "return_export_watchdog"
        if index == 3 and now - self.phase_started >= 300:
            return "cleanup_watchdog"
        if len(events) > len(self.seen):
            for phase in events[len(self.seen) :]:
                self.transitions.append({"phase": phase, "observed_seconds": now - self.started})
                if phase == "optimization":
                    self.optimization_started = now
                if phase == "export_validation":
                    self.export_deadline = min(now + 900, self.optimization_started + 4500)
                if phase != "build":
                    self.phase_started = now
            self.seen = list(events)
        if aborted and not self.aborted:
            d.require(1 <= len(events) <= 3, "Invalid failure cleanup.")
            self.aborted, self.phase_started = True, now
            self.transitions.append(
                {"phase": "cleanup_after_failure", "observed_seconds": now - self.started}
            )
        return None


def worker_identity(plan, threads, step):
    return diag.binding(
        {
            "source_commit": plan["preparation"]["source_commit"],
            "plan_sha256": d.digest(plan),
            "threads": threads,
            "step_id": step,
        }
    )


def solver_profile(threads):
    """Approved sole scientific-setting change; no per-priority TimeLimit reset."""
    return replace(old.native.solver_profile(threads), time_limit=3600)


def preparation(source, runtime_hash, input_hash, protected_hash):
    value = old.entry.preparation(source, runtime_hash, input_hash, protected_hash)
    value["schema_version"] = "s2-p4-terminal-preparation-v2"
    value["allocation"]["walltime_seconds"] = 43200
    value["budget"]["optimization_seconds"] = 3600
    value["budget"]["child_watchdog_seconds"] = 5700
    value["budget_ledger"] = {
        "child_seconds": 5700,
        "minimum_block_seconds": 30600,
        "reserved_block_seconds": 43200,
        "production_admitted": False,
        "repeats_admitted": False,
    }
    for arm in value["arms"]:
        arm["solver"]["time_limit"] = 3600
    return value


def reference_plan(plan):
    """Projection only for old input/source checks, NEVER an execution profile."""
    reference = dict(plan)
    info = plan["preparation"]
    reference["schema_version"] = "s2-h300-academic-plan-v1"
    reference["preparation"] = old.entry.preparation(
        info["source_commit"],
        info["runtime_sha256"],
        info["input_sha256"],
        info["protected_source_sha256"],
    )
    return reference


def validate(plan):
    old._validate(reference_plan(plan))
    info = plan["preparation"]
    d.require(
        plan["schema_version"] == "s2-p4-terminal-plan-v2"
        and c.encoded(info)
        == c.encoded(
            preparation(
                info["source_commit"],
                info["runtime_sha256"],
                info["input_sha256"],
                info["protected_source_sha256"],
            )
        ),
        "New 3600-second plan/ledger drift.",
    )
    return plan


def _plan(commit, root, p3, reference, **kwargs):
    plan = old._plan(commit, root, p3, reference, **kwargs)
    info = plan["preparation"]
    plan["schema_version"] = "s2-p4-terminal-plan-v2"
    plan["preparation"] = preparation(
        commit, info["runtime_sha256"], info["input_sha256"], info["protected_source_sha256"]
    )
    return validate(plan)


def _recheck(plan, root, reference, **kwargs):
    validate(plan)
    return old._recheck(reference_plan(plan), root, reference, **kwargs)


class Native3600Hooks(old.native.NativeHooks):
    def __call__(self, phase, model, grb):
        if phase != "native_ready":
            return super().__call__(phase, model, grb)
        d.require(not self.ready and self.journal.index == 1, "Repeated native readiness.")
        for name, value in {
            "TimeLimit": 3600,
            "Threads": self.solver.threads,
            "Seed": 42,
            "MIPGap": 0.1,
            "SoftMemLimit": 128,
            "NumericFocus": 1,
        }.items():
            seen = getattr(model.Params, name)
            d.require(
                type(seen) in (int, float) and seen == value,
                "Effective native parameter drift: " + name,
            )
        self.ready = True


def _native(
    target,
    plan,
    threads,
    reference,
    remaining,
    *,
    recheck=_recheck,
    check=diag.license_probe.check_file,
    clock=time.monotonic,
):
    """Real original backend seam with explicit worker license selection and safe hooks."""
    directory = target / "diagnostics"
    directory.mkdir()
    ident = worker_identity(
        plan,
        threads,
        os.environ.get("SLURM_JOB_ID", "") + "." + os.environ.get("SLURM_STEP_ID", ""),
    )
    diag._select_worker_license(directory, ident, check=check)
    journal = c.PhaseJournal(
        target / "native", d.digest({"plan": d.digest(plan), "threads": threads})
    )
    journal.enter("build")
    hooks = diag.NativeSeams(
        directory,
        ident,
        journal,
        solver_profile(threads),
        clock=clock,
        profile_factory=solver_profile,
        hooks_factory=Native3600Hooks,
    )

    def cleanup():
        if journal.index == 3:
            journal.enter("cleanup")
        elif journal.index < 3 and not (journal.directory / "failure-cleanup.json").exists():
            journal.failure_cleanup()

    try:
        data, config = recheck(plan, ROOT, reference)
        anchor = old.partial.anchor(
            data,
            config,
            source_commit=plan["preparation"]["source_commit"],
            runtime_sha256=d.digest(plan["runtime"]),
            workbook_sha256=d.WORKBOOK,
            threads=threads,
        )
        from src.logic.optimization_gurobipy_stochastic import solve_stochastic_model_gurobipy

        result = solve_stochastic_model_gurobipy(
            data,
            config,
            solver_profile(threads),
            native_phase_hook=hooks,
            _on_failure_cleanup=cleanup,
        )
        terminal = hooks.terminal
        d.require(terminal is not None and journal.index == 3, "Missing native terminal/phases.")
        d.require(
            result.metadata.get("solution_count") == terminal["solution_count"]
            and result.metadata.get("gurobi_status_code") == terminal["native_status_code"]
            and result.metadata.get("gurobi_status_name") == terminal["native_status_name"],
            "Live terminal/result drift.",
        )
        lifecycle = result.metadata.get("native_model_lifecycle")
        d.require(
            isinstance(lifecycle, list)
            and len(lifecycle) == 1
            and lifecycle[0]["backend"] == "gurobipy"
            and lifecycle[0]["status"] == "disposed",
            "Native disposal.",
        )
        report = p.export(
            journal.directory / "products", result, data, config, anchor, remaining=remaining
        )
        p.publish(journal.directory / "root-resources.json", old.worker_tools.resources())
        return report
    except BaseException as error:
        p.publish(
            journal.directory / "failure.json",
            {"exception_type": type(error).__name__, "after_phase_count": journal.index},
        )
        raise
    finally:
        cleanup()


def dispatch_argv(action, target):
    d.require(action in {"worker", "review"}, "Private dispatch scope.")
    code = (
        "import sys;sys.dont_write_bytecode=True;sys.path.insert(0,"
        + repr(str(ROOT))
        + ");from scripts.mvp2_s2_p4_terminal_runtime import _dispatch;_dispatch("
        + repr(action)
        + ","
        + repr(str(target))
        + ")"
    )
    return [sys.executable, "-B", "-I", "-c", code]


def _dispatch(action, path):
    target = p.safe(path)
    claim = target.parent.parent
    d.require(claim.name == CLAIM and target.parent.name == "arms", "Dedicated worker claim.")
    from scripts import mvp2_s2_p4_terminal_release as release

    plan, _sealed = release.load_claim(claim)
    release.verify_origin(claim, plan)
    job = old.products.read(claim / "job.json")["job_id"]
    origin, ticket = p.read(claim / "origin.json"), p.read(target / "ticket.json")
    d.require(target.name == f"t{ticket['threads']}", "Worker ticket/thread path.")
    if action == "worker":
        return _worker(
            target,
            plan,
            ticket["threads"],
            job,
            ticket["environment"],
            origin["reference"],
            ticket["remaining"],
            execute=_native,
        )
    d.require(action == "review", "Private action denied.")
    data, config = _recheck(plan, ROOT, origin["reference"])
    anchor = old.partial.anchor(
        data,
        config,
        source_commit=plan["preparation"]["source_commit"],
        runtime_sha256=d.digest(plan["runtime"]),
        workbook_sha256=d.WORKBOOK,
        threads=ticket["threads"],
    )
    report = p.review(target / "native/products", data, config, anchor)
    p.publish(target / "independent.json", report)
    return report


def _supervise(
    process,
    target,
    plan,
    threads,
    job,
    environment,
    hard,
    *,
    command=old.source.command,
    clock=time.monotonic,
    pause=time.sleep,
    sample=None,
):
    """Same exact-step control/resource scope, with approved shared-reserve guard."""
    if sample is None:
        from src.logic.resource_telemetry import process_observation

        sample = process_observation
    started = clock()
    guard = SharedDeadlines(started, hard - 30)
    identity = d.digest({"plan": d.digest(plan), "threads": threads})
    step, pid, reason, reaped = None, None, None, False
    samples, last_sample, term, kill = [], started - 5, None, None
    try:
        while True:
            now = clock()
            if step is None and (target / "worker-start.json").exists():
                bind = p.read(target / "worker-start.json")
                d.require(
                    bind["plan_sha256"] == d.digest(plan)
                    and bind["uid"] == os.getuid()
                    and bind["threads"] == threads
                    and bind["environment_sha256"] == d.digest(environment)
                    and re.fullmatch(re.escape(job) + r"\.(?:0|[1-9][0-9]*)", bind["step_id"]),
                    "Worker binding drift.",
                )
                step, pid = bind["step_id"], bind["pid"]
                d.require(type(pid) is int and pid > 1, "Worker PID.")
                fields = old.scheduler.fields(
                    old.query(["scontrol", "-o", "show", "step", step], command=command)
                )
                d.require(
                    fields.get("StepId") == step
                    and fields.get("UserId") == str(os.getuid())
                    and fields.get("State") == "RUNNING"
                    and fields.get("Nodes") == "1"
                    and fields.get("NodeList") == environment["allocation"]["node"]
                    and fields.get("Tasks") == "1"
                    and fields.get("CPUs") == "16",
                    "Actual worker step drift.",
                )
                p.publish(
                    target / "release.json",
                    {
                        "plan_sha256": d.digest(plan),
                        "step_id": step,
                        "environment_sha256": d.digest(environment),
                    },
                )
            events = c.phase_events(target / "native", identity)
            aborted = c.failure_cleanup_event(target / "native", identity, events)
            reason = guard.observe(now, events, aborted=aborted)
            if reason:
                break
            if pid is not None and now - last_sample >= 5:
                d.require(len(samples) < CONTRACT["sample_cap"], "Resource sample cap.")
                try:
                    observation = sample(pid)
                except Exception as error:
                    observation = {"observation_errors": type(error).__name__}
                samples.append(
                    {
                        "seconds": now - started,
                        "phase": events[-1] if events else None,
                        "scope": "sampled_live_worker_tree_batch_cgroup",
                        **observation,
                    }
                )
                last_sample = now
            if process.poll() is not None:
                if step is None or events != list(c.PHASES) or aborted or process.returncode != 0:
                    reason = "worker_exit_unqualified"
                else:
                    records = diag.catalogue(
                        target / "diagnostics",
                        worker_identity(plan, threads, step),
                        profile_factory=solver_profile,
                    )
                    d.require(
                        records["native_return_observed"], "Missing native return diagnostic."
                    )
                    d.require(
                        p.read(target / "diagnostics/native-return.json")["terminal_sha256"]
                        == d.digest(p.read(target / "native/native-terminal.json")),
                        "Live diagnostic terminal binding.",
                    )
                break
            if step is None and now - started >= 30:
                reason = "unbound_startup"
                break
            pause(0.1)
    except BaseException as error:
        reason = type(error).__name__
    finally:
        if reason is not None and step is not None:
            try:
                term, _ = command(["scancel", "--signal=TERM", step], timeout=5, limit=1024)
            except Exception as error:
                term = {"status": "command_exception", "error_kind": type(error).__name__}
            pause(min(5, max(0, hard - clock() - 15)))
            try:
                kill, _ = command(["scancel", "--signal=KILL", step], timeout=5, limit=1024)
            except Exception as error:
                kill = {"status": "command_exception", "error_kind": type(error).__name__}
        elif reason is not None and process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=max(0.1, min(15, hard - clock() - 5)))
            reaped = True
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
            reaped, reason = True, reason or "local_client_timeout"
        attempt = {
            "plan_sha256": d.digest(plan),
            "threads": threads,
            "step_id": step,
            "stop_reason": reason,
            "term": term,
            "kill": kill,
            "local_client_reaped": reaped,
            "return_code": process.returncode,
            "elapsed_seconds": clock() - started,
            "observed_transitions": guard.transitions,
            "global_cleanup_proven": False,
            "enforcement_contract_sha256": d.digest(CONTRACT),
        }
        p.publish(target / "attempt.json", attempt)
        p.publish(
            target / "resources.json",
            {
                "samples": samples,
                "max_gap_seconds": max(
                    [
                        b["seconds"] - a["seconds"]
                        for a, b in zip(samples, samples[1:], strict=False)
                    ]
                    or [None]
                ),
                "continuous_coverage": False,
                "lifetime_tree_cpu_seconds": None,
                "first_sample_delay_seconds": samples[0]["seconds"] if samples else None,
                "last_sample_to_exit_seconds": clock() - started - samples[-1]["seconds"]
                if samples
                else None,
            },
        )
    return attempt


def _arm(
    target,
    plan,
    threads,
    job,
    environment,
    reference,
    remaining,
    hard,
    *,
    popen=subprocess.Popen,
    command=old.source.command,
    supervise=_supervise,
    dispatch=None,
):
    dispatch = dispatch_argv if dispatch is None else dispatch
    target.mkdir()
    p.publish(
        target / "ticket.json",
        {"threads": threads, "environment": environment, "remaining": remaining},
    )
    argv = [
        "srun",
        "--exclusive",
        "--exact",
        "--nodes=1",
        "--ntasks=1",
        "--cpus-per-task=16",
        "--cpu-bind=threads",
        "--time=01:35:00",
        "--kill-on-bad-exit=1",
        "--export=ALL",
        *dispatch("worker", target),
    ]
    with (target / "worker.out").open("xb") as out, (target / "worker.err").open("xb") as err:
        process = popen(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err, shell=False)
        return supervise(process, target, plan, threads, job, environment, hard, command=command)


def _independent(arm, data, config, anchor, remaining, *, run=subprocess.run, dispatch=None):
    dispatch = dispatch_argv if dispatch is None else dispatch
    d.require(0 < remaining <= 900, "Total independent review budget.")
    with (arm / "review.out").open("xb") as out, (arm / "review.err").open("xb") as err:
        result = run(
            dispatch("review", arm),
            stdout=out,
            stderr=err,
            stdin=subprocess.DEVNULL,
            shell=False,
            timeout=remaining,
            check=False,
        )
    d.require(result.returncode == 0, "Independent review subprocess failed.")
    return p.read(arm / "independent.json")


def _worker(
    target,
    plan,
    threads,
    job,
    environment,
    reference,
    remaining,
    *,
    execute=_native,
    clock=time.monotonic,
    pause=time.sleep,
):
    validate(plan)
    d.require(type(threads) is int and threads in d.GRID, "Worker Threads.")
    step = os.environ.get("SLURM_STEP_ID", "")
    d.require(
        os.environ.get("SLURM_JOB_ID") == job and re.fullmatch(r"0|[1-9][0-9]*", step),
        "Worker numeric step binding.",
    )
    d.require(sorted(os.sched_getaffinity(0)) == environment["affinity"], "Worker affinity drift.")
    d.require(
        {k: os.environ.get(k) for k in old.ENVIRONMENT} == environment["native_thread_environment"],
        "Native environment drift.",
    )
    p.publish(
        target / "worker-start.json",
        {
            "plan_sha256": d.digest(plan),
            "step_id": job + "." + step,
            "pid": os.getpid(),
            "uid": os.getuid(),
            "threads": threads,
            "environment_sha256": d.digest(environment),
        },
    )
    deadline = clock() + 30
    while not (target / "release.json").exists():
        d.require(clock() < deadline, "Parent release timeout.")
        pause(0.05)
    d.require(
        p.read(target / "release.json")
        == {
            "plan_sha256": d.digest(plan),
            "step_id": job + "." + step,
            "environment_sha256": d.digest(environment),
        },
        "Parent release binding.",
    )
    return execute(target, plan, threads, reference, remaining)


def _environment(plan, job, *, command=old.source.command):
    text = old.query(["scontrol", "-o", "show", "job", job], command=command)
    observed = old.academic.allocation(
        text, job, os.getuid(), {"cpus": 16, "memory_mib": 196608, "wall_seconds": 43200}
    )
    affinity = sorted(os.sched_getaffinity(0))
    d.require(16 <= len(affinity) <= observed["allocated_cpus"], "Actual affinity pool.")
    topology = []
    for cpu in affinity:
        base = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
        topology.append(
            {
                "cpu": cpu,
                "package": (base / "physical_package_id").read_text().strip(),
                "core": (base / "core_id").read_text().strip(),
                "siblings": (base / "thread_siblings_list").read_text().strip(),
            }
        )
    return {
        "allocation": observed,
        "affinity": affinity,
        "topology": topology,
        "architecture": platform.machine(),
        "qos": old.scheduler.fields(text).get("QOS"),
        "native_thread_environment": {k: os.environ.get(k) for k in old.ENVIRONMENT},
        "runtime_sha256": d.digest(plan["runtime"]),
        "exclusive_node": False,
        "production_isolation_certified": False,
    }


def _batch(
    target,
    *,
    recheck=_recheck,
    environment=_environment,
    license_check=old._license,
    run_arm=_arm,
    independent=_independent,
    command=old.source.command,
    clock=time.monotonic,
    export_limit=None,
    allocation_deadline=None,
):
    target = p.safe(target)
    plan = validate(p.read(target / "plan.json"))
    ack_deadline = clock() + 30
    while not (target / "job.json").exists():
        d.require(clock() < ack_deadline, "Acknowledgement not published; no worker launched.")
        time.sleep(0.05)
    job = p.read(target / "job.json")["job_id"]
    d.require(os.environ.get("SLURM_JOB_ID") == job, "Batch job binding.")
    origin = p.read(target / "origin.json")
    started = clock()
    block_end, audit_remaining = started + 43200, 900
    if allocation_deadline is not None:
        d.number(allocation_deadline, "Absolute allocation deadline")
        block_end = min(block_end, allocation_deadline)
    export_limit = p.LIMIT if export_limit is None else export_limit
    d.require(
        type(export_limit) is int and p.LIMIT <= export_limit <= 1024**3,
        "Prospective transfer envelope.",
    )
    arms, stopped, env, capability = [], None, None, None
    try:
        d.require(
            origin["python"] == sys.executable and Path(origin["root"]) == ROOT,
            "Executing source origin.",
        )
        data, config = recheck(plan, ROOT, origin["reference"])
        env = environment(plan, job, command=command)
        capability = license_check()
        d.require(clock() - started < 600, "Fresh admission budget exhausted.")
        (target / "arms").mkdir()
        for index, threads in enumerate(d.ORDER):
            d.require(
                clock() + 5700 + audit_remaining + 600 <= block_end, "Insufficient arm headroom."
            )
            recheck(plan, ROOT, origin["reference"])
            d.require(environment(plan, job, command=command) == env, "Nonhomogeneous allocation.")
            d.require(clock() + 5700 + audit_remaining + 600 <= block_end, "Post-check headroom.")
            path = target / "arms" / f"t{threads}"
            remaining = min(
                p.LIMIT, export_limit - sum(x.stat().st_size + 1024 for x in target.rglob("*.json"))
            )
            arms.append({"threads": threads, "attempt": None, "review": None})
            attempt = run_arm(
                path,
                plan,
                threads,
                job,
                env,
                origin["reference"],
                remaining,
                min(clock() + 5700, block_end - audit_remaining - 600),
                command=command,
            )
            arms[-1]["attempt"] = attempt
            d.require(
                attempt["stop_reason"] is None
                and attempt["local_client_reaped"] is True
                and attempt["return_code"] == 0
                and attempt["step_id"] is not None,
                "Arm control not normally closed.",
            )
            rows = old.scheduler.accounting(
                old.query(
                    [
                        "sacct",
                        "-j",
                        attempt["step_id"],
                        "--noheader",
                        "--parsable2",
                        "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw",
                    ],
                    command=command,
                ),
                job,
            )
            d.require(
                set(rows) == {attempt["step_id"]}
                and rows[attempt["step_id"]]["state"] == "COMPLETED"
                and rows[attempt["step_id"]]["exit_code"] == "0:0",
                "Step closure.",
            )
            anchor = old.partial.anchor(
                data,
                config,
                source_commit=plan["preparation"]["source_commit"],
                runtime_sha256=d.digest(plan["runtime"]),
                workbook_sha256=d.WORKBOOK,
                threads=threads,
            )
            audit_started = clock()
            report = independent(
                path, data, config, anchor, min(audit_remaining, block_end - clock() - 600)
            )
            audit_remaining -= clock() - audit_started
            d.require(audit_remaining > 0 and clock() + 600 <= block_end, "Total audit reserve.")
            d.require(
                report["classification"]["disposition"]
                in {"complete_accepted_hierarchy", "feasible_partial_hierarchy", "no_incumbent"},
                "Unclassifiable scientific evidence.",
            )
            d.require(
                p.read(path / "native/products/observation.json")["native_status"]
                in {"OPTIMAL", "TIME_LIMIT", "MEM_LIMIT"},
                "Unexpected native interruption.",
            )
            arms[-1].update(review=report, index=index)
    except BaseException as error:
        stopped = type(error).__name__
    value = {
        "schema_version": "s2-p4-terminal-block-v2",
        "plan_sha256": d.digest(plan),
        "job_id": job,
        "environment": env,
        "license": capability,
        "arms": arms,
        "unrun": list(d.ORDER[len(arms) :]),
        "stop_reason": stopped,
        "elapsed_seconds": clock() - started,
        "h300_execution_admitted": False,
        "production_isolation_certified": False,
        "repeats_admitted": False,
    }
    p.publish(target / "batch.json", value)
    return value


def _collect(
    target,
    expected_plan,
    job,
    *,
    command=old.source.command,
    recheck=_recheck,
    reviewer=None,
    pack=None,
    inventory=None,
    unpack=None,
):
    """Fresh vector validation on NPAD; immutable portable evidence of all terminal outcomes."""
    target = p.safe(target)
    reviewer = p.review if reviewer is None else reviewer
    pack = p.pack if pack is None else pack
    inventory = p.inventory if inventory is None else inventory
    unpack = p.unpack_review if unpack is None else unpack
    plan = validate(p.read(target / "plan.json"))
    d.require(
        d.digest(plan) == expected_plan
        and p.read(target / "job.json") == {"job_id": job, "plan_sha256": expected_plan},
        "External collection anchors.",
    )
    missing_batch = not (target / "batch.json").exists()
    batch = (
        p.read(target / "batch.json")
        if not missing_batch
        else {
            "schema_version": "s2-p4-terminal-block-v2",
            "plan_sha256": expected_plan,
            "job_id": job,
            "arms": [],
            "unrun": [],
            "unaccounted": list(d.ORDER),
            "stop_reason": "missing_batch_receipt",
            "environment": None,
            "h300_execution_admitted": False,
            "repeats_admitted": False,
        }
    )
    d.require(
        batch["plan_sha256"] == expected_plan
        and batch["job_id"] == job
        and [x["threads"] for x in batch["arms"]] == list(d.ORDER[: len(batch["arms"])])
        and (
            (
                batch["stop_reason"] == "missing_batch_receipt"
                and batch["arms"] == []
                and batch["unrun"] == []
                and batch.get("unaccounted") == list(d.ORDER)
            )
            or batch["unrun"] == list(d.ORDER[len(batch["arms"]) :])
        ),
        "Block prefix/unrun binding.",
    )
    steps = [
        x["attempt"]["step_id"]
        for x in batch["arms"]
        if x["attempt"] is not None and x["attempt"]["step_id"]
    ]
    raw = old.query(
        [
            "sacct",
            "-j",
            job,
            "--noheader",
            "--parsable2",
            "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw",
        ],
        command=command,
    )
    accounting_error = None
    try:
        rows = old.accounting(raw, job, steps)
    except ValueError:
        rows = {}
        for line in raw.strip().splitlines():
            parsed = old.scheduler.accounting(line, job)
            d.require(not rows.keys() & parsed.keys(), "Duplicate forensic accounting.")
            rows.update(parsed)
        d.require(
            {job, job + ".batch", job + ".extern"} <= rows.keys()
            and all(x["state"] in old.scheduler.TERMINAL for x in rows.values()),
            "Accounting not terminal.",
        )
        accounting_error = "unexpected_or_missing_step_accounting"
    if missing_batch:
        p.publish(target / "batch.json", batch)
    try:
        text = old.query(
            [
                "sacct",
                "-j",
                job,
                "--noheader",
                "--parsable2",
                "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw,TotalCPU,MaxRSS,AllocCPUS,ReqMem",
            ],
            command=command,
        )
        resources = {"rows": old.resource_accounting(text, rows), "error_kind": None}
    except Exception as error:
        resources = {"rows": None, "error_kind": type(error).__name__}
    validation_error, reviewed = None, []
    try:
        data, config = recheck(plan, ROOT, p.read(target / "origin.json")["reference"])
    except Exception as error:
        validation_error = type(error).__name__
    for item in batch["arms"]:
        path = target / "arms" / f"t{item['threads']}"
        attempt = p.read(path / "attempt.json") if (path / "attempt.json").exists() else None
        d.require(attempt == item["attempt"], "Parent attempt drift.")
        report = None
        if item["review"] is not None and validation_error is None and accounting_error is None:
            try:
                anchor = old.partial.anchor(
                    data,
                    config,
                    source_commit=plan["preparation"]["source_commit"],
                    runtime_sha256=d.digest(plan["runtime"]),
                    workbook_sha256=d.WORKBOOK,
                    threads=item["threads"],
                )
                report = reviewer(path / "native/products", data, config, anchor)
                d.require(
                    report == item["review"]
                    and attempt["stop_reason"] is None
                    and attempt["local_client_reaped"] is True
                    and attempt["return_code"] == 0
                    and rows[attempt["step_id"]]["state"] == "COMPLETED"
                    and rows[attempt["step_id"]]["exit_code"] == "0:0",
                    "Vector/control replay drift.",
                )
            except Exception as error:
                validation_error, report = type(error).__name__, None
        reviewed.append({"threads": item["threads"], "review": report})
    complete = (
        accounting_error is None
        and validation_error is None
        and len(reviewed) == 5
        and all(x["review"] is not None for x in reviewed)
        and batch["stop_reason"] is None
        and not batch["unrun"]
        and all(
            rows[k]["state"] == "COMPLETED" and rows[k]["exit_code"] == "0:0"
            for k in (job, job + ".batch", job + ".extern")
        )
    )
    report = {
        "schema_version": "s2-p4-terminal-review-v2",
        "plan_sha256": expected_plan,
        "job_id": job,
        "status": "five_arms_accounted_not_s2_closure" if complete else "forensic_partial_block",
        "arms": reviewed,
        "unrun": batch["unrun"],
        "unaccounted": batch.get("unaccounted", []),
        "accounting_error": accounting_error,
        "validation_error": validation_error,
        "scientific_configuration_selected": False,
        "h300_execution_admitted": False,
        "repeats_admitted": False,
        "production_isolation_certified": False,
    }
    for name, value in (
        ("accounting.json", {"raw": raw, "rows": rows}),
        ("scheduler-resources.json", resources),
        ("review.json", report),
    ):
        if (target / name).exists():
            d.require(p.read(target / name) == value, "Immutable collection cache drift.")
        else:
            p.publish(target / name, value)
    archive = target / "s2-h300-academic-evidence.tar.gz"
    if archive.exists():
        transfer = p.read(target / "transfer.json")
        unpack(archive, transfer["sha256"], transfer["files"])
        d.require(transfer["files"] == inventory(target), "Cached inventory drift.")
    else:
        checksum, files = pack(target, archive)
        p.publish(
            target / "transfer.json",
            {"sha256": checksum, "files": files, "plan_sha256": expected_plan},
        )
        unpack(archive, checksum, files)
    return report
