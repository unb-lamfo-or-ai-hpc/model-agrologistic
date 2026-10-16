"""Bounded P4 products; no scheduler, input loader or native solver effects.

The inherited 256MiB transfer envelope applies to the ENTIRE block, not each arm.
JSON sizing is streaming and precedes publication. Native extraction and residual
validation still use the existing in-memory sparse vector; this is not an RSS cap.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import tarfile
from pathlib import Path

from scripts import mvp2_h300_controls as c
from scripts import mvp2_h300_partial as partial
from scripts import mvp2_h300_thread_contract as d

LIMIT = partial.LIMIT
METADATA = 8 * 1024**2
RESERVE = 2 * 1024**2
ENCODER = json.JSONEncoder(sort_keys=True, allow_nan=False, separators=(",", ":"))


def safe(path):
    path = Path(path).absolute()
    d.require(not any(p.is_symlink() for p in (path, *path.parents)), "Linked product path.")
    return path


def sha_file(path):
    digest = hashlib.sha256()
    with safe(path).open("rb") as stream:
        for raw in iter(lambda: stream.read(65536), b""):
            digest.update(raw)
    return digest.hexdigest()


def chunks(value):
    for text in ENCODER.iterencode(value):
        # Do not duplicate a large individual string as one UTF-8 allocation.
        for index in range(0, len(text), 16384):
            yield text[index : index + 16384].encode()
    yield b"\n"


def size(value, limit):
    d.require(type(limit) is int and 0 < limit <= LIMIT, "JSON budget.")
    total = 0
    for raw in chunks(value):
        total += len(raw)
        d.require(total <= limit, "JSON export budget exhausted; no truncation permitted.")
    return total


def publish(path, value, *, limit=METADATA):
    """Size first, exclusively write pending, then publish; never replace originals."""
    path = safe(path)
    expected = size(value, limit)
    pending = path.with_name(path.name + ".pending")
    d.require(not path.exists(), "Product already exists.")
    total = 0
    with pending.open("xb") as stream:
        for raw in chunks(value):
            total += len(raw)
            d.require(total <= expected, "Product changed during serialization.")
            stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    d.require(total == expected and not path.exists(), "Product sizing/publication drift.")
    # Trusted single writer. No crash-durability or hostile-writer guarantee.
    pending.rename(path)
    return expected


def read(path, *, limit=METADATA):
    with safe(path).open("rb") as stream:
        raw = stream.read(limit + 1)
    d.require(len(raw) <= limit, "Product read budget.")
    return c.decode_json(raw)


def export(directory, result, data, config, anchor, *, remaining):
    """Same residual/priority evaluator, streamed publication and explicit block cap."""
    d.require(RESERVE < remaining <= LIMIT, "Remaining block product budget.")
    native, count = result.metadata.get("gurobi_status_name"), result.metadata.get("solution_count")
    d.require(native in partial.NATIVE_STOPS and type(count) is int and count >= 0, "Native stop.")
    observation = {
        "schema_version": "s2-partial-observation-v1",
        "anchor": anchor,
        "native_status": native,
        "solution_count": count,
        "result_status": result.status,
        "stages": [
            {k: stage.get(k) for k in partial.STAGE_FIELDS}
            for stage in result.metadata.get("lexicographic_stages", [])
        ],
    }
    vector = {k: getattr(result, k) for k in partial.VECTOR_FIELDS} if count else None
    if not count:
        d.require(
            result.objective_value is None
            and not result.cost_breakdown
            and all(not getattr(result, k) for k in partial.VECTOR_FIELDS[2:]),
            "Stale no-incumbent vector.",
        )
    report = partial.evaluate(observation, vector, data, config, anchor)
    assets = {"observation.json": observation, "independent_validation.json": report["validation"]}
    if vector is not None:
        assets["incumbent.json"] = vector
    # Exact byte preflight BEFORE writing any large JSON product. An over-budget
    # result is a preserved export failure, not a truncated scientific observation.
    sizes, total = {}, 0
    for name, value in assets.items():
        sizes[name] = size(value, remaining - RESERVE - total)
        total += sizes[name]
    directory = safe(directory)
    directory.mkdir(exist_ok=False)
    for name, value in assets.items():
        publish(directory / name, value, limit=sizes[name])
    publish(
        directory / "closure.json",
        {
            "schema_version": "s2-p4-product-closure-v1",
            "anchor_sha256": d.digest(anchor),
            "artifacts": {name: sha_file(directory / name) for name in assets},
            "sizes": sizes,
            "production_admitted": False,
            "repeats_admitted": False,
        },
    )
    return report


def review(directory, data, config, anchor):
    """Independent fresh residual replay; never trust the worker's acceptance flag."""
    directory = safe(directory)
    closure = read(directory / "closure.json")
    names = set(closure["artifacts"])
    d.require(
        set(closure)
        == {
            "schema_version",
            "anchor_sha256",
            "artifacts",
            "sizes",
            "production_admitted",
            "repeats_admitted",
        }
        and closure["schema_version"] == "s2-p4-product-closure-v1"
        and closure["anchor_sha256"] == d.digest(anchor)
        and closure["production_admitted"] is False
        and closure["repeats_admitted"] is False
        and names
        in (
            {"observation.json", "independent_validation.json"},
            {"observation.json", "independent_validation.json", "incumbent.json"},
        )
        and set(closure["sizes"]) == names,
        "Product closure scope.",
    )
    d.require(
        all(type(x) is int and 0 < x <= LIMIT for x in closure["sizes"].values()),
        "Product length grammar.",
    )
    d.require({p.name for p in directory.iterdir()} == names | {"closure.json"}, "Extra product.")
    total = sum(closure["sizes"].values())
    d.require(0 < total <= LIMIT - RESERVE, "Product aggregate bound.")
    for name in names:
        path = safe(directory / name)
        d.require(
            path.stat().st_size == closure["sizes"][name]
            and sha_file(path) == closure["artifacts"][name],
            "Product hash/size drift.",
        )
    observation = read(directory / "observation.json")
    vector = read(directory / "incumbent.json", limit=LIMIT) if "incumbent.json" in names else None
    report = partial.evaluate(observation, vector, data, config, anchor)
    d.require(
        report["validation"] == read(directory / "independent_validation.json"),
        "Fresh residual validation mismatch.",
    )
    return report


def inventory(root):
    """Only fixed portable records: never logs, origin/private paths or workbook."""
    root = safe(root)
    pattern = (
        r"(?:plan|job|batch|accounting|scheduler-resources|review)\.json|"
        r"arms/t(?:1|2|4|8|16)/(?:attempt|resources|worker-start|release|ticket|independent)\.json|"
        r"arms/t(?:1|2|4|8|16)/native/(?:root-resources|native-terminal|"
        r"failure|phase-[0-3]|failure-cleanup)\.json|"
        r"arms/t(?:1|2|4|8|16)/native/products/(?:observation|incumbent|"
        r"independent_validation|closure)\.json"
    )
    files = {}
    total = 0
    for path in root.rglob("*"):
        name = path.relative_to(root).as_posix()
        if re.fullmatch(pattern, name) and path.is_file():
            safe(path)
            length = path.stat().st_size
            total += length + 1024  # Conservative tar header/padding accounting.
            d.require(total <= LIMIT - RESERVE, "Block transfer envelope exhausted.")
            files[name] = {"sha256": sha_file(path), "size": length}
    d.require(
        {"plan.json", "job.json", "batch.json", "accounting.json", "review.json"} <= files.keys(),
        "Missing terminal forensic records.",
    )
    return dict(sorted(files.items()))


def pack(root, path):
    """Stream one whole-block tar; original oversized products stay in the run."""
    root, path = safe(root), safe(path)
    files = inventory(root)
    with path.open("xb") as output:
        with tarfile.open(fileobj=output, mode="w:gz", format=tarfile.USTAR_FORMAT) as archive:
            for name, item in files.items():
                info = tarfile.TarInfo(name)
                info.size = item["size"]
                info.mode = 0o600
                with safe(root / name).open("rb") as stream:
                    archive.addfile(info, stream)
    d.require(path.stat().st_size <= LIMIT, "Compressed archive bound.")
    d.require(inventory(root) == files, "Collection source changed during packing.")
    return sha_file(path), files


def unpack_review(path, checksum, expected):
    """Stream verify without extracting; an externally anchored manifest is required."""
    d.require(sha_file(path) == checksum and safe(path).stat().st_size <= LIMIT, "Archive anchor.")
    found, total = {}, 0
    with (
        gzip.open(safe(path), "rb") as compressed,
        tarfile.open(fileobj=compressed, mode="r|") as archive,
    ):
        for member in archive:
            d.require(
                member.name in expected
                and member.name not in found
                and member.isfile()
                and not member.pax_headers
                and member.size == expected[member.name]["size"],
                "Archive member scope/size.",
            )
            total += member.size + 1024
            d.require(total <= LIMIT - RESERVE, "Expanded archive bound.")
            digest = hashlib.sha256()
            stream = archive.extractfile(member)
            for raw in iter(lambda stream=stream: stream.read(65536), b""):
                digest.update(raw)
            found[member.name] = {"size": member.size, "sha256": digest.hexdigest()}
        # Drain the tar stream itself, including buffered bytes. Trailing payload,
        # concatenated gzip members and excessive zero padding are not ignored.
        tail_size = 0
        for raw in iter(lambda: archive.fileobj.read(65536), b""):
            tail_size += len(raw)
            d.require(total + tail_size <= LIMIT and not any(raw), "Archive trailing bytes/bound.")
    d.require(found == expected, "Archive inventory/hash mismatch.")
    return found
