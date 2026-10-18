"""Read-only existing-vector replay; never build, optimize, resume or repeat a model.

The historical strict certificate and its claim are immutable. A derived replay
may qualify only analytically bounded order effects in transport rounding-budget
diagnostics, after the unchanged independent validator has actually accepted.
"""

from __future__ import annotations

import argparse
import copy
import gzip
import json
import math
import os
import re
import shlex
import sys
import tarfile
import tempfile
import time
from pathlib import Path

from scripts import mvp2_s2_p4_terminal_release as prior

p, d, c, r = prior.p, prior.d, prior.c, prior.runtime.old
ROOT, BASE = Path(__file__).resolve().parents[1], prior.BASE
CLAIM = ".mvp2-s2-residual-replay-v1"
ARCHIVE = "s2-residual-replay-evidence.tar.gz"
ALLOCATION = {"cpus": 4, "memory_mib": 16384, "wall_seconds": 1800}
WITNESS_LIMIT = 128 * 1024**2
ANCHORS = {
    "source_commit": "c9b4fa7e783a499596cf31a2c5e31995605c90e2",
    "job_id": "2214305",
    "archive_sha256": "27e2a6055463c54333f5368a1452e09af966a91be1034521a7c68db75cba57f0",
    "release_sha256": "e2f95a5e54cf2e024a9a4e1a0e6d690bae46d06fbc2c5c1ddcafd725680a6c4d",
    "native_plan_sha256": "daf4de2a261eadb2ce8e76663fb1f84e77e3ac25518f350f4224ea984e9b90dc",
}
FLAGS = {
    "optimization_performed": False,
    "native_license_probe_performed": False,
    "original_claim_modified": False,
    "new_h300_admitted": False,
    "repeats_admitted": False,
    "automatic_follow_on_allowed": False,
    "s2_closed": False,
}
KINDS = ("od", "dc", "dd", "oc")
MEMBERS = {
    "plan.json",
    "job.json",
    "result.json",
    "fresh-report.json",
    "worker-validation.json",
    "witness.json",
    "accounting.json",
    "allocation.json",
    "prior.tar.gz",
}


def witness(data, config):
    """Exactly the original per-term arithmetic, stable sum, no validator mutation."""
    value = {}
    for kind in KINDS:
        terms = []
        freight = data.freight_origin if kind in {"od", "oc"} else data.freight_warehouse
        distance = getattr(data, "dist_" + kind)
        for a, b, _product in {tuple(x) for x in data.metadata["_frozen_routes"].get(kind, [])}:
            unit = distance.get((a, b), 0.0) * freight.get(a, 0.0)
            if kind == "dd":
                unit *= config.interhub_factor
            if kind in {"od", "dd"}:
                unit += data.transshipment_cost.get(b, 0.0)
            terms.append(abs(unit) * len(data.periods) * 1e-7)
        value["transport_" + kind] = sorted(terms)
    return value


def order_bound(terms):
    d.require(
        type(terms) is list
        and len(terms) <= 1000000
        and all(type(x) in (int, float) and math.isfinite(x) and x >= 0 for x in terms),
        "Finite nonnegative coefficient witness required.",
    )
    try:
        total = math.fsum(terms)
    except OverflowError as error:
        raise ValueError("Witness sum overflow.") from error
    d.require(math.isfinite(total), "Witness sum overflow.")
    if total == 0:
        return 0.0, 0.0
    # Unit roundoff for binary64. Inputs are the already-rounded per-term values.
    # gamma_n bounds sequential accumulation, not the scientific residual test.
    d.require(
        all(x == 0 or x >= sys.float_info.min for x in terms), "Subnormal witness not qualified."
    )
    neps = len(terms) * 2.0**-53
    d.require(neps < 0.01, "Witness accumulation bound.")
    return total, neps / (1 - neps) * total + 2 * math.ulp(total)


def compare(worker, fresh, terms):
    """Never tolerate changed residual acceptance, counts, thresholds or metadata."""
    d.require(set(terms) == {"transport_" + x for x in KINDS}, "Witness scope.")
    for report in (worker, fresh):
        d.require(
            report["status"] == "accepted"
            and type(report["failed_check_count"]) is int
            and report["failed_check_count"] == 0
            and report["absolute_tolerance"] == 1e-5
            and report["relative_tolerance"] == 1e-8,
            "Unchanged fresh scientific acceptance required.",
        )
    left, right, changes = copy.deepcopy(worker), copy.deepcopy(fresh), []
    key = "cost_reconstruction_sparse_rounding_budgets"
    for component in sorted(terms):
        canonical, bound = order_bound(terms[component])
        before, after = worker[key][component], fresh[key][component]
        d.require(
            all(
                type(v) in (int, float)
                and math.isfinite(v)
                and v >= 0
                and abs(v - canonical) <= bound
                for v in (before, after)
            ),
            "Derived rounding budget outside analytic order bound.",
        )
        left[key][component] = right[key][component] = canonical
        if before != after:
            changes.append(
                {
                    "component": component,
                    "worker": before,
                    "fresh": after,
                    "canonical": canonical,
                    "each_sum_absolute_bound": bound,
                    "term_count": len(terms[component]),
                }
            )
    d.require(c.encoded(left) == c.encoded(right), "Non-derived validation report drift.")
    return {
        "schema_version": "s2-derived-budget-replay-v1",
        "status": "strict_identical"
        if c.encoded(worker) == c.encoded(fresh)
        else "bounded_transport_budget_order_difference",
        "worker_validation_sha256": d.digest(worker),
        "fresh_validation_sha256": d.digest(fresh),
        "canonical_validation_sha256": d.digest(left),
        "witness_sha256": d.digest(terms),
        "differences": changes,
        "scientific_tolerances_changed": False,
        **FLAGS,
    }


def original():
    return p.safe(BASE / prior.runtime.CLAIM)


def carrier():
    return original() / prior.ARCHIVE


def authenticated(path):
    result = prior.audit(
        path,
        ANCHORS["archive_sha256"],
        ANCHORS["source_commit"],
        ANCHORS["release_sha256"],
        ANCHORS["job_id"],
    )
    d.require(
        result["native_plan_sha256"] == ANCHORS["native_plan_sha256"]
        and result["unrun"] == [1, 8, 2, 16],
        "Preserved original anchors.",
    )
    return result


def product_inventory(path):
    authenticated(path)
    with tempfile.TemporaryDirectory(prefix="s2-original-products-") as temporary:
        temporary = Path(temporary)
        prior._members(path, temporary)
        inventory = p.read(temporary / "native-transfer.json")["files"]
    prefix = "arms/t4/native/products/"
    value = {
        name.removeprefix(prefix): record
        for name, record in inventory.items()
        if name.startswith(prefix)
    }
    d.require(
        set(value)
        == {"closure.json", "observation.json", "incumbent.json", "independent_validation.json"},
        "Original closed products required.",
    )
    return value


def original_validation(path):
    """Bind the derived worker report to the authenticated original carrier."""
    with tempfile.TemporaryDirectory(prefix="s2-original-validation-") as temporary:
        temporary = Path(temporary)
        prior._members(path, temporary)
        return prior.previous.native_metadata(
            temporary / "native.tar.gz", "arms/t4/native/products/independent_validation.json"
        )


def validate_plan(plan, commit):
    r.entry.require_hash(commit, 40)
    d.require(
        plan["schema_version"] == "s2-residual-replay-plan-v1"
        and plan["source_commit"] == commit
        and plan["prior"] == ANCHORS
        and plan["allocation"] == ALLOCATION
        and all(plan[k] is False for k in FLAGS),
        "Read-only replay binding.",
    )
    r.entry.require_hash(plan["origin_sha256"])
    d.require(
        type(plan["files"]) is dict and "scripts/mvp2_s2_residual_replay.py" in plan["files"],
        "Replay source inventory.",
    )
    for name, checksum in plan["files"].items():
        d.require(
            name
            and not Path(name).is_absolute()
            and ".." not in Path(name).parts
            and "\\" not in name
            and ":" not in name,
            "Replay source path.",
        )
        r.entry.require_hash(checksum)
    return plan


def target():
    return p.safe(BASE / CLAIM)


def load(commit):
    r.entry.require_hash(commit, 40)
    folder = target()
    plan = validate_plan(p.read(folder / "plan.json"), commit)
    return folder, plan


def start(commit, *, command=r.source.command):
    r.entry.require_hash(commit, 40)
    d.require(not target().exists(), "Existing replay claim; collect only, never resubmit.")
    authenticated(carrier())
    old_plan = prior.runtime.validate(p.read(original() / "plan.json"))
    d.require(d.digest(old_plan) == ANCHORS["native_plan_sha256"], "Original private plan drift.")
    r.entry.source_parity(ROOT, old_plan["files"])
    files = r.source.source_files(ROOT, commit)
    origin = p.read(original() / "origin.json")
    d.require(p.safe(origin["root"]).name == "source", "Preserved source origin.")
    r.source.verify_tree(origin["root"], old_plan["files"])
    plan = {
        "schema_version": "s2-residual-replay-plan-v1",
        "source_commit": commit,
        "files": files,
        "prior": dict(ANCHORS),
        "origin_sha256": d.digest(origin),
        "original_products": product_inventory(carrier()),
        "allocation": dict(ALLOCATION),
        **FLAGS,
    }
    folder = target()
    folder.mkdir(mode=0o700)
    p.publish(folder / "plan.json", plan)
    p.publish(folder / "origin.json", origin)
    p.publish(folder / "replay-origin.json", {"root": str(ROOT), "python": sys.executable})
    code = (
        "import sys;sys.dont_write_bytecode=True;sys.path.insert(0,"
        + repr(str(ROOT))
        + ");from scripts.mvp2_s2_residual_replay import batch;batch("
        + repr(commit)
        + ")"
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
        "--cpus-per-task=4",
        "--mem=16384M",
        "--time=00:30:00",
        "--no-requeue",
        "--export=NONE",
        "--job-name=s2-residual-replay",
        "--chdir=" + str(ROOT),
        "--output=" + str(folder / "slurm.out"),
        "--error=" + str(folder / "slurm.err"),
        str(folder / "batch.sh"),
    ]
    p.publish(folder / "submission-intent.json", {"argv_sha256": d.digest(argv), **FLAGS})
    meta, raw = command(argv, timeout=30, limit=1024)
    p.publish(folder / "submission-call.json", meta)
    d.require(
        meta["status"] == "complete"
        and meta["returncode"] == 0
        and re.fullmatch(rb"[1-9][0-9]*(?:;[A-Za-z0-9_-]+)?\n?", raw),
        "Unknown submission acknowledgement; consumed claim, never retry.",
    )
    job = {"job_id": raw.decode().strip().split(";")[0], "plan_sha256": d.digest(plan)}
    p.publish(folder / "job.json", job)
    return {"status": "submitted_existing_vector_replay_only", **job, **FLAGS}


def products(directory, data, config, anchor, expected):
    """Same closure/hash/schema/residual evaluator, return BOTH raw reports."""
    closure = p.read(directory / "closure.json")
    names = {"observation.json", "independent_validation.json", "incumbent.json"}
    d.require(set(expected) == names | {"closure.json"}, "Externally anchored product names.")
    for name, record in expected.items():
        file = p.safe(directory / name)
        d.require(
            file.stat().st_size == record["size"] and p.sha_file(file) == record["sha256"],
            "Preserved product differs from original transferred carrier.",
        )
    d.require(
        set(closure)
        == {
            "schema_version",
            "anchor_sha256",
            "artifacts",
            "sizes",
            "production_admitted",
            "repeats_admitted",
        }
        and closure["schema_version"] == "s2-p4-product-closure-v1"
        and set(closure["artifacts"]) == names
        and set(closure["sizes"]) == names
        and closure["anchor_sha256"] == d.digest(anchor)
        and closure["production_admitted"] is False
        and closure["repeats_admitted"] is False
        and {x.name for x in directory.iterdir()} == names | {"closure.json"},
        "Original product closure scope.",
    )
    d.require(
        all(type(x) is int and 0 < x <= p.LIMIT for x in closure["sizes"].values())
        and sum(closure["sizes"].values()) <= p.LIMIT - p.RESERVE,
        "Original aggregate product bound.",
    )
    for name in names:
        file = p.safe(directory / name)
        d.require(
            file.stat().st_size == closure["sizes"][name]
            and p.sha_file(file) == closure["artifacts"][name],
            "Original product drift.",
        )
    observed = p.read(directory / "observation.json")
    vector = p.read(directory / "incumbent.json", limit=p.LIMIT)
    fresh = r.partial.evaluate(observed, vector, data, config, anchor)
    return p.read(directory / "independent_validation.json"), fresh


def batch(commit):
    folder, plan = load(commit)
    with (folder / "batch-slot").open("x"):
        pass
    phase = "source_and_prior"
    outcome = {
        "status": "observed_error",
        "error_kind": None,
        "comparison": None,
        "changed_validation_fields": None,
        "changed_budget_components": None,
        "fresh_validation_status": None,
        "fresh_failed_checks": None,
        "fresh_classification": None,
    }
    try:
        r.source.verify_tree(ROOT, plan["files"])
        authenticated(carrier())
        job = os.environ.get("SLURM_JOB_ID", "")
        d.require(re.fullmatch(r"[1-9][0-9]*", job or ""), "Batch job identity.")
        deadline = time.monotonic() + 30
        while not (folder / "job.json").exists():
            d.require(time.monotonic() < deadline, "Replay acknowledgement missing.")
            time.sleep(0.05)
        d.require(
            p.read(folder / "job.json") == {"job_id": job, "plan_sha256": d.digest(plan)},
            "Replay batch/acknowledgement mismatch.",
        )
        from scripts import mvp2_s2_academic as academic

        allocation = academic.allocation(
            r.query(["scontrol", "-o", "show", "job", job]), job, os.getuid(), plan["allocation"]
        )
        p.publish(folder / "allocation.json", allocation)
        phase = "fresh_private_input"
        old_plan = prior.runtime.validate(p.read(original() / "plan.json"))
        d.require(d.digest(old_plan) == ANCHORS["native_plan_sha256"], "Original plan.")
        origin = p.read(folder / "origin.json")
        d.require(
            d.digest(origin) == plan["origin_sha256"]
            and p.read(original() / "origin.json") == origin,
            "Original origin drift.",
        )
        data, config = prior.runtime._recheck(old_plan, origin["root"], origin["reference"])
        anchor = r.partial.anchor(
            data,
            config,
            source_commit=ANCHORS["source_commit"],
            runtime_sha256=d.digest(old_plan["runtime"]),
            workbook_sha256=d.WORKBOOK,
            threads=4,
        )
        phase = "unchanged_residual_evaluation"
        worker, fresh = products(
            original() / "arms/t4/native/products", data, config, anchor, plan["original_products"]
        )
        for name, value in (("worker-validation.json", worker), ("fresh-report.json", fresh)):
            p.publish(folder / name, value)
        phase = "coefficient_witness"
        terms = witness(data, config)
        p.publish(folder / "witness.json", terms, limit=WITNESS_LIMIT)
        phase = "derived_budget_comparison"
        key = "cost_reconstruction_sparse_rounding_budgets"
        outcome.update(
            changed_validation_fields=sorted(
                k
                for k in set(worker) | set(fresh["validation"])
                if worker.get(k) != fresh["validation"].get(k)
            ),
            changed_budget_components=sorted(
                k for k in worker[key] if worker[key][k] != fresh["validation"][key].get(k)
            ),
            fresh_validation_status=fresh["validation"]["status"],
            fresh_failed_checks=fresh["validation"]["failed_check_count"],
            fresh_classification=fresh["classification"]["disposition"],
        )
        certificate = compare(worker, fresh["validation"], terms)
        outcome.update(status="existing_vector_replay_qualified", comparison=certificate)
    except Exception as error:
        outcome["error_kind"] = type(error).__name__
    p.publish(
        folder / "result.json",
        {**outcome, "phase": phase, "prior": dict(ANCHORS), "source_commit": commit, **FLAGS},
    )


def status(commit):
    folder, _plan = load(commit)
    job = p.read(folder / "job.json")
    text = r.query(
        [
            "sacct",
            "-j",
            job["job_id"],
            "--noheader",
            "--parsable2",
            "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw",
        ]
    )
    return {"status": "accounting_observed", **job, "accounting": text, **FLAGS}


def members(path, destination):
    d.require(p.sha_file(path) and p.safe(path).stat().st_size <= p.LIMIT, "Replay archive size.")
    found, size = set(), 10240
    with gzip.open(path, "rb") as compressed, tarfile.open(fileobj=compressed, mode="r|") as stream:
        for member in stream:
            d.require(
                member.name in MEMBERS
                and member.name not in found
                and member.isfile()
                and not member.pax_headers
                and 0 <= member.size <= p.LIMIT,
                "Replay member scope.",
            )
            size += ((member.size + 511) // 512) * 512 + 512
            d.require(size <= p.LIMIT, "Expanded replay archive bound.")
            if member.name != "prior.tar.gz":
                limit = WITNESS_LIMIT if member.name == "witness.json" else p.METADATA
                d.require(member.size <= limit, "Replay metadata bound.")
            with (destination / member.name).open("xb") as output:
                source = stream.extractfile(member)
                copied = 0
                for raw in iter(lambda source=source: source.read(65536), b""):
                    copied += len(raw)
                    output.write(raw)
                d.require(copied == member.size, "Truncated replay member.")
            found.add(member.name)
        tail = 0
        for raw in iter(lambda: stream.fileobj.read(65536), b""):
            tail += len(raw)
            d.require(size + tail <= p.LIMIT and not any(raw), "Replay trailing payload.")
    d.require(
        {"plan.json", "job.json", "result.json", "accounting.json", "prior.tar.gz"} <= found,
        "Replay essential inventory.",
    )


def audit(path, checksum, commit, job):
    for value, length in ((checksum, 64), (commit, 40)):
        r.entry.require_hash(value, length)
    d.require(re.fullmatch(r"[1-9][0-9]*", job or ""), "External replay job anchor.")
    d.require(p.sha_file(path) == checksum, "External replay checksum.")
    with tempfile.TemporaryDirectory(prefix="s2-residual-audit-") as temp:
        temp = Path(temp)
        members(path, temp)
        authenticated(temp / "prior.tar.gz")
        plan, receipt, result = (
            p.read(temp / name) for name in ("plan.json", "job.json", "result.json")
        )
        validate_plan(plan, commit)
        d.require(
            plan["source_commit"] == commit
            and plan["prior"] == ANCHORS
            and receipt == {"job_id": job, "plan_sha256": d.digest(plan)}
            and result["source_commit"] == commit
            and result["prior"] == ANCHORS
            and plan["original_products"] == product_inventory(temp / "prior.tar.gz")
            and all(result[k] is False and plan[k] is False for k in FLAGS),
            "Replay anchors.",
        )
        accounting = p.read(temp / "accounting.json")
        rows = r.scheduler.accounting(accounting["raw"], job)
        d.require(
            rows == accounting["rows"]
            and set(rows) == {job, job + ".batch", job + ".extern"}
            and all(v["state"] in r.scheduler.TERMINAL for v in rows.values()),
            "Replay terminal accounting.",
        )
        if result["comparison"] is not None:
            worker, fresh = (
                p.read(temp / name) for name in ("worker-validation.json", "fresh-report.json")
            )
            terms = p.read(temp / "witness.json", limit=WITNESS_LIMIT)
            d.require(
                c.encoded(worker) == c.encoded(original_validation(temp / "prior.tar.gz")),
                "Original worker validation binding.",
            )
            allocation = p.read(temp / "allocation.json")
            from scripts import mvp2_s2_academic as academic

            fields = allocation["scheduler_fields"]
            rebuilt = academic.allocation(
                " ".join(k + "=" + v for k, v in fields.items()), job, allocation["uid"], ALLOCATION
            )
            d.require(rebuilt == allocation, "Replay allocation receipt drift.")
            d.require(
                result["status"] == "existing_vector_replay_qualified"
                and compare(worker, fresh["validation"], terms) == result["comparison"],
                "Replay certificate drift.",
            )
        else:
            d.require(result["status"] == "observed_error", "Replay result grammar.")
        qualified = result["comparison"] is not None and all(
            v["state"] == "COMPLETED" and v["exit_code"] == "0:0" for v in rows.values()
        )
        return {
            "status": "portable_replay_integrity_verified",
            "observed_status": result["status"],
            "existing_vector_replay_qualified": qualified,
            "comparison": result["comparison"],
            "phase": result["phase"],
            "error_kind": result["error_kind"],
            "job_id": job,
            "source_commit": commit,
            "fresh_private_residuals_recomputed_by_portable_auditor": False,
            **FLAGS,
        }


def collect(commit):
    folder, plan = load(commit)
    record = status(commit)
    rows = r.scheduler.accounting(record["accounting"], record["job_id"])
    d.require(
        set(rows) == {record["job_id"], record["job_id"] + ".batch", record["job_id"] + ".extern"}
        and all(x["state"] in r.scheduler.TERMINAL for x in rows.values()),
        "Not terminal.",
    )
    if not (folder / "result.json").exists():
        p.publish(
            folder / "result.json",
            {
                "status": "observed_error",
                "phase": "missing_batch_receipt",
                "comparison": None,
                "error_kind": None,
                "prior": dict(ANCHORS),
                "source_commit": commit,
                **FLAGS,
            },
        )
    accounting = {"raw": record["accounting"], "rows": rows}
    if not (folder / "accounting.json").exists():
        p.publish(folder / "accounting.json", accounting)
    else:
        d.require(
            p.read(folder / "accounting.json") == accounting, "Replay accounting cache drift."
        )
    path = folder / ARCHIVE
    if not path.exists():
        sources = {name: carrier() if name == "prior.tar.gz" else folder / name for name in MEMBERS}
        d.require(
            sum(
                ((x.stat().st_size + 511) // 512) * 512 + 512
                for x in sources.values()
                if x.exists()
            )
            + 10240
            <= p.LIMIT,
            "Replay whole-archive cap.",
        )
        pending = folder / (ARCHIVE + ".pending")
        with (
            pending.open("xb") as output,
            tarfile.open(fileobj=output, mode="w:gz", format=tarfile.USTAR_FORMAT) as stream,
        ):
            for name in sorted(MEMBERS):
                source = carrier() if name == "prior.tar.gz" else folder / name
                if not source.exists():
                    continue
                info = tarfile.TarInfo(name)
                info.size, info.mode = source.stat().st_size, 0o600
                with p.safe(source).open("rb") as data:
                    stream.addfile(info, data)
        audit(pending, p.sha_file(pending), commit, record["job_id"])
        pending.rename(path)
    checksum = p.sha_file(path)
    result = audit(path, checksum, commit, record["job_id"])
    sidecar = Path(str(path) + ".sha256")
    text = checksum + "  " + path.name + "\n"
    if not sidecar.exists():
        with sidecar.open("x", newline="\n") as stream:
            stream.write(text)
    else:
        d.require(sidecar.read_text() == text, "Replay sidecar cache drift.")
    return {**result, "sha256": checksum, "download": str(path), "transfer_checksum": str(sidecar)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=("start", "batch", "status", "wait", "collect", "audit", "optimize", "repeat"),
    )
    parser.add_argument("source_sha")
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--sha256")
    parser.add_argument("--job-id")
    args = parser.parse_args(argv)
    d.require(args.action not in {"optimize", "repeat"}, "No optimization or repeat admitted.")
    if args.action == "audit":
        result = audit(args.archive, args.sha256, args.source_sha, args.job_id)
    else:
        d.require(sys.platform == "linux" and os.getuid() > 0, "Non-root Linux required.")
        while True:
            try:
                result = {
                    "start": start,
                    "status": status,
                    "wait": collect,
                    "collect": collect,
                    "batch": batch,
                }[args.action](args.source_sha)
                break
            except ValueError as error:
                if args.action != "wait" or str(error) != "Not terminal.":
                    raise
                print("REPLAY_ACCOUNTING_PENDING; Ctrl-C safe; no resubmission", flush=True)
                time.sleep(20)
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    if args.action != "audit":
        print("PRESERVE_CLAIM=" + str(target()))
    for key, label in (
        ("job_id", "JOB_ID"),
        ("sha256", "SHA256"),
        ("download", "DOWNLOAD"),
        ("transfer_checksum", "TRANSFER_CHECKSUM"),
    ):
        if key in result:
            print(label + "=" + result[key])
    print("NO_OPTIMIZATION_REPEAT_OR_S2_CLOSURE_ADMITTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
