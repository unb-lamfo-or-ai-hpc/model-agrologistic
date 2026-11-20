"""Independently compare local derived registry cells with the original source."""

from __future__ import annotations

import argparse
import gc
import io
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.logic.effective_baseline import dump, identity, load_bundle, sha256  # noqa: E402


def check(args):
    import openpyxl
    import pandas as pd

    with zipfile.ZipFile(args.archive) as archive:
        original = pd.read_excel(
            io.BytesIO(archive.read("external-inputs/Warehouses_Existing_Candidate_All.xlsx")),
            sheet_name="Sheet1",
            keep_default_na=False,
        )
    wb = openpyxl.load_workbook(args.registry, read_only=True, data_only=True)
    values = iter(wb["Registry"].values)
    header = next(values)
    rows = [dict(zip(header, row, strict=True)) for row in values]
    wb.close()
    if len(rows) != 18086 or [r["CDA"] for r in rows] != list(original["CDA"]):
        raise ValueError("Registry CDA cardinality/order differs.")
    originals = original.to_dict(orient="records")
    for expected, observed in zip(originals, rows, strict=True):
        for column, value in expected.items():
            actual = observed[column]
            if (value is None or value == "") and (actual is None or actual == ""):
                continue
            if value != actual:
                raise ValueError(f"Original registry cell changed: {column}, CDA {expected['CDA']}")
    lookup = {row["CDA"]: row for row in rows}
    populations, cases = {}, {}
    manifest = json.loads((Path(args.bundle) / "manifest.json").read_text(encoding="utf-8"))
    for scope in manifest["cases"]:
        n, mode = scope.split(":")
        data, cfg = load_bundle(args.bundle, int(n), mode)
        cases[scope] = identity(data, cfg)
        if mode != "sto":
            del data
            gc.collect()
            continue
        selected = [r for r in rows if r[f"Em_h{n}"] == 1]
        ordered = sorted(selected, key=lambda r: r[f"order_h{n}"])
        if [r["CDA"] for r in ordered] != data.warehouses:
            raise ValueError("Derived membership/order differs from the frozen baseline.")
        if any(r[f"Em_h{n}"] not in (0, 1) for r in rows):
            raise ValueError("Membership flags are not binary.")
        for cda in data.candidate_warehouses:
            if any(
                lookup[cda][name] != 0
                for name in ("model_K0_t", "model_R0_t_day", "model_H0_t_day")
            ):
                raise ValueError("A selected candidate has nonzero modeled initial capacity.")
            if lookup[cda]["candidate_limit_t"] != data.max_candidate_capacity[cda]:
                raise ValueError("The candidate investible limit differs from its baseline.")
        source_capacity_differences = sum(
            lookup[cda]["Cap. Estática (t)"] != data.max_candidate_capacity[cda]
            for cda in data.candidate_warehouses
        )
        populations[n] = {
            "total": len(data.warehouses),
            "existing": len(data.existing_warehouses),
            "candidates": len(data.candidate_warehouses),
            "source_capacity_limit_differences": source_capacity_differences,
            "membership_order_match": True,
        }
        del data
        gc.collect()
    report = {
        "status": "accepted_derived_registry_and_bundle",
        "original_registry_rows": 18086,
        "original_registry_values_preserved": True,
        "populations": populations,
        "effective_cases": cases,
        "registry_xlsx_sha256": sha256(args.registry),
        "bundle_manifest_sha256": sha256(Path(args.bundle) / "manifest.json"),
        "solver_calls": 0,
        "comparison": "Cell values with empty/null equivalence; not XLSX ZIP bytes",
    }
    dump(args.output, report)
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--output", required=True)
    check(parser.parse_args())
