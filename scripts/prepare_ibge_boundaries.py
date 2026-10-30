"""Explicit local IBGE preparation; original archives are verified, never downloaded here."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import zipfile
from pathlib import Path

from src.visualization.cartography import (
    DISPLAY_EXTENT,
    PROJECTION,
    prepare_context,
    validate_context,
)
from src.visualization.geography import digest, require

SOURCES = {
    "BR_UF_2023.zip": "5273fc6a3add9f3f18dbbcf4d844a03f9ed0c76a1fe779ce03cfff313488460c",
    "BR_Pais_2023.zip": "d2f70a0f009960031e64253be4a22638186e23a858e0baa3d50aff0d38b209f6",
}
BASE = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/"
    "malhas_municipais/municipio_2023/Brasil/"
)
LEGAL = "https://www.ibge.gov.br/biblioteca/visualizacao/livros/liv102152.pdf"


def build(archives, tolerance=1000.0):
    # Preparation-only dependencies. No GIS package is needed to read the SQLite cache.
    import pyproj
    import shapefile
    import shapely
    from shapely.geometry import mapping, shape
    from shapely.ops import transform

    require(tolerance == 1000.0, "This version fixes coverage simplification to 1000 m")
    original, features, crs_texts = {}, {}, {}
    for name, expected in SOURCES.items():
        raw = (Path(archives) / name).read_bytes()
        require(hashlib.sha256(raw).hexdigest() == expected, "Original IBGE archive hash differs")
        with zipfile.ZipFile(Path(archives) / name) as z:
            names = z.namelist()

            def stream(ext, names=names, z=z):
                return z.open(next(n for n in names if n.endswith(ext)))

            reader = shapefile.Reader(shp=stream(".shp"), dbf=stream(".dbf"), encoding="utf-8")
            crs = z.read(next(n for n in names if n.endswith(".prj"))).decode()
            require(pyproj.CRS.from_wkt(crs).to_epsg() == 4674, "IBGE source CRS differs")
            crs_texts[name] = crs
            rows = [
                (r.record.as_dict(), shape(r.shape.__geo_interface__))
                for r in reader.iterShapeRecords()
            ]
            original[name] = rows
    ufs = original["BR_UF_2023.zip"]
    national = original["BR_Pais_2023.zip"]
    require(len(ufs) == 27 and len(national) == 1, "IBGE cardinalities differ")
    geoms = [g for _, g in ufs]
    require(all(g.is_valid for g in geoms), "Invalid original UF geometry")
    require(bool(shapely.coverage_is_valid(geoms)), "Original UF edges do not form a coverage")
    union = shapely.union_all(geoms)
    require(union.equals(national[0][1]), "Original country is not the UF union")
    to_metric = pyproj.Transformer.from_crs(4674, 5880, always_xy=True)
    to_wgs = pyproj.Transformer.from_crs(5880, 4326, always_xy=True)
    projected = [transform(to_metric.transform, g) for g in geoms]
    simple = list(shapely.coverage_simplify(projected, tolerance, simplify_boundary=True))
    require(bool(shapely.coverage_is_valid(simple)), "Simplified UF coverage invalid")
    require(all(g.is_valid and not g.is_empty for g in simple), "Simplified polygon invalid")
    normalized = [transform(to_wgs.transform, g) for g in simple]
    country = shapely.union_all(normalized)
    # Stable ordered features, full precision retained: no independent ring rounding.
    for (record, before), geom in zip(ufs, normalized, strict=True):
        geometry = json.loads(json.dumps(mapping(geom)))
        features[record["CD_UF"]] = {
            "id": record["CD_UF"],
            "level": "UF",
            "name": record["NM_UF"],
            "abbreviation": record["SIGLA_UF"],
            "geometry": geometry,
            "original_geometry_sha256": hashlib.sha256(shapely.to_wkb(before)).hexdigest(),
            "geometry_sha256": digest(geometry),
        }
    geometry = json.loads(json.dumps(mapping(country)))
    features["BR"] = {
        "id": "BR",
        "level": "country",
        "name": "Brasil",
        "geometry": geometry,
        "original_geometry_sha256": hashlib.sha256(shapely.to_wkb(national[0][1])).hexdigest(),
        "geometry_sha256": digest(geometry),
    }
    context = {
        "schema_version": "ibge-cartographic-context-v1",
        "reference_year": 2023,
        "publication_year": 2024,
        "publication_year_basis": "IBGE technical/legal notes 01/2024; archive members dated 2024",
        "source_crs": "EPSG:4674",
        "display_source_crs": "EPSG:4326",
        "simplification_crs": "EPSG:5880",
        "projection": PROJECTION,
        "geographic_extent": list(DISPLAY_EXTENT),
        "license": "CC-BY-4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "legal_source": LEGAL,
        "attribution": "IBGE (2023), adapted; CC BY 4.0",
        "sources": [{"url": BASE + name, "sha256": sha} for name, sha in SOURCES.items()],
        "source_crs_wkt": crs_texts,
        "simplification": {
            "method": "GEOS topology-preserving coverage Visvalingam-Whyatt",
            "tolerance_m": tolerance,
            "qualification": "Tolerance controls triangle-area scale, not a maximum displacement.",
            "shared_edges_preserved": True,
            "additional_coordinate_rounding": False,
        },
        "preparation_versions": {
            "shapely": shapely.__version__,
            "GEOS": shapely.geos_version_string,
            "pyproj": pyproj.__version__,
            "PROJ": pyproj.proj_version_str,
            "pyshp": shapefile.__version__,
        },
        "validation": {
            "original_uf_coverage_valid": True,
            "original_country_equals_union": True,
            "simplified_uf_coverage_valid": True,
            "country_derived_from_simplified_uf_union": True,
            "original_vertices": sum(int(shapely.get_num_coordinates(g)) for g in geoms),
            "simplified_vertices": sum(int(shapely.get_num_coordinates(g)) for g in normalized),
            "relative_area_change": (
                shapely.union_all(simple).area / shapely.union_all(projected).area - 1
            ),
        },
        "features": [features[k] for k in sorted(features)],
    }
    return validate_context({**context, "dataset_sha256": digest(context)})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archives", type=Path)
    p.add_argument("--context", type=Path)
    p.add_argument("--output", type=Path)
    p.add_argument("--sqlite", type=Path, required=True)
    a = p.parse_args()
    require(bool(a.context) != bool(a.archives), "Select frozen context OR original archives")
    if a.context:
        raw = a.context.read_bytes()
        if a.context.suffix == ".gz":
            raw = gzip.decompress(raw)
        context = validate_context(json.loads(raw))
    else:
        context = build(a.archives)
        require(a.output is not None and not a.output.exists(), "New context output required")
        a.output.parent.mkdir(parents=True, exist_ok=True)
        payload = (
            json.dumps(context, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
        ).encode("utf-8")
        a.output.write_bytes(
            gzip.compress(payload, mtime=0) if a.output.suffix == ".gz" else payload
        )
    key, created = prepare_context(a.sqlite, context)
    print(
        json.dumps(
            {
                "boundary_dataset": key,
                "prepared": created,
                "UFs": 27,
                "network_access": False,
                "solver_executed": False,
            }
        )
    )


if __name__ == "__main__":
    main()
