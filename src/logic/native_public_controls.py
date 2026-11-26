"""Literal public software controls; no private input, native import or execution."""

from dataclasses import asdict

from src.logic.effective_baseline import effective_projection, identity, seal
from src.logic.model_config import ModelConfig, SolverConfig
from src.logic.model_data import ModelData
from src.logic.parametric_scenarios import ParameterScenario, apply_scenario


class PublicNativeConfig(SolverConfig):
    """Distinct bounded software profile, accepted only for exact public fixtures."""


def public_solver_config():
    return PublicNativeConfig(
        time_limit=60, threads=0, mip_gap=None, seed=None, tee=False,
        solver_options={"Method": -1},
    )


def check_native_environment(config, environment):
    if isinstance(config, PublicNativeConfig) != (environment is not None):
        raise ValueError("An owned environment is required only for public native qualification.")


def control_specs():
    policies = [
        (None, None), (0.9, None), (0.95, None), (None, 0.6), (None, 0.5),
        (0.9, 0.6), (0.9, 0.5), (0.95, 0.6), (0.95, 0.5), (1, 0), (0, 0),
    ]
    result = []
    for mode in ("det", "sto"):
        entries = [(f"policy-{i}", "existing", 1, b, a) for i, (b, a) in enumerate(policies)]
        entries += [(f"{kind}-K{k}", kind, k, 1, 0)
                    for kind in ("candidate", "expansion") for k in (1, 2)]
        entries += [("blocked-shipping", "blocked", 1, 0.9, None)]
        for label, kind, k, beta, alpha in entries:
            result.append({"id": f"public-native-{mode}-{label}", "mode": mode,
                           "kind": kind, "K": k, "beta": beta, "alpha": alpha})
    return result


def make_control(control_id):
    spec = next((s for s in control_specs() if s["id"] == control_id), None)
    if spec is None:
        raise ValueError("Unknown public native control.")
    kind, mode = spec["kind"], spec["mode"]
    candidate = kind == "candidate"
    investing = kind in {"candidate", "expansion"}
    data = ModelData(
        origins=["O"], warehouses=["W"], existing_warehouses=[] if candidate else ["W"],
        candidate_warehouses=["W"] if candidate else [], bulk_eligible_warehouses=[],
        customers=["C", "X"], domestic_customers=["C"], export_customers=["X"],
        products=["P"], periods=["t"],
        routes_od={("O", "W", "P")}, routes_dc={("W", "C", "P"), ("W", "X", "P")},
        supply={("O", "P", "t"): 10}, demand_dom={("C", "P", "t"): 10},
        demand_exp={("X", "P", "t"): 10}, dist_od={("O", "W"): 3},
        dist_dc={("W", "C"): 1000, ("W", "X"): 4},
        freight_origin={"O": 3}, freight_warehouse={"W": 2},
        storage_tariff={("W", "P"): 2},
        static_capacity={"W": 6 if kind == "expansion" else 0},
        reception_capacity={"W": 0 if investing else 10},
        shipping_capacity={"W": 0 if investing or kind == "blocked" else 10},
        max_candidate_capacity={"W": 1.5} if candidate else {},
        opening_fixed_cost={"W": 0} if candidate else {},
        candidate_capacity_cost={"W": 1250} if candidate else {},
        max_expand_capacity={"W": 1.5} if kind == "expansion" else {},
        expand_fixed_cost={"W": 0} if kind == "expansion" else {},
        expand_variable_cost={"W": 900} if kind == "expansion" else {},
        unmet_demand_penalty={("C", "P"): 1000},
        emergency_static_capacity_penalty={"W": 2000},
        emergency_reception_capacity_penalty={"W": 3000},
    )
    cfg = ModelConfig(mode=mode)
    if mode == "sto":
        data.scenarios = [f"s{i}" for i in range(9)]
        data.scenario_prob = dict.fromkeys(data.scenarios, 1 / 9)
        for field in ("supply", "demand_dom", "demand_exp"):
            setattr(data, field + "_s", {
                (s, *key): value * (0.5 + i / 8) for i, s in enumerate(data.scenarios)
                for key, value in getattr(data, field).items()
            })
    data = seal(effective_projection(data, cfg), cfg, {"scenario_id": "baseline"})
    changed, _ = apply_scenario(data, cfg, ParameterScenario(
        spec["id"], {"candidate_limit": spec["K"], "expansion_limit": spec["K"]},
        beta=spec["beta"], alpha=spec["alpha"],
        justification="Literal public native software control; no agricultural observation.",
    ))
    changed.metadata["public_native_control"] = spec["id"]
    return changed, cfg


def verify_public_control(data, cfg):
    """A public budget cannot be used for arbitrary sealed or private input."""
    control_id = data.metadata.get("public_native_control")
    expected, expected_cfg = make_control(control_id)
    if (asdict(cfg) != asdict(expected_cfg)
            or identity(data, cfg) != identity(expected, expected_cfg)
            or data.metadata != expected.metadata):
        raise ValueError("Public native control differs from its literal source fixture.")


def expected(control):
    investing = control["kind"] in {"candidate", "expansion"}
    if control["kind"] == "blocked" or (investing and control["K"] == 1):
        return {"classification": "infeasible", "objective": None}
    # Mean scenario supply is 10 t, maximum is 15 t. Shipping is 6 t per
    # installed investment-tonne/month. The shared investment is charged once.
    export = min(10, 10 * (1-control["beta"]) if control["beta"] is not None else 10,
                 10 * control["alpha"] if control["alpha"] is not None else 10)
    installed = (15 if control["mode"] == "sto" else 10) / 6 if investing else 0
    unit = 1250 if control["kind"] == "candidate" else 900
    return {"classification": "optimal", "objective": 20090 - 992 * export + installed * unit,
            "expected_export_t": export, "expected_served_t": 10-export,
            "installed_t": installed}
