"""Closed normal diagnostic integration; no driver, live admission or retries.

Independent lifecycle reads improve visibility, not containment acceptance.
The existing finite controller, worker, resource policy and budgets are unchanged.
"""

from __future__ import annotations

if __name__ == "__main__":
    raise PermissionError("Diagnostic normal integration is closed; no execution admitted.")

import copy

from scripts import mvp2_s2_normal_audit as d
from scripts import mvp2_s2_resource_forensics as f
from scripts import mvp2_s2_resource_normal as n

a, c, q, s, p = n.a, n.c, n.q, n.s, n.p


def inputs(payloads, diagnostic, *, force_fault, cadence_exceeded, target):
    """Unknown remains unknown; terminal products never replace scope proof."""
    s.require(type(force_fault) is bool and type(cadence_exceeded) is bool, "Stop/cadence flags.")
    fault = force_fault or cadence_exceeded or diagnostic["any_unavailable"]
    members = payloads.get("members")
    snapshot = payloads.get("resources")
    fingerprint = payloads.get("products")
    rows = payloads.get("accounting", {})
    return {
        "worker_done": bool(
            fingerprint and {"terminal.json", "failure.json"} & fingerprint["products"].keys()
        ),
        "fault": fault,
        "scope_hash": snapshot["scope_sha256"] if snapshot and not fault else None,
        "members": members["members"] if members else None,
        "all_known_pids_absent": payloads.get("absence", {}).get("all_known_pids_absent", False),
        "launcher_reaped": payloads.get("launcher", {}).get("launcher_reaped", False),
        "step_terminal": rows.get(target, {}).get("state") in a.TERMINAL,
        "writes_sha256": s.digest(fingerprint) if fingerprint is not None else None,
    }


class DiagnosticNormalAdapter(n.ResourceNormalAdapter):
    """Explicit transport only; inherited public launch still denies."""

    def __init__(self, item, *, transport, **kwargs):
        s.require(transport is not None, "Explicit qualified transport required.")
        super().__init__(item, transport=transport, **kwargs)
        self.diagnostics = []

    def _products(self):
        products = a.read_products(self.root / "worker")
        q.verify_worker_products(self.contract, products)
        value = {"products": products, "heartbeat": None, "pending": None}
        for name, key in (("heartbeat.json", "heartbeat"), ("heartbeat.pending", "pending")):
            path = self.root / name
            if path.exists():
                item = c.decode_json(a._file(path, 4096))
                q._keys(item, {"nonce", "counter"})
                s.require(
                    item["nonce"] == self.item["nonce"]
                    and type(item["counter"]) is int
                    and 0 <= item["counter"] <= 120,
                    "Heartbeat drift.",
                )
                value[key] = item
        return value

    def tick(self, *, force_fault=False):
        s.require(type(force_fault) is bool, "Explicit stop flag.")
        s.require(
            self.controller is not None and len(self.samples) < a.MAX_SAMPLES, "Sample bound/state."
        )
        payloads, runtime = {}, {}

        def capture(name, read):
            def wrapped():
                value = read()
                payloads[name] = value
                return value

            return wrapped

        def launcher():
            self.handle.pump(deadline=min(self.started + 660, self._now() + 0.5))
            return {"launcher_reaped": self.handle.process.poll() is not None}

        def members():
            pids, _records = self._members()
            runtime["pids"] = pids
            return {"members": len(pids), "registry_sha256": s.digest(self.known)}

        def resources():
            snap = self.snapshot(self.worker["scopes"])
            s.require("pids" in runtime, "Membership unavailable; never substitute zero.")
            self.check_snapshot(snap, runtime["pids"])
            initial = self.initial_snapshot["counters"]
            s.require(
                all(
                    snap["counters"][k] == initial[k]
                    for k in (
                        "memory_limit_bytes",
                        "effective_reported_memory_limit_bytes",
                        "cpuset_cpu_count",
                    )
                ),
                "Limit drift.",
            )
            previous = next(
                (v["snapshot"] for v in reversed(self.samples) if v["snapshot"] and not v["fault"]),
                self.initial_snapshot,
            )
            s.require(
                all(
                    snap["counters"][k] >= previous["counters"][k]
                    for k in ("memory_max_usage_bytes", "cpu_usage_ns", "memory_failcnt")
                ),
                "Counter rollback.",
            )
            outside = self.record(self.supervisor["identity"]["pid"])
            s.require(
                q._stable_identity(outside["identity"])
                == q._stable_identity(self.supervisor["identity"])
                and outside["scopes"] == self.supervisor["scopes"],
                "Supervisor moved/reused.",
            )
            return {"snapshot": snap, "scope_sha256": s.digest(snap["scopes"])}

        def accounting():
            return a.accounting(
                self._query(
                    "sacct",
                    "--noheader",
                    "--parsable2",
                    "--jobs=" + self.item["job_id"],
                    "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw",
                ),
                self.item["job_id"],
            )

        def absence():
            s.require(1 <= len(self.known) <= 64, "Known-PID registry bound.")
            observed = [self.pid_absent(pid) for pid in self.known]
            s.require(all(type(value) is bool for value in observed), "Unknown PID absence.")
            return {"all_known_pids_absent": all(observed)}

        readers = dict(
            zip(
                d.CHANNELS,
                (launcher, members, resources, self._products, accounting, absence),
                strict=True,
            )
        )
        diagnostic = d.observe_channels(
            {name: capture(name, read) for name, read in readers.items()}
        )
        now = self._now()
        cadence = bool(self.samples and now - (self.samples[-1]["seconds"] + self.started) > 5)
        projected = inputs(
            payloads,
            diagnostic,
            force_fault=force_fault,
            cadence_exceeded=cadence,
            target=self.target,
        )
        action = self.controller.observe(now, **projected)
        sample = {
            "seconds": now - self.started,
            "snapshot": payloads.get("resources", {}).get("snapshot"),
            "fault": projected["fault"],
            "accounting_sha256": s.digest(payloads.get("accounting", {})),
            "writes_sha256": projected["writes_sha256"],
        }
        index = len(self.samples)
        self.samples.append(sample)
        c.write_once(self.root / f"sample-{index:04d}.json", sample)
        self._journal()
        record = {
            "schema_version": "s2-normal-diagnostic-sample-v1",
            "specification_sha256": s.digest(self.item),
            "index": index,
            "seconds": sample["seconds"],
            "force_fault": force_fault,
            "cadence_exceeded": cadence,
            "diagnostic": diagnostic,
            "payloads": payloads,
            "sample_sha256": s.digest(sample),
            "event_sha256": s.digest(self.controller.events[-1]),
            **p.FLAGS,
        }
        c.write_once(self.root / f"diagnostic-sample-{index:04d}.json", record)
        self.diagnostics.append(record)
        if action in {"TERM_exact_step", "KILL_exact_step"}:
            self._signal(action.split("_", 1)[0])
        return action

    def preserve(self, *, failure_code=None):
        report = super().preserve(failure_code=failure_code)
        if self.claimed:
            base = c.decode_json(a._file(self.root / "resource-evidence.json", n.LIMIT))
            value = {
                "schema_version": "s2-normal-diagnostic-evidence-v1",
                "specification_sha256": s.digest(self.item),
                "base_evidence": base,
                "samples": copy.deepcopy(self.samples),
                "diagnostics": copy.deepcopy(self.diagnostics),
                **p.FLAGS,
            }
            s.require(len(c.encoded(value)) <= n.LIMIT, "Diagnostic carrier bound.")
            c.write_once(self.root / "diagnostic-evidence.json", value)
        return report


def review(value, spec):
    """Replay every channel-to-controller binding, never attest installed cleanup."""
    return review_portable(value, n.portable_binding(spec))


def review_portable(value, binding):
    """Identical replay with the existing path-free, externally bound identity."""
    spec = n.validate_portable_binding(binding)
    q._keys(
        value,
        {
            "schema_version",
            "specification_sha256",
            "base_evidence",
            "samples",
            "diagnostics",
            *p.FLAGS,
        },
    )
    s.require(
        value["schema_version"] == "s2-normal-diagnostic-evidence-v1"
        and value["specification_sha256"] == spec["specification_sha256"]
        and all(value[k] is False for k in p.FLAGS),
        "Diagnostic carrier binding.",
    )
    result = n.review_portable(value["base_evidence"], spec)
    f.review_samples(value["samples"], value["base_evidence"])
    samples, records = value["samples"], value["diagnostics"]
    s.require(type(records) is list and len(records) == len(samples), "Diagnostic count.")
    events = value["base_evidence"]["events"][1:]
    contract = value["base_evidence"]["contract"]
    target = (
        None
        if contract is None
        else spec["job_id"] + "." + contract["legacy_contract"]["binding"]["worker_step_id"]
    )
    for index, (record, sample, event) in enumerate(zip(records, samples, events, strict=True)):
        q._number(record["seconds"])
        q._keys(
            record,
            {
                "schema_version",
                "specification_sha256",
                "index",
                "seconds",
                "force_fault",
                "cadence_exceeded",
                "diagnostic",
                "payloads",
                "sample_sha256",
                "event_sha256",
                *p.FLAGS,
            },
        )
        s.require(
            record["schema_version"] == "s2-normal-diagnostic-sample-v1"
            and record["specification_sha256"] == spec["specification_sha256"]
            and type(record["index"]) is int
            and record["index"] == index
            and record["seconds"] == sample["seconds"]
            and record["sample_sha256"] == s.digest(sample)
            and record["event_sha256"] == s.digest(event)
            and all(record[k] is False for k in p.FLAGS),
            "Diagnostic journal drift.",
        )
        diagnostic, payloads = record["diagnostic"], record["payloads"]
        q._keys(diagnostic, {"schema_version", "observations", "any_unavailable", *p.FLAGS})
        q._keys(diagnostic["observations"], set(d.CHANNELS))
        s.require(
            diagnostic["schema_version"] == "s2-normal-diagnostic-channels-v1"
            and all(diagnostic[k] is False for k in p.FLAGS)
            and type(payloads) is dict
            and payloads.keys() <= set(d.CHANNELS),
            "Diagnostic authority/schema.",
        )
        for name, observed in diagnostic["observations"].items():
            q._keys(observed, {"status", "semantic_sha256", "error_kind"})
            if name in payloads:
                s.require(
                    observed
                    == {
                        "status": "observed_not_qualified",
                        "semantic_sha256": s.digest(payloads[name]),
                        "error_kind": None,
                    },
                    "Channel hash drift.",
                )
            else:
                s.require(
                    observed["status"] == "unavailable"
                    and observed["semantic_sha256"] is None
                    and observed["error_kind"]
                    in {"missing", "timeout", "os_error", "invalid_observation"},
                    "Unavailable channel drift.",
                )
        s.require(
            type(diagnostic["any_unavailable"]) is bool
            and diagnostic["any_unavailable"] == (len(payloads) != len(d.CHANNELS)),
            "Missing channel drift.",
        )
        validate_payloads(payloads, spec, contract)
        cadence = bool(index and sample["seconds"] - samples[index - 1]["seconds"] > 5)
        s.require(record["cadence_exceeded"] is cadence, "Cadence drift.")
        expected = inputs(
            payloads,
            diagnostic,
            force_fault=record["force_fault"],
            cadence_exceeded=cadence,
            target=target,
        )
        s.require(expected == event["payload"]["inputs"], "Independent channels/controller drift.")
        s.require(
            sample["snapshot"] == payloads.get("resources", {}).get("snapshot")
            and sample["accounting_sha256"] == s.digest(payloads.get("accounting", {})),
            "Sample/channel drift.",
        )
    return {
        "schema_version": "s2-normal-diagnostic-review-v1",
        "status": "replayed_not_live_qualified",
        "controller_state": result["controller_state"],
        "evidence_sha256": s.digest(value),
        **p.FLAGS,
    }


def validate_payloads(payloads, spec, contract):
    for name, value in payloads.items():
        if name in {"launcher", "absence"}:
            key = "launcher_reaped" if name == "launcher" else "all_known_pids_absent"
            q._keys(value, {key})
            s.require(type(value[key]) is bool, "Diagnostic boolean.")
        elif name == "members":
            q._keys(value, {"members", "registry_sha256"})
            s.require(
                type(value["members"]) is int and 0 <= value["members"] <= 64, "Member count."
            )
            q._hash(value["registry_sha256"])
        elif name == "resources":
            q._keys(value, {"snapshot", "scope_sha256"})
            s.require(
                "members" in payloads
                and value["scope_sha256"] == s.digest(value["snapshot"]["scopes"])
                and value["snapshot"]["counters"]["freezer_unique_process_count"]
                == payloads["members"]["members"],
                "Resource membership binding.",
            )
        elif name == "accounting":
            s.require(type(value) is dict, "Accounting payload.")
            text = ""
            for job, row in value.items():
                q._keys(row, {"state", "exit_code", "elapsed_seconds"})
                text += f"{job}|{row['state']}|{row['exit_code']}|{row['elapsed_seconds']}\n"
            s.require(a.accounting(text, spec["job_id"]) == value, "Accounting grammar.")
        elif name == "products":
            q._keys(value, {"products", "heartbeat", "pending"})
            q.verify_worker_products(contract["legacy_contract"], value["products"])
            for key in ("heartbeat", "pending"):
                if value[key] is not None:
                    q._keys(value[key], {"nonce", "counter"})
                    s.require(
                        value[key]["nonce"] == spec["nonce"]
                        and type(value[key]["counter"]) is int
                        and 0 <= value[key]["counter"] <= 120,
                        "Diagnostic heartbeat drift.",
                    )


def collect_components(run, destination, spec):
    """Derived complete/partial carrier only; no scheduler, repair or admission."""
    from pathlib import Path

    spec = a.validate_spec(spec)
    run, destination = Path(run), Path(destination)
    q._safe_path(run)
    q._safe_path(destination)
    s.require(
        str(run) == spec["run"]
        and run != destination
        and run not in destination.parents
        and destination not in run.parents,
        "Collection location drift.",
    )
    s.require(
        Path(spec["checkout"]) not in destination.parents and destination != Path(spec["checkout"]),
        "Output in source.",
    )

    def capture():
        records = f.read_records(run)
        names = {"diagnostic-evidence.json"}
        for path in run.iterdir():
            if path.name.startswith("diagnostic-sample-"):
                index = path.name.removeprefix("diagnostic-sample-").removesuffix(".json")
                s.require(
                    path.name == f"diagnostic-sample-{int(index):04d}.json"
                    and 0 <= int(index) < a.MAX_SAMPLES,
                    "Diagnostic name bound.",
                )
                names.add(path.name)
        for name in names:
            try:
                records[name] = a._file(run / name, n.LIMIT)
            except FileNotFoundError:
                pass
        s.require(sum(len(v) for v in records.values()) <= f.LIMIT, "Diagnostic transfer bound.")
        return records

    records = capture()
    f.same(records, "claim.json", {"specification_sha256": s.digest(spec), **a.FLAGS})
    value, result = None, {"status": "forensic_preserved_not_qualified", **p.FLAGS}
    raw = records.get("diagnostic-evidence.json")
    if raw is not None:
        try:
            value = c.decode_json(raw)
            result = review(value, spec)
            base = value["base_evidence"]
            f.same(records, "resource-evidence.json", base)
            f.same(records, "attempt.json", base["attempt"])
            expected = {}
            for prefix, items in (
                ("sample", value["samples"]),
                ("diagnostic-sample", value["diagnostics"]),
                ("event", base["events"]),
            ):
                for index, item in enumerate(items):
                    expected[f"{prefix}-{index:04d}.json"] = item
                s.require(
                    {v for v in records if v.startswith(prefix + "-")}
                    == {v for v in expected if v.startswith(prefix + "-")},
                    "Journal tail/hole.",
                )
            for name, item in expected.items():
                f.same(records, name, item)
            if base["contract"] is not None:
                f.same(records, "contract.json", base["contract"]["legacy_contract"])
                f.same(records, "resource-contract.json", base["contract"])
            for prefix, expected in (
                (
                    "resource-barrier",
                    {f"resource-barrier-{i}.json": v for i, v in enumerate(base["barriers"])},
                ),
                (
                    "resource-sample",
                    {f"resource-sample-{v['index']:04d}.json": v for v in base["resources"]},
                ),
            ):
                s.require(
                    {v for v in records if v.startswith(prefix + "-")} == expected.keys(),
                    "Resource journal tail/hole.",
                )
                for name, item in expected.items():
                    f.same(records, name, item)
        except (ValueError, KeyError, TypeError, IndexError, UnicodeError, RecursionError):
            value, result = None, {"status": "forensic_rejected_not_qualified", **p.FLAGS}
    s.require(records == capture(), "Diagnostic evidence changed during collection.")
    carrier = {
        "schema_version": "s2-normal-diagnostic-transfer-v1",
        "specification_sha256": s.digest(spec),
        "inventory": {name: f.metadata(raw) for name, raw in sorted(records.items())},
        "evidence": value,
        "review": result,
        **p.FLAGS,
    }
    s.require(len(c.encoded(carrier)) <= f.LIMIT, "Transfer carrier bound.")
    destination.mkdir(mode=0o700, exist_ok=False)
    c.write_once(destination / "diagnostic-transfer.json", carrier)
    return carrier
