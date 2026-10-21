"""Browser-free SVG/PDF/PNG maps from the same semantic definition as Dash.

Coordinates use a declared equirectangular display, not distance measurement.
ReportLab and Pillow are lazy optional imports; no Kaleido, Chrome or server.
"""

from __future__ import annotations

import html
import json
import math
from pathlib import Path

from .geography import STYLES, digest, require


def primitives(definition, width=1200, height=850):
    """One layout and legend for every static output format."""
    require(width >= 700 and height >= 550, "Figure canvas too small")
    unsigned = {k: v for k, v in definition.items() if k != "figure_sha256"}
    require(digest(unsigned) == definition["figure_sha256"], "Figure definition drift")
    points = [(n["lon"], n["lat"]) for n in definition["nodes"]]
    points += [tuple(p) for r in definition["routes"] for p in r["geometry"]]
    require(points, "No geographic points")
    xs, ys = zip(*points, strict=True)
    low_x, high_x, low_y, high_y = min(xs) - 1, max(xs) + 1, min(ys) - 1, max(ys) + 1
    scale = min((width - 365) / (high_x - low_x), (height - 190) / (high_y - low_y))

    def xy(p):
        left = 65 + ((width - 365) - (high_x - low_x) * scale) / 2
        return (left + (p[0] - low_x) * scale, height - 125 - (p[1] - low_y) * scale)

    prefix = "SYNTHETIC FIXTURE - NOT A RESEARCH RESULT: " if definition["synthetic"] else ""
    title = f"{prefix}h{definition['population']} / {definition['evidence_status']}"
    text = [
        (35, 32, title, 24),
        (35, 63, "Longitude/latitude display; not a metric projection", 18),
        (
            35,
            height - 66,
            f"Case: {definition['case'] or 'availability only'}; "
            f"product: {definition['filters']['product'] or 'all'}; "
            f"period: {definition['filters']['period'] or 'all'}; "
            f"scenario: {definition['filters']['scenario'] or 'weighted'}",
            16,
        ),
        (
            35,
            height - 39,
            f"Road geometry missing for {len(definition['missing_geometry'])} "
            f"positive-flow routes; no straight-line replacements",
            18,
        ),
        (
            35,
            height - 12,
            "Figure ID: "
            + definition["figure_sha256"][:16]
            + "; full source/filter receipt accompanies the figure",
            16,
        ),
    ]
    lines, markers = [], []
    for lon in range(math.ceil(low_x / 5) * 5, math.floor(high_x) + 1, 5):
        a, b = xy((lon, low_y)), xy((lon, high_y))
        lines.append({"points": [a, b], "color": "#e4e8ed", "width": 1})
        text.append((a[0] - 10, a[1] + 22, str(lon), 20))
    for lat in range(math.ceil(low_y / 5) * 5, math.floor(high_y) + 1, 5):
        a, b = xy((low_x, lat)), xy((high_x, lat))
        lines.append({"points": [a, b], "color": "#e4e8ed", "width": 1})
        text.append((a[0] - 42, a[1] + 6, str(lat), 20))
    for route in definition["routes"]:
        line = [xy(p) for p in route["geometry"]]
        lines.append({"points": line, "color": "#427c99", "width": 1.6})
        a, b = next(
            ((a, b) for a, b in zip(line[-2::-1], line[:0:-1], strict=True) if a != b),
            (line[0], line[-1]),
        )
        angle = math.atan2(b[1] - a[1], b[0] - a[0])
        wings = [
            (b[0] - 8 * math.cos(angle + d), b[1] - 8 * math.sin(angle + d)) for d in (-0.5, 0.5)
        ]
        lines.append({"points": [wings[0], b, wings[1]], "color": "#427c99", "width": 1.6})
    for n in definition["nodes"]:
        markers.append(
            {
                "xy": xy((n["lon"], n["lat"])),
                "color": n["color"],
                "symbol": n["symbol"],
                "size": 6,
                "ids": [f["id"] for f in n["facilities"]],
            }
        )
    legend_x, legend_y = width - 260, 100
    layers = [layer for layer in STYLES if any(n["layer"] == layer for n in definition["nodes"])]
    for i, layer in enumerate(layers):
        markers.append(
            {
                "xy": (legend_x, legend_y + i * 34),
                "color": STYLES[layer][0],
                "symbol": STYLES[layer][1],
                "size": 6,
                "ids": [],
            }
        )
        text.append((legend_x + 16, legend_y + 6 + i * 34, layer.replace("_", " "), 20))
    text += [
        (legend_x, legend_y + 36 * len(layers) + 20, "Road geometry only", 19),
        (legend_x, legend_y + 36 * len(layers) + 52, "No invented connections", 18),
        (legend_x, legend_y + 36 * len(layers) + 84, "Coincident IDs retained", 18),
    ]
    return {"width": width, "height": height, "text": text, "lines": lines, "markers": markers}


def marker_points(marker):
    x, y = marker["xy"]
    r, symbol = marker["size"], marker["symbol"]
    if symbol == "square":
        return [(x - r, y - r), (x + r, y - r), (x + r, y + r), (x - r, y + r)]
    if symbol == "diamond":
        return [(x, y - r), (x + r, y), (x, y + r), (x - r, y)]
    if symbol.startswith("triangle"):
        sign = -1 if symbol == "triangle-up" else 1
        return [(x, y + sign * r), (x + r, y - sign * r), (x - r, y - sign * r)]
    return None


def render(definition, output, *, width=1200, height=850):
    """Export exclusively; a provenance sidecar binds the scientific figure."""
    path = Path(output)
    require(path.suffix.lower() in {".svg", ".pdf", ".png"}, "SVG/PDF/PNG required")
    sidecar = path.with_suffix(path.suffix + ".json")
    require(not path.exists() and not sidecar.exists(), "Preserve existing figure outputs")
    scene = primitives(definition, width, height)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".svg":
        content = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
            '<rect width="100%" height="100%" fill="white"/>',
        ]
        for line in scene["lines"]:
            points = " ".join(f"{x:.3f},{y:.3f}" for x, y in line["points"])
            content.append(
                f'<polyline points="{points}" fill="none" stroke="{line["color"]}" '
                f'stroke-width="{line["width"]}"/>'
            )
        for m in scene["markers"]:
            points = marker_points(m)
            fill = "white" if m["symbol"] == "circle-open" else m["color"]
            title = html.escape(" | ".join(m["ids"]))
            shape = (
                f'<polygon points="{" ".join(f"{x},{y}" for x, y in points)}"'
                if points
                else f'<circle cx="{m["xy"][0]}" cy="{m["xy"][1]}" r="{m["size"]}"'
            )
            content.append(
                f'{shape} fill="{fill}" stroke="{m["color"]}"><title>{title}</title>'
                + ("</polygon>" if points else "</circle>")
            )
        for x, y, value, size in scene["text"]:
            content.append(
                f'<text x="{x}" y="{y}" font-family="Arial,sans-serif" '
                f'font-size="{size}">{html.escape(value)}</text>'
            )
        path.write_text("\n".join(content) + "\n</svg>\n", encoding="utf-8")
    elif path.suffix == ".pdf":
        from reportlab.lib.colors import HexColor
        from reportlab.pdfgen.canvas import Canvas

        canvas = Canvas(str(path), pagesize=(width, height), invariant=1)
        for line in scene["lines"]:
            canvas.setStrokeColor(HexColor(line["color"]))
            canvas.setLineWidth(line["width"])
            p = canvas.beginPath()
            p.moveTo(line["points"][0][0], height - line["points"][0][1])
            for x, y in line["points"][1:]:
                p.lineTo(x, height - y)
            canvas.drawPath(p)
        for m in scene["markers"]:
            canvas.setStrokeColor(HexColor(m["color"]))
            canvas.setFillColor(HexColor("#ffffff" if m["symbol"] == "circle-open" else m["color"]))
            points = marker_points(m)
            if points:
                p = canvas.beginPath()
                p.moveTo(points[0][0], height - points[0][1])
                for x, y in points[1:]:
                    p.lineTo(x, height - y)
                p.close()
                canvas.drawPath(p, fill=1)
            else:
                canvas.circle(m["xy"][0], height - m["xy"][1], m["size"], fill=1)
        canvas.setFillColor(HexColor("#172033"))
        for x, y, value, size in scene["text"]:
            canvas.setFont("Helvetica", size)
            canvas.drawString(x, height - y, value)
        canvas.save()
    else:
        from PIL import Image, ImageDraw, ImageFont

        image = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(image)
        for line in scene["lines"]:
            draw.line(line["points"], fill=line["color"], width=2)
        for m in scene["markers"]:
            fill = "white" if m["symbol"] == "circle-open" else m["color"]
            points = marker_points(m)
            if points:
                draw.polygon(points, fill=fill, outline=m["color"])
            else:
                x, y = m["xy"]
                r = m["size"]
                draw.ellipse((x - r, y - r, x + r, y + r), fill=fill, outline=m["color"])
        for x, y, value, size in scene["text"]:
            draw.text((x, y - size), value, fill="#172033", font=ImageFont.load_default(size=size))
        image.save(path, dpi=(150, 150))
    receipt = {
        "figure_sha256": definition["figure_sha256"],
        "snapshot": definition["snapshot"],
        "filters": definition["filters"],
        "synthetic": definition["synthetic"],
        "renderer": "browser-free-equirectangular-v1",
        "definition": definition,
    }
    sidecar.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return receipt
