"""Data/custody failure controls; no solver or NPAD connection."""

import hashlib
import importlib.util
import json
import math
import os
import sqlite3
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "t2_reconcile", ROOT / "scripts/t2/reconcile_inputs.py"
)
T2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(T2)


def xlsx(path, cells, extra=()):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(
            "xl/workbook.xml",
            '<workbook xmlns="' + T2.NS[1:-1] + '" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Test" sheetId="1" r:id="r1"/></sheets></workbook>',
        )
        z.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships><Relationship Id="r1" Target="worksheets/sheet1.xml"/></Relationships>',
        )
        z.writestr(
            "xl/worksheets/sheet1.xml",
            '<worksheet xmlns="'
            + T2.NS[1:-1]
            + '"><sheetData><row r="1">'
            + cells
            + "</row></sheetData></worksheet>",
        )
        for name, value in extra:
            z.writestr(name, value)


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_read_is_byte_stable_and_no_write(self):
        p = self.root / "source"
        p.write_bytes(b"original")
        before = p.stat()
        self.assertEqual(T2.read_stable(p), b"original")
        self.assertEqual(before.st_mtime_ns, p.stat().st_mtime_ns)

    def test_read_budget_rejects(self):
        p = self.root / "source"
        p.write_bytes(b"123")
        with self.assertRaisesRegex(ValueError, "oversized"):
            T2.read_stable(p, 2)

    def test_changed_identity_rejected(self):
        p = self.root / "source"
        p.write_bytes(b"original")
        with patch.object(T2, "stamp", side_effect=[("one",), ("two",)]):
            with self.assertRaisesRegex(ValueError, "changed"):
                T2.read_stable(p)

    def test_sparse_cell_does_not_shift(self):
        p = self.root / "book.xlsx"
        xlsx(p, '<c r="A1" t="inlineStr"><is><t>ID</t></is></c><c r="C1"><v>0</v></c>')
        self.assertEqual(list(T2.Workbook(p).rows("Test")), [["ID", None, 0.0]])

    def test_formula_requires_review_even_with_cache(self):
        p = self.root / "book.xlsx"
        xlsx(p, '<c r="A1"><f>1+1</f><v>2</v></c>')
        with self.assertRaisesRegex(ValueError, "Formula"):
            list(T2.Workbook(p).rows("Test"))

    def test_excel_error_rejected(self):
        p = self.root / "book.xlsx"
        xlsx(p, '<c r="A1" t="e"><v>#REF!</v></c>')
        with self.assertRaisesRegex(ValueError, "error"):
            list(T2.Workbook(p).rows("Test"))

    def test_nonfinite_value_rejected(self):
        p = self.root / "book.xlsx"
        xlsx(p, '<c r="A1"><v>nan</v></c>')
        with self.assertRaisesRegex(ValueError, "Nonfinite"):
            list(T2.Workbook(p).rows("Test"))

    def test_missing_and_zero_remain_distinct(self):
        p = self.root / "book.xlsx"
        xlsx(p, '<c r="A1"/><c r="B1"><v>0</v></c>')
        self.assertEqual(list(T2.Workbook(p).rows("Test")), [[None, 0.0]])

    def test_duplicate_header_rejected(self):
        p = self.root / "book.xlsx"
        xlsx(
            p,
            '<c r="A1" t="inlineStr"><is><t>ID</t></is></c>'
            '<c r="B1" t="inlineStr"><is><t>ID</t></is></c>',
        )
        with self.assertRaisesRegex(ValueError, "header"):
            list(T2.Workbook(p).records("Test"))

    def test_live_sqlite_header_never_connects(self):
        p = self.root / "policy-pairs-v020.sqlite3"
        header = bytearray(100)
        header[:16] = b"SQLite format 3\x00"
        header[18:20] = b"\x02\x02"
        p.write_bytes(header)
        wal = Path(str(p) + "-wal")
        wal.write_bytes(b"untouched WAL")
        with patch.object(
            T2.sqlite3, "connect", side_effect=AssertionError("live open")
        ):
            result = T2.cache_header(p)
        self.assertEqual(result["header_journal_hint"], "wal")
        self.assertIsNone(result["consistent_database_sha256"])
        self.assertEqual(wal.read_bytes(), b"untouched WAL")

    def test_bad_sqlite_header_rejected(self):
        p = self.root / "cache.sqlite3"
        p.write_bytes(b"not SQLite")
        with self.assertRaisesRegex(ValueError, "header"):
            T2.cache_header(p)

    def test_discovery_refuses_secret_directory(self):
        secrets = self.root / "secrets"
        secrets.mkdir()
        (secrets / next(iter(T2.PINS))).write_bytes(b"secret")
        result = T2.discover([self.root])
        self.assertEqual(result["candidates"], [])

    def test_discovery_missing_root_reported(self):
        result = T2.discover([self.root / "absent"])
        self.assertEqual(result["status"], "inventory_with_omissions")
        self.assertEqual(result["errors"][0]["reason"], "missing_root")

    def test_discovery_bound_is_not_complete(self):
        result = T2.discover([self.root], max_entries=0)
        self.assertEqual(result["status"], "bounded_partial_inventory")

    def test_exclusive_report_does_not_overwrite(self):
        p = self.root / "report.json"
        T2.dump(p, {"original": True})
        with self.assertRaises(FileExistsError):
            T2.dump(p, {"original": False})
        self.assertTrue(json.loads(p.read_text())["original"])

    def test_report_archive_ledger(self):
        T2.finish(self.root, {"status": "test"})
        ledger = (self.root / "SHA256SUMS").read_text().strip().split("  ")
        self.assertEqual(
            ledger[0], hashlib.sha256((self.root / ledger[1]).read_bytes()).hexdigest()
        )
        self.assertEqual(len(list(self.root.glob("*.tar.gz.sha256"))), 1)

    def fixture_cache(self, *, extra_identity=False, distance=1000.0):
        db = sqlite3.connect(":memory:")
        db.execute(
            "CREATE TABLE osrm_pair_cache(cache_key TEXT, key_payload_json TEXT, "
            "distance_m REAL, source TEXT, data_version TEXT)"
        )
        payload = {"origin": [1, 2], "destination": [3, 4], "dataset_id": "route-v1"}
        for _ in range(2 if extra_identity else 1):
            text = json.dumps(
                payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            )
            db.execute(
                "INSERT INTO osrm_pair_cache VALUES(?,?,?,?,?)",
                (T2.digest(text.encode()), text, distance, "osrm", "v1"),
            )
            payload["dataset_id"] = "different-routing-version"
        db.commit()
        p = self.root / "offline.sqlite3"
        p.write_bytes(db.serialize())
        db.close()
        (self.root / "nodes.json").write_text(
            json.dumps(
                {
                    "215:sto": {
                        "a": {"latitude": 1, "longitude": 2},
                        "b": {"latitude": 3, "longitude": 4},
                    }
                }
            )
        )
        (self.root / "arcs.csv").write_text(
            "population,origin_id,destination_id,osrm_distance_km\n215,a,b,1.0\n"
        )
        sha = T2.digest(p.read_bytes())
        acquisition = self.root / "acquisition.json"
        acquisition.write_text(
            json.dumps(
                {
                    "consistent_snapshot": True,
                    "snapshot_sha256": sha,
                    "method": "sqlite_backup",
                    "source_path": "/source",
                    "captured_utc": "2026-11-23T00:00:00Z",
                }
            )
        )
        return p, sha, acquisition

    def test_offline_cache_distance_conversion_once(self):
        p, sha, receipt = self.fixture_cache()
        before = p.read_bytes()
        result = T2.cache_crosswalk(p, sha, self.root, receipt)
        self.assertEqual(
            result["arc_comparison"], {"distance_equal_provenance_review_pending": 1}
        )
        self.assertEqual(p.read_bytes(), before)
        self.assertFalse(Path(str(p) + "-wal").exists())

    def test_multiple_routing_versions_stay_ambiguous(self):
        p, sha, receipt = self.fixture_cache(extra_identity=True)
        result = T2.cache_crosswalk(p, sha, self.root, receipt)
        self.assertEqual(result["arc_comparison"], {"ambiguous_routing_identity": 1})

    def test_distance_disagreement_not_rounded_away(self):
        p, sha, receipt = self.fixture_cache(distance=1000.0000001)
        result = T2.cache_crosswalk(p, sha, self.root, receipt)
        self.assertEqual(result["arc_comparison"], {"distance_differs": 1})

    def test_historical_negative_roundoff_is_bounded(self):
        for raw in (-1.0, -0.4, -0.2):
            with self.subTest(raw=raw):
                self.assertEqual(T2.effective_cache_distance(raw), (0.0, True))
        self.assertEqual(T2.effective_cache_distance(0.0), (0.0, False))
        self.assertEqual(T2.effective_cache_distance(1000.0), (1.0, False))

    def test_invalid_cache_distance_is_not_normalised(self):
        for raw in (-1.000001, float("nan"), float("inf"), True, None, "1"):
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, "Invalid"):
                T2.effective_cache_distance(raw)

    def test_normalised_cache_matches_zero_without_source_write(self):
        p, sha, receipt = self.fixture_cache(distance=-0.4)
        (self.root / "arcs.csv").write_text(
            "population,origin_id,destination_id,osrm_distance_km\n215,a,b,0.0\n"
        )
        before = p.read_bytes()
        result = T2.cache_crosswalk(p, sha, self.root, receipt)
        self.assertEqual(
            result["arc_comparison"], {"distance_equal_provenance_review_pending": 1}
        )
        self.assertEqual(result["normalised_cache_records"], 1)
        self.assertEqual(result["selected_arc_records_using_normalisation"], 1)
        self.assertEqual(p.read_bytes(), before)
        self.assertFalse(result["raw_cache_or_frozen_arc_values_changed"])
        self.assertIn("pending", result["cache_identity_acceptance"])

    def test_adjacent_positive_unit_conversion_is_reported_separately(self):
        value = 1234.5678
        adjacent = math.nextafter(value, math.inf)
        self.assertEqual(
            T2.distance_comparison(value, adjacent),
            "distance_equal_unit_conversion_roundoff_provenance_review_pending",
        )

    def test_larger_difference_and_zero_remain_distinct(self):
        value = 1234.5678
        twice = math.nextafter(math.nextafter(value, math.inf), math.inf)
        self.assertEqual(T2.distance_comparison(value, twice), "distance_differs")
        self.assertEqual(T2.distance_comparison(0.0, math.ulp(0.0)), "distance_differs")

    def test_nonfinite_or_negative_effective_values_fail(self):
        for value in (-0.1, float("nan"), float("inf"), None, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                T2.distance_comparison(value, 0.0)

    def test_crosswalk_retains_unit_conversion_classification_by_population(self):
        p, sha, receipt = self.fixture_cache(distance=1234567.8)
        cache_km, _ = T2.effective_cache_distance(1234567.8)
        frozen = math.nextafter(cache_km, math.inf)
        (self.root / "arcs.csv").write_text(
            "population,origin_id,destination_id,osrm_distance_km\n"
            f"215,a,b,{frozen!r}\n"
        )
        result = T2.cache_crosswalk(p, sha, self.root, receipt)
        label = "distance_equal_unit_conversion_roundoff_provenance_review_pending"
        self.assertEqual(result["arc_comparison_by_population"], {"215": {label: 1}})
        self.assertGreater(result["maximum_conversion_delta_km"], 0.0)
        self.assertIn("pending", result["cache_identity_acceptance"])

    def test_snapshot_hash_mismatch_rejected(self):
        p, _, receipt = self.fixture_cache()
        with self.assertRaises(ValueError):
            T2.cache_crosswalk(p, "0" * 64, self.root, receipt)

    def test_snapshot_sidecar_rejected(self):
        p, sha, receipt = self.fixture_cache()
        Path(str(p) + "-wal").write_bytes(b"committed data")
        with self.assertRaisesRegex(ValueError, "sidecars"):
            T2.cache_crosswalk(p, sha, self.root, receipt)

    def test_acquisition_evidence_required(self):
        p, sha, receipt = self.fixture_cache()
        receipt.write_text("{}")
        with self.assertRaisesRegex(ValueError, "acquisition"):
            T2.cache_crosswalk(p, sha, self.root, receipt)

    def test_invalid_integer_types_rejected(self):
        for value in (True, None, 0.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                T2.integer(value)

    def test_script_imports_no_solver_or_process_runner(self):
        import ast

        tree = ast.parse((ROOT / "scripts/t2/reconcile_inputs.py").read_text())
        names = [n.names[0].name for n in ast.walk(tree) if isinstance(n, ast.Import)]
        self.assertFalse({"subprocess", "gurobipy", "pyomo", "requests"} & set(names))
        self.assertNotIn("gurobipy", sys.modules)

    def test_linux_no_follow_rejects_symlink(self):
        if os.name == "nt":
            return  # Linux CI exercises the actual symlink syscall.
        p = self.root / "source"
        p.write_bytes(b"original")
        link = self.root / "link"
        link.symlink_to(p)
        with self.assertRaisesRegex(ValueError, "Symlink"):
            T2.read_stable(link)

    def test_new_paths_route_without_native_solver_jobs(self):
        spec = importlib.util.spec_from_file_location(
            "scope", ROOT / "scripts/effective_ci_scope.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        paths = [
            "scripts/t2/reconcile_inputs.py",
            "scripts/t2/npad_t2_verify.sh",
            "tests/t2/test_reconciliation.py",
            ".github/workflows/t2-reconciliation.yml",
            "docs/mvp3_t3_protocol_readiness_20261123.md",
        ]
        self.assertTrue(module.classify(paths)["data_only"])
        self.assertFalse(
            module.classify(paths + ["src/logic/optimization_gurobipy.py"])["data_only"]
        )
        self.assertFalse(module.classify(paths + ["pyproject.toml"])["data_only"])

    def test_t3_engineering_does_not_activate_an_experiment(self):
        doc = json.loads(
            (ROOT / "docs/evidence/mvp3_t3_readiness_20261123.json").read_text()
        )
        self.assertFalse(doc["executable"])
        self.assertFalse(doc["submit_jobs"])
        self.assertTrue(doc["development_before_coauthor_agreement"])
        self.assertTrue(doc["platform"]["cpu_only"])
        self.assertEqual(
            (doc["platform"]["Method"], doc["platform"]["Threads"]), (-1, 0)
        )


if __name__ == "__main__":
    unittest.main()
