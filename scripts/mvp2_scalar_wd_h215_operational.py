"""One human-acknowledged D DET/STO h215 block; preserve all historical W claims.

Reuses the original scalar case engine, native hook, exact-step controller,
phase limits and independent validator. No old launcher/default/model is changed.
"""

from __future__ import annotations

import argparse
import csv
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
from pathlib import Path

from scripts import mvp2_scalar_wd_h215_gate as g

o, r = g.old, g.r
ROOT = Path(__file__).resolve().parents[1]
CLAIM = ".mvp2-scalar-wd-h215-d-14h-v1"
ARCHIVE = "scalar-wd-h215-evidence.tar.gz"
PROFILE = {**o.PROFILE, "status": "D_pair_maintainer_approved_20261022"}
MODES = ("det", "sto")
SHAPE = dict(o.SHAPE)
INPUT_KEYS = ("workbook", "population", "order", "materialization", "w_archive")
PENALTIES = ("unmet_demand", "emergency_static", "emergency_reception")


def closed():
    return {
        **r.closed(),
        "d_execution_admitted": False,
        "w_repetition_admitted": False,
        "resource_envelope_approved_for_d": True,
    }


def budget():
    return {
        **o.budget(),
        **PROFILE,
        **closed(),
        "scope": "Approved ONE D DET->STO block; no W repeat or additional block.",
    }


def specs(workbook):
    candidates = g.proposed_specs(workbook)
    return [candidates["D_" + mode] for mode in MODES]


def case_contract(cases):
    """Strict template comparison without accessing the private workbook on replay."""
    from dataclasses import asdict, replace

    from src.logic.experiment_runner import load_experiment_manifest

    templates = load_experiment_manifest(r.MANIFEST).experiments
    r.require(len(cases) == 2 and cases[0]["workbook"] == cases[1]["workbook"], "One D pair input.")
    for actual, template in zip(cases, templates, strict=True):
        expected = {
            "name": "scalar_h215_d_" + template.model.mode,
            "workbook_sha256": o.WORKBOOK_SHA,
            "loader": asdict(replace(template.loader, include_direct_origin_customer_routes=True)),
            "model": asdict(replace(template.model, use_direct_origin_customer=True)),
            "solver": asdict(replace(template.solver, time_limit=14400)),
            "max_estimated_variables": template.max_estimated_variables,
            "metadata": template.metadata,
        }
        r.require(
            {k: v for k, v in actual.items() if k != "workbook"}
            == r.strict_json(r.r2.encoded(expected)),
            "Frozen D profile differs.",
        )


def design(files):
    plan = r.strict_json(files["plan.json"])
    source = r.strict_json(files["source.json"])
    previous = r.strict_json(files["historical_w.json"])
    r.require(
        plan["schema_version"] == "scalar-wd-h215-operational-v1"
        and plan["profile"] == PROFILE
        and plan["budget"] == budget()
        and plan["expected_shape"] == SHAPE
        and all(plan[k] == v for k, v in closed().items()),
        "D scope/resource/admission differs.",
    )
    case_contract(plan["cases"])
    for name in (
        "source.json",
        "warehouse_selection.json",
        "materialization.original.json",
        "historical_w.json",
    ):
        r.require(
            r.r2.digest(files[name]) == plan["artifact_sha256"][name], "Plan-bound artifact drift."
        )
    r.require(
        re.fullmatch(r"[0-9a-f]{40}", plan["source_commit"])
        and source["source_commit"] == plan["source_commit"]
        and previous["archive_sha256"] == g.W_SHA
        and previous["source_commit"] == g.W_SOURCE
        and previous["plan_sha256"] == g.W_PLAN
        and previous["review"]["job_id"] == "2217990"
        and previous["review"]["status"] == "pair_quality_target_met",
        "Historical W/source binding differs.",
    )
    r.require(
        {k: v for k, v in source["files"].items() if k.startswith("src/logic/")}
        == previous["scientific_sources"],
        "Scientific implementation changed from W.",
    )
    o.materialization(r.strict_json(files["materialization.original.json"]))
    selection = r.strict_json(files["warehouse_selection.json"])
    r.require(
        selection["target_population"] == SHAPE["warehouses"]
        and selection["population_manifest_sha256"] == o.POPULATION_SHA
        and selection["population_order_sha256"] == o.ORDER_SHA
        and plan["selection_sha256"] == plan["artifact_sha256"]["warehouse_selection.json"],
        "Warehouse selection drift.",
    )
    r.require(
        {k: plan["input_sha256"][k] for k in ("workbook", "population", "order", "w_archive")}
        == {
            "workbook": o.WORKBOOK_SHA,
            "population": o.POPULATION_SHA,
            "order": o.ORDER_SHA,
            "w_archive": g.W_SHA,
        }
        and plan["input_sha256"]["materialization"]
        == plan["artifact_sha256"]["materialization.original.json"],
        "Historical input hash binding differs.",
    )
    return plan


def plan_files(claim):
    return {
        n: o.regular(claim / n).read_bytes()
        for n in (
            "plan.json",
            "source.json",
            "warehouse_selection.json",
            "materialization.original.json",
            "historical_w.json",
        )
    }


def prepare(claim, sha, **paths):
    """Login metadata/hash preparation only; no workbook ETL, solver or scheduler."""
    r.require(
        claim.name == CLAIM and not claim.exists() and not claim.is_symlink(),
        "Fresh exclusive D claim required.",
    )
    frozen = {}
    for key in INPUT_KEYS:
        try:
            frozen[key] = o.regular(paths[key])
        except (ValueError, TypeError) as exc:
            raise ValueError(
                "Required " + key + " file missing/linked; no claim/job created."
            ) from exc
    hashes = {k: r.file_hash(p) for k, p in frozen.items()}
    r.require(hashes["workbook"] == o.WORKBOOK_SHA, "Historical h215 workbook checksum differs.")
    material = frozen["materialization"].read_bytes()
    o.materialization(r.strict_json(material))
    selection = r.warehouses.read_policy(
        frozen["population"], frozen["order"], o.POPULATION_SHA, o.ORDER_SHA, 215
    )
    previous = g.historical_w(frozen["w_archive"])
    inventory = g.source_inventory(ROOT)
    r.require(inventory["source_commit"] == sha, "Exact source SHA required.")
    tools = {k: str(o.regular(Path(shutil.which(k) or "").resolve())) for k in o.TOOLS}
    artifacts = {
        "source.json": r.r2.encoded(inventory),
        "warehouse_selection.json": r.r2.encoded(selection),
        "materialization.original.json": material,
        "historical_w.json": r.r2.encoded(previous),
    }
    plan = {
        "schema_version": "scalar-wd-h215-operational-v1",
        "source_commit": sha,
        "source_root": str(ROOT),
        "python": sys.executable,
        "python_sha256": r.file_hash(sys.executable),
        "tools": tools,
        "tool_sha256": {k: r.file_hash(p) for k, p in tools.items()},
        "input_paths": {k: str(v.resolve()) for k, v in frozen.items()},
        "input_sha256": hashes,
        "artifact_sha256": {n: r.r2.digest(b) for n, b in artifacts.items()},
        "selection_sha256": r.r2.digest(artifacts["warehouse_selection.json"]),
        "cases": [r.spec_payload(s) for s in specs(frozen["workbook"])],
        "profile": PROFILE,
        "budget": budget(),
        "expected_shape": SHAPE,
        **closed(),
    }
    artifacts["plan.json"] = r.r2.encoded(plan)
    design(artifacts)
    r.require(
        hashes == {k: r.file_hash(p) for k, p in frozen.items()},
        "Input changed before claim creation.",
    )
    r.r2.verify_source(inventory, ROOT)
    claim.mkdir(mode=0o700)
    for name, content in artifacts.items():
        with (claim / name).open("xb") as stream:
            stream.write(content)
    return r.strict_json(artifacts["plan.json"])


def load(claim, sha):
    r.require(claim.name == CLAIM and not claim.is_symlink(), "Dedicated D claim required.")
    files = plan_files(claim)
    plan = design(files)
    r.require(
        plan["source_commit"] == sha and Path(plan["source_root"]).resolve() == ROOT,
        "Source head/root drift.",
    )
    r.r2.verify_source(r.strict_json(files["source.json"]), ROOT)
    r.require(r.file_hash(sys.executable) == plan["python_sha256"], "Python drift.")
    return plan


def invocation(action, claim, sha, *extra):
    return [
        sys.executable,
        "-B",
        "-I",
        "-c",
        "import runpy,sys;sys.dont_write_bytecode=True;sys.path.insert(0,sys.argv.pop(1));"
        "runpy.run_module('scripts.mvp2_scalar_wd_h215_operational',run_name='__main__')",
        str(ROOT),
        action,
        "--claim",
        str(claim),
        "--source-sha",
        sha,
        *extra,
    ]


def start(claim, sha, acknowledged, paths, *, command=r.r2.command):
    r.require(acknowledged, "Explicit human one-reviewed-D-pair acknowledgement required.")
    r.require(
        sys.version_info[:2] == (3, 13) and not os.environ.get("SLURM_JOB_ID"),
        "Login Python3.13 only.",
    )
    if claim.exists():
        load(claim, sha)
        job = o.job_receipt(claim, sha)  # Uncertain consumed claim cannot resubmit.
        return {"status": "existing_D_claim_collect_only", **job, **closed()}
    from scripts.probe_npad_gurobi_license import check_file

    check_file()  # Designated file metadata only; never read/hash secrets on login.
    plan = prepare(claim, sha, **paths)
    token = r.r2.digest(r.r2.encoded(plan))
    with (claim / "batch.sh").open("x", newline="\n") as stream:
        stream.write("#!/bin/sh\nexec " + shlex.join(invocation("batch", claim, sha)) + "\n")
    r.r2.write(
        claim / "submission_intent.json",
        {"plan_sha256": token, "one_D_pair_acknowledged": True, "automatic_retry": False},
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
            "--job-name=scalar-h215-D",
            "--chdir=" + str(claim),
            "--output=" + str(claim / "slurm.out"),
            "--error=" + str(claim / "slurm.err"),
            str(claim / "batch.sh"),
        ]
    )
    r.r2.write(
        claim / "submission.json",
        {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr},
    )
    match = re.fullmatch(r"([1-9][0-9]*)(?:;[A-Za-z0-9_.-]+)?\s*", result.stdout)
    r.require(
        result.returncode == 0 and match, "Submission uncertain; preserve claim, never retry."
    )
    job = {"job_id": match[1], "source_commit": sha, "plan_sha256": token}
    o.publish(claim / "job.json", job)
    return {"status": "submitted_one_D_det_sto_pair_only", **job, **closed()}


def recheck_inputs(plan):
    r.require(
        {k: r.file_hash(o.regular(p)) for k, p in plan["input_paths"].items()}
        == plan["input_sha256"],
        "Frozen input/evidence changed.",
    )


def fresh_comparison(claim, plan, job):
    """Compute-node data-only gate, using sealed source metadata, NEVER Git."""
    recheck_inputs(plan)
    cells, comparisons = g.inspect_comparison(
        Path(plan["input_paths"]["workbook"]),
        r.r2.read(claim / "warehouse_selection.json"),
        r.r2.read(claim / "historical_w.json"),
    )
    recheck_inputs(plan)
    directory = claim / "comparability"
    directory.mkdir()
    for label, cell in cells.items():
        r.r2.write(directory / (label + ".json"), cell)
    anchor = {
        "job": job,
        "cell_sha256": {label: r.file_hash(directory / (label + ".json")) for label in cells},
        "comparisons": comparisons,
        "input_sha256": plan["input_sha256"],
        **closed(),
    }
    o.publish(claim / "comparison_anchor.json", anchor)
    return anchor


def comparison_review(files, plan, job):
    anchor = r.strict_json(files["comparison_anchor.json"])
    previous = r.strict_json(files["historical_w.json"])
    r.require(
        anchor["job"] == job
        and anchor["input_sha256"] == plan["input_sha256"]
        and all(anchor[k] == v for k, v in closed().items()),
        "Comparison/job scope differs.",
    )
    cells = {}
    r.require(
        set(anchor["cell_sha256"]) == {t + "_" + m for t in ("W", "D") for m in MODES},
        "Exactly four input cells required.",
    )
    for mode in MODES:
        for topology in ("W", "D"):
            label = topology + "_" + mode
            raw = files["comparability/" + label + ".json"]
            r.require(r.r2.digest(raw) == anchor["cell_sha256"][label], "Comparison cell drift.")
            cells[label] = r.strict_json(raw)
            r.require(
                cells[label]["estimate"]["period_count"] == SHAPE["periods"]
                and cells[label]["estimate"]["scenario_count"] == SHAPE[mode + "_scenarios"]
                and cells[label]["warehouse_selection"]["count"] == SHAPE["warehouses"],
                "Input comparison shape drift.",
            )
        r.require(
            g.compare_pair(cells["W_" + mode], cells["D_" + mode]) == anchor["comparisons"][mode],
            "W/D comparison replay drift.",
        )
        expected = plan["cases"][MODES.index(mode)]
        r.require(cells["D_" + mode]["specification"] == expected, "D cell/config drift.")
        w, original = cells["W_" + mode], previous["receipts"][mode]
        r.require(
            {k: v for k, v in w["specification"].items() if k != "workbook"}
            == {k: v for k, v in original["experiment"].items() if k != "workbook"}
            and w["contract"] == original["mathematical_contract"]
            and w["warehouse_selection"] == original["warehouse_selection"]
            and w["effective_probabilities"] == original["effective_scenario_probabilities"],
            "Historical W restriction drift.",
        )
    return anchor, cells


def snapshot(claim):
    return o.snapshot(claim, archive_name=ARCHIVE)


def hardware_observation():
    record = {"host": platform.node(), "machine": platform.machine(), "cpu_model": {}}
    try:
        for line in Path("/proc/cpuinfo").read_text().split("\n\n")[0].splitlines():
            key, sep, value = line.partition(":")
            if sep and key.strip() in {
                "vendor_id",
                "cpu family",
                "model",
                "model name",
                "stepping",
            }:
                record["cpu_model"][key.strip()] = value.strip()
    except OSError as exc:
        record["observation_error"] = type(exc).__name__
    return record


def worker(claim, sha, mode):
    plan = load(claim, sha)
    job = o.job_receipt(claim, sha)
    step = os.environ.get("SLURM_STEP_ID", "")
    r.require(
        mode in MODES and os.environ.get("SLURM_JOB_ID") == job["job_id"] and step.isdigit(),
        "Owned numeric D step required.",
    )
    control = claim / "control" / mode
    entry = {
        **job,
        "mode": mode,
        "step_id": step,
        "pid": os.getpid(),
        "started_monotonic": time.monotonic(),
    }
    o.publish(control / "entry.json", entry)
    until = time.monotonic() + 60
    while not (control / "release.json").exists() and time.monotonic() < until:
        time.sleep(0.1)
    r.require(r.r2.read(control / "release.json") == entry, "Exact-step release absent/different.")
    o.verify_tools(plan)
    from scripts.probe_npad_gurobi_license import probe

    capability = probe()
    r.r2.write(control / "license_capability.json", capability)
    r.require(capability["status"] == "accepted", "Fresh designated WLS capability rejected.")
    recheck_inputs(plan)
    selected = specs(Path(plan["cases"][0]["workbook"]))[MODES.index(mode)]
    r.require(
        r.strict_json(r.r2.encoded(r.spec_payload(selected))) == plan["cases"][MODES.index(mode)],
        "Frozen D case drift.",
    )
    affinity = sorted(os.sched_getaffinity(0))
    r.require(4 <= len(affinity) <= 24, "Four solver threads need allocated logical affinity.")
    r.r2.write(
        control / "runtime.json",
        {
            "python": platform.python_version(),
            "python_sha256": r.file_hash(sys.executable),
            "affinity_logical_cpus": affinity,
            "gurobi_version": capability["gurobi_version"],
            "solver_threads": 4,
            "hardware": hardware_observation(),
            "scope": "Observed logical affinity, no physical-core equivalence claim.",
        },
    )
    expected_raw = o.regular(claim / "comparability" / ("D_" + mode + ".json")).read_bytes()
    anchor = r.r2.read(claim / "comparison_anchor.json")
    r.require(
        anchor["job"] == job and r.r2.digest(expected_raw) == anchor["cell_sha256"]["D_" + mode],
        "D cell anchor drift.",
    )
    expected_cell = r.strict_json(expected_raw)
    selection = r.r2.read(claim / "warehouse_selection.json")

    def input_reviewer(data, receipt):
        actual = g.inspect_cell(selected, loader=lambda *_: data)
        population = r.warehouses.membership_receipt(actual.pop("warehouse_data"), selection)
        actual["warehouse_selection"] = population
        r.require(actual == expected_cell, "Fresh D input differs from pre-build W/D gate.")
        receipt["wd_cell_sha256"] = r.r2.digest(expected_raw)

    o.run_case(
        selected,
        claim / "cases" / selected.name,
        SHAPE,
        selection,
        control,
        entry,
        input_reviewer=input_reviewer,
    )
    recheck_inputs(plan)
    load(claim, sha)


def diagnostic_metrics(files, case, probabilities):
    """Keep raw products; summarize distinct flow/activation and memory scopes."""
    base = "cases/" + case + "/products/" + case + "/"
    native = r.strict_json(files[base + "result.json"])["result"]
    summary = r.strict_json(files[base + "run_summary.json"])
    flows = {
        family: {"raw_arc_tonnes": 0.0, "expected_arc_tonnes": 0.0, "positive_records": 0}
        for family in ("OD", "DC", "DD", "OC")
    }
    for row in native["flows"]:
        family = row["route_type"]
        value = row["value"]
        r.require(family in flows and math.isfinite(value) and value >= 0, "Flow metric malformed.")
        scenario = row.get("scenario", "deterministic")
        r.require(scenario in probabilities, "Flow scenario weight missing.")
        flows[family]["raw_arc_tonnes"] += value
        flows[family]["expected_arc_tonnes"] += value * probabilities[scenario]
        flows[family]["positive_records"] += int(value > 0)
    decisions = native["warehouse_decisions"]

    def positive(key):
        return sum(float(row.get(key, 0)) > 1e-6 for row in decisions)

    memory = {}
    for filename, keys in (
        ("resource_timeseries.csv", ("process_tree_rss_bytes", "cgroup_current_bytes")),
        ("solver_progress.csv", ("solver_memory_bytes",)),
    ):
        for row in csv.DictReader(io.StringIO(files[base + "resources/" + filename].decode())):
            phase = row.get("phase", "unreported")
            observed = memory.setdefault(phase, {})
            for key in keys:
                if row.get(key) not in (None, ""):
                    value = float(row[key])
                    r.require(math.isfinite(value) and value >= 0, "Invalid memory sample.")
                    observed[key] = max(observed.get(key, value), value)

    return {
        "cost_components": native["cost_breakdown"],
        "investment": {
            "candidate_activations": sum(
                bool(row["is_candidate"]) and row["open"] > 0.5 for row in decisions
            ),
            "positive_candidate_capacity_count": positive("candidate_capacity"),
            "positive_expansion_count": positive("expansion_capacity"),
            "positive_bulk_capacity_count": positive("bulk_capacity"),
            "candidate_capacity": sum(row.get("candidate_capacity", 0) for row in decisions),
            "expansion_capacity": sum(row.get("expansion_capacity", 0) for row in decisions),
            "bulk_capacity": sum(row.get("bulk_capacity", 0) for row in decisions),
        },
        "positive_flows_by_family": flows,
        "flow_scope": (
            "OC and DC are destination arrivals; OD/DD are network-arc volumes, "
            "not additive delivered tonnes. Original records retain product/period/scenario."
        ),
        "physical_diagnostics": {
            k: summary.get(k)
            for k in (
                "domestic_service_level",
                "total_unmet_demand",
                "emergency_static_capacity",
                "emergency_reception_capacity",
                "penalty_cost_share",
                "peak_rss_mb",
            )
        },
        "matrix": r.strict_json(files[base + "resources/matrix_statistics.json"]),
        "resource_termination": r.strict_json(files[base + "resources/termination.json"]),
        "sampled_memory_maxima_by_original_phase": memory,
        "resource_scope": (
            "Sampled application RSS, native solver memory, cgroup and Slurm MaxRSS "
            "remain separate; no inferred peak or causal speedup."
        ),
    }


def science_review(files, plan):
    report = o.scalar_review(files, plan, include_case_names=True)
    accepted, rejected = [], list(report["missing_or_rejected"])
    for arm in report["arms"]:
        try:
            case = arm["case_name"]
            receipt = r.strict_json(files["cases/" + case + "/input_receipt.json"])
            label = "D_" + arm["mode"]
            expected = files["comparability/" + label + ".json"]
            cell = r.strict_json(expected)
            r.require(
                receipt["wd_cell_sha256"] == r.r2.digest(expected)
                and receipt["mathematical_contract"] == cell["contract"]
                and receipt["estimate"] == cell["estimate"]
                and receipt["warehouse_selection"] == cell["warehouse_selection"],
                "Fresh D input receipt binding differs.",
            )
            arm["diagnostics"] = diagnostic_metrics(
                files, case, receipt["effective_scenario_probabilities"]
            )
            accepted.append(arm)
        except (KeyError, ValueError, TypeError) as exc:
            rejected.append({"name": arm["case_name"], "error_kind": type(exc).__name__})
    feasible = (
        len(accepted) == 2
        and not rejected
        and all(a["classification"] == "validated_feasible" for a in accepted)
    )
    quality = feasible and all(a["scalar_gap_target_met"] for a in accepted)
    return {
        **report,
        "arms": accepted,
        "missing_or_rejected": rejected,
        "quality_target_met": quality,
        "status": "D_pair_quality_target_met"
        if quality
        else (
            "D_pair_feasible_quality_censored" if feasible else "D_partial_or_rejected_preserved"
        ),
        "historical_W_controls": r.strict_json(files["historical_w.json"])["review"],
        "causal_runtime_comparison_admitted": False,
        **closed(),
    }


def review_arm(claim, sha, mode):
    report = science_review(snapshot(claim), load(claim, sha))
    arm = next((a for a in report["arms"] if a["mode"] == mode), None)
    r.require(
        arm and arm["classification"] == "validated_feasible",
        "Original independent feasible incumbent required.",
    )
    r.r2.write(claim / "control" / mode / "review.json", arm)
    return arm


def review_process(claim, sha, mode, remaining):
    control = claim / "control" / mode
    with (control / "review.out").open("xb") as out, (control / "review.err").open("xb") as err:
        result = subprocess.run(
            invocation("review", claim, sha, "--mode", mode),
            stdout=out,
            stderr=err,
            timeout=remaining,
            check=False,
        )
    r.require(result.returncode == 0, "Original product review failed; preserve diagnostics.")


def supervise(claim, sha, mode, allocated, job):
    return o.supervise(
        claim,
        sha,
        mode,
        allocated,
        job,
        invoke=invocation,
        reviewer=review_process,
        phase_profile=PROFILE,
        whole_arm_seconds=budget()["step_seconds"],
    )


def batch(claim, sha):
    begun = time.monotonic()
    result = {
        "status": "blocked_or_partial",
        "completed_modes": [],
        "unrun": list(MODES),
        **closed(),
    }
    phase, spans = "source_and_job_binding", 0.0
    try:
        plan = load(claim, sha)
        o.verify_tools(plan)
        until = time.monotonic() + 30
        while not (claim / "job.json").exists() and time.monotonic() < until:
            time.sleep(0.1)
        job = o.job_receipt(claim, sha)
        r.require(job["job_id"] == os.environ.get("SLURM_JOB_ID"), "Batch job mismatch.")
        r.r2.write(claim / "batch_entry.json", job)
        phase = "fresh_allocation_and_comparison"
        query = r.r2.command(["scontrol", "-o", "show", "job", job["job_id"]])
        r.r2.write(
            claim / "allocation_query.json",
            {"returncode": query.returncode, "stdout": query.stdout, "stderr": query.stderr},
        )
        r.require(query.returncode == 0, "Allocation query failed.")
        allocated = o.allocation(query.stdout, job["job_id"], os.getuid())
        r.r2.write(claim / "allocation.json", allocated)
        fresh_comparison(claim, plan, job)
        for mode in MODES:
            r.require(
                time.monotonic() - begun - spans <= PROFILE["setup_cleanup_seconds"],
                "Setup/cleanup reserve exhausted; no next arm.",
            )
            phase = "serial_D_" + mode
            result["unrun"].remove(mode)
            started = time.monotonic()
            outcome = supervise(claim, sha, mode, allocated, job)
            spans += time.monotonic() - started
            r.require(outcome["next_arm_allowed"], "Stop D pair; preserve remaining cells unrun.")
            result["completed_modes"].append(mode)
        load(claim, sha)
        recheck_inputs(plan)
        auxiliary = time.monotonic() - begun - spans
        r.require(auxiliary <= PROFILE["setup_cleanup_seconds"], "Auxiliary reserve exceeded.")
        result.update(
            status="D_pair_returned", source_verified_after=True, auxiliary_seconds=auxiliary
        )
    except Exception as exc:
        result.update(error_kind=type(exc).__name__, failure_phase=phase)
    r.r2.write(claim / "batch_outcome.json", result)
    return int(result["status"] != "D_pair_returned")


def operational_review(files, plan, job, science, rows):
    """Original exact-step receipt replay; failed/partial evidence remains forensic."""
    comparison_review(files, plan, job)
    query = r.strict_json(files["allocation_query.json"])
    owner = re.fullmatch(r"[^()]+\(([0-9]+)\)", o.fields(query["stdout"])["UserId"])
    r.require(query["returncode"] == 0 and owner, "Allocation query/owner.")
    allocated = o.allocation(query["stdout"], job["job_id"], int(owner[1]))
    r.require(
        allocated == r.strict_json(files["allocation.json"])
        and r.strict_json(files["batch_entry.json"]) == job,
        "Allocation/batch binding.",
    )
    wanted, runtimes = {job["job_id"], job["job_id"] + ".batch"}, []
    for mode in MODES:
        base = "control/" + mode + "/"
        entry = r.strict_json(files[base + "entry.json"])
        r.require(
            all(entry[k] == v for k, v in job.items())
            and entry["mode"] == mode
            and r.strict_json(files[base + "release.json"]) == entry,
            "Worker entry/release.",
        )
        query = r.strict_json(files[base + "step_query.json"])
        r.require(query["returncode"] == 0, "Step query failed.")
        exact = o.step_binding(query["stdout"], entry, allocated, int(owner[1]))
        wanted.add(exact)
        terminal_step = r.strict_json(files[base + "terminal_step.json"])
        terminal_rows = r.r2.accounting(terminal_step["raw"], job["job_id"])
        r.require(
            terminal_step["row"] in terminal_rows
            and terminal_step["row"]["job_id"] == exact
            and terminal_step["row"]["state"] == "COMPLETED"
            and terminal_step["row"]["exit_code"] == "0:0",
            "Owned terminal step receipt differs.",
        )
        control = r.strict_json(files[base + "controller.json"])
        events = [r.strict_json(files[n]) for n in sorted(files) if n.startswith(base + "phase-")]
        r.require(
            events
            and all(e["entry"] == entry for e in events)
            and events[-1]["phase"] == "complete",
            "Phase closure.",
        )
        usage = o.phase_usage(events, events[-1]["elapsed_seconds"], profile=PROFILE)
        r.require(
            control["status"] == "closed_feasible_arm"
            and control["local_client_reaped"]
            and control["step_id"] == entry["step_id"]
            and control["usage"] == usage
            and usage["stop_reason"] is None,
            "Controller/phase envelope.",
        )
        chosen = next(a for a in science["arms"] if a["mode"] == mode)
        r.require(
            chosen["classification"] == "validated_feasible"
            and r.strict_json(files[base + "review.json"]) == chosen,
            "Original post-worker review.",
        )
        terminal = r.strict_json(files[base + "native_terminal.json"])
        r.require(
            terminal["entry"] == entry
            and terminal["solution_count"] > 0
            and terminal["time_limit_seconds"] == 14400
            and math.isfinite(terminal["runtime_seconds"])
            and 0 <= terminal["runtime_seconds"] <= 15300,
            "Native termination budget.",
        )
        seconds = control["product_review_seconds"]
        r.require(
            type(seconds) in (int, float)
            and math.isfinite(seconds)
            and seconds >= 0
            and seconds + usage["seconds"]["independent_validation"] <= 1800,
            "Combined validation reserve.",
        )
        capability = r.strict_json(files[base + "license_capability.json"])
        runtime = r.strict_json(files[base + "runtime.json"])
        from scripts.probe_npad_gurobi_license import LICENSE_FILE

        r.require(
            capability["status"] == "accepted"
            and capability["license_file"] == LICENSE_FILE
            and capability["probe_variable_count"] == capability["probe_constraint_count"] == 2001
            and abs(capability["objective_value"] - 2001) <= 1e-6
            and capability["gurobi_version"][0] == 13,
            "Fresh designated WLS capability.",
        )
        affinity = runtime["affinity_logical_cpus"]
        r.require(
            runtime["python"].startswith("3.13.")
            and runtime["python_sha256"] == plan["python_sha256"]
            and runtime["solver_threads"] == 4
            and runtime["gurobi_version"] == capability["gurobi_version"]
            and 4 <= len(affinity) == len(set(affinity)) <= 24
            and all(type(v) is int and v >= 0 for v in affinity),
            "Runtime/affinity drift.",
        )
        runtimes.append((runtime["python"], capability["gurobi_version"], runtime["hardware"]))
    numeric = {
        row["job_id"]
        for row in rows
        if "." in row["job_id"] and row["job_id"].split(".")[-1].isdigit()
    }
    r.require(
        len(wanted) == 4
        and runtimes[0] == runtimes[1]
        and wanted <= {x["job_id"] for x in rows}
        and numeric == wanted - {job["job_id"], job["job_id"] + ".batch"}
        and all(
            x["state"] == "COMPLETED"
            and x["exit_code"] == "0:0"
            and x["elapsed_seconds"] <= (18900 if x["job_id"] in numeric else 50400)
            for x in rows
        ),
        "Accounting closure/envelope.",
    )
    result = r.strict_json(files["batch_outcome.json"])
    auxiliary = result["auxiliary_seconds"]
    r.require(
        result["status"] == "D_pair_returned"
        and result["completed_modes"] == list(MODES)
        and result["source_verified_after"]
        and not result["unrun"]
        and type(auxiliary) in (int, float)
        and math.isfinite(auxiliary)
        and 0 <= auxiliary <= 1800,
        "D batch closure.",
    )


def portable_review(files):
    plan = design(files)
    job = r.strict_json(files["job.json"])
    r.require(
        re.fullmatch(r"[1-9][0-9]*", job["job_id"])
        and job["source_commit"] == plan["source_commit"]
        and job["plan_sha256"] == r.r2.digest(files["plan.json"]),
        "D job/source/plan binding.",
    )
    rows = r.r2.accounting(files["accounting.txt"].decode(), job["job_id"])
    r.require(r.r2.terminal(rows, job["job_id"]), "Terminal accounting required.")
    science = science_review(files, plan)
    operational, error = False, None
    try:
        operational_review(files, plan, job, science, rows)
        operational = True
    except (ValueError, KeyError, TypeError, IndexError, StopIteration) as exc:
        error = type(exc).__name__
    return {
        **science,
        "status": science["status"] if operational else "D_forensic_partial_preserved",
        "operational_receipts_closed": operational,
        "operational_error_kind": error,
        "job_id": job["job_id"],
        "source_commit": plan["source_commit"],
        "production_isolation_certified": False,
        **closed(),
    }


def collect(claim, sha, *, command=r.r2.command):
    load(claim, sha)
    marker = claim / "collection.json"
    if marker.exists():
        saved = r.r2.read(o.regular(marker))
        r.require(
            saved["archive"] == ARCHIVE
            and r.file_hash(o.regular(claim / ARCHIVE)) == saved["sha256"]
            and o.regular(Path(str(claim / ARCHIVE) + ".sha256")).read_text().strip()
            == saved["sha256"] + "  " + ARCHIVE,
            "Preserved transfer changed; never overwrite.",
        )
        return saved
    job = o.job_receipt(claim, sha)
    query = command(
        [
            "sacct",
            "-j",
            job["job_id"],
            "--noheader",
            "--parsable2",
            "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw,MaxRSS",
        ]
    )
    r.require(query.returncode == 0, "Accounting unavailable; preserve and collect later.")
    rows = r.r2.accounting(query.stdout, job["job_id"])
    wanted = {job["job_id"], job["job_id"] + ".batch"}
    for mode in MODES:
        path = claim / "control" / mode / "entry.json"
        if path.exists():
            entry = r.r2.read(o.regular(path))
            r.require(
                entry["job_id"] == job["job_id"] and entry["step_id"].isdigit(),
                "Step identity drift.",
            )
            wanted.add(job["job_id"] + "." + entry["step_id"])
    if not wanted <= {x["job_id"] for x in rows} or any(
        x["state"] not in r.r2.TERMINAL for x in rows
    ):
        return {"status": "nonterminal_or_accounting_pending", **closed()}
    terminal = claim / "terminal_accounting.json"
    if not terminal.exists():
        r.r2.write(terminal, {"raw": query.stdout, "rows": rows})
    files = snapshot(claim)
    files["accounting.txt"] = r.r2.read(terminal)["raw"].encode()
    report = portable_review(files)
    files["review.json"] = r.r2.encoded(report)
    files["inventory.json"] = r.r2.encoded({n: r.r2.digest(b) for n, b in files.items()})
    r.require(
        len(files) <= 4096 and sum(map(len, files.values())) <= 1024**3,
        "Transfer cap exceeded; no truncation.",
    )
    archive = claim / ARCHIVE
    with archive.open("xb") as stream, tarfile.open(fileobj=stream, mode="w:gz") as tar:
        for name, content in sorted(files.items()):
            member = tarfile.TarInfo(name)
            member.size, member.mode = len(content), 0o600
            tar.addfile(member, io.BytesIO(content))
    report.update(
        archive=ARCHIVE,
        sha256=r.file_hash(archive),
        download=str(archive),
        transfer_checksum=str(archive) + ".sha256",
    )
    with Path(str(archive) + ".sha256").open("x") as stream:
        stream.write(report["sha256"] + "  " + ARCHIVE + "\n")
    r.r2.write(marker, report)
    return report


def audit(archive, checksum):
    from scripts.review_scalar_h300_evidence import read_archive

    files, _ = read_archive(archive, checksum)
    return portable_review(files)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "start",
            "batch",
            "worker",
            "review",
            "status",
            "wait",
            "collect",
            "audit",
            "budget",
        ),
    )
    parser.add_argument("--claim", type=Path)
    parser.add_argument("--source-sha")
    parser.add_argument("--mode", choices=MODES)
    parser.add_argument("--one-reviewed-d-pair", action="store_true")
    for name in (*INPUT_KEYS, "archive"):
        parser.add_argument("--" + name.replace("_", "-"), type=Path)
    parser.add_argument("--sha256")
    args = parser.parse_args(argv)
    if args.action == "budget":
        report = budget()
    elif args.action == "audit":
        report = audit(args.archive, args.sha256)
    else:
        r.require(
            args.claim is not None and args.source_sha is not None, "Claim/full source required."
        )
        claim = args.claim.absolute()
        if args.action == "start":
            report = start(
                claim,
                args.source_sha,
                args.one_reviewed_d_pair,
                {k: getattr(args, k) for k in INPUT_KEYS},
            )
        elif args.action == "batch":
            return batch(claim, args.source_sha)
        elif args.action == "worker":
            worker(claim, args.source_sha, args.mode)
            return 0
        elif args.action == "review":
            report = review_arm(claim, args.source_sha, args.mode)
        elif args.action == "status":
            load(claim, args.source_sha)
            job = o.job_receipt(claim, args.source_sha)
            query = r.r2.command(
                [
                    "sacct",
                    "-j",
                    job["job_id"],
                    "--noheader",
                    "--parsable2",
                    "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw,MaxRSS",
                ]
            )
            report = {
                "status": "accounting_observed",
                "raw": query.stdout,
                "query_returncode": query.returncode,
                **job,
                **closed(),
            }
        else:
            while True:
                report = collect(claim, args.source_sha)
                if args.action != "wait" or report["status"] != "nonterminal_or_accounting_pending":
                    break
                print(
                    "NONTERMINAL; Ctrl-C safe; resume wait/collect, never reset a claim.",
                    flush=True,
                )
                time.sleep(20)
    print(json.dumps(report, sort_keys=True, allow_nan=False), flush=True)
    print("NO_W_REPEAT_ADDITIONAL_BLOCK_OR_AUTOMATIC_FOLLOW_ON_ADMITTED", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
