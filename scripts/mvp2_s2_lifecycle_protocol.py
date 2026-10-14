"""Closed lifecycle-aware qualification; observations are not execution authority."""

from __future__ import annotations

if __name__ == "__main__":
    raise PermissionError("Lifecycle software qualification only; all execution stays closed.")

import copy
import re

from scripts import mvp2_s2_synthetic_resources as p

q, s = p.q, p.s
CONTROLLERS = ("memory", "freezer", "cpuset")
FLAGS = {**p.FLAGS, "cleanup_accepted": False, "normal_worker_admitted": False}
POLICY = {
    "quiet_seconds": 5,
    "quiet_minimum_samples": 3,
    "maximum_sample_gap_seconds": 5,
    "cleanup_seconds": 390,
    "maximum_groups": 128,
    "maximum_depth": 16,
    "maximum_members": 64,
    "maximum_samples": 1024,
    "post_exit_missing_step_scope": "unobservable_not_empty",
    "query_process_exclusions": "none_queries_must_be_reaped_before_capture",
}
ASSURANCES = {
    "scheduler_job_ownership",
    "kernel_mount_and_namespace_binding",
    "parent_persistence_for_cleanup_window",
    "complete_recursive_controller_coverage",
    "unprivileged_descendants_cannot_migrate_or_escape",
    "no_other_jobs_or_writers_in_parent",
}
WRITE_FILES = {
    *["worker/" + name for name in q.WORKER_FILES],
    "heartbeat.json",
    "heartbeat.pending",
}


def contract(resource_contract):
    return {
        "schema_version": "s2-lifecycle-contract-v1",
        "resource_contract": p.validate_contract(resource_contract),
        "policy": dict(POLICY),
        **FLAGS,
    }


def validate_contract(item):
    q._keys(item, {"schema_version", "resource_contract", "policy", *FLAGS})
    s.require(s.digest(item) == s.digest(contract(item["resource_contract"])), "Contract drift.")
    return copy.deepcopy(item)


def stable(process):
    return q._stable_identity(q._identity(process))


def token(process):
    return s.digest(stable(process))


def inode(value):
    s.require(
        type(value) is list
        and len(value) == 2
        and all(type(v) is int and v >= 0 for v in value)
        and value[1] > 0,
        "Invalid device/inode.",
    )
    return value


def boundary(item, resource_contract):
    """Validate declarations only; a valid schema does not establish persistence."""
    q._keys(
        item,
        {
            "binding",
            "worker",
            "supervisor",
            "controllers",
            "assurance",
            "resource_scope_sha256",
            "owned_batch",
        },
    )
    q._hash(item["resource_scope_sha256"])
    binding = resource_contract["legacy_contract"]["binding"]
    s.require(item["binding"] == binding, "Boundary job/source/nonce drift.")
    worker, supervisor = (stable(item[k]) for k in ("worker", "supervisor"))
    s.require(
        all(item[k]["state"] not in "ZTXx" for k in ("worker", "supervisor")),
        "Dead/stopped initial role.",
    )
    s.require(
        worker["pid"] != supervisor["pid"] and worker["uid"] == supervisor["uid"],
        "Role identity drift.",
    )
    q._keys(item["controllers"], CONTROLLERS)
    owned_batch(item)
    for descriptor in item["controllers"].values():
        q._keys(
            descriptor,
            {
                "mount",
                "parent",
                "worker",
                "supervisor",
                "mount_id",
                "mount_identity",
                "parent_identity",
                "worker_identity",
                "supervisor_identity",
            },
        )
        mount, parent, leaf, batch = (
            s._absolute(descriptor[k]) for k in ("mount", "parent", "worker", "supervisor")
        )
        s.require(
            mount in parent.parents
            and parent in leaf.parents
            and parent in batch.parents
            and leaf != batch
            and leaf not in batch.parents
            and batch not in leaf.parents,
            "Unbound/shared/nested allocation ancestry.",
        )
        s.require(
            type(descriptor["mount_id"]) is int and descriptor["mount_id"] > 0,
            "Mount identity required.",
        )
        identities = [
            inode(descriptor[k + "_identity"]) for k in ("mount", "parent", "worker", "supervisor")
        ]
        s.require(len({tuple(v) for v in identities}) == 4, "Aliased scope identity.")
        s.require(len({v[0] for v in identities}) == 1, "Cross-device ancestry.")
    assurance = item["assurance"]
    q._keys(assurance, {"binding_sha256", "boundary_sha256", "checks"})
    s.require(assurance["binding_sha256"] == s.digest(binding), "Assurance binding drift.")
    s.require(
        assurance["boundary_sha256"]
        == s.digest({k: v for k, v in item.items() if k != "assurance"}),
        "Assurance boundary drift.",
    )
    q._keys(assurance["checks"], ASSURANCES)
    for check in assurance["checks"].values():
        q._keys(check, {"status", "evidence_sha256"})
        s.require(check["status"] == "checked_not_attested", "Incomplete environment assurance.")
        q._hash(check["evidence_sha256"])
    # These are mandatory input obligations, not proof supplied by this module.
    return copy.deepcopy(item)


def owned_batch(bound):
    values = bound["owned_batch"]
    s.require(type(values) is list and len(values) <= 8, "Owned batch role bound.")
    result, roles = {}, set()
    for value in values:
        q._keys(value, {"role", "process", "ownership_evidence_sha256"})
        role, identity = value["role"], stable(value["process"])
        s.require(
            role in {"batch_shell", "local_srun_client"}
            and role not in roles
            and identity["pid"] not in result
            and identity["pid"] not in {bound[k]["pid"] for k in ("worker", "supervisor")}
            and identity["uid"] == bound["supervisor"]["uid"],
            "Owned batch identity drift.",
        )
        q._hash(value["ownership_evidence_sha256"])
        result[identity["pid"]] = identity
        roles.add(role)
    return result


def tree(value, descriptor):
    q._keys(value, {"mount_id", "mount_identity", "parent_identity", "groups"})
    for key in ("mount_id", "mount_identity", "parent_identity"):
        s.require(value[key] == descriptor[key], "Persistent root/mount replaced.")
    groups = value["groups"]
    s.require(type(groups) is list and 1 <= len(groups) <= 128, "Recursive inventory bound.")
    paths, members, locations, identities = {}, {}, {}, set()
    for group in groups:
        q._keys(group, {"relative", "identity", "members"})
        name = group["relative"]
        s.require(type(name) is str and len(name) <= 4096, "Group path bound.")
        path = s._absolute("/" + name) if name else s._absolute("/")
        s.require(len(path.parts) <= 17 and name not in paths, "Group depth/duplicate.")
        ident = tuple(inode(group["identity"]))
        s.require(
            ident not in identities and ident[0] == descriptor["parent_identity"][0],
            "Aliased/cross-device inventory.",
        )
        identities.add(ident)
        paths[name] = group["identity"]
        local = group["members"]
        s.require(type(local) is list and len(local) <= 64, "Member bound.")
        for process in local:
            identity = stable(process)
            pid = identity["pid"]
            s.require(pid not in members, "Duplicate/moving PID in recursive inventory.")
            members[pid] = process
            locations[pid] = name
            s.require(len(members) <= 64, "Total member bound.")
    s.require(paths.get("") == descriptor["parent_identity"], "Missing inventory root.")
    for name in paths:
        if name:
            s.require(name.rpartition("/")[0] in paths, "Incomplete ancestor inventory.")
    for role in ("worker", "supervisor"):
        relative = str(s._absolute(descriptor[role]).relative_to(s._absolute(descriptor["parent"])))
        if relative in paths:
            s.require(paths[relative] == descriptor[role + "_identity"], "Role scope replaced.")
    return members, paths, locations


def inventories(packet, bound):
    q._keys(packet, CONTROLLERS)
    results = [tree(packet[k], bound["controllers"][k]) for k in CONTROLLERS]
    expected = {pid: stable(v) for pid, v in results[0][0].items()}
    s.require(
        all({pid: stable(v) for pid, v in r[0].items()} == expected for r in results),
        "Controller membership disagreement.",
    )
    return (
        results[0][0],
        dict(zip(CONTROLLERS, (r[1] for r in results), strict=True)),
        dict(zip(CONTROLLERS, (r[2] for r in results), strict=True)),
    )


def placements(bound, members, locations):
    outside = {bound["supervisor"]["pid"], *owned_batch(bound)}
    for controller, descriptor in bound["controllers"].items():
        for pid in members:
            role = "supervisor" if pid in outside else "worker"
            relative = str(
                s._absolute(descriptor[role]).relative_to(s._absolute(descriptor["parent"]))
            )
            actual = locations[controller][pid]
            s.require(
                actual == relative or (role == "worker" and actual.startswith(relative + "/")),
                "Process migrated outside its bound role subtree.",
            )


class Protocol:
    """Effect-free software reducer. Candidate means replayable checks, never admission."""

    def __init__(self, item):
        self.item = validate_contract(item)
        self.resource = p.ResourceGate(item["resource_contract"])
        self.bound = None
        self.known = {}
        self.state = "startup"
        self.last = self.ended = self.quiet_at = None
        self.last_observation = None
        self.quiet_count = 0
        self.quiet_hash = None
        self.journal = []
        self.previous = s.digest(self.item)

    def _time(self, now):
        q._number(now)
        s.require(now >= 0 and (self.last is None or now > self.last), "Nonprogressing clock.")
        s.require(now < 660, "Global software observation deadline.")
        return now

    def _event(self, kind, now, payload):
        s.require(len(self.journal) < 1024, "Journal bound.")
        record = {
            "index": len(self.journal),
            "kind": kind,
            "seconds": now,
            "payload": copy.deepcopy(payload),
            "previous_sha256": self.previous,
        }
        self.previous = s.digest(record)
        self.journal.append(record)
        self.last = now

    def bind(self, now, bound, first, second):
        now = self._time(now)
        s.require(self.state == "startup" and now < 30, "Late/repeated barrier.")
        bound = boundary(bound, self.item["resource_contract"])
        for packet in (first, second):
            q._keys(packet, {"inventories", "resources"})
            members, paths, locations = inventories(packet["inventories"], bound)
            placements(bound, members, locations)
            s.require(
                set(members)
                == {bound[k]["pid"] for k in ("worker", "supervisor")} | set(owned_batch(bound)),
                "Unknown initial member/query process.",
            )
            for role in ("worker", "supervisor"):
                s.require(
                    stable(members[bound[role]["pid"]]) == stable(bound[role]),
                    "Barrier process identity drift.",
                )
                for controller, descriptor in bound["controllers"].items():
                    relative = str(
                        s._absolute(descriptor[role]).relative_to(s._absolute(descriptor["parent"]))
                    )
                    s.require(
                        paths[controller].get(relative) == descriptor[role + "_identity"],
                        "Initial role scope unavailable.",
                    )
            value = p.validate_observation(packet["resources"], self.item["resource_contract"])
            s.require(
                all(
                    stable(members[pid]) == identity for pid, identity in owned_batch(bound).items()
                ),
                "Owned batch process identity drift.",
            )
            s.require(
                value["identities_sha256"]
                == s.digest([stable(bound["worker"]), stable(bound["supervisor"])]),
                "Resource/role binding drift.",
            )
            s.require(
                value["scope_sha256"] == bound["resource_scope_sha256"],
                "Resource/scope binding drift.",
            )
        s.require(first["inventories"] == second["inventories"], "Barrier inventory drift.")
        self.resource.bind(first["resources"], second["resources"])
        self.bound = bound
        self.known = {bound["worker"]["pid"]: stable(bound["worker"])}
        self.state = "running"
        self.bound_at = now
        self.last_observation = now
        self._event("bind", now, {"boundary": bound, "first": first, "second": second})
        return self.receipt()

    def register(self, now, process, parent, ownership_evidence_sha256):
        now = self._time(now)
        s.require(self.state == "running", "Late descendant registration.")
        identity = stable(process)
        s.require(
            identity["pid"] not in self.known
            and identity["pid"] not in {self.bound["supervisor"]["pid"], *owned_batch(self.bound)}
            and identity["uid"] == self.bound["worker"]["uid"]
            and stable(parent) == self.known.get(parent["pid"]),
            "Unbound descendant identity.",
        )
        s.require(len(self.known) < 64, "Descendant registry bound.")
        q._hash(ownership_evidence_sha256)
        self.known[identity["pid"]] = identity
        self._event(
            "register",
            now,
            {
                "process": process,
                "parent": parent,
                "ownership_evidence_sha256": ownership_evidence_sha256,
            },
        )

    def end(self, now):
        now = self._time(now)
        s.require(self.state == "running", "Repeated/premature exit observation.")
        s.require(
            now - self.last_observation <= 5 and now - self.bound_at <= 60,
            "Unobserved exercise interval.",
        )
        self.ended, self.state = now, "cleanup"
        self._event("end", now, {})

    def _sample(self, now, packet):
        q._keys(
            packet,
            {
                "inventories",
                "resources",
                "step_scopes",
                "accounting",
                "absence",
                "launcher_reaped",
                "products",
                "assurance_sha256",
                "writes",
            },
        )
        s.require(
            packet["assurance_sha256"] == s.digest(self.bound["assurance"]),
            "Environment coverage assurance drift.",
        )
        members, _paths, locations = inventories(packet["inventories"], self.bound)
        placements(self.bound, members, locations)
        supervisor = stable(self.bound["supervisor"])
        s.require(
            stable(members.get(supervisor["pid"])) == supervisor,
            "Supervisor identity missing/drift.",
        )
        outside = owned_batch(self.bound)
        s.require(
            all(
                stable(members[pid]) == identity
                for pid, identity in outside.items()
                if pid in members
            ),
            "Owned batch role reused.",
        )
        worker_members = {
            pid: stable(v) for pid, v in members.items() if pid not in {supervisor["pid"], *outside}
        }
        s.require(
            all(v == self.known.get(pid) for pid, v in worker_members.items()),
            "Unknown/reused member or query process.",
        )
        q._keys(packet["step_scopes"], CONTROLLERS)
        s.require(
            all(
                v in {"available", "missing", "unavailable"} for v in packet["step_scopes"].values()
            ),
            "Step scope status grammar.",
        )
        s.require(type(packet["launcher_reaped"]) is bool, "Launcher state grammar.")
        products = packet["products"]
        q.verify_worker_products(self.item["resource_contract"]["legacy_contract"], products)
        q._keys(packet["writes"], WRITE_FILES)
        for name, checksum in packet["writes"].items():
            if checksum is not None:
                q._hash(checksum)
            if name.startswith("worker/"):
                product = products.get(name[7:])
                s.require(
                    checksum == (s.digest(product) if product is not None else None),
                    "Product/write inventory drift.",
                )
        if self.state == "running":
            s.require(now - self.bound_at < 60, "Exercise deadline.")
            s.require(
                all(v == "available" for v in packet["step_scopes"].values())
                and self.bound["worker"]["pid"] in worker_members,
                "Live enforcement/leader unavailable.",
            )
            self.resource.sample(packet["resources"])
            return False, None
        s.require(packet["resources"] is None, "Do not synthesize live resources after exit.")
        absence = packet["absence"]
        s.require(
            type(absence) is dict and set(absence) == {s.digest(v) for v in self.known.values()},
            "Incomplete known-identity absence inventory.",
        )
        s.require(
            all(v in {"absent", "present", "reused", "unavailable"} for v in absence.values()),
            "Absence observation grammar.",
        )
        binding = self.item["resource_contract"]["legacy_contract"]["binding"]
        target = binding["job_id"] + "." + binding["worker_step_id"]
        rows = p.q.c.decode_json(p.q.c.encoded(packet["accounting"]))
        q._keys(rows, {"job_step", "state", "exit_code"})
        s.require(
            rows["job_step"] == target
            and rows["state"] in {"COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY"}
            and type(rows["exit_code"]) is str
            and re.fullmatch(r"[0-9]+:[0-9]+", rows["exit_code"]),
            "Bound terminal accounting required.",
        )
        clean = (
            not worker_members
            and packet["launcher_reaped"]
            and all(v == "absent" for v in absence.values())
            and bool({"terminal.json", "failure.json"} & products.keys())
            and not any(
                v["role"] == "local_srun_client" and v["process"]["pid"] in members
                for v in self.bound["owned_batch"]
            )
        )
        return clean, s.digest(packet["writes"])

    def sample(self, now, packet):
        """Failures latch blocked and are journaled; never silently restart quiet time."""
        q._number(now)
        s.require(self.state in {"running", "cleanup"}, "Terminal/unbound protocol.")
        try:
            now = self._time(now)
            s.require(now - self.last_observation <= 5, "Sampling coverage gap.")
            if self.ended is not None:
                s.require(now - self.ended < 390, "Cleanup deadline precedes acceptance.")
            clean, fingerprint = self._sample(now, packet)
            if clean:
                if self.quiet_at is None or fingerprint != self.quiet_hash:
                    self.quiet_at, self.quiet_hash, self.quiet_count = now, fingerprint, 1
                else:
                    self.quiet_count += 1
                if now - self.quiet_at >= 5 and self.quiet_count >= 3:
                    self.state = "software_candidate_closed"
            else:
                self.quiet_at, self.quiet_count = None, 0
            outcome = "checks_observed_not_attested"
        except (ValueError, KeyError, TypeError, IndexError, AttributeError):
            self.state, self.quiet_at = "blocked", None
            outcome = "observation_invalid_or_unknown"
        self._event("sample", now, {"packet": packet, "outcome": outcome})
        self.last_observation = now
        return self.receipt()

    def receipt(self):
        return {
            "schema_version": "s2-lifecycle-software-review-v1",
            "contract_sha256": s.digest(self.item),
            "state": self.state,
            "journal_sha256": self.previous,
            "event_count": len(self.journal),
            "environment_attested": False,
            "worker_cpu_usage_ns": None,
            "installed_cleanup_proven": False,
            **FLAGS,
        }


def replay(item, journal):
    s.require(type(journal) is list and len(journal) <= 1024, "Journal replay bound.")
    reducer = Protocol(item)
    for event in journal:
        q._keys(event, {"index", "kind", "seconds", "payload", "previous_sha256"})
        s.require(
            event["index"] == len(reducer.journal) and event["previous_sha256"] == reducer.previous,
            "Journal tail/order/hash drift.",
        )
        value, now, kind = event["payload"], event["seconds"], event["kind"]
        if kind == "bind":
            q._keys(value, {"boundary", "first", "second"})
            reducer.bind(now, value["boundary"], value["first"], value["second"])
        elif kind == "register":
            q._keys(value, {"process", "parent", "ownership_evidence_sha256"})
            reducer.register(
                now, value["process"], value["parent"], value["ownership_evidence_sha256"]
            )
        elif kind == "end":
            q._keys(value, set())
            reducer.end(now)
        else:
            s.require(kind == "sample", "Unknown lifecycle event.")
            q._keys(value, {"packet", "outcome"})
            reducer.sample(now, value["packet"])
        s.require(reducer.journal[-1] == event, "Replayed event drift.")
    return reducer.receipt()
