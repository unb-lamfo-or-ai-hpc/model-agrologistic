"""Qualified normal release/claim components; execution entries remain closed.

Effects are mandatory injected qualification seams. There is no live transport
factory, admission switch, scheduler invocation or runnable worker entry here.
Historical identities are references, never newly replayed or upgraded receipts.
"""

from __future__ import annotations

import copy
import hashlib
import os
import shlex
from pathlib import Path

if __name__ == "__main__":
    raise PermissionError("Resource launcher execution remains blocked; no claim or job admitted.")

from scripts import mvp2_h300_controls as c
from scripts import mvp2_s2_batch_adapter as a
from scripts import mvp2_s2_compute_identity as identity
from scripts import mvp2_s2_first_normal as first
from scripts import mvp2_s2_operational as o
from scripts import mvp2_s2_resource_normal as normal
from scripts import mvp2_s2_slurm_step as s
from scripts import mvp2_s2_slurm_synthetic as q

ENTRY = "scripts/mvp2_s2_resource_launcher.py"
OPERATIONAL_ENTRY = "scripts/mvp2_s2_resource_operational.py"
COLLECTOR = "scripts/mvp2_s2_resource_forensics.py"
CLAIM = ".mvp2-s2-resource-normal-v1"
BASE_COMMIT = "5f4100de9fb9969f0246247947a6050ebf439c2f"
LIMIT = 1024**2
HISTORY = (
    {
        "job_id": "2208459",
        "archive_sha256": "64617380256e8cf3c5031ef87fb3d71d9526d923e69e100c5140879a60ad34e3",
    },
    {
        "job_id": "2209138",
        "archive_sha256": "4f0f4bc20337d5bc7b42283afd5de620d0500509d6a7010938b18425214a14a1",
    },
    {
        "job_id": "2209770",
        "archive_sha256": "f1f19fd0b494526af78e59ea979c5d428089e9f0afda4a7e78040d4df53be18f",
    },
)
CLOSURE = identity.REQUIRED | {ENTRY, COLLECTOR, "scripts/mvp2_s2_resource_normal.py"}


def execute_normal(*_args, **_kwargs):
    raise PermissionError("Resource launcher execution remains blocked; no claim or job admitted.")


def claim_path():
    path = Path(o.BASE) / CLAIM
    q._safe_path(path)
    return path


def validate_release(value, commit, digest):
    q._hash(commit, 40)
    q._hash(digest)
    s.require(len(c.encoded(value)) <= LIMIT, "Release bound.")
    q._keys(
        value,
        {
            "schema_version",
            "envelope",
            "plan",
            "manifest",
            "base_commit",
            "history",
            "resource_policy",
            "profile",
            *normal.p.FLAGS,
        },
    )
    s.require(
        value["schema_version"] == "s2-resource-launcher-release-v1"
        and s.digest(value) == digest
        and value["base_commit"] == BASE_COMMIT
        and value["history"] == list(HISTORY)
        and value["resource_policy"] == normal.p.POLICY
        and value["profile"] == q.PROFILE
        and all(value[k] is False for k in normal.p.FLAGS),
        "Release/authority drift.",
    )
    env = o.validate_envelope(value["envelope"], commit)
    first.checked_baseline(env)
    plan = o.validate_normal_plan(value["plan"], env, s.digest(env), commit)
    spec = plan["specification"]
    manifest = identity.validate_manifest(value["manifest"], commit, s.digest(value["manifest"]))
    s.require(
        manifest["source"] == env["source"]
        and CLOSURE <= manifest["files"].keys()
        and commit != BASE_COMMIT
        and spec["job_id"] not in {v["job_id"] for v in HISTORY}
        and Path(spec["run"]).parent == Path(o.BASE)
        and spec["run"] != o.BASE + "/" + CLAIM
        and spec["checkout"] != o.BASE + "/" + CLAIM
        and len((spec["run"] + "/ipc.sock").encode()) <= 100,
        "Fresh source/run/worker closure drift.",
    )
    return copy.deepcopy(value)


def prepare(envelope, *, run, nonce):
    """Login sealing only: full raw-HEAD tree, no reservation or scheduler effect."""
    commit = envelope["source_commit"]
    env = o.validate_envelope(envelope, commit)
    first.checked_baseline(env)
    plan = o.normal_plan(env, s.digest(env), commit, run=run, nonce=nonce, job_id="1")
    first.recheck(env)
    spec = plan["specification"]
    manifest = identity.seal_login_source(spec, a.RealTransport(spec).source_command)
    value = {
        "schema_version": "s2-resource-launcher-release-v1",
        "envelope": env,
        "plan": plan,
        "manifest": manifest,
        "base_commit": BASE_COMMIT,
        "history": copy.deepcopy(list(HISTORY)),
        "resource_policy": dict(normal.p.POLICY),
        "profile": dict(q.PROFILE),
        **normal.p.FLAGS,
    }
    return validate_release(value, commit, s.digest(value))


def verify_release(value, digest, *, role):
    """Compute never needs Git/sbatch or reads/imports a historical checkout."""
    commit = value["envelope"]["source_commit"]
    value = validate_release(value, commit, digest)
    s.require(role in {"login", "batch", "worker"}, "Runtime role.")
    spec = value["plan"]["specification"]
    source = identity.verify_compute_source(
        spec["checkout"], value["manifest"], commit, s.digest(value["manifest"])
    )
    if role == "login":
        first.recheck(value["envelope"])
        runtime = identity.expected_compute_runtime(spec)
    else:
        runtime = identity.verify_compute_runtime(spec, role)
    return value, source, runtime


def submit_argv(value):
    env, claim = value["envelope"], claim_path()
    old = first.submit_argv(env, first.claim_path())
    return (
        old[0],
        old[1],
        "--job-name=mvp2-s2-resource-normal",
        *old[3:-3],
        "--output=" + str(claim / "slurm-%j.out"),
        "--error=" + str(claim / "slurm-%j.err"),
        str(claim / "batch.sh"),
    )


def checked_entry(value, entry):
    s.require(
        entry == ENTRY or entry == OPERATIONAL_ENTRY and entry in value["manifest"]["files"],
        "Unreviewed entry/source closure.",
    )
    return entry


def batch_script(value, *, entry=ENTRY):
    entry = checked_entry(value, entry)
    env = value["envelope"]
    argv = (
        env["python"],
        "-B",
        "-I",
        env["checkout"] + "/" + entry,
        "batch",
        "--source-sha",
        env["source_commit"],
        "--proposal-sha",
        s.digest(value),
    )
    return ("#!/bin/sh\nexec " + shlex.join(argv) + "\n").encode("ascii")


def worker_argv(value, *, entry=ENTRY):
    entry = checked_entry(value, entry)
    spec = value["plan"]["specification"]
    old = first.normal_worker_argv(spec)
    argv = tuple(
        spec["checkout"] + "/" + entry if arg == spec["checkout"] + "/" + first.ENTRY else arg
        for arg in old
    )
    return argv + ("--release-sha", s.digest(value))


def acknowledged(proposal, job):
    value = validate_release(proposal, proposal["envelope"]["source_commit"], s.digest(proposal))
    s.require(
        value["plan"]["specification"]["job_id"] == "1" and job != "1",
        "Only an unsubmitted proposal may be acknowledged.",
    )
    value["plan"]["specification"]["job_id"] = job
    return validate_release(value, value["envelope"]["source_commit"], s.digest(value))


def submission_intent(proposal, *, entry=ENTRY):
    return {
        "source_commit": proposal["envelope"]["source_commit"],
        "proposal_sha256": s.digest(proposal),
        "argv_sha256": s.digest(submit_argv(proposal)),
        "script_sha256": hashlib.sha256(batch_script(proposal, entry=entry)).hexdigest(),
        "scope": "resource_normal_only" if entry == ENTRY else "resource_operational_normal_only",
        **normal.p.FLAGS,
    }


def reserve_components(proposal, latch, *, submit, entry=ENTRY):
    """Injected-effect qualification only; durable one-shot intent precedes callback.

    No default callback exists. Unknown acknowledgement, interruption or failed
    publication permanently consumes this distinct claim. Start/CLI stay closed.
    """
    proposal, _source, _runtime = verify_release(proposal, s.digest(proposal), role="login")
    spec = proposal["plan"]["specification"]
    s.require(spec["job_id"] == "1", "Proposal already acknowledged.")
    run = Path(spec["run"])
    q._safe_path(run)
    s.require(not run.exists(), "Preserved run already exists.")
    claim = claim_path()
    claim.mkdir(mode=0o700, exist_ok=False)
    c.write_once(claim / "proposal.json", proposal)
    c.write_once(claim / "submission-intent.json", submission_intent(proposal, entry=entry))
    with (claim / "batch.sh").open("xb") as stream:
        stream.write(batch_script(proposal, entry=entry))
        stream.flush()
        os.fsync(stream.fileno())
    if latch.reason is not None:
        c.write_once(claim / "stop.json", {"reason": "interrupted_before_submit", **normal.p.FLAGS})
        return {"status": "stopped_before_submit", **normal.p.FLAGS}
    try:
        # Last byte/tool recheck before the one injected effect. No resealing.
        verify_release(proposal, s.digest(proposal), role="login")
        s.require(latch.reason is None, "Interrupted before scheduler callback.")
        job = first.parse_acknowledgement(submit(submit_argv(proposal)))
        release = acknowledged(proposal, job)
        c.write_once(claim / "release.json", release)
        if latch.reason is not None:
            c.write_once(
                claim / "stop.json", {"reason": "interrupted_after_submit", **normal.p.FLAGS}
            )
        receipt = {
            "source_commit": spec["source_commit"],
            "job_id": job,
            "release_sha256": s.digest(release),
            "specification_sha256": s.digest(release["plan"]["specification"]),
        }
        c.write_once(claim / "job.json", receipt)  # Publish last, never guess a job ID.
        return {"status": "acknowledgement_preserved_not_admitted", **receipt, **normal.p.FLAGS}
    except (Exception, KeyboardInterrupt):
        c.write_once(
            claim / "submission-unknown.json",
            {"status": "unknown_effect_no_retry", **normal.p.FLAGS},
        )
        return {"status": "unknown_effect_no_retry", **normal.p.FLAGS}


def load_release(*, entry=ENTRY):
    """Bind pre-effect descriptor and acknowledgement without invoking any tool."""
    claim = claim_path()
    proposal = c.decode_json(a._file(claim / "proposal.json", LIMIT))
    proposal = validate_release(proposal, proposal["envelope"]["source_commit"], s.digest(proposal))
    s.require(
        c.decode_json(a._file(claim / "submission-intent.json", 8192))
        == submission_intent(proposal, entry=entry)
        and a._file(claim / "batch.sh", 8192) == batch_script(proposal, entry=entry),
        "Submission drift.",
    )
    receipt = c.decode_json(a._file(claim / "job.json", 8192))
    q._keys(receipt, {"source_commit", "job_id", "release_sha256", "specification_sha256"})
    release = acknowledged(proposal, receipt["job_id"])
    spec = release["plan"]["specification"]
    s.require(
        receipt
        == {
            "source_commit": spec["source_commit"],
            "job_id": spec["job_id"],
            "release_sha256": s.digest(release),
            "specification_sha256": s.digest(spec),
        }
        and c.decode_json(a._file(claim / "release.json", LIMIT)) == release,
        "Acknowledged release drift.",
    )
    return release


def role_components(release, *, role, job_id, specification_digest, dispatch, entry=ENTRY):
    """One-shot batch/worker binding for injected qualification, never a CLI route."""
    s.require(role in {"batch", "worker"}, "Compute role.")
    release, source, runtime = verify_release(release, s.digest(release), role=role)
    spec = release["plan"]["specification"]
    claim = claim_path()
    s.require(
        (load_release() if entry == ENTRY else load_release(entry=entry)) == release
        and spec["job_id"] == job_id != "1"
        and specification_digest == s.digest(spec)
        and not (claim / "stop.json").exists()
        and not (claim / "submission-unknown.json").exists(),
        "Stopped/unbound compute role.",
    )
    (claim / (role + "-claim")).mkdir(mode=0o700, exist_ok=False)
    if role == "worker":
        run = Path(spec["run"])
        s.require(
            c.decode_json(a._file(run / "claim.json", 8192))
            == {"specification_sha256": s.digest(spec), **a.FLAGS},
            "Worker run binding.",
        )
        c.write_once(
            run / "worker-identity.json",
            {
                "schema_version": "s2-resource-launcher-worker-v1",
                "source": source,
                "runtime": runtime,
                "release_sha256": s.digest(release),
                "specification_sha256": s.digest(spec),
                **normal.p.FLAGS,
            },
        )
    return dispatch(
        copy.deepcopy(spec),
        copy.deepcopy(source),
        copy.deepcopy(runtime),
        worker_argv(release, entry=entry),
    )


def adapter_components(spec, source, runtime, argv, *, adapter, latch, sleep):
    """Connect the existing finite normal loop to an injected ResourceNormalAdapter.

    The production adapter's launch still denies. Qualification fixtures override
    launch using the inherited implementation and fake transports/server/clock.
    No fallback adapter, transport or worker dispatcher is supplied by this gate.
    """
    s.require(
        isinstance(adapter, normal.ResourceNormalAdapter)
        and adapter.item == spec
        and adapter.source == source
        and adapter.runtime == runtime
        and adapter.worker_command() == argv,
        "Adapter/entry binding drift.",
    )
    return o.supervise_normal_components(adapter, latch, sleep=sleep)
