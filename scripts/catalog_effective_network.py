"""Normalize original W distances into an active/inactive inspection catalog.

The selected computational arcs stay immutable. This reads existing distances;
it performs no routing requests, recalculation, selection or optimization.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.logic.effective_baseline import (  # noqa: E402
    ARC_COLUMNS,
    EXPECTED_INPUTS,
    dump,
    numeric,
    read_csv,
    sha256,
)
from src.logic.excel_loader import _normalize_text  # noqa: E402


def catalog(directory):
    import openpyxl

    directory = Path(directory)
    output = directory / "network-catalog"
    output.mkdir(exist_ok=False)
    selections, policies, sets = {}, {}, {}
    for row in read_csv(directory / "seed/arcs.csv", ARC_COLUMNS):
        population = int(row["population"])
        selections.setdefault(population, {})[
            row["arc_family"], row["origin_id"], row["destination_id"], row["product"]
        ] = numeric(row["osrm_distance_km"])
        policies[population] = row["policy_id"]
    for row in read_csv(
        directory / "seed/sets.csv", ("population", "mode", "field", "position", "value")
    ):
        if row["mode"] == "sto":
            sets.setdefault(int(row["population"]), {}).setdefault(row["field"], []).append(
                row["value"]
            )
    files, controls = {}, {}
    for population, expected in EXPECTED_INPUTS.items():
        original = directory / f"original-copies/h{population}.xlsx"
        if sha256(original) != expected:
            raise ValueError("Original distance workbook identity differs.")
        data = sets[population]
        selected = selections[population]
        seen_selected, seen_pairs = set(), set()
        counts = Counter()
        target = output / f"h{population}-W-network.csv.gz"
        workbook = openpyxl.load_workbook(original, read_only=True, data_only=True)
        values = iter(workbook["Distancias"].values)
        header = next(values)
        family_names = {"OD": "OW", "DC": "WD", "DD": "WW"}
        with target.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
                with io.TextIOWrapper(zipped, encoding="utf-8", newline="") as text:
                    columns = [*ARC_COLUMNS, "source_row", "distance_unit"]
                    writer = csv.DictWriter(text, fieldnames=columns, lineterminator="\n")
                    writer.writeheader()
                    for source_row, raw_values in enumerate(values, 2):
                        row = dict(zip(header, raw_values, strict=True))
                        code = row["Tipo_Arco"]
                        if code not in family_names:
                            # Original OC distances stay historical, outside new W.
                            continue
                        family = family_names[code]
                        a, b = _normalize_text(row["Origem"]), _normalize_text(row["Destino"])
                        if (family, a, b) in seen_pairs:
                            raise ValueError("Duplicate original directed distance.")
                        seen_pairs.add((family, a, b))
                        aa = data["origins"] if family == "OW" else data["warehouses"]
                        bb = data["customers"] if family == "WD" else data["warehouses"]
                        if a not in aa or b not in bb or (family == "WW" and a == b):
                            raise ValueError(
                                "Distance endpoint lies outside the declared W universe."
                            )
                        source = str(row["Fonte_Distancia"] or "").lower()
                        distance = row["Distancia_km"]
                        missing = distance is None or distance == ""
                        if not missing:
                            distance = numeric(distance)
                            if source != "osrm" or row["Motivo_Fallback"] not in (None, ""):
                                raise ValueError(
                                    "An unidentified/fallback distance entered the catalog."
                                )
                        for product in data["products"]:
                            key = (family, a, b, product)
                            active = key in selected
                            if active:
                                if missing or selected[key] != distance:
                                    raise ValueError(
                                        "Selected OSRM value differs from original distance."
                                    )
                                seen_selected.add(key)
                            index = counts[family]
                            counts[family] += 1
                            counts["active" if active else "inactive"] += 1
                            counts["missing_distance"] += missing
                            counts["zero_distance"] += not missing and distance == 0
                            writer.writerow(
                                {
                                    "population": population,
                                    "origin_id": a,
                                    "destination_id": b,
                                    "arc_family": family,
                                    "product": product,
                                    "osrm_distance_km": "" if missing else repr(distance),
                                    "distance_status": "unavailable" if missing else "osrm",
                                    "arc_active": int(active),
                                    "source_id": f"workbook_h{population}",
                                    "policy_id": policies[population],
                                    "origin_role": "origin" if family == "OW" else "warehouse",
                                    "destination_role": "warehouse"
                                    if family != "WD"
                                    else "domestic"
                                    if b in data["domestic_customers"]
                                    else "export",
                                    "record_order": index,
                                    "source_row": source_row,
                                    "distance_unit": "km",
                                }
                            )
        workbook.close()
        if seen_selected != set(selected):
            raise ValueError("Selected graph is not entirely covered by the original catalog.")
        expected_pairs = (
            len(data["origins"]) * population
            + population * len(data["customers"])
            + population * (population - 1)
        )
        if len(seen_pairs) != expected_pairs:
            raise ValueError("Original W distance-pair universe is incomplete.")
        files[target.name] = sha256(target)
        controls[str(population)] = dict(counts)
        print(json.dumps({"population": population, "counts": dict(counts)}), flush=True)
    manifest = {
        "status": "accepted_original_W_catalog",
        "files": files,
        "source_workbooks": EXPECTED_INPUTS,
        "controls": controls,
        "universe": "All original directed OW/WD/WW pairs times products; WW excludes self loops",
        "runtime_graph": "Only immutable selected arcs.csv enters ModelData",
        "routing_requests": 0,
        "distance_recalculations": 0,
    }
    dump(output / "manifest.json", manifest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    catalog(parser.parse_args().directory)
