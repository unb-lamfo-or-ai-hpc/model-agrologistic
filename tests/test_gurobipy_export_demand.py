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


def export_data(
    *,
    supply: float = 100.0,
    domestic_demand: float = 40.0,
    export_upper_bound: float = 60.0,
    storage_tariff: float = 1_000_000.0,
) -> ModelData:
    return ModelData(
        origins=["O1"],
        warehouses=["W1"],
        existing_warehouses=["W1"],
        candidate_warehouses=[],
        bulk_eligible_warehouses=[],
        customers=["C1", "P1"],
        domestic_customers=["C1"],
        export_customers=["P1"],
        products=["soy"],
        periods=["t1"],
        routes_od={
            ("O1", "W1", "soy"),
        },
        routes_dc={
            ("W1", "C1", "soy"),
            ("W1", "P1", "soy"),
        },
        supply={
            ("O1", "soy", "t1"): supply,
        },
        demand_dom={
            ("C1", "soy", "t1"): domestic_demand,
        },
        demand_exp={
            ("P1", "soy", "t1"): export_upper_bound,
        },
        dist_od={
            ("O1", "W1"): 1.0,
        },
        dist_dc={
            ("W1", "C1"): 1.0,
            ("W1", "P1"): 1.0,
        },
        freight_origin={
            "O1": 1.0,
        },
        freight_dest={
            "C1": 1.0,
            "P1": 1.0,
        },
        storage_tariff={
            ("W1", "soy"): storage_tariff,
        },
        static_capacity={
            "W1": 200.0,
        },
        reception_capacity={
            "W1": 200.0,
        },
        shipping_capacity={
            "W1": 200.0,
        },
        unmet_demand_penalty={
            ("C1", "soy"): 1_000_000.0,
        },
        emergency_static_capacity_penalty={
            "W1": 1_000_000.0,
        },
        emergency_reception_capacity_penalty={
            "W1": 1_000_000.0,
        },
    )


def solve_export_data(data: ModelData):
    return solve_model(
        data=data,
        model_config=ModelConfig(
            mode="det",
            candidate_capacity_mode="scalable",
            days_per_period=1.0,
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


def flow_to_customer(result, customer: str) -> float:
    return sum(
        record["value"]
        for record in result.flows
        if record.get("customer") == customer
    )


def ending_inventory(result) -> float:
    return sum(record["value"] for record in result.inventories)


def test_export_upper_bound_absorbs_excess_supply():
    require_gurobi_available()

    result = solve_export_data(
        export_data(
            supply=100.0,
            domestic_demand=40.0,
            export_upper_bound=60.0,
            storage_tariff=1_000_000.0,
        )
    )

    assert result.status == "optimal"

    assert flow_to_customer(result, "C1") == pytest.approx(40.0)
    assert flow_to_customer(result, "P1") == pytest.approx(60.0)
    assert ending_inventory(result) == pytest.approx(0.0)

    export_records = [
        record
        for record in result.flows
        if record.get("customer") == "P1"
    ]

    assert export_records
    assert all(record["customer_type"] == "export" for record in export_records)


def test_export_upper_bound_is_not_exceeded():
    require_gurobi_available()

    result = solve_export_data(
        export_data(
            supply=100.0,
            domestic_demand=0.0,
            export_upper_bound=30.0,
            storage_tariff=1_000_000.0,
        )
    )

    assert result.status == "optimal"

    assert flow_to_customer(result, "P1") == pytest.approx(30.0)
    assert ending_inventory(result) == pytest.approx(70.0)


def test_zero_export_upper_bound_blocks_export_flow():
    require_gurobi_available()

    result = solve_export_data(
        export_data(
            supply=100.0,
            domestic_demand=100.0,
            export_upper_bound=0.0,
            storage_tariff=1_000_000.0,
        )
    )

    assert result.status == "optimal"

    assert flow_to_customer(result, "C1") == pytest.approx(100.0)
    assert flow_to_customer(result, "P1") == pytest.approx(0.0)