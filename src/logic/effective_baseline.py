"""Lossless effective-data boundary; historical loaders and builders stay unchanged.

Local bundles may contain restricted inputs. Only schemas, code and redacted
qualification receipts belong in Git. This module never invokes an optimizer.
"""

from __future__ import annotations

import copy
import csv
import hashlib
import json
import math
from dataclasses import asdict, fields, replace
from pathlib import Path

from src.logic.mathematical_contract import canonical_hash, prepare_model_data
from src.logic.model_config import ModelConfig
from src.logic.model_data import ModelData, NodeInfo
from src.logic.route_filtering import select_routes

SCHEMA = "agrologistic-effective-baseline-v1"
SET_FIELDS = (
    "origins",
    "warehouses",
    "existing_warehouses",
    "candidate_warehouses",
    "bulk_eligible_warehouses",
    "customers",
    "domestic_customers",
    "export_customers",
    "products",
    "periods",
    "scenarios",
)
FAMILIES = {"OW": "od", "WD": "dc", "WW": "dd"}
MAP_FIELDS = tuple(
    f.name
    for f in fields(ModelData)
    if f.name not in (*SET_FIELDS, "metadata", "node_info")
    and not f.name.startswith(("routes_", "dist_"))
)
UNITS = {
    **dict.fromkeys(
        ("supply", "supply_s", "demand_dom", "demand_dom_s", "demand_exp", "demand_exp_s"),
        "t/period",
    ),
    **dict.fromkeys(
        (
            "static_capacity",
            "max_candidate_capacity",
            "max_expand_capacity",
            "max_bulk_capacity",
            "initial_inventory",
        ),
        "t",
    ),
    "reception_capacity": "t/day",
    "shipping_capacity": "t/day",
    **dict.fromkeys(("freight_origin", "freight_dest", "freight_warehouse"), "BRL/(t*km)"),
    **dict.fromkeys(
        (
            "transshipment_cost",
            "candidate_capacity_cost",
            "expand_variable_cost",
            "bulk_variable_cost",
            "unmet_demand_penalty",
            "emergency_reception_capacity_penalty",
        ),
        "BRL/t",
    ),
    **dict.fromkeys(("opening_fixed_cost", "expand_fixed_cost", "bulk_fixed_cost"), "BRL"),
    "storage_tariff": "BRL/(t*period)",
    "emergency_static_capacity_penalty": "BRL/t_excess_per_period",
    "scenario_prob": "probability",
    **dict.fromkeys(("duration_od", "duration_dc", "duration_dd", "duration_oc"), "s"),
}
EXPECTED_INPUTS = {
    215: "40edb66585daca9cc393cab1f86bde6d4528a5f34b6afc57260cc1684396da4e",
    300: "7761cce77cf93dcba2f617714f0117c1f2ead4de0c3f27149daceba447e0c7d1",
    400: "c3085456997714ef5a8bdbf61e2c9a5e578c2636003947427cf58933d21ceb13",
    500: "888fbff42e4f80817d4d5f0101049495c86c6ed4cda75f00813779dadab41515",
}
ORIGIN_CLASSES = {
    "static_capacity": "source_static_value_or_derived_candidate_zero",
    "reception_capacity": "source_value_model_adopts_t_per_day",
    "shipping_capacity": "source_value_model_adopts_t_per_day",
    "initial_inventory": "historical_zero_default_not_observed_stock",
    "storage_tariff": "approximate_historical_reference_equivalence_pending",
    "candidate_capacity_cost": "historical_reference_not_empirically_calibrated",
    "expand_variable_cost": "historical_reference_not_empirically_calibrated",
    "bulk_variable_cost": "historical_reference_not_empirically_calibrated",
    "unmet_demand_penalty": "synthetic_penalty_derived_by_historical_rule",
    "emergency_static_capacity_penalty": "synthetic_penalty_derived_by_historical_rule",
    "emergency_reception_capacity_penalty": "synthetic_penalty_derived_by_historical_rule",
    "opening_fixed_cost": "resolved_historical_fixed_component_including_zero",
    "expand_fixed_cost": "resolved_historical_fixed_component_including_zero",
    "bulk_fixed_cost": "resolved_historical_fixed_component_including_zero",
    "scenario_prob": "synthetic_equiprobable_scenario_design",
}
PARAMETER_COLUMNS = (
    "population",
    "mode",
    "field",
    "key_json",
    "value",
    "unit",
    "source_id",
    "transformation",
    "origin_class",
    "usage_class",
)
ARC_COLUMNS = (
    "population",
    "origin_id",
    "destination_id",
    "arc_family",
    "product",
    "osrm_distance_km",
    "distance_status",
    "arc_active",
    "source_id",
    "policy_id",
    "origin_role",
    "destination_role",
    "record_order",
)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dump(path, value):
    Path(path).write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def annotation_json(value, missing, location=""):
    """Represent missing OPTIONAL annotations as null, never numerical model maps."""
    if isinstance(value, float) and not math.isfinite(value):
        missing.append(location)
        return None
    if isinstance(value, dict):
        return {k: annotation_json(v, missing, f"{location}/{k}") for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [annotation_json(v, missing, f"{location}/{i}") for i, v in enumerate(value)]
    return value


def write_csv(path, columns, rows):
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path, columns):
    with Path(path).open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(columns):
            raise ValueError(f"Unexpected CSV schema: {Path(path).name}")
        yield from reader


def numeric(value):
    if isinstance(value, bool) or value is None or value == "":
        raise ValueError("Missing or boolean numerical value.")
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError("A finite nonnegative value is required.")
    return value


def encoded_key(key):
    return json.dumps(key, ensure_ascii=False, separators=(",", ":"))


def decoded_key(text):
    value = json.loads(text)
    if isinstance(value, list) and value and all(isinstance(x, str) and x for x in value):
        return tuple(value)
    if isinstance(value, str) and value:
        return value
    raise ValueError("Parameter keys must contain nonempty string identifiers.")


def effective_projection(data, config):
    """Retain consumed routes/distances; original complete matrices stay at source."""
    if config.use_direct_origin_customer or not config.use_warehouse_transshipment:
        raise ValueError("New effective bundles support W topology only.")
    prepared = prepare_model_data(data, config)
    routes = select_routes(prepared, config)
    changes = {}
    for code in ("od", "dc", "dd", "oc"):
        chosen = set(getattr(routes, code)) if code != "oc" else set()
        changes[f"routes_{code}"] = chosen
        pairs = {arc[:2] for arc in chosen}
        changes[f"dist_{code}"] = {
            k: v for k, v in getattr(prepared, f"dist_{code}").items() if k in pairs
        }
        changes[f"duration_{code}"] = {
            k: v for k, v in getattr(prepared, f"duration_{code}").items() if k in pairs
        }
    # Historical base arrays may be sparse. The builder reads absent quantities
    # as zero. Materialize those consumed zeros explicitly, with no unit conversion.
    for name, nodes in (
        ("supply", data.origins),
        ("demand_dom", data.domestic_customers),
        ("demand_exp", data.export_customers),
    ):
        original = getattr(prepared, name)
        changes[name] = {
            (n, p, t): original.get((n, p, t), 0.0)
            for n in nodes
            for p in data.products
            for t in data.periods
        }
    changes["initial_inventory"] = {
        (w, p): prepared.initial_inventory.get((w, p), 0.0)
        for w in prepared.warehouses
        for p in prepared.products
    }
    return replace(prepared, **changes, metadata=copy.deepcopy(prepared.metadata))


def identity(data, config):
    """Exact ordered algebra-input identity, excluding noncomputational node labels."""
    payload = {name: list(getattr(data, name)) for name in SET_FIELDS}
    for name in MAP_FIELDS:
        payload[name] = [
            [encoded_key(k), numeric(v).hex()] for k, v in sorted(getattr(data, name).items())
        ]
    for code in ("od", "dc", "dd", "oc"):
        payload[f"routes_{code}"] = sorted(getattr(data, f"routes_{code}"))
        payload[f"dist_{code}"] = [
            [*k, numeric(v).hex()] for k, v in sorted(getattr(data, f"dist_{code}").items())
        ]
    payload["model_config"] = asdict(config)
    return canonical_hash(payload)


def first_difference(expected, actual, expected_config, actual_config):
    """Locate a data/configuration mismatch without accepting a numerical tolerance."""
    for name in SET_FIELDS:
        left, right = getattr(expected, name), getattr(actual, name)
        if left != right:
            for i in range(max(len(left), len(right))):
                a = left[i] if i < len(left) else None
                b = right[i] if i < len(right) else None
                if a != b:
                    return {
                        "field": name,
                        "position": i,
                        "expected": a,
                        "actual": b,
                        "effect": "Index membership/order changes algebra or scenario weighting",
                    }
    for name in (*MAP_FIELDS, "dist_od", "dist_dc", "dist_dd", "dist_oc"):
        left, right = getattr(expected, name), getattr(actual, name)
        for key in sorted(left.keys() | right.keys()):
            if key not in left or key not in right or numeric(left[key]) != numeric(right[key]):
                return {
                    "field": name,
                    "key": key,
                    "expected": left.get(key),
                    "actual": right.get(key),
                    "unit": UNITS.get(name, "km"),
                    "effect": "Effective coefficient, bound, RHS or input domain changes",
                }
    for code in ("od", "dc", "dd", "oc"):
        left, right = getattr(expected, "routes_" + code), getattr(actual, "routes_" + code)
        if left != right:
            return {
                "field": "routes_" + code,
                "first_arc": sorted(left ^ right)[0],
                "effect": "Selected directed/product-indexed graph changes",
            }
    for name, value in asdict(expected_config).items():
        observed = getattr(actual_config, name)
        if value != observed:
            return {
                "field": "ModelConfig." + name,
                "expected": value,
                "actual": observed,
                "effect": "Mathematical configuration changes",
            }
    return None


def validate(data, config):
    """Reject missing/duplicate semantics before handing data to the existing builder."""
    if config.objective_policy != "penalty" or config.capacity_coupling_policy != "daily_factors":
        raise ValueError("The scalar daily-capacity contract is required.")
    if config.use_direct_origin_customer or not config.use_warehouse_transshipment:
        raise ValueError("W topology required.")
    for name in SET_FIELDS:
        values = getattr(data, name)
        if len(values) != len(set(values)) or any(not isinstance(x, str) or not x for x in values):
            raise ValueError(f"Invalid or duplicate identifiers: {name}")
    if set(data.existing_warehouses) & set(data.candidate_warehouses):
        raise ValueError("Existing and candidate sets overlap.")
    if set(data.warehouses) != set(data.existing_warehouses) | set(data.candidate_warehouses):
        raise ValueError("Warehouse membership differs.")
    if set(data.domestic_customers) & set(data.export_customers):
        raise ValueError("Domestic and export roles need distinct identifiers.")
    if set(data.customers) != set(data.domestic_customers) | set(data.export_customers):
        raise ValueError("Customer roles differ.")
    for name in MAP_FIELDS:
        for value in getattr(data, name).values():
            numeric(value)
    if config.mode == "sto":
        if set(data.scenario_prob) != set(data.scenarios) or not math.isclose(
            sum(data.scenario_prob.values()), 1, rel_tol=0, abs_tol=1e-12
        ):
            raise ValueError("Scenario probabilities differ from the declared scenario set.")
    elif data.scenarios or data.scenario_prob:
        raise ValueError("DET must use deterministic arrays; embedding belongs to the builder.")
    for name, nodes in (
        ("supply", data.origins),
        ("demand_dom", data.domestic_customers),
        ("demand_exp", data.export_customers),
    ):
        expected = {(n, p, t) for n in nodes for p in data.products for t in data.periods}
        if set(getattr(data, name)) != expected:
            raise ValueError(f"Incomplete or extraneous keys: {name}")
        if config.mode == "sto":
            expected_s = {(s, *k) for s in data.scenarios for k in expected}
            if set(getattr(data, name + "_s")) != expected_s:
                raise ValueError(f"Incomplete scenario keys: {name}")
    for name in (
        "static_capacity",
        "reception_capacity",
        "shipping_capacity",
        "emergency_static_capacity_penalty",
        "emergency_reception_capacity_penalty",
    ):
        if set(getattr(data, name)) != set(data.warehouses):
            raise ValueError(f"Incomplete facility parameter: {name}")
    for name in ("max_candidate_capacity", "opening_fixed_cost", "candidate_capacity_cost"):
        if set(getattr(data, name)) != set(data.candidate_warehouses):
            raise ValueError(f"Incomplete candidate parameter: {name}")
    frozen = data.metadata.get("_frozen_routes", {})
    for family, code in FAMILIES.items():
        routes = getattr(data, "routes_" + code)
        pairs = set()
        for a, b, p in routes:
            aa = data.origins if family == "OW" else data.warehouses
            bb = data.customers if family == "WD" else data.warehouses
            if a not in aa or b not in bb or p not in data.products or (family == "WW" and a == b):
                raise ValueError("An arc has invalid endpoints or product.")
            pairs.add((a, b))
        distances = getattr(data, "dist_" + code)
        if set(distances) != pairs:
            raise ValueError("Missing or unused effective distance.")
        for value in distances.values():
            numeric(value)
        if set(map(tuple, frozen.get(code, []))) != routes:
            raise ValueError("Frozen selected graph differs from effective arcs.")
    if data.routes_oc or data.dist_oc:
        raise ValueError("Direct arcs cannot enter the W experimental boundary.")
    for name in ("reception_capacity", "shipping_capacity", "static_capacity"):
        if any(getattr(data, name)[w] != 0 for w in data.candidate_warehouses):
            raise ValueError("Candidates must retain zero initial modeled capacities.")
    if any(config.operating_days(t) != 30 for t in data.periods):
        raise ValueError("The qualified effective baseline uses 30 operating days.")
    return identity(data, config)


def seal(data, config, provenance):
    """Refresh effective metadata without replaying historical penalty derivations."""
    result = replace(data, metadata=copy.deepcopy(data.metadata))
    vector = {
        "unmet": [[*key, value] for key, value in sorted(result.unmet_demand_penalty.items())],
        "static": sorted(result.emergency_static_capacity_penalty.items()),
        "reception": sorted(result.emergency_reception_capacity_penalty.items()),
    }
    result.metadata["historical_penalty_policy"] = result.metadata.get(
        "historical_penalty_policy", result.metadata.get("penalty_policy")
    )
    result.metadata["penalty_policy"] = "fixed"
    contract = result.metadata["mathematical_contract"]
    contract.update(
        penalty_vector=vector,
        penalty_vector_sha256=canonical_hash(vector),
        penalty_scope="explicit_effective_vector",
    )
    result.metadata["effective_baseline"] = {
        "schema": SCHEMA,
        **provenance,
        "input_sha256": validate(result, config),
    }
    return result


def write_bundle(directory, cases, sources):
    """Write local normalized effective data, preserving binary64 round trips."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    set_rows, parameter_rows, arc_rows, configs, metadata, nodes = [], [], [], {}, {}, {}
    seen_populations = set()
    for (population, mode), (data, cfg) in sorted(cases.items()):
        if mode != cfg.mode:
            raise ValueError("Case label and mathematical model mode differ.")
        if data.metadata.get("effective_baseline", {}).get("scenario_id", "baseline") != "baseline":
            raise ValueError("An experimental scenario cannot be relabeled as a baseline bundle.")
        observed = validate(data, cfg)
        sealed = data.metadata.get("effective_baseline", {}).get("input_sha256")
        if sealed is not None and sealed != observed:
            raise ValueError("Sealed baseline data changed before export.")
        scope = f"{population}:{mode}"
        configs[scope] = asdict(cfg)
        metadata[scope] = data.metadata
        nodes[scope] = {key: asdict(value) for key, value in data.node_info.items()}
        source = f"workbook_h{population}"
        for name in SET_FIELDS:
            set_rows.extend(
                dict(population=population, mode=mode, field=name, position=i, value=v)
                for i, v in enumerate(getattr(data, name))
            )
        for name in MAP_FIELDS:
            for key, value in sorted(getattr(data, name).items()):
                parameter_rows.append(
                    dict(
                        population=population,
                        mode=mode,
                        field=name,
                        key_json=encoded_key(key),
                        value=repr(numeric(value)),
                        unit=UNITS[name],
                        source_id=source,
                        transformation="historical_effective_freeze",
                        origin_class=ORIGIN_CLASSES.get(name, "historical_derived_effective_value"),
                        usage_class="historical_baseline",
                    )
                )
        if population in seen_populations:
            continue
        seen_populations.add(population)
        for family, code in FAMILIES.items():
            for i, (a, b, product) in enumerate(sorted(getattr(data, "routes_" + code))):
                arc_rows.append(
                    dict(
                        population=population,
                        origin_id=a,
                        destination_id=b,
                        arc_family=family,
                        product=product,
                        osrm_distance_km=repr(numeric(getattr(data, "dist_" + code)[a, b])),
                        distance_status="osrm",
                        arc_active=1,
                        source_id=source,
                        policy_id=data.metadata["mathematical_contract"]["selected_network_sha256"],
                        origin_role="origin" if family == "OW" else "warehouse",
                        destination_role=(
                            "warehouse"
                            if family != "WD"
                            else "domestic"
                            if b in data.domestic_customers
                            else "export"
                        ),
                        record_order=i,
                    )
                )
    write_csv(
        directory / "sets.csv", ("population", "mode", "field", "position", "value"), set_rows
    )
    write_csv(directory / "parameters.csv", PARAMETER_COLUMNS, parameter_rows)
    write_csv(directory / "arcs.csv", ARC_COLUMNS, arc_rows)
    optional_missing = {}
    for name, value in (
        ("configs", configs),
        ("metadata", metadata),
        ("nodes", nodes),
        ("sources", sources),
    ):
        if name in ("metadata", "nodes"):
            locations = []
            value = annotation_json(value, locations)
            optional_missing[name] = locations
        dump(directory / f"{name}.json", value)
    manifest = {
        "schema": SCHEMA,
        "private_derived_data": True,
        "files": {p.name: sha256(p) for p in sorted(directory.iterdir())},
        "cases": {f"{p}:{m}": identity(d, c) for (p, m), (d, c) in cases.items()},
        "source_identities": sources,
        "optional_annotation_nulls": {k: len(v) for k, v in optional_missing.items()},
        "scope": "Effective selected W graph; complete OSRM matrices remain at original source.",
    }
    dump(directory / "manifest.json", manifest)
    return manifest


def load_bundle(directory, population, mode):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != SCHEMA:
        raise ValueError("Unsupported effective bundle.")
    for name, expected in manifest["files"].items():
        if Path(name).name != name or sha256(directory / name) != expected:
            raise ValueError(f"Bundle hash differs: {name}")
    scope = f"{population}:{mode}"
    cfg = ModelConfig(**json.loads((directory / "configs.json").read_text(encoding="utf-8"))[scope])
    if cfg.mode != mode:
        raise ValueError("Requested mode and declared ModelConfig differ.")
    lists = {name: [] for name in SET_FIELDS}
    for row in read_csv(
        directory / "sets.csv", ("population", "mode", "field", "position", "value")
    ):
        if row["population"] == str(population) and row["mode"] == mode:
            if row["field"] not in lists or int(row["position"]) != len(lists[row["field"]]):
                raise ValueError("Set order or field differs.")
            lists[row["field"]].append(row["value"])
    data = ModelData(**lists)
    for row in read_csv(directory / "parameters.csv", PARAMETER_COLUMNS):
        if row["population"] != str(population) or row["mode"] != mode:
            continue
        name = row["field"]
        if name not in MAP_FIELDS or row["unit"] != UNITS[name]:
            raise ValueError("Unknown parameter or incompatible unit.")
        if row["source_id"] != f"workbook_h{population}":
            raise ValueError("Parameter provenance differs from the population source.")
        key = decoded_key(row["key_json"])
        mapping = getattr(data, name)
        if key in mapping:
            raise ValueError("Duplicate parameter key.")
        mapping[key] = numeric(row["value"])
    ordered = {family: 0 for family in FAMILIES}
    seen = set()
    data.metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))[scope]
    for row in read_csv(directory / "arcs.csv", ARC_COLUMNS):
        if row["population"] != str(population):
            continue
        family, a, b, p = (row[k] for k in ("arc_family", "origin_id", "destination_id", "product"))
        if family not in FAMILIES or row["arc_active"] not in ("0", "1"):
            raise ValueError("Invalid arc family or activity.")
        if (family, a, b, p) in seen:
            raise ValueError("Duplicate arc.")
        seen.add((family, a, b, p))
        if row["source_id"] != f"workbook_h{population}":
            raise ValueError("Arc provenance differs from the population source.")
        if row["policy_id"] != data.metadata["mathematical_contract"]["selected_network_sha256"]:
            raise ValueError("Arc policy identity differs.")
        expected_roles = (
            "origin" if family == "OW" else "warehouse",
            "warehouse"
            if family != "WD"
            else "domestic"
            if b in data.domestic_customers
            else "export",
        )
        if (row["origin_role"], row["destination_role"]) != expected_roles:
            raise ValueError("Arc endpoint roles differ.")
        if int(row["record_order"]) != ordered[family]:
            raise ValueError("Arc order differs.")
        ordered[family] += 1
        if row["arc_active"] == "0":
            continue
        if (
            row["distance_status"] != "osrm"
            or row["source_id"] not in manifest["source_identities"]
        ):
            raise ValueError("Active arc requires an identified OSRM distance.")
        distance = numeric(row["osrm_distance_km"])
        code = FAMILIES[family]
        mapping = getattr(data, "dist_" + code)
        if (a, b) in mapping and mapping[a, b] != distance:
            raise ValueError("Product records disagree about the physical distance.")
        mapping[a, b] = distance
        getattr(data, "routes_" + code).add((a, b, p))
    data.metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))[scope]
    raw_nodes = json.loads((directory / "nodes.json").read_text(encoding="utf-8"))[scope]
    data.node_info = {key: NodeInfo(**value) for key, value in raw_nodes.items()}
    observed = validate(data, cfg)
    if observed != manifest["cases"][scope]:
        raise ValueError("Effective data differ from the declared algebra-input identity.")
    return seal(
        data,
        cfg,
        {
            "baseline_sha256": observed,
            "scenario_id": "baseline",
            "bundle_manifest_sha256": sha256(directory / "manifest.json"),
            "source_identities": manifest["source_identities"],
            "bundle_files": manifest["files"],
        },
    ), cfg


def build_effective_model(data, config, *, max_variables=200000):
    """Thin integration with the existing Pyomo builder, with a fresh data seal."""
    expected = data.metadata.get("effective_baseline", {}).get("input_sha256")
    if validate(data, config) != expected:
        raise ValueError("Data changed after sealing; prepare an identified scenario.")
    from src.logic.optimization_pyomo import build_model

    return build_model(data, config, max_variables=max_variables)
