"""Strong directed connectivity is distinct from customer reachability."""

import json
from dataclasses import replace

import pytest

from src.logic.interhub_connectivity import (
    ARTIFACTS,
    build_interhub_audit,
    components,
    repair_interhub,
    write_interhub_audit,
)
from src.logic.mathematical_contract import prepare_model_data
from src.logic.model_config import ModelConfig
from src.logic.model_data import ModelData
from src.logic.route_filtering import SelectedRoutes, route_policy_signature, select_routes


def data_fixture():
    nodes = ["A", "B", "C", "D", "E", "F"]
    return ModelData(
        origins=[], warehouses=nodes, existing_warehouses=nodes, candidate_warehouses=[],
        bulk_eligible_warehouses=[], customers=[], domestic_customers=[], export_customers=[],
        products=["soy", "corn"], periods=["t"], scenarios=[f"s{i}" for i in range(9)],
        routes_dd={(a, b, p) for a in nodes for b in nodes for p in ("soy", "corn") if a != b},
        dist_dd={(a, b): (1.0 if (a, b) in {("A", "B"), ("B", "A"), ("C", "D"),
                                          ("D", "C"), ("E", "F"), ("F", "E")} else 10.0)
                 for a in nodes for b in nodes if a != b},
    )


def config_fixture():
    return ModelConfig(mode="sto", route_filter_strategy="connectivity_preserving_pareto",
                       pareto_fraction=0.2, interhub_strong_connectivity=True)


def test_repair_preserves_baseline_and_other_arc_families(tmp_path):
    data, config = data_fixture(), config_fixture()
    old = replace(config, interhub_strong_connectivity=False)
    baseline = select_routes(data, replace(old, route_filter_strategy="thesis_pareto"))
    before, final = select_routes(data, old), select_routes(data, config)
    assert baseline.dd <= final.dd <= data.routes_dd
    assert before.od == final.od and before.dc == final.dc and before.oc == final.oc
    assert final.repair_dd == final.dd - baseline.dd
    audit = build_interhub_audit(data, baseline, before, final, 0.2)
    assert all(r["strongly_connected"] for r in audit["products"])
    assert all(r["final_fraction"] > 0.2 for r in audit["products"])
    assert all(r["unreachable_other_hubs"] == 0 for r in audit["path_summary"])
    assert any(r["maximum_minimum_hops"] > 1 for r in audit["path_summary"])
    write_interhub_audit(audit, tmp_path)
    assert all((tmp_path / name).is_file() for name in ARTIFACTS)
    assert json.loads((tmp_path / ARTIFACTS[0]).read_text())["status"] == "accepted"


def test_weakly_connected_graph_cannot_be_repaired():
    data = data_fixture()
    data.routes_dd = {("A", "B", "soy"), ("B", "C", "soy")}
    with pytest.raises(ValueError, match="not strongly connected"):
        repair_interhub(data, SelectedRoutes(set(), set(), set(), set()))


@pytest.mark.parametrize("distance", [-0.1, float("nan"), float("inf")])
def test_invalid_distance_fails_closed(distance):
    data = data_fixture()
    data.dist_dd["A", "B"] = distance
    with pytest.raises(ValueError, match="Invalid interhub distance"):
        select_routes(data, config_fixture())


def test_existing_campaign_signature_is_unchanged():
    assert "interhub_strong_connectivity" not in route_policy_signature(ModelConfig())
    for mode, scenarios in (("det", 9), ("sto", 3)):
        data = data_fixture()
        data.scenarios = data.scenarios[:scenarios]
        with pytest.raises(ValueError, match="nine-scenario"):
            select_routes(data, replace(config_fixture(), mode=mode))


def test_freeze_is_idempotent_and_retains_audit():
    data, config = data_fixture(), config_fixture()
    frozen = prepare_model_data(data, config)
    assert prepare_model_data(frozen, config) is frozen
    assert frozen.metadata["interhub_connectivity"]["status"] == "accepted"
    assert select_routes(frozen, config) == select_routes(data, config)
    assert "_frozen_routes" not in data.metadata


def test_direction_is_preserved_and_components_include_isolates():
    assert components({"A", "B", "C"}, {("A", "B")}) == [["A"], ["B"], ["C"]]
    data, config = data_fixture(), config_fixture()
    expected = select_routes(data, config)
    data.warehouses.reverse()
    data.products.reverse()
    assert select_routes(data, config) == expected
