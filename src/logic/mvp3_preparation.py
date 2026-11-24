"""Proposed staged T3 identities and canonical native-policy row specifications.

Preparation only: no Gurobi import, model allocation, optimizer or scheduler.
The row interface is not a qualified native execution adapter.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from math import fsum
from pathlib import Path

from src.logic.mathematical_contract import canonical_hash
from src.logic.parametric_scenarios import (
    ParameterScenario,
    resolve_policy,
    verify_scenario_record,
)

PROTOCOL = (
    Path(__file__).resolve().parents[2]
    / "experiments/proposals/mvp3_t3_staged_design_20261124.json"
)


def read_protocol():
    record = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if record["execution_authorized"] is not False:
        raise ValueError("This preparation source cannot admit execution.")
    if record["status"] != "proposed_pending_researcher_approval":
        raise ValueError("The staged design remains a proposal, not an official-plan replacement.")
    if record["native_options"] != {"Method": -1, "Threads": 0, "TimeLimit": 28800}:
        raise ValueError("The approved automatic reference profile differs.")
    return record


def case_catalog():
    """One complete DET or joint nine-scenario STO case per observation."""
    protocol = read_protocol()
    result = []
    for stage, design in protocol["stages"].items():
        population = design["population"]
        for mode in protocol["modes"]:
            for profile in design["profiles"]:
                for k in design["K_levels"]:
                    repetitions = range(1, protocol["repetition_proposal"]["total_repetitions"] + 1)
                    for repetition in repetitions:
                        spec = {
                            "id": (
                                f"h{population}-{mode}-{profile}-K{int(k * 100)}-AUTO-r{repetition}"
                            ),
                            "population": int(population),
                            "mode": mode,
                            "topology": "W",
                            "profile": profile,
                            "stage": stage,
                            "K": k,
                            "repetition": repetition,
                            **protocol["profiles"][profile],
                            "implementation": "native_gurobipy",
                            "gurobi_version": "14.0.0",
                            "protocol_sha256": canonical_hash(protocol),
                            "workbook_sha256": {
                                role: value["sha256"]
                                for role, value in protocol["workbooks"].items()
                            },
                            "reference_input_sha256": protocol["h215_input_identities"][mode],
                            "input_qualification": "v2_neutral_identity_retained",
                            "scientific_approval": "pending",
                            "execution_authorized": False,
                            "job_id": None,
                            "status": "proposed_no_job",
                        }
                        spec["case_sha256"] = canonical_hash(spec)
                        result.append(spec)
    if len(result) != 24 or sum(r["repetition"] == 1 for r in result) != 24:
        raise ValueError("The proposed case and repetition counts differ.")
    return result


def case_scenario(case):
    """K maps only to existing bound multipliers; physical tonne prices stay fixed."""
    expected = next((c for c in case_catalog() if c["id"] == case.get("id")), None)
    if expected is None or case != expected:
        raise ValueError("Case differs from the source-bound proposed catalog.")
    return ParameterScenario(
        case["id"],
        multipliers={"candidate_limit": case["K"], "expansion_limit": case["K"]},
        beta=case["beta"],
        alpha=case["alpha"],
        justification=(
            "Proposed staged T3 design; scientific approval pending; software checks only."
        ),
    )


@dataclass(frozen=True)
class HorizonPolicyRow:
    control: str
    scenario: str
    product: str
    variable_family: str
    terms: tuple[tuple[str, ...], ...]
    upper_tonnes: float


def native_policy_rows(data, config):
    """Canonical unweighted rows for a future adapter on the retained native model.

    DET uses a canonical 'deterministic' prefix. A native adapter must explicitly
    map that prefix to its DET keys. Construction and validation remain separate.
    """
    if config.use_direct_origin_customer or not config.use_warehouse_transshipment:
        raise ValueError("MVP3 preparation requires the approved W topology.")
    verify_scenario_record(data, config)
    spec = data.metadata["effective_baseline"].get("specification", {})
    policies = {name: resolve_policy(spec.get(name), data, config) for name in ("beta", "alpha")}
    rows = []
    for (s, p), fraction in policies["beta"].items():
        demand = fsum(
            data.demand_dom_s[s, c, p, t] if config.mode == "sto" else data.demand_dom[c, p, t]
            for c in data.domestic_customers
            for t in data.periods
        )
        terms = tuple((s, c, p, t) for c in data.domestic_customers for t in data.periods)
        rows.append(HorizonPolicyRow("beta", s, p, "unmet", terms, (1 - fraction) * demand))
    for (s, p), fraction in policies["alpha"].items():
        supply = fsum(
            data.supply_s[s, o, p, t] if config.mode == "sto" else data.supply[o, p, t]
            for o in data.origins
            for t in data.periods
        )
        terms = tuple(
            (s, w, c, p, t)
            for w, c, product in sorted(data.routes_dc)
            if product == p and c in data.export_customers
            for t in data.periods
        )
        rows.append(HorizonPolicyRow("alpha", s, p, "DC", terms, fraction * supply))
    return tuple(rows)
