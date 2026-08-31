import pytest

from src.logic.model_config import ModelConfig, SolverConfig
from src.logic.model_data import ModelData
from src.logic.optimization import configure_gurobi_wls_license, solve_model


def require_gurobi_available() -> None:
    gp = pytest.importorskip("gurobipy")

    configure_gurobi_wls_license(SolverConfig())

    try:
        env = gp.Env(empty=True)
        env.setParam("OutputFlag", 0)
        env.start()
        env.dispose()
    except gp.GurobiError as exc:
        pytest.skip(f"Gurobi is installed, but no usable license is available: {exc}")


def base_transshipment_data(
    *,
    routes_dc=None,
    routes_dd=None,
    dist_dc=None,
    dist_dd=None,
    supply: float = 100.0,
    demand: float = 100.0,
    w1_reception: float = 200.0,
    w1_shipping: float = 200.0,
    w2_reception: float = 200.0,
    w2_shipping: float = 200.0,
    storage_tariff: float = 1.0,
    unmet_penalty: float = 1_000_000.0,
    emergency_reception_penalty: float = 1_000_000_000.0,
) -> ModelData:
    if routes_dc is None:
        routes_dc = {
            ("W1", "C1", "soy"),
        }

    if routes_dd is None:
        routes_dd = set()

    if dist_dc is None:
        dist_dc = {
            ("W1", "C1"): 1.0,
        }

    if dist_dd is None:
        dist_dd = {}

    return ModelData(
        origins=["O1"],
        warehouses=["W1", "W2"],
        existing_warehouses=["W1", "W2"],
        candidate_warehouses=[],
        bulk_eligible_warehouses=[],
        customers=["C1"],
        domestic_customers=["C1"],
        export_customers=[],
        products=["soy"],
        periods=["t1"],
        routes_od={
            ("O1", "W1", "soy"),
        },
        routes_dc=routes_dc,
        routes_dd=routes_dd,
        routes_oc=set(),
        supply={
            ("O1", "soy", "t1"): supply,
        },
        demand_dom={
            ("C1", "soy", "t1"): demand,
        },
        demand_exp={},
        dist_od={
            ("O1", "W1"): 1.0,
        },
        dist_dc=dist_dc,
        dist_dd=dist_dd,
        dist_oc={},
        freight_origin={
            "O1": 1.0,
        },
        freight_dest={
            "C1": 1.0,
            "W1": 1.0,
            "W2": 1.0,
        },
        transshipment_cost={
            "W1": 0.0,
            "W2": 0.0,
        },
        storage_tariff={
            ("W1", "soy"): storage_tariff,
            ("W2", "soy"): storage_tariff,
        },
        static_capacity={
            "W1": 500.0,
            "W2": 500.0,
        },
        reception_capacity={
            "W1": w1_reception,
            "W2": w2_reception,
        },
        shipping_capacity={
            "W1": w1_shipping,
            "W2": w2_shipping,
        },
        unmet_demand_penalty={
            ("C1", "soy"): unmet_penalty,
        },
        emergency_static_capacity_penalty={
            "W1": 1_000_000_000.0,
            "W2": 1_000_000_000.0,
        },
        emergency_reception_capacity_penalty={
            "W1": emergency_reception_penalty,
            "W2": emergency_reception_penalty,
        },
    )


def solve_transshipment_data(data: ModelData):
    return solve_model(
        data=data,
        model_config=ModelConfig(
            mode="det",
            candidate_capacity_mode="scalable",
            days_per_period=1.0,
            allow_unmet_domestic_demand=True,
            allow_emergency_static_capacity=True,
            allow_emergency_reception_capacity=True,
        ),
        solver_config=SolverConfig(
            backend="gurobipy",
            solver_name="gurobi",
            mip_gap=0.0,
            time_limit=60,
            threads=1,
            tee=False,
        ),
    )


def dd_flow(result, warehouse_from: str, warehouse_to: str) -> float:
    return sum(
        record["value"]
        for record in result.flows
        if record.get("route_type") == "DD"
        and record.get("warehouse_from") == warehouse_from
        and record.get("warehouse_to") == warehouse_to
    )


def customer_flow(result, customer: str) -> float:
    return sum(
        record["value"]
        for record in result.flows
        if record.get("route_type") == "DC"
        and record.get("customer") == customer
    )


def inventory_at(result, warehouse: str) -> float:
    return sum(
        record["value"]
        for record in result.inventories
        if record.get("warehouse") == warehouse
    )


def test_no_transshipment_routes_preserves_previous_behavior():
    require_gurobi_available()

    data = base_transshipment_data(
        routes_dc={
            ("W1", "C1", "soy"),
        },
        routes_dd=set(),
        dist_dc={
            ("W1", "C1"): 1.0,
        },
        dist_dd={},
    )

    result = solve_transshipment_data(data)

    assert result.status == "optimal"
    assert customer_flow(result, "C1") == pytest.approx(100.0)
    assert dd_flow(result, "W1", "W2") == pytest.approx(0.0)

    assert all(record.get("route_type") != "DD" for record in result.flows)


def test_transshipment_is_used_when_required_by_route_structure():
    require_gurobi_available()

    data = base_transshipment_data(
        routes_dc={
            ("W2", "C1", "soy"),
        },
        routes_dd={
            ("W1", "W2", "soy"),
        },
        dist_dc={
            ("W2", "C1"): 1.0,
        },
        dist_dd={
            ("W1", "W2"): 1.0,
        },
    )

    result = solve_transshipment_data(data)

    assert result.status == "optimal"

    assert dd_flow(result, "W1", "W2") == pytest.approx(100.0)
    assert customer_flow(result, "C1") == pytest.approx(100.0)
    assert inventory_at(result, "W1") == pytest.approx(0.0)
    assert inventory_at(result, "W2") == pytest.approx(0.0)


def test_transshipment_is_used_when_economically_advantageous():
    require_gurobi_available()

    data = base_transshipment_data(
        routes_dc={
            ("W1", "C1", "soy"),
            ("W2", "C1", "soy"),
        },
        routes_dd={
            ("W1", "W2", "soy"),
        },
        dist_dc={
            ("W1", "C1"): 1000.0,
            ("W2", "C1"): 1.0,
        },
        dist_dd={
            ("W1", "W2"): 1.0,
        },
    )

    result = solve_transshipment_data(data)

    assert result.status == "optimal"

    assert dd_flow(result, "W1", "W2") == pytest.approx(100.0)
    assert customer_flow(result, "C1") == pytest.approx(100.0)


def test_transshipment_respects_receiving_warehouse_reception_capacity():
    require_gurobi_available()

    data = base_transshipment_data(
        routes_dc={
            ("W2", "C1", "soy"),
        },
        routes_dd={
            ("W1", "W2", "soy"),
        },
        dist_dc={
            ("W2", "C1"): 1.0,
        },
        dist_dd={
            ("W1", "W2"): 1.0,
        },
        supply=100.0,
        demand=100.0,
        w2_reception=40.0,
        w2_shipping=200.0,
        storage_tariff=1.0,
        unmet_penalty=1_000.0,
        emergency_reception_penalty=1_000_000_000.0,
    )

    result = solve_transshipment_data(data)

    assert result.status == "optimal"

    assert dd_flow(result, "W1", "W2") <= 40.0 + 1e-6
    assert dd_flow(result, "W1", "W2") == pytest.approx(40.0)
    assert customer_flow(result, "C1") == pytest.approx(40.0)
    assert inventory_at(result, "W1") == pytest.approx(60.0)


def test_transshipment_respects_sending_warehouse_shipping_capacity():
    require_gurobi_available()

    data = base_transshipment_data(
        routes_dc={
            ("W2", "C1", "soy"),
        },
        routes_dd={
            ("W1", "W2", "soy"),
        },
        dist_dc={
            ("W2", "C1"): 1.0,
        },
        dist_dd={
            ("W1", "W2"): 1.0,
        },
        supply=100.0,
        demand=100.0,
        w1_shipping=30.0,
        w2_reception=200.0,
        storage_tariff=1.0,
        unmet_penalty=1_000.0,
    )

    result = solve_transshipment_data(data)

    assert result.status == "optimal"

    assert dd_flow(result, "W1", "W2") <= 30.0 + 1e-6
    assert dd_flow(result, "W1", "W2") == pytest.approx(30.0)
    assert customer_flow(result, "C1") == pytest.approx(30.0)
    assert inventory_at(result, "W1") == pytest.approx(70.0)
