"""One requested complete 3600s thread cohort; historical claims stay read-only."""

from __future__ import annotations

import os
import subprocess
import sys
import time

from scripts import mvp2_s2_grid_products as products
from scripts import mvp2_s2_p4_terminal_runtime as native
from scripts import mvp2_s2_residual_replay as replay

p, d, c = replay.p, replay.d, replay.c
CLAIM = ".mvp2-s2-grid3600-v1"
ROOT = native.ROOT


def dispatch_argv(action, path):
    d.require(action in {"worker", "review", "preflight"}, "Grid private dispatch action.")
    code = (
        "import sys;sys.dont_write_bytecode=True;sys.path.insert(0,"
        + repr(str(ROOT))
        + ");from scripts.mvp2_s2_grid_runtime import dispatch;dispatch("
        + repr(action)
        + ","
        + repr(str(path))
        + ")"
    )
    return [sys.executable, "-B", "-I", "-c", code]


def preflight(folder):
    """Re-evaluate only the existing vector before ANY license probe/native build."""
    phase, outcome = "original_carrier", {"status": "blocked", "error_kind": None}
    try:
        replay.authenticated(replay.carrier())
        old = replay.original()
        plan = native.validate(p.read(old / "plan.json"))
        d.require(d.digest(plan) == replay.ANCHORS["native_plan_sha256"], "Original plan drift.")
        origin = p.read(old / "origin.json")
        native.old.entry.source_parity(ROOT, plan["files"])
        phase = "original_private_input"
        data, config = native._recheck(plan, origin["root"], origin["reference"])
        anchor = native.old.partial.anchor(
            data,
            config,
            source_commit=replay.ANCHORS["source_commit"],
            runtime_sha256=d.digest(plan["runtime"]),
            workbook_sha256=d.WORKBOOK,
            threads=4,
        )
        phase = "original_vector_residuals"
        worker, fresh = replay.products(
            old / "arms/t4/native/products",
            data,
            config,
            anchor,
            replay.product_inventory(replay.carrier()),
        )
        p.publish(folder / "worker-validation.json", worker)
        p.publish(folder / "fresh-report.json", fresh)
        phase = "original_report_comparison"
        terms = replay.witness(data, config)
        p.publish(folder / "witness.json", terms, limit=replay.WITNESS_LIMIT)
        compared = replay.compare(worker, fresh["validation"], terms)
        p.publish(folder / "comparison.json", compared)
        outcome["status"] = "existing_vector_replay_qualified"
    except Exception as error:
        outcome["error_kind"] = type(error).__name__
    p.publish(
        folder / "outcome.json",
        {**outcome, "phase": phase, "prior": dict(replay.ANCHORS), "optimization_performed": False},
    )


def dispatch(action, path):
    from scripts import mvp2_s2_grid_release as release

    target = p.safe(path)
    claim = target.parent if action == "preflight" else target.parent.parent
    d.require(claim.name == CLAIM, "Dedicated new grid claim.")
    plan, _sealed, job = release.load_claim(claim)
    release.verify_origin(claim, plan)
    d.require(os.environ.get("SLURM_JOB_ID") == job["job_id"], "Grid compute identity.")
    if action == "preflight":
        d.require(target.name == "prerequisite", "Preflight output scope.")
        return preflight(target)
    d.require(target.parent.name == "arms", "Arm path scope.")
    ticket = p.read(target / "ticket.json")
    threads = ticket["threads"]
    d.require(target.name == f"t{threads}", "Grid ticket path.")
    origin = p.read(claim / "origin.json")
    if action == "worker":
        return native._worker(
            target,
            plan,
            threads,
            job["job_id"],
            ticket["environment"],
            origin["reference"],
            ticket["remaining"],
            execute=native._native,
        )
    d.require(action == "review", "Grid action denied.")
    folder = target / "derived-review"
    folder.mkdir()
    phase, outcome = "fresh_private_input", {"status": "blocked", "error_kind": None}
    try:
        data, config = native._recheck(plan, ROOT, origin["reference"])
        anchor = native.old.partial.anchor(
            data,
            config,
            source_commit=plan["preparation"]["source_commit"],
            runtime_sha256=d.digest(plan["runtime"]),
            workbook_sha256=d.WORKBOOK,
            threads=threads,
        )
        phase = "independent_vector_review"
        report = products.review(
            target / "native/products",
            data,
            config,
            anchor,
            capture=lambda name, value, limit: p.publish(folder / name, value, limit=limit),
        )
        p.publish(target / "independent.json", report)
        outcome["status"] = "independent_review_returned"
    except Exception as error:
        outcome["error_kind"] = type(error).__name__
    p.publish(folder / "outcome.json", {**outcome, "phase": phase, "threads": threads})
    d.require(
        outcome["status"] == "independent_review_returned",
        "Grid review blocked; raw reports preserved.",
    )


def arm(*args, **kwargs):
    return native._arm(*args, dispatch=dispatch_argv, **kwargs)


def independent(*args, **kwargs):
    return native._independent(*args, dispatch=dispatch_argv, **kwargs)


def execute(claim, *, run=subprocess.run, clock=time.monotonic, block=native._batch):
    """One allocation: bounded old-vector check, fresh admission, five cold arms."""
    started = clock()
    prerequisite = claim / "prerequisite"
    prerequisite.mkdir()
    with (prerequisite / "out").open("xb") as out, (prerequisite / "err").open("xb") as err:
        done = run(
            dispatch_argv("preflight", prerequisite),
            stdout=out,
            stderr=err,
            stdin=subprocess.DEVNULL,
            timeout=900,
            check=False,
            shell=False,
        )
    d.require(
        done.returncode == 0
        and p.read(prerequisite / "outcome.json")["status"] == "existing_vector_replay_qualified"
        and clock() - started < 900,
        "Existing-vector preflight blocked; no new optimization.",
    )
    # Keep source, pool, native settings and every phase deadline unchanged.
    # Absolute deadline includes preflight; headroom cannot extend Slurm or TimeLimit.
    return block(
        claim,
        run_arm=arm,
        independent=independent,
        export_limit=products.LIMIT - products.RESERVE,
        allocation_deadline=started + 43200,
        clock=clock,
    )
