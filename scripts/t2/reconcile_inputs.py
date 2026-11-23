"""Read-only MVP3 input custody and reconciliation. Standard library only.

Never imports a solver, writes source workbooks, opens a LIVE SQLite engine,
requests routes or executes a scheduler. Reports remain private until reviewed.
"""

from __future__ import annotations

import argparse
import collections
import contextlib
import csv
import hashlib
import io
import json
import math
import os
import platform
import posixpath
import sqlite3
import stat
import sys
import tarfile
import tempfile
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

AUDIT = Path("/home/vrrcelestino/model-agrologistic-hygiene-audit")
ROOTS = tuple(
    Path("/home/vrrcelestino") / n
    for n in (
        "model-agrologistic",
        "model-agrologistic-hygiene-audit",
        "model-agrologistic-inputs",
        "model-agrologistic-quarantine",
        "model-agrologistic-scientific-archive",
        "osrm-agrologistic",
    )
)
PINS = {
    "agrologistic_effective_baseline_v1.xlsx": (
        "d5babec48bb40a61843ccb4e7c9c059429b4d8ac32cefec945fda4e4fb84c917"
    ),
    "agrologistic_warehouse_registry_v1.xlsx": (
        "f39c2f29862aecb9a64fd0d37548eb788e402c805a5db6def6c5ec8a351d25bc"
    ),
}
ARC_COUNTS = {215: 25112, 300: 45240, 400: 76320, 500: 115400}
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
SKIP = {
    ".git",
    ".aws",
    ".ssh",
    ".venv",
    "venv",
    "venv313",
    "venv313_g14",
    "node_modules",
    "site-packages",
    "secrets",
    "__pycache__",
}
MAX_FILE = 128 * 1024**2


def require(condition, message):
    if not condition:
        raise ValueError(message)


def clean_path(path):
    path = Path(os.path.abspath(path))
    for part in (path, *path.parents):
        require(not part.is_symlink(), "Symlink path refused")
    return path


def stamp(st):
    return (
        st.st_dev,
        st.st_ino,
        st.st_size,
        st.st_mtime_ns,
        st.st_ctime_ns if os.name != "nt" else None,
    )


def read_stable(path, limit=MAX_FILE):
    path = clean_path(path)
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        require(
            stat.S_ISREG(before.st_mode) and before.st_size <= limit,
            "Non-regular or oversized input",
        )
        raw = stream.read(limit + 1)
        require(len(raw) <= limit, "Input read budget exceeded")
        require(
            stamp(before) == stamp(os.fstat(stream.fileno())) == stamp(path.stat()),
            "Input changed while reading",
        )
    return raw


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def dump(path, value):
    raw = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    with Path(path).open("x", encoding="utf-8") as stream:
        stream.write(raw)


class Workbook:
    """Value-only reader with sparse cell coordinates and bounded ZIP members."""

    def __init__(self, path):
        self.raw = read_stable(path)
        self.sha256 = digest(self.raw)
        self.archive = zipfile.ZipFile(io.BytesIO(self.raw))
        members = self.archive.infolist()
        require(
            len({m.filename for m in members}) == len(members), "Duplicate ZIP member"
        )
        require(
            len(members) < 1000 and sum(m.file_size for m in members) < 256 * 1024**2,
            "XLSX expansion budget exceeded",
        )
        require(all(m.file_size <= MAX_FILE for m in members), "XLSX member too large")
        self.shared = []
        if "xl/sharedStrings.xml" in self.archive.namelist():
            self.shared = [
                "".join(n.itertext())
                for n in ET.fromstring(self.archive.read("xl/sharedStrings.xml"))
            ]
        rels = {
            r.attrib["Id"]: r.attrib["Target"]
            for r in ET.fromstring(self.archive.read("xl/_rels/workbook.xml.rels"))
        }
        self.sheets = {}
        book = ET.fromstring(self.archive.read("xl/workbook.xml"))
        for sh in book.find(NS + "sheets"):
            key = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
            target = rels[sh.attrib[key]]
            target = (
                target.lstrip("/")
                if target.startswith("/")
                else posixpath.normpath("xl/" + target)
            )
            require(
                target.startswith("xl/") and ".." not in target.split("/"),
                "Unsafe XLSX relationship",
            )
            require(sh.attrib["name"] not in self.sheets, "Duplicate sheet")
            self.sheets[sh.attrib["name"]] = target

    def rows(self, name):
        with self.archive.open(self.sheets[name]) as stream:
            for _, node in ET.iterparse(stream, events=["end"]):
                if node.tag != NS + "row":
                    continue
                cells = {}
                for c in node:
                    require(
                        c.find(NS + "f") is None, "Formula requires explicit review"
                    )
                    address = c.attrib["r"]
                    letters = "".join(x for x in address if x.isalpha())
                    column = 0
                    for letter in letters:
                        column = column * 26 + ord(letter) - ord("A") + 1
                    require(0 < column <= 256, "Column budget exceeded")
                    v = c.find(NS + "v")
                    value = v.text if v is not None else None
                    kind = c.attrib.get("t")
                    if kind == "s":
                        value = self.shared[int(value)] if value is not None else None
                    elif kind == "inlineStr":
                        value = "".join(c.find(NS + "is").itertext())
                    elif value is not None and kind not in ("str", "e"):
                        value = float(value)
                        require(math.isfinite(value), "Nonfinite XLSX value")
                        if kind == "b":
                            value = bool(value)
                    require(kind != "e", "XLSX error cell")
                    require(column not in cells, "Duplicate XLSX cell")
                    cells[column] = value
                yield [cells.get(i) for i in range(1, max(cells, default=0) + 1)]
                node.clear()

    def records(self, name):
        rows = self.rows(name)
        header = next(rows)
        require(len(header) == len(set(header)), "Duplicate header")
        for row in rows:
            require(len(row) <= len(header), "Unexpected extra column")
            if any(v is not None for v in row):
                yield dict(
                    zip(header, row + [None] * (len(header) - len(row)), strict=True)
                )


def integer(value):
    require(
        not isinstance(value, bool) and value is not None and float(value).is_integer(),
        "Expected integer",
    )
    return int(value)


def reconcile_workbooks(effective, registry, support=None):
    wb, reg = Workbook(effective), Workbook(registry)
    require(
        wb.sha256 == PINS[Path(effective).name]
        and reg.sha256 == PINS[Path(registry).name],
        "Review workbook hash differs",
    )
    identification = {r["item"]: r["value"] for r in wb.records("Identification")}
    require(
        identification["schema"] == "agrologistic-effective-baseline-v1",
        "Unknown effective schema",
    )
    calendar = list(wb.records("Calendar"))
    require(
        [(r["period"], r["operating_days"], r["unit"]) for r in calendar]
        == [
            (f"{y}-{m:02}", 30, "day/period")
            for y in range(2021, 2026)
            for m in range(1, 13)
        ],
        "Calendar or daily conversion differs",
    )
    sets = collections.defaultdict(list)
    for r in wb.records("Sets"):
        key = (integer(r["population"]), r["mode"], r["field"])
        require(integer(r["position"]) == len(sets[key]), "Set order differs")
        require(r["value"] not in sets[key], "Duplicate set member")
        sets[key].append(r["value"])
    records = list(reg.records("Registry"))
    ids = [r["CDA"] for r in records]
    require(
        len(ids) == len(set(ids)) == 18086
        and all(isinstance(x, str) and x for x in ids),
        "Registry CDA cardinality or type differs",
    )
    by_id = dict(zip(ids, records, strict=True))
    results = {}
    for population in ARC_COUNTS:
        expected = sets[population, "sto", "warehouses"]
        existing = sets[population, "sto", "existing_warehouses"]
        candidates = sets[population, "sto", "candidate_warehouses"]
        require(
            len(expected) == population
            and len(existing) == 146
            and len(candidates) == population - 146,
            "Population cardinality differs",
        )
        require(
            not set(existing) & set(candidates)
            and set(expected) == set(existing) | set(candidates),
            "Role partition differs",
        )
        flags = []
        for row in records:
            flag = integer(row[f"Em_h{population}"])
            require(flag in (0, 1), "Nonbinary membership")
            order = row[f"order_h{population}"]
            if flag:
                flags.append((integer(order), row["CDA"]))
            else:
                require(order is None, "Absent facility has selection order")
        require(
            [x[0] for x in sorted(flags)] == list(range(population))
            and [x[1] for x in sorted(flags)] == expected,
            "Registry order differs from Sets",
        )
        for cda in candidates:
            require(
                all(
                    by_id[cda][k] == 0
                    for k in ("model_K0_t", "model_R0_t_day", "model_H0_t_day")
                ),
                "Candidate initial capacity is nonzero",
            )
        results[str(population)] = {
            "existing": len(existing),
            "candidates": len(candidates),
            "ordered_membership": "matched",
        }
    require(
        sets[215, "det", "warehouses"] == sets[215, "sto", "warehouses"],
        "h215 DET/STO membership differs",
    )
    references = list(wb.records("NetworkReferences"))
    support_result = {
        "status": "pending_support_files",
        "required_names": [r["file"] for r in references],
    }
    if support is not None:
        support = clean_path(support)
        for r in references:
            require(Path(r["file"]).name == r["file"], "Unsafe support name")
            require(
                digest(read_stable(support / r["file"])) == r["sha256"],
                "Support hash differs: " + r["file"],
            )
        support_result = {"status": "four_workbook_references_matched"}
    return {
        "workbook_hashes": {
            Path(effective).name: wb.sha256,
            Path(registry).name: reg.sha256,
        },
        "calendar": "matched",
        "registry_records": len(ids),
        "populations": results,
        "support": support_result,
        "model_data_equivalence": "not_run",
        "algebra_equivalence": "not_run",
        "final_mvp3_input_accepted": False,
    }


def cache_header(path):
    """No SQLite engine connection to live source; WAL/SHM are never changed."""
    path = clean_path(path)
    st = path.stat()
    require(stat.S_ISREG(st.st_mode), "SQLite source is not regular")
    with path.open("rb") as stream:
        header = stream.read(100)
    require(
        header[:16] == b"SQLite format 3\x00" and len(header) == 100,
        "Invalid SQLite header",
    )
    sidecars = {}
    for suffix in ("-wal", "-shm", "-journal"):
        p = Path(str(path) + suffix)
        if p.exists() or p.is_symlink():
            clean_path(p)
            s = p.stat()
            sidecars[suffix] = {"bytes": s.st_size, "mtime_ns": s.st_mtime_ns}
    return {
        "path": str(path),
        "bytes": st.st_size,
        "header_sha256": digest(header),
        "read_version": header[19],
        "write_version": header[18],
        "header_journal_hint": "wal"
        if header[18:20] == b"\x02\x02"
        else "rollback_or_other",
        "sidecars": sidecars,
        "consistent_database_sha256": None,
        "status": "snapshot_method_review_pending",
        "live_engine_opened": False,
    }


def cache_crosswalk(snapshot, expected_sha, support, acquisition):
    """Inspect an explicitly supplied OFFLINE, single-file consistent snapshot.

    Caller must supply its acquisition receipt. Never call on the live cache.
    An in-memory deserialize prevents SQLite from creating files by the source.
    """
    receipt = json.loads(read_stable(acquisition, limit=1024**2))
    require(
        receipt.get("consistent_snapshot") is True
        and receipt.get("snapshot_sha256") == expected_sha
        and receipt.get("method") == "sqlite_backup"
        and receipt.get("source_path")
        and receipt.get("captured_utc"),
        "Consistent backup acquisition receipt required",
    )
    raw = read_stable(snapshot, limit=512 * 1024**2)
    require(digest(raw) == expected_sha, "Snapshot SHA differs")
    require(raw[:16] == b"SQLite format 3\x00", "Not SQLite")
    for suffix in ("-wal", "-shm", "-journal"):
        require(not Path(str(snapshot) + suffix).exists(), "Snapshot has sidecars")
    require(
        hasattr(sqlite3.Connection, "deserialize"), "SQLite deserialize unavailable"
    )
    with contextlib.closing(sqlite3.connect(":memory:")) as db:
        db.deserialize(raw)
        db.execute("PRAGMA query_only=ON")
        require(
            db.execute("PRAGMA quick_check").fetchall() == [("ok",)],
            "Snapshot structural check failed",
        )
        columns = {r[1] for r in db.execute("PRAGMA table_info(osrm_pair_cache)")}
        required = {
            "cache_key",
            "key_payload_json",
            "distance_m",
            "source",
            "data_version",
        }
        require(required <= columns, "Unknown OSRM cache schema")
        lookup = collections.defaultdict(list)
        bad_keys = 0
        for key, payload, distance, source, version in db.execute(
            "SELECT cache_key,key_payload_json,distance_m,source,data_version FROM osrm_pair_cache"
        ):
            parsed = json.loads(payload)
            canonical = json.dumps(
                parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            )
            if digest(canonical.encode()) != key:
                bad_keys += 1
            require(
                isinstance(distance, (int, float))
                and math.isfinite(distance)
                and distance >= 0,
                "Invalid cache distance",
            )
            pair = (tuple(parsed["origin"]), tuple(parsed["destination"]))
            lookup[pair].append((distance / 1000.0, source, version, key))
        require(bad_keys == 0, "Cache payload/key disagreement")
        nodes = json.loads(read_stable(Path(support) / "nodes.json"))
        counts = collections.Counter()
        with io.StringIO(
            read_stable(Path(support) / "arcs.csv").decode("utf-8")
        ) as stream:
            for row in csv.DictReader(stream):
                scope = row["population"] + ":sto"
                endpoints = [
                    nodes[scope][row[k]] for k in ("origin_id", "destination_id")
                ]
                pair = tuple((n["latitude"], n["longitude"]) for n in endpoints)
                matches = lookup.get(pair, [])
                # Multiple routing identities must not be collapsed by coordinates alone.
                if not matches:
                    label = "missing_pair"
                elif len(matches) != 1:
                    label = "ambiguous_routing_identity"
                elif matches[0][1] != "osrm":
                    label = "non_osrm_source"
                elif float(row["osrm_distance_km"]) != matches[0][0]:
                    label = "distance_differs"
                else:
                    label = "distance_equal_provenance_review_pending"
                counts[label] += 1
        return {
            "sqlite_version": sqlite3.sqlite_version,
            "snapshot_sha256": expected_sha,
            "cache_records": sum(map(len, lookup.values())),
            "arc_comparison": dict(counts),
            "cache_identity_acceptance": "pending_routing_provenance_and_acquisition_review",
            "unit_conversion": "distance_m / 1000 once",
            "source_engine_opened": False,
        }


def discover(roots, max_entries=180000, max_seconds=600):
    started = time.monotonic()
    found, errors, visited = [], [], 0
    for root in roots:
        if not root.exists():
            errors.append({"path": str(root), "reason": "missing_root"})
            continue
        clean_path(root)
        for directory, dirs, files in os.walk(
            root,
            followlinks=False,
            onerror=lambda e: errors.append(
                {"path": e.filename, "reason": type(e).__name__}
            ),
        ):
            dirs[:] = sorted(
                n for n in dirs if n not in SKIP and not Path(directory, n).is_symlink()
            )
            visited += 1 + len(files)
            if visited > max_entries or time.monotonic() - started > max_seconds:
                return {
                    "status": "bounded_partial_inventory",
                    "candidates": found,
                    "errors": errors,
                    "entries": visited,
                }
            for name in files:
                path = Path(directory, name)
                if name not in PINS and name != "policy-pairs-v020.sqlite3":
                    continue
                try:
                    if name in PINS:
                        value = digest(read_stable(path))
                        found.append(
                            {
                                "path": str(path),
                                "sha256": value,
                                "matches_review_copy": value == PINS[name],
                            }
                        )
                    else:
                        found.append(cache_header(path))
                except (OSError, ValueError) as e:
                    errors.append({"path": str(path), "reason": str(e)})
            if {"manifest.json", "nodes.json", "arcs.csv"} <= set(files):
                found.append(
                    {
                        "path": directory,
                        "kind": "effective_support_candidate",
                        "identity": "not_yet_verified",
                    }
                )
    return {
        "status": "inventory_finished" if not errors else "inventory_with_omissions",
        "candidates": found,
        "errors": errors,
        "entries": visited,
    }


def finish(output, report):
    dump(output / "report.json", report)
    files = [p for p in output.iterdir() if p.is_file()]
    ledger = "".join(f"{digest(p.read_bytes())}  {p.name}\n" for p in sorted(files))
    (output / "SHA256SUMS").write_text(ledger, encoding="utf-8")
    archive = output / "t2-reconciliation-reports.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for path in [*files, output / "SHA256SUMS"]:
            tar.add(path, arcname=path.name, recursive=False)
    sha = digest(archive.read_bytes())
    (output / (archive.name + ".sha256")).write_text(
        sha + "  " + archive.name + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "transfer_dir": str(output),
                "archive": str(archive),
                "sha256": sha,
                "status": report["status"],
                "jobs_submitted": 0,
                "shared_environment_changed": False,
            }
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inventory", "reconcile"))
    parser.add_argument("--controller-sha256", required=True)
    parser.add_argument("--workbook")
    parser.add_argument("--registry")
    parser.add_argument("--support")
    parser.add_argument("--snapshot")
    parser.add_argument("--snapshot-sha256")
    parser.add_argument("--acquisition")
    args = parser.parse_args()
    require(
        digest(read_stable(__file__)) == args.controller_sha256,
        "Controller SHA differs",
    )
    clean_path(AUDIT)
    require(AUDIT.is_dir(), "Audit root absent")
    output = Path(tempfile.mkdtemp(prefix="t2-reconciliation-", dir=AUDIT))
    os.chmod(output, 0o700)
    report = {
        "status": "verification_failed",
        "python": platform.python_version(),
        "sqlite_runtime_version": sqlite3.sqlite_version,
        "source_controller_sha256": args.controller_sha256,
        "optimizer_calls": 0,
        "jobs_submitted": 0,
        "sources_modified": False,
    }
    try:
        if args.command == "inventory":
            report["inventory"] = discover(ROOTS)
            paths = {}
            for name, expected in PINS.items():
                matches = [
                    c["path"]
                    for c in report["inventory"]["candidates"]
                    if c.get("sha256") == expected and Path(c["path"]).name == name
                ]
                if matches:
                    paths[name] = matches[0]
            if len(paths) == 2:
                report["workbooks"] = reconcile_workbooks(
                    paths["agrologistic_effective_baseline_v1.xlsx"],
                    paths["agrologistic_warehouse_registry_v1.xlsx"],
                )
            report["missing_review_workbooks"] = sorted(set(PINS) - paths.keys())
            report["status"] = "inventory_only_reconciliation_pending"
        else:
            require(args.workbook and args.registry, "Two workbook paths required")
            report["workbooks"] = reconcile_workbooks(
                args.workbook, args.registry, args.support
            )
            if args.snapshot:
                require(
                    args.support and args.snapshot_sha256 and args.acquisition,
                    "Snapshot needs support, SHA and acquisition receipt",
                )
                snapshot = clean_path(args.snapshot)
                require(
                    snapshot.is_relative_to(AUDIT), "Snapshot must be in audit custody"
                )
                require(
                    snapshot.name != "policy-pairs-v020.sqlite3",
                    "Live cache name refused",
                )
                report["cache"] = cache_crosswalk(
                    snapshot, args.snapshot_sha256, args.support, args.acquisition
                )
            report["status"] = "partial_data_checks_complete_not_input_qualification"
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        ET.ParseError,
        StopIteration,
        zipfile.BadZipFile,
        sqlite3.Error,
    ) as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
    finish(output, report)
    return 1 if report["status"] == "verification_failed" else 0


if __name__ == "__main__":
    sys.exit(main())
