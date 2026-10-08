"""Closed S2 partial-vector export and portable review components; never optimize."""

from __future__ import annotations

import hashlib
import io
import math
import re
import tarfile
from pathlib import Path

from scripts import mvp2_h300_controls as controls
from scripts import mvp2_h300_thread_contract as design
from src.logic.objective_diagnostics import stage_degradation_records
from src.logic.optimization import OptimizationResult
from src.logic.run_integrity import scientific_identity
from src.logic.solution_validation import COST_NAMES, validate_solution

VECTOR_FIELDS = (
    "objective_value",
    "cost_breakdown",
    "warehouse_decisions",
    "flows",
    "inventories",
    "unmet_demand",
    "emergency_capacity",
)
STAGE_FIELDS = ("stage_role", "status", "objective_value", "objective_bound", "mip_gap")
PRODUCTS = (
    "observation.json",
    "incumbent.json",
    "independent_validation.json",
    "resources.json",
    "control.json",
    "closure.json",
)
NATIVE_STOPS = {
    "OPTIMAL": "completed",
    "TIME_LIMIT": "time_limit",
    "MEM_LIMIT": "memory_limit",
    "INTERRUPTED": "interrupted",
}
LIMIT = 256 * 1024**2
ROW_KEYS = {
    "warehouse_decisions": {
        "warehouse",
        "is_existing",
        "is_candidate",
        "open",
        "candidate_capacity",
        "expand",
        "expansion_capacity",
        "bulkify",
        "bulk_capacity",
        "static_capacity",
        "effective_static_capacity",
    },
    "flows": {
        "scenario",
        "route_type",
        "origin",
        "warehouse",
        "customer",
        "customer_type",
        "warehouse_from",
        "warehouse_to",
        "product",
        "period",
        "value",
    },
    "inventories": {"scenario", "warehouse", "product", "period", "value"},
    "unmet_demand": {"scenario", "customer", "product", "period", "value"},
    "emergency_capacity": {"scenario", "warehouse", "period", "capacity_type", "value"},
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def anchor(data, config, *, source_commit, runtime_sha256, workbook_sha256, threads):
    """Bind caller-supplied inputs; not proof of original archive/current NPAD admission."""
    design.require(re.fullmatch(r"[0-9a-f]{40}", source_commit) is not None, "Invalid source.")
    for value in (runtime_sha256, workbook_sha256):
        design.require(
            isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value),
            "Invalid runtime/workbook identity.",
        )
    design.require(type(threads) is int and threads in design.GRID, "Invalid threads.")
    design.require(
        config.mode == "sto" and config.objective_policy == "lexicographic",
        "This component qualifies the stochastic native hierarchy only.",
    )
    return {
        "schema_version": "s2-partial-anchor-v1",
        "source_commit": source_commit,
        "runtime_sha256": runtime_sha256,
        "workbook_sha256": workbook_sha256,
        "data_sha256": scientific_identity(data),
        "config_sha256": scientific_identity(config),
        "threads": threads,
        "scope": "component_qualification_not_production_admission",
    }


def reconstructed_values(result, validation, data):
    """Final values come from validated sparse records, not unverified result.metrics."""
    weights = data.scenario_prob
    unmet = sum(weights[r["scenario"]] * r["value"] for r in result.unmet_demand)
    emergency = sum(weights[r["scenario"]] * r["value"] for r in result.emergency_capacity)
    costs = validation["reconstructed_costs"]
    economic = sum(
        v
        for k, v in costs.items()
        if k not in {"unmet_demand", "emergency_static", "emergency_reception"}
    )
    return dict(zip(design.ROLES, (unmet, emergency, economic), strict=True))


def evaluate(
    observation,
    vector,
    data,
    config,
    expected_anchor,
    *,
    scheduler_state="COMPLETED",
    exit_code="0:0",
    products_closed=True,
):
    """Recompute residuals and inherited degradation; never infer a vector from status."""
    design.require(
        observation["anchor"] == expected_anchor
        and expected_anchor["data_sha256"] == scientific_identity(data)
        and expected_anchor["config_sha256"] == scientific_identity(config),
        "External input/source/runtime anchor mismatch.",
    )
    design.require(
        set(observation)
        == {
            "schema_version",
            "anchor",
            "native_status",
            "solution_count",
            "result_status",
            "stages",
        }
        and observation["schema_version"] == "s2-partial-observation-v1",
        "Unexpected observation schema.",
    )
    design.require(
        observation["result_status"]
        in {"optimal", "feasible", "time_limit", "error", "interrupted"},
        "Unexpected result status.",
    )
    count, native = observation["solution_count"], observation["native_status"]
    design.require(
        type(count) is int and count >= 0 and native in NATIVE_STOPS,
        "Invalid native stop/SolCount.",
    )
    design.require((count > 0) == (vector is not None), "Incumbent/count contradiction.")
    design.require(native != "OPTIMAL" or count > 0, "OPTIMAL without an incumbent.")
    stages = observation["stages"]
    design.require(isinstance(stages, list) and len(stages) <= 3, "Invalid observed stages.")
    normalized = []
    for i, stage in enumerate(stages):
        design.require(
            set(stage) == set(STAGE_FIELDS)
            and stage["stage_role"] == design.ROLES[i]
            and stage["status"] in NATIVE_STOPS,
            "Stage schema/order drift.",
        )
        for key in ("objective_value", "objective_bound"):
            design.require(
                stage[key] is None
                or type(stage[key]) in (int, float)
                and math.isfinite(stage[key]),
                "Nonfinite/nonnumeric stage value.",
            )
        design.number(stage["mip_gap"], "stage gap", nullable=True)
        if stage["objective_bound"] is not None and stage["objective_value"] is not None:
            design.require(
                stage["objective_bound"] <= stage["objective_value"] + 1e-5,
                "Minimization bound exceeds incumbent.",
            )
            if stage["mip_gap"] is not None and stage["objective_value"] != 0:
                calculated = abs(stage["objective_value"] - stage["objective_bound"]) / abs(
                    stage["objective_value"]
                )
                design.require(
                    abs(calculated - stage["mip_gap"]) <= 1e-6,
                    "Stage gap contradicts observed incumbent/bound.",
                )
        accepted = (
            stage["status"] == "OPTIMAL"
            and all(stage[k] is not None for k in ("objective_value", "objective_bound", "mip_gap"))
            and stage["mip_gap"] <= 0.1
        )
        if i == 0:
            accepted = accepted and abs(stage["objective_value"] or 0) <= 1.01e-6
        normalized.append(
            {
                "role": design.ROLES[i],
                "status": {
                    "OPTIMAL": "optimal",
                    "TIME_LIMIT": "time_limit",
                    "MEM_LIMIT": "memory_limit",
                    "INTERRUPTED": "interrupted",
                }[stage["status"]],
                "priority_accepted": accepted,
            }
        )
    validation = {"status": "not_applicable_no_incumbent"}
    values = None
    certificates = []
    if vector is not None:
        design.require(set(vector) == set(VECTOR_FIELDS), "Unallowlisted vector fields.")
        design.require(
            isinstance(vector["cost_breakdown"], dict)
            and set(vector["cost_breakdown"]) == set(COST_NAMES),
            "Cost schema drift.",
        )
        for name, keys in ROW_KEYS.items():
            design.require(
                isinstance(vector[name], list)
                and all(isinstance(row, dict) and set(row).issubset(keys) for row in vector[name]),
                "Unallowlisted sparse vector columns.",
            )
        # A private validation copy recognizes the explicitly observed incumbent,
        # including native MEM_LIMIT. Original stop/status are never rewritten.
        result = OptimizationResult(status="feasible", **vector)
        validation = validate_solution(data, config, result)
        if validation["status"] == "accepted":
            values = reconstructed_values(result, validation, data)
            certificates = stage_degradation_records(
                stages,
                values,
                mip_gap=0.1,
                mip_gap_abs=1e-10,
                objective_abs_tol=config.feasibility_tolerance,
            )
    final_accepted = (
        values is not None
        and values["unmet_demand"] <= 1.01e-6
        and len(certificates) == 3
        and all(c.get("within_mip_degradation_limit") is True for c in certificates)
    )
    classification = design.observation(
        {
            "stages": normalized,
            "scheduler_state": scheduler_state,
            "exit_code": exit_code,
            "native_stop": NATIVE_STOPS[native],
            "has_incumbent": count > 0,
            "residuals_accepted": validation["status"] == "accepted",
            "final_priority_accepted": final_accepted,
            "products_closed": products_closed,
            "integrity_accepted": True,
        }
    )
    return controls.decode_json(
        controls.encoded(
            {
                "classification": classification,
                "validation": validation,
                "final_values": values,
                "stage_certificates": certificates,
            }
        )
    )


def export_partial(directory, result, data, config, expected_anchor, *, resource_samples=None):
    """Write named products once; closure is last, not a full-hierarchy run_completion."""
    native = result.metadata.get("gurobi_status_name")
    count = result.metadata.get("solution_count")
    design.require(
        type(count) is int and count >= 0 and native in NATIVE_STOPS,
        "Native solution count/stop are required.",
    )
    stages = [
        {k: stage.get(k) for k in STAGE_FIELDS}
        for stage in result.metadata.get("lexicographic_stages", [])
    ]
    observation = {
        "schema_version": "s2-partial-observation-v1",
        "anchor": expected_anchor,
        "native_status": native,
        "solution_count": count,
        "result_status": result.status,
        "stages": stages,
    }
    vector = {k: getattr(result, k) for k in VECTOR_FIELDS} if count else None
    if not count:
        design.require(
            result.objective_value is None
            and not result.cost_breakdown
            and all(not getattr(result, k) for k in VECTOR_FIELDS[2:]),
            "No-incumbent result carries a fabricated/stale vector.",
        )
    # Check JSON representability before creating a directory or acceptance marker.
    controls.encoded(observation)
    controls.encoded(vector)
    report = evaluate(observation, vector, data, config, expected_anchor)
    resources = None
    if resource_samples is not None:
        resources = {
            "samples": resource_samples,
            "summary": controls.resource_summary(resource_samples),
        }
        controls.encoded(resources)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    assets = {"observation.json": observation, "independent_validation.json": report["validation"]}
    if vector is not None:
        assets["incumbent.json"] = vector
    if resources is not None:
        assets["resources.json"] = resources
    for name, value in assets.items():
        controls.write_once(directory / name, value)
    controls.write_once(
        directory / "closure.json",
        {
            "schema_version": "s2-partial-closure-v1",
            "anchor_sha256": design.digest(expected_anchor),
            "artifacts": {name: sha((directory / name).read_bytes()) for name in assets},
            "production_admitted": False,
            "repeats_admitted": False,
        },
    )
    return report


def load_assets(assets, data, config, expected_anchor, *, scheduler_state, exit_code):
    """Use an external anchor and fresh residuals; self-consistent hashes alone are insufficient."""
    design.require(
        set(assets).issubset(PRODUCTS) and "closure.json" in assets,
        "Missing/unallowlisted closure products.",
    )

    def read(name):
        return controls.decode_json(assets[name])

    closure = read("closure.json")
    names = set(assets) - {"closure.json", "control.json"}
    design.require(
        set(closure)
        == {
            "schema_version",
            "anchor_sha256",
            "artifacts",
            "production_admitted",
            "repeats_admitted",
        }
        and closure["schema_version"] == "s2-partial-closure-v1"
        and closure["anchor_sha256"] == design.digest(expected_anchor)
        and closure["production_admitted"] is False
        and closure["repeats_admitted"] is False
        and closure["artifacts"] == {n: sha(assets[n]) for n in names},
        "Closure identity/hash/permissions drift.",
    )
    design.require(
        {"observation.json", "independent_validation.json"}.issubset(names),
        "Missing observation/validation.",
    )
    report = evaluate(
        read("observation.json"),
        read("incumbent.json") if "incumbent.json" in names else None,
        data,
        config,
        expected_anchor,
        scheduler_state=scheduler_state,
        exit_code=exit_code,
    )
    design.require(
        report["validation"] == read("independent_validation.json"),
        "Recorded validation differs from fresh residual checks.",
    )
    design.require("control.json" in assets, "Missing parent closure after cleanup.")
    parent = read("control.json")
    design.require(
        set(parent) == {"anchor_sha256", "child_closure_sha256", "control"}
        and parent["anchor_sha256"] == design.digest(expected_anchor)
        and parent["child_closure_sha256"] == sha(assets["closure.json"]),
        "Parent/child closure binding drift.",
    )
    control = verify_control(parent["control"], expected_anchor)
    report["control"] = control
    report["classification"]["products_closed"] = control["owned_group_closed"]
    if control["return_code"] != 0 or control["stop_reason"] is not None:
        report["classification"]["disposition"] = "execution_failed"
    elif not control["owned_group_closed"] and report["classification"]["disposition"] == (
        "complete_accepted_hierarchy"
    ):
        report["classification"]["disposition"] = "feasible_partial_hierarchy"
    report["resources"] = None
    if "resources.json" in names:
        resources = read("resources.json")
        design.require(
            set(resources) == {"samples", "summary"}
            and controls.resource_summary(resources["samples"]) == resources["summary"],
            "Resource summary differs from original observations.",
        )
        report["resources"] = resources["summary"]
    report["classification"]["integrity_accepted"] = True
    return report


def verify_control(control, expected_anchor):
    """A hash-bound parent record is not itself a live scheduler/cgroup attestation."""
    design.require(
        set(control)
        == {
            "identity",
            "root_pid",
            "return_code",
            "stop_reason",
            "error_type",
            "owned_group_closed",
            "allocation_tree_closed",
            "observed_transitions",
            "application_seconds",
            "production_admitted",
            "repeats_admitted",
        },
        "Control schema drift.",
    )
    design.require(
        control["identity"] == design.digest(expected_anchor)
        and type(control["root_pid"]) is int
        and control["root_pid"] > 0
        and type(control["return_code"]) is int,
        "Control identity/exit drift.",
    )
    design.require(
        control["stop_reason"]
        in {
            None,
            "build_watchdog",
            "optimization_watchdog",
            "export_validation_watchdog",
            "cleanup_watchdog",
            "child_or_block_watchdog",
            "child_failure",
            "incomplete_phase_journal",
            "live_descendants",
            "control_error",
        },
        "Unknown control stop.",
    )
    for key in ("owned_group_closed", "allocation_tree_closed"):
        design.require(type(control[key]) is bool, "Invalid closure flag.")
    design.require(
        control["production_admitted"] is False and control["repeats_admitted"] is False,
        "Control cannot admit execution.",
    )
    design.number(control["application_seconds"], "control elapsed")
    design.require(
        control["error_type"] is None
        or control["error_type"]
        in {
            "ValueError",
            "OSError",
            "KeyError",
            "TypeError",
            "FileNotFoundError",
            "PermissionError",
            "JSONDecodeError",
        },
        "Unallowlisted control error.",
    )
    previous = -1
    phases = []
    for event in control["observed_transitions"]:
        design.require(set(event) == {"phase", "observed_seconds"}, "Control transition drift.")
        stamp = design.number(event["observed_seconds"], "control phase observation")
        design.require(previous <= stamp <= control["application_seconds"], "Control clock drift.")
        previous = stamp
        phases.append(event["phase"])
    normal = phases[:-1] if phases and phases[-1] == "cleanup_after_failure" else phases
    design.require(
        normal == list(controls.PHASES[: len(normal)]) and len(normal) <= 4,
        "Control phase order drift.",
    )
    design.require(
        control["stop_reason"] is not None
        or control["return_code"] != 0
        or phases == list(controls.PHASES),
        "Successful control lacks completed phases.",
    )
    return control


def seal_control(directory, control, expected_anchor):
    """Parent writes once AFTER supervision/cleanup, retaining the child's original closure."""
    verify_control(control, expected_anchor)
    directory = Path(directory)
    child = directory / "closure.json"
    design.require(child.is_file() and not child.is_symlink(), "No closed child product catalog.")
    controls.write_once(
        directory / "control.json",
        {
            "anchor_sha256": design.digest(expected_anchor),
            "child_closure_sha256": file_digest(child),
            "control": control,
        },
    )


def terminal(text, job_id):
    """Exact root row in JobIDRaw|State|ExitCode; accounting is supplied, never queried here."""
    design.require(isinstance(text, str) and len(text.encode()) <= 65536, "Unbounded accounting.")
    design.require(isinstance(job_id, str) and re.fullmatch(r"[0-9]+", job_id), "Bad job ID.")
    rows = [r.split("|") for r in text.splitlines() if r.strip()]
    roots = [r for r in rows if r[0].strip() == job_id]
    design.require(len(roots) == 1 and len(roots[0]) == 3, "Ambiguous/malformed root accounting.")
    state, code = (v.strip() for v in roots[0][1:])
    design.require(
        state
        in {
            "COMPLETED",
            "FAILED",
            "TIMEOUT",
            "OUT_OF_MEMORY",
            "PREEMPTED",
            "CANCELLED",
            "NODE_FAIL",
            "BOOT_FAIL",
        }
        and re.fullmatch(r"[0-9]+:[0-9]+", code),
        "Nonterminal/invalid accounting.",
    )
    return state, code


def collect(directory, destination, accounting, job_id, data, config, expected_anchor):
    """Package success or incomplete failure from a fixed allowlist; preserve original bytes."""
    state, code = terminal(accounting, job_id)
    directory, destination = Path(directory), Path(destination)
    design.require(not directory.is_symlink(), "Linked source directory.")
    root = directory.resolve()
    dest = destination.resolve()
    design.require(
        not dest.is_relative_to(root) and not root.is_relative_to(dest),
        "Collection overlaps original run.",
    )
    assets = {}
    for name in PRODUCTS:
        path = directory / name
        design.require(not path.is_symlink() and path.resolve().parent == root, "Unsafe product.")
        if path.exists():
            design.require(
                path.is_file() and path.stat().st_size <= LIMIT, "Invalid/oversized product."
            )
            with path.open("rb") as stream:
                assets[name] = stream.read(LIMIT + 1)
    design.require(
        sum(map(len, assets.values())) <= LIMIT, "Transfer exceeds bounded component size."
    )
    try:
        report = load_assets(
            assets, data, config, expected_anchor, scheduler_state=state, exit_code=code
        )
        status = "component_evidence_closed"
    except (ValueError, KeyError, TypeError, OSError) as error:
        status = "component_evidence_rejected"
        report = {"error_type": type(error).__name__, "production_admitted": False}
    record = {
        "schema_version": "s2-partial-transfer-v1",
        "status": status,
        "job_id": job_id,
        "anchor_sha256": design.digest(expected_anchor),
        "report": report,
        "artifacts": {n: sha(v) for n, v in assets.items()},
        "production_admitted": False,
        "repeats_admitted": False,
    }
    assets["accounting.txt"] = accounting.encode()
    record["artifacts"]["accounting.txt"] = sha(assets["accounting.txt"])
    assets["transfer.json"] = controls.encoded(record)
    design.require(
        sum(map(len, assets.values())) <= LIMIT, "Products plus receipts exceed transfer limit."
    )
    destination.mkdir(parents=True, exist_ok=False)
    archive = destination / "partial-component-evidence.tar.gz"
    with tarfile.open(archive, "x:gz") as stream:
        for name, payload in sorted(assets.items()):
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            stream.addfile(info, io.BytesIO(payload))
    checksum = file_digest(archive)
    with archive.with_suffix(".gz.sha256").open("x", encoding="utf-8") as stream:
        stream.write(f"{checksum}  {archive.name}\n")
    return archive, checksum, record


def review_transfer(archive, expected_sha256, job_id, data, config, expected_anchor):
    """Portable review without extractall, raw logs, a solver, or a private-input reload."""
    archive = Path(archive)
    design.require(
        archive.is_file() and not archive.is_symlink() and archive.stat().st_size <= LIMIT,
        "Invalid/oversized compressed archive.",
    )
    design.require(file_digest(archive) == expected_sha256, "Archive checksum mismatch.")
    assets = {}
    allowed = {*PRODUCTS, "accounting.txt", "transfer.json"}
    with tarfile.open(archive, "r:gz") as stream:
        for member in stream:
            design.require(
                member.name in allowed
                and member.name not in assets
                and member.isfile()
                and 0 <= member.size <= LIMIT,
                "Unsafe/duplicate/oversized archive member.",
            )
            design.require(
                sum(map(len, assets.values())) + member.size <= LIMIT,
                "Uncompressed transfer limit.",
            )
            assets[member.name] = stream.extractfile(member).read()
    design.require({"transfer.json", "accounting.txt"}.issubset(assets), "Incomplete transfer.")
    receipt = controls.decode_json(assets.pop("transfer.json"))
    design.require(
        receipt["schema_version"] == "s2-partial-transfer-v1"
        and set(receipt)
        == {
            "schema_version",
            "status",
            "job_id",
            "anchor_sha256",
            "report",
            "artifacts",
            "production_admitted",
            "repeats_admitted",
        }
        and receipt["job_id"] == job_id
        and receipt["anchor_sha256"] == design.digest(expected_anchor)
        and receipt["production_admitted"] is False
        and receipt["repeats_admitted"] is False
        and receipt["artifacts"] == {n: sha(v) for n, v in assets.items()},
        "Transfer identity/catalog/permissions mismatch.",
    )
    state, code = terminal(assets.pop("accounting.txt").decode(), job_id)
    report = load_assets(
        assets, data, config, expected_anchor, scheduler_state=state, exit_code=code
    )
    design.require(
        receipt["status"] == "component_evidence_closed" and receipt["report"] == report,
        "Transfer classification differs from fresh review.",
    )
    return report
