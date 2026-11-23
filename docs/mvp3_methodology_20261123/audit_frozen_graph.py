"""Recompute aggregate directed reachability from an identified frozen baseline.
This audit reads effective tables; it does not select or repair routes, solve a
model, open a routing database, or certify capacity/time feasibility.
"""
from __future__ import annotations
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def audit(support):
    manifest_path = support / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for name, expected in manifest["files"].items():
        if Path(name).name != name:
            raise ValueError("Manifest entries must be direct support files.")
        if digest(support / name) != expected:
            raise ValueError(f"Input digest differs: {name}")
    sets = collections.defaultdict(lambda: collections.defaultdict(set))
    with (support / "sets.csv").open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            sets[(row["population"], row["mode"])][row["field"]].add(row["value"])
    active = collections.defaultdict(lambda: collections.defaultdict(set))
    wanted = {"supply", "supply_s", "demand_dom", "demand_dom_s",
              "demand_exp", "demand_exp_s"}
    with (support / "parameters.csv").open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["field"] not in wanted or float(row["value"]) <= 0:
                continue
            key = json.loads(row["key_json"])
            offset = int(row["field"].endswith("_s"))
            active[(row["population"], row["mode"])][row["field"]].add(
                (str(key[offset]), str(key[offset + 1]))
            )
    with (support / "arcs.csv").open(encoding="utf-8", newline="") as stream:
        arcs = list(csv.DictReader(stream))
    metadata = json.loads((support / "metadata.json").read_text(encoding="utf-8"))
    roles = {"OW": ("origin", "warehouse"),
             "WW": ("warehouse", "warehouse"),
             "WD": ("warehouse", "customer")}
    cases = {}
    for scope, record in metadata.items():
        population, mode = scope.split(":")
        key = population, mode
        suffix = "_s" if mode == "sto" else ""
        adjacency = collections.defaultdict(set)
        counts = collections.Counter()
        for row in arcs:
            if row["population"] != population:
                continue
            if row["arc_active"] != "1":
                continue
            family = row["arc_family"]
            first, last = roles[family]
            source = first, row["origin_id"], row["product"]
            target = last, row["destination_id"], row["product"]
            adjacency[source].add(target)
            counts[family] += 1
        starts = [("origin", origin, product)
                  for origin, product in active[key]["supply" + suffix]]
        distance = {node: 0 for node in starts}
        queue = collections.deque(starts)
        while queue:
            source = queue.popleft()
            for target in sorted(adjacency[source]):
                if target not in distance:
                    distance[target] = distance[source] + 1
                    queue.append(target)
        outcome = {"arc_counts": dict(counts),
                   "active_origin_product_pairs": len(starts)}
        for label, field in (("domestic", "demand_dom"),
                             ("export", "demand_exp")):
            pairs = active[key][field + suffix]
            paths = [distance.get(("customer", node, product))
                     for node, product in sorted(pairs)]
            outcome[f"active_{label}_product_pairs"] = len(pairs)
            outcome[f"reachable_{label}_pairs"] = sum(
                value is not None for value in paths
            )
            outcome[f"{label}_shortest_path_edge_counts"] = dict(
                collections.Counter(str(value) for value in paths)
            )
        outcome["frozen_repair_counts"] = {
            name: len(routes)
            for name, routes in record["_frozen_routes"].items()
            if name.startswith("repair_")
        }
        outcome["route_policy"] = record["mathematical_contract"]["route_policy"]
        cases[scope] = outcome
    return {
        "manifest_sha256": digest(manifest_path),
        "all_manifest_files_verified": True,
        "method": "Multi-source breadth-first traversal per product; active "
                  "endpoints are unions of positive entries in the applicable "
                  "realisation set. Tagged origin/warehouse/customer roles "
                  "are derived from arc families.",
        "interpretation": "Reachability from some active source; no "
                          "origin-to-every-destination, throughput, timing "
                          "or achieved-service feasibility certificate.",
        "cases": cases,
        "optimizer_called": False,
        "database_opened": False,
        "jobs_submitted": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--support", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Preserve the previous audit; choose a new output.")
    result = audit(args.support.resolve())
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=True)
        stream.write("\n")
    print(json.dumps({"output": str(args.output),
                      "cases": len(result["cases"]),
                      "all_manifest_files_verified": True}))


if __name__ == "__main__":
    main()
