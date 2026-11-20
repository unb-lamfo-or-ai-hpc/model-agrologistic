"""Read-only audit and diagnostic extraction of the final operator transfer."""

import argparse
import csv
import hashlib
import json
import tarfile
from collections import Counter
from pathlib import Path, PurePosixPath

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("readback", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
ROOT = args.output.resolve()
ROOT.mkdir(parents=True, exist_ok=False)
SOURCE = args.readback.resolve()
ARCHIVE = SOURCE / "h300-2252608-closeout.tar.gz"
EXPECTED = "92491a1489c11c3267c30109d90e81cff4c4553a76d3a67b3d542188574a6ff0"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


assert digest(ARCHIVE) == EXPECTED
transfer = []
for line in (SOURCE / "TRANSFER_SHA256SUMS").read_text().splitlines():
    sha, name = line.split("  ", 1)
    p = PurePosixPath(name)
    assert not p.is_absolute() and ".." not in p.parts
    path = SOURCE.joinpath(*p.parts)
    assert digest(path) == sha, name
    transfer.append(name)

hashes = {}
names = set()
small = {}
size = 0
with tarfile.open(ARCHIVE, "r|gz") as archive:
    for member in archive:
        assert (
            member.isfile()
            and not PurePosixPath(member.name).is_absolute()
            and ".." not in PurePosixPath(member.name).parts
        )
        assert member.name not in names
        names.add(member.name)
        size += member.size
        retain = member.size < 16 * 1024**2 and (
            member.name.endswith((".json", ".log", ".err", ".out"))
            or member.name in ("tasks.csv", "accounting.txt")
        )
        stream = archive.extractfile(member)
        digestor = hashlib.sha256()
        chunks = []
        while chunk := stream.read(1024**2):
            digestor.update(chunk)
            if retain:
                chunks.append(chunk)
        hashes[member.name] = digestor.hexdigest()
        if retain:
            raw = b"".join(chunks)
            small[member.name] = raw
            destination = ROOT / "diagnostics" / member.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)

inventory = json.loads(small["inventory.json"])
assert names == set(inventory["files_sha256"]) | {"inventory.json"}
assert all(hashes[name] == sha for name, sha in inventory["files_sha256"].items())
plan_raw = small["claim/plan.json"]
assert (
    hashlib.sha256(plan_raw).hexdigest()
    == "de528d6ac5f15ecc4be37a6540d0d1159e2e6990049c25a574eb21567de60f32"
)
plan = json.loads(plan_raw)
assert plan["source"] == "9d43c963ed53b968e2e6c508de8dc06ed7e6693a"
assert json.loads(small["claim/block-1.json"])["array_job"] == "2252608"
tasks = list(csv.DictReader(small["tasks.csv"].decode().splitlines()))
assert sorted(int(t["task"]) for t in tasks) == list(range(60))
for index, t in enumerate(tasks):
    assert t["case"] == plan["rows"][index]["id"]
(ROOT / "tasks.csv").write_bytes(small["tasks.csv"])
result = {
    "archive_sha256": EXPECTED,
    "transfer_files_verified": len(transfer),
    "archive_members": len(names),
    "uncompressed_bytes": size,
    "inventory_members_verified": len(inventory["files_sha256"]),
    "missing_originals": inventory["missing_originals"],
    "scheduler_counts": dict(Counter(t["state"].split()[0] for t in tasks)),
    "original_files": inventory["original_files"],
}
(ROOT / "audit.json").write_text(json.dumps(result, indent=2))
(ROOT / "plan.json").write_text(json.dumps(plan, indent=2))
(ROOT / "inventory.json").write_text(json.dumps(inventory, indent=2))
print(json.dumps(result, indent=2))
