"""One normal synthetic operational wrapper; no adverse/native/h300/retry route.

Only a separately reviewed merged source and human login CLI can start this
one-shot attempt. Generic component entries remain closed. Receipts retain
non-admission flags; installed containment requires later independent audit.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import secrets
import sys
import time
from pathlib import Path

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in {
        "start",
        "status",
        "wait",
        "collect",
        "batch",
        "worker",
        "audit",
    }:
        raise PermissionError("One normal operational wrapper only.")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import mvp2_h300_controls as c  # noqa: E402
from scripts import mvp2_s2_batch_adapter as a  # noqa: E402
from scripts import mvp2_s2_compute_integration as integration  # noqa: E402
from scripts import mvp2_s2_resource_forensics as forensic  # noqa: E402
from scripts import mvp2_s2_resource_launcher as launcher  # noqa: E402
from scripts import mvp2_s2_resource_normal as normal  # noqa: E402

s, q, o, first = launcher.s, launcher.q, launcher.o, launcher.first
ENTRY = launcher.OPERATIONAL_ENTRY
DRIVER = "scripts/npad_s2_resource_normal.sh"
INTEGRATED_BASE = "f1ab13568cd961d1bf0a61638caa2d3874b9fa8c"


def validate_operational(value, commit):
    value = launcher.validate_release(value, commit, s.digest(value))
    s.require({ENTRY, DRIVER} <= value["manifest"]["files"].keys(), "Operational source closure.")
    return value


def local_entry(value, commit):
    spec = value["plan"]["specification"]
    s.require(
        spec["source_commit"] == commit
        and Path(__file__).resolve() == Path(spec["checkout"]) / ENTRY
        and Path(sys.executable).resolve() == Path(spec["python"]),
        "Frozen operational entry/runtime.",
    )


def load(commit, *, proposal_digest=None, release_digest=None):
    value = validate_operational(launcher.load_release(entry=ENTRY), commit)
    local_entry(value, commit)
    if proposal_digest is not None:
        q._hash(proposal_digest)
        proposal = c.decode_json(a._file(launcher.claim_path() / "proposal.json", launcher.LIMIT))
        s.require(s.digest(proposal) == proposal_digest, "Batch proposal digest drift.")
    if release_digest is not None:
        q._hash(release_digest)
        s.require(s.digest(value) == release_digest, "Worker release digest drift.")
    return value


def start(commit):
    first.require_host()
    q._hash(commit, 40)
    claim = launcher.claim_path()
    if claim.exists():
        return collect(commit)  # Existing or uncertain claims never reach sbatch.
    root = Path(__file__).resolve().parents[1]
    env = o.observe_envelope(root, commit)
    proposal = launcher.prepare(
        env, run=o.BASE + "/s2n-" + secrets.token_hex(4), nonce=secrets.token_hex(32)
    )
    proposal = validate_operational(proposal, commit)
    local_entry(proposal, commit)
    spec = proposal["plan"]["specification"]
    transport = a.RealTransport(spec)
    allowed = launcher.submit_argv(proposal)

    def submit(argv):
        s.require(argv == allowed, "Fixed normal submission descriptor.")
        return transport._open(argv).query_result(10, 4096)

    with o.StopLatch().installed() as latch:
        result = launcher.reserve_components(proposal, latch, submit=submit, entry=ENTRY)
    if result["status"] == "acknowledgement_preserved_not_admitted":
        result = {**result, "status": "submitted_normal_only"}
    return result


class OperationalTransport(integration.ComputeTransport):
    def __init__(self, spec, *, release, **kwargs):
        super().__init__(spec, release_digest=s.digest(release), **kwargs)
        self.release = copy.deepcopy(release)

    def worker_command(self):
        return launcher.worker_argv(self.release, entry=ENTRY)


class OperationalAdapter(normal.ResourceNormalAdapter):
    """Fixed normal entry; the generic resource adapter keeps its closed launch."""

    def __init__(self, spec, *, release, **kwargs):
        super().__init__(spec, **kwargs)
        self.release = copy.deepcopy(release)

    def launch(self):
        value = load(self.item["source_commit"], release_digest=s.digest(self.release))
        checked, source, runtime = launcher.verify_release(value, s.digest(value), role="batch")
        s.require(
            checked == self.release
            and checked["plan"]["specification"] == self.item
            and source == self.source
            and runtime == self.runtime
            and os.environ.get("SLURM_JOB_ID") == self.item["job_id"]
            and (launcher.claim_path() / "batch-claim").is_dir()
            and not (launcher.claim_path() / "stop.json").exists(),
            "Normal launch binding.",
        )
        return a.BatchAdapter.launch(self)


def await_acknowledgement(claim, latch, *, clock=time.monotonic, sleep=time.sleep):
    deadline = clock() + 30
    while not (claim / "job.json").exists():
        s.require(
            clock() < deadline
            and latch.reason is None
            and not (claim / "stop.json").exists()
            and not (claim / "submission-unknown.json").exists(),
            "No acknowledged release; never guess a job.",
        )
        sleep(0.2)
    s.require(latch.reason is None and not (claim / "stop.json").exists(), "Stopped batch release.")


def batch_dispatch(
    value,
    source,
    runtime,
    argv,
    started,
    latch,
    *,
    adapter_factory=OperationalAdapter,
    transport_factory=OperationalTransport,
    sleep=time.sleep,
):
    spec = value["plan"]["specification"]
    transport = transport_factory(spec, release=value, preflight_deadline=started + 120)
    adapter = adapter_factory(spec, release=value, transport=transport, allocation_started=started)
    adapter.preflight(
        uid=os.getuid(),
        pid=os.getpid(),
        node=os.uname().nodename,
        source=source,
        tool_sha256=spec["tools_sha256"],
        python_sha256=spec["python_sha256"],
    )
    s.require(adapter.runtime == runtime, "Batch preflight runtime drift.")
    return launcher.adapter_components(
        spec, source, runtime, argv, adapter=adapter, latch=latch, sleep=sleep
    )


def batch(commit, proposal_digest):
    started, phase = time.monotonic(), "release"
    claim = launcher.claim_path()
    try:
        first.require_host()
        with o.StopLatch().installed() as latch:
            await_acknowledgement(claim, latch)
            value = load(commit, proposal_digest=proposal_digest)
            spec = value["plan"]["specification"]
            phase = "dispatch"

            def dispatch(actual, source, runtime, argv):
                s.require(actual == spec, "Batch specification drift.")
                return batch_dispatch(value, source, runtime, argv, started, latch)

            result = launcher.role_components(
                value,
                role="batch",
                job_id=os.environ.get("SLURM_JOB_ID"),
                specification_digest=s.digest(spec),
                dispatch=dispatch,
                entry=ENTRY,
            )
        report = {
            "schema_version": "s2-resource-operational-batch-v1",
            "source_commit": commit,
            "status": "attempt_preserved",
            "controller_state": result["attempt"]["status"],
            **normal.p.FLAGS,
        }
        c.write_once(claim / "batch-outcome.json", report)
        return report
    except (Exception, KeyboardInterrupt) as error:
        diagnostic = integration.emit_error("batch", phase, error)
        c.write_once(
            claim / "batch-outcome.json",
            {
                "schema_version": "s2-resource-operational-batch-v1",
                "source_commit": commit,
                "status": "blocked_or_incomplete_attempt",
                "diagnostic": diagnostic,
                **normal.p.FLAGS,
            },
        )
        raise SystemExit(2) from None


def worker(commit, specification_digest, release_digest):
    try:
        first.require_host()
        value = load(commit, release_digest=release_digest)

        def dispatch(spec, _source, _runtime, _argv):
            return o.worker_dispatch_components(
                spec, specification_digest, spec["run"] + "/worker-plan.json"
            )

        return launcher.role_components(
            value,
            role="worker",
            job_id=os.environ.get("SLURM_JOB_ID"),
            specification_digest=specification_digest,
            dispatch=dispatch,
            entry=ENTRY,
        )
    except (Exception, KeyboardInterrupt) as error:
        integration.emit_error("worker", "dispatch", error)
        raise SystemExit(2) from None


def terminal_text(value):
    spec = value["plan"]["specification"]
    first.recheck(value["envelope"])  # Login only. Never used by batch/worker.
    return a.RealTransport(spec).command(
        (
            spec["tools"]["sacct"],
            "--noheader",
            "--parsable2",
            "--jobs=" + spec["job_id"],
            "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw",
        )
    )


def status(commit):
    first.require_host()
    if not (launcher.claim_path() / "job.json").exists():
        return {"status": "unacknowledged_claim_no_retry", **normal.p.FLAGS}
    value = load(commit)
    spec = value["plan"]["specification"]
    rows, ready = forensic.terminal_rows(terminal_text(value), spec["job_id"])
    return {
        "status": "terminal" if ready else "nonterminal_or_accounting_pending",
        "job_id": spec["job_id"],
        "accounting": rows,
        **normal.p.FLAGS,
    }


def cached_collection(saved, value):
    result = c.decode_json(a._file(saved, launcher.LIMIT))
    spec, claim = value["plan"]["specification"], launcher.claim_path()
    target = Path(result["download"])
    q._safe_path(target)
    s.require(
        target.parent.parent == claim
        and target.parent.name.startswith("collection-")
        and target.name == "s2-resource-normal-evidence.tar.gz"
        and result["transfer_checksum"] == str(target) + ".sha256"
        and a._file(str(target) + ".sha256", 256)
        == (result["sha256"] + "  " + target.name + "\n").encode(),
        "Cached collection location/checksum drift.",
    )
    review = forensic.audit(
        target,
        result["sha256"],
        commit=spec["source_commit"],
        job=spec["job_id"],
        release_digest=s.digest(value),
    )
    s.require(
        result["review"] == review and result["status"] == review["status"], "Cached review drift."
    )
    return result


def collect(commit):
    first.require_host()
    claim = launcher.claim_path()
    if not (claim / "job.json").exists():
        return {"status": "unacknowledged_claim_no_retry", **normal.p.FLAGS}
    value = load(commit)
    saved = claim / "collection.json"
    if saved.exists():
        return cached_collection(saved, value)
    text = terminal_text(value)
    spec = value["plan"]["specification"]
    _rows, ready = forensic.terminal_rows(text, spec["job_id"])
    if not ready:
        return {
            "status": "nonterminal_or_accounting_pending",
            "job_id": spec["job_id"],
            **normal.p.FLAGS,
        }
    # Do not precreate destination: the immutable collector owns exclusive mkdir.
    destination = claim / ("collection-" + secrets.token_hex(8))
    result = forensic.collect_components(
        spec["run"], destination, value, text, release_loader=lambda: load(commit)
    )
    c.write_once(saved, result)
    return result


def wait_collect(commit, *, sleep=time.sleep):
    while True:
        result = collect(commit)
        if result["status"] != "nonterminal_or_accounting_pending":
            return result
        print(
            "RESOURCE_NORMAL_STATUS=nonterminal_or_accounting_pending JOB_ID=" + result["job_id"],
            flush=True,
        )
        sleep(20)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="action", required=True)
    for action in ("start", "status", "wait", "collect", "batch", "worker", "audit"):
        child = subs.add_parser(action)
        child.add_argument("--source-sha", required=True)
        if action == "batch":
            child.add_argument("--proposal-sha", required=True)
        if action in {"worker", "audit"}:
            child.add_argument("--release-sha", required=True)
        if action == "worker":
            child.add_argument("--specification-sha", required=True)
        if action == "audit":
            for key in ("archive", "sha256", "job"):
                child.add_argument("--" + key, required=True)
    args = parser.parse_args()
    if args.action == "worker":
        worker(args.source_sha, args.specification_sha, args.release_sha)
        return 0
    if args.action == "batch":
        result = batch(args.source_sha, args.proposal_sha)
    elif args.action == "audit":
        result = forensic.audit(
            args.archive,
            args.sha256,
            commit=args.source_sha,
            job=args.job,
            release_digest=args.release_sha,
        )
    else:
        result = {"start": start, "status": status, "wait": wait_collect, "collect": collect}[
            args.action
        ](args.source_sha)
    print("RESOURCE_NORMAL_STATUS=" + result["status"])
    if args.action != "audit":
        print("PRESERVE_CLAIM=" + str(launcher.claim_path()))
    for key in (
        "job_id",
        "proposal_sha256",
        "release_sha256",
        "sha256",
        "download",
        "transfer_checksum",
    ):
        if result.get(key):
            print(key.upper() + "=" + result[key])
    if "accounting" in result:
        print("ACCOUNTING=" + json.dumps(result["accounting"], sort_keys=True))
    print("NO_ADVERSE_NATIVE_MINIATURE_H300_OR_REPEAT_ADMITTED")
    return (
        2
        if result["status"]
        in {"unacknowledged_claim_no_retry", "unknown_effect_no_retry", "stopped_before_submit"}
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
