"""Offline diagnostics/privacy and unchanged historical evidence; no live effects."""

import copy
import gzip
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import mvp2_h300_controls as c
from scripts import mvp2_s2_batch_adapter as a
from scripts import mvp2_s2_first_normal as n
from scripts import mvp2_s2_operational as o
from tests import test_mvp2_s2_first_normal as fixtures


@pytest.fixture
def envelope():
    return fixtures.envelope.__wrapped__()


@pytest.fixture
def spec(envelope):
    return fixtures.spec.__wrapped__(envelope)


@pytest.fixture
def negative_records(envelope, spec):
    return fixtures.negative_records.__wrapped__(envelope, spec)


@pytest.mark.parametrize(
    "phase",
    [
        "load_plan",
        "verify_release",
        "verify_runtime",
        "verify_source",
        "create_adapter",
        "preflight",
        "supervise",
        "verify_operation",
        None,
    ],
)
def test_real_batch_records_phase_without_error_text(tmp_path, monkeypatch, envelope, spec, phase):
    spec = {**spec, "run": str(tmp_path / "worker")}
    observed = []

    class PrivateError(ValueError):
        def __str__(self):
            pytest.fail("Do not stringify exception payloads")

    def fail_here(stage):
        observed.append(stage)
        if phase == stage:
            raise PrivateError("/private/license/token=SECRET")

    monkeypatch.setattr(n, "require_host", lambda: None)
    monkeypatch.setattr(n, "load_claim", lambda _: (tmp_path, envelope, {"run": spec["run"]}))

    def plan(_):
        fail_here("load_plan")
        return tmp_path, envelope, spec

    def runtime(_):
        fail_here("verify_runtime")

    def source(*_):
        fail_here("verify_source")
        return envelope["source"]

    class Adapter:
        def __init__(self, *_args, **_kwargs):
            fail_here("create_adapter")
            self.claimed = False

        def preflight(self, **_kwargs):
            fail_here("preflight")

    def supervise(subject, _latch):
        if phase in {"supervise", "verify_operation"}:
            Path(spec["run"]).mkdir()
        fail_here("supervise")
        subject.claimed = True
        return {"operation": {"remote_cleanup_proven": phase == "verify_operation"}}

    monkeypatch.setattr(n, "load_plan", plan)
    monkeypatch.setattr(n, "recheck", runtime)
    monkeypatch.setattr(
        n, "NormalTransport", lambda *_args, **_kwargs: SimpleNamespace(source_command=None)
    )
    monkeypatch.setattr(a, "verify_checkout", source)
    monkeypatch.setattr(n, "NormalAdapter", Adapter)
    monkeypatch.setattr(o, "supervise_normal_components", supervise)
    monkeypatch.setattr(os, "getuid", lambda: 1000, raising=False)
    monkeypatch.setattr(os, "uname", lambda: SimpleNamespace(nodename="node"), raising=False)
    monkeypatch.setenv("SLURM_JOB_ID", "wrong" if phase == "verify_release" else spec["job_id"])
    (tmp_path / "job.json").write_text("{}")
    report = n.batch("a" * 40)
    assert report["schema_version"] == "s2-first-normal-batch-v2"
    diagnostic = report["diagnostic"]
    assert diagnostic["phase"] == (phase or "complete")
    assert diagnostic["error_kind"] == ("value_error" if phase else "none")
    assert (
        diagnostic["site"] is None
        if phase is None
        else diagnostic["site"]["module"] == n.__name__.split(".")[-1]
    )
    expected = (
        "attempt_preserved"
        if phase is None
        else (
            "incomplete_attempt_preserved"
            if phase in {"supervise", "verify_operation"}
            else "blocked_before_launch"
        )
    )
    assert report["status"] == expected
    raw = (tmp_path / "batch-outcome.json").read_bytes()
    assert b"SECRET" not in raw and b"/private" not in raw
    assert all(report[key] is False for key in n.FUTURE)
    if phase not in {None, "supervise", "verify_operation"}:
        assert "supervise" not in observed
    with pytest.raises(FileExistsError):
        n.batch("a" * 40)


@pytest.mark.parametrize(
    "cls,kind",
    [
        (TimeoutError, "timeout"),
        (KeyboardInterrupt, "interrupted"),
        (UnicodeError, "unicode_error"),
        (OSError, "os_error"),
        (ValueError, "value_error"),
    ],
)
def test_fixed_exception_categories(cls, kind):
    diagnostic = n.batch_diagnostic("preflight", cls("private payload"))
    assert diagnostic == {"phase": "preflight", "error_kind": kind, "site": None}


def test_missing_acknowledgement_times_out_without_launch(tmp_path, monkeypatch, envelope):
    monkeypatch.setattr(n, "require_host", lambda: None)
    monkeypatch.setattr(
        n, "load_claim", lambda _: (tmp_path, envelope, {"run": str(tmp_path / "absent")})
    )
    ticks = iter([0, 0, 31])
    monkeypatch.setattr(n.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(n, "load_plan", lambda _: pytest.fail("unreleased plan"))
    report = n.batch("a" * 40)
    assert report["status"] == "blocked_before_launch"
    assert report["diagnostic"]["phase"] == "await_job_receipt"
    assert report["diagnostic"]["error_kind"] == "value_error"


def test_unreviewed_exception_is_not_relabelled():
    with pytest.raises(ValueError, match="Unreviewed diagnostic"):
        n.batch_diagnostic("preflight", RuntimeError("private payload"))


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_read_only_audit_cli_displays_only_available_diagnostics(monkeypatch, capsys, version):
    review = {"status": "integrity_replayed_not_live_qualified"}
    if version == "v2":
        review["batch_diagnostic"] = n.batch_diagnostic("preflight", ValueError("SECRET"))
    monkeypatch.setattr(
        n.sys,
        "argv",
        [
            "entry",
            "audit",
            "--source-sha",
            "a" * 40,
            "--job",
            "500000",
            "--archive",
            "unused",
            "--sha256",
            "b" * 64,
        ],
    )
    monkeypatch.setattr(n, "audit", lambda *_: review)
    assert n.main() == 0
    text = capsys.readouterr().out
    assert ("BATCH_PHASE=preflight" in text) is (version == "v2")
    assert "SECRET" not in text
    assert "NO_ADVERSE_NATIVE_MINIATURE_H300_OR_REPEAT_ADMITTED" in text


def test_guard_location_not_generic_require():
    try:
        n.parse_acknowledgement("malformed")
    except ValueError as error:
        diagnostic = n.batch_diagnostic("preflight", error)
    assert diagnostic["site"]["module"] == "mvp2_s2_first_normal"
    assert diagnostic["site"]["line"] == n.parse_acknowledgement.__code__.co_firstlineno + 2


@pytest.mark.parametrize(
    "field,value",
    [
        ("phase", "native"),
        ("phase", []),
        ("error_kind", "secret message"),
        ("error_kind", {}),
        ("site", {"module": "/private/path", "line": 1}),
        ("site", {"module": "mvp2_s2_first_normal", "line": True}),
        ("site", {"module": "mvp2_s2_first_normal", "line": 20001}),
        ("site", {"module": "mvp2_s2_first_normal", "line": 1, "message": "SECRET"}),
    ],
)
def test_diagnostic_rejects_unbounded_or_private_fields(field, value):
    item = n.batch_diagnostic("preflight", ValueError())
    item[field] = value
    with pytest.raises(ValueError):
        n.review_batch_diagnostic(item)


def test_v2_roundtrip_and_legacy_unchanged(tmp_path, negative_records):
    old = n.review_records(negative_records, "a" * 40, "500000")
    assert old["schema_version"] == "s2-first-normal-review-v1"
    assert "batch_diagnostic" not in old
    wrapper = c.decode_json(negative_records["wrapper.json"])
    wrapper.update(
        schema_version="s2-first-normal-batch-v2",
        diagnostic=n.batch_diagnostic("preflight", ValueError("SECRET")),
    )
    negative_records["wrapper.json"] = c.encoded(wrapper)
    result = n.pack(tmp_path, negative_records, "a" * 40, "500000")
    assert n.audit(result["download"], result["sha256"], "a" * 40, "500000") == result["review"]
    assert result["review"]["batch_diagnostic"] == wrapper["diagnostic"]
    assert result["review"]["schema_version"] == "s2-first-normal-review-v2"
    assert all(result["review"][key] is False for key in n.FUTURE)
    assert b"SECRET" not in gzip.decompress(Path(result["download"]).read_bytes())


@pytest.mark.parametrize(
    "kind",
    [
        "legacy_extra",
        "v2_missing",
        "missing_receipt",
        "scope",
        "version",
        "complete_error",
        "false_success",
    ],
)
def test_receipt_schema_cannot_hide_or_promote(negative_records, kind):
    wrapper = c.decode_json(negative_records["wrapper.json"])
    wrapper.update(
        schema_version="s2-first-normal-batch-v2",
        diagnostic=n.batch_diagnostic("preflight", ValueError()),
    )
    if kind == "legacy_extra":
        wrapper["schema_version"] = "s2-first-normal-batch-v1"
    elif kind == "v2_missing":
        wrapper.pop("diagnostic")
    elif kind == "missing_receipt":
        wrapper["status"] = "missing_terminal_batch_receipt"
    elif kind == "scope":
        wrapper["production_admitted"] = True
    elif kind == "version":
        wrapper["schema_version"] = []
    elif kind == "complete_error":
        wrapper["diagnostic"]["phase"] = "complete"
    elif kind == "false_success":
        wrapper["status"] = "attempt_preserved"
    negative_records["wrapper.json"] = c.encoded(wrapper)
    with pytest.raises(ValueError):
        n.review_records(negative_records, "a" * 40, "500000")


def test_historical_public_records_stay_v1():
    path = (
        Path(__file__).resolve().parents[1] / "docs/evidence/s2-first-normal-2207167/records.json"
    )
    records = json.loads(path.read_bytes())
    original = copy.deepcopy(records)
    replay = n.review_records(
        {k: c.encoded(v) for k, v in records.items()},
        "12691638cd85d5218725bf704dc6b9452b1ca90c",
        "2207167",
    )
    assert replay == records["review.json"]
    assert replay["batch_status"] == "blocked_before_launch"
    assert replay["worker_outcome"] == "unknown"
    assert records == original and "batch_diagnostic" not in replay
