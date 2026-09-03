import pytest

from src.logic.excel_loader import ExcelLoaderConfig, load_model_data_from_excel
from src.logic.model_config import ModelConfig, SolverConfig
from src.logic.model_data import ModelData
from src.logic.optimization import solve_model
from tests.test_excel_loader import build_tiny_golden_excel
from tests.test_gurobipy_transshipment import require_gurobi_available


def base_direct_data(
    *,
    routes_od=None,
    routes_dc=None,
    routes_oc=None,
    dist_od=None,
    dist_dc=None,
    dist_oc=None,
    supply: float = 100.0,
    demand: float = 100.0,
    storage_tariff: float = 1.0,
) -> ModelData:
    if routes_od is None:
        routes_od = {("O1", "W1", "soy")}
    if routes_dc is None:
        routes_dc = {("W1", "C1", "soy")}
    if routes_oc is None:
        routes_oc = {("O1", "C1", "soy")}
    if dist_od is None:
        dist_od = {("O1", "W1"): 1.0}
    if dist_dc is None:
        dist_dc = {("W1", "C1"): 1.0}
    if dist_oc is None:
        dist_oc = {("O1", "C1"): 1.0}

    return ModelData(
        origins=["O1"],
        warehouses=["W1"],
        existing_warehouses=["W1"],
        candidate_warehouses=[],
        bulk_eligible_warehouses=[],
        customers=["C1"],
        domestic_customers=["C1"],
        export_customers=[],
        products=["soy"],
        periods=["t1"],
        routes_od=routes_od,
        routes_dc=routes_dc,
        routes_dd=set(),
        routes_oc=routes_oc,
        supply={("O1", "soy", "t1"): supply},
        demand_dom={("C1", "soy", "t1"): demand},
        demand_exp={},
        dist_od=dist_od,
        dist_dc=dist_dc,
        dist_dd={},
        dist_oc=dist_oc,
        freight_origin={"O1": 1.0},
        freight_dest={"C1": 1.0},
        freight_warehouse={"W1": 1.0},
        transshipment_cost={"W1": 0.0},
        storage_tariff={("W1", "soy"): storage_tariff},
        static_capacity={"W1": 500.0},
        reception_capacity={"W1": 500.0},
        shipping_capacity={"W1": 500.0},
        unmet_demand_penalty={("C1", "soy"): 1_000_000.0},
        emergency_static_capacity_penalty={"W1": 1_000_000_000.0},
        emergency_reception_capacity_penalty={"W1": 1_000_000_000.0},
    )


def solve_direct_data(
    data: ModelData,
    *,
    enabled: bool = True,
    objective_policy: str = "penalty",
):
    return solve_model(
        data=data,
        model_config=ModelConfig(
            mode="det",
            objective_policy=objective_policy,
            use_direct_origin_customer=enabled,
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


def test_lexicographic_policy_serves_demand_before_minimizing_cost():
    require_gurobi_available()

    data = base_direct_data(
        routes_oc=set(),
        dist_oc={},
        dist_dc={("W1", "C1"): 100.0},
        storage_tariff=0.0,
    )
    data.unmet_demand_penalty[("C1", "soy")] = 0.1

    penalty_result = solve_direct_data(data, enabled=False)
    lexicographic_result = solve_direct_data(
        data,
        enabled=False,
        objective_policy="lexicographic",
    )

    assert penalty_result.metrics["total_unmet_demand"] == pytest.approx(100.0)
    assert lexicographic_result.metrics["total_unmet_demand"] == pytest.approx(0.0)
    assert lexicographic_result.objective_value == pytest.approx(0.0)
    assert lexicographic_result.metadata["objective_policy"] == "lexicographic"
    assert lexicographic_result.metadata["objective_priority_order"] == [
        "emergency_capacity",
        "unmet_demand",
        "economic_cost",
    ]
    assert lexicographic_result.metrics["objective_values"][
        "economic_cost"
    ] > penalty_result.metrics["objective_values"]["economic_cost"]


def route_flow(result, route_type: str, *, customer: str | None = None) -> float:
    return sum(
        record["value"]
        for record in result.flows
        if record.get("route_type") == route_type
        and (customer is None or record.get("customer") == customer)
    )


def test_direct_route_is_used_when_required_by_route_structure():
    require_gurobi_available()

    data = base_direct_data(
        routes_od=set(),
        routes_dc=set(),
        routes_oc={("O1", "C1", "soy")},
        dist_od={},
        dist_dc={},
        dist_oc={("O1", "C1"): 2.0},
    )

    result = solve_direct_data(data)

    assert result.status == "optimal"
    assert route_flow(result, "OC", customer="C1") == pytest.approx(100.0)
    assert result.cost_breakdown["transport_oc"] == pytest.approx(200.0)


def test_direct_route_is_used_when_economically_advantageous():
    require_gurobi_available()

    data = base_direct_data(
        dist_od={("O1", "W1"): 100.0},
        dist_dc={("W1", "C1"): 100.0},
        dist_oc={("O1", "C1"): 1.0},
    )

    result = solve_direct_data(data)

    assert result.status == "optimal"
    assert route_flow(result, "OC", customer="C1") == pytest.approx(100.0)
    assert route_flow(result, "OD") == pytest.approx(0.0)
    assert route_flow(result, "DC", customer="C1") == pytest.approx(0.0)


def test_supply_can_split_between_direct_and_warehouse_paths():
    require_gurobi_available()

    data = base_direct_data()
    data.customers = ["C1", "C2"]
    data.domestic_customers = ["C1", "C2"]
    data.routes_dc = {("W1", "C2", "soy")}
    data.routes_oc = {("O1", "C1", "soy")}
    data.demand_dom = {
        ("C1", "soy", "t1"): 40.0,
        ("C2", "soy", "t1"): 60.0,
    }
    data.dist_dc = {("W1", "C2"): 1.0}
    data.dist_oc = {("O1", "C1"): 1.0}
    data.freight_dest["C2"] = 1.0
    data.unmet_demand_penalty[("C2", "soy")] = 1_000_000.0

    result = solve_direct_data(data)

    assert result.status == "optimal"
    assert route_flow(result, "OC", customer="C1") == pytest.approx(40.0)
    assert route_flow(result, "OD") == pytest.approx(60.0)
    assert route_flow(result, "DC", customer="C2") == pytest.approx(60.0)


def test_export_upper_bound_combines_direct_and_warehouse_flows():
    require_gurobi_available()

    data = base_direct_data(storage_tariff=100.0)
    data.customers = ["E1"]
    data.domestic_customers = []
    data.export_customers = ["E1"]
    data.routes_dc = {("W1", "E1", "soy")}
    data.routes_oc = {("O1", "E1", "soy")}
    data.demand_dom = {}
    data.demand_exp = {("E1", "soy", "t1"): 30.0}
    data.dist_od = {("O1", "W1"): 10.0}
    data.dist_dc = {("W1", "E1"): 1.0}
    data.dist_oc = {("O1", "E1"): 1.0}
    data.freight_dest = {"E1": 1.0}
    data.unmet_demand_penalty = {}

    result = solve_direct_data(data)

    assert result.status == "optimal"
    exported = route_flow(result, "OC", customer="E1") + route_flow(
        result, "DC", customer="E1"
    )
    assert exported == pytest.approx(30.0)


def test_disabled_flag_ignores_declared_direct_routes():
    require_gurobi_available()

    data = base_direct_data(
        dist_od={("O1", "W1"): 1.0},
        dist_dc={("W1", "C1"): 1.0},
        dist_oc={("O1", "C1"): 0.1},
    )

    result = solve_direct_data(data, enabled=False)

    assert result.status == "optimal"
    assert route_flow(result, "OC") == pytest.approx(0.0)
    assert route_flow(result, "OD") == pytest.approx(100.0)
    assert route_flow(result, "DC", customer="C1") == pytest.approx(100.0)
    assert result.cost_breakdown["transport_oc"] == pytest.approx(0.0)


def test_zero_supply_and_demand_do_not_create_direct_flow():
    require_gurobi_available()

    data = base_direct_data(
        routes_od=set(),
        routes_dc=set(),
        supply=0.0,
        demand=0.0,
    )

    result = solve_direct_data(data)

    assert result.status == "optimal"
    assert route_flow(result, "OC") == pytest.approx(0.0)


def test_excel_direct_routes_feed_the_gurobi_model(tmp_path):
    require_gurobi_available()

    workbook = tmp_path / "tiny_direct_origin_customer.xlsx"
    build_tiny_golden_excel(workbook)

    data = load_model_data_from_excel(
        workbook,
        config=ExcelLoaderConfig(
            include_export_routes=False,
            include_direct_origin_customer_routes=True,
        ),
    )

    origin = "Rio Verde - GO"
    customer = "Goiânia - GO"
    product = "Soja"
    period = "2026-01"

    assert (origin, customer, product) in data.routes_oc
    assert (origin, customer) in data.dist_oc

    data.origins = [origin]
    data.customers = [customer]
    data.domestic_customers = [customer]
    data.export_customers = []
    data.products = [product]
    data.periods = [period]
    data.routes_od = set()
    data.routes_dc = set()
    data.routes_dd = set()
    data.routes_oc = {(origin, customer, product)}
    data.supply = {(origin, product, period): 80.0}
    data.demand_dom = {(customer, product, period): 80.0}
    data.demand_exp = {}

    result = solve_direct_data(data)

    expected_transport_cost = (
        80.0 * data.dist_oc[(origin, customer)] * data.freight_origin[origin]
    )

    assert result.status == "optimal"
    assert route_flow(result, "OC", customer=customer) == pytest.approx(80.0)
    assert result.cost_breakdown["transport_oc"] == pytest.approx(
        expected_transport_cost
    )
