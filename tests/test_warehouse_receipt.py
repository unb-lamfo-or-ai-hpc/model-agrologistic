"""Per-attempt population provenance; no real private registry or solver."""

import copy
import csv
import json
from types import SimpleNamespace

import pytest

from scripts import mvp2_scalar_r3a as r
from scripts import mvp2_warehouse_receipt as w
from tests.test_scalar_r3a import fixture, tiny_selection


def registry_files(tmp_path, mutate=None):
    registered = w.r2.read(w.ROOT / "data/manifests/warehouse_population_source_v020.json")
    meta = {
        "schema_version": 1,
        "source_sha256": registered["source_sha256"],
        "anchor_source": {
            "sha256": r.file_hash(w.ROOT / registered["canonical_anchor"]["workbook"])
        },
        "selection_seed": "unit_fixture_not_live",
        "selection_method": "existing frozen nested ranking",
        "target_populations": [215, 300, 400, 500],
    }
    rows = (
        [
            {
                "CDA": "E" + str(i),
                "population_role": "existing",
                "population_eligible": "True",
                "selection_stratum": "protected_existing",
                "candidate_rank": "",
            }
            for i in range(146)
        ]
        + [
            {
                "CDA": "C" + str(i),
                "population_role": "candidate",
                "population_eligible": "True",
                "selection_stratum": "canonical_gold_anchor" if i <= 69 else "GO|Silo|Q1",
                "candidate_rank": str(float(i)),
            }
            for i in range(1, 355)
        ]
        + [
            {
                "CDA": "excluded_zero_capacity",
                "population_role": "candidate",
                "population_eligible": "False",
                "selection_stratum": "",
                "candidate_rank": "",
            }
        ]
    )
    if mutate is not None:
        mutate(meta, rows)
    manifest, order = tmp_path / "manifest.json", tmp_path / "order.csv"
    manifest.write_text(json.dumps(meta))
    with order.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return manifest, order, r.file_hash(manifest), r.file_hash(order)


@pytest.mark.parametrize("target,candidates", [(215, 69), (300, 154), (400, 254), (500, 354)])
def test_exact_selected_list_for_every_prospective_population(tmp_path, target, candidates):
    policy = w.read_policy(*registry_files(tmp_path), target)
    assert len(policy["members"]) == target
    assert sum(x["population_role"] == "existing" for x in policy["members"]) == 146
    assert sum(x["population_role"] == "candidate" for x in policy["members"]) == candidates
    assert "excluded_zero_capacity" not in {x["warehouse_id"] for x in policy["members"]}
    assert policy["selection_seed"] == "unit_fixture_not_live"


def test_memberships_remain_nested_without_resampling(tmp_path):
    args = registry_files(tmp_path)
    groups = [
        {x["warehouse_id"] for x in w.read_policy(*args, n)["members"]}
        for n in (215, 300, 400, 500)
    ]
    assert all(a < b for a, b in zip(groups[:-1], groups[1:], strict=True))


@pytest.mark.parametrize(
    "kind",
    [
        "registry_revision",
        "anchor_revision",
        "duplicate_id",
        "rank_gap",
        "missing_anchor",
        "missing_seed",
        "ineligible_existing",
    ],
)
def test_bad_selection_protocol_fails_closed(tmp_path, kind):
    def mutate(meta, rows):
        if kind == "registry_revision":
            meta["source_sha256"] = "f" * 64
        elif kind == "anchor_revision":
            meta["anchor_source"]["sha256"] = "f" * 64
        elif kind == "duplicate_id":
            rows[-1]["CDA"] = rows[0]["CDA"]
        elif kind == "rank_gap":
            rows[146]["candidate_rank"] = "900"
        elif kind == "missing_anchor":
            rows[146]["selection_stratum"] = "other"
        elif kind == "missing_seed":
            meta["selection_seed"] = ""
        elif kind == "ineligible_existing":
            rows[0]["population_eligible"] = "False"

    with pytest.raises(ValueError):
        w.read_policy(*registry_files(tmp_path, mutate), 215)


def test_selection_input_hash_required(tmp_path):
    manifest, order, msha, osha = registry_files(tmp_path)
    with pytest.raises(ValueError, match="protocol hash"):
        w.read_policy(manifest, order, msha, "0" * 64, 215)


@pytest.mark.parametrize(
    "kind",
    [
        "missing_criterion",
        "duplicate_model_id",
        "substituted_model_id",
        "wrong_role",
        "role_overlap",
        "missing_policy",
    ],
)
def test_attempt_must_match_actual_model_warehouses(kind):
    policy = copy.deepcopy(tiny_selection())
    data = SimpleNamespace(
        warehouses=["W1", "W2"], existing_warehouses=["W1"], candidate_warehouses=["W2"]
    )
    if kind == "missing_criterion":
        policy["criterion"] = ""
    elif kind == "duplicate_model_id":
        data.warehouses = ["W1", "W1"]
    elif kind == "substituted_model_id":
        data.warehouses = ["W1", "substitute"]
    elif kind == "wrong_role":
        policy["members"][0]["population_role"] = "candidate"
    elif kind == "role_overlap":
        data.candidate_warehouses = ["W1", "W2"]
    elif kind == "missing_policy":
        policy = None
    with pytest.raises(ValueError):
        w.membership_receipt(data, policy)


def test_model_order_is_preserved_separately_from_selection_rank():
    a = SimpleNamespace(
        warehouses=["W1", "W2"], existing_warehouses=["W1"], candidate_warehouses=["W2"]
    )
    b = SimpleNamespace(
        warehouses=["W2", "W1"], existing_warehouses=["W1"], candidate_warehouses=["W2"]
    )
    first, second = [w.membership_receipt(x, tiny_selection()) for x in (a, b)]
    assert first["ordered_ids_sha256"] != second["ordered_ids_sha256"]
    assert second["included"][0]["warehouse_id"] == "W2"
    assert second["included"][0]["candidate_rank"] == 1
    assert "NOT facilities selected/opened" in second["scope"]


@pytest.mark.parametrize("member", ["warehouses_used.csv", "warehouses_used.json"])
def test_corrupted_per_attempt_population_prevents_positive_review(member):
    files = fixture()
    files["cases/tiny_det/" + member] += b"corrupt"
    report = r.cohort_review(files)
    assert report["status"] == "partial_or_unvalidated_preserved"
    assert report["missing_or_rejected"][0]["name"] == "tiny_det"
