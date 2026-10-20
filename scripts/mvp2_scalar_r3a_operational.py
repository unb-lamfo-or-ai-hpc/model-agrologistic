"""One human-acknowledged scalar h215 pair; no agent/automatic execution authority.

Uses the accepted case engine and unchanged mathematical code. Preparation,
merge and successful collection never admit repeats or a larger population.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import time
from dataclasses import replace
from pathlib import Path

from scripts import mvp2_scalar_r3a as r

ROOT = r.ROOT
CLAIM = ".mvp2-scalar-r3a-h215-4h-v1"
WORKBOOK_SHA = "40edb66585daca9cc393cab1f86bde6d4528a5f34b6afc57260cc1684396da4e"
POPULATION_SHA = "4134147f45188d2e8722476dd325b40e584c3746affe99889e045a547d283505"
ORDER_SHA = "7a524b2ed69b41481264d8049842b37e27cd3b96cc20d4e96d98eaf2a39e7903"
PROFILE = {
    **r.BUDGET,
    "status": "maintainer_confirmed_20261020",
    "slurm_wall_seconds": 50400,
    "native_time_limit_seconds_per_arm": 14400,
}
SHAPE = {"warehouses": 215, "periods": 60, "det_scenarios": 1, "sto_scenarios": 9}
PHASES = (
    "input_build",
    "optimization",
    "native_return",
    "independent_validation",
    "artifact_export",
    "complete",
)
TOOLS = ("srun", "sacct", "scontrol", "scancel")
MAX_BYTES, MAX_FILES = r.MAX_BYTES, r.MAX_FILES
MODES = ("det", "sto")
DATASET = (
    "pbf:brazil-260901@sha256:95c432ac3219338bbc7d4f5f7d20a5de709348ea928f656efd34609a51319fde;"
    "osrm:v6.0.0;oci:sha256:5116c66d814485be70bc7b239be890e4d36f62b1025a2f1c8139c20fa2697309;"
    "sif:sha256:1d6d8c47996ee31d1d2282433e13a94a1d48e9b218912fdf39741bf3b5b05249;"
    "profile:driving@sha256:9809a111a8fc8c465c2d6ef3208938a2a7c35fab0d3cda407ffa7ff187a96477;"
    "algorithm:MLD"
)


def budget():
    per = sum(
        PROFILE[k]
        for k in (
            "build_input_seconds_per_arm",
            "native_time_limit_seconds_per_arm",
            "late_return_export_seconds_per_arm",
            "validation_seconds_per_arm",
        )
    )
    planned = 2 * per + PROFILE["setup_cleanup_seconds"]
    r.require(planned == 39600 and planned < PROFILE["slurm_wall_seconds"], "Budget ledger.")
    return {
        **PROFILE,
        "planned_seconds": planned,
        "step_seconds": per,
        "reserve_seconds": PROFILE["slurm_wall_seconds"] - planned,
        "reserved_logical_cpu_hours": 336,
        "scope": "Reservation bound, not measured consumption or a convergence forecast.",
        **r.closed(),
    }


def specs(workbook):
    original, _ = r.frozen_specs(r.MANIFEST, workbook)
    # A separate approved operational profile, not mutation of the PR114 proposal.
    return [replace(s, solver=replace(s.solver, time_limit=14400)) for s in original]


def materialization(audit):
    p = audit["distance_provenance"]
    r.require(
        audit["schema_version"] == 1
        and audit["output_workbook_sha256"] == WORKBOOK_SHA
        and audit["distance_status"] == "osrm_authoritative"
        and p["provider"] == "osrm"
        and p["profile"] == "driving"
        and p["route_count_by_source"] == {"osrm": 63289}
        and p["route_count_by_arc_type"] == {"DD": 46010, "OD": 7955, "DC": 7955, "OC": 1369}
        and p["route_count"] == 63289
        and p["fallback_count"] == 0
        and p["osrm_cache_hit_count"] == 63504
        and all(
            p[k] == 0
            for k in ("osrm_request_count", "osrm_cache_miss_count", "osrm_cache_write_count")
        )
        and p["osrm_negative_distance_normalization_count"] == 4
        and p["dataset_id"] == DATASET
        and audit["input_workbook_sha256"]
        == "c3224645328bc498a9a897aa2a21ec790d8522e7d0ea3c7279c492fd0b743a05",
        "Historical OSRM materialization differs; no automatic rebuild.",
    )
    return audit


def regular(path):
    path = Path(path)
    r.require(path.is_file() and not path.is_symlink(), "Regular unlinked file required.")
    return path


def publish(path, value):
    """Expose complete immutable IPC JSON, never a zero/partially written file."""
    pending = path.with_name("." + path.name + ".pending")
    with pending.open("xb") as stream:
        stream.write(r.r2.encoded(value))
        stream.flush()
        os.fsync(stream.fileno())
    if os.name == "nt":
        # Windows rename fails if destination exists; POSIX rename would replace it.
        os.rename(pending, path)
    else:
        os.link(pending, path)  # Exclusive publication: cannot replace a prior receipt.
        pending.unlink()  # Only this function's new temporary link; final bytes persist.


def prepare(claim, sha, workbook, population, order, audit, predecessor):
    """Hash/config preparation only; no Excel ETL, solver, database or Slurm call."""
    r.require(claim.name == CLAIM and not claim.exists(), "Fresh operational claim required.")
    r.require(re.fullmatch(r"[0-9a-f]{40}", sha), "Full reviewed source required.")
    regular(workbook)
    r.require(r.file_hash(workbook) == WORKBOOK_SHA, "Historical workbook hash differs.")
    original_audit = regular(audit).read_bytes()
    observed = materialization(r.strict_json(original_audit))
    selection = r.warehouses.read_policy(population, order, POPULATION_SHA, ORDER_SHA, 215)
    previous = r.verify_r2(predecessor, r.R2_SHA)
    inventory = r.r2.source_inventory(ROOT)
    r.require(inventory["source_commit"] == sha, "Wrong source head.")
    r.r2.verify_source(inventory, ROOT)
    tools = {k: str(regular(Path(shutil.which(k) or "").resolve())) for k in TOOLS}
    plan = {
        "schema_version": "scalar-h215-operational-v1",
        "source_commit": sha,
        "source_root": str(ROOT),
        "python": sys.executable,
        "python_sha256": r.file_hash(sys.executable),
        "tools": tools,
        "tool_sha256": {k: r.file_hash(v) for k, v in tools.items()},
        "source_inventory_sha256": r.r2.digest(r.r2.encoded(inventory)),
        "selection_sha256": r.r2.digest(r.r2.encoded(selection)),
        "materialization_sha256": r.r2.digest(r.r2.encoded(observed)),
        "materialization_original_sha256": r.r2.digest(original_audit),
        "r2_predecessor": previous,
        "profile": PROFILE,
        "budget": budget(),
        "cases": [r.spec_payload(s) for s in specs(workbook)],
        "expected_shape": SHAPE,
        "one_pair_human_acknowledgement_required": True,
        **r.closed(),
    }
    plan = r.strict_json(r.r2.encoded(plan))
    r.require(r.file_hash(workbook) == WORKBOOK_SHA, "Input drift during preparation.")
    claim.mkdir(mode=0o700)
    for name, value in (
        ("source.json", inventory),
        ("warehouse_selection.json", selection),
        ("materialization.json", observed),
        ("plan.json", plan),
    ):
        r.r2.write(claim / name, value)
    with (claim / "materialization.original.json").open("xb") as f:
        f.write(original_audit)
    return plan


def load(claim, sha, *, verify=True):
    r.require(claim.name == CLAIM and not claim.is_symlink(), "Dedicated unlinked claim.")
    p = r.strict_json(regular(claim / "plan.json").read_bytes())
    r.require(
        p["schema_version"] == "scalar-h215-operational-v1"
        and p["source_commit"] == sha
        and re.fullmatch(r"[0-9a-f]{40}", sha)
        and p["profile"] == PROFILE
        and p["budget"] == budget()
        and p["expected_shape"] == SHAPE
        and all(p[k] is False for k in r.closed()),
        "Operational plan/source/profile differs.",
    )
    inventory = r.strict_json(regular(claim / "source.json").read_bytes())
    r.require(
        r.file_hash(claim / "source.json") == p["source_inventory_sha256"]
        and inventory["source_commit"] == sha
        and r.file_hash(regular(claim / "warehouse_selection.json")) == p["selection_sha256"]
        and r.file_hash(regular(claim / "materialization.json")) == p["materialization_sha256"],
        "Source/input provenance binding differs.",
    )
    if verify:
        r.require(Path(p["source_root"]).resolve() == ROOT, "Preserved source root differs.")
        r.r2.verify_source(inventory, ROOT)  # No Git needed on compute.
        r.require(r.file_hash(sys.executable) == p["python_sha256"], "Python bytes drift.")
    return p


def invocation(action, claim, sha, *extra):
    code = (
        "import runpy,sys;sys.dont_write_bytecode=True;sys.path.insert(0,sys.argv.pop(1));"
        "runpy.run_module('scripts.mvp2_scalar_r3a_operational',run_name='__main__')"
    )
    return [
        sys.executable,
        "-B",
        "-I",
        "-c",
        code,
        str(ROOT),
        action,
        "--claim",
        str(claim),
        "--source-sha",
        sha,
        *extra,
    ]


def job_receipt(claim, sha):
    job = r.strict_json(regular(claim / "job.json").read_bytes())
    r.require(
        job["source_commit"] == sha
        and re.fullmatch(r"[1-9][0-9]*", job["job_id"])
        and job["plan_sha256"] == r.file_hash(claim / "plan.json"),
        "Job/source/plan receipt differs.",
    )
    return job


def start(claim, sha, acknowledged, paths, *, command=r.r2.command):
    r.require(acknowledged, "Explicit human one-reviewed-h215-pair acknowledgement required.")
    r.require(sys.version_info[:2] == (3, 13) and not os.environ.get("SLURM_JOB_ID"), "Login only.")
    if claim.exists():
        load(claim, sha)
        r.require((claim / "job.json").is_file(), "Consumed uncertain claim; never resubmit.")
        return {"status": "existing_claim_collect_only", **r.r2.read(claim / "job.json")}
    from scripts.probe_npad_gurobi_license import check_file

    check_file()  # Metadata/access only on login; no contents or solver probe.
    plan = prepare(claim, sha, **paths)
    token = r.r2.digest(r.r2.encoded(plan))
    with (claim / "batch.sh").open("x", newline="\n") as f:
        f.write("#!/bin/sh\nexec " + shlex.join(invocation("batch", claim, sha)) + "\n")
    r.r2.write(
        claim / "submission_intent.json",
        {
            "plan_sha256": token,
            "human_one_pair_acknowledged": True,
            "automatic_retry": False,
        },
    )
    result = command(
        [
            "sbatch",
            "--parsable",
            "--account=sxdsouza",
            "--partition=intel-256",
            "--qos=preempt",
            "--nodes=1",
            "--ntasks=1",
            "--cpus-per-task=24",
            "--mem=192G",
            "--time=14:00:00",
            "--no-requeue",
            "--export=ALL",
            "--job-name=scalar-h215-4h",
            "--chdir=" + str(claim),
            "--output=" + str(claim / "slurm.out"),
            "--error=" + str(claim / "slurm.err"),
            str(claim / "batch.sh"),
        ]
    )
    r.r2.write(
        claim / "submission.json",
        {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        },
    )
    match = re.fullmatch(r"([1-9][0-9]*)(?:;[A-Za-z0-9_.-]+)?\s*", result.stdout)
    r.require(result.returncode == 0 and match, "Submission uncertain; preserve, never retry.")
    job = {"job_id": match[1], "source_commit": sha, "plan_sha256": token}
    publish(claim / "job.json", job)
    return {"status": "submitted_one_h215_pair_only", **job, **r.closed()}


def fields(text):
    pairs = re.findall(r"(?:^|\s)([A-Za-z][A-Za-z0-9_/:]*)=(\S*)", text)
    r.require(len(dict(pairs)) == len(pairs), "Duplicate scheduler field.")
    return dict(pairs)


def allocation(text, job, uid):
    f = fields(text)
    expected = {
        "JobId": job,
        "NumNodes": "1",
        "NumCPUs": "24",
        "CPUs/Task": "24",
        "TimeLimit": "14:00:00",
        "Partition": "intel-256",
        "Account": "sxdsouza",
        "QOS": "preempt",
        "JobState": "RUNNING",
    }
    r.require(all(f.get(k) == v for k, v in expected.items()), "Allocation profile mismatch.")
    r.require(re.fullmatch(r"[^()\s]+\(" + str(uid) + r"\)", f.get("UserId", "")), "Wrong owner.")
    r.require(f.get("MinMemoryNode") in {"192G", "196608M"}, "Memory request differs.")
    r.require(re.fullmatch(r"[A-Za-z0-9_-]+", f.get("NodeList", "")), "One explicit node.")
    # Slurm22 NPAD exposes TRES alone. It is preserved as TRES, not renamed ReqTRES.
    for name in ("TRES", "ReqTRES", "AllocTRES"):
        if name in f:
            tres = dict(x.split("=", 1) for x in f[name].split(","))
            r.require(
                tres.get("cpu") == "24"
                and tres.get("node") == "1"
                and tres.get("mem") in {"192G", "196608M"},
                "Conflicting TRES.",
            )
    r.require(any(k in f for k in ("TRES", "AllocTRES")), "No allocation TRES observation.")
    return f


def step_binding(text, entry, allocated, uid):
    f = fields(text)
    exact = entry["job_id"] + "." + entry["step_id"]
    r.require(entry["step_id"].isdigit(), "Numeric step required.")
    r.require(
        f.get("StepId") == exact
        and f.get("Nodes") == allocated["NodeList"]
        and f.get("UserId") in {str(uid), allocated["UserId"]}
        and f.get("CPUs") == "4",
        "Exact owned step not proven.",
    )
    return exact


def phase_usage(events, elapsed):
    r.require(events and events[0]["phase"] == "input_build", "Initial phase absent.")
    names = [e["phase"] for e in events]
    r.require(names == list(PHASES[: len(names)]), "Phase order/duplicate differs.")
    values = [e["elapsed_seconds"] for e in events]
    r.require(
        all(type(v) in (int, float) and math.isfinite(v) and v >= 0 for v in values)
        and values == sorted(values)
        and values[-1] <= elapsed,
        "Invalid phase clock.",
    )
    used = {k: 0.0 for k in PHASES}
    for i, event in enumerate(events):
        used[event["phase"]] += (values[i + 1] if i + 1 < len(values) else elapsed) - values[i]
    reserve = max(0.0, used["optimization"] - PROFILE["native_time_limit_seconds_per_arm"])
    reserve += used["native_return"] + used["artifact_export"]
    reason = None
    if used["input_build"] > PROFILE["build_input_seconds_per_arm"]:
        reason = "input_build_watchdog"
    elif reserve > PROFILE["late_return_export_seconds_per_arm"]:
        reason = "shared_return_export_watchdog"
    elif used["independent_validation"] > PROFILE["validation_seconds_per_arm"]:
        reason = "validation_watchdog"
    return {"seconds": used, "shared_reserve_used_seconds": reserve, "stop_reason": reason}


def events_at(directory, entry):
    events = []
    for path in sorted(directory.glob("phase-*.json")):
        value = r.strict_json(regular(path).read_bytes())
        r.require(value["entry"] == entry, "Phase identity drift.")
        events.append(value)
    return events


def terminate_step(exact, process, *, command, sleep=time.sleep):
    """Only a proven numeric step is signalled; reaping is not remote proof."""
    r.require(re.fullmatch(r"[1-9][0-9]*\.[0-9]+", exact), "Exact step required.")
    signals = []
    for sig, delay in (("TERM", 15), ("KILL", 15)):
        result = command(["scancel", "--signal=" + sig, exact])
        signals.append({"signal": sig, "returncode": result.returncode})
        try:
            process.wait(timeout=delay)
            break
        except subprocess.TimeoutExpired:
            sleep(0)
    try:
        process.wait(timeout=5)
        reaped = True
    except subprocess.TimeoutExpired:
        reaped = False
    return {
        "signals": signals,
        "local_client_reaped": reaped,
        "remote_cleanup_proven": False,
        "next_arm_allowed": False,
    }


def scalar_review(files, plan):
    """Original certificate replay, not a second solve or fresh residual computation."""
    selection = r.strict_json(files["warehouse_selection.json"])
    r.require(
        r.r2.digest(files["warehouse_selection.json"]) == plan["selection_sha256"],
        "Selection binding differs.",
    )
    arms, missing = [], []
    for expected in plan["cases"]:
        prefix = "cases/" + expected["name"]
        try:
            inp = r.strict_json(files[prefix + "/input_receipt.json"])
            pop = r.strict_json(files[prefix + "/warehouses_used.json"])
            r.require(
                inp["experiment"] == expected and inp["shape"] == plan["expected_shape"],
                "Input configuration/shape differs.",
            )
            probabilities = inp["effective_scenario_probabilities"]
            if expected["model"]["mode"] == "sto":
                r.require(
                    len(probabilities) == plan["expected_shape"]["sto_scenarios"]
                    and all(v == 1 / len(probabilities) for v in probabilities.values()),
                    "Effective equiprobable scenario design differs.",
                )
            else:
                r.require(probabilities == {"deterministic": 1.0}, "DET probabilities differ.")
            r.require(
                pop == inp["warehouse_selection"]
                and pop["policy_sha256"] == plan["selection_sha256"],
                "Warehouse receipt differs.",
            )
            r.require(
                files[prefix + "/warehouses_used.csv"] == r.warehouses.csv_bytes(pop["included"])
                and r.r2.digest(files[prefix + "/warehouses_used.csv"]) == pop["csv_sha256"]
                and pop["count"] == len(pop["included"]) == plan["expected_shape"]["warehouses"]
                and {(m["warehouse_id"], m["population_role"]) for m in pop["included"]}
                == {(m["warehouse_id"], m["population_role"]) for m in selection["members"]},
                "Included population differs.",
            )
            arm = r.case_review(files, prefix, expected)
            from src.logic.optimization import scalar_mip_gap

            payload = r.strict_json(
                files[prefix + "/products/" + expected["name"] + "/result.json"]
            )
            native = payload["result"]
            metadata_bound = native["metadata"].get("objective_bound")
            legacy_bound = native.get("objective_bound")
            r.require(
                metadata_bound is None or legacy_bound is None or metadata_bound == legacy_bound,
                "Conflicting original bound fields.",
            )
            arm["bound"] = metadata_bound if metadata_bound is not None else legacy_bound
            arm["common_gap"] = scalar_mip_gap(arm["objective"], arm["bound"])
            arm["native_gap"] = native["metadata"].get("gurobi_native_gap", native.get("mip_gap"))
            arm["solve_sequence_runtime_seconds"] = arm.pop("native_runtime_seconds")
            arm["native_runtime_seconds"] = arm["timings"].get("solver_reported_runtime_seconds")
            gap = arm["common_gap"]
            arm["scalar_gap_target_met"] = (
                arm["classification"] == "validated_feasible"
                and gap is not None
                and math.isfinite(gap)
                and gap <= expected["solver"]["mip_gap"]
            )
            arm["quality_reason"] = (
                "target_met"
                if arm["scalar_gap_target_met"]
                else (
                    "recorded_bound_exceeds_incumbent"
                    if arm["bound"] is not None
                    and arm["objective"] is not None
                    and arm["bound"] > arm["objective"]
                    else ("gap_unavailable" if gap is None else "gap_above_target")
                )
            )
            arms.append(arm)
        except (KeyError, ValueError, TypeError) as exc:
            missing.append({"name": expected["name"], "error_kind": type(exc).__name__})
    feasible = (
        len(arms) == 2
        and not missing
        and all(a["classification"] == "validated_feasible" for a in arms)
    )
    quality = feasible and all(a["scalar_gap_target_met"] for a in arms)
    return {
        "status": "pair_quality_target_met"
        if quality
        else ("pair_feasible_quality_censored" if feasible else "partial_or_rejected_preserved"),
        "arms": arms,
        "missing_or_rejected": missing,
        "quality_target_met": quality,
        "qualification": "Original certificate replay; not fresh private-input residual re-solve.",
        **r.closed(),
    }


def case_contract(cases):
    """Compare full scientific settings without reading private input during replay."""
    from src.logic.experiment_runner import load_experiment_manifest

    originals = load_experiment_manifest(r.MANIFEST).experiments
    r.require(len(cases) == 2 and cases[0]["workbook"] == cases[1]["workbook"], "One input pair.")
    for actual, template in zip(cases, originals, strict=True):
        actual = r.strict_json(r.r2.encoded(actual))
        r.require(
            actual["name"] == template.name and actual["workbook_sha256"] == WORKBOOK_SHA,
            "Frozen input/name differs.",
        )
        from dataclasses import asdict

        expected = r.strict_json(
            r.r2.encoded(
                {
                    "loader": asdict(template.loader),
                    "model": asdict(template.model),
                    "solver": asdict(replace(template.solver, time_limit=14400)),
                }
            )
        )
        r.require(
            actual["loader"] == expected["loader"]
            and actual["model"] == expected["model"]
            and actual["solver"] == expected["solver"]
            and actual["max_estimated_variables"] == template.max_estimated_variables
            and actual["metadata"] == template.metadata,
            "Scientific profile differs.",
        )


def snapshot(claim):
    """Bounded private artifacts only; never input workbooks, databases or licenses."""
    files = {}
    for path in sorted(claim.rglob("*")):
        r.require(not path.is_symlink(), "Linked evidence rejected.")
        if not path.is_file():
            continue
        name = path.relative_to(claim).as_posix()
        if name in {
            "scalar-h215-evidence.tar.gz",
            "scalar-h215-evidence.tar.gz.sha256",
            "collection.json",
        }:
            continue
        r.require(
            r._safe_name(name) and path.suffix.lower() not in {".lic", ".xlsx", ".sqlite3"},
            "Forbidden evidence member.",
        )
        r.require(path.stat().st_size <= MAX_BYTES, "Member exceeds cap; no truncation.")
        files[name] = path.read_bytes()
        r.require(
            len(files) <= MAX_FILES - 2 and sum(map(len, files.values())) <= MAX_BYTES,
            "Transfer cap exceeded; preserve without truncation.",
        )
    return files


def run_case(spec, target, shape, selection, control, entry):
    """Complete original case engine with existing native hook, no scientific edits."""
    from src.logic.experiment_runner import run_experiment
    from src.logic.mathematical_contract import extensive_form_inputs
    from src.logic.optimization import configure_gurobi_wls_license, project_deterministic_result
    from src.logic.optimization_gurobipy_stochastic import solve_stochastic_model_gurobipy

    origin = entry.get("started_monotonic", time.monotonic())
    count = 0

    def mark(name):
        nonlocal count
        r.require(count < len(PHASES) and PHASES[count] == name, "Worker phase order.")
        publish(
            control / f"phase-{count:02d}.json",
            {
                "entry": entry,
                "phase": name,
                "elapsed_seconds": 0.0 if count == 0 else time.monotonic() - origin,
            },
        )
        count += 1

    mark("input_build")

    def solve(*, data, model_config, solver_config):
        from src.logic.model_validation import validate_or_raise_model_data

        # Keep the exact public solve_model admission checks before its native
        # backend; the only integration difference is the already-existing hook.
        model_config.__post_init__()
        solver_config.__post_init__()
        validate_or_raise_model_data(data=data, config=model_config, require_distances=True)
        configure_gurobi_wls_license(solver_config)
        prepared, config = extensive_form_inputs(data, model_config)

        def hook(name, model, _grb):
            if name == "optimization":
                r.require(
                    model.Params.TimeLimit == solver_config.time_limit
                    and model.Params.Threads == solver_config.threads
                    and model.Params.MIPGap == solver_config.mip_gap,
                    "Effective solver parameters differ.",
                )
                mark("optimization")
            elif name == "export_validation":
                mark("native_return")
                publish(
                    control / "native_terminal.json",
                    {
                        "entry": entry,
                        "status_code": int(model.Status),
                        "solution_count": int(model.SolCount),
                        "runtime_seconds": float(model.Runtime),
                        "time_limit_seconds": float(model.Params.TimeLimit),
                        "objective": float(model.ObjVal) if model.SolCount else None,
                    },
                )

        result = solve_stochastic_model_gurobipy(
            prepared, config, solver_config, native_phase_hook=hook
        )
        result = project_deterministic_result(result) if model_config.mode == "det" else result
        mark("independent_validation")
        return result

    def progress(message):
        if "exporting structured artifacts" in message:
            mark("artifact_export")

    def runner(*args, **kwargs):
        kwargs.update(solver=solve, progress=progress)
        return run_experiment(*args, **kwargs)

    result = r.run_case_software(spec, target, shape, selection, runner=runner)
    mark("complete")
    return result


def worker(claim, sha, mode):
    plan = load(claim, sha)
    job = job_receipt(claim, sha)
    r.require(os.environ.get("SLURM_JOB_ID") == job["job_id"], "Worker job identity.")
    step = os.environ.get("SLURM_STEP_ID", "")
    r.require(step.isdigit() and mode in MODES, "Numeric native step/mode required.")
    control = claim / "control" / mode
    entry = {
        **job,
        "step_id": step,
        "mode": mode,
        "pid": os.getpid(),
        "started_monotonic": time.monotonic(),
    }
    publish(control / "entry.json", entry)
    deadline = time.monotonic() + 60
    while not (control / "release.json").exists() and time.monotonic() < deadline:
        time.sleep(0.1)
    r.require(r.r2.read(control / "release.json") == entry, "Exact-step release absent/different.")
    for name in TOOLS:
        r.require(r.file_hash(plan["tools"][name]) == plan["tool_sha256"][name], "Tool drift.")
    from scripts.probe_npad_gurobi_license import probe

    capability = probe()
    r.r2.write(control / "license_capability.json", capability)
    r.require(capability["status"] == "accepted", "Fresh designated WLS capability rejected.")
    selected = specs(plan["cases"][0]["workbook"])[MODES.index(mode)]
    r.require(
        r.strict_json(r.r2.encoded(r.spec_payload(selected))) == plan["cases"][MODES.index(mode)],
        "Case/input drift.",
    )
    affinity = sorted(os.sched_getaffinity(0))
    r.require(4 <= len(affinity) <= PROFILE["allocated_logical_cpus"], "Worker affinity differs.")
    r.r2.write(
        control / "runtime.json",
        {
            "python": platform.python_version(),
            "affinity_logical_cpus": affinity,
            "python_sha256": r.file_hash(sys.executable),
            "scope": "Observed logical affinity; no physical-core or speedup inference.",
        },
    )
    selection = r.r2.read(claim / "warehouse_selection.json")
    run_case(selected, claim / "cases" / selected.name, SHAPE, selection, control, entry)
    load(claim, sha)


def review_process(claim, sha, mode, remaining):
    control = claim / "control" / mode
    with (
        (control / "review.out").open("xb") as out,
        (control / "review.err").open("xb") as err,
    ):
        result = subprocess.run(
            invocation("review", claim, sha, "--mode", mode),
            stdout=out,
            stderr=err,
            check=False,
            timeout=remaining,
        )
    r.require(result.returncode == 0, "Independent product receipt review failed.")


def verify_tools(plan):
    for name in TOOLS:
        r.require(
            str(Path(shutil.which(name) or "").resolve()) == plan["tools"][name]
            and r.file_hash(plan["tools"][name]) == plan["tool_sha256"][name],
            "Compute tool identity drift.",
        )


def supervise(
    claim,
    sha,
    mode,
    allocated,
    job,
    *,
    command=r.r2.command,
    popen=subprocess.Popen,
    clock=time.monotonic,
    sleep=time.sleep,
    reviewer=review_process,
):
    control = claim / "control" / mode
    control.mkdir(parents=True)
    begun, exact, entry = clock(), None, None
    outcome = {"mode": mode, "status": "partial", "next_arm_allowed": False}
    with (control / "worker.out").open("xb") as out, (control / "worker.err").open("xb") as err:
        process = popen(
            [
                "srun",
                "--exact",
                "--nodes=1",
                "--ntasks=1",
                "--cpus-per-task=4",
                "--cpu-bind=threads",
                "--time=05:15:00",
                "--kill-on-bad-exit=1",
                "--export=ALL",
                *invocation("worker", claim, sha, "--mode", mode),
            ],
            stdout=out,
            stderr=err,
        )
        try:
            while process.poll() is None:
                elapsed = clock() - begun
                if entry is None and (control / "entry.json").exists():
                    entry = r.r2.read(control / "entry.json")
                    r.require(
                        all(entry[k] == v for k, v in job.items()) and entry["mode"] == mode,
                        "Worker entry binding differs.",
                    )
                    exact_id = entry["job_id"] + "." + entry["step_id"]
                    r.require(re.fullmatch(r"[1-9][0-9]*\.[0-9]+", exact_id), "Step grammar.")
                    query = command(["scontrol", "-o", "show", "step", exact_id])
                    r.r2.write(
                        control / "step_query.json",
                        {
                            "returncode": query.returncode,
                            "stdout": query.stdout,
                            "stderr": query.stderr,
                        },
                    )
                    r.require(query.returncode == 0, "Step ownership query failed.")
                    exact = step_binding(query.stdout, entry, allocated, os.getuid())
                    publish(control / "release.json", entry)
                r.require(entry is not None or elapsed <= 45, "Worker startup unbound.")
                if entry is not None:
                    events = events_at(control, entry)
                    if events:
                        # Worker elapsed is on the same monotonic clock but with its own epoch.
                        age = clock() - entry["started_monotonic"]
                        usage = phase_usage(events, age)
                        r.require(usage["stop_reason"] is None, usage["stop_reason"])
                    else:
                        r.require(
                            elapsed <= PROFILE["build_input_seconds_per_arm"],
                            "Preflight/license startup watchdog.",
                        )
                r.require(elapsed <= budget()["step_seconds"], "Whole-step watchdog.")
                sleep(0.25)
            process.wait(timeout=5)
            r.require(entry is not None and exact is not None, "Worker exited before binding.")
            events = events_at(control, entry)
            usage = phase_usage(events, events[-1]["elapsed_seconds"] if events else 0)
            r.require(
                events[-1]["phase"] == "complete"
                and not usage["stop_reason"]
                and process.returncode == 0,
                "Worker failed or phase envelope exceeded.",
            )
            # Reaped srun is insufficient; terminal owned-step accounting is required.
            until = clock() + 60
            while True:
                q = command(
                    [
                        "sacct",
                        "-j",
                        exact,
                        "--noheader",
                        "--parsable2",
                        "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw,MaxRSS",
                    ]
                )
                rows = r.r2.accounting(q.stdout, job["job_id"]) if q.returncode == 0 else []
                record = next((x for x in rows if x["job_id"] == exact), None)
                if record and record["state"] in r.r2.TERMINAL:
                    r.r2.write(control / "terminal_step.json", {"raw": q.stdout, "row": record})
                    r.require(
                        record["state"] == "COMPLETED" and record["exit_code"] == "0:0",
                        "Native step did not complete normally.",
                    )
                    break
                r.require(clock() < until, "Step accounting pending; no next arm.")
                sleep(1)
            remaining = (
                PROFILE["validation_seconds_per_arm"] - usage["seconds"]["independent_validation"]
            )
            r.require(remaining > 0, "Validation reserve exhausted.")
            review_started = clock()
            reviewer(claim, sha, mode, remaining)
            r.require(clock() - review_started <= remaining, "Product review deadline exceeded.")
            outcome.update(
                status="closed_feasible_arm",
                next_arm_allowed=True,
                usage=usage,
                step_id=entry["step_id"],
                local_client_reaped=True,
                product_review_seconds=clock() - review_started,
            )
        except Exception as exc:
            outcome.update(error_kind=type(exc).__name__)
            if process.poll() is None and exact is not None:
                outcome["stop"] = terminate_step(exact, process, command=command, sleep=sleep)
            elif process.poll() is None:
                # Only our local srun child, never a guessed remote PID/job target.
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
                outcome["unbound_local_client_reaped"] = True
            # Unknown ownership never becomes a broad scancel or permission to continue.
            outcome["remote_cleanup_proven"] = False
    r.r2.write(control / "controller.json", outcome)
    return outcome


def review_arm(claim, sha, mode):
    plan = load(claim, sha)
    files = snapshot(claim)
    report = scalar_review(files, plan)
    selected = next((a for a in report["arms"] if a["mode"] == mode), None)
    r.require(
        selected and selected["classification"] == "validated_feasible",
        "Original independent validation did not accept an incumbent.",
    )
    r.r2.write(claim / "control" / mode / "review.json", selected)
    return selected


def batch(claim, sha):
    result = {
        "status": "blocked_or_partial",
        "completed_modes": [],
        "unrun": list(MODES),
        **r.closed(),
    }
    phase = "source_and_job_binding"
    try:
        plan = load(claim, sha)
        verify_tools(plan)
        until = time.monotonic() + 30
        while not (claim / "job.json").exists() and time.monotonic() < until:
            time.sleep(0.1)
        job = r.r2.read(claim / "job.json")
        r.require(
            job
            == {
                "job_id": os.environ.get("SLURM_JOB_ID"),
                "source_commit": sha,
                "plan_sha256": r.file_hash(claim / "plan.json"),
            },
            "Batch job binding.",
        )
        r.r2.write(claim / "batch_entry.json", job)
        phase = "fresh_allocation"
        q = r.r2.command(["scontrol", "-o", "show", "job", job["job_id"]])
        r.r2.write(
            claim / "allocation_query.json",
            {
                "returncode": q.returncode,
                "stdout": q.stdout,
                "stderr": q.stderr,
            },
        )
        r.require(q.returncode == 0, "Allocation query failed.")
        allocated = allocation(q.stdout, job["job_id"], os.getuid())
        r.r2.write(claim / "allocation.json", allocated)
        for mode in MODES:
            phase = "serial_" + mode
            result["unrun"].remove(mode)
            outcome = supervise(claim, sha, mode, allocated, job)
            r.require(outcome["next_arm_allowed"], "Stop serial pair; preserve unrun arms.")
            result["completed_modes"].append(mode)
        load(claim, sha)
        result.update(status="pair_returned", source_verified_after=True)
    except Exception as exc:
        result["error_kind"] = type(exc).__name__
        result["failure_phase"] = phase
    r.r2.write(claim / "batch_outcome.json", result)
    return int(result["status"] != "pair_returned")


def portable_review(files):
    plan, job = (r.strict_json(files[n]) for n in ("plan.json", "job.json"))
    r.require(
        plan["schema_version"] == "scalar-h215-operational-v1"
        and plan["profile"] == PROFILE
        and plan["budget"] == budget()
        and plan["expected_shape"] == SHAPE
        and all(plan[k] is False for k in r.closed())
        and [s["model"]["mode"] for s in plan["cases"]] == list(MODES),
        "Portable profile.",
    )
    case_contract(plan["cases"])
    r.require(
        job["plan_sha256"] == r.r2.digest(files["plan.json"])
        and job["source_commit"] == plan["source_commit"],
        "Portable job/plan binding.",
    )
    r.require(
        r.r2.digest(files["source.json"]) == plan["source_inventory_sha256"]
        and r.strict_json(files["source.json"])["source_commit"] == plan["source_commit"],
        "Portable source identity.",
    )
    r.require(
        r.r2.digest(files["materialization.json"]) == plan["materialization_sha256"],
        "Materialization hash.",
    )
    materialization(r.strict_json(files["materialization.json"]))
    r.require(
        r.r2.digest(files["materialization.original.json"])
        == plan["materialization_original_sha256"]
        and r.strict_json(files["materialization.original.json"])
        == r.strict_json(files["materialization.json"]),
        "Original OSRM audit differs.",
    )
    rows = r.r2.accounting(files["accounting.txt"].decode(), job["job_id"])
    r.require(r.r2.terminal(rows, job["job_id"]), "Nonterminal portable evidence.")
    science = scalar_review(files, plan)
    try:
        query = r.strict_json(files["allocation_query.json"])
        f = fields(query["stdout"])
        owner = re.fullmatch(r"[^()]+\(([0-9]+)\)", f["UserId"])
        r.require(owner and query["returncode"] == 0, "Allocation observation missing.")
        allocated = allocation(query["stdout"], job["job_id"], int(owner[1]))
        r.require(
            allocated == r.strict_json(files["allocation.json"]), "Allocation replay differs."
        )
        r.require(r.strict_json(files["batch_entry.json"]) == job, "Batch entry differs.")
        wanted = {job["job_id"], job["job_id"] + ".batch"}
        runtimes = []
        for mode in MODES:
            base = "control/" + mode + "/"
            entry = r.strict_json(files[base + "entry.json"])
            r.require(
                all(entry[k] == v for k, v in job.items())
                and entry["mode"] == mode
                and r.strict_json(files[base + "release.json"]) == entry,
                "Entry/release differs.",
            )
            q = r.strict_json(files[base + "step_query.json"])
            r.require(q["returncode"] == 0, "Step query failed.")
            exact = step_binding(q["stdout"], entry, allocated, int(owner[1]))
            wanted.add(exact)
            control = r.strict_json(files[base + "controller.json"])
            r.require(
                control["status"] == "closed_feasible_arm"
                and control["local_client_reaped"]
                and control["step_id"] == entry["step_id"],
                "Unclosed native controller.",
            )
            ev = [r.strict_json(files[n]) for n in sorted(files) if n.startswith(base + "phase-")]
            r.require(
                all(e["entry"] == entry for e in ev) and ev[-1]["phase"] == "complete",
                "Worker phase bindings differ.",
            )
            usage = phase_usage(ev, ev[-1]["elapsed_seconds"])
            r.require(
                not usage["stop_reason"] and usage == control["usage"], "Phase budget differs."
            )
            review_seconds = control.get("product_review_seconds")
            r.require(
                type(review_seconds) in (int, float)
                and math.isfinite(review_seconds)
                and review_seconds >= 0
                and review_seconds + usage["seconds"]["independent_validation"]
                <= PROFILE["validation_seconds_per_arm"],
                "Combined review budget differs.",
            )
            capability = r.strict_json(files[base + "license_capability.json"])
            runtime = r.strict_json(files[base + "runtime.json"])
            from scripts.probe_npad_gurobi_license import LICENSE_FILE

            r.require(
                capability["status"] == "accepted"
                and capability["probe_variable_count"] == 2001
                and capability["probe_constraint_count"] == 2001
                and abs(capability["objective_value"] - 2001) <= 1e-6,
                "Capability differs.",
            )
            affinity = runtime["affinity_logical_cpus"]
            r.require(
                capability["license_file"] == LICENSE_FILE
                and capability["gurobi_version"][0] == 13
                and runtime["python"].startswith("3.13.")
                and runtime["python_sha256"] == plan["python_sha256"]
                and 4 <= len(affinity) <= PROFILE["allocated_logical_cpus"]
                and len(affinity) == len(set(affinity))
                and all(type(cpu) is int and cpu >= 0 for cpu in affinity),
                "Runtime/license/affinity receipt differs.",
            )
            runtimes.append((runtime["python"], capability["gurobi_version"]))
        r.require(
            len(wanted) == 4
            and runtimes[0] == runtimes[1]
            and wanted <= {x["job_id"] for x in rows}
            and {
                x["job_id"]
                for x in rows
                if x["job_id"].split(".")[-1].isdigit() and "." in x["job_id"]
            }
            == wanted - {job["job_id"], job["job_id"] + ".batch"}
            and all(x["state"] == "COMPLETED" and x["exit_code"] == "0:0" for x in rows),
            "Unexpected/missing/failed accounting step.",
        )
        r.require(
            all(
                x["elapsed_seconds"]
                <= (
                    budget()["step_seconds"]
                    if x["job_id"] in wanted - {job["job_id"], job["job_id"] + ".batch"}
                    else PROFILE["slurm_wall_seconds"]
                )
                for x in rows
            ),
            "Observed scheduler envelope exceeded.",
        )
        result = r.strict_json(files["batch_outcome.json"])
        r.require(
            result["status"] == "pair_returned"
            and result["completed_modes"] == list(MODES)
            and result["source_verified_after"]
            and not result["unrun"],
            "Pair not closed.",
        )
        operational = True
    except (ValueError, KeyError, TypeError, IndexError):
        operational = False
    return {
        **science,
        "operational_receipts_closed": operational,
        "status": science["status"] if operational else "forensic_partial_pair_preserved",
        "job_id": job["job_id"],
        "production_isolation_certified": False,
        "automatic_follow_on_allowed": False,
    }


def collect(claim, sha, *, command=r.r2.command):
    load(claim, sha)
    marker = claim / "collection.json"
    if marker.exists():
        saved = r.r2.read(marker)
        r.require(
            saved["archive"] == "scalar-h215-evidence.tar.gz"
            and r.file_hash(regular(claim / saved["archive"])) == saved["sha256"],
            "Preserved collection changed; never overwrite.",
        )
        return saved
    job = r.r2.read(claim / "job.json")
    r.require(
        job["source_commit"] == sha and job["plan_sha256"] == r.file_hash(claim / "plan.json"),
        "Job binding differs.",
    )
    q = command(
        [
            "sacct",
            "-j",
            job["job_id"],
            "--noheader",
            "--parsable2",
            "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw,MaxRSS",
        ]
    )
    r.require(q.returncode == 0, "Accounting unavailable; preserve and collect later.")
    rows = r.r2.accounting(q.stdout, job["job_id"])
    required = {job["job_id"], job["job_id"] + ".batch"}
    for mode in MODES:
        entry = claim / "control" / mode / "entry.json"
        if entry.exists():
            value = r.r2.read(regular(entry))
            r.require(
                value["job_id"] == job["job_id"] and value["step_id"].isdigit(), "Entry differs."
            )
            required.add(job["job_id"] + "." + value["step_id"])
    if not r.r2.terminal(rows, job["job_id"]) or not required <= {x["job_id"] for x in rows}:
        return {"status": "nonterminal_or_accounting_pending", **r.closed()}
    terminal = claim / "terminal_accounting.json"
    if not terminal.exists():
        r.r2.write(terminal, {"raw": q.stdout, "rows": rows})
    files = snapshot(claim)
    files["accounting.txt"] = r.r2.read(terminal)["raw"].encode()
    result = portable_review(files)
    files["review.json"] = r.r2.encoded(result)
    files["inventory.json"] = r.r2.encoded({k: r.r2.digest(v) for k, v in files.items()})
    r.require(
        len(files) <= MAX_FILES and sum(map(len, files.values())) <= MAX_BYTES,
        "Final transfer cap exceeded; no truncation.",
    )
    archive = claim / "scalar-h215-evidence.tar.gz"
    with archive.open("xb") as f, tarfile.open(fileobj=f, mode="w:gz") as tar:
        for name, value in sorted(files.items()):
            member = tarfile.TarInfo(name)
            member.size, member.mode = len(value), 0o600
            tar.addfile(member, io.BytesIO(value))
    result.update(
        archive=archive.name,
        sha256=r.file_hash(archive),
        download=str(archive),
        transfer_checksum=str(archive) + ".sha256",
    )
    with Path(str(archive) + ".sha256").open("x") as f:
        f.write(result["sha256"] + "  " + archive.name + "\n")
    r.r2.write(marker, result)
    return result


def audit(archive, checksum):
    r.require(
        re.fullmatch(r"[0-9a-f]{64}", checksum) and r.file_hash(archive) == checksum,
        "External checksum mismatch.",
    )
    files, size = {}, 0
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar:
            r.require(
                member.isfile() and r._safe_name(member.name) and member.name not in files,
                "Unsafe/duplicate member.",
            )
            size += member.size
            r.require(size <= MAX_BYTES and len(files) < MAX_FILES, "Archive cap exceeded.")
            files[member.name] = tar.extractfile(member).read()
    inventory = r.strict_json(files.pop("inventory.json"))
    r.require(inventory == {k: r.r2.digest(v) for k, v in files.items()}, "Inventory mismatch.")
    return portable_review(files)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "action",
        choices=(
            "start",
            "batch",
            "worker",
            "review",
            "status",
            "collect",
            "wait",
            "audit",
            "budget",
            "h300",
        ),
    )
    p.add_argument("--claim", type=Path)
    p.add_argument("--source-sha")
    p.add_argument("--mode", choices=MODES)
    p.add_argument("--one-reviewed-h215-pair", action="store_true")
    for name in ("workbook", "population", "order", "materialization", "predecessor", "archive"):
        p.add_argument("--" + name, type=Path)
    p.add_argument("--sha256")
    args = p.parse_args(argv)
    if args.action == "h300":
        p.exit(2, "H300_AND_REPEATS_CLOSED; NO_JOB_SUBMITTED\n")
    if args.action == "budget":
        result = budget()
    elif args.action == "audit":
        result = audit(args.archive, args.sha256)
    else:
        r.require(args.claim is not None and args.source_sha is not None, "Claim/source required.")
        claim = args.claim.absolute()
        if args.action == "start":
            result = start(
                claim,
                args.source_sha,
                args.one_reviewed_h215_pair,
                {
                    "workbook": args.workbook,
                    "population": args.population,
                    "order": args.order,
                    "audit": args.materialization,
                    "predecessor": args.predecessor,
                },
            )
        elif args.action == "batch":
            return batch(claim, args.source_sha)
        elif args.action == "worker":
            worker(claim, args.source_sha, args.mode)
            return 0
        elif args.action == "review":
            result = review_arm(claim, args.source_sha, args.mode)
        elif args.action == "status":
            load(claim, args.source_sha)
            job = job_receipt(claim, args.source_sha)
            q = r.r2.command(
                [
                    "sacct",
                    "-j",
                    job["job_id"],
                    "--noheader",
                    "--parsable2",
                    "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw,MaxRSS",
                ]
            )
            result = {
                "status": "accounting_observed",
                "raw": q.stdout,
                "query_returncode": q.returncode,
                **job,
                **r.closed(),
            }
        else:
            while True:
                result = collect(claim, args.source_sha)
                if args.action != "wait" or result["status"] != "nonterminal_or_accounting_pending":
                    break
                print(
                    "NONTERMINAL; Ctrl-C safe; repeat wait/collect, never start a new claim.",
                    flush=True,
                )
                time.sleep(20)
    print(json.dumps(result, sort_keys=True, allow_nan=False), flush=True)
    print("NO_REPEAT_LARGER_INSTANCE_OR_AUTOMATIC_FOLLOW_ON_ADMITTED", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
