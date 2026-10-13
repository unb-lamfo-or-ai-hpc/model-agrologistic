"""Versioned synthetic resource gate; no scheduler, worker or admission CLI.

The maintainer approved a two-logical-CPU hard envelope, not execution. Legacy
contracts/readers remain unchanged. Callers must independently bind allocation,
process ownership and step membership; these observations are not capabilities.
"""

from __future__ import annotations

if __name__ == "__main__":
    raise PermissionError("Resource qualification only; no execution admitted.")

import copy
import re

from scripts import mvp2_s2_scope_diagnostic as d
from scripts import mvp2_s2_slurm_step as s
from scripts import mvp2_s2_slurm_synthetic as q

FLAGS = {
    **q.FLAGS,
    "normal_execution_admitted": False,
    "adverse_execution_admitted": False,
    "live_containment_qualified": False,
    "remote_cleanup_proven": False,
}
POLICY = {
    "worker_cpuset_max_logical_cpus": 2,
    "initial_affinity_logical_cpus": 1,
    "cpu_exclusivity_required": False,
    "shared_cpuacct_worker_attribution": "unavailable",
}
COUNTERS = {
    "memory_usage_bytes",
    "memory_max_usage_bytes",
    "memory_limit_bytes",
    "memory_failcnt",
    "cpu_usage_ns",
    "cpuset_cpu_count",
    "effective_reported_memory_limit_bytes",
    "freezer_group_count",
    "freezer_unique_process_count",
}


def contract(legacy):
    """Explicit new identity; never reinterpret a stored legacy contract."""
    legacy = q.validate_contract(legacy)
    return {
        "schema_version": "s2-synthetic-resources-contract-v2",
        "legacy_contract": legacy,
        "resource_policy": dict(POLICY),
        **FLAGS,
    }


def validate_contract(item):
    q._keys(item, {"schema_version", "legacy_contract", "resource_policy", *FLAGS})
    expected = contract(item["legacy_contract"])
    s.require(s.digest(item) == s.digest(expected), "Resource contract/admission drift.")
    return copy.deepcopy(item)


def cpu_ids(text):
    """Bounded canonical membership, not just a count or a topology inference."""
    s._cpus(text)
    ids = set()
    for part in text.split(","):
        ends = part.split("-")
        ids.update(range(int(ends[0]), int(ends[-1]) + 1))
    return sorted(ids)


def affinity(status):
    s.require(type(status) is str and len(status) <= 65536, "Status bound.")
    fields = re.findall(r"^Cpus_allowed_list:\s*([^\r\n]+)$", status, re.M)
    s.require(len(fields) == 1, "Missing/duplicate CPU affinity.")
    return cpu_ids(fields[0].strip())


def _ids(values):
    s.require(
        type(values) is list
        and 1 <= len(values) <= 2
        and all(type(x) is int and 0 <= x <= 1048575 for x in values)
        and sorted(set(values)) == values,
        "Invalid bounded CPU membership.",
    )
    return set(values)


def _snapshot(value, scopes, memory_mib):
    q._keys(
        value,
        {
            "schema_version",
            "synthetic_observation",
            "status",
            "errors",
            "counters",
            "scopes",
            *s.FLAGS,
        },
    )
    s.require(
        value["schema_version"] == "s2-cgroup-v1-observation-v1"
        and type(value["synthetic_observation"]) is bool
        and value["status"] == "observed_not_qualified"
        and value["errors"] == []
        and all(value[k] is False for k in s.FLAGS),
        "Incomplete/admitting observation.",
    )
    q._keys(value["scopes"], s.CONTROLLERS)
    for key in s.CONTROLLERS:
        observed = value["scopes"][key]
        q._keys(observed, {"path_sha256", "inode"})
        s.require(observed["path_sha256"] == s.digest(scopes[key]["scope"]), "Scope mismatch.")
        s.require(
            type(observed["inode"]) is list
            and len(observed["inode"]) == 2
            and all(type(v) is int and v >= 0 for v in observed["inode"]),
            "Invalid inode.",
        )
    counters = value["counters"]
    q._keys(counters, COUNTERS)
    s.require(
        all(type(v) is int and 0 <= v <= s.MAX_COUNTER for v in counters.values()),
        "Invalid counter.",
    )
    s.require(
        0 < counters["effective_reported_memory_limit_bytes"] <= memory_mib * 1024**2
        and counters["effective_reported_memory_limit_bytes"] <= counters["memory_limit_bytes"]
        and 1 <= counters["freezer_group_count"] <= 128,
        "Unbounded memory/subtree.",
    )
    return counters


def observe(
    item,
    *,
    worker_scopes,
    supervisor_scopes,
    allocation_cpuset,
    worker_snapshot,
    supervisor_snapshot,
    worker_cpus,
    allocation_cpus,
    initial_affinity,
    identities_sha256,
):
    """Redact independently supplied, stable, ownership-bound observations.

    Allocation cpuset must come from an independently verified job scope, NOT
    from the batch task's affinity. We check ancestry, IDs and finite bounds.
    This function performs no kernel or scheduler access and grants no release.
    """
    item = validate_contract(item)
    q._hash(identities_sha256)
    relations = d.relations(worker_scopes, supervisor_scopes)
    s._validate_scope(allocation_cpuset)
    parent = s._absolute(allocation_cpuset["scope"])
    for scopes in (worker_scopes, supervisor_scopes):
        child = scopes["cpuset"]
        s.require(
            child["mount"] == allocation_cpuset["mount"]
            and parent in s._absolute(child["scope"]).parents,
            "Unbound allocation cpuset.",
        )
    for key in ("memory", "freezer", "cpuset"):
        s.require(relations[key]["relation"] == "disjoint", "Shared/nested enforcement scope.")
        s.require(
            worker_snapshot["scopes"][key]["inode"] != supervisor_snapshot["scopes"][key]["inode"],
            "Aliased enforcement inode.",
        )
    accounting = relations["cpuacct"]["relation"]
    s.require(accounting in {"equal", "disjoint"}, "Unqualified accounting relation.")
    wc = _snapshot(worker_snapshot, worker_scopes, 256)
    sc = _snapshot(supervisor_snapshot, supervisor_scopes, 2048)
    s.require(
        worker_snapshot["synthetic_observation"] is supervisor_snapshot["synthetic_observation"],
        "Mixed observation provenance.",
    )
    w, alloc, initial = map(_ids, (worker_cpus, allocation_cpus, initial_affinity))
    s.require(
        len(alloc) == 2 and w <= alloc and len(initial) == 1 and initial <= w,
        "CPU envelope/initial affinity outside allocation.",
    )
    s.require(
        wc["cpuset_cpu_count"] == len(w) and 0 < sc["cpuset_cpu_count"] <= 2,
        "CPU count/membership mismatch.",
    )
    s.require(1 <= wc["freezer_unique_process_count"] <= 64, "Initial worker membership.")
    same_inode = (
        worker_snapshot["scopes"]["cpuacct"]["inode"]
        == supervisor_snapshot["scopes"]["cpuacct"]["inode"]
    )
    s.require(same_inode == (accounting == "equal"), "Accounting path/inode mismatch.")
    result = {
        "schema_version": "s2-synthetic-resources-observation-v2",
        "contract_sha256": s.digest(item),
        "identities_sha256": identities_sha256,
        "synthetic_observation": worker_snapshot["synthetic_observation"],
        "scope_sha256": s.digest(
            [worker_snapshot["scopes"], supervisor_snapshot["scopes"], allocation_cpuset]
        ),
        "enforcement_paths_disjoint": True,
        "worker_cpus": sorted(w),
        "allocation_cpus": sorted(alloc),
        "initial_affinity": sorted(initial),
        "worker_memory_limit_bytes": wc["effective_reported_memory_limit_bytes"],
        "supervisor_memory_limit_bytes": sc["effective_reported_memory_limit_bytes"],
        "worker_memory_peak_bytes": wc["memory_max_usage_bytes"],
        "worker_memory_failcnt": wc["memory_failcnt"],
        "cpuacct_relation": accounting,
        "cpuacct_scope_usage_ns": wc["cpu_usage_ns"],
        # Even disjoint from the supervisor does not prove allocation-exclusive
        # accounting. Worker-only CPU measurement is unavailable in this gate.
        "worker_cpu_usage_ns": None,
        "worker_cpu_attribution": "unavailable",
        "exclusive_cpu_placement_proven": False,
        **FLAGS,
    }
    return validate_observation(result, item)


def validate_observation(value, item):
    item = validate_contract(item)
    q._keys(
        value,
        {
            "schema_version",
            "contract_sha256",
            "identities_sha256",
            "synthetic_observation",
            "scope_sha256",
            "enforcement_paths_disjoint",
            "worker_cpus",
            "allocation_cpus",
            "initial_affinity",
            "worker_memory_limit_bytes",
            "supervisor_memory_limit_bytes",
            "worker_memory_peak_bytes",
            "worker_memory_failcnt",
            "cpuacct_relation",
            "cpuacct_scope_usage_ns",
            "worker_cpu_usage_ns",
            "worker_cpu_attribution",
            "exclusive_cpu_placement_proven",
            *FLAGS,
        },
    )
    s.require(
        value["schema_version"] == "s2-synthetic-resources-observation-v2"
        and value["contract_sha256"] == s.digest(item),
        "Observation binding drift.",
    )
    for key in ("identities_sha256", "scope_sha256"):
        q._hash(value[key])
    s.require(
        type(value["synthetic_observation"]) is bool
        and value["enforcement_paths_disjoint"] is True
        and value["exclusive_cpu_placement_proven"] is False
        and all(value[k] is False for k in FLAGS),
        "Observation authority drift.",
    )
    w, alloc, initial = map(
        _ids, (value["worker_cpus"], value["allocation_cpus"], value["initial_affinity"])
    )
    s.require(
        len(alloc) == 2 and w <= alloc and len(initial) == 1 and initial <= w,
        "CPU membership drift.",
    )
    for key, limit in (
        ("worker_memory_limit_bytes", 256 * 1024**2),
        ("supervisor_memory_limit_bytes", 2048 * 1024**2),
    ):
        s.require(type(value[key]) is int and 0 < value[key] <= limit, "Memory drift.")
    for key in ("worker_memory_peak_bytes", "worker_memory_failcnt", "cpuacct_scope_usage_ns"):
        s.require(type(value[key]) is int and 0 <= value[key] <= s.MAX_COUNTER, "Counter drift.")
    s.require(
        value["cpuacct_relation"] in {"equal", "disjoint"}
        and value["worker_cpu_usage_ns"] is None
        and value["worker_cpu_attribution"] == "unavailable",
        "False CPU attribution.",
    )
    return copy.deepcopy(value)


class ResourceGate:
    """Closed adapter for barrier and subsequent samples; never releases IPC.

    Bind two independently collected initial observations, then check samples
    against the same allocation/scope identity. Original receipts stay immutable.
    The initial affinity is a startup property, NOT a lifetime one-CPU limit.
    """

    def __init__(self, item):
        self.contract = validate_contract(item)
        self.initial = self.previous = None

    def bind(self, first, second):
        s.require(self.initial is None, "Repeated resource binding.")
        first, second = [validate_observation(v, self.contract) for v in (first, second)]
        self._stable(first, second)
        self.initial, self.previous = copy.deepcopy(first), copy.deepcopy(second)
        return self._receipt(second)

    @staticmethod
    def _stable(previous, current):
        changing = {"worker_memory_peak_bytes", "worker_memory_failcnt", "cpuacct_scope_usage_ns"}
        s.require(
            all(current[k] == previous[k] for k in current if k not in changing),
            "Resource binding/limit drift.",
        )
        s.require(all(current[k] >= previous[k] for k in changing), "Counter rollback.")

    def sample(self, value):
        s.require(self.initial is not None, "Unbound resource sample.")
        value = validate_observation(value, self.contract)
        self._stable(self.previous, value)
        self.previous = copy.deepcopy(value)
        return self._receipt(value)

    def _receipt(self, value):
        return {
            "schema_version": "s2-synthetic-resources-review-v2",
            "status": "resource_checks_passed_not_live_qualified",
            "contract_sha256": s.digest(self.contract),
            "observation_sha256": s.digest(value),
            "worker_cpu_usage_ns": None,
            **FLAGS,
        }
