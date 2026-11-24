"""Version two approved review views over a hash-frozen effective bundle.

No solver, source workbook write, registry selection or coordinate adjustment.
The existing exporter remains the only XLSX-to-ModelData implementation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.prepare_effective_baseline import sheet, workbook_payload  # noqa: E402
from src.logic.effective_baseline import load_bundle  # noqa: E402


def payloads(support, reviewed_registry, frozen_manifest):
    """Create inspectable JSON payloads, retaining all source registry values."""
    sheets = workbook_payload(support)
    by_name = {s["name"]: s for s in sheets}
    ids = by_name["Identification"]["rows"]
    ids[:] = [r for r in ids if r[0] != "pending"]
    ids.extend(
        [
            ["workbook_version", 2],
            ["presentation_schema", "agrologistic-workbook-view-v2"],
            [
                "approved_controls",
                (
                    "beta: domestic service floor; alpha: export share ceiling; K: candidate and "
                    "expansion ceilings"
                ),
            ],
            ["reference_case", "K=1; beta and alpha disabled; historical coefficients unchanged"],
            [
                "calibration",
                "Positive fixed costs and empirical recalibration are separate future decisions",
            ],
            [
                "investment_cost",
                (
                    "Unit cost in BRL/t times physical installed tonnes, once; fixed costs stay "
                    "unchanged"
                ),
            ],
            [
                "registry",
                "Complete CONAB list retained, as confirmed by the researcher (Artur, 2026)",
            ],
        ]
    )
    ids.extend(
        [
            [
                "reviewed_source_sha256",
                frozen_manifest["agrologistic_effective_baseline_v1_revised.xlsx"],
            ],
            [
                "investment_view_scope",
                "h500 union of frozen populations. Membership and order "
                "remain in Registry and Sets. Only selected facilities enter each model.",
            ],
        ]
    )
    dictionary = by_name["Dictionary"]
    dictionary["columns"] = ["field", "unit", "definition", "indices", "role", "missingness"]
    for row in dictionary["rows"]:
        name, unit, _ = row
        definition = {
            "supply": "Tonnes offered at each origin, product and month in DET.",
            "supply_s": "Tonnes offered at each scenario, origin, product and month in STO.",
            "demand_dom": "Domestic required tonnes per customer, product and month in DET.",
            "demand_dom_s": "Domestic required tonnes per scenario, customer, product and month.",
            "demand_exp": "Historical export upper bound per destination, product and month.",
            "demand_exp_s": "Historical export upper bound per scenario, destination, "
            "product and month.",
            "scenario_prob": "Probability of one of the nine STO trajectories, equal to 1/9.",
            "static_capacity": "Initial installed static tonnes. "
            "Selected candidates start at zero.",
            "initial_inventory": "Initial stock tonnes per facility and product, "
            "zero in baseline.",
            "storage_tariff": "Charge per warehouse, product and tonne held for one period.",
            "freight_origin": "Unit freight rate for origin outbound transport.",
            "freight_dest": "Unit freight rate for direct origin-customer transport, "
            "inactive in W.",
            "freight_warehouse": "Unit freight rate for warehouse outbound transport.",
            "transshipment_cost": "Handling cost per tonne passing through the facility.",
            "unmet_demand_penalty": "Charge per unmet domestic tonne by customer and product.",
            "emergency_reception_capacity_penalty": "Charge per tonne of reception above "
            "installed period capacity.",
        }.get(name, name.replace("_", " "))
        role = "Effective baseline input"
        missing = "Required effective keys retained exactly; no zero substitution"
        if name.startswith("duration_"):
            definition = (
                "Optional travel duration in seconds. Empty in this baseline; not used to "
                "calculate freight."
            )
            role = "Optional unused annotation"
            missing = "Absent values remain absent; never interpreted as distance zero"
        if name == "max_candidate_capacity":
            definition = (
                "Reference candidate opening ceiling. Controls K scales this bound once. "
                "Initial candidate capacity remains zero."
            )
        if name == "max_expand_capacity":
            definition = (
                "Reference existing-site expansion ceiling, 25% of initial static capacity. "
                "Controls K scales this bound once."
            )
        if name == "max_bulk_capacity":
            definition = "Reference bulk-handling investment basis; unchanged by K."
        if name in ("reception_capacity", "shipping_capacity"):
            definition = (
                "Effective daily rate. Multiply by Calendar operating days once when "
                "constructing period capacity."
            )
        if name in ("candidate_capacity_cost", "expand_variable_cost", "bulk_variable_cost"):
            definition = (
                "Unit investment cost per physical installed tonne of the respective "
                "investment basis. K changes bounds, not this rate."
            )
        if name in ("opening_fixed_cost", "expand_fixed_cost", "bulk_fixed_cost"):
            definition = (
                "Effective fixed investment charge, including verified zero. A multiplier "
                "cannot make a zero charge positive."
            )
        if name == "emergency_static_capacity_penalty":
            definition = (
                "Charge per tonne of inventory above installed static capacity in each period."
            )
        row[:] = [
            name,
            unit,
            definition,
            "Ordered key_json indices in parameter sheet",
            role,
            missing,
        ]
    for code, desc in [
        ("od", "origin to warehouse (OW)"),
        ("dc", "warehouse to customer (WD)"),
        ("dd", "warehouse to warehouse (WW)"),
        ("oc", "direct origin to customer; inactive in W"),
    ]:
        dictionary["rows"].append(
            [
                f"dist_{code}",
                "km",
                f"OSRM road distance: {desc}. "
                "Freight = BRL/(t*km) x km x flow tonnes. No duration-to-distance conversion.",
                "origin, destination; product-indexed selected arcs in arcs.csv",
                "Frozen normalized network support",
                "Unavailable/absent arcs differ from valid zero distance",
            ]
        )
    dictionary["rows"].extend(
        [
            [
                "K",
                "multiplier",
                "Positive multiplier of reference candidate and expansion "
                "ceilings, applied once. K=1 is neutral. "
                "Initial capacities and unit costs are unchanged.",
                "Controls; same value for all selected sites",
                "Approved optional scenario input",
                "Required positive finite number",
            ],
            [
                "beta",
                "fraction",
                "Minimum domestic service share, per product and scenario, "
                "aggregated over the full horizon. Disabled in the neutral reference.",
                "product, scenario; common fraction in Controls",
                "Approved optional policy",
                "Blank when disabled; [0,1] required when enabled",
            ],
            [
                "alpha",
                "fraction",
                "Maximum exported share of offered supply, per product and "
                "scenario over the full horizon. Existing destination-period export bounds remain.",
                "product, scenario; common fraction in Controls",
                "Approved optional policy",
                "Blank when disabled; [0,1] required when enabled",
            ],
        ]
    )
    by_name["Transformations"]["rows"] = [
        [
            "penalties",
            "Frozen effective coefficients",
            (
                "Unmet demand 90000 BRL/t; static excess 45000 BRL/t per period; reception "
                "excess 45000 BRL/t. No implicit recalculation."
            ),
        ],
        [
            "expansion",
            "Reference ceiling = 0.25 x initial static tonnes",
            (
                "Scenario ceiling = K x reference ceiling. Installed expansion is a separate "
                "optimization decision."
            ),
        ],
        [
            "candidate",
            "Reference ceiling = declared source static tonnes",
            (
                "Initial modeled static/reception/shipping capacity is zero. Scenario opening"
                " ceiling = K x reference ceiling."
            ),
        ],
        [
            "investment cost",
            "Reference unit cost and fixed component retained",
            (
                "Charge = unit cost x physical installed tonnes + fixed charge x activation. "
                "Do not multiply physical tonnes by K twice."
            ),
        ],
        [
            "rates",
            "Model convention: t/day",
            (
                "Daily rate multiplied once by 30 operating days per period. Source ambiguity"
                " is documented, not empirically recalibrated."
            ),
        ],
        [
            "scenarios",
            "Frozen nine-scenario STO design",
            "Nine equiprobable trajectories; DET arrays retained.",
        ],
        [
            "policies",
            "Approved full-horizon product/scenario scope",
            (
                "beta optionally limits shortage relative to domestic demand; alpha "
                "optionally caps exports relative to supply. Historic destination/period "
                "export bounds retained."
            ),
        ],
        [
            "freight",
            "Effective rate x frozen OSRM kilometres",
            (
                "Duration fields in seconds are optional unused annotations. No routing or "
                "distance recomputation."
            ),
        ],
    ]
    controls = sheet(
        "Controls",
        ["parameter", "value", "unit", "meaning", "reference"],
        [
            [
                "scenario_id",
                "baseline",
                "identifier",
                "Use a new identifier for any non-neutral case.",
                "baseline",
            ],
            [
                "K",
                1,
                "multiplier",
                (
                    "Scale candidate opening and existing expansion ceilings once. Bulk-handling "
                    "ceiling is unchanged."
                ),
                1,
            ],
            [
                "beta_enabled",
                0,
                "0/1",
                (
                    "1 enables the approved full-horizon domestic service floor for every "
                    "product/scenario."
                ),
                0,
            ],
            [
                "beta",
                None,
                "fraction",
                (
                    "Enter a fraction in [0,1] when enabled. Disabled reference has no domestic "
                    "service floor."
                ),
                None,
            ],
            [
                "alpha_enabled",
                0,
                "0/1",
                (
                    "1 enables the approved full-horizon export share ceiling for every "
                    "product/scenario."
                ),
                0,
            ],
            [
                "alpha",
                None,
                "fraction",
                (
                    "Enter a fraction in [0,1] when enabled. Historic destination/period export "
                    "bounds remain."
                ),
                None,
            ],
            [
                "justification",
                "Neutral baseline; no experimental levels selected.",
                "text",
                "Describe the scientific reason for a non-neutral case.",
                "Neutral baseline; no experimental levels selected.",
            ],
            [
                "existing_expansion_fraction",
                None,
                "fraction",
                "Derived maximum added static capacity divided by initial existing capacity.",
                0.25,
            ],
            [
                "capacity_semantics",
                "Bounds are potential investments, not installed capacity or optimized output.",
                "definition",
                (
                    "No aggregate investment budget is introduced. Static excess retains its "
                    "effective penalty."
                ),
                None,
            ],
        ],
    )
    controls["formulas"] = {"B9": "=0.25*B3"}
    data, _ = load_bundle(support, 500, "sto")
    limits = []
    for investment, field, costfield, fixedfield in [
        ("candidate", "max_candidate_capacity", "candidate_capacity_cost", "opening_fixed_cost"),
        ("expansion", "max_expand_capacity", "expand_variable_cost", "expand_fixed_cost"),
        ("bulk", "max_bulk_capacity", "bulk_variable_cost", "bulk_fixed_cost"),
    ]:
        for cda, value in getattr(data, field).items():
            if value <= 0:
                continue
            limits.append(
                [
                    cda,
                    investment,
                    value,
                    None,
                    None,
                    getattr(data, costfield).get(cda, 0),
                    getattr(data, fixedfield).get(cda, 0),
                    "BRL/t x physical installed tonnes + BRL fixed activation",
                ]
            )
    limsheet = sheet(
        "InvestmentLimits",
        [
            "warehouse_id",
            "investment",
            "reference_limit_t",
            "multiplier",
            "scenario_limit_t",
            "unit_cost_BRL_t",
            "fixed_cost_BRL",
            "cost_basis",
        ],
        limits,
    )
    limsheet["formulas"] = {}
    for i, row in enumerate(limits, 2):
        limsheet["formulas"][f"D{i}"] = "=Controls!$B$3" if row[1] != "bulk" else "=1"
        limsheet["formulas"][f"E{i}"] = f"=C{i}*D{i}"
    by_name["ParameterTemplate"]["rows"] = [
        [
            json.dumps(
                {
                    "scenario_id": "baseline",
                    "multipliers": {"candidate_limit": 1, "expansion_limit": 1},
                    "beta": None,
                    "alpha": None,
                    "justification": "Neutral baseline; no experimental levels selected.",
                }
            ),
            (
                "Controls is authoritative. K maps to existing candidate_limit and "
                "expansion_limit multipliers."
            ),
        ]
    ]
    # Changes to presentation order do not affect keyed CSV or ModelData order.
    order = ["Identification", "Controls", "InvestmentLimits", "Dictionary"]
    sheets = (
        [by_name[n] for n in order if n in by_name]
        + [controls, limsheet]
        + [s for s in sheets if s["name"] not in order]
    )
    sheets.sort(key=lambda s: order.index(s["name"]) if s["name"] in order else len(order))
    reviewed_registry = Path(reviewed_registry)
    if reviewed_registry.suffix.lower() == ".xlsx":
        import openpyxl

        expected = frozen_manifest["agrologistic_warehouse_registry_v1_revised.xlsx"]
        if hashlib.sha256(reviewed_registry.read_bytes()).hexdigest() != expected:
            raise ValueError("Reviewed registry file identity differs.")
        wb = openpyxl.load_workbook(reviewed_registry, read_only=True, data_only=True)
        try:
            reviewed = {name: list(wb[name].values) for name in ("Identification", "Registry")}
        finally:
            wb.close()
    else:
        reviewed = json.loads(reviewed_registry.read_text(encoding="utf8"))
    registry = [list(row) for row in reviewed["Registry"] if any(v is not None for v in row)]
    columns, rows = registry[0], registry[1:]
    original_columns = list(columns)
    # Source placeholders stay numeric and are explicitly separated from effective bounds.
    columns[9] = "Reception source value (model t/day)"
    columns[10] = "Shipping source value (model t/day)"
    columns[11] = "Maximum static capacity - source placeholder (t)"
    columns[12] = "Opening cost - source placeholder (BRL)"
    columns.extend(
        [
            "expansion_limit_ref_t",
            "opening_unit_cost_BRL_t",
            "expansion_unit_cost_BRL_t",
            "bulk_unit_cost_BRL_t",
        ]
    )
    cda_idx = columns.index("CDA")
    for row in rows:
        cda = str(row[cda_idx])
        if cda in data.candidate_warehouses:
            text = (
                "Selected candidate: initial modeled static/reception/shipping = 0; declared "
                "static capacity is the reference opening ceiling."
            )
        elif cda in data.existing_warehouses:
            text = (
                "Selected existing facility: effective initial capacities retained; reference"
                " expansion ceiling = 25% of initial static capacity."
            )
        else:
            text = (
                "Outside h215-h500 modeled populations: source values retained; effective "
                "model fields remain blank."
            )
        row[original_columns.index("transformation")] = text
        row.extend(
            [
                getattr(data, field).get(cda) if cda in data.warehouses else None
                for field in (
                    "max_expand_capacity",
                    "candidate_capacity_cost",
                    "expand_variable_cost",
                    "bulk_variable_cost",
                )
            ]
        )
    regdict = []
    for i, name in enumerate(columns):
        unit = "identifier" if name == "CDA" else "text"
        meaning = "Accepted source registry value; complete list retained."
        role = "Source registry"
        missing = "Preserve source blanks and zeros"
        if name.startswith("Em_h"):
            unit = "0/1"
            meaning = "Membership only; not opening, investment or use."
            role = "Frozen population membership"
        if name.startswith("order_"):
            unit = "zero-based position"
            meaning = "Frozen population selection order."
            role = "Frozen population order"
            missing = "Blank outside the population"
        if name.startswith(("model_", "candidate_limit", "expansion_limit")):
            unit = "t/day" if name.endswith("t_day") else "t"
            role = "Effective baseline reference"
            missing = "Blank outside h500; zero only when defined"
            meaning = (
                "Effective initial capacity"
                if name.startswith("model_")
                else (
                    "Reference investment ceiling at K=1. Candidate/expansion scenario ceilings "
                    "are derived in baseline InvestmentLimits."
                )
            )
        if i == 11:
            unit = "t"
            meaning = (
                "Original zero placeholder, not the effective candidate or expansion "
                "investment limit."
            )
        if i == 12:
            unit = "BRL"
            meaning = (
                "Original zero placeholder; effective installed-tonne investment rates appear"
                " in separate fields."
            )
        if i in (9, 10):
            unit = "t/day (model convention)"
            meaning = (
                "Source heading omitted /day. Numerical value retained. Model uses daily "
                "rate; multiply by 30 once for period capacity."
            )
        if i == 8:
            unit = "t"
            meaning = (
                "Declared source static capacity; candidates start at modeled capacity zero "
                "and may invest up to K times this reference."
            )
        if name.endswith("unit_cost_BRL_t"):
            unit = "BRL/t"
            role = "Effective model investment rate"
            meaning = (
                "Multiply by physical installed tonnes once. Missing for non-applicable "
                "investment types."
            )
            missing = "Blank where not applicable"
        if name in ("Latitude", "Longitude"):
            unit = "degrees"
            meaning = "Accepted source coordinate preserved without rounding or coalescing."
        if name == "modeled_in_baseline":
            unit = "0/1"
            meaning = "Included in frozen h500 effective baseline, not an optimized decision."
        regdict.append([name, unit, meaning, role, missing, "CDA; stable source order"])
    regids = [r for r in reviewed["Identification"][1:] if r[0] and r[0] != "units"]
    regids.extend(
        [
            ["workbook_version", 2],
            ["presentation_schema", "agrologistic-warehouse-view-v2"],
            [
                "registry_attestation",
                (
                    "Researcher confirms complete list matches CONAB source downloaded by Artur "
                    "(2026). No warehouse identity audit requested."
                ),
            ],
            [
                "controls",
                (
                    "K/alpha/beta have a single authoritative input in effective baseline "
                    "Controls. This registry shows reference values at K=1."
                ),
            ],
            [
                "units",
                (
                    "BRL currency; static tonnes; modeled reception/shipping t/day; raw "
                    "placeholders separated from effective limits."
                ),
            ],
            [
                "reviewed_source_sha256",
                frozen_manifest["agrologistic_warehouse_registry_v1_revised.xlsx"],
            ],
        ]
    )
    return {"sheets": sheets}, {
        "sheets": [
            sheet("Identification", ["item", "value"], regids),
            sheet(
                "Dictionary", ["field", "unit", "definition", "role", "missingness", "key"], regdict
            ),
            sheet("Registry", columns, rows),
        ]
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--support", type=Path, required=True)
    p.add_argument("--registry-records", type=Path, required=True)
    p.add_argument("--frozen-manifest", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(a.frozen_manifest.read_text(encoding="utf8"))
    for name, payload in zip(
        ("baseline", "registry"), payloads(a.support, a.registry_records, manifest), strict=False
    ):
        target = a.output / f"{name}-workbook-v2.json"
        target.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False), encoding="utf8")
        print(
            json.dumps(
                {
                    "payload": name,
                    "sheets": len(payload["sheets"]),
                    "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                }
            )
        )


if __name__ == "__main__":
    main()
