"""Materialize OSRM-authoritative distances in policy population workbooks."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from src.logic.artur_adapter import build_osrm_distance_table
from src.logic.osrm import OSRMClient


@dataclass(frozen=True, slots=True)
class PolicyOSRMArtifacts:
    """Paths created by one policy OSRM materialization."""

    workbook: Path
    audit_json: Path


def materialize_policy_osrm_workbook(
    input_workbook: Path,
    output_dir: Path,
    client: OSRMClient,
    *,
    dataset_id: str,
    overwrite: bool = False,
) -> PolicyOSRMArtifacts:
    """Add a complete audited OSRM matrix to one bounded population workbook."""

    input_workbook = Path(input_workbook)
    output_dir = Path(output_dir)
    if not dataset_id.strip():
        raise ValueError("An immutable OSRM dataset identifier is required.")
    sheets = pd.read_excel(input_workbook, sheet_name=None, engine="openpyxl")
    required = {"Oferta", "Demanda", "Warehouses"}
    missing = sorted(required - set(sheets))
    if missing:
        raise ValueError(f"The policy workbook is missing sheets: {missing}.")

    output_path = output_dir / "model_input.xlsx"
    audit_path = output_dir / "osrm_materialization_audit.json"
    if (output_path.exists() or audit_path.exists()) and not overwrite:
        raise FileExistsError(
            f"OSRM materialization already exists under {output_dir}."
        )

    distances, summary = build_osrm_distance_table(
        sheets["Oferta"],
        sheets["Demanda"],
        sheets["Warehouses"],
        client,
        dataset_id=dataset_id,
    )
    _validate_distance_table(distances, sheets)

    output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(input_workbook, output_path)
    with pd.ExcelWriter(
        output_path,
        engine="openpyxl",
        mode="a",
        if_sheet_exists="replace",
    ) as writer:
        distances.to_excel(writer, sheet_name="Distancias", index=False)

    audit = {
        "schema_version": 1,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "input_workbook": input_workbook.name,
        "input_workbook_sha256": _sha256(input_workbook),
        "output_workbook": output_path.name,
        "output_workbook_sha256": _sha256(output_path),
        "distance_status": "osrm_authoritative",
        "distance_provenance": summary,
    }
    audit_path.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return PolicyOSRMArtifacts(workbook=output_path, audit_json=audit_path)


def _validate_distance_table(
    distances: pd.DataFrame,
    sheets: dict[str, pd.DataFrame],
) -> None:
    origins = sheets["Oferta"]["Cidade"].dropna().astype(str).nunique()
    warehouses = sheets["Warehouses"]["CDA"].dropna().astype(str).nunique()
    demand = sheets["Demanda"]
    customer_columns = ["Cidade", "Tipo_Demanda"]
    missing_customer_columns = sorted(set(customer_columns) - set(demand.columns))
    if missing_customer_columns:
        raise ValueError(
            "Demand data cannot reproduce customer identifiers; missing "
            f"{missing_customer_columns}."
        )
    customers = len(demand[customer_columns].drop_duplicates())
    expected = {
        "OD": origins * warehouses,
        "DC": warehouses * customers,
        "DD": warehouses * (warehouses - 1),
        "OC": origins * customers,
    }
    observed = {
        str(key): int(value)
        for key, value in distances["Tipo_Arco"].value_counts().items()
    }
    if observed != expected:
        raise ValueError(
            f"OSRM route counts differ from the complete matrix: {observed} "
            f"!= {expected}."
        )
    if distances["Distancia_km"].isna().any():
        raise ValueError("OSRM materialization produced missing distances.")
    accepted_sources = {"osrm", "haversine_fallback"}
    invalid_sources = sorted(
        set(distances["Fonte_Distancia"].dropna().astype(str)) - accepted_sources
    )
    if invalid_sources:
        raise ValueError(f"Unsupported distance sources: {invalid_sources}.")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
