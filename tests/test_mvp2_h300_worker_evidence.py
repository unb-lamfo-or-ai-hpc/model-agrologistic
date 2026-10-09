"""Full worker envelopes remain portable after failure; no solver is executed."""

import copy
import io
import tarfile
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import mvp2_h300_native_worker as worker
from scripts import mvp2_h300_worker_evidence as evidence
from tests.test_mvp2_h300_native_worker import install_backend
from tests.test_mvp2_h300_partial import fixture, synthetic_control


def inputs(count=1, stages=1, native="TIME_LIMIT"):
    result, data, config, anchor = fixture(native, count, stages)
    runtime = {
        "python_version": "3.13.15",
        "python_implementation": "CPython",
        "system": "Linux",
        "machine": "x86_64",
        "python_executable_sha256": "1" * 64,
        "distributions": {"gurobipy": "13.0.3", "pytest": "9.1.1"},
    }
    anchor["runtime_sha256"] = evidence.design.digest(runtime)
    source = {
        "source_commit_declared": anchor["source_commit"],
        "source_files_sha256": {
            "pyproject.toml": "2" * 64,
            "src/logic/optimization.py": "3" * 64,
            "scripts/mvp2_h300_native_worker.py": "4" * 64,
        },
    }
    cohort = {
        "cohort_manifest_sha256": "5" * 64,
        "block_id": "6" * 64,
        "attempt_id": "7" * 64,
        "job_id": "123",
        "threads": anchor["threads"],
        "solver_profile_sha256": evidence.design.digest(
            asdict(worker.solver_profile(anchor["threads"]))
        ),
    }
    expected = evidence.binding(source, runtime, anchor, cohort)
    return result, data, config, expected


def publish(root, values):
    root.mkdir(exist_ok=True)
    if "binding.json" in values:
        expected = values["binding.json"]
        values = {
            **values,
            "worker-origin.json": {
                "binding_sha256": evidence.design.digest(expected),
                "anchor_sha256": evidence.design.digest(expected["anchor"]),
                **evidence.FLAGS,
            },
        }
    for name, value in values.items():
        path = root / name
        path.parent.mkdir(exist_ok=True, parents=True)
        evidence.controls.write_once(path, value)


def assets(root):
    return {
        name: (root / name).read_bytes()
        for name in evidence.ENVELOPE_FILES
        if (root / name).exists()
    }


def inspect(root, expected, data, config, state="COMPLETED", code="0:0"):
    return evidence.inspect_assets(
        assets(root), expected, data, config, scheduler_state=state, exit_code=code
    )


def test_public_entry_unconditionally_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(evidence, "runtime_receipt", lambda: pytest.fail("Read runtime"))
    with pytest.raises(PermissionError):
        evidence.execute_worker_envelope(tmp_path, accepted=True, production_admitted=True)
    assert not list(tmp_path.iterdir())


def test_binding_detached_and_profile_bound():
    _, _, _, expected = inputs()
    detached = evidence.binding(
        expected["source"], expected["runtime"], expected["anchor"], expected["cohort"]
    )
    expected["cohort"]["block_id"] = "8" * 64
    assert detached["cohort"]["block_id"] == "6" * 64
    with pytest.raises(ValueError):
        evidence.verify_binding(detached, expected)


@pytest.mark.parametrize(
    "field",
    [
        "source",
        "runtime",
        "anchor",
        "cohort",
        "policy_sha256",
        "production_admitted",
        "repeats_admitted",
    ],
)
def test_external_binding_drift(field):
    _, _, _, expected = inputs()
    changed = copy.deepcopy(expected)
    changed[field] = True if field.endswith("admitted") else "different"
    with pytest.raises(ValueError):
        evidence.verify_binding(changed, expected)


@pytest.mark.parametrize(
    "field,value",
    [
        ("job_id", "123_0"),
        ("threads", 16),
        ("solver_profile_sha256", "0" * 64),
        ("attempt_id", "invalid"),
        ("block_id", "../escape"),
    ],
)
def test_invalid_cohort(field, value):
    _, _, _, expected = inputs()
    cohort = dict(expected["cohort"], **{field: value})
    with pytest.raises(ValueError):
        evidence.binding(expected["source"], expected["runtime"], expected["anchor"], cohort)


def test_actual_source_bytes_and_tool_inventory(tmp_path):
    for name, content in {
        "pyproject.toml": "[project]\n",
        "src/logic/a.py": "x = 1\n",
        "scripts/mvp2_h300_a.py": "y = 2\n",
    }.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    first = evidence.source_receipt(tmp_path, "a" * 40)
    (tmp_path / "scripts/mvp2_h300_a.py").write_text("y = 3\n")
    second = evidence.source_receipt(tmp_path, "a" * 40)
    assert first != second
    assert (
        first["source_files_sha256"]["src/logic/a.py"]
        == second["source_files_sha256"]["src/logic/a.py"]
    )
    (tmp_path / "scripts/mvp2_h300_new.py").write_text("z = 4\n")
    assert len(evidence.source_receipt(tmp_path, "a" * 40)["source_files_sha256"]) == 4


def test_runtime_receipt_no_solver_import(monkeypatch):
    monkeypatch.setattr(
        evidence.importlib.metadata,
        "distributions",
        lambda: [
            SimpleNamespace(metadata={"Name": "pytest"}, version="9.1.1"),
            SimpleNamespace(metadata={"Name": "pytest"}, version="9.1.1"),
        ],
    )
    runtime = evidence.runtime_receipt()
    assert runtime["python_version"]
    assert runtime["distributions"]["pytest"]
    assert len(runtime["python_executable_sha256"]) == 64
    assert "license" not in str(runtime).lower()


def test_runtime_conflicting_distribution_versions_fail_closed(monkeypatch):
    monkeypatch.setattr(
        evidence.importlib.metadata,
        "distributions",
        lambda: [
            SimpleNamespace(metadata={"Name": "Test_Package"}, version="1.0"),
            SimpleNamespace(metadata={"Name": "test-package"}, version="2.0"),
        ],
    )
    with pytest.raises(ValueError, match="Ambiguous installed distribution"):
        evidence.runtime_receipt()


def test_current_provenance_requires_actual_bytes(tmp_path, monkeypatch):
    _, _, _, expected = inputs()
    monkeypatch.setattr(evidence, "runtime_receipt", lambda: expected["runtime"])
    monkeypatch.setattr(evidence, "source_receipt", lambda *_: expected["source"])
    root = Path(evidence.__file__).resolve().parents[1]
    assert evidence.verify_current_provenance(root, expected) == expected
    with pytest.raises(ValueError, match="executing tools"):
        evidence.verify_current_provenance(tmp_path, expected)
    altered = dict(expected["runtime"], python_version="3.13.16")
    monkeypatch.setattr(evidence, "runtime_receipt", lambda: altered)
    with pytest.raises(ValueError):
        evidence.verify_current_provenance(root, expected)


def test_loaded_module_cannot_come_from_another_checkout(tmp_path, monkeypatch):
    _, _, _, expected = inputs()
    monkeypatch.setattr(worker, "__file__", str(tmp_path / "mvp2_h300_native_worker.py"))
    with pytest.raises(ValueError, match="outside executing source"):
        evidence.verify_current_provenance(Path(evidence.__file__).resolve().parents[1], expected)


@pytest.mark.parametrize(
    "count,stages,native",
    [
        (1, 3, "OPTIMAL"),
        (1, 1, "TIME_LIMIT"),
        (0, 0, "TIME_LIMIT"),
        (0, 0, "MEM_LIMIT"),
        (1, 1, "INTERRUPTED"),
    ],
)
def test_worker_products_native_and_parent_bound(count, stages, native, tmp_path, monkeypatch):
    result, data, config, expected = inputs(count, stages, native)
    install_backend(monkeypatch, result, [])
    monkeypatch.setattr(evidence, "verify_current_provenance", lambda *_: expected)
    root = tmp_path / "worker"
    worker._integrate_native(
        root, data, config, expected["anchor"], worker_binding=expected, source_root=tmp_path
    )
    parent = synthetic_control(expected["anchor"])
    worker.partial.seal_control(root / "products", parent, expected["anchor"])
    publish(
        root,
        {
            "parent.json": evidence.parent_envelope(
                root, expected, parent, started_ms=0, ended_ms=4000
            )
        },
    )
    report = inspect(root, expected, data, config)
    assert report["integrity_accepted"]
    assert not report["worker_products_closed"]  # No live containment/sampling assertion.
    assert report["partial_review"]["validation"]["status"] == (
        "accepted" if count else "not_applicable_no_incumbent"
    )
    assert report["incumbent_observation"] == (
        "native_incumbent_vector_available" if count else "none"
    )
    archive, checksum, original = evidence.collect_worker(
        root, tmp_path / "transfer", "123|COMPLETED|0:0\n", "123", expected, data, config
    )
    assert evidence.review_worker(archive, checksum, "123", expected, data, config) == report
    assert original["presence"]["native-terminal.json"]["present"]
    assert not original["presence"]["failure.json"]["present"]
    assert not original["production_admitted"]
    assert report["worker_artifacts_associated"]


@pytest.mark.parametrize("fail", ["before_model", "construction", "optimization", "extraction"])
def test_failed_worker_portable_without_child_closure(fail, tmp_path, monkeypatch):
    result, data, config, expected = inputs()
    install_backend(monkeypatch, result, [], fail=fail)
    monkeypatch.setattr(evidence, "verify_current_provenance", lambda *_: expected)
    root = tmp_path / "worker"
    with pytest.raises(ValueError):
        worker._integrate_native(
            root, data, config, expected["anchor"], worker_binding=expected, source_root=tmp_path
        )
    archive, checksum, record = evidence.collect_worker(
        root, tmp_path / "transfer", "123|FAILED|1:0\n", "123", expected, data, config
    )
    report = evidence.review_worker(archive, checksum, "123", expected, data, config)
    assert report["integrity_accepted"] and report["failure_recorded"]
    assert not report["worker_products_closed"]
    assert report["incumbent_observation"] == (
        "native_incumbent_vector_unavailable" if fail == "extraction" else "unknown"
    )
    assert not record["presence"]["products/closure.json"]["present"]


@pytest.mark.parametrize("payload", [b"{", b'{"identity":1,"identity":2}', b'{"bad":NaN}'])
def test_unsafe_diagnostics_remain_local_without_archive(payload, tmp_path):
    _, data, config, expected = inputs()
    root = tmp_path / "worker"
    publish(root, {"binding.json": expected})
    (root / "failure.json").write_bytes(payload)
    with pytest.raises(ValueError):
        evidence.collect_worker(
            root, tmp_path / "transfer", "123|FAILED|1:0\n", "123", expected, data, config
        )
    assert not (tmp_path / "transfer").exists()
    assert (root / "failure.json").read_bytes() == payload


def test_missing_native_is_unknown_not_zero(tmp_path):
    _, data, config, expected = inputs(0, 0)
    publish(tmp_path, {"binding.json": expected})
    assert inspect(tmp_path, expected, data, config)["incumbent_observation"] == "unknown"


def test_unknown_native_code_preserved_not_promoted(tmp_path):
    _, data, config, expected = inputs()
    identity = evidence.design.digest(expected["anchor"])
    publish(
        tmp_path,
        {
            "binding.json": expected,
            **{
                f"phase-{i}.json": {"identity": identity, "index": i, "phase": p}
                for i, p in enumerate(evidence.controls.PHASES[:3])
            },
            "native-terminal.json": {
                "identity": identity,
                "native_status_code": 123,
                "native_status_name": "UNKNOWN",
                "solution_count": 0,
                "native_runtime_seconds": None,
                "native_peak_decimal_gb": None,
                **evidence.FLAGS,
            },
        },
    )
    report = inspect(tmp_path, expected, data, config)
    assert report["integrity_accepted"] and not report["worker_products_closed"]
    assert report["native_terminal"]["native_status_code"] == 123


def test_phase_hole_and_unknown_fields_rejected(tmp_path):
    _, data, config, expected = inputs()
    publish(tmp_path, {"binding.json": expected, "phase-1.json": {}})
    with pytest.raises(ValueError):
        inspect(tmp_path, expected, data, config)


def test_archive_checksum_external_job_and_original_preserved(tmp_path):
    _, data, config, expected = inputs()
    root = tmp_path / "worker"
    publish(root, {"binding.json": expected})
    before = (root / "binding.json").read_bytes()
    archive, checksum, _ = evidence.collect_worker(
        root, tmp_path / "transfer", "123|FAILED|1:0\n", "123", expected, data, config
    )
    with pytest.raises(ValueError):
        evidence.review_worker(archive, "0" * 64, "123", expected, data, config)
    with pytest.raises(ValueError):
        evidence.review_worker(archive, checksum, "124", expected, data, config)
    with pytest.raises(FileExistsError):
        evidence.collect_worker(
            root, tmp_path / "transfer", "123|FAILED|1:0\n", "123", expected, data, config
        )
    assert (root / "binding.json").read_bytes() == before


@pytest.mark.parametrize("name", ["../escape", "/absolute", "license.lic", "products/raw.log"])
def test_unsafe_archive_member(tmp_path, name):
    _, data, config, expected = inputs()
    archive = tmp_path / "unsafe.tar.gz"
    with tarfile.open(archive, "w:gz") as stream:
        member = tarfile.TarInfo(name)
        member.size = 1
        stream.addfile(member, io.BytesIO(b"x"))
    with pytest.raises(ValueError):
        evidence.review_worker(
            archive, evidence.partial.file_digest(archive), "123", expected, data, config
        )


def test_unallowlisted_source_path():
    _, _, _, expected = inputs()
    source = copy.deepcopy(expected["source"])
    source["source_files_sha256"]["../license.lic"] = "9" * 64
    with pytest.raises(ValueError):
        evidence.binding(source, expected["runtime"], expected["anchor"], expected["cohort"])


def test_oversized_extended_header_bounded_before_tar_parsing(tmp_path, monkeypatch):
    _, data, config, expected = inputs()
    archive = tmp_path / "metadata-bomb.tar.gz"
    with tarfile.open(archive, "w:gz", format=tarfile.PAX_FORMAT) as stream:
        member = tarfile.TarInfo("binding.json")
        member.pax_headers = {"comment": "x" * 16384}
        stream.addfile(member, io.BytesIO())
    monkeypatch.setattr(evidence, "LIMIT", 4096)
    monkeypatch.setattr(
        evidence.tarfile, "open", lambda *_a, **_kw: pytest.fail("Unbounded tar parser")
    )
    with pytest.raises(ValueError, match="Uncompressed tar"):
        evidence.review_worker(
            archive, evidence.partial.file_digest(archive), "123", expected, data, config
        )


@pytest.mark.parametrize("kind", ["source", "attempt", "cohort"])
def test_worker_origin_prevents_cross_source_or_attempt_substitution(kind, tmp_path):
    _, data, config, expected = inputs()
    root = tmp_path / "worker"
    publish(root, {"binding.json": expected})
    replacement = copy.deepcopy(expected)
    if kind == "source":
        replacement["source"]["source_files_sha256"]["pyproject.toml"] = "9" * 64
    else:
        key = "attempt_id" if kind == "attempt" else "cohort_manifest_sha256"
        replacement["cohort"][key] = "9" * 64
    (root / "binding.json").write_bytes(evidence.controls.encoded(replacement))
    with pytest.raises(ValueError, match="origin"):
        evidence.collect_worker(
            root, tmp_path / "transfer", "123|FAILED|1:0\n", "123", replacement, data, config
        )
    assert not (tmp_path / "transfer").exists()


def test_external_identity_error_never_becomes_generic_rejected_archive(tmp_path):
    _, data, config, expected = inputs()
    root = tmp_path / "worker"
    publish(root, {"binding.json": expected})
    replacement = copy.deepcopy(expected)
    replacement["cohort"]["attempt_id"] = "9" * 64
    with pytest.raises(ValueError, match="binding"):
        evidence.collect_worker(
            root, tmp_path / "transfer", "123|FAILED|1:0\n", "123", replacement, data, config
        )


def test_adverse_evidence_checks_supplied_scientific_config(tmp_path):
    _, data, config, expected = inputs()
    root = tmp_path / "worker"
    publish(root, {"binding.json": expected})
    altered = copy.deepcopy(config)
    altered.use_direct_origin_customer = True
    with pytest.raises(ValueError, match="configuration"):
        evidence.collect_worker(
            root, tmp_path / "transfer", "123|FAILED|1:0\n", "123", expected, data, altered
        )


def test_unallowlisted_credential_field_never_transferred(tmp_path):
    _, data, config, expected = inputs()
    root = tmp_path / "worker"
    publish(root, {"binding.json": expected, "failure.json": {"credential": "TEST_ONLY"}})
    with pytest.raises(ValueError, match="Unallowlisted"):
        evidence.collect_worker(
            root, tmp_path / "transfer", "123|FAILED|1:0\n", "123", expected, data, config
        )
    assert not (tmp_path / "transfer").exists()


def test_credential_nested_in_known_failure_field_never_transferred(tmp_path):
    _, data, config, expected = inputs()
    root = tmp_path / "worker"
    publish(
        root,
        {
            "binding.json": expected,
            "failure.json": {
                "identity": evidence.design.digest(expected["anchor"]),
                "exception_type": {"credential": "TEST_ONLY"},
                "after_phase_count": 0,
                "native_terminal_captured": False,
                **evidence.FLAGS,
            },
        },
    )
    with pytest.raises(ValueError, match="Unsafe failure values"):
        evidence.collect_worker(
            root, tmp_path / "transfer", "123|FAILED|1:0\n", "123", expected, data, config
        )
    assert not (tmp_path / "transfer").exists()


@pytest.mark.parametrize("replace_catalog", [False, True])
def test_catalog_prevents_substitution_with_genuine_origin(tmp_path, replace_catalog):
    _, data, config, expected = inputs()
    root = tmp_path / "worker"
    publish(root, {"binding.json": expected})
    evidence.seal_worker_catalog(root, expected)
    if replace_catalog:
        replacement = copy.deepcopy(expected)
        replacement["cohort"]["attempt_id"] = "9" * 64
        other = tmp_path / "other"
        publish(other, {"binding.json": replacement})
        evidence.seal_worker_catalog(other, replacement)
        (root / "worker-catalog.json").write_bytes((other / "worker-catalog.json").read_bytes())
    else:
        publish(
            root,
            {
                "phase-0.json": {
                    "identity": evidence.design.digest(expected["anchor"]),
                    "index": 0,
                    "phase": evidence.controls.PHASES[0],
                }
            },
        )
    with pytest.raises(ValueError, match="catalogue"):
        evidence.collect_worker(
            root, tmp_path / "transfer", "123|FAILED|1:0\n", "123", expected, data, config
        )
    assert not (tmp_path / "transfer").exists()


@pytest.mark.parametrize("name", ["OPTIMAL", "TIME_LIMIT"])
def test_unknown_native_code_cannot_impersonate_known_status(name, tmp_path):
    _, data, config, expected = inputs()
    identity = evidence.design.digest(expected["anchor"])
    publish(
        tmp_path,
        {
            "binding.json": expected,
            **{
                f"phase-{i}.json": {"identity": identity, "index": i, "phase": p}
                for i, p in enumerate(evidence.controls.PHASES[:3])
            },
            "native-terminal.json": {
                "identity": identity,
                "native_status_code": 123,
                "native_status_name": name,
                "solution_count": 1,
                "native_runtime_seconds": None,
                "native_peak_decimal_gb": None,
                **evidence.FLAGS,
            },
        },
    )
    with pytest.raises(ValueError, match="substituted code"):
        inspect(tmp_path, expected, data, config)


def test_bound_native_worker_checks_current_source_before_creating_directory(monkeypatch, tmp_path):
    _, data, config, expected = inputs()

    def reject(*_args):
        raise ValueError("Current source drift")

    monkeypatch.setattr(evidence, "verify_current_provenance", reject)
    with pytest.raises(ValueError, match="source drift"):
        worker._integrate_native(
            tmp_path / "worker",
            data,
            config,
            expected["anchor"],
            worker_binding=expected,
            source_root=tmp_path,
        )
    assert not (tmp_path / "worker").exists()


def test_sampling_roundtrip_bound_to_full_attempt_and_synthetic_not_live(tmp_path):
    from scripts import mvp2_h300_resources as resources
    from tests.test_mvp2_h300_resources import group, proc, receipt

    _, data, config, expected = inputs()
    child = tmp_path / "allocation" / "owned"
    group(child)
    proc(tmp_path / "proc")
    observer = resources.CgroupV2Observer(
        child.parent, child, owned={123: 77}, proc_root=tmp_path / "proc", test_only=True
    )
    sampling = receipt(observer)
    sampling["identity"] = evidence.design.digest(expected)
    root = tmp_path / "worker"
    publish(root, {"binding.json": expected, "sampling.json": sampling})
    evidence.seal_worker_catalog(root, expected)
    archive, checksum, _ = evidence.collect_worker(
        root, tmp_path / "transfer", "123|FAILED|1:0\n", "123", expected, data, config
    )
    report = evidence.review_worker(archive, checksum, "123", expected, data, config)
    assert report["sampling"]["synthetic_observation"]
    assert report["sampling"]["allocation_tree_closed"] is False
    assert not report["worker_products_closed"] and not report["production_admitted"]
    parent = synthetic_control(expected["anchor"])
    wrapper = evidence.parent_envelope(root, expected, parent, started_ms=10000, ended_ms=14000)
    publish(root, {"parent.json": wrapper})
    with pytest.raises(ValueError, match="cover parent"):
        inspect(root, expected, data, config)
    wrapper["started_ms"], wrapper["ended_ms"] = 10000, 12000
    with pytest.raises(ValueError, match="duration"):
        evidence._transfer_shapes(
            {"parent.json": evidence.controls.encoded(wrapper)}, expected, data, config
        )
    sampling["ended_ms"] = sampling["final"]["at_ms"] = 14000
    (root / "sampling.json").write_bytes(evidence.controls.encoded(sampling))
    wrapper = evidence.parent_envelope(root, expected, parent, started_ms=10000, ended_ms=14000)
    (root / "parent.json").write_bytes(evidence.controls.encoded(wrapper))
    assert inspect(root, expected, data, config)["sampling"]["sampling_valid"]
    wrapper["sampling_sha256"] = "0" * 64
    (root / "parent.json").write_bytes(evidence.controls.encoded(wrapper))
    with pytest.raises(ValueError, match="sampling digest"):
        inspect(root, expected, data, config)
    sampling["identity"] = evidence.design.digest(expected["anchor"])
    (root / "sampling.json").write_bytes(evidence.controls.encoded(sampling))
    with pytest.raises(ValueError, match="identity"):
        evidence.collect_worker(
            root, tmp_path / "bad-transfer", "123|FAILED|1:0\n", "123", expected, data, config
        )


def test_accounting_with_unreviewed_extra_data_never_transferred(tmp_path):
    _, data, config, expected = inputs()
    root = tmp_path / "worker"
    publish(root, {"binding.json": expected})
    with pytest.raises(ValueError, match="canonical root"):
        evidence.collect_worker(
            root,
            tmp_path / "transfer",
            "123|FAILED|1:0\nTEST_ONLY_PRIVATE_EXTRA\n",
            "123",
            expected,
            data,
            config,
        )
    assert not (tmp_path / "transfer").exists()


@pytest.mark.skipif(__import__("os").name != "posix", reason="POSIX symlink fixture")
def test_linked_evidence_parent_rejected(tmp_path):
    _, data, config, expected = inputs()
    root = tmp_path / "worker"
    publish(root, {"binding.json": expected})
    (root / "products").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError):
        evidence.collect_worker(
            root, tmp_path / "transfer", "123|FAILED|1:0\n", "123", expected, data, config
        )


def test_source_receipt_real_scope():
    root = Path(__file__).resolve().parents[1]
    receipt = evidence.source_receipt(root, "a" * 40)
    assert "scripts/mvp2_h300_worker_evidence.py" in receipt["source_files_sha256"]
    assert "src/logic/solution_validation.py" in receipt["source_files_sha256"]
