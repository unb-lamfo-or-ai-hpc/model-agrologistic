"""Independent post-exit observations; never a cleanup or execution certificate."""

from __future__ import annotations

import math
import re
from pathlib import Path

from scripts import mvp2_s2_allocation_diagnostic as d
from scripts import mvp2_s2_batch_adapter as a
from scripts import mvp2_s2_first_normal as n
from scripts import mvp2_s2_scope_diagnostic as scope
from scripts import mvp2_s2_slurm_step as s
from scripts import mvp2_s2_slurm_synthetic as q

FLAGS = {**d.FLAGS, "live_isolation_proven": False}
OFFSETS = (0, 1, 3, 6, 10)
FILES = {
    "memory": ("cgroup.procs", "memory.limit_in_bytes", "memory.usage_in_bytes"),
    "cpuacct": ("cgroup.procs", "cpuacct.usage"),
    "freezer": ("cgroup.procs", "freezer.state"),
    "cpuset": ("cgroup.procs", "cpuset.cpus"),
}
CHANNELS = {"controllers", "members", "step", "accounting", "products", "leader"}
OUTCOMES = {"available", "missing", "denied", "invalid", "unavailable"}
LIMIT = 2 * 1024**2


def keys(value, expected):
    d.require(type(value) is dict and set(value) == set(expected), "Observation schema.")


def integer(value, maximum=2**64 - 1):
    d.require(type(value) is int and 0 <= value <= maximum, "Observation integer.")


def failure(exc):
    return (
        "missing"
        if isinstance(exc, FileNotFoundError)
        else "denied"
        if isinstance(exc, PermissionError)
        else "invalid"
        if isinstance(
            exc, (ValueError, UnicodeError, TypeError, KeyError, OverflowError, RecursionError)
        )
        else "unavailable"
    )


def error_site(exc):
    site = None
    trace = exc.__traceback__
    while trace is not None:
        module = trace.tb_frame.f_globals.get("__name__", "").split(".")[-1]
        if module in {"mvp2_s2_fast_exit", "mvp2_s2_fast_exit_observation", "__main__"}:
            site = {
                "module": "mvp2_s2_fast_exit_observation" if module == "__main__" else module,
                "line": trace.tb_lineno,
            }
        trace = trace.tb_next
    return site


def validate_site(site):
    if site is not None:
        keys(site, {"module", "line"})
        d.require(
            site["module"] in {"mvp2_s2_fast_exit", "mvp2_s2_fast_exit_observation"},
            "Reviewed error site.",
        )
        integer(site["line"], 10000)
        d.require(site["line"] > 0, "Error line.")


def entry_log(path):
    """Metadata plus at most one allowlisted structured entry diagnostic, never messages."""

    def read():
        raw = a._file(path, 65536)
        diagnostics = []
        for line in raw.splitlines():
            try:
                value = d.decode(line)
            except (ValueError, UnicodeError):
                continue
            if type(value) is dict and value.get("schema_version") == "s2-fast-exit-entry-v1":
                validate_entry(value)
                diagnostics.append(value)
        d.require(len(diagnostics) <= 1, "Entry diagnostic bound.")
        return {"bytes": len(raw), "sha256": d.digest(raw), "diagnostics": diagnostics}

    return channel(read)


def validate_entry(value):
    keys(value, {"schema_version", "role", "error_kind", "site", *FLAGS})
    d.require(
        value["schema_version"] == "s2-fast-exit-entry-v1"
        and value["role"] in {"batch", "leaf"}
        and value["error_kind"] in {"missing", "denied", "invalid", "unavailable"}
        and all(value[key] is False for key in FLAGS),
        "Entry diagnostic.",
    )
    validate_site(value["site"])


def channel(callback):
    """An unavailable channel must not suppress any other channel."""
    try:
        return {"status": "available", "value": callback()}
    except (
        OSError,
        ValueError,
        TimeoutError,
        UnicodeError,
        TypeError,
        KeyError,
        OverflowError,
        RecursionError,
    ) as exc:
        return {"status": failure(exc), "value": None}


def controller(path, names, initial=None):
    """Direct members only, not recursive descendant cleanup; no raw paths exported."""
    directory = q.r._Directory(path)
    try:
        d.require(initial is None or directory.identity == initial, "Replaced scope.")
        values = {}
        for name in names:

            def read(name=name):
                text = directory.read(name)
                if name == "cgroup.procs":
                    d.require(len(text.splitlines()) <= 64, "Direct member bound.")
                    members = [s._uint(x) for x in text.splitlines()]
                    d.require(
                        all(x > 0 for x in members) and len(set(members)) == len(members),
                        "Direct member grammar.",
                    )
                    return sorted(members)
                if name == "cpuset.cpus":
                    return s._cpus(text)
                if name == "freezer.state":
                    d.require(text in {"THAWED", "FREEZING", "FROZEN"}, "Freezer grammar.")
                    return text
                return s._uint(text)

            values[name] = channel(read)
        return {"identity": directory.identity, "files": values}
    finally:
        directory.close()


def controllers(scopes, initial=None):
    return {
        key: channel(
            lambda key=key: controller(
                scopes[key]["scope"], FILES[key], None if initial is None else initial[key]
            )
        )
        for key in s.CONTROLLERS
    }


def products(root, nonce):
    """Fixed normal stdlib prefix; partial/missing files stay individually visible."""
    expected = {
        f"phase-{i}.json": {"nonce": nonce, "phase": phase}
        for i, phase in enumerate(("build", "optimization", "export", "disposal"))
    }
    expected["terminal.json"] = {"nonce": nonce, "status": "synthetic_complete"}
    result = {}
    for name, value in expected.items():

        def read(name=name, value=value):
            raw = a._file(Path(root) / name, 4096)
            d.require(d.decode(raw) == value, "Unexpected phase/nonce.")
            return {"sha256": d.digest(raw)}

        result[name] = channel(read)
    return result


def leader(identity, proc_root="/proc"):
    """Known PID absence is not proof of descendant cleanup."""
    try:
        text = a._file(Path(proc_root) / str(identity["pid"]) / "stat", 65536).decode()
    except FileNotFoundError:
        return "known_pid_absent"
    actual = q.proc_identity(text, identity["uid"], identity["pid"])
    return "known_pid_present" if actual["starttime"] == identity["starttime"] else "pid_reused"


def accounting_argv(tool, job):
    return [
        tool,
        "-j",
        job,
        "--noheader",
        "--parsable2",
        "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw",
    ]


def query(argv, parser, command=d.command):
    meta, raw = command(argv, timeout=2)
    if meta["status"] != "complete":
        raise TimeoutError("Bounded query incomplete.")
    if meta["returncode"] != 0:
        raise OSError("Bounded query unsuccessful.")
    return {"stdout_sha256": d.digest(raw), "data": parser(raw.decode("ascii"))}


def step_summary(text, binding):
    fields = a.fields(text)
    d.require(
        fields.get("StepId") == binding["job_id"] + "." + binding["worker_step_id"],
        "Foreign step query.",
    )
    state = fields.get("State")
    d.require(state in a.TERMINAL | {"RUNNING", "PENDING", "COMPLETING"}, "Step state.")
    return {"state": state}


def sample(binding, scopes, initial, identity, root, tools, *, command=d.command):
    subject = binding["job_id"] + "." + binding["worker_step_id"]
    # Each callback is independently caught; order is not a dependency chain.
    callbacks = {
        "controllers": lambda: controllers(scopes, initial),
        "members": lambda: query(
            [tools["scontrol"], "listpids", subject],
            lambda text: sorted(q.parse_listpids(text, binding)),
            command,
        ),
        "step": lambda: query(
            [tools["scontrol"], "-o", "show", "step", subject],
            lambda text: step_summary(text, binding),
            command,
        ),
        "accounting": lambda: query(
            accounting_argv(tools["sacct"], binding["job_id"]),
            lambda text: a.accounting(text, binding["job_id"]),
            command,
        ),
        "products": lambda: products(root, binding["nonce"]),
        "leader": lambda: leader(identity),
    }
    return {key: channel(callback) for key, callback in callbacks.items()}


def review_initial(private, job_text, step_text, members_text, binding, uid, node):
    """Bind current allocation/step/kernel peer and the unchanged synthetic limits."""
    job, step = a.fields(job_text), a.fields(step_text)
    node = a.scheduler_node(node)
    d.require(
        job.get("JobId") == binding["job_id"]
        and a._uid(job.get("UserId", "")) == uid
        and job.get("JobState") == "RUNNING"
        and job.get("NumNodes") == "1"
        and job.get("NumCPUs") == "2"
        and job.get("NodeList") == node
        and job.get("BatchHost") == node
        and job.get("TimeLimit") == "00:05:00"
        and job.get("MinMemoryNode") in {"2048M", "2G"},
        "Observation allocation.",
    )
    d.require(
        step.get("StepId") == binding["job_id"] + "." + binding["worker_step_id"]
        and step.get("UserId") == str(uid)
        and step.get("Nodes") == "1"
        and step.get("NodeList") == node
        and step.get("State") == "RUNNING"
        and step.get("CPUs") == "1"
        and step.get("Tasks") == "1"
        and step.get("TimeLimit") == "00:02:00",
        "Observation step.",
    )
    d.require(
        q.parse_listpids(members_text, binding) == {private["worker"]["identity"]["pid"]},
        "Kernel/scheduler peer mismatch.",
    )
    limits = scope.limits(private)
    for role, ceiling in (("worker", 256 * 1024**2), ("supervisor", 2048 * 1024**2)):
        item = limits[role]
        d.require(
            item["error_kind"] is None
            and 0 < item["cpuset_cpu_count"] <= 2
            and 0
            < min(item["memory_limit_bytes"], item["hierarchical_memory_limit_bytes"])
            <= ceiling,
            "Observation resource boundary.",
        )
        affinity = re.findall(r"^Cpus_allowed_list:\s*(.+)$", private[role]["raw"]["status"], re.M)
        d.require(
            len(affinity) == 1 and 0 < s._cpus(affinity[0]) <= (1 if role == "worker" else 2),
            "Initial affinity boundary.",
        )
    maps = s.mapped_scopes(
        private["worker"]["raw"]["cgroup"], private["worker"]["raw"]["mountinfo"]
    )
    first = controllers(maps)
    d.require(
        all(first[k]["status"] == "available" for k in s.CONTROLLERS),
        "Initial controller unavailable.",
    )
    return maps, {k: first[k]["value"]["identity"] for k in s.CONTROLLERS}


def validate_channel(item, validator):
    keys(item, {"status", "value"})
    d.require(item["status"] in OUTCOMES, "Channel outcome.")
    if item["status"] == "available":
        validator(item["value"])
    else:
        d.require(item["value"] is None, "Unknown is not a value.")


def sha(value):
    d.require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value), "SHA256 grammar.")


def pids(value):
    d.require(
        type(value) is list
        and len(value) <= 64
        and all(type(x) is int for x in value)
        and value == sorted(set(value)),
        "PID list.",
    )
    for pid in value:
        integer(pid, 2**32 - 1)
        d.require(pid > 0, "Positive PID.")


def validate_controllers(value):
    keys(value, s.CONTROLLERS)
    for name, item in value.items():

        def validate(record, name=name):
            keys(record, {"identity", "files"})
            d.require(
                type(record["identity"]) is list and len(record["identity"]) == 2, "Scope identity."
            )
            for part in record["identity"]:
                integer(part)
            keys(record["files"], FILES[name])
            for filename, field in record["files"].items():

                def validate_file(v, filename=filename):
                    if filename == "cgroup.procs":
                        pids(v)
                    elif filename == "freezer.state":
                        d.require(v in {"THAWED", "FREEZING", "FROZEN"}, "Freezer state.")
                    else:
                        integer(v)

                validate_channel(field, validate_file)

        validate_channel(item, validate)


def validate_accounting(value, job):
    d.require(type(value) is dict and len(value) <= 16, "Accounting row bound.")
    # Reuse strict parser/row schema by round-tripping canonical wide rows.
    lines = []
    for key, row in value.items():
        keys(row, {"state", "exit_code", "elapsed_seconds"})
        integer(row["elapsed_seconds"])
        d.require(
            type(key) is str and type(row["state"]) is str and type(row["exit_code"]) is str,
            "Accounting types.",
        )
        lines.append(f"{key}|{row['state']}|{row['exit_code']}|{row['elapsed_seconds']}")
    d.require(a.accounting("\n".join(lines), job) == value, "Accounting replay.")


def validate_products(value):
    keys(value, {*[f"phase-{i}.json" for i in range(4)], "terminal.json"})
    for item in value.values():

        def validate(record):
            keys(record, {"sha256"})
            sha(record["sha256"])

        validate_channel(item, validate)


def initial_record(private):
    return {"summary": scope.summarize(private), "limits": scope.limits(private)}


def validate_initial(value, commit, job, plan_sha):
    keys(value, {"summary", "limits"})
    # Reuse the existing path-free scope/limit schema, never its consumed live claim.
    scope.validate_observation(
        {
            "schema_version": "s2-scope-observation-v1",
            "source_commit": commit,
            "plan_sha256": plan_sha,
            "job_id": job,
            "step_id": None,
            "status": "incomplete",
            "phase": "observation",
            "error_kind": None,
            "summary": value["summary"],
            "limits": value["limits"],
            "queries": {},
            "local_client_returncode": None,
            **scope.FLAGS,
        },
        commit,
        plan_sha,
        job,
    )


def validate_report(report, commit, job, plan_sha):
    keys(
        report,
        {
            "schema_version",
            "source_commit",
            "job_id",
            "plan_sha256",
            "step_id",
            "status",
            "phase",
            "error_kind",
            "error_site",
            "initial_sha256",
            "initial",
            "local_client_returncode",
            "samples",
            *FLAGS,
        },
    )
    d.require(
        report["schema_version"] == "s2-fast-exit-observation-v1"
        and report["source_commit"] == commit
        and report["job_id"] == job
        and report["plan_sha256"] == plan_sha
        and all(report[k] is False for k in FLAGS),
        "Observation anchor/authority.",
    )
    d.require(
        report["status"] in {"observed_not_admitted", "blocked_environment", "incomplete"}
        and report["phase"] in {"identity", "handshake", "initial", "exit", "samples", "complete"}
        and report["error_kind"] in {None, "missing", "denied", "invalid", "unavailable"},
        "Observation outcome.",
    )
    validate_site(report["error_site"])
    if report["initial_sha256"] is not None:
        sha(report["initial_sha256"])
    if report["initial"] is not None:
        validate_initial(report["initial"], commit, job, plan_sha)
    step = report["step_id"]
    d.require(
        step is None
        or (type(step) is str and re.fullmatch(r"[0-9]{1,10}", step) and int(step) < 0xFFFFFFFA),
        "Numeric step.",
    )
    rc = report["local_client_returncode"]
    d.require(rc is None or (type(rc) is int and -255 <= rc <= 255), "Client exit.")
    samples = report["samples"]
    d.require(type(samples) is list and len(samples) <= len(OFFSETS), "Sample bound.")
    previous = -1
    for i, item in enumerate(samples):
        keys(item, {"offset_seconds", "elapsed_seconds", "channels"})
        elapsed = item["elapsed_seconds"]
        d.require(
            type(item["offset_seconds"]) is int
            and item["offset_seconds"] == OFFSETS[i]
            and type(elapsed) in (int, float)
            and math.isfinite(elapsed)
            and max(previous, OFFSETS[i]) <= elapsed <= 240,
            "Actual observation time.",
        )
        previous = elapsed
        keys(item["channels"], CHANNELS)
        for key, field in item["channels"].items():

            def validate(value, key=key):
                if key == "controllers":
                    validate_controllers(value)
                elif key == "products":
                    validate_products(value)
                elif key == "leader":
                    d.require(
                        value in {"known_pid_absent", "known_pid_present", "pid_reused"},
                        "Leader observation.",
                    )
                else:
                    keys(value, {"stdout_sha256", "data"})
                    sha(value["stdout_sha256"])
                    if key == "members":
                        pids(value["data"])
                    elif key == "step":
                        keys(value["data"], {"state"})
                        d.require(
                            value["data"]["state"]
                            in a.TERMINAL | {"RUNNING", "PENDING", "COMPLETING"},
                            "Step state.",
                        )
                    else:
                        validate_accounting(value["data"], job)

            validate_channel(field, validate)
    if report["status"] == "observed_not_admitted":
        d.require(
            step is not None
            and rc == 0
            and len(samples) == 5
            and report["phase"] == "complete"
            and report["error_kind"] is None
            and report["error_site"] is None
            and report["initial_sha256"] is not None,
            "Complete observation prerequisites.",
        )
    d.require(not samples or (step is not None and rc is not None), "Unbound samples.")
    return report


def audit(path, checksum, commit, job, plan_sha):
    """Path-free bounded archive; checksum/replay never establishes live cleanup."""
    sha(checksum)
    sha(plan_sha)
    raw = a._file(path, LIMIT)
    d.require(d.digest(raw) == checksum, "Archive checksum.")
    records = n.read_tar(
        raw, LIMIT, {"anchor.json", "observation.json", "accounting.json", "entry.json"}
    )
    d.require(
        set(records) == {"anchor.json", "observation.json", "accounting.json", "entry.json"},
        "Archive inventory.",
    )
    anchor = d.decode(records["anchor.json"])
    keys(anchor, {"schema_version", "source_commit", "job_id", "plan_sha256", *FLAGS})
    d.require(all(anchor[k] is False for k in FLAGS), "Carrier boolean authority.")
    d.require(
        anchor
        == {
            "schema_version": "s2-fast-exit-carrier-v1",
            "source_commit": commit,
            "job_id": job,
            "plan_sha256": plan_sha,
            **FLAGS,
        },
        "Carrier identity.",
    )
    report = d.decode(records["observation.json"])
    if report is not None:
        validate_report(report, commit, job, plan_sha)
    rows = d.decode(records["accounting.json"])
    validate_accounting(rows, job)
    required = {job, job + ".batch"}
    if report is not None and report["step_id"] is not None:
        required.add(job + "." + report["step_id"])
    d.require(
        required <= set(rows) and all(row["state"] in a.TERMINAL for row in rows.values()),
        "Exact terminal accounting required.",
    )
    entry = d.decode(records["entry.json"])
    keys(
        entry,
        {
            "stdout",
            "stderr",
            "client_stdout",
            "client_stderr",
            "leaf",
            "invalid_observation_sha256",
        },
    )

    def validate_leaf(value):
        keys(value, {"step_id", "sha256"})
        sha(value["sha256"])
        d.require(
            type(value["step_id"]) is str
            and re.fullmatch(r"[0-9]{1,10}", value["step_id"])
            and int(value["step_id"]) < 0xFFFFFFFA,
            "Forensic numeric step.",
        )
        if report is not None and report["step_id"] is not None:
            d.require(value["step_id"] == report["step_id"], "Leaf/report step drift.")
        d.require(job + "." + value["step_id"] in rows, "Forensic exact-step accounting.")

    validate_channel(entry["leaf"], validate_leaf)
    for key in ("stdout", "stderr", "client_stdout", "client_stderr"):

        def validate_log(value):
            keys(value, {"bytes", "sha256", "diagnostics"})
            integer(value["bytes"], 65536)
            sha(value["sha256"])
            d.require(
                type(value["diagnostics"]) is list and len(value["diagnostics"]) <= 1,
                "Entry diagnostics.",
            )
            for diagnostic in value["diagnostics"]:
                validate_entry(diagnostic)

        validate_channel(entry[key], validate_log)
    if entry["invalid_observation_sha256"] is not None:
        sha(entry["invalid_observation_sha256"])
    return {
        "status": "terminal_observation_preserved_not_qualified"
        if report is not None
        else "terminal_forensic_preserved_not_qualified",
        **FLAGS,
    }
