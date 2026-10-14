"""Read-only interpretation of transferred fast-exit observations, never admission."""

from __future__ import annotations

import argparse
import copy
import json
import sys

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "audit":
        raise PermissionError("Transferred observation audit only; execution stays closed.")
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import mvp2_s2_fast_exit as f  # noqa: E402

ENFORCEMENT = ("memory", "freezer", "cpuset")


def initial_summary(initial):
    """Direct unlimited sentinel and finite inherited ceiling are different quantities."""
    if initial is None:
        return None
    result = {"relations": None, "limits": None, "initial_affinity_in_portable_archive": False}
    summary, limits = initial["summary"], initial["limits"]
    if summary is not None and summary["relations"] is not None:
        result["relations"] = {k: v["relation"] for k, v in summary["relations"].items()}
    if limits is not None:
        result["limits"] = {}
        for role, record in limits.items():
            direct, inherited = (
                record["memory_limit_bytes"],
                record["hierarchical_memory_limit_bytes"],
            )
            valid = record["error_kind"] is None and all(
                type(x) is int and x > 0 for x in (direct, inherited)
            )
            result["limits"][role] = {
                "error_kind": record["error_kind"],
                "cpuset_cpu_count": record["cpuset_cpu_count"],
                "direct_memory_limit_bytes": direct,
                "hierarchical_memory_limit_bytes": inherited,
                "reported_effective_memory_limit_bytes": min(direct, inherited) if valid else None,
                "direct_limit_is_unlimited_sentinel": direct >= f.s.UNLIMITED_FLOOR
                if type(direct) is int
                else None,
            }
    return result


def product_fingerprint(channel):
    if channel["status"] != "available":
        return None
    value = channel["value"]
    if any(item["status"] != "available" for item in value.values()):
        return None
    return {k: item["value"]["sha256"] for k, item in value.items()}


def summarize_sample(item, job, step):
    channels = item["channels"]
    controllers = channels["controllers"]
    controller_states = dict.fromkeys(f.s.CONTROLLERS, "unavailable")
    cpuacct_members = None
    if controllers["status"] == "available":
        controller_states = {k: v["status"] for k, v in controllers["value"].items()}
        cpuacct = controllers["value"]["cpuacct"]
        if cpuacct["status"] == "available":
            members = cpuacct["value"]["files"]["cgroup.procs"]
            if members["status"] == "available":
                cpuacct_members = len(members["value"])
    members, accounting, leader = (channels[k] for k in ("members", "accounting", "leader"))
    step_row = None
    if accounting["status"] == "available" and step is not None:
        step_row = accounting["value"]["data"].get(job + "." + step)
    products = channels["products"]
    return {
        "requested_offset_seconds": item["offset_seconds"],
        "actual_start_seconds_after_client_reaping": item["elapsed_seconds"],
        "channel_statuses": {k: v["status"] for k, v in channels.items()},
        "controller_directory_statuses": controller_states,
        "shared_cpuacct_direct_member_count": cpuacct_members,
        "cpuacct_is_worker_attributed": False,
        "exact_step_member_count": len(members["value"]["data"])
        if members["status"] == "available"
        else None,
        "known_leader_observation": leader["value"] if leader["status"] == "available" else None,
        "accounted_worker_step": copy.deepcopy(step_row),
        "product_file_statuses": {k: v["status"] for k, v in products["value"].items()}
        if products["status"] == "available"
        else None,
    }


def interpret(records, *, checksum, commit, job, plan_sha, portable_review):
    """Validated records only; no new scheduler/kernel effects or inferred cleanup."""
    obs = records["observation.json"]
    if obs is not None:
        f.validate_report(obs, commit, job, plan_sha)
    samples = [] if obs is None else obs["samples"]
    step = None if obs is None else obs["step_id"]
    summaries = [summarize_sample(item, job, step) for item in samples]
    fingerprints = [product_fingerprint(item["channels"]["products"]) for item in samples]
    complete = obs is not None and obs["status"] == "observed_not_admitted"
    blocked_pattern = bool(summaries) and all(
        all(item["controller_directory_statuses"][k] == "missing" for k in ENFORCEMENT)
        and item["channel_statuses"]["members"] != "available"
        for item in summaries
    )
    outcome = (
        "forensic_only_no_live_qualification"
        if obs is None
        else "incomplete_observation_no_live_qualification"
        if not complete
        else "post_exit_step_scopes_unobservable_protocol_decision_required"
        if blocked_pattern
        else "post_exit_observations_require_independent_protocol_review"
    )
    return {
        "schema_version": "s2-fast-exit-outcome-audit-v1",
        "source_commit": commit,
        "job_id": job,
        "plan_sha256": plan_sha,
        "archive_sha256": checksum,
        "portable_review": copy.deepcopy(portable_review),
        "observation_status": None if obs is None else obs["status"],
        "local_client_returncode": None if obs is None else obs["local_client_returncode"],
        "initial_reported_observations": initial_summary(None if obs is None else obs["initial"]),
        "sample_count": len(samples),
        "samples": summaries,
        "reported_product_receipts_stable": all(value is not None for value in fingerprints)
        and all(value == fingerprints[0] for value in fingerprints)
        if fingerprints
        else None,
        "raw_product_contents_in_portable_archive": False,
        "exact_post_exit_rpc_failure_reason_in_portable_archive": False,
        "final_accounting": copy.deepcopy(records["accounting.json"]),
        "outcome": outcome,
        "protocol_decision_required": blocked_pattern,
        "cleanup_accepted": False,
        "worker_only_cpu_usage_available": False,
        "full_run_memory_peak_available": False,
        "scope_deletion_mechanism_proven": False,
        "original_2210506_exception_identified": False,
        "normal_retry_admitted": False,
        **f.FLAGS,
    }


def audit_archive(path, checksum, *, commit, job, plan_sha):
    portable = f.audit(path, checksum, commit, job, plan_sha)
    raw = f.a._file(path, f.LIMIT)
    f.d.require(f.d.digest(raw) == checksum, "Archive changed during outcome audit.")
    records = {
        k: f.d.decode(value)
        for k, value in f.n.read_tar(
            raw, f.LIMIT, {"anchor.json", "observation.json", "accounting.json", "entry.json"}
        ).items()
    }
    return interpret(
        records,
        checksum=checksum,
        commit=commit,
        job=job,
        plan_sha=plan_sha,
        portable_review=portable,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True).add_parser("audit")
    for key in ("archive", "sha256", "source-sha", "job", "plan-sha"):
        sub.add_argument("--" + key, required=True)
    args = parser.parse_args()
    result = audit_archive(
        args.archive, args.sha256, commit=args.source_sha, job=args.job, plan_sha=args.plan_sha
    )
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
