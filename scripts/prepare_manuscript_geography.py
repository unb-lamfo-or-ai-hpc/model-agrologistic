"""Read frozen ZIP/XLSX and accepted archives into a separate geographic bundle.

This is documentary post-processing, not private-input residual validation or
optimization. Route geometry is optional, source-bound and never fabricated.
Original workbook, membership, decision and certificate bytes stay unchanged.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

from openpyxl import load_workbook

from scripts.review_scalar_h300_evidence import read_archive
from src.visualization import geography as g

ARCHIVES = {
    215: (
        "scalar-h215-evidence.tar.gz",
        "81890b546d720ad5999d11f44fd499337aad937e32773db39067796f73660534",
    ),
    300: (
        "scalar-h300-30h-evidence.tar.gz",
        "dc5969fa391dc81590210ef7e6f89abbb5df554e4bc5b2032ba9eafe1a67f3fc",
    ),
    400: (
        "scalar-h400-8h-evidence.tar.gz",
        "e0b58bb74ac254706d30f0f1863162df5d8a714751eadf43b28e7dbc0c5d5def",
    ),
}
WORKBOOKS = {
    215: (
        "policy_population_v020_osrm",
        "40edb66585daca9cc393cab1f86bde6d4528a5f34b6afc57260cc1684396da4e",
    ),
    300: (
        "nine_population_osrm_v1",
        "7761cce77cf93dcba2f617714f0117c1f2ead4de0c3f27149daceba447e0c7d1",
    ),
    400: (
        "nine_population_osrm_v1",
        "c3085456997714ef5a8bdbf61e2c9a5e578c2636003947427cf58933d21ceb13",
    ),
    500: (
        "nine_population_osrm_v1",
        "888fbff42e4f80817d4d5f0101049495c86c6ed4cda75f00813779dadab41515",
    ),
}


def rows(content):
    return csv.DictReader(io.StringIO(content.decode("utf-8-sig"), newline=None))


def customer_identity(row):
    """Preserve domestic/export roles even when a municipality has both."""
    city = row["customer"]
    prefix, separator, suffix = city.rpartition(" | ")
    declared = suffix.casefold() if separator else row["customer_type"].casefold()
    g.require(
        declared in {"domestic", "domestica", "export", "exportacao"},
        "Customer role unavailable; do not guess from a municipality",
    )
    role = "domestic" if declared in {"domestic", "domestica"} else "export"
    return role + ":" + (prefix if separator else city)


def workbook_entities(content):
    """Read declared coordinates only; no inferred centroids or node merging."""
    wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    entities, membership = {}, []
    try:
        for sheet, kind in (
            ("Oferta", "origin"),
            ("Demanda", "destination"),
            ("Warehouses", "warehouse"),
        ):
            iterator = wb[sheet].values
            headers = next(iterator)
            for values in iterator:
                r = dict(zip(headers, values, strict=True))
                if kind == "warehouse":
                    if not r.get("CDA"):
                        continue
                    identifier = str(r["CDA"])
                    actual_kind = "warehouse"
                    role = "existing" if str(r["Status"]).casefold() == "existente" else "candidate"
                    entity = {
                        "id": identifier,
                        "kind": actual_kind,
                        "role": role,
                        "state": r["UF"],
                        "name": r["Município"],
                    }
                    membership.append(identifier)
                else:
                    if not r.get("Cidade"):
                        continue
                    actual_kind = (
                        kind
                        if kind == "origin"
                        else ("domestic" if r["Tipo_Demanda"] == "DOMESTICA" else "export")
                    )
                    identifier = actual_kind + ":" + r["Cidade"]
                    entity = {
                        "id": identifier,
                        "kind": actual_kind,
                        "name": r["Cidade"],
                        "products": [r["Produto"]],
                    }
                entity.update(lat=r["Latitude"], lon=r["Longitude"])
                if identifier in entities:
                    old = entities[identifier]
                    g.require(
                        old["lat"] == entity["lat"] and old["lon"] == entity["lon"],
                        "Node ID has conflicting coordinates",
                    )
                    old["products"] = sorted(
                        set(old.get("products", [])) | set(entity.get("products", []))
                    )
                else:
                    entities[identifier] = entity
    finally:
        wb.close()
    return entities, membership


def build(inputs_zip, evidence_directory):
    sources, entities, populations, cases, routes, diagnostics = {}, {}, {}, [], {}, []
    with zipfile.ZipFile(inputs_zip) as package:
        for population, (folder, checksum) in WORKBOOKS.items():
            member = f"data/processed/{folder}/warehouses_{population}/model_input.xlsx"
            content = package.read(member)
            g.require(
                hashlib.sha256(content).hexdigest() == checksum, "Original workbook hash differs"
            )
            sources[f"workbook_h{population}"] = checksum
            found, membership = workbook_entities(content)
            populations[str(population)] = membership
            for identifier, entity in found.items():
                if identifier in entities:
                    g.require(
                        entities[identifier] == entity, "Cross-population coordinates/roles differ"
                    )
                entities[identifier] = entity
            if population == 500:
                continue
            archive, archive_sha = ARCHIVES[population]
            files, _ = read_archive(Path(evidence_directory) / archive, archive_sha)
            sources[f"archive_h{population}"] = archive_sha
            review = json.loads(files["review.json"])
            g.require(
                review["quality_target_met"] and review["operational_receipts_closed"],
                "Original quality and operational acceptance required",
            )
            for arm in review["arms"]:
                case_id = arm.get("case_name", f"scalar_h215_{arm['mode']}")
                prefix = f"cases/{case_id}/"
                product_path = prefix + f"products/{case_id}/"
                validation_bytes = files[product_path + "independent_validation.json"]
                validation = json.loads(validation_bytes)
                summary = json.loads(files[product_path + "run_summary.json"])
                cert_sha = hashlib.sha256(validation_bytes).hexdigest()
                g.require(
                    validation["status"] == "accepted" and validation["failed_check_count"] == 0,
                    "Original residual rejection",
                )
                sources[case_id + "_validation"] = cert_sha
                receipt = json.loads(files[prefix + "input_receipt.json"])
                probabilities = receipt["effective_scenario_probabilities"]
                selected = json.loads(files[prefix + "warehouses_used.json"])
                g.require(
                    [r["warehouse_id"] for r in selected["included"]] == membership,
                    "Original experimental membership/order differs",
                )
                decisions = []
                for row in rows(files[product_path + "warehouse_decisions.csv"]):
                    decision = {"warehouse": row["warehouse"]}
                    for key in ("open", "expand", "bulkify"):
                        value = float(row[key])
                        g.require(
                            min(abs(value), abs(value - 1)) <= 1e-5,
                            "Original activation not display-integral",
                        )
                        decision[key] = int(value >= 0.5)
                    decision.update(
                        {
                            key: float(row[key])
                            for key in ("candidate_capacity", "expansion_capacity", "bulk_capacity")
                        }
                    )
                    # Existing open=1 denotes availability, not candidate opening.
                    if entities[row["warehouse"]]["role"] == "existing":
                        decision["open"] = 0
                    decisions.append(decision)
                flows, products, periods, used_ids, export_ids = [], set(), set(), set(), set()
                for row in rows(files[product_path + "flows.csv"]):
                    tonnes = float(row["value"])
                    g.require(
                        g.finite(tonnes) and tonnes >= -1e-5,
                        "Unexpected flow outside original residual tolerance",
                    )
                    if tonnes <= 1e-8:
                        continue
                    arc = row["route_type"]
                    if arc == "OD":
                        origin, target = "origin:" + row["origin"], row["warehouse"]
                    elif arc == "DD":
                        origin, target = row["warehouse_from"], row["warehouse_to"]
                    else:
                        origin = row["warehouse"] if arc == "DC" else "origin:" + row["origin"]
                        target = customer_identity(row)
                    route_id = g.digest([arc, origin, target])
                    routes[route_id] = {
                        "id": route_id,
                        "origin": origin,
                        "destination": target,
                        "geometry": None,
                        "provenance": {
                            "provider": "osrm",
                            "dataset_id": "brazil-260901-osrm-v6.0.0-driving-mld",
                            "source_sha256": checksum,
                            "geometry_status": "not_in_distance_workbook",
                        },
                    }
                    flows.append(
                        {
                            "route": route_id,
                            "arc_type": arc,
                            "scenario": row.get("scenario") or next(iter(probabilities)),
                            "product": row["product"],
                            "period": row["period"],
                            "tonnes": tonnes,
                        }
                    )
                    products.add(row["product"])
                    periods.add(row["period"])
                    used_ids.update(
                        i for i in (origin, target) if entities[i]["kind"] == "warehouse"
                    )
                    if entities[target]["kind"] == "export":
                        export_ids.add(target)
                case = {
                    "id": case_id,
                    "population": population,
                    "mode": arm["mode"],
                    "status": "accepted",
                    "certificate_sha256": cert_sha,
                    "original_validation_status": "accepted",
                    "probabilities": probabilities,
                    "products": sorted(products),
                    "periods": sorted(periods),
                    "decisions": decisions,
                    "flows": flows,
                }
                cases.append(case)
                diagnostics.append(
                    {
                        **arm,
                        "physical_diagnostics": {
                            **{
                                k: summary[k]
                                for k in (
                                    "domestic_service_level",
                                    "emergency_reception_capacity",
                                    "emergency_static_capacity",
                                    "peak_rss_mb",
                                    "total_unmet_demand",
                                )
                            },
                            "penalty_cost_share": arm["artificial_penalties"]
                            / (arm["economic_cost"] + arm["artificial_penalties"]),
                        },
                        "case": case_id,
                        "population": population,
                        "included": len(membership),
                        "candidate_count": selected["candidate_count"],
                        "candidate_activations": sum(d["open"] for d in decisions),
                        "positive_candidate_investments": sum(
                            d["candidate_capacity"] > 1e-8 for d in decisions
                        ),
                        "expansion_activations": sum(d["expand"] for d in decisions),
                        "positive_expansions": sum(
                            d["expansion_capacity"] > 1e-8 for d in decisions
                        ),
                        "bulkification_activations": sum(d["bulkify"] for d in decisions),
                        "positive_bulkifications": sum(
                            d["bulk_capacity"] > 1e-8 for d in decisions
                        ),
                        "candidate_capacity_t": sum(d["candidate_capacity"] for d in decisions),
                        "expansion_capacity_t": sum(d["expansion_capacity"] for d in decisions),
                        "bulkification_basis_t": sum(d["bulk_capacity"] for d in decisions),
                        "warehouses_with_positive_transport": len(used_ids),
                        "export_destinations_with_positive_transport": len(export_ids),
                        "original_validation_sha256": cert_sha,
                        "source_archive_sha256": archive_sha,
                        "warehouse_decisions_sha256": hashlib.sha256(
                            files[product_path + "warehouse_decisions.csv"]
                        ).hexdigest(),
                        "flows_sha256": hashlib.sha256(
                            files[product_path + "flows.csv"]
                        ).hexdigest(),
                        "reconstructed_costs": validation["reconstructed_costs"],
                        "matrix": json.loads(
                            files[product_path + "resources/matrix_statistics.json"]
                        ),
                        "display_threshold_t": 1e-8,
                        "qualification": (
                            "Original vector post-processing, not fresh residual validation"
                        ),
                    }
                )
    cases.append({"id": "h500_pending", "population": 500, "mode": "sto", "status": "pending"})
    bundle = {
        "schema_version": g.SCHEMA,
        "synthetic": False,
        "sources": sources,
        "entities": sorted(entities.values(), key=lambda e: e["id"]),
        "populations": populations,
        "routes": list(routes.values()),
        "cases": cases,
    }
    g.validate(bundle, sources)
    return bundle, diagnostics


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs-zip", type=Path, required=True)
    parser.add_argument("--evidence-directory", type=Path, required=True)
    parser.add_argument("--new-output", type=Path, required=True)
    args = parser.parse_args(argv)
    g.require(not args.new_output.exists(), "Preserve previous preparation")
    bundle, diagnostics = build(args.inputs_zip, args.evidence_directory)
    args.new_output.mkdir(parents=True)
    for name, value in (("bundle.json", bundle), ("decision_diagnostics.json", diagnostics)):
        (args.new_output / name).write_text(
            json.dumps(value, allow_nan=False) + "\n", encoding="utf-8"
        )
    snapshot, _ = g.prepare(args.new_output / "geographic.sqlite3", bundle, bundle["sources"])
    print(
        json.dumps(
            {
                "snapshot": snapshot,
                "cases": len(bundle["cases"]),
                "route_geometry": "unavailable; no fabricated polylines",
                "h500_result": "pending; availability only",
                "output": str(args.new_output),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
