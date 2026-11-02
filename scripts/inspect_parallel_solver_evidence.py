"""Inspect original parallel-solver archives locally; never extract or execute them."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import tarfile
import urllib.request
from pathlib import Path, PurePosixPath

REPO = "unb-lamfo-or-ai-hpc/model-agrologistic"
CASES = (
    ("2226388", "scalar-scip-h215-w-native8h-evidence.tar.gz",
     "5626db207faf9436c9600c8a00f5ef1d5814d1acdc86bc0aab6c422f51d7548d",
     "82cb58ff6975662a7b576e7c6c0d5589539e635c"),
    ("2226536", "scalar-highs-h215-w-native8h-startup-v2-evidence.tar.gz",
     "db04224d755cd5720091ddb96fc275bcefc6082431ea4b417a1b90d0fece071b",
     "009119a07eb8c68573cfa105893b9d4a719c5155"),
)
LIMIT = 1024**3


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate JSON key")
            result[key] = value
        return result

    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def safe_name(name):
    path = PurePosixPath(name)
    return bool(name) and not path.is_absolute() and "\\" not in name and all(
        part not in {"", ".", ".."} for part in name.split("/")
    )


def scrub(value):
    if isinstance(value, dict):
        return {key: scrub(item) for key, item in value.items()}
    if isinstance(value, list):
        return [scrub(item) for item in value]
    if isinstance(value, str):
        value = re.sub(r"/home/[^/\s\"']+", "<HOME>", value)
        return re.sub(r"[A-Za-z]:\\Users\\[^\\\s\"']+", "<USER>", value)
    return value


def original_source(expected, commit):
    url = f"https://codeload.github.com/{REPO}/tar.gz/{commit}"
    request = urllib.request.Request(url, headers={"User-Agent": "agrologistic-local-audit"})
    with urllib.request.urlopen(request, timeout=90) as response:
        raw = response.read(64 * 1024**2 + 1)
    require(len(raw) <= 64 * 1024**2, "Original source archive exceeds limit")
    actual = {}
    total = 0
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r|gz") as archive:
        for member in archive:
            if member.isdir():
                continue
            parts = member.name.split("/", 1)
            require(len(parts) == 2 and member.isfile() and safe_name(parts[1]),
                    "Unsafe original-source member")
            name = parts[1]
            require(name not in actual, "Duplicate original-source member")
            total += member.size
            require(total <= 128 * 1024**2, "Expanded source exceeds limit")
            actual[name] = digest(archive.extractfile(member).read())
    require(actual == expected, "Original GitHub source inventory differs")
    return len(actual)


def read_payload(stream, *, size, retain, is_log, json_limit=64 * 1024**2):
    """Hash every byte; retain only bounded JSON and a bounded log tail."""
    hasher, data, tail = hashlib.sha256(), bytearray(), b""
    keep_json = retain and size <= json_limit
    seen = 0
    for block in iter(lambda: stream.read(1024**2), b""):
        hasher.update(block)
        seen += len(block)
        if keep_json:
            data.extend(block)
        if is_log:
            tail = (tail + block)[-5000:]
    require(seen == size, "Truncated evidence member")
    return hasher.hexdigest(), bytes(data) if keep_json else None, tail


def self_test():
    """Exercise bounded reads before requesting any original archive."""
    raw = b'{"status":"complete"}'
    hashed, kept, tail = read_payload(
        io.BytesIO(raw), size=len(raw), retain=True, is_log=False, json_limit=64
    )
    require(hashed == digest(raw) and kept == raw and tail == b"", "Small JSON regression")
    raw = bytes(range(256)) * 10000
    hashed, kept, tail = read_payload(
        io.BytesIO(raw), size=len(raw), retain=True, is_log=True, json_limit=64
    )
    require(hashed == digest(raw) and kept is None, "Large member hash/retention regression")
    require(tail == raw[-5000:], "Bounded log-tail regression")
    try:
        read_payload(io.BytesIO(b"x"), size=2, retain=False, is_log=False)
    except ValueError:
        pass
    else:
        raise ValueError("Truncation regression")
    try:
        strict_json(b'{"key":1,"key":2}')
    except ValueError:
        pass
    else:
        raise ValueError("Duplicate-key regression")
    print("LOCAL_INSPECTOR_SELF_TEST=PASSED; CASES=5; NO_ARCHIVE_OR_SOLVER")


def inspect(base, specification):
    job, name, checksum, commit = specification
    path = base / name
    sidecar = base / (name + ".sha256")
    require(path.is_file() and not path.is_symlink(), "Regular original archive required")
    require(sidecar.is_file() and not sidecar.is_symlink(), "Regular checksum required")
    parts = sidecar.read_text(encoding="utf-8-sig").split()
    require(parts == [checksum, name], "External checksum/name differs")
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024**2), b""):
            hasher.update(block)
    require(hasher.hexdigest() == checksum, "Original archive checksum differs")
    hashes, selected, tails, unparsed = {}, {}, {}, []
    total = 0
    keep = {
        "plan.json", "job.json", "source.json", "review.json", "inventory.json",
        "batch_outcome.json", "historical_w.json",
    }
    suffixes = (
        "controller.json", "native_terminal.json", "independent_validation.json",
        "run_summary.json", "run_completion.json", "result.json", "runtime.json",
        "input_receipt.json", "warehouses_used.json", "matrix_statistics.json",
        "error.json", "outcome.json",
    )
    with tarfile.open(path, "r|gz") as archive:
        for member in archive:
            require(member.isfile() and safe_name(member.name), "Unsafe evidence member")
            require(member.name not in hashes, "Duplicate evidence member")
            total += member.size
            require(total <= LIMIT and len(hashes) < 4096, "Evidence limit exceeded")
            stream = archive.extractfile(member)
            retain = member.name in keep or member.name.endswith(suffixes)
            is_log = member.name.endswith((".log", ".err", ".out", ".txt", ".stderr"))
            is_log = is_log and "/qualification-cases/" not in member.name
            checksum_value, data, tail = read_payload(
                stream, size=member.size, retain=retain, is_log=is_log
            )
            hashes[member.name] = checksum_value
            if data is not None:
                selected[member.name] = data
            elif retain:
                unparsed.append({
                    "name": member.name, "bytes": member.size, "sha256": checksum_value,
                    "reason": "Fully hashed; JSON exceeds the bounded metadata buffer",
                })
            if is_log and (member.name.startswith("control/sto/") or "/" not in member.name):
                tails[member.name] = tail.decode("utf-8", errors="replace")
    inventory = strict_json(selected["inventory.json"])
    require(inventory == {key: value for key, value in hashes.items()
                          if key != "inventory.json"}, "Inventory digests differ")
    plan = strict_json(selected["plan.json"])
    source = strict_json(selected["source.json"])
    receipt = strict_json(selected["job.json"])
    review = strict_json(selected["review.json"])
    require(plan["source_commit"] == source["source_commit"] == commit, "Source differs")
    require(receipt["source_commit"] == commit and str(receipt["job_id"]) == job,
            "Original job binding differs")
    require(receipt["plan_sha256"] == hashes["plan.json"], "Plan binding differs")
    for artifact, expected in plan["artifact_sha256"].items():
        require(hashes.get(artifact) == expected, "Plan artifact differs: " + artifact)
    source_count = original_source(source["files"], commit)
    completions = {}
    for key, raw in selected.items():
        if not key.endswith("/run_completion.json") or "/qualification-cases/" in key:
            continue
        completion = strict_json(raw)
        prefix = key.rsplit("/", 1)[0] + "/"
        artifacts = completion.get("artifacts")
        complete_map = isinstance(artifacts, dict)
        if complete_map:
            for artifact, expected in artifacts.items():
                require(safe_name(artifact) and hashes.get(prefix + artifact) == expected,
                        "Product completion artifact differs")
        elif review.get("quality_target_met"):
            require(False, "Claimed accepted result has no completion artifact map")
        completions[key] = {
            "status": completion.get("status"),
            "artifact_map_present": complete_map,
            "artifact_hashes_checked": len(artifacts) if complete_map else 0,
            "record": completion if not complete_map else {"status": completion.get("status")},
        }
    validations = {}
    physical = {}
    for key, raw in selected.items():
        if "/qualification-cases/" in key:
            continue
        if key.endswith("/independent_validation.json"):
            item = strict_json(raw)
            costs = item.get("reconstructed_costs", {})
            validations[key] = {field: item.get(field) for field in (
                "status", "validator_version", "failed_check_count",
                "absolute_tolerance", "relative_tolerance", "families",
            )}
            validations[key]["reconstructed_costs"] = costs
            if item.get("status") == "accepted":
                require(item["failed_check_count"] == 0
                        and item["absolute_tolerance"] == 1e-5
                        and item["relative_tolerance"] == 1e-8
                        and all(f["failed"] == 0 for f in item["families"].values()),
                        "Accepted original residual certificate differs")
                total_cost = sum(costs.values())
                require(math.isclose(total_cost, review["objective"],
                                     rel_tol=1e-8, abs_tol=1e-5), "Cost reconstruction differs")
        if key.endswith("/run_summary.json"):
            item = strict_json(raw)
            physical[key] = {field: value for field, value in item.items()
                             if isinstance(value, (int, float, bool, type(None)))
                             and any(word in field for word in (
                                 "demand", "service", "economic", "penal", "capacity"
                             ))}
    numerical = {}
    for key, raw in selected.items():
        if "/qualification-cases/" in key or not key.endswith("/result.json"):
            continue
        document = strict_json(raw)
        native = document.get("result") or {}
        metadata = native.get("metadata") or {}
        numerical[key] = {
            field: native.get(field) for field in (
                "status", "objective_value", "objective_bound", "solver_backend", "solver_name"
            )
        }
        numerical[key]["metadata"] = {
            field: metadata.get(field) for field in (
                "solver_termination", "scip_status", "solver_versions",
                "effective_highs_options", "effective_scip_parameters",
                "pyomo_reformulation", "timings"
            )
        }
        if review.get("quality_target_met"):
            objective, bound = native["objective_value"], native["objective_bound"]
            gap = (objective - bound) / abs(objective)
            require(0 <= gap <= 0.01 and math.isclose(
                gap, review["common_gap"], rel_tol=1e-8, abs_tol=1e-12
            ), "Original objective/bound/common-gap arithmetic differs")
    input_bindings = {}
    historical = strict_json(selected["historical_w.json"])["receipts"]["sto"]
    for key, raw in selected.items():
        if "/qualification-cases/" in key or not key.endswith("/input_receipt.json"):
            continue
        receipt = strict_json(raw)
        matches = all(receipt.get(field) == historical.get(field) for field in (
            "mathematical_contract", "effective_scenario_probabilities", "warehouse_selection"
        ))
        input_bindings[key] = {"matches_historical_w": matches}
        if review.get("quality_target_met"):
            require(matches, "Accepted result differs from original W input binding")
    controls = {
        key: strict_json(raw) for key, raw in selected.items()
        if (key == "batch_outcome.json" or key.startswith("control/sto/"))
        and key.endswith(("controller.json", "native_terminal.json", "error.json", "outcome.json"))
        and "/qualification-cases/" not in key
    }
    gap_check = None
    if review.get("quality_target_met"):
        objective, bound = review["objective"], review["bound"]
        gap_check = (objective - bound) / abs(objective)
        require(0 <= gap_check <= 0.01 and math.isclose(
            gap_check, review["common_gap"], rel_tol=1e-8, abs_tol=1e-12
        ), "Original review objective/bound/common-gap arithmetic differs")
        require(validations and all(
            item["status"] == "accepted" for item in validations.values()
        ), "Accepted result lacks a bounded original residual certificate")
        require(completions and all(
            item["artifact_map_present"] for item in completions.values()
        ), "Accepted result lacks product-completion integrity")
        require(input_bindings and all(
            item["matches_historical_w"] for item in input_bindings.values()
        ), "Accepted result lacks original-W input bindings")
    return scrub({
        "job_id": job, "archive": name, "archive_sha256": checksum,
        "members": len(hashes), "expanded_bytes": total,
        "inventory_digests_verified": len(inventory),
        "original_source_commit": commit, "original_source_files_matched": source_count,
        "plan_sha256": hashes["plan.json"], "original_review": review,
        "completion_artifacts_checked": completions, "original_validation": validations,
        "physical_summary": physical, "numerical_metadata": numerical,
        "input_bindings": input_bindings, "controls": controls,
        "retained_log_tails": tails,
        "fully_hashed_json_not_parsed": unparsed,
        "gap_recomputed_from_original_review": gap_check,
        "native_result_metadata_reread": bool(numerical),
        "scope": (
            "Integrity/source/certificate inspection; no extraction, solver or fresh residuals"
        ),
        "full_operational_replay_performed": False,
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    require(args.base is not None and args.output is not None, "Base/output required")
    base = args.base.resolve(strict=True)
    require(base.is_dir() and not base.is_symlink(), "Existing temporary directory required")
    report = {"schema_version": "parallel-original-integrity-inspection-v2",
              "observations": [], "all_integrity_inspections_completed": False}
    with args.output.open("x", encoding="utf-8") as stream:
        for item in CASES:
            try:
                observation = inspect(base, item)
                observation["integrity_inspection_completed"] = True
            except Exception as exc:
                observation = {
                    "job_id": item[0], "archive": item[1],
                    "integrity_inspection_completed": False,
                    "inspection_error_kind": type(exc).__name__,
                    "inspection_error": scrub(str(exc)),
                }
            report["observations"].append(observation)
            stream.seek(0)
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write("\n")
            stream.truncate()
            stream.flush()
        report["all_integrity_inspections_completed"] = all(
            row["integrity_inspection_completed"] for row in report["observations"]
        )
        stream.seek(0)
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
        stream.truncate()
    print(json.dumps(report, indent=2, allow_nan=False))
    print("LOCAL_REPORT_CREATED=" + str(args.output))
    if not report["all_integrity_inspections_completed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
