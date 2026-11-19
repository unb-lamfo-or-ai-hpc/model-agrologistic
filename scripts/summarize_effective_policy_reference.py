"""Read accepted h215 W vectors into national product/scenario policy tables."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.logic.effective_baseline import dump, load_bundle, sha256, write_csv  # noqa: E402

CASES = {
    "scalar_h215_det": ("scalar-h215-evidence", "det", "historical_native"),
    "scalar_h215_sto": ("scalar-h215-evidence", "sto", "historical_native"),
    "pyomo_gurobi_h215_w_native8h_license_v2": (
        "pyomo-gurobi-h215-w-native8h-license-v2-evidence",
        "sto",
        "historical_pyomo",
    ),
}


def summarize(data, mode, folder):
    scenarios = data.scenarios if mode == "sto" else ["deterministic"]
    values = defaultdict(list)
    for name in ("flows", "unmet_demand", "inventories"):
        with (folder / f"{name}.csv").open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                s = row.get("scenario") if mode == "sto" else "deterministic"
                p, t = row["product"], row["period"]
                value = float(row["value"])
                if s not in scenarios or p not in data.products or t not in data.periods:
                    raise ValueError("Unknown vector index.")
                if not math.isfinite(value) or value < 0:
                    raise ValueError("Invalid retained vector value.")
                if name == "flows" and row["route_type"] == "DC":
                    c = row["customer"]
                    kind = "served" if c in data.domestic_customers else "export"
                    if c not in data.customers:
                        raise ValueError("Unknown destination role.")
                    values[s, p, kind].append(value)
                elif name == "flows" and row["route_type"] == "OC":
                    raise ValueError("This reference is restricted to W topology.")
                elif name == "unmet_demand":
                    if row["customer"] not in data.domestic_customers:
                        raise ValueError("Unknown shortage destination.")
                    values[s, p, "unmet"].append(value)
                    values[s, p, "shortage_penalty"].append(
                        value * data.unmet_demand_penalty[row["customer"], p]
                    )
                elif name == "inventories" and t == data.periods[-1]:
                    values[s, p, "terminal_stock"].append(value)
    rows = []
    for s in scenarios:
        for p in data.products:
            total = {
                kind: math.fsum(values[s, p, kind])
                for kind in ("served", "export", "unmet", "terminal_stock", "shortage_penalty")
            }
            demand = math.fsum(
                (data.demand_dom_s[s, c, p, t] if mode == "sto" else data.demand_dom[c, p, t])
                for c in data.domestic_customers
                for t in data.periods
            )
            supply = math.fsum(
                (data.supply_s[s, o, p, t] if mode == "sto" else data.supply[o, p, t])
                for o in data.origins
                for t in data.periods
            )
            opening = math.fsum(data.initial_inventory.get((w, p), 0) for w in data.warehouses)
            domestic_residual = demand - total["served"] - total["unmet"]
            physical_residual = (
                supply + opening - total["served"] - total["export"] - total["terminal_stock"]
            )
            if abs(domestic_residual) > 1e-5 + 1e-8 * max(1, demand):
                raise ValueError("Retained domestic aggregate does not balance.")
            if abs(physical_residual) > 1e-5 + 1e-8 * max(1, supply + opening):
                raise ValueError("Retained national mass balance differs.")
            rows.append(
                {
                    "product": p,
                    "scenario": s,
                    "probability": data.scenario_prob[s] if mode == "sto" else 1,
                    "domestic_demand_t": demand,
                    "served_t": total["served"],
                    "unmet_t": total["unmet"],
                    "service_fraction": total["served"] / demand if demand else None,
                    "supply_t": supply,
                    "export_t": total["export"],
                    "export_supply_fraction": total["export"] / supply if supply else None,
                    "terminal_stock_t": total["terminal_stock"],
                    "shortage_penalty_brl": total["shortage_penalty"],
                    "domestic_balance_residual_t": domestic_residual,
                    "national_balance_residual_t": physical_residual,
                }
            )
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--originals", required=True)
    parser.add_argument("--source-identities", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    identities = json.loads(Path(args.source_identities).read_text(encoding="utf-8"))
    all_rows, sources = [], {}
    for case, (archive, mode, cohort) in CASES.items():
        folder = Path(args.originals) / case
        record = identities[archive]
        sources[case] = {"archive_sha256": record["sha256"], "files": {}}
        for name in (
            "flows.csv",
            "unmet_demand.csv",
            "inventories.csv",
            "input_receipt.json",
            "independent_validation.json",
        ):
            matches = [
                digest
                for path, digest in record["members"].items()
                if path.startswith(f"cases/{case}/") and path.endswith("/" + name)
            ]
            if len(matches) != 1 or sha256(folder / name) != matches[0]:
                raise ValueError(f"Original member hash differs: {case}/{name}")
            sources[case]["files"][name] = matches[0]
        cert = json.loads((folder / "independent_validation.json").read_text())
        if cert.get("status") != "accepted" or cert.get("failed_check_count") != 0:
            raise ValueError("An original accepted certificate is required.")
        receipt = json.loads((folder / "input_receipt.json").read_text())
        data, _ = load_bundle(args.bundle, 215, mode)
        if (
            receipt["experiment"]["workbook_sha256"]
            != "40edb66585daca9cc393cab1f86bde6d4528a5f34b6afc57260cc1684396da4e"
        ):
            raise ValueError("Reference workbook differs.")
        all_rows.extend(
            {"case": case, "cohort": cohort, "mode": mode, **row}
            for row in summarize(data, mode, folder)
        )
    write_csv(output / "h215-policy-reference.csv", tuple(all_rows[0]), all_rows)
    dump(
        output / "h215-policy-reference.json",
        {
            "status": "accepted_historical_vector_readback",
            "scope": "National product/scenario sums; cohorts separate; no new optimization",
            "sources": sources,
            "bundle_manifest_sha256": sha256(Path(args.bundle) / "manifest.json"),
            "rows": all_rows,
            "optimizations": 0,
            "new_hpc_jobs": 0,
        },
    )
    print(json.dumps({"status": "accepted", "rows": len(all_rows), "cases": len(CASES)}))


if __name__ == "__main__":
    main()
