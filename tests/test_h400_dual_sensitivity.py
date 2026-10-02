"""One-factor method sensitivity preserves the original evidence and resource budget."""

import json

import pytest
import yaml

from scripts.prepare_h400_dual_sensitivity import prepare, sha256
from scripts.prepare_nine_scenario_campaign import campaign


@pytest.fixture
def baseline(tmp_path):
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    workbook = tmp_path / "input.xlsx"
    workbook.write_bytes(b"fixture: no workbook parsing or solve required")
    old = tmp_path / "baseline"
    old.mkdir()
    source = campaign(root, old / "runs", populations=(400,),
                      workbook_overrides={400: workbook}, max_estimated_variables=43000000,
                      resource_review_note="Frozen 400-hub resource experiment.")
    manifest = old / "campaign.yaml"
    manifest.write_text(yaml.safe_dump(source))
    return manifest, workbook, source


def test_method_is_the_only_solver_or_model_change(baseline, tmp_path):
    manifest, workbook, original = baseline
    old_bytes = manifest.read_bytes()
    destination = tmp_path / "dual"
    output = prepare(manifest, destination, sha256(manifest), sha256(workbook))
    actual = yaml.safe_load(output.read_text())
    assert actual["defaults"]["solver"]["solver_options"].pop("Method") == 1
    actual["output_dir"] = original["output_dir"]
    for run in actual["experiments"]:
        run["name"] = run["name"].removesuffix("_dual")
    assert actual == original
    assert manifest.read_bytes() == old_bytes
    receipt = json.loads((destination / "sensitivity_contract.json").read_text())
    assert receipt["recommended_initial_indices"] == [1]
    assert receipt["manifest_sha256"] == sha256(output)
    assert receipt["status"] == "prepared_not_executed"
    with pytest.raises(FileExistsError):
        prepare(manifest, destination, sha256(manifest), sha256(workbook))


@pytest.mark.parametrize("bad_manifest", [True, False])
def test_hash_mismatch_writes_nothing(baseline, tmp_path, bad_manifest):
    manifest, workbook, _ = baseline
    destination = tmp_path / "rejected"
    with pytest.raises(ValueError, match="checksum"):
        prepare(manifest, destination, "0" * 64 if bad_manifest else sha256(manifest),
                sha256(workbook) if bad_manifest else "0" * 64)
    assert not destination.exists()


def test_rejects_output_inside_old_campaign(baseline):
    manifest, workbook, _ = baseline
    with pytest.raises(ValueError, match="outside"):
        prepare(manifest, manifest.parent / "nested", sha256(manifest), sha256(workbook))


@pytest.mark.parametrize("change", ["threads", "method", "override", "evpi", "order"])
def test_rejects_confounding_baselines(baseline, tmp_path, change):
    manifest, workbook, source = baseline
    if change == "threads":
        source["defaults"]["solver"]["threads"] = 8
    elif change == "method":
        source["defaults"]["solver"]["solver_options"]["Method"] = 2
    elif change == "override":
        source["experiments"][1]["solver"] = {"solver_options": {"Method": 4}}
    elif change == "evpi":
        source["experiments"][0]["calculate_evpi_vss"] = True
    else:
        source["experiments"].reverse()
    manifest.write_text(yaml.safe_dump(source))
    with pytest.raises(ValueError):
        prepare(manifest, tmp_path / "rejected", sha256(manifest), sha256(workbook))
    assert not (tmp_path / "rejected").exists()
