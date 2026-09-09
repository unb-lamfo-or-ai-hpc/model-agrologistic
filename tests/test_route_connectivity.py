from src.logic.model_config import ModelConfig
from src.logic.model_data import ModelData
from src.logic.route_connectivity import build_route_connectivity_diagnostics


def disconnected_customer_data() -> ModelData:
    return ModelData(
        origins=["O1"],
        warehouses=["W1"],
        existing_warehouses=["W1"],
        candidate_warehouses=[],
        bulk_eligible_warehouses=[],
        customers=["C1", "C2", "EXP"],
        domestic_customers=["C1", "C2"],
        export_customers=["EXP"],
        products=["soy"],
        periods=["t1"],
        routes_od={("O1", "W1", "soy")},
        routes_dc={
            ("W1", "C1", "soy"),
            ("W1", "C2", "soy"),
            ("W1", "EXP", "soy"),
        },
        dist_od={("O1", "W1"): 1.0},
        dist_dc={
            ("W1", "C1"): 1.0,
            ("W1", "C2"): 2.0,
            ("W1", "EXP"): 3.0,
        },
        supply={("O1", "soy", "t1"): 3.0},
        demand_dom={
            ("C1", "soy", "t1"): 1.0,
            ("C2", "soy", "t1"): 1.0,
        },
        demand_exp={("EXP", "soy", "t1"): 10.0},
    )


def thesis_config(*, fraction: float = 0.20) -> ModelConfig:
    return ModelConfig(
        route_filter_strategy="thesis_pareto",
        pareto_fraction=fraction,
        use_warehouse_transshipment=False,
        use_direct_origin_customer=False,
    )


def test_route_decisions_report_historical_rank_and_cutoff():
    diagnostics = build_route_connectivity_diagnostics(
        disconnected_customer_data(),
        thesis_config(),
    )
    dc_records = {
        record["destination"]: record
        for record in diagnostics["route_filter_decisions"]
        if record["route_type"] == "DC"
    }

    assert dc_records["C1"]["rank_within_group"] == 1
    assert dc_records["C1"]["selection_cutoff_count"] == 1
    assert dc_records["C1"]["selected"] is True
    assert dc_records["C2"]["rank_within_group"] == 2
    assert dc_records["C2"]["selected"] is False
    assert dc_records["EXP"]["rank_within_group"] == 3
    assert dc_records["EXP"]["selection_reason"] == "outside_group_cutoff"


def test_diagnostics_find_one_real_route_for_each_missing_customer():
    diagnostics = build_route_connectivity_diagnostics(
        disconnected_customer_data(),
        thesis_config(),
    )
    gaps = {
        record["customer"]: record
        for record in diagnostics["connectivity_gaps"]
    }

    assert set(gaps) == {"C2", "EXP"}
    for gap in gaps.values():
        assert gap["gap_cause"] == "no_selected_inbound_route"
        assert gap["repair_status"] == "candidate_path_found"
        assert gap["minimal_added_route_count"] == 1

    added = {
        (record["customer"], record["route_type"], record["destination"])
        for record in diagnostics["connectivity_repair_candidates"]
        if record["is_added_route"]
    }
    assert added == {("C2", "DC", "C2"), ("EXP", "DC", "EXP")}


def upstream_disconnection_data() -> ModelData:
    return ModelData(
        origins=["O1"],
        warehouses=["W1", "W2"],
        existing_warehouses=["W1", "W2"],
        candidate_warehouses=[],
        bulk_eligible_warehouses=[],
        customers=["C1", "EXP"],
        domestic_customers=["C1"],
        export_customers=["EXP"],
        products=["soy"],
        periods=["t1"],
        routes_od={
            ("O1", "W1", "soy"),
            ("O1", "W2", "soy"),
        },
        routes_dc={
            ("W1", "C1", "soy"),
            ("W1", "EXP", "soy"),
            ("W2", "C1", "soy"),
            ("W2", "EXP", "soy"),
        },
        dist_od={("O1", "W1"): 1.0, ("O1", "W2"): 10.0},
        dist_dc={
            ("W1", "C1"): 1.0,
            ("W1", "EXP"): 100.0,
            ("W2", "C1"): 100.0,
            ("W2", "EXP"): 1.0,
        },
        supply={("O1", "soy", "t1"): 1.0},
        demand_dom={("C1", "soy", "t1"): 1.0},
        demand_exp={("EXP", "soy", "t1"): 1.0},
    )


def test_repair_prefers_shorter_added_route_for_upstream_disconnection():
    diagnostics = build_route_connectivity_diagnostics(
        upstream_disconnection_data(),
        thesis_config(fraction=0.50),
    )
    assert len(diagnostics["connectivity_gaps"]) == 1
    gap = diagnostics["connectivity_gaps"][0]

    assert gap["customer"] == "EXP"
    assert gap["gap_cause"] == "selected_inbound_disconnected_upstream"
    assert gap["minimal_added_route_count"] == 1
    assert gap["added_distance_km"] == 10.0

    path = diagnostics["connectivity_repair_candidates"]
    assert [(record["route_type"], record["is_added_route"]) for record in path] == [
        ("OD", True),
        ("DC", False),
    ]

