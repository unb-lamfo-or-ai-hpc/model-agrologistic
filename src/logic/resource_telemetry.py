"""Opt-in OS telemetry; the sampling thread never calls a solver API.

All byte counts have an explicit scope. Missing observations are null, not
zero. Resource evidence is not an optimization or feasibility certificate.
"""

from __future__ import annotations

import csv
import json
import math
import os
import platform
import re
import threading
from contextvars import ContextVar
from functools import wraps
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from time import perf_counter

CURRENT = ContextVar("agrologistic_resource_session", default=None)
PRODUCTS = (
    "runtime_capabilities.json",
    "allocation_receipt.json",
    "matrix_statistics.json",
    "resource_timeseries.csv",
    "stage_progress.csv",
    "termination.json",
    "manifest.json",
)
RESOURCE_FIELDS = (
    "elapsed_seconds",
    "phase",
    "process_tree_rss_bytes",
    "process_tree_cpu_seconds",
    "process_count",
    "root_native_threads",
    "cgroup_current_bytes",
    "cgroup_limit_bytes",
    "inspection_seconds",
    "observation_errors",
)
PROGRESS_FIELDS = (
    "elapsed_seconds",
    "phase",
    "stage_number",
    "stage_role",
    "event",
    "incumbent",
    "bound",
    "mip_gap",
    "iterations",
    "nodes",
    "solver_memory_bytes",
    "status",
    "python_index_entries",
)


def _json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) and abs(value) < 1e99 else None
    except (ValueError, TypeError):
        return None


def cgroup_memory(proc_root=Path("/proc"), *, sys_root=Path("/sys")):
    """Resolve the process's actual v1/v2 memory controller and ancestor cap.

    Mount roots are honoured. No host-root cgroup is substituted for a missing
    process membership; such a substitution could misstate the allocation.
    """
    try:
        groups = (proc_root / "self/cgroup").read_text().splitlines()
        mounts = (proc_root / "self/mountinfo").read_text().splitlines()
        for group in groups:
            _, controllers, membership = group.split(":", 2)
            unified = controllers == ""
            if not unified and "memory" not in controllers.split(","):
                continue
            for line in mounts:
                left, right = line.split(" - ", 1)
                fields, fs = left.split(), right.split()
                if fs[0] != ("cgroup2" if unified else "cgroup"):
                    continue
                if not unified and "memory" not in fs[2].split(","):
                    continue
                mount_root, mountpoint = fields[3:5]
                relative = Path(membership).relative_to(mount_root)
                mount = sys_root / Path(mountpoint).relative_to("/sys")
                leaf = mount / relative
                current_name = "memory.current" if unified else "memory.usage_in_bytes"
                limit_name = "memory.max" if unified else "memory.limit_in_bytes"
                current = int((leaf / current_name).read_text().strip())
                limits = []
                for directory in (leaf, *leaf.parents):
                    if not directory.is_relative_to(mount):
                        break
                    raw = (directory / limit_name).read_text().strip()
                    if raw != "max" and int(raw) < 2**60:
                        limits.append(int(raw))
                return {
                    "current_bytes": current,
                    "limit_bytes": min(limits) if limits else None,
                    "path": str(leaf),
                    "version": 2 if unified else 1,
                    "error": None,
                }
    except (OSError, ValueError, IndexError) as exc:
        return {"current_bytes": None, "limit_bytes": None, "error": type(exc).__name__}
    return {"current_bytes": None, "limit_bytes": None, "error": "controller_unavailable"}


def process_observation(pid=None, proc_root=Path("/proc")):
    """Sample live same-user descendants; this is not cgroup or solver memory.

    CPU seconds are cumulative for currently observed processes. Exited children
    are not retained, so differences are not a lifetime core-hour estimator.
    """
    pid = os.getpid() if pid is None else pid
    started = perf_counter()
    errors, processes = [], {}
    try:
        ticks = os.sysconf("SC_CLK_TCK")
        uid = os.getuid()
        for path in proc_root.iterdir():
            if not path.name.isdecimal():
                continue
            try:
                status = dict(
                    line.split(":", 1)
                    for line in (path / "status").read_text().splitlines()
                    if ":" in line
                )
                if int(status["Uid"].split()[0]) != uid:
                    continue
                stat = (path / "stat").read_text().rsplit(")", 1)[1].split()
                processes[int(path.name)] = {
                    "ppid": int(stat[1]),
                    "cpu": (int(stat[11]) + int(stat[12])) / ticks,
                    "rss": int(status["VmRSS"].split()[0]) * 1024 if "VmRSS" in status else None,
                    "threads": int(status["Threads"]),
                }
            except (OSError, ValueError, KeyError, IndexError):
                if int(path.name) == pid:
                    errors.append("root_process_unreadable")
        selected = {pid} if pid in processes else set()
        while True:
            expanded = selected | {p for p, v in processes.items() if v["ppid"] in selected}
            if expanded == selected:
                break
            selected = expanded
        rows = [processes[p] for p in selected]
        rss = (
            sum(v["rss"] for v in rows)
            if rows and all(v["rss"] is not None for v in rows)
            else None
        )
        cpu = sum(v["cpu"] for v in rows) if rows else None
    except (OSError, AttributeError, ValueError) as exc:
        errors.append(type(exc).__name__)
        rows, rss, cpu = [], None, None
    cgroup = cgroup_memory(proc_root)
    if cgroup["error"]:
        errors.append("cgroup:" + cgroup["error"])
    return {
        "process_tree_rss_bytes": rss,
        "process_tree_cpu_seconds": cpu,
        "process_count": len(rows) if rows else None,
        "root_native_threads": processes.get(pid, {}).get("threads"),
        "cgroup_current_bytes": cgroup["current_bytes"],
        "cgroup_limit_bytes": cgroup["limit_bytes"],
        "inspection_seconds": perf_counter() - started,
        "observation_errors": ";".join(errors),
    }


class ResourceSession:
    """Bounded, streamed evidence; exclusive directory prevents historical overwrite."""

    def __init__(self, directory, config, *, probe=process_observation):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=False)
        self.config, self.probe = config, probe
        self.started, self.phase_name = perf_counter(), "initialization"
        self.stop = threading.Event()
        self.lock = threading.RLock()
        self.closed = False
        self.counts = {"resource": 0, "progress": 0}
        self.dropped = {"resource": 0, "progress": 0}
        self.overhead_seconds = 0.0
        self.last_solver_sample = -math.inf
        self.matrices, self.errors = [], []
        self.files, self.writers = {}, {}
        for kind, name, fields in (
            ("resource", "resource_timeseries.csv", RESOURCE_FIELDS),
            ("progress", "stage_progress.csv", PROGRESS_FIELDS),
        ):
            stream = (self.directory / name).open("w", newline="", encoding="utf-8")
            self.files[kind] = stream
            self.writers[kind] = csv.DictWriter(stream, fieldnames=fields)
            self.writers[kind].writeheader()
        packages = {}
        for name in ("gurobipy", "pyscipopt"):
            try:
                packages[name] = version(name)
            except PackageNotFoundError:
                packages[name] = None
        try:
            affinity = sorted(os.sched_getaffinity(0))
        except (OSError, AttributeError):
            affinity = None
        _json(
            self.directory / "runtime_capabilities.json",
            {
                "schema_version": "resource-runtime-v1",
                "python": platform.python_version(),
                "platform": platform.platform(),
                "packages": packages,
                "cpu_affinity": affinity,
                "solver_capabilities": "not_inferred_from_installed_packages",
                "sampling_solver_api_calls": False,
                "sample_interval_seconds": config.resource_sample_seconds,
            },
        )
        names = (
            "SLURM_JOB_ID",
            "SLURM_ARRAY_JOB_ID",
            "SLURM_ARRAY_TASK_ID",
            "SLURM_JOB_PARTITION",
            "SLURM_CPUS_PER_TASK",
            "SLURM_JOB_CPUS_PER_NODE",
            "SLURM_JOB_NODELIST",
            "SLURM_MEM_PER_NODE",
            "SLURM_MEM_PER_CPU",
        )
        _json(
            self.directory / "allocation_receipt.json",
            {
                "schema_version": "resource-allocation-v1",
                "environment_observations": {name: os.environ.get(name) for name in names},
                "cgroup": cgroup_memory(),
                "qualification": (
                    "Observed environment, not an authenticated Slurm allocation record."
                ),
                "effective_parallelism": "not_inferred_from_allocated_cpus_or_thread_ceilings",
            },
        )
        self.sample()
        self.thread = threading.Thread(
            target=self._loop, name="agrologistic-os-sampler", daemon=True
        )
        self.thread.start()

    def _write(self, kind, row):
        with self.lock:
            if self.closed:
                return
            if self.counts[kind] >= self.config.resource_max_samples:
                self.dropped[kind] += 1
                return
            self.writers[kind].writerow(row)
            self.files[kind].flush()
            self.counts[kind] += 1

    def sample(self):
        started = perf_counter()
        try:
            row = self.probe()
            self._write(
                "resource",
                {"elapsed_seconds": perf_counter() - self.started, "phase": self.phase_name, **row},
            )
        except Exception as exc:
            with self.lock:
                if len(self.errors) < 20:
                    self.errors.append(type(exc).__name__)
        finally:
            self.overhead_seconds += perf_counter() - started

    def _loop(self):
        while not self.stop.wait(self.config.resource_sample_seconds):
            self.sample()

    def event(self, event, **values):
        self._write(
            "progress",
            {
                "elapsed_seconds": perf_counter() - self.started,
                "phase": self.phase_name,
                "event": event,
                **{k: v for k, v in values.items() if k in PROGRESS_FIELDS},
            },
        )

    def phase(self, name):
        self.phase_name = name
        self.event("phase_boundary")
        self.sample()

    def matrix(self, scope, **values):
        if len(self.matrices) < 100:
            self.matrices.append({"scope": scope, "phase": self.phase_name, **values})

    def finish(self, status, *, exception=None):
        if self.closed:
            return
        self.stop.set()
        self.thread.join()
        self.sample()
        self.event("execution_end", status=status)
        with self.lock:
            self.closed = True
            for stream in self.files.values():
                stream.close()
        _json(
            self.directory / "matrix_statistics.json",
            {
                "schema_version": "resource-matrix-v1",
                "observations": self.matrices,
                "qualification": (
                    "Missing fields are unavailable; no presolved model copy is created."
                ),
            },
        )
        _json(
            self.directory / "termination.json",
            {
                "schema_version": "resource-termination-v1",
                "execution_status": status,
                "exception_type": exception,
                "elapsed_seconds": perf_counter() - self.started,
                "sampler_work_seconds": self.overhead_seconds,
                "samples": self.counts,
                "dropped_samples": self.dropped,
                "inspection_errors": self.errors,
                "quality_acceptance": "requires_independent_validation_and_stage_certificates",
            },
        )
        from src.logic.run_integrity import file_sha256

        _json(
            self.directory / "manifest.json",
            {
                "schema_version": "resource-manifest-v1",
                "status": "closed",
                "artifacts": {name: file_sha256(self.directory / name) for name in PRODUCTS[:-1]},
            },
        )


def phase(name):
    if (session := CURRENT.get()) is not None:
        session.phase(name)


def event(name, **values):
    if (session := CURRENT.get()) is not None:
        session.event(name, **values)


def observed_matrix(model, backend, scope="original"):
    session = CURRENT.get()
    if session is None:
        return
    if backend == "gurobipy":
        model.update()
        fields = {
            "variables": "NumVars",
            "binary_variables": "NumBinVars",
            "integer_variables": "NumIntVars",
            "constraints": "NumConstrs",
            "nonzeros": "DNumNZs",
            "general_constraints": "NumGenConstrs",
            "coefficient_min": "MinCoeff",
            "coefficient_max": "MaxCoeff",
        }
        values = {}
        for name, attr in fields.items():
            try:
                values[name] = _number(getattr(model, attr))
            except (AttributeError, RuntimeError):
                values[name] = None
        values["integer_count_semantics"] = "includes_binary"
    else:
        values = {
            "variables": model.getNVars(),
            "binary_variables": model.getNBinVars(),
            "integer_variables": model.getNIntVars() + model.getNBinVars(),
            "implicit_integer_variables": model.getNImplVars(),
            "integer_count_semantics": "includes_binary_excludes_implicit_integer",
            "constraints": model.getNConss(),
            "nonzeros": None,
            "coefficient_min": None,
            "coefficient_max": None,
        }
    session.matrix(scope, backend=backend, **values)


def gurobi_message(model, where, callback, session=None):
    """Bounded matrix/phase log observations on the solver's callback thread."""
    session = session if session is not None else CURRENT.get()
    if session is None:
        return
    if where != getattr(callback, "MESSAGE", None):
        now = perf_counter()
        if now - session.last_solver_sample < session.config.resource_sample_seconds:
            return
        kind = next(
            (
                name
                for name in ("MIP", "SIMPLEX", "BARRIER", "PRESOLVE")
                if where == getattr(callback, name, None)
            ),
            None,
        )
        if kind is None:
            return
        session.last_solver_sample = now

        def query(name):
            try:
                return _number(model.cbGet(getattr(callback, name)))
            except Exception:
                return None

        values = {"solver_memory_bytes": query("MEMUSED")}
        if values["solver_memory_bytes"] is not None:
            values["solver_memory_bytes"] *= 1e9  # Gurobi decimal GB, not process RSS.
        if kind == "MIP":
            values.update(
                incumbent=query("MIP_OBJBST"),
                bound=query("MIP_OBJBND"),
                iterations=query("MIP_ITRCNT"),
                nodes=query("MIP_NODCNT"),
            )
        elif kind in {"SIMPLEX", "BARRIER"}:
            values["iterations"] = query("SPX_ITRCNT" if kind == "SIMPLEX" else "BARRIER_ITRCNT")
        session.event(kind, **values)
        return
    message = model.cbGet(callback.MSG_STRING)
    if match := re.search(r"optimize objective (\d+)", message):
        session.phase("optimization_stage_" + match[1])
    if match := re.search(r"Presolved: (\d+) rows, (\d+) columns, (\d+) nonzeros", message):
        session.matrix(
            "presolved_log",
            backend="gurobipy",
            constraints=int(match[1]),
            variables=int(match[2]),
            nonzeros=int(match[3]),
        )


def install_scip_events(model):
    """Native solve events only; no unsupported in-progress LP bound is inferred."""
    session = CURRENT.get()
    if session is None:
        return
    from pyscipopt import SCIP_EVENTTYPE, Eventhdlr

    mask = (
        SCIP_EVENTTYPE.LPSOLVED
        | SCIP_EVENTTYPE.BESTSOLFOUND
        | SCIP_EVENTTYPE.NODEFOCUSED
        | SCIP_EVENTTYPE.DUALBOUNDIMPROVED
    )

    class Progress(Eventhdlr):
        def eventinit(self):
            self.model.catchEvent(mask, self)

        def eventexit(self):
            self.model.dropEvent(mask, self)

        def eventexec(self, ev):
            now = perf_counter()
            if now - session.last_solver_sample < session.config.resource_sample_seconds:
                return
            session.last_solver_sample = now
            try:
                infinite = self.model.infinity()
                incumbent, bound = self.model.getPrimalbound(), self.model.getDualbound()
                session.event(
                    "SCIP_NATIVE_EVENT",
                    incumbent=incumbent if abs(incumbent) < infinite else None,
                    bound=bound if abs(bound) < infinite else None,
                    iterations=self.model.getNLPIterations(),
                    nodes=self.model.getNNodes(),
                    solver_memory_bytes=self.model.getMemUsed(),
                )
            except Exception as exc:
                if len(session.errors) < 20:
                    session.errors.append("scip_event:" + type(exc).__name__)

    model.includeEventhdlr(Progress(), "resource_progress", "Bounded native resource events")


def resource_run(function):
    @wraps(function)
    def wrapped(spec, output_root, **kwargs):
        if not spec.solver.collect_resource_diagnostics:
            return function(spec, output_root, **kwargs)
        session = ResourceSession(
            Path(output_root).resolve() / spec.name / "resources", spec.solver
        )
        token = CURRENT.set(session)
        try:
            result = function(spec, output_root, **kwargs)
            session.finish(result.status)
            return result
        except BaseException as exc:
            session.finish("exception", exception=type(exc).__name__)
            raise
        finally:
            CURRENT.reset(token)

    return wrapped
