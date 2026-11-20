"""Explicit W sensitivities over frozen effective values; no solver execution."""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

from src.logic.effective_baseline import UNITS, identity, numeric, seal, sha256, validate
from src.logic.mathematical_contract import canonical_hash

MULTIPLIERS = {
    "existing_static": ("static_capacity",),
    "existing_reception": ("reception_capacity",),
    "existing_shipping": ("shipping_capacity",),
    "candidate_limit": ("max_candidate_capacity",),
    "expansion_limit": ("max_expand_capacity",),
    "bulk_limit": ("max_bulk_capacity",),
    "freight": ("freight_origin", "freight_dest", "freight_warehouse"),
    "opening_variable": ("candidate_capacity_cost",),
    "expansion_variable": ("expand_variable_cost",),
    "bulk_variable": ("bulk_variable_cost",),
    "storage": ("storage_tariff",),
    "shortage_penalty": ("unmet_demand_penalty",),
    "stock_penalty": ("emergency_static_capacity_penalty",),
    "reception_penalty": ("emergency_reception_capacity_penalty",),
    "delta_D": ("demand_dom", "demand_dom_s"),
}
FIXED_FIELDS = {"opening_fixed_cost", "expand_fixed_cost", "bulk_fixed_cost"}
NEUTRAL_JUSTIFICATION = "Neutral baseline; no experimental levels selected."


def policy_value(value):
    """Validate an approved fraction or complete product/scenario nested map."""
    if value is None:
        return
    if isinstance(value, dict):
        if not value:
            raise ValueError("An indexed policy cannot be empty.")
        for product, scenarios in value.items():
            if not isinstance(product, str) or not product or not isinstance(scenarios, dict):
                raise ValueError("Policy indices must be product/scenario maps.")
            if not scenarios or any(not isinstance(s, str) or not s for s in scenarios):
                raise ValueError("Policy scenario indices must be nonempty strings.")
            for fraction in scenarios.values():
                if not isinstance(fraction, (int, float)):
                    raise ValueError("Policy fractions must be numerical values.")
                if numeric(fraction) > 1:
                    raise ValueError("Policy fractions must be between zero and one.")
    else:
        if not isinstance(value, (int, float)):
            raise ValueError("Policy fractions must be numerical values.")
        if numeric(value) > 1:
            raise ValueError("Policy fractions must be between zero and one.")


def resolve_policy(value, data, config):
    policy_value(value)
    if value is None:
        return {}
    scenarios = data.scenarios if config.mode == "sto" else ["deterministic"]
    if isinstance(value, dict) and (
        set(value) != set(data.products)
        or any(set(value[p]) != set(scenarios) for p in data.products)
    ):
        raise ValueError("Indexed policies must cover every product/scenario exactly.")
    return {
        (s, p): numeric(value[p][s] if isinstance(value, dict) else value)
        for s in scenarios
        for p in data.products
    }


@dataclass(frozen=True)
class ParameterScenario:
    scenario_id: str
    multipliers: dict[str, float] = field(default_factory=dict)
    fixed_absolute: dict[str, float | None] = field(default_factory=dict)
    beta: float | dict[str, dict[str, float]] | None = None
    alpha: float | dict[str, dict[str, float]] | None = None
    justification: str = NEUTRAL_JUSTIFICATION

    def __post_init__(self):
        if not self.scenario_id or not self.justification:
            raise ValueError("An identified, justified scenario is required.")
        if self.scenario_id == "baseline" and (
            any(v != 1 for v in self.multipliers.values())
            or self.beta is not None
            or self.alpha is not None
        ):
            raise ValueError("A non-neutral transformation cannot be named baseline.")
        if set(self.multipliers) - MULTIPLIERS.keys():
            raise ValueError("Unknown multiplier; undeclared transformations are forbidden.")
        for value in self.multipliers.values():
            numeric(value)
        if set(self.fixed_absolute) - FIXED_FIELDS:
            raise ValueError("Unknown fixed-cost field.")
        for value in self.fixed_absolute.values():
            if value is not None and numeric(value) != 0:
                raise ValueError("Positive absolute fixed costs await scientific authorization.")
        policy_value(self.beta)
        policy_value(self.alpha)
        changed = (
            any(v != 1 for v in self.multipliers.values())
            or any(v is not None for v in self.fixed_absolute.values())
            or self.beta is not None
            or self.alpha is not None
        )
        if changed and self.justification == NEUTRAL_JUSTIFICATION:
            raise ValueError("Non-neutral controls require an explicit scientific justification.")


def source_identity():
    """Bind all implementation modules, including the reused algebra and validator."""
    root = Path(__file__).resolve().parent
    return canonical_hash({p.name: sha256(p) for p in sorted(root.glob("*.py"))})


def apply_scenario(data, config, scenario):
    # Revalidate copies: frozen dataclasses can still contain mutable dictionaries.
    scenario = ParameterScenario(**asdict(scenario))
    baseline = validate(data, config)
    if baseline != data.metadata.get("effective_baseline", {}).get("input_sha256"):
        raise ValueError("The baseline was changed outside the declared scenario interface.")
    if data.metadata["effective_baseline"].get("scenario_id") != "baseline":
        raise ValueError(
            "Apply each scenario to the immutable baseline, never to another scenario."
        )
    changes, audit = {}, []
    for parameter, factor in scenario.multipliers.items():
        factor = numeric(factor)
        for name in MULTIPLIERS[parameter]:
            original = getattr(data, name)
            updated = dict(original)
            for key, old in original.items():
                if parameter.startswith("existing_") and key not in data.existing_warehouses:
                    continue
                value = numeric(old * factor)
                updated[key] = value
                if value != old:
                    audit.append(
                        {
                            "parameter": parameter,
                            "field": name,
                            "key": key,
                            "before": old,
                            "after": value,
                            "unit": UNITS[name],
                            "transformation": "baseline_value * multiplier",
                        }
                    )
            changes[name] = updated
    for name, value in scenario.fixed_absolute.items():
        if value is None:
            continue
        changes[name] = dict.fromkeys(getattr(data, name), numeric(value))
        for key, old in getattr(data, name).items():
            if old != value:
                audit.append(
                    {
                        "parameter": name,
                        "field": name,
                        "key": key,
                        "before": old,
                        "after": value,
                        "unit": UNITS[name],
                        "transformation": "absolute override",
                    }
                )
    changed = replace(copy.deepcopy(data), **changes)
    resolve_policy(scenario.beta, changed, config)
    resolve_policy(scenario.alpha, changed, config)
    code = source_identity()
    record = {
        "baseline_sha256": baseline,
        "baseline_bundle_sha256": data.metadata["effective_baseline"].get("bundle_manifest_sha256"),
        "source_identities": copy.deepcopy(
            data.metadata["effective_baseline"].get("source_identities", {})
        ),
        "scenario_id": scenario.scenario_id,
        "specification": asdict(scenario),
        "source_sha256": code,
        "changes": audit,
        "origin_class": "synthetic_counterfactual_parameter",
        "usage_class": "experimental_scenario",
        "changes_sha256": canonical_hash(audit),
        "physical_coupling": (
            "unchanged daily_factors; realized investments remain optimizer decisions"
        ),
        "derived_slack_bounds": "recompute from scenario data in the unchanged builder",
    }
    record["scenario_sha256"] = canonical_hash(
        {
            "baseline": baseline,
            "baseline_bundle": record["baseline_bundle_sha256"],
            "specification": asdict(scenario),
            "source": code,
            "effective_inputs": identity(changed, config),
        }
    )
    return seal(changed, config, record), record


def verify_scenario_record(data, config):
    """Bind optional constraints to the sealed inputs and reviewed specification."""
    record = data.metadata.get("effective_baseline", {})
    if "specification" not in record:
        if record.get("scenario_id") != "baseline":
            raise ValueError("Missing effective scenario specification.")
        return {"beta": {}, "alpha": {}}
    spec = ParameterScenario(**copy.deepcopy(record["specification"]))
    expected = canonical_hash(
        {
            "baseline": record["baseline_sha256"],
            "baseline_bundle": record.get("baseline_bundle_sha256"),
            "specification": asdict(spec),
            "source": record["source_sha256"],
            "effective_inputs": identity(data, config),
        }
    )
    if (
        record.get("scenario_sha256") != expected
        or record.get("scenario_id") != spec.scenario_id
        or record.get("source_sha256") != source_identity()
    ):
        raise ValueError("Effective scenario specification/source identity changed after sealing.")
    return {name: resolve_policy(getattr(spec, name), data, config) for name in ("beta", "alpha")}
