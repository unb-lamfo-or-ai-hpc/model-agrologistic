"""Read-only normal outcome audit and disconnected diagnostic qualification.

No live observer/transport, execution, retry or cleanup acceptance is provided.
Historical event/sample schemas and controller predicates remain unchanged.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "audit":
        raise PermissionError("Read-only transferred-archive audit only.")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import mvp2_s2_resource_forensics as f  # noqa: E402

CHANNELS = ("launcher", "members", "resources", "products", "accounting", "absence")


def observe_channels(readers):
    """Disconnected seam: keep diagnostic channels independent, never admit.

    Callbacks must supply separately validated bounded observations in a future
    reviewed integration. Only canonical hashes/error classes leave this seam;
    neither values, paths nor exception messages are exported. Unavailability
    is not empty membership, zero use, terminal accounting or cleanup proof.
    """
    f.q._keys(readers, set(CHANNELS))
    f.s.require(all(callable(v) for v in readers.values()), "Diagnostic reader schema.")
    observations = {}
    for name in CHANNELS:
        try:
            value = readers[name]()
            observations[name] = {
                "status": "observed_not_qualified",
                "semantic_sha256": f.s.digest(value),
                "error_kind": None,
            }
        except (OSError, ValueError, TimeoutError, KeyError, UnicodeError, TypeError) as error:
            observations[name] = {
                "status": "unavailable",
                "semantic_sha256": None,
                "error_kind": (
                    "missing"
                    if isinstance(error, FileNotFoundError)
                    else "timeout"
                    if isinstance(error, TimeoutError)
                    else "os_error"
                    if isinstance(error, OSError)
                    else "invalid_observation"
                ),
            }
    return {
        "schema_version": "s2-normal-diagnostic-channels-v1",
        "observations": observations,
        "any_unavailable": any(v["status"] == "unavailable" for v in observations.values()),
        **f.normal.p.FLAGS,
    }


def audit_archive(path, checksum, *, commit, job, release_digest):
    """Externally bound portable replay plus conservative outcome explanation."""
    review = f.audit(path, checksum, commit=commit, job=job, release_digest=release_digest)
    raw = f.a._file(path, f.LIMIT)
    f.s.require(f.hashlib.sha256(raw).hexdigest() == checksum, "Archive changed during audit.")
    records = f.launcher.first.read_tar(raw, f.LIMIT, f.MEMBERS)
    carrier = f.c.decode_json(records["carrier.json"])
    evidence = carrier["evidence"]
    events = evidence["events"] if evidence is not None else []
    samples = carrier["samples"]
    observations = [v for v in events if v["kind"] == "observation"]
    signals = [
        {"seconds": v["seconds"], "action": v["payload"]["action"]}
        for v in observations
        if v["payload"]["action"] in {"TERM_exact_step", "KILL_exact_step"}
    ]
    barriers = evidence["barriers"] if evidence is not None else []
    resource = copy.deepcopy(barriers[0]["resource"]) if barriers else None
    products = carrier["worker_products"]
    first = observations[0] if observations else None
    return {
        "schema_version": "s2-normal-outcome-audit-v1",
        "source_commit": commit,
        "job_id": job,
        "release_sha256": release_digest,
        "archive_sha256": checksum,
        "portable_review": review,
        "accounting": copy.deepcopy(carrier["accounting"]),
        "source": copy.deepcopy(carrier["anchor"]["source"]),
        "barrier_count": len(barriers),
        "initial_resource_observation": resource,
        "sample_count": len(samples),
        "fault_sample_count": sum(v["fault"] for v in samples),
        "usable_resource_sample_count": len(evidence["resources"]) if evidence else 0,
        "first_observation": copy.deepcopy(first),
        "last_observation": copy.deepcopy(observations[-1]) if observations else None,
        "signal_intents": signals,
        "worker_phases": [
            products[name]["phase"] for name in sorted(products) if name.startswith("phase-")
        ],
        "worker_terminal_status": products.get("terminal.json", {}).get("status"),
        "outcome": (
            "normal_not_qualified"
            if review["controller_state"] != "candidate_closed"
            else "candidate_requires_independent_live_audit"
        ),
        "fault_exception_recorded": False,
        "cleanup_accepted": False,
        "retry_admitted": False,
        **f.normal.p.FLAGS,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True).add_parser("audit")
    for key in ("archive", "sha256", "source-sha", "job", "release-sha"):
        sub.add_argument("--" + key, required=True)
    args = parser.parse_args()
    result = audit_archive(
        args.archive,
        args.sha256,
        commit=args.source_sha,
        job=args.job,
        release_digest=args.release_sha,
    )
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
