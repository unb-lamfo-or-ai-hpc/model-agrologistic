"""Closed normal-adapter integration of the approved synthetic resource policy.

No driver dispatches this adapter. Public launch denies before effects. The
inherited normal handshake, sampling and exact-step cleanup are qualified with
injected transports; a future immutable release must explicitly admit a new run.
"""

from __future__ import annotations

if __name__ == "__main__":
    raise PermissionError("Resource-normal execution remains closed; no job admitted.")

import copy
import hashlib
import sys
from pathlib import Path, PurePosixPath

from scripts import mvp2_h300_controls as c
from scripts import mvp2_s2_batch_adapter as a
from scripts import mvp2_s2_compute_integration as x
from scripts import mvp2_s2_slurm_step as s
from scripts import mvp2_s2_slurm_synthetic as q
from scripts import mvp2_s2_synthetic_resources as p

LIMIT = 8 * 1024**2


def execute_normal(*_args, **_kwargs):
    raise PermissionError("Resource-normal execution remains closed; no job admitted.")


def proposal(spec):
    spec = a.validate_spec(spec)
    s.require(spec["case"] == "normal", "Normal only.")
    return {
        "schema_version": "s2-resource-normal-proposal-v1",
        "specification_sha256": s.digest(spec),
        "resource_policy": dict(p.POLICY),
        "profile": dict(q.PROFILE),
        **p.FLAGS,
    }


def allocation_scope(scopes, job):
    """Resolve the exact Slurm job component, never infer IDs from affinity/counts."""
    s.require(type(job) is str and job.isascii() and job.isdecimal(), "Job identity.")
    value = scopes["cpuset"]
    s._validate_scope(value)
    candidates = [v for v in PurePosixPath(value["scope"]).parents if v.name == "job_" + job]
    s.require(len(candidates) == 1, "Unbound job cpuset path.")
    result = {"mount": value["mount"], "scope": str(candidates[0])}
    s._validate_scope(result)
    return result


def read_cpu_chain(scope, allocation, *, directory=q.r._Directory):
    """Read exact IDs and inode identities, pinning each ancestor through reread."""
    s._validate_scope(scope)
    s._validate_scope(allocation)
    leaf, parent = map(PurePosixPath, (scope["scope"], allocation["scope"]))
    s.require(scope["mount"] == allocation["mount"] and parent in leaf.parents, "CPU ancestry.")
    paths = [leaf]
    while paths[-1] != parent:
        paths.append(paths[-1].parent)
        s.require(len(paths) <= 16, "CPU ancestor bound.")
    opened = []
    try:
        for path in paths:
            fd = directory(str(path))
            opened.append((path, fd, p.cpu_ids(fd.read("cpuset.cpus"))))
        for _path, _fd, ids in opened:
            p._ids(ids)
        s.require(len(opened[-1][2]) == 2, "Allocation must contain two logical CPUs.")
        for index in range(len(opened) - 1):
            s.require(set(opened[index][2]) <= set(opened[index + 1][2]), "CPU escape.")
        result = []
        for path, fd, ids in opened:
            other = directory(str(path))
            try:
                s.require(
                    other.identity == fd.identity
                    and p.cpu_ids(other.read("cpuset.cpus")) == ids
                    and p.cpu_ids(fd.read("cpuset.cpus")) == ids,
                    "CPU scope changed during read.",
                )
            finally:
                other.close()
            result.append({"path_sha256": s.digest(str(path)), "inode": fd.identity, "cpus": ids})
        return result
    finally:
        for _path, fd, _ids in opened:
            fd.close()


def read_initial_affinity(worker, *, record=q.read_process_record, directory=q.r._Directory):
    pid = worker["identity"]["pid"]
    first = record(pid)
    fd = directory("/proc/" + str(pid))
    try:
        value = p.affinity(fd.read("status"))
        s.require(p.affinity(fd.read("status")) == value, "Initial affinity drift.")
    finally:
        fd.close()
    second = record(pid)
    for observed in (first, second):
        s.require(
            q._stable_identity(observed["identity"]) == q._stable_identity(worker["identity"])
            and observed["identity"]["state"] not in "ZXx"
            and observed["scopes"] == worker["scopes"],
            "Affinity process identity/membership drift.",
        )
    s.require(len(value) == 1, "Initial affinity must be one logical CPU.")
    return value


def capture_resources(adapter, *, initial):
    """Read-only kernel collector. No affinity writes, cgroup writes or subprocesses."""
    s.require(sys.platform == "linux", "Linux resource observation required.")
    allocation = allocation_scope(adapter.worker["scopes"], adapter.item["job_id"])
    s.require(
        allocation_scope(adapter.supervisor["scopes"], adapter.item["job_id"]) == allocation,
        "Worker/batch job scope disagreement.",
    )
    worker_chain = read_cpu_chain(adapter.worker["scopes"]["cpuset"], allocation)
    supervisor_chain = read_cpu_chain(adapter.supervisor["scopes"]["cpuset"], allocation)
    s.require(worker_chain[-1] == supervisor_chain[-1], "Allocation changed between readers.")
    return {
        "allocation_cpuset": allocation,
        "worker_chain": worker_chain,
        "supervisor_chain": supervisor_chain,
        "supervisor_snapshot": s.read_v1_snapshot(adapter.supervisor["scopes"]),
        "initial_affinity": read_initial_affinity(adapter.worker) if initial else None,
    }


def validate_capture(value, worker_snapshot, supervisor_scopes, allocation):
    q._keys(
        value,
        {
            "allocation_cpuset",
            "worker_chain",
            "supervisor_chain",
            "supervisor_snapshot",
            "initial_affinity",
        },
    )
    s.require(value["allocation_cpuset"] == allocation, "Allocation identity drift.")
    for role, snapshot in (
        ("worker", worker_snapshot),
        ("supervisor", value["supervisor_snapshot"]),
    ):
        chain = value[role + "_chain"]
        s.require(type(chain) is list and 2 <= len(chain) <= 16, "CPU chain bound.")
        for entry in chain:
            q._keys(entry, {"path_sha256", "inode", "cpus"})
            q._hash(entry["path_sha256"])
            p._ids(entry["cpus"])
            s.require(
                type(entry["inode"]) is list
                and len(entry["inode"]) == 2
                and all(type(v) is int and v >= 0 for v in entry["inode"]),
                "CPU inode.",
            )
        s.require(
            {k: chain[0][k] for k in ("path_sha256", "inode")} == snapshot["scopes"]["cpuset"]
            and chain[-1]["path_sha256"] == s.digest(allocation["scope"])
            and len(chain[-1]["cpus"]) == 2
            and len(chain[0]["cpus"]) == snapshot["counters"]["cpuset_cpu_count"]
            and all(
                set(chain[i]["cpus"]) <= set(chain[i + 1]["cpus"]) for i in range(len(chain) - 1)
            ),
            "CPU chain/snapshot disagreement.",
        )
    s.require(value["worker_chain"][-1] == value["supervisor_chain"][-1], "Job inode drift.")
    p._snapshot(value["supervisor_snapshot"], supervisor_scopes, 2048)


class Controller(q.Controller):
    """Reuse the unchanged finite cleanup automaton, not the legacy barrier claim."""

    def __init__(self, item, started):
        item = p.validate_contract(item)
        super().__init__(item["legacy_contract"], started)
        self.item = item
        self.previous = s.digest(item)

    def release(self, now, first, second):
        now = self._clock(now)
        s.require(self.state == "startup" and now - self.started < 30, "Late/repeated barrier.")
        for receipt in (first, second):
            q._keys(
                receipt,
                {
                    "schema_version",
                    "resource",
                    "scope_identity_sha256",
                    "members_sha256",
                    "cpu_chain_sha256",
                    *p.FLAGS,
                },
            )
            s.require(
                receipt["schema_version"] == "s2-resource-normal-barrier-v1"
                and all(receipt[k] is False for k in p.FLAGS),
                "Barrier authority drift.",
            )
            for key in ("scope_identity_sha256", "members_sha256", "cpu_chain_sha256"):
                q._hash(receipt[key])
        gate = p.ResourceGate(self.item)
        gate.bind(first["resource"], second["resource"])
        s.require(
            all(
                first[k] == second[k]
                for k in ("scope_identity_sha256", "members_sha256", "cpu_chain_sha256")
            ),
            "Barrier membership drift.",
        )
        self.scope_hash = first["scope_identity_sha256"]
        self.released, self.state, self.released_at = True, "exercise", now
        self._event(now, "release", {"first": first, "second": second})
        return "release_barrier"

    def receipt(self):
        result = super().receipt()
        result.update(schema_version="s2-resource-normal-controller-v1", **p.FLAGS)
        return result


def replay_events(item, events):
    s.require(type(events) is list and len(events) <= q.PROFILE["maximum_events"], "Event bound.")
    controller = Controller(item, 0)
    for event in events:
        q._keys(event, {"index", "seconds", "kind", "payload", "previous_sha256"})
        if event["kind"] == "release":
            q._keys(event["payload"], {"first", "second"})
            controller.release(event["seconds"], **event["payload"])
        else:
            s.require(event["kind"] == "observation", "Unknown event.")
            q._keys(event["payload"], {"inputs", "action", "state"})
            controller.observe(event["seconds"], **event["payload"]["inputs"])
        s.require(c.encoded(controller.events[-1]) == c.encoded(event), "Event replay drift.")
    return controller


class ResourceNormalAdapter(x.ComputeAdapter):
    """Real normal handshake/tick seams, separate resource receipts, closed launch."""

    def __init__(self, item, *, capture=capture_resources, **kwargs):
        super().__init__(item, **kwargs)
        self.proposal = proposal(self.item)
        self.capture = capture
        self.resource_contract = None
        self.resources = []
        self.resource_samples = []

    def launch(self):
        # No environment variable, constructor flag or old CLI can admit this path.
        execute_normal()

    def attempt_schema(self):
        return "s2-resource-normal-attempt-v1"

    def barrier(
        self,
        item,
        pids,
        worker,
        supervisor,
        writer,
        worker_scopes,
        outside_scopes,
        snapshot,
        records,
    ):
        # BatchAdapter already checked peer credentials, executable, exact numeric
        # step, source and allocation, and independently gathered these members.
        worker, supervisor, writer = map(q._identity, (worker, supervisor, writer))
        s.require(
            all(v["state"] not in "ZXx" for v in (worker, supervisor, writer)),
            "Nonlive barrier identity.",
        )
        s.require(
            writer == supervisor
            and worker["pid"] in pids
            and supervisor["pid"] not in pids
            and worker["uid"] == supervisor["uid"] == self.uid,
            "Outside writer/member identity.",
        )
        s.require(
            snapshot["counters"]["freezer_unique_process_count"] == len(pids),
            "Membership disagreement.",
        )
        leaders = [v for v in records if v["identity"]["pid"] == worker["pid"]]
        s.require(
            len(leaders) == 1
            and q._stable_identity(leaders[0]["identity"]) == q._stable_identity(worker)
            and leaders[0]["scopes"] == worker_scopes,
            "Leader moved/reused.",
        )
        self.resource_contract = p.contract(item)
        captured = self.capture(self, initial=True)
        allocation = allocation_scope(worker_scopes, self.item["job_id"])
        validate_capture(captured, snapshot, outside_scopes, allocation)
        observed = p.observe(
            self.resource_contract,
            worker_scopes=worker_scopes,
            supervisor_scopes=outside_scopes,
            allocation_cpuset=allocation,
            worker_snapshot=snapshot,
            supervisor_snapshot=captured["supervisor_snapshot"],
            worker_cpus=captured["worker_chain"][0]["cpus"],
            allocation_cpus=captured["worker_chain"][-1]["cpus"],
            initial_affinity=captured["initial_affinity"],
            identities_sha256=s.digest(
                [q._stable_identity(worker), q._stable_identity(supervisor)]
            ),
        )
        s.require(observed["synthetic_observation"] is False, "Fixture cannot release IPC.")
        receipt = {
            "schema_version": "s2-resource-normal-barrier-v1",
            "resource": observed,
            "scope_identity_sha256": s.digest(snapshot["scopes"]),
            "members_sha256": s.digest(
                [
                    {"identity": q._stable_identity(v["identity"]), "scopes": v["scopes"]}
                    for v in records
                ]
            ),
            "cpu_chain_sha256": s.digest([captured["worker_chain"], captured["supervisor_chain"]]),
            **p.FLAGS,
        }
        s.require(len(self.resources) < 2, "Repeated resource barrier.")
        c.write_once(self.root / f"resource-barrier-{len(self.resources)}.json", receipt)
        self.resources.append(receipt)
        self.resource_capture = copy.deepcopy(captured)
        self.resource_snapshot = copy.deepcopy(snapshot)
        return receipt

    def make_controller(self):
        self.resource_gate = p.ResourceGate(self.resource_contract)
        self.resource_gate.bind(*(v["resource"] for v in self.resources))
        c.write_once(self.root / "resource-contract.json", self.resource_contract)
        return Controller(self.resource_contract, self.started)

    def verify_events(self):
        return replay_events(self.resource_contract, self.controller.events)

    def release_digest(self):
        return s.digest(self.resource_contract)

    def check_snapshot(self, snapshot, pids):
        # Post-exit zero members are legitimate only in sampling, never at bind.
        # Reuse frozen identity facts only after rereading their scopes/limits;
        # do not fabricate a live leader or replace zero members with one.
        p._snapshot(snapshot, self.worker["scopes"], 256)
        s.require(snapshot["synthetic_observation"] is False, "Fixture sample.")
        captured = self.capture(self, initial=False)
        validate_capture(
            captured,
            snapshot,
            self.supervisor["scopes"],
            self.resource_capture["allocation_cpuset"],
        )
        s.require(captured["initial_affinity"] is None, "Sample cannot replace initial affinity.")
        for key in ("worker_chain", "supervisor_chain"):
            s.require(captured[key] == self.resource_capture[key], "CPU identity/membership drift.")
        for current, initial in (
            (snapshot, self.resource_snapshot),
            (captured["supervisor_snapshot"], self.resource_capture["supervisor_snapshot"]),
        ):
            s.require(
                current["synthetic_observation"] is False
                and current["scopes"] == initial["scopes"],
                "Scope replacement.",
            )
            for key in (
                "memory_limit_bytes",
                "effective_reported_memory_limit_bytes",
                "cpuset_cpu_count",
            ):
                s.require(
                    current["counters"][key] == initial["counters"][key], "Resource limit drift."
                )
        s.require(
            snapshot["counters"]["freezer_unique_process_count"] == len(pids) <= 64,
            "Sample membership.",
        )
        observed = copy.deepcopy(self.resource_gate.previous)
        observed.update(
            worker_memory_peak_bytes=snapshot["counters"]["memory_max_usage_bytes"],
            worker_memory_failcnt=snapshot["counters"]["memory_failcnt"],
            cpuacct_scope_usage_ns=snapshot["counters"]["cpu_usage_ns"],
        )
        self.resource_gate.sample(observed)
        record = {
            "index": len(self.samples),
            "members": len(pids),
            "resource": observed,
            "cpu_chain_sha256": self.resources[0]["cpu_chain_sha256"],
            **p.FLAGS,
        }
        c.write_once(self.root / f"resource-sample-{len(self.samples):04d}.json", record)
        self.resource_samples.append(record)

    def preserve(self, *, failure_code=None):
        report = super().preserve(failure_code=failure_code)
        if self.claimed:
            # Distinct carrier: legacy collectors reject its attempt schema.
            record = {
                "schema_version": "s2-resource-normal-evidence-v1",
                "proposal": self.proposal,
                "contract": self.resource_contract,
                "attempt": report,
                "barriers": copy.deepcopy(self.resources),
                "resources": copy.deepcopy(self.resource_samples),
                "events": copy.deepcopy(self.controller.events) if self.controller else [],
                **p.FLAGS,
            }
            c.write_once(self.root / "resource-evidence.json", record)
        return report


def review(value, spec):
    """Independent bounded replay; partial/negative evidence is never admission."""
    spec = a.validate_spec(spec)
    return review_portable(value, portable_binding(spec))


def portable_binding(spec):
    """Export the existing identity without exporting private executable/run paths."""
    spec = a.validate_spec(spec)
    return {
        **{k: copy.deepcopy(spec[k]) for k in ("inventory", "nonce", "source_commit", "job_id")},
        "specification_sha256": s.digest(spec),
        "runtime": x.identity.expected_compute_runtime(spec),
    }


def validate_portable_binding(binding):
    q._keys(
        binding,
        {"inventory", "nonce", "source_commit", "job_id", "specification_sha256", "runtime"},
    )
    for key in ("nonce", "specification_sha256"):
        q._hash(binding[key])
    q._hash(binding["source_commit"], 40)
    s.require(
        type(binding["job_id"]) is str
        and binding["job_id"].isascii()
        and binding["job_id"].isdecimal()
        and not binding["job_id"].startswith("0"),
        "Portable job identity.",
    )
    s.review_inventory(binding["inventory"])
    x.identity.review_compute_runtime(binding["runtime"])
    return copy.deepcopy(binding)


def review_portable(value, binding):
    """Same replay with an externally bound, path-free identity; no receipt rewrite."""
    binding = validate_portable_binding(binding)
    spec = binding
    q._keys(
        value,
        {
            "schema_version",
            "proposal",
            "contract",
            "attempt",
            "barriers",
            "resources",
            "events",
            *p.FLAGS,
        },
    )
    s.require(
        value["schema_version"] == "s2-resource-normal-evidence-v1"
        and value["proposal"]
        == {
            "schema_version": "s2-resource-normal-proposal-v1",
            "specification_sha256": binding["specification_sha256"],
            "resource_policy": dict(p.POLICY),
            "profile": dict(q.PROFILE),
            **p.FLAGS,
        }
        and all(value[k] is False for k in p.FLAGS),
        "Carrier binding/authority drift.",
    )
    attempt = value["attempt"]
    q._keys(
        attempt,
        {
            "schema_version",
            "specification_sha256",
            "status",
            "source",
            "runtime",
            "sample_count",
            "failure_code",
            "live_containment_qualified",
            *a.FLAGS,
        },
    )
    s.require(
        attempt["schema_version"] == "s2-resource-normal-attempt-v1"
        and attempt["specification_sha256"] == binding["specification_sha256"]
        and all(attempt[k] is False for k in (*a.FLAGS, "live_containment_qualified"))
        and type(attempt["sample_count"]) is int
        and 0 <= attempt["sample_count"] <= a.MAX_SAMPLES
        and attempt["failure_code"] in {None, "adapter_failure_preserved"},
        "Attempt drift.",
    )
    if attempt["source"] is not None:
        q._keys(attempt["source"], {"source_sha256", "worker_sha256", "tracked_count"})
        for key in ("source_sha256", "worker_sha256"):
            q._hash(attempt["source"][key])
        s.require(
            type(attempt["source"]["tracked_count"]) is int
            and 1 <= attempt["source"]["tracked_count"] <= 1024,
            "Source count.",
        )
    if attempt["runtime"] is not None:
        s.require(attempt["runtime"] == binding["runtime"], "Runtime drift.")
    s.require(
        attempt["source"] is not None and attempt["runtime"] is not None,
        "Claimed normal attempt requires preflight source/runtime.",
    )
    s.require(
        type(value["barriers"]) is list
        and len(value["barriers"]) <= 2
        and type(value["resources"]) is list
        and len(value["resources"]) <= attempt["sample_count"],
        "Resource count bound.",
    )
    state = "blocked_unbound"
    if value["contract"] is None:
        s.require(
            not value["barriers"] and not value["resources"] and not value["events"],
            "Unbound data drift.",
        )
    else:
        contract = p.validate_contract(value["contract"])
        legacy = contract["legacy_contract"]
        expected = q.contract(
            spec["inventory"],
            legacy["binding"],
            "normal",
            legacy["source_sha256"],
            legacy["worker_sha256"],
        )
        s.require(
            legacy == expected
            and all(legacy["binding"][k] == spec[k] for k in ("job_id", "nonce", "source_commit")),
            "Contract/spec drift.",
        )
        s.require(
            attempt["source"] is not None
            and legacy["source_sha256"] == attempt["source"]["source_sha256"]
            and legacy["worker_sha256"] == attempt["source"]["worker_sha256"],
            "Source binding.",
        )
        for barrier in value["barriers"]:
            Controller(contract, 0).release(0, barrier, barrier)
        if value["events"]:
            controller = replay_events(contract, value["events"])
            s.require(
                len(value["barriers"]) == 2
                and value["events"][0]["payload"]
                == dict(zip(("first", "second"), value["barriers"], strict=True)),
                "Barrier/event drift.",
            )
            state = controller.state
            gate = p.ResourceGate(contract)
            gate.bind(*(v["resource"] for v in value["barriers"]))
            indices = []
            for sample in value["resources"]:
                q._keys(sample, {"index", "members", "resource", "cpu_chain_sha256", *p.FLAGS})
                index = sample["index"]
                s.require(
                    type(index) is int
                    and 0 <= index < attempt["sample_count"]
                    and type(sample["members"]) is int
                    and 0 <= sample["members"] <= 64
                    and sample["cpu_chain_sha256"] == value["barriers"][0]["cpu_chain_sha256"]
                    and all(sample[k] is False for k in p.FLAGS),
                    "Sample drift.",
                )
                indices.append(index)
                gate.sample(sample["resource"])
            s.require(indices == sorted(set(indices)), "Resource sample order.")
            observations = value["events"][1:]
            s.require(len(observations) == attempt["sample_count"], "Partial event journal.")
            by_index = {v["index"]: v for v in value["resources"]}
            for index, event in enumerate(observations):
                inputs = event["payload"]["inputs"]
                if not inputs["fault"]:
                    s.require(
                        index in by_index and by_index[index]["members"] == inputs["members"],
                        "Missing positive resource sample.",
                    )
        else:
            s.require(
                not value["resources"] and attempt["sample_count"] == 0, "Unreleased samples."
            )
    s.require(attempt["status"] == state, "Attempt/controller status drift.")
    return {
        "schema_version": "s2-resource-normal-review-v1",
        "status": "replayed_not_live_qualified",
        "controller_state": state,
        "evidence_sha256": s.digest(value),
        "worker_cpu_usage_ns": None,
        **p.FLAGS,
    }


def collect(run, destination, spec):
    """Exclusive derived JSON carrier, no scheduler access or writes to the run."""
    spec = a.validate_spec(spec)
    s.require(Path(run) == Path(spec["run"]), "Run identity drift.")
    run, destination = Path(run), Path(destination)
    q._safe_path(run)
    q._safe_path(destination)
    s.require(run != destination and run not in destination.parents, "Output inside preserved run.")
    raw = a._file(run / "resource-evidence.json", LIMIT)
    value = c.decode_json(raw)
    result = review(value, spec)

    def same(name, expected):
        s.require(c.decode_json(a._file(run / name, LIMIT)) == expected, "Durable carrier drift.")

    same("attempt.json", value["attempt"])
    for index, barrier in enumerate(value["barriers"]):
        same(f"resource-barrier-{index}.json", barrier)
    for sample in value["resources"]:
        same(f"resource-sample-{sample['index']:04d}.json", sample)
    for event in value["events"]:
        same(f"event-{event['index']:04d}.json", event)
    if value["events"]:
        same("resource-contract.json", value["contract"])
    # Strict semantic carrier when complete. Missing/interrupted preservation
    # raises, leaving every original byte intact; never fabricate missing records.
    destination.mkdir(mode=0o700, exist_ok=False)
    c.write_once(destination / "evidence.json", value)
    c.write_once(destination / "review.json", result)
    checksum = hashlib.sha256(c.encoded(value)).hexdigest()
    return {"sha256": checksum, "review": result, **p.FLAGS}
