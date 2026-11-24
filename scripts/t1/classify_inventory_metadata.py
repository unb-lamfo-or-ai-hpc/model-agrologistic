"""Conservative metadata classification; no original-file hashes or cleanup actions."""

import collections
import csv
import json
import pathlib
import sys

D = pathlib.Path(sys.argv[1]).resolve()
ROWS = list(csv.DictReader((D / "inventory.csv").open(encoding="utf-8", newline="")))
CATS = ("ACTIVE_KEEP", "ARCHIVE_PROPOSAL", "DELETION_CANDIDATE", "HOLD_REVIEW")
AUDIT = "model-agrologistic-hygiene-audit"
CURRENT = {
    ".mvp3-gurobi14-environment-v1",
    ".mvp3-gurobi14-h215-compat-v1",
    ".mvp3-gurobi14-h215-compat-v2-shared106",
    "gurobi14-h215-source-QDDQUuMt",
    "gurobi14-h215-source-m16lNUC8",
    "gurobi14-2278573-final-pqizplo_",
    "gurobi14-2280449-closeout-WOpVvm0S",
    "gurobi14-h215-readback-s133tc1m",
    "gurobi14-h215-readback-l6avcs1i",
}
CONTROLS = {
    "plan.json",
    "campaign.json",
    "job.json",
    "job-id.txt",
    "job.sh",
    "started.json",
    "submission-intent.json",
    "submission.stdout",
    "submission.stderr",
    "release.stdout",
    "release.stderr",
    "queue.json",
    "queue-status.json",
    "campaign_observation.json",
    "collection.json",
    "source-identity.txt",
    "runtime-baseline.json",
    "SHA256SUMS",
    "TRANSFER_SHA256SUMS",
    "submission-intent",
    "claim.json",
}
CACHE = {"__pycache__", ".pytest_cache", ".ruff_cache"}
OPAQUE = {
    ".git",
    ".ssh",
    ".aws",
    "secrets",
    ".venv",
    "venv",
    "venv313",
    "venv313_g14",
    "node_modules",
    "site-packages",
}


def classify(r):
    root = r["root"]
    p = pathlib.PurePosixPath(r["relative_path"])
    parts = p.parts
    name = p.name
    top = parts[0]
    low = name.lower()
    if r["type"] != "file":
        return (
            "HOLD_REVIEW",
            "nonregular_entry",
            "Entry only: no recursive action; opaque contents and link targets are unknown.",
        )
    if (
        any(x in OPAQUE for x in parts)
        or low.endswith((".lic", ".pem", ".key"))
        or low.startswith(".env")
    ):
        return (
            "HOLD_REVIEW",
            "credential_or_opaque_scope",
            "Preserve privately; no content or credential review performed.",
        )
    if root == "model-agrologistic-quarantine":
        return (
            "HOLD_REVIEW",
            "quarantine",
            "Preserve unresolved provenance and quarantine decisions.",
        )
    if root == AUDIT and (top in CURRENT or top.startswith("npad-t1-inventory")):
        return (
            "ACTIVE_KEEP",
            "migration_or_inventory_dependency",
            "Preserve migration proof, source/input checks and original failed/accepted claims.",
        )
    isclaim = root == AUDIT and top.startswith((".mvp2", ".mvp3", ".pr"))
    if (
        isclaim
        and "source" not in parts
        and not any(x.startswith("model-agrologistic-") for x in parts)
    ):
        if (
            len(parts) == 2
            or name in CONTROLS
            or name.startswith(("gate-", "submission-", "release-", "block-", "public-job"))
        ):
            return (
                "ACTIVE_KEEP",
                "consumed_claim_control",
                (
                    "Keep consumed-claim and collection safeguards at original "
                    "paths; never enable resubmission."
                ),
            )
    if any(x in CACHE for x in parts) or low.endswith((".pyc", ".pyo")):
        return (
            "DELETION_CANDIDATE",
            "regenerable_cache",
            (
                "Conditional only: verify provenance, references and absence "
                "of required diagnostic evidence before approval."
            ),
        )
    if root == "model-agrologistic-inputs":
        return (
            "ACTIVE_KEEP",
            "original_registry_input",
            "Retain authoritative original input until XLSX/data reconciliation and custody close.",
        )
    if root == "osrm-agrologistic":
        if top == "audits":
            return (
                "ARCHIVE_PROPOSAL",
                "routing_materialization_evidence",
                (
                    "Retain dataset/version/materialization provenance in a "
                    "verified restorable historical bundle."
                ),
            )
        return (
            "ACTIVE_KEEP",
            "routing_data_and_tools",
            (
                "Retain cache, PBF/profile/configuration and scripts until a "
                "consistent snapshot/crosswalk is qualified."
            ),
        )
    if root == "model-agrologistic-scientific-archive":
        return (
            "ARCHIVE_PROPOSAL",
            "existing_scientific_custody",
            "Retain existing archive material; inspect manifest/restoration before consolidation.",
        )
    if root == "model-agrologistic":
        if parts[:2] == ("data", "results") or name.startswith("slurm-"):
            return (
                "ARCHIVE_PROPOSAL",
                "historical_results",
                (
                    "Preserve historical results/logs; establish references and "
                    "complete verified archive before any relocation."
                ),
            )
        return (
            "ACTIVE_KEEP",
            "current_checkout_or_input",
            (
                "Preserve checkout, unreviewed local edits, inputs and "
                "templates; no Git clean/blob identity proof."
            ),
        )
    if root == AUDIT:
        return (
            "ARCHIVE_PROPOSAL",
            "historical_audit_or_execution_snapshot",
            (
                "Proposal only: verify closure, source/data references, "
                "original claims and restorable copies before archival "
                "action."
            ),
        )
    return "HOLD_REVIEW", "unknown_scope", "No supported action from this metadata inventory."


def writecsv(name, rows, fields):
    with (D / name).open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fields)
        w.writeheader()
        w.writerows(rows)


classified = []
aggregate = collections.defaultdict(lambda: collections.Counter())
rootcats = collections.defaultdict(lambda: collections.Counter())
groups = collections.defaultdict(lambda: collections.Counter())
rules = collections.Counter()
for r in ROWS:
    cat, rule, why = classify(r)
    entry = {
        **r,
        "classification": cat,
        "rule": rule,
        "reason": why,
        "record_scope": "entry_only",
        "deletion_authorized": "false",
        "archive_action_authorized": "false",
        "source_sha256": "",
    }
    classified.append(entry)
    if r["type"] == "file":
        n = int(r["logical_bytes"])
        blocks = int(r["allocated_bytes"])
        aggregate[cat]["files"] += 1
        aggregate[cat]["logical_bytes_by_path"] += n
        aggregate[cat]["allocated_bytes_by_path"] += blocks
        rootcats[(r["root"], cat)]["files"] += 1
        rootcats[(r["root"], cat)]["logical_bytes_by_path"] += n
        top = r["relative_path"].split("/")[0]
        groups[(r["root"], top, cat)]["files"] += 1
        groups[(r["root"], top, cat)]["logical_bytes_by_path"] += n
        rules[rule] += 1
fields = list(classified[0])
writecsv("path-classification.csv", classified, fields)
for cat in CATS:
    writecsv(
        cat.lower() + ".csv",
        [r for r in classified if r["type"] == "file" and r["classification"] == cat],
        fields,
    )
rootlist = [
    {"root": root, "classification": cat, **values}
    for (root, cat), values in sorted(rootcats.items())
]
grouplist = [
    {"root": root, "top_component": top, "classification": cat, **values}
    for (root, top, cat), values in sorted(
        groups.items(), key=lambda x: x[1]["logical_bytes_by_path"], reverse=True
    )
]
writecsv(
    "classification-by-root.csv",
    rootlist,
    ["root", "classification", "files", "logical_bytes_by_path"],
)
writecsv(
    "classification-by-group.csv",
    grouplist,
    ["root", "top_component", "classification", "files", "logical_bytes_by_path"],
)
same = collections.defaultdict(list)
for r in classified:
    if r["type"] == "file" and int(r["logical_bytes"]) > 0:
        same[(pathlib.PurePosixPath(r["relative_path"]).name, int(r["logical_bytes"]))].append(r)
hints = []
gid = 0
for (name, n), items in sorted(same.items(), key=lambda x: x[0][1] * len(x[1]), reverse=True):
    if len(items) < 2 or len({(r["device"], r["inode"]) for r in items}) < 2:
        continue
    gid += 1
    for r in items:
        hints.append(
            {
                "group": gid,
                "basename": name,
                "logical_bytes": n,
                "paths_in_group": len(items),
                "root": r["root"],
                "relative_path": r["relative_path"],
                "device": r["device"],
                "inode": r["inode"],
                "content_match": "not_tested",
                "deletion_authorized": "false",
            }
        )
writecsv(
    "same-name-size-review.csv",
    hints,
    [
        "group",
        "basename",
        "logical_bytes",
        "paths_in_group",
        "root",
        "relative_path",
        "device",
        "inode",
        "content_match",
        "deletion_authorized",
    ],
)
a = json.loads((D / "audit-private.json").read_text())
locator_names = {
    "agrologistic_effective_baseline_v1.xlsx",
    "agrologistic_warehouse_registry_v1.xlsx",
}
locators = [
    r
    for r in classified
    if r["type"] == "file" and pathlib.PurePosixPath(r["relative_path"]).name in locator_names
]
result = {
    "schema_version": "npad-t1-metadata-classification-v1",
    "reviewed_on": "2026-11-23",
    "source_archive_sha256": a["archive_sha256"],
    "source_archive_bytes": a["archive_bytes"],
    "internal_manifest_entries_verified": 7,
    "hash_mismatches": 0,
    "metadata_rows": len(ROWS),
    "regular_files": sum(x["files"] for x in aggregate.values()),
    "directories": sum(r["type"] == "directory" for r in ROWS),
    "symlinks": sum(r["type"] == "symlink" for r in ROWS),
    "special_entries": sum(r["type"] not in {"file", "directory", "symlink"} for r in ROWS),
    "opaque_directories": len(a["opaque_directories"]),
    "scan_errors": 0,
    "logical_bytes_by_path": sum(x["logical_bytes_by_path"] for x in aggregate.values()),
    "unique_regular_inodes": a["unique_regular_inodes"],
    "unique_inode_logical_bytes": a["unique_inode_logical_bytes"],
    "hardlinked_inode_groups_seen": a["hardlinked_inode_groups_seen"],
    "classification": dict(aggregate),
    "rule_file_counts": dict(rules),
    "root_classification": rootlist,
    "deletion_approved_files": 0,
    "archive_action_approved_files": 0,
    "verified_source_duplicates": 0,
    "same_basename_size_hint_groups": gid,
    "same_basename_size_hint_rows": len(hints),
    "new_xlsx_exact_basename_matches_in_enumerated_files": len(locators),
    "queue_snapshot": {
        "captured_with_inventory_on": "2026-11-22",
        "stdout_bytes": 0,
        "stderr_bytes": 0,
        "interpretation": (
            "No user jobs returned in that captured query; not current 23-Nov dependency clearance."
        ),
    },
    "limits": [
        (
            "Classifications are custody proposals based on "
            "names/metadata and known contracts, not verified file "
            "contents."
        ),
        (
            "Original source contents were not supplied or hashed; zero "
            "files are approved for deletion or moving."
        ),
        (
            "Full private path CSVs remain local; GitHub receives a "
            "redacted summary and reproducible classifier."
        ),
        (
            "The two new XLSX basenames were not found among enumerated "
            "files; opaque areas/other locations remain unknown."
        ),
        "Shared environments live outside these six roots and remain excluded.",
        (
            "No compression ratio, whole-project size or "
            "reclaimable-space claim follows from path byte totals."
        ),
    ],
    "next_review": [
        "Consistent SQLite snapshot and current effective XLSX/registry location for T2.",
        (
            "Read-only source/hash/dependency and Git-tracked/untracked "
            "review before cleanup approval."
        ),
        "Restore and external custody verification before any future archive relocation.",
        (
            "Keep claim markers/absolute-source dependencies and "
            "unresolved quarantine material intact."
        ),
    ],
}
assert result["regular_files"] == 122882 and result["logical_bytes_by_path"] == 19034672522
assert sum(x["files"] for x in aggregate.values()) == 122882
assert all(r["classification"] in CATS and r["deletion_authorized"] == "false" for r in classified)
assert not locators
(D / "classification-summary.json").write_text(json.dumps(result, indent=2) + "\n")
print(
    json.dumps(
        {
            k: result[k]
            for k in (
                "source_archive_sha256",
                "metadata_rows",
                "regular_files",
                "logical_bytes_by_path",
                "classification",
                "rule_file_counts",
                "same_basename_size_hint_groups",
                "same_basename_size_hint_rows",
                "new_xlsx_exact_basename_matches_in_enumerated_files",
            )
        },
        indent=2,
    )
)
print(
    "TOP_ARCHIVE_GROUPS",
    json.dumps([r for r in grouplist if r["classification"] == "ARCHIVE_PROPOSAL"][:12], indent=2),
)
