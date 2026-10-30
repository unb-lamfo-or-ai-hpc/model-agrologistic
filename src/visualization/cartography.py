"""Offline, source-bound cartographic context; never modifies scientific coordinates."""

from __future__ import annotations

import json
import math
import sqlite3
from contextlib import closing
from pathlib import Path

from .geography import canonical, digest, readonly, require

UF_CODES = {
    "11",
    "12",
    "13",
    "14",
    "15",
    "16",
    "17",
    "21",
    "22",
    "23",
    "24",
    "25",
    "26",
    "27",
    "28",
    "29",
    "31",
    "32",
    "33",
    "35",
    "41",
    "42",
    "43",
    "50",
    "51",
    "52",
    "53",
}
PROJECTION = {
    "name": "Albers equal-area (spherical display)",
    "lon_0": -54.0,
    "lat_0": -12.0,
    "lat_1": -2.0,
    "lat_2": -22.0,
    "radius_m": 6371008.8,
    "units": "km",
    "datum_input": "EPSG:4326",
}
DISPLAY_EXTENT = (-75.0, -28.0, -35.5, 6.5)


def project(lon, lat):
    """Display transform only, in km; common to all static and interactive maps."""
    r = math.pi / 180
    phi1, phi2 = PROJECTION["lat_1"] * r, PROJECTION["lat_2"] * r
    n = (math.sin(phi1) + math.sin(phi2)) / 2
    c = math.cos(phi1) ** 2 + 2 * n * math.sin(phi1)
    radius = PROJECTION["radius_m"] / 1000
    rho = radius * math.sqrt(c - 2 * n * math.sin(lat * r)) / n
    rho0 = radius * math.sqrt(c - 2 * n * math.sin(PROJECTION["lat_0"] * r)) / n
    theta = n * (lon - PROJECTION["lon_0"]) * r
    return rho * math.sin(theta), rho0 - rho * math.cos(theta)


def polygons(geometry):
    require(geometry["type"] in {"Polygon", "MultiPolygon"}, "Polygon geometry required")
    return [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]


def validate_context(context):
    unsigned = {k: v for k, v in context.items() if k != "dataset_sha256"}
    require(digest(unsigned) == context["dataset_sha256"], "Boundary dataset hash differs")
    require(context["schema_version"] == "ibge-cartographic-context-v1", "Boundary schema")
    require(context["projection"] == PROJECTION, "Display projection differs")
    require(tuple(context["geographic_extent"]) == DISPLAY_EXTENT, "Display extent differs")
    require(context["display_source_crs"] == "EPSG:4326", "Boundary display CRS differs")
    units = context["features"]
    require(len(units) == 28, "Country and exactly 27 UF entities required")
    require(
        {f["id"] for f in units if f["level"] == "UF"} == UF_CODES,
        "Official UF identifiers differ",
    )
    require(sum(f["id"] == "BR" and f["level"] == "country" for f in units) == 1, "BR outline")
    for f in units:
        require(f["geometry_sha256"] == digest(f["geometry"]), "Boundary geometry hash differs")
        for poly in polygons(f["geometry"]):
            for ring in poly:
                require(len(ring) >= 4 and ring[0] == ring[-1], "Unclosed polygon ring")
                require(
                    all(
                        len(v) == 2
                        and all(math.isfinite(x) for x in v)
                        and -180 <= v[0] <= 180
                        and -90 <= v[1] <= 90
                        for v in ring
                    ),
                    "Invalid boundary coordinate",
                )
    return context


def prepare_context(database, context):
    """Explicit preparation; a matching cached dataset is reused without a write."""
    validate_context(context)
    path = Path(database)
    key = context["dataset_sha256"]
    if path.exists():
        with closing(readonly(path)) as db:
            table = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='cartographic_context'"
            ).fetchone()
            row = (
                db.execute("SELECT dataset FROM cartographic_context WHERE id=1").fetchone()
                if table
                else None
            )
        if row is not None and row[0] == key:
            require(read_context(path) == context, "Cached boundary payload differs")
            return key, False
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        version = db.execute("PRAGMA user_version").fetchone()[0]
        require(version in (0, 1), "SQLite schema differs")
        db.executescript("""
            CREATE TABLE IF NOT EXISTS cartographic_datasets(
                key TEXT PRIMARY KEY, metadata TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS administrative_boundaries(
                dataset TEXT NOT NULL, id TEXT NOT NULL, level TEXT NOT NULL,
                payload TEXT NOT NULL, PRIMARY KEY(dataset,id));
            CREATE TABLE IF NOT EXISTS cartographic_context(
                id INTEGER PRIMARY KEY CHECK(id=1), dataset TEXT NOT NULL);
        """)
        metadata = {k: v for k, v in context.items() if k != "features"}
        db.execute(
            "INSERT OR IGNORE INTO cartographic_datasets VALUES (?,?)", (key, canonical(metadata))
        )
        db.executemany(
            "INSERT OR IGNORE INTO administrative_boundaries VALUES (?,?,?,?)",
            [(key, f["id"], f["level"], canonical(f)) for f in context["features"]],
        )
        db.execute("INSERT OR REPLACE INTO cartographic_context VALUES (1,?)", (key,))
        db.execute("PRAGMA user_version=1")
    return key, True


def read_context(database):
    with closing(readonly(database)) as db:
        if not db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='cartographic_context'"
        ).fetchone():
            return None
        row = db.execute("SELECT dataset FROM cartographic_context WHERE id=1").fetchone()
        require(row is not None, "Missing boundary selection")
        key = row[0]
        meta = db.execute(
            "SELECT metadata FROM cartographic_datasets WHERE key=?", (key,)
        ).fetchone()
        require(meta is not None, "Missing boundary metadata")
        context = json.loads(meta[0])
        context["features"] = [
            json.loads(r[0])
            for r in db.execute(
                "SELECT payload FROM administrative_boundaries WHERE dataset=? ORDER BY id", (key,)
            )
        ]
    return validate_context(context)


def with_context(definition, context):
    validate_context(context)
    require(
        digest({k: v for k, v in definition.items() if k != "figure_sha256"})
        == definition["figure_sha256"],
        "Figure definition drift",
    )
    updated = {k: v for k, v in definition.items() if k != "figure_sha256"}
    updated["cartography"] = context
    return {**updated, "figure_sha256": digest(updated)}
