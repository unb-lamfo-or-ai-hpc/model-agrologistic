"""Public zero-flow model; actual validator, no native solver or private input."""

from src.logic.model_config import ModelConfig
from src.logic.model_data import ModelData
from src.logic.optimization import OptimizationResult
from src.logic.solution_validation import COST_NAMES, validate_solution


def fixture():
    origins, warehouses = [f"O{i}" for i in range(2003)], ["W0", "W1"]
    routes = {(o, w, "P") for o in origins for w in warehouses}
    data = ModelData(
        origins=origins,
        warehouses=warehouses,
        existing_warehouses=warehouses,
        candidate_warehouses=[],
        bulk_eligible_warehouses=[],
        customers=["C"],
        domestic_customers=["C"],
        export_customers=[],
        products=["P"],
        periods=["t"],
        scenarios=["s"],
        scenario_prob={"s": 1.0},
        routes_od=routes,
        dist_od={
            (o, w): 1.01 + (i % 17) * 0.13 + j * 0.09
            for i, o in enumerate(origins)
            for j, w in enumerate(warehouses)
        },
        freight_origin={o: 0.13 + (i % 7) * 0.07 for i, o in enumerate(origins)},
        metadata={"_frozen_routes": {"od": sorted(routes), "dc": [], "dd": [], "oc": []}},
    )
    result = OptimizationResult(
        status="feasible",
        objective_value=0.0,
        cost_breakdown=dict.fromkeys(COST_NAMES, 0.0),
        warehouse_decisions=[
            {
                "warehouse": w,
                "open": 1.0,
                "candidate_capacity": 0.0,
                "expand": 0.0,
                "expansion_capacity": 0.0,
                "bulkify": 0.0,
                "bulk_capacity": 0.0,
            }
            for w in warehouses
        ],
    )
    return data, ModelConfig(mode="sto", objective_policy="lexicographic"), result


def report():
    data, config, result = fixture()
    return validate_solution(data, config, result)
