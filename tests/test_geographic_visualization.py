"""Small analytical map contracts, not production security or scientific solves."""

import copy
import hashlib
import json
import sqlite3
import xml.etree.ElementTree as ET

import pytest

from scripts.geographic_evidence import verified_sources
from scripts.prepare_manuscript_geography import customer_identity
from src.visualization import geography as g
from src.visualization.render import render


@pytest.fixture
def bundle():
    source = "a" * 64
    return {
        "schema_version": g.SCHEMA,
        "synthetic": True,
        "sources": {"test": source},
        "entities": [
            {"id": "o", "kind": "origin", "products": ["Soja", "Milho"], "lon": -48, "lat": -16},
            {"id": "w", "kind": "warehouse", "role": "existing", "lon": -47, "lat": -15},
            {"id": "n", "kind": "warehouse", "role": "candidate", "lon": -47, "lat": -15},
            {"id": "c", "kind": "domestic", "lon": -46, "lat": -14},
        ],
        "populations": {"215": ["w"], "300": ["w", "n"]},
        "routes": [
            {
                "id": "r",
                "origin": "o",
                "destination": "w",
                "geometry": [[-48, -16], [-47.7, -15.8], [-47, -15]],
                "provenance": {
                    "provider": "osrm",
                    "dataset_id": "SYNTHETIC TEST",
                    "source_sha256": source,
                },
            }
        ],
        "cases": [
            {
                "id": "accepted",
                "population": 300,
                "mode": "sto",
                "status": "accepted",
                "certificate_sha256": source,
                "original_validation_status": "accepted",
                "probabilities": {"low": 0.25, "high": 0.75},
                "products": ["Soja", "Milho"],
                "periods": ["2021-01"],
                "decisions": [
                    {
                        "warehouse": "n",
                        "open": 1,
                        "expand": 0,
                        "bulkify": 0,
                        "candidate_capacity": 0,
                        "expansion_capacity": 0,
                        "bulk_capacity": 0,
                    }
                ],
                "flows": [
                    {
                        "route": "r",
                        "arc_type": "OD",
                        "scenario": s,
                        "product": "Soja",
                        "period": "2021-01",
                        "tonnes": t,
                    }
                    for s, t in [("low", 4), ("high", 8)]
                ],
            },
            {"id": "pending", "population": 300, "mode": "sto", "status": "pending"},
        ],
    }


def prepared(tmp_path, bundle):
    path = tmp_path / "geographic.sqlite3"
    key, created = g.prepare(path, bundle, bundle["sources"])
    assert created
    return path, key


def test_reopening_and_filters_do_not_write_or_reprepare(tmp_path, bundle):
    db, key = prepared(tmp_path, bundle)
    before = db.read_bytes()
    assert g.prepare(db, bundle, bundle["sources"]) == (key, False)
    f = g.figure_definition(db, key, population=300, case_id="accepted")
    assert f["routes"][0]["tonnes"] == 7
    assert (
        g.figure_definition(db, key, population=300, case_id="accepted", scenario="low")["routes"][
            0
        ]["tonnes"]
        == 4
    )
    assert db.read_bytes() == before
    assert {n["layer"] for n in f["nodes"]} >= {"origin_soybean", "origin_corn"}


def test_query_connection_is_read_only(tmp_path, bundle):
    db, _ = prepared(tmp_path, bundle)
    connection = g.readonly(db)
    with pytest.raises(sqlite3.OperationalError):
        connection.execute("DELETE FROM snapshots")
    connection.close()


def test_geometry_missing_not_drawn_as_straight_line(tmp_path, bundle):
    bundle["routes"][0]["geometry"] = None
    db, key = prepared(tmp_path, bundle)
    f = g.figure_definition(db, key, population=300, case_id="accepted")
    assert not f["routes"] and f["missing_geometry"][0]["tonnes"] == 7


def test_pending_case_has_no_invented_decisions(tmp_path, bundle):
    db, key = prepared(tmp_path, bundle)
    f = g.figure_definition(db, key, population=300, case_id="pending")
    assert f["evidence_status"] == "pending" and not f["routes"]
    assert "opened" not in {n["layer"] for n in f["nodes"]}


def test_incremental_population_filter_preserves_ids_and_receipt(tmp_path, bundle):
    db, key = prepared(tmp_path, bundle)
    all_nodes = g.figure_definition(db, key, population=300, case_id="accepted")
    added = g.figure_definition(db, key, population=300, case_id="accepted", warehouse_layer=300)
    ids = {f["id"] for n in added["nodes"] for f in n["facilities"]}
    assert "n" in ids and "w" not in ids
    assert added["figure_sha256"] != all_nodes["figure_sha256"]


def test_activation_is_distinct_from_positive_investment(tmp_path, bundle):
    db, key = prepared(tmp_path, bundle)
    f = g.figure_definition(db, key, population=300, case_id="accepted")
    node = next(n for n in f["nodes"] if n["layer"] == "opened")
    assert node["facilities"][0]["investment"]["candidate_capacity"] == 0
    assert node["facilities"][0]["first_population"] == 300
    assert node["lon"] == -47 and node["lat"] == -15


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate",
        "not_nested",
        "nan",
        "negative",
        "unaccepted",
        "probabilities",
        "route_source",
        "real_count",
    ],
)
def test_bad_scientific_display_inputs_rejected(bundle, mutation):
    b = copy.deepcopy(bundle)
    if mutation == "duplicate":
        b["entities"].append(b["entities"][0])
    elif mutation == "not_nested":
        b["populations"]["300"] = ["n"]
    elif mutation == "nan":
        b["entities"][0]["lat"] = float("nan")
    elif mutation == "negative":
        b["cases"][0]["flows"][0]["tonnes"] = -1
    elif mutation == "unaccepted":
        b["cases"][0]["status"] = "pending"
    elif mutation == "probabilities":
        b["cases"][0]["probabilities"]["low"] = 0.5
    elif mutation == "route_source":
        b["routes"][0]["provenance"]["source_sha256"] = "b" * 64
    else:
        b["synthetic"] = False
    with pytest.raises(ValueError):
        g.validate(b, b["sources"])


def test_svg_export_is_pure_and_source_bound(tmp_path, bundle):
    db, key = prepared(tmp_path, bundle)
    before = db.read_bytes()
    f = g.figure_definition(db, key, population=300, case_id="accepted")
    out = tmp_path / "map.svg"
    receipt = render(f, out)
    ET.parse(out)
    assert receipt["figure_sha256"] == f["figure_sha256"]
    assert "SYNTHETIC FIXTURE" in out.read_text()
    assert db.read_bytes() == before
    with pytest.raises(ValueError, match="Preserve"):
        render(f, out)
    f["population"] = 500
    with pytest.raises(ValueError, match="drift"):
        render(f, tmp_path / "corrupt.svg")


def test_source_file_hashes_are_verified_before_preparation(tmp_path):
    source = tmp_path / "source.json"
    source.write_bytes(b"original")
    manifest = tmp_path / "sources.json"
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest.write_text(json.dumps({"source": {"path": source.name, "sha256": sha}}))
    assert verified_sources(manifest) == {"source": sha}
    source.write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash differs"):
        verified_sources(manifest)


def test_customer_roles_cannot_merge_coincident_municipalities():
    assert (
        customer_identity({"customer": "X | DOMESTICA", "customer_type": "domestic"})
        == "domestic:X"
    )
    assert (
        customer_identity({"customer": "X | EXPORTACAO", "customer_type": "export"}) == "export:X"
    )
    with pytest.raises(ValueError):
        customer_identity({"customer": "X", "customer_type": "unknown"})


def test_dash_layout_and_plotly_keep_figures_read_only(tmp_path, bundle):
    from src.visualization.app import create_app

    db, key = prepared(tmp_path, bundle)
    before = db.read_bytes()
    app = create_app(db, key)
    assert app.server.test_client().get("/_dash-layout").status_code == 200
    f = g.figure_definition(db, key, population=300, case_id="accepted")
    assert g.plotly_figure(f).layout.meta["figure_sha256"] == f["figure_sha256"]
    callback = next(
        v["callback"].__wrapped__ for k, v in app.callback_map.items() if "map.figure" in k
    )
    figure, qualification = callback(215, "accepted", "Soja", "old", "high", 300)
    assert figure.layout.meta["figure_sha256"]
    assert json.loads(qualification)["evidence_status"] == "availability_only"
    assert db.read_bytes() == before


@pytest.mark.parametrize("extension", ["pdf", "png"])
def test_static_formats_need_no_browser(tmp_path, bundle, extension):
    db, key = prepared(tmp_path, bundle)
    f = g.figure_definition(db, key, population=300, case_id="accepted")
    out = tmp_path / ("map." + extension)
    render(f, out)
    if extension == "pdf":
        from pypdf import PdfReader

        assert len(PdfReader(out).pages) == 1
        assert "SYNTHETIC FIXTURE" in PdfReader(out).pages[0].extract_text()
    else:
        from PIL import Image

        assert Image.open(out).size == (1200, 850)
