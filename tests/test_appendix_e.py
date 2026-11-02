"""Directed original-flow joins and probability accounting; no optimizer or private data."""

import csv
import io

import pytest

from scripts.build_appendix_e import endpoints, joined_flows, sparse_matrix


def exported(rows):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode()


def row(scenario="low", value=10):
    return dict(
        route_type="OD",
        origin="O",
        warehouse="W",
        customer="",
        customer_type="",
        warehouse_from="",
        warehouse_to="",
        product="Soja",
        period="2021-01",
        scenario=scenario,
        value=value,
    )


def test_scenarios_are_weighted_and_distances_are_not_summed():
    flows = list(
        joined_flows(
            exported([row(), row("high", 30)]),
            {"low": 0.25, "high": 0.75},
            {("OD", "O", "W"): 123.5},
        )
    )
    matrix = sparse_matrix(flows)
    assert len(matrix) == 1
    assert matrix[0]["expected_horizon_tonnes"] == 25
    assert matrix[0]["osrm_km"] == 123.5


def test_reverse_direction_does_not_supply_a_missing_distance():
    with pytest.raises(ValueError, match="exact directed OSRM"):
        list(joined_flows(exported([row()]), {"low": 1}, {("OD", "W", "O"): 100}))


def test_duplicate_flow_coordinate_is_rejected():
    with pytest.raises(ValueError, match="Duplicate original flow"):
        list(joined_flows(exported([row(), row()]), {"low": 1}, {("OD", "O", "W"): 100}))


def test_direct_customer_family_uses_origin_and_customer():
    direct = dict(row(), route_type="OC", customer="Port", customer_type="export")
    assert endpoints(direct) == ("O", "Port")


def test_unknown_scenario_is_not_silently_reweighted():
    with pytest.raises(ValueError, match="Unknown scenario"):
        list(joined_flows(exported([row()]), {"other": 1}, {("OD", "O", "W"): 100}))


def test_coincident_destination_roles_remain_distinct():
    flows = [
        dict(
            route_type="DC",
            origin="W",
            destination="City",
            destination_role=role,
            product="Soja",
            expected_tonnes=value,
            osrm_km=50,
        )
        for role, value in [("domestic", 10), ("export", 20)]
    ]
    assert len(sparse_matrix(flows)) == 2


def test_star_port_and_bulk_diamond_are_distinct_vectors():
    from src.visualization.geography import STYLES
    from src.visualization.render import marker_points

    assert STYLES["export"][1] == "star"
    assert STYLES["bulkified"][1] == "diamond"
    marker = dict(xy=(0, 0), size=5)
    assert len(marker_points(dict(marker, symbol="star"))) == 10
    assert len(marker_points(dict(marker, symbol="diamond"))) == 4
