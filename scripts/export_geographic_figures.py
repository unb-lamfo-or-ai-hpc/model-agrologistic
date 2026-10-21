"""Export source-bound manuscript map definitions from read-only SQLite."""

import argparse
import json
from pathlib import Path

from src.visualization.geography import figure_definition, require

FIGURES = [
    (215, "scalar_h215_det"),
    (215, "scalar_h215_sto"),
    (300, "scalar_h300_t1"),
    (400, "scalar_h400_t1"),
    (500, "h500_pending"),
]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sqlite", type=Path, required=True)
    p.add_argument("--snapshot", required=True)
    p.add_argument("--new-source-dir", type=Path, required=True)
    a = p.parse_args(argv)
    require(not a.new_source_dir.exists(), "Preserve prior figure definitions")
    definitions = [
        figure_definition(a.sqlite, a.snapshot, population=population, case_id=case)
        for population, case in FIGURES
    ]
    a.new_source_dir.mkdir(parents=True)
    for definition in definitions:
        path = a.new_source_dir / (definition["case"] + ".json")
        path.write_text(
            json.dumps(definition, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    print(
        json.dumps(
            {
                "definitions": len(definitions),
                "source_snapshot": a.snapshot,
                "sqlite_modified": False,
                "new_routes_requested": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
