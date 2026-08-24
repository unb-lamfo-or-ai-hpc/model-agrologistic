from src.logic.model_data import ModelData, NodeInfo


def test_model_data_can_represent_tiny_instance():
    data = ModelData(
        origins=["O1"],
        warehouses=["W1", "W2"],
        existing_warehouses=["W1"],
        candidate_warehouses=["W2"],
        bulk_eligible_warehouses=["W1"],
        customers=["C1"],
        domestic_customers=["C1"],
        export_customers=[],
        products=["soy"],
        periods=["t1"],
        routes_od={("O1", "W1", "soy"), ("O1", "W2", "soy")},
        routes_dc={("W1", "C1", "soy"), ("W2", "C1", "soy")},
        supply={("O1", "soy", "t1"): 100.0},
        demand_dom={("C1", "soy", "t1"): 100.0},
        dist_od={("O1", "W1"): 100.0, ("O1", "W2"): 150.0},
        dist_dc={("W1", "C1"): 80.0, ("W2", "C1"): 60.0},
        static_capacity={"W1": 120.0},
        reception_capacity={"W1": 100.0},
        shipping_capacity={"W1": 100.0},
        max_candidate_capacity={"W2": 200.0},
        opening_fixed_cost={"W2": 1000.0},
        candidate_capacity_cost={"W2": 10.0},
        node_info={
            "O1": NodeInfo(node_id="O1", node_type="origin", latitude=-15.0, longitude=-47.0),
            "W1": NodeInfo(node_id="W1", node_type="warehouse", latitude=-16.0, longitude=-48.0),
            "W2": NodeInfo(node_id="W2", node_type="warehouse", latitude=-17.0, longitude=-49.0),
            "C1": NodeInfo(node_id="C1", node_type="customer", latitude=-18.0, longitude=-50.0),
        },
    )

    assert data.is_stochastic is False
    assert data.all_nodes == ["O1", "W1", "W2", "C1"]
    assert data.investment_nodes == ["W2", "W1"]


def test_model_data_can_represent_stochastic_instance():
    data = ModelData(
        origins=["O1"],
        warehouses=["W1"],
        existing_warehouses=["W1"],
        candidate_warehouses=[],
        bulk_eligible_warehouses=[],
        customers=["C1"],
        domestic_customers=["C1"],
        export_customers=[],
        products=["corn"],
        periods=["t1"],
        scenarios=["pessimistic", "expected", "optimistic"],
        scenario_prob={
            "pessimistic": 0.25,
            "expected": 0.50,
            "optimistic": 0.25,
        },
        routes_od={("O1", "W1", "corn")},
        routes_dc={("W1", "C1", "corn")},
        supply_s={
            ("pessimistic", "O1", "corn", "t1"): 80.0,
            ("expected", "O1", "corn", "t1"): 100.0,
            ("optimistic", "O1", "corn", "t1"): 120.0,
        },
        demand_dom_s={
            ("pessimistic", "C1", "corn", "t1"): 90.0,
            ("expected", "C1", "corn", "t1"): 100.0,
            ("optimistic", "C1", "corn", "t1"): 110.0,
        },
    )

    assert data.is_stochastic is True
    assert len(data.scenarios) == 3