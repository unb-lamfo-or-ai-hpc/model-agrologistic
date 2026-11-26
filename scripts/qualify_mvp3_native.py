"""Prepare/collect public native qualification; execution requires a separate operator action.

No input-file or scheduler interface. Native imports occur only in the owned
worker after a source-bound, one-use execute action with explicit acknowledgement.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import secrets
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.logic.native_public_controls import control_specs, expected, make_control  # noqa: E402

ACK = "PUBLIC_NATIVE_TINY_ONLY_NO_H215_OR_HPC"
LIMITS = {"models": 32, "native_seconds_each": 60, "wall_seconds": 2700,
          "workers": 1, "Method": -1, "Threads": 0}
CONNECTION = {"ComputeServer", "LicenseID", "ServerPassword", "ServerTimeout", "TokenServer",
              "TSPort", "UserName", "JobID", "TLSInsecure"}


def encoded(record):
    return (json.dumps(record, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_new(path, record):
    raw = encoded(record)
    with Path(path).open("xb") as stream:
        stream.write(raw)


def read(path):
    return json.loads(Path(path).read_bytes())


def source_snapshot(revision):
    if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
        raise ValueError("A full source commit is required.")
    files = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", revision, "--", "src",
         "scripts/qualify_mvp3_native.py"], cwd=ROOT, check=True, capture_output=True,
    ).stdout.decode().splitlines()
    files = [name for name in files if name.endswith(".py")]
    if "scripts/qualify_mvp3_native.py" not in files:
        raise ValueError("Qualification source must be committed first.")
    snapshot = {name: subprocess.run(
        ["git", "cat-file", "blob", f"{revision}:{name}"], cwd=ROOT,
        check=True, capture_output=True,
    ).stdout for name in files}
    if snapshot["scripts/qualify_mvp3_native.py"] != Path(__file__).read_bytes():
        raise ValueError("Invoke the committed qualification script.")
    return snapshot


def selected_license(license_file):
    """Pin only a path; never open, copy or hash license contents."""
    if license_file is None:
        return {"source": "inherited_environment"}
    path = Path(license_file).absolute()
    if not path.is_file():
        raise ValueError("An existing local license file is required.")
    return {"source": "explicit_local_file", "path": str(path)}


def plan_record(revision, files, *, license_selection=None):
    return {"schema": "mvp3-native-public-qualification-v2", "revision": revision,
            "files": {name: sha(raw) for name, raw in sorted(files.items())},
            "controls": control_specs(), "limits": dict(LIMITS),
            "license_selection": license_selection or selected_license(None),
            "execution_authorized": False, "private_inputs": False,
            "scope": "Public tiny native software checks; not license capacity or h215 admission"}


def prepare(output, revision, *, license_file=None):
    selection = selected_license(license_file)
    snapshot = source_snapshot(revision)
    plan = plan_record(revision, snapshot, license_selection=selection)
    output = Path(output).absolute()
    if output.is_symlink():
        raise ValueError("A new regular claim directory is required.")
    output.mkdir(parents=True, exist_ok=False)
    source = output / "source"
    for name, raw in snapshot.items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    write_new(output / "plan.json", plan)
    return {"status": "prepared_no_native_execution", "plan_sha256": sha(encoded(plan)),
            "claim": str(output), "controls": len(plan["controls"]),
            "execution_authorized": False, "native_imported": False}


def verify_plan(claim, plan_sha256):
    claim = Path(claim).absolute()
    if claim.is_symlink() or not claim.is_dir():
        raise ValueError("Regular prepared claim required.")
    raw = (claim / "plan.json").read_bytes()
    if sha(raw) != plan_sha256:
        raise ValueError("Plan digest differs.")
    plan = json.loads(raw)
    if (encoded(plan["limits"]) != encoded(LIMITS)
            or encoded(plan["controls"]) != encoded(control_specs())
            or plan["execution_authorized"] is not False or plan["private_inputs"] is not False
            or plan["schema"] != "mvp3-native-public-qualification-v2"):
        raise ValueError("Prepared public scope differs from the fixed source contract.")
    selection = plan.get("license_selection")
    if selection != {"source": "inherited_environment"} and not (
        isinstance(selection, dict) and set(selection) == {"source", "path"}
        and selection["source"] == "explicit_local_file" and isinstance(selection["path"], str)
        and Path(selection["path"]).is_absolute()
    ):
        raise ValueError("Invalid pinned license selection.")
    source = (claim / "source").resolve()
    actual_files = {p.relative_to(source).as_posix() for p in (source / "src").rglob("*.py")}
    actual_files.add("scripts/qualify_mvp3_native.py")
    if set(plan["files"]) != actual_files:
        raise ValueError("Frozen runtime source inventory differs.")
    for name, digest in plan["files"].items():
        key = PurePosixPath(name)
        path = source.joinpath(*key.parts)
        if (key.is_absolute() or ".." in key.parts or path.is_symlink()
                or not path.resolve().is_relative_to(source) or sha(path.read_bytes()) != digest):
            raise ValueError("Frozen source identity differs.")
    if ROOT.resolve() != source:
        raise ValueError("Use the script inside the prepared frozen source capsule.")
    return claim, plan


class PublicParameterAuditError(ValueError):
    def __init__(self, reason, report):
        super().__init__("Public native parameter audit rejected.")
        self.public_diagnostic = {"reason": reason, **report}


def connection_parameter(name):
    key = name.replace("_", "").casefold()
    excluded = {item.replace("_", "").casefold() for item in CONNECTION}
    return key in excluded or key.startswith(("wls", "cs", "cloud", "worker"))


def full_default_audit(model, grb):
    checked, changed = 0, []
    names = {getattr(grb.Param, n) for n in dir(grb.Param)
             if not n.startswith("_") and isinstance(getattr(grb.Param, n), str)}
    for name in sorted(names):
        if connection_parameter(name):
            continue
        info = model.getParamInfo(name)
        if info is None or len(info) != 6:
            raise PublicParameterAuditError("introspection_unavailable", {
                "parameter": name, "checked": checked,
                "connection_parameter_values_read_or_exported": False})
        checked += 1
        if info[2] != info[5]:
            changed.append(name)
    report = {"checked": checked, "nondefaults": changed,
              "connection_parameter_values_read_or_exported": False}
    if checked < 100 or changed != ["OutputFlag", "TimeLimit"]:
        raise PublicParameterAuditError("nondefault_or_inventory_mismatch", report)
    if model.getParamInfo("TimeLimit")[2] != 60 or model.getParamInfo("OutputFlag")[2] != 0:
        raise PublicParameterAuditError("public_budget_or_display_mismatch", report)
    return report


def accept_result(control, result):
    lifecycle = result.metadata.get("native_model_lifecycle", [])
    audit = result.metadata.get("effective_native_parameters", {}).get(
        "full_public_default_audit", {})
    matrix = result.metadata.get("matrix", {})
    if (len(lifecycle) != 1 or lifecycle[0].get("status") != "disposed"
            or audit.get("checked", 0) < 100
            or audit.get("nondefaults") != ["OutputFlag", "TimeLimit"]
            or not 0 < matrix.get("variables", 0) <= 128
            or not 0 < matrix.get("constraints", 0) <= 256):
        return False
    target = expected(control)
    if target["classification"] == "infeasible":
        return (result.status == "infeasible" and not result.has_solution
                and result.objective_value is None
                and result.metadata.get("gurobi_status_code") == 3)
    if (result.status != "optimal" or not result.has_solution
            or result.metadata.get("gurobi_status_code") != 2
            or result.metadata.get("effective_validation", {}).get("status") != "accepted"
            or result.metadata.get("effective_dense_coverage", {}).get("status") != "accepted"
            or not math.isclose(result.objective_value, target["objective"],
                                rel_tol=1e-8, abs_tol=1e-5)):
        return False
    weight = 1 / 9 if control["mode"] == "sto" else 1
    for destination, field in (("X", "expected_export_t"), ("C", "expected_served_t")):
        tonnes = math.fsum(weight * r["value"] for r in result.flows
                          if r["route_type"] == "DC" and r["customer"] == destination)
        if not math.isclose(tonnes, target[field], rel_tol=1e-8, abs_tol=1e-5):
            return False
    field = "candidate_capacity" if control["kind"] == "candidate" else "expansion_capacity"
    return math.isclose(math.fsum(r[field] for r in result.warehouse_decisions),
                        target["installed_t"], rel_tol=1e-8, abs_tol=1e-5)


def worker(claim, plan_sha256, nonce):
    claim, plan = verify_plan(claim, plan_sha256)
    start = read(claim / "started.json")
    if start["parent_pid"] != os.getppid() or start["nonce_sha256"] != sha(nonce.encode()):
        raise ValueError("Owned qualification worker required.")
    state = {"phase": "native_import", "control_id": None,
             "native_import_completed": False, "environment_started": False,
             "control_receipts": 0, "native_phase": None,
             "optimization_entered": False, "optimization_returned": False}
    with record_worker_failure(claim, plan_sha256, state):
        run_public_controls(claim, plan, plan_sha256, state)


@contextmanager
def record_worker_failure(claim, plan_sha256, state):
    """Retain phase/class/code only; never serialize exception text or credentials."""
    try:
        yield
    except Exception as exc:
        code = getattr(exc, "errno", None) if type(exc).__module__.startswith("gurobipy") else None
        write_new(claim / "worker-failure.json", {
            "schema": "mvp3-public-worker-failure-v1", "plan_sha256": plan_sha256,
            **state, "error_class": type(exc).__name__,
            "native_error_code": code if type(code) is int else None,
            "public_source_origin": public_error_origin(exc),
            "public_parameter_audit": (
                exc.public_diagnostic if isinstance(exc, PublicParameterAuditError) else None),
            "exception_text_or_traceback_retained": False,
        })
        raise


def public_error_origin(error):
    """Return the final public-source location, excluding messages, locals and stack text."""
    origin, traceback = None, error.__traceback__
    while traceback is not None:
        frame = traceback.tb_frame
        filename = frame.f_code.co_filename
        if filename.endswith(".py"):
            try:
                relative = Path(filename).resolve().relative_to(ROOT.resolve())
            except ValueError:
                relative = None
            if relative is not None and relative.parts[0] in {"src", "scripts"}:
                origin = {"file": relative.as_posix(), "function": frame.f_code.co_name,
                          "line": traceback.tb_lineno}
        traceback = traceback.tb_next
    return origin


def run_public_controls(claim, plan, plan_sha256, state):
    # This is the only native import in the package, beyond explicit execute admission.
    import gurobipy as gp

    state.update(phase="runtime_imports", native_import_completed=True)
    from src.logic import optimization_gurobipy_stochastic as core
    from src.logic.native_public_controls import public_solver_config
    from src.logic.optimization_gurobipy import solve_model_gurobipy

    state["phase"] = "native_version"
    if tuple(gp.gurobi.version())[:2] != (14, 0):
        raise ValueError("Gurobi 14.0 required.")
    records = []
    state["phase"] = "engine_fingerprint"
    distribution = importlib.metadata.distribution("gurobipy")
    engine_files = {str(p): sha(distribution.locate_file(p).read_bytes())
                    for p in distribution.files or ()
                    if str(p).endswith((".py", ".pyd", ".dll", ".so"))}
    if not engine_files:
        raise ValueError("Native package code inventory unavailable.")
    state["phase"] = "environment_construct"
    with gp.Env(empty=True) as environment:
        state["phase"] = "environment_start"
        environment.setParam("OutputFlag", 0)
        environment.start()
        state.update(phase="audit_setup", environment_started=True)
        original = core.audit_reference_parameters

        def checked_parameters(model, api, config):
            record = original(model, api, config)
            record["full_public_default_audit"] = full_default_audit(model, gp.GRB)
            return record

        core.audit_reference_parameters = checked_parameters

        def observed_phase(phase, model, api):
            state["native_phase"] = phase
            if phase == "optimization":
                state["optimization_entered"] = True
            elif phase == "export_validation":
                state["optimization_returned"] = True

        try:
            for control in plan["controls"]:
                state.update(phase="control_data", control_id=control["id"], native_phase=None,
                             optimization_entered=False, optimization_returned=False)
                data, cfg = make_control(control["id"])
                state["phase"] = "control_solve"
                result = solve_model_gurobipy(data, cfg, public_solver_config(),
                                             native_environment=environment,
                                             native_phase_hook=observed_phase)
                state["phase"] = "control_acceptance"
                accepted = accept_result(control, result)
                path = claim / (control["id"] + ".json")
                state["phase"] = "control_receipt"
                write_new(path, {"control": control, "expected": expected(control),
                                 "accepted": accepted, "result": asdict(result)})
                state["control_receipts"] += 1
                records.append({"id": control["id"], "sha256": sha(path.read_bytes()),
                                "accepted": accepted})
                if not accepted:
                    raise ValueError("Public analytical/native control rejected.")
            state.update(phase="environment_dispose", control_id=None)
        finally:
            core.audit_reference_parameters = original
    state.update(phase="source_recheck", control_id=None)
    verify_plan(claim, plan_sha256)
    state["phase"] = "worker_summary"
    write_new(claim / "worker-result.json", {"status": "accepted", "records": records,
              "engine_code": engine_files, "python_sha256": sha(Path(sys.executable).read_bytes()),
              "production_or_license_capacity_qualified": False, "new_hpc_jobs": 0})


def worker_environment(plan):
    """Override the selected path only in the owned child; leave the parent/OS alone."""
    selection = plan["license_selection"]
    if selection["source"] == "inherited_environment":
        return None
    if not Path(selection["path"]).is_file():
        raise ValueError("The selected local license file is no longer present.")
    return {**os.environ, "GRB_LICENSE_FILE": selection["path"]}


def execute(claim, plan_sha256, acknowledgement):
    if acknowledgement != ACK:
        raise ValueError("Explicit public-only operator acknowledgement required.")
    claim, plan = verify_plan(claim, plan_sha256)
    if sys.version_info[:2] != (3, 13) or importlib.metadata.version("gurobipy") != "14.0.0":
        raise ValueError("Use the existing Python 3.13 / Gurobi 14.0.0 environment.")
    environment = worker_environment(plan)
    nonce = secrets.token_hex(24)
    clock = time.monotonic()
    write_new(claim / "started.json", {"plan_sha256": plan_sha256, "parent_pid": os.getpid(),
                                       "started_at_utc": datetime.now(UTC).isoformat(),
                                       "nonce_sha256": sha(nonce.encode())})
    status, returncode, parent_error = "rejected", None, None
    try:
        completed = subprocess.run(
            [sys.executable, "-B", "-I", str(Path(__file__).resolve()), "worker",
             "--claim", str(claim),
             "--plan-sha256", plan_sha256, "--nonce", nonce],
            timeout=LIMITS["wall_seconds"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env=environment,
        )
        returncode = completed.returncode
        verify_plan(claim, plan_sha256)
        if completed.returncode == 0:
            verify_worker_report(claim)
            status = "accepted"
    except subprocess.TimeoutExpired:
        status = "owned_worker_wall_timeout"
    except Exception as exc:
        parent_error = type(exc).__name__
        raise
    finally:
        failure = claim / "worker-failure.json"
        write_new(claim / "terminal.json", {"status": status, "plan_sha256": plan_sha256,
                  "worker_returncode": returncode, "parent_error_class": parent_error,
                  "worker_failure_sha256": sha(failure.read_bytes()) if failure.is_file() else None,
                  "finished_at_utc": datetime.now(UTC).isoformat(),
                  "wall_elapsed_seconds": time.monotonic() - clock,
                  "claim_consumed": True, "production_admission": False, "new_hpc_jobs": 0})
    return {"status": status, "claim_consumed": True, "production_admission": False}


def verify_worker_report(claim):
    report = read(claim / "worker-result.json")
    catalog = {c["id"]: c for c in control_specs()}
    if (report["status"] != "accepted" or not report["engine_code"]
            or len(report["records"]) != LIMITS["models"]
            or {r["id"] for r in report["records"]} != set(catalog)):
        raise ValueError("Incomplete public control inventory.")
    for row in report["records"]:
        path = claim / (row["id"] + ".json")
        record = read(path)
        if (row["accepted"] is not True or record["accepted"] is not True
                or record["control"] != catalog[row["id"]]
                or record["expected"] != expected(record["control"])
                or sha(path.read_bytes()) != row["sha256"] or not accept_result(
                    record["control"], restore_result(record["result"]))):
            raise ValueError("Collected public evidence differs.")


def collect(claim, plan_sha256):
    claim, _ = verify_plan(claim, plan_sha256)
    terminal = read(claim / "terminal.json")
    if terminal["plan_sha256"] != plan_sha256:
        raise ValueError("Terminal plan binding differs.")
    if terminal.get("worker_failure_sha256") is not None:
        failure = claim / "worker-failure.json"
        if (sha(failure.read_bytes()) != terminal["worker_failure_sha256"]
                or read(failure)["plan_sha256"] != plan_sha256):
            raise ValueError("Worker failure receipt differs.")
    if terminal["status"] == "accepted":
        verify_worker_report(claim)
    return terminal


def restore_result(record):
    from src.logic.optimization import OptimizationResult

    return OptimizationResult(**record)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "execute", "collect", "worker"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--revision")
    parser.add_argument("--license-file", type=Path,
                        help="Preparation only: pin an existing local file for the child process.")
    parser.add_argument("--claim", type=Path)
    parser.add_argument("--plan-sha256")
    parser.add_argument("--ack")
    parser.add_argument("--nonce")
    args = parser.parse_args(argv)
    try:
        if args.license_file is not None and args.action != "prepare":
            raise ValueError("License selection must be frozen during preparation.")
        if args.action == "prepare":
            result = prepare(args.output, args.revision, license_file=args.license_file)
        elif args.action == "execute":
            result = execute(args.claim, args.plan_sha256, args.ack)
        elif args.action == "collect":
            result = collect(args.claim, args.plan_sha256)
        else:
            worker(args.claim, args.plan_sha256, args.nonce)
            return 0
        print(json.dumps(result, allow_nan=False))
        return 0 if result["status"] in {"accepted", "prepared_no_native_execution"} else 1
    except Exception as exc:
        # Native startup/exception text may contain account information. Never emit it.
        print(json.dumps({"status": "rejected", "error_class": type(exc).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
