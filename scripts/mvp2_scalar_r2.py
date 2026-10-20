"""One small academic R2 allocation; no production isolation or follow-on admission."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import tarfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
CLAIM = ".mvp2-scalar-r2-v1"
PROFILE = {
    "logical_cpus": 4,
    "memory_mib": 8192,
    "wall_seconds": 1200,
    "solver_threads": 1,
    "case_time_limit_ceiling": 60,
}
STEP_SECONDS = 900
MAX_BYTES = 64 * 1024 * 1024
MAX_FILES = 4096
TERMINAL = {
    "COMPLETED",
    "FAILED",
    "CANCELLED",
    "TIMEOUT",
    "OUT_OF_MEMORY",
    "NODE_FAIL",
    "PREEMPTED",
    "BOOT_FAIL",
    "DEADLINE",
    "REVOKED",
}
TESTS = {
    "test_det_equals_one_scenario_sto_and_hand_calculated_cost[gurobipy]",
    *(
        f"test_three_distinct_slacks_have_separate_units_and_penalties[{k}-gurobipy]"
        for k in ("unmet", "static", "reception")
    ),
    "test_expected_cost_uses_unequal_probabilities[gurobipy]",
    "test_duplicate_scenario_split_keeps_investment_once[gurobipy]",
    "test_timeout_without_incumbent_is_not_a_feasible_solution[gurobipy]",
    *(
        f"test_real_excel_to_independent_validation_and_closed_artifacts[{m}-gurobipy]"
        for m in ("det", "sto")
    ),
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def write(path, value):
    """Exclusive evidence files: failure never replaces an earlier receipt."""
    with Path(path).open("xb") as stream:
        stream.write(encoded(value))


def command(argv, *, timeout=30, **kwargs):
    return subprocess.run(
        argv, capture_output=True, text=True, timeout=timeout, check=False, **kwargs
    )


def source_inventory(root=ROOT):
    head = command(["git", "rev-parse", "HEAD"], cwd=root)
    require(head.returncode == 0, "Login source Git unavailable.")
    listing = command(["git", "ls-files", "-z"], cwd=root)
    require(listing.returncode == 0, "Tracked inventory unavailable.")
    files = {}
    for name in filter(None, listing.stdout.split("\0")):
        path = root / name
        require(path.is_file() and not path.is_symlink(), "Tracked file missing/link.")
        expected = subprocess.check_output(["git", "show", "HEAD:" + name], cwd=root)
        require(path.read_bytes() == expected, "Raw HEAD-byte mismatch: " + name)
        files[name] = digest(expected)
    return {"source_commit": head.stdout.strip(), "files": files}


def verify_source(inventory, root=ROOT):
    for name, sha in inventory["files"].items():
        require(
            not PurePosixPath(name).is_absolute() and ".." not in PurePosixPath(name).parts,
            "Unsafe inventory path.",
        )
        path = root / name
        require(
            path.is_file() and not path.is_symlink() and digest(path.read_bytes()) == sha,
            "Source bytes changed: " + name,
        )
    physical = {p.relative_to(root).as_posix() for p in (root / "src").rglob("*.py")}
    require(
        physical == {n for n in inventory["files"] if n.startswith("src/") and n.endswith(".py")},
        "Extra/missing scientific source.",
    )


def invocation(action, claim, sha):
    code = (
        "import runpy,sys;sys.dont_write_bytecode=True;"
        "sys.path.insert(0,sys.argv.pop(1));"
        "runpy.run_module('scripts.mvp2_scalar_r2',run_name='__main__',alter_sys=True)"
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
    ]


def load(claim, sha):
    require(re.fullmatch(r"[0-9a-f]{40}", sha) is not None, "Full source SHA required.")
    plan = read(claim / "plan.json")
    require(
        plan["source_commit"] == sha and plan["profile"] == PROFILE,
        "Claim source/profile mismatch; preserve it.",
    )
    inventory = read(claim / "source.json")
    require(
        digest(encoded(inventory)) == plan["source_inventory_sha256"]
        and inventory["source_commit"] == sha,
        "Source inventory anchor mismatch.",
    )
    return plan, inventory


def start(claim, sha, acknowledged=False):
    require(acknowledged, "Require explicit one-reviewed-R2-only acknowledgement.")
    require(not os.environ.get("SLURM_JOB_ID"), "Start is login-only, never nested.")
    require(claim.name == CLAIM, "Use the exclusive R2 claim name.")
    if claim.exists():
        load(claim, sha)
        require(
            (claim / "job.json").is_file(),
            "Existing claim has no job receipt: preserve; no automatic resubmission.",
        )
        return {"status": "existing_claim_no_resubmission", **read(claim / "job.json")}
    from scripts.probe_npad_gurobi_license import check_file

    check_file()  # Metadata/access only; no solver or license-content read on login.
    inventory = source_inventory()
    require(inventory["source_commit"] == sha, "Checkout is not the requested source.")
    claim.mkdir(exist_ok=False)
    write(claim / "source.json", inventory)
    plan = {
        "schema_version": "scalar-r2-plan-v1",
        "source_commit": sha,
        "profile": PROFILE,
        "source_inventory_sha256": digest(encoded(inventory)),
        "source_root": str(ROOT),
        "python": sys.executable,
        "selected_tests": sorted(TESTS),
        "step_seconds": STEP_SECONDS,
        "archive_expanded_cap_bytes": MAX_BYTES,
        "follow_on_allowed": False,
    }
    write(claim / "plan.json", plan)
    import shlex

    batch_text = "#!/bin/sh\nexec " + shlex.join(invocation("batch", claim, sha)) + "\n"
    with (claim / "batch.sh").open("x", newline="\n") as stream:
        stream.write(batch_text)
    # Durable intent precedes the single submission. An uncertain outcome consumes the claim.
    write(
        claim / "submission_intent.json",
        {"plan_sha256": digest(encoded(plan)), "automatic_retry": False},
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
            "--cpus-per-task=4",
            "--mem=8G",
            "--time=00:20:00",
            "--no-requeue",
            "--job-name=scalar-r2-small",
            "--chdir=" + str(claim),
            "--output=" + str(claim / "slurm.out"),
            "--error=" + str(claim / "slurm.err"),
            str(claim / "batch.sh"),
        ]
    )
    write(
        claim / "submission.json",
        {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr},
    )
    match = re.fullmatch(r"([1-9][0-9]*)(?:;[A-Za-z0-9_.-]+)?\s*", result.stdout)
    require(result.returncode == 0 and match, "Submission uncertain/failed; do not retry.")
    job = {"job_id": match[1], "source_commit": sha, "plan_sha256": digest(encoded(plan))}
    write(claim / "job.json", job)
    return {"status": "submitted_one_small_r2_only", **job}


def allocation(text, job):
    fields = dict(re.findall(r"(?:^|\s)([A-Za-z][A-Za-z0-9_/:]*)=(\S*)", text))
    require(
        fields.get("JobId") == job and fields.get("NumNodes") == "1",
        "Allocation job/node identity.",
    )
    require(
        fields.get("NumCPUs") == "4" and fields.get("CPUs/Task") == "4",
        "Allocation CPUs exceed/differ from approved profile.",
    )
    require(fields.get("TimeLimit") == "00:20:00", "Allocation time differs.")
    require(
        fields.get("Partition") == "intel-256"
        and fields.get("Account") == "sxdsouza"
        and fields.get("QOS") == "preempt",
        "Allocation partition/account differs.",
    )
    # NPAD Slurm22 can expose TRES rather than ReqTRES/AllocTRES. Do not conflate them.
    memory = fields.get("MinMemoryNode")
    require(memory in {"8G", "8192M"}, "Allocation memory request differs.")
    return {
        k: fields.get(k)
        for k in (
            "JobId",
            "NumCPUs",
            "CPUs/Task",
            "NumNodes",
            "TimeLimit",
            "Partition",
            "Account",
            "QOS",
            "NodeList",
            "MinMemoryNode",
            "TRES",
            "ReqTRES",
            "AllocTRES",
        )
    }


def junit_report(raw):
    root = ET.fromstring(raw)
    cases = list(root.iter("testcase"))
    names = [c.get("name") for c in cases]
    require(len(names) == len(TESTS) and set(names) == TESTS, "Selected test inventory differs.")
    require(
        all(
            not list(c) or all(n.tag not in {"failure", "error", "skipped"} for n in c)
            for c in cases
        ),
        "Native test failed/skipped.",
    )
    suites = list(root.iter("testsuite"))
    require(
        suites and sum(int(s.get("tests", "0")) for s in suites) == len(TESTS),
        "JUnit test total differs.",
    )
    require(
        all(int(s.get(k, "0")) == 0 for s in suites for k in ("failures", "errors", "skipped")),
        "JUnit totals failed/skipped.",
    )
    return {"tests": len(names), "failures": 0, "errors": 0, "skipped": 0}


def run_math(directory):
    """Reuse qualified R1 mathematics and original validator; no model/parameter edits."""
    import pytest

    directory.mkdir(exist_ok=False)
    before = time.monotonic()
    original = os.environ.get("AGRO_REQUIRE_NATIVE_SOLVERS")
    os.environ["AGRO_REQUIRE_NATIVE_SOLVERS"] = "1"
    try:
        from tests.test_scalar_contract import qualified_solver

        solver = qualified_solver("gurobipy")
        require(
            solver.threads == 1
            and isinstance(solver.time_limit, (int, float))
            and 0 < solver.time_limit <= PROFILE["case_time_limit_ceiling"],
            "Selected R1 case configuration exceeds approved R2 ceiling.",
        )
        exit_code = pytest.main(
            [
                str(ROOT / "tests/test_scalar_contract.py"),
                "-k",
                "gurobipy",
                "-p",
                "no:cacheprovider",
                "--basetemp=" + str(directory / "cases"),
                "--junitxml=" + str(directory / "tests.xml"),
                "-q",
            ]
        )
    finally:
        if original is None:
            os.environ.pop("AGRO_REQUIRE_NATIVE_SOLVERS", None)
        else:
            os.environ["AGRO_REQUIRE_NATIVE_SOLVERS"] = original
    require(exit_code == 0, "Native mathematical gate failed; preserve pytest evidence.")
    counts = junit_report((directory / "tests.xml").read_bytes())
    return {
        "status": "small_mathematics_accepted",
        **counts,
        "wall_seconds": time.monotonic() - before,
        "native_solver_limit_seconds": solver.time_limit,
        "solver_threads": 1,
        "scope": "8 native mathematical/integration cases plus 1 no-incumbent API case",
    }


def native(claim, sha):
    plan, inventory = load(claim, sha)
    require(os.environ.get("SLURM_JOB_ID", "").isdigit(), "Native gate is compute-only.")
    verify_source(inventory)
    affinity = sorted(os.sched_getaffinity(0))
    require(0 < len(affinity) <= PROFILE["logical_cpus"], "Native affinity exceeds allocation.")
    from scripts.probe_npad_gurobi_license import probe

    capability = probe()  # Existing designated WLS; never copy/read/hash license contents.
    write(claim / "license_capability.json", capability)
    require(capability["status"] == "accepted", "Fresh WLS capability not accepted.")
    report = run_math(claim / "native")
    verify_source(inventory)
    import resource

    usage = resource.getrusage(resource.RUSAGE_SELF)
    report.update(
        job_id=os.environ["SLURM_JOB_ID"],
        source_commit=sha,
        plan_sha256=digest(encoded(plan)),
        source_verified_before_after=True,
        runtime={
            "python": platform.python_version(),
            "affinity_logical_cpus": affinity,
            "peak_self_rss_kib": usage.ru_maxrss,
            "self_user_cpu_seconds": usage.ru_utime,
            "self_system_cpu_seconds": usage.ru_stime,
            "scope": "whole native Python process incl. pytest/license, not solve-only",
        },
        follow_on_allowed=False,
    )
    write(claim / "native_outcome.json", report)


def batch(claim, sha):
    job = os.environ.get("SLURM_JOB_ID", "")
    require(job.isdigit(), "Batch requires a Slurm allocation.")
    phase = "source_and_allocation"
    result = {
        "status": "blocked_or_partial",
        "job_id": job,
        "source_commit": sha,
        "follow_on_allowed": False,
    }
    try:
        plan, inventory = load(claim, sha)
        verify_source(inventory)
        query = command(["scontrol", "-o", "show", "job", job], timeout=15)
        write(
            claim / "allocation_query.json",
            {"returncode": query.returncode, "stdout": query.stdout, "stderr": query.stderr},
        )
        require(query.returncode == 0, "Allocation query failed.")
        observed = allocation(query.stdout, job)
        write(claim / "allocation.json", observed)
        phase = "bounded_native_step"
        with (claim / "worker.out").open("xb") as out, (claim / "worker.err").open("xb") as err:
            # Slurm owns the exact step timeout; no local-PID kill/remote-cleanup inference.
            run = subprocess.run(
                [
                    "srun",
                    "--exact",
                    "--nodes=1",
                    "--ntasks=1",
                    "--cpus-per-task=1",
                    "--time=00:15:00",
                    "--kill-on-bad-exit=1",
                    *invocation("native", claim, sha),
                ],
                stdout=out,
                stderr=err,
                check=False,
            )
        result.update(step_returncode=run.returncode, plan_sha256=digest(encoded(plan)))
        require(run.returncode == 0, "Native step failed; collect forensic evidence.")
        outcome = read(claim / "native_outcome.json")
        require(
            outcome["job_id"] == job and outcome["plan_sha256"] == result["plan_sha256"],
            "Native outcome binding differs.",
        )
        verify_source(inventory)
        result.update(status="small_block_returned", source_verified_after=True)
    except Exception as error:
        # Preserve phase/type, not potentially sensitive exception/connection strings.
        result.update(error_type=type(error).__name__, phase=phase)
    write(claim / "batch_outcome.json", result)
    return int(result["status"] != "small_block_returned")


def accounting(text, job):
    rows = []
    for line in text.splitlines():
        cells = line.split("|")
        require(len(cells) == 5, "Accounting fields differ.")
        identity, state, exit_code, elapsed, rss = cells
        require(
            re.fullmatch(re.escape(job) + r"(?:\.(?:batch|extern|[0-9]+))?", identity),
            "Unexpected accounting identity.",
        )
        require(re.fullmatch(r"[A-Z_]+(?: by [0-9]+)?", state), "Untruncated state required.")
        require(
            re.fullmatch(r"[0-9]+:[0-9]+", exit_code) and elapsed.isdigit(),
            "Accounting exit/time grammar.",
        )
        rows.append(
            {
                "job_id": identity,
                "state": state.split()[0],
                "exit_code": exit_code,
                "elapsed_seconds": int(elapsed),
                "max_rss_raw": rss or None,
            }
        )
    require(len({r["job_id"] for r in rows}) == len(rows), "Duplicate accounting rows.")
    return rows


def observe(claim, sha):
    plan, _ = load(claim, sha)
    job = read(claim / "job.json")
    require(
        job["source_commit"] == sha and job["plan_sha256"] == digest(encoded(plan)),
        "Submission receipt binding differs.",
    )
    result = command(
        [
            "sacct",
            "-j",
            job["job_id"],
            "--noheader",
            "--parsable2",
            "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw,MaxRSS",
        ]
    )
    require(result.returncode == 0, "Accounting query failed; preserve and collect later.")
    return accounting(result.stdout, job["job_id"]), result.stdout


def terminal(rows, job):
    root = next((r for r in rows if r["job_id"] == job), None)
    return bool(root and root["state"] in TERMINAL and all(r["state"] in TERMINAL for r in rows))


def review_products(files):
    """Replay complete original Excel-case certificates without changing their validator."""
    modes = []
    paths = [n for n in files if n.startswith("native/cases/") and n.endswith("/result.json")]
    require(len(paths) == 2, "Both DET/STO Excel artifacts must be preserved.")
    for name in paths:
        root = str(PurePosixPath(name).parent) + "/"
        payload = json.loads(files[name])
        require(payload["schema_version"] == 2, "Scalar result schema differs.")
        mode = payload["experiment"]["model"]["mode"]
        solver = payload["experiment"]["solver"]
        result = payload["result"]
        require(
            mode in {"det", "sto"}
            and result["model_mode"] == mode
            and result["solver_backend"] == "gurobipy"
            and solver["threads"] == 1
            and 0 < solver["time_limit"] <= 60,
            "Excel-case execution contract differs.",
        )
        completion = json.loads(files[root + "run_completion.json"])
        require(
            completion["status"] == "complete"
            and completion["run_identity"] == result["metadata"]["run_identity"],
            "Original completion identity differs.",
        )
        artifacts = completion["artifacts"]
        require(
            {"result.json", "run_summary.json", "independent_validation.json"} <= set(artifacts),
            "Original completion artifact contract incomplete.",
        )
        for member, sha in artifacts.items():
            require(
                not PurePosixPath(member).is_absolute() and ".." not in PurePosixPath(member).parts,
                "Unsafe original completion path.",
            )
            require(digest(files[root + member]) == sha, "Original artifact hash differs.")
        require(
            json.loads(files[root + "independent_validation.json"])["status"] == "accepted",
            "Original independent residuals not accepted.",
        )
        modes.append(mode)
    require(sorted(modes) == ["det", "sto"], "Excel mode inventory differs.")
    return {"closed_excel_cases": modes, "independent_residual_receipts": "accepted"}


def review(files):
    """Independent portable integrity/acceptance replay, not a fresh optimizer call."""
    plan, job = (json.loads(files[n]) for n in ("plan.json", "job.json"))
    require(
        plan["profile"] == PROFILE and plan["selected_tests"] == sorted(TESTS),
        "Portable profile/test scope differs.",
    )
    require(
        digest(files["plan.json"]) == job["plan_sha256"]
        and job["source_commit"] == plan["source_commit"],
        "Portable plan anchor differs.",
    )
    require(
        digest(files["source.json"]) == plan["source_inventory_sha256"]
        and json.loads(files["source.json"])["source_commit"] == plan["source_commit"],
        "Portable source anchor differs.",
    )
    rows = accounting(files["accounting.txt"].decode(), job["job_id"])
    query = json.loads(files["allocation_query.json"])
    require(
        query["returncode"] == 0
        and allocation(query["stdout"], job["job_id"]) == json.loads(files["allocation.json"]),
        "Portable allocation observation differs.",
    )
    require(terminal(rows, job["job_id"]), "Terminal accounting incomplete.")
    require(
        {job["job_id"], job["job_id"] + ".batch", job["job_id"] + ".0"}
        <= {r["job_id"] for r in rows},
        "Required root/batch/native step missing.",
    )
    require(
        all(r["state"] == "COMPLETED" and r["exit_code"] == "0:0" for r in rows),
        "Scheduler/step did not complete normally.",
    )
    capability, outcome, batch_result = (
        json.loads(files[n])
        for n in ("license_capability.json", "native_outcome.json", "batch_outcome.json")
    )
    require(
        capability["status"] == "accepted"
        and capability["probe_variable_count"] == 2001
        and capability["probe_constraint_count"] == 2001
        and abs(capability["objective_value"] - 2001) <= 1e-6,
        "License capability rejected.",
    )
    require(
        outcome["status"] == "small_mathematics_accepted"
        and outcome["plan_sha256"] == job["plan_sha256"]
        and outcome["job_id"] == job["job_id"]
        and outcome["source_commit"] == plan["source_commit"]
        and outcome["source_verified_before_after"] is True
        and outcome["native_solver_limit_seconds"] <= 60
        and outcome["solver_threads"] == 1,
        "Native mathematical receipt differs.",
    )
    require(
        batch_result["status"] == "small_block_returned"
        and batch_result["source_verified_after"] is True
        and batch_result["job_id"] == job["job_id"]
        and batch_result["plan_sha256"] == job["plan_sha256"],
        "Batch receipt differs.",
    )
    counts = junit_report(files["native/tests.xml"])
    products = review_products(files)
    return {
        "status": "small_r2_evidence_accepted",
        **counts,
        **products,
        "source_commit": plan["source_commit"],
        "job_id": job["job_id"],
        "follow_on_allowed": False,
        "production_isolation_certified": False,
        "qualification": "portable receipt/integrity replay; not fresh mathematical re-solve",
    }


def collect(claim, sha):
    if (claim / "collection.json").exists():
        prior = read(claim / "collection.json")
        load(claim, sha)
        require(
            digest((claim / prior["archive"]).read_bytes()) == prior["sha256"],
            "Preserved archive differs; do not regenerate.",
        )
        return prior
    rows, raw = observe(claim, sha)
    job = read(claim / "job.json")["job_id"]
    if not terminal(rows, job):
        return {
            "status": "nonterminal_or_accounting_pending",
            "job_id": job,
            "follow_on_allowed": False,
        }
    terminal_path = claim / "terminal_accounting.json"
    if terminal_path.exists():
        raw = read(terminal_path)["raw"]  # Resume the first preserved terminal observation.
    else:
        write(terminal_path, {"rows": rows, "raw": raw})
    names = (
        "plan.json",
        "source.json",
        "job.json",
        "batch.sh",
        "submission_intent.json",
        "submission.json",
        "allocation_query.json",
        "allocation.json",
        "batch_outcome.json",
        "native_outcome.json",
        "license_capability.json",
        "slurm.out",
        "slurm.err",
        "worker.out",
        "worker.err",
        "terminal_accounting.json",
    )
    files = {}
    for name in names:
        path = claim / name
        require(not path.is_symlink(), "Do not transfer linked evidence.")
        if path.is_file():
            require(path.stat().st_size <= MAX_BYTES, "Evidence file exceeds cap.")
            files[name] = path.read_bytes()
    files["accounting.txt"] = raw.encode()
    require(not (claim / "native").is_symlink(), "Linked native evidence root.")
    for path in sorted((claim / "native").rglob("*")):
        require(not path.is_symlink(), "Do not transfer linked evidence.")
        if path.is_file():
            require(path.stat().st_size <= MAX_BYTES, "Evidence file exceeds transport cap.")
            files[path.relative_to(claim).as_posix()] = path.read_bytes()
    require(
        len(files) <= MAX_FILES and sum(map(len, files.values())) <= MAX_BYTES,
        "Evidence exceeds cap; preserve without truncation; request review.",
    )
    try:
        assessment = review(files)
    except (ValueError, KeyError, ET.ParseError, TypeError):
        assessment = {
            "status": "forensic_evidence_not_accepted",
            "job_id": job,
            "follow_on_allowed": False,
        }
    files["review.json"] = encoded(assessment)
    files["inventory.json"] = encoded({n: digest(b) for n, b in sorted(files.items())})
    require(
        len(files) <= MAX_FILES and sum(map(len, files.values())) <= MAX_BYTES,
        "Final evidence cap exceeded; no truncation.",
    )
    archive = claim / "scalar-r2-evidence.tar.gz"
    import io

    with archive.open("xb") as stream, tarfile.open(fileobj=stream, mode="w:gz") as tar:
        for name, content in sorted(files.items()):
            entry = tarfile.TarInfo(name)
            entry.size = len(content)
            entry.mode = 0o600
            tar.addfile(entry, io.BytesIO(content))
    sha256 = digest(archive.read_bytes())
    with archive.with_suffix(archive.suffix + ".sha256").open("x") as stream:
        stream.write(sha256 + "  " + archive.name + "\n")
    receipt = {
        **assessment,
        "archive": archive.name,
        "sha256": sha256,
        "download": str(archive),
        "transfer_checksum": str(archive) + ".sha256",
    }
    write(claim / "collection.json", receipt)
    return receipt


def audit(archive):
    files = {}
    with tarfile.open(archive, "r:gz") as tar:
        size = 0
        for entry in tar:
            name = PurePosixPath(entry.name)
            require(
                entry.isfile()
                and not name.is_absolute()
                and ".." not in name.parts
                and entry.name not in files,
                "Unsafe/duplicate archive member.",
            )
            size += entry.size
            require(size <= MAX_BYTES and len(files) < MAX_FILES, "Archive cap exceeded.")
            files[entry.name] = tar.extractfile(entry).read()
    inventory = json.loads(files.pop("inventory.json"))
    require(inventory == {n: digest(b) for n, b in files.items()}, "Archive content hash differs.")
    try:
        return review(files)
    except (ValueError, KeyError, ET.ParseError, TypeError):
        return {"status": "forensic_evidence_not_accepted", "follow_on_allowed": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("start", "status", "wait", "collect", "batch", "native", "audit")
    )
    parser.add_argument("--claim", type=Path)
    parser.add_argument("--source-sha")
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--one-reviewed-r2-only", action="store_true")
    args = parser.parse_args(argv)
    if args.action == "audit":
        result = audit(args.archive)
    else:
        require(args.claim is not None and args.source_sha is not None, "Claim/source required.")
        claim = args.claim.resolve()
        if args.action == "start":
            result = start(claim, args.source_sha, args.one_reviewed_r2_only)
        elif args.action == "batch":
            return batch(claim, args.source_sha)
        elif args.action == "native":
            native(claim, args.source_sha)
            return 0
        elif args.action == "status":
            rows, _ = observe(claim, args.source_sha)
            result = {"status": "accounting_observed", "rows": rows, "follow_on_allowed": False}
        else:
            while True:
                result = collect(claim, args.source_sha)
                if args.action != "wait" or result["status"] != "nonterminal_or_accounting_pending":
                    break
                print("R2_NONTERMINAL; Ctrl-C safe; resume wait/collect, never reset.", flush=True)
                time.sleep(20)
    print(json.dumps(result, sort_keys=True, allow_nan=False), flush=True)
    print("NO_REPEAT_OR_LARGER_INSTANCE_ADMITTED", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
