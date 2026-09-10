from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.logic.osrm import OSRMMatrixResult
from src.logic.policy_osrm import materialize_policy_osrm_workbook


class _FakeOSRMClient:
    base_url = "http://osrm.test"
    profile = "driving"

    def get_distance_matrix_detailed(self, origins, destinations):
        row_count = len(origins)
        column_count = len(destinations)
        return OSRMMatrixResult(
            distances_m=[
                [
                    float((row + 1) * (column + 1) * 1_000)
                    for column in range(column_count)
                ]
                for row in range(row_count)
            ],
            durations_s=[[60.0] * column_count for _ in range(row_count)],
            sources=[["osrm"] * column_count for _ in range(row_count)],
            fallback_reasons=[[None] * column_count for _ in range(row_count)],
            request_count=1,
            data_versions=("fixture",),
        )


def test_policy_osrm_materialization_preserves_workbook_and_audits_routes(
    tmp_path: Path,
):
    workbook = tmp_path / "policy.xlsx"
    with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
        pd.DataFrame(
            {
                "Cidade": ["Origin"],
                "Latitude": [-15.0],
                "Longitude": [-47.0],
            }
        ).to_excel(writer, sheet_name="Oferta", index=False)
        pd.DataFrame(
            {
                "Cidade": ["Customer"],
                "Tipo_Demanda": ["DOMESTICA"],
                "Latitude": [-16.0],
                "Longitude": [-48.0],
            }
        ).to_excel(writer, sheet_name="Demanda", index=False)
        pd.DataFrame(
            {
                "CDA": ["W1", "W2"],
                "Latitude": [-14.0, -13.0],
                "Longitude": [-46.0, -45.0],
            }
        ).to_excel(writer, sheet_name="Warehouses", index=False)
        pd.DataFrame({"value": ["preserved"]}).to_excel(
            writer,
            sheet_name="Other",
            index=False,
        )

    artifacts = materialize_policy_osrm_workbook(
        workbook,
        tmp_path / "output",
        _FakeOSRMClient(),
        dataset_id="fixture-dataset",
    )

    sheets = pd.read_excel(artifacts.workbook, sheet_name=None)
    assert sheets["Other"].iloc[0, 0] == "preserved"
    assert sheets["Distancias"]["Tipo_Arco"].value_counts().to_dict() == {
        "OD": 2,
        "DC": 2,
        "DD": 2,
        "OC": 1,
    }
    audit = json.loads(artifacts.audit_json.read_text(encoding="utf-8"))
    assert audit["distance_status"] == "osrm_authoritative"
    assert audit["distance_provenance"]["fallback_count"] == 0
