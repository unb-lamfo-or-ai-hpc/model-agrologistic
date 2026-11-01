"""Prepare Appendix E from immutable original exports and exact OSRM workbooks.

No solver, scheduler, route request or input mutation. Full-resolution companions
are written only to the explicitly selected local output directory.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import sqlite3
import tarfile
import zipfile
from collections import defaultdict
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
FAMILIES = {
    "OD": "origin-warehouse",
    "DD": "warehouse-warehouse",
    "DC": "warehouse-destination",
    "OC": "origin-destination",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def original_members(path, expected, selected):
    """Hash every member before accepting selected original exports; never extract."""
    require(sha(path) == expected, "Original archive SHA-256 differs")
    hashes, kept, total = {}, {}, 0
    with tarfile.open(path, "r|gz") as archive:
        for member in archive:
            if member.isdir():
                continue
            require(
                member.isfile()
                and not PurePosixPath(member.name).is_absolute()
                and ".." not in PurePosixPath(member.name).parts
                and member.name not in hashes,
                "Unsafe/duplicate archive member",
            )
            total += member.size
            require(total <= 2 * 1024**3, "Archive expanded-size bound")
            keep = member.name in selected or member.name == "inventory.json"
            stream, digest, buffer = archive.extractfile(member), hashlib.sha256(), bytearray()
            for block in iter(lambda stream=stream: stream.read(1024**2), b""):
                digest.update(block)
                if keep:
                    require(len(buffer) + len(block) <= 256 * 1024**2, "Export buffer bound")
                    buffer.extend(block)
            hashes[member.name] = digest.hexdigest()
            if keep:
                kept[member.name] = bytes(buffer)
    inventory = json.loads(kept.pop("inventory.json"))
    require(set(inventory) == set(hashes) - {"inventory.json"}, "Inventory membership differs")
    require(all(hashes[n] == h for n, h in inventory.items()), "Inventory digest differs")
    require(all(hashes.get(n) == h for n, h in selected.items()), "Selected export differs")
    return kept, len(inventory)


def workbook_tables(raw, expected):
    import openpyxl

    require(hashlib.sha256(raw).hexdigest() == expected, "Executed workbook SHA-256 differs")
    workbook = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    distances = {}
    for row in list_rows(workbook["Distancias"]):
        key = (row["Tipo_Arco"], str(row["Origem"]), str(row["Destino"]))
        require(key not in distances, "Duplicate directed distance")
        value = float(row["Distancia_km"])
        require(
            row["Fonte_Distancia"] == "osrm" and math.isfinite(value) and value >= 0,
            "An original OSRM distance is required",
        )
        distances[key] = value
    warehouses = {str(r["CDA"]): r for r in list_rows(workbook["Warehouses"])}
    workbook.close()
    return distances, warehouses


def list_rows(sheet):
    rows = sheet.iter_rows(values_only=True)
    columns = next(rows)
    for values in rows:
        if values[0] is not None:
            yield dict(zip(columns, values, strict=True))


def endpoints(row):
    family = row["route_type"]
    if family == "OD":
        return row["origin"], row["warehouse"]
    if family == "DD":
        return row["warehouse_from"], row["warehouse_to"]
    if family == "DC":
        return row["warehouse"], row["customer"]
    require(family == "OC", "Unknown flow family")
    return row["origin"], row["customer"]


def joined_flows(raw, probabilities, distances):
    """Keep original dimensions and values; direction and destination role are explicit."""
    seen = set()
    for row in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline="")):
        value = float(row["value"])
        require(math.isfinite(value) and value >= 0, "Invalid exported tonnes")
        if value == 0:
            continue
        scenario = row.get("scenario") or next(iter(probabilities))
        require(scenario in probabilities, "Unknown scenario")
        start, end = endpoints(row)
        key = (row["route_type"], start, end)
        require(
            key in distances, "Positive flow lacks its exact directed OSRM distance: " + str(key)
        )
        role = row.get("customer_type") or ""
        identity = (*key, role, row["product"], row["period"], scenario)
        require(identity not in seen, "Duplicate original flow coordinate")
        seen.add(identity)
        probability = float(probabilities[scenario])
        yield dict(
            route_type=key[0],
            movement=FAMILIES[key[0]],
            origin=start,
            destination=end,
            destination_role=role,
            product=row["product"],
            period=row["period"],
            scenario=scenario,
            probability=probability,
            tonnes=value,
            osrm_km=distances[key],
            expected_tonnes=probability * value,
        )


def sparse_matrix(flows):
    totals, distances = defaultdict(float), {}
    for row in flows:
        key = tuple(
            row[k] for k in ["route_type", "origin", "destination", "destination_role", "product"]
        )
        require(key not in distances or distances[key] == row["osrm_km"], "Distance drift")
        distances[key] = row["osrm_km"]
        totals[key] += row["expected_tonnes"]
    return [
        dict(
            zip(
                ["route_type", "origin", "destination", "destination_role", "product"],
                k,
                strict=True,
            ),
            expected_horizon_tonnes=v,
            osrm_km=distances[k],
        )
        for k, v in sorted(totals.items())
    ]


def csv_bytes(rows, fields):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def investments(raw, warehouses):
    output = []
    for row in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))):
        identifier = row["warehouse"]
        require(identifier in warehouses, "Unknown warehouse ID")
        source = warehouses[identifier]
        candidate = row["is_candidate"].lower() == "true"
        record = dict(
            warehouse=identifier,
            municipality=source["Município"],
            uf=source["UF"],
            role="candidate" if candidate else "existing",
        )
        for name in ["candidate_capacity", "expansion_capacity", "bulk_capacity"]:
            record[name + "_t"] = float(row[name])
            require(
                math.isfinite(record[name + "_t"]) and record[name + "_t"] >= -1e-7,
                "Invalid investment quantity",
            )
        for name in ["open", "expand", "bulkify"]:
            value = float(row[name])
            require(min(abs(value), abs(value - 1)) <= 1e-5, "Invalid binary investment")
            record[name] = int(value >= 0.5) if name != "open" or candidate else 0
        output.append(record)
    require(len(output) == len(warehouses), "Incomplete original investment vector")
    return output


def build(archives, inputs_zip, destination):
    manifest = json.loads(
        (ROOT / "manuscript/supplement/appendix_e_sources.json").read_text(encoding="utf-8")
    )
    destination = Path(destination)
    require(not destination.exists(), "Preserve prior companion output; choose a new directory")
    destination.mkdir(parents=True)
    cases, archive_cache, workbook_cache = [], {}, {}
    db = sqlite3.connect(destination / "appendix_e.sqlite3")
    db.execute("CREATE TABLE configurations(case_id TEXT PRIMARY KEY, metadata_json TEXT)")
    db.execute("CREATE TABLE investments(case_id TEXT, warehouse TEXT, record_json TEXT)")
    db.execute(
        "CREATE TABLE flows(case_id TEXT, route_type TEXT, origin TEXT, destination TEXT, "
        "destination_role TEXT, product TEXT, period TEXT, scenario TEXT, probability REAL, "
        "tonnes REAL, osrm_km REAL)"
    )
    with zipfile.ZipFile(inputs_zip) as inputs:
        for config in manifest["cases"]:
            case = config["case"]
            if config["archive"] not in archive_cache:
                wanted = {
                    n: h
                    for c in manifest["cases"]
                    if c["archive"] == config["archive"]
                    for n, h in c["members"].items()
                }
                archive_cache[config["archive"]] = original_members(
                    Path(archives) / config["archive"], config["archive_sha256"], wanted
                )
            original, count = archive_cache[config["archive"]]
            if config["workbook_sha256"] not in workbook_cache:
                workbook_cache[config["workbook_sha256"]] = workbook_tables(
                    inputs.read(config["workbook_member"]), config["workbook_sha256"]
                )
            distances, warehouses = workbook_cache[config["workbook_sha256"]]
            prefix = f"cases/{case}/products/{case}/"
            certificate = json.loads(original[prefix + "independent_validation.json"])
            require(
                certificate["status"] == "accepted" and certificate["failed_check_count"] == 0,
                "Accepted original primal certificate required",
            )
            decisions = investments(original[prefix + "warehouse_decisions.csv"], warehouses)
            flows = list(
                joined_flows(original[prefix + "flows.csv"], config["probabilities"], distances)
            )
            require(
                config["topology"] == "D" or all(f["route_type"] != "OC" for f in flows),
                "Direct flows in W configuration",
            )
            matrix = sparse_matrix(flows)
            for label, rows in [
                ("investments", decisions),
                ("flows", flows),
                ("od_matrix", matrix),
            ]:
                raw = csv_bytes(rows, list(rows[0]))
                (destination / f"{case}_{label}.csv.gz").write_bytes(gzip.compress(raw, mtime=0))
            db.execute("INSERT INTO configurations VALUES (?,?)", (case, json.dumps(config)))
            db.executemany(
                "INSERT INTO investments VALUES (?,?,?)",
                [(case, d["warehouse"], json.dumps(d)) for d in decisions],
            )
            columns = [
                "route_type",
                "origin",
                "destination",
                "destination_role",
                "product",
                "period",
                "scenario",
                "probability",
                "tonnes",
                "osrm_km",
            ]
            db.executemany(
                "INSERT INTO flows VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                [(case, *(f[k] for k in columns)) for f in flows],
            )
            counts = {
                k: sum(d[field] > 1e-7 for d in decisions)
                for k, field in [
                    ("opened", "candidate_capacity_t"),
                    ("expanded", "expansion_capacity_t"),
                    ("bulk_handling", "bulk_capacity_t"),
                ]
            }
            families = {
                family: dict(
                    positive_export_records=sum(f["route_type"] == family for f in flows),
                    expected_arc_tonnes=sum(
                        f["expected_tonnes"] for f in flows if f["route_type"] == family
                    ),
                )
                for family in FAMILIES
            }
            summary = dict(
                config,
                inventory_digests_verified=count,
                counts=counts,
                positive_flow_records=len(flows),
                sparse_od_coordinates=len(matrix),
                families=families,
                decisions=decisions,
                largest_od=sorted(matrix, key=lambda r: r["expected_horizon_tonnes"], reverse=True)[
                    :5
                ],
            )
            cases.append(summary)
            print(
                json.dumps(
                    {
                        "case": case,
                        "counts": counts,
                        "flows": len(flows),
                        "matrix_coordinates": len(matrix),
                    }
                ),
                flush=True,
            )
    db.execute("CREATE INDEX flow_dimensions ON flows(case_id,route_type,product,scenario,period)")
    db.commit()
    db.close()
    receipt = dict(
        schema_version="appendix-e-local-companions-v1",
        cases=cases,
        aliases=manifest["aliases"],
        solver_executed=False,
        network_access=False,
        aggregation="Expected tonnes summed over original periods; distances never summed",
        omitted_flow_semantics="Nonpositive/unexported below original sparse threshold; "
        "a missing admitted-arc mask is not a proof of an exact zero",
        publication_clearance_asserted=False,
        outputs={p.name: sha(p) for p in destination.iterdir() if p.is_file()},
    )
    (destination / "receipt.json").write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archives", required=True, type=Path)
    parser.add_argument("--inputs-zip", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    build(args.archives, args.inputs_zip, args.output)


if __name__ == "__main__":
    main()
