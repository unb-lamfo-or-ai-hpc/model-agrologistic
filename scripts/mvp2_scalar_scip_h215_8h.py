"""One longer human-only scalar SCIP STO/W h215 observation, native8h/Slurm12h.

Preserves Gurobi evidence and the scientific implementation. No repeat, HiGHS
fallback, second topology, larger instance or automatic follow-on is admitted.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import time
from dataclasses import asdict, replace
from importlib.metadata import distribution
from pathlib import Path

from scripts import mvp2_scalar_scip_h215 as predecessor
from scripts import mvp2_scalar_wd_h215_gate as g
from scripts import mvp2_scalar_wd_h215_operational as d
from scripts.scip_external_observer import ExternalObserver, proc_start, review_external

o, r = g.old, g.r
ROOT = Path(__file__).resolve().parents[1]
CLAIM = ".mvp2-scalar-scip-h215-w-native8h-v1"
ARCHIVE = "scalar-scip-h215-w-native8h-evidence.tar.gz"
CASE = "scalar_scip_h215_w_native8h"
MODES = ("sto",)
SHAPE = dict(o.SHAPE)
INPUT_KEYS = (*d.INPUT_KEYS, "scip_predecessor")
PROFILE = {
    **{k: v for k, v in o.PROFILE.items() if k != "solver_soft_memory_decimal_gb"},
    "status": "one_longer_scip_scalar_W_requested_20261028",
    "slurm_wall_seconds": 43200,
    "build_input_seconds_per_arm": 3600,
    "native_time_limit_seconds_per_arm": 28800,
    "solver_threads": 4,
    "scip_memory_limit_mb": 163840,
}
EXPECTED_PARAMS = {
    "limits/gap": 0.01, "limits/absgap": 1e-10, "limits/memory": 163840.0,
    "parallel/maxnthreads": 4, "lp/threads": 4, "numerics/feastol": 1e-9,
}


PREDECESSOR_SHA = "41557726ecd93ab67a5764077ea18a35e08db4d6f97123a03ebd6b72930ebf68"
PREDECESSOR_SOURCE = "cbd64d86914dd416ed16b6a58ffe1069401e3aad"
PREDECESSOR_PLAN = "1af2f262961cfcca46edfca6a2663e5e82267b3dab0dcefedebea3785761a7fe"


def inspect_predecessor(path):
    from scripts.review_scalar_h300_evidence import read_archive

    files, _ = read_archive(path, PREDECESSOR_SHA)
    report = predecessor.portable_review(files)
    r.require(
        report == r.strict_json(files["review.json"])
        and report["job_id"] == "2225638" and report["source_commit"] == PREDECESSOR_SOURCE
        and r.r2.digest(files["plan.json"]) == PREDECESSOR_PLAN
        and report["classification"] == "no_usable_incumbent"
        and report["native_status"] == "timelimit" and not report["has_usable_incumbent"]
        and report["operational_receipts_closed"] and not report["quality_target_met"],
        "Original four-hour SCIP predecessor differs.",
    )
    return {
        "archive_sha256": PREDECESSOR_SHA, "source_commit": PREDECESSOR_SOURCE,
        "plan_sha256": PREDECESSOR_PLAN, "review": report,
        "original_review_sha256": r.r2.digest(files["review.json"]),
        "original_native_terminal_sha256": r.r2.digest(files["control/sto/native_terminal.json"]),
    }


def check_predecessor(record):
    r.require(
        record["archive_sha256"] == PREDECESSOR_SHA
        and record["source_commit"] == PREDECESSOR_SOURCE
        and record["plan_sha256"] == PREDECESSOR_PLAN
        and record["review"]["job_id"] == "2225638"
        and record["review"]["classification"] == "no_usable_incumbent"
        and record["review"]["operational_receipts_closed"]
        and not record["review"]["has_usable_incumbent"],
        "Sealed four-hour predecessor differs.",
    )


def recheck_inputs(plan):
    d.recheck_inputs(plan)
    r.require(
        r.file_hash(o.regular(Path(plan["input_paths"]["scip_predecessor"])))
        == PREDECESSOR_SHA == plan["input_sha256"]["scip_predecessor"],
        "Original SCIP archive changed.",
    )


ADMISSION_COMMAND = [
    "sbatch", "--test-only", "--account=sxdsouza", "--partition=intel-256",
    "--qos=preempt", "--nodes=1", "--ntasks=1", "--cpus-per-task=24",
    "--mem=192G", "--time=12:00:00", "--no-requeue", "--wrap=/usr/bin/true",
]


def admission_test():
    """Human CLI only: Slurm validation, no job or executable is launched."""
    result = r.r2.command(ADMISSION_COMMAND, timeout=30)
    r.require(result.returncode == 0, "12h scheduler preflight rejected; no claim/job created.")
    return {"argv": ADMISSION_COMMAND, "returncode": result.returncode,
            "stdout": result.stdout, "stderr": result.stderr, "job_submitted": False}


def closed():
    return {
        **r.closed(), "highs_execution_admitted": False,
        "additional_scip_execution_admitted": False,
    }


def budget():
    per = sum(PROFILE[k] for k in (
        "build_input_seconds_per_arm", "native_time_limit_seconds_per_arm",
        "late_return_export_seconds_per_arm", "validation_seconds_per_arm",
    ))
    planned = per + PROFILE["setup_cleanup_seconds"]
    r.require(per == 35100 and planned == 36900 and planned < 43200, "Budget ledger.")
    return {
        "step_seconds": per, "planned_seconds": planned, "reserve_seconds": 6300,
        "reservation_logical_cpu_hours": 288,
        "scope": "One observation; allocation product, not measured utilization.",
        **closed(),
    }


def spec(workbook):
    original = o.specs(workbook)[1]
    return replace(
        original, name=CASE, max_estimated_variables=16000000,
        solver=replace(
            original.solver, backend="pyscipopt", solver_name="scip",
            time_limit=28800, threads=4, tee=True, log_file="scip-native.log",
            solver_options={"limits/memory": 163840},
        ),
    )


def case_contract(cases):
    from src.logic.experiment_runner import load_experiment_manifest

    template = load_experiment_manifest(r.MANIFEST).experiments[1]
    expected = {
        "name": CASE, "workbook_sha256": o.WORKBOOK_SHA,
        "loader": asdict(template.loader), "model": asdict(template.model),
        "solver": asdict(replace(
            template.solver, backend="pyscipopt", solver_name="scip", time_limit=28800,
            threads=4, tee=True, log_file="scip-native.log",
            solver_options={"limits/memory": 163840},
        )),
        "max_estimated_variables": 16000000, "metadata": template.metadata,
    }
    r.require(
        len(cases) == 1
        and {k: v for k, v in cases[0].items() if k != "workbook"}
        == r.strict_json(r.r2.encoded(expected)),
        "Frozen one-arm scalar SCIP contract differs.",
    )


def environment():
    """Installed metadata/native bytes only; never import a solver on login."""
    dist = distribution("pyscipopt")
    r.require(dist.version == "6.2.1", "Existing PySCIPOpt6.2.1 required; no installation.")
    native = {}
    for item in dist.files or []:
        name = str(item)
        if name.endswith((".so", ".pyd", ".dll", ".dylib")) or ".so." in name:
            path = Path(dist.locate_file(item))
            r.require(path.is_file() and not path.is_symlink(), "Native dependency missing/link.")
            native[name] = r.file_hash(path)
    r.require(native, "Native distribution fingerprint unavailable.")
    return {"pyscipopt": dist.version, "python": platform.python_version(), "native_sha256": native}


def output_location(claim):
    home = Path("/home/vrrcelestino").resolve()
    parent = claim.parent.resolve()
    r.require(
        not claim.is_symlink() and claim.name == CLAIM
        and parent.parent == home and parent.name.startswith("model-agrologistic")
        and parent.name != "model-agrologistic",
        "Use a dedicated model-agrologistic output sibling, never home/input checkout.",
    )


def design(files):
    plan = r.strict_json(files["plan.json"])
    previous = r.strict_json(files["historical_w.json"])
    source = r.strict_json(files["source.json"])
    selection = r.strict_json(files["warehouse_selection.json"])
    r.require(
        plan["schema_version"] == "scalar-scip-h215-w-native8h-v1"
        and plan["profile"] == PROFILE and plan["budget"] == budget()
        and plan["expected_shape"] == SHAPE
        and all(plan[k] == v for k, v in closed().items()),
        "SCIP scope/resource/admission differs.",
    )
    case_contract(plan["cases"])
    probe = r.strict_json(files["admission_test.json"])
    r.require(probe["argv"] == ADMISSION_COMMAND and probe["returncode"] == 0
              and probe["job_submitted"] is False, "12h admission preflight differs.")
    check_predecessor(r.strict_json(files["scip_predecessor.json"]))
    for name in (
        "source.json", "historical_w.json",
        "warehouse_selection.json", "materialization.original.json",
        "scip_predecessor.json", "admission_test.json",
    ):
        r.require(r.r2.digest(files[name]) == plan["artifact_sha256"][name], "Plan artifact drift.")
    r.require(
        re.fullmatch(r"[0-9a-f]{40}", plan["source_commit"])
        and source["source_commit"] == plan["source_commit"]
        and previous["archive_sha256"] == g.W_SHA
        and previous["source_commit"] == g.W_SOURCE and previous["plan_sha256"] == g.W_PLAN
        and previous["review"]["job_id"] == "2217990"
        and previous["review"]["status"] == "pair_quality_target_met",
        "Historical W/source binding differs.",
    )
    r.require(
        {k: v for k, v in source["files"].items() if k.startswith("src/logic/")}
        == previous["scientific_sources"], "Scientific source changed from original scalar W.",
    )
    o.materialization(r.strict_json(files["materialization.original.json"]))
    r.require(
        selection["target_population"] == 215
        and selection["population_manifest_sha256"] == o.POPULATION_SHA
        and selection["population_order_sha256"] == o.ORDER_SHA,
        "Frozen h215 membership differs.",
    )
    r.require(
        plan["input_sha256"] == {
            "workbook": o.WORKBOOK_SHA, "population": o.POPULATION_SHA, "order": o.ORDER_SHA,
            "w_archive": g.W_SHA, "scip_predecessor": PREDECESSOR_SHA,
            "materialization": plan["artifact_sha256"]["materialization.original.json"],
        }
        and plan["environment"]["pyscipopt"] == "6.2.1",
        "Frozen inputs/runtime differ.",
    )
    return plan


def plan_files(claim):
    return {n: o.regular(claim / n).read_bytes() for n in (
        "plan.json", "source.json", "historical_w.json",
        "warehouse_selection.json", "materialization.original.json",
        "scip_predecessor.json", "admission_test.json",
    )}


def prepare(claim, sha, **paths):
    output_location(claim)
    r.require(not claim.exists(), "Fresh exclusive SCIP claim required; preserve old claim.")
    frozen = {k: o.regular(paths[k]) for k in INPUT_KEYS}
    hashes = {k: r.file_hash(p) for k, p in frozen.items()}
    r.require(hashes["workbook"] == o.WORKBOOK_SHA, "Original h215 workbook checksum differs.")
    material = frozen["materialization"].read_bytes()
    o.materialization(r.strict_json(material))
    selection = r.warehouses.read_policy(
        frozen["population"], frozen["order"], o.POPULATION_SHA, o.ORDER_SHA, 215,
    )
    previous = g.historical_w(frozen["w_archive"])
    scip_previous = inspect_predecessor(frozen["scip_predecessor"])
    inventory = g.source_inventory(ROOT)
    r.require(inventory["source_commit"] == sha, "Exact source SHA required.")
    tools = {k: str(o.regular(Path(shutil.which(k) or "").resolve())) for k in o.TOOLS}
    artifacts = {
        "source.json": r.r2.encoded(inventory), "historical_w.json": r.r2.encoded(previous),
        "warehouse_selection.json": r.r2.encoded(selection),
        "materialization.original.json": material,
        "scip_predecessor.json": r.r2.encoded(scip_previous),
        "admission_test.json": r.r2.encoded(admission_test()),
    }
    plan = {
        "schema_version": "scalar-scip-h215-w-native8h-v1", "source_commit": sha,
        "source_root": str(ROOT), "python": sys.executable,
        "python_sha256": r.file_hash(sys.executable), "environment": environment(),
        "tools": tools, "tool_sha256": {k: r.file_hash(p) for k, p in tools.items()},
        "input_paths": {k: str(v.resolve()) for k, v in frozen.items()},
        "input_sha256": hashes,
        "artifact_sha256": {n: r.r2.digest(b) for n, b in artifacts.items()},
        "cases": [r.spec_payload(spec(frozen["workbook"]))], "profile": PROFILE,
        "budget": budget(), "expected_shape": SHAPE, **closed(),
    }
    artifacts["plan.json"] = r.r2.encoded(plan)
    design(artifacts)
    recheck_inputs(plan)
    r.r2.verify_source(inventory, ROOT)
    claim.mkdir(mode=0o700)
    for name, content in artifacts.items():
        with (claim / name).open("xb") as stream:
            stream.write(content)
    return plan


def load(claim, sha):
    output_location(claim)
    files = plan_files(claim)
    plan = design(files)
    r.require(
        plan["source_commit"] == sha and Path(plan["source_root"]).resolve() == ROOT,
        "Exact source/root mismatch.",
    )
    r.r2.verify_source(r.strict_json(files["source.json"]), ROOT)
    r.require(
        r.file_hash(sys.executable) == plan["python_sha256"]
        and environment() == plan["environment"],
        "Existing interpreter/native distribution changed.",
    )
    recheck_inputs(plan)
    return plan


def invocation(action, claim, sha, *extra):
    return [
        sys.executable, "-B", "-I", "-c",
        "import runpy,sys;sys.dont_write_bytecode=True;sys.path.insert(0,sys.argv.pop(1));"
        "runpy.run_module('scripts.mvp2_scalar_scip_h215_8h',run_name='__main__')",
        str(ROOT), action, "--claim", str(claim), "--source-sha", sha, *extra,
    ]


def start(claim, sha, acknowledged, paths, *, command=r.r2.command):
    r.require(acknowledged, "Explicit human one-reviewed-SCIP-W acknowledgement required.")
    output_location(claim)
    r.require(
        sys.version_info[:2] == (3, 13) and not os.environ.get("SLURM_JOB_ID"),
        "Login Python3.13 only.",
    )
    r.require(not claim.exists(), "Existing SCIP claim: inspect/collect, never submit again.")
    plan = prepare(claim, sha, **paths)
    token = r.r2.digest(r.r2.encoded(plan))
    with (claim / "batch.sh").open("x", newline="\n") as stream:
        stream.write("#!/bin/sh\nexec " + shlex.join(invocation("batch", claim, sha)) + "\n")
    r.r2.write(claim / "submission_intent.json", {
        "plan_sha256": token, "one_Scip_W_acknowledged": True, "automatic_retry": False,
    })
    result = command([
        "sbatch", "--parsable", "--account=sxdsouza", "--partition=intel-256", "--qos=preempt",
        "--nodes=1", "--ntasks=1", "--cpus-per-task=24", "--mem=192G", "--time=12:00:00",
        "--no-requeue", "--export=ALL", "--job-name=scalar-scip-h215-W-native8h",
        "--chdir=" + str(claim), "--output=" + str(claim / "slurm.out"),
        "--error=" + str(claim / "slurm.err"), str(claim / "batch.sh"),
    ])
    r.r2.write(claim / "submission.json", {
        "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr,
    })
    match = re.fullmatch(r"([1-9][0-9]*)(?:;[A-Za-z0-9_.-]+)?\s*", result.stdout)
    r.require(
        result.returncode == 0 and match, "Submission uncertain; preserve claim, never retry."
    )
    job = {"job_id": match[1], "source_commit": sha, "plan_sha256": token}
    o.publish(claim / "job.json", job)
    return {"status": "submitted_one_scalar_scip_W_only", **job, **closed()}


def inspect_native():
    """Compute-only native build identity without optimizing the population."""
    import pyscipopt

    model = pyscipopt.Model("build_identity_only")
    buffer = io.StringIO()
    try:
        model.redirectOutput()
        with contextlib.redirect_stdout(buffer):
            model.printVersion()
            model.printExternalCodeVersions()
        native = ".".join(str(f()) for f in (
            model.getMajorVersion, model.getMinorVersion, model.getTechVersion,
        ))
    finally:
        model.freeProb()
    banner = buffer.getvalue()
    r.require(
        pyscipopt.__version__ == "6.2.1" and native == "10.0.2"
        and re.search(r"SoPlex\s+8\.0\.2\b", banner),
        "SCIP10.0.2/SoPlex8.0.2 build required; preserve unexpected build, no population solve.",
    )
    return {
        "pyscipopt": pyscipopt.__version__, "scip": native, "lp_solver": "SoPlex8.0.2",
        "native_banner": banner, "population_optimized": False,
    }


def run_math(control):
    """Fresh scalar analytical/integration gate on the SAME compute environment."""
    import pytest

    names = {n.replace("gurobipy", "pyscipopt") for n in r.r2.TESTS}
    report = control / "qualification.xml"
    exit_code = pytest.main([
        str(ROOT / "tests/test_scalar_contract.py"), "-k", "pyscipopt",
        "-p", "no:cacheprovider", "--basetemp=" + str(control / "qualification-cases"),
        "--junitxml=" + str(report), "-q",
    ])
    import xml.etree.ElementTree as et

    root = et.fromstring(report.read_bytes())
    cases = list(root.iter("testcase"))
    r.require(
        exit_code == 0 and len(cases) == 9 and {c.get("name") for c in cases} == names
        and all(not any(e.tag in {"failure", "error", "skipped"} for e in c) for c in cases)
        and all(int(s.get(k, "0")) == 0 for s in root.iter("testsuite")
                for k in ("failures", "errors", "skipped")),
        "Fresh scalar SCIP mathematical gate failed/skipped.",
    )
    return {"tests": 9, "failures": 0, "errors": 0, "skipped": 0, "status": "accepted"}


def compare_input(specification, data, receipt, previous):
    cell = g.inspect_cell(specification, loader=lambda *_: data)
    cell.pop("warehouse_data")
    prior = previous["receipts"]["sto"]
    r.require(
        receipt["warehouse_selection"] == prior["warehouse_selection"]
        and cell["contract"] == prior["mathematical_contract"]
        and cell["effective_probabilities"] == prior["effective_scenario_probabilities"]
        and len(cell["edges"]["oc"]) == 0
        and {k: len(v) for k, v in cell["edges"].items()}
        == {"od": 3182, "dc": 3440, "dd": 18490, "oc": 0},
        "Same original W input/membership/graph/objective/scenarios required.",
    )


def run_case(selected, target, selection, control, entry, previous):
    """Observe existing resource phases; no mathematical/solver backend edits."""
    from src.logic.experiment_runner import run_experiment
    from src.logic.optimization import solve_model
    from src.logic.resource_telemetry import CURRENT

    names = []
    origin = entry["started_monotonic"]

    def mark(name):
        r.require(name == o.PHASES[len(names)], "Phase order differs.")
        o.publish(control / f"phase-{len(names):02d}.json", {
            "entry": entry, "phase": name,
            "elapsed_seconds": 0.0 if not names else time.monotonic() - origin,
        })
        names.append(name)

    mark("input_build")

    def solve(*, data, model_config, solver_config):
        session = CURRENT.get()
        r.require(session is not None, "Original telemetry required.")
        phase = session.phase

        def observed(name):
            phase(name)
            if name == "optimization":
                mark("optimization")
            elif name == "result_extraction":
                mark("native_return")

        session.phase = observed
        try:
            result = solve_model(data, model_config, solver_config)
        finally:
            session.phase = phase
        if names[-1] == "optimization":
            mark("native_return")  # No incumbent: no result-extraction event.
        metadata = result.metadata
        r.require(metadata["effective_scip_parameters"] == EXPECTED_PARAMS, "Effective SCIP drift.")
        o.publish(control / "native_terminal.json", {
            "entry": entry, "status": metadata["scip_status"],
            "solution_count": metadata["solution_count"],
            "runtime_seconds": metadata["timings"]["solver_reported_runtime_seconds"],
            "time_limit_seconds": solver_config.time_limit,
            "effective_parameters": metadata["effective_scip_parameters"],
        })
        mark("independent_validation")
        return result

    def progress(message):
        if "exporting structured artifacts" in message:
            mark("artifact_export")

    def runner(*args, **kwargs):
        kwargs.update(solver=solve, progress=progress)
        return run_experiment(*args, **kwargs)

    result = r.run_case_software(
        selected, target, SHAPE, selection, runner=runner,
        input_reviewer=lambda data, receipt: compare_input(selected, data, receipt, previous),
    )
    mark("complete")
    return result


def worker(claim, sha, mode):
    plan = load(claim, sha)
    job = o.job_receipt(claim, sha)
    step = os.environ.get("SLURM_STEP_ID", "")
    r.require(
        mode == "sto" and os.environ.get("SLURM_JOB_ID") == job["job_id"] and step.isdigit(),
        "Owned numeric SCIP step required.",
    )
    control = claim / "control/sto"
    entry = {
        **job, "mode": mode, "step_id": step, "pid": os.getpid(),
        "proc_start_ticks": proc_start(os.getpid()),
        "started_monotonic": time.monotonic(),
    }
    o.publish(control / "entry.json", entry)
    until = time.monotonic() + 60
    while not (control / "release.json").exists() and time.monotonic() < until:
        time.sleep(0.1)
    r.require(r.r2.read(control / "release.json") == entry, "Exact-step release required.")
    o.verify_tools(plan)
    recheck_inputs(plan)
    affinity = sorted(os.sched_getaffinity(0))
    r.require(4 <= len(affinity) == len(set(affinity)) <= 24, "Observed affinity differs.")
    native = inspect_native()
    r.r2.write(control / "native_build.json", native)
    r.r2.write(control / "qualification.json", run_math(control))
    r.r2.write(control / "runtime.json", {
        "python": platform.python_version(), "python_sha256": r.file_hash(sys.executable),
        "affinity_logical_cpus": affinity, "solver_threads": 4, "native": native,
        "hardware": d.hardware_observation(),
        "scope": "Thread ceilings, not observed parallel execution.",
    })
    selected = spec(Path(plan["cases"][0]["workbook"]))
    r.require(
        r.strict_json(r.r2.encoded(r.spec_payload(selected))) == plan["cases"][0],
        "Frozen SCIP case drift.",
    )
    # Native logfile is private evidence inside the owned control directory.
    r.require(Path.cwd().resolve() == control.resolve(), "Native log must stay in owned control.")
    run_case(
        selected, claim / "cases" / selected.name,
        r.r2.read(claim / "warehouse_selection.json"), control, entry,
        r.r2.read(claim / "historical_w.json"),
    )
    recheck_inputs(plan)
    load(claim, sha)


def snapshot(claim):
    """Retain real pytest products once; only internal generated aliases are skipped."""
    files = {}
    for path in sorted(claim.rglob("*")):
        if path.is_symlink():
            r.require(
                path.name.endswith("current")
                and path.resolve().is_relative_to(
                    (claim / "control/sto/qualification-cases").resolve()
                ),
                "Linked evidence rejected.",
            )
            continue
        if not path.is_file():
            continue
        name = path.relative_to(claim).as_posix()
        if name in {ARCHIVE, ARCHIVE + ".sha256", "collection.json"}:
            continue
        public_fixture = path.is_relative_to(claim / "control/sto/qualification-cases")
        r.require(
            r._safe_name(name) and path.suffix.lower() not in {".lic", ".sqlite3"}
            and (path.suffix.lower() != ".xlsx" or public_fixture),
            "Forbidden private evidence member.",
        )
        r.require(path.stat().st_size <= 1024**3, "Evidence cap, no truncation.")
        files[name] = path.read_bytes()
        r.require(len(files) <= 4094 and sum(map(len, files.values())) <= 1024**3, "Transfer cap.")
    return files


def case_review(files, plan):
    base = "cases/" + CASE + "/products/" + CASE + "/"
    result = r.strict_json(files[base + "result.json"])
    native = result["result"]
    completion = r.strict_json(files[base + "run_completion.json"])
    validation = r.strict_json(files[base + "independent_validation.json"])
    summary = r.strict_json(files[base + "run_summary.json"])
    r.require(
        result["schema_version"] == 2 and result["experiment"] == plan["cases"][0]
        and native["solver_backend"] == "pyscipopt" and native["model_mode"] == "sto"
        and completion["status"] == "complete"
        and completion["run_identity"] == native["metadata"]["run_identity"],
        "Original scalar SCIP completion/identity differs.",
    )
    required = {"result.json", "run_summary.json", "independent_validation.json",
                "preflight.json", "model_audit.json"}
    r.require(required <= completion["artifacts"].keys(), "Incomplete products.")
    for name, digest in completion["artifacts"].items():
        r.require(r._safe_name(name) and r.r2.digest(files[base + name]) == digest,
                  "Original completion artifact drift.")
    receipt = r.strict_json(files["cases/" + CASE + "/input_receipt.json"])
    population = r.strict_json(files["cases/" + CASE + "/warehouses_used.json"])
    historical = r.strict_json(files["historical_w.json"])["receipts"]["sto"]
    r.require(
        receipt["experiment"] == plan["cases"][0]
        and receipt["mathematical_contract"] == historical["mathematical_contract"]
        and receipt["effective_scenario_probabilities"]
        == historical["effective_scenario_probabilities"]
        and receipt["warehouse_selection"] == population == historical["warehouse_selection"]
        and files["cases/" + CASE + "/warehouses_used.csv"]
        == r.warehouses.csv_bytes(population["included"]),
        "Original W input/selection/scenario certificate binding differs.",
    )
    metadata = native["metadata"]
    r.require(
        metadata["effective_scip_parameters"] == EXPECTED_PARAMS, "Effective native settings."
    )
    from src.logic.optimization import OptimizationResult, scalar_mip_gap

    usable = OptimizationResult(
        status=native["status"], objective_value=native["objective_value"],
    ).has_solution
    accepted = (usable and validation["status"] == "accepted"
                and validation["failed_check_count"] == 0)
    r.require(
        summary["independent_validation_status"] == validation["status"], "Validation summary."
    )
    if accepted:
        r.require(
            validation["validator_version"] == "mvp2-scalar-independent-residuals-v1"
            and validation["absolute_tolerance"] == 1e-5
            and validation["relative_tolerance"] == 1e-8
            and all(f["failed"] == 0 for f in validation["families"].values()),
            "Original independent residual contract differs.",
        )
    gap = scalar_mip_gap(native["objective_value"], native.get("objective_bound"))
    quality = accepted and gap is not None and gap <= 0.01
    classification = (
        "quality_target_met" if quality else
        "validated_feasible_above_target_or_uncertified_bound" if accepted else
        "incumbent_validation_rejected" if usable else "no_usable_incumbent"
    )
    return {
        "classification": classification, "quality_target_met": quality,
        "has_usable_incumbent": usable, "original_validation_status": validation["status"],
        "objective": native["objective_value"], "bound": native.get("objective_bound"),
        "common_gap": gap, "native_gap": metadata.get("scip_native_gap"),
        "native_status": metadata["scip_status"], "timings": metadata["timings"],
        "economic_cost": summary.get("economic_cost"),
        "penalized_total": summary.get("penalized_cost"),
        "interpretation": "One original SCIP observation; no open-source impossibility inference.",
        **closed(),
    }


def review_arm(claim, sha, mode):
    r.require(mode == "sto", "One STO arm only.")
    report = case_review(snapshot(claim), load(claim, sha))
    r.r2.write(claim / "control/sto/review.json", report)
    return report


def review_process(claim, sha, mode, remaining):
    control = claim / "control" / mode
    with (control / "review.out").open("xb") as out, (control / "review.err").open("xb") as err:
        result = subprocess.run(
            invocation("review", claim, sha, "--mode", mode),
            stdout=out, stderr=err, timeout=remaining, check=False,
        )
    r.require(result.returncode == 0, "Original review failed; preserve diagnostics.")


def batch(claim, sha):
    job_id = os.environ.get("SLURM_JOB_ID", "")
    result = {"status": "forensic_partial", "completed_modes": [], **closed()}
    try:
        r.require(job_id.isdigit(), "Compute allocation only.")
        plan = load(claim, sha)
        o.verify_tools(plan)
        job = o.job_receipt(claim, sha)
        r.require(job["job_id"] == job_id, "Job binding.")
        r.r2.write(claim / "batch_entry.json", job)
        query = r.r2.command(["scontrol", "-o", "show", "job", job_id], timeout=15)
        r.r2.write(claim / "allocation_query.json", {
            "returncode": query.returncode, "stdout": query.stdout, "stderr": query.stderr,
        })
        r.require(query.returncode == 0, "Allocation query failed.")
        allocated = o.allocation(query.stdout, job_id, os.getuid(), walltime="12:00:00")
        r.r2.write(claim / "allocation.json", allocated)
        # Four-thread ceiling with a 16-logical-CPU affinity pool; remaining CPUs are allocation.
        control = claim / "control/sto"
        control.mkdir(parents=True, exist_ok=False)
        # supervise owns creation of the leaf; its srun worker gets this explicit cwd.
        control.rmdir()
        def invoke(action, claim, sha, *extra):
            return ["--chdir=" + str(claim / "control/sto"),
                    *invocation(action, claim, sha, *extra)]
        observer = ExternalObserver(claim, job)
        try:
            outcome = o.supervise(
                claim, sha, "sto", allocated, job, invoke=invoke,
                reviewer=review_process, step_cpus=16,
                bind_step=lambda *a: o.step_binding(*a, cpus=16),
                whole_arm_seconds=35100, phase_profile=PROFILE,
                sleep=observer.sleep,
            )
        finally:
            observer.finish()
        r.require(outcome["status"] == "closed_feasible_arm", "SCIP step not operationally closed.")
        load(claim, sha)
        result.update(status="one_scip_observation_returned", completed_modes=["sto"],
                      source_verified_after=True)
    except Exception as exc:
        result["error_kind"] = type(exc).__name__
    r.r2.write(claim / "batch_outcome.json", result)
    return int(result["status"] != "one_scip_observation_returned")


def portable_review(files):
    plan = design(files)
    job = r.strict_json(files["job.json"])
    r.require(
        re.fullmatch(r"[1-9][0-9]*", job["job_id"])
        and job["source_commit"] == plan["source_commit"]
        and job["plan_sha256"] == r.r2.digest(files["plan.json"]),
        "Original job/source/plan differs.",
    )
    rows = r.r2.accounting(files["accounting.txt"].decode(), job["job_id"])
    r.require(r.r2.terminal(rows, job["job_id"]), "Terminal accounting required.")
    assessment = {"classification": "build_or_execution_incomplete", "quality_target_met": False}
    try:
        assessment = case_review(files, plan)
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        assessment["product_review_error_kind"] = type(exc).__name__
    operational, error = False, None
    try:
        query = r.strict_json(files["allocation_query.json"])
        allocated = r.strict_json(files["allocation.json"])
        owner = re.fullmatch(r"[^()]+\(([0-9]+)\)", o.fields(query["stdout"])["UserId"])
        r.require(query["returncode"] == 0 and owner, "Allocation owner/query.")
        r.require(o.allocation(query["stdout"], job["job_id"], int(owner[1]),
                               walltime="12:00:00") == allocated, "Allocation replay.")
        r.require(r.strict_json(files["batch_entry.json"]) == job, "Batch entry.")
        base = "control/sto/"
        entry = r.strict_json(files[base + "entry.json"])
        r.require(
            all(entry[k] == v for k, v in job.items()) and entry["mode"] == "sto"
            and r.strict_json(files[base + "release.json"]) == entry, "Owned release.",
        )
        query = r.strict_json(files[base + "step_query.json"])
        r.require(query["returncode"] == 0, "Step query.")
        exact = o.step_binding(query["stdout"], entry, allocated, int(owner[1]), cpus=16)
        events = [r.strict_json(files[n]) for n in sorted(files) if n.startswith(base + "phase-")]
        r.require(
            events and events[-1]["phase"] == "complete"
            and all(e["entry"] == entry for e in events), "Phase identity/closure.",
        )
        usage = o.phase_usage(events, events[-1]["elapsed_seconds"], profile=PROFILE)
        control = r.strict_json(files[base + "controller.json"])
        terminal = r.strict_json(files[base + "terminal_step.json"])
        r.require(
            terminal["row"] in r.r2.accounting(terminal["raw"], job["job_id"])
            and terminal["row"]["job_id"] == exact
            and terminal["row"]["state"] == "COMPLETED" and terminal["row"]["exit_code"] == "0:0",
            "Owned-step terminal closure.",
        )
        r.require(
            control["status"] == "closed_feasible_arm" and control["local_client_reaped"]
            and control["step_id"] == entry["step_id"] and control["usage"] == usage
            and usage["stop_reason"] is None
            and control["product_review_seconds"] >= 0
            and control["product_review_seconds"]
            + usage["seconds"]["independent_validation"] <= 1800,
            "Controller/phase budget.",
        )
        r.require(
            r.strict_json(files[base + "review.json"]) == assessment, "Post-worker review drift."
        )
        runtime = r.strict_json(files[base + "runtime.json"])
        build = r.strict_json(files[base + "native_build.json"])
        r.require(
            build == runtime["native"] and build["pyscipopt"] == "6.2.1"
            and build["scip"] == "10.0.2" and build["lp_solver"] == "SoPlex8.0.2"
            and re.search(r"SoPlex\s+8\.0\.2\b", build["native_banner"]),
            "Native LP provenance.",
        )
        r.require(
            runtime["python"] == plan["environment"]["python"]
            and runtime["python_sha256"] == plan["python_sha256"] and runtime["solver_threads"] == 4
            and 4 <= len(runtime["affinity_logical_cpus"])
            == len(set(runtime["affinity_logical_cpus"])) <= 24,
            "Runtime/affinity.",
        )
        r.require(r.strict_json(files[base + "qualification.json"]) == {
            "tests": 9, "failures": 0, "errors": 0, "skipped": 0, "status": "accepted",
        }, "Fresh scalar math qualification.")
        native = r.strict_json(files[base + "native_terminal.json"])
        r.require(
            native["entry"] == entry and native["effective_parameters"] == EXPECTED_PARAMS
            and native["time_limit_seconds"] == 28800
            and 0 <= native["runtime_seconds"] <= 29700, "Native budget/parameters.",
        )
        numerical = {x["job_id"] for x in rows
                     if "." in x["job_id"] and x["job_id"].split(".")[-1].isdigit()}
        r.require(
            numerical == {exact}
            and {job["job_id"], job["job_id"] + ".batch", exact} <= {x["job_id"] for x in rows}
            and all(x["state"] == "COMPLETED" and x["exit_code"] == "0:0"
                    and x["elapsed_seconds"] <= (35100 if x["job_id"] == exact else 43200)
                    for x in rows), "Accounting closure.",
        )
        r.require(r.strict_json(files["batch_outcome.json"])["status"]
                  == "one_scip_observation_returned", "Batch closure.")
        operational = True
    except (ValueError, KeyError, TypeError, IndexError, StopIteration) as exc:
        error = type(exc).__name__
    return {
        **assessment, "external_observation": review_external(files, job), "status": (
            "scip_quality_target_met" if operational and assessment["quality_target_met"] else
            "scip_returned_quality_not_met" if operational else "scip_forensic_partial_preserved"
        ),
        "operational_receipts_closed": operational, "operational_error_kind": error,
        "source_commit": plan["source_commit"], "job_id": job["job_id"],
        "accounting": rows, "production_isolation_certified": False, **closed(),
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
    parser.add_argument("--one-reviewed-scip-w", action="store_true")
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
                args.one_reviewed_scip_w,
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

