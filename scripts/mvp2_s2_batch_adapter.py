"""Real POSIX transports and batch integration, with public execution CLOSED.

No sbatch, solver, license or arbitrary command interface. Internal components
are not capabilities: callers can forge Python objects. Admission stays a
separate reviewed gate. Live Slurm/proc/filesystem behaviour is not qualified by
offline tests. Blocking kernel/process creation cannot be given a hard deadline.
"""

from __future__ import annotations

if __name__ == "__main__":
    raise PermissionError("S2 batch execution remains closed; no execution admitted.")

import copy
import gzip
import hashlib
import io
import os
import re
import selectors
import socket
import stat
import struct
import subprocess
import sys
import tarfile
import time
from pathlib import Path

from scripts import mvp2_h300_controls as c
from scripts import mvp2_s2_slurm_step as s
from scripts import mvp2_s2_slurm_synthetic as q

TOOLS = ("git", "srun", "scontrol", "scancel", "sacct")
FLAGS = {**q.FLAGS, "batch_execution_admitted": False}
MAX_RPC = 512
MAX_SAMPLES = 256
TERMINAL = {
    "COMPLETED",
    "FAILED",
    "CANCELLED",
    "TIMEOUT",
    "OUT_OF_MEMORY",
    "NODE_FAIL",
    "PREEMPTED",
}


def execute_batch(*_args, **_kwargs):
    raise PermissionError("Batch/synthetic execution remains closed; no inputs inspected.")


def _file(path, limit):
    path = Path(path)
    q._safe_path(path)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_BINARY", 0)
    )
    with os.fdopen(os.open(path, flags), "rb") as stream:
        s.require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), "Nonregular source/product.")
        data = stream.read(limit + 1)
    s.require(len(data) <= limit, "File bound.")
    return data


def sha_file(path, limit=128 * 1024**2):
    return hashlib.sha256(_file(path, limit)).hexdigest()


def specification(
    *,
    checkout,
    run,
    python,
    tools,
    source_commit,
    nonce,
    job_id,
    case,
    inventory,
    tools_sha256,
    python_sha256,
):
    """Pre-binding plan: deliberately has NO guessed worker step ID."""
    for path in (checkout, run, python, *tools.values()):
        s._absolute(path)
        s.require(path != "/", "Unsafe path.")
    s.require(set(tools) == set(TOOLS) and len(set(tools.values())) == len(TOOLS), "Tool map.")
    q._hash(source_commit, 40)
    q._hash(nonce)
    s.require(type(job_id) is str and re.fullmatch(r"[1-9][0-9]{0,19}", job_id), "Job ID.")
    s.require(case in q.CASES and type(case) is str, "Case.")
    s.review_inventory(inventory)
    s.require(type(tools_sha256) is dict and set(tools_sha256) == set(TOOLS), "Tool digest map.")
    for value in tools_sha256.values():
        q._hash(value)
    q._hash(python_sha256)
    s.require(checkout != run and not run.startswith(checkout + "/"), "Run inside source.")
    return {
        "schema_version": "s2-closed-batch-spec-v1",
        "checkout": checkout,
        "run": run,
        "python": python,
        "tools": dict(tools),
        "source_commit": source_commit,
        "nonce": nonce,
        "job_id": job_id,
        "case": case,
        "inventory": copy.deepcopy(inventory),
        "tools_sha256": dict(tools_sha256),
        "python_sha256": python_sha256,
        **FLAGS,
    }


def validate_spec(item):
    q._keys(
        item,
        {
            "schema_version",
            "checkout",
            "run",
            "python",
            "tools",
            "source_commit",
            "nonce",
            "job_id",
            "case",
            "inventory",
            "tools_sha256",
            "python_sha256",
            *FLAGS,
        },
    )
    rebuilt = specification(**{k: item[k] for k in item if k not in {*FLAGS, "schema_version"}})
    s.require(c.encoded(item) == c.encoded(rebuilt), "Specification/admission drift.")
    return rebuilt


def worker_argv(item):
    """Existing allocation only. Worker CLI is still closed in this revision."""
    item = validate_spec(item)
    return (
        item["tools"]["srun"],
        "--jobid=" + item["job_id"],
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
        item["python"],
        "-I",
        item["checkout"] + "/scripts/mvp2_s2_synthetic_worker.py",
        "--closed-contract",
        item["run"] + "/worker-plan.json",
    )


class PipeHandle:
    """Drain both nonblocking pipes together; bounded retained bytes, finite waits.

    Does not kill an srun client implicitly: that is not remote containment proof.
    Query timeout cleanup only kills the locally owned query Popen, never groups.
    """

    def __init__(
        self, process, *, clock=time.monotonic, selector_factory=selectors.DefaultSelector
    ):
        self.process, self.clock = process, clock
        self.selector = selector_factory()
        self.outputs = {"stdout": bytearray(), "stderr": bytearray()}
        self.total = 0
        for name in self.outputs:
            stream = getattr(process, name)
            os.set_blocking(stream.fileno(), False)
            self.selector.register(stream, selectors.EVENT_READ, name)

    def pump(self, *, deadline, maximum=65536):
        s.require(type(maximum) is int and 0 < maximum <= 8 * 1024**2, "Pipe byte bound.")
        q._number(deadline)
        remaining = deadline - self.clock()
        if remaining <= 0:
            raise TimeoutError("transport_deadline")
        for key, _mask in self.selector.select(min(0.1, remaining)):
            try:
                data = os.read(key.fileobj.fileno(), min(4096, maximum - self.total + 1))
            except BlockingIOError:
                continue
            if not data:
                self.selector.unregister(key.fileobj)
                key.fileobj.close()
                continue
            self.total += len(data)
            s.require(self.total <= maximum, "transport_output_bound")
            self.outputs[key.data].extend(data)
        if self.clock() >= deadline:
            raise TimeoutError("transport_deadline")
        return self.process.poll() is not None and not self.selector.get_map()

    def query_result(self, seconds, maximum):
        s.require(type(seconds) in (int, float) and 0 < seconds <= 10, "RPC deadline bound.")
        deadline = self.clock() + seconds
        try:
            while not self.pump(deadline=deadline, maximum=maximum):
                pass
            s.require(self.process.returncode == 0, "transport_nonzero")
            return bytes(self.outputs["stdout"]).decode("utf-8", errors="strict")
        except (OSError, ValueError, TimeoutError, UnicodeError):
            if self.process.poll() is None:
                self.process.kill()
                try:
                    self.process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    raise TimeoutError("query_cleanup_unknown") from None
            raise
        finally:
            self.close_pipes()

    def close_pipes(self):
        self.selector.close()
        for name in self.outputs:
            getattr(self.process, name).close()


class RealTransport:
    """Exact allowlisted commands, resolved binaries, no shell or inherited secrets."""

    def __init__(self, item):
        self.item = validate_spec(item)
        self.rpcs = 0
        self.source_rpcs = 0
        self.launched = False
        self.bound_step = None
        self.signals = set()

    def bind(self, step):
        binding = s.binding(step)
        s.require(
            binding["job_id"] == self.item["job_id"] and self.bound_step is None,
            "Transport rebind.",
        )
        self.bound_step = binding["worker_step_id"]

    def _query_allowed(self, argv):
        t, job, step = self.item["tools"], self.item["job_id"], self.bound_step
        if argv in {
            (t["srun"], "--version"),
            (t["scontrol"], "--version"),
            (t["sacct"], "--version"),
            (t["scancel"], "--version"),
        }:
            return True
        if argv == (t["scontrol"], "-o", "show", "job", job):
            return True
        if argv == (t["scontrol"], "listpids", job + ".batch"):
            return True
        if len(argv) == 5 and argv[:4] == (t["scontrol"], "-o", "show", "step"):
            # Candidate step query is read-only; it is not signal authority.
            return re.fullmatch(re.escape(job) + r"\.(0|[1-9][0-9]{0,9})", argv[4]) is not None
        if step is not None and argv == (t["scontrol"], "listpids", job + "." + step):
            return True
        if argv == (
            t["sacct"],
            "--noheader",
            "--parsable2",
            "--jobs=" + job,
            "--format=JobIDRaw,State,ExitCode,ElapsedRaw",
        ):
            return True
        prefix = (t["git"], "--no-optional-locks", "-C", self.item["checkout"])
        if argv[:4] == prefix:
            rest = argv[4:]
            if rest in {
                ("rev-parse", "HEAD"),
                ("status", "--porcelain=v1", "-z", "--untracked-files=all"),
                ("ls-files", "--stage", "-z"),
            }:
                return True
            if len(rest) == 3 and rest[:2] == ("cat-file", "blob") and rest[2].startswith("HEAD:"):
                return safe_repo_name(rest[2][5:])
        return False

    def _open(self, argv):
        s.require(sys.platform == "linux", "Linux transport required.")
        # Absolute Slurm executables still need site-specific runtime qualification.
        process = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            close_fds=True,
            start_new_session=True,
            cwd=self.item["checkout"],
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C"},
        )
        return PipeHandle(process)

    def command(self, argv, *, timeout_seconds=10, max_output_bytes=65536):
        argv = tuple(argv)
        s.require(self._query_allowed(argv) and self.rpcs < MAX_RPC, "Command/RPC not allowed.")
        s.require(
            type(timeout_seconds) in (int, float) and 0 < timeout_seconds <= 10, "RPC timeout."
        )
        s.require(
            type(max_output_bytes) is int and 0 < max_output_bytes <= 8 * 1024**2, "RPC bytes."
        )
        self.rpcs += 1  # Unknown acknowledgement consumes this RPC, never retry here.
        return self._open(argv).query_result(timeout_seconds, max_output_bytes)

    def source_command(self, argv, *, timeout_seconds=10, max_output_bytes=65536):
        """Fixed raw-blob exception; bounded separately from live scheduler RPCs."""
        if tuple(argv)[4:6] != ("cat-file", "blob"):
            return self.command(
                argv, timeout_seconds=timeout_seconds, max_output_bytes=max_output_bytes
            )
        s.require(
            self._query_allowed(tuple(argv)) and self.source_rpcs < 1024, "Source command bound."
        )
        s.require(
            type(timeout_seconds) in (int, float)
            and 0 < timeout_seconds <= 10
            and type(max_output_bytes) is int
            and 0 < max_output_bytes <= 8 * 1024**2,
            "Raw query bound.",
        )
        self.source_rpcs += 1
        handle = self._open(tuple(argv))
        deadline = handle.clock() + timeout_seconds
        try:
            while not handle.pump(deadline=deadline, maximum=max_output_bytes):
                pass
            s.require(handle.process.returncode == 0, "Raw blob query failure.")
            return bytes(handle.outputs["stdout"])
        finally:
            try:
                if handle.process.poll() is None:
                    handle.process.kill()
                    try:
                        handle.process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        raise TimeoutError("source_query_cleanup_unknown") from None
            finally:
                handle.close_pipes()

    def spawn(self, argv):
        s.require(
            tuple(argv) == worker_argv(self.item) and not self.launched,
            "Unreviewed/repeated worker.",
        )
        self.launched = True
        return self._open(tuple(argv))

    def signal(self, binding, name):
        binding = s.binding(binding)
        s.require(
            binding["job_id"] == self.item["job_id"]
            and binding["worker_step_id"] == self.bound_step
            and name in {"TERM", "KILL"}
            and name not in self.signals
            and (name == "TERM" or "TERM" in self.signals)
            and self.rpcs < MAX_RPC,
            "Unbound/repeated signal.",
        )
        self.signals.add(name)
        self.rpcs += 1
        argv = (
            self.item["tools"]["scancel"],
            "--signal=" + name,
            binding["job_id"] + "." + binding["worker_step_id"],
        )
        return self._open(argv).query_result(10, 65536)


def safe_repo_name(name):
    return (
        type(name) is str
        and bool(re.fullmatch(r"[A-Za-z0-9_./-]{1,512}", name))
        and not name.startswith(("/", "-"))
        and all(x not in {"", ".", "..", ".git"} for x in name.split("/"))
    )


def verify_checkout(item, command):
    """Compare every regular tracked working file with its raw HEAD blob."""
    item = validate_spec(item)
    prefix = (item["tools"]["git"], "--no-optional-locks", "-C", item["checkout"])

    def git(*args, maximum=65536):
        return command(prefix + args, timeout_seconds=10, max_output_bytes=maximum)

    s.require(git("rev-parse", "HEAD").strip() == item["source_commit"], "Source HEAD drift.")
    s.require(
        git("status", "--porcelain=v1", "-z", "--untracked-files=all") == "",
        "Dirty/untracked source.",
    )
    listing = git("ls-files", "--stage", "-z", maximum=1024**2)
    s.require(listing.endswith("\0"), "Incomplete source index.")
    records, total = {}, 0
    for entry in listing[:-1].split("\0"):
        mode_object, name = entry.split("\t", 1)
        fields = mode_object.split()
        s.require(
            len(fields) == 3
            and fields[0] in {"100644", "100755"}
            and fields[2] == "0"
            and safe_repo_name(name)
            and name not in records,
            "Unreviewed index entry.",
        )
        q._hash(fields[1], 40)
        s.require(len(records) < 1024, "Tracked count bound.")
        # Git blob stream is bytes, not a UTF-8 text conversion (PDF/ZIP allowed).
        raw = command(
            prefix + ("cat-file", "blob", "HEAD:" + name),
            timeout_seconds=10,
            max_output_bytes=8 * 1024**2,
        )
        s.require(type(raw) is bytes, "Raw HEAD blob bytes required.")
        working = _file(Path(item["checkout"]) / name, 8 * 1024**2)
        total += len(raw)
        s.require(total <= 32 * 1024**2 and raw == working, "Raw HEAD byte drift/bound.")
        records[name] = hashlib.sha256(raw).hexdigest()
    required = {
        "scripts/mvp2_s2_batch_adapter.py",
        "scripts/mvp2_s2_synthetic_worker.py",
        "scripts/mvp2_s2_slurm_synthetic.py",
    }
    s.require(required <= set(records), "Missing source closure.")
    return {
        "source_sha256": s.digest(records),
        "tracked_count": len(records),
        "worker_sha256": records["scripts/mvp2_s2_synthetic_worker.py"],
    }


def verify_binaries(item, expected_tools, expected_python):
    item = validate_spec(item)
    s.require(
        expected_tools == item["tools_sha256"] and expected_python == item["python_sha256"],
        "Runtime envelope mismatch.",
    )
    s.require(type(expected_tools) is dict and set(expected_tools) == set(TOOLS), "Tool receipts.")
    for key in TOOLS:
        q._hash(expected_tools[key])
        s.require(sha_file(item["tools"][key]) == expected_tools[key], "Tool bytes changed.")
    q._hash(expected_python)
    s.require(sha_file(item["python"]) == expected_python, "Runtime bytes changed.")
    return {"python_sha256": expected_python, "tools_sha256": dict(expected_tools)}


def fields(text):
    s.require(
        type(text) is str and 0 < len(text) <= 65536 and len(text.strip().splitlines()) == 1,
        "Scheduler grammar.",
    )
    result = {}
    for key, value in re.findall(r"(?:^|\s)([A-Za-z][A-Za-z0-9_]*)=(\S*)", text.strip()):
        s.require(key not in result, "Duplicate scheduler key.")
        result[key] = value
    return result


def _uid(value):
    match = re.fullmatch(r"[A-Za-z0-9_.-]+\(([0-9]+)\)", value)
    s.require(match is not None, "Scheduler UID grammar.")
    return int(match[1])


def review_allocation(text, job, uid, node):
    d = fields(text)
    s.require(
        d.get("JobId") == job
        and _uid(d.get("UserId", "")) == uid
        and d.get("JobState") == "RUNNING"
        and d.get("NumNodes") == "1"
        and d.get("NumCPUs") == "2"
        and d.get("NodeList") == node
        and d.get("BatchHost") == node
        and d.get("TimeLimit") == "00:12:00"
        and d.get("MinMemoryNode") in {"2048M", "2G"},
        "Allocation mismatch.",
    )
    return {
        "allocation_sha256": s.digest(
            {
                k: d[k]
                for k in (
                    "JobId",
                    "UserId",
                    "JobState",
                    "NumNodes",
                    "NumCPUs",
                    "NodeList",
                    "BatchHost",
                    "TimeLimit",
                    "MinMemoryNode",
                )
            }
        ),
        **FLAGS,
    }


def review_step(text, binding, uid, node):
    binding = s.binding(binding)
    d = fields(text)
    s.require(
        d.get("StepId") == binding["job_id"] + "." + binding["worker_step_id"]
        and _uid(d.get("UserId", "")) == uid
        and d.get("Nodes") == node
        and d.get("State") == "RUNNING"
        and d.get("CPUs") == "1"
        and d.get("Tasks") == "1"
        and d.get("TimeLimit") == "00:09:00",
        "Worker step mismatch.",
    )
    return s.digest(
        {k: d[k] for k in ("StepId", "UserId", "Nodes", "State", "CPUs", "Tasks", "TimeLimit")}
    )


def accounting(text, job):
    s.require(type(text) is str and len(text) <= 65536, "Accounting bound.")
    result = {}
    lines = text.strip().splitlines()
    s.require(len(lines) <= 6, "Accounting rows bound.")
    for line in lines:
        row = line.split("|")
        s.require(len(row) == 4, "Accounting columns.")
        ident, state, code, elapsed = row
        s.require(
            re.fullmatch(re.escape(job) + r"(?:\.(?:batch|extern|0|[1-9][0-9]{0,9}))?", ident)
            and ident not in result
            and re.fullmatch(r"[0-9]+:[0-9]+", code)
            and re.fullmatch(r"[0-9]{1,9}", elapsed),
            "Accounting identity/exit grammar.",
        )
        s.require(
            state in TERMINAL | {"RUNNING", "PENDING", "COMPLETING"}, "Accounting state grammar."
        )
        result[ident] = {"state": state, "exit_code": code, "elapsed_seconds": int(elapsed)}
    return result


class BarrierServer:
    """Private local SOCK_SEQPACKET handshake; peer PID is kernel supplied."""

    def __init__(self, path):
        s.require(sys.platform == "linux", "Linux IPC required.")
        q._safe_path(Path(path))
        s.require(
            len(os.fsencode(path)) <= 100 and not Path(path).exists(), "IPC path bound/exists."
        )
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        try:
            self.socket.bind(str(path))
            os.chmod(path, 0o600)
            self.socket.listen(1)
        except BaseException:
            self.socket.close()
            raise
        self.peer = None

    def accept(self, remaining):
        s.require(0 < remaining <= 30, "IPC deadline.")
        deadline = time.monotonic() + remaining
        self.socket.settimeout(remaining)
        self.peer, _ = self.socket.accept()
        remaining = deadline - time.monotonic()
        s.require(remaining > 0, "IPC accept exhausted startup window.")
        self.peer.settimeout(remaining)
        pid, uid, _gid = struct.unpack(
            "3i", self.peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
        )
        data = self.peer.recv(4097)
        s.require(len(data) <= 4096, "Handshake bound.")
        return c.decode_json(data), {"pid": pid, "uid": uid}

    def release(self, value, remaining):
        s.require(self.peer is not None and 0 < remaining <= 30, "IPC release deadline.")
        payload = c.encoded(value)
        s.require(len(payload) <= 4096, "Release bound.")
        self.peer.settimeout(remaining)
        s.require(self.peer.send(payload) == len(payload), "Incomplete release.")

    def close(self):
        if self.peer is not None:
            self.peer.close()
        self.socket.close()  # Preserve the socket path/claim; no unlink/retry.


class BatchAdapter:
    """Integration behind a closed CLI. One instance/claim, no implicit retries.

    Live dependencies default to real read-only observers and transports. Tests
    inject all scheduler/process observations. Caller clocks never grant admission.
    """

    def __init__(
        self,
        item,
        *,
        transport=None,
        clock=time.monotonic,
        record=q.read_process_record,
        snapshot=s.read_v1_snapshot,
        pid_absent=None,
        server_factory=BarrierServer,
        exe_path=None,
    ):
        self.item = validate_spec(item)
        self.transport = RealTransport(item) if transport is None else transport
        self.clock, self.record, self.snapshot = clock, record, snapshot
        self.pid_absent = self._absent if pid_absent is None else pid_absent
        self.server_factory = server_factory
        self.exe_path = (
            (lambda pid: os.readlink("/proc/" + str(pid) + "/exe"))
            if exe_path is None
            else exe_path
        )
        self.started = q._number(clock())
        self.last = self.started
        self.known, self.samples, self.signal_names = {}, [], set()
        self.controller = self.handle = self.server = None
        self.claimed = False
        self.launch_attempted = False
        self.source = None
        self.journaled = 0

    @staticmethod
    def _absent(pid):
        try:
            os.stat("/proc/" + str(pid))
            return False
        except FileNotFoundError:
            return True
        # Permission/read errors are unknown, never absence/reaping.

    def _now(self):
        value = q._number(self.clock())
        s.require(value >= self.last, "Adapter clock rollback.")
        self.last = value
        return value

    def _query(self, tool, *args):
        return self.transport.command(
            (self.item["tools"][tool], *args), timeout_seconds=10, max_output_bytes=65536
        )

    def preflight(self, *, uid, pid, node, source, tool_sha256, python_sha256):
        """Called with independently checked raw checkout/runtime receipts."""
        s.require(not self.claimed and self.source is None, "Repeated preflight.")
        q._keys(source, {"source_sha256", "tracked_count", "worker_sha256"})
        q._hash(source["source_sha256"])
        q._hash(source["worker_sha256"])
        s.require(
            type(source["tracked_count"]) is int and 1 <= source["tracked_count"] <= 1024,
            "Source count.",
        )
        self.runtime = verify_binaries(self.item, tool_sha256, python_sha256)
        s.require(sys.version_info[:2] == (3, 13), "Supervisor Python version.")
        for tool in ("srun", "scontrol", "sacct", "scancel"):
            s.require(
                self._query(tool, "--version").strip() == "slurm 22.05.11",
                "Installed client version drift.",
            )
        self.supervisor = self.record(pid)
        s.require(
            self.supervisor["identity"]["uid"] == uid
            and self.supervisor["identity"]["state"] not in "ZXx",
            "Supervisor identity.",
        )
        # Independent caller must compare pid/uid/node with os.getpid/getuid/uname;
        # run_components below does so. Environment variables do not authorize.
        batch_text = self._query("scontrol", "listpids", self.item["job_id"] + ".batch")
        batch_binding = {
            "job_id": self.item["job_id"],
            "worker_step_id": "0",
            "supervisor_step_id": "batch",
            "nonce": self.item["nonce"],
            "source_commit": self.item["source_commit"],
        }
        # The numeric parser cannot accept 'batch'; validate the same columns explicitly.
        lines = batch_text.splitlines()
        s.require(
            lines and lines[0].split() == ["PID", "JOBID", "STEPID", "LOCALID", "GLOBALID"],
            "Batch grammar.",
        )
        batch_pids = set()
        for line in lines[1:]:
            values = line.split()
            s.require(
                len(values) == 5
                and re.fullmatch(r"[1-9][0-9]{0,9}", values[0])
                and values[1:3] == [self.item["job_id"], "batch"]
                and all(re.fullmatch(r"-1|0|[1-9][0-9]{0,9}", x) for x in values[3:])
                and int(values[0]) not in batch_pids,
                "Batch member drift.",
            )
            batch_pids.add(int(values[0]))
            s.require(len(batch_pids) <= 64, "Batch member bound.")
        s.require(pid in batch_pids, "Supervisor not in batch step.")
        self.allocation = review_allocation(
            self._query("scontrol", "-o", "show", "job", self.item["job_id"]),
            self.item["job_id"],
            uid,
            node,
        )
        self.node, self.uid, self.source = node, uid, copy.deepcopy(source)
        s.binding(batch_binding)

    def launch(self):
        s.require(
            self.source is not None and not self.launch_attempted,
            "Missing preflight/repeated claim.",
        )
        self.launch_attempted = True
        self.root = Path(self.item["run"])
        q._safe_path(self.root)
        self.root.mkdir(mode=0o700, exist_ok=False)
        self.claimed = True
        self.started = self._now()
        c.write_once(
            self.root / "claim.json", {"specification_sha256": s.digest(self.item), **FLAGS}
        )
        worker_plan = {
            "nonce": self.item["nonce"],
            "job_id": self.item["job_id"],
            "case": self.item["case"],
            "worker_sha256": self.source["worker_sha256"],
            "python_sha256": self.runtime["python_sha256"],
            "supervisor_pid": self.supervisor["identity"]["pid"],
            "uid": self.uid,
        }
        c.write_once(self.root / "worker-plan.json", worker_plan)
        self.server = self.server_factory(self.root / "ipc.sock")
        c.write_once(
            self.root / "launch-intent.json",
            {"argv": worker_argv(self.item), "specification_sha256": s.digest(self.item), **FLAGS},
        )
        self.handle = self.transport.spawn(worker_argv(self.item))

    def _members(self):
        pids = q.parse_listpids(
            self._query("scontrol", "listpids", self.target), self.contract["binding"]
        )
        records = [self.record(pid) for pid in sorted(pids)]
        for record in records:
            ident = q._identity(record["identity"])
            s.require(
                ident["uid"] == self.uid and ident["state"] not in "ZXx", "Invalid member identity."
            )
            if ident["pid"] in self.known:
                s.require(self.known[ident["pid"]] == q._stable_identity(ident), "PID reuse.")
            for key in s.CONTROLLERS:
                observed, base = record["scopes"][key], self.worker["scopes"][key]
                s._validate_scope(observed)
                op, bp = s._absolute(observed["scope"]), s._absolute(base["scope"])
                s.require(
                    observed["mount"] == base["mount"] and (op == bp or bp in op.parents),
                    "Member escaped.",
                )
            else:
                s.require(len(self.known) < 64, "Lifetime member bound.")
            self.known[ident["pid"]] = q._stable_identity(ident)
        return pids, records

    def handshake(self):
        s.require(
            self.claimed and self.handle is not None and self.controller is None, "Handshake state."
        )
        hello, peer = self.server.accept(30 - (self._now() - self.started))
        q._keys(
            hello,
            {
                "nonce",
                "job_id",
                "worker_step_id",
                "worker_sha256",
                "python_sha256",
                "python_version",
            },
        )
        s.require(
            hello["nonce"] == self.item["nonce"]
            and hello["job_id"] == self.item["job_id"]
            and hello["worker_sha256"] == self.source["worker_sha256"]
            and hello["python_sha256"] == self.runtime["python_sha256"]
            and hello["python_version"] == [3, 13]
            and peer["uid"] == self.uid,
            "Worker handshake drift.",
        )
        binding = s.binding(
            {
                "job_id": hello["job_id"],
                "worker_step_id": hello["worker_step_id"],
                "supervisor_step_id": "batch",
                "nonce": hello["nonce"],
                "source_commit": self.item["source_commit"],
            }
        )
        self.worker = self.record(peer["pid"])
        worker_exe = self.exe_path(peer["pid"])
        s.require(
            worker_exe == self.item["python"]
            and sha_file(worker_exe) == self.runtime["python_sha256"],
            "Actual worker executable drift.",
        )
        s.require(
            self.worker["identity"]["pid"] == peer["pid"]
            and self.worker["identity"]["uid"] == self.uid,
            "Peer process mismatch.",
        )
        step_hash = review_step(
            self._query(
                "scontrol",
                "-o",
                "show",
                "step",
                binding["job_id"] + "." + binding["worker_step_id"],
            ),
            binding,
            self.uid,
            self.node,
        )
        self.transport.bind(binding)
        self.contract = q.contract(
            self.item["inventory"],
            binding,
            self.item["case"],
            self.source["source_sha256"],
            self.source["worker_sha256"],
        )
        self.target = binding["job_id"] + "." + binding["worker_step_id"]
        receipts = []
        for _ in range(2):
            pids, records = self._members()
            snap = self.snapshot(self.worker["scopes"])
            s.require(
                snap.get("synthetic_observation") is False, "Fixture cannot release real IPC."
            )
            outside = self.record(self.supervisor["identity"]["pid"])
            s.require(
                q._stable_identity(outside["identity"])
                == q._stable_identity(self.supervisor["identity"])
                and outside["scopes"] == self.supervisor["scopes"],
                "Supervisor moved.",
            )
            receipts.append(
                q.barrier(
                    self.contract,
                    pids,
                    self.worker["identity"],
                    outside["identity"],
                    outside["identity"],
                    self.worker["scopes"],
                    outside["scopes"],
                    snap,
                    records,
                )
            )
        self.initial_snapshot = copy.deepcopy(snap)
        self.controller = q.Controller(self.contract, self.started)
        self.controller.release(self._now(), *receipts)
        c.write_once(self.root / "contract.json", self.contract)
        c.write_once(
            self.root / "binding.json", {"step_sha256": step_hash, "receipts": receipts, **FLAGS}
        )
        self._journal()
        self.server.release(
            {
                "nonce": self.item["nonce"],
                "contract_sha256": s.digest(self.contract),
                "worker_step_id": binding["worker_step_id"],
            },
            30 - (self._now() - self.started),
        )

    def _journal(self):
        # Immutable sequential records are outside worker scope. Intent before signal.
        for event in self.controller.events[self.journaled :]:
            path = self.root / f"event-{event['index']:04d}.json"
            if not path.exists():
                c.write_once(path, event)
            else:
                s.require(c.decode_json(_file(path, 65536)) == event, "Durable event drift.")
            self.journaled += 1

    def _signal(self, name):
        s.require(name not in self.signal_names, "Repeated adapter signal.")
        q.verify_events(self.contract, self.controller.events)
        s.require(
            self.controller.events[-1]["payload"]["action"] == name + "_exact_step",
            "No controller intent.",
        )
        self.signal_names.add(name)
        c.write_once(
            self.root / (name.lower() + "-intent.json"),
            {"target_sha256": s.digest(self.target), "signal": name, **FLAGS},
        )
        self.transport.signal(self.contract["binding"], name)

    def tick(self):
        s.require(
            self.controller is not None and len(self.samples) < MAX_SAMPLES, "Sample state/bound."
        )
        fault, snap, pids, rows, writes, products, reaped = False, None, None, {}, None, {}, False
        try:
            self.handle.pump(deadline=min(self.started + 660, self._now() + 0.5))
            reaped = self.handle.process.poll() is not None
            pids, _records = self._members()
            snap = self.snapshot(self.worker["scopes"])
            validate_snapshot(snap)
            initial = self.initial_snapshot["counters"]
            s.require(
                all(
                    snap["counters"][key] == initial[key]
                    for key in (
                        "memory_limit_bytes",
                        "effective_reported_memory_limit_bytes",
                        "cpuset_cpu_count",
                    )
                ),
                "Worker limits changed.",
            )
            previous_snapshot = next(
                (
                    sample["snapshot"]
                    for sample in reversed(self.samples)
                    if sample["snapshot"] and not sample["fault"]
                ),
                self.initial_snapshot,
            )
            s.require(
                all(
                    snap["counters"][key] >= previous_snapshot["counters"][key]
                    for key in ("memory_max_usage_bytes", "cpu_usage_ns", "memory_failcnt")
                ),
                "Lifetime counter rollback.",
            )
            s.require(
                snap["counters"]["freezer_unique_process_count"] == len(pids),
                "Membership disagreement.",
            )
            outside = self.record(self.supervisor["identity"]["pid"])
            s.require(
                q._stable_identity(outside["identity"])
                == q._stable_identity(self.supervisor["identity"])
                and outside["scopes"] == self.supervisor["scopes"],
                "Supervisor reused/moved.",
            )
            products = read_products(self.root / "worker")
            q.verify_worker_products(self.contract, products)
            fingerprint = {"products": products, "heartbeat": None, "pending": None}
            for name in ("heartbeat.json", "heartbeat.pending"):
                heartbeat = self.root / name
                if heartbeat.exists():
                    value = c.decode_json(_file(heartbeat, 4096))
                    q._keys(value, {"nonce", "counter"})
                    s.require(
                        value["nonce"] == self.item["nonce"]
                        and type(value["counter"]) is int
                        and 0 <= value["counter"] <= 120,
                        "Heartbeat drift.",
                    )
                    fingerprint["heartbeat" if name.endswith("json") else "pending"] = value
            writes = s.digest(fingerprint)
            rows = accounting(
                self._query(
                    "sacct",
                    "--noheader",
                    "--parsable2",
                    "--jobs=" + self.item["job_id"],
                    "--format=JobIDRaw,State,ExitCode,ElapsedRaw",
                ),
                self.item["job_id"],
            )
        except (OSError, ValueError, TimeoutError, KeyError, UnicodeError):
            fault = True
        now = self._now()
        if self.samples and now - (self.samples[-1]["seconds"] + self.started) > 5:
            fault = True
        absent = False
        try:
            absent = all(self.pid_absent(pid) is True for pid in self.known)
        except (OSError, ValueError):
            fault = True
        scope_hash = s.digest(snap["scopes"]) if snap and not fault else None
        inputs = {
            "worker_done": "terminal.json" in products or "failure.json" in products,
            "fault": fault,
            "scope_hash": scope_hash,
            "members": len(pids) if pids is not None else None,
            "all_known_pids_absent": absent,
            "launcher_reaped": reaped,
            "step_terminal": rows.get(self.target, {}).get("state") in TERMINAL and not fault,
            "writes_sha256": writes,
        }
        action = self.controller.observe(now, **inputs)
        self.samples.append(
            {
                "seconds": now - self.started,
                "snapshot": snap,
                "fault": fault,
                "accounting_sha256": s.digest(rows),
                "writes_sha256": writes,
            }
        )
        c.write_once(self.root / f"sample-{len(self.samples) - 1:04d}.json", self.samples[-1])
        self._journal()
        if action in {"TERM_exact_step", "KILL_exact_step"}:
            self._signal(action.split("_", 1)[0])
        return action

    def preserve(self, *, failure_code=None):
        """Keep an unbound/partial attempt without guessing signals or rerunning."""
        if self.server is not None:
            self.server.close()
        if self.handle is not None:
            self.handle.close_pipes()
        s.require(failure_code in {None, "adapter_failure_preserved"}, "Unknown failure code.")
        report = {
            "schema_version": "s2-batch-attempt-v1",
            "specification_sha256": s.digest(self.item),
            "status": self.controller.state if self.controller else "blocked_unbound",
            "source": self.source,
            "runtime": getattr(self, "runtime", None),
            "sample_count": len(self.samples),
            "failure_code": failure_code,
            "live_containment_qualified": False,
            **FLAGS,
        }
        if self.claimed and self.root.exists():
            c.write_once(self.root / "attempt.json", report)
        return report


def run_components(item):
    """Real integration, NOT admitted by CLI or receipts. Never submits a job.

    A future admission wrapper must check an approved runtime/source envelope
    before calling this component. No environment-variable escape hatch exists.
    """
    s.require(sys.platform == "linux", "Linux batch required.")
    item = validate_spec(item)
    s.require(
        Path(sys.executable).resolve() == Path(item["python"])
        and Path(__file__).resolve() == Path(item["checkout"]) / "scripts/mvp2_s2_batch_adapter.py",
        "Actual supervisor/source entry mismatch.",
    )
    expected_tools_sha256, expected_python_sha256 = item["tools_sha256"], item["python_sha256"]
    verify_binaries(item, expected_tools_sha256, expected_python_sha256)
    transport = RealTransport(item)
    # cat-file needs binary mode; the specialized method below preserves blobs.
    source = verify_checkout(item, transport.source_command)
    adapter = BatchAdapter(item, transport=transport)
    adapter.preflight(
        uid=os.getuid(),
        pid=os.getpid(),
        node=os.uname().nodename,
        source=source,
        tool_sha256=expected_tools_sha256,
        python_sha256=expected_python_sha256,
    )
    try:
        adapter.launch()
        adapter.handshake()
        while adapter.controller.state not in {"candidate_closed", "blocked"}:
            adapter.tick()
            if adapter.controller.state not in {"candidate_closed", "blocked"}:
                time.sleep(2)
        return adapter.preserve()
    except (OSError, ValueError, TimeoutError):
        return adapter.preserve(failure_code="adapter_failure_preserved")


def validate_snapshot(value):
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
        and value["synthetic_observation"] is False
        and value["status"] == "observed_not_qualified"
        and value["errors"] == []
        and all(value[k] is False for k in s.FLAGS),
        "Invalid live snapshot.",
    )
    counters = value["counters"]
    q._keys(
        counters,
        {
            "memory_usage_bytes",
            "memory_max_usage_bytes",
            "memory_limit_bytes",
            "memory_failcnt",
            "cpu_usage_ns",
            "cpuset_cpu_count",
            "effective_reported_memory_limit_bytes",
            "freezer_group_count",
            "freezer_unique_process_count",
        },
    )
    s.require(
        all(type(x) is int and 0 <= x <= s.MAX_COUNTER for x in counters.values())
        and 0
        < counters["effective_reported_memory_limit_bytes"]
        <= min(counters["memory_limit_bytes"], 256 * 1024**2)
        and counters["cpuset_cpu_count"] == 1
        and 1 <= counters["freezer_group_count"] <= 128
        and counters["freezer_unique_process_count"] <= 64,
        "Runtime resource drift.",
    )
    q._keys(value["scopes"], s.CONTROLLERS)
    for scope in value["scopes"].values():
        q._keys(scope, {"path_sha256", "inode"})
        q._hash(scope["path_sha256"])
        s.require(
            type(scope["inode"]) is list
            and len(scope["inode"]) == 2
            and all(type(x) is int and x >= 0 for x in scope["inode"]),
            "Scope inode drift.",
        )
    return value


BUNDLE_FILES = (
    "contract.json",
    "events.json",
    "worker.json",
    "adapter.json",
    "accounting.json",
    "review.json",
)


def review_bundle(records, expected_spec, expected_contract, expected_job_id):
    """Integrity replay, never installed-containment attestation or admission."""
    q._keys(records, BUNDLE_FILES)
    expected_spec = validate_spec(expected_spec)
    expected_spec_sha256 = s.digest(expected_spec)
    s.require(expected_job_id == expected_spec["job_id"], "External job/spec mismatch.")
    s.require(
        type(expected_job_id) is str and re.fullmatch(r"[1-9][0-9]{0,19}", expected_job_id),
        "External job required.",
    )
    attempt = records["adapter.json"]
    q._keys(attempt, {"attempt", "samples"})
    report, samples = attempt["attempt"], attempt["samples"]
    q._keys(
        report,
        {
            "schema_version",
            "specification_sha256",
            "status",
            "source",
            "runtime",
            "sample_count",
            "failure_code",
            "live_containment_qualified",
            *FLAGS,
        },
    )
    s.require(
        report["schema_version"] == "s2-batch-attempt-v1"
        and report["specification_sha256"] == expected_spec_sha256
        and all(report[k] is False for k in FLAGS)
        and report["live_containment_qualified"] is False
        and report["failure_code"] in {None, "adapter_failure_preserved"},
        "Attempt drift.",
    )
    s.require(
        type(samples) is list
        and len(samples) <= MAX_SAMPLES
        and type(report["sample_count"]) is int
        and report["sample_count"] == len(samples),
        "Sample count drift.",
    )
    if report["source"] is not None:
        q._keys(report["source"], {"source_sha256", "worker_sha256", "tracked_count"})
        q._hash(report["source"]["source_sha256"])
        q._hash(report["source"]["worker_sha256"])
        s.require(
            type(report["source"]["tracked_count"]) is int
            and 1 <= report["source"]["tracked_count"] <= 1024,
            "Source count drift.",
        )
    if report["runtime"] is not None:
        q._keys(report["runtime"], {"python_sha256", "tools_sha256"})
        q._hash(report["runtime"]["python_sha256"])
        q._keys(report["runtime"]["tools_sha256"], TOOLS)
        for value in report["runtime"]["tools_sha256"].values():
            q._hash(value)
        s.require(
            report["runtime"]
            == {
                "python_sha256": expected_spec["python_sha256"],
                "tools_sha256": expected_spec["tools_sha256"],
            },
            "External runtime envelope mismatch.",
        )
    if expected_contract is None:
        s.require(
            records["contract.json"] is None
            and records["events.json"] == []
            and records["worker.json"] == {}
            and samples == []
            and report["status"] == "blocked_unbound",
            "Unbound outcome drift.",
        )
        state = "blocked_unbound"
        worker = {"phase_count": 0, "worker_outcome": "partial", **q.FLAGS}
    else:
        expected_contract = q.validate_contract(expected_contract)
        s.require(
            c.encoded(records["contract.json"]) == c.encoded(expected_contract),
            "External contract drift.",
        )
        replay = q.verify_events(expected_contract, records["events.json"])
        state = replay["status"]
        s.require(state == report["status"], "Attempt/controller state drift.")
        worker = q.verify_worker_products(expected_contract, records["worker.json"])
        observations = [x for x in records["events.json"] if x["kind"] == "observation"]
        s.require(len(observations) == len(samples), "Missing resource observations.")
        for event, sample in zip(observations, samples, strict=True):
            q._keys(sample, {"seconds", "snapshot", "fault", "accounting_sha256", "writes_sha256"})
            q._hash(sample["accounting_sha256"])
            inputs = event["payload"]["inputs"]
            if sample["snapshot"] is not None:
                validate_portable_snapshot(sample["snapshot"])
            s.require(
                sample["seconds"] == event["seconds"]
                and sample["fault"] == inputs["fault"]
                and sample["writes_sha256"] == inputs["writes_sha256"],
                "Resource/event drift.",
            )
            if not sample["fault"]:
                validate_snapshot(sample["snapshot"])
                s.require(
                    s.digest(sample["snapshot"]["scopes"]) == inputs["scope_hash"]
                    and sample["snapshot"]["counters"]["freezer_unique_process_count"]
                    == inputs["members"],
                    "Resource/scope drift.",
                )
        s.require(
            report["source"]["source_sha256"] == expected_contract["source_sha256"]
            and report["source"]["worker_sha256"] == expected_contract["worker_sha256"],
            "Source binding drift.",
        )
    rows = records["accounting.json"]
    s.require(type(rows) is dict and 2 <= len(rows) <= 6, "Terminal accounting absent.")
    for ident, row in rows.items():
        s.require(
            type(ident) is str
            and re.fullmatch(r"[1-9][0-9]*(?:\.(?:batch|extern|0|[1-9][0-9]*))?", ident),
            "Accounting ID.",
        )
        q._keys(row, {"state", "exit_code", "elapsed_seconds"})
        s.require(
            row["state"] in TERMINAL
            and type(row["exit_code"]) is str
            and re.fullmatch(r"[0-9]+:[0-9]+", row["exit_code"])
            and type(row["elapsed_seconds"]) is int
            and row["elapsed_seconds"] >= 0,
            "Nonterminal/invalid accounting.",
        )
    jobs = [key for key in rows if "." not in key]
    s.require(
        len(jobs) == 1
        and jobs[0] == expected_job_id
        and jobs[0] + ".batch" in rows
        and all(key == jobs[0] or key.startswith(jobs[0] + ".") for key in rows),
        "Accounting cohort drift.",
    )
    if expected_contract is not None:
        binding = expected_contract["binding"]
        s.require(
            jobs[0] == binding["job_id"] and jobs[0] + "." + binding["worker_step_id"] in rows,
            "Missing bound step accounting.",
        )
    return {
        "schema_version": "s2-batch-bundle-review-v1",
        "status": "integrity_replayed_not_live_qualified",
        "controller_state": state,
        "worker": worker,
        "sample_count": len(samples),
        "specification_sha256": expected_spec_sha256,
        "live_containment_qualified": False,
        **FLAGS,
    }


def collect_terminal_components(run, destination, expected_spec, expected_contract, terminal_text):
    """Read-only original run + exclusive collection; no query, signal or retry."""
    spec = validate_spec(expected_spec)
    root = Path(run)
    q._safe_path(root)
    s.require(str(root) == spec["run"], "Run path mismatch.")
    claim = c.decode_json(_file(root / "claim.json", 4096))
    s.require(claim == {"specification_sha256": s.digest(spec), **FLAGS}, "Original claim drift.")
    report = c.decode_json(_file(root / "attempt.json", 65536))
    count = report["sample_count"]
    s.require(type(count) is int and 0 <= count <= MAX_SAMPLES, "Sample bound.")
    samples = [c.decode_json(_file(root / f"sample-{i:04d}.json", 65536)) for i in range(count)]
    events = []
    if expected_contract is not None:
        for i in range(q.PROFILE["maximum_events"]):
            path = root / f"event-{i:04d}.json"
            if not path.exists():
                s.require(
                    not any(
                        (root / f"event-{j:04d}.json").exists()
                        for j in range(i + 1, q.PROFILE["maximum_events"])
                    ),
                    "Event journal hole.",
                )
                break
            events.append(c.decode_json(_file(path, 65536)))
        actual = c.decode_json(_file(root / "contract.json", 65536))
        s.require(c.encoded(actual) == c.encoded(expected_contract), "Original contract drift.")
    records = {
        "contract.json": expected_contract,
        "events.json": events,
        "worker.json": read_products(root / "worker") if expected_contract else {},
        "adapter.json": {"attempt": report, "samples": samples},
        "accounting.json": accounting(terminal_text, spec["job_id"]),
        "review.json": None,
    }
    review = review_bundle(records, spec, expected_contract, spec["job_id"])
    records["review.json"] = review
    return pack_bundle(destination, records, spec, expected_contract, spec["job_id"])


def pack_bundle(destination, records, expected_spec, expected_contract, expected_job_id):
    review = review_bundle(records, expected_spec, expected_contract, expected_job_id)
    s.require(records["review.json"] == review, "Unrecomputed review.")
    payloads = {key: c.encoded(records[key]) for key in BUNDLE_FILES}
    s.require(sum(map(len, payloads.values())) <= q.LIMIT - 16384, "Bundle size bound.")
    root = Path(destination)
    q._safe_path(root)
    root.mkdir(mode=0o700, exist_ok=False)
    target = root / "batch-evidence.tar.gz"
    with target.open("xb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode="w") as archive:
            for key, payload in payloads.items():
                info = tarfile.TarInfo(key)
                info.size, info.mode = len(payload), 0o600
                archive.addfile(info, io.BytesIO(payload))
    checksum = sha_file(target, q.LIMIT)
    with (root / "batch-evidence.tar.gz.sha256").open("x", encoding="ascii") as stream:
        stream.write(checksum + "  batch-evidence.tar.gz\n")
    return {"sha256": checksum, "review": review, **FLAGS}


def read_products(root):
    result = {}
    for name in q.WORKER_FILES:
        path = Path(root) / name
        q._safe_path(path)
        try:
            result[name] = c.decode_json(_file(path, 4096))
        except FileNotFoundError:
            pass
    return result


def validate_portable_snapshot(value):
    """Preserve invalid measured limits as adverse data, but reject arbitrary fields."""
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
        and value["status"] in {"observed_not_qualified", "blocked_observation"}
        and value["errors"] in ([], ["scope_or_counter_invalid"])
        and all(value[key] is False for key in s.FLAGS),
        "Portable observation schema.",
    )
    s.require(
        type(value["scopes"]) is dict and set(value["scopes"]) <= set(s.CONTROLLERS),
        "Portable scope schema.",
    )
    for scope in value["scopes"].values():
        q._keys(scope, {"path_sha256", "inode"})
        q._hash(scope["path_sha256"])
        s.require(
            type(scope["inode"]) is list
            and len(scope["inode"]) == 2
            and all(type(x) is int and x >= 0 for x in scope["inode"]),
            "Portable inode schema.",
        )
    if value["counters"] is not None:
        q._keys(
            value["counters"],
            {
                "memory_usage_bytes",
                "memory_max_usage_bytes",
                "memory_limit_bytes",
                "memory_failcnt",
                "cpu_usage_ns",
                "cpuset_cpu_count",
                "effective_reported_memory_limit_bytes",
                "freezer_group_count",
                "freezer_unique_process_count",
            },
        )
        s.require(
            all(type(x) is int and 0 <= x <= s.MAX_COUNTER for x in value["counters"].values()),
            "Portable counter schema.",
        )


def audit_bundle(path, expected_sha256, expected_spec, expected_contract, expected_job_id):
    q._hash(expected_sha256)
    raw = _file(path, q.LIMIT)
    s.require(hashlib.sha256(raw).hexdigest() == expected_sha256, "Bundle checksum drift.")
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
        unpacked = stream.read(q.LIMIT + 1)
    s.require(len(unpacked) <= q.LIMIT, "Bundle expansion bound.")
    records, end = {}, 0
    with tarfile.open(fileobj=io.BytesIO(unpacked), mode="r:") as archive:
        for member in archive:
            s.require(
                member.name in BUNDLE_FILES
                and member.name not in records
                and member.isfile()
                and not member.pax_headers
                and 0 < member.size <= q.LIMIT,
                "Bundle member drift.",
            )
            records[member.name] = c.decode_json(archive.extractfile(member).read())
            end = member.offset_data + ((member.size + 511) // 512) * 512
    s.require(not any(unpacked[end:]), "Bundle trailing data.")
    review = review_bundle(records, expected_spec, expected_contract, expected_job_id)
    s.require(records["review.json"] == review, "Bundle review drift.")
    return review


if __name__ == "__main__":
    execute_batch()
