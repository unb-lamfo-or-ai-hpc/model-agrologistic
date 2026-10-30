"""Shared static/Plotly layout over the same cached IBGE polygons."""

from __future__ import annotations

import math

from .cartography import DISPLAY_EXTENT, PROJECTION, polygons, project, validate_context
from .geography import STYLES, require

LABELS = {
    "origin": "Origins",
    "origin_soybean": "Soybean origins",
    "origin_corn": "Corn origins",
    "domestic": "Domestic destinations",
    "export": "Export outlets",
    "existing": "Existing warehouses",
    "candidate": "Candidate sites",
    "opened": "Opened candidates",
    "expanded": "Expanded warehouses",
    "bulkified": "Bulk handling",
}
# Same national extent for every population/case; covers the complete IBGE dataset and all nodes.
LON_LAT_EXTENT = DISPLAY_EXTENT


def projected_extent():
    left, right, bottom, top = LON_LAT_EXTENT
    outline = [(left + (right - left) * i / 100, y) for i in range(101) for y in (bottom, top)]
    outline += [(x, bottom + (top - bottom) * i / 100) for i in range(101) for x in (left, right)]
    pts = [project(*p) for p in outline]
    return (
        min(p[0] for p in pts),
        max(p[0] for p in pts),
        min(p[1] for p in pts),
        max(p[1] for p in pts),
    )


def display_nodes(definition):
    """Investment symbols share original coordinates; no jitter or inferred decisions."""
    output = []
    for node in definition["nodes"]:
        if node["layer"] not in {"opened", "expanded", "bulkified"}:
            output.append(node)
            continue
        # A facility can carry expansion AND conversion; expose both at the same location.
        for flag in ("opened", "expanded", "bulkified"):
            facilities = [f for f in node["facilities"] if flag in f["decision_flags"]]
            if facilities:
                output.append(
                    {
                        **node,
                        "layer": flag,
                        "facilities": facilities,
                        "color": STYLES[flag][0],
                        "symbol": STYLES[flag][1],
                    }
                )
    return output


def capacity_nodes(definition):
    """Added static tonnes, grouped only for coincident display; IDs remain explicit."""
    groups, seen = {}, set()
    for node in definition["nodes"]:
        for facility in node["facilities"]:
            if facility["kind"] != "warehouse" or facility["id"] in seen:
                continue
            seen.add(facility["id"])
            investment = facility.get("investment") or {}
            tonnes = sum(investment.get(k, 0) for k in ("candidate_capacity", "expansion_capacity"))
            require(math.isfinite(tonnes) and tonnes >= 0, "Invalid added static capacity")
            if tonnes <= 1e-8:
                continue
            key = (node["lon"], node["lat"])
            group = groups.setdefault(key, {"lon": key[0], "lat": key[1], "tonnes": 0, "ids": []})
            group["tonnes"] += tonnes
            group["ids"].append(facility["id"])
    return list(groups.values())


def scene(definition, width, height, publication, capacity=False):
    context = validate_context(definition["cartography"])
    unit = min(width / 1200, height / 850)
    lo_x, hi_x, lo_y, hi_y = projected_extent()
    scale = min(785 / (hi_x - lo_x), 610 / (hi_y - lo_y))

    def xy(lonlat):
        x, y = project(*lonlat)
        return (
            (45 + (785 - (hi_x - lo_x) * scale) / 2 + (x - lo_x) * scale) * unit,
            (105 + (610 - (hi_y - lo_y) * scale) / 2 + (hi_y - y) * scale) * unit,
        )

    text, lines, markers, shapes = [], [], [], []
    country = next(f for f in context["features"] if f["level"] == "country")
    for poly in polygons(country["geometry"]):
        shapes.append(
            {
                "rings": [[xy(p) for p in ring] for ring in poly],
                "fill": "#f7f7f5",
                "stroke": None,
                "width": 0,
            }
        )
    for feature in context["features"]:
        if feature["level"] != "UF":
            continue
        for poly in polygons(feature["geometry"]):
            for ring in poly:
                lines.append(
                    {"points": [xy(p) for p in ring], "color": "#bdc3c7", "width": 0.65 * unit}
                )
    # National silhouette is explicitly stronger than internal boundaries.
    for poly in polygons(country["geometry"]):
        for ring in poly:
            lines.append(
                {"points": [xy(p) for p in ring], "color": "#777f82", "width": 1.05 * unit}
            )
    for route in definition["routes"]:
        require(route["provenance"]["provider"] == "osrm", "Only verified OSRM road geometry")
        line = [xy(p) for p in route["geometry"]]
        lines.append({"points": line, "color": "#427c99", "width": 1.6 * unit})
        a, b = next(
            ((a, b) for a, b in zip(line[-2::-1], line[:0:-1], strict=True) if a != b),
            (line[0], line[-1]),
        )
        angle = math.atan2(b[1] - a[1], b[0] - a[0])
        wings = [
            (b[0] - 8 * unit * math.cos(angle + d), b[1] - 8 * unit * math.sin(angle + d))
            for d in (-0.5, 0.5)
        ]
        lines.append({"points": [wings[0], b, wings[1]], "color": "#427c99", "width": 1.6 * unit})
    nodes = display_nodes(definition)
    if capacity:
        for node in capacity_nodes(definition):
            markers.append(
                {
                    "xy": xy((node["lon"], node["lat"])),
                    "color": "#b36616",
                    "symbol": "circle-open",
                    "size": 10 * math.sqrt(node["tonnes"] / 100000) * unit,
                    "ids": node["ids"],
                    "hollow": True,
                }
            )
    for node in nodes:
        lon, lat = node["lon"], node["lat"]
        require(
            LON_LAT_EXTENT[0] <= lon <= LON_LAT_EXTENT[1]
            and LON_LAT_EXTENT[2] <= lat <= LON_LAT_EXTENT[3],
            "Node outside fixed Brazil extent",
        )
        markers.append(
            {
                "xy": xy((lon, lat)),
                "color": node["color"],
                "symbol": node["symbol"],
                "size": 4.5 * unit,
                "ids": [f["id"] for f in node["facilities"]],
            }
        )
    prefix = "SYNTHETIC FIXTURE - NOT A RESEARCH RESULT: " if definition["synthetic"] else ""
    name = (
        "Input facility availability"
        if definition["evidence_status"] != "accepted"
        else "Deterministic investments"
        if "det" in (definition["case"] or "")
        else "Stochastic investments"
    )
    if capacity:
        name = "Deterministic" if "det" in (definition["case"] or "") else "Stochastic"
        name += " added static capacity"
    text += [
        (35 * unit, 35 * unit, f"{prefix}{name} | {definition['population']} sites", 25 * unit),
        (
            35 * unit,
            64 * unit,
            "Brazil and federative units | Albers equal-area display",
            17 * unit,
        ),
    ]
    layers = [layer for layer in STYLES if any(n["layer"] == layer for n in nodes)]
    for i, layer in enumerate(layers):
        y = (130 + i * 34) * unit
        markers.append(
            {
                "xy": (900 * unit, y),
                "color": STYLES[layer][0],
                "symbol": STYLES[layer][1],
                "size": 5 * unit,
                "ids": [],
            }
        )
        text.append((917 * unit, y + 5 * unit, LABELS[layer], 18 * unit))
    text.append((35 * unit, 818 * unit, "Boundaries: IBGE (2023), adapted | CC BY 4.0", 16 * unit))
    if definition["evidence_status"] != "accepted":
        text.append(
            (
                35 * unit,
                785 * unit,
                "Input locations only; no optimized investments shown.",
                17 * unit,
            )
        )
    elif not definition["routes"]:
        text.append(
            (
                35 * unit,
                785 * unit,
                "Investment locations; road-route geometry unavailable.",
                17 * unit,
            )
        )
    if not publication:
        text.append(
            (
                35 * unit,
                843 * unit,
                "Source and filter identity: " + definition["figure_sha256"][:20],
                13 * unit,
            )
        )
    if capacity:
        text.append((895 * unit, 480 * unit, "Added static capacity (t)", 18 * unit))
        for i, tonnes in enumerate((50000, 150000, 300000)):
            x = (925 + i * 85) * unit
            markers.append(
                {
                    "xy": (x, 530 * unit),
                    "color": "#b36616",
                    "symbol": "circle-open",
                    "size": 10 * math.sqrt(tonnes / 100000) * unit,
                    "ids": [],
                    "hollow": True,
                }
            )
            text.append((x - 23 * unit, 570 * unit, f"{tonnes // 1000}k", 16 * unit))
        text.append((895 * unit, 609 * unit, "Candidate + expansion", 16 * unit))
        text.append((895 * unit, 636 * unit, "Circle area proportional to t", 16 * unit))
        text.append((895 * unit, 663 * unit, "Bulk handling excluded", 16 * unit))
    return {
        "width": width,
        "height": height,
        "text": text,
        "lines": lines,
        "markers": markers,
        "polygons": shapes,
    }


def plotly_map(definition):
    import plotly.graph_objects as go

    context = validate_context(definition["cartography"])
    figure = go.Figure()
    country = next(f for f in context["features"] if f["level"] == "country")
    parts = []
    for poly in polygons(country["geometry"]):
        for ring in poly:
            points = [project(*p) for p in ring]
            parts.append("M " + " L ".join(f"{x},{y}" for x, y in points) + " Z")
    figure.add_shape(
        type="path",
        path=" ".join(parts),
        fillcolor="#f7f7f5",
        fillrule="evenodd",
        line={"width": 0},
        layer="below",
    )
    for level, label, color, width in (
        ("UF", "Federative units (IBGE 2023)", "#bdc3c7", 0.6),
        ("country", "Brazil outline", "#777f82", 1.1),
    ):
        for f in [f for f in context["features"] if f["level"] == level]:
            xs, ys = [], []
            for poly in polygons(f["geometry"]):
                for ring in poly:
                    pts = [project(*p) for p in ring]
                    xs += [p[0] for p in pts] + [None]
                    ys += [p[1] for p in pts] + [None]
            figure.add_trace(
                go.Scatter(
                    x=xs,
                    y=ys,
                    mode="lines",
                    line={"color": color, "width": width},
                    name=label,
                    legendgroup=level,
                    showlegend=f["id"] in {"11", "BR"},
                    text=f["name"],
                    hoverinfo="text",
                )
            )
    for route in definition["routes"]:
        pts = [project(*p) for p in route["geometry"]]
        figure.add_trace(
            go.Scatter(
                x=[p[0] for p in pts],
                y=[p[1] for p in pts],
                mode="lines",
                name=route["arc_type"],
                line={"color": "#427c99", "width": 1.5},
                text=f"{route['id']}: {route['tonnes']:,.3f} {definition['flow_units']}",
                hoverinfo="text",
            )
        )
        a, b = pts[-2:]
        figure.add_annotation(
            x=b[0],
            y=b[1],
            ax=a[0],
            ay=a[1],
            xref="x",
            yref="y",
            axref="x",
            ayref="y",
            showarrow=True,
            arrowhead=2,
        )
    nodes = display_nodes(definition)
    capacity = capacity_nodes(definition)
    if capacity:
        pts = [project(n["lon"], n["lat"]) for n in capacity]
        figure.add_trace(
            go.Scatter(
                x=[p[0] for p in pts],
                y=[p[1] for p in pts],
                mode="markers",
                name="Added static capacity (t)",
                visible="legendonly",
                marker={
                    "color": "#b36616",
                    "symbol": "circle-open",
                    "size": [20 * math.sqrt(n["tonnes"] / 100000) for n in capacity],
                },
                text=[f"{n['tonnes']:,.3f} t: " + " | ".join(n["ids"]) for n in capacity],
                hoverinfo="text",
            )
        )
    for layer in STYLES:
        rows = [n for n in nodes if n["layer"] == layer]
        if not rows:
            continue
        pts = [project(n["lon"], n["lat"]) for n in rows]
        figure.add_trace(
            go.Scatter(
                x=[p[0] for p in pts],
                y=[p[1] for p in pts],
                mode="markers",
                name=LABELS[layer],
                marker={"color": STYLES[layer][0], "symbol": STYLES[layer][1], "size": 9},
                customdata=[n["facilities"] for n in rows],
                text=[
                    f"lon={n['lon']}; lat={n['lat']}<br>"
                    + "<br>".join(
                        f["id"] + " | " + str(f.get("investment") or f.get("role", ""))
                        for f in n["facilities"]
                    )
                    for n in rows
                ],
                hoverinfo="text",
            )
        )
    x0, x1, y0, y1 = projected_extent()
    prefix = "SYNTHETIC FIXTURE - NOT A RESEARCH RESULT: " if definition["synthetic"] else ""
    figure.update_layout(
        title=f"{prefix}h{definition['population']} / {definition['evidence_status']}",
        xaxis={"range": [x0, x1], "visible": False},
        yaxis={"range": [y0, y1], "visible": False, "scaleanchor": "x", "scaleratio": 1},
        template="plotly_white",
        plot_bgcolor="white",
        legend={"x": 1.01, "y": 1},
        margin={"l": 20, "r": 230, "t": 70, "b": 45},
        meta={
            "figure_sha256": definition["figure_sha256"],
            "cartography_sha256": context["dataset_sha256"],
            "projection": PROJECTION,
        },
    )
    figure.add_annotation(
        xref="paper", yref="paper", x=0, y=-0.04, showarrow=False, text=context["attribution"]
    )
    return figure
