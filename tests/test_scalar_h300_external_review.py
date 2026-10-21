"""Synthetic diagnostic arithmetic/transport tests, not private h300 mathematics."""

import copy
import hashlib
import io
import json
import tarfile

import pytest

from scripts import review_scalar_h300_evidence as m


def fixture():
    files = {}

    def put(name, data):
        files[name] = json.dumps(data).encode()

    put("plan.json", {"source_commit": "a" * 40})
    put(
        "hardware.json",
        dict(
            cpu_model={},
            physical_cores_observed=12,
            affinity_logical_cpus=list(range(16)),
            topology=[],
        ),
    )
    files["accounting.txt"] = b"123|COMPLETED|0:0|60|\n123.batch|COMPLETED|0:0|60|\n"
    arms = []
    for threads in (4, 1, 8, 2, 16):
        name = f"scalar_h300_t{threads}"
        case = f"cases/{name}/"
        products = f"{case}products/{name}/"
        physical = dict(
            penalty_cost_share=0.9,
            domestic_service_level=0.9,
            total_unmet_demand=1.0,
            emergency_static_capacity=1.0,
            emergency_reception_capacity=1.0,
            peak_rss_mb=1024.0,
        )
        arms.append(
            dict(
                case_name=name,
                threads=threads,
                objective=200000.0,
                bound=199000.0,
                economic_cost=20000.0,
                common_gap=0.005,
                physical_diagnostics=physical,
            )
        )
        put(
            products + "run_summary.json",
            dict(served_domestic_demand=9.0, total_domestic_demand=10.0),
        )
        put(
            products + "independent_validation.json",
            dict(
                status="accepted",
                failed_check_count=0,
                absolute_tolerance=1e-5,
                relative_tolerance=1e-8,
                mathematical_contract={"selected_network_sha256": "b" * 64},
                reconstructed_costs=dict(
                    unmet_demand=90000.0,
                    emergency_static=45000.0,
                    emergency_reception=45000.0,
                    transport=20000.0,
                ),
            ),
        )
        put(
            case + "input_receipt.json",
            {"effective_scenario_probabilities": {str(i): 1 / 9 for i in range(9)}},
        )
        put(
            case + "warehouses_used.json",
            dict(
                count=300,
                existing_count=146,
                candidate_count=154,
                csv_sha256="c" * 64,
                ordered_ids_sha256="d" * 64,
                criterion="public fixture",
                selection_seed="public seed",
            ),
        )
        put(f"control/t{threads}/runtime.json", {"solver_threads": threads})
        put(products + "resources/matrix_statistics.json", {"observations": []})
        put(products + "resources/termination.json", {"inspection_errors": []})
        files[products + "resources/solver_progress.csv"] = (
            b"iterations,nodes,solver_memory_bytes\n1,0,100\n2,0,200\n"
        )
        for filename in m.DECISIONS:
            files[products + filename] = b"public,fixture\n1,2\n"
    replay = dict(
        status="block_quality_target_met",
        quality_target_met=True,
        operational_receipts_closed=True,
        missing_or_rejected=[],
        arms=arms,
        job_id="123",
        penalty_rates=dict(unmet=90000, static=45000, reception=45000),
    )
    return files, replay


def change(files, name, **updates):
    value = json.loads(files[name])
    value.update(updates)
    files[name] = json.dumps(value).encode()


def test_complete_summary_is_redacted_and_does_not_admit_anything():
    files, replay = fixture()
    report = m.summarize(files, replay)
    assert report["status"] == "accepted_scalar_h300_block"
    assert [a["threads"] for a in report["arms"]] == [4, 1, 8, 2, 16]
    assert all(report["decision_artifacts_identical_across_arms"].values())
    assert report["arms"][0]["gap_percent"] == 0.5
    assert report["arms"][0]["application_sampled_peak_rss_gib"] == 1
    assert report["arms"][0]["sampled_solver_progress"]["sampled_max_iterations"] == 2
    for flag in (
        "execution_admitted",
        "h300_admitted",
        "repeats_admitted",
        "automatic_follow_on_allowed",
    ):
        assert report[flag] is False
    assert "host" not in report["hardware"]


@pytest.mark.parametrize(
    "key,value",
    [
        ("status", "partial"),
        ("quality_target_met", False),
        ("operational_receipts_closed", False),
        ("missing_or_rejected", ["missing"]),
    ],
)
def test_summary_cannot_upgrade_an_unaccepted_original_replay(key, value):
    files, replay = fixture()
    replay[key] = value
    with pytest.raises(ValueError, match="Full accepted"):
        m.summarize(files, replay)


@pytest.mark.parametrize(
    "key,value",
    [
        ("objective", 400000.0),
        ("bound", 100.0),
        ("economic_cost", 3.0),
        ("common_gap", 0.1),
        ("threads", 3),
    ],
)
def test_corrupt_arm_arithmetic_or_binding_rejected(key, value):
    files, replay = fixture()
    replay["arms"][0][key] = value
    with pytest.raises((ValueError, KeyError)):
        m.summarize(files, replay)


@pytest.mark.parametrize(
    "key,value",
    [
        ("total_unmet_demand", 2.0),
        ("emergency_static_capacity", 2.0),
        ("emergency_reception_capacity", 2.0),
        ("penalty_cost_share", 0.1),
        ("domestic_service_level", 1.0),
    ],
)
def test_physical_quantities_and_penalty_share_are_checked(key, value):
    files, replay = fixture()
    replay["arms"][0]["physical_diagnostics"][key] = value
    with pytest.raises(ValueError):
        m.summarize(files, replay)


@pytest.mark.parametrize(
    "key,value",
    [
        ("status", "rejected"),
        ("failed_check_count", 1),
        ("absolute_tolerance", 0.1),
        ("relative_tolerance", 0.1),
    ],
)
def test_original_validation_cannot_be_weakened(key, value):
    files, replay = fixture()
    name = "cases/scalar_h300_t4/products/scalar_h300_t4/independent_validation.json"
    change(files, name, **{key: value})
    with pytest.raises(ValueError):
        m.summarize(files, replay)


def test_different_decision_vectors_are_reported_not_rejected():
    files, replay = fixture()
    files["cases/scalar_h300_t4/products/scalar_h300_t4/flows.csv"] = b"different,valid\n"
    report = m.summarize(files, replay)
    assert report["decision_artifacts_identical_across_arms"]["flows.csv"] is False
    assert report["status"] == "accepted_scalar_h300_block"


def test_population_drift_rejected():
    files, replay = fixture()
    change(files, "cases/scalar_h300_t4/warehouses_used.json", csv_sha256="e" * 64)
    with pytest.raises(ValueError, match="Population/network drift"):
        m.summarize(files, replay)


def test_different_probabilities_rejected():
    files, replay = fixture()
    change(
        files,
        "cases/scalar_h300_t4/input_receipt.json",
        effective_scenario_probabilities={"base": 1.0},
    )
    with pytest.raises(ValueError, match="Scenario"):
        m.summarize(files, replay)


def archive(tmp_path, entries):
    path = tmp_path / "public.tar.gz"
    with tarfile.open(path, "w:gz") as stream:
        for name, raw, kind in entries:
            member = tarfile.TarInfo(name)
            member.type = kind
            member.size = len(raw)
            stream.addfile(member, io.BytesIO(raw))
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def test_stream_inventory_is_bounded_and_not_extracted(tmp_path):
    raw = b"public bytes"
    items = {"public.txt": hashlib.sha256(raw).hexdigest()}
    path, checksum = archive(
        tmp_path,
        [
            ("public.txt", raw, tarfile.REGTYPE),
            ("inventory.json", json.dumps(items).encode(), tarfile.REGTYPE),
        ],
    )
    files, meta = m.read_archive(path, checksum)
    assert files == {"public.txt": raw} and meta["members"] == 2
    assert not (tmp_path / "public.txt").exists()
    with pytest.raises(ValueError, match="checksum"):
        m.read_archive(path, "0" * 64)


@pytest.mark.parametrize(
    "name,kind",
    [("../escape", tarfile.REGTYPE), ("/absolute", tarfile.REGTYPE), ("link", tarfile.SYMTYPE)],
)
def test_unsafe_members_rejected(tmp_path, name, kind):
    path, checksum = archive(tmp_path, [(name, b"", kind)])
    with pytest.raises(ValueError, match="Unsafe"):
        m.read_archive(path, checksum)


def test_duplicate_inventory_drift_and_cap_rejected(tmp_path, monkeypatch):
    path, checksum = archive(tmp_path, [("a", b"1", tarfile.REGTYPE)] * 2)
    with pytest.raises(ValueError, match="duplicate"):
        m.read_archive(path, checksum)
    path, checksum = archive(
        tmp_path, [("a", b"1", tarfile.REGTYPE), ("inventory.json", b"{}", tarfile.REGTYPE)]
    )
    with pytest.raises(ValueError, match="Inventory"):
        m.read_archive(path, checksum)
    monkeypatch.setattr(m.original, "MAX_BYTES", 0)
    with pytest.raises(ValueError, match="cap"):
        m.read_archive(path, checksum)


def test_review_always_invokes_original_verifier(monkeypatch, tmp_path):
    files, replay = fixture()
    seen = []
    monkeypatch.setattr(m, "read_archive", lambda *_: (files, {"members": len(files)}))

    def verify(given):
        seen.append(given)
        return copy.deepcopy(replay)

    monkeypatch.setattr(m.original, "portable_review", verify)
    path = tmp_path / "private.tar.gz"
    path.write_bytes(b"synthetic")
    report = m.review(path, "a" * 64)
    assert seen == [files] and report["archive_bytes"] == 9


def test_output_is_exclusive_and_never_overwrites_evidence(tmp_path, monkeypatch):
    target = tmp_path / "review.json"
    target.write_text("preserve")
    monkeypatch.setattr(m, "review", lambda *_: {})
    with pytest.raises(FileExistsError):
        m.main(["--archive", "unused", "--sha256", "a" * 64, "--output", str(target)])
    assert target.read_text() == "preserve"
