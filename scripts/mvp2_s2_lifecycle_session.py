"""Fixed normal worker/session components; no public execution or live default.

Effects are explicit qualification dependencies. No native solver, fork tree,
license, environment switch or old claim loader is reachable from the CLI.
"""

from __future__ import annotations

if __name__ == "__main__":
    raise PermissionError("Lifecycle worker/session execution remains blocked.")

import copy
import ctypes
import os
import socket
import sys
import time
from pathlib import Path

from scripts import mvp2_s2_lifecycle_adapter as m
from scripts import mvp2_s2_synthetic_worker as worker

e, lc, s, q, a = m.e, m.lc, m.s, m.q, m.a


def execute(*_args, **_kwargs):
    raise PermissionError("Lifecycle worker/session execution remains blocked.")


def release_token(spec, manifest_sha256, item):
    """Bound wire value, never a transferable execution-admission capability."""
    return {
        "schema_version": "s2-lifecycle-wire-release-v1",
        "source_commit": spec["source_commit"],
        "job_id": spec["job_id"],
        "nonce": spec["nonce"],
        "manifest_sha256": manifest_sha256,
        "contract_sha256": s.digest(item),
        **lc.FLAGS,
    }


def linux_prctl(option, value, arg3, arg4, arg5):
    """Explicit future worker-only primitive; never selected or called by CLI."""
    s.require(
        (option, value, arg3, arg4, arg5) in {(38, 1, 0, 0, 0), (39, 0, 0, 0, 0)},
        "Only fixed no_new_privs SET/GET is qualified.",
    )
    libc = e._libc()
    libc.prctl.argtypes = [ctypes.c_int, *([ctypes.c_ulong] * 4)]
    libc.prctl.restype = ctypes.c_int
    return libc.prctl(option, value, arg3, arg4, arg5)


class WorkerChannel:
    """Explicit Linux local IPC bridge with a single bounded connect/exchange."""

    def __init__(self, path):
        s.require(sys.platform == "linux", "Linux IPC required.")
        path = Path(path)
        q._safe_path(path)
        s.require(len(os.fsencode(path)) <= 100, "IPC path bound.")
        self.path, self.connection = path, None

    def connect(self, remaining):
        s.require(self.connection is None and 0 < remaining <= 30, "Repeated/late connection.")
        self.connection = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.connection.settimeout(remaining)
        self.connection.connect(str(self.path))
        return e.KernelReader().peer(self.connection)

    def exchange(self, handshake, remaining):
        s.require(self.connection is not None and 0 < remaining <= 30, "IPC exchange deadline.")
        data = q.c.encoded(handshake)
        s.require(len(data) <= 4096, "Handshake byte bound.")
        deadline = time.monotonic() + remaining
        self.connection.settimeout(remaining)
        s.require(self.connection.send(data) == len(data), "Incomplete handshake.")
        remaining = deadline - time.monotonic()
        s.require(remaining > 0, "Handshake exhausted startup budget.")
        self.connection.settimeout(remaining)
        data = self.connection.recv(4097)
        s.require(len(data) <= 4096, "Release byte bound.")
        return q.c.decode_json(data)

    def close(self):
        if self.connection is not None:
            self.connection.close()


def exercise_normal(spec, item):
    """Fixed stdlib phases only; no linger, nested factory or arbitrary command."""
    s.require(spec["case"] == "normal", "Only normal worker qualified.")

    def no_nested():
        raise PermissionError("Adverse tree remains closed.")

    return worker.exercise_components(
        "normal",
        Path(spec["run"]) / "worker",
        spec["nonce"],
        release=lambda: True,
        nested_factory=no_nested,
    )


def worker_components(
    spec, manifest, manifest_sha256, item, supervisor, *, channel, prctl, clock, affinity, exercise
):
    """Full worker ordering with explicit effects; standalone route still denies.

    The supervisor independently verifies the environment before replying. Worker
    phases cannot precede source/security/peer/token/deadline checks.
    """
    spec, manifest, item = m.validate_identity_inputs(spec, manifest, manifest_sha256, item)
    supervisor = lc.stable(supervisor)
    s.require(all(callable(v) for v in (clock, affinity, exercise)), "Explicit worker effects.")
    started = clock()

    def remaining():
        now = clock()
        s.require(started <= now < started + 30, "Worker startup deadline/rollback.")
        return started + 30 - now

    try:
        handshake = m.worker_components(spec, manifest, manifest_sha256, item, prctl=prctl)
        initial = affinity()
        s.require(
            type(initial) is list
            and len(initial) == 1
            and type(initial[0]) is int
            and initial[0] >= 0,
            "Initial single logical CPU affinity required; no implicit affinity writes.",
        )
        peer = channel.connect(remaining())
        s.require(
            peer["pid"] == supervisor["pid"] and peer["uid"] == supervisor["uid"],
            "Unexpected kernel supervisor peer.",
        )
        token = channel.exchange(handshake, remaining())
        s.require(token == release_token(spec, manifest_sha256, item), "Unbound IPC release.")
        remaining()
        m.verify_current(spec, manifest, manifest_sha256, item, role="worker")
        remaining()
        exercise(spec, item)
        return {"status": "normal_components_completed_not_cleanup", **lc.FLAGS}
    finally:
        channel.close()


def launch_arguments(spec, manifest_sha256, item):
    """Existing allocation, fixed worker entry and original synthetic request."""
    spec = a.validate_spec(spec)
    return (
        spec["tools"]["srun"],
        "--jobid=" + spec["job_id"],
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
        *m.worker_arguments(spec, manifest_sha256, item),
    )


def launch_components(value, *, kernel, queries, record_once, spawn):
    """Allocation/source checks and durable one-shot intent before a fixed spawn.

    No default spawn is provided. An exception after intent consumes the attempt,
    even if process creation may have happened; never guess a PID or retry.
    """
    from scripts import mvp2_s2_lifecycle_release as r

    value = r.validate(value)
    spec, item = value["specification"], value["contract"]
    s.require(
        spec["job_id"] != "1" and callable(record_once) and callable(spawn),
        "Acknowledged release and explicit effects required.",
    )
    m.verify_current(spec, value["manifest"], value["manifest_sha256"], item)
    supervisor = kernel.process(kernel.self_pid())
    allocation = a.review_allocation(
        queries.query("allocation"), spec["job_id"], supervisor["identity"]["uid"], kernel.node()
    )
    argv = launch_arguments(spec, value["manifest_sha256"], item)
    record_once(
        "launcher-intent.json",
        {
            "release_sha256": s.digest(value),
            "argv_sha256": s.digest(argv),
            "allocation_sha256": s.digest(allocation),
            **lc.FLAGS,
        },
    )
    try:
        m.verify_current(spec, value["manifest"], value["manifest_sha256"], item)
        handle = spawn(argv)
        process = getattr(handle, "process", handle)
        s.require(
            type(process.pid) is int and process.pid > 0 and callable(process.poll),
            "Owned local launcher receipt required.",
        )
        record_once(
            "launcher-result.json",
            {"pid": process.pid, "status": "owned_client_not_cleanup", **lc.FLAGS},
        )
        return {
            "handle": handle,
            "process": process,
            "status": "software_launcher_preserved_not_admitted",
            **lc.FLAGS,
        }
    except (Exception, KeyboardInterrupt):
        record_once("launcher-unknown.json", {"status": "unknown_effect_no_retry", **lc.FLAGS})
        return {"handle": None, "process": None, "status": "unknown_effect_no_retry", **lc.FLAGS}


class EffectsTransport(a.RealTransport):
    """Explicit fixed future effects; no factory/default/public dispatch selects it."""

    def spawn_components(self, manifest_sha256, item):
        s.require(not self.launched, "One local launcher only.")
        self.launched = True  # Unknown spawn consumes the attempt before the call.
        return self._open(launch_arguments(self.item, manifest_sha256, item))

    def signal_components(self, binding, name):
        binding = s.binding(binding)
        s.require(
            binding["job_id"] == self.item["job_id"]
            and binding["worker_step_id"] == self.bound_step
            and name in {"TERM", "KILL"}
            and name not in self.signals
            and (name == "TERM" or "TERM" in self.signals)
            and self.rpcs < a.MAX_RPC,
            "Unbound/repeated exact-step signal.",
        )
        self.signals.add(name)
        self.rpcs += 1
        argv = (
            self.item["tools"]["scancel"],
            "--signal=" + name,
            binding["job_id"] + "." + binding["worker_step_id"],
        )
        return self._open(argv).query_result(1, 65536)


class ControlledSession:
    """Durable one-shot release/stop wiring around the independent adapter.

    Every effect is injected, journaled before invocation and never retried after
    unknown acknowledgement. There is no terminal-accounting cleanup shortcut.
    """

    def __init__(self, adapter, *, record_once, signal, stop_latched):
        s.require(
            all(callable(v) for v in (record_once, signal, stop_latched)), "Explicit effects."
        )
        self.adapter, self.record_once, self.signal, self.stop_latched = (
            adapter,
            record_once,
            signal,
            stop_latched,
        )
        self.events, self.used = [], set()
        self.released, self.failed = False, False
        self.term_at = None

    def _record(self, name, value):
        s.require(name not in self.used and len(self.events) < 16, "Repeated effect record.")
        self.used.add(name)
        event = {
            "name": name,
            "value": copy.deepcopy(value),
            "previous_sha256": s.digest(self.events[-1])
            if self.events
            else s.digest(self.adapter.item),
        }
        self.record_once(name + ".json", event)  # Durable before any IPC/signal effect.
        self.events.append(event)

    def _bound(self):
        adapter = self.adapter
        s.require(adapter.original is not None, "No exact-step signal authority before binding.")
        return adapter.original["boundary"]["binding"]

    def release_components(self, server):
        adapter = self.adapter
        s.require(
            not self.released
            and not self.failed
            and "release-intent" not in self.used
            and "stop-latched" not in self.used
            and not self.stop_latched()
            and not adapter.terminal
            and adapter.original is not None
            and adapter.protocol.state == "running",
            "Release blocked or already consumed.",
        )
        token = release_token(adapter.spec, adapter.manifest_sha256, adapter.item)
        self._record(
            "release-intent",
            {"token": token, "barrier_sha256": s.digest(adapter.protocol.journal), **lc.FLAGS},
        )
        try:
            m.verify_current(adapter.spec, adapter.manifest, adapter.manifest_sha256, adapter.item)
            remaining = 30 - adapter.clock()
            s.require(0 < remaining <= 30 and not self.stop_latched(), "Late/latched release.")
            server.release(token, remaining)
            self.released = True
            self._record("release-result", {"status": "sent_not_admitted", **lc.FLAGS})
        except (Exception, KeyboardInterrupt):
            self.failed = True
            self._record("release-unknown", {"status": "unknown_effect_no_retry", **lc.FLAGS})
        return self.receipt()

    def stop_components(self, *, reason):
        s.require(
            reason in {"operator_stop", "observation_failure", "exercise_deadline"},
            "Fixed stop reason required.",
        )
        adapter = self.adapter
        now = adapter.clock()
        s.require(0 <= now < 660, "Global deadline; preserve blocked, no late effect.")
        if "stop-latched" not in self.used:
            self._record("stop-latched", {"reason": reason, "seconds": now, **lc.FLAGS})
        if adapter.original is None:
            return self.receipt()  # Never guess a step or cancel an entire job.
        if self.term_at is not None:
            s.require(now - self.term_at < 390, "Cleanup deadline precedes signal.")
        name = "TERM" if self.term_at is None else "KILL"
        if name == "KILL" and (now - self.term_at < 5 or "signal-KILL-intent" in self.used):
            return self.receipt()
        binding = self._bound()
        self._record("signal-" + name + "-intent", {"binding": binding, "seconds": now, **lc.FLAGS})
        if name == "TERM":
            self.term_at = now
        try:
            m.verify_current(adapter.spec, adapter.manifest, adapter.manifest_sha256, adapter.item)
            uid = adapter.original["boundary"]["worker"]["uid"]
            node = adapter.frames[0]["candidate"]["node"]
            a.review_allocation(adapter.queries.query("allocation"), binding["job_id"], uid, node)
            step_binding = {
                k: binding[k]
                for k in (
                    "job_id",
                    "worker_step_id",
                    "supervisor_step_id",
                    "nonce",
                    "source_commit",
                )
            }
            a.review_step(adapter.queries.query("step"), step_binding, uid, node)
            current = adapter.kernel.process(
                adapter.original["boundary"]["worker"]["pid"], protected=True
            )
            s.require(
                lc.stable(current["identity"]) == lc.stable(adapter.original["boundary"]["worker"]),
                "Exact worker process identity drift before signal.",
            )
            s.require(adapter.kernel.host() == adapter.original["host"], "Host profile drift.")
            e.protected_process(current, adapter.original["host"])
            s.require(
                all(
                    current["scopes"][key]
                    == {"mount": descriptor["mount"], "scope": descriptor["worker"]}
                    for key, descriptor in adapter.original["boundary"]["controllers"].items()
                ),
                "Worker enforcement scope drift before signal.",
            )
            at = adapter.clock()
            s.require(at < 660 and at - self.term_at < 390, "Signal/cleanup deadline exhausted.")
            self.signal(step_binding, name)
            self._record(
                "signal-" + name + "-result", {"status": "acknowledged_not_cleanup", **lc.FLAGS}
            )
        except (Exception, KeyboardInterrupt):
            self.failed = True
            self._record(
                "signal-" + name + "-unknown", {"status": "unknown_effect_no_retry", **lc.FLAGS}
            )
        return self.receipt()

    def observe_components(self, reader):
        s.require(self.released and not self.failed, "No observations before a known release.")
        result = self.adapter.observe_components(reader)
        if result["failures"] or result["protocol"]["state"] == "blocked" or self.stop_latched():
            self.stop_components(reason="observation_failure")
        return self.receipt()

    def run_components(self, server, candidate, reader, *, sleep):
        """One bounded complete normal sequence; effects/clock are explicit."""
        s.require(callable(sleep), "Explicit bounded wait required.")
        try:
            self.adapter.prepare_components(server, candidate)
            if self.adapter.original is None:
                return self.receipt()
            self.release_components(server)
            if self.failed:
                return self.stop_components(reason="observation_failure")
            for _ in range(660):
                s.require(self.adapter.clock() < 660, "Global supervision deadline.")
                if self.stop_latched():
                    self.stop_components(reason="operator_stop")
                result = self.observe_components(reader)
                if self.failed or self.adapter.terminal:
                    return result
                sleep(1)
            raise ValueError("Bounded supervision iterations exhausted.")
        except (Exception, KeyboardInterrupt):
            self.failed = True
            if self.adapter.original is not None and self.adapter.clock() < 660:
                self.stop_components(reason="observation_failure")
            return self.receipt()
        finally:
            server.close()

    def receipt(self):
        return {
            "schema_version": "s2-lifecycle-session-review-v1",
            "events": copy.deepcopy(self.events),
            "release_sent_not_admitted": self.released,
            "unknown_effect": self.failed,
            "adapter": self.adapter.receipt(),
            **lc.FLAGS,
        }
