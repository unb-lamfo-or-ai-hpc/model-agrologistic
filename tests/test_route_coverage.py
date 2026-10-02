from src.logic.model_config import ModelConfig
from src.logic.model_data import ModelData
from src.logic.route_coverage import build_route_coverage_audit


def coverage_data() -> ModelData:
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
        routes_oc={
            ("O1", "C1", "soy"),
            ("O1", "C2", "soy"),
            ("O1", "EXP", "soy"),
        },
        dist_od={("O1", "W1"): 1.0},
        dist_dc={
            ("W1", "C1"): 1.0,
            ("W1", "C2"): 2.0,
            ("W1", "EXP"): 3.0,
        },
        dist_oc={
            ("O1", "C1"): 1.0,
            ("O1", "C2"): 2.0,
            ("O1", "EXP"): 3.0,
        },
        supply={("O1", "soy", "t1"): 3.0},
        demand_dom={
            ("C1", "soy", "t1"): 1.0,
            ("C2", "soy", "t1"): 1.0,
        },
        demand_exp={("EXP", "soy", "t1"): 10.0},
    )


def test_historical_filter_reports_customer_coverage_loss():
    audit = build_route_coverage_audit(
        coverage_data(),
        ModelConfig(
            route_filter_strategy="thesis_pareto",
            pareto_fraction=0.20,
            use_warehouse_transshipment=False,
            use_direct_origin_customer=False,
        ),
    )

    assert audit["selected_route_counts"]["DC"] == 1
    assert audit["summary"]["all_active_domestic_customers_reachable"] is False
    assert audit["summary"]["all_active_export_customers_reachable"] is False
    assert audit["summary"]["unreachable_domestic_customer_product_pairs"] == 1
    assert audit["summary"]["unreachable_export_customer_product_pairs"] == 1


def test_unfiltered_control_preserves_all_customer_paths():
    audit = build_route_coverage_audit(
        coverage_data(),
        ModelConfig(
            route_filter_strategy="none",
            use_warehouse_transshipment=False,
            use_direct_origin_customer=False,
        ),
    )

    assert audit["summary"]["all_active_domestic_customers_reachable"] is True
    assert audit["summary"]["all_active_export_customers_reachable"] is True
    assert audit["summary"]["supply_origin_product_pairs_without_export_path"] == 0
