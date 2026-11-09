"""Refresh reader tables and investment-only maps from a checked local companion receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from scripts.build_appendix_e import FAMILIES, csv_bytes, require, sha
from src.visualization import geography as g

ROOT = Path(__file__).resolve().parents[1]


def build(receipt_path, cache, source_ref):
    if not re.fullmatch(r"[0-9a-f]{40}", source_ref):
        raise ValueError("A full source commit for reader links is required")
    receipt = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
    require(receipt["schema_version"] == "appendix-e-local-companions-v1", "Companion schema")
    local = Path(receipt_path).parent
    for name, digest in receipt["outputs"].items():
        require(Path(name).name == name, "Companion filename")
        require(sha(local / name) == digest, "Prepared companion changed")
    expected = json.loads(
        (ROOT / "manuscript/supplement/appendix_e_sources.json").read_text(encoding="utf-8")
    )
    originals = {c["case"]: c for c in expected["cases"]}
    require({c["case"] for c in receipt["cases"]} == set(originals), "Configuration coverage")
    for case in receipt["cases"]:
        require(
            all(case[k] == v for k, v in originals[case["case"]].items()),
            "Original configuration binding changed",
        )
    root = Path(cache)
    root.mkdir(parents=True, exist_ok=True)
    source = ROOT
    output = source / "manuscript/supplement/investments"
    output.mkdir(exist_ok=True)
    geo_path = source / "manuscript/geographic_sources.json"
    geo = json.loads(geo_path.read_text(encoding="utf-8"))
    base_path = source / "manuscript/maps/scalar_h215_sto.json"
    base = json.loads(base_path.read_text(encoding="utf-8"))
    new_cases = [
        c
        for c in receipt["cases"]
        if c["case"]
        not in {
            "scalar_h215_det",
            "scalar_h215_sto",
            "scalar_h300_t1",
            "scalar_h400_t1",
            "scalar_h500_t1",
        }
    ]
    for case in new_cases:
        entities = {}
        for node in base["nodes"]:
            for f in node["facilities"]:
                e = {
                    k: v
                    for k, v in f.items()
                    if k not in {"decision_flags", "first_population", "investment"}
                }
                if e["id"] in entities:
                    e["products"] = sorted(
                        set(e.get("products", [])) | set(entities[e["id"]].get("products", []))
                    )
                entities[e["id"]] = e
        decisions = [
            dict(
                warehouse=d["warehouse"],
                open=d["open"],
                expand=d["expand"],
                bulkify=d["bulkify"],
                candidate_capacity=d["candidate_capacity_t"],
                expansion_capacity=d["expansion_capacity_t"],
                bulk_capacity=d["bulk_capacity_t"],
            )
            for d in case["decisions"]
        ]
        prefix = f"cases/{case['case']}/products/{case['case']}/"
        sources = dict(
            original_archive=case["archive_sha256"],
            original_validation=case["members"][prefix + "independent_validation.json"],
            original_decisions=case["members"][prefix + "warehouse_decisions.csv"],
            coordinate_definition=hashlib.sha256(
                base_path.read_text(encoding="utf-8").encode()
            ).hexdigest(),
            workbook=case["workbook_sha256"],
        )
        bundle = dict(
            schema_version=g.SCHEMA,
            synthetic=False,
            sources=sources,
            entities=sorted(entities.values(), key=lambda e: e["id"]),
            populations={"215": [d["warehouse"] for d in case["decisions"]]},
            routes=[],
            cases=[
                dict(
                    id=case["case"],
                    population=215,
                    mode=case["mode"],
                    status="accepted",
                    certificate_sha256=sources["original_validation"],
                    original_validation_status="accepted",
                    probabilities=case["probabilities"],
                    products=[],
                    periods=[],
                    decisions=decisions,
                    flows=[],
                )
            ],
        )
        snapshot, _ = g.prepare(root / f"{case['case']}-investments.sqlite3", bundle, sources)
        definition = g.figure_definition(
            root / f"{case['case']}-investments.sqlite3",
            snapshot,
            population=215,
            case_id=case["case"],
        )
        text = json.dumps(definition, ensure_ascii=False, separators=(",", ":")) + "\n"
        filename = case["case"] + ".json"
        (source / "manuscript/maps" / filename).write_text(text, encoding="utf-8", newline="\n")
        geo["figures"][filename] = dict(
            figure_sha256=definition["figure_sha256"],
            normalized_utf8_sha256=hashlib.sha256(text.encode()).hexdigest(),
            snapshot=snapshot,
        )
        geo["sources"][case["case"] + "_validation"] = sources["original_validation"]
    geo_path.write_text(json.dumps(geo, indent=2) + "\n", encoding="utf-8")

    tables = []
    summaries = []
    for index, case in enumerate(receipt["cases"], 1):
        identifier = case["case"]
        name = f"h{case['population']} {case['mode'].upper()}/{case['topology']}"
        interface = "Pyomo/APPSI" if case["interface"] == "pyomo" else "native gurobipy"
        if case["solver"] == "highs":
            interface = "Pyomo/APPSI"
        solver_label = {"gurobi": "Gurobi", "scip": "SCIP", "highs": "HiGHS"}[case["solver"]]
        thread_label = "thread" if case["threads"] == 1 else "threads"
        label = f"{name}, {solver_label}, {interface}, {case['threads']} {thread_label}"
        path = output / (identifier + ".csv")
        path.write_bytes(csv_bytes(case["decisions"], list(case["decisions"][0])))
        investments_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        link = (
            f"https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/{source_ref}/"
            f"manuscript/supplement/investments/{identifier}.csv"
        )
        tables += [
            f"## E{index + 2} {label}\n",
            f"![Figure E.{2 * index - 1}. Investments for {label}.]"
            f'(../figures/{identifier}.png){{fig-pos="H"}}\n',
            "The accepted solution has a relative objective gap of "
            f"**{case['mip_gap'] * 100:.6f}%**. "
            f"It opens {case['counts']['opened']} candidates, "
            f"expands {case['counts']['expanded']} existing "
            f"sites and converts {case['counts']['bulk_handling']} sites for bulk handling.\n",
            f"The [complete warehouse investment list]({link}) "
            "provides CDA, municipality, UF, role, activation flags, candidate capacity, "
            "expansion and bulk-handling basis in tonnes. Existing-site availability "
            "is excluded from candidate openings.\n",
            "| Movement | Positive exported records | Expected arc-tonnes over the horizon |",
            "|:--|--:|--:|",
        ]
        for family, facts in case["families"].items():
            tables.append(
                f"| {FAMILIES[family]} ({family}) | {facts['positive_export_records']:,} "
                f"| {facts['expected_arc_tonnes']:,.3f} |"
            )
        tables += [
            "\nThese are network-arc volumes. Adding different movement families would count "
            "a consignment at successive legs; their sum is not delivered demand. "
            f"The full-resolution companion retains {case['positive_flow_records']:,} "
            "flow records, while the expected-horizon sparse matrix contains "
            f"{case['sparse_od_coordinates']:,} positive product/arc coordinates.\n"
        ]
        tables += [
            "The following five largest product/arc entries illustrate the paired "
            "flow-distance matrices. They are a selected view, not the complete matrix.\n",
            "| Family | From | To / role | Product | Expected horizon t | OSRM km |",
            "|:--|:--|:--|:--|--:|--:|",
        ]
        for row in case["largest_od"]:
            role = " / " + row["destination_role"] if row["destination_role"] else ""
            tables.append(
                f"| {row['route_type']} | {row['origin']} | {row['destination']}{role} "
                f"| {row['product']} | {row['expected_horizon_tonnes']:,.3f} "
                f"| {row['osrm_km']:,.4f} |"
            )
        tables += [
            f"\n![Figure E.{2 * index}. Added static capacity for {label}.]"
            f'(../figures/{identifier}_capacity.png){{fig-pos="H"}}\n',
            "Circle area represents added candidate plus expansion storage in tonnes. "
            "Bulk-handling basis is "
            "excluded from the circles; it determines handling gains rather than "
            "additional static storage.\n",
        ]
        summaries.append(
            {k: v for k, v in case.items() if k not in {"decisions", "largest_od"}}
            | {
                "investment_csv_sha256": investments_sha,
                "local_companions": {
                    n: h for n, h in receipt["outputs"].items() if n.startswith(identifier + "_")
                },
            }
        )
    (source / "manuscript/supplement/appendix_e_case_tables.qmd").write_text(
        "\n".join(tables) + "\n", encoding="utf-8"
    )
    (source / "manuscript/supplement/appendix_e_summary.json").write_text(
        json.dumps(
            dict(
                schema_version="appendix-e-reader-summary-v1",
                cases=summaries,
                aliases=receipt["aliases"],
                all_distances_bound_to_exact_workbooks=True,
                full_resolution_tables_public=False,
                scope="Derived original-export summaries; no optimizer or fresh residual checks",
            ),
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print("READER_CASES", len(summaries), "NEW_MAPS", len(new_cases))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--source-ref", required=True)
    args = parser.parse_args()
    build(args.receipt, args.cache, args.source_ref)


if __name__ == "__main__":
    main()
