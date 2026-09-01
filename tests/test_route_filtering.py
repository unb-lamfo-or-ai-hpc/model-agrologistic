import pytest

from src.logic.experiment_runner import estimate_model_size
from src.logic.model_config import ModelConfig
from src.logic.model_data import ModelData
from src.logic.route_filtering import select_routes


def route_data() -> ModelData:
    warehouses = ["W1", "W2", "W3"]
    return ModelData(
        origins=["O1"],
        warehouses=warehouses,
        existing_warehouses=warehouses,
        candidate_warehouses=[],
        bulk_eligible_warehouses=[],
        customers=["C1"],
        domestic_customers=["C1"],
        export_customers=[],
        products=["soy"],
        periods=["t1", "t2"],
        routes_od={("O1", warehouse, "soy") for warehouse in warehouses},
        routes_dc={(warehouse, "C1", "soy") for warehouse in warehouses},
        routes_dd={
            (source, destination, "soy")
            for source in warehouses
            for destination in warehouses
            if source != destination
        },
        routes_oc={("O1", "C1", "soy")},
        dist_od={("O1", "W1"): 30.0, ("O1", "W2"): 10.0, ("O1", "W3"): 20.0},
        dist_dc={("W1", "C1"): 20.0, ("W2", "C1"): 30.0, ("W3", "C1"): 10.0},
        dist_dd={
            (source, destination): float(index + 1)
            for index, (source, destination) in enumerate(
                (source, destination)
                for source in warehouses
                for destination in warehouses
                if source != destination
            )
        },
        dist_oc={("O1", "C1"): 5.0},
    )


def test_top_k_keeps_nearest_routes_per_connectivity_group():
    data = route_data()
    config = ModelConfig(
        route_filter_strategy="top_k",
        route_top_k=1,
        use_warehouse_transshipment=True,
        use_direct_origin_customer=True,
    )

    routes = select_routes(data, config)

    assert routes.od == {("O1", "W2", "soy")}
    assert routes.dc == {("W2", "C1", "soy"), ("W3", "C1", "soy")}
    assert len(routes.dd) == 3
    assert routes.oc == {("O1", "C1", "soy")}


def test_structural_flags_remove_disabled_route_families():
    routes = select_routes(
        route_data(),
        ModelConfig(
            route_filter_strategy="none",
            use_warehouse_transshipment=False,
            use_direct_origin_customer=False,
        ),
    )

    assert routes.dd == set()
    assert routes.oc == set()


def test_pareto_filter_keeps_at_least_one_route_per_group():
    routes = select_routes(
        route_data(),
        ModelConfig(route_filter_strategy="pareto", pareto_fraction=0.20),
    )

    assert len(routes.od) == 1
    assert len(routes.dc) == 2
    assert len(routes.dd) == 3


def test_model_size_estimate_reflects_route_filtering():
    data = route_data()
    unfiltered = estimate_model_size(data, ModelConfig())
    filtered = estimate_model_size(
        data,
        ModelConfig(route_filter_strategy="top_k", route_top_k=1),
    )

    assert filtered.flow_variables < unfiltered.flow_variables
    assert filtered.routes_od == 1
    assert filtered.routes_dc == 2
    assert filtered.routes_dd == 3


def test_top_k_strategy_requires_a_limit():
    with pytest.raises(ValueError, match="route_top_k is required"):
        ModelConfig(route_filter_strategy="top_k")


def test_filtered_inbound_warehouse_keeps_an_export_exit():
    data = route_data()
    data.customers.append("EXP")
    data.export_customers.append("EXP")
    data.routes_dc.update(
        (warehouse, "EXP", "soy") for warehouse in data.warehouses
    )
    data.dist_dc.update(
        {(warehouse, "EXP"): 100.0 for warehouse in data.warehouses}
    )

    routes = select_routes(
        data,
        ModelConfig(route_filter_strategy="top_k", route_top_k=1),
    )

    assert ("W2", "C1", "soy") in routes.dc
    assert ("W2", "EXP", "soy") in routes.dc

