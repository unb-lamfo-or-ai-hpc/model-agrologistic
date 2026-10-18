"""Prospective five-arm transfer; historical 256MiB transports remain unchanged.

The versioned 1GiB expanded block envelope is a transfer policy, NOT solver RSS.
Each native vector still uses the inherited <=256MiB product exporter. Nothing
is truncated or omitted to make a completed block appear to fit.
"""

from __future__ import annotations

import copy
import gzip
import hashlib
import re
import tarfile

from scripts import mvp2_s2_residual_replay as replay

p, d, c = replay.p, replay.d, replay.c
LIMIT = 1024**3
RESERVE = 16 * 1024**2
PATTERN = (
    r"(?:plan|job|batch|accounting|scheduler-resources|review)\.json|"
    r"prerequisite/(?:worker-validation|fresh-report|witness|comparison|outcome)\.json|"
    r"arms/t(?:1|2|4|8|16)/(?:attempt|resources|worker-start|release|ticket|independent)\.json|"
    r"arms/t(?:1|2|4|8|16)/derived-review/(?:worker-validation|fresh-report|witness|comparison|outcome)\.json|"
    r"arms/t(?:1|2|4|8|16)/diagnostics/(?:license-selection|native-ready|optimization|native-return)\.json|"
    r"arms/t(?:1|2|4|8|16)/native/(?:root-resources|native-terminal|failure|phase-[0-3]|failure-cleanup)\.json|"
    r"arms/t(?:1|2|4|8|16)/native/products/(?:observation|incumbent|independent_validation|closure)\.json"
)


def review(directory, data, config, anchor, *, capture=None):
    """Same residual evaluator; stable derived report, preserving raw reports first."""
    directory = p.safe(directory)
    if not (directory / "incumbent.json").exists():
        report = p.review(directory, data, config, anchor)
        d.require(
            report["validation"]["status"] == "not_applicable_no_incumbent"
            and report["classification"]["disposition"] == "no_incumbent",
            "No-incumbent classification drift.",
        )
        return report
    inventory = {
        f.name: {"size": f.stat().st_size, "sha256": p.sha_file(f)} for f in directory.iterdir()
    }
    worker, fresh = replay.products(directory, data, config, anchor, inventory)
    # A real private mismatch must never again discard the fresh report.
    if capture is not None:
        capture("worker-validation.json", worker, p.METADATA)
        capture("fresh-report.json", fresh, p.METADATA)
    terms = replay.witness(data, config)
    if capture is not None:
        capture("witness.json", terms, replay.WITNESS_LIMIT)
    compared = replay.compare(worker, fresh["validation"], terms)
    if capture is not None:
        capture("comparison.json", compared, p.METADATA)
    canonical = copy.deepcopy(fresh)
    key = "cost_reconstruction_sparse_rounding_budgets"
    for component, values in terms.items():
        canonical["validation"][key][component] = replay.order_bound(values)[0]
    canonical["derived_validation_equivalence"] = {
        "schema_version": compared["schema_version"],
        "canonical_validation_sha256": compared["canonical_validation_sha256"],
        "witness_sha256": compared["witness_sha256"],
        "scientific_tolerances_changed": False,
    }
    return canonical


def limit_for(name):
    if name.endswith("/incumbent.json"):
        return p.LIMIT
    if name.endswith("/witness.json"):
        return replay.WITNESS_LIMIT
    return p.METADATA


def inventory(root):
    root, files, total = p.safe(root), {}, 10240
    for path in root.rglob("*"):
        name = path.relative_to(root).as_posix()
        if not re.fullmatch(PATTERN, name) or not path.is_file():
            continue
        p.safe(path)
        length = path.stat().st_size
        d.require(0 < length <= limit_for(name), "Versioned member bound.")
        total += ((length + 511) // 512) * 512 + 512
        d.require(total <= LIMIT - RESERVE, "Expanded five-arm envelope exhausted.")
        files[name] = {"size": length, "sha256": p.sha_file(path)}
    d.require(
        {"plan.json", "job.json", "batch.json", "accounting.json", "review.json"} <= files.keys(),
        "Missing terminal five-arm records.",
    )
    return dict(sorted(files.items()))


def pack(root, path):
    files = inventory(root)
    with (
        p.safe(path).open("xb") as output,
        tarfile.open(fileobj=output, mode="w:gz", format=tarfile.USTAR_FORMAT) as archive,
    ):
        for name, record in files.items():
            info = tarfile.TarInfo(name)
            info.size, info.mode = record["size"], 0o600
            with p.safe(root / name).open("rb") as stream:
                archive.addfile(info, stream)
    d.require(inventory(root) == files, "Five-arm source changed during collection.")
    unpack(path, p.sha_file(path), files)
    return p.sha_file(path), files


def unpack(path, checksum, expected):
    """Stream bounded member hashes without materializing private incumbent vectors."""
    d.require(
        p.sha_file(path) == checksum and p.safe(path).stat().st_size <= LIMIT,
        "Five-arm archive anchor/bound.",
    )
    found, total = {}, 10240
    with gzip.open(path, "rb") as compressed, tarfile.open(fileobj=compressed, mode="r|") as stream:
        for member in stream:
            d.require(
                member.name in expected
                and re.fullmatch(PATTERN, member.name)
                and member.name not in found
                and member.isfile()
                and not member.pax_headers
                and 0 < member.size <= limit_for(member.name)
                and member.size == expected[member.name]["size"],
                "Five-arm member scope.",
            )
            total += ((member.size + 511) // 512) * 512 + 512
            d.require(total <= LIMIT - RESERVE, "Expanded five-arm archive bound.")
            digest, copied = hashlib.sha256(), 0
            source = stream.extractfile(member)
            for raw in iter(lambda source=source: source.read(65536), b""):
                copied += len(raw)
                digest.update(raw)
            d.require(copied == member.size, "Truncated five-arm member.")
            found[member.name] = {"size": copied, "sha256": digest.hexdigest()}
        trailing = 0
        for raw in iter(lambda: stream.fileobj.read(65536), b""):
            trailing += len(raw)
            d.require(
                total + trailing <= LIMIT and not any(raw), "Five-arm trailing payload/bound."
            )
    d.require(found == expected, "Five-arm archive inventory drift.")
    return found


def metadata(path, name):
    """Call only after authenticated unpack; JSON remains separately bounded."""
    d.require(
        re.fullmatch(PATTERN, name) and not name.endswith("/incumbent.json"),
        "No private incumbent materialization by portable metadata reader.",
    )
    with tarfile.open(path, "r:gz") as stream:
        member = stream.getmember(name)
        d.require(member.isfile() and member.size <= limit_for(name), "Portable metadata bound.")
        return c.decode_json(stream.extractfile(member).read(member.size + 1))
