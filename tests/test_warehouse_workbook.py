from __future__ import annotations

import json
from pathlib import Path

import openpyxl
import pandas as pd

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
from src.logic.warehouse_workbook import build_population_workbooks


def test_population_workbooks_preserve_anchor_and_translate_new_candidates(
    tmp_path: Path,
):
    source = pd.DataFrame(
        [
            _warehouse("existing", "Existente", 100.0),
            _warehouse("anchor", "Candidato", 50.0),
            _warehouse("new-1", "Candidato", 70.0),
            _warehouse("new-2", "Candidato", 90.0),
        ]
    )
    anchor = source.iloc[:2].copy()
    anchor.loc[anchor[WAREHOUSE_ID] == "anchor", STATIC_CAPACITY] = 0.0
    anchor.loc[anchor[WAREHOUSE_ID] == "anchor", RECEPTION_CAPACITY] = 0.0
    anchor.loc[anchor[WAREHOUSE_ID] == "anchor", SHIPPING_CAPACITY] = 0.0
    anchor.loc[anchor[WAREHOUSE_ID] == "anchor", MAX_STATIC_CAPACITY] = 50.0
    source_path = tmp_path / "source.xlsx"
    anchor_path = tmp_path / "anchor.xlsx"
    source.to_excel(source_path, sheet_name="Sheet1", index=False)
    with pd.ExcelWriter(anchor_path, engine="openpyxl") as writer:
        anchor.to_excel(writer, sheet_name="Warehouses", index=False)
        pd.DataFrame({"value": ["preserved"]}).to_excel(
            writer,
            sheet_name="Other",
            index=False,
        )

    order, _, _ = build_population_order(
        source,
        target_populations=(2, 4),
        anchor_candidate_ids=("anchor",),
        anchor_existing_ids=("existing",),
    )
    order_path = tmp_path / "population_order.csv"
    order.to_csv(order_path, index=False)

    artifacts = build_population_workbooks(
        source_path,
        anchor_path,
        order_path,
        tmp_path / "output",
    )

    assert len(artifacts.workbooks) == 2
    first = pd.read_excel(artifacts.workbooks[0], sheet_name="Warehouses")
    expanded = pd.read_excel(artifacts.workbooks[1], sheet_name="Warehouses")
    assert first[WAREHOUSE_ID].tolist() == ["existing", "anchor"]
    assert set(expanded[WAREHOUSE_ID]) == {"existing", "anchor", "new-1", "new-2"}
    new_rows = expanded.loc[expanded[WAREHOUSE_ID].str.startswith("new-")]
    assert new_rows[STATIC_CAPACITY].eq(0.0).all()
    assert new_rows[RECEPTION_CAPACITY].eq(0.0).all()
    assert new_rows[SHIPPING_CAPACITY].eq(0.0).all()
    assert set(new_rows[MAX_STATIC_CAPACITY]) == {70.0, 90.0}
    assert openpyxl.load_workbook(artifacts.workbooks[1])["Other"]["A2"].value == (
        "preserved"
    )
    manifest = json.loads(artifacts.manifest_json.read_text(encoding="utf-8"))
    assert manifest["distance_status"] == "pending_osrm_materialization"
    assert all(
        item["candidate_activation_contract_valid"]
        for item in manifest["populations"]
    )


def _warehouse(warehouse: str, status: str, capacity: float) -> dict[str, object]:
    return {
        WAREHOUSE_ID: warehouse,
        STATUS: status,
        "Município": "City",
        STATE: "DF",
        LATITUDE: -15.0,
        LONGITUDE: -47.0,
        "Armazenador": "Holder",
        WAREHOUSE_TYPE: "Silo",
        STATIC_CAPACITY: capacity,
        RECEPTION_CAPACITY: 10.0,
        SHIPPING_CAPACITY: 11.0,
        MAX_STATIC_CAPACITY: 0.0,
        OPENING_COST: 0.0,
        "Custo_Fixo_Abertura_Modelo ($)": 0.0,
        "Custo_Capacidade_Candidata_Modelo ($/t)": None,
        "Permite_Expansao": "NAO",
        "Cap_Expansao_Maxima_Modelo (t)": None,
        "Custo_Expansao_Modelo ($/t)": None,
        "Permite_Granelizacao": "NAO",
        "Custo_Granelizacao_Modelo ($/t)": None,
        "Fonte_Parametro": "Fixture",
        "Observacao": "Fixture",
        "Alteracao_Excel_Modelo": "Fixture",
    }

