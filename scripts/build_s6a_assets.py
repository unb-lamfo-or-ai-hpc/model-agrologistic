"""Render source-bound editorial figures; never solve, route or open a browser."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

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
        (35, 35, "h300: descriptive thread observations", 26),
        (35, 68, "One cold solve per level; no causal speedup claim", 20),
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
    labels.append((35, 585, "Execution order: 4 / 1 / 8 / 2 / 16; identical exported vectors", 20))
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


def build(destination, *, workflow=True):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    source_hashes = {}
    provenance = ROOT / "manuscript/geographic_sources.json"
    source_hashes[provenance.relative_to(ROOT).as_posix()] = sha(provenance)
    expected = json.loads(provenance.read_text(encoding="utf-8"))
    for source in sorted((ROOT / "manuscript/maps").glob("*.json")):
        definition = json.loads(source.read_text(encoding="utf-8"))
        normalized_sha = hashlib.sha256(source.read_text(encoding="utf-8").encode()).hexdigest()
        if (
            normalized_sha != expected["figures"][source.name]["normalized_utf8_sha256"]
            or definition["snapshot"] != expected["snapshot"]
        ):
            raise ValueError("Geographic source receipt differs")
        source_hashes[source.relative_to(ROOT).as_posix()] = sha(source)
        for extension in ("svg", "pdf", "png"):
            target = destination / f"{source.stem}.{extension}"
            if target.exists():
                receipt = json.loads(target.with_suffix(target.suffix + ".json").read_text())
                if receipt["figure_sha256"] != definition["figure_sha256"]:
                    raise ValueError("Existing geographic figure source differs")
            else:
                render(definition, target)
    evidence = ROOT / "manuscript/scalar_evidence.json"
    source_hashes[evidence.relative_to(ROOT).as_posix()] = sha(evidence)
    # Generated products only; original certificates and published figures are not edited.
    thread_chart(json.loads(evidence.read_text(encoding="utf-8")), destination)
    if workflow:
        source = ROOT / "docs/s6a_20261021/figures/human_ai_workflow.svg"
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
    parser.add_argument(
        "--without-workflow",
        action="store_true",
        help="Map/chart QA only; full manuscript build requires rsvg-convert",
    )
    args = parser.parse_args()
    build(args.output, workflow=not args.without_workflow)


if __name__ == "__main__":
    main()
