"""Build reader-facing tables and figures from completed optimization runs."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PRESENTATION_SCHEMA_VERSION = 1
PENALTY_COMPONENTS = {
    "unmet_demand",
    "emergency_static",
    "emergency_reception",
}
INVESTMENT_COMPONENTS = {
    "opening",
    "candidate_capacity",
    "expansion_fixed",
    "expansion_variable",
    "bulkification_fixed",
    "bulkification_variable",
}
COST_GROUPS = {
    "Freight": ("transport_od", "transport_dc", "transport_oc"),
    "Storage": ("storage",),
    "Transshipment": ("transport_dd",),
    "Opening": ("opening", "candidate_capacity"),
    "Expansion": ("expansion_fixed", "expansion_variable"),
    "Bulkification": ("bulkification_fixed", "bulkification_variable"),
}
ROUTE_LABELS = {
    "OD": "Origin to warehouse",
    "DD": "Warehouse to warehouse",
    "DC_domestic": "Warehouse to domestic demand",
    "DC_export": "Warehouse to export demand",
    "OC_domestic": "Direct origin to domestic demand",
    "OC_export": "Direct origin to export demand",
}


class ScientificResultsError(RuntimeError):
    """Raised when completed runs cannot support a valid comparison."""


@dataclass(frozen=True)
class CompletedRun:
    """Structured optimization result and its accompanying run metadata."""

    run_dir: Path
    payload: dict[str, Any]
    summary: dict[str, Any]
    preflight: dict[str, Any]

    @property
    def name(self) -> str:
        return str(self.payload["experiment"]["name"])

    @property
    def result(self) -> dict[str, Any]:
        return self.payload["result"]

    @property
    def experiment(self) -> dict[str, Any]:
        return self.payload["experiment"]


def build_scientific_results_presentation(
    *,
    deterministic_policy_dir: str | Path,
    deterministic_baseline_dir: str | Path,
    stochastic_extension_dir: str | Path,
    output_dir: str | Path,
    dpi: int = 300,
    data_loader: Callable[[CompletedRun], Any] | None = None,
) -> dict[str, Path]:
    """Generate publication tables, figures, tidy data, and a provenance manifest.

    The deterministic network-policy campaign supplies the direct-arc and route-set
    comparisons. The bounded deterministic run and controlled stochastic extensions
    supply the like-for-like deterministic-versus-stochastic comparison. These two
    instance families are never pooled into a single numerical ranking.
    """

    if dpi < 72:
        raise ValueError("dpi must be at least 72.")
    destination = Path(output_dir).resolve()
    destination.mkdir(parents=True, exist_ok=True)

    deterministic = _discover_runs(Path(deterministic_policy_dir), mode="det")
    baseline_candidates = _discover_runs(Path(deterministic_baseline_dir), mode="det")
    stochastic_candidates = _discover_runs(Path(stochastic_extension_dir), mode="sto")
    stochastic = _select_stochastic_results(stochastic_candidates)
    if len(deterministic) < 2:
        raise ScientificResultsError(
            "At least two deterministic network-policy runs are required."
        )
    if len(baseline_candidates) != 1:
        raise ScientificResultsError(
            "Exactly one bounded deterministic baseline is required."
        )
    if not stochastic:
        raise ScientificResultsError(
            "At least one stochastic EVPI/VSS run is required."
        )
    baseline = baseline_candidates[0]

    plt, sns, pd = _plot_dependencies()
    _configure_style(plt, sns)
    loader = data_loader or _default_data_loader

    deterministic_summary = _deterministic_summary(deterministic, pd)
    stochastic_summary = _stochastic_summary(stochastic, pd)
    paths: dict[str, Path] = {}
    paths.update(
        _save_table(
            deterministic_summary,
            destination,
            "deterministic_configuration_summary",
            "Deterministic network-policy configurations",
        )
    )
    paths.update(
        _save_table(
            stochastic_summary,
            destination,
            "stochastic_configuration_summary",
            "Controlled stochastic designs",
        )
    )
    paths.update(
        _save_table(
            _transpose_summary(
                deterministic_summary,
                key_columns=("configuration",),
                pd=pd,
            ),
            destination,
            "deterministic_manuscript_table",
            "Deterministic configurations: costs, decisions, and performance",
        )
    )
    paths.update(
        _save_table(
            _transpose_summary(
                stochastic_summary,
                key_columns=("design", "scenario"),
                pd=pd,
            ),
            destination,
            "stochastic_manuscript_table",
            "Stochastic designs: costs, decisions, and performance",
        )
    )

    cached_data: dict[str, Any] = {}

    def model_data(run: CompletedRun) -> Any:
        key = run.name
        if key not in cached_data:
            cached_data[key] = loader(run)
        return cached_data[key]

    deterministic_transport = _transport_work_records(deterministic, model_data, pd)
    stochastic_transport = _transport_work_records(stochastic, model_data, pd)
    deterministic_profiles = _warehouse_profiles(deterministic, pd)
    stochastic_profiles = _warehouse_profiles(stochastic, pd)
    direct_inventory = _direct_arc_inventory_differences(deterministic, pd)
    stochastic_inventory = _stochastic_inventory_differences(
        baseline,
        stochastic,
        pd,
    )
    cross_design_costs = _cross_design_cost_records(baseline, stochastic, pd)
    information = _information_records(stochastic, pd)
    robustness = _robustness_records(baseline, stochastic, pd)

    figures: list[
        tuple[
            str,
            Callable[..., tuple[Any, Any, str]],
            tuple[Any, ...],
        ]
    ] = [
        (
            "deterministic_cost_composition",
            _plot_deterministic_cost_composition,
            (deterministic_summary,),
        ),
        (
            "deterministic_transport_work",
            _plot_deterministic_transport_work,
            (deterministic_transport,),
        ),
        (
            "deterministic_warehouse_profiles",
            _plot_deterministic_warehouse_profiles,
            (deterministic_profiles,),
        ),
        (
            "direct_arc_inventory_difference",
            _plot_inventory_difference,
            (
                direct_inventory,
                "Inventory change when direct arcs are enabled",
            ),
        ),
        (
            "deterministic_stochastic_cost_composition",
            _plot_cross_design_cost_composition,
            (cross_design_costs,),
        ),
        (
            "stochastic_transport_work",
            _plot_stochastic_transport_work,
            (stochastic_transport,),
        ),
        (
            "stochastic_warehouse_profiles",
            _plot_stochastic_warehouse_profiles,
            (stochastic_profiles,),
        ),
        (
            "stochastic_inventory_difference",
            _plot_inventory_difference,
            (
                stochastic_inventory,
                "Inventory change: stochastic central scenario minus deterministic",
            ),
        ),
        (
            "value_of_information_detailed",
            _plot_information_detail,
            (information,),
        ),
        (
            "objective_robustness",
            _plot_objective_robustness,
            (robustness,),
        ),
    ]

    figure_manifest: list[dict[str, Any]] = []
    for stem, builder, arguments in figures:
        figure, tidy, note = builder(*arguments, plt=plt, sns=sns, pd=pd)
        generated, record = _save_figure(
            figure,
            tidy,
            destination,
            stem,
            note,
            dpi,
            plt,
        )
        paths.update(generated)
        figure_manifest.append(record)

    source_runs = [*deterministic, baseline, *stochastic]
    source_instance_ids = {
        **{run.name: "gold_workbook_network" for run in deterministic},
        **{
            run.name: "artur_legacy_i001"
            for run in (baseline, *stochastic)
        },
    }
    artur_workbook_hashes = sorted(
        {
            str(run.experiment.get("workbook_sha256"))
            for run in (baseline, *stochastic)
            if run.experiment.get("workbook_sha256")
        }
    )
    manifest = {
        "schema_version": PRESENTATION_SCHEMA_VERSION,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "scientific_scope": {
            "network_policy": (
                "full gold-workbook deterministic sensitivity using exploratory "
                "coverage-preserving shortest-distance and top-k route filters; "
                "these filters are not equivalent to either the historical "
                "20-percent filter or the thesis interhub cost factor"
            ),
            "stochastic": (
                "bounded legacy reproduction and controlled three- and "
                "nine-scenario extensions"
            ),
        },
        "route_filter_semantics": {
            "current_pareto": (
                "retains the configured shortest-distance fraction within route "
                "groups and then adds coverage-preserving routes"
            ),
            "current_top_k": (
                "retains the configured number of shortest routes within route "
                "groups and then adds coverage-preserving routes"
            ),
            "historical_artur_reference": (
                "retains 20 percent of distance-ranked candidates within the "
                "historical OD, DC, DD, and OC group definitions without the "
                "current coverage augmentations"
            ),
        },
        "instance_lineage": {
            "artur_legacy_i001": {
                "comparison_basis": (
                    "shared normalized adaptation protocol and logical solver-input "
                    "path"
                ),
                "binary_workbook_snapshots_identical": (
                    len(artur_workbook_hashes) == 1
                ),
                "workbook_sha256": artur_workbook_hashes,
                "interpretation": (
                    "binary workbook hashes may differ across runs produced after "
                    "workbook rebuilds; this is not a byte-identical replay"
                ),
            }
        },
        "units": {
            "money": "model monetary units; Big-M penalties are non-observed",
            "transport_work": "tonne-kilometres",
            "dynamic_capacity": "tonnes per annual equivalent",
            "turnover": "cycles per year",
            "inventory": "tonnes",
        },
        "source_runs": [
            {
                "name": run.name,
                "logical_instance_id": source_instance_ids[run.name],
                "result_sha256": _sha256(run.run_dir / "result.json"),
                "workbook_sha256": run.experiment.get("workbook_sha256"),
            }
            for run in source_runs
        ],
        "outputs": {
            key: {
                "path": path.name,
                "sha256": _sha256(path),
                "size_bytes": path.stat().st_size,
            }
            for key, path in paths.items()
        },
        "figures": figure_manifest,
    }
    manifest_path = destination / "scientific_results_manifest.json"
    _write_json(manifest_path, manifest)
    paths["manifest_json"] = manifest_path
    return paths


def _discover_runs(root: Path, *, mode: str) -> list[CompletedRun]:
    if not root.is_dir():
        raise ScientificResultsError(f"Run directory not found: {root.resolve()}")
    runs = []
    for result_path in sorted(root.glob("*/result.json")):
        payload = _read_json(result_path)
        result = payload.get("result", {})
        if result.get("model_mode") != mode or result.get("status") not in {
            "optimal",
            "time_limit",
        }:
            continue
        run_dir = result_path.parent
        runs.append(
            CompletedRun(
                run_dir=run_dir,
                payload=payload,
                summary=_read_optional_json(run_dir / "run_summary.json"),
                preflight=_read_optional_json(run_dir / "preflight.json"),
            )
        )
    return runs


def _select_stochastic_results(runs: list[CompletedRun]) -> list[CompletedRun]:
    selected: dict[int, CompletedRun] = {}
    for run in runs:
        count = int(run.summary.get("scenario_count") or 0)
        if count <= 0:
            continue
        current = selected.get(count)
        if current is None or (
            run.payload.get("stochastic_performance")
            and not current.payload.get("stochastic_performance")
        ):
            selected[count] = run
    return [selected[count] for count in sorted(selected)]


def _default_data_loader(run: CompletedRun) -> Any:
    from src.logic.excel_loader import ExcelLoaderConfig, load_model_data_from_excel

    experiment = run.experiment
    workbook = Path(str(experiment["workbook"]))
    if not workbook.is_file():
        raise ScientificResultsError(
            f"Source workbook is unavailable for {run.name}: {workbook}"
        )
    return load_model_data_from_excel(
        workbook,
        ExcelLoaderConfig(
            **_normalize_exported_loader_values(experiment.get("loader", {}))
        ),
    )


def _normalize_exported_loader_values(raw: dict[str, Any]) -> dict[str, Any]:
    """Restore tuple-valued loader fields after their JSON serialization."""

    values = dict(raw)
    for key in ("stochastic_supply_levels", "stochastic_demand_levels"):
        if values.get(key) is not None:
            values[key] = tuple(str(value) for value in values[key])
    if values.get("stochastic_combinations") is not None:
        values["stochastic_combinations"] = tuple(
            tuple(str(level) for level in combination)
            for combination in values["stochastic_combinations"]
        )
    if values.get("stochastic_probabilities") is not None:
        values["stochastic_probabilities"] = tuple(
            float(value) for value in values["stochastic_probabilities"]
        )
    return values


def _deterministic_summary(runs: list[CompletedRun], pd):
    records = []
    for run in runs:
        model = run.experiment.get("model", {})
        costs = _cost_groups(run.result.get("cost_breakdown", {}))
        decisions = _decision_totals(run.result.get("warehouse_decisions", []))
        estimate = run.preflight.get("estimate", run.preflight)
        strategy = str(model.get("route_filter_strategy", "none"))
        records.append(
            {
                "configuration": _network_policy_label(run),
                "direct_arcs": bool(model.get("use_direct_origin_customer", False)),
                "route_filter": strategy,
                "pareto_fraction": (
                    model.get("pareto_fraction") if strategy == "pareto" else None
                ),
                "route_top_k": (
                    model.get("route_top_k") if strategy == "top_k" else None
                ),
                "economic_cost_billion": _economic_cost(run) / 1e9,
                "penalized_objective_billion": _penalized_cost(run) / 1e9,
                "penalty_cost_billion": _penalty_cost(run) / 1e9,
                **{
                    f"{key.lower()}_billion": value / 1e9
                    for key, value in costs.items()
                },
                **decisions,
                "domestic_service_percent": _number(
                    run.summary.get("domestic_service_level"), 0.0
                )
                * 100.0,
                "dyn_cap_million_tonnes_per_year": _number(
                    run.summary.get("dyn_cap"), 0.0
                )
                / 1e6,
                "turnover_cycles_per_year": run.summary.get("turnover"),
                "emergency_capacity_tonnes_over_periods": run.summary.get(
                    "total_emergency_capacity"
                ),
                "estimated_variables": estimate.get("total_variables"),
                "routes_od": estimate.get("routes_od"),
                "routes_dc": estimate.get("routes_dc"),
                "routes_dd": estimate.get("routes_dd"),
                "routes_oc": estimate.get("routes_oc"),
                "runtime_seconds": run.summary.get("runtime_seconds"),
                "peak_rss_mb": run.summary.get("peak_rss_mb"),
            }
        )
    frame = pd.DataFrame(records)
    frame["_direct_order"] = ~frame["direct_arcs"]
    frame = frame.sort_values(["_direct_order", "route_filter", "configuration"])
    return frame.drop(columns="_direct_order")


def _stochastic_summary(runs: list[CompletedRun], pd):
    records = []
    for run in runs:
        scenario_metrics = run.result.get("metrics", {}).get("scenario_metrics", {})
        investment_cost = _investment_cost(run)
        scenario_costs = {
            scenario: investment_cost
            + _number(record.get("operating_cost"), math.nan)
            for scenario, record in scenario_metrics.items()
        }
        if not scenario_costs:
            raise ScientificResultsError(
                f"Stochastic run {run.name} has no scenario metrics."
            )
        costs = _cost_groups(run.result.get("cost_breakdown", {}))
        decisions = _decision_totals(run.result.get("warehouse_decisions", []))
        stochastic = run.payload.get("stochastic_performance") or {}
        estimate = run.preflight.get("estimate", run.preflight)
        model = run.experiment.get("model", {})
        common = {
            "design": _stochastic_label(run),
            "scenario_count": int(run.summary.get("scenario_count") or 0),
            "direct_arcs": bool(model.get("use_direct_origin_customer", False)),
            "route_policy": _route_policy_label(model),
            "economic_cost_billion": _economic_cost(run) / 1e9,
            "penalized_objective_billion": _penalized_cost(run) / 1e9,
            "penalty_cost_billion": _penalty_cost(run) / 1e9,
            **{
                f"{key.lower()}_billion": value / 1e9
                for key, value in costs.items()
            },
            **decisions,
            "minimum_scenario_objective_billion": min(scenario_costs.values())
            / 1e9,
            "maximum_scenario_objective_billion": max(scenario_costs.values())
            / 1e9,
            "evpi_million": _number(stochastic.get("evpi"), 0.0) / 1e6,
            "vss_billion": _number(stochastic.get("vss"), 0.0) / 1e9,
            "estimated_variables": estimate.get("total_variables"),
            "runtime_seconds": run.summary.get("runtime_seconds"),
            "peak_rss_mb": run.summary.get("peak_rss_mb"),
        }
        performance_path = run.run_dir / "scenario_performance.csv"
        performance_records = (
            pd.read_csv(performance_path).to_dict("records")
            if performance_path.is_file()
            else []
        )
        scenario_performance = {
            str(item["scenario"]): item for item in performance_records
        }
        for scenario, values in scenario_metrics.items():
            performance = scenario_performance.get(str(scenario), {})
            records.append(
                {
                    **common,
                    "row_scope": "scenario",
                    "scenario": _scenario_label(scenario),
                    "probability": values.get("probability"),
                    "scenario_objective_billion": scenario_costs[scenario] / 1e9,
                    "domestic_service_percent": 100.0
                    * _number(
                        performance.get("domestic_service_level"),
                        run.summary.get("domestic_service_level", 0.0),
                    ),
                    "dyn_cap_million_tonnes_per_year": _number(
                        performance.get("dynamic_capacity"),
                        run.summary.get("dyn_cap", 0.0),
                    )
                    / 1e6,
                    "turnover_cycles_per_year": performance.get(
                        "turnover", run.summary.get("turnover")
                    ),
                    "emergency_static_tonne_periods": performance.get(
                        "emergency_static_capacity"
                    ),
                    "emergency_reception_tonne_per_day_periods": performance.get(
                        "emergency_reception_capacity"
                    ),
                }
            )
        records.append(
            {
                **common,
                "row_scope": "probability_weighted_expected",
                "scenario": "Probability-weighted expected",
                "probability": 1.0,
                "scenario_objective_billion": (
                    investment_cost + _weighted_scenario_cost(run)
                )
                / 1e9,
                "domestic_service_percent": 100.0
                * _number(run.summary.get("domestic_service_level"), 0.0),
                "dyn_cap_million_tonnes_per_year": _number(
                    run.summary.get("dyn_cap"), 0.0
                )
                / 1e6,
                "turnover_cycles_per_year": run.summary.get("turnover"),
                "emergency_static_tonne_periods": run.summary.get(
                    "emergency_static_capacity"
                ),
                "emergency_reception_tonne_per_day_periods": run.summary.get(
                    "emergency_reception_capacity"
                ),
            }
        )
    return pd.DataFrame(records).sort_values(
        ["scenario_count", "row_scope", "scenario"]
    )


def _transport_work_records(runs, data_loader, pd):
    records = []
    for run in runs:
        data = data_loader(run)
        for flow in run.result.get("flows", []):
            value = _number(flow.get("value"), 0.0)
            if value <= 0.0:
                continue
            route_type = str(flow["route_type"]).upper()
            distance, distance_resolution = _flow_distance(
                data,
                flow,
                route_type,
            )
            route_key = _route_key(flow, route_type)
            records.append(
                {
                    "design": (
                        _network_policy_label(run)
                        if run.result.get("model_mode") == "det"
                        else _stochastic_label(run)
                    ),
                    "scenario": _scenario_label(flow.get("scenario", "Deterministic")),
                    "route_type": route_type,
                    "route_path": ROUTE_LABELS[route_key],
                    "product": str(flow.get("product", "All products")),
                    "tonnes": value,
                    "distance_km": distance,
                    "distance_resolution": distance_resolution,
                    "tonne_kilometres": value * distance,
                }
            )
    frame = pd.DataFrame(records)
    if frame.empty:
        raise ScientificResultsError(
            "No positive flows are available for transport-work plots."
        )
    return (
        frame.groupby(
            [
                "design",
                "scenario",
                "route_type",
                "route_path",
                "product",
                "distance_resolution",
            ],
            as_index=False,
        )[["tonnes", "tonne_kilometres"]]
        .sum()
        .sort_values(["design", "scenario", "route_path", "product"])
    )


def _warehouse_profiles(runs: list[CompletedRun], pd):
    records = []
    for run in runs:
        storage_path = run.run_dir / "storage_by_warehouse.csv"
        storage = (
            pd.read_csv(storage_path)
            if storage_path.is_file()
            else pd.DataFrame(
                run.result.get("metrics", {})
                .get("storage", {})
                .get("warehouse_metrics", [])
            )
        )
        decisions = {
            str(item["warehouse"]): item
            for item in run.result.get("warehouse_decisions", [])
        }
        for row in storage.to_dict("records"):
            warehouse = str(row["warehouse"])
            decision = decisions.get(warehouse, {})
            records.append(
                {
                    "design": (
                        _network_policy_label(run)
                        if run.result.get("model_mode") == "det"
                        else _stochastic_label(run)
                    ),
                    "scenario": _scenario_label(row.get("scenario", "Deterministic")),
                    "warehouse": warehouse,
                    "investment_status": _investment_status(decision),
                    "dynamic_capacity_tonnes_per_year": row.get("dynamic_capacity"),
                    "turnover_cycles_per_year": row.get("turnover"),
                    "total_outbound_tonnes": row.get("total_outbound"),
                    "terminal_inventory_tonnes": row.get("terminal_inventory"),
                    "effective_static_capacity_tonnes": row.get(
                        "effective_static_capacity"
                    ),
                }
            )
    frame = pd.DataFrame(records)
    frame = frame.dropna(
        subset=["dynamic_capacity_tonnes_per_year", "turnover_cycles_per_year"]
    )
    frame = frame[
        (frame["dynamic_capacity_tonnes_per_year"] > 0.0)
        & (frame["total_outbound_tonnes"] > 0.0)
    ]
    if frame.empty:
        raise ScientificResultsError(
            "No active warehouses are available for operational profiles."
        )
    return frame


def _direct_arc_inventory_differences(runs: list[CompletedRun], pd):
    by_policy: dict[str, dict[bool, CompletedRun]] = {}
    for run in runs:
        model = run.experiment.get("model", {})
        policy = _route_policy_label(model)
        direct = bool(model.get("use_direct_origin_customer", False))
        by_policy.setdefault(policy, {})[direct] = run
    records = []
    for policy, pair in sorted(by_policy.items()):
        if set(pair) != {False, True}:
            continue
        enabled = _inventory_frame(pair[True], pd)
        disabled = _inventory_frame(pair[False], pd)
        merged = enabled.merge(
            disabled,
            on=["warehouse", "period"],
            how="outer",
            suffixes=("_enabled", "_disabled"),
        ).fillna(0.0)
        for row in merged.to_dict("records"):
            records.append(
                {
                    "comparison": policy,
                    "warehouse": row["warehouse"],
                    "period": row["period"],
                    "inventory_difference_tonnes": (
                        row["inventory_tonnes_enabled"]
                        - row["inventory_tonnes_disabled"]
                    ),
                }
            )
    if not records:
        raise ScientificResultsError(
            "No matched direct-enabled/direct-disabled inventory pairs were found."
        )
    return pd.DataFrame(records)


def _stochastic_inventory_differences(
    baseline: CompletedRun,
    stochastic: list[CompletedRun],
    pd,
):
    deterministic = _inventory_frame(baseline, pd)
    records = []
    for run in stochastic:
        inventory = _central_or_expected_inventory(run, pd)
        merged = inventory.merge(
            deterministic,
            on=["warehouse", "period"],
            how="outer",
            suffixes=("_stochastic", "_deterministic"),
        ).fillna(0.0)
        for row in merged.to_dict("records"):
            records.append(
                {
                    "comparison": _stochastic_label(run),
                    "warehouse": row["warehouse"],
                    "period": row["period"],
                    "inventory_difference_tonnes": (
                        row["inventory_tonnes_stochastic"]
                        - row["inventory_tonnes_deterministic"]
                    ),
                }
            )
    return pd.DataFrame(records)


def _cross_design_cost_records(baseline, stochastic, pd):
    records = []
    for run, design in [
        (baseline, "Deterministic baseline"),
        *((run, _stochastic_label(run)) for run in stochastic),
    ]:
        groups = _cost_groups(run.result.get("cost_breakdown", {}))
        denominator = sum(groups.values())
        for component, value in groups.items():
            records.append(
                {
                    "design": design,
                    "cost_component": component,
                    "cost_billion": value / 1e9,
                    "economic_cost_share_percent": (
                        100.0 * value / denominator if denominator else 0.0
                    ),
                }
            )
    return pd.DataFrame(records)


def _information_records(runs: list[CompletedRun], pd):
    records = []
    for run in runs:
        label = _stochastic_label(run)
        stochastic = run.payload.get("stochastic_performance") or {}
        for metric, key in (
            ("Recourse problem", "recourse_problem"),
            ("Wait-and-see", "wait_and_see"),
            ("Expected-value problem", "expected_value_problem"),
            ("Expected result of EV solution", "expected_result_of_ev_solution"),
        ):
            records.append(
                {
                    "design": label,
                    "record_type": "solution_value",
                    "metric": metric,
                    "component": "Total",
                    "value": _number(stochastic.get(key), math.nan),
                }
            )
        records.extend(
            [
                {
                    "design": label,
                    "record_type": "information_metric",
                    "metric": "EVPI",
                    "component": "Total",
                    "value": _number(stochastic.get("evpi"), math.nan),
                },
                {
                    "design": label,
                    "record_type": "information_metric",
                    "metric": "VSS",
                    "component": "Total",
                    "value": _number(stochastic.get("vss"), math.nan),
                },
            ]
        )
        decomposition = stochastic.get("decomposition", {}).get("vss_by_group", {})
        for component in ("investment", "operation", "penalty"):
            records.append(
                {
                    "design": label,
                    "record_type": "vss_decomposition",
                    "metric": "VSS",
                    "component": component.title(),
                    "value": _number(decomposition.get(component), 0.0),
                }
            )
    return pd.DataFrame(records)


def _robustness_records(baseline, stochastic, pd):
    records = [
        {
            "design": "Deterministic baseline",
            "scenario": "Deterministic",
            "probability": 1.0,
            "penalized_objective": _penalized_cost(baseline),
            "evpi": math.nan,
        }
    ]
    for run in stochastic:
        metrics = run.result.get("metrics", {}).get("scenario_metrics", {})
        evpi = _number(
            (run.payload.get("stochastic_performance") or {}).get("evpi"),
            math.nan,
        )
        for scenario, values in metrics.items():
            records.append(
                {
                    "design": _stochastic_label(run),
                    "scenario": _scenario_label(scenario),
                    "probability": _number(values.get("probability"), 0.0),
                    "penalized_objective": _investment_cost(run)
                    + _number(values.get("operating_cost"), 0.0),
                    "evpi": evpi,
                }
            )
    return pd.DataFrame(records)


def _plot_deterministic_cost_composition(frame, *, plt, sns, pd):
    components = [f"{name.lower()}_billion" for name in COST_GROUPS]
    tidy = frame.melt(
        id_vars=["configuration", "direct_arcs", "route_filter"],
        value_vars=components,
        var_name="cost_component",
        value_name="cost_billion",
    )
    tidy["cost_component"] = tidy["cost_component"].str.replace(
        "_billion", "", regex=False
    ).str.title()
    totals = tidy.groupby("configuration")["cost_billion"].transform("sum")
    tidy["economic_cost_share_percent"] = 100.0 * tidy["cost_billion"] / totals
    pivot = tidy.pivot(
        index="configuration",
        columns="cost_component",
        values="economic_cost_share_percent",
    ).fillna(0.0)
    order = frame["configuration"].tolist()
    pivot = pivot.reindex(order)
    figure, axis = plt.subplots(figsize=(9.6, 4.8))
    left = None
    colors = sns.color_palette("colorblind", len(COST_GROUPS))
    for color, component in zip(colors, COST_GROUPS, strict=True):
        values = pivot.get(component, pd.Series(0.0, index=pivot.index))
        axis.barh(pivot.index, values, left=left, label=component, color=color)
        left = values if left is None else left + values
    axis.set_xlabel("Share of modeled economic cost (%)")
    axis.set_ylabel("")
    axis.set_xlim(0.0, 100.0)
    axis.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.18))
    axis.set_title("Economic cost composition by routing policy")
    figure.tight_layout()
    return figure, tidy, (
        "Big-M feasibility penalties are excluded from the percentage denominator."
    )


def _plot_deterministic_transport_work(frame, *, plt, sns, pd):
    designs = list(dict.fromkeys(frame["design"]))
    rows = math.ceil(len(designs) / 2)
    figure, axes = plt.subplots(rows, 2, figsize=(11.0, 4.0 * rows), squeeze=False)
    for axis, design in zip(axes.flat, designs, strict=False):
        data = frame[frame["design"] == design].copy()
        data["billion_tonne_kilometres"] = data["tonne_kilometres"] / 1e9
        sns.barplot(
            data=data,
            x="route_path",
            y="billion_tonne_kilometres",
            hue="product",
            estimator="sum",
            errorbar=None,
            ax=axis,
        )
        axis.set_title(design)
        axis.set_xlabel("")
        axis.set_ylabel("Transport work (billion tonne-kilometres)")
        axis.tick_params(axis="x", rotation=35)
    for axis in axes.flat[len(designs) :]:
        axis.set_visible(False)
    figure.suptitle("Transport work by route type and deterministic policy")
    figure.tight_layout()
    return figure, frame, (
        "Tonne-kilometres equal transported tonnes times route distance."
    )


def _plot_deterministic_warehouse_profiles(frame, *, plt, sns, pd):
    designs = list(dict.fromkeys(frame["design"]))
    rows = math.ceil(len(designs) / 2)
    figure, axes = plt.subplots(rows, 2, figsize=(10.8, 4.2 * rows), squeeze=False)
    for axis, design in zip(axes.flat, designs, strict=False):
        data = frame[frame["design"] == design].copy()
        sns.scatterplot(
            data=data,
            x="turnover_cycles_per_year",
            y="dynamic_capacity_tonnes_per_year",
            hue="investment_status",
            size="total_outbound_tonnes",
            sizes=(18, 220),
            alpha=0.72,
            ax=axis,
        )
        axis.set_xscale("symlog", linthresh=0.1)
        axis.set_yscale("log")
        axis.set_xlabel("Inventory turnover (cycles/year)")
        axis.set_ylabel("Annualized dynamic capacity (tonnes/year)")
        axis.set_title(design)
    for axis in axes.flat[len(designs) :]:
        axis.set_visible(False)
    figure.suptitle("Operational profiles of active warehouses")
    figure.tight_layout()
    return figure, frame, "Bubble area represents total warehouse outbound flow."


def _plot_inventory_difference(frame, title, *, plt, sns, pd):
    comparisons = list(dict.fromkeys(frame["comparison"]))
    figure, axes = plt.subplots(
        1,
        len(comparisons),
        figsize=(6.0 * len(comparisons), 6.2),
        squeeze=False,
    )
    peak = (
        frame.assign(abs_difference=frame["inventory_difference_tonnes"].abs())
        .groupby(["comparison", "warehouse"], as_index=False)["abs_difference"]
        .max()
    )
    selected: dict[str, list[str]] = {
        comparison: group.nlargest(25, "abs_difference")["warehouse"].tolist()
        for comparison, group in peak.groupby("comparison")
    }
    displayed = frame.copy()
    displayed["displayed"] = displayed.apply(
        lambda row: row["warehouse"] in selected[row["comparison"]],
        axis=1,
    )
    visible_values = displayed.loc[
        displayed["displayed"], "inventory_difference_tonnes"
    ].abs()
    limit = max(float(visible_values.quantile(0.98)), 1.0)
    for axis, comparison in zip(axes.flat, comparisons, strict=True):
        data = displayed[
            (displayed["comparison"] == comparison) & displayed["displayed"]
        ]
        matrix = data.pivot(
            index="warehouse",
            columns="period",
            values="inventory_difference_tonnes",
        ).fillna(0.0)
        matrix = matrix.reindex(selected[comparison]) / 1e3
        sns.heatmap(
            matrix,
            cmap="vlag",
            center=0.0,
            vmin=-limit / 1e3,
            vmax=limit / 1e3,
            ax=axis,
            cbar_kws={"label": "Inventory difference (thousand tonnes)"},
        )
        axis.set_title(comparison)
        axis.set_xlabel("Period")
        axis.set_ylabel("Warehouse")
    figure.suptitle(title)
    figure.tight_layout()
    return figure, displayed, (
        "The 25 warehouses with the largest absolute temporal difference are shown."
    )


def _plot_cross_design_cost_composition(frame, *, plt, sns, pd):
    pivot = frame.pivot(
        index="design",
        columns="cost_component",
        values="economic_cost_share_percent",
    ).fillna(0.0)
    figure, axis = plt.subplots(figsize=(9.6, 4.4))
    left = None
    colors = sns.color_palette("colorblind", len(COST_GROUPS))
    for color, component in zip(colors, COST_GROUPS, strict=True):
        values = pivot.get(component, pd.Series(0.0, index=pivot.index))
        axis.barh(pivot.index, values, left=left, label=component, color=color)
        left = values if left is None else left + values
    axis.set_xlabel("Share of modeled economic cost (%)")
    axis.set_ylabel("")
    axis.set_xlim(0.0, 100.0)
    axis.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.2))
    axis.set_title("Deterministic and stochastic economic cost composition")
    figure.tight_layout()
    return figure, frame, (
        "The bounded baseline and stochastic extensions derive from the same "
        "logical Artur adaptation protocol; binary workbook snapshot hashes are "
        "reported separately."
    )


def _plot_stochastic_transport_work(frame, *, plt, sns, pd):
    designs = list(dict.fromkeys(frame["design"]))
    figure, axes = plt.subplots(
        len(designs),
        1,
        figsize=(11.0, 3.6 * len(designs)),
        squeeze=False,
    )
    plotted = (
        frame.groupby(
            ["design", "scenario", "route_path", "product"],
            as_index=False,
        )["tonne_kilometres"]
        .sum()
        .assign(
            billion_tonne_kilometres=lambda value: value["tonne_kilometres"]
            / 1e9,
            route_product=lambda value: value["route_path"]
            + " | "
            + value["product"].astype(str),
        )
    )
    for axis, design in zip(axes.flat, designs, strict=True):
        data = plotted[plotted["design"] == design]
        matrix = data.pivot(
            index="route_product",
            columns="scenario",
            values="billion_tonne_kilometres",
        ).fillna(0.0)
        sns.heatmap(
            matrix,
            cmap="crest",
            annot=True,
            fmt=".1f",
            ax=axis,
            cbar_kws={"label": "Billion tonne-kilometres"},
        )
        axis.set_title(design)
        axis.set_xlabel("Scenario")
        axis.set_ylabel("Route type and product")
    figure.suptitle("Transport work across stochastic scenarios")
    figure.tight_layout()
    exported = frame.copy()
    exported["billion_tonne_kilometres"] = (
        exported["tonne_kilometres"] / 1e9
    )
    return figure, exported, (
        "Cells report total transport work by route type and scenario."
    )


def _plot_stochastic_warehouse_profiles(frame, *, plt, sns, pd):
    designs = list(dict.fromkeys(frame["design"]))
    figure, axes = plt.subplots(
        1,
        len(designs),
        figsize=(6.0 * len(designs), 5.0),
        squeeze=False,
    )
    for axis, design in zip(axes.flat, designs, strict=True):
        data = frame[frame["design"] == design]
        sns.scatterplot(
            data=data,
            x="turnover_cycles_per_year",
            y="dynamic_capacity_tonnes_per_year",
            hue="scenario",
            style="investment_status",
            size="total_outbound_tonnes",
            sizes=(16, 180),
            alpha=0.68,
            ax=axis,
        )
        axis.set_xscale("symlog", linthresh=0.1)
        axis.set_yscale("log")
        axis.set_xlabel("Inventory turnover (cycles/year)")
        axis.set_ylabel("Annualized dynamic capacity (tonnes/year)")
        axis.set_title(design)
    figure.suptitle("Warehouse operating profiles under uncertainty")
    figure.tight_layout()
    return figure, frame, (
        "Color identifies the scenario, marker shape the investment status, and "
        "bubble area total outbound flow."
    )


def _plot_information_detail(frame, *, plt, sns, pd):
    figure, axes = plt.subplots(2, 2, figsize=(11.0, 7.2))
    solutions = frame[frame["record_type"] == "solution_value"].copy()
    solutions["billion"] = solutions["value"] / 1e9
    sns.barplot(
        data=solutions,
        x="design",
        y="billion",
        hue="metric",
        ax=axes[0, 0],
    )
    axes[0, 0].set_title("RP, WS, EV, and EEV objective values")
    axes[0, 0].set_ylabel("Billion model monetary units")
    axes[0, 0].set_xlabel("")

    evpi = frame[
        (frame["record_type"] == "information_metric") & (frame["metric"] == "EVPI")
    ].copy()
    evpi["million"] = evpi["value"] / 1e6
    sns.barplot(data=evpi, x="design", y="million", color="#4477AA", ax=axes[0, 1])
    axes[0, 1].set_title("Expected value of perfect information")
    axes[0, 1].set_ylabel("Million model monetary units")
    axes[0, 1].set_xlabel("")

    vss = frame[
        (frame["record_type"] == "information_metric") & (frame["metric"] == "VSS")
    ].copy()
    vss["billion"] = vss["value"] / 1e9
    sns.barplot(data=vss, x="design", y="billion", color="#66CCEE", ax=axes[1, 0])
    axes[1, 0].set_title("Value of the stochastic solution")
    axes[1, 0].set_ylabel("Billion model monetary units")
    axes[1, 0].set_xlabel("")

    decomposition = frame[frame["record_type"] == "vss_decomposition"].copy()
    decomposition["billion"] = decomposition["value"] / 1e9
    sns.barplot(
        data=decomposition,
        x="design",
        y="billion",
        hue="component",
        ax=axes[1, 1],
    )
    axes[1, 1].axhline(0.0, color="black", linewidth=0.8)
    axes[1, 1].set_yscale("symlog", linthresh=0.001)
    axes[1, 1].set_title("VSS decomposition (symlog scale)")
    axes[1, 1].set_ylabel("Billion model monetary units")
    axes[1, 1].set_xlabel("")
    for axis in axes.flat:
        axis.tick_params(axis="x", rotation=12)
    figure.suptitle("Value of information and stochasticity")
    figure.tight_layout()
    return figure, frame, (
        "The Big-M penalty contribution is a feasibility diagnostic, not an "
        "observed cost."
    )


def _plot_objective_robustness(frame, *, plt, sns, pd):
    groups = []
    for design, data in frame.groupby("design", sort=False):
        probabilities = data["probability"].astype(float)
        values = data["penalized_objective"].astype(float)
        probabilities = probabilities / probabilities.sum()
        groups.append(
            {
                "design": design,
                "expected": float((probabilities * values).sum()),
                "minimum": float(values.min()),
                "maximum": float(values.max()),
                "evpi": (
                    float(data["evpi"].dropna().iloc[0])
                    if data["evpi"].notna().any()
                    else math.nan
                ),
            }
        )
    summary = pd.DataFrame(groups)
    figure, axis = plt.subplots(figsize=(9.6, 4.8))
    positions = list(range(len(summary)))
    expected = summary["expected"] / 1e9
    lower = expected - summary["minimum"] / 1e9
    upper = summary["maximum"] / 1e9 - expected
    axis.bar(positions, expected, color=sns.color_palette("colorblind", len(summary)))
    axis.errorbar(
        positions,
        expected,
        yerr=[lower.clip(lower=0.0), upper.clip(lower=0.0)],
        fmt="none",
        color="black",
        capsize=4,
    )
    axis.set_xticks(positions, summary["design"], rotation=12)
    axis.set_ylabel("Penalized objective (billion model monetary units)")
    axis.set_xlabel("")
    second = axis.twinx()
    second.plot(
        positions,
        summary["evpi"] / 1e6,
        color="#CC3311",
        marker="D",
        linestyle="--",
    )
    second.set_ylabel("EVPI (million model monetary units)", color="#CC3311")
    axis.set_title("Objective robustness and scenario spread")
    figure.tight_layout()
    return figure, summary, (
        "Whiskers show the minimum and maximum scenario operating objective; "
        "the objective includes non-observed Big-M feasibility penalties."
    )


def _save_table(frame, output, stem, title):
    csv_path = output / f"{stem}.csv"
    markdown_path = output / f"{stem}.md"
    _write_csv(csv_path, frame)
    _write_markdown(markdown_path, frame, title)
    return {f"{stem}_csv": csv_path, f"{stem}_md": markdown_path}


def _transpose_summary(frame, *, key_columns, pd):
    display = frame.copy()
    display["reader_column"] = display[list(key_columns)].astype(str).agg(
        " | ".join,
        axis=1,
    )
    display = display.drop(columns=list(key_columns)).set_index("reader_column")
    transposed = display.transpose().reset_index(names="metric")
    transposed["metric"] = transposed["metric"].map(_reader_label)
    return transposed


def _save_figure(figure, tidy, output, stem, note, dpi, plt):
    csv_path = output / f"{stem}.csv"
    png_path = output / f"{stem}.png"
    pdf_path = output / f"{stem}.pdf"
    _write_csv(csv_path, tidy)
    metadata = {"Creator": "model-agrologistic", "Title": stem}
    figure.savefig(png_path, dpi=dpi, bbox_inches="tight", metadata=metadata)
    figure.savefig(pdf_path, bbox_inches="tight", metadata=metadata)
    plt.close(figure)
    paths = {
        f"{stem}_csv": csv_path,
        f"{stem}_png": png_path,
        f"{stem}_pdf": pdf_path,
    }
    record = {
        "name": stem,
        "interpretation_note": note,
        "outputs": {
            kind: {"sha256": _sha256(path), "size_bytes": path.stat().st_size}
            for kind, path in (("csv", csv_path), ("png", png_path), ("pdf", pdf_path))
        },
    }
    return paths, record


def _inventory_frame(run: CompletedRun, pd):
    frame = pd.DataFrame(run.result.get("inventories", []))
    if frame.empty:
        return pd.DataFrame(columns=["warehouse", "period", "inventory_tonnes"])
    return (
        frame.groupby(["warehouse", "period"], as_index=False)["value"]
        .sum()
        .rename(columns={"value": "inventory_tonnes"})
    )


def _central_or_expected_inventory(run: CompletedRun, pd):
    frame = pd.DataFrame(run.result.get("inventories", []))
    if frame.empty:
        return pd.DataFrame(columns=["warehouse", "period", "inventory_tonnes"])
    central = frame[frame["scenario"].astype(str).str.contains("base__demanda_base")]
    if not central.empty:
        frame = central
        frame = frame.assign(weighted_value=frame["value"])
    else:
        probabilities = run.result.get("metadata", {}).get("scenario_probabilities", {})
        frame = frame.assign(
            weighted_value=frame.apply(
                lambda row: row["value"] * probabilities.get(row["scenario"], 0.0),
                axis=1,
            )
        )
    return (
        frame.groupby(["warehouse", "period"], as_index=False)["weighted_value"]
        .sum()
        .rename(columns={"weighted_value": "inventory_tonnes"})
    )


def _flow_distance(
    data: Any,
    flow: dict[str, Any],
    route_type: str,
) -> tuple[float, str]:
    if route_type == "OD":
        key = (str(flow["origin"]), str(flow["warehouse"]))
        mapping = data.dist_od
    elif route_type == "DC":
        key = (str(flow["warehouse"]), str(flow["customer"]))
        mapping = data.dist_dc
    elif route_type == "OC":
        key = (str(flow["origin"]), str(flow["customer"]))
        mapping = data.dist_oc
    elif route_type == "DD":
        key = (str(flow["warehouse_from"]), str(flow["warehouse_to"]))
        mapping = data.dist_dd
    else:
        raise ScientificResultsError(f"Unsupported route type: {route_type}")
    if key in mapping:
        return float(mapping[key]), "exact"
    if route_type not in {"DC", "OC"}:
        raise ScientificResultsError(
            f"Missing {route_type} distance for route {key}."
        )

    physical_destination = _physical_customer_id(key[1])
    candidates = [
        (pair, float(distance))
        for pair, distance in mapping.items()
        if pair[0] == key[0]
        and _physical_customer_id(str(pair[1])) == physical_destination
    ]
    if len(candidates) == 1:
        return candidates[0][1], "typed_customer_alias"
    distinct_distances = {distance for _pair, distance in candidates}
    if candidates and len(distinct_distances) == 1:
        return candidates[0][1], "typed_customer_alias_equal_distances"
    candidate_text = ", ".join(str(pair) for pair, _distance in candidates[:5])
    raise ScientificResultsError(
        f"Missing unambiguous {route_type} distance for route {key}. "
        f"Physical-customer candidates: {candidate_text or 'none'}."
    )


def _physical_customer_id(value: str) -> str:
    base, separator, suffix = value.rpartition(" | ")
    if separator and suffix.strip().upper() in {
        "DOMESTICA",
        "DOMÉSTICA",
        "DOMESTIC",
        "EXPORTACAO",
        "EXPORTAÇÃO",
        "EXPORT",
    }:
        return base.strip()
    return value.strip()


def _route_key(flow: dict[str, Any], route_type: str) -> str:
    if route_type in {"DC", "OC"}:
        return f"{route_type}_{flow.get('customer_type', 'domestic')}"
    return route_type


def _cost_groups(costs: dict[str, Any]) -> dict[str, float]:
    return {
        group: sum(_number(costs.get(component), 0.0) for component in components)
        for group, components in COST_GROUPS.items()
    }


def _penalty_cost(run: CompletedRun) -> float:
    costs = run.result.get("cost_breakdown", {})
    return sum(_number(costs.get(name), 0.0) for name in PENALTY_COMPONENTS)


def _investment_cost(run: CompletedRun) -> float:
    costs = run.result.get("cost_breakdown", {})
    return sum(_number(costs.get(name), 0.0) for name in INVESTMENT_COMPONENTS)


def _economic_cost(run: CompletedRun) -> float:
    objective_values = run.result.get("metrics", {}).get("objective_values", {})
    value = objective_values.get("economic_cost")
    if value is not None:
        return float(value)
    return sum(_cost_groups(run.result.get("cost_breakdown", {})).values())


def _penalized_cost(run: CompletedRun) -> float:
    objective_values = run.result.get("metrics", {}).get("objective_values", {})
    value = objective_values.get("penalized_cost")
    if value is not None:
        return float(value)
    return _economic_cost(run) + _penalty_cost(run)


def _weighted_scenario_cost(run: CompletedRun) -> float:
    metrics = run.result.get("metrics", {}).get("scenario_metrics", {})
    return sum(
        _number(values.get("probability"), 0.0)
        * _number(values.get("operating_cost"), 0.0)
        for values in metrics.values()
    )


def _decision_totals(decisions: Iterable[dict[str, Any]]) -> dict[str, Any]:
    values = list(decisions)
    return {
        "candidates_opened": sum(
            _number(item.get("open"), 0.0) > 0.5 for item in values
        ),
        "candidate_capacity_thousand_tonnes": sum(
            _number(item.get("candidate_capacity"), 0.0) for item in values
        )
        / 1e3,
        "warehouses_expanded": sum(
            _number(item.get("expand"), 0.0) > 0.5 for item in values
        ),
        "expansion_capacity_thousand_tonnes": sum(
            _number(item.get("expansion_capacity"), 0.0) for item in values
        )
        / 1e3,
        "warehouses_bulkified": sum(
            _number(item.get("bulkify"), 0.0) > 0.5 for item in values
        ),
        "bulkification_capacity_tonnes_per_day": sum(
            _number(item.get("bulk_capacity"), 0.0) for item in values
        ),
    }


def _investment_status(decision: dict[str, Any]) -> str:
    opened = _number(decision.get("open"), 0.0) > 0.5
    expanded = _number(decision.get("expand"), 0.0) > 0.5
    bulkified = _number(decision.get("bulkify"), 0.0) > 0.5
    if opened:
        return "Candidate opened"
    if expanded and bulkified:
        return "Expanded and bulkified"
    if bulkified:
        return "Bulkified"
    if expanded:
        return "Expanded"
    return "Existing"


def _network_policy_label(run: CompletedRun) -> str:
    model = run.experiment.get("model", {})
    direct = (
        "Direct arcs enabled"
        if model.get("use_direct_origin_customer")
        else "Direct arcs disabled"
    )
    return f"{_route_policy_label(model)} | {direct}"


def _route_policy_label(model: dict[str, Any]) -> str:
    strategy = str(model.get("route_filter_strategy", "none"))
    if strategy == "pareto":
        fraction = 100.0 * float(model.get("pareto_fraction", 0.0))
        return f"Coverage-preserving shortest {fraction:g}% per group"
    if strategy == "top_k":
        count = int(model.get("route_top_k") or 0)
        return f"Coverage-preserving top-{count} per group"
    return "Unfiltered routes"


def _stochastic_label(run: CompletedRun) -> str:
    count = int(run.summary.get("scenario_count") or 0)
    return f"{count}-scenario stochastic design"


def _scenario_label(value: Any) -> str:
    text = str(value)
    replacements = {
        "oferta_baixo__demanda_alto": "Low supply / high demand",
        "oferta_base__demanda_base": "Base supply / base demand",
        "oferta_alto__demanda_baixo": "High supply / low demand",
        "oferta_baixo__demanda_baixo": "Low supply / low demand",
        "oferta_baixo__demanda_base": "Low supply / base demand",
        "oferta_base__demanda_baixo": "Base supply / low demand",
        "oferta_base__demanda_alto": "Base supply / high demand",
        "oferta_alto__demanda_base": "High supply / base demand",
        "oferta_alto__demanda_alto": "High supply / high demand",
    }
    return replacements.get(text, text.replace("_", " ").title())


def _plot_dependencies():
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import pandas as pd
        import seaborn as sns
    except ImportError as exc:
        raise ScientificResultsError(
            "Scientific presentation requires pip install -e '.[visualization]'."
        ) from exc
    return plt, sns, pd


def _configure_style(plt, sns) -> None:
    sns.set_theme(context="paper", style="whitegrid", palette="colorblind")
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.titleweight": "bold",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "legend.frameon": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def _write_csv(path: Path, frame: Any) -> None:
    frame.to_csv(path, index=False, lineterminator="\n", float_format="%.12g")


def _write_markdown(path: Path, frame: Any, title: str) -> None:
    display = frame.copy()
    for column in display.select_dtypes(include="number"):
        display[column] = display[column].map(
            lambda value: "" if not math.isfinite(float(value)) else f"{value:.4g}"
        )
    labels = (_reader_label(column) for column in display.columns)
    header = "| " + " | ".join(labels) + " |"
    separator = "| " + " | ".join("---" for _ in display.columns) + " |"
    rows = [
        "| "
        + " | ".join(_markdown_cell(row[column]) for column in display.columns)
        + " |"
        for row in display.to_dict("records")
    ]
    path.write_text(
        "\n".join([f"# {title}", "", header, separator, *rows, ""]),
        encoding="utf-8",
        newline="",
    )


def _reader_label(value: Any) -> str:
    text = str(value)
    exact = {
        "dyn_cap_million_tonnes_per_year": (
            "DynCap (10^6 tonnes per annual equivalent)"
        ),
        "evpi_million": "EVPI (10^6 model monetary units)",
        "vss_billion": "VSS (10^9 model monetary units)",
        "turnover_cycles_per_year": "Turnover (cycles per year)",
        "runtime_seconds": "Runtime (seconds)",
        "peak_rss_mb": "Peak RSS (MiB)",
        "bulkification_capacity_tonnes_per_day": (
            "Bulkification capacity (tonnes per day)"
        ),
        "emergency_static_tonne_periods": (
            "Emergency static capacity (tonne-periods)"
        ),
        "emergency_reception_tonne_per_day_periods": (
            "Emergency reception capacity (tonnes per day-period)"
        ),
        "emergency_capacity_tonnes_over_periods": (
            "Emergency capacity (reported native units over periods)"
        ),
    }
    if text in exact:
        return exact[text]
    suffixes = {
        "_billion": " (10^9 model monetary units)",
        "_thousand_tonnes": " (10^3 tonnes)",
        "_percent": " (%)",
    }
    unit = ""
    for suffix, label in suffixes.items():
        if text.endswith(suffix):
            text = text.removesuffix(suffix)
            unit = label
            break
    replacements = {
        "dyn": "Dyn",
        "cap": "Cap",
        "evpi": "EVPI",
        "vss": "VSS",
        "rss": "RSS",
        "dd": "DD",
        "dc": "DC",
        "oc": "OC",
        "od": "OD",
    }
    words = text.split("_")
    label = " ".join(replacements.get(word, word.title()) for word in words)
    return label + unit


def _markdown_cell(value: Any) -> str:
    try:
        if value != value:
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).replace("|", "\\|").replace("\n", " ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ScientificResultsError(f"Required JSON artifact not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ScientificResultsError(f"Expected a JSON object: {path}")
    return payload


def _read_optional_json(path: Path) -> dict[str, Any]:
    return _read_json(path) if path.is_file() else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _number(value: Any, default: float | None = None) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        if default is None:
            raise
        return default
    if math.isfinite(result):
        return result
    if default is None:
        raise ValueError(f"Expected a finite number, received {value!r}.")
    return default

