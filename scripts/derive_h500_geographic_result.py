"""Reconstruct only h500 investment cartography from original accepted CSV/certificate.

Coordinates are replayed from the frozen 500-site availability definition.
No workbook, optimization or road geometry is reconstructed or changed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import tarfile
from pathlib import Path

from src.visualization import geography as g

ARCHIVE_SHA = "34346c318b0335e70c56984d8394dd9d00a4ca4ee7d004149c3d3f154cbf2238"
AVAILABILITY_SHA = "b933b13260c860cded4aaf10ba05ab61c395d37b24280314ef12f1be8959e7d9"
PREFIX = "cases/scalar_h500_t1/"
PRODUCT = PREFIX + "products/scalar_h500_t1/"


def derive(archive, availability, database):
    h = hashlib.sha256()
    with Path(archive).open("rb") as stream:
        for block in iter(lambda: stream.read(1024**2), b""):
            h.update(block)
    g.require(h.hexdigest() == ARCHIVE_SHA, "Original h500 archive hash differs")
    text = Path(availability).read_text(encoding="utf-8")
    g.require(
        hashlib.sha256(text.encode()).hexdigest() == AVAILABILITY_SHA,
        "Frozen coordinate source differs",
    )
    source = json.loads(text)
    g.require(
        source["population"] == 500 and source["evidence_status"] == "pending",
        "Expected original availability map",
    )
    wanted = {
        "inventory.json",
        "review.json",
        PREFIX + "input_receipt.json",
        PREFIX + "warehouses_used.json",
        PRODUCT + "warehouse_decisions.csv",
        PRODUCT + "independent_validation.json",
    }
    selected, hashes = {}, {}
    with tarfile.open(archive, "r|gz") as tar:
        for member in tar:
            if member.isdir():
                continue
            g.require(
                member.isfile() and not member.issym() and not member.islnk(),
                "Regular archive members required",
            )
            g.require(
                not Path(member.name).is_absolute() and ".." not in Path(member.name).parts,
                "Archive member path",
            )
            fh = hashlib.sha256()
            data = bytearray()
            keep = member.name in wanted
            g.require(not keep or member.size < 16 * 1024**2, "Selected metadata too large")
            stream = tar.extractfile(member)
            for block in iter(lambda stream=stream: stream.read(1024**2), b""):
                fh.update(block)
                if keep:
                    data.extend(block)
            hashes[member.name] = fh.hexdigest()
            if keep:
                selected[member.name] = bytes(data)
    inventory = json.loads(selected["inventory.json"])
    g.require(set(inventory) == set(hashes) - {"inventory.json"}, "Inventory members differ")
    g.require(all(hashes[n] == sha for n, sha in inventory.items()), "Inventory digest differs")
    certificate = json.loads(selected[PRODUCT + "independent_validation.json"])
    review = json.loads(selected["review.json"])
    g.require(
        certificate["status"] == "accepted"
        and certificate["failed_check_count"] == 0
        and review["quality_target_met"],
        "Original h500 certificate not accepted",
    )
    receipt = json.loads(selected[PREFIX + "input_receipt.json"])
    g.require(
        receipt["experiment"]["workbook_sha256"]
        == "888fbff42e4f80817d4d5f0101049495c86c6ed4cda75f00813779dadab41515",
        "Original h500 workbook binding differs",
    )
    membership = [
        r["warehouse_id"] for r in json.loads(selected[PREFIX + "warehouses_used.json"])["included"]
    ]
    facilities = {
        f["id"]: {
            k: v
            for k, v in f.items()
            if k not in {"decision_flags", "first_population", "investment"}
        }
        for n in source["nodes"]
        for f in n["facilities"]
    }
    g.require(
        set(membership) == {k for k, f in facilities.items() if f["kind"] == "warehouse"}
        and len(membership) == 500,
        "h500 warehouse identities differ",
    )
    decisions = []
    for row in csv.DictReader(
        io.StringIO(selected[PRODUCT + "warehouse_decisions.csv"].decode("utf-8-sig"), newline=None)
    ):
        decision = {"warehouse": row["warehouse"]}
        g.require(decision["warehouse"] in membership, "Unknown decision warehouse")
        for name in ("open", "expand", "bulkify"):
            val = float(row[name])
            g.require(
                min(abs(val), abs(val - 1)) <= 1e-5, "Original binary outside display tolerance"
            )
            decision[name] = int(val >= 0.5)
        for name in ("candidate_capacity", "expansion_capacity", "bulk_capacity"):
            decision[name] = float(row[name])
        if facilities[decision["warehouse"]]["role"] == "existing":
            decision["open"] = 0
        decisions.append(decision)
    g.require(len(decisions) == 500, "Complete original h500 decision vector required")
    sources = {
        "h500_original_archive": ARCHIVE_SHA,
        "h500_original_validation": hashes[PRODUCT + "independent_validation.json"],
        "h500_original_decisions": hashes[PRODUCT + "warehouse_decisions.csv"],
        "h500_original_membership": hashes[PREFIX + "warehouses_used.json"],
        "h500_coordinate_availability_definition": AVAILABILITY_SHA,
    }
    bundle = {
        "schema_version": g.SCHEMA,
        "synthetic": False,
        "sources": sources,
        "entities": sorted(facilities.values(), key=lambda f: f["id"]),
        "populations": {"500": membership},
        "routes": [],
        "materialization_scope": "Investment-only cartography; original flow arrays not copied",
        "cases": [
            {
                "id": "scalar_h500_t1",
                "population": 500,
                "mode": "sto",
                "status": "accepted",
                "certificate_sha256": sources["h500_original_validation"],
                "original_validation_status": "accepted",
                "probabilities": receipt["effective_scenario_probabilities"],
                "products": [],
                "periods": [],
                "decisions": decisions,
                "flows": [],
            }
        ],
    }
    snapshot, _ = g.prepare(database, bundle, sources)
    figure = g.figure_definition(database, snapshot, population=500, case_id="scalar_h500_t1")
    figure.pop("figure_sha256")
    figure["materialization_scope"] = bundle["materialization_scope"]
    figure["notes"].append(
        "All original investments reconstructed; no flow vectors or route geometry included."
    )
    figure = {**figure, "figure_sha256": g.digest(figure)}
    audit = {
        "original_archive_sha256": ARCHIVE_SHA,
        "inventory_digests_verified": len(inventory),
        "validation_sha256": sources["h500_original_validation"],
        "decisions_sha256": sources["h500_original_decisions"],
        "coordinate_definition_sha256": AVAILABILITY_SHA,
        "coordinate_workbook_bytes_reread": False,
        "warehouses": 500,
        "candidates_opened": sum(d["open"] for d in decisions),
        "positive_candidate_investments": sum(d["candidate_capacity"] > 1e-8 for d in decisions),
        "positive_expansions": sum(d["expansion_capacity"] > 1e-8 for d in decisions),
        "positive_bulkifications": sum(d["bulk_capacity"] > 1e-8 for d in decisions),
        "added_candidate_static_capacity_t": sum(d["candidate_capacity"] for d in decisions),
        "added_expansion_static_capacity_t": sum(d["expansion_capacity"] for d in decisions),
        "source_snapshot": source["snapshot"],
        "derived_snapshot": snapshot,
        "fresh_residual_validation_performed": False,
        "solver_executed": False,
    }
    return figure, audit


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--availability", type=Path, required=True)
    p.add_argument("--sqlite", type=Path, required=True)
    p.add_argument("--new-output", type=Path, required=True)
    a = p.parse_args()
    g.require(not a.new_output.exists(), "Preserve previous geographic reconstruction")
    figure, audit = derive(a.archive, a.availability, a.sqlite)
    a.new_output.mkdir(parents=True)
    for name, obj in (("scalar_h500_t1.json", figure), ("h500_map_reconstruction.json", audit)):
        (a.new_output / name).write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit))


if __name__ == "__main__":
    main()
