"""Complete P4 transport seams under a CLOSED public operational boundary.

Private functions are qualified using injected local doubles. No CLI switch,
certificate, environment variable or JSON acceptance flag can admit execution.
Human admission requires a separately reviewed release boundary, not import of
these private functions on NPAD. Old claims and protocols are never reused.
"""

from __future__ import annotations

import argparse
import os
import platform
import re
import shlex
import subprocess
import sys
import tarfile
import tempfile
import time
from dataclasses import asdict
from pathlib import Path

from scripts import mvp2_h300_controls as c
from scripts import mvp2_h300_native_worker as native
from scripts import mvp2_h300_partial as partial
from scripts import mvp2_h300_thread_contract as d
from scripts import mvp2_s2_academic as academic
from scripts import mvp2_s2_academic_worker as worker_tools
from scripts import mvp2_s2_allocation_diagnostic as source
from scripts import mvp2_s2_batch_adapter as scheduler
from scripts import mvp2_s2_h300_academic as entry
from scripts import mvp2_s2_h300_products as products

ROOT = Path(__file__).resolve().parents[1]
ENTRY = "scripts/mvp2_s2_h300_runtime.py"
CLAIM = ".mvp2-s2-h300-academic-p4-v1"
REFERENCE = "348c4c08c2c9e906cbd3a28df7753577ebed3cac30702aae30dfb8ce2ad25694"
ENVIRONMENT = ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")


def _p3_files(archive):
    entry.p3_entry(archive)
    d.require(products.sha_file(archive) == entry.P3["archive"], "P3 archive changed.")
    with tarfile.open(archive, "r:gz") as stream:
        p = c.decode_json(stream.extractfile("plan.json").read())
    d.require(
        d.digest(p) == entry.P3["plan"] and p["source_commit"] == entry.P3["source"],
        "P3 source inventory anchor.",
    )
    return p["files"]


def _input(reference):
    """Fresh exact workbook/manifest/dimensions, with no solver construction."""
    from src.logic.excel_loader import load_model_data_from_excel
    from src.logic.experiment_runner import (
        _data_signature,
        build_model_audit,
        estimate_model_size,
        load_experiment_manifest,
    )
    from src.logic.mathematical_contract import prepare_model_data
    from src.logic.run_integrity import scientific_identity

    d.require(products.sha_file(reference) == REFERENCE, "Reference manifest drift.")
    spec = load_experiment_manifest(reference).experiments[2]
    d.require(products.sha_file(spec.workbook) == d.WORKBOOK, "Workbook drift.")
    d.require(
        spec.model.mode == "sto"
        and spec.model.objective_policy == "lexicographic"
        and spec.model.use_direct_origin_customer is False
        and spec.calculate_evpi_vss is False
        and spec.resume is False,
        "Scientific mode/resume/direct-arc drift.",
    )
    data = prepare_model_data(load_model_data_from_excel(spec.workbook, spec.loader), spec.model)
    expected = products.read(ROOT / "docs/mvp2_h300_input_size_review.json")
    estimate = asdict(estimate_model_size(data, spec.model))
    counts = _data_signature(data)["counts"]
    d.require(
        all(estimate[k] == v for k, v in expected["snapshot_fields"].items())
        and all(counts[k] == v for k, v in expected["counts"].items()),
        "Fresh input dimensions/routes drift.",
    )
    # Match historical JSON formatting exactly; do not relabel that old receipt.
    import json

    audit = (
        json.dumps(
            build_model_audit(data, spec.model), ensure_ascii=False, indent=2, sort_keys=True
        )
        + "\n"
    ).encode()
    d.require(
        academic.sha(audit) == expected["audit_sha256"]["model_audit.json"],
        "Fresh model audit drift.",
    )
    from src.logic.interhub_connectivity import write_interhub_audit

    # Reuse the original writer, including its summary projection/CSV ordering.
    # Hashing the full metadata dictionary would NOT reproduce the frozen audits.
    with tempfile.TemporaryDirectory(prefix="p4-input-audit-") as temporary:
        write_interhub_audit(data.metadata["interhub_connectivity"], temporary)
        for name, digest in expected["audit_sha256"].items():
            if name != "model_audit.json":
                d.require(
                    products.sha_file(Path(temporary) / name) == digest,
                    "Fresh connectivity audit drift.",
                )
    identity = {
        "workbook_sha256": d.WORKBOOK,
        "reference_sha256": REFERENCE,
        "data_sha256": scientific_identity(data),
        "config_sha256": scientific_identity(spec.model),
        "counts": {k: counts[k] for k in expected["counts"]},
        "size": {k: estimate[k] for k in expected["snapshot_fields"]},
    }
    return data, spec.model, identity


def _plan(
    commit, root, p3, reference, *, files=source.source_files, runtime=academic.runtime, load=_input
):
    original = _p3_files(p3)
    current = files(root, commit)
    protected = entry.source_parity(root, original)
    runtime_record = runtime()
    d.require(
        runtime_record["python_version"] == "3.13.15"
        and runtime_record["distributions"].get("gurobipy") == "13.0.3",
        "Unqualified native runtime.",
    )
    _data, _config, identity = load(reference)
    preparation = entry.preparation(
        commit, d.digest(runtime_record), d.digest(identity), d.digest(protected)
    )
    return {
        "schema_version": "s2-h300-academic-plan-v1",
        "preparation": preparation,
        "files": current,
        "runtime": runtime_record,
        "input": identity,
        "protected": protected,
        "export_limit_bytes": products.LIMIT,
        "h300_execution_admitted": False,
        "repeats_admitted": False,
    }


def _validate(p):
    d.require(
        set(p)
        == {
            "schema_version",
            "preparation",
            "files",
            "runtime",
            "input",
            "protected",
            "export_limit_bytes",
            "h300_execution_admitted",
            "repeats_admitted",
        },
        "Plan schema.",
    )
    entry.validate_preparation(p["preparation"])
    d.require(
        p["schema_version"] == "s2-h300-academic-plan-v1"
        and p["h300_execution_admitted"] is False
        and p["repeats_admitted"] is False
        and type(p["export_limit_bytes"]) is int
        and p["export_limit_bytes"] == products.LIMIT
        and d.digest(p["runtime"]) == p["preparation"]["runtime_sha256"]
        and d.digest(p["input"]) == p["preparation"]["input_sha256"]
        and d.digest(p["protected"]) == p["preparation"]["protected_source_sha256"],
        "Plan identities/permissions.",
    )
    d.require(
        p["input"]["workbook_sha256"] == d.WORKBOOK and p["input"]["reference_sha256"] == REFERENCE,
        "Input anchors.",
    )
    for name, digest in p["files"].items():
        d.require(
            name
            and not Path(name).is_absolute()
            and ".." not in Path(name).parts
            and "\\" not in name,
            "Source inventory path.",
        )
        entry.require_hash(digest)
    d.require(
        ENTRY in p["files"] and all(p["files"].get(k) == v for k, v in p["protected"].items()),
        "Protected inventory.",
    )
    return p


def _recheck(p, root, reference, *, runtime=academic.runtime, load=_input):
    _validate(p)
    source.verify_tree(root, p["files"])
    d.require(runtime() == p["runtime"], "Runtime drift.")
    data, config, identity = load(reference)
    d.require(identity == p["input"], "Fresh scientific input drift.")
    return data, config


def query(argv, *, command=source.command):
    meta, raw = command(argv, timeout=5, limit=65536)
    d.require(meta["status"] == "complete" and meta["returncode"] == 0, "Scheduler query.")
    return raw.decode("ascii")


def accounting(text, job, steps, *, terminal=True):
    """Five steps plus root/batch/extern; retain exact cancellation semantics."""
    d.require(
        re.fullmatch(r"[1-9][0-9]*", job) and len(steps) <= 5 and len(set(steps)) == len(steps),
        "Accounting scope.",
    )
    rows = {}
    for line in text.strip().splitlines():
        row = scheduler.accounting(line, job)
        d.require(not rows.keys() & row.keys(), "Duplicate accounting row.")
        rows.update(row)
    expected = {job, job + ".batch", job + ".extern", *steps}
    d.require(set(rows) == expected, "Missing/unexpected accounting row.")
    if terminal:
        d.require(
            all(x["state"] in scheduler.TERMINAL for x in rows.values()), "Accounting not terminal."
        )
    return rows


def resource_accounting(text, expected):
    """Keep scheduler CPU/RSS strings and scopes; blank is unknown, not zero."""
    found = {}
    d.require(type(text) is str and len(text) <= 65536, "Resource accounting bound.")
    for line in text.strip().splitlines():
        cells = line.split("|")
        d.require(
            len(cells) == 8 and cells[0] in expected and cells[0] not in found,
            "Resource accounting scope.",
        )
        ident, state, code, elapsed, cpu, rss, allocated, requested = cells
        normalized = scheduler.accounting("|".join(cells[:4]), ident.split(".")[0])[ident]
        d.require(normalized == expected[ident], "Resource/accounting identity drift.")
        d.require(not cpu or re.fullmatch(r"(?:[0-9]+-)?[0-9:.]+", cpu), "CPU time grammar.")
        d.require(not rss or re.fullmatch(r"[0-9]+(?:\.[0-9]+)?[KMGTPE]?", rss), "RSS grammar.")
        d.require(
            not allocated or re.fullmatch(r"[1-9][0-9]*", allocated), "Allocated CPU grammar."
        )
        d.require(
            not requested or re.fullmatch(r"[0-9]+(?:\.[0-9]+)?[KMGTPE]?[cn]?", requested),
            "Requested memory grammar.",
        )
        found[ident] = {
            "scope": "scheduler_job" if "." not in ident else "scheduler_step",
            "total_cpu_slurm": cpu or None,
            "max_rss_slurm": rss or None,
            "allocated_cpus": int(allocated) if allocated else None,
            "requested_memory_slurm": requested or None,
        }
    d.require(set(found) == set(expected), "Incomplete resource accounting.")
    return found


def _submit(target, p, root, reference, *, command=source.command):
    """Private one-shot seam. Public start NEVER invokes it in this release."""
    _validate(p)
    target = products.safe(target)
    d.require(target.name == CLAIM, "Dedicated claim required.")
    if target.exists():
        d.require(products.read(target / "plan.json") == p, "Existing claim plan drift.")
        return {"status": "existing_claim_collection_only", "submitted": False}
    target.mkdir()
    products.publish(target / "plan.json", p)
    products.publish(
        target / "origin.json",
        {"root": str(root), "reference": str(reference), "python": sys.executable},
    )
    argv = _dispatch_argv(root, "batch", target)
    with (target / "batch.sh").open("x", newline="\n") as stream:
        stream.write("#!/bin/sh\nexec " + shlex.join(argv) + "\n")
    submit = [
        "sbatch",
        "--parsable",
        "--partition=intel-256",
        "--account=sxdsouza",
        "--nodes=1",
        "--ntasks=1",
        "--cpus-per-task=16",
        "--mem=196608M",
        "--time=06:00:00",
        "--no-requeue",
        "--export=NONE",
        "--output=" + str(target / "slurm.out"),
        "--error=" + str(target / "slurm.err"),
        str(target / "batch.sh"),
    ]
    products.publish(
        target / "submission-intent.json",
        {"plan_sha256": d.digest(p), "argv_sha256": d.digest(submit)},
    )
    meta, raw = command(submit, timeout=30, limit=1024)
    products.publish(target / "submission-call.json", meta)
    d.require(
        meta["status"] == "complete"
        and meta["returncode"] == 0
        and re.fullmatch(rb"[1-9][0-9]*(?:;[A-Za-z0-9_-]+)?\n?", raw),
        "Unknown acknowledgement consumes slot; never retry.",
    )
    job = raw.decode().strip().split(";")[0]
    products.publish(target / "job.json", {"job_id": job, "plan_sha256": d.digest(p)})
    return {"status": "private_test_submission_receipt", "job_id": job, "submitted": True}


def _environment(p, job, *, command=source.command):
    text = query(["scontrol", "-o", "show", "job", job], command=command)
    observation = academic.allocation(
        text, job, os.getuid(), {"cpus": 16, "memory_mib": 196608, "wall_seconds": 21600}
    )
    affinity = sorted(os.sched_getaffinity(0))
    d.require(16 <= len(affinity) <= observation["allocated_cpus"], "Actual affinity pool.")
    # Read-only topology observation. Shared-node siblings are not exclusive cores.
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
    fields = scheduler.fields(text)
    return {
        "allocation": observation,
        "affinity": affinity,
        "topology": topology,
        "architecture": platform.machine(),
        "qos": fields.get("QOS"),
        "native_thread_environment": {k: os.environ.get(k) for k in ENVIRONMENT},
        "runtime_sha256": d.digest(p["runtime"]),
        "exclusive_node": False,
        "production_isolation_certified": False,
    }


def _dispatch_argv(root, action, target):
    d.require(action in {"batch", "worker", "review"}, "Private dispatch scope.")
    # Exact trusted code, not a shell. This argv can only be produced by the
    # private transport seams; public actions remain an unconditional deny.
    code = (
        "import sys;sys.dont_write_bytecode=True;sys.path.insert(0,"
        + repr(str(root))
        + ");from scripts.mvp2_s2_h300_runtime import _dispatch;"
        + "_dispatch("
        + repr(action)
        + ","
        + repr(str(target))
        + ")"
    )
    return [sys.executable, "-B", "-I", "-c", code]


def _dispatch(action, target):
    """Private transport entry, never selected by public CLI or an acceptance flag."""
    target = products.safe(target)
    if action == "batch":
        _batch(target)
    elif action in {"worker", "review"}:
        claim = target.parent.parent
        d.require(claim.name == CLAIM and target.parent.name == "arms", "Worker claim scope.")
        p = _validate(products.read(claim / "plan.json"))
        job = products.read(claim / "job.json")["job_id"]
        origin = products.read(claim / "origin.json")
        ticket = products.read(target / "ticket.json")
        if action == "worker":
            _worker(
                target,
                p,
                ticket["threads"],
                job,
                ticket["environment"],
                origin["reference"],
                ticket["remaining"],
            )
        else:
            data, config = _recheck(p, ROOT, origin["reference"])
            anchor = partial.anchor(
                data,
                config,
                source_commit=p["preparation"]["source_commit"],
                runtime_sha256=d.digest(p["runtime"]),
                workbook_sha256=d.WORKBOOK,
                threads=ticket["threads"],
            )
            report = products.review(target / "native/products", data, config, anchor)
            products.publish(target / "independent.json", report)
    else:
        raise ValueError("Unknown private dispatch.")


def _license():
    from scripts import probe_npad_gurobi_license as probe

    os.environ["GRB_LICENSE_FILE"] = probe.LICENSE_FILE
    value = probe.probe()
    d.require(
        value["status"] == "accepted" and value.get("gurobi_version") == [13, 0, 3],
        "Fresh native license/runtime rejected.",
    )
    return {k: value[k] for k in ("status", "gurobi_version")}


def _native(directory, p, threads, reference, remaining, *, recheck=_recheck):
    """Cold native integration using unchanged profile, hooks, disposal and evaluator."""
    identity = d.digest({"plan": d.digest(p), "threads": threads})
    journal = c.PhaseJournal(directory / "native", identity)
    journal.enter("build")  # Includes fresh workbook loading, not only model construction.
    hooks = native.NativeHooks(journal, native.solver_profile(threads))

    def cleanup():
        if journal.index == 3:
            journal.enter("cleanup")
        elif journal.index < 3 and not (journal.directory / "failure-cleanup.json").exists():
            journal.failure_cleanup()

    try:
        data, config = recheck(p, ROOT, reference)
        anchor = partial.anchor(
            data,
            config,
            source_commit=p["preparation"]["source_commit"],
            runtime_sha256=d.digest(p["runtime"]),
            workbook_sha256=d.WORKBOOK,
            threads=threads,
        )
        from src.logic.optimization_gurobipy_stochastic import solve_stochastic_model_gurobipy

        result = solve_stochastic_model_gurobipy(
            data,
            config,
            native.solver_profile(threads),
            native_phase_hook=hooks,
            _on_failure_cleanup=cleanup,
        )
        terminal = hooks.terminal
        d.require(terminal is not None and journal.index == 3, "Missing native phases.")
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
        report = products.export(
            journal.directory / "products", result, data, config, anchor, remaining=remaining
        )
        products.publish(journal.directory / "root-resources.json", worker_tools.resources())
        return report
    except BaseException as error:
        products.publish(
            journal.directory / "failure.json",
            {"exception_type": type(error).__name__, "after_phase_count": journal.index},
        )
        raise
    finally:
        cleanup()


def _worker(
    target,
    p,
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
    _validate(p)
    d.require(type(threads) is int and threads in d.GRID, "Worker Threads.")
    step = os.environ.get("SLURM_STEP_ID", "")
    d.require(
        os.environ.get("SLURM_JOB_ID") == job and re.fullmatch(r"0|[1-9][0-9]*", step),
        "Worker numeric step binding.",
    )
    d.require(sorted(os.sched_getaffinity(0)) == environment["affinity"], "Worker affinity drift.")
    d.require(
        {k: os.environ.get(k) for k in ENVIRONMENT} == environment["native_thread_environment"],
        "Worker native environment drift.",
    )
    products.publish(
        target / "worker-start.json",
        {
            "plan_sha256": d.digest(p),
            "step_id": job + "." + step,
            "pid": os.getpid(),
            "uid": os.getuid(),
            "threads": threads,
            "environment_sha256": d.digest(environment),
        },
    )
    end = clock() + 30
    while not (target / "release.json").exists():
        d.require(clock() < end, "Parent release timeout.")
        pause(0.05)
    release = products.read(target / "release.json")
    d.require(
        release
        == {
            "plan_sha256": d.digest(p),
            "step_id": job + "." + step,
            "environment_sha256": d.digest(environment),
        },
        "Release identity drift.",
    )
    return execute(target, p, threads, reference, remaining)


def _supervise(
    process,
    target,
    p,
    threads,
    job,
    environment,
    hard,
    *,
    command=source.command,
    clock=time.monotonic,
    pause=time.sleep,
    sample=None,
):
    """Exact numeric-step control; no job-wide cancellation or process-group proof."""
    if sample is None:
        from src.logic.resource_telemetry import process_observation

        sample = process_observation
    start = clock()
    guard = c.Deadlines(start, hard - 30)
    identity = d.digest({"plan": d.digest(p), "threads": threads})
    step, reason, reaped = None, None, False
    samples, last_sample, pid = [], start - 5, None
    term = kill = None
    try:
        while True:
            now = clock()
            if step is None and (target / "worker-start.json").exists():
                binding = products.read(target / "worker-start.json")
                d.require(
                    binding["plan_sha256"] == d.digest(p)
                    and binding["uid"] == os.getuid()
                    and binding["threads"] == threads
                    and binding["environment_sha256"] == d.digest(environment)
                    and re.fullmatch(re.escape(job) + r"\.(?:0|[1-9][0-9]*)", binding["step_id"]),
                    "Worker binding drift.",
                )
                step, pid = binding["step_id"], binding["pid"]
                d.require(type(pid) is int and pid > 1, "Worker PID.")
                observed = scheduler.fields(
                    query(["scontrol", "-o", "show", "step", step], command=command)
                )
                d.require(
                    observed.get("StepId") == step
                    and observed.get("UserId") == str(os.getuid())
                    and observed.get("State") == "RUNNING"
                    and observed.get("Nodes") == "1"
                    and observed.get("NodeList") == environment["allocation"]["node"]
                    and observed.get("Tasks") == "1"
                    and observed.get("CPUs") == "16",
                    "Actual worker step drift.",
                )
                products.publish(
                    target / "release.json",
                    {
                        "plan_sha256": d.digest(p),
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
                d.require(len(samples) < 800, "Resource sample cap.")
                try:
                    observation = sample(pid)
                except Exception as error:
                    observation = {"observation_errors": type(error).__name__}
                # Explicit scope: cgroup read belongs to the BATCH observer, not
                # necessarily the worker. Exited descendants' CPU is unavailable.
                samples.append(
                    {
                        "seconds": now - start,
                        "phase": events[-1] if events else None,
                        "scope": "sampled_live_worker_tree_batch_cgroup",
                        **observation,
                    }
                )
                last_sample = now
            if process.poll() is not None:
                if step is None or events != list(c.PHASES) or aborted or process.returncode != 0:
                    reason = "worker_exit_unqualified"
                break
            if step is None and now - start >= 30:
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
            process.terminate()  # Local srun only. Remote effect remains UNKNOWN.
        try:
            process.wait(timeout=max(0.1, min(15, hard - clock() - 5)))
            reaped = True
        except subprocess.TimeoutExpired:
            process.kill()  # Local srun only; unknown remote effects stop the block.
            process.wait(timeout=5)
            reaped = True
            reason = reason or "local_client_timeout"
        attempt = {
            "plan_sha256": d.digest(p),
            "threads": threads,
            "step_id": step,
            "stop_reason": reason,
            "term": term,
            "kill": kill,
            "local_client_reaped": reaped,
            "return_code": process.returncode,
            "elapsed_seconds": clock() - start,
            "observed_transitions": guard.transitions,
            "global_cleanup_proven": False,
        }
        products.publish(target / "attempt.json", attempt)
        products.publish(
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
                "last_sample_to_exit_seconds": clock() - start - samples[-1]["seconds"]
                if samples
                else None,
            },
        )
    return attempt


def _arm(
    target,
    p,
    threads,
    job,
    environment,
    reference,
    remaining,
    hard,
    *,
    popen=subprocess.Popen,
    command=source.command,
    supervise=_supervise,
):
    target.mkdir()
    products.publish(
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
        "--time=01:05:00",
        "--kill-on-bad-exit=1",
        "--export=ALL",
        *_dispatch_argv(ROOT, "worker", target),
    ]
    # All arms receive the SAME full affinity pool; only Gurobi Threads varies.
    # Logs remain private and outside the transfer allowlist.
    with (target / "worker.out").open("xb") as out, (target / "worker.err").open("xb") as err:
        process = popen(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err, shell=False)
        return supervise(process, target, p, threads, job, environment, hard, command=command)


def _batch(
    target,
    *,
    recheck=_recheck,
    environment=_environment,
    license_check=_license,
    run_arm=_arm,
    independent=None,
    command=source.command,
    clock=time.monotonic,
):
    """One serial block; unexpected effects stop, leaving an explicit unrun suffix."""
    target = products.safe(target)
    p = _validate(products.read(target / "plan.json"))
    ack_end = time.monotonic() + 30
    while not (target / "job.json").exists():
        d.require(time.monotonic() < ack_end, "Acknowledgement not published; no worker launched.")
        time.sleep(0.05)
    job = products.read(target / "job.json")["job_id"]
    d.require(os.environ.get("SLURM_JOB_ID") == job, "Batch job binding.")
    origin = products.read(target / "origin.json")
    started = clock()
    block_end = started + 21600
    audit_remaining = 900
    arms, stopped, env = [], None, None
    try:
        d.require(
            origin["python"] == sys.executable and Path(origin["root"]) == ROOT,
            "Executing source origin.",
        )
        data, config = recheck(p, ROOT, origin["reference"])
        env = environment(p, job, command=command)
        capability = license_check()
        d.require(clock() - started < 600, "Admission budget exhausted.")
        (target / "arms").mkdir()
        for index, threads in enumerate(d.ORDER):
            d.require(
                clock() + 3900 + 900 + 600 <= block_end,
                "Insufficient complete-arm/audit/terminal headroom.",
            )
            recheck(p, ROOT, origin["reference"])
            d.require(environment(p, job, command=command) == env, "Nonhomogeneous allocation.")
            d.require(clock() + 3900 + 1500 <= block_end, "Post-check remaining headroom.")
            arm = target / "arms" / f"t{threads}"
            remaining = products.LIMIT - sum(
                x.stat().st_size + 1024 for x in target.rglob("*.json")
            )
            arms.append({"threads": threads, "attempt": None, "review": None})
            attempt = run_arm(
                arm,
                p,
                threads,
                job,
                env,
                origin["reference"],
                remaining,
                min(clock() + 3900, block_end - 1500),
                command=command,
            )
            arms[-1]["attempt"] = attempt
            d.require(
                attempt["stop_reason"] is None
                and attempt["local_client_reaped"] is True
                and attempt["return_code"] == 0
                and attempt["step_id"] is not None,
                "Arm control/cleanup not normally closed.",
            )
            row = scheduler.accounting(
                query(
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
                set(row) == {attempt["step_id"]}
                and row[attempt["step_id"]]["state"] == "COMPLETED"
                and row[attempt["step_id"]]["exit_code"] == "0:0",
                "Step not closed.",
            )
            anchor = partial.anchor(
                data,
                config,
                source_commit=p["preparation"]["source_commit"],
                runtime_sha256=d.digest(p["runtime"]),
                workbook_sha256=d.WORKBOOK,
                threads=threads,
            )
            audit_started = clock()
            # Isolated trusted Python validator, not a solver or another Slurm
            # step. Enforce the TOTAL 900s block-audit allowance, not 900s per arm.
            if independent is None:
                report = _independent(arm, min(audit_remaining, block_end - clock() - 600))
            else:
                report = independent(arm, data, config, anchor, audit_remaining)
            audit_remaining -= clock() - audit_started
            d.require(
                audit_remaining > 0 and clock() + 600 <= block_end,
                "Independent review/terminal reserve exhausted.",
            )
            d.require(
                report["classification"]["disposition"]
                in {"complete_accepted_hierarchy", "feasible_partial_hierarchy", "no_incumbent"},
                "Arm scientific evidence not classifiable.",
            )
            observation = products.read(arm / "native/products/observation.json")
            d.require(
                observation["native_status"] in {"OPTIMAL", "TIME_LIMIT", "MEM_LIMIT"},
                "Unexpected native interruption.",
            )
            arms[-1]["review"] = report
            arms[-1]["index"] = index
    except BaseException as error:
        stopped = type(error).__name__
    value = {
        "schema_version": "s2-h300-academic-block-v1",
        "plan_sha256": d.digest(p),
        "job_id": job,
        "environment": env,
        "license": locals().get("capability"),
        "arms": arms,
        "unrun": list(d.ORDER[len(arms) :]),
        "stop_reason": stopped,
        "elapsed_seconds": clock() - started,
        "h300_execution_admitted": False,
        "production_isolation_certified": False,
        "repeats_admitted": False,
    }
    products.publish(target / "batch.json", value)
    return value


def _independent(arm, remaining, *, run=subprocess.run):
    d.require(0 < remaining <= 900, "Independent review budget exhausted.")
    with (arm / "review.out").open("xb") as out, (arm / "review.err").open("xb") as err:
        result = run(
            _dispatch_argv(ROOT, "review", arm),
            stdout=out,
            stderr=err,
            stdin=subprocess.DEVNULL,
            shell=False,
            timeout=remaining,
            check=False,
        )
    d.require(result.returncode == 0, "Independent review subprocess failed.")
    return products.read(arm / "independent.json")


def _collect(target, expected_plan, expected_job, *, command=source.command, recheck=_recheck):
    """Terminal forensic record plus fresh independent scientific replay."""
    target = products.safe(target)
    p = _validate(products.read(target / "plan.json"))
    d.require(
        d.digest(p) == expected_plan
        and products.read(target / "job.json")
        == {"job_id": expected_job, "plan_sha256": expected_plan},
        "External collection anchors.",
    )
    missing_batch = not (target / "batch.json").exists()
    if missing_batch:
        # A batch may fail before it publishes a receipt. Preserve that absence;
        # never infer that missing workers ran successfully or reuse their slot.
        batch = {
            "schema_version": "s2-h300-academic-block-v1",
            "plan_sha256": expected_plan,
            "job_id": expected_job,
            "arms": [],
            "unrun": [],
            "unaccounted": list(d.ORDER),
            "stop_reason": "missing_batch_receipt",
            "environment": None,
            "h300_execution_admitted": False,
            "repeats_admitted": False,
        }
    else:
        batch = products.read(target / "batch.json")
    d.require(
        batch["plan_sha256"] == expected_plan
        and batch["job_id"] == expected_job
        and [x["threads"] for x in batch["arms"]] == list(d.ORDER[: len(batch["arms"])])
        and (
            (
                batch["stop_reason"] == "missing_batch_receipt"
                and batch["unrun"] == []
                and batch.get("unaccounted") == list(d.ORDER)
            )
            or batch["unrun"] == list(d.ORDER[len(batch["arms"]) :])
        ),
        "Block prefix/unrun drift.",
    )
    steps = [
        x["attempt"]["step_id"]
        for x in batch["arms"]
        if x["attempt"] is not None and x["attempt"]["step_id"]
    ]
    raw = query(
        [
            "sacct",
            "-j",
            expected_job,
            "--noheader",
            "--parsable2",
            "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw",
        ],
        command=command,
    )
    accounting_error = None
    try:
        rows = accounting(raw, expected_job, steps)
    except ValueError:
        rows = {}
        for line in raw.strip().splitlines():
            parsed = scheduler.accounting(line, expected_job)
            d.require(not rows.keys() & parsed.keys(), "Duplicate forensic accounting row.")
            rows.update(parsed)
        d.require(
            {expected_job, expected_job + ".batch", expected_job + ".extern"} <= rows.keys()
            and all(x["state"] in scheduler.TERMINAL for x in rows.values()),
            "Accounting not terminal.",
        )
        accounting_error = "unexpected_or_missing_step_accounting"
    if missing_batch:
        # Publish only AFTER terminal accounting. A running job is not closed
        # by an eager collector; unknown execution is distinct from known unrun.
        products.publish(target / "batch.json", batch)
    try:
        resource_text = query(
            [
                "sacct",
                "-j",
                expected_job,
                "--noheader",
                "--parsable2",
                "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw,TotalCPU,MaxRSS,AllocCPUS,ReqMem",
            ],
            command=command,
        )
        scheduler_resources = {"rows": resource_accounting(resource_text, rows), "error_kind": None}
    except Exception as error:
        scheduler_resources = {"rows": None, "error_kind": type(error).__name__}
    origin = products.read(target / "origin.json")
    validation_error = None
    try:
        data, config = recheck(p, ROOT, origin["reference"])
    except Exception as error:
        validation_error = type(error).__name__
    reviewed = []
    for arm in batch["arms"]:
        threads = arm["threads"]
        path = target / "arms" / f"t{threads}"
        attempt = products.read(path / "attempt.json") if (path / "attempt.json").exists() else None
        d.require(attempt == arm["attempt"], "Parent attempt drift.")
        report = None
        if arm["review"] is not None and validation_error is None and accounting_error is None:
            anchor = partial.anchor(
                data,
                config,
                source_commit=p["preparation"]["source_commit"],
                runtime_sha256=d.digest(p["runtime"]),
                workbook_sha256=d.WORKBOOK,
                threads=threads,
            )
            try:
                report = products.review(path / "native/products", data, config, anchor)
            except Exception as error:
                validation_error = type(error).__name__
                reviewed.append({"threads": threads, "review": None})
                continue
            d.require(
                report == arm["review"]
                and attempt["stop_reason"] is None
                and attempt["local_client_reaped"] is True
                and attempt["return_code"] == 0
                and rows[attempt["step_id"]]["state"] == "COMPLETED"
                and rows[attempt["step_id"]]["exit_code"] == "0:0",
                "Arm replay/control drift.",
            )
        reviewed.append({"threads": threads, "review": report})
    complete = (
        accounting_error is None
        and validation_error is None
        and len(reviewed) == 5
        and all(x["review"] is not None for x in reviewed)
        and batch["stop_reason"] is None
        and not batch["unrun"]
        and all(
            rows[k]["state"] == "COMPLETED" and rows[k]["exit_code"] == "0:0"
            for k in (expected_job, expected_job + ".batch", expected_job + ".extern")
        )
    )
    report = {
        "schema_version": "s2-h300-academic-terminal-v1",
        "plan_sha256": expected_plan,
        "job_id": expected_job,
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
        ("scheduler-resources.json", scheduler_resources),
        ("review.json", report),
    ):
        path = target / name
        if path.exists():
            d.require(products.read(path) == value, "Immutable collection cache drift.")
        else:
            products.publish(path, value)
    archive = target / "s2-h300-academic-evidence.tar.gz"
    if archive.exists():
        manifest = products.read(target / "transfer.json")
        products.unpack_review(archive, manifest["sha256"], manifest["files"])
        d.require(manifest["files"] == products.inventory(target), "Cached archive source drift.")
    else:
        digest, files = products.pack(target, archive)
        products.publish(
            target / "transfer.json",
            {"sha256": digest, "files": files, "plan_sha256": expected_plan},
        )
        products.unpack_review(archive, digest, files)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("check", "start", "batch", "worker", "status", "collect", "wait")
    )
    parser.add_argument("--claim", type=Path)
    parser.add_argument("--threads", type=int)
    parser.add_argument("--plan-sha256")
    parser.add_argument("--job-id")
    args = parser.parse_args(argv)
    if args.action in {"start", "batch", "worker"}:
        entry.execute_h300()  # BEFORE any claim/input/native/scheduler effect.
    if args.action == "check":
        d.budget_ledger()
        print("P4_SOFTWARE_CONTRACT=CHECKED; H300_AND_REPEATS_BLOCKED")
        return 0
    d.require(args.claim is not None and args.claim.name == CLAIM, "Dedicated P4 claim only.")
    entry.require_hash(args.plan_sha256)
    d.require(re.fullmatch(r"[1-9][0-9]*", args.job_id or ""), "External job anchor required.")
    if args.action == "status":
        print(
            query(
                [
                    "sacct",
                    "-j",
                    args.job_id,
                    "--noheader",
                    "--parsable2",
                    "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw",
                ]
            )
        )
        return 0
    while True:
        try:
            report = _collect(args.claim, args.plan_sha256, args.job_id)
            print("P4_STATUS=" + report["status"])
            return 0
        except ValueError as error:
            if args.action != "wait" or str(error) not in {
                "Accounting not terminal.",
                "Missing/unexpected accounting row.",
            }:
                raise
            print("P4_ACCOUNTING_PENDING; Ctrl-C safe; no submission", flush=True)
            time.sleep(20)


if __name__ == "__main__":
    if __package__ in (None, ""):
        # Direct -I dispatch is intentionally blocked as well. The wrapper uses
        # runpy with an explicit trusted source root for solver-free check only.
        raise PermissionError("Direct execution is closed; no h300 or repeat admission.")
    raise SystemExit(main())
