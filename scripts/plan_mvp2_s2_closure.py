"""Compile the finite S2 closure campaign; never submit, audit or admit a job.

The executable contract is deliberately a planner, not a new scheduler or an
evidence verifier. Reuse the existing synthetic and h300 policy arithmetic;
missing live evidence and the unqualified native envelope remain explicit.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import mvp2_h300_thread_contract as h  # noqa: E402
from scripts import mvp2_s2_slurm_synthetic as synthetic  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/mvp2_s2_closure_campaign.json"
NORMAL_DRIVER_SHA256 = "3603441668908ecd7132da87b91c75da559e5e63dd68279b647f11417391c0b9"
# One committed definition; this canonical digest detects an unreviewed plan
# edit without duplicating the full graph in code. It is not an authorization.
MANIFEST_SHA256 = "23bced6a6278b288a71a065aea652ef3653d54b1864a6bd79ac653efddfa3740"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate campaign key.")
        result[key] = value
    return result


def load_manifest(path=MANIFEST):
    # Read at most one small planning record. Never inspect an archive/claim/license.
    with Path(path).open("rb") as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise ValueError("Campaign manifest exceeds 64 KiB.")
    return json.loads(raw, object_pairs_hook=unique_object)


def compile_campaign(manifest):
    """Return an inert plan, not acceptance of caller-supplied evidence flags."""
    if hashlib.sha256(canonical(manifest)).hexdigest() != MANIFEST_SHA256:
        raise ValueError("Unreviewed campaign scope, evidence or admission change.")
    policy = h.policy()
    ledger = h.budget_ledger(policy)
    profile = synthetic.PROFILE
    # Freeze the existing profile; changing an imported constant must not silently
    # expand this campaign. Numbers in the report describe requests, not allocation.
    if (
        profile["allocation_cpus"],
        profile["allocation_memory_mib"],
        profile["allocation_wall_seconds"],
    ) != (2, 2048, 720):
        raise ValueError("Synthetic resource policy drift.")
    adverse = manifest["stages"][1]["cases"]
    if set(adverse) != set(synthetic.CASES) - {"normal"} or len(adverse) != 5:
        raise ValueError("Synthetic case coverage drift.")
    driver_hash = hashlib.sha256((ROOT / "scripts/npad_s2_step_normal.sh").read_bytes()).hexdigest()
    if driver_hash != NORMAL_DRIVER_SHA256:
        raise ValueError("Frozen PR80 bootstrap changed; no substitute execution pin.")
    allocation = policy["allocation"]
    synthetic_jobs = 1 + len(adverse)
    synthetic_seconds = synthetic_jobs * profile["allocation_wall_seconds"]
    h300_seconds = allocation["walltime_seconds"]
    return {
        "schema_version": "mvp2-s2-closure-plan-v1",
        "status": "planned_not_execution_admitted",
        "campaign_sha256": hashlib.sha256(canonical(manifest)).hexdigest(),
        "contract": copy.deepcopy(manifest),
        "h300_policy_sha256": h.digest(policy),
        "h300_budget": ledger,
        "synthetic_slots": [
            {
                "case": case,
                "maximum_jobs": 1,
                "cpus": 2,
                "memory_mib": 2048,
                "wall_seconds": 720,
                "execution_admitted_by_this_plan": False,
            }
            for case in ["normal", *adverse]
        ],
        "h300_arms": [
            {
                "ordinal": i + 1,
                "threads": threads,
                "global_optimization_seconds": policy["budget"]["optimization_seconds"],
                "child_watchdog_seconds": ledger["child_seconds"],
                "execution_admitted_by_this_plan": False,
            }
            for i, threads in enumerate(policy["order"])
        ],
        "h300_allocation": copy.deepcopy(allocation),
        "budget": {
            "known_job_slots": synthetic_jobs + 1,
            "known_sequential_allocation_seconds": synthetic_seconds + h300_seconds,
            "known_requested_cpu_hours": (
                synthetic_seconds * profile["allocation_cpus"]
                + h300_seconds * allocation["requested_cpus_per_task"]
            )
            / 3600,
            "h300_requested_cpu_hours": h300_seconds * allocation["requested_cpus_per_task"] / 3600,
            "h300_optimization_seconds_sum": len(h.GRID) * policy["budget"]["optimization_seconds"],
            "native_miniature_allocation_seconds": None,
            "total_campaign_allocation_seconds": None,
            "actual_allocated_cpu_hours": None,
            "queue_and_review_time_included": False,
            "historical_failed_jobs_included": False,
            "normal_slot_is_existing_pr77_not_a_repeat": True,
        },
        "current_blocker": (
            "Job 2209138 failed the shared/nested controller predicate; normal claim consumed"
        ),
        "next_human_action": (
            "Use the separately qualified scope observation; no normal retry or downstream release"
        ),
        "execution_admitted": False,
        "repeats_admitted": False,
        "s2_complete": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument(
        "--check", action="store_true", help="Validate plan only; no output files or jobs"
    )
    args = parser.parse_args(argv)
    plan = compile_campaign(load_manifest(args.manifest))
    if args.check:
        print("S2_CAMPAIGN=VERIFIED_PLANNING_ONLY; NO_JOB_OR_GATE_ADMITTED")
    else:
        print(json.dumps(plan, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
