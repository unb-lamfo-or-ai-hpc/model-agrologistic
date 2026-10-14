"""Closed qualification wrapper and terminal/forensic semantic collection.

No live defaults, effects, original-claim loader or public runnable entry point.
Private software journals are explicit inputs, never discovered on NPAD.
"""

from __future__ import annotations

if __name__ == "__main__":
    raise PermissionError("Lifecycle package is software-only; start/collect/execution are closed.")

import copy

from scripts import mvp2_s2_batch_adapter as a
from scripts import mvp2_s2_lifecycle_observer as o

lc = o.lc
LIMIT = 8 * 1024**2
CLOSURE = {
    "scripts/mvp2_s2_lifecycle_protocol.py",
    "scripts/mvp2_s2_lifecycle_observer.py",
    "scripts/mvp2_s2_lifecycle_package.py",
}


def execute(*_args, **_kwargs):
    raise PermissionError("Lifecycle package is closed; no execution admitted.")


def readiness():
    return {
        "schema_version": "s2-lifecycle-readiness-v1",
        "qualification_scope": "offline_reducer_observer_wrapper_and_replay",
        "installed_persistent_observer_qualified": False,
        "live_adapter_implemented": False,
        "operational_claim_reserved": False,
        "additional_source_files": sorted(CLOSURE),
        "missing": [
            "independent_environment_assurance_verifier",
            "current_scheduler_kernel_source_and_ipc_binding",
            "effectful_normal_adapter_and_separately_reviewed_release",
            "installed_persistent_scope_and_no_escape_evidence",
        ],
        **lc.FLAGS,
    }


class QualificationAdapter:
    """Fixed software seam. It never releases IPC, signals, forks or submits."""

    def __init__(self, item):
        self.protocol = lc.Protocol(item)
        self.channels = []

    def observe(self, now, readers):
        channels = o.capture(readers)
        result = self.protocol.sample(now, o.payload(channels))
        self.channels.append(copy.deepcopy(channels))
        return result


def collect(
    item,
    journal,
    accounting_text,
    *,
    source_commit,
    job_id,
    contract_sha256,
    expected_journal_sha256,
):
    """Pure derived collection; externally bound terminal text is mandatory.

    Missing/rejected journals retain only metadata and a negative review. The
    whole private journal is not returned; original inputs are never mutated.
    Hashes bind the source observations, but cannot reconstruct or attest them.
    """
    item = lc.validate_contract(item)
    binding = item["resource_contract"]["legacy_contract"]["binding"]
    lc.q._hash(expected_journal_sha256)
    lc.s.require(
        binding["source_commit"] == source_commit
        and binding["job_id"] == job_id
        and lc.s.digest(item) == contract_sha256,
        "External collection binding drift.",
    )
    lc.s.require(
        type(accounting_text) is str and len(accounting_text.encode()) <= 65536,
        "Accounting text bound.",
    )
    rows = a.accounting(accounting_text, job_id)
    target = job_id + "." + binding["worker_step_id"]
    lc.s.require(
        all(
            key in rows and rows[key]["state"] in a.TERMINAL
            for key in (job_id, job_id + ".batch", target)
        ),
        "Terminal accounting required.",
    )
    if job_id + ".extern" in rows:
        lc.s.require(rows[job_id + ".extern"]["state"] in a.TERMINAL, "Nonterminal extern.")
    raw = lc.q.c.encoded(journal)
    lc.s.require(len(raw) <= LIMIT, "Qualification carrier bound.")
    disposition, review = "missing_journal", None
    if journal is not None:
        disposition = "rejected_journal"
        if lc.s.digest(journal) == expected_journal_sha256:
            try:
                review = lc.replay(item, journal)
                for event in journal:
                    if event["kind"] == "sample":
                        row = event["payload"]["packet"].get("accounting")
                        if row is not None and row["state"] in a.TERMINAL:
                            lc.s.require(
                                row["job_step"] == target
                                and row["state"] == rows[target]["state"]
                                and row["exit_code"] == rows[target]["exit_code"],
                                "Recorded/final step accounting drift.",
                            )
                disposition = "software_replayed_not_live_qualified"
            except (ValueError, TypeError, KeyError, AttributeError, IndexError):
                review = None
    return {
        "schema_version": "s2-lifecycle-forensic-review-v1",
        "source_commit": source_commit,
        "job_id": job_id,
        "contract_sha256": contract_sha256,
        "expected_journal_sha256": expected_journal_sha256,
        "observed_journal_sha256": lc.s.digest(journal),
        "journal_bytes": len(raw),
        "accounting_sha256": lc.s.digest(rows),
        "disposition": disposition,
        "software_review": review,
        "original_inputs_preserved": True,
        "readiness": readiness(),
        **lc.FLAGS,
    }
