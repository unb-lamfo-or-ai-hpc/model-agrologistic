"""Effective-data and documentary checks, not GAMS compile/numerical parity."""

import copy
import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from scripts.export_scalar_gams_data import export
from src.logic.model_config import ModelConfig
from tests.test_scalar_contract import economic_data, scenario_data

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("mode", ["det", "sto"])
@pytest.mark.parametrize("direct", [False, True])
def test_export_uses_original_arrays_and_four_costs_without_solver(tmp_path, mode, direct):
    data = economic_data()
    data.routes_oc = {("O", "C", "P")}
    data.dist_oc = {("O", "C"): 5}
    if mode == "sto":
        data = scenario_data(data, {"low": 0.25, "high": 0.75})
    before = copy.deepcopy(data)
    receipt = export(
        data,
        ModelConfig(mode=mode, use_direct_origin_customer=direct),
        tmp_path / "export",
        provenance={"input": "synthetic"},
    )
    raw = (tmp_path / "export/data.inc").read_bytes()
    text = raw.decode()
    assert data == before
    assert hashlib.sha256(raw).hexdigest() == receipt["data_include_sha256"]
    assert receipt["execution_admitted"] is False
    assert "costOW('o00000','w00000','p00000') = 9.0;" in text
    assert "costWD('w00000','c00000','p00000') = 6.0;" in text
    assert ("costOD(" in text) is direct
    if direct:
        assert "costOD('o00000','c00000','p00000') = 20.0;" in text
    assert "rhoNew = 0.2;" in text and "etaBulk = 1.0;" in text
    if mode == "det":
        assert "pi('deterministic') = 1.0;" in text
        assert "supply('deterministic','o00000','p00000','t00000') = 10.0;" in text
    else:
        assert "pi('s00000') = 0.25;" in text
        assert "pi('s00001') = 0.75;" in text
    with pytest.raises(FileExistsError):
        export(data, ModelConfig(mode=mode), tmp_path / "export", provenance={})


@pytest.mark.parametrize(
    "field,value",
    [
        ("candidate_capacity_mode", "fixed"),
        ("capacity_coupling_policy", "period_equivalent"),
        ("allow_emergency_static_capacity", False),
    ],
)
def test_untranslated_settings_fail_without_output(tmp_path, field, value):
    with pytest.raises(ValueError, match="outside"):
        export(
            economic_data(),
            replace(ModelConfig(), **{field: value}),
            tmp_path / "absent",
            provenance={},
        )
    assert not (tmp_path / "absent").exists()


def test_translation_keeps_native_indicators_and_blocks_large_execution():
    text = (ROOT / "manuscript/supplement/appendix_c/model_common.inc").read_text()
    assert "indic closedStock(s,w,t)$y(w) 0" in text
    assert "indic closedReception(s,w,t)$y(w) 0" in text
    assert "gams/indicatorfile=grain.indic" in text
    assert "$setglobal execute_small 0" in text
    assert "card(w)>10" in text
    assert "qR(s,w,t);" in text
    assert "pi(s)*(" in text
    assert "sum(s,pi(s)*(" in text


def test_new_editorial_sections_are_numbered_and_ordered():
    text = (ROOT / "manuscript/index.qmd").read_text(encoding="utf-8")
    assert "# Declaration of generative AI" in text
    assert "manuscript preparation process {-}" not in text
    assert text.index("# Declaration of generative AI") < text.index("# Acknowledgements")
    assert text.index("# Acknowledgements") < text.index("# References")
    assert "Núcleo de Processamento de Alto Desempenho" in text


def test_supplement_includes_cd_and_exact_input_membership_metadata():
    import json

    directory = ROOT / "manuscript/supplement"
    source = (directory / "index.qmd").read_text(encoding="utf-8")
    assert "{{< include appendix_c.qmd >}}" in source
    assert "{{< include appendix_d.qmd >}}" in source
    metadata = json.loads((directory / "appendix_d_inventory.json").read_text(encoding="utf-8"))
    assert all(metadata["nesting_by_identifier"].values())
    assert len(metadata["original_receipt_order_comparisons"]) == 8
    assert all(r["input_order_exact_match"] for r in metadata["original_receipt_order_comparisons"])
    assert metadata["h500_optimized_output_available"] is False
    populations = {
        r["population"]: (r["existing"], r["candidate"])
        for r in metadata["workbooks"]
        if "population" in r
    }
    assert populations == {215: (146, 69), 300: (146, 154), 400: (146, 254), 500: (146, 354)}
    cells = {(r["sheet"], r["cell"]): r["original"] for r in metadata["reference_cells"]}
    assert [cells["Parametros_Modelo", f"B{i}"] for i in (4, 5, 6)] == [1e6] * 3
