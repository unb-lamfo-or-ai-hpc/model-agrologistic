from __future__ import annotations

import pandas as pd
import pytest

from src.logic.warehouse_population import (
    LATITUDE,
    LONGITUDE,
    MAX_STATIC_CAPACITY,
    OPENING_COST,
    RECEPTION_CAPACITY,
    SHIPPING_CAPACITY,
    STATE,
    STATIC_CAPACITY,
    STATUS,
    WAREHOUSE_ID,
    WAREHOUSE_TYPE,
    build_population_order,
)


def _registry() -> pd.DataFrame:
    rows = []
    for index in range(2):
        rows.append(_row(f"existing-{index}", "Existente", index + 10.0))
    for index in range(10):
        rows.append(
            _row(
                f"candidate-{index}",
                "Candidato",
                index + 1.0,
                state="GO" if index % 2 else "MT",
                warehouse_type="Silo" if index % 3 else "Graneleiro",
            )
        )
    return pd.DataFrame(rows)


def _row(
    warehouse: str,
    status: str,
    static_capacity: float,
    *,
    state: str = "DF",
    warehouse_type: str = "Convencional",
) -> dict[str, object]:
    return {
        WAREHOUSE_ID: warehouse,
        STATUS: status,
        STATE: state,
        WAREHOUSE_TYPE: warehouse_type,
        LATITUDE: -15.0,
        LONGITUDE: -47.0,
        STATIC_CAPACITY: static_capacity,
        RECEPTION_CAPACITY: 10.0,
        SHIPPING_CAPACITY: 10.0,
        MAX_STATIC_CAPACITY: 0.0,
        OPENING_COST: 0.0,
    }


def test_population_levels_are_nested_and_reproducible():
    first_order, first_levels, audit = build_population_order(
        _registry(),
        target_populations=(4, 7, 12),
        selection_seed="fixture-seed",
    )
    second_order, second_levels, _ = build_population_order(
        _registry().sample(frac=1.0, random_state=8),
        target_populations=(4, 7, 12),
        selection_seed="fixture-seed",
    )

    first_candidates = first_order.loc[
        first_order["population_role"] == "candidate",
        [WAREHOUSE_ID, "candidate_rank", "first_population_total"],
    ].sort_values(WAREHOUSE_ID)
    second_candidates = second_order.loc[
        second_order["population_role"] == "candidate",
        [WAREHOUSE_ID, "candidate_rank", "first_population_total"],
    ].sort_values(WAREHOUSE_ID)

    pd.testing.assert_frame_equal(
        first_candidates.reset_index(drop=True),
        second_candidates.reset_index(drop=True),
    )
    pd.testing.assert_frame_equal(first_levels, second_levels)
    assert first_levels["total_warehouses"].tolist() == [4, 7, 12]
    assert audit["solver_translation_required"] is True


def test_nonpositive_candidate_capacity_is_excluded():
    registry = _registry()
    registry.loc[registry[WAREHOUSE_ID] == "candidate-9", STATIC_CAPACITY] = 0.0

    order, levels, audit = build_population_order(
        registry,
        target_populations=(4, 11),
    )

    excluded = order.loc[order[WAREHOUSE_ID] == "candidate-9"].iloc[0]
    assert not excluded["population_eligible"]
    assert excluded["exclusion_reason"] == "nonpositive_static_capacity"
    assert pd.isna(excluded["candidate_rank"])
    assert levels["total_warehouses"].tolist() == [4, 11]
    assert audit["excluded_candidate_count"] == 1


def test_canonical_candidates_anchor_the_smallest_population():
    order, levels, audit = build_population_order(
        _registry(),
        target_populations=(4, 7, 12),
        anchor_candidate_ids=("candidate-8", "candidate-9"),
        anchor_existing_ids=("existing-0", "existing-1"),
    )

    first_level = set(
        order.loc[
            order["first_population_total"] == 4,
            WAREHOUSE_ID,
        ]
    )
    assert first_level == {
        "existing-0",
        "existing-1",
        "candidate-8",
        "candidate-9",
    }
    assert levels["total_warehouses"].tolist() == [4, 7, 12]
    assert audit["canonical_anchor_candidate_count"] == 2
    assert audit["canonical_existing_warehouse_count"] == 2


def test_population_rejects_a_changed_canonical_existing_population():
    with pytest.raises(ValueError, match="does not preserve the canonical existing"):
        build_population_order(
            _registry(),
            target_populations=(4, 7, 12),
            anchor_candidate_ids=("candidate-8", "candidate-9"),
            anchor_existing_ids=("existing-0", "different-existing"),
        )


def test_population_rejects_duplicate_identifiers():
    registry = _registry()
    registry.loc[1, WAREHOUSE_ID] = registry.loc[0, WAREHOUSE_ID]

    with pytest.raises(ValueError, match="Duplicate warehouse identifiers"):
        build_population_order(registry, target_populations=(4,))

