"""Solver-free, read-only resource observations; never an admission/kill authority.

CgroupV2Observer(allocation, child, owned={pid: starttime}, ...).read() observes
a dedicated child below an allocation. The future supervisor supplies the exact
authorized PID/starttime allowlist (including nested members). No cgroup is made,
modified, or killed. Synthetic fixtures require test_only=True; real observations
require Linux and a cgroup2 mount. Reads are bounded and non-atomic. Delegated,
race-free startup and scoped kill still need NPAD miniature qualification.

ResourceSampler(probe, phase, *, identity, ...).sample()/finish() is synchronous:
the parent calls it; there are no threads, sleeps, launches or import-time work.
probe returns {"cgroup": observer.read(), "process_tree": None}; phase is supplied
by the parent. finish() probes again after cleanup and returns the strict receipt
accepted by verify_sampling(receipt, identity). Process-tree RSS/CPU are currently
unimplemented and stay null. Only stable, nondecreasing cgroup lifetime counters
(which retain exited descendants' CPU) produce measured_lifetime_cpu_hours.
containment_closed requires live subtree evidence; synthetic observations expose
synthetic_observation=True and cannot close containment. Allocation closure and
production admission always remain false. Receipts are not capabilities. Scope
paths are SHA256 of UTF-8 absolute paths; replay validates digest syntax/distinction
and stability, while only the local observer checks the descendant relationship.
Subtree nodes export only node_id/parent_id path digests, never directory names.
The root node_id equals scope.child_path_sha256, with parent_id=None and the
known child inode. Replay requires one connected acyclic rooted topology.
Portable errors contain only ERROR_CODES; exception messages never enter receipts.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import sys
import time
from pathlib import Path

SCHEMA = "mvp2_h300_resources.v1"
PHASES = (
    "startup",
    "build",
    "optimization",
    "export_validation",
    "cleanup",
    "cleanup_after_failure",
)
MAX_GAP_MS = 5000
MAX_SAMPLES = 10000
MAX_BYTES = 65536
COUNTERS = (
    "memory_max_bytes",
    "memory_current_bytes",
    "memory_peak_bytes",
    "cpu_usage_usec",
    "oom",
    "oom_kill",
)
ERROR_CODES = frozenset(
    {
        "clock_rollback",
        "phase_rollback_or_missing",
        "missing_cgroup",
        "scope_identity_changed",
        "memory_limit_changed",
        "nested_identity_changed",
        "missing_lifetime_cpu",
        "lifetime_cpu_reset",
        "sampling_gap_exceeded",
        "final_observation_before_cleanup",
        "insufficient_samples",
        "sample_bound_reached",
        "phase_read_failed",
        "probe_read_failed",
        "scope_read_failed",
        "scope_invalid",
        "subtree_bound_exceeded",
        "scope_changed_during_read",
        "pid_reused",
        "unowned_member",
        "unsafe_nested_path",
    }
    | {f"{field}_{reason}" for field in COUNTERS for reason in ("missing", "invalid")}
)
MAX_ERRORS = len(ERROR_CODES)


class _ObservationError(ValueError):
    def __init__(self, code):
        _require(code in ERROR_CODES, "Unknown internal error code.")
        self.code = code
        super().__init__(code)


def _observe_require(ok, code):
    if not ok:
        raise _ObservationError(code)


def _nested_path(value):
    return (
        type(value) is str
        and len(value) <= 512
        and (
            value == "."
            or (
                len(value.split("/")) <= 16
                and all(
                    re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}", part) is not None
                    for part in value.split("/")
                )
            )
        )
    )


def _path_digest(path):
    return hashlib.sha256(str(path).encode("utf-8")).hexdigest()


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def _number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def _integer(value):
    return type(value) is int and value >= 0


def _identity(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _keys(value, keys):
    _require(type(value) is dict and set(value) == set(keys), "Unexpected resource schema fields.")


def _errors(value):
    _require(
        type(value) is list
        and len(value) <= MAX_ERRORS
        and all(type(e) is str and e in ERROR_CODES for e in value),
        "Invalid error codes.",
    )


class _Directory:
    """No-follow descriptor traversal on Linux; synthetic Windows fallback only."""

    def __init__(self, path):
        self.path = Path(os.path.abspath(path))
        self.fd = None
        if os.name == "posix":
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
            fd = os.open(self.path.anchor, flags)
            try:
                for part in self.path.parts[1:]:
                    nxt = os.open(part, flags, dir_fd=fd)
                    os.close(fd)
                    fd = nxt
                self.fd = fd
                info = os.fstat(fd)
            except BaseException:
                os.close(fd)
                raise
        else:
            for item in (self.path, *self.path.parents):
                _require(not item.is_symlink() and not item.is_junction(), "Linked directory.")
            info = self.path.stat()
        _require(stat.S_ISDIR(info.st_mode), "Expected directory.")
        self.identity = [info.st_dev, info.st_ino]

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def read(self, name):
        _require("/" not in name and "\\" not in name and name not in (".", ".."), "Bad filename.")
        if self.fd is None:
            path = self.path / name
            _require(not path.is_symlink(), "Linked resource file.")
            with path.open("rb") as stream:
                data = stream.read(MAX_BYTES + 1)
        else:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.fd)
            with os.fdopen(fd, "rb") as stream:
                _require(
                    stat.S_ISREG(os.fstat(stream.fileno()).st_mode), "Nonregular resource file."
                )
                data = stream.read(MAX_BYTES + 1)
        _require(len(data) <= MAX_BYTES, "Oversized resource file.")
        return data.decode("ascii").strip()

    def children(self):
        names = os.listdir(self.fd if self.fd is not None else self.path)
        _require(len(names) <= 4096, "Directory entry bound exceeded.")
        result = []
        for name in names:
            info = (
                os.stat(name, dir_fd=self.fd, follow_symlinks=False)
                if self.fd is not None
                else (self.path / name).lstat()
            )
            _require(not stat.S_ISLNK(info.st_mode), "Linked subtree entry.")
            if stat.S_ISDIR(info.st_mode):
                result.append(name)
        return sorted(result)


def _uint(text):
    _require(re.fullmatch(r"[0-9]+", text) is not None, "Expected unsigned integer.")
    return int(text)


def _pairs(text):
    values = {}
    for line in text.splitlines():
        parts = line.split()
        _require(len(parts) == 2 and parts[0] not in values, "Malformed/duplicate counter.")
        values[parts[0]] = _uint(parts[1])
    return values


def _starttime(proc_root, pid):
    directory = _Directory(Path(proc_root) / str(pid))
    try:
        text = directory.read("stat")
        end = text.rfind(")")
        _require(text.startswith(f"{pid} (") and end > 0, "Malformed proc stat.")
        return _uint(text[end + 1 :].split()[19])
    finally:
        directory.close()


class CgroupV2Observer:
    """Read bounded nested membership; reject shared, linked, replaced scopes.

    owned is an immutable snapshot of supervisor-authorized PID/starttime pairs.
    Unexpected members or PID reuse invalidate the observation. A future parent
    may construct a new observer with an expanded allowlist, but must preserve the
    original child inode when comparing receipts. No ownership is inferred from a
    root PID exiting. memory.max must be finite, positive and stable.
    """

    def __init__(
        self, allocation, child, *, owned, proc_root="/proc", test_only=False, max_groups=128
    ):
        _require(
            type(test_only) is bool and (test_only or sys.platform == "linux"), "Linux required."
        )
        _require(type(max_groups) is int and 1 <= max_groups <= 1024, "Bad group bound.")
        _require(
            type(owned) is dict
            and 0 < len(owned) <= 4096
            and all(_integer(p) and p > 0 and _integer(s) for p, s in owned.items()),
            "Explicit owned PID/starttime map required.",
        )
        self.allocation = Path(os.path.abspath(allocation))
        self.child = Path(os.path.abspath(child))
        _require(
            self.child != self.allocation and self.allocation in self.child.parents,
            "Child must be strictly below allocation, never root/shared allocation.",
        )
        if not test_only:
            with open("/proc/self/mountinfo", encoding="ascii") as stream:
                mounts = stream.read(1024 * 1024 + 1)
            _require(len(mounts) <= 1024 * 1024, "Mount table bound exceeded.")
            roots = [
                Path(re.sub(r"\\([0-7]{3})", lambda m: chr(int(m[1], 8)), line.split()[4]))
                for line in mounts.splitlines()
                if " - cgroup2 " in line
            ]
            _require(
                any(root == self.allocation or root in self.allocation.parents for root in roots),
                "Not a cgroup v2 mount.",
            )
        self.owned, self.proc_root, self.max_groups = dict(owned), proc_root, max_groups
        self.ids = {}
        allocation_dir, child_dir = _Directory(self.allocation), None
        try:
            child_dir = _Directory(self.child)
            _require(allocation_dir.identity != child_dir.identity, "Shared allocation inode.")
            _require(child_dir.read("cgroup.type") == "domain", "Domain cgroup required.")
            self.limit = _uint(child_dir.read("memory.max"))
            _require(self.limit > 0, "Positive finite memory.max required.")
            self.scope = {
                "allocation_path_sha256": _path_digest(self.allocation),
                "allocation_id": allocation_dir.identity,
                "child_path_sha256": _path_digest(self.child),
                "child_id": child_dir.identity,
                "test_only": test_only,
            }
            self.ids["."] = child_dir.identity
        finally:
            allocation_dir.close()
            if child_dir is not None:
                child_dir.close()
        initial = self.read()
        _require(not initial["errors"], "Invalid dedicated scope.")

    def read(self):
        """Missing counters stay null; all read/ownership failures are explicit."""
        result = {"scope": dict(self.scope), **dict.fromkeys(COUNTERS), "subtree": [], "errors": []}
        opened = []
        try:
            for path, expected in (
                (self.allocation, self.scope["allocation_id"]),
                (self.child, self.scope["child_id"]),
            ):
                directory = _Directory(path)
                opened.append(directory)
                _observe_require(directory.identity == expected, "scope_identity_changed")
            root = opened[-1]
            for field, filename, key in (
                ("memory_max_bytes", "memory.max", None),
                ("memory_current_bytes", "memory.current", None),
                ("memory_peak_bytes", "memory.peak", None),
                ("cpu_usage_usec", "cpu.stat", "usage_usec"),
                ("oom", "memory.events", "oom"),
                ("oom_kill", "memory.events", "oom_kill"),
            ):
                try:
                    value = root.read(filename)
                    result[field] = _uint(value) if key is None else _pairs(value)[key]
                except FileNotFoundError:
                    if field != "memory_peak_bytes":
                        result["errors"].append(f"{field}_missing")
                except (OSError, ValueError, KeyError, UnicodeError):
                    result["errors"].append(f"{field}_invalid")
            _observe_require(result["memory_max_bytes"] == self.limit, "memory_limit_changed")
            pending, seen_pids, snapshots = [(".", root)], set(), []
            while pending:
                relative, directory = pending.pop()
                _observe_require(len(result["subtree"]) < self.max_groups, "subtree_bound_exceeded")
                expected = self.ids.setdefault(relative, directory.identity)
                _observe_require(directory.identity == expected, "nested_identity_changed")
                _require(directory.read("cgroup.type") == "domain", "Non-domain descendant.")
                populated = _pairs(directory.read("cgroup.events"))["populated"]
                _require(populated in (0, 1), "Invalid populated value.")
                pids = [_uint(p) for p in directory.read("cgroup.procs").splitlines()]
                _require(
                    len(pids) <= 4096 and len(pids) == len(set(pids)), "Membership bound/duplicate."
                )
                for pid in pids:
                    _observe_require(pid in self.owned and pid not in seen_pids, "unowned_member")
                    _observe_require(
                        _starttime(self.proc_root, pid) == self.owned[pid], "pid_reused"
                    )
                    seen_pids.add(pid)
                result["subtree"].append(
                    {
                        "node_id": _path_digest(directory.path),
                        "parent_id": None
                        if relative == "."
                        else _path_digest(directory.path.parent),
                        "id": directory.identity,
                        "populated": populated,
                        "pids": pids,
                    }
                )
                names = directory.children()
                snapshots.append((directory, pids, populated, names))
                for name in names:
                    _observe_require(len(opened) - 1 < self.max_groups, "subtree_bound_exceeded")
                    nested_path = name if relative == "." else relative + "/" + name
                    _observe_require(_nested_path(nested_path), "unsafe_nested_path")
                    subpath = self.child / name if relative == "." else self.child / relative / name
                    child = _Directory(subpath)
                    opened.append(child)
                    pending.append((nested_path, child))
            for directory, pids, populated, names in snapshots:
                _observe_require(
                    [_uint(p) for p in directory.read("cgroup.procs").splitlines()] == pids
                    and _pairs(directory.read("cgroup.events"))["populated"] == populated
                    and directory.children() == names,
                    "scope_changed_during_read",
                )
                for pid in pids:
                    _observe_require(
                        _starttime(self.proc_root, pid) == self.owned[pid], "pid_reused"
                    )
            # Reopen names: a still-readable unlinked descriptor is not stable identity.
            for directory in opened:
                check = _Directory(directory.path)
                try:
                    _observe_require(
                        check.identity == directory.identity, "scope_changed_during_read"
                    )
                finally:
                    check.close()
        except _ObservationError as exc:
            result["errors"].append(exc.code)
        except (OSError, ValueError, KeyError, IndexError, UnicodeError):
            result["errors"].append("scope_read_failed")
        finally:
            for directory in opened:
                directory.close()
        return result


def _check_cgroup(value):
    if value is None:
        return
    _keys(value, ("scope", *COUNTERS, "subtree", "errors"))
    _errors(value["errors"])
    scope = value["scope"]
    _keys(
        scope,
        ("allocation_path_sha256", "allocation_id", "child_path_sha256", "child_id", "test_only"),
    )
    _require(
        _identity(scope["allocation_path_sha256"])
        and _identity(scope["child_path_sha256"])
        and scope["allocation_path_sha256"] != scope["child_path_sha256"],
        "Invalid scope path digests.",
    )
    _require(type(scope["test_only"]) is bool, "Invalid test_only.")
    for name in ("allocation_id", "child_id"):
        _require(
            type(scope[name]) is list
            and len(scope[name]) == 2
            and all(_integer(v) for v in scope[name]),
            "Invalid inode identity.",
        )
    _require(scope["allocation_id"] != scope["child_id"], "Shared allocation inode.")
    for name in COUNTERS:
        _require(value[name] is None or _integer(value[name]), "Invalid resource counter.")
    _require(
        value["memory_max_bytes"] is None or value["memory_max_bytes"] > 0,
        "Nonfinite/zero memory limit.",
    )
    _require(type(value["subtree"]) is list and len(value["subtree"]) <= 1024, "Invalid subtree.")
    nodes, pids = {}, set()
    root_id = scope["child_path_sha256"]
    for group in value["subtree"]:
        _keys(group, ("node_id", "parent_id", "id", "populated", "pids"))
        node_id, parent_id = group["node_id"], group["parent_id"]
        _require(_identity(node_id) and node_id not in nodes, "Invalid/duplicate node digest.")
        _require(
            (node_id == root_id and parent_id is None)
            or (node_id != root_id and _identity(parent_id) and parent_id != node_id),
            "Invalid parent digest.",
        )
        nodes[node_id] = parent_id
        _require(
            type(group["id"]) is list
            and len(group["id"]) == 2
            and all(_integer(v) for v in group["id"]),
            "Invalid nested inode.",
        )
        _require(
            type(group["populated"]) is int and group["populated"] in (0, 1), "Invalid populated."
        )
        _require(
            type(group["pids"]) is list
            and len(group["pids"]) <= 4096
            and all(_integer(p) and p > 0 and p not in pids for p in group["pids"])
            and len(set(group["pids"])) == len(group["pids"]),
            "Invalid nested members.",
        )
        pids.update(group["pids"])
        if node_id == root_id:
            _require(group["id"] == scope["child_id"], "Root inode mismatch.")
    if nodes:
        _require(root_id in nodes, "Missing subtree root.")
        for node_id in nodes:
            visited = set()
            while node_id != root_id:
                _require(
                    node_id in nodes and node_id not in visited, "Disconnected/cyclic subtree."
                )
                visited.add(node_id)
                node_id = nodes[node_id]
    if not value["errors"]:
        _require(
            root_id in nodes
            and all(
                v is not None
                for k, v in value.items()
                if k in COUNTERS and k != "memory_peak_bytes"
            ),
            "Missing required evidence without error.",
        )


def verify_sampling(value, identity):
    """Strict replay; raise ValueError for malformed schema/identity.

    Return sampling_valid, containment_closed, allocation_tree_closed=False,
    measured_lifetime_cpu_hours, sample_count, max_gap_ms, leading_gap_ms,
    trailing_gap_ms, synthetic_observation, errors and production_admitted=False. Gaps over 5000 ms,
    phase/clock rollback, missing probes, inode drift and CPU reset invalidate
    measurement. Final closure requires a fresh live terminal-phase empty subtree;
    any test_only observation prevents containment qualification.
    """
    _keys(
        value,
        (
            "schema",
            "identity",
            "cadence_ms",
            "max_samples",
            "started_ms",
            "ended_ms",
            "samples",
            "final",
            "errors",
        ),
    )
    _require(
        _identity(identity) and value["identity"] == identity and value["schema"] == SCHEMA,
        "Sampling identity/schema mismatch.",
    )
    _require(
        _number(value["cadence_ms"]) and 0 < value["cadence_ms"] <= MAX_GAP_MS, "Invalid cadence."
    )
    _require(
        type(value["max_samples"]) is int and 2 <= value["max_samples"] <= MAX_SAMPLES,
        "Invalid sample bound.",
    )
    _require(_number(value["started_ms"]) and _number(value["ended_ms"]), "Invalid receipt clock.")
    _require(
        type(value["samples"]) is list and len(value["samples"]) < value["max_samples"],
        "Sample bound exceeded.",
    )
    _errors(value["errors"])
    errors = list(value["errors"])
    records = [*value["samples"], value["final"]]
    previous_time, previous_phase, scope, previous_cpu, first_cpu = (
        value["started_ms"],
        -1,
        None,
        None,
        None,
    )
    nested_ids, limit, synthetic = {}, None, False
    gaps = []
    for record in records:
        _keys(record, ("at_ms", "phase", "cgroup", "process_tree", "errors"))
        _require(
            _number(record["at_ms"])
            and (
                record["phase"] is None
                or (type(record["phase"]) is str and record["phase"] in PHASES)
            ),
            "Invalid sample time/phase.",
        )
        _require(record["process_tree"] is None, "Process tree counters are not implemented.")
        _errors(record["errors"])
        errors.extend(record["errors"])
        gap = record["at_ms"] - previous_time
        gaps.append(gap)
        if gap < 0:
            errors.append("clock_rollback")
        previous_time = record["at_ms"]
        phase = PHASES.index(record["phase"]) if record["phase"] in PHASES else -1
        if phase < previous_phase or phase < 0 or (previous_phase >= 4 and phase != previous_phase):
            errors.append("phase_rollback_or_missing")
        previous_phase = phase
        group = record["cgroup"]
        _check_cgroup(group)
        if group is None:
            errors.append("missing_cgroup")
            continue
        errors.extend(group["errors"])
        synthetic = synthetic or group["scope"]["test_only"]
        if scope is None:
            scope = group["scope"]
        if group["scope"] != scope:
            errors.append("scope_identity_changed")
        if limit is None:
            limit = group["memory_max_bytes"]
        elif group["memory_max_bytes"] != limit:
            errors.append("memory_limit_changed")
        for nested in group["subtree"]:
            binding = (nested["id"], nested["parent_id"])
            expected = nested_ids.setdefault(nested["node_id"], binding)
            if binding != expected:
                errors.append("nested_identity_changed")
        cpu = group["cpu_usage_usec"]
        if cpu is None:
            errors.append("missing_lifetime_cpu")
        else:
            if previous_cpu is not None and cpu < previous_cpu:
                errors.append("lifetime_cpu_reset")
            first_cpu = cpu if first_cpu is None else first_cpu
            previous_cpu = cpu
    trailing = value["ended_ms"] - previous_time
    gaps.append(trailing)
    if trailing < 0:
        errors.append("clock_rollback")
    if any(gap > MAX_GAP_MS for gap in gaps):
        errors.append("sampling_gap_exceeded")
    if value["final"]["phase"] not in ("cleanup", "cleanup_after_failure"):
        errors.append("final_observation_before_cleanup")
    if len(records) < 2:
        errors.append("insufficient_samples")
    errors = list(dict.fromkeys(errors))
    valid = not errors
    final = value["final"]["cgroup"]
    closed = bool(
        valid
        and not synthetic
        and final
        and final["subtree"]
        and all(g["populated"] == 0 and not g["pids"] for g in final["subtree"])
    )
    return {
        "sampling_valid": valid,
        "containment_closed": closed,
        "synthetic_observation": synthetic,
        "allocation_tree_closed": False,
        "production_admitted": False,
        "measured_lifetime_cpu_hours": (previous_cpu - first_cpu) / 3_600_000_000
        if valid
        else None,
        "sample_count": len(records),
        "max_gap_ms": max(gaps),
        "leading_gap_ms": gaps[0],
        "trailing_gap_ms": trailing,
        "errors": errors,
    }


class ResourceSampler:
    """Bounded parent-driven recorder. Clock returns monotonic seconds.

    sample() returns a record or None when cadence/count suppresses a probe.
    One slot is reserved for finish(), which always makes the final probe.
    Callback failures become null observations plus explicit errors. Exhausting
    the sample bound is explicit; ordinary cadence suppression is harmless.
    """

    def __init__(
        self, probe, phase, *, identity, cadence_ms=1000, max_samples=1000, clock=time.monotonic
    ):
        _require(
            callable(probe) and callable(phase) and callable(clock) and _identity(identity),
            "Bad sampler callbacks/identity.",
        )
        _require(
            _number(cadence_ms)
            and 0 < cadence_ms <= MAX_GAP_MS
            and type(max_samples) is int
            and 2 <= max_samples <= MAX_SAMPLES,
            "Bad sampling bounds.",
        )
        self.probe, self.phase, self.clock = probe, phase, clock
        self.identity, self.cadence_ms, self.max_samples = identity, cadence_ms, max_samples
        self.started_ms = self._now()
        self.last_seen = self.started_ms
        self.samples, self.errors = [], []
        self.finished = False

    def _now(self):
        now = self.clock()
        _require(_number(now), "Invalid monotonic clock.")
        return now * 1000

    def _record(self, now):
        record = {"at_ms": now, "phase": None, "cgroup": None, "process_tree": None, "errors": []}
        try:
            phase = self.phase()
            _require(type(phase) is str and phase in PHASES, "Unknown parent-observed phase.")
            record["phase"] = phase
        except Exception:
            record["errors"].append("phase_read_failed")
        try:
            observation = self.probe()
            _keys(observation, ("cgroup", "process_tree"))
            _require(observation["process_tree"] is None, "Process-tree counters unsupported.")
            _check_cgroup(observation["cgroup"])
            # Copy via standard JSON also rejects NaN and non-JSON callback values.
            record["cgroup"] = json.loads(json.dumps(observation["cgroup"], allow_nan=False))
        except Exception:
            record["errors"].append("probe_read_failed")
        return record

    def sample(self):
        _require(not self.finished, "Sampler already finished.")
        now = self._now()
        if now < self.last_seen:
            if "clock_rollback" not in self.errors:
                self.errors.append("clock_rollback")
        self.last_seen = now
        if len(self.samples) >= self.max_samples - 1:
            if "sample_bound_reached" not in self.errors:
                self.errors.append("sample_bound_reached")
            return None
        if self.samples and now - self.samples[-1]["at_ms"] < self.cadence_ms:
            return None
        record = self._record(now)
        self.samples.append(record)
        return record

    def finish(self):
        _require(not self.finished, "Sampler already finished.")
        now = self._now()
        if now < self.last_seen and "clock_rollback" not in self.errors:
            self.errors.append("clock_rollback")
        final = self._record(now)
        ended = self._now()
        self.finished = True
        return {
            "schema": SCHEMA,
            "identity": self.identity,
            "cadence_ms": self.cadence_ms,
            "max_samples": self.max_samples,
            "started_ms": self.started_ms,
            "ended_ms": ended,
            "samples": self.samples,
            "final": final,
            "errors": self.errors,
        }


def production_entry(*_args, **_kwargs):
    """Unconditional denial until delegated containment/supervision is qualified."""
    raise PermissionError(
        "Production admission disabled: NPAD delegated setup/scoped kill remain unqualified."
    )
