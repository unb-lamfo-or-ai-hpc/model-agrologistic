"""Build deterministic, nested warehouse populations for scale experiments."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

DEFAULT_TARGET_POPULATIONS = (215, 500, 1_000, 2_000, 5_000, 10_000, 18_000)
DEFAULT_SELECTION_SEED = "model-agrologistic-v020-warehouse-population-v1"

WAREHOUSE_ID = "CDA"
STATUS = "Status"
STATE = "UF"
WAREHOUSE_TYPE = "Tipo"
LATITUDE = "Latitude"
LONGITUDE = "Longitude"
STATIC_CAPACITY = "Cap. Estática (t)"
RECEPTION_CAPACITY = "Cap. Recepção (t)"
SHIPPING_CAPACITY = "Cap. Expedição (t)"
MAX_STATIC_CAPACITY = "Cap. Estática Máxima (t)"
OPENING_COST = "Custo de Abertura ($)"

REQUIRED_COLUMNS = (
    WAREHOUSE_ID,
    STATUS,
    STATE,
    WAREHOUSE_TYPE,
    LATITUDE,
    LONGITUDE,
    STATIC_CAPACITY,
    RECEPTION_CAPACITY,
    SHIPPING_CAPACITY,
    MAX_STATIC_CAPACITY,
    OPENING_COST,
)


@dataclass(frozen=True, slots=True)
class WarehousePopulationArtifacts:
    """Paths created by one warehouse-registry audit."""

    population_order_csv: Path
    population_levels_csv: Path
    manifest_json: Path


def audit_warehouse_registry(
    source_workbook: Path,
    output_dir: Path,
    *,
    target_populations: tuple[int, ...] = DEFAULT_TARGET_POPULATIONS,
    selection_seed: str = DEFAULT_SELECTION_SEED,
    sheet_name: str = "Sheet1",
    anchor_workbook: Path | None = None,
    anchor_sheet_name: str = "Warehouses",
) -> WarehousePopulationArtifacts:
    """Audit a source workbook and persist an immutable population protocol."""

    source_workbook = Path(source_workbook)
    output_dir = Path(output_dir)
    frame = pd.read_excel(source_workbook, sheet_name=sheet_name)
    anchor_candidate_ids: tuple[str, ...] = ()
    anchor_existing_ids: tuple[str, ...] = ()
    if anchor_workbook is not None:
        anchor_workbook = Path(anchor_workbook)
        anchor_frame = pd.read_excel(anchor_workbook, sheet_name=anchor_sheet_name)
        _validate_columns(anchor_frame)
        anchor_candidate_ids = tuple(
            anchor_frame.loc[
                anchor_frame[STATUS].map(_population_role) == "candidate",
                WAREHOUSE_ID,
            ].astype(str)
        )
        anchor_existing_ids = tuple(
            anchor_frame.loc[
                anchor_frame[STATUS].map(_population_role) == "existing",
                WAREHOUSE_ID,
            ].astype(str)
        )
    population_order, level_summary, audit = build_population_order(
        frame,
        target_populations=target_populations,
        selection_seed=selection_seed,
        anchor_candidate_ids=anchor_candidate_ids,
        anchor_existing_ids=anchor_existing_ids,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    population_order_path = output_dir / "warehouse_population_order.csv"
    population_levels_path = output_dir / "warehouse_population_levels.csv"
    manifest_path = output_dir / "warehouse_population_manifest.json"

    population_order.to_csv(population_order_path, index=False)
    level_summary.to_csv(population_levels_path, index=False)
    manifest = {
        "schema_version": 1,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "source_file": source_workbook.name,
        "source_sha256": _sha256(source_workbook),
        "source_sheet": sheet_name,
        "anchor_source": (
            {
                "file": anchor_workbook.name,
                "sha256": _sha256(anchor_workbook),
                "sheet": anchor_sheet_name,
            }
            if anchor_workbook is not None
            else None
        ),
        "selection_seed": selection_seed,
        "selection_method": (
            "nested deterministic proportional strata over state, warehouse "
            "type, and static-capacity quartile"
        ),
        "target_populations": list(target_populations),
        **audit,
        "artifacts": {
            "population_order_csv": population_order_path.name,
            "population_levels_csv": population_levels_path.name,
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return WarehousePopulationArtifacts(
        population_order_csv=population_order_path,
        population_levels_csv=population_levels_path,
        manifest_json=manifest_path,
    )


def build_population_order(
    frame: pd.DataFrame,
    *,
    target_populations: tuple[int, ...] = DEFAULT_TARGET_POPULATIONS,
    selection_seed: str = DEFAULT_SELECTION_SEED,
    anchor_candidate_ids: tuple[str, ...] = (),
    anchor_existing_ids: tuple[str, ...] = (),
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Return a nested facility order, level summary, and validation audit."""

    _validate_columns(frame)
    targets = _validate_targets(target_populations)
    prepared = frame.copy()
    prepared[WAREHOUSE_ID] = prepared[WAREHOUSE_ID].astype(str).str.strip()
    if prepared[WAREHOUSE_ID].eq("").any():
        raise ValueError("Warehouse identifiers cannot be blank.")
    if prepared[WAREHOUSE_ID].duplicated().any():
        duplicates = sorted(
            prepared.loc[prepared[WAREHOUSE_ID].duplicated(False), WAREHOUSE_ID]
            .astype(str)
            .unique()
        )
        raise ValueError(f"Duplicate warehouse identifiers: {duplicates[:10]!r}.")

    prepared["population_role"] = prepared[STATUS].map(_population_role)
    _validate_numeric_inputs(prepared)
    _validate_coordinates(prepared)

    existing = prepared.loc[prepared["population_role"] == "existing"].copy()
    candidates = prepared.loc[prepared["population_role"] == "candidate"].copy()
    candidates["population_eligible"] = candidates[STATIC_CAPACITY] > 0.0
    candidates["exclusion_reason"] = candidates["population_eligible"].map(
        {True: "", False: "nonpositive_static_capacity"}
    )
    eligible = candidates.loc[candidates["population_eligible"]].copy()

    maximum_population = len(existing) + len(eligible)
    if targets[0] < len(existing):
        raise ValueError(
            "The smallest target population cannot exclude protected existing "
            "warehouses."
        )
    if targets[-1] > maximum_population:
        raise ValueError(
            f"Target {targets[-1]} exceeds the {maximum_population} eligible "
            "real facilities."
        )

    anchor_ids = tuple(
        dict.fromkeys(str(item).strip() for item in anchor_candidate_ids)
    )
    protected_existing_ids = tuple(
        dict.fromkeys(str(item).strip() for item in anchor_existing_ids)
    )
    if protected_existing_ids:
        source_existing_ids = set(existing[WAREHOUSE_ID])
        expected_existing_ids = set(protected_existing_ids)
        if source_existing_ids != expected_existing_ids:
            missing = sorted(expected_existing_ids - source_existing_ids)
            additional = sorted(source_existing_ids - expected_existing_ids)
            raise ValueError(
                "The source registry does not preserve the canonical existing "
                f"warehouse population; missing={missing[:10]!r}, "
                f"additional={additional[:10]!r}."
            )
    if anchor_ids:
        expected_anchor_count = targets[0] - len(existing)
        if len(anchor_ids) != expected_anchor_count:
            raise ValueError(
                f"The canonical anchor must contain {expected_anchor_count} "
                f"candidates, not {len(anchor_ids)}."
            )
        eligible_ids = set(eligible[WAREHOUSE_ID])
        missing_anchor_ids = sorted(set(anchor_ids) - eligible_ids)
        if missing_anchor_ids:
            raise ValueError(
                "Canonical anchor candidates are absent or ineligible in the "
                f"registry: {missing_anchor_ids[:10]!r}."
            )

    anchor = eligible.loc[eligible[WAREHOUSE_ID].isin(anchor_ids)].copy()
    anchor["capacity_quartile"] = pd.NA
    anchor["selection_stratum"] = "canonical_gold_anchor"
    anchor["selection_hash"] = anchor[WAREHOUSE_ID].map(
        lambda warehouse: hashlib.sha256(
            f"{selection_seed}|anchor|{warehouse}".encode()
        ).hexdigest()
    )
    anchor = anchor.sort_values(["selection_hash", WAREHOUSE_ID]).reset_index(
        drop=True
    )
    anchor["candidate_rank"] = anchor.index + 1

    extension_pool = eligible.loc[~eligible[WAREHOUSE_ID].isin(anchor_ids)]
    extension = _rank_candidates(extension_pool, selection_seed)
    extension["candidate_rank"] += len(anchor)
    ranked = pd.concat([anchor, extension], ignore_index=True)
    first_target = {
        rank: next(
            target
            for target in targets
            if rank <= target - len(existing)
        )
        for rank in range(1, targets[-1] - len(existing) + 1)
    }
    ranked["first_population_total"] = ranked["candidate_rank"].map(first_target)

    derived_columns = [
        WAREHOUSE_ID,
        "population_eligible",
        "exclusion_reason",
        "capacity_quartile",
        "selection_stratum",
        "selection_hash",
        "candidate_rank",
        "first_population_total",
    ]
    candidate_order = candidates[
        [WAREHOUSE_ID, "population_eligible", "exclusion_reason"]
    ]
    candidate_order = candidate_order.merge(
        ranked[derived_columns],
        on=[WAREHOUSE_ID, "population_eligible", "exclusion_reason"],
        how="left",
        validate="one_to_one",
    )
    existing_order = existing[[WAREHOUSE_ID]].copy()
    existing_order["population_eligible"] = True
    existing_order["exclusion_reason"] = ""
    existing_order["capacity_quartile"] = pd.NA
    existing_order["selection_stratum"] = "protected_existing"
    existing_order["selection_hash"] = ""
    existing_order["candidate_rank"] = pd.NA
    existing_order["first_population_total"] = targets[0]

    order = pd.concat([existing_order, candidate_order], ignore_index=True)
    order = prepared[
        [
            WAREHOUSE_ID,
            STATUS,
            STATE,
            WAREHOUSE_TYPE,
            LATITUDE,
            LONGITUDE,
            STATIC_CAPACITY,
            RECEPTION_CAPACITY,
            SHIPPING_CAPACITY,
            "population_role",
        ]
    ].merge(order, on=WAREHOUSE_ID, how="left", validate="one_to_one")
    order["population_role_rank"] = order["population_role"].map(
        {"existing": 0, "candidate": 1}
    )
    order = order.sort_values(
        ["population_role_rank", "candidate_rank", WAREHOUSE_ID],
        na_position="first",
    ).drop(columns="population_role_rank").reset_index(drop=True)

    levels = _summarize_levels(prepared, ranked, len(existing), targets)
    coordinate_duplicate_rows = int(
        prepared.duplicated([LATITUDE, LONGITUDE], keep=False).sum()
    )
    audit = {
        "source_row_count": int(len(prepared)),
        "unique_warehouse_count": int(prepared[WAREHOUSE_ID].nunique()),
        "existing_warehouse_count": int(len(existing)),
        "candidate_warehouse_count": int(len(candidates)),
        "eligible_candidate_count": int(len(eligible)),
        "canonical_anchor_candidate_count": int(len(anchor)),
        "canonical_existing_warehouse_count": int(len(protected_existing_ids)),
        "canonical_anchor_enabled": bool(anchor_ids),
        "excluded_candidate_count": int(len(candidates) - len(eligible)),
        "exclusions_by_reason": {
            str(key): int(value)
            for key, value in candidates.loc[
                ~candidates["population_eligible"], "exclusion_reason"
            ].value_counts().items()
        },
        "coordinate_duplicate_row_count": coordinate_duplicate_rows,
        "candidate_source_max_capacity_zero_count": int(
            candidates[MAX_STATIC_CAPACITY].eq(0.0).sum()
        ),
        "candidate_source_opening_cost_zero_count": int(
            candidates[OPENING_COST].eq(0.0).sum()
        ),
        "solver_translation_required": True,
        "solver_translation_contract": {
            "candidate_base_static_capacity": 0.0,
            "candidate_base_reception_capacity": 0.0,
            "candidate_base_shipping_capacity": 0.0,
            "candidate_max_static_capacity_source": STATIC_CAPACITY,
            "candidate_cost_source": (
                "canonical investment-cost table; never infer zero cost from "
                "the registry placeholders"
            ),
        },
    }
    return order, levels, audit


def _rank_candidates(candidates: pd.DataFrame, seed: str) -> pd.DataFrame:
    ranked = candidates.copy()
    quartiles = min(4, len(ranked))
    ranked["capacity_quartile"] = pd.qcut(
        ranked[STATIC_CAPACITY].rank(method="first"),
        q=quartiles,
        labels=False,
        duplicates="drop",
    ).astype(int) + 1
    ranked["selection_stratum"] = (
        ranked[STATE].astype(str)
        + "|"
        + ranked[WAREHOUSE_TYPE].astype(str)
        + "|Q"
        + ranked["capacity_quartile"].astype(str)
    )
    ranked["selection_hash"] = ranked[WAREHOUSE_ID].map(
        lambda warehouse: hashlib.sha256(
            f"{seed}|{warehouse}".encode()
        ).hexdigest()
    )
    ranked = ranked.sort_values(
        ["selection_stratum", "selection_hash", WAREHOUSE_ID]
    )
    grouped = ranked.groupby("selection_stratum", sort=True)
    ranked["stratum_position"] = grouped.cumcount() + 1
    ranked["stratum_size"] = grouped[WAREHOUSE_ID].transform("size")
    ranked["proportional_priority"] = (
        ranked["stratum_position"] - 0.5
    ) / ranked["stratum_size"]
    ranked = ranked.sort_values(
        ["proportional_priority", "selection_stratum", "selection_hash"]
    ).reset_index(drop=True)
    ranked["candidate_rank"] = ranked.index + 1
    return ranked


def _summarize_levels(
    prepared: pd.DataFrame,
    ranked: pd.DataFrame,
    existing_count: int,
    targets: tuple[int, ...],
) -> pd.DataFrame:
    existing = prepared.loc[prepared["population_role"] == "existing"]
    rows = []
    for target in targets:
        selected_candidates = ranked.loc[
            ranked["candidate_rank"] <= target - existing_count
        ]
        selected = pd.concat([existing, selected_candidates], ignore_index=True)
        rows.append(
            {
                "target_population": target,
                "existing_warehouses": existing_count,
                "candidate_warehouses": int(len(selected_candidates)),
                "total_warehouses": int(len(selected)),
                "state_count": int(selected[STATE].nunique()),
                "warehouse_type_count": int(selected[WAREHOUSE_TYPE].nunique()),
                "observed_static_capacity_tons": float(
                    selected[STATIC_CAPACITY].sum()
                ),
            }
        )
    return pd.DataFrame(rows)


def _validate_columns(frame: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Warehouse registry is missing columns: {missing!r}.")


def _validate_targets(targets: tuple[int, ...]) -> tuple[int, ...]:
    normalized = tuple(int(target) for target in targets)
    if not normalized or any(target <= 0 for target in normalized):
        raise ValueError("Target populations must contain positive integers.")
    if tuple(sorted(set(normalized))) != normalized:
        raise ValueError("Target populations must be strictly increasing.")
    return normalized


def _validate_numeric_inputs(frame: pd.DataFrame) -> None:
    numeric_columns = (
        LATITUDE,
        LONGITUDE,
        STATIC_CAPACITY,
        RECEPTION_CAPACITY,
        SHIPPING_CAPACITY,
        MAX_STATIC_CAPACITY,
        OPENING_COST,
    )
    for column in numeric_columns:
        values = pd.to_numeric(frame[column], errors="coerce")
        if values.isna().any():
            raise ValueError(f"Column {column!r} contains missing or nonnumeric data.")
        frame[column] = values.astype(float)
    capacity_columns = numeric_columns[2:]
    if frame[list(capacity_columns)].lt(0.0).any().any():
        raise ValueError("Warehouse capacities and costs cannot be negative.")


def _validate_coordinates(frame: pd.DataFrame) -> None:
    if not frame[LATITUDE].between(-90.0, 90.0).all():
        raise ValueError("Warehouse latitudes must be in [-90, 90].")
    if not frame[LONGITUDE].between(-180.0, 180.0).all():
        raise ValueError("Warehouse longitudes must be in [-180, 180].")


def _population_role(value: Any) -> str:
    normalized = str(value).strip().casefold()
    if normalized.startswith("exist"):
        return "existing"
    if normalized.startswith("candidat"):
        return "candidate"
    raise ValueError(f"Unknown warehouse status {value!r}.")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

