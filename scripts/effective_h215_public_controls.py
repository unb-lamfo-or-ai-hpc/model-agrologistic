"""Public analytical controls, never historical input or performance observations."""

from dataclasses import replace

from src.logic.effective_baseline import effective_projection, seal
from src.logic.parametric_scenarios import ParameterScenario, apply_scenario
from tests.test_effective_policy import export_data


def control_specs():
    policies = [
        (None, None),
        (0.9, None),
        (0.95, None),
        (None, 0.6),
        (None, 0.5),
        (0.9, 0.6),
        (0.9, 0.5),
        (0.95, 0.6),
        (0.95, 0.5),
    ]
    controls = []
    for mode in ("det", "sto"):
        for threads in (1, 4):
            for index, (beta, alpha) in enumerate(policies):
                controls.append(
                    {
                        "id": f"{mode}-t{threads}-policy-{index}",
                        "mode": mode,
                        "threads": threads,
                        "kind": "policy",
                        "beta": beta,
                        "alpha": alpha,
                    }
                )
            for kind, beta, alpha in (
                ("endpoint", 1, 0),
                ("candidate", None, None),
                ("infeasible", 0.9, None),
            ):
                controls.append(
                    {
                        "id": f"{mode}-t{threads}-{kind}",
                        "mode": mode,
                        "threads": threads,
                        "kind": kind,
                        "beta": beta,
                        "alpha": alpha,
                    }
                )
    return controls


def make_control(control):
    # Reuse the existing public fixture. These literal analytical cost changes
    # make both policy mechanisms observable; they are not h215 coefficients.
    data, cfg = export_data(control["mode"])
    data.dist_dc["W", "C"] = 1000
    data.static_capacity["W"] = 0
    if control["kind"] == "infeasible":
        data.shipping_capacity["W"] = 0
    if control["kind"] == "candidate":
        data.existing_warehouses = []
        data.candidate_warehouses = ["W"]
        data.reception_capacity["W"] = data.shipping_capacity["W"] = 0
        data.max_candidate_capacity["W"] = 2
        data.opening_fixed_cost["W"] = 0
        data.candidate_capacity_cost["W"] = 1
        cfg = replace(cfg, candidate_capacity_mode="scalable")
    for name in ("effective_baseline", "mathematical_contract", "_frozen_routes"):
        data.metadata.pop(name, None)
    data = seal(effective_projection(data, cfg), cfg, {"scenario_id": "baseline"})
    changed, audit = apply_scenario(
        data,
        cfg,
        ParameterScenario(
            control["id"],
            beta=control["beta"],
            alpha=control["alpha"],
            justification="Public analytical software control; not an experimental dataset.",
        ),
    )
    return changed, cfg, audit


def expected(control):
    if control["kind"] == "infeasible":
        return {"classification": "infeasible", "objective": None}
    exported = min(
        10,
        10 * (1 - control["beta"]) if control["beta"] is not None else 10,
        10 * control["alpha"] if control["alpha"] is not None else 10,
    )
    # Per-tonne choice: domestic costs 2000; export costs 8 plus shortage 1000;
    # stock costs 2+2000 plus shortage 1000. Origin receipt costs 90 in total.
    # First-stage candidate investment, when enabled, is charged ONCE.
    investment = 10 / 6 if control["kind"] == "candidate" else 0
    return {
        "classification": "optimal",
        "objective": 20090 - 992 * exported + investment,
        "export_t": exported,
        "served_t": 10 - exported,
        "unmet_t": exported,
        "candidate_capacity": investment,
    }
