"""Personal soft quota, measured growth and preserved-output stop conditions."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "serial_storage_unit", ROOT / "scripts/pyomo_serial_storage.py"
)
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)


def command(argv, **kwargs):
    if argv[0] == "df":
        return SimpleNamespace(
            returncode=0,
            stdout=(
                "Filesystem 1024-blocks Used Available Capacity Mounted on\n"
                "userhomeplus:/home 100000 20000 80000 20% /home\n"
            ),
        )
    return SimpleNamespace(
        returncode=0,
        stdout=(
            "Disk quotas for user fixture:\n"
            "Filesystem space quota limit grace files quota limit grace\n"
            "userhomeplus:/home\n36090M 100G 1000G 251k 0 0\n"
        ),
    )


def test_actual_wrapped_quota_is_bounded_without_assuming_hard_limit_is_usable(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(S.shutil, "disk_usage", lambda p: SimpleNamespace(free=100 * S.GIB))
    row = S.observe(tmp_path, command=command)
    assert row["used_upper_bytes"] == 36091 * 1024**2
    assert row["limit_lower_bytes"] == 99 * S.GIB
    assert row["available_lower_bytes"] < 65 * S.GIB
    S.check_initial(tmp_path, 32, command=command)
    with pytest.raises(ValueError, match="exceeds"):
        S.check_initial(tmp_path, 768, command=command)


@pytest.mark.parametrize("raw", ["unlimited", "100GB", "-1M", "NaN", "100Gextra"])
def test_unrecognized_or_unbounded_quota_does_not_admit_output(raw):
    with pytest.raises(ValueError):
        S.human_bytes(raw, upper=True)


@pytest.mark.parametrize(
    "case", ["query_failed", "wrong_filesystem", "duplicate", "unlimited", "over_soft", "low_free"]
)
def test_storage_preparation_requires_live_quota_and_shared_free_space(tmp_path, monkeypatch, case):
    monkeypatch.setattr(
        S.shutil,
        "disk_usage",
        lambda p: SimpleNamespace(free=(1 if case == "low_free" else 100) * S.GIB),
    )

    def faulty(argv, **kwargs):
        row = command(argv, **kwargs)
        if argv[0] == "quota":
            if case == "query_failed":
                row.returncode = 1
            elif case == "wrong_filesystem":
                row.stdout = row.stdout.replace("userhomeplus:/home", "other:/home")
            elif case == "duplicate":
                row.stdout += "\nuserhomeplus:/home 1M 100G 1000G"
            elif case == "unlimited":
                row.stdout = row.stdout.replace("100G 1000G", "0 0")
            elif case == "over_soft":
                row.stdout = row.stdout.replace("36090M", "120G*")
        return row

    with pytest.raises(ValueError):
        S.check_initial(tmp_path, 32, command=faulty)


@pytest.mark.parametrize("fault", [None, "growth", "quota", "shrunk"])
def test_growth_and_reserve_stop_admission_without_deleting_originals(tmp_path, monkeypatch, fault):
    p = tmp_path / "original.txt"
    p.write_bytes(b"preserved")
    monkeypatch.setattr(
        S,
        "directory_usage",
        lambda _: (1 if fault == "shrunk" else 20 if fault == "growth" else 2) * S.GIB,
    )
    monkeypatch.setattr(
        S,
        "observe",
        lambda *a, **k: {
            "available_lower_bytes": (1 if fault == "quota" else 50) * S.GIB,
            "filesystem_free_bytes": 100 * S.GIB,
        },
    )
    manifest = {
        "storage_budget_gib_confirmed_in_human_CLI": 32,
        "campaign_allocated_bytes_at_prepare": 2 * S.GIB,
    }
    if fault is None:
        S.check_growth(tmp_path, tmp_path, manifest, command=command)
    else:
        with pytest.raises(ValueError):
            S.check_growth(tmp_path, tmp_path, manifest, command=command)
    assert p.read_bytes() == b"preserved"


def test_usage_counts_regular_files_without_content_reading(tmp_path):
    (tmp_path / "sample.bin").write_bytes(b"x" * 5000)
    assert S.directory_usage(tmp_path) >= 5000
