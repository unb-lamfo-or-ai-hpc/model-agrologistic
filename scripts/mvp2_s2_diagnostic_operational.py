"""Complete closed normal operational integration, qualified with injected effects.

One functional package owns source/runtime, exclusive claim, acknowledgement,
roles, diagnostic adapter and resumed terminal collection. No live defaults or
public execution route exists. Missing fast-exit evidence is an explicit blocker,
not permission for another normal trial or a weaker cleanup predicate.
"""

from __future__ import annotations

if __name__ == "__main__":
    raise PermissionError(
        "Diagnostic operational execution blocked; qualification components only."
    )

import copy
import hashlib
import os
import shlex
from pathlib import Path

from scripts import mvp2_s2_diagnostic_forensic as forensic
from scripts import mvp2_s2_diagnostic_gate as g
from scripts import mvp2_s2_resource_launcher as l

a, c, d, n, p, q, s = g.a, g.c, g.d, g.n, g.p, g.q, g.s
ENTRY = "scripts/mvp2_s2_diagnostic_operational.py"
BASE = l.o.BASE
CLOSURE = g.CLOSURE | {ENTRY, "scripts/mvp2_s2_diagnostic_forensic.py"}
CLAIM = g.CLAIM
INTEGRATED_BASE = "a0c5e7c2859c6fb99b718bfc29b7087996f44eb8"
BLOCKERS = (
    "installed_fast_exit_scope_observation_missing",
    "operational_execution_release_not_admitted",
)


def execute_normal(*_args, **_kwargs):
    raise PermissionError(
        "Diagnostic operational execution blocked; qualification components only."
    )


def claim_path():
    root = Path(BASE) / CLAIM
    q._safe_path(root)
    return root


def validate(value, commit):
    value = l.validate_release(value, commit, s.digest(value))
    s.require(CLOSURE <= value["manifest"]["files"].keys(), "Complete operational source closure.")
    g.qualify_release(value, commit=commit, release_digest=s.digest(value))
    return value


def verify(value, *, role):
    """Read-only current bytes and role tools; compute never checks login Git."""
    value = validate(value, value["envelope"]["source_commit"])
    return l.verify_release(value, s.digest(value), role=role)


def readiness(value):
    """No caller-supplied boolean or old success certificate can open execution."""
    value = validate(value, value["envelope"]["source_commit"])
    return {
        "schema_version": "s2-diagnostic-operational-readiness-v1",
        "status": "qualified_components_execution_blocked",
        "source_commit": value["envelope"]["source_commit"],
        "release_sha256": s.digest(value),
        "claim_name": CLAIM,
        "blockers": list(BLOCKERS),
        "downstream_blockers": ["normal_live_containment_audit_missing"],
        **p.FLAGS,
    }


def worker_argv(value):
    value = validate(value, value["envelope"]["source_commit"])
    spec = value["plan"]["specification"]
    argv = l.first.normal_worker_argv(spec)
    return tuple(
        spec["checkout"] + "/" + ENTRY if v == spec["checkout"] + "/" + l.first.ENTRY else v
        for v in argv
    ) + ("--release-sha", s.digest(value))


def batch_script(value):
    env = value["envelope"]
    argv = (
        env["python"],
        "-B",
        "-I",
        env["checkout"] + "/" + ENTRY,
        "batch",
        "--source-sha",
        env["source_commit"],
        "--proposal-sha",
        s.digest(value),
    )
    return ("#!/bin/sh\nexec " + shlex.join(argv) + "\n").encode("ascii")


def submit_argv(value):
    claim = claim_path()
    return (
        value["envelope"]["tools"]["sbatch"],
        "--parsable",
        "--job-name=mvp2-s2-diagnostic-normal",
        "--account=sxdsouza",
        "--partition=intel-256",
        "--nodes=1",
        "--ntasks=1",
        "--cpus-per-task=2",
        "--mem=2048M",
        "--time=00:12:00",
        "--no-requeue",
        "--export=NONE",
        "--output=" + str(claim / "slurm-%j.out"),
        "--error=" + str(claim / "slurm-%j.err"),
        str(claim / "batch.sh"),
    )


def intent(value):
    return {
        "schema_version": "s2-diagnostic-operational-intent-v1",
        "source_commit": value["envelope"]["source_commit"],
        "proposal_sha256": s.digest(value),
        "argv_sha256": s.digest(submit_argv(value)),
        "script_sha256": hashlib.sha256(batch_script(value)).hexdigest(),
        "claim_name": CLAIM,
        "scope": "closed_normal_qualification_only",
        **p.FLAGS,
    }


def reserve_components(proposal, latch, *, submit):
    """Mandatory injected effect only; no public start/default live submit exists."""
    s.require(callable(submit), "Explicit qualification callback required.")
    proposal, _source, _runtime = verify(proposal, role="login")
    spec = proposal["plan"]["specification"]
    s.require(spec["job_id"] == "1", "Already acknowledged proposal.")
    run = Path(spec["run"])
    q._safe_path(run)
    s.require(not run.exists(), "Preserved run exists.")
    claim = claim_path()
    claim.mkdir(mode=0o700, exist_ok=False)
    c.write_once(claim / "proposal.json", proposal)
    c.write_once(claim / "submission-intent.json", intent(proposal))
    with (claim / "batch.sh").open("xb") as stream:
        stream.write(batch_script(proposal))
        stream.flush()
        os.fsync(stream.fileno())
    if latch.reason is not None:
        c.write_once(claim / "stop.json", {"reason": "interrupted_before_submit", **p.FLAGS})
        return {"status": "stopped_before_submit", **p.FLAGS}
    try:
        verify(proposal, role="login")
        s.require(latch.reason is None, "Stopped before qualification callback.")
        job = l.first.parse_acknowledgement(submit(submit_argv(proposal)))
        release = l.acknowledged(proposal, job)
        validate(release, spec["source_commit"])
        gate = g.qualify_release(
            release, commit=spec["source_commit"], release_digest=s.digest(release)
        )
        g.review_gate(gate, commit=spec["source_commit"], job=job, release_digest=s.digest(release))
        c.write_once(claim / "release.json", release)
        if latch.reason is not None:
            c.write_once(claim / "stop.json", {"reason": "interrupted_after_submit", **p.FLAGS})
        receipt = {
            "source_commit": spec["source_commit"],
            "job_id": job,
            "release_sha256": s.digest(release),
            "specification_sha256": s.digest(release["plan"]["specification"]),
        }
        c.write_once(claim / "job.json", receipt)
        return {
            "status": "qualification_acknowledgement_preserved_not_admitted",
            **receipt,
            **p.FLAGS,
        }
    except (Exception, KeyboardInterrupt):
        c.write_once(
            claim / "submission-unknown.json", {"status": "unknown_effect_no_retry", **p.FLAGS}
        )
        return {"status": "unknown_effect_no_retry", **p.FLAGS}


def load(commit):
    """Only this new claim, never discover or load a historical predecessor."""
    claim = claim_path()
    proposal = validate(c.decode_json(a._file(claim / "proposal.json", l.LIMIT)), commit)
    s.require(
        c.decode_json(a._file(claim / "submission-intent.json", 8192)) == intent(proposal)
        and a._file(claim / "batch.sh", 8192) == batch_script(proposal),
        "Submission descriptor drift.",
    )
    receipt = c.decode_json(a._file(claim / "job.json", 8192))
    q._keys(receipt, {"source_commit", "job_id", "release_sha256", "specification_sha256"})
    release = validate(l.acknowledged(proposal, receipt["job_id"]), commit)
    spec = release["plan"]["specification"]
    s.require(
        receipt
        == {
            "source_commit": commit,
            "job_id": spec["job_id"],
            "release_sha256": s.digest(release),
            "specification_sha256": s.digest(spec),
        }
        and c.decode_json(a._file(claim / "release.json", l.LIMIT)) == release,
        "Acknowledged release drift.",
    )
    gate = g.qualify_release(release, commit=commit, release_digest=s.digest(release))
    g.review_gate(gate, commit=commit, job=spec["job_id"], release_digest=s.digest(release))
    return release


def resume_components(proposal, latch, *, submit, collect):
    """Existing/uncertain claim can only collect; callback never retries."""
    s.require(callable(submit) and callable(collect), "Explicit qualification callbacks.")
    proposal = validate(proposal, proposal["envelope"]["source_commit"])
    if claim_path().exists():
        return collect(proposal["envelope"]["source_commit"])
    return reserve_components(proposal, latch, submit=submit)


def role_components(release, *, role, job_id, specification_digest, dispatch):
    s.require(role in {"batch", "worker"} and callable(dispatch), "Explicit role/dispatch.")
    release, source, runtime = verify(release, role=role)
    spec = release["plan"]["specification"]
    claim = claim_path()
    s.require(
        load(spec["source_commit"]) == release
        and job_id == spec["job_id"] != "1"
        and specification_digest == s.digest(spec)
        and not (claim / "stop.json").exists()
        and not (claim / "submission-unknown.json").exists(),
        "Stopped/unbound compute role.",
    )
    (claim / (role + "-claim")).mkdir(mode=0o700, exist_ok=False)
    if role == "worker":
        root = Path(spec["run"])
        g.f.same(
            {"claim.json": a._file(root / "claim.json", 8192)},
            "claim.json",
            {"specification_sha256": s.digest(spec), **a.FLAGS},
        )
        c.write_once(
            root / "worker-identity.json",
            {
                "schema_version": "s2-resource-launcher-worker-v1",
                "source": source,
                "runtime": runtime,
                "release_sha256": s.digest(release),
                "specification_sha256": s.digest(spec),
                **p.FLAGS,
            },
        )
    return dispatch(
        copy.deepcopy(spec), copy.deepcopy(source), copy.deepcopy(runtime), worker_argv(release)
    )


def await_acknowledgement(claim, latch, *, clock, sleep):
    """Bounded role-entry race handling, with no guessed job or implicit effect."""
    deadline = clock() + 30
    while not (claim / "job.json").exists():
        s.require(
            clock() < deadline
            and latch.reason is None
            and not (claim / "stop.json").exists()
            and not (claim / "submission-unknown.json").exists(),
            "No complete acknowledgement.",
        )
        sleep(0.2)
    s.require(
        latch.reason is None
        and not (claim / "stop.json").exists()
        and not (claim / "submission-unknown.json").exists(),
        "Stopped/uncertain role entry.",
    )


def adapter_components(spec, source, runtime, argv, *, adapter, latch, sleep):
    """No old coupled sampler or default adapter may enter the normal loop."""
    s.require(isinstance(adapter, d.DiagnosticNormalAdapter), "Diagnostic adapter required.")
    return l.adapter_components(
        spec, source, runtime, argv, adapter=adapter, latch=latch, sleep=sleep
    )


class DiagnosticOperationalTransport(n.x.ComputeTransport):
    """Fixed worker descriptor; constructed only by explicit qualification code."""

    def __init__(self, spec, *, release, **kwargs):
        release = validate(release, spec["source_commit"])
        s.require(release["plan"]["specification"] == spec, "Transport specification drift.")
        super().__init__(spec, release_digest=s.digest(release), **kwargs)
        self.release = release

    def worker_command(self):
        return worker_argv(self.release)


class DiagnosticOperationalAdapter(d.DiagnosticNormalAdapter):
    """Complete role-bound component; no implicit transport or public CLI launch."""

    def __init__(self, spec, *, release, transport, **kwargs):
        release = validate(release, spec["source_commit"])
        s.require(release["plan"]["specification"] == spec, "Adapter specification drift.")
        super().__init__(spec, transport=transport, **kwargs)
        self.release = release

    def launch(self):
        value = load(self.item["source_commit"])
        value, source, runtime = verify(value, role="batch")
        claim = claim_path()
        s.require(
            value == self.release
            and value["plan"]["specification"] == self.item
            and source == self.source
            and runtime == self.runtime
            and self.worker_command() == worker_argv(value)
            and os.environ.get("SLURM_JOB_ID") == self.item["job_id"]
            and (claim / "batch-claim").is_dir()
            and not (claim / "stop.json").exists()
            and not (claim / "submission-unknown.json").exists(),
            "Diagnostic launch binding.",
        )
        return a.BatchAdapter.launch(self)


def cached_collection(saved, release):
    result = c.decode_json(a._file(saved, l.LIMIT))
    q._keys(result, {"status", "download", "sha256", "transfer_checksum", "review", *p.FLAGS})
    target = Path(result["download"])
    q._safe_path(target)
    s.require(
        target.parent.parent == Path(BASE)
        and target.parent.name.startswith("s2dc-")
        and target.name == "s2-diagnostic-normal-evidence.tar.gz"
        and result["transfer_checksum"] == str(target) + ".sha256"
        and all(result[k] is False for k in p.FLAGS),
        "Cached collection location/authority.",
    )
    q._hash(result["sha256"])
    s.require(
        a._file(result["transfer_checksum"], 256)
        == (result["sha256"] + "  " + target.name + "\n").encode(),
        "Cached sidecar drift.",
    )
    spec = release["plan"]["specification"]
    replay = forensic.audit(
        target,
        result["sha256"],
        commit=spec["source_commit"],
        job=spec["job_id"],
        release_digest=s.digest(release),
    )
    s.require(
        result["review"] == replay and result["status"] == replay["status"], "Cached review drift."
    )
    return result


def collect_components(commit, *, terminal_text, destination):
    """Bounded resumable collection outside all claims; no implicit query or retry."""
    s.require(callable(terminal_text) and callable(destination), "Explicit collection callbacks.")
    claim = claim_path()
    if not (claim / "job.json").exists():
        return {"status": "unacknowledged_claim_no_retry", **p.FLAGS}
    value = load(commit)
    saved = claim / "diagnostic-collection.json"
    if saved.exists():
        return cached_collection(saved, value)
    spec = value["plan"]["specification"]
    text = terminal_text(copy.deepcopy(value))
    s.require(type(text) is str and len(text.encode()) <= 65536, "Accounting text bound.")
    _rows, ready = g.f.terminal_rows(text, spec["job_id"])
    if not ready:
        return {"status": "nonterminal_or_accounting_pending", **p.FLAGS}
    target = Path(destination())
    s.require(
        target.parent == Path(BASE) and target.name.startswith("s2dc-"),
        "Fresh derived collection location.",
    )
    q._safe_path(target)
    for preserved in (Path(spec["run"]), Path(spec["checkout"]), claim):
        s.require(
            target != preserved
            and target not in preserved.parents
            and preserved not in target.parents,
            "Collection covers preserved data.",
        )
    s.require(load(commit) == value, "Release changed before capture.")
    captured = forensic.capture(spec["run"], claim, spec["job_id"])
    target.mkdir(mode=0o700, exist_ok=False)
    result = None
    if "claim.json" in captured["inventory"]:
        try:
            result = g.collect_components(
                spec["run"],
                target / "diagnostic",
                value,
                text,
                commit=commit,
                release_digest=s.digest(value),
            )
        except (ValueError, KeyError, TypeError, IndexError, UnicodeError, RecursionError):
            pass  # Preserve metadata; never reconstruct an invalid run binding.
    s.require(
        captured == forensic.capture(spec["run"], claim, spec["job_id"]),
        "Forensic capture changed.",
    )
    if result is None:
        gate = g.qualify_release(value, commit=commit, release_digest=s.digest(value))
        rows, _ready = g.f.terminal_rows(text, spec["job_id"])
        carrier = {
            "schema_version": forensic.SCHEMA,
            "gate": gate,
            "accounting_text": text,
            "accounting": rows,
            "capture": captured,
            "disposition": "no_bound_attempt"
            if "claim.json" not in captured["inventory"]
            else "run_binding_rejected",
            **p.FLAGS,
        }
        result = forensic.pack(
            target, carrier, commit=commit, job=spec["job_id"], release_digest=s.digest(value)
        )
    else:
        # Copy only the already verified derived archive, never move originals.
        archive = target / "s2-diagnostic-normal-evidence.tar.gz"
        with archive.open("xb") as stream:
            stream.write(a._file(result["download"], g.f.LIMIT))
        sidecar = str(archive) + ".sha256"
        with open(sidecar, "x", encoding="ascii", newline="\n") as stream:
            stream.write(result["sha256"] + "  " + archive.name + "\n")
        result = {**result, "download": str(archive), "transfer_checksum": sidecar}
    s.require(load(commit) == value, "Release changed during capture.")
    s.require(
        forensic.audit(
            result["download"],
            result["sha256"],
            commit=commit,
            job=spec["job_id"],
            release_digest=s.digest(value),
        )
        == result["review"],
        "Operational archive replay drift.",
    )
    c.write_once(saved, result)
    return result
