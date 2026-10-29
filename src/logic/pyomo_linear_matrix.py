"""Ordered linear Pyomo matrix identity; no solver or rounded coefficient export."""

import hashlib
import json
from math import isfinite


def number(value):
    """Encode finite binary64 values exactly; None denotes an absent bound."""
    if value is None:
        return None
    value = float(value)
    if not isfinite(value):
        raise ValueError("Nonfinite linear coefficient or explicit bound.")
    return value.hex()


def representation(expression, index):
    from pyomo.repn import generate_standard_repn

    rep = generate_standard_repn(expression, compute_values=True)
    if not rep.is_linear():
        raise ValueError("Only a linear Pyomo matrix is qualified.")
    terms = sorted(
        (index[id(var)], float(coef))
        for var, coef in zip(rep.linear_vars, rep.linear_coefs, strict=True)
        if coef != 0
    )
    number(rep.constant or 0)
    for _, coef in terms:
        number(coef)
    return float(rep.constant or 0), terms


def matrix_identity(model):
    """Hash one row at a time; retain no second complete coefficient matrix."""
    import pyomo.environ as pyo

    for kind in (pyo.SOSConstraint, pyo.LogicalConstraint):
        if next(model.component_data_objects(kind, active=True), None) is not None:
            raise ValueError("Only an already linearized Pyomo model is qualified.")
    digest = hashlib.sha256()

    def emit(record):
        digest.update(json.dumps(record, separators=(",", ":"), ensure_ascii=True).encode())
        digest.update(b"\n")

    variables = list(model.component_data_objects(pyo.Var, active=True))
    index = {id(var): i for i, var in enumerate(variables)}
    emit(["ordered-pyomo-linear-matrix-v1"])
    binaries = 0
    for i, var in enumerate(variables):
        kind = "binary" if var.is_binary() else "integer" if var.is_integer() else "continuous"
        binaries += var.is_binary()
        emit(["var", i, var.name, kind, number(var.lb), number(var.ub), var.fixed])
        if var.fixed:
            emit(["fixed_value", number(pyo.value(var))])
    objectives = list(model.component_data_objects(pyo.Objective, active=True))
    if len(objectives) != 1 or objectives[0].sense != pyo.minimize:
        raise ValueError("One minimization objective required.")
    constant, terms = representation(objectives[0].expr, index)
    emit(["objective", number(constant), [[i, number(c)] for i, c in terms]])
    rows, nonzeros = 0, 0
    for row in model.component_data_objects(pyo.Constraint, active=True):
        constant, terms = representation(row.body, index)
        emit(["row", rows, row.name, number(row.lower), number(row.upper), number(constant)])
        emit([[i, number(c)] for i, c in terms])
        rows += 1
        nonzeros += len(terms)
    return {
        "schema_version": "ordered-pyomo-linear-matrix-v1",
        "sha256": digest.hexdigest(), "variables": len(variables),
        "binary_variables": binaries, "linear_constraints": rows, "nonzeros": nonzeros,
        "scope": "Ordered common Pyomo algebra; not a presolved/native matrix fingerprint.",
    }
