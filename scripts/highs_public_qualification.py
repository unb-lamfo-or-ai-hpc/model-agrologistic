"""Public, generated analytical controls; no private input or scheduler."""

from dataclasses import replace

from src.logic.model_data import ModelData


def public_data(origins=1, periods=1):
    """15 BRL per unit through one existing warehouse, no competing cheap arcs."""
    os = [f"O{i}" for i in range(origins)]
    ts = [f"T{i}" for i in range(periods)]
    amount = 10 if origins == 1 else 0.01
    return ModelData(
        origins=os, warehouses=["W"], existing_warehouses=["W"],
        candidate_warehouses=[], bulk_eligible_warehouses=[],
        customers=["C"], domestic_customers=["C"], export_customers=[],
        products=["P"], periods=ts,
        routes_od={(o, "W", "P") for o in os}, routes_dc={("W", "C", "P")},
        dist_od={(o, "W"): 2 for o in os}, dist_dc={("W", "C"): 3},
        freight_origin={o: 4 for o in os}, freight_warehouse={"W": 2},
        transshipment_cost={"W": 1},
        supply={(o, "P", t): amount for o in os for t in ts},
        demand_dom={("C", "P", t): origins * amount for t in ts},
        storage_tariff={("W", "P"): 2},
        static_capacity={"W": 100}, reception_capacity={"W": 100},
        shipping_capacity={"W": 100},
        unmet_demand_penalty={("C", "P"): 90000},
        emergency_static_capacity_penalty={"W": 45000},
        emergency_reception_capacity_penalty={"W": 45000},
    )


def stochastic(data):
    weights = {"low": 0.25, "middle": 0.5, "high": 0.25}
    scales = {"low": 0.8, "middle": 1, "high": 1.2}
    return replace(
        data, scenarios=list(weights), scenario_prob=weights,
        supply_s={(s, *k): v * scales[s] for s in weights for k, v in data.supply.items()},
        demand_dom_s={(s, *k): v * scales[s] for s in weights
                      for k, v in data.demand_dom.items()},
    )
