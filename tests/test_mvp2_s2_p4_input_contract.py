"""Real public Excel/manifest integration, not a fake ExperimentSpec or private input."""

import json
import shlex
import subprocess
import sys
import tempfile
from dataclasses import asdict

import pandas as pd
import pytest
import yaml

from scripts import mvp2_s2_h300_runtime as r
from scripts import mvp2_s2_p4_admission as a
from scripts import mvp2_s2_p4_observation as o
from src.logic import excel_loader, mathematical_contract
from src.logic import experiment_runner as runner
from src.logic.interhub_connectivity import write_interhub_audit
from tests.test_excel_loader import build_tiny_golden_excel


@pytest.fixture
def public_input(tmp_path, monkeypatch):
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    workbook = tmp_path / "public-fixture.xlsx"
    build_tiny_golden_excel(workbook)
    sheets = pd.read_excel(workbook, sheet_name=None)
    sheets["Cenarios"] = pd.DataFrame(
        [
            {
                "Cenario": "scenario-" + str(i),
                "Probabilidade": 1 / 9,
                "Ativo": "SIM",
                "Multiplicador_Oferta": 1.0,
                "Multiplicador_Demanda_Domestica": 1.0,
            }
            for i in range(9)
        ]
    )
    with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name, index=False)
    reference = tmp_path / "campaign.yaml"
    raw = {
        "version": 1,
        "experiments": [
            {
                "name": "case-" + str(i),
                "workbook": workbook.name,
                "loader": {
                    "include_stochastic_scenarios": True,
                    "include_transshipment_routes": True,
                },
                "model": {
                    "mode": "sto",
                    "objective_policy": "lexicographic",
                    "use_direct_origin_customer": False,
                    "interhub_strong_connectivity": True,
                    "route_filter_strategy": "connectivity_preserving_pareto",
                },
                "calculate_evpi_vss": False,
                "resume_evpi_vss": False,
            }
            for i in range(3)
        ],
    }
    reference.write_text(yaml.safe_dump(raw), encoding="utf-8")
    manifest = runner.load_experiment_manifest(reference)
    spec = manifest.experiments[2]
    assert isinstance(spec, runner.ExperimentSpec) and not hasattr(spec, "resume")
    data = mathematical_contract.prepare_model_data(
        excel_loader.load_model_data_from_excel(spec.workbook, spec.loader), spec.model
    )
    audits = tmp_path / "audits"
    write_interhub_audit(data.metadata["interhub_connectivity"], audits)
    review = {
        "counts": runner._data_signature(data)["counts"],
        "snapshot_fields": asdict(runner.estimate_model_size(data, spec.model)),
        "audit_sha256": {p.name: a.p.sha_file(p) for p in audits.iterdir() if p.is_file()},
    }
    model_audit = (
        json.dumps(
            runner.build_model_audit(data, spec.model), ensure_ascii=False, indent=2, sort_keys=True
        )
        + "\n"
    ).encode()
    review["audit_sha256"]["model_audit.json"] = r.academic.sha(model_audit)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/mvp2_h300_input_size_review.json").write_text(json.dumps(review))
    monkeypatch.setattr(r, "ROOT", tmp_path)
    monkeypatch.setattr(r, "REFERENCE", a.p.sha_file(reference))
    monkeypatch.setattr(r.d, "WORKBOOK", a.p.sha_file(workbook))
    return reference, manifest, data, review


def test_real_manifest_excel_reader_reaches_identity_without_solver(public_input, monkeypatch):
    reference, manifest, expected, review = public_input
    monkeypatch.setattr(r, "_native", lambda *args, **kwargs: pytest.fail("native solve"))
    monkeypatch.setattr(runner, "solve_model", lambda *args, **kwargs: pytest.fail("optimization"))
    actual, config, identity = r._input(reference)
    assert config == manifest.experiments[2].model
    assert actual.warehouses == expected.warehouses
    assert identity["counts"] == review["counts"]
    assert identity["size"] == review["snapshot_fields"]
    assert identity["data_sha256"] and identity["config_sha256"]
    assert manifest.experiments[2].resume_evpi_vss is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("mode", "det"),
        ("objective_policy", "penalty"),
        ("use_direct_origin_customer", True),
        ("calculate_evpi_vss", True),
        ("resume_evpi_vss", True),
    ],
)
def test_real_slotted_spec_rejects_scientific_flags_before_excel(
    public_input, monkeypatch, field, value
):
    reference, manifest, _, _ = public_input
    spec = manifest.experiments[2]
    setattr(spec.model if hasattr(spec.model, field) else spec, field, value)
    monkeypatch.setattr(runner, "load_experiment_manifest", lambda *args: manifest)
    monkeypatch.setattr(
        excel_loader,
        "load_model_data_from_excel",
        lambda *args: pytest.fail("Excel accessed despite invalid flag"),
    )
    with pytest.raises(ValueError, match="Scientific mode"):
        r._input(reference)


@pytest.mark.parametrize("which", ["workbook", "reference"])
def test_real_file_digest_drift_fails(public_input, which):
    reference, manifest, _, _ = public_input
    path = reference if which == "reference" else manifest.experiments[2].workbook
    with path.open("ab") as stream:
        stream.write(b"changed")
    with pytest.raises(ValueError, match="drift"):
        r._input(reference)


@pytest.mark.parametrize(
    "which",
    [
        "counts",
        "snapshot_fields",
        "model_audit.json",
        "interhub_connectivity_audit.json",
        "interhub_components.csv",
        "interhub_repair_edges.csv",
        "interhub_path_summary.csv",
    ],
)
def test_real_input_audit_comparisons_still_fail_closed(public_input, which):
    reference, _, _, review = public_input
    if which in {"counts", "snapshot_fields"}:
        key = next(iter(review[which]))
        review[which][key] += 1
    else:
        review["audit_sha256"][which] = "0" * 64
    (r.ROOT / "docs/mvp2_h300_input_size_review.json").write_text(json.dumps(review))
    with pytest.raises(ValueError, match="drift"):
        r._input(reference)


def test_actual_input_failure_precedes_every_claim_and_submission(tmp_path, monkeypatch):
    monkeypatch.setattr(o, "BASE", tmp_path)
    bootstrap = tmp_path / "preserved-bootstrap"
    bootstrap.mkdir()
    (bootstrap / "evidence").write_bytes(b"original")

    def fail(*args):
        raise AttributeError("legacy ExperimentSpec.resume")

    with pytest.raises(AttributeError):
        o.start(
            "b" * 40,
            acknowledged=True,
            prepare=fail,
            command=lambda *args, **kwargs: pytest.fail("sbatch reached"),
        )
    assert not (tmp_path / o.CLAIM).exists() and not (tmp_path / a.CLAIM).exists()
    assert (bootstrap / "evidence").read_bytes() == b"original"


def test_current_transport_hash_and_original_runtime_remain_explicit():
    assert a.p.sha_file(o.ROOT / r.ENTRY) == a.TRANSPORT[r.ENTRY]
    assert a.PR101_TRANSPORT[r.ENTRY] == (
        "f1ebdf77be384e5b1cfed39dcaf372a36262f2157df96488947a0bb6a518c36d"
    )
    assert a.TRANSPORT[r.ENTRY] != a.PR101_TRANSPORT[r.ENTRY]
    assert all(a.TRANSPORT[k] == v for k, v in a.PR101_TRANSPORT.items() if k != r.ENTRY)


@pytest.mark.skipif(sys.platform != "linux", reason="Actual Bash absent-claim diagnostic on Linux")
def test_actual_wait_status_collect_without_claim_is_explicit_and_effect_free(tmp_path):
    wrapper = o.ROOT / "scripts/npad_s2_p4_observation.sh"
    raw = wrapper.read_text()
    base = "BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit"
    assert raw.count(base) == 1
    isolated = tmp_path / "wrapper.sh"
    isolated.write_text(raw.replace(base, "BASE=" + shlex.quote(str(tmp_path))), encoding="utf-8")
    for action in ("wait", "status", "collect"):
        result = subprocess.run(["bash", str(isolated), action, "b" * 40], capture_output=True)
        assert result.returncode == 2
        assert b"OBSERVATION_STATUS=not_submitted" in result.stderr
        assert b"NO_JOB_OR_TERMINAL_COLLECTION_AVAILABLE" in result.stderr
