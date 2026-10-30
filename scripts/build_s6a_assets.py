"""Render source-bound editorial figures; never solve, route or open a browser."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import subprocess
from pathlib import Path

from src.visualization.cartography import prepare_context, read_context, with_context
from src.visualization.render import render

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def thread_chart(record, directory):
    """The same bar coordinates, labels and units in raster and vector outputs."""
    from PIL import Image, ImageDraw, ImageFont
    from reportlab.lib.colors import HexColor
    from reportlab.pdfgen.canvas import Canvas

    rows = sorted(
        (r for r in record["observations"] if r["population"] == 300), key=lambda r: r["threads"]
    )
    labels = [
        (35, 35, "Runtime and memory at 300 sites", 26),
    ]
    lines, boxes = [], []
    for panel, (title, values, limit, color) in enumerate(
        [
            (
                "Native Runtime (min)",
                [r["native_runtime_seconds"] / 60 for r in rows],
                80,
                "#285979",
            ),
            (
                "Sampled application RSS (GiB)",
                [r["physical_diagnostics"]["peak_rss_mb"] / 1024 for r in rows],
                90,
                "#ac6621",
            ),
        ]
    ):
        left, bottom, panel_width, panel_height = 75 + panel * 590, 460, 460, 310
        labels.append((left, 112, title, 23))
        for tick in range(0, limit + 1, 10):
            y = bottom - tick / limit * panel_height
            lines.append((left, y, left + panel_width, y, "#dce1e7"))
            labels.append((left - 35, y + 6, str(tick), 18))
        for i, (row, value) in enumerate(zip(rows, values, strict=True)):
            x = left + 28 + i * 90
            y = bottom - value / limit * panel_height
            boxes.append((x, y, x + 52, bottom, color))
            labels.extend(
                [
                    (x - 1, y - 12, f"{value:.2f}", 18),
                    (x + 20, bottom + 30, str(row["threads"]), 20),
                ]
            )
        labels.append((left + 140, bottom + 66, "Solver threads", 21))
    image = Image.new("RGB", (1200, 620), "white")
    draw = ImageDraw.Draw(image)
    pdf = Canvas(str(directory / "scalar_threads.pdf"), pagesize=(1200, 620), invariant=1)
    for x1, y1, x2, y2, color in lines:
        draw.line((x1, y1, x2, y2), fill=color, width=1)
        pdf.setStrokeColor(HexColor(color))
        pdf.line(x1, 620 - y1, x2, 620 - y2)
    for x1, y1, x2, y2, color in boxes:
        draw.rectangle((x1, y1, x2, y2), fill=color)
        pdf.setFillColor(HexColor(color))
        pdf.rect(x1, 620 - y2, x2 - x1, y2 - y1, fill=1, stroke=0)
    pdf.setFillColor(HexColor("#172033"))
    for x, y, value, size in labels:
        draw.text((x, y - size), value, font=ImageFont.load_default(size=size), fill="#172033")
        pdf.setFont("Helvetica", size)
        pdf.drawString(x, 620 - y, value)
    image.save(directory / "scalar_threads.png", dpi=(150, 150))
    pdf.save()


def build(destination, *, workflow=True, maps_only=False, boundary_database=None):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    source_hashes = {}
    boundary_source = ROOT / "data/cartography/ibge_2023_simplified.json.gz"
    context = json.loads(gzip.decompress(boundary_source.read_bytes()))
    database = boundary_database or ROOT / "manuscript/.cartography.sqlite3"
    boundary_key, prepared = prepare_context(database, context)
    context = read_context(database)
    source_hashes[boundary_source.relative_to(ROOT).as_posix()] = sha(boundary_source)
    provenance = ROOT / "manuscript/geographic_sources.json"
    source_hashes[provenance.relative_to(ROOT).as_posix()] = sha(provenance)
    expected = json.loads(provenance.read_text(encoding="utf-8"))
    for source in sorted((ROOT / "manuscript/maps").glob("*.json")):
        definition = json.loads(source.read_text(encoding="utf-8"))
        normalized_sha = hashlib.sha256(source.read_text(encoding="utf-8").encode()).hexdigest()
        if normalized_sha != expected["figures"][source.name][
            "normalized_utf8_sha256"
        ] or definition["snapshot"] != expected["figures"][source.name].get(
            "snapshot", expected["snapshot"]
        ):
            raise ValueError("Geographic source receipt differs")
        source_hashes[source.relative_to(ROOT).as_posix()] = sha(source)
        definition = with_context(definition, context)
        variants = [False, True] if definition["evidence_status"] == "accepted" else [False]
        for capacity in variants:
            stem = source.stem + ("_capacity" if capacity else "")
            for extension in ("svg", "pdf", "png"):
                target = destination / f"{stem}.{extension}"
                if target.exists():
                    receipt = json.loads(target.with_suffix(target.suffix + ".json").read_text())
                    if (
                        receipt["figure_sha256"] != definition["figure_sha256"]
                        or receipt.get("presentation") != "publication"
                        or bool(receipt.get("capacity_encoding")) != capacity
                    ):
                        raise ValueError("Existing geographic figure source differs")
                else:
                    render(
                        definition,
                        target,
                        width=2400,
                        height=1700,
                        publication=True,
                        capacity=capacity,
                    )
    if maps_only:
        receipt = {
            "schema_version": "ibge-manuscript-map-build-v1",
            "sources": source_hashes,
            "outputs": {
                p.name: sha(p)
                for p in sorted(destination.iterdir())
                if p.suffix in {".png", ".pdf", ".svg"}
            },
            "boundary_dataset": boundary_key,
            "boundary_cache_prepared": prepared,
            "solver_executed": False,
            "routes_acquired": False,
            "network_access": False,
        }
        (destination / "ibge_map_assets.json").write_text(
            json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "map_figures": len(expected["figures"]),
                    "boundary_cache_prepared": prepared,
                    "solver_executed": False,
                }
            )
        )
        return
    evidence = ROOT / "manuscript/scalar_evidence.json"
    source_hashes[evidence.relative_to(ROOT).as_posix()] = sha(evidence)
    # Generated products only; original certificates and published figures are not edited.
    thread_chart(json.loads(evidence.read_text(encoding="utf-8")), destination)
    if workflow:
        source = ROOT / "manuscript/figures/human_ai_workflow.svg"
        source_hashes[source.relative_to(ROOT).as_posix()] = sha(source)
        for extension in ("png", "pdf"):
            subprocess.run(
                [
                    "rsvg-convert",
                    "--format",
                    extension,
                    "--output",
                    str(destination / f"human_ai_workflow.{extension}"),
                    str(source),
                ],
                check=True,
            )
    files = {
        p.name: sha(p)
        for p in sorted(destination.iterdir())
        if p.is_file() and p.suffix in {".png", ".pdf", ".svg"}
    }
    receipt = {
        "schema_version": "s6a-figure-build-v1",
        "sources": source_hashes,
        "outputs": files,
        "solver_executed": False,
        "routes_acquired": False,
        "browser_required": False,
        "workflow_included": workflow,
    }
    (destination / "s6a_assets.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "figures": len(files),
                "workflow_included": workflow,
                "solver_executed": False,
                "routes_acquired": False,
            }
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "manuscript/figures")
    parser.add_argument("--maps-only", action="store_true", help="Export maps only")
    parser.add_argument("--boundary-sqlite", type=Path, help="Existing/new explicit boundary cache")
    parser.add_argument(
        "--without-workflow",
        action="store_true",
        help="Map/chart QA only; full manuscript build requires rsvg-convert",
    )
    args = parser.parse_args()
    build(
        args.output,
        workflow=not args.without_workflow,
        maps_only=args.maps_only,
        boundary_database=args.boundary_sqlite,
    )


if __name__ == "__main__":
    main()
