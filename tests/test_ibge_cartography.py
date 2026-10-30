"""Cartographic context contracts; public static inputs, no model or road queries."""

import copy
import gzip
import hashlib
import json
from pathlib import Path

import pytest

from src.visualization import geography as g
from src.visualization.cartographic_view import display_nodes, projected_extent
from src.visualization.cartography import (
    PROJECTION,
    UF_CODES,
    prepare_context,
    project,
    read_context,
    validate_context,
    with_context,
)
from src.visualization.render import primitives, render

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def context():
    return json.loads(
        gzip.decompress((ROOT / "data/cartography/ibge_2023_simplified.json.gz").read_bytes())
    )


@pytest.fixture
def definition():
    return json.loads((ROOT / "manuscript/maps/scalar_h215_sto.json").read_text(encoding="utf-8"))


def test_27_official_units_and_matching_context_hash(context):
    validate_context(context)
    assert {f["id"] for f in context["features"] if f["level"] == "UF"} == UF_CODES
    assert context["validation"]["original_country_equals_union"]
    assert context["validation"]["simplified_uf_coverage_valid"]


@pytest.mark.parametrize("mutation", ["UF", "geometry", "CRS", "projection"])
def test_boundary_source_and_configuration_tampering_rejected(context, mutation):
    if mutation == "UF":
        context["features"].pop()
    elif mutation == "geometry":
        context["features"][0]["geometry"]["coordinates"][0][0][0] += 1
    elif mutation == "CRS":
        context["display_source_crs"] = "EPSG:3857"
    else:
        context["projection"]["lon_0"] = 0
    with pytest.raises(ValueError):
        validate_context(context)


def test_sqlite_read_and_identical_preparation_are_byte_preserving(tmp_path, context):
    db = tmp_path / "geo.sqlite3"
    key, created = prepare_context(db, context)
    before = db.read_bytes()
    stamp = db.stat().st_mtime_ns
    assert created
    assert read_context(db) == context
    assert prepare_context(db, context) == (key, False)
    assert db.read_bytes() == before
    assert db.stat().st_mtime_ns == stamp


def test_changed_source_configuration_selects_new_cache_without_deleting_old(tmp_path, context):
    import sqlite3

    db = tmp_path / "geo.sqlite3"
    old, _ = prepare_context(db, context)
    context["attribution"] += " (new display receipt)"
    context["dataset_sha256"] = g.digest(
        {k: v for k, v in context.items() if k != "dataset_sha256"}
    )
    new, created = prepare_context(db, context)
    assert old != new and created
    assert read_context(db)["dataset_sha256"] == new
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT count(*) FROM cartographic_datasets").fetchone()[0] == 2
        assert conn.execute("SELECT count(*) FROM administrative_boundaries").fetchone()[0] == 56


def test_context_does_not_modify_scientific_nodes_filters_or_geometry(context, definition):
    before = copy.deepcopy(definition)
    updated = with_context(definition, context)
    assert definition == before
    for key in ("nodes", "routes", "missing_geometry", "filters", "snapshot", "case", "population"):
        assert updated[key] == before[key]
    assert updated["figure_sha256"] != definition["figure_sha256"]
    before_ids = {f["id"] for n in definition["nodes"] for f in n["facilities"]}
    after_ids = {f["id"] for n in display_nodes(updated) for f in n["facilities"]}
    assert before_ids == after_ids


def test_projection_origin_and_fixed_scale():
    assert project(-54, -12) == (0, 0)
    assert project(-45, -20)[0] > 0
    assert project(-63, -20)[0] < 0
    assert project(-54, -25)[1] < 0
    assert PROJECTION["units"] == "km"
    assert projected_extent() == projected_extent()


@pytest.mark.parametrize("extension", ["svg", "pdf", "png"])
def test_headless_cartographic_exports_keep_receipt_and_avoid_mutation(
    tmp_path, context, definition, extension
):
    figure = with_context(definition, context)
    before = g.digest(figure)
    target = tmp_path / ("map." + extension)
    receipt = render(figure, target, publication=True)
    assert g.digest(figure) == before
    assert receipt["cartography_sha256"] == context["dataset_sha256"]
    assert receipt["renderer"] == "browser-free-ibge-albers-v1"
    assert receipt["definition"]["nodes"] == definition["nodes"]
    if extension == "svg":
        text = target.read_text(encoding="utf-8")
        assert 'fill-rule="evenodd"' in text
        assert "IBGE (2023)" in text
    assert target.stat().st_size > 1000


def test_every_current_map_uses_identical_projection_and_original_nodes(context):
    ids = set()
    for path in sorted((ROOT / "manuscript/maps").glob("*.json")):
        raw = path.read_bytes()
        old = json.loads(raw)
        updated = with_context(old, context)
        scene = primitives(updated, publication=True)
        assert updated["nodes"] == old["nodes"]
        assert len(scene["polygons"]) > 0
        assert updated["cartography"]["projection"] == PROJECTION
        assert hashlib.sha256(path.read_bytes()).hexdigest() == hashlib.sha256(raw).hexdigest()
        ids.add(old["case"])
    assert len(ids) == 6


def test_offline_plotly_carries_all_ids_and_same_cartographic_projection(context, definition):
    from src.visualization.geography import plotly_figure

    updated = with_context(definition, context)
    figure = plotly_figure(updated)
    assert figure.layout.meta["cartography_sha256"] == context["dataset_sha256"]
    assert figure.layout.meta["projection"] == PROJECTION
    retained = {
        f["id"]
        for trace in figure.data
        if trace.customdata is not None
        for group in trace.customdata
        for f in group
    }
    expected = {f["id"] for n in definition["nodes"] for f in n["facilities"]}
    assert retained == expected
    assert len(figure.layout.shapes) == 1


def test_context_extends_existing_sqlite_and_keeps_coincident_ids(tmp_path, context):
    bundle = {
        "schema_version": g.SCHEMA,
        "synthetic": True,
        "sources": {"fixture": "a" * 64},
        "entities": [
            {"id": value, "kind": "warehouse", "role": "existing", "lon": -47, "lat": -15}
            for value in ("one", "two")
        ],
        "populations": {"215": ["one", "two"]},
        "routes": [],
        "cases": [],
    }
    db = tmp_path / "combined.sqlite3"
    snapshot, _ = g.prepare(db, bundle, bundle["sources"])
    before = g.figure_definition(db, snapshot, population=215)
    prepare_context(db, context)
    data = db.read_bytes()
    after = g.figure_definition(db, snapshot, population=215)
    assert after["nodes"] == before["nodes"]
    assert {f["id"] for n in after["nodes"] for f in n["facilities"]} == {"one", "two"}
    assert after["cartography"]["dataset_sha256"] == context["dataset_sha256"]
    assert db.read_bytes() == data


def test_capacity_circle_area_represents_static_tonnes_only(context, definition):
    from src.visualization.cartographic_view import capacity_nodes

    data = with_context(definition, context)
    quantities = {tuple(n["ids"]): n["tonnes"] for n in capacity_nodes(data)}
    layout = primitives(data, publication=True, capacity=True)
    for marker in layout["markers"]:
        if marker.get("hollow") and marker["ids"]:
            assert marker["size"] ** 2 / quantities[tuple(marker["ids"])] == pytest.approx(0.001)
    assert sum(quantities.values()) == pytest.approx(
        sum(
            (f.get("investment") or {}).get("candidate_capacity", 0)
            + (f.get("investment") or {}).get("expansion_capacity", 0)
            for n in definition["nodes"]
            for f in n["facilities"]
            if f["kind"] == "warehouse"
        )
    )


def test_h500_reconstruction_keeps_original_coordinate_membership_and_quantities():
    old = json.loads((ROOT / "manuscript/maps/h500_pending.json").read_bytes())
    new = json.loads((ROOT / "manuscript/maps/scalar_h500_t1.json").read_bytes())

    def coordinates(d):
        return {f["id"]: (f["lon"], f["lat"]) for n in d["nodes"] for f in n["facilities"]}

    assert coordinates(old) == coordinates(new)
    assert old["evidence_status"] == "pending" and new["evidence_status"] == "accepted"
    assert old["snapshot"] != new["snapshot"]
    rows = [
        f["investment"] for n in new["nodes"] for f in n["facilities"] if f["kind"] == "warehouse"
    ]
    assert len(rows) == 500
    assert sum(r["candidate_capacity"] > 1e-8 for r in rows) == 354
    assert sum(r["candidate_capacity"] for r in rows) == pytest.approx(10992729)
    assert sum(r["expansion_capacity"] for r in rows) == pytest.approx(389176.25)
    assert new["routes"] == [] and new["materialization_scope"].startswith("Investment-only")
