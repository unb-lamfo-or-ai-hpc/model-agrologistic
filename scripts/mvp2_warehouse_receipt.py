"""Bind each attempt to included warehouses and its original selection protocol.

Reads the existing population auditor's manifest/order; does not select a new
population, infer opened facilities, rewrite registries or change model inputs.
"""

from __future__ import annotations

import csv
import io
import math
from pathlib import Path

from scripts import mvp2_scalar_r2 as r2

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ("model_order", "warehouse_id", "population_role", "selection_stratum", "candidate_rank")


def _rank(raw):
    if not raw.strip():
        return None
    value = float(raw)
    r2.require(math.isfinite(value) and value.is_integer() and value > 0, "Invalid candidate rank.")
    return int(value)


def read_policy(manifest, order, manifest_sha, order_sha, target):
    """Reproduce membership from the already-audited nested ranking, no resampling."""
    from src.logic.run_integrity import file_sha256

    r2.require(target in {215, 300, 400, 500}, "Reviewed population level required.")
    r2.require(
        file_sha256(manifest) == manifest_sha and file_sha256(order) == order_sha,
        "Population protocol hash differs.",
    )
    meta = r2.read(manifest)
    registered = r2.read(ROOT / "data/manifests/warehouse_population_source_v020.json")
    r2.require(
        meta["source_sha256"] == registered["source_sha256"],
        "Registry bytes differ: review source revision, do not substitute.",
    )
    r2.require(
        meta["anchor_source"]["sha256"]
        == file_sha256(ROOT / registered["canonical_anchor"]["workbook"]),
        "Canonical anchor bytes differ: source review required.",
    )
    r2.require(
        meta["schema_version"] == 1 and target in meta["target_populations"],
        "Population protocol differs.",
    )
    r2.require(
        bool(meta["selection_method"].strip()) and bool(meta["selection_seed"].strip()),
        "Selection method/seed required.",
    )
    with Path(order).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {
            "CDA",
            "population_role",
            "population_eligible",
            "selection_stratum",
            "candidate_rank",
        }
        r2.require(
            reader.fieldnames is not None
            and len(set(reader.fieldnames)) == len(reader.fieldnames)
            and required <= set(reader.fieldnames),
            "Population CSV schema differs.",
        )
        rows = list(reader)
    ids = [row["CDA"].strip() for row in rows]
    r2.require(all(ids) and len(ids) == len(set(ids)), "Duplicate/missing registry identifier.")
    members = []
    for row, warehouse in zip(rows, ids, strict=True):
        role = row["population_role"]
        r2.require(role in {"existing", "candidate"}, "Unknown population role.")
        rank = _rank(row["candidate_rank"])
        eligible = row["population_eligible"].strip().lower()
        r2.require(eligible in {"true", "false"}, "Invalid eligibility flag.")
        include = role == "existing" or (
            eligible == "true" and rank is not None and rank <= target - 146
        )
        if include:
            r2.require(eligible == "true", "Protected/selected warehouse cannot be ineligible.")
            members.append(
                {
                    "warehouse_id": warehouse,
                    "population_role": role,
                    "selection_stratum": row["selection_stratum"],
                    "candidate_rank": rank,
                }
            )
    existing = [m for m in members if m["population_role"] == "existing"]
    candidates = [m for m in members if m["population_role"] == "candidate"]
    r2.require(len(existing) == 146 and len(members) == target, "Population count differs.")
    r2.require(
        all(
            m["selection_stratum"] == "protected_existing" and m["candidate_rank"] is None
            for m in existing
        ),
        "Protected existing criterion differs.",
    )
    r2.require(
        sorted(m["candidate_rank"] for m in candidates) == list(range(1, target - 146 + 1)),
        "Selected candidate ranking has gaps/duplicates.",
    )
    r2.require(
        sum(m["selection_stratum"] == "canonical_gold_anchor" for m in candidates) == 69,
        "Original 69 anchor candidates must be preserved.",
    )
    r2.require(
        all(
            (m["selection_stratum"] == "canonical_gold_anchor") == (m["candidate_rank"] <= 69)
            for m in candidates
        ),
        "Canonical anchor must be the first69 frozen ranks.",
    )
    return {
        "schema_version": "warehouse-selection-policy-v1",
        "target_population": target,
        "selection_method": meta["selection_method"],
        "criterion": (
            "Protect all146 existing and69 canonical anchor candidates; "
            "extend by frozen deterministic nested rank, never solver opening decisions."
        ),
        "selection_seed": meta["selection_seed"],
        "registry_sha256": meta["source_sha256"],
        "anchor_sha256": meta["anchor_source"]["sha256"],
        "population_manifest_sha256": manifest_sha,
        "population_order_sha256": order_sha,
        "members": members,
    }


def membership_receipt(data, policy):
    r2.require(
        policy is not None and policy["schema_version"] == "warehouse-selection-policy-v1",
        "Explicit warehouse selection policy required.",
    )
    r2.require(
        bool(policy["selection_method"].strip()) and bool(policy["criterion"].strip()),
        "Selection criterion required.",
    )
    r2.require(
        len(data.warehouses) == len(set(data.warehouses)) == policy["target_population"],
        "Model warehouse count/duplicates differ.",
    )
    if policy["target_population"] >= 215:
        r2.require(
            policy["selection_method"] != "public_tiny_fixture",
            "Tiny fixture cannot certify production membership.",
        )
    by_id = {m["warehouse_id"]: m for m in policy["members"]}
    r2.require(
        len(by_id) == len(policy["members"]) and set(by_id) == set(data.warehouses),
        "Selected warehouse membership differs from actual input.",
    )
    existing, candidates = set(data.existing_warehouses), set(data.candidate_warehouses)
    r2.require(
        not existing & candidates and existing | candidates == set(data.warehouses),
        "Warehouse roles do not partition the actual input.",
    )
    included = []
    for index, warehouse in enumerate(data.warehouses, 1):
        row = by_id[warehouse]
        role = "existing" if warehouse in existing else "candidate"
        r2.require(row["population_role"] == role, "Frozen warehouse role differs.")
        included.append({"model_order": index, **row})
    content = csv_bytes(included)
    return {
        "schema_version": "warehouses-used-v1",
        "scope": "Included in MILP, NOT facilities selected/opened by the solver.",
        "policy_sha256": r2.digest(r2.encoded(policy)),
        "criterion": policy["criterion"],
        "selection_method": policy["selection_method"],
        "selection_seed": policy.get("selection_seed"),
        "count": len(included),
        "existing_count": len(existing),
        "candidate_count": len(candidates),
        "ordered_ids_sha256": r2.digest(r2.encoded(data.warehouses)),
        "csv_sha256": r2.digest(content),
        "included": included,
    }


def csv_bytes(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")
