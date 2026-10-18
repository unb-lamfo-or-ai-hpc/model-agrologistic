"""Human-only full-grid successor: one allocation, 3600s per arm, no automatic repeat."""

from __future__ import annotations

import argparse
import gzip
import os
import re
import shlex
import sys
import tarfile
import tempfile
import time
from pathlib import Path

from scripts import mvp2_s2_grid_products as g
from scripts import mvp2_s2_grid_runtime as runtime
from scripts import mvp2_s2_residual_replay as replay

p, d, c, native, old = replay.p, replay.d, replay.c, runtime.native, runtime.native.old
ROOT, BASE, REFERENCE = runtime.ROOT, replay.BASE, replay.prior.REFERENCE
ARCHIVE = "s2-grid3600-evidence.tar.gz"
FLAGS = {
    "additional_blocks_allowed": False,
    "automatic_follow_on_allowed": False,
    "repeats_admitted": False,
    "s2_closed": False,
    "scientific_configuration_selected": False,
    "production_isolation_certified": False,
}
MEMBERS = {"release.json", "prior.tar.gz", "native.tar.gz", "transfer.json", "driver.json"}


def directory():
    return p.safe(BASE / runtime.CLAIM)


def sealed(plan):
    native.validate(plan)
    d.require(
        all(
            name in plan["files"]
            for name in (
                "scripts/mvp2_s2_grid_products.py",
                "scripts/mvp2_s2_grid_runtime.py",
                "scripts/mvp2_s2_grid_release.py",
                "scripts/npad_s2_grid3600.sh",
            )
        ),
        "Complete integrated grid source required.",
    )
    return {
        "schema_version": "s2-grid3600-release-v1",
        "source_commit": plan["preparation"]["source_commit"],
        "native_plan_sha256": d.digest(plan),
        "prior": dict(replay.ANCHORS),
        "order": list(d.ORDER),
        "native_time_limit_seconds": 3600,
        "enforcement": dict(native.CONTRACT),
        "expanded_transfer_limit_bytes": g.LIMIT,
        "per_arm_product_limit_bytes": p.LIMIT,
        "preflight_seconds": 900,
        "validation_comparison": "s2-derived-budget-replay-v1",
        "scope": "one_explicitly_requested_new_full_grid_not_old_job_continuation",
        **FLAGS,
    }


def load_claim(folder):
    folder = p.safe(folder)
    d.require(folder == directory(), "Dedicated grid claim.")
    plan = native.validate(p.read(folder / "plan.json"))
    release = p.read(folder / "release.json")
    d.require(c.encoded(release) == c.encoded(sealed(plan)), "Grid release drift.")
    job = p.read(folder / "job.json")
    d.require(
        re.fullmatch(r"[1-9][0-9]*", job["job_id"]) and job["plan_sha256"] == d.digest(plan),
        "Grid acknowledgement binding.",
    )
    return plan, release, job


def load(commit):
    old.entry.require_hash(commit, 40)
    plan, release, job = load_claim(directory())
    d.require(release["source_commit"] == commit, "Pinned grid source drift.")
    return plan, release, job


def verify_origin(folder, plan):
    d.require(
        p.read(folder / "origin.json")
        == {"root": str(ROOT), "reference": str(REFERENCE), "python": sys.executable},
        "Grid source origin drift.",
    )
    old.source.verify_tree(ROOT, plan["files"])


def start(commit, *, acknowledged=False, planner=native._plan, command=old.source.command):
    d.require(acknowledged is True, "One reviewed five-arm block acknowledgement required.")
    old.entry.require_hash(commit, 40)
    folder = directory()
    d.require(not folder.exists(), "Existing grid claim; collect only, never resubmit.")
    replay.authenticated(replay.carrier())
    historical = native.validate(p.read(replay.original() / "plan.json"))
    d.require(
        d.digest(historical) == replay.ANCHORS["native_plan_sha256"], "Original private plan."
    )
    plan = planner(
        commit,
        ROOT,
        BASE / ".mvp2-s2-academic-v2-native_miniature/s2-academic-evidence.tar.gz",
        REFERENCE,
    )
    d.require(
        all(plan[k] == historical[k] for k in ("runtime", "input", "protected")),
        "Scientific/runtime identity differs from original cohort.",
    )
    release = sealed(plan)
    folder.mkdir(mode=0o700)
    for name, value in (
        ("plan.json", plan),
        ("release.json", release),
        ("origin.json", {"root": str(ROOT), "reference": str(REFERENCE), "python": sys.executable}),
    ):
        p.publish(folder / name, value)
    code = (
        "import sys;sys.dont_write_bytecode=True;sys.path.insert(0,"
        + repr(str(ROOT))
        + ");from scripts.mvp2_s2_grid_release import batch;raise SystemExit(batch("
        + repr(commit)
        + "))"
    )
    with (folder / "batch.sh").open("x", newline="\n") as stream:
        stream.write(
            "#!/bin/sh\nexec " + shlex.join([sys.executable, "-B", "-I", "-c", code]) + "\n"
        )
    argv = [
        "sbatch",
        "--parsable",
        "--partition=intel-256",
        "--account=sxdsouza",
        "--nodes=1",
        "--ntasks=1",
        "--cpus-per-task=16",
        "--mem=196608M",
        "--time=12:00:00",
        "--no-requeue",
        "--export=NONE",
        "--job-name=s2-grid3600",
        "--chdir=" + str(ROOT),
        "--output=" + str(folder / "slurm.out"),
        "--error=" + str(folder / "slurm.err"),
        str(folder / "batch.sh"),
    ]
    p.publish(
        folder / "submission-intent.json",
        {"release_sha256": d.digest(release), "argv_sha256": d.digest(argv)},
    )
    meta, raw = command(argv, timeout=30, limit=1024)
    p.publish(folder / "submission-call.json", meta)
    d.require(
        meta["status"] == "complete"
        and meta["returncode"] == 0
        and re.fullmatch(rb"[1-9][0-9]*(?:;[A-Za-z0-9_-]+)?\n?", raw),
        "Unknown acknowledgement consumes grid slot; never retry.",
    )
    job = {"job_id": raw.decode().strip().split(";")[0], "plan_sha256": d.digest(plan)}
    p.publish(folder / "job.json", job)
    return {
        "status": "submitted_one_requested_full_grid",
        **job,
        "release_sha256": d.digest(release),
        **FLAGS,
    }


def batch(commit, *, execute=runtime.execute):
    folder = directory()
    with (folder / "batch-slot").open("x"):
        pass
    phase, error, good = "source_and_acknowledgement", None, False
    try:
        end = time.monotonic() + 30
        while not (folder / "job.json").exists():
            d.require(time.monotonic() < end, "Grid acknowledgement not published.")
            time.sleep(0.05)
        plan, _release, job = load(commit)
        d.require(os.environ.get("SLURM_JOB_ID") == job["job_id"], "Batch job mismatch.")
        verify_origin(folder, plan)
        for name in old.ENVIRONMENT:
            os.environ[name] = "1"
        # Enforce the SAME allocation before the existing-vector subprocess.
        native._environment(plan, job["job_id"])
        phase = "existing_vector_preflight_then_fresh_five_arm_block"
        value = execute(folder)
        good = value["stop_reason"] is None and len(value["arms"]) == 5 and not value["unrun"]
    except BaseException as caught:
        error = type(caught).__name__
    p.publish(
        folder / "driver.json",
        {
            "status": "block_returned" if good else "blocked_or_partial",
            "phase": phase,
            "error_kind": error,
            "source_commit": commit,
            **FLAGS,
        },
    )
    return 0 if good else 2


def status(commit, *, command=old.source.command):
    _plan, release, job = load(commit)
    raw = old.query(
        [
            "sacct",
            "-j",
            job["job_id"],
            "--noheader",
            "--parsable2",
            "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw",
        ],
        command=command,
    )
    return {
        "status": "accounting_observed",
        **job,
        "release_sha256": d.digest(release),
        "accounting": raw,
        **FLAGS,
    }


def extract_outer(path, destination):
    d.require(p.safe(path).stat().st_size <= g.LIMIT, "Compressed grid release bound.")
    found, expanded = set(), 10240
    with gzip.open(path, "rb") as compressed, tarfile.open(fileobj=compressed, mode="r|") as stream:
        for member in stream:
            d.require(
                member.name in MEMBERS
                and member.name not in found
                and member.isfile()
                and not member.pax_headers
                and 0 < member.size <= g.LIMIT,
                "Grid release member scope.",
            )
            if member.name.endswith(".json"):
                d.require(member.size <= p.METADATA, "Grid release metadata bound.")
            expanded += ((member.size + 511) // 512) * 512 + 512
            d.require(expanded <= g.LIMIT, "Expanded grid release bound.")
            with (destination / member.name).open("xb") as output:
                source, copied = stream.extractfile(member), 0
                for raw in iter(lambda source=source: source.read(65536), b""):
                    copied += len(raw)
                    output.write(raw)
                d.require(copied == member.size, "Truncated grid release.")
            found.add(member.name)
        trailing = 0
        for raw in iter(lambda: stream.fileobj.read(65536), b""):
            trailing += len(raw)
            d.require(expanded + trailing <= g.LIMIT and not any(raw), "Grid release tail.")
    d.require(found == MEMBERS, "Missing grid release member.")


def verify_comparison(native_archive, prefix, canonical=None, *, original=False):
    worker = g.metadata(native_archive, prefix + "worker-validation.json")
    fresh = g.metadata(native_archive, prefix + "fresh-report.json")
    terms = g.metadata(native_archive, prefix + "witness.json")
    result = g.metadata(native_archive, prefix + "comparison.json")
    if original:
        d.require(
            c.encoded(worker) == c.encoded(replay.original_validation(replay.carrier())),
            "Preflight original report drift.",
        )
    d.require(
        replay.compare(worker, fresh["validation"], terms) == result,
        "Derived grid comparison drift.",
    )
    if canonical is not None:
        import copy

        normalized = copy.deepcopy(fresh)
        for component, values in terms.items():
            normalized["validation"]["cost_reconstruction_sparse_rounding_budgets"][component] = (
                replay.order_bound(values)[0]
            )
        normalized["derived_validation_equivalence"] = {
            "schema_version": result["schema_version"],
            "canonical_validation_sha256": result["canonical_validation_sha256"],
            "witness_sha256": result["witness_sha256"],
            "scientific_tolerances_changed": False,
        }
        d.require(c.encoded(normalized) == c.encoded(canonical), "Canonical grid report drift.")
    return result


def historical_plan(path):
    """Read only after authenticating the original carrier's fixed external hash."""
    with tempfile.TemporaryDirectory(prefix="grid-original-plan-") as temporary:
        temporary = Path(temporary)
        replay.prior._members(path, temporary)
        return native.validate(
            replay.prior.previous.native_metadata(temporary / "native.tar.gz", "plan.json")
        )


def audit(path, checksum, commit, release_sha, job):
    for value, length in ((checksum, 64), (commit, 40), (release_sha, 64)):
        old.entry.require_hash(value, length)
    d.require(
        re.fullmatch(r"[1-9][0-9]*", job or "") and p.sha_file(path) == checksum,
        "External grid archive/job anchor.",
    )
    with tempfile.TemporaryDirectory(prefix="s2-grid-audit-") as temporary:
        temporary = Path(temporary)
        extract_outer(path, temporary)
        replay.authenticated(temporary / "prior.tar.gz")
        archive = temporary / "native.tar.gz"
        transfer = p.read(temporary / "transfer.json")
        g.unpack(archive, transfer["sha256"], transfer["files"])
        # The full raw native inventory, including vectors/witnesses, plus outer
        # overhead fits the explicit new bound. Prior keeps its original cap.
        total = sum(v["size"] + 1024 for v in transfer["files"].values())
        d.require(
            total + (temporary / "prior.tar.gz").stat().st_size + p.METADATA < g.LIMIT,
            "Whole transferred block envelope.",
        )
        plan = native.validate(g.metadata(archive, "plan.json"))
        original_plan = historical_plan(temporary / "prior.tar.gz")
        d.require(
            all(plan[k] == original_plan[k] for k in ("runtime", "input", "protected")),
            "Portable original scientific/runtime binding.",
        )
        release = p.read(temporary / "release.json")
        d.require(
            c.encoded(release) == c.encoded(sealed(plan))
            and release["source_commit"] == commit
            and d.digest(release) == release_sha
            and transfer["plan_sha256"] == d.digest(plan)
            and g.metadata(archive, "job.json") == {"job_id": job, "plan_sha256": d.digest(plan)},
            "Grid source/release/native binding.",
        )
        accounting = g.metadata(archive, "accounting.json")
        rows = {}
        lines = accounting["raw"].strip().splitlines()
        d.require(3 <= len(lines) <= 8, "Five-arm accounting row bound.")
        for line in lines:
            parsed = old.scheduler.accounting(line, job)
            d.require(not rows.keys() & parsed.keys(), "Duplicate grid accounting row.")
            rows.update(parsed)
        d.require(
            rows == accounting["rows"]
            and {job, job + ".batch", job + ".extern"} <= rows.keys()
            and all(v["state"] in old.scheduler.TERMINAL for v in rows.values()),
            "Grid terminal accounting.",
        )
        block, report = g.metadata(archive, "batch.json"), g.metadata(archive, "review.json")
        d.require(
            block["plan_sha256"] == report["plan_sha256"] == d.digest(plan)
            and block["job_id"] == report["job_id"] == job
            and [a["threads"] for a in block["arms"]] == list(d.ORDER[: len(block["arms"])])
            and [a["threads"] for a in report["arms"]] == [a["threads"] for a in block["arms"]],
            "Grid prefix/report binding.",
        )
        d.require(
            all(
                report[k] is False
                for k in (
                    "scientific_configuration_selected",
                    "h300_execution_admitted",
                    "repeats_admitted",
                    "production_isolation_certified",
                )
            ),
            "Grid report cannot select configuration or admit repeats.",
        )
        if block["stop_reason"] == "missing_batch_receipt":
            d.require(
                not block["arms"]
                and not report["unrun"]
                and report["unaccounted"] == list(d.ORDER),
                "Unknown grid inventory.",
            )
        else:
            d.require(
                report["unrun"] == block["unrun"] == list(d.ORDER[len(block["arms"]) :])
                and not report["unaccounted"],
                "Known grid unrun suffix.",
            )
        failures = []
        prerequisite = transfer["files"].get("prerequisite/comparison.json")
        if prerequisite:
            # Unlike the private replay carrier location, the portable anchor is
            # this authenticated original archive supplied INSIDE the new transfer.
            original_report = replay.original_validation(temporary / "prior.tar.gz")
            worker = g.metadata(archive, "prerequisite/worker-validation.json")
            d.require(
                c.encoded(worker) == c.encoded(original_report),
                "Original preflight report binding.",
            )
            verify_comparison(archive, "prerequisite/")
        for index, item in enumerate(block["arms"]):
            prefix = f"arms/t{item['threads']}/"
            independent = report["arms"][index]["review"]
            if independent is None:
                failures.append(item["threads"])
                continue
            d.require(
                c.encoded(item["review"]) == c.encoded(independent)
                and c.encoded(g.metadata(archive, prefix + "independent.json"))
                == c.encoded(independent),
                "Independent grid report binding.",
            )
            attempt = g.metadata(archive, prefix + "attempt.json")
            d.require(
                attempt == item["attempt"]
                and attempt["stop_reason"] is None
                and attempt["return_code"] == 0
                and attempt["local_client_reaped"] is True
                and rows[attempt["step_id"]]["state"] == "COMPLETED"
                and rows[attempt["step_id"]]["exit_code"] == "0:0",
                "Grid step/control binding.",
            )
            if independent["validation"]["status"] != "not_applicable_no_incumbent":
                verify_comparison(archive, prefix + "derived-review/", independent)
            terminal = g.metadata(archive, prefix + "native/native-terminal.json")
            returned = g.metadata(archive, prefix + "diagnostics/native-return.json")
            with tempfile.TemporaryDirectory(prefix="grid-diagnostics-") as diagnostics:
                diagnostics = Path(diagnostics)
                for name in native.diag.NAMES:
                    p.publish(
                        diagnostics / name,
                        g.metadata(archive, prefix + "diagnostics/" + name),
                        limit=2048,
                    )
                catalogue = native.diag.catalogue(
                    diagnostics,
                    native.worker_identity(plan, item["threads"], attempt["step_id"]),
                    profile_factory=native.solver_profile,
                )
                d.require(catalogue["native_return_observed"], "Grid native return missing.")
            d.require(
                returned["terminal_sha256"] == d.digest(terminal),
                "Grid native terminal diagnostic.",
            )
        driver = p.read(temporary / "driver.json")
        d.require(
            driver["source_commit"] == commit and all(driver[k] is False for k in FLAGS),
            "Grid driver binding.",
        )
        complete = (
            bool(prerequisite)
            and len(block["arms"]) == 5
            and not failures
            and not report["unrun"]
            and not report["unaccounted"]
            and report["validation_error"] is None
            and report["accounting_error"] is None
            and report["status"] == "five_arms_accounted_not_s2_closure"
            and driver["status"] == "block_returned"
            and all(v["state"] == "COMPLETED" and v["exit_code"] == "0:0" for v in rows.values())
        )
        return {
            "schema_version": "s2-grid3600-portable-v1",
            "status": "portable_integrity_replayed_p5_required",
            "job_id": job,
            "source_commit": commit,
            "release_sha256": release_sha,
            "native_plan_sha256": d.digest(plan),
            "five_arm_evidence_accounted": complete,
            "reported_arms": report["arms"],
            "unrun": report["unrun"],
            "unaccounted": report["unaccounted"],
            "validation_error": report["validation_error"],
            "fresh_private_input_revalidated_by_portable_auditor": False,
            **FLAGS,
        }


def collect(commit, *, command=old.source.command):
    plan, release, job = load(commit)
    folder = directory()
    report = native._collect(
        folder,
        d.digest(plan),
        job["job_id"],
        command=command,
        reviewer=g.review,
        pack=g.pack,
        inventory=g.inventory,
        unpack=g.unpack,
    )
    if not (folder / "driver.json").exists():
        p.publish(
            folder / "driver.json",
            {
                "status": "blocked_or_partial",
                "phase": "missing_driver",
                "error_kind": None,
                "source_commit": commit,
                **FLAGS,
            },
        )
    sources = {
        "release.json": folder / "release.json",
        "prior.tar.gz": replay.carrier(),
        "native.tar.gz": folder / "s2-h300-academic-evidence.tar.gz",
        "transfer.json": folder / "transfer.json",
        "driver.json": folder / "driver.json",
    }
    path = folder / ARCHIVE
    if not path.exists():
        d.require(
            sum(x.stat().st_size + 1024 for x in sources.values()) + 10240 < g.LIMIT,
            "Whole grid release bound.",
        )
        pending = folder / (ARCHIVE + ".pending")
        with (
            pending.open("xb") as output,
            tarfile.open(fileobj=output, mode="w:gz", format=tarfile.USTAR_FORMAT) as stream,
        ):
            for name, source in sorted(sources.items()):
                info = tarfile.TarInfo(name)
                info.size, info.mode = source.stat().st_size, 0o600
                with p.safe(source).open("rb") as data:
                    stream.addfile(info, data)
        audit(pending, p.sha_file(pending), commit, d.digest(release), job["job_id"])
        pending.rename(path)
    checksum = p.sha_file(path)
    result = audit(path, checksum, commit, d.digest(release), job["job_id"])
    sidecar = Path(str(path) + ".sha256")
    text = checksum + "  " + path.name + "\n"
    if sidecar.exists():
        d.require(sidecar.read_text() == text, "Grid sidecar drift.")
    else:
        with sidecar.open("x", newline="\n") as stream:
            stream.write(text)
    d.require(result["reported_arms"] == report["arms"], "Grid portable report drift.")
    return {**result, "sha256": checksum, "download": str(path), "transfer_checksum": str(sidecar)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "status", "collect", "wait", "audit", "repeat"))
    parser.add_argument("source_sha")
    parser.add_argument("--one-reviewed-five-arm-block-only", action="store_true")
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--sha256")
    parser.add_argument("--release-sha256")
    parser.add_argument("--job-id")
    args = parser.parse_args(argv)
    d.require(args.action != "repeat", "No automatic or additional block admitted.")
    if args.action == "audit":
        result = audit(args.archive, args.sha256, args.source_sha, args.release_sha256, args.job_id)
    else:
        d.require(sys.platform == "linux" and os.getuid() > 0, "Non-root Linux required.")
        while True:
            try:
                if args.action == "start":
                    result = start(
                        args.source_sha, acknowledged=args.one_reviewed_five_arm_block_only
                    )
                elif args.action == "status":
                    result = status(args.source_sha)
                else:
                    result = collect(args.source_sha)
                break
            except ValueError as error:
                if args.action != "wait" or str(error) not in {
                    "Accounting not terminal.",
                    "Missing/unexpected accounting row.",
                }:
                    raise
                print("GRID_ACCOUNTING_PENDING; Ctrl-C safe; no resubmission", flush=True)
                time.sleep(20)
    print(c.encoded(result).decode(), end="")
    if args.action != "audit":
        print("PRESERVE_CLAIM=" + str(directory()))
    for key, label in (
        ("job_id", "JOB_ID"),
        ("sha256", "SHA256"),
        ("download", "DOWNLOAD"),
        ("transfer_checksum", "TRANSFER_CHECKSUM"),
        ("release_sha256", "RELEASE_SHA256"),
    ):
        if key in result:
            print(label + "=" + result[key])
    print("NO_ADDITIONAL_BLOCK_AUTOMATIC_FOLLOW_ON_OR_S2_CLOSURE_ADMITTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
