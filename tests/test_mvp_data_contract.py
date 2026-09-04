import hashlib
import json
from pathlib import Path

from src.logic.excel_loader import load_model_data_from_excel

CONTRACT_PATH = Path("data/manifests/mvp_data_contract.json")


def test_gold_workbook_matches_frozen_mvp_contract():
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    track = contract["tracks"]["gold_workbook_extension"]
    workbook_path = Path(track["path"])
    workbook_bytes = workbook_path.read_bytes()

    assert len(workbook_bytes) == track["size_bytes"]
    assert hashlib.sha256(workbook_bytes).hexdigest() == track["sha256"]

    data = load_model_data_from_excel(workbook_path)
    assert {
        "origins": len(data.origins),
        "warehouses": len(data.warehouses),
        "existing_warehouses": len(data.existing_warehouses),
        "candidate_warehouses": len(data.candidate_warehouses),
        "domestic_customers": len(data.domestic_customers),
        "export_customers": len(data.export_customers),
        "products": len(data.products),
        "periods": len(data.periods),
    } == track["structural_signature"]


def test_artur_benchmark_source_is_pinned_to_immutable_assets():
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    track = contract["tracks"]["artur_benchmark_reproduction"]

    assert len(track["commit_sha"]) == 40
    assert track["subtree"] == "benchmark"
    assert len(track["assets"]) == 10
    assert all(len(asset["git_blob_sha"]) == 40 for asset in track["assets"])
    assert all(asset["size_bytes"] > 0 for asset in track["assets"])
