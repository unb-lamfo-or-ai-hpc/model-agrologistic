"""Prepare local effective workbooks/CSVs and validate them, without optimizers.

The seed reads the four pinned workbooks and original input receipts. Rendering
is delegated to render_effective_workbooks.mjs; no source workbook is overwritten.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import zipfile
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.logic.effective_baseline import (  # noqa: E402
    EXPECTED_INPUTS,
    MAP_FIELDS,
    ORIGIN_CLASSES,
    PARAMETER_COLUMNS,
    SCHEMA,
    SET_FIELDS,
    UNITS,
    dump,
    effective_projection,
    identity,
    load_bundle,
    numeric,
    read_csv,
    sha256,
    write_bundle,
)
from src.logic.excel_loader import ExcelLoaderConfig, load_model_data_from_excel  # noqa: E402
from src.logic.model_config import ModelConfig  # noqa: E402
from src.logic.parametric_scenarios import ParameterScenario  # noqa: E402

GROUPS = {
    "Supply": ("supply", "supply_s"),
    "DomesticDemand": ("demand_dom", "demand_dom_s"),
    "Exports": ("demand_exp", "demand_exp_s"),
    "Capacities": (
        "static_capacity",
        "reception_capacity",
        "shipping_capacity",
        "initial_inventory",
    ),
    "Investments": (
        "max_candidate_capacity",
        "max_expand_capacity",
        "max_bulk_capacity",
        "opening_fixed_cost",
        "candidate_capacity_cost",
        "expand_fixed_cost",
        "expand_variable_cost",
        "bulk_fixed_cost",
        "bulk_variable_cost",
    ),
    "Costs": (
        "freight_origin",
        "freight_dest",
        "freight_warehouse",
        "transshipment_cost",
        "storage_tariff",
    ),
    "Penalties": (
        "unmet_demand_penalty",
        "emergency_static_capacity_penalty",
        "emergency_reception_capacity_penalty",
    ),
    "Scenarios": ("scenario_prob",),
    "Durations": ("duration_od", "duration_dc", "duration_dd", "duration_oc"),
}
VALUE_COLUMNS = [
    "field",
    "key_json",
    "value",
    "unit",
    "scopes",
    "source_ids",
    "transformation",
    "origin_class",
    "usage_class",
]


def sheet(name, columns, rows):
    return {"name": name, "columns": list(columns), "rows": list(rows)}


def workbook_payload(stage):
    grouped = defaultdict(dict)
    for row in read_csv(stage / "parameters.csv", PARAMETER_COLUMNS):
        name = next(group for group, names in GROUPS.items() if row["field"] in names)
        key = tuple(row[k] for k in ("field", "key_json", "value", "unit"))
        record = grouped[name].setdefault(
            key,
            [
                row["field"],
                row["key_json"],
                numeric(row["value"]),
                row["unit"],
                [],
                [],
                row["transformation"],
                ORIGIN_CLASSES.get(row["field"], "historical_derived_effective_value"),
                "historical_baseline",
            ],
        )
        record[4].append(f"{row['population']}:{row['mode']}")
        if row["source_id"] not in record[5]:
            record[5].append(row["source_id"])
    sources = json.loads((stage / "sources.json").read_text(encoding="utf-8"))
    configs = json.loads((stage / "configs.json").read_text(encoding="utf-8"))
    result = [
        sheet(
            "Identification",
            ["item", "value"],
            [
                ["schema", SCHEMA],
                [
                    "use",
                    "Local derived inspection and lossless CSV export; not a published dataset",
                ],
                ["baseline", "Historical effective values, not empirical recalibration"],
                ["objective", "Investment once + expected operations + three separate penalties"],
                ["network", "W; original complete OSRM matrices remain identified at source"],
                ["pending", "beta/alpha scopes and positive absolute fixed costs await approval"],
                [
                    "originals",
                    "Original values remain in the immutable, hash-identified source workbooks",
                ],
            ],
        ),
        sheet(
            "Dictionary",
            ["field", "unit", "definition"],
            [
                [
                    name,
                    UNITS[name],
                    "Exact effective ModelData map; key_json retains ordered string indices",
                ]
                for name in MAP_FIELDS
            ],
        ),
        sheet(
            "Calendar",
            ["period", "operating_days", "unit"],
            [[f"{y}-{m:02}", 30, "day/period"] for y in range(2021, 2026) for m in range(1, 13)],
        ),
    ]
    for group in GROUPS:
        rows = list(grouped[group].values())
        for row in rows:
            row[4], row[5] = "|".join(row[4]), "|".join(row[5])
        result.append(sheet(group, VALUE_COLUMNS, rows))
    result.extend(
        [
            sheet(
                "Sets",
                ["population", "mode", "field", "position", "value"],
                [
                    [r[k] for k in ("population", "mode", "field", "position", "value")]
                    for r in read_csv(
                        stage / "sets.csv", ("population", "mode", "field", "position", "value")
                    )
                ],
            ),
            sheet(
                "Configurations",
                ["scope", "parameter", "value_json"],
                [
                    [scope, name, json.dumps(value)]
                    for scope, config in configs.items()
                    for name, value in config.items()
                ],
            ),
            sheet(
                "Sources",
                ["source_id", "source_sha256", "description"],
                [[k, v["sha256"], v["description"]] for k, v in sources.items()],
            ),
            sheet(
                "NetworkReferences",
                ["file", "sha256", "role"],
                [
                    [
                        name,
                        sha256(stage / name),
                        "Immutable local support; no distance recomputation",
                    ]
                    for name in ("arcs.csv", "metadata.json", "nodes.json", "sources.json")
                ],
            ),
            sheet(
                "Transformations",
                ["component", "historical_rule", "effective_rule"],
                [
                    [
                        "penalties",
                        "thesis_dynamic; raw defaults include 1000000",
                        "Freeze each effective coefficient; no implicit recalculation",
                    ],
                    [
                        "expansion",
                        "Explicit maximum or fallback 0.25 * original static capacity",
                        "Freeze effective maximum independently of K0",
                    ],
                    [
                        "candidate",
                        "Registered static capacity becomes investible maximum",
                        "Initial K/R/H remain zero",
                    ],
                    [
                        "rates",
                        "Source headings may omit /day",
                        "Preserve original heading; model adoption is t/day, multiplied once by 30",
                    ],
                    [
                        "scenarios",
                        "Cartesian historical supply/demand transformations",
                        "Nine equiprobable STO trajectories; DET base arrays retained",
                    ],
                    [
                        "exports",
                        "Automatic supply-total upper bound per export destination/product/period",
                        "Retain effective limits; no global alpha control enabled",
                    ],
                    [
                        "freight",
                        "Historical proportional coefficient times OSRM km",
                        "Preserve coefficients; alternative calibrations remain hypotheses",
                    ],
                ],
            ),
            sheet(
                "ParameterTemplate",
                ["scenario_json", "status"],
                [
                    [
                        json.dumps(asdict(ParameterScenario("baseline"))),
                        "neutral; beta/alpha disabled",
                    ]
                ],
            ),
        ]
    )
    return result


def seed(args):
    import pandas as pd

    accepted = json.loads(
        (ROOT / "data/manifests/effective_baseline_sources_v1.json").read_text(encoding="utf-8")
    )
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    inputs = output / "original-copies"
    inputs.mkdir()
    sources, cases = {}, {}
    with zipfile.ZipFile(args.archive) as archive:
        for population, expected in EXPECTED_INPUTS.items():
            suffix = f"warehouses_{population}/model_input.xlsx"
            names = [n for n in archive.namelist() if n.endswith(suffix) and "osrm" in n]
            if len(names) != 1:
                raise ValueError("Ambiguous original workbook.")
            raw = archive.read(names[0])
            if hashlib.sha256(raw).hexdigest() != expected:
                raise ValueError(f"Historical workbook hash differs: h{population}")
            path = inputs / f"h{population}.xlsx"
            path.write_bytes(raw)
            sources[f"workbook_h{population}"] = {
                "sha256": expected,
                "description": names[0],
            }
            modes = ("det", "sto") if population == 215 else ("sto",)
            for mode in modes:
                label = f"scalar_h215_{mode}" if population == 215 else f"scalar_h{population}_t1"
                receipt_path = Path(args.receipts) / label / "input_receipt.json"
                receipt_id = f"receipt_h{population}_{mode}"
                if sha256(receipt_path) != accepted["original_sources"][receipt_id]["sha256"]:
                    raise ValueError("Original input-receipt identity differs; preserve the file.")
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                cfg = ModelConfig(**receipt["experiment"]["model"])
                if cfg.mode != mode:
                    raise ValueError("Original receipt mode differs.")
                loader = ExcelLoaderConfig(**receipt["experiment"]["loader"])
                data = effective_projection(load_model_data_from_excel(path, loader), cfg)
                if identity(data, cfg) != accepted["cases"][f"{population}:{mode}"]:
                    raise ValueError(
                        "Historical effective baseline identity differs; qualification stopped."
                    )
                expected_arcs = {215: 25112, 300: 45240, 400: 76320, 500: 115400}
                if (
                    len(data.warehouses),
                    len(data.existing_warehouses),
                    len(data.candidate_warehouses),
                ) != (population, 146, population - 146):
                    raise ValueError("Frozen population cardinality differs.")
                if (
                    sum(len(getattr(data, "routes_" + code)) for code in ("od", "dc", "dd"))
                    != (expected_arcs[population])
                ):
                    raise ValueError("Frozen product-indexed arc cardinality differs.")
                cases[population, mode] = data, cfg
                sources[f"receipt_h{population}_{mode}"] = {
                    "sha256": sha256(receipt_path),
                    "description": f"Original input_receipt.json: {label}",
                }
                print(
                    json.dumps(
                        {"prepared": f"{population}:{mode}", "input_sha256": identity(data, cfg)}
                    ),
                    flush=True,
                )
        registry_name = "external-inputs/Warehouses_Existing_Candidate_All.xlsx"
        raw = archive.read(registry_name)
        expected = "0d19865ac72eca0706960d10b6dbd1647a4951378a831715e39af8029ecb77f2"
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("Original registry hash differs.")
        registry = pd.read_excel(io.BytesIO(raw), sheet_name="Sheet1", keep_default_na=False)
        sources["registry_original"] = {"sha256": expected, "description": registry_name}
        for name in (
            "data/templates/model_agrologistic_padrao_ouro.xlsx",
            "data/processed/warehouse_population_v020/warehouse_population_manifest.json",
            "data/processed/nine_population_inputs_v1/population_order.csv",
            "data/processed/nine_population_inputs_v1/population_workbook_manifest.json",
        ):
            blob = archive.read(name)
            sources[name] = {"sha256": hashlib.sha256(blob).hexdigest(), "description": name}
    manifest = write_bundle(output / "seed", cases, sources)
    dump(output / "baseline-workbook.json", {"sheets": workbook_payload(output / "seed")})
    selected = {n: cases[n, "sto"][0] for n in EXPECTED_INPUTS}
    universe = selected[500]
    extra = [
        *(f"Em_h{n}" for n in selected),
        *(f"order_h{n}" for n in selected),
        "modeled_in_baseline",
        "model_K0_t",
        "model_R0_t_day",
        "model_H0_t_day",
        "candidate_limit_t",
        "source_id",
        "transformation",
    ]
    records = []
    for original in registry.to_dict(orient="records"):
        cda = str(original["CDA"])
        row = [None if pd.isna(v) else v for v in original.values()]
        row += [int(cda in d.warehouses) for d in selected.values()]
        row += [d.warehouses.index(cda) if cda in d.warehouses else None for d in selected.values()]
        present = cda in universe.warehouses
        row += [
            int(present),
            *(
                getattr(universe, field).get(cda) if present else None
                for field in (
                    "static_capacity",
                    "reception_capacity",
                    "shipping_capacity",
                    "max_candidate_capacity",
                )
            ),
            "registry_original",
            "Selected candidate: zero initial K/R/H; "
            "registered static capacity is investible limit",
        ]
        records.append(row)
    if len(registry) != 18086 or registry["CDA"].nunique() != 18086:
        raise ValueError("Registry cardinality differs.")
    dump(
        output / "registry-workbook.json",
        {
            "sheets": [
                sheet(
                    "Identification",
                    ["item", "value"],
                    [
                        ["source_sha256", expected],
                        ["scope", "Local restricted derivative; no public redistribution approval"],
                        [
                            "membership",
                            "Em_h* means inclusion, not investment activation or operational use",
                        ],
                        [
                            "outside_h500",
                            "Modeled-capacity cells blank: "
                            "not a modeled facility in these baselines",
                        ],
                        ["units", "Original headings retained; model rate adoption is t/day"],
                    ],
                ),
                sheet("Registry", [*registry.columns, *extra], records),
            ]
        },
    )
    print(
        json.dumps(
            {"status": "local_seed_prepared", "cases": manifest["cases"], "output": str(output)}
        ),
        flush=True,
    )


def export(args):
    """Read effective values from the new XLSX; support files retain the frozen graph."""
    import openpyxl

    workbook = Path(args.workbook)
    stage = Path(args.support)
    wb = openpyxl.load_workbook(workbook, read_only=True, data_only=True)
    rows = list(wb["Identification"].values)
    if dict(rows[1:]).get("schema") != SCHEMA:
        raise ValueError("Unexpected workbook schema.")
    references = list(wb["NetworkReferences"].values)
    for name, expected, _ in references[1:]:
        if Path(name).name != name or sha256(stage / name) != expected:
            raise ValueError("Workbook support hash differs.")
    # Start from the verified effective support to preserve metadata and node provenance.
    original_manifest = json.loads((stage / "manifest.json").read_text(encoding="utf-8"))
    expected_sources = original_manifest["source_identities"]
    actual_sources = {
        row[0]: {"sha256": row[1], "description": row[2]}
        for row in list(wb["Sources"].values)[1:]
        if row[0] is not None
    }
    if actual_sources != expected_sources:
        raise ValueError("Workbook source catalog differs from its identified support.")
    calendar = [row for row in list(wb["Calendar"].values)[1:] if row[0] is not None]
    expected_calendar = [
        (f"{y}-{m:02}", 30, "day/period") for y in range(2021, 2026) for m in range(1, 13)
    ]
    if calendar != expected_calendar:
        raise ValueError("Workbook calendar or operating-day conversion differs.")
    cases = {
        tuple((int(scope.split(":")[0]), scope.split(":")[1])): load_bundle(
            stage, int(scope.split(":")[0]), scope.split(":")[1]
        )
        for scope in original_manifest["cases"]
    }
    for data, _ in cases.values():
        for name in (*SET_FIELDS, *MAP_FIELDS):
            setattr(data, name, [] if name in SET_FIELDS else {})
    for population, mode, name, position, value in list(wb["Sets"].values)[1:]:
        data = cases[int(population), mode][0]
        if name not in SET_FIELDS or int(position) != len(getattr(data, name)):
            raise ValueError("Invalid set identifier or order in workbook.")
        getattr(data, name).append(str(value))
    config_values = defaultdict(dict)
    for scope, name, value in list(wb["Configurations"].values)[1:]:
        if scope is None:
            continue
        if name in config_values[scope]:
            raise ValueError("Duplicate configuration parameter.")
        config_values[scope][name] = json.loads(value)
    if set(config_values) != set(original_manifest["cases"]):
        raise ValueError("Configuration scopes differ.")
    for scope, values in config_values.items():
        pop, mode = scope.split(":")
        data, expected_config = cases[int(pop), mode]
        if set(values) != set(asdict(expected_config)):
            raise ValueError("Incomplete configuration fields.")
        cases[int(pop), mode] = data, ModelConfig(**values)
    for group in GROUPS:
        sheet_rows = iter(wb[group].values)
        if list(next(sheet_rows)) != VALUE_COLUMNS:
            raise ValueError("Workbook parameter schema differs.")
        for values in sheet_rows:
            if all(value is None for value in values):
                continue
            name, key_text, value, unit, scopes, *_ = values
            if name not in GROUPS[group] or unit != UNITS[name]:
                raise ValueError("Workbook field or unit differs.")
            from src.logic.effective_baseline import decoded_key

            key = decoded_key(key_text)
            for scope in scopes.split("|"):
                pop, mode = scope.split(":")
                mapping = getattr(cases[int(pop), mode][0], name)
                if key in mapping:
                    raise ValueError("Duplicate effective workbook key.")
                mapping[key] = numeric(value)
    wb.close()
    for (population, mode), (data, cfg) in cases.items():
        if identity(data, cfg) != original_manifest["cases"][f"{population}:{mode}"]:
            from src.logic.effective_baseline import first_difference

            expected, expected_cfg = load_bundle(stage, population, mode)
            difference = first_difference(expected, data, expected_cfg, cfg)
            raise ValueError(
                json.dumps(
                    {
                        "case": f"{population}:{mode}",
                        "first_divergence": difference,
                        "action": "Qualification stopped; preserve both inputs.",
                    }
                )
            )
    sources = original_manifest["source_identities"]
    sources["effective_workbook"] = {"sha256": sha256(workbook), "description": workbook.name}
    manifest = write_bundle(Path(args.output), cases, sources)
    print(
        json.dumps({"status": "effective_workbook_exported", "cases": manifest["cases"]}),
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("seed")
    p.add_argument("--archive", required=True)
    p.add_argument("--receipts", required=True)
    p.add_argument("--output", required=True)
    p = commands.add_parser("export")
    p.add_argument("--workbook", required=True)
    p.add_argument("--support", required=True)
    p.add_argument("--output", required=True)
    args = parser.parse_args()
    (seed if args.command == "seed" else export)(args)


if __name__ == "__main__":
    main()
