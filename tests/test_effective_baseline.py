"""Data/construction regression controls only; never call an optimizer."""

import copy
import csv
import json
from dataclasses import replace

import pytest

from src.logic.effective_baseline import (
    ARC_COLUMNS,
    PARAMETER_COLUMNS,
    build_effective_model,
    effective_projection,
    identity,
    load_bundle,
    seal,
    sha256,
    validate,
    write_bundle,
)
from src.logic.model_config import ModelConfig
from src.logic.parametric_scenarios import ParameterScenario, apply_scenario
from src.logic.pyomo_linear_matrix import matrix_identity
from tests.test_scalar_contract import economic_data, scenario_data


def baseline(mode="det"):
    data = economic_data()
    if mode == "sto":
        data = scenario_data(data, {"low": 0.25, "high": 0.75})
    cfg = ModelConfig(mode=mode)
    # Existing fixture omits zero maps that were implicit in its tiny builder tests.
    for name in (
        "static_capacity",
        "reception_capacity",
        "shipping_capacity",
        "emergency_static_capacity_penalty",
        "emergency_reception_capacity_penalty",
    ):
        getattr(data, name).setdefault("W", 0)
    for name in ("supply", "demand_dom", "demand_exp"):
        nodes = {
            "supply": data.origins,
            "demand_dom": data.domestic_customers,
            "demand_exp": data.export_customers,
        }[name]
        for n in nodes:
            for p in data.products:
                for t in data.periods:
                    getattr(data, name).setdefault((n, p, t), 0)
    projected = effective_projection(data, cfg)
    return seal(projected, cfg, {"scenario_id": "baseline"}), cfg


@pytest.mark.parametrize("mode", ["det", "sto"])
def test_lossless_round_trip_and_existing_pyomo_algebra(tmp_path, mode):
    data, cfg = baseline(mode)
    target = tmp_path / "bundle"
    write_bundle(
        target,
        {(215, mode): (data, cfg)},
        {"workbook_h215": {"sha256": "a" * 64, "description": "existing public fixture"}},
    )
    restored, restored_cfg = load_bundle(target, 215, mode)
    assert identity(restored, restored_cfg) == identity(data, cfg)
    old = build_effective_model(data, cfg)
    new = build_effective_model(restored, restored_cfg)
    assert matrix_identity(old.model) == matrix_identity(new.model)


def test_neutral_controls_and_no_cascading_transforms():
    data, cfg = baseline("sto")
    before = copy.deepcopy(data)
    neutral, _ = apply_scenario(data, cfg, ParameterScenario("neutral"))
    assert identity(neutral, cfg) == identity(data, cfg)
    changed, audit = apply_scenario(
        data,
        cfg,
        ParameterScenario(
            "freight-control", {"freight": 2}, justification="Local regression control."
        ),
    )
    assert changed.unmet_demand_penalty == data.unmet_demand_penalty
    assert changed.emergency_static_capacity_penalty == data.emergency_static_capacity_penalty
    assert changed.freight_origin["O"] == 2 * data.freight_origin["O"]
    assert audit["changes"]
    assert data == before
    changed, _ = apply_scenario(
        data,
        cfg,
        ParameterScenario(
            "K-control", {"existing_static": 2}, justification="Local regression control."
        ),
    )
    assert changed.max_expand_capacity == data.max_expand_capacity
    assert changed.reception_capacity == data.reception_capacity
    assert changed.shipping_capacity == data.shipping_capacity


def test_demand_quantity_does_not_change_export_limits_or_penalties():
    data, cfg = baseline("sto")
    changed, _ = apply_scenario(
        data,
        cfg,
        ParameterScenario(
            "demand-control", {"delta_D": 0.5}, justification="Local regression control."
        ),
    )
    assert changed.demand_dom["C", "P", "t"] == data.demand_dom["C", "P", "t"] / 2
    assert all(changed.demand_dom_s[k] == v / 2 for k, v in data.demand_dom_s.items())
    assert changed.demand_exp == data.demand_exp
    assert changed.demand_exp_s == data.demand_exp_s
    assert changed.unmet_demand_penalty == data.unmet_demand_penalty
    assert (
        changed.metadata["effective_baseline"]["input_sha256"]
        != data.metadata["effective_baseline"]["input_sha256"]
    )
    build_effective_model(changed, cfg)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"beta": 0.9},
        {"alpha": 0.5},
        {"fixed_absolute": {"opening_fixed_cost": 1}},
        {"multipliers": {"unknown": 1}},
        {"multipliers": {"freight": float("nan")}},
        {"multipliers": {"delta_D": -1}},
        {"multipliers": {"freight": True}},
    ],
)
def test_unapproved_or_invalid_controls_fail(kwargs):
    with pytest.raises(ValueError):
        ParameterScenario("invalid", **kwargs)


def test_mutation_and_scenario_chaining_fail():
    data, cfg = baseline()
    changed, _ = apply_scenario(data, cfg, ParameterScenario("first"))
    with pytest.raises(ValueError, match="immutable baseline"):
        apply_scenario(changed, cfg, ParameterScenario("second"))
    data.storage_tariff["W", "P"] += 1
    with pytest.raises(ValueError, match="changed after sealing"):
        build_effective_model(data, cfg)


@pytest.mark.parametrize(
    "damage", ["unit", "duplicate", "missing", "distance", "scenario", "provenance", "role"]
)
def test_semantic_corruption_is_detected_even_with_refreshed_file_hash(tmp_path, damage):
    data, cfg = baseline("sto")
    target = tmp_path / "bundle"
    write_bundle(
        target,
        {(215, "sto"): (data, cfg)},
        {"workbook_h215": {"sha256": "a" * 64, "description": "public fixture"}},
    )
    arc_damage = damage in ("distance", "role")
    name = "arcs.csv" if arc_damage else "parameters.csv"
    columns = ARC_COLUMNS if arc_damage else PARAMETER_COLUMNS
    with (target / name).open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if damage == "unit":
        rows[0]["unit"] = "t/day"
    elif damage == "duplicate":
        rows.append(rows[0])
    elif damage == "missing":
        rows = [r for r in rows if not (r["field"] == "supply" and '"O"' in r["key_json"])]
    elif damage == "distance":
        rows[0]["osrm_distance_km"] = ""
    elif damage == "provenance":
        rows[0]["source_id"] = "unidentified_source"
    elif damage == "role":
        rows[0]["destination_role"] = "export"
    else:
        rows = [r for r in rows if r["field"] != "scenario_prob"]
    with (target / name).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    manifest_path = target / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"][name] = sha256(target / name)
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        load_bundle(target, 215, "sto")


def test_daily_conversion_and_bounds_remain_in_existing_builder():
    data, cfg = baseline()
    with pytest.raises(ValueError, match="30 operating days"):
        validate(data, replace(cfg, days_per_period=900))
    assert cfg.operating_days("t") == 30
    from src.logic.mathematical_contract import extensive_form_inputs
    from src.logic.pyomo_bounds import candidate_slack_bounds

    projected, sto_cfg = extensive_form_inputs(data, cfg)
    _, proof = candidate_slack_bounds(projected, sto_cfg)
    changed, _ = apply_scenario(
        data,
        cfg,
        ParameterScenario(
            "shipping-control", {"existing_shipping": 2}, justification="Local regression control."
        ),
    )
    altered, _ = extensive_form_inputs(changed, cfg)
    _, after = candidate_slack_bounds(altered, sto_cfg)
    assert proof["bounds_sha256"] == after["bounds_sha256"]  # fixture has no candidates


def test_sparse_historical_zeros_are_materialized_without_algebra_change():
    data = economic_data()
    data.supply = {}
    cfg = ModelConfig()
    from src.logic.optimization_pyomo import build_model

    original = matrix_identity(build_model(data, cfg).model)
    projected = effective_projection(data, cfg)
    assert projected.supply["O", "P", "t"] == 0
    assert projected.initial_inventory["W", "P"] == 0
    assert matrix_identity(build_model(projected, cfg).model) == original


def test_optional_missing_annotations_are_null_but_model_nan_is_rejected(tmp_path):
    data, cfg = baseline()
    data.metadata["optional_source_annotation"] = float("nan")
    target = tmp_path / "bundle"
    manifest = write_bundle(
        target,
        {(215, "det"): (data, cfg)},
        {"workbook_h215": {"sha256": "a" * 64, "description": "public fixture"}},
    )
    restored, _ = load_bundle(target, 215, "det")
    assert restored.metadata["optional_source_annotation"] is None
    assert manifest["optional_annotation_nulls"]["metadata"] == 1
    data.supply["O", "P", "t"] = float("nan")
    with pytest.raises(ValueError, match="finite nonnegative"):
        validate(data, cfg)


def test_first_difference_exposes_a_single_ulp_without_rounding():
    import math

    from src.logic.effective_baseline import first_difference

    data, cfg = baseline()
    changed = copy.deepcopy(data)
    changed.storage_tariff["W", "P"] = math.nextafter(data.storage_tariff["W", "P"], math.inf)
    difference = first_difference(data, changed, cfg, cfg)
    assert difference["field"] == "storage_tariff"
    assert difference["expected"] != difference["actual"]


def test_non_neutral_controls_cannot_relabel_the_baseline():
    with pytest.raises(ValueError, match="named baseline"):
        ParameterScenario("baseline", {"delta_D": 0.5})


def test_experimental_data_cannot_be_exported_as_a_baseline(tmp_path):
    data, cfg = baseline()
    changed, _ = apply_scenario(
        data,
        cfg,
        ParameterScenario(
            "counterfactual", {"delta_D": 2}, justification="Local regression control."
        ),
    )
    with pytest.raises(ValueError, match="relabeled"):
        write_bundle(tmp_path / "invalid", {(215, "det"): (changed, cfg)}, {})
    with pytest.raises(ValueError, match="Case label"):
        write_bundle(tmp_path / "wrong-mode", {(215, "sto"): (data, cfg)}, {})


def test_zero_distance_round_trips_as_a_real_value(tmp_path):
    data, cfg = baseline()
    data.dist_od["O", "W"] = 0
    data = seal(data, cfg, {"scenario_id": "baseline"})
    target = tmp_path / "zero"
    write_bundle(
        target,
        {(215, "det"): (data, cfg)},
        {"workbook_h215": {"sha256": "a" * 64, "description": "public fixture"}},
    )
    restored, _ = load_bundle(target, 215, "det")
    assert restored.dist_od["O", "W"] == 0
    assert ("O", "W", "P") in restored.routes_od


def test_a_changed_sealed_baseline_is_not_silently_exported(tmp_path):
    data, cfg = baseline()
    data.unmet_demand_penalty["C", "P"] += 1
    with pytest.raises(ValueError, match="Sealed baseline data changed"):
        write_bundle(tmp_path / "changed", {(215, "det"): (data, cfg)}, {})


def test_scenario_layers_do_not_share_mutable_parameter_maps():
    data, cfg = baseline()
    changed, record = apply_scenario(
        data,
        cfg,
        ParameterScenario("independent", {"freight": 2}, justification="Local regression control."),
    )
    changed.storage_tariff["W", "P"] = 123
    assert data.storage_tariff["W", "P"] == 2
    assert all("unit" in item for item in record["changes"])


def test_mutated_specs_are_revalidated_before_application():
    data, cfg = baseline()
    spec = ParameterScenario("invalid-after-construction")
    spec.fixed_absolute["opening_fixed_cost"] = 10
    with pytest.raises(ValueError, match="scientific authorization"):
        apply_scenario(data, cfg, spec)
    with pytest.raises(ValueError, match="explicit scientific justification"):
        ParameterScenario("unjustified", {"delta_D": 2})
