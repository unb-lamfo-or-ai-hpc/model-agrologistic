"""Export effective scalar inputs for source inspection; never construct or solve a MILP."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from dataclasses import asdict
from pathlib import Path

from src.logic.mathematical_contract import extensive_form_inputs, prepare_model_data
from src.logic.model_validation import validate_or_raise_model_data
from src.logic.optimization_gurobipy import (
    _origin_to_customer_unit_cost,
    _origin_to_warehouse_unit_cost,
    _warehouse_to_customer_unit_cost,
    _warehouse_to_warehouse_unit_cost,
)
from src.logic.route_filtering import select_routes


def export(data, config, output, *, provenance):
    """Map existing effective arrays to a transparent GAMS include and symbol receipt.

    Only the approved daily-factor/scalable/free-terminal/three-enabled-slack
    subset is translated. Unsupported settings fail, never silently approximate.
    Original ModelData, source workbooks and scientific code remain unmodified.
    """
    if (
        config.capacity_coupling_policy != "daily_factors"
        or config.candidate_capacity_mode != "scalable"
        or config.terminal_inventory_policy != "free"
        or config.terminal_inventory_penalty != 0
        or not all(
            (
                config.allow_unmet_domestic_demand,
                config.allow_emergency_static_capacity,
                config.allow_emergency_reception_capacity,
            )
        )
    ):
        raise ValueError("Configuration outside the documented GAMS translation.")
    prepared = prepare_model_data(data, config)
    effective, stochastic_config = extensive_form_inputs(prepared, config)
    validate_or_raise_model_data(effective, stochastic_config)
    routes = select_routes(effective, stochastic_config)
    domains = {
        "o": effective.origins,
        "w": effective.warehouses,
        "c": effective.customers,
        "p": effective.products,
        "t": effective.periods,
        "s": effective.scenarios,
    }
    maps = {
        kind: {value: f"{kind}{i:05}" for i, value in enumerate(values)}
        for kind, values in domains.items()
    }
    # The DET wrapper explicitly checks this stable semantic singleton label.
    if config.mode == "det":
        maps["s"] = {"deterministic": "deterministic"}
    lines = ["* Generated from effective Python arrays; see data_manifest.json."]

    def labels(kinds, key):
        return ",".join("'" + maps[k][v] + "'" for k, v in zip(kinds, key, strict=True))

    def set_values(name, kinds, values):
        for key in values:
            key = (key,) if len(kinds) == 1 else key
            lines.append(f"{name}({labels(kinds, key)}) = yes;")

    def value(number):
        number = float(number)
        if math.isnan(number) or number == -math.inf:
            raise ValueError("Nonfinite effective input.")
        return "inf" if number == math.inf else repr(number)

    def parameter(name, kinds, items):
        for key, number in items:
            key = (key,) if len(kinds) == 1 else key
            lines.append(f"{name}({labels(kinds, key)}) = {value(number)};")

    # Base domains must be STATIC GAMS data statements, not assigned dynamic
    # sets (which cannot subsequently be declaration domains).
    lines.append("$onEmpty")
    for kind, pairs in maps.items():
        lines.append(
            f"Set {kind} / " + ", ".join("'" + label + "'" for label in pairs.values()) + " /;"
        )
    lines.append("$offEmpty")
    # Explicit predecessor relation avoids reliance on GAMS global UEL ordering
    # or lag operators on dynamically populated input sets.
    set_values("firstPeriod", "t", effective.periods[:1])
    set_values("predecessor", "tt", zip(effective.periods[1:], effective.periods[:-1], strict=True))
    set_values("n", "w", effective.candidate_warehouses)
    set_values("old", "w", effective.existing_warehouses)
    set_values(
        "ex",
        "w",
        [
            w
            for w in effective.warehouses
            if config.allow_capacity_expansion and effective.max_expand_capacity.get(w, 0) > 0
        ],
    )
    set_values(
        "bulk",
        "w",
        [
            w
            for w in effective.bulk_eligible_warehouses
            if config.allow_bulkification
            and w in effective.warehouses
            and effective.max_bulk_capacity.get(w, 0) > 0
        ],
    )
    set_values("dom", "c", effective.domestic_customers)
    set_values("exportDest", "c", effective.export_customers)
    for symbol, kinds, family in [
        ("ow", "owp", "od"),
        ("wd", "wcp", "dc"),
        ("ww", "wwp", "dd"),
        ("direct", "ocp", "oc"),
    ]:
        set_values(symbol, kinds, sorted(getattr(routes, family)))
    for symbol, kinds, attribute in [
        ("pi", "s", "scenario_prob"),
        ("supply", "sopt", "supply_s"),
        ("demand", "scpt", "demand_dom_s"),
        ("exportCap", "scpt", "demand_exp_s"),
        ("initial", "wp", "initial_inventory"),
        ("stock0", "w", "static_capacity"),
        ("receive0", "w", "reception_capacity"),
        ("ship0", "w", "shipping_capacity"),
        ("maxNew", "w", "max_candidate_capacity"),
        ("maxExp", "w", "max_expand_capacity"),
        ("maxBulk", "w", "max_bulk_capacity"),
        ("fixedNew", "w", "opening_fixed_cost"),
        ("unitNew", "w", "candidate_capacity_cost"),
        ("fixedExp", "w", "expand_fixed_cost"),
        ("unitExp", "w", "expand_variable_cost"),
        ("fixedBulk", "w", "bulk_fixed_cost"),
        ("unitBulk", "w", "bulk_variable_cost"),
        ("hold", "wp", "storage_tariff"),
    ]:
        parameter(symbol, kinds, sorted(getattr(effective, attribute).items()))
    parameter(
        "penaltyD",
        "cp",
        (
            ((c, p), effective.unmet_demand_penalty.get((c, p), 1e6))
            for c in effective.domestic_customers
            for p in effective.products
        ),
    )
    for symbol, mapping in [
        ("penaltyK", effective.emergency_static_capacity_penalty),
        ("penaltyR", effective.emergency_reception_capacity_penalty),
    ]:
        parameter(symbol, "w", ((w, mapping.get(w, 1e6)) for w in effective.warehouses))
    parameter("days", "t", ((t, config.operating_days(t)) for t in effective.periods))
    cost_helpers = [
        ("costOW", "owp", routes.od, _origin_to_warehouse_unit_cost),
        ("costWD", "wcp", routes.dc, _warehouse_to_customer_unit_cost),
        ("costOD", "ocp", routes.oc, _origin_to_customer_unit_cost),
    ]
    for symbol, kinds, arcs, helper in cost_helpers:
        parameter(symbol, kinds, ((key, helper(effective, *key)) for key in sorted(arcs)))
    parameter(
        "costWW",
        "wwp",
        (
            (key, _warehouse_to_warehouse_unit_cost(effective, *key, config))
            for key in sorted(routes.dd)
        ),
    )
    for symbol, field in [
        ("rhoNew", "candidate_reception_daily_factor"),
        ("rhoExp", "expansion_reception_daily_factor"),
        ("rhoBulk", "bulkification_reception_daily_factor"),
        ("etaNew", "candidate_shipping_daily_factor"),
        ("etaExp", "expansion_shipping_daily_factor"),
        ("etaBulk", "bulkification_shipping_daily_factor"),
    ]:
        lines.append(f"{symbol} = {value(getattr(config, field))};")
    raw = ("\n".join(lines) + "\n").encode("utf-8")
    receipt = {
        "schema_version": "scalar-gams-input-v1",
        "provenance": provenance,
        "model": asdict(config),
        "mathematical_contract": prepared.metadata["mathematical_contract"],
        "symbols": {
            k: {mapped: original for original, mapped in pairs.items()} for k, pairs in maps.items()
        },
        "data_include_sha256": hashlib.sha256(raw).hexdigest(),
        "qualification": "effective parameter export; no GAMS compile or solve",
        "execution_admitted": False,
    }
    # Build/validate all bytes before creating a fresh output, never overwrite.
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output / "data.inc").write_bytes(raw)
    (output / "data_manifest.json").write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8"
    )
    return receipt


def main():
    from src.logic.excel_loader import load_model_data_from_excel
    from src.logic.experiment_runner import load_experiment_manifest

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--workbook", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sha = hashlib.sha256(args.workbook.read_bytes()).hexdigest()
    if sha != args.expected_sha256:
        raise ValueError("Workbook identity differs.")
    manifest = load_experiment_manifest(args.manifest)
    if args.index < 0 or args.index >= len(manifest.experiments):
        raise ValueError("Explicit valid case index required.")
    spec = manifest.experiments[args.index]
    data = load_model_data_from_excel(args.workbook, spec.loader)
    receipt = export(
        data,
        spec.model,
        args.output,
        provenance={
            "workbook_sha256": sha,
            "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
            "case_index": args.index,
            "case_name": spec.name,
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[1], text=True
            ).strip(),
        },
    )
    print(
        json.dumps(
            {
                "status": receipt["qualification"],
                "data_include_sha256": receipt["data_include_sha256"],
                "execution_admitted": False,
            }
        )
    )


if __name__ == "__main__":
    main()
