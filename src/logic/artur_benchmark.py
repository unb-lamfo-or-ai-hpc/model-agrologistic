"""Verified acquisition and structural reconciliation of Artur's benchmark data."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.request import urlopen

import pandas as pd


DEFAULT_CONTRACT_PATH = Path("data/manifests/mvp_data_contract.json")


class AssetIntegrityError(ValueError):
    """Raised when a downloaded or cached artifact violates the frozen contract."""


@dataclass(frozen=True, slots=True)
class AssetSpec:
    """Immutable identity of one file required for benchmark reconstruction."""

    path: str
    git_blob_sha: str
    size_bytes: int
    role: str


def load_artur_contract(path: Path = DEFAULT_CONTRACT_PATH) -> dict[str, Any]:
    """Load and minimally validate the Artur reproduction track."""

    contract = json.loads(path.read_text(encoding="utf-8"))
    try:
        track = contract["tracks"]["artur_benchmark_reproduction"]
        repository = track["repository"]
        commit_sha = track["commit_sha"]
    except KeyError as exc:
        raise ValueError(f"Missing Artur contract field: {exc.args[0]}") from exc

    if not repository.startswith("https://github.com/"):
        raise ValueError("The Artur repository must be an HTTPS GitHub URL.")
    if len(commit_sha) != 40 or any(char not in "0123456789abcdef" for char in commit_sha):
        raise ValueError("The Artur commit SHA must be a lowercase 40-character hex digest.")
    return track


def iter_asset_specs(track: dict[str, Any]) -> Iterable[AssetSpec]:
    """Yield source-pool files and reconstruction dependencies from the contract."""

    groups = (
        ("source_pool", track.get("assets", [])),
        ("reconstruction_dependency", track.get("reconstruction_dependencies", [])),
    )
    seen: set[str] = set()
    for default_role, assets in groups:
        for asset in assets:
            spec = AssetSpec(
                path=asset["path"],
                git_blob_sha=asset["git_blob_sha"],
                size_bytes=int(asset["size_bytes"]),
                role=asset.get("role", default_role),
            )
            _safe_relative_path(spec.path)
            if spec.path in seen:
                raise ValueError(f"Duplicate asset path in contract: {spec.path}")
            seen.add(spec.path)
            yield spec


def git_blob_sha(data: bytes) -> str:
    """Return the SHA-1 Git assigns to the exact byte sequence of a blob."""

    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def verify_asset(path: Path, spec: AssetSpec) -> None:
    """Verify size and Git blob identity for a local artifact."""

    data = path.read_bytes()
    actual_sha = git_blob_sha(data)
    if len(data) != spec.size_bytes or actual_sha != spec.git_blob_sha:
        raise AssetIntegrityError(
            f"Integrity check failed for {spec.path}: expected size={spec.size_bytes} "
            f"and blob={spec.git_blob_sha}, got size={len(data)} and blob={actual_sha}."
        )


def materialize_artur_assets(
    track: dict[str, Any],
    cache_dir: Path,
    *,
    fetch_missing: bool,
    fetcher: Callable[[str], bytes] | None = None,
) -> list[dict[str, Any]]:
    """Verify cached files and optionally fetch missing files from the pinned commit."""

    commit_sha = track["commit_sha"]
    repository_slug = track["repository"].removeprefix("https://github.com/").removesuffix("/")
    root = cache_dir / commit_sha
    download = fetcher or _download_bytes
    records: list[dict[str, Any]] = []

    for spec in iter_asset_specs(track):
        relative_path = _safe_relative_path(spec.path)
        target = root.joinpath(*relative_path.parts)
        status = "verified_existing"
        if not target.exists():
            if not fetch_missing:
                raise FileNotFoundError(
                    f"Missing {spec.path}. Run the reconciliation command with --fetch."
                )
            url = (
                f"https://raw.githubusercontent.com/{repository_slug}/"
                f"{commit_sha}/{spec.path}"
            )
            data = download(url)
            actual_sha = git_blob_sha(data)
            if len(data) != spec.size_bytes or actual_sha != spec.git_blob_sha:
                raise AssetIntegrityError(
                    f"Downloaded bytes violate the contract for {spec.path}."
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(f"{target.name}.part")
            temporary.write_bytes(data)
            temporary.replace(target)
            status = "downloaded"
        verify_asset(target, spec)
        records.append(
            {
                "path": spec.path,
                "role": spec.role,
                "status": status,
                "size_bytes": spec.size_bytes,
                "git_blob_sha": spec.git_blob_sha,
                "local_path": str(target),
            }
        )
    return records


def build_artur_gold_reconciliation(
    track: dict[str, Any],
    cache_dir: Path,
    gold_workbook: Path,
) -> dict[str, Any]:
    """Compare the pinned Artur source pool with the canonical gold workbook."""

    artur_root = cache_dir / track["commit_sha"] / "benchmark"
    artur_supply = pd.read_excel(artur_root / "Edited_Supply.xlsx")
    artur_demand = pd.read_excel(artur_root / "Edited_Demand.xlsx")
    artur_warehouses = pd.read_excel(artur_root / "Warehouses.xlsx")
    gold_supply = pd.read_excel(gold_workbook, sheet_name="Oferta")
    gold_demand = pd.read_excel(gold_workbook, sheet_name="Demanda")
    gold_warehouses = pd.read_excel(gold_workbook, sheet_name="Warehouses")

    inventories = {
        "artur_source_pool": {
            "supply": _supply_inventory(artur_supply),
            "demand": _demand_inventory(artur_demand),
            "warehouses": _warehouse_inventory(artur_warehouses, gold=False),
        },
        "gold_workbook": {
            "supply": _supply_inventory(gold_supply),
            "demand": _demand_inventory(gold_demand),
            "warehouses": _warehouse_inventory(gold_warehouses, gold=True),
        },
    }
    rows = _comparison_rows(inventories)

    artur_demand_values = pd.to_numeric(artur_demand["Peso (ton)"], errors="coerce")
    finite_mask = artur_demand_values.notna()
    gold_demand_values = pd.to_numeric(gold_demand["Peso (ton)"], errors="coerce")
    artur_ids = set(artur_warehouses["CDA"].astype(str))
    gold_ids = set(gold_warehouses["CDA"].astype(str))
    lineage_checks = {
        "supply_source_rows_identical": _frames_equal(artur_supply, gold_supply),
        "demand_keys_identical": _frames_equal(
            artur_demand.drop(columns=["Peso (ton)"]),
            gold_demand[list(artur_demand.columns)].drop(columns=["Peso (ton)"]),
        ),
        "finite_demand_values_identical": bool(
            finite_mask.equals(gold_demand_values.notna())
            and _numeric_series_equal(
                artur_demand_values.loc[finite_mask], gold_demand_values.loc[finite_mask]
            )
        ),
        "artur_export_infinity_rows": int((artur_demand["Peso (ton)"] == "∞").sum()),
        "gold_explicit_export_rows": int(
            (gold_demand["Tipo_Demanda"].astype(str).str.upper() == "EXPORTACAO").sum()
        ),
        "shared_warehouse_ids": len(artur_ids & gold_ids),
        "artur_only_warehouse_ids": len(artur_ids - gold_ids),
        "gold_extension_warehouse_ids": len(gold_ids - artur_ids),
    }

    controls = track.get("reproduction_controls", {})
    return {
        "schema_version": 1,
        "scope": "source_pool_structural_reconciliation",
        "reproduction_level": "bounded",
        "source_repository": track["repository"],
        "source_commit_sha": track["commit_sha"],
        "gold_workbook": str(gold_workbook),
        "inventories": inventories,
        "lineage_checks": lineage_checks,
        "comparison_rows": rows,
        "reproduction_controls": controls,
        "interpretation": {
            "same_source": (
                "The gold workbook preserves Artur's complete supply source pool and finite "
                "domestic demand values."
            ),
            "schema_transformation": (
                "Legacy infinity export demand is represented by explicit demand type and "
                "upper-bound rules in the gold workbook."
            ),
            "extension": (
                "The gold workbook extends the warehouse network and model parameters; its "
                "optimization results are robustness evidence, not a direct numerical replica."
            ),
            "exact_replication_limit": (
                "The terminal last_* benchmark instance and a frozen OSRM distance matrix are "
                "not present at the pinned commit. Exact thesis-result replication cannot yet "
                "be claimed."
            ),
        },
    }


def write_reconciliation_outputs(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    """Write the complete JSON report and a tabular metric comparison."""

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "artur_gold_reconciliation.json"
    csv_path = output_dir / "artur_gold_reconciliation.csv"
    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    rows = report["comparison_rows"]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return json_path, csv_path


def _download_bytes(url: str) -> bytes:
    with urlopen(url, timeout=60) as response:
        return response.read()


def _safe_relative_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"Unsafe asset path: {value}")
    return path


def _supply_inventory(frame: pd.DataFrame) -> dict[str, int | float]:
    weights = pd.to_numeric(frame["Peso (ton)"], errors="raise")
    return {
        "rows": len(frame),
        "nodes": int(frame["Cidade"].nunique()),
        "products": int(frame["Produto"].nunique()),
        "periods": int(frame["Data"].nunique()),
        "total_tons": float(weights.sum()),
    }


def _demand_inventory(frame: pd.DataFrame) -> dict[str, int | float]:
    weights = pd.to_numeric(frame["Peso (ton)"], errors="coerce")
    if "Tipo_Demanda" in frame:
        export_mask = frame["Tipo_Demanda"].astype(str).str.upper() == "EXPORTACAO"
    else:
        export_mask = weights.isna()
    domestic_mask = ~export_mask
    return {
        "rows": len(frame),
        "nodes": int(frame["Cidade"].nunique()),
        "domestic_nodes": int(frame.loc[domestic_mask, "Cidade"].nunique()),
        "export_nodes": int(frame.loc[export_mask, "Cidade"].nunique()),
        "products": int(frame["Produto"].nunique()),
        "periods": int(frame["Data"].nunique()),
        "domestic_total_tons": float(weights.loc[domestic_mask].sum()),
        "export_rows": int(export_mask.sum()),
    }


def _warehouse_inventory(frame: pd.DataFrame, *, gold: bool) -> dict[str, int | float]:
    if gold:
        columns = {
            "static": "Cap. Estática (t)",
            "reception": "Cap. Recepção (t)",
            "shipping": "Cap. Expedição (t)",
            "maximum": "Cap. Estática Máxima (t)",
        }
        normalized_status = frame["Status"].replace(
            {"Existente": "Existing", "Candidato": "Candidate"}
        )
    else:
        columns = {
            "static": "Static Cap. (t)",
            "reception": "Recep. Cap. (t)",
            "shipping": "Exped. Cap. (t)",
            "maximum": "Max Static Cap. (t)",
        }
        normalized_status = frame["Status"]
    return {
        "rows": len(frame),
        "existing": int((normalized_status == "Existing").sum()),
        "candidate": int((normalized_status == "Candidate").sum()),
        "static_capacity_tons": _numeric_total(frame[columns["static"]]),
        "reception_capacity_tons_per_day": _numeric_total(frame[columns["reception"]]),
        "shipping_capacity_tons_per_day": _numeric_total(frame[columns["shipping"]]),
        "candidate_max_static_capacity_tons": _numeric_total(frame[columns["maximum"]]),
    }


def _numeric_total(series: pd.Series) -> float:
    return float(pd.to_numeric(series, errors="coerce").fillna(0.0).sum())


def _comparison_rows(inventories: dict[str, Any]) -> list[dict[str, Any]]:
    artur = inventories["artur_source_pool"]
    gold = inventories["gold_workbook"]
    rows: list[dict[str, Any]] = []
    for dataset in ("supply", "demand", "warehouses"):
        for metric, artur_value in artur[dataset].items():
            gold_value = gold[dataset][metric]
            equal = _values_equal(artur_value, gold_value)
            rows.append(
                {
                    "dataset": dataset,
                    "metric": metric,
                    "artur_source_pool": artur_value,
                    "gold_workbook": gold_value,
                    "delta_gold_minus_artur": gold_value - artur_value,
                    "relationship": "same" if equal else "extended_or_transformed",
                }
            )
    return rows


def _values_equal(left: int | float, right: int | float) -> bool:
    return math.isclose(float(left), float(right), rel_tol=1e-12, abs_tol=1e-6)


def _frames_equal(left: pd.DataFrame, right: pd.DataFrame) -> bool:
    if list(left.columns) != list(right.columns) or left.shape != right.shape:
        return False
    for column in left:
        left_values = left[column]
        right_values = right[column]
        if pd.api.types.is_numeric_dtype(left_values):
            if not _numeric_series_equal(left_values, right_values):
                return False
        elif not left_values.fillna("").astype(str).equals(
            right_values.fillna("").astype(str)
        ):
            return False
    return True


def _numeric_series_equal(left: pd.Series, right: pd.Series) -> bool:
    left_values = pd.to_numeric(left, errors="coerce")
    right_values = pd.to_numeric(right, errors="coerce")
    if not left_values.isna().equals(right_values.isna()):
        return False
    differences = (left_values.fillna(0.0) - right_values.fillna(0.0)).abs()
    return bool((differences <= 1e-8).all())

