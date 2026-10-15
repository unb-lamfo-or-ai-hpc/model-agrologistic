"""Closed operational lifecycle integration and independently replayed forensics.

All public execution/worker/claim entries deny. Internal components can perform
explicit read-only kernel/RPC observations; they never spawn/release/signal a
worker, submit a job, create a claim or rewrite original evidence.
"""

from __future__ import annotations

if __name__ == "__main__":
    raise PermissionError("Lifecycle operational execution remains closed.")

import copy

from scripts import mvp2_s2_compute_identity as identity
from scripts import mvp2_s2_environment as e

lc, q, s, a, package = e.lc, e.q, e.s, e.a, e.package
ENTRY = "scripts/mvp2_s2_lifecycle_adapter.py"
WORKER_ENTRY = "scripts/mvp2_s2_lifecycle_session.py"
CLOSURE = package.CLOSURE | {
    ENTRY,
    "scripts/mvp2_s2_environment.py",
    "scripts/mvp2_s2_compute_identity.py",
    "scripts/mvp2_s2_resource_normal.py",
    WORKER_ENTRY,
    "scripts/mvp2_s2_lifecycle_release.py",
    "scripts/mvp2_s2_lifecycle_transfer.py",
    "scripts/npad_s2_lifecycle_normal.sh",
}
METHODS = {
    "process",
    "host",
    "descriptor",
    "hierarchy",
    "inventory",
    "resources",
    "mountinfo",
    "anchors",
    "absence",
    "step_status",
    "self_pid",
}
LIMIT = 16 * 1024**2


def execute(*_args, **_kwargs):
    raise PermissionError("Lifecycle operational execution remains closed.")


def validate_identity_inputs(spec, manifest, manifest_sha256, item):
    spec, item = a.validate_spec(spec), lc.validate_contract(item)
    manifest = identity.validate_manifest(manifest, spec["source_commit"], manifest_sha256)
    legacy = item["resource_contract"]["legacy_contract"]
    s.require(
        spec["case"] == legacy["case"] == "normal"
        and legacy["binding"]["job_id"] == spec["job_id"]
        and legacy["binding"]["nonce"] == spec["nonce"]
        and legacy["binding"]["source_commit"] == spec["source_commit"]
        and legacy["source_sha256"] == manifest["source"]["source_sha256"]
        and legacy["worker_sha256"] == manifest["source"]["worker_sha256"]
        and CLOSURE <= manifest["files"].keys(),
        "Current source/contract/specification closure drift.",
    )
    return spec, manifest, item


def verify_current(spec, manifest, manifest_sha256, item, *, role="batch"):
    spec, manifest, _item = validate_identity_inputs(spec, manifest, manifest_sha256, item)
    source = identity.verify_compute_source(
        spec["checkout"], manifest, spec["source_commit"], manifest_sha256
    )
    runtime = identity.verify_compute_runtime(spec, role)
    return {"source": source, "runtime": runtime, "manifest_sha256": manifest_sha256}


def worker_arguments(spec, manifest_sha256, item):
    return [
        spec["python"],
        "-B",
        "-I",
        spec["checkout"] + "/" + WORKER_ENTRY,
        "worker",
        "--manifest-sha",
        manifest_sha256,
        "--contract-sha",
        s.digest(item),
    ]


def worker_components(spec, manifest, manifest_sha256, item, *, prctl):
    """Qualified future preparation, not a worker entry or IPC release."""
    proof = verify_current(spec, manifest, manifest_sha256, item, role="worker")
    hardened = e.harden_worker_components(prctl)
    return {
        "schema_version": "s2-lifecycle-handshake-v1",
        "source_commit": spec["source_commit"],
        "job_id": spec["job_id"],
        "worker_step_id": item["resource_contract"]["legacy_contract"]["binding"]["worker_step_id"],
        "nonce": spec["nonce"],
        "manifest_sha256": manifest_sha256,
        "contract_sha256": s.digest(item),
        "runtime": proof["runtime"],
        "hardening": hardened,
    }


class FixedQueries:
    """Read-only subset of an explicit transport; no submit/launch/signal method."""

    def __init__(self, spec, binding, transport):
        self.spec = a.validate_spec(spec)
        self.binding = s.binding(binding)
        s.require(callable(getattr(transport, "command", None)), "Explicit RPC transport required.")
        self.transport, self.calls = transport, 0

    def query(self, kind):
        spec, job = self.spec, self.binding["job_id"]
        target = job + "." + self.binding["worker_step_id"]
        commands = {
            "allocation": (spec["tools"]["scontrol"], "-o", "show", "job", job),
            "step": (spec["tools"]["scontrol"], "-o", "show", "step", target),
            "worker_members": (spec["tools"]["scontrol"], "listpids", target),
            "batch_members": (
                spec["tools"]["scontrol"],
                "listpids",
                job + "." + a.BATCH_QUERY_STEP,
            ),
            "accounting": (
                spec["tools"]["sacct"],
                "--noheader",
                "--parsable2",
                "--jobs=" + job,
                "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw",
            ),
        }
        s.require(kind in commands and self.calls < 1024, "Fixed query/count bound.")
        self.calls += 1
        result = self.transport.command(commands[kind], timeout_seconds=1, max_output_bytes=65536)
        s.require(type(result) is str and len(result.encode()) <= 65536, "RPC output bound.")
        return result


class RecordedKernel:
    def __init__(self, kernel):
        s.require(type(kernel.fixture) is bool, "Observation provenance required.")
        self.kernel, self.fixture, self.records = kernel, kernel.fixture, []

    def __getattr__(self, name):
        s.require(name in METHODS, "Kernel method not qualified.")

        def call(*args, **kwargs):
            s.require(len(self.records) < 512, "Kernel observation count bound.")
            record = {
                "method": name,
                "args": copy.deepcopy(list(args)),
                "kwargs": copy.deepcopy(kwargs),
                "value": None,
                "error_kind": None,
            }
            try:
                value = getattr(self.kernel, name)(*args, **kwargs)
            except (OSError, ValueError, UnicodeError, KeyError, TypeError, IndexError):
                record["error_kind"] = "read_invalid_or_unavailable"
                self.records.append(record)
                raise
            record["value"] = copy.deepcopy(value)
            self.records.append(record)
            return value

        return call


class ReplayKernel:
    def __init__(self, records, fixture):
        s.require(
            type(records) is list and len(records) <= 512 and type(fixture) is bool,
            "Kernel replay bound/provenance.",
        )
        self.records, self.fixture, self.index = records, fixture, 0

    def __getattr__(self, name):
        s.require(name in METHODS, "Replay method not qualified.")

        def call(*args, **kwargs):
            s.require(self.index < len(self.records), "Missing kernel observation.")
            record = self.records[self.index]
            q._keys(record, {"method", "args", "kwargs", "value", "error_kind"})
            s.require(
                record["method"] == name
                and record["args"] == list(args)
                and record["kwargs"] == kwargs,
                "Kernel replay request drift.",
            )
            self.index += 1
            if record["error_kind"] is not None:
                s.require(
                    record["error_kind"] == "read_invalid_or_unavailable"
                    and record["value"] is None,
                    "Kernel error grammar.",
                )
                raise ValueError("Recorded unavailable kernel evidence.")
            return copy.deepcopy(record["value"])

        return call


def prepare_frame(item, candidate, kernel, scheduler, *, initial_affinity=None):
    recording = RecordedKernel(kernel)
    error_site = None
    try:
        result = e.collect_environment(
            item, candidate, recording, scheduler, initial_affinity=initial_affinity
        )
    except (OSError, ValueError, UnicodeError, KeyError, TypeError, IndexError) as error:
        result = None
        error_site = error.site if isinstance(error, e.EvidenceError) else "kernel_read_or_schema"
    frame = {
        "schema_version": "s2-environment-frame-v1",
        "candidate": copy.deepcopy(candidate),
        "scheduler": copy.deepcopy(scheduler),
        "kernel": recording.records,
        "fixture": recording.fixture,
        "initial_affinity": initial_affinity,
        "result": result,
        "error_site": error_site,
    }
    s.require(len(q.c.encoded(frame)) <= LIMIT, "Environment frame byte bound.")
    return frame


def replay_frame(item, frame):
    q._keys(
        frame,
        {
            "schema_version",
            "candidate",
            "scheduler",
            "kernel",
            "fixture",
            "initial_affinity",
            "result",
            "error_site",
        },
    )
    s.require(
        frame["schema_version"] == "s2-environment-frame-v1" and len(q.c.encoded(frame)) <= LIMIT,
        "Environment frame grammar/bound.",
    )
    reader = ReplayKernel(frame["kernel"], frame["fixture"])
    error_site = None
    try:
        result = e.collect_environment(
            item,
            frame["candidate"],
            reader,
            frame["scheduler"],
            initial_affinity=frame["initial_affinity"],
        )
    except (OSError, ValueError, UnicodeError, KeyError, TypeError, IndexError) as error:
        result = None
        error_site = error.site if isinstance(error, e.EvidenceError) else "kernel_read_or_schema"
    s.require(
        reader.index == len(reader.records)
        and result == frame["result"]
        and error_site == frame["error_site"],
        "Environment replay tail/result drift.",
    )
    return result


def observation_inputs(
    item, original, kernel, rows, products, writes, known, launcher_reaped, current_running
):
    binding = item["resource_contract"]["legacy_contract"]["binding"]
    target = binding["job_id"] + "." + binding["worker_step_id"]
    row = rows.get(target)
    leader = kernel.absence(original["boundary"]["worker"])
    ended = current_running and (
        (row is not None and row["state"] in a.TERMINAL) or leader == "absent"
    )
    running = current_running and not ended
    inventories, resources = e.refresh(item, original, kernel, running=running)
    steps = kernel.step_status(original["boundary"]["controllers"])
    packet = {
        "inventories": inventories,
        "resources": resources,
        "step_scopes": steps,
        "accounting": {"job_step": target, "state": row["state"], "exit_code": row["exit_code"]}
        if row
        else None,
        "absence": {
            s.digest(value): kernel.absence({**value, "state": "S"}) for value in known.values()
        },
        "launcher_reaped": launcher_reaped,
        "products": products,
        "writes": writes,
        "assurance_sha256": s.digest(original["boundary"]["assurance"]),
    }
    return {
        "transition_to_cleanup": ended,
        "accounting_pending": not running and (row is None or row["state"] not in a.TERMINAL),
        "packet": packet,
    }


def capture_observation(
    item, original, kernel, rows, products, writes, known, launcher_reaped, current_running
):
    reader, error_site, result = RecordedKernel(kernel), None, None
    try:
        result = observation_inputs(
            item, original, reader, rows, products, writes, known, launcher_reaped, current_running
        )
    except (OSError, ValueError, UnicodeError, KeyError, TypeError, IndexError) as error:
        error_site = error.site if isinstance(error, e.EvidenceError) else "kernel_read_or_schema"
    value = {
        "schema_version": "s2-independent-observation-v1",
        "kernel": reader.records,
        "fixture": reader.fixture,
        "rows": copy.deepcopy(rows),
        "products": copy.deepcopy(products),
        "writes": copy.deepcopy(writes),
        "known": copy.deepcopy(known),
        "launcher_reaped": launcher_reaped,
        "current_running": current_running,
        "result": result,
        "error_site": error_site,
    }
    s.require(len(q.c.encoded(value)) <= LIMIT, "Observation frame bound.")
    return value


def replay_observation(item, original, frame):
    q._keys(
        frame,
        {
            "schema_version",
            "kernel",
            "fixture",
            "rows",
            "products",
            "writes",
            "known",
            "launcher_reaped",
            "current_running",
            "result",
            "error_site",
        },
    )
    s.require(
        frame["schema_version"] == "s2-independent-observation-v1"
        and len(q.c.encoded(frame)) <= LIMIT,
        "Observation frame grammar/bound.",
    )
    reader, result, error_site = ReplayKernel(frame["kernel"], frame["fixture"]), None, None
    # JSON turns integer registry keys into strings; normalize and check values.
    known = {value["pid"]: value for value in frame["known"].values()}
    s.require(len(known) == len(frame["known"]), "Registry alias.")
    try:
        result = observation_inputs(
            item,
            original,
            reader,
            frame["rows"],
            frame["products"],
            frame["writes"],
            known,
            frame["launcher_reaped"],
            frame["current_running"],
        )
    except (OSError, ValueError, UnicodeError, KeyError, TypeError, IndexError) as error:
        error_site = error.site if isinstance(error, e.EvidenceError) else "kernel_read_or_schema"
    s.require(
        reader.index == len(reader.records)
        and result == frame["result"]
        and error_site == frame["error_site"],
        "Observation replay tail/result drift.",
    )
    return result


class OperationalAdapter:
    """Independent verifier runs before the software barrier and every observation.

    No live defaults or IPC send. Caller cannot pass a preapproved assurance JSON
    to bypass kernel/scheduler/source checks. Fake backends remain fixture-labelled.
    """

    def __init__(self, spec, manifest, manifest_sha256, item, *, kernel, queries, clock, launcher):
        self.spec, self.manifest, self.item = validate_identity_inputs(
            spec, manifest, manifest_sha256, item
        )
        s.require(
            callable(clock) and callable(getattr(launcher, "poll", None)),
            "Explicit clock/owned launcher observer required.",
        )
        self.manifest_sha256, self.kernel, self.queries = manifest_sha256, kernel, queries
        self.clock, self.launcher = clock, launcher
        self.protocol, self.frames, self.failures = lc.Protocol(item), [], []
        self.observations = []
        self.original = None
        self.terminal = False
        self.evidence_bytes = 0

    def launch(self):
        execute()

    def _failure(self, phase):
        self.terminal = True
        self.failures.append({"phase": phase, "error_kind": "invalid_or_unavailable_evidence"})
        return self.receipt()

    def _store(self, frame, target):
        size = len(q.c.encoded(frame))
        s.require(
            self.evidence_bytes + size <= 32 * 1024**2 and len(target) < 1024,
            "Cumulative evidence memory bound.",
        )
        self.evidence_bytes += size
        target.append(frame)

    def prepare_components(self, server, candidate):
        s.require(not self.terminal and self.original is None, "Repeated/terminal preparation.")
        phase = "source_runtime"
        try:
            proof = verify_current(self.spec, self.manifest, self.manifest_sha256, self.item)
            phase = "ipc_receive"
            remaining = 30 - self.clock()
            s.require(0 < remaining <= 30, "IPC startup deadline.")
            handshake, accepted_peer = server.accept(remaining)
            q._keys(
                handshake,
                {
                    "schema_version",
                    "source_commit",
                    "job_id",
                    "worker_step_id",
                    "nonce",
                    "manifest_sha256",
                    "contract_sha256",
                    "runtime",
                    "hardening",
                },
            )
            binding = self.item["resource_contract"]["legacy_contract"]["binding"]
            s.require(
                handshake["schema_version"] == "s2-lifecycle-handshake-v1"
                and all(
                    handshake[k] == binding[k]
                    for k in ("source_commit", "job_id", "worker_step_id", "nonce")
                )
                and handshake["manifest_sha256"] == self.manifest_sha256
                and handshake["contract_sha256"] == s.digest(self.item)
                and handshake["runtime"] == identity.expected_compute_runtime(self.spec, "worker")
                and handshake["hardening"]
                == {
                    "schema_version": "s2-worker-hardening-components-v1",
                    "no_new_privs_checked": True,
                    **lc.FLAGS,
                },
                "Unbound worker handshake.",
            )
            phase = "kernel_peer"
            peer = self.kernel.peer(server.peer)
            s.require(
                peer["pid"] == candidate["worker_pid"]
                and accepted_peer == {key: peer[key] for key in ("pid", "uid")},
                "Kernel peer PID/UID drift.",
            )
            scheduler = {
                kind: self.queries.query(kind)
                for kind in ("allocation", "step", "worker_members", "batch_members")
            }
            phase = "first_environment"
            first = prepare_frame(self.item, candidate, self.kernel, scheduler)
            self._store(first, self.frames)
            observed = first["result"]
            s.require(observed is not None, "Environment unsupported or unavailable.")
            s.require(
                peer["uid"] == observed["boundary"]["worker"]["uid"], "Kernel peer UID drift."
            )
            phase = "worker_and_launcher_identity"
            process = self.kernel.process(peer["pid"], protected=True)
            s.require(
                process["executable"] == self.spec["python"]
                and process["argv"] == worker_arguments(self.spec, self.manifest_sha256, self.item),
                "Worker executable/argv drift.",
            )
            s.require(peer["gid"] == e.security(process["status"])["gid"], "Kernel peer GID drift.")
            client_roles = [
                v for v in observed["boundary"]["owned_batch"] if v["role"] == "local_srun_client"
            ]
            s.require(
                len(client_roles) == 1 and self.launcher.pid == client_roles[0]["process"]["pid"],
                "Owned local client binding required.",
            )
            client = self.kernel.process(self.launcher.pid)
            s.require(
                client["ppid"] == candidate["supervisor_pid"]
                and client["executable"] == self.spec["tools"]["srun"],
                "Local launcher ownership/executable drift.",
            )
            second_scheduler = {kind: self.queries.query(kind) for kind in scheduler}
            phase = "second_environment"
            second = prepare_frame(
                self.item,
                candidate,
                self.kernel,
                second_scheduler,
                initial_affinity=observed["initial"]["resources"]["initial_affinity"],
            )
            self._store(second, self.frames)
            s.require(second["result"] is not None, "Second environment verification failed.")
            # Each frame independently satisfies all obligations; the immutable
            # assurance binding comes from the first actual capture, not a caller.
            stable_keys = ("binding", "controllers", "owned_batch", "resource_scope_sha256")
            s.require(
                all(
                    observed["boundary"][k] == second["result"]["boundary"][k] for k in stable_keys
                ),
                "Environment binding changed.",
            )
            phase = "software_barrier"
            verify_current(self.spec, self.manifest, self.manifest_sha256, self.item)
            self.protocol.bind(
                self.clock(), observed["boundary"], observed["initial"], second["result"]["initial"]
            )
            self.original = observed
            self.source_proof = proof
        except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError):
            return self._failure(phase)
        return self.receipt()

    def observe_components(self, read_products_and_writes):
        s.require(not self.terminal and self.original is not None, "Unprepared/terminal adapter.")
        try:
            verify_current(self.spec, self.manifest, self.manifest_sha256, self.item)
            rows = a.accounting(self.queries.query("accounting"), self.spec["job_id"])
            now = self.clock()
            s.require(
                now < 660
                and now - self.protocol.last_observation <= 5
                and (self.protocol.ended is None or now - self.protocol.ended < 390),
                "Observation/cleanup deadline.",
            )
            products, writes = read_products_and_writes()
            frame = capture_observation(
                self.item,
                self.original,
                self.kernel,
                rows,
                products,
                writes,
                self.protocol.known,
                self.launcher.poll() is not None,
                self.protocol.state == "running",
            )
            self._store(frame, self.observations)
            s.require(frame["result"] is not None, "Independent observation unavailable.")
            if frame["result"]["transition_to_cleanup"]:
                self.protocol.end(self.clock())
            if frame["result"]["accounting_pending"]:
                return self.receipt()
            self.protocol.sample(self.clock(), frame["result"]["packet"])
            self.terminal = self.protocol.state in {"blocked", "software_candidate_closed"}
        except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError):
            return self._failure("independent_observation")
        return self.receipt()

    def receipt(self):
        return {
            "schema_version": "s2-lifecycle-adapter-review-v1",
            "status": "blocked_environment_or_observation"
            if self.failures
            else "software_checked_execution_blocked",
            "source_commit": self.spec["source_commit"],
            "job_id": self.spec["job_id"],
            "manifest_sha256": self.manifest_sha256,
            "contract_sha256": s.digest(self.item),
            "environment_frame_sha256": [s.digest(v) for v in self.frames],
            "observation_frame_sha256": [s.digest(v) for v in self.observations],
            "environment_error_sites": [
                v["error_site"] for v in self.frames if v["error_site"] is not None
            ],
            "protocol": self.protocol.receipt(),
            "failures": copy.deepcopy(self.failures),
            "ipc_released": False,
            "operational_claim_reserved": False,
            "observation_provenance": "software_fixture"
            if self.kernel.fixture
            else "kernel_reads_not_live_qualified",
            **lc.FLAGS,
        }

    def terminal_review(self, text):
        """Independent semantic replay; negative pre-barrier evidence is preserved."""
        rows = a.accounting(text, self.spec["job_id"])
        s.require(
            all(
                key in rows and rows[key]["state"] in a.TERMINAL
                for key in (self.spec["job_id"], self.spec["job_id"] + ".batch")
            ),
            "Root/batch terminal accounting required.",
        )
        try:
            for frame in self.frames:
                replay_frame(self.item, frame)
            expected_packets = [
                event["payload"]["packet"]
                for event in self.protocol.journal
                if event["kind"] == "sample"
            ]
            packets = []
            for frame in self.observations:
                value = replay_observation(self.item, self.original, frame)
                s.require(
                    {v["pid"]: v for v in frame["known"].values()} == self.protocol.known,
                    "Operational registry drift.",
                )
                if value is not None and not value["accounting_pending"]:
                    packets.append(value["packet"])
            s.require(
                packets == expected_packets, "Operational observation/protocol journal drift."
            )
            if self.original is not None:
                replay = package.collect(
                    self.item,
                    self.protocol.journal,
                    text,
                    source_commit=self.spec["source_commit"],
                    job_id=self.spec["job_id"],
                    contract_sha256=s.digest(self.item),
                    expected_journal_sha256=s.digest(self.protocol.journal),
                )
                s.require(
                    replay["disposition"] == "software_replayed_not_live_qualified",
                    "Nested lifecycle journal rejected.",
                )
            else:
                replay = None
            disposition = (
                "negative_or_partial_preserved"
                if self.failures
                else "software_replayed_not_live_qualified"
            )
        except (ValueError, TypeError, KeyError, IndexError, AttributeError):
            replay, disposition = None, "rejected_evidence_preserved"
        return {
            "schema_version": "s2-lifecycle-operational-terminal-v1",
            "adapter": self.receipt(),
            "accounting_sha256": s.digest(rows),
            "disposition": disposition,
            "replay": replay,
            **lc.FLAGS,
        }
