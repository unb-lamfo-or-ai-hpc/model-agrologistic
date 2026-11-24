"""Read approved workbook controls into the existing ParameterScenario interface.

K is a view over two established bound multipliers, never a new model variable.
"""

from __future__ import annotations

import math

FIELDS = {"scenario_id", "K", "beta_enabled", "beta", "alpha_enabled", "alpha", "justification"}
DERIVED = {"existing_expansion_fraction", "capacity_semantics"}


def specification(rows):
    """Validate flat Controls rows; reject hidden, ambiguous or repeated scaling."""
    values = {}
    for row in rows:
        name, value = row[:2]
        if name is None:
            continue
        if name in values:
            raise ValueError("Duplicate control: " + name)
        if name not in FIELDS | DERIVED:
            raise ValueError("Unknown control: " + str(name))
        values[name] = value
    if not FIELDS <= values.keys():
        raise ValueError("Incomplete approved controls.")
    k = values["K"]
    if isinstance(k, bool) or not isinstance(k, (int, float)) or not math.isfinite(k) or k <= 0:
        raise ValueError("K must be a finite positive multiplier.")
    result = {
        "scenario_id": values["scenario_id"],
        "multipliers": {"candidate_limit": k, "expansion_limit": k},
        "beta": None,
        "alpha": None,
        "justification": values["justification"],
    }
    for name in ("beta", "alpha"):
        enabled = values[name + "_enabled"]
        if isinstance(enabled, bool) or enabled not in (0, 1):
            raise ValueError(name + "_enabled must be numeric 0 or 1.")
        value = values[name]
        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not 0 <= value <= 1
        ):
            raise ValueError(name + " must be a fraction in [0,1] or blank when disabled.")
        if enabled:
            if value is None:
                raise ValueError("Enabled " + name + " requires a fraction.")
            result[name] = value
    if not isinstance(result["scenario_id"], str) or not result["scenario_id"].strip():
        raise ValueError("A scenario identifier is required.")
    if not isinstance(result["justification"], str) or not result["justification"].strip():
        raise ValueError("A scientific justification is required.")
    if result["scenario_id"] == "baseline" and (
        k != 1 or result["alpha"] is not None or result["beta"] is not None
    ):
        raise ValueError("A non-neutral case requires its own scenario identifier.")
    return result


def read_specification(workbook):
    import openpyxl

    wb = openpyxl.load_workbook(workbook, read_only=True, data_only=True)
    try:
        identification = dict(list(wb["Identification"].values)[1:])
        if (
            identification.get("workbook_version") != 2
            or identification.get("schema") != "agrologistic-effective-baseline-v1"
        ):
            raise ValueError("Expected the approved version-two workbook view.")
        rows = iter(wb["Controls"].values)
        if list(next(rows)) != ["parameter", "value", "unit", "meaning", "reference"]:
            raise ValueError("Unexpected Controls schema.")
        return specification(rows)
    finally:
        wb.close()


def scenario_from_workbook(workbook):
    from src.logic.parametric_scenarios import ParameterScenario

    return ParameterScenario(**read_specification(workbook))
