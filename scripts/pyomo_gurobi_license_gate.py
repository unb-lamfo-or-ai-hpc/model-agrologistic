"""Compute-only Gurobi default-environment admission for the large Pyomo arm.

The public LP exceeds the bundled restricted-license size. It is neither the
h215 instance nor a performance observation. Never export license contents,
exception messages or native startup output.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from scripts import probe_npad_gurobi_license as policy

SCHEMA = "pyomo-gurobi-default-license-v1"


def compute_context():
    """Reject the login node before importing a native engine."""
    job, step = os.environ.get("SLURM_JOB_ID", ""), os.environ.get("SLURM_STEP_ID", "")
    if not job.isdecimal() or int(job) <= 0 or not step.isdecimal():
        raise ValueError("An owned numeric compute step is required.")


def probe():
    """Test the SAME default environment used by APPSI, before private construction."""
    record = {
        "schema_version": SCHEMA,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": "rejected",
        "large_model_construction_allowed": False,
        "environment_scope": "gurobipy_default_environment_as_used_by_appsi",
        "probe_variable_count": policy.PROBE_SIZE,
        "probe_constraint_count": policy.PROBE_SIZE,
        "private_input_accessed": False,
        "qualification": "Public license capacity only; no h215 or performance acceptance.",
    }
    try:
        compute_context()
        record["compute_identity"] = {
            "job_id": os.environ.get("SLURM_JOB_ID"),
            "step_id": os.environ.get("SLURM_STEP_ID"),
        }
        policy.check_file()
        # Import only after the compute and designated-file metadata guards.
        from pyomo.common.tee import capture_output

        # Default environment startup can print credential parameters before a
        # model-level OutputFlag exists. Discard both Python and native output.
        with capture_output(capture_fd=True):
            import gurobipy as gp

            record["gurobi_version"] = list(gp.gurobi.version())
            if record["gurobi_version"] != [13, 0, 3]:
                raise ValueError("Pinned native Gurobi required.")
            # No custom Env: APPSI creates gp.Model() with this default environment.
            # Dispose this probe model only, never the process default environment.
            with gp.Model("pyomo_public_license_capacity") as model:
                model.Params.OutputFlag = 0
                model.Params.TimeLimit = 10
                model.Params.Threads = 1
                x = model.addVars(policy.PROBE_SIZE, lb=0, ub=2)
                model.addConstrs(x[i] >= 1 for i in range(policy.PROBE_SIZE))
                model.setObjective(gp.quicksum(x.values()), gp.GRB.MINIMIZE)
                model.optimize()
                record["solver_status_code"] = model.Status
                if model.Status == gp.GRB.OPTIMAL and model.SolCount:
                    record["objective_value"] = model.ObjVal
                    if abs(model.ObjVal - policy.PROBE_SIZE) <= 1e-6:
                        record.update(status="accepted", large_model_construction_allowed=True)
    except Exception as error:
        # Strings can contain license/server details; types and integer codes suffice.
        record["error_type"] = type(error).__name__
        code = getattr(error, "errno", None)
        if isinstance(code, int):
            record["error_code"] = code
    return record


def accepted(record):
    """Replay the capacity proof, rather than trusting its status label."""
    return (
        record.get("schema_version") == SCHEMA
        and record.get("status") == "accepted"
        and record.get("large_model_construction_allowed") is True
        and record.get("environment_scope") == "gurobipy_default_environment_as_used_by_appsi"
        and record.get("probe_variable_count") == policy.PROBE_SIZE
        and record.get("probe_constraint_count") == policy.PROBE_SIZE
        and record.get("private_input_accessed") is False
        and record.get("gurobi_version") == [13, 0, 3]
        and record.get("solver_status_code") == 2
        and isinstance(record.get("objective_value"), (int, float))
        and abs(record["objective_value"] - policy.PROBE_SIZE) <= 1e-6
        and "error_type" not in record
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    compute_context()
    record = probe()
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(record, indent=2, allow_nan=False) + "\n")
    print(json.dumps(record, allow_nan=False))
    return int(not accepted(record))


if __name__ == "__main__":
    raise SystemExit(main())

