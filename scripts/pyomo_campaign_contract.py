"""Read-only qualification and native evidence contracts for new Pyomo W arms."""

import hashlib
import json
import re
import subprocess
from pathlib import Path

SOURCE = "f166f60c1600057dea2a4538ef7e6c2aed372dd8"
PLAN = "dc41c8b7f151b5d22d1b65b94f787e09415c6cfc50a691ea696e1da266a73ea6"
CBC_SHA = "d7b39260dc23a7b8441db4511242d6bb314f9deb97d5d44bcd6561774587517e"
OPERATIONAL_CLAIM = ".mvp2-pyomo-h215-operational-qualification-v1"
OPERATIONAL_TESTS = 282
PACKAGES = {"pyomo": "6.10.1", "gurobipy": "13.0.3", "pyscipopt": "6.2.1", "highspy": "1.15.1"}
INTERFACES = {"gurobi": "appsi_gurobi", "scip": "pyscipopt_linear", "cbc": "cbc"}
VERSIONS = {
    "gurobi": {"pyomo": "6.10.1", "gurobipy": "13.0.3"},
    "scip": {"pyomo": "6.10.1", "pyscipopt": "6.2.1", "scip": "10.0.2"},
    "cbc": {"pyomo": "6.10.1", "cbc": "2.10.13.0"},
}
PARAMETERS = {
    "gurobi": {
        "TimeLimit": 28800,
        "MIPGap": 0.01,
        "Threads": 4,
        "Seed": 42,
        "FeasibilityTol": 1e-9,
        "IntFeasTol": 1e-9,
        "Presolve": -1,
        "Method": -1,
        "NodeMethod": -1,
        "Heuristics": 0.05,
        "Cuts": -1,
        "ConcurrentMIP": 1,
    },
    "scip": {
        "limits/time": 28800,
        "limits/gap": 0.01,
        "limits/absgap": 1e-10,
        "timing/clocktype": 2,
        "numerics/feastol": 1e-9,
        "parallel/maxnthreads": 4,
        "lp/threads": 4,
        "randomization/randomseedshift": 42,
        "randomization/permutationseed": 0,
        "randomization/lpseed": 0,
    },
    "cbc": {
        "timeMode": "elapsed",
        "ratio": 0.01,
        "threads": 4,
        "randomSeed": 42,
        "randomCbcSeed": 42,
        "primalTolerance": 1e-9,
        "integerTolerance": 1e-9,
        "seconds": 28800,
    },
}


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def regular(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), "Regular qualification receipt required.")
    return path


def qualification(plan_raw, result_raw):
    """Validate the original accepted public control, without running its code."""
    require(hashlib.sha256(plan_raw).hexdigest() == PLAN, "Public qualification plan differs.")
    plan, result = json.loads(plan_raw), json.loads(result_raw)
    require(
        plan["source_commit"] == result["source_commit"] == SOURCE
        and result["job_id"] == "2227458"
        and result["plan_sha256"] == PLAN
        and result["pytest_exit"] == 0
        and result["status"] == "accepted"
        and result["counts"] == {"tests": 168, "failures": 0, "errors": 0, "skipped": 0}
        and result["source_verified_after"] is True
        and result["failed_tests"] == []
        and result["private_h215_execution_admitted"] is False
        and plan["private_h215_execution_admitted"] is False
        and plan["packages"] == PACKAGES
        and plan["cbc_sha256"] == CBC_SHA,
        "Accepted original public qualification differs.",
    )
    return plan


def read_qualification(base):
    directory = base / ".mvp2-pyomo-adapter-qualification-v2"
    require(directory.is_dir() and not directory.is_symlink(), "Preserve qualification v2.")
    raw = {name: regular(directory / name).read_bytes() for name in ("plan.json", "result.json")}
    plan = qualification(raw["plan.json"], raw["result.json"])
    binary = regular(directory / "cbc-bin/cbc")
    require(digest(binary) == CBC_SHA, "Qualified CBC binary differs.")
    return raw, plan, binary


def operational_qualification(plan_raw, result_raw, source_files):
    plan, result = json.loads(plan_raw), json.loads(result_raw)
    require(
        plan["schema_version"] == "public-pyomo-operational-qualification-v1"
        and plan["predecessor"]["plan_sha256"] == PLAN
        and result["source_commit"] == plan["source_commit"]
        and result["plan_sha256"] == hashlib.sha256(plan_raw).hexdigest()
        and re.fullmatch(r"[1-9][0-9]*", result["job_id"])
        and result["pytest_exit"] == 0
        and result["status"] == "accepted"
        and result["counts"]
        == {"tests": OPERATIONAL_TESTS, "failures": 0, "errors": 0, "skipped": 0}
        and result["source_verified_after"] is True
        and result["failed_tests"] == []
        and result["private_h215_execution_admitted"] is False
        and plan["private_h215_execution_admitted"] is False,
        "Operational public qualification not accepted.",
    )
    capability = result["cbc_capability"]
    require(
        capability["binary_sha256"] == CBC_SHA
        and type(capability["threads_option_accepted"]) is bool
        and capability["cbc_arm_cancelled"] is (not capability["threads_option_accepted"]),
        "CBC arm decision missing or inconsistent.",
    )

    def executables(files):
        return {k: v for k, v in files.items() if k.startswith(("src/", "scripts/", "tests/"))}

    require(
        executables(source_files) == executables(plan["source_files"]),
        "Operational-qualified source bytes differ.",
    )
    return plan


def read_operational(base, source_files):
    directory = base / OPERATIONAL_CLAIM
    require(
        directory.is_dir() and not directory.is_symlink(), "Operational qualification required."
    )
    raw = {name: regular(directory / name).read_bytes() for name in ("plan.json", "result.json")}
    operational_qualification(raw["plan.json"], raw["result.json"], source_files)
    return raw


def cbc_acknowledgements(log):
    """Check retained option acknowledgements; not native in-process introspection."""
    require(
        not re.search(r"No match for|Unknown option|Unable to open|not recognized", log, re.I),
        "CBC rejected a command-line option.",
    )
    acknowledgements = {}
    for name, expected in PARAMETERS["cbc"].items():
        label = "ratioGap" if name == "ratio" else name
        pattern = rf"{label} (?:was )?changed from \S+ to (\S+)"
        matches = re.findall(pattern, log, re.I)
        require(matches, "Missing CBC option acknowledgement: " + name)
        value = matches[-1]
        require(
            value == expected if isinstance(expected, str) else float(value) == expected,
            "CBC option acknowledgement differs: " + name,
        )
        acknowledgements[name] = value
    return {
        "scope": "Retained CBC log acknowledgements, not native option introspection",
        "acknowledgements": acknowledgements,
    }


def probe_cbc(executable):
    """Compute-only option probe; no model, optimize or scheduler command."""
    executable = regular(executable)
    process = subprocess.run(
        [str(executable), "-threads", "4", "-quit"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    log = process.stdout + process.stderr
    require(process.returncode == 0, "CBC capability probe failed.")
    accepted = bool(re.search(r"threads (?:was )?changed from \S+ to 4(?:\s|$)", log, re.I))
    require(accepted or "No match for threads" in log, "Unknown CBC thread capability.")
    return {
        "binary_sha256": digest(executable),
        "returncode": process.returncode,
        "threads_option_accepted": accepted,
        "cbc_arm_cancelled": not accepted,
        "stdout": process.stdout,
        "stderr": process.stderr,
        "scope": "Option capability only; no population model or optimization",
    }


def metadata(solver, value, *, cbc_log=None, large=True):
    require(
        value["pyomo_solver_interface"] == INTERFACES[solver]
        and value["solver_versions"] == VERSIONS[solver],
        "Native interface/version differs.",
    )
    proof = value["pyomo_reformulation"]
    require(
        proof["policy"] == "bounded_scalar_slacks_v1"
        and proof["equivalence"] == "physical_investment_projection_and_optimal_scalar_value"
        and proof["entire_redundant_slack_region_preserved"] is False
        and re.fullmatch(r"[0-9a-f]{64}", proof["bounds_sha256"])
        and type(proof["candidate_slack_bounds"]) is int
        and proof["candidate_slack_bounds"] >= 0
        and 0 <= proof["maximum_bound"] < float("inf"),
        "Reformulation provenance differs.",
    )
    matrix = value["common_linear_matrix"]
    require(
        matrix["schema_version"] == "ordered-pyomo-linear-matrix-v1"
        and re.fullmatch(r"[0-9a-f]{64}", matrix["sha256"]),
        "Common matrix identity missing.",
    )
    if large:
        require(
            matrix["variables"] == 14054654
            and matrix["binary_variables"] == 307
            and matrix["linear_constraints"] == 735577,
            "Common h215 matrix size differs.",
        )
    if solver == "cbc":
        require(
            value["effective_native_options"] is None
            and value["requested_cbc_options"] == PARAMETERS[solver],
            "CBC request differs.",
        )
        require(cbc_log is not None, "Retained CBC log required.")
        return cbc_acknowledgements(cbc_log)
    require(value["effective_native_options"] == PARAMETERS[solver], "Effective parameters differ.")
    return {
        "scope": "Native in-process option introspection",
        "effective_parameters": value["effective_native_options"],
    }
