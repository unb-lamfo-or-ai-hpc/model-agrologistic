import hashlib
import json
from pathlib import Path

import pandas as pd

from src.logic.artur_adapter import build_artur_solver_workbook
from src.logic.artur_benchmark import git_blob_sha
from src.logic.excel_loader import ExcelLoaderConfig, load_model_data_from_excel


def _write_csv_with_identity(path: Path, frame: pd.DataFrame) -> dict:
    frame.to_csv(path, index=False, lineterminator="\n", float_format="%.12g")
    data = path.read_bytes()
    return {
        "rows": len(frame),
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
    }


def test_adapter_builds_audited_workbook_with_frozen_distances(tmp_path: Path):
    commit = "a" * 40
    normalized_dir = tmp_path / "instance" / "normalized"
    normalized_dir.mkdir(parents=True)
    tables = {
        "supply.csv": pd.DataFrame(
            {
                "Produto": ["Corn"],
                "Cidade": ["Origin - GO"],
                "Latitude": [-16.0],
                "Longitude": [-49.0],
                "Data": ["2025-01"],
                "Peso (ton)": [10.0],
            }
        ),
        "demand.csv": pd.DataFrame(
            {
                "Produto": ["Corn", "Corn"],
                "Cidade": ["Demand - GO", "Port - SP"],
                "Latitude": [-16.5, -23.9],
                "Longitude": [-49.5, -46.3],
                "Data": ["2025-01", "2025-01"],
                "Peso (ton)": [8.0, None],
                "Tipo_Demanda": ["DOMESTICA", "EXPORTACAO"],
                "Regra_Limite": ["FIXO", "AUTO_OFERTA_TOTAL_PRODUTO_PERIODO"],
            }
        ),
        "warehouses.csv": pd.DataFrame(
            {
                "CDA": ["W1", "W2"],
                "Status": ["Existing", "Candidate"],
                "Municipality": ["Origin", "Port"],
                "State": ["GO", "SP"],
                "Latitude": [-16.1, -23.8],
                "Longitude": [-49.1, -46.2],
                "Storage Provider": ["Public", "Private"],
                "Type": ["Convencional", "Graneleiro"],
                "Static Cap. (t)": [100.0, 0.0],
                "Recep. Cap. (t)": [20.0, 0.0],
                "Exped. Cap. (t)": [20.0, 0.0],
                "Max Static Cap. (t)": [0.0, 50.0],
                "Opening Cost ($)": [0.0, 1000.0],
            }
        ),
        "distances.csv": pd.DataFrame(
            [
                (arc, origin, destination, value)
                for value, (arc, origin, destination) in enumerate(
                    [
                        ("OD", "Origin - GO", "W1"),
                        ("OD", "Origin - GO", "W2"),
                        ("DC", "W1", "Demand - GO"),
                        ("DC", "W1", "Port - SP"),
                        ("DC", "W2", "Demand - GO"),
                        ("DC", "W2", "Port - SP"),
                        ("DD", "W1", "W2"),
                        ("DD", "W2", "W1"),
                    ],
                    start=101,
                )
            ],
            columns=["arc_type", "origin", "destination", "distance_km"],
        ),
    }
    identities = {
        filename: _write_csv_with_identity(normalized_dir / filename, frame)
        for filename, frame in tables.items()
    }
    (normalized_dir / "transformation_audit.json").write_text(
        json.dumps(
            {
                "instance_name": "artur_test_i001",
                "normalization_policy": "bounded_reproduction_v1",
                "normalized_table_files": identities,
            }
        ),
        encoding="utf-8",
    )

    benchmark_dir = tmp_path / "cache" / commit / "benchmark"
    benchmark_dir.mkdir(parents=True)
    reference_frames = {
        "Valor_Tonelada_km.xlsx": pd.DataFrame(
            {"Estado": ["GO", "SP"], "Frete Tonelada Km": [1.0, 1.5]}
        ),
        "Tarifa_de_Armazenagem.xlsx": pd.DataFrame(
            {
                "Produto": ["Corn", "Outros"],
                "Armazenar_Publico": [2.0, 2.0],
                "Armazenar_Privado": [3.0, 3.0],
            }
        ),
        "Custos_Investimento.xlsx": pd.DataFrame(
            {
                "Tipo": ["Expansão", "Granelização", "Novo Armazém Convencional"],
                "Custo Baixo (R$/t)": [1000.0, 600.0, 800.0],
                "Custo Alto (R$/t)": [1100.0, 760.0, 900.0],
            }
        ),
        "Custos_Transbordo.xlsx": pd.DataFrame(
            {"Tipo": ["Existing", "Candidate"], "Transbordo/t": [9.56, 6.9]}
        ),
    }
    assets = []
    for filename, frame in reference_frames.items():
        path = benchmark_dir / filename
        frame.to_excel(path, index=False)
        data = path.read_bytes()
        assets.append(
            {
                "path": f"benchmark/{filename}",
                "git_blob_sha": git_blob_sha(data),
                "size_bytes": len(data),
            }
        )
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(
        json.dumps(
            {
                "tracks": {
                    "artur_benchmark_reproduction": {
                        "repository": "https://github.com/example/repository",
                        "commit_sha": commit,
                        "assets": assets,
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    workbook, audit_path = build_artur_solver_workbook(
        normalized_dir,
        tmp_path / "cache",
        tmp_path / "instance" / "solver",
        contract_path=contract_path,
    )

    data = load_model_data_from_excel(
        workbook,
        ExcelLoaderConfig(
            compute_haversine_distances=False,
            use_workbook_distances=True,
            include_transshipment_routes=True,
            candidate_cost_policy="fixed_total",
        ),
    )
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert data.dist_od[("Origin - GO", "W1")] == 101
    assert data.opening_fixed_cost["W2"] == 1000
    assert data.max_expand_capacity["W1"] == 10_000
    assert audit["reproduction_level"] == "bounded"
    assert audit["model_data_signature"]["routes_dd"] == 2
    assert len(audit["workbook"]["sha256"]) == 64

