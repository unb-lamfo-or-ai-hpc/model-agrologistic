"""Read-only S1 checks on frozen v2 inputs; no native model, license or scheduler."""

from __future__ import annotations

import argparse
import gc
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def check(args):
    from scripts.no_solver_guard import NoSolverGuard

    platform.uname()
    guard = NoSolverGuard()
    guard.install()
    from scripts.prepare_mvp3_t3 import inspect_inputs
    from src.logic.effective_baseline import MAP_FIELDS, identity, load_bundle
    from src.logic.mvp3_preparation import case_catalog, case_scenario
    from src.logic.native_effective import prepare_effective_native, reference_solver_config
    from src.logic.parametric_scenarios import apply_scenario, source_identity

    preflight = inspect_inputs(args.baseline, args.registry, args.bundle)
    before_source = source_identity()
    records = []
    for mode in ("det", "sto"):
        data, cfg = load_bundle(args.bundle, 215, mode)
        original_identity = identity(data, cfg)
        for case in (c for c in case_catalog() if c["mode"] == mode):
            changed, audit = apply_scenario(data, cfg, case_scenario(case))
            context = prepare_effective_native(changed, cfg, reference_solver_config())
            for field in MAP_FIELDS:
                if field in {"max_candidate_capacity", "max_expand_capacity"}:
                    expected = {k: v * case["K"] for k, v in getattr(data, field).items()}
                else:
                    expected = getattr(data, field)
                if getattr(changed, field) != expected:
                    raise ValueError(f"Unexpected transformation: {case['id']}/{field}")
            pairs = len(data.products) * (len(data.scenarios) if mode == "sto" else 1)
            counts = {control: sum(r.control == control for r in context.rows)
                      for control in ("beta", "alpha")}
            if any(counts[name] != (pairs if case[name] is not None else 0) for name in counts):
                raise ValueError("Native policy row indexing/count differs.")
            if case["K"] == 1 and identity(changed, cfg) != original_identity:
                raise ValueError("K=1 changed effective algebra inputs.")
            records.append({
                "case_id": case["id"], "case_sha256": case["case_sha256"],
                "mode": mode, "K": case["K"], "policy_rows": counts,
                "input_sha256": changed.metadata["effective_baseline"]["input_sha256"],
                "scenario_sha256": audit["scenario_sha256"],
                "native_embedding_input_sha256": context.native_input_sha256,
                "K_once_and_other_parameter_maps_unchanged": True,
            })
            print("Verified native input assembly: " + case["id"], flush=True)
            del context, changed, audit
            gc.collect()
        if identity(data, cfg) != original_identity:
            raise ValueError("Original baseline changed during S1 inspection.")
        del data
        gc.collect()
    after = inspect_inputs(args.baseline, args.registry, args.bundle)
    if preflight != after or before_source != source_identity() or guard.blocked:
        raise ValueError("Source/input drift or forbidden execution during local S1 checks.")
    report = {
        "schema": "agrologistic-mvp3-s1-local-input-check-v1", "status": "accepted",
        "preflight": preflight, "source_sha256": before_source, "cases": records,
        "originals_unchanged": True, "source_consistency_certified": False,
        "native_model_or_license_opened": False, "optimizer_calls": 0,
        "forbidden_execution_attempts": guard.execution_blocks,
        "native_import_attempts": guard.import_blocks, "new_jobs": 0,
        "full_native_matrix_qualified": False, "execution_authorized": False,
        "scope": "Real frozen h215 data/scenario/native-row assembly; not a native solve",
    }
    output = Path(args.output)
    with output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in {"cases", "preflight"}}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline", "registry", "bundle", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    check(parser.parse_args())


if __name__ == "__main__":
    main()
