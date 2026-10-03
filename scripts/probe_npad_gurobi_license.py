"""Check the designated NPAD license without exporting credentials or native logs."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

LICENSE_FILE = "/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic"
PROBE_SIZE = 2001


def check_file():
    """Check file metadata/access only; never read or hash license contents."""
    if os.environ.get("GRB_LICENSE_FILE") != LICENSE_FILE:
        raise ValueError("GRB_LICENSE_FILE must select the designated NPAD license.")
    if not Path(LICENSE_FILE).is_file() or not os.access(LICENSE_FILE, os.R_OK):
        raise ValueError("The designated NPAD license is missing or unreadable.")


def probe():
    """Exceed the bundled 2000-variable/constraint limit before a large build."""
    record = {
        "schema_version": "npad-gurobi-license-capability-v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "license_file": LICENSE_FILE,
        "status": "rejected", "large_model_construction_allowed": False,
        "probe_variable_count": PROBE_SIZE, "probe_constraint_count": PROBE_SIZE,
        "qualification": "License capability only; not scientific or performance acceptance.",
    }
    try:
        check_file()
        import gurobipy as gp

        # Silence startup BEFORE license initialization, including WLS parameters.
        with gp.Env(empty=True) as env:
            env.setParam("OutputFlag", 0)
            env.start()
            with gp.Model("npad_license_capability", env=env) as model:
                model.Params.TimeLimit = 10
                model.Params.Threads = 1
                variables = model.addVars(PROBE_SIZE, lb=0, ub=2)
                model.addConstrs(variables[i] >= 1 for i in range(PROBE_SIZE))
                model.setObjective(gp.quicksum(variables.values()), gp.GRB.MINIMIZE)
                model.optimize()
                record["solver_status_code"] = model.Status
                if model.Status == gp.GRB.OPTIMAL and model.SolCount:
                    record["objective_value"] = model.ObjVal
                    if abs(model.ObjVal - PROBE_SIZE) <= 1e-6:
                        record.update(status="accepted", large_model_construction_allowed=True)
                record["gurobi_version"] = list(gp.gurobi.version())
    except Exception as error:
        # Exception strings may contain connection details. Export only safe codes.
        record["error_type"] = type(error).__name__
        code = getattr(error, "errno", None)
        if isinstance(code, int):
            record["error_code"] = code
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-file", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.check_file:
        check_file()
        print("NPAD GUROBI LICENSE PATH: VERIFIED")
        return 0
    if args.output is None:
        parser.error("Require a new capability-report output path.")
    record = probe()
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(record, indent=2, allow_nan=False) + "\n")
    print(f"NPAD GUROBI LICENSE CAPABILITY: {record['status'].upper()}")
    return int(record["status"] != "accepted")


if __name__ == "__main__":
    raise SystemExit(main())
