"""Closed synthetic Slurm-step components; no job submission or execution CLI.

Transport callbacks are injected, never discovered from PATH. Public execution
denies before I/O. Receipts qualify software/replay, not installed Slurm or live
containment. No native imports, arbitrary commands, retries or allocation kills.
"""

from __future__ import annotations

import copy
import gzip
import hashlib
import io
import math
import os
import re
import stat
import sys
import tarfile
from pathlib import Path

from scripts import mvp2_h300_controls as c
from scripts import mvp2_h300_resources as r
from scripts import mvp2_s2_slurm_step as s

FLAGS = {**s.FLAGS, "synthetic_execution_admitted": False}
CASES = (
    "normal",
    "nested_setsid_term_ignore",
    "build_failure",
    "optimization_failure",
    "export_failure",
    "disposal_failure",
)
PROFILE = {
    "allocation_cpus": 2,
    "allocation_memory_mib": 2048,
    "worker_cpus": 1,
    "worker_memory_mib": 256,
    "startup_seconds": 30,
    "exercise_seconds": 60,
    "term_grace_seconds": 5,
    "cleanup_seconds": 390,
    "quiet_seconds": 5,
    "allocation_wall_seconds": 720,
    "maximum_events": 1024,
    "maximum_members": 64,
}
LIMIT = 2 * 1024**2
FILES = ("contract.json", "events.json", "worker.json", "review.json")
WORKER_FILES = tuple(f"phase-{i}.json" for i in range(4)) + ("failure.json", "terminal.json")


def execute_synthetic(*_args, **_kwargs):
    """Closed admission boundary: no inputs, files, process or scheduler inspected."""
    raise PermissionError("Live synthetic execution is not admitted by this software gate.")


def _keys(item, fields):
    s.require(type(item) is dict and set(item) == set(fields), "Schema drift.")


def _number(value):
    s.require(type(value) in (int, float) and math.isfinite(value) and value >= 0, "Bad clock.")
    return value


def _hash(value, size=64):
    s.require(type(value) is str and re.fullmatch(rf"[0-9a-f]{{{size}}}", value), "Bad digest.")
    return value


def contract(inventory, binding, case, source_sha256, worker_sha256):
    """One attempt/case/step; supplied bytes are declarations until runtime checks."""
    site, binding = s.review_inventory(inventory), s.binding(binding)
    s.require(case in CASES and type(case) is str, "Unknown synthetic case.")
    return {
        "schema_version": "s2-slurm-synthetic-contract-v1",
        "binding": binding,
        "site_sha256": site["inventory_sha256"],
        "case": case,
        "source_sha256": _hash(source_sha256),
        "worker_sha256": _hash(worker_sha256),
        "profile": dict(PROFILE),
        **FLAGS,
    }


def validate_contract(item):
    _keys(
        item,
        {
            "schema_version",
            "binding",
            "site_sha256",
            "case",
            "source_sha256",
            "worker_sha256",
            "profile",
            *FLAGS,
        },
    )
    s.require(item["schema_version"] == "s2-slurm-synthetic-contract-v1", "Wrong contract.")
    s.binding(item["binding"])
    for key in ("site_sha256", "source_sha256", "worker_sha256"):
        _hash(item[key])
    s.require(type(item["case"]) is str and item["case"] in CASES, "Case drift.")
    s.require(
        type(item["profile"]) is dict
        and c.encoded(item["profile"]) == c.encoded(PROFILE)
        and all(item[key] is False for key in FLAGS),
        "Profile/admission drift.",
    )
    return copy.deepcopy(item)


def launch_descriptor(item, python, worker, run):
    """Inert fixed srun command; explicit existing allocation and fixed worker only."""
    item = validate_contract(item)
    for path in (python, worker, run):
        s._absolute(path)
        s.require(path != "/" and len(path) <= 4096, "Unsafe launch path.")
    s.require(worker.endswith("/scripts/mvp2_s2_synthetic_worker.py"), "Wrong worker.")
    job = item["binding"]["job_id"]
    return {
        "argv": [
            "srun",
            "--jobid=" + job,
            "--nodes=1",
            "--ntasks=1",
            "--cpus-per-task=1",
            "--exact",
            "--mem=256M",
            "--cpu-bind=threads",
            "--immediate=10",
            "--time=00:09:00",
            "--kill-on-bad-exit=1",
            "--export=NONE",
            python,
            "-I",
            worker,
            "--closed-contract",
            run + "/contract.json",
        ],
        "contract_sha256": s.digest(item),
        "execution_admitted": False,
        **FLAGS,
    }


def parse_listpids(text, binding):
    """Strict local listpids grammar; no node-name/path inference or env authority."""
    binding = s.binding(binding)
    s.require(type(text) is str and len(text) <= 65536, "Unbounded scheduler output.")
    lines = text.splitlines()
    s.require(
        lines and lines[0].split() == ["PID", "JOBID", "STEPID", "LOCALID", "GLOBALID"],
        "Unreviewed listpids header.",
    )
    result = set()
    for line in lines[1:]:
        fields = line.split()
        s.require(len(fields) == 5, "Unreviewed listpids row.")
        pid, job, step, local, global_id = fields
        s.require(
            re.fullmatch(r"[1-9][0-9]{0,9}", pid)
            and job == binding["job_id"]
            and step == binding["worker_step_id"]
            and all(re.fullmatch(r"-1|0|[1-9][0-9]{0,9}", x) for x in (local, global_id)),
            "Foreign/ambiguous scheduler member.",
        )
        s.require(int(pid) not in result, "Duplicate scheduler member.")
        result.add(int(pid))
        s.require(len(result) <= PROFILE["maximum_members"], "Scheduler member bound.")
    return result


def proc_identity(stat_text, uid, pid):
    """Parse /proc stat after the last ')'; state Z is not reaped."""
    s.require(type(stat_text) is str and len(stat_text) <= 65536, "Bad proc stat.")
    s.require(type(uid) is int and uid >= 0 and type(pid) is int and pid > 0, "Bad proc identity.")
    split = stat_text.rfind(") ")
    s.require(split > 0 and stat_text[:split].startswith(str(pid) + " ("), "Proc PID drift.")
    fields = stat_text[split + 2 :].split()
    s.require(len(fields) >= 20 and fields[0] in "RSDZTWtXxKPI", "Bad proc fields.")
    s.require(re.fullmatch(r"[1-9][0-9]*", fields[19]), "Bad process starttime.")
    return {"pid": pid, "uid": uid, "starttime": int(fields[19]), "state": fields[0]}


def _identity(item):
    _keys(item, {"pid", "uid", "starttime", "state"})
    s.require(all(type(item[k]) is int for k in ("pid", "uid", "starttime")), "Identity types.")
    s.require(item["pid"] > 0 and item["uid"] >= 0 and item["starttime"] > 0, "Bad identity.")
    s.require(type(item["state"]) is str and item["state"] in tuple("RSDZTWtXxKPI"), "Bad state.")
    return item


def _stable_identity(item):
    return {key: item[key] for key in ("pid", "uid", "starttime")}


def read_process_record(pid):
    """Read-only Linux identity/membership twice; disappearance is not reaping proof."""
    s.require(sys.platform == "linux" and type(pid) is int and pid > 0, "Linux PID required.")
    directory = r._Directory(Path("/proc") / str(pid))
    try:

        def read_uid():
            lines = [
                line.split()[1:]
                for line in directory.read("status").splitlines()
                if line.startswith("Uid:")
            ]
            s.require(
                len(lines) == 1
                and len(lines[0]) == 4
                and all(re.fullmatch(r"[0-9]+", x) for x in lines[0]),
                "Ambiguous UID.",
            )
            s.require(len(set(lines[0])) == 1, "Credential transition not qualified.")
            return int(lines[0][0])

        uid = read_uid()
        first = proc_identity(directory.read("stat"), uid, pid)
        member, mounts = directory.read("cgroup"), directory.read("mountinfo")
        scopes = s.mapped_scopes(member, mounts)
        second = proc_identity(directory.read("stat"), uid, pid)
        s.require(
            first["starttime"] == second["starttime"]
            and member == directory.read("cgroup")
            and mounts == directory.read("mountinfo")
            and uid == read_uid(),
            "Process identity/membership drift.",
        )
        return {"identity": second, "scopes": scopes}
    finally:
        directory.close()


def barrier(
    item,
    scheduler_pids,
    worker,
    supervisor,
    writer,
    worker_scopes,
    outside_scopes,
    snapshot,
    member_records,
):
    """Validate observations before release; this receipt is NOT a capability.

    Caller must collect live records independently twice around the barrier.
    Offline callers can forge observations; flags deliberately cannot promote.
    """
    item = validate_contract(item)
    worker, supervisor, writer = map(_identity, (worker, supervisor, writer))
    s.require(type(scheduler_pids) is set and 1 <= len(scheduler_pids) <= 64, "Member bound.")
    s.require(all(type(x) is int and x > 0 for x in scheduler_pids), "Bad scheduler PID.")
    s.require(
        worker["pid"] in scheduler_pids
        and supervisor["pid"] not in scheduler_pids
        and writer["pid"] not in scheduler_pids
        and worker["pid"] != supervisor["pid"]
        and worker["uid"] == supervisor["uid"] == writer["uid"]
        and all(p["state"] not in "ZXx" for p in (worker, supervisor, writer)),
        "Worker/outside identity mismatch.",
    )
    # The parent itself is the durable writer, not a worker-owned descendant.
    s.require(writer == supervisor, "Writer must be the outside supervisor.")
    s.separated_scopes(worker_scopes, outside_scopes)
    s.require(
        type(member_records) is list and len(member_records) == len(scheduler_pids),
        "Missing independently observed member identities.",
    )
    seen = set()
    for record in member_records:
        _keys(record, {"identity", "scopes"})
        identity = _identity(record["identity"])
        pid = identity["pid"]
        s.require(
            pid in scheduler_pids
            and pid not in seen
            and identity["uid"] == worker["uid"]
            and identity["state"] not in "ZXx",
            "Foreign/reused member.",
        )
        seen.add(pid)
        s.require(
            type(record["scopes"]) is dict and set(record["scopes"]) == set(s.CONTROLLERS),
            "Member controllers missing.",
        )
        for key in s.CONTROLLERS:
            entry = record["scopes"][key]
            s._validate_scope(entry)
            base, observed = s._absolute(worker_scopes[key]["scope"]), s._absolute(entry["scope"])
            s.require(
                entry["mount"] == worker_scopes[key]["mount"]
                and (observed == base or base in observed.parents),
                "Member escaped scope.",
            )
        if pid == worker["pid"]:
            s.require(
                _stable_identity(identity) == _stable_identity(worker)
                and record["scopes"] == worker_scopes,
                "Leader drift.",
            )
    _keys(
        snapshot,
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
        snapshot["schema_version"] == "s2-cgroup-v1-observation-v1"
        and type(snapshot["synthetic_observation"]) is bool
        and snapshot["status"] == "observed_not_qualified"
        and snapshot["errors"] == []
        and all(snapshot[k] is False for k in s.FLAGS),
        "Invalid barrier observation.",
    )
    s.require(
        type(snapshot["scopes"]) is dict and set(snapshot["scopes"]) == set(s.CONTROLLERS),
        "Missing scope identities.",
    )
    for key in s.CONTROLLERS:
        observed = snapshot["scopes"][key]
        _keys(observed, {"path_sha256", "inode"})
        s.require(
            observed["path_sha256"] == s.digest(worker_scopes[key]["scope"]),
            "Snapshot scope mismatch.",
        )
        s.require(
            type(observed["inode"]) is list
            and len(observed["inode"]) == 2
            and all(type(v) is int and v >= 0 for v in observed["inode"]),
            "Bad inode.",
        )
    counters = snapshot["counters"]
    expected = {
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
    _keys(counters, expected)
    s.require(
        all(type(v) is int and 0 <= v <= s.MAX_COUNTER for v in counters.values()),
        "Bad resource counters.",
    )
    s.require(
        0 < counters["effective_reported_memory_limit_bytes"] <= 256 * 1024**2
        and counters["effective_reported_memory_limit_bytes"] <= counters["memory_limit_bytes"]
        and 0 < counters["cpuset_cpu_count"] <= 1
        and 1 <= counters["freezer_group_count"] <= 128
        and counters["freezer_unique_process_count"] == len(scheduler_pids),
        "Finite requested worker limits/membership not observed.",
    )
    return {
        "contract_sha256": s.digest(item),
        "identities_sha256": s.digest(
            [
                _stable_identity(worker),
                _stable_identity(supervisor),
                _stable_identity(writer),
                [
                    {"identity": _stable_identity(record["identity"]), "scopes": record["scopes"]}
                    for record in sorted(member_records, key=lambda x: x["identity"]["pid"])
                ],
            ]
        ),
        "scope_identity_sha256": s.digest(snapshot["scopes"]),
        "observation_sha256": s.digest(snapshot),
        "synthetic_observation": snapshot["synthetic_observation"],
        "barrier_checked_not_attested": True,
        **FLAGS,
    }


class Launcher:
    """Fixed commands through supplied transports; not connected to a live CLI.

    Claim and intent precede effects. Exception/unknown acknowledgement consumes
    the attempt, never retries. Handles belong to the supplied transport. A future
    admission adapter must validate source bytes, allocation and real ownership.
    """

    def __init__(self, item, directory, *, spawn, command):
        self.item = validate_contract(item)
        self.directory = Path(directory)
        _safe_path(self.directory)
        self.directory.mkdir(exist_ok=False)
        c.write_once(self.directory / "claim.json", {"contract_sha256": s.digest(self.item)})
        self.spawn, self.command = spawn, command
        self.used = False
        self.signals = set()
        self.bound = False

    def launch(self, python, worker, run):
        s.require(not self.used, "Launch is one-shot.")
        proposal = launch_descriptor(self.item, python, worker, run)
        self.used = True
        c.write_once(self.directory / "launch-intent.json", proposal)
        return self.spawn(tuple(proposal["argv"]))

    def listpids(self):
        s.require(self.used, "No launched attempt.")
        target = self.item["binding"]["job_id"] + "." + self.item["binding"]["worker_step_id"]
        # Deliberately no host argument; this path is single-node/local only.
        return parse_listpids(
            self.command(
                ("scontrol", "listpids", target), timeout_seconds=10, max_output_bytes=65536
            ),
            self.item["binding"],
        )

    def bind_barrier(self, receipt):
        Controller(self.item, 0).release(0, receipt, receipt)
        s.require(
            self.used
            and not self.bound
            and receipt["contract_sha256"] == s.digest(self.item)
            and receipt["barrier_checked_not_attested"] is True
            and all(receipt[k] is False for k in FLAGS),
            "Unbound signal target.",
        )
        self.bound = True
        self.bound_receipt = copy.deepcopy(receipt)

    def signal(self, name, events):
        s.require(
            self.used and self.bound and name in {"TERM", "KILL"} and name not in self.signals,
            "Invalid/repeated signal.",
        )
        s.require(name != "KILL" or "TERM" in self.signals, "KILL before TERM.")
        verify_events(self.item, events)
        releases = [event for event in events if event["kind"] == "release"]
        s.require(
            len(releases) == 1
            and all(
                releases[0]["payload"]["first"][key] == self.bound_receipt[key]
                for key in ("identities_sha256", "scope_identity_sha256", "synthetic_observation")
            ),
            "Signal/controller barrier drift.",
        )
        s.require(
            events
            and events[-1]["kind"] == "observation"
            and events[-1]["payload"]["action"] == name + "_exact_step",
            "Controller has not requested this signal.",
        )
        proposal = s.signal_descriptor(self.item["binding"], name)
        self.signals.add(name)
        c.write_once(self.directory / (name.lower() + "-intent.json"), proposal)
        return self.command(tuple(proposal["argv"]), timeout_seconds=10, max_output_bytes=65536)


class Controller:
    """Deterministic parent-clock automaton; actions are returned, not executed.

    The adapter must journal each action before its effect and bind observations
    to live records. Missing/replaced scopes never become a cleanup success.
    This software gate only returns candidate outcomes, always non-admitting.
    """

    def __init__(self, item, started):
        self.item = validate_contract(item)
        self.started = self.last = _number(started)
        self.state, self.released = "startup", False
        self.term_at = self.kill_at = self.quiet_at = None
        self.scope_hash = None
        self.events = []
        self.previous = s.digest(self.item)

    def _event(self, now, kind, payload):
        s.require(len(self.events) < PROFILE["maximum_events"], "Event bound reached.")
        record = {
            "index": len(self.events),
            "seconds": now - self.started,
            "kind": kind,
            "payload": copy.deepcopy(payload),
            "previous_sha256": self.previous,
        }
        self.previous = s.digest(record)
        self.events.append(record)

    def release(self, now, first, second):
        s.require(len(self.events) < PROFILE["maximum_events"], "Event bound reached.")
        now = self._clock(now)
        s.require(self.state == "startup" and now - self.started < 30, "Late/repeated barrier.")
        for receipt in (first, second):
            _keys(
                receipt,
                {
                    "contract_sha256",
                    "identities_sha256",
                    "scope_identity_sha256",
                    "observation_sha256",
                    "synthetic_observation",
                    "barrier_checked_not_attested",
                    *FLAGS,
                },
            )
            s.require(
                receipt["contract_sha256"] == s.digest(self.item)
                and receipt["barrier_checked_not_attested"] is True
                and type(receipt["synthetic_observation"]) is bool
                and all(receipt[k] is False for k in FLAGS),
                "Unbound/admitting barrier.",
            )
            for k in ("identities_sha256", "scope_identity_sha256", "observation_sha256"):
                _hash(receipt[k])
        s.require(
            all(
                first[k] == second[k]
                for k in ("identities_sha256", "scope_identity_sha256", "synthetic_observation")
            ),
            "Barrier identity drift.",
        )
        self.scope_hash = first["scope_identity_sha256"]
        self.released, self.state, self.released_at = True, "exercise", now
        self._event(now, "release", {"first": first, "second": second})
        return "release_barrier"

    def _clock(self, now):
        now = _number(now)
        s.require(now >= self.last, "Clock rollback.")
        self.last = now
        return now

    def observe(
        self,
        now,
        *,
        worker_done=False,
        fault=False,
        scope_hash=None,
        members=None,
        all_known_pids_absent=False,
        launcher_reaped=False,
        step_terminal=False,
        writes_sha256=None,
    ):
        s.require(len(self.events) < PROFILE["maximum_events"], "Event bound reached.")
        inputs = {
            "worker_done": worker_done,
            "fault": fault,
            "scope_hash": scope_hash,
            "members": members,
            "all_known_pids_absent": all_known_pids_absent,
            "launcher_reaped": launcher_reaped,
            "step_terminal": step_terminal,
            "writes_sha256": writes_sha256,
        }
        action = self._observe(now, **inputs)
        self._event(now, "observation", {"inputs": inputs, "action": action, "state": self.state})
        return action

    def _observe(
        self,
        now,
        *,
        worker_done=False,
        fault=False,
        scope_hash=None,
        members=None,
        all_known_pids_absent=False,
        launcher_reaped=False,
        step_terminal=False,
        writes_sha256=None,
    ):
        now = self._clock(now)
        s.require(self.state not in {"candidate_closed", "blocked"}, "Terminal controller.")
        s.require(
            all(
                type(x) is bool
                for x in (worker_done, fault, all_known_pids_absent, launcher_reaped, step_terminal)
            ),
            "Boolean drift.",
        )
        age = now - self.started
        if self.state == "startup":
            if age >= 30 or fault:
                self.state = "blocked"
                return "preserve_unbound_attempt"
            return "wait"
        if age >= 660:
            self.state = "blocked"
            return "preserve_blocked_attempt"
        observation_ok = (
            scope_hash == self.scope_hash
            and type(members) is int
            and 0 <= members <= 64
            and type(writes_sha256) is str
            and re.fullmatch(r"[0-9a-f]{64}", writes_sha256) is not None
        )
        if self.term_at is None and (
            fault or not observation_ok or worker_done or now - self.released_at >= 60
        ):
            self.term_at, self.state = now, "term"
            return "TERM_exact_step"
        if self.term_at is not None:
            # Cleanup deadline always precedes late positive observations.
            if now - self.term_at >= 390 or age >= 660:
                self.state = "blocked"
                return "preserve_blocked_attempt"
            clean = (
                observation_ok
                and members == 0
                and all_known_pids_absent
                and launcher_reaped
                and step_terminal
            )
            if clean:
                if self.quiet_at is None or writes_sha256 != self.quiet_hash:
                    self.quiet_at, self.quiet_hash, self.quiet_count = now, writes_sha256, 1
                else:
                    self.quiet_count += 1
                if now - self.quiet_at >= 5 and self.quiet_count >= 3:
                    self.state = "candidate_closed"
                    return "preserve_candidate_not_admission"
            else:
                self.quiet_at = None
            if self.kill_at is None and now - self.term_at >= 5 and not clean:
                self.kill_at, self.state = now, "kill"
                return "KILL_exact_step"
        return "wait"

    def receipt(self):
        return {
            "schema_version": "s2-slurm-synthetic-controller-v1",
            "contract_sha256": s.digest(self.item),
            "state": self.state,
            "events": copy.deepcopy(self.events),
            **FLAGS,
        }


def verify_events(item, events):
    item = validate_contract(item)
    s.require(type(events) is list and len(events) <= PROFILE["maximum_events"], "Event bound.")
    previous, last = s.digest(item), 0
    replay = Controller(item, 0)
    for index, event in enumerate(events):
        _keys(event, {"index", "seconds", "kind", "payload", "previous_sha256"})
        s.require(
            type(event["index"]) is int
            and event["index"] == index
            and event["previous_sha256"] == previous,
            "Event binding/order drift.",
        )
        seconds = _number(event["seconds"])
        s.require(last <= seconds, "Event clock drift.")
        kind, payload = event["kind"], event["payload"]
        s.require(type(kind) is str and type(payload) is dict, "Event types.")
        if kind == "release":
            _keys(payload, {"first", "second"})
            replay.release(seconds, payload["first"], payload["second"])
        elif kind == "observation":
            _keys(payload, {"inputs", "action", "state"})
            _keys(
                payload["inputs"],
                {
                    "worker_done",
                    "fault",
                    "scope_hash",
                    "members",
                    "all_known_pids_absent",
                    "launcher_reaped",
                    "step_terminal",
                    "writes_sha256",
                },
            )
            action = replay.observe(seconds, **payload["inputs"])
            s.require(
                action == payload["action"] and replay.state == payload["state"],
                "Nonrecomputable action/state.",
            )
        else:
            raise ValueError("Unknown event kind.")
        s.require(c.encoded(replay.events[-1]) == c.encoded(event), "Event replay drift.")
        previous, last = s.digest(event), seconds
    return {
        "schema_version": "s2-slurm-synthetic-review-v1",
        "contract_sha256": s.digest(item),
        "event_count": len(events),
        "event_chain_sha256": previous,
        "status": replay.state,
        "portable_integrity_only": True,
        "live_containment_qualified": False,
        **FLAGS,
    }


def verify_worker_products(item, products):
    """Partial ordered phases stay partial; a worker terminal never proves cleanup."""
    item = validate_contract(item)
    s.require(type(products) is dict and set(products) <= set(WORKER_FILES), "Worker allowlist.")
    nonce, count = item["binding"]["nonce"], 0
    for index, phase in enumerate(("build", "optimization", "export", "disposal")):
        name = f"phase-{index}.json"
        if name not in products:
            s.require(
                not any(f"phase-{j}.json" in products for j in range(index + 1, 4)),
                "Phase journal hole.",
            )
            break
        s.require(products[name] == {"nonce": nonce, "phase": phase}, "Phase binding drift.")
        count += 1
    s.require(not {"failure.json", "terminal.json"} <= set(products), "Conflicting terminals.")
    outcome = "partial"
    if "failure.json" in products:
        phase_case = {
            "build_failure": 1,
            "optimization_failure": 2,
            "export_failure": 3,
            "disposal_failure": 4,
        }
        s.require(
            count == phase_case.get(item["case"])
            and products["failure.json"] == {"nonce": nonce, "status": "synthetic_phase_failure"},
            "Failure phase/case drift.",
        )
        outcome = "synthetic_failure"
    if "terminal.json" in products:
        s.require(
            count == 4
            and item["case"] in {"normal", "nested_setsid_term_ignore"}
            and products["terminal.json"] == {"nonce": nonce, "status": "synthetic_complete"},
            "Incomplete/unexpected worker terminal.",
        )
        outcome = "synthetic_complete_not_cleanup"
    return {"phase_count": count, "worker_outcome": outcome, **FLAGS}


def read_worker_products(directory):
    root = Path(directory)
    _safe_path(root)
    result = {}
    for name in WORKER_FILES:
        path = root / name
        _safe_path(path)
        if not path.exists():
            continue
        with path.open("rb") as stream:
            s.require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), "Nonregular product.")
            payload = stream.read(4097)
        s.require(len(payload) <= 4096, "Product size bound.")
        result[name] = c.decode_json(payload)
    return result


def collect(directory, item, events, worker_products=None):
    """Exclusive, bounded parent publication. Does not signal, launch or retry."""
    item = validate_contract(item)
    review = verify_events(item, events)
    worker_products = {} if worker_products is None else worker_products
    review["worker"] = verify_worker_products(item, worker_products)
    payloads = {
        "contract.json": c.encoded(item),
        "events.json": c.encoded(events),
        "worker.json": c.encoded(worker_products),
        "review.json": c.encoded(review),
    }
    s.require(sum(map(len, payloads.values())) <= LIMIT, "Evidence size bound.")
    root = Path(directory)
    _safe_path(root)
    root.mkdir(exist_ok=False)
    for name, payload in payloads.items():
        with (root / name).open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    target = root / "synthetic-evidence.tar.gz"
    with target.open("xb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode="w") as archive:
            for name in FILES:
                info = tarfile.TarInfo(name)
                info.size, info.mode = len(payloads[name]), 0o600
                archive.addfile(info, io.BytesIO(payloads[name]))
    checksum = hashlib.sha256(target.read_bytes()).hexdigest()
    with (root / "synthetic-evidence.tar.gz.sha256").open("x", encoding="ascii") as stream:
        stream.write(checksum + "  synthetic-evidence.tar.gz\n")
    return {"sha256": checksum, "review": review, **FLAGS}


def audit_archive(path, expected_sha256, expected_contract):
    """Replay against an independently supplied contract, never archive self-trust."""
    expected_contract = validate_contract(expected_contract)
    _hash(expected_sha256)
    path = Path(path)
    _safe_path(path)
    with path.open("rb") as stream:
        s.require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), "Nonregular archive.")
        raw = stream.read(LIMIT + 1)
    s.require(len(raw) <= LIMIT, "Archive size bound.")
    s.require(hashlib.sha256(raw).hexdigest() == expected_sha256, "Archive checksum drift.")
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
        unpacked = stream.read(LIMIT + 1)
    s.require(len(unpacked) <= LIMIT, "Decompression bound.")
    records = {}
    end = 0
    with tarfile.open(fileobj=io.BytesIO(unpacked), mode="r:") as archive:
        for member in archive:
            s.require(
                member.name in FILES
                and member.name not in records
                and member.isfile()
                and not member.pax_headers
                and 0 < member.size <= LIMIT,
                "Archive member drift.",
            )
            records[member.name] = c.decode_json(archive.extractfile(member).read())
            end = member.offset_data + ((member.size + 511) // 512) * 512
    s.require(not any(unpacked[end:]), "Unexpected trailing archive data.")
    s.require(set(records) == set(FILES), "Missing evidence file.")
    s.require(
        c.encoded(records["contract.json"]) == c.encoded(expected_contract),
        "External contract mismatch.",
    )
    review = verify_events(expected_contract, records["events.json"])
    review["worker"] = verify_worker_products(expected_contract, records["worker.json"])
    s.require(c.encoded(review) == c.encoded(records["review.json"]), "Review not recomputable.")
    return review


def _safe_path(path):
    s.require(path.is_absolute() and ".." not in path.parts, "Absolute canonical path required.")
    for parent in (path, *path.parents):
        s.require(not parent.is_symlink() and not parent.is_junction(), "Linked evidence path.")


if __name__ == "__main__":
    execute_synthetic()
