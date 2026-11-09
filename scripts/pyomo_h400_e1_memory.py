"""E1 memory checks for the existing exact-step supervisor."""

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

from scripts import npad_pyomo_h400_e1_cgroup_probe as probe
from scripts import pyomo_h400_e1 as e1
from scripts.pyomo_scaling_contract import encoded, require

CAMPAIGN = ".mvp2-pyomo-h400-e1-native8h-v1"
QUALIFICATION = ".mvp2-pyomo-h400-e1-public-v2"
SCOPES = {"cgroup_v1": "slurm_job_cgroup_v1", "cgroup_v2": "slurm_job_cgroup_v2"}
EVENTS = {
    "cgroup_v1": {"oom_kill": "oom_kill_delta", "failcnt": "failcnt_delta"},
    "cgroup_v2": {"oom": "oom_delta", "oom_kill": "oom_kill_delta"},
}
V2_IDENTITY = (
    b"source=3cee6d3647442806cadc177222b94d34ca1e0799\n"
    b"probe_sha256=ef83c74203685da4d7a41908305aa0bed74ee9f5c05fe0020e37d64d68bc3559\n"
)


def read_small(path):
    require(
        path.is_file() and not path.is_symlink() and path.stat().st_size <= 1024**2,
        "Bounded regular E1 receipt required.",
    )
    return path.read_bytes()


def public_probe_evidence(base, root):
    """Bind the approved technical evidence to bytes still present on NPAD."""
    digests = {}
    for version, job in enumerate(("2247610", "2247615"), 1):
        record = json.loads(read_small(
            root / f"docs/evidence/npad_pyomo_h400_e1_cgroup_{job}_20261109.json"
        ))
        claim = base / f".mvp2-pyomo-h400-e1-cgroup-public-v{version}"
        require(claim.is_dir() and not claim.is_symlink(), "Public cgroup claim differs.")
        require(
            read_small(claim / "submitted-job.txt").decode().strip().split(";")[0] == job,
            "Public cgroup job identity differs.",
        )
        expected = {name: entry["sha256"] for name, entry in record["transferred_logs"].items()}
        expected["npad_pyomo_h400_e1_cgroup_probe.py"] = record["probe_sha256"]
        if version == 2:
            expected["source-identity.txt"] = hashlib.sha256(V2_IDENTITY).hexdigest()
        for name, sha in expected.items():
            actual = hashlib.sha256(read_small(claim / name)).hexdigest()
            require(actual == sha, f"Public cgroup receipt differs: {job}/{name}")
            digests[f"{job}/{name}"] = actual
    return digests


def local_scope(job_id):
    require(os.environ.get("SLURM_JOB_ID") == job_id, "Local Slurm job differs.")
    version, *locations = probe.cgroup_locations(
        Path("/proc/self/cgroup").read_text(encoding="ascii"),
        Path("/proc/self/mountinfo").read_text(encoding="ascii"),
        job_id,
    )
    return version, *(Path(path) for path in locations)


def require_matching_snapshot(snapshot, initial):
    require(
        snapshot["status"] == "cgroup_memory_capabilities_present"
        and snapshot["controller"] == initial["controller"] == "cgroup_v1"
        and snapshot["job_cgroup"] == initial["job_cgroup"]
        and snapshot["effective_member_limit_bytes"] == e1.MEMORY_BYTES,
        "E1 requires the publicly qualified 192 GiB hierarchical v1 job cgroup.",
    )


class JobMemoryGuard:
    def __init__(self, job_id, *, scope=local_scope):
        self.version, self.mount, self.job, self.member = scope(job_id)
        self.limit = e1.limits()["e1_job_peak_bytes"]
        self.trigger = None
        self.initial = self.snapshot()
        require_matching_snapshot(self.initial, self.initial)
        self.check()

    def snapshot(self):
        return probe.memory_snapshot(self.version, self.mount, self.job, self.member)

    def check(self):
        if self.trigger is not None:
            return
        try:
            sample = self.snapshot()
            require_matching_snapshot(sample, self.initial)
            require(
                max(sample["job_current_bytes"], sample["job_peak_bytes"]) < self.limit,
                "E1 job memory threshold reached.",
            )
        except (OSError, ValueError, KeyError) as error:
            self.trigger = {"error_kind": type(error).__name__, "reason": str(error)}
            raise ValueError("E1 memory guard stopped the owned step.") from error

    def receipt(self):
        final = self.snapshot()
        start_events = self.initial["job_memory_events"]
        end_events = final["job_memory_events"]
        result = {
            "scope": SCOPES[self.version],
            "effective_limit_bytes": final["effective_member_limit_bytes"],
            "peak_bytes": final["job_peak_bytes"],
            "guard_triggered": self.trigger is not None,
            "trigger": self.trigger,
            "initial_snapshot": self.initial,
            "final_snapshot": final,
        }
        for name, output in EVENTS[self.version].items():
            result[output] = end_events[name] - start_events[name]
        if self.version == "cgroup_v1":
            result["under_oom_at_end"] = end_events["under_oom"]
        return result

    def clock(self):
        """Read the supervisor's monotonic clock after checking the E1 memory scope."""
        self.check()
        return time.monotonic()

    def run_review(self, argv, out, err, remaining):
        deadline = time.monotonic() + remaining
        self.check()
        with subprocess.Popen(argv, stdout=out, stderr=err, start_new_session=True) as process:
            try:
                while process.poll() is None:
                    self.check()
                    left = deadline - time.monotonic()
                    require(left > 0, "E1 product review deadline exceeded.")
                    try:
                        return process.wait(timeout=min(left, 0.25))
                    except subprocess.TimeoutExpired:
                        continue
                return process.returncode
            finally:
                if process.poll() is None:
                    probe.stop_owned_process(process)


def check_worker(claim, job_id):
    initial = json.loads(read_small(claim / "e1_memory_initial.json"))
    snapshot = probe.memory_snapshot(*local_scope(job_id))
    require_matching_snapshot(snapshot, initial)
    with (claim / "control/sto/e1_worker_cgroup.json").open("xb") as stream:
        stream.write(encoded(snapshot))
