from pathlib import Path

import pandas as pd

from src.logic.excel_loader import ExcelLoaderConfig, load_model_data_from_excel
from src.logic.model_config import ModelConfig
from src.logic.model_validation import validate_model_data


def build_tiny_golden_excel(path: Path) -> None:
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
                "Cidade": "Jataí - GO",
                "Latitude": -17.8784,
                "Longitude": -51.7204,
                "Data": "2026-01",
                "Peso (ton)": 50.0,
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
                "Tipo_Demanda": "DOMESTICA",
                "Regra_Limite": "FIXO",
                "Peso_Modelo (ton)": 80.0,
                "Fonte_Parametro": "Informado",
                "Observacao": "Demanda doméstica fixa",
            },
            {
                "Produto": "Soja",
                "Cidade": "Santos - SP",
                "Latitude": -23.9535,
                "Longitude": -46.3350,
                "Data": "2026-01",
                "Peso (ton)": None,
                "Tipo_Demanda": "EXPORTACAO",
                "Regra_Limite": "AUTO_OFERTA_TOTAL_PRODUTO_PERIODO",
                "Peso_Modelo (ton)": None,
                "Fonte_Parametro": "Derivado_da_Oferta",
                "Observacao": "Mercado externo não restritivo",
            },
            {
                "Produto": "Soja",
                "Cidade": "Santos - SP",
                "Latitude": -23.9535,
                "Longitude": -46.3350,
                "Data": "2026-02",
                "Peso (ton)": None,
                "Tipo_Demanda": "EXPORTACAO",
                "Regra_Limite": "AUTO_OFERTA_TOTAL_PRODUTO_PERIODO",
                "Peso_Modelo (ton)": None,
                "Fonte_Parametro": "Derivado_da_Oferta",
                "Observacao": "Mercado externo não restritivo",
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
                "Permite_Granelizacao": "SIM",
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
                "Custo_Fixo_Abertura_Modelo ($)": 1000.0,
                "Custo_Variavel_Capacidade_Modelo ($/t)": 20.0,
                "Permite_Granelizacao": "NAO",
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

    parametros_modelo = pd.DataFrame(
        [
            {
                "Parametro": "unmet_demand_penalty_default",
                "Valor": 1_000_000.0,
                "Fonte_Parametro": "Sintético",
            }
        ]
    )

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        oferta.to_excel(writer, sheet_name="Oferta", index=False)
        demanda.to_excel(writer, sheet_name="Demanda", index=False)
        warehouses.to_excel(writer, sheet_name="Warehouses", index=False)
        frete.to_excel(writer, sheet_name="Frete", index=False)
        tarifa_armz.to_excel(writer, sheet_name="Tarifa_Armz", index=False)
        custo_invest.to_excel(writer, sheet_name="Custo_Invest", index=False)
        parametros_modelo.to_excel(writer, sheet_name="Parametros_Modelo", index=False)


def test_load_model_data_from_golden_excel_schema(tmp_path):
    path = tmp_path / "tiny_golden_agrologistic.xlsx"
    build_tiny_golden_excel(path)

    data = load_model_data_from_excel(path)

    assert data.origins == ["Rio Verde - GO", "Jataí - GO"]
    assert data.domestic_customers == ["Goiânia - GO"]
    assert data.export_customers == ["Santos - SP"]

    assert data.warehouses == ["W1", "W2"]
    assert data.existing_warehouses == ["W1"]
    assert data.candidate_warehouses == ["W2"]

    assert data.products == ["Soja"]
    assert data.periods == ["2026-01", "2026-02"]

    assert data.supply[("Rio Verde - GO", "Soja", "2026-01")] == 100.0
    assert data.supply[("Jataí - GO", "Soja", "2026-01")] == 50.0
    assert data.demand_dom[("Goiânia - GO", "Soja", "2026-01")] == 80.0

    assert data.demand_exp[("Santos - SP", "Soja", "2026-01")] == 150.0
    assert data.demand_exp[("Santos - SP", "Soja", "2026-02")] == 120.0

    assert ("Rio Verde - GO", "W1", "Soja") in data.routes_od
    assert ("W1", "Goiânia - GO", "Soja") in data.routes_dc
    assert ("W1", "Santos - SP", "Soja") in data.routes_dc

    assert ("Rio Verde - GO", "W1") in data.dist_od
    assert ("W1", "Goiânia - GO") in data.dist_dc

    assert data.opening_fixed_cost["W2"] == 1000.0
    assert data.candidate_capacity_cost["W2"] == 20.0

    assert data.metadata["loader_warnings"] == []


def test_loaded_golden_excel_data_passes_model_validation(tmp_path):
    path = tmp_path / "tiny_golden_agrologistic.xlsx"
    build_tiny_golden_excel(path)

    data = load_model_data_from_excel(path)

    result = validate_model_data(
        data=data,
        config=ModelConfig(mode="det", candidate_capacity_mode="scalable"),
        require_distances=True,
    )

    assert result.is_valid
    assert result.errors == []


def test_legacy_infinity_demand_is_still_supported(tmp_path):
    path = tmp_path / "legacy_infinity.xlsx"
    build_tiny_golden_excel(path)

    demanda = pd.read_excel(path, sheet_name="Demanda", engine="openpyxl")
    demanda = demanda.drop(
        columns=[
            "Tipo_Demanda",
            "Regra_Limite",
            "Peso_Modelo (ton)",
            "Fonte_Parametro",
            "Observacao",
        ]
    )
    demanda.loc[1, "Peso (ton)"] = "∞"
    demanda.loc[2, "Peso (ton)"] = "∞"

    all_sheets = pd.read_excel(path, sheet_name=None, engine="openpyxl")
    all_sheets["Demanda"] = demanda

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, df in all_sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    data = load_model_data_from_excel(path)

    assert data.demand_exp[("Santos - SP", "Soja", "2026-01")] == 150.0
    assert data.demand_exp[("Santos - SP", "Soja", "2026-02")] == 120.0
    assert data.metadata["loader_warnings"] != []


def test_fixed_total_candidate_cost_policy_is_used_when_enhanced_columns_absent(tmp_path):
    path = tmp_path / "tiny_golden_agrologistic.xlsx"
    build_tiny_golden_excel(path)

    all_sheets = pd.read_excel(path, sheet_name=None, engine="openpyxl")
    warehouses = all_sheets["Warehouses"].drop(
        columns=[
            "Custo_Fixo_Abertura_Modelo ($)",
            "Custo_Variavel_Capacidade_Modelo ($/t)",
        ]
    )
    all_sheets["Warehouses"] = warehouses

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, df in all_sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    data = load_model_data_from_excel(
        path,
        config=ExcelLoaderConfig(candidate_cost_policy="fixed_total"),
    )

    assert data.opening_fixed_cost["W2"] == 3000.0
    assert data.candidate_capacity_cost["W2"] == 0.0

def test_loader_splits_overlapping_domestic_and_export_customers(tmp_path):
    path = tmp_path / "overlap_demand.xlsx"
    build_tiny_golden_excel(path)

    all_sheets = pd.read_excel(path, sheet_name=None, engine="openpyxl")
    demanda = all_sheets["Demanda"]

    extra_domestic = demanda.iloc[[0]].copy()
    extra_domestic.loc[:, "Cidade"] = "Santos - SP"
    extra_domestic.loc[:, "Latitude"] = -23.9535
    extra_domestic.loc[:, "Longitude"] = -46.3350
    extra_domestic.loc[:, "Tipo_Demanda"] = "DOMESTICA"
    extra_domestic.loc[:, "Regra_Limite"] = "FIXO"
    extra_domestic.loc[:, "Peso (ton)"] = 10.0
    extra_domestic.loc[:, "Peso_Modelo (ton)"] = 10.0
    extra_domestic.loc[:, "Fonte_Parametro"] = "Informado"

    demanda = pd.concat([demanda, extra_domestic], ignore_index=True)
    all_sheets["Demanda"] = demanda

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, df in all_sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    data = load_model_data_from_excel(path)

    assert "Santos - SP | DOMESTICA" in data.domestic_customers
    assert "Santos - SP | EXPORTACAO" in data.export_customers

    assert set(data.domestic_customers).isdisjoint(set(data.export_customers))

    assert data.demand_dom[("Santos - SP | DOMESTICA", "Soja", "2026-01")] == 10.0
    assert data.demand_exp[("Santos - SP | EXPORTACAO", "Soja", "2026-01")] == 150.0

def test_legacy_infinity_overlap_is_split_with_correct_export_id(tmp_path):
    path = tmp_path / "legacy_overlap_infinity.xlsx"
    build_tiny_golden_excel(path)

    all_sheets = pd.read_excel(path, sheet_name=None, engine="openpyxl")
    demanda = all_sheets["Demanda"]

    extra_domestic = demanda.iloc[[0]].copy()
    extra_domestic.loc[:, "Cidade"] = "Santos - SP"
    extra_domestic.loc[:, "Latitude"] = -23.9535
    extra_domestic.loc[:, "Longitude"] = -46.3350
    extra_domestic.loc[:, "Tipo_Demanda"] = "DOMESTICA"
    extra_domestic.loc[:, "Regra_Limite"] = "FIXO"
    extra_domestic.loc[:, "Peso (ton)"] = 10.0
    extra_domestic.loc[:, "Peso_Modelo (ton)"] = 10.0

    demanda = pd.concat([demanda, extra_domestic], ignore_index=True)

    demanda = demanda.drop(
        columns=[
            "Tipo_Demanda",
            "Regra_Limite",
            "Peso_Modelo (ton)",
            "Fonte_Parametro",
            "Observacao",
        ]
    )

    demanda.loc[1, "Peso (ton)"] = "∞"
    demanda.loc[2, "Peso (ton)"] = "∞"

    all_sheets["Demanda"] = demanda

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, df in all_sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    data = load_model_data_from_excel(path)

    assert "Santos - SP | DOMESTICA" in data.domestic_customers
    assert "Santos - SP | EXPORTACAO" in data.export_customers

    assert set(data.domestic_customers).isdisjoint(set(data.export_customers))

    assert data.demand_dom[("Santos - SP | DOMESTICA", "Soja", "2026-01")] == 10.0
    assert data.demand_exp[("Santos - SP | EXPORTACAO", "Soja", "2026-01")] == 150.0