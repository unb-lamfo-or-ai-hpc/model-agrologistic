"""One operator-authorized native DET/W compatibility test; no scheduler submission.

Historical mathematical builders and independent validation are reused unchanged.
Prepare/collect use the standard library only. Real Gurobi is imported on compute.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from dataclasses import asdict
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
BASE = Path("/home/vrrcelestino/model-agrologistic-hygiene-audit")
CLAIM = BASE / ".mvp3-gurobi14-h215-compat-v2-shared106"
APPROVED_INVENTORY = ROOT / "experiments/gurobi14_shared106_inventory_20261120.json"
ENV_CLAIM = BASE / ".mvp3-gurobi14-environment-v1"
PYTHON = Path("/home/vrrcelestino/venv313_g14/bin/python")
LICENSE = Path("/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic")
INPUT_ROOT = Path("/home/vrrcelestino/model-agrologistic/data/processed")
INPUTS = {
    "model_input.xlsx": (
        "policy_population_v020_osrm/warehouses_215/model_input.xlsx",
        "40edb66585daca9cc393cab1f86bde6d4528a5f34b6afc57260cc1684396da4e",
    ),
    "population.json": (
        "warehouse_population_v020/warehouse_population_manifest.json",
        "4134147f45188d2e8722476dd325b40e584c3746affe99889e045a547d283505",
    ),
    "population.csv": (
        "warehouse_population_v020/warehouse_population_order.csv",
        "7a524b2ed69b41481264d8049842b37e27cd3b96cc20d4e96d98eaf2a39e7903",
    ),
}
ENV_FILES = (
    "original-before.json",
    "original-after.json",
    "clone-before.json",
    "clone-after.json",
    "environment-result.json",
    "pip-report.json",
)
# Initialization/authentication fields are not optimization controls. Never export values.
CONNECTION = {
    "ComputeServer",
    "LicenseID",
    "ServerPassword",
    "ServerTimeout",
    "TokenServer",
    "TSPort",
    "Username",
    "JobID",
    "TLSInsecure",
}
DISPLAY_PARAMS = (
    "TimeLimit",
    "Method",
    "Threads",
    "MIPGap",
    "Seed",
    "ConcurrentMIP",
    "Heuristics",
    "Presolve",
    "FeasibilityTol",
    "IntFeasTol",
    "SoftMemLimit",
    "PDHGGPU",
)
TERMINAL = {
    "COMPLETED",
    "FAILED",
    "CANCELLED",
    "TIMEOUT",
    "OUT_OF_MEMORY",
    "NODE_FAIL",
    "PREEMPTED",
    "BOOT_FAIL",
    "DEADLINE",
    "REVOKED",
}


class CompatibilityError(Exception):
    """A public fixed error code, never a native exception or credential string."""


def require(condition, code):
    if not condition:
        raise CompatibilityError(code)


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def encoded(value):
    return (
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode()


def publish(path, value):
    # A serialization error must not create an empty, misleading receipt.
    raw = encoded(value)
    with Path(path).open("xb") as stream:
        stream.write(raw)


def read(path):
    return json.loads(Path(path).read_bytes())


def parameter_record(value):
    """Represent nonfinite parameter metadata explicitly, without setting a parameter."""
    if isinstance(value, float) and not math.isfinite(value):
        if math.isnan(value):
            return "NaN"
        return "Infinity" if value > 0 else "-Infinity"
    return value


def json_receipt_status(path):
    """Describe incomplete original JSON without modifying it or treating it as accepted."""
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        return {"status": "absent_or_linked", "bytes": None}
    raw = path.read_bytes()
    answer = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    if not raw:
        return {**answer, "status": "empty"}
    def reject_constant(_value):
        raise ValueError("nonstandard_json_number")

    try:
        value = json.loads(raw, parse_constant=reject_constant)
    except (ValueError, UnicodeDecodeError):
        return {**answer, "status": "invalid_json"}
    return {
        **answer,
        "status": "valid_json_object" if isinstance(value, dict) else "nonobject_json",
    }


def audit_defaults(model, parameter_names):
    """Check all exposed nonconnection parameters; disclose only a short safe subset."""
    changed, displayed, checked = [], {}, 0
    for name in sorted(set(parameter_names)):
        if name in CONNECTION or name.startswith(("WLS", "CS", "Cloud", "Worker")):
            continue
        info = model.getParamInfo(name)
        require(info is not None and len(info) == 6, "parameter_introspection_failed")
        checked += 1
        if info[2] != info[5]:
            changed.append(name)
        if name in DISPLAY_PARAMS:
            displayed[name] = parameter_record(info[2])
    require(checked >= len(DISPLAY_PARAMS), "parameter_audit_incomplete")
    require(changed == ["TimeLimit"], "unexpected_nondefault_parameter")
    require(model.getParamInfo("TimeLimit")[2] == 300, "incorrect_native_time_limit")
    return {
        "nondefault_parameters": changed,
        "checked": checked,
        "parameters": displayed,
    }


@contextlib.contextmanager
def silence_native_output():
    """Discard native startup/log text without changing any Gurobi parameter."""
    sys.stdout.flush()
    sys.stderr.flush()
    saved = [os.dup(1), os.dup(2)]
    try:
        with open(os.devnull, "wb") as sink:
            os.dup2(sink.fileno(), 1)
            os.dup2(sink.fileno(), 2)
            yield
    finally:
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        finally:
            for target, original in zip((1, 2), saved, strict=True):
                os.dup2(original, target)
                os.close(original)


def finite_attribute(model, name):
    try:
        value = float(getattr(model, name))
        return value if math.isfinite(value) and abs(value) < 1e100 else None
    except Exception:  # noqa: BLE001 - optional native attributes may raise backend exceptions
        return None


@contextlib.contextmanager
def native_binding(core, gp, env, state, emit):
    """Scope only environment/parameter/observation seams in the unchanged builder."""
    original = {
        name: getattr(core, name)
        for name in ("_import_gurobi", "_apply_solver_parameters", "_optimize_scalar")
    }
    names = [
        getattr(gp.GRB.Param, name)
        for name in dir(gp.GRB.Param)
        if not name.startswith("_") and isinstance(getattr(gp.GRB.Param, name), str)
    ]

    class Proxy:
        def __getattr__(self, name):
            return getattr(gp, name)

        def Model(self, *args, **kwargs):
            require(
                state["models"] == 0 and not kwargs, "multiple_or_reconfigured_model"
            )
            state["models"] += 1
            return gp.Model(*args, env=env)

    def apply(model, config):
        model.setParam("TimeLimit", 300)
        state["initial_parameter_audit"] = audit_defaults(model, names)
        # This describes the queried default; it does not set a native MIPGap.
        config.mip_gap = model.getParamInfo("MIPGap")[2]

    def hook(phase, model, _grb):
        if phase == "native_ready":
            state["model_built"] = True
            state["parameter_audit"] = audit_defaults(model, names)
            emit(
                "native-ready.json",
                {"model_built": True, "parameter_audit": state["parameter_audit"]},
            )
        elif phase == "optimization":
            state["optimization_attempts"] += 1
            require(state["optimization_attempts"] == 1, "multiple_optimize_attempts")
            emit(
                "optimization-entry.json",
                {"scope": "About to call optimize, not proof of return"},
            )
        elif phase == "export_validation":
            state["optimization_returned"] = True
            state["parameter_audit_after"] = audit_defaults(model, names)
            usable = model.SolCount > 0
            state["native"] = {
                "status_code": int(model.Status),
                "solution_count": int(model.SolCount),
                "incumbent": finite_attribute(model, "ObjVal") if usable else None,
                "best_bound": finite_attribute(model, "ObjBound"),
                "mip_gap": finite_attribute(model, "MIPGap") if usable else None,
                "runtime_seconds": finite_attribute(model, "Runtime"),
                "work": finite_attribute(model, "Work"),
                "nodes": finite_attribute(model, "NodeCount"),
                "memory_decimal_gb": finite_attribute(model, "MemUsed"),
                "peak_memory_decimal_gb": finite_attribute(model, "MaxMemUsed"),
            }
            emit("native-return.json", state["native"])

    def optimize(model, grb, *, native_phase_hook=None):
        require(native_phase_hook is None, "unexpected_external_hook")
        return original["_optimize_scalar"](model, grb, native_phase_hook=hook)

    core._import_gurobi = lambda: (Proxy(), gp.GRB)
    core._apply_solver_parameters = apply
    core._optimize_scalar = optimize
    try:
        yield
    finally:
        for name, value in original.items():
            setattr(core, name, value)


def verdict(state):
    if state.get("error"):
        return "NO-GO"
    complete = (
        state.get("license", {}).get("status") == "accepted_designated_wls"
        and state.get("models") == state.get("optimization_attempts") == 1
        and state.get("model_built")
        and state.get("optimization_returned")
        and state.get("native", {}).get("runtime_seconds") is not None
    )
    if not complete:
        return "INCONCLUSIVE"
    native = state["native"]
    if native["status_code"] not in {2, 9, 13}:
        return "NO-GO"
    if native["solution_count"] and state.get("validation_status") != "accepted":
        return "NO-GO"
    return "GO"


def source_inventory(archive, source_sha, archive_sha):
    require(re.fullmatch(r"[0-9a-f]{40}", source_sha), "full_source_sha_required")
    require(digest(archive) == archive_sha, "source_archive_hash_mismatch")
    files, total = {}, 0
    prefix = "model-agrologistic-" + source_sha
    with tarfile.open(archive, "r:gz") as stream:
        for member in stream:
            parts = PurePosixPath(member.name).parts
            require(
                parts and parts[0] == prefix and ".." not in parts,
                "unsafe_archive_path",
            )
            require(member.isfile() or member.isdir(), "unsupported_archive_member")
            if not member.isfile():
                continue
            relative = PurePosixPath(*parts[1:]).as_posix()
            require(
                relative not in files and not relative.endswith(".lic"),
                "unsafe_source_file",
            )
            total += member.size
            require(len(files) < 4096 and total < 96 * 1024**2, "source_archive_size")
            raw = stream.extractfile(member).read()
            files[relative] = hashlib.sha256(raw).hexdigest()
            require(
                digest(ROOT / relative) == files[relative], "extracted_source_differs"
            )
    require(
        "scripts/gurobi14_h215_compat.py" in files, "controller_missing_from_source"
    )
    return files


def verify_files(root, files):
    for name, expected in files.items():
        path = Path(root) / name
        require(
            not path.is_symlink() and digest(path) == expected, "frozen_file_changed"
        )


def environment_receipt():
    checks = {}
    for line in (ENV_CLAIM / "SHA256SUMS").read_text().splitlines():
        checksum, name = line.split("  ", 1)
        require(name in ENV_FILES and name not in checks, "invalid_environment_ledger")
        checks[name] = checksum
    require(set(checks) == set(ENV_FILES), "incomplete_environment_ledger")
    verify_files(ENV_CLAIM, checks)
    result = read(ENV_CLAIM / "environment-result.json")
    require(
        result["status"] == "cloned_environment_verified"
        and result["original_environment_preserved"] is True
        and result["only_changed_distribution"] == "gurobipy"
        and result["source_version"] == "13.0.3"
        and result["target_version"] == "14.0.0"
        and result["new_prefix"] == str(PYTHON.parent.parent),
        "clone_receipt_rejected",
    )
    return checks



def distribution_inventory():
    """Read installed metadata only; do not import packages or open a WLS session."""
    packages = {}
    for distribution in importlib.metadata.distributions():
        name = re.sub(r"[-_.]+", "-", distribution.metadata["Name"]).lower()
        require(name not in packages, "duplicate_distribution_metadata")
        metadata = distribution.read_text("METADATA")
        require(metadata is not None, "missing_distribution_metadata")
        packages[name] = {
            "version": distribution.version,
            "metadata_sha256": hashlib.sha256(metadata.encode()).hexdigest(),
        }
    return packages


def runtime_snapshot():
    """Attest the separately approved shared inventory, never rewrite clone history."""
    expected = read(APPROVED_INVENTORY)
    require(
        expected["distribution_count"] == 106
        and len(expected["packages"]) == 106
        and expected["packages"]["gurobipy"] == "14.0.0",
        "invalid_shared_baseline_specification",
    )
    after = read(ENV_CLAIM / "clone-after.json")
    require(
        platform.python_version() == expected["python"] == after["python"] == "3.13.15",
        "python_changed",
    )
    require(
        sys.prefix == expected["prefix"] == str(PYTHON.parent.parent),
        "wrong_runtime_prefix",
    )
    require(digest(sys.executable) == after["python_sha256"], "python_binary_changed")
    packages = distribution_inventory()
    require(
        {key: value["version"] for key, value in packages.items()} == expected["packages"],
        "shared_distribution_versions_changed",
    )
    return {
        "baseline_id": expected["baseline_id"],
        "specification_sha256": digest(APPROVED_INVENTORY),
        "historical_clone_receipt_sha256": digest(ENV_CLAIM / "clone-after.json"),
        "python": platform.python_version(),
        "python_sha256": digest(sys.executable),
        "prefix": sys.prefix,
        "distribution_count": len(packages),
        "packages": packages,
        "scope": "Installed versions and METADATA hashes; not all installed package bytes",
        "original_69_package_baseline_preserved": True,
    }


def verify_runtime_snapshot():
    frozen = read(CLAIM / "runtime-baseline.json")
    require(runtime_snapshot() == frozen, "shared_runtime_metadata_changed")
    return frozen


def batch_text(claim, source_sha):
    q = shlex.quote
    return f"""#!/bin/bash
#SBATCH --job-name=agro-g14-h215-compat
#SBATCH --partition=intel-256
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --hint=nomultithread
#SBATCH --exclusive
#SBATCH --no-requeue
#SBATCH --mem=196608M
#SBATCH --time=01:00:00
#SBATCH --chdir={claim}
#SBATCH --output={claim}/slurm-%j.out
#SBATCH --error={claim}/slurm-%j.err
set -euo pipefail
umask 077
export PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1
export GRB_LICENSE_FILE={q(str(LICENSE))}
export TMPDIR={q(str(claim / "tmp"))}
export XDG_CACHE_HOME={q(str(claim / "cache"))}
export CUDA_VISIBLE_DEVICES=''
unset OMP_NUM_THREADS MKL_NUM_THREADS OPENBLAS_NUM_THREADS
trap 'code=$?; printf "{{\\"exit_code\\":%s}}\\n" "$code" > {claim}/batch-exit.json' EXIT
srun --ntasks=1 --cpus-per-task=32 --cpu-bind=cores --hint=nomultithread \\
  {q(str(PYTHON))} -B -I {q(str(ROOT / "scripts/gurobi14_h215_compat.py"))} \\
  run --source-sha {q(source_sha)}
"""


def prepare(args):
    require(not os.environ.get("SLURM_JOB_ID"), "login_only_preparation")
    require(
        ROOT.is_relative_to(BASE) and not ROOT.is_symlink(),
        "source_outside_audit_project",
    )
    require(
        not CLAIM.exists() and not CLAIM.is_symlink(), "preserve_existing_test_claim"
    )
    inventory = source_inventory(args.archive, args.source_sha, args.archive_sha256)
    environment = environment_receipt()
    runtime = runtime_snapshot()
    require(args.expected_license_id > 0, "license_identity_required")
    CLAIM.mkdir()
    publish(CLAIM / "runtime-baseline.json", runtime)
    (CLAIM / "input").mkdir()
    (CLAIM / "tmp").mkdir()
    (CLAIM / "cache").mkdir()
    for name, (relative, expected) in INPUTS.items():
        path = INPUT_ROOT / relative
        require(
            not path.is_symlink() and digest(path) == expected,
            "original_input_hash_mismatch",
        )
        shutil.copyfile(path, CLAIM / "input" / name)
    inputs = {name: value[1] for name, value in INPUTS.items()}
    verify_files(CLAIM / "input", inputs)
    batch = batch_text(CLAIM, args.source_sha)
    with (CLAIM / "job.sh").open("x") as stream:
        stream.write(batch)
    plan = {
        "source_sha": args.source_sha,
        "source_root": str(ROOT),
        "source_archive_sha256": args.archive_sha256,
        "source_files": inventory,
        "inputs": inputs,
        "environment_files": environment,
        "runtime_baseline_sha256": digest(CLAIM / "runtime-baseline.json"),
        "runtime_baseline_id": runtime["baseline_id"],
        "predecessor_job_id": "2278573",
        "predecessor_claim": str(BASE / ".mvp3-gurobi14-h215-compat-v1"),
        "expected_license_id": args.expected_license_id,
        "job_sha256": digest(CLAIM / "job.sh"),
        "optimization_parameters": {"TimeLimit": 300},
        "mode": "det",
        "topology": "W",
        "population": 215,
        "memory_mib": 196608,
        "wall_seconds": 3600,
    }
    publish(CLAIM / "plan.json", plan)
    return {
        "status": "prepared_no_job",
        "claim": str(CLAIM),
        "new_jobs": 0,
        "plan_sha256": digest(CLAIM / "plan.json"),
    }


def load_plan(source_sha):
    plan = read(CLAIM / "plan.json")
    require(
        plan["source_sha"] == source_sha and plan["source_root"] == str(ROOT),
        "source_drift",
    )
    verify_files(ROOT, plan["source_files"])
    verify_files(CLAIM / "input", plan["inputs"])
    verify_files(ENV_CLAIM, plan["environment_files"])
    require(
        digest(CLAIM / "runtime-baseline.json") == plan["runtime_baseline_sha256"],
        "runtime_baseline_receipt_changed",
    )
    require(digest(CLAIM / "job.sh") == plan["job_sha256"], "batch_drift")
    return plan


def scientific_input():
    from scripts import mvp2_warehouse_receipt as warehouses
    from src.logic.excel_loader import load_model_data_from_excel
    from src.logic.experiment_runner import load_experiment_manifest
    from src.logic.mathematical_contract import prepare_model_data
    from src.logic.route_filtering import select_routes

    spec = load_experiment_manifest(
        ROOT / "experiments/mvp2_scalar_r3a_h215.yaml"
    ).experiments[0]
    require(
        spec.model.mode == "det" and not spec.model.use_direct_origin_customer,
        "wrong_model",
    )
    selection = warehouses.read_policy(
        CLAIM / "input/population.json",
        CLAIM / "input/population.csv",
        INPUTS["population.json"][1],
        INPUTS["population.csv"][1],
        215,
    )
    data = prepare_model_data(
        load_model_data_from_excel(CLAIM / "input/model_input.xlsx", spec.loader),
        spec.model,
    )
    membership = warehouses.membership_receipt(data, selection)
    routes = select_routes(data, spec.model)
    require(
        len(data.warehouses) == 215 and len(data.periods) == 60,
        "instance_shape_changed",
    )
    require(
        [len(routes.od), len(routes.dc), len(routes.dd), len(routes.oc)]
        == [3182, 3440, 18490, 0],
        "selected_network_changed",
    )
    contract = data.metadata["mathematical_contract"]
    require(
        contract["penalty_vector_sha256"]
        == "e0f93593659c35d14b85cdaddecbe020edb375376f5e30ae99b05bed876d276f",
        "historical_penalty_vector_changed",
    )
    publish(
        CLAIM / "input-receipt.json",
        {
            "model": asdict(spec.model),
            "loader": asdict(spec.loader),
            "workbook_sha256": INPUTS["model_input.xlsx"][1],
            "included_population_sha256": hashlib.sha256(
                encoded(membership)
            ).hexdigest(),
            "selected_network_sha256": contract["selected_network_sha256"],
            "penalty_vector_sha256": contract["penalty_vector_sha256"],
        },
    )
    return data, spec.model


def run(source_sha):
    # All real execution remains inaccessible from login, local tests and CI.
    require(
        sys.platform == "linux" and os.environ.get("SLURM_JOB_ID", "").isdigit(),
        "compute_only",
    )
    require(not os.environ.get("SLURM_ARRAY_TASK_ID"), "no_array_allowed")
    require(Path(sys.prefix).resolve() == PYTHON.parent.parent, "wrong_interpreter")
    require(
        Path.cwd() == CLAIM and not (CLAIM / "gurobi.env").exists(),
        "unsafe_runtime_directory",
    )
    job = (CLAIM / "job-id.txt").read_text().strip()
    require(job == os.environ["SLURM_JOB_ID"], "unowned_job")
    intent = read(CLAIM / "submission-intent.json")
    require(
        intent["source_sha"] == source_sha
        and intent["plan_sha256"] == digest(CLAIM / "plan.json")
        and intent["new_jobs"] == 1,
        "submission_intent_differs",
    )
    require(os.environ.get("SLURM_JOB_PARTITION") == "intel-256", "wrong_partition")
    require(os.environ.get("SLURM_MEM_PER_NODE") == "196608", "wrong_memory_request")
    require(
        os.environ.get("GRB_LICENSE_FILE") == str(LICENSE), "wrong_license_selection"
    )
    plan = load_plan(source_sha)
    publish(
        CLAIM / "started.json",
        {"job_id": job, "plan_sha256": digest(CLAIM / "plan.json")},
    )
    state = {
        "source_sha": source_sha,
        "command": [
            str(PYTHON),
            "-B",
            "-I",
            str(Path(__file__).resolve()),
            "run",
            "--source-sha",
            source_sha,
        ],
        "plan_sha256": digest(CLAIM / "plan.json"),
        "job_id": job,
        "models": 0,
        "optimization_attempts": 0,
        "model_built": False,
        "optimization_returned": False,
        "license": {"status": "not_tested"},
        "validation_status": "not_applicable",
        "stage": "environment_check",
    }
    started, env = time.monotonic(), None
    with silence_native_output():
        try:
            runtime = verify_runtime_snapshot()
            state["stage"] = "input_preparation"
            sys.path.insert(0, str(ROOT))
            data, model_config = scientific_input()
            import gurobipy as gp

            from src.logic import optimization_gurobipy_stochastic as core
            from src.logic.model_config import SolverConfig
            from src.logic.optimization_gurobipy import solve_model_gurobipy
            from src.logic.solution_validation import validate_solution

            require(tuple(gp.gurobi.version()) == (14, 0, 0), "wrong_loaded_gurobi")
            require(
                Path(gp.__file__).resolve().is_relative_to(PYTHON.parent.parent),
                "gurobi_loaded_outside_clone",
            )
            for module in list(sys.modules.values()):
                name = getattr(module, "__name__", "")
                file = getattr(module, "__file__", None)
                if name.startswith(("src.logic.", "scripts.mvp2_")) and file:
                    require(
                        Path(file).resolve().is_relative_to(ROOT),
                        "editable_source_leak",
                    )
            state["environment"] = {
                "python": platform.python_version(),
                "prefix": sys.prefix,
                "executable": sys.executable,
                "gurobi": list(gp.gurobi.version()),
                "clone_receipt_sha256": digest(ENV_CLAIM / "environment-result.json"),
                "runtime_baseline_sha256": plan["runtime_baseline_sha256"],
                "runtime_baseline_id": runtime["baseline_id"],
                "distribution_count": runtime["distribution_count"],
                "affinity_logical_cpus": sorted(os.sched_getaffinity(0)),
                "gpu_requested": False,
            }
            state["stage"] = "license_start"
            env = gp.Env(empty=True)
            env.start()
            require(
                env.getParam("LicenseID") == plan["expected_license_id"]
                and bool(env.getParam("WLSAccessID")),
                "designated_wls_not_recognized",
            )
            require(
                not any(
                    env.getParam(p)
                    for p in ("ComputeServer", "CSManager", "CloudAccessID")
                ),
                "remote_execution_outside_scope",
            )
            state["license"] = {"status": "accepted_designated_wls"}
            state["stage"] = "native_construction_and_optimization"
            config = SolverConfig(
                backend="gurobipy",
                solver_name="gurobi",
                time_limit=300,
                threads=None,
                seed=None,
                tee=True,
                compute_iis=False,
                solver_options={},
                collect_resource_diagnostics=False,
                compact_python_indices=False,
            )
            with native_binding(
                core, gp, env, state, lambda n, v: publish(CLAIM / n, v)
            ):
                result = solve_model_gurobipy(data, model_config, config)
            env.dispose()
            env = None
            state["native"]["status_name"] = result.metadata["gurobi_status_name"]
            state["stage"] = "independent_validation"
            if state["native"]["solution_count"]:
                validation = validate_solution(data, model_config, result)
                publish(CLAIM / "independent-validation.json", validation)
                state["validation_status"] = validation["status"]
            load_plan(source_sha)
            verify_runtime_snapshot()
            state["stage"] = "complete"
        except BaseException as error:  # noqa: BLE001 - sanitize all native failure paths
            state["error"] = {"kind": type(error).__name__}
            if isinstance(error, CompatibilityError):
                state["error"]["code"] = str(error)
            number = getattr(error, "errno", None)
            if isinstance(number, int):
                state["error"]["native_or_os_error_code"] = number
            if state["stage"] == "license_start":
                state["license"] = {"status": "rejected_or_unverified"}
        finally:
            if env is not None:
                try:
                    env.dispose()
                except Exception:  # noqa: BLE001 - never expose native cleanup exception text
                    state["error"] = {"kind": "EnvironmentDisposalError"}
    import resource

    state["worker_peak_rss_bytes"] = (
        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    )
    state["worker_peak_rss_scope"] = (
        "Entire Linux Python worker, including construction/validation"
    )
    state["end_to_end_seconds"] = time.monotonic() - started
    state["native_memory_scope"] = (
        "Gurobi attributes in decimal GB; distinct from worker RSS"
    )
    state["verdict"] = verdict(state)
    publish(CLAIM / "result.json", state)
    files = [p for p in CLAIM.glob("*.json") if p.name != "plan.json"] + [
        CLAIM / "plan.json"
    ]
    with (CLAIM / "SHA256SUMS").open("x") as stream:
        for path in sorted(files):
            stream.write(digest(path) + "  " + path.name + "\n")
    print(json.dumps(state, indent=2, allow_nan=False))
    return 0 if state["verdict"] == "GO" else 1


def collect(source_sha):
    require(not os.environ.get("SLURM_JOB_ID"), "login_only_collection")
    load_plan(source_sha)
    job = (CLAIM / "job-id.txt").read_text().strip()
    require(job.isdigit(), "invalid_job_identity")
    completed = subprocess.run(
        [
            "sacct",
            "-j",
            job,
            "--parsable2",
            "--format=JobIDRaw,State%30,ElapsedRaw,ExitCode,ReqMem,MaxRSS,AllocCPUS,NodeList",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    root = [
        line.split("|")
        for line in completed.stdout.splitlines()
        if line.startswith(job + "|")
    ]
    if not root or root[0][1].split()[0] not in TERMINAL:
        return {"status": "nonterminal_or_accounting_pending", "job_id": job}
    target = Path(tempfile.mkdtemp(prefix="gurobi14-h215-readback-", dir=BASE))
    (target / "sacct.txt").write_text(completed.stdout)
    names = [
        "runtime-baseline.json",
        "release.stdout",
        "release.stderr",
        "plan.json",
        "started.json",
        "input-receipt.json",
        "native-ready.json",
        "optimization-entry.json",
        "native-return.json",
        "independent-validation.json",
        "result.json",
        "SHA256SUMS",
        "batch-exit.json",
        "job-id.txt",
        "job.sh",
        "submission-intent.json",
        "submission.stdout",
        "submission.stderr",
        "slurm-" + job + ".out",
        "slurm-" + job + ".err",
    ]
    for name in names:
        path = CLAIM / name
        if path.is_file() and not path.is_symlink():
            shutil.copyfile(path, target / name)
    ledger = CLAIM / "SHA256SUMS"
    verified = None
    if ledger.is_file():
        checks = {}
        for line in ledger.read_text().splitlines():
            checksum, name = line.split("  ", 1)
            require(name in names and name not in checks, "invalid_result_ledger")
            checks[name] = checksum
        try:
            verify_files(CLAIM, checks)
            verified = True
        except CompatibilityError:
            verified = False
    publish(
        target / "collection-review.json",
        {
            "receipt_hashes_verified": verified,
            "compatibility_verdict": "pending_original_receipt_review",
            "json_receipts": {
                name: json_receipt_status(target / name)
                for name in (
                    "result.json", "native-ready.json", "optimization-entry.json",
                    "native-return.json", "independent-validation.json",
                )
            },
        },
    )
    files = [p for p in target.iterdir() if p.is_file()]
    with (target / "TRANSFER_SHA256SUMS").open("x") as stream:
        for path in sorted(files):
            stream.write(digest(path) + "  " + path.name + "\n")
    return {
        "status": "original_receipts_copied",
        "transfer_dir": str(target),
        "job_id": job,
        "scheduler_root_state": root[0][1],
        "native_result_present": (target / "result.json").is_file(),
        "native_result_json_status": json_receipt_status(target / "result.json"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "run", "collect"))
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--archive-sha256")
    parser.add_argument("--expected-license-id", type=int)
    args = parser.parse_args()
    try:
        if args.action == "run":
            return run(args.source_sha)
        result = prepare(args) if args.action == "prepare" else collect(args.source_sha)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except Exception as error:  # noqa: BLE001 - public CLI must redact arbitrary exception text
        # Never expose unrestricted exception text from native APIs or process calls.
        result = {
            "status": "stopped_preserve_claim_no_retry",
            "error_kind": type(error).__name__,
        }
        if isinstance(error, CompatibilityError):
            result["code"] = str(error)
        print(json.dumps(result, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
