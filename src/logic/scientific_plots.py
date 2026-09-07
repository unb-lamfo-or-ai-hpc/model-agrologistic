"""Generate publication-grade figures from an accepted scientific evidence package."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

PLOT_SCHEMA_VERSION = 1
REQUIRED_EVIDENCE_OUTPUTS = (
    "summary_csv",
    "checks_csv",
    "decomposition_csv",
    "investment_decisions_csv",
    "investment_changes_csv",
)
GATE_LABELS = {
    "gate_2b": "Gate 2B\nDeterministic",
    "gate_2c": "Gate 2C\n3 scenarios",
    "gate_2d": "Gate 2D\n9 scenarios",
}
GROUP_LABELS = {
    "investment": "Investment",
    "operation": "Operation",
    "penalty": "Big-M penalty",
}
INVESTMENT_LABELS = {
    "candidate_capacity": "Candidate capacity",
    "expansion_capacity": "Expansion capacity",
    "bulk_capacity": "Bulkification capacity",
}


class ScientificPlotError(RuntimeError):
    """Raised when an evidence package cannot support trustworthy figures."""


def build_publication_plots(
    evidence_dir: str | Path,
    output_dir: str | Path,
    *,
    dpi: int = 300,
) -> dict[str, Path]:
    """Build deterministic PNG, PDF, tidy CSV, and provenance artifacts.

    The evidence manifest must report an accepted package with no blocking
    failures. Every consumed CSV is checked against the SHA-256 digest stored
    in that manifest before any figure is generated.
    """

    if dpi < 72:
        raise ValueError("dpi must be at least 72.")
    evidence_root = Path(evidence_dir).resolve()
    destination = Path(output_dir).resolve()
    manifest_path = evidence_root / "mvp_evidence_manifest.json"
    manifest = _read_json(manifest_path)
    _validate_evidence_manifest(manifest, manifest_path)

    frames, sources = _load_evidence_frames(evidence_root, manifest)
    _validate_acceptance_checks(frames["checks_csv"])
    gate_order = [str(gate) for gate in manifest.get("gate_order", [])]
    if not gate_order:
        raise ScientificPlotError("The evidence manifest does not declare a gate order.")

    plt, sns, pd = _plot_dependencies()
    _configure_style(plt, sns)
    destination.mkdir(parents=True, exist_ok=True)

    builders: list[
        tuple[str, Callable[..., tuple[Any, Any, tuple[str, ...]]]]
    ] = [
        ("gate_performance", _plot_gate_performance),
        ("capacity_adequacy", _plot_capacity_adequacy),
        ("cost_structure", _plot_cost_structure),
        ("value_of_information", _plot_value_of_information),
        ("value_of_information_decomposition", _plot_value_decomposition),
        ("investment_capacity", _plot_investment_capacity),
        ("investment_changes", _plot_investment_changes),
    ]

    paths: dict[str, Path] = {}
    figure_records: list[dict[str, Any]] = []
    for stem, builder in builders:
        figure, tidy, source_keys = builder(frames, gate_order, plt, sns, pd)
        record, generated = _save_figure(
            figure,
            tidy,
            destination,
            stem,
            dpi=dpi,
            plt=plt,
            source_keys=source_keys,
            sources=sources,
        )
        figure_records.append(record)
        paths.update(generated)

    plot_manifest = {
        "schema_version": PLOT_SCHEMA_VERSION,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "scientific_scope": (
            "bounded reproduction and controlled stochastic extensions; "
            "not direct numerical validation of the thesis forecasting pipeline"
        ),
        "evidence_status": "accepted",
        "evidence_manifest": {
            "path": manifest_path.name,
            "sha256": _sha256(manifest_path),
            "schema_version": manifest.get("schema_version"),
            "gate_order": gate_order,
        },
        "probability_interpretation": manifest.get("interpretation", {}).get(
            "probability_policy_fallback"
        ),
        "monetary_caveat": manifest.get("interpretation", {}).get("monetary_caveat"),
        "rendering": {
            "dpi": dpi,
            "backend": "Agg",
            "matplotlib": _package_version("matplotlib"),
            "seaborn": _package_version("seaborn"),
            "pandas": _package_version("pandas"),
        },
        "sources": sources,
        "figures": figure_records,
    }
    manifest_output = destination / "scientific_plot_manifest.json"
    _write_json(manifest_output, plot_manifest)
    paths["manifest_json"] = manifest_output
    return paths


def _validate_evidence_manifest(manifest: dict[str, Any], path: Path) -> None:
    if manifest.get("overall_status") != "accepted":
        raise ScientificPlotError(f"Evidence package is not accepted: {path}")
    if int(manifest.get("blocking_failure_count", -1)) != 0:
        raise ScientificPlotError("Accepted evidence reports blocking failures.")
    outputs = manifest.get("outputs")
    if not isinstance(outputs, dict):
        raise ScientificPlotError("Evidence manifest outputs are missing or invalid.")
    missing = sorted(set(REQUIRED_EVIDENCE_OUTPUTS) - set(outputs))
    if missing:
        raise ScientificPlotError(f"Evidence manifest is missing outputs: {missing}.")


def _load_evidence_frames(
    evidence_root: Path,
    manifest: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    _, _, pd = _plot_dependencies()
    outputs = manifest["outputs"]
    frames: dict[str, Any] = {}
    sources: dict[str, dict[str, Any]] = {}
    for key in REQUIRED_EVIDENCE_OUTPUTS:
        record = outputs[key]
        if not isinstance(record, dict):
            raise ScientificPlotError(f"Invalid evidence output record: {key}.")
        relative = Path(str(record.get("path", "")))
        if relative.is_absolute() or ".." in relative.parts:
            raise ScientificPlotError(f"Evidence output escapes its package: {relative}.")
        source = (evidence_root / relative).resolve()
        if not source.is_relative_to(evidence_root) or not source.is_file():
            raise ScientificPlotError(f"Evidence output is unavailable: {source}.")
        observed_hash = _sha256(source)
        expected_hash = str(record.get("sha256", ""))
        if observed_hash != expected_hash:
            raise ScientificPlotError(f"Evidence output checksum mismatch: {source}.")
        frames[key] = pd.read_csv(source)
        sources[key] = {
            "path": relative.as_posix(),
            "sha256": observed_hash,
            "size_bytes": source.stat().st_size,
        }
    return frames, sources


def _validate_acceptance_checks(frame: Any) -> None:
    _require_columns(frame, "checks_csv", {"passed", "severity"})
    failed = frame[
        frame["severity"].astype(str).str.lower().eq("error")
        & ~frame["passed"].map(_as_bool)
    ]
    if not failed.empty:
        raise ScientificPlotError("Evidence acceptance checks contain a blocking failure.")


def _plot_gate_performance(frames: dict[str, Any], gate_order: list[str], plt, sns, pd):
    summary = frames["summary_csv"].copy()
    _require_columns(
        summary,
        "summary_csv",
        {
            "gate",
            "domestic_service_level",
            "minimum_scenario_service_level",
            "maximum_scenario_service_level",
            "dyn_cap",
            "turnover",
        },
    )
    summary = _ordered(summary, gate_order, pd)
    definitions = (
        ("domestic_service_level", "Domestic service", "%", 100.0),
        ("dyn_cap", "Annualized DynCap", "Mt/year equivalent", 1e-6),
        ("turnover", "Inventory turnover", "year⁻¹", 1.0),
    )
    records: list[dict[str, Any]] = []
    for row in summary.to_dict("records"):
        for metric, label, unit, scale in definitions:
            value = _finite(row.get(metric))
            if value is None:
                continue
            lower = value
            upper = value
            if metric == "domestic_service_level":
                observed_lower = _finite(row.get("minimum_scenario_service_level"))
                observed_upper = _finite(row.get("maximum_scenario_service_level"))
                lower = value if observed_lower is None else observed_lower
                upper = value if observed_upper is None else observed_upper
            records.append(
                {
                    "gate": str(row["gate"]),
                    "gate_label": _gate_label(str(row["gate"])),
                    "metric": metric,
                    "metric_label": label,
                    "value": value,
                    "display_value": value * scale,
                    "lower": lower * scale,
                    "upper": upper * scale,
                    "unit": unit,
                }
            )
    tidy = pd.DataFrame(records)
    figure, axes = plt.subplots(1, 3, figsize=(11.2, 3.6))
    color = sns.color_palette("colorblind", 7)[0]
    for axis, (metric, title, unit, _) in zip(axes, definitions, strict=True):
        data = tidy[tidy["metric"] == metric]
        sns.barplot(data=data, x="gate_label", y="display_value", color=color, ax=axis)
        if metric == "domestic_service_level" and not data.empty:
            centers = list(range(len(data)))
            values = data["display_value"].to_numpy()
            lower = values - data["lower"].to_numpy()
            upper = data["upper"].to_numpy() - values
            axis.errorbar(
                centers,
                values,
                yerr=[lower, upper],
                fmt="none",
                color="black",
                capsize=3,
            )
            axis.set_ylim(0.0, 105.0)
        axis.set_title(title)
        axis.set_xlabel("")
        axis.set_ylabel(unit)
    figure.suptitle("Physical performance across the accepted evidence gates", fontweight="bold")
    figure.tight_layout()
    return figure, tidy, ("summary_csv",)


def _plot_capacity_adequacy(frames: dict[str, Any], gate_order: list[str], plt, sns, pd):
    summary = frames["summary_csv"].copy()
    metrics = (
        (
            "emergency_static_capacity",
            "Emergency static capacity",
            "Mt-period",
        ),
        (
            "emergency_reception_capacity",
            "Emergency reception capacity",
            "Mt/day-period",
        ),
        ("total_unmet_demand", "Unmet domestic demand", "Mt"),
    )
    _require_columns(summary, "summary_csv", {"gate", *(item[0] for item in metrics)})
    summary = _ordered(summary, gate_order, pd)
    records = []
    for row in summary.to_dict("records"):
        for metric, label, unit in metrics:
            value = _finite(row.get(metric))
            if value is None:
                continue
            records.append(
                {
                    "gate": str(row["gate"]),
                    "gate_label": _gate_label(str(row["gate"])),
                    "metric": metric,
                    "metric_label": label,
                    "value": value,
                    "display_value": value / 1e6,
                    "unit": unit,
                    "interpretation": "physical_complete_recourse_indicator",
                }
            )
    tidy = pd.DataFrame(records)
    figure, axes = plt.subplots(1, 3, figsize=(11.2, 3.6))
    colors = sns.color_palette("colorblind", 7)[2:5]
    for axis, (metric, title, unit), color in zip(axes, metrics, colors, strict=True):
        data = tidy[tidy["metric"] == metric]
        sns.barplot(data=data, x="gate_label", y="display_value", color=color, ax=axis)
        axis.set_title(title)
        axis.set_xlabel("")
        axis.set_ylabel(unit)
        if data["display_value"].max() > 0.0:
            axis.set_yscale("symlog", linthresh=1e-6)
    figure.suptitle(
        "Complete-recourse activation as a capacity-adequacy diagnostic",
        fontweight="bold",
    )
    figure.tight_layout()
    return figure, tidy, ("summary_csv",)


def _plot_cost_structure(frames: dict[str, Any], gate_order: list[str], plt, sns, pd):
    summary = frames["summary_csv"].copy()
    columns = {
        "investment_cost": "investment",
        "operation_cost": "operation",
        "penalty_cost": "penalty",
    }
    _require_columns(summary, "summary_csv", {"gate", "penalty_cost_share", *columns})
    summary = _ordered(summary, gate_order, pd)
    records = []
    for row in summary.to_dict("records"):
        for column, group in columns.items():
            value = _finite(row.get(column))
            if value is None:
                continue
            records.append(
                {
                    "gate": str(row["gate"]),
                    "gate_label": _gate_label(str(row["gate"])),
                    "cost_group": group,
                    "cost_group_label": GROUP_LABELS[group],
                    "value": value,
                    "billion_model_units": value / 1e9,
                    "interpretation": (
                        "nonobserved_big_m_feasibility_cost"
                        if group == "penalty"
                        else "modeled_economic_cost"
                    ),
                }
            )
    tidy = pd.DataFrame(records)
    shares = summary[["gate", "penalty_cost_share"]].copy()
    shares["gate_label"] = shares["gate"].map(_gate_label)
    shares["penalty_share_percent"] = pd.to_numeric(
        shares["penalty_cost_share"], errors="coerce"
    ) * 100.0
    share_records = shares.assign(
        record_type="penalty_share",
        value=shares["penalty_cost_share"],
        unit="fraction_of_penalized_cost",
    )[
        [
            "gate",
            "gate_label",
            "record_type",
            "value",
            "penalty_share_percent",
            "unit",
        ]
    ]
    tidy["record_type"] = "absolute_cost"
    tidy["unit"] = "model_currency_units"
    tidy_export = pd.concat([tidy, share_records], ignore_index=True, sort=False)

    figure, axes = plt.subplots(1, 2, figsize=(10.2, 3.8), gridspec_kw={"width_ratios": [1.6, 1]})
    sns.barplot(
        data=tidy,
        x="gate_label",
        y="billion_model_units",
        hue="cost_group_label",
        hue_order=[GROUP_LABELS[key] for key in ("investment", "operation", "penalty")],
        palette="colorblind",
        ax=axes[0],
    )
    axes[0].set_yscale("symlog", linthresh=0.1)
    axes[0].set_title("Absolute components")
    axes[0].set_xlabel("")
    axes[0].set_ylabel("10⁹ model currency units (symlog)")
    axes[0].legend(title="")
    sns.barplot(
        data=shares,
        x="gate_label",
        y="penalty_share_percent",
        color=sns.color_palette("colorblind", 7)[3],
        ax=axes[1],
    )
    axes[1].set_title("Big-M share of penalized cost")
    axes[1].set_xlabel("")
    axes[1].set_ylabel("%")
    axes[1].set_ylim(0.0, 105.0)
    figure.suptitle("Objective-function structure and interpretation boundary", fontweight="bold")
    figure.text(
        0.5,
        -0.02,
        "Big-M penalties preserve feasibility and are not observed shortage prices.",
        ha="center",
        fontsize=8,
    )
    figure.tight_layout()
    return figure, tidy_export, ("summary_csv",)


def _plot_value_of_information(frames: dict[str, Any], gate_order: list[str], plt, sns, pd):
    summary = frames["summary_csv"].copy()
    _require_columns(summary, "summary_csv", {"gate", "evpi", "vss"})
    summary = _ordered(summary, gate_order, pd)
    records = []
    for row in summary.to_dict("records"):
        for metric in ("evpi", "vss"):
            value = _finite(row.get(metric))
            if value is None:
                continue
            records.append(
                {
                    "gate": str(row["gate"]),
                    "gate_label": _gate_label(str(row["gate"])),
                    "metric": metric.upper(),
                    "value": value,
                    "billion_model_units": value / 1e9,
                    "interpretation": (
                        "perfect_information_value"
                        if metric == "evpi"
                        else "stochastic_solution_value_with_big_m_caveat"
                    ),
                }
            )
    tidy = pd.DataFrame(records)
    figure, axes = plt.subplots(1, 2, figsize=(8.2, 3.6))
    colors = sns.color_palette("colorblind", 7)
    for axis, metric, color in zip(axes, ("EVPI", "VSS"), (colors[0], colors[1]), strict=True):
        data = tidy[tidy["metric"] == metric]
        sns.barplot(data=data, x="gate_label", y="billion_model_units", color=color, ax=axis)
        axis.set_title(metric)
        axis.set_xlabel("")
        axis.set_ylabel("10⁹ model currency units")
    figure.suptitle(
        "Value of information under the controlled stochastic extensions",
        fontweight="bold",
    )
    figure.tight_layout()
    return figure, tidy, ("summary_csv",)


def _plot_value_decomposition(frames: dict[str, Any], gate_order: list[str], plt, sns, pd):
    decomposition = frames["decomposition_csv"].copy()
    _require_columns(
        decomposition,
        "decomposition_csv",
        {"gate", "section", "item", "value", "interpretation"},
    )
    decomposition = decomposition[
        decomposition["section"].isin(["evpi_group", "vss_group"])
        & decomposition["item"].isin(GROUP_LABELS)
    ].copy()
    decomposition["gate"] = pd.Categorical(
        decomposition["gate"], categories=gate_order, ordered=True
    )
    decomposition = decomposition.sort_values(["gate", "section", "item"])
    decomposition["gate_label"] = decomposition["gate"].astype(str).map(_gate_label)
    decomposition["metric"] = (
        decomposition["section"].str.replace("_group", "", regex=False).str.upper()
    )
    decomposition["group_label"] = decomposition["item"].map(GROUP_LABELS)
    decomposition["value"] = pd.to_numeric(decomposition["value"], errors="coerce")
    decomposition["billion_model_units"] = decomposition["value"] / 1e9
    tidy = decomposition[
        [
            "gate",
            "gate_label",
            "metric",
            "item",
            "group_label",
            "value",
            "billion_model_units",
            "interpretation",
        ]
    ].dropna(subset=["value"])

    figure, axes = plt.subplots(1, 2, figsize=(10.4, 3.8))
    for axis, metric in zip(axes, ("EVPI", "VSS"), strict=True):
        data = tidy[tidy["metric"] == metric]
        sns.barplot(
            data=data,
            x="gate_label",
            y="billion_model_units",
            hue="group_label",
            hue_order=[GROUP_LABELS[key] for key in ("investment", "operation", "penalty")],
            palette="colorblind",
            ax=axis,
        )
        axis.axhline(0.0, color="black", linewidth=0.8)
        axis.set_yscale("symlog", linthresh=0.01)
        axis.set_title(f"{metric} group contribution")
        axis.set_xlabel("")
        axis.set_ylabel("10⁹ model currency units (symlog)")
        axis.legend(title="")
    figure.suptitle("Value-of-information decomposition", fontweight="bold")
    figure.tight_layout()
    return figure, tidy, ("decomposition_csv",)


def _plot_investment_capacity(frames: dict[str, Any], gate_order: list[str], plt, sns, pd):
    summary = frames["summary_csv"].copy()
    _require_columns(summary, "summary_csv", {"gate", *INVESTMENT_LABELS})
    summary = _ordered(summary, gate_order, pd)
    records = []
    for row in summary.to_dict("records"):
        for metric, label in INVESTMENT_LABELS.items():
            value = _finite(row.get(metric))
            if value is None:
                continue
            records.append(
                {
                    "gate": str(row["gate"]),
                    "gate_label": _gate_label(str(row["gate"])),
                    "investment_type": metric,
                    "investment_label": label,
                    "capacity_tonnes": value,
                    "capacity_thousand_tonnes": value / 1e3,
                }
            )
    tidy = pd.DataFrame(records)
    figure, axis = plt.subplots(figsize=(7.6, 4.0))
    sns.barplot(
        data=tidy,
        x="gate_label",
        y="capacity_thousand_tonnes",
        hue="investment_label",
        hue_order=list(INVESTMENT_LABELS.values()),
        palette="colorblind",
        ax=axis,
    )
    axis.set_title("First-stage selected capacity")
    axis.set_xlabel("")
    axis.set_ylabel("Thousand tonnes")
    axis.legend(title="")
    figure.tight_layout()
    return figure, tidy, ("summary_csv", "investment_decisions_csv")


def _plot_investment_changes(frames: dict[str, Any], gate_order: list[str], plt, sns, pd):
    changes = frames["investment_changes_csv"].copy()
    _require_columns(
        changes,
        "investment_changes_csv",
        {"baseline_gate", "comparison_gate", "metric", "changed"},
    )
    changes["transition"] = (
        changes["baseline_gate"].astype(str) + " → " + changes["comparison_gate"].astype(str)
    )
    changes["changed_flag"] = changes["changed"].map(_as_bool).astype(int)
    counts = (
        changes.groupby(["transition", "metric"], sort=False, observed=True)["changed_flag"]
        .sum()
        .reset_index(name="changed_warehouses")
    )
    transition_order = [
        f"{left} → {right}" for left, right in zip(gate_order, gate_order[1:], strict=False)
    ]
    metric_order = [
        "open",
        "candidate_capacity",
        "expand",
        "expansion_capacity",
        "bulkify",
        "bulk_capacity",
        "effective_static_capacity",
    ]
    matrix = (
        counts.pivot(index="transition", columns="metric", values="changed_warehouses")
        .reindex(index=transition_order, columns=metric_order)
        .fillna(0.0)
    )
    tidy = matrix.rename_axis(index="transition", columns="metric").stack().reset_index()
    tidy.columns = ["transition", "metric", "changed_warehouses"]

    figure, axis = plt.subplots(figsize=(10.0, 3.2))
    sns.heatmap(
        matrix,
        annot=True,
        fmt=".0f",
        cmap="Blues",
        linewidths=0.5,
        linecolor="white",
        cbar_kws={"label": "Changed warehouses"},
        ax=axis,
    )
    axis.set_title("Facility-level stability of first-stage investment decisions")
    axis.set_xlabel("Decision metric")
    axis.set_ylabel("Gate transition")
    axis.set_xticklabels(axis.get_xticklabels(), rotation=30, ha="right")
    figure.tight_layout()
    return figure, tidy, ("investment_changes_csv",)


def _save_figure(
    figure,
    tidy,
    output_dir: Path,
    stem: str,
    *,
    dpi: int,
    plt,
    source_keys: tuple[str, ...],
    sources: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Path]]:
    csv_path = output_dir / f"{stem}.csv"
    png_path = output_dir / f"{stem}.png"
    pdf_path = output_dir / f"{stem}.pdf"
    _write_tidy_csv(csv_path, tidy)
    figure.savefig(
        png_path,
        format="png",
        dpi=dpi,
        bbox_inches="tight",
        facecolor="white",
        metadata={"Software": "model-agrologistic"},
    )
    figure.savefig(
        pdf_path,
        format="pdf",
        bbox_inches="tight",
        facecolor="white",
        metadata={
            "Creator": "model-agrologistic",
            "CreationDate": None,
            "ModDate": None,
        },
    )
    plt.close(figure)
    outputs = {"csv": csv_path, "png": png_path, "pdf": pdf_path}
    record = {
        "name": stem,
        "source_keys": list(source_keys),
        "source_sha256": {key: sources[key]["sha256"] for key in source_keys},
        "artifacts": {
            kind: {
                "path": path.name,
                "sha256": _sha256(path),
                "size_bytes": path.stat().st_size,
            }
            for kind, path in outputs.items()
        },
    }
    return record, {f"{stem}_{kind}": path for kind, path in outputs.items()}


def _plot_dependencies():
    try:
        import matplotlib

        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot as plt
        import pandas as pd
        import seaborn as sns
    except ImportError as exc:
        raise ScientificPlotError(
            "Scientific plotting requires the visualization dependency group: "
            "pip install -e '.[visualization]'."
        ) from exc
    return plt, sns, pd


def _configure_style(plt, sns) -> None:
    sns.set_theme(context="paper", style="whitegrid", palette="colorblind", font_scale=1.0)
    plt.rcParams.update(
        {
            "figure.dpi": 120,
            "savefig.dpi": 300,
            "font.family": "DejaVu Sans",
            "axes.titleweight": "semibold",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "legend.frameon": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def _ordered(frame: Any, gate_order: list[str], pd):
    ordered = frame.copy()
    ordered["gate"] = pd.Categorical(ordered["gate"], categories=gate_order, ordered=True)
    return ordered.sort_values("gate")


def _gate_label(gate: str) -> str:
    return GATE_LABELS.get(gate, gate.replace("_", " ").title())


def _require_columns(frame: Any, source: str, columns: set[str]) -> None:
    missing = sorted(columns - set(frame.columns))
    if missing:
        raise ScientificPlotError(f"{source} is missing columns: {missing}.")


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _package_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ScientificPlotError(f"Evidence manifest not found: {path}.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ScientificPlotError(f"Expected a JSON mapping: {path}.")
    return payload


def _write_tidy_csv(path: Path, frame: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False, lineterminator="\n", float_format="%.12g")
    temporary.replace(path)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="",
    )
    temporary.replace(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
