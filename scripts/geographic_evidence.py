"""Explicit geographic preparation, read-only figures or local-only Dash.

Preparation verifies local source-file bytes against an external manifest. It
creates a SEPARATE SQLite, never an experimental cache. No network or solver.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from src.visualization import geography as g


def verified_sources(manifest):
    manifest = Path(manifest)
    record = json.loads(manifest.read_text(encoding="utf-8"))
    identities = {}
    for label, source in record.items():
        path = Path(source["path"])
        if not path.is_absolute():
            path = manifest.parent / path
        with path.open("rb") as stream:
            observed = hashlib.file_digest(stream, "sha256").hexdigest()
        g.require(observed == source["sha256"], f"Source hash differs: {label}")
        identities[label] = observed
    return identities


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--bundle", type=Path, required=True)
    prepare.add_argument("--sources", type=Path, required=True)
    prepare.add_argument("--new-geographic-sqlite", type=Path, required=True)
    for name in ("render", "dash"):
        p = sub.add_parser(name)
        p.add_argument("--sqlite", type=Path, required=True)
        p.add_argument("--snapshot", required=True)
        if name == "render":
            p.add_argument("--population", type=int, choices=g.POPULATIONS, required=True)
            p.add_argument("--case")
            p.add_argument("--product")
            p.add_argument("--period")
            p.add_argument("--scenario")
            p.add_argument("--warehouse-layer", type=int, choices=g.POPULATIONS)
            p.add_argument("--output", type=Path, required=True)
        else:
            p.add_argument("--port", type=int, default=8050)
    args = parser.parse_args(argv)
    if args.action == "prepare":
        bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
        sources = verified_sources(args.sources)
        target = args.new_geographic_sqlite.resolve()
        source_paths = [Path(v["path"]) for v in json.loads(args.sources.read_text()).values()]
        source_paths = [
            (p if p.is_absolute() else args.sources.parent / p).resolve() for p in source_paths
        ]
        g.require(
            target not in source_paths
            and target != args.bundle.resolve()
            and target != args.sources.resolve(),
            "Geographic DB must be separate from sources",
        )
        snapshot, created = g.prepare(target, bundle, sources)
        print(
            json.dumps(
                {
                    "snapshot": snapshot,
                    "created": created,
                    "qualification": "source-bound geographic preparation; not a new solve",
                }
            )
        )
    elif args.action == "render":
        from src.visualization.render import render

        figure = g.figure_definition(
            args.sqlite,
            args.snapshot,
            population=args.population,
            case_id=args.case,
            product=args.product,
            period=args.period,
            scenario=args.scenario,
            warehouse_layer=args.warehouse_layer,
        )
        print(json.dumps(render(figure, args.output)))
    else:
        from src.visualization.app import create_app

        create_app(args.sqlite, args.snapshot).run(host="127.0.0.1", port=args.port, debug=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
