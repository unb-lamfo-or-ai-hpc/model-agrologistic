"""Audit a transferred metadata inventory; no original NPAD access."""

import collections
import csv
import hashlib
import io
import json
import pathlib
import re
import sys
import tarfile

A = pathlib.Path(sys.argv[1]).resolve()
D = pathlib.Path(sys.argv[2]).resolve()
D.mkdir(parents=True, exist_ok=True)
expected = "c0127ce8c9fe76409ab192f877eaf05213d39eb560a78579db95fb116a8d59d0"


def sha(b):
    return hashlib.sha256(b).hexdigest()


assert sha(A.read_bytes()) == expected
assert A.with_name(A.name + ".sha256").read_text().strip() == expected + "  " + A.name
files = {}
with tarfile.open(A, "r:gz") as t:
    for m in t:
        q = pathlib.PurePosixPath(m.name)
        assert not q.is_absolute() and ".." not in q.parts and "\\" not in m.name
        assert m.isdir() or m.isfile()
        if m.isdir():
            continue
        assert 0 <= m.size <= 128 * 1024**2
        name = q.as_posix()
        assert name not in files
        files[name] = t.extractfile(m).read()
assert set(files) == {
    "inventory.py",
    "inventory.csv",
    "errors.csv",
    "top-directories.csv",
    "summary.json",
    "squeue.txt",
    "squeue.stderr",
    "SHA256SUMS",
}
assert sum(map(len, files.values())) < 256 * 1024**2
entries = {}
for line in files["SHA256SUMS"].decode().splitlines():
    h, name = re.fullmatch(r"([0-9a-f]{64})  (.+)", line).groups()
    assert name in files and name not in entries
    assert sha(files[name]) == h, name
    entries[name] = h
assert set(entries) == set(files) - {"SHA256SUMS"}
for name, raw in files.items():
    with (D / name).open("xb") as f:
        f.write(raw)
s = json.loads(files["summary.json"])
rows = list(csv.DictReader(io.StringIO(files["inventory.csv"].decode())))
errors = list(csv.DictReader(io.StringIO(files["errors.csv"].decode())))
top = list(csv.DictReader(io.StringIO(files["top-directories.csv"].decode())))
assert not errors and not files["squeue.stderr"]
seen = set()
byroot = {r["root"]: collections.Counter() for r in s["roots"]}
opaque = []
regular = []
inodegroups = collections.defaultdict(list)
for r in rows:
    key = (r["root"], r["relative_path"])
    assert key not in seen
    seen.add(key)
    p = pathlib.PurePosixPath(r["relative_path"])
    assert not p.is_absolute() and ".." not in p.parts
    c = byroot[r["root"]]
    c[r["type"]] += 1
    if r["type"] == "file":
        c["logical_bytes_by_path"] += int(r["logical_bytes"])
        c["allocated_bytes_by_path"] += int(r["allocated_bytes"])
        regular.append(r)
        inodegroups[(int(r["device"]), int(r["inode"]))].append(r)
    if r["note"] == "contents not enumerated":
        opaque.append({"root": r["root"], "path": r["relative_path"]})
for r in s["roots"]:
    c = byroot[r["root"]]
    for a, b in [
        ("files", "file"),
        ("directories", "directory"),
        ("symlinks", "symlink"),
        ("logical_bytes_by_path", "logical_bytes_by_path"),
        ("allocated_bytes_by_path", "allocated_bytes_by_path"),
    ]:
        assert r[a] == c[b], (r["root"], a, r[a], c[b])
    assert r["opaque_directories"] == sum(x["root"] == r["root"] for x in opaque)
computed = collections.defaultdict(lambda: collections.Counter())
for r in regular:
    p = pathlib.PurePosixPath(r["relative_path"])
    k = (r["root"], p.parts[0] if len(p.parts) > 1 else "[root files]")
    computed[k]["files"] += 1
    computed[k]["logical_bytes_by_path"] += int(r["logical_bytes"])
    computed[k]["allocated_bytes_by_path"] += int(r["allocated_bytes"])
assert len(computed) == len(top)
for t in top:
    c = computed[(t["root"], t["top_component"])]
    assert all(c[k] == int(t[k]) for k in c)
big = sorted(regular, key=lambda r: int(r["logical_bytes"]), reverse=True)
dups = [g for g in inodegroups.values() if len(g) > 1]
unique_bytes = sum(int(g[0]["logical_bytes"]) for g in inodegroups.values())
assert all(len({(x["logical_bytes"], x["allocated_bytes"]) for x in g}) == 1 for g in dups)
receipt = dict(
    archive_sha256=expected,
    archive_bytes=A.stat().st_size,
    internal_manifest_entries_verified=len(entries),
    hash_mismatches=0,
    members={n: dict(bytes=len(b), sha256=sha(b)) for n, b in files.items()},
    metadata_rows=len(rows),
    regular_files=len(regular),
    unique_regular_inodes=len(inodegroups),
    hardlinked_inode_groups_seen=len(dups),
    logical_bytes_by_path=sum(int(r["logical_bytes"]) for r in regular),
    unique_inode_logical_bytes=unique_bytes,
    reported_summary=s,
    validation="All root and top-directory counts/byte totals reconcile",
    scanned_job_queue=files["squeue.txt"].decode(),
    largest_files=[{k: r[k] for k in ("root", "relative_path", "logical_bytes")} for r in big[:45]],
    top_directory_groups=sorted(top, key=lambda r: int(r["logical_bytes_by_path"]), reverse=True)[
        :65
    ],
    opaque_directories=opaque,
)
(D / "audit-private.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(
    json.dumps(
        {
            k: receipt[k]
            for k in (
                "archive_sha256",
                "archive_bytes",
                "internal_manifest_entries_verified",
                "hash_mismatches",
                "metadata_rows",
                "regular_files",
                "unique_regular_inodes",
                "hardlinked_inode_groups_seen",
                "logical_bytes_by_path",
                "unique_inode_logical_bytes",
            )
        },
        indent=2,
    )
)
