from pathlib import Path

import pandas as pd

from src.logic.excel_loader import ExcelLoaderConfig, load_model_data_from_excel
from src.logic.model_config import ModelConfig
from src.logic.model_validation import validate_model_data


def build_tiny_excel(path: Path) -> None:
    oferta = pd.DataFrame(
        [
            {
                "Produto": "Soja",
                "Cidade": "Rio Verde - GO",
                "Latitude": -17.7923,
                "Longitude": -50.9192,
                "Data": "2026-01",
                "Peso (ton)": 100.0,
            },
            {
                "Produto": "Soja",
                "Cidade": "Rio Verde - GO",
                "Latitude": -17.7923,
                "Longitude": -50.9192,
                "Data": "2026-02",
                "Peso (ton)": 120.0,
            },
        ]
    )

    demanda = pd.DataFrame(
        [
            {
                "Produto": "Soja",
                "Cidade": "Goiânia - GO",
                "Latitude": -16.6869,
                "Longitude": -49.2648,
                "Data": "2026-01",
                "Peso (ton)": 80.0,
            },
            {
                "Produto": "Soja",
                "Cidade": "Goiânia - GO",
                "Latitude": -16.6869,
                "Longitude": -49.2648,
                "Data": "2026-02",
                "Peso (ton)": 90.0,
            },
            {
                "Produto": "Soja",
                "Cidade": "Santos - SP",
                "Latitude": -23.9535,
                "Longitude": -46.3350,
                "Data": "2026-01",
                "Peso (ton)": "∞",
            },
        ]
    )

    warehouses = pd.DataFrame(
        [
            {
                "CDA": "W1",
                "Status": "Existente",
                "Município": "Rio Verde",
                "UF": "GO",
                "Latitude": -17.7923,
                "Longitude": -50.9192,
                "Armazenador": "COMPANHIA NACIONAL DE ABASTECIMENTO",
                "Tipo": "Convencional",
                "Cap. Estática (t)": 200.0,
                "Cap. Recepção (t)": 200.0,
                "Cap. Expedição (t)": 200.0,
                "Cap. Estática Máxima (t)": 0.0,
                "Custo de Abertura ($)": 0.0,
            },
            {
                "CDA": "W2",
                "Status": "Candidato",
                "Município": "Santos",
                "UF": "SP",
                "Latitude": -23.9535,
                "Longitude": -46.3350,
                "Armazenador": "PRIVADO",
                "Tipo": "Graneleiro",
                "Cap. Estática (t)": 0.0,
                "Cap. Recepção (t)": 0.0,
                "Cap. Expedição (t)": 0.0,
                "Cap. Estática Máxima (t)": 300.0,
                "Custo de Abertura ($)": 3000.0,
            },
        ]
    )

    frete = pd.DataFrame(
        [
            {"Estado": "GO", "Frete Tonelada Km": 1.0},
            {"Estado": "SP", "Frete Tonelada Km": 2.0},
        ]
    )

    tarifa_armz = pd.DataFrame(
        [
            {
                "Produto": "Outros",
                "Armazenar_Publico": 50.0,
                "Armazenar_Privado": 60.0,
            },
            {
                "Produto": "Soja",
                "Armazenar_Publico": 45.0,
                "Armazenar_Privado": 55.0,
            },
        ]
    )

    custo_invest = pd.DataFrame(
        [
            {
                "Tipo": "Novo Armazém Convencional",
                "Custo Baixo (R$/t)": 1000.0,
                "Custo Alto (R$/t)": 1500.0,
            },
            {
                "Tipo": "Novo Silo Metálico",
                "Custo Baixo (R$/t)": 785.0,
                "Custo Alto (R$/t)": 1310.0,
            },
            {
                "Tipo": "Expansão",
                "Custo Baixo (R$/t)": 600.0,
                "Custo Alto (R$/t)": 1200.0,
            },
            {
                "Tipo": "Granelização",
                "Custo Baixo (R$/t)": 380.0,
                "Custo Alto (R$/t)": 660.0,
            },
        ]
    )

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        oferta.to_excel(writer, sheet_name="Oferta", index=False)
        demanda.to_excel(writer, sheet_name="Demanda", index=False)
        warehouses.to_excel(writer, sheet_name="Warehouses", index=False)
        frete.to_excel(writer, sheet_name="Frete", index=False)
        tarifa_armz.to_excel(writer, sheet_name="Tarifa_Armz", index=False)
        custo_invest.to_excel(writer, sheet_name="Custo_Invest", index=False)


def test_load_model_data_from_excel_minimal_schema(tmp_path):
    path = tmp_path / "tiny_agrologistic.xlsx"
    build_tiny_excel(path)

    data = load_model_data_from_excel(path)

    assert data.origins == ["Rio Verde - GO"]
    assert data.domestic_customers == ["Goiânia - GO"]
    assert data.export_customers == ["Santos - SP"]

    assert data.warehouses == ["W1", "W2"]
    assert data.existing_warehouses == ["W1"]
    assert data.candidate_warehouses == ["W2"]

    assert data.products == ["Soja"]
    assert data.periods == ["2026-01", "2026-02"]

    assert data.supply[("Rio Verde - GO", "Soja", "2026-01")] == 100.0
    assert data.demand_dom[("Goiânia - GO", "Soja", "2026-01")] == 80.0

    assert data.demand_exp == {}
    assert len(data.metadata["unbounded_export_demand_keys"]) == 1

    assert ("Rio Verde - GO", "W1", "Soja") in data.routes_od
    assert ("W1", "Goiânia - GO", "Soja") in data.routes_dc
    assert ("W1", "Santos - SP", "Soja") in data.routes_dc

    assert ("Rio Verde - GO", "W1") in data.dist_od
    assert ("W1", "Goiânia - GO") in data.dist_dc

    assert data.opening_fixed_cost["W2"] == 0.0
    assert data.candidate_capacity_cost["W2"] == 10.0


def test_loaded_excel_data_passes_model_validation(tmp_path):
    path = tmp_path / "tiny_agrologistic.xlsx"
    build_tiny_excel(path)

    data = load_model_data_from_excel(path)

    result = validate_model_data(
        data=data,
        config=ModelConfig(mode="det", candidate_capacity_mode="scalable"),
        require_distances=True,
    )

    assert result.is_valid
    assert result.errors == []


def test_fixed_total_candidate_cost_policy(tmp_path):
    path = tmp_path / "tiny_agrologistic.xlsx"
    build_tiny_excel(path)

    data = load_model_data_from_excel(
        path,
        config=ExcelLoaderConfig(candidate_cost_policy="fixed_total"),
    )

    assert data.opening_fixed_cost["W2"] == 3000.0
    assert data.candidate_capacity_cost["W2"] == 0.0