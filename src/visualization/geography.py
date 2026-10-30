"""Source-bound geographic preparation and read-only scientific figure definitions.

Preparation alone writes a NEW, separate geographic SQLite repository. Reading
never invokes preparation, optimization, routing, or a network service. Accepted
case labels replay supplied original certificate metadata; they are not a fresh
mathematical validation. Missing road geometry is reported, never interpolated.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
from collections import defaultdict
from contextlib import closing
from pathlib import Path

SCHEMA = "agrologistic-geography-v1"
POPULATIONS = (215, 300, 400, 500)
STYLES = {
    "origin": ("#176b42", "triangle-up"),
    "origin_soybean": ("#176b42", "triangle-up"),
    "origin_corn": ("#8b6b00", "triangle-down"),
    "domestic": ("#3465a4", "square"),
    "export": ("#78469b", "diamond"),
    "existing": ("#4d4d4d", "circle"),
    "candidate": ("#bdbdbd", "circle-open"),
    "opened": ("#d47700", "circle"),
    "expanded": ("#ca3b3b", "square"),
    "bulkified": ("#aa4499", "diamond"),
}
PRODUCT_GROUPS = {"soybean": {"soybean", "soy", "soja"}, "corn": {"corn", "maize", "milho"}}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def readonly(database):
    path = Path(database).resolve(strict=True)
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    connection.execute("PRAGMA query_only=ON")
    if connection.execute("PRAGMA user_version").fetchone()[0] != 1:
        connection.close()
        raise ValueError("SQLite schema differs")
    return connection


def validate(bundle, expected_sources):
    require(bundle["schema_version"] == SCHEMA, "Geographic bundle schema differs")
    require(type(bundle.get("synthetic", False)) is bool, "Synthetic marker must be boolean")
    require(bundle["populations"], "At least one population is required")
    sources = bundle["sources"]
    require(sources == expected_sources and bool(sources), "Source identities differ")
    require(all(re.fullmatch(r"[0-9a-f]{64}", v) for v in sources.values()), "SHA256 required")
    entities = bundle["entities"]
    by_id = {e["id"]: e for e in entities}
    require(len(by_id) == len(entities), "Duplicate entity ID; coordinates are not IDs")
    for e in entities:
        require(e["id"] and e["kind"] in {"origin", "domestic", "export", "warehouse"}, "Node kind")
        require(finite(e["lat"]) and -90 <= e["lat"] <= 90, "Invalid latitude")
        require(finite(e["lon"]) and -180 <= e["lon"] <= 180, "Invalid longitude")
        if e["kind"] == "warehouse":
            require(e["role"] in {"existing", "candidate"}, "Warehouse role")
    previous = set()
    for population in sorted(map(int, bundle["populations"])):
        require(population in POPULATIONS, "Unsupported warehouse population")
        ids = bundle["populations"][str(population)]
        require(len(ids) == len(set(ids)), "Duplicate population member")
        require(all(i in by_id and by_id[i]["kind"] == "warehouse" for i in ids), "Population ID")
        require(previous <= set(ids), "Warehouse population is not nested")
        if not bundle.get("synthetic", False):
            require(len(ids) == population, "Population cardinality differs")
            require(sum(by_id[i]["role"] == "existing" for i in ids) == 146, "Existing membership")
        previous = set(ids)
    routes = {r["id"]: r for r in bundle.get("routes", [])}
    require(len(routes) == len(bundle.get("routes", [])), "Duplicate route ID")
    for r in routes.values():
        require(r["origin"] in by_id and r["destination"] in by_id, "Route association")
        provenance = r["provenance"]
        require(provenance["provider"] == "osrm" and provenance["dataset_id"], "Road provenance")
        require(provenance["source_sha256"] in sources.values(), "Unbound route geometry source")
        points = r.get("geometry")
        if points is not None:
            require(len(points) >= 2, "Road geometry needs at least two points")
            require(
                all(
                    len(p) == 2
                    and all(finite(v) for v in p)
                    and -180 <= p[0] <= 180
                    and -90 <= p[1] <= 90
                    for p in points
                ),
                "Invalid longitude/latitude geometry",
            )
    cases = bundle.get("cases", [])
    require(len({c["id"] for c in cases}) == len(cases), "Duplicate case ID")
    for c in cases:
        require(str(c["population"]) in bundle["populations"], "Missing case population")
        require(c["mode"] in {"det", "sto"}, "Case mode")
        require(c["status"] in {"accepted", "pending", "rejected"}, "Case evidence status")
        decisions, flows = c.get("decisions", []), c.get("flows", [])
        if c["status"] != "accepted":
            require(
                not decisions and not flows, "Unaccepted case cannot supply optimized decisions"
            )
            continue
        require(c["certificate_sha256"] in sources.values(), "Unbound original certificate")
        require(
            c["original_validation_status"] == "accepted", "Original residual certificate required"
        )
        probabilities = c["probabilities"]
        require(
            probabilities
            and all(finite(v) and v > 0 for v in probabilities.values())
            and math.isclose(sum(probabilities.values()), 1, abs_tol=1e-12),
            "Scenario weights",
        )
        require(c["mode"] != "det" or len(probabilities) == 1, "DET is one scenario")
        members = set(bundle["populations"][str(c["population"])])
        require(
            len({d["warehouse"] for d in decisions}) == len(decisions), "Duplicate investment row"
        )
        for d in decisions:
            require(d["warehouse"] in members, "Investment outside included population")
            for name in ("candidate_capacity", "expansion_capacity", "bulk_capacity"):
                require(finite(d[name]) and d[name] >= 0, "Invalid investment quantity")
            for name in ("open", "expand", "bulkify"):
                require(d[name] in (0, 1), "Validated binary display requires 0/1")
        for f in flows:
            require(finite(f["tonnes"]) and f["tonnes"] >= 0, "Negative/nonfinite grain flow")
            require(
                f["scenario"] in probabilities
                and f["product"] in c["products"]
                and str(f["period"]) in list(map(str, c["periods"])),
                "Flow dimensions",
            )
            require(f["route"] in routes, "Missing route identity; geometry may be unavailable")
            route = routes[f["route"]]
            origin, target = by_id[route["origin"]], by_id[route["destination"]]
            kinds = (origin["kind"], target["kind"])
            allowed = {"OD": ("origin", "warehouse"), "DD": ("warehouse", "warehouse")}
            require(f["arc_type"] in {"OD", "DC", "DD", "OC"}, "Arc family")
            if f["arc_type"] in allowed:
                require(kinds == allowed[f["arc_type"]], "Arc family/endpoints differ")
            else:
                require(
                    kinds[0] == ("warehouse" if f["arc_type"] == "DC" else "origin")
                    and kinds[1] in {"domestic", "export"},
                    "Destination role differs",
                )
            require(
                all(e["kind"] != "warehouse" or e["id"] in members for e in (origin, target)),
                "Flow uses excluded warehouse",
            )
    return bundle


def prepare(database, bundle, expected_sources):
    """Explicit preparation only; unchanged content reuses SQLite without a write."""
    validate(bundle, expected_sources)
    key = digest({"schema": SCHEMA, "bundle": bundle})
    path = Path(database)
    if path.exists():
        with closing(readonly(path)) as db:
            if db.execute("SELECT 1 FROM snapshots WHERE key=?", (key,)).fetchone():
                return key, False
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript("""
          CREATE TABLE IF NOT EXISTS snapshots(key TEXT PRIMARY KEY, metadata TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS entities(snapshot TEXT, id TEXT, payload TEXT,
            PRIMARY KEY(snapshot,id), FOREIGN KEY(snapshot) REFERENCES snapshots(key));
          CREATE TABLE IF NOT EXISTS memberships(snapshot TEXT,population INTEGER,id TEXT,
            PRIMARY KEY(snapshot,population,id),
            FOREIGN KEY(snapshot,id) REFERENCES entities(snapshot,id));
          CREATE TABLE IF NOT EXISTS routes(snapshot TEXT,id TEXT,payload TEXT,
            PRIMARY KEY(snapshot,id), FOREIGN KEY(snapshot) REFERENCES snapshots(key));
          CREATE TABLE IF NOT EXISTS cases(snapshot TEXT,id TEXT,payload TEXT,
            PRIMARY KEY(snapshot,id), FOREIGN KEY(snapshot) REFERENCES snapshots(key));
          CREATE TABLE IF NOT EXISTS flows(snapshot TEXT,case_id TEXT,scenario TEXT,
            product TEXT,period TEXT,route TEXT,arc_type TEXT,tonnes REAL,
            FOREIGN KEY(snapshot,case_id) REFERENCES cases(snapshot,id),
            FOREIGN KEY(snapshot,route) REFERENCES routes(snapshot,id));
          CREATE INDEX IF NOT EXISTS flow_selection
            ON flows(snapshot,case_id,scenario,product,period);
        """)
        metadata = {
            k: v
            for k, v in bundle.items()
            if k not in {"entities", "populations", "routes", "cases"}
        }
        metadata["available_populations"] = sorted(map(int, bundle["populations"]))
        db.execute("INSERT INTO snapshots VALUES (?,?)", (key, canonical(metadata)))
        db.executemany(
            "INSERT INTO entities VALUES (?,?,?)",
            [(key, e["id"], canonical(e)) for e in bundle["entities"]],
        )
        db.executemany(
            "INSERT INTO memberships VALUES (?,?,?)",
            [(key, int(p), i) for p, ids in bundle["populations"].items() for i in ids],
        )
        db.executemany(
            "INSERT INTO routes VALUES (?,?,?)",
            [(key, r["id"], canonical(r)) for r in bundle.get("routes", [])],
        )
        for case in bundle.get("cases", []):
            meta = {k: v for k, v in case.items() if k != "flows"}
            db.execute("INSERT INTO cases VALUES (?,?,?)", (key, case["id"], canonical(meta)))
            db.executemany(
                "INSERT INTO flows VALUES (?,?,?,?,?,?,?,?)",
                [
                    (
                        key,
                        case["id"],
                        f["scenario"],
                        f["product"],
                        str(f["period"]),
                        f["route"],
                        f["arc_type"],
                        f["tonnes"],
                    )
                    for f in case.get("flows", [])
                    if f["tonnes"] > 0
                ],
            )
        db.execute("PRAGMA user_version=1")
    return key, True


def catalogue(database, key):
    with closing(readonly(database)) as db:
        row = db.execute("SELECT metadata FROM snapshots WHERE key=?", (key,)).fetchone()
        require(row is not None, "Unknown snapshot")
        return {
            "metadata": json.loads(row[0]),
            "cases": [
                json.loads(r[0])
                for r in db.execute(
                    "SELECT payload FROM cases WHERE snapshot=? ORDER BY id", (key,)
                )
            ],
        }


def figure_definition(
    database,
    key,
    *,
    population,
    case_id=None,
    product=None,
    period=None,
    scenario=None,
    positive_threshold=1e-8,
    warehouse_layer=None,
):
    """Shared semantic map for Dash and headless; no straight-line substitutes."""
    require(finite(positive_threshold) and positive_threshold >= 0, "Display threshold")
    info = catalogue(database, key)
    with closing(readonly(database)) as db:
        entities = {
            i: json.loads(p)
            for i, p in db.execute(
                "SELECT id,payload FROM entities WHERE snapshot=? ORDER BY id", (key,)
            )
        }
        members = {
            r[0]
            for r in db.execute(
                "SELECT id FROM memberships WHERE snapshot=? AND population=?", (key, population)
            )
        }
        require(bool(members), "Population unavailable")
        groups, decision, visible_routes, missing = defaultdict(list), {}, [], []
        selected = None
        if case_id:
            selected = next((c for c in info["cases"] if c["id"] == case_id), None)
            require(
                selected is not None and selected["population"] == population,
                "Case/population mismatch",
            )
            if selected["status"] == "accepted":
                require(product is None or product in selected["products"], "Unknown product")
                require(
                    scenario is None or scenario in selected["probabilities"], "Unknown scenario"
                )
                require(
                    period is None or str(period) in list(map(str, selected["periods"])),
                    "Unknown period",
                )
                decision = {d["warehouse"]: d for d in selected.get("decisions", [])}
                query = (
                    "SELECT scenario,route,arc_type,tonnes FROM flows "
                    "WHERE snapshot=? AND case_id=?"
                )
                args = [key, case_id]
                for field, value in (
                    ("product", product),
                    ("period", period),
                    ("scenario", scenario),
                ):
                    if value is not None:
                        query += " AND " + field + "=?"
                        args.append(str(value))
                sums = defaultdict(float)
                for sc, route, arc, tonnes in db.execute(query, args):
                    sums[(route, arc)] += tonnes * (
                        selected["probabilities"][sc] if scenario is None else 1
                    )
                for (route, arc), tonnes in sorted(sums.items()):
                    if tonnes <= positive_threshold:
                        continue
                    raw = db.execute(
                        "SELECT payload FROM routes WHERE snapshot=? AND id=?", (key, route)
                    ).fetchone()
                    r = json.loads(raw[0])
                    if r.get("geometry") is None:
                        missing.append({"route": route, "tonnes": tonnes, "arc_type": arc})
                    else:
                        visible_routes.append({**r, "tonnes": tonnes, "arc_type": arc})
        for e in entities.values():
            if e["kind"] == "warehouse" and e["id"] not in members:
                continue
            if (
                e["kind"] == "origin"
                and product is not None
                and product not in e.get("products", [])
            ):
                continue
            role, flags = e["kind"], []
            if role == "warehouse":
                role = e["role"]
                d = decision.get(e["id"], {})
                for flag, binary in (
                    ("opened", "open"),
                    ("expanded", "expand"),
                    ("bulkified", "bulkify"),
                ):
                    if d.get(binary) == 1:
                        flags.append(flag)
                if flags:
                    role = flags[-1]
            first_population = (
                next(
                    (
                        p
                        for p in POPULATIONS
                        if db.execute(
                            "SELECT 1 FROM memberships WHERE snapshot=? AND population=? AND id=?",
                            (key, p, e["id"]),
                        ).fetchone()
                    ),
                    None,
                )
                if e["kind"] == "warehouse"
                else None
            )
            if e["kind"] == "warehouse" and warehouse_layer is not None:
                require(
                    warehouse_layer in POPULATIONS and warehouse_layer <= population,
                    "Invalid incremental population layer",
                )
                if first_population != warehouse_layer:
                    continue
            variants = [role]
            if role == "origin":
                products = [product] if product else e.get("products", [])
                variants = [
                    "origin_" + group
                    for group, aliases in PRODUCT_GROUPS.items()
                    if any(str(p).casefold() in aliases for p in products)
                ] or ["origin"]
            for layer in variants:
                group_key = (e["lon"], e["lat"], layer)
                groups[group_key].append(
                    {
                        **e,
                        "decision_flags": flags,
                        "first_population": first_population,
                        "investment": decision.get(e["id"]),
                    }
                )
        nodes = [
            {
                "lon": lon,
                "lat": lat,
                "layer": layer,
                "facilities": rows,
                "color": STYLES[layer][0],
                "symbol": STYLES[layer][1],
            }
            for (lon, lat, layer), rows in sorted(groups.items())
        ]
    definition = {
        "schema_version": "agrologistic-map-v1",
        "snapshot": key,
        "population": population,
        "case": case_id,
        "evidence_status": selected["status"] if selected else "availability_only",
        "synthetic": bool(info["metadata"].get("synthetic", False)),
        "filters": {
            "product": product,
            "period": period,
            "scenario": scenario,
            "warehouse_layer": warehouse_layer,
        },
        "flow_units": "t; expected across scenarios"
        if scenario is None
        else "t; selected scenario",
        "nodes": nodes,
        "routes": visible_routes,
        "missing_geometry": missing,
        "notes": [
            "Coordinates unchanged; coincident IDs retained in grouped details.",
            "Road geometries only. Missing geometries are omitted, never replaced.",
            "Transport-leg totals are not unique grain supply.",
        ],
    }
    definition = {**definition, "figure_sha256": digest(definition)}
    from .cartography import read_context, with_context

    context = read_context(database)
    return with_context(definition, context) if context is not None else definition


def plotly_figure(definition):
    """Offline Cartesian geographic coordinates; no external basemap requests."""
    if definition.get("cartography"):
        from .cartographic_view import plotly_map

        return plotly_map(definition)
    import plotly.graph_objects as go

    figure = go.Figure()
    for route in definition["routes"]:
        figure.add_trace(
            go.Scatter(
                x=[p[0] for p in route["geometry"]],
                y=[p[1] for p in route["geometry"]],
                mode="lines",
                name=route["arc_type"],
                text=f"{route['id']}: {route['tonnes']:,.3f} {definition['flow_units']}",
                hoverinfo="text",
                line={"width": 1.5, "color": "#427c99"},
            )
        )
        a, b = route["geometry"][-2:]
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
    for layer, (color, symbol) in STYLES.items():
        nodes = [n for n in definition["nodes"] if n["layer"] == layer]
        if not nodes:
            continue
        figure.add_trace(
            go.Scatter(
                x=[n["lon"] for n in nodes],
                y=[n["lat"] for n in nodes],
                mode="markers",
                name=layer,
                customdata=[n["facilities"] for n in nodes],
                text=[" | ".join(f["id"] for f in n["facilities"]) for n in nodes],
                hoverinfo="text",
                marker={"color": color, "symbol": symbol, "size": 10},
            )
        )
    prefix = "SYNTHETIC FIXTURE — NOT A RESEARCH RESULT: " if definition["synthetic"] else ""
    figure.update_layout(
        title=f"{prefix}h{definition['population']} / {definition['evidence_status']}",
        xaxis_title="Longitude (degrees)",
        yaxis_title="Latitude (degrees)",
        template="plotly_white",
        legend_title="Node/decision layer",
        meta={"figure_sha256": definition["figure_sha256"]},
    )
    figure.update_yaxes(scaleanchor="x", scaleratio=1)
    return figure
