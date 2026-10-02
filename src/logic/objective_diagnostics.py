"""Explain final incumbent drift under the Gurobi MIP multiobjective contract."""

from __future__ import annotations

import math


def stage_degradation_records(stages, final_values, *, mip_gap, mip_gap_abs, objective_abs_tol):
    """Retain pass optima and final values separately; do not claim exact lexicography.

    For a minimization MIP, the inherited base is max(incumbent,
    bound + abs(incumbent)*MIPGap, bound + MIPGapAbs). Objective tolerances
    can relax it further. This project sets ObjNRelTol=0. The base is a
    diagnostic of MIP semantics, not a certificate for an LP-only solve.
    """
    records = []
    for stage in stages:
        record = dict(stage)
        role = stage.get("stage_role", stage.get("objective_name"))
        final = final_values.get(role, final_values.get("expected_" + str(role)))
        incumbent, bound = stage.get("objective_value"), stage.get("objective_bound")
        record.update(
            final_objective_value=final,
            configured_mip_gap=mip_gap,
            configured_mip_gap_abs=mip_gap_abs,
            objective_relative_tolerance=0.0,
            objective_absolute_tolerance=objective_abs_tol,
        )
        if all(v is not None and math.isfinite(v) for v in (final, incumbent, bound)):
            base = max(incumbent, bound + abs(incumbent) * mip_gap, bound + mip_gap_abs)
            record.update(
                final_minus_pass_objective=final - incumbent,
                mip_inherited_base=base,
                mip_next_pass_limit=base + objective_abs_tol,
                within_mip_degradation_limit=(
                    final <= base + objective_abs_tol + 1e-5 + abs(base) * 1e-8
                ),
            )
        records.append(record)
    return records
