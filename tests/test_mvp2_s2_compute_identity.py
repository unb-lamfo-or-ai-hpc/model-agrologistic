"""Offline identity qualification; no scheduler, live worker or solver effects."""

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import mvp2_s2_batch_adapter as a
from scripts import mvp2_s2_compute_identity as identity
from scripts import mvp2_s2_first_normal as n
from scripts import mvp2_s2_normal_recovery as recovery
from scripts import mvp2_s2_slurm_step as s
from tests import test_mvp2_s2_first_normal as fixtures


@pytest.fixture
def source(tmp_path):
    files = {}
    for name in sorted(identity.REQUIRED | {"asset.pdf"}):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = b"\x00\xffraw-CRLF\r\n" + name.encode()
        path.write_bytes(raw)
        files[name] = hashlib.sha256(raw).hexdigest()
    manifest = {
        "schema_version": "s2-sealed-source-v1",
        "source_commit": "a" * 40,
        "files": files,
        "source": identity.source_summary(files),
    }
    return tmp_path, manifest, s.digest(manifest)


def verify(source):
    root, manifest, digest = source
    return identity.verify_compute_source(root, manifest, "a" * 40, digest)


def test_compute_bytes_without_git_or_any_process(source, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Compute identity must not execute a command.")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(a, "verify_checkout", forbidden)
    assert verify(source) == source[1]["source"]
    assert not (source[0] / ".git").exists()


@pytest.mark.parametrize("change", ["modified", "missing", "extra", "directory", "cache"])
def test_compute_tree_drift_rejected(source, change):
    root = source[0]
    if change == "modified":
        (root / "asset.pdf").write_bytes(b"changed")
    elif change == "missing":
        (root / "asset.pdf").unlink()
    elif change == "extra":
        (root / "json.py").write_text("shadow", encoding="ascii")
    else:
        (root / ("__pycache__" if change == "cache" else "extra")).mkdir()
    with pytest.raises(ValueError):
        verify(source)


@pytest.mark.parametrize("change", ["commit", "digest", "summary", "path", "closure", "extra_key"])
def test_manifest_binding_rejected(source, change):
    root, original, digest = source
    manifest = copy.deepcopy(original)
    if change == "commit":
        manifest["source_commit"] = "b" * 40
    elif change == "digest":
        digest = "0" * 64
    elif change == "summary":
        manifest["source"]["tracked_count"] += 1
    elif change == "path":
        manifest["files"]["../escape"] = "0" * 64
    elif change == "closure":
        del manifest["files"]["scripts/mvp2_s2_synthetic_worker.py"]
    else:
        manifest["execution_admitted"] = True
    if change not in {"commit", "digest"}:
        digest = s.digest(manifest)
    with pytest.raises(ValueError):
        identity.verify_compute_source(root, manifest, "a" * 40, digest)


def test_byte_bound(source, monkeypatch):
    monkeypatch.setattr(identity, "TREE_LIMIT", 1)
    with pytest.raises(ValueError, match="byte bound"):
        verify(source)


def test_source_symlink_rejected(source, monkeypatch):
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda p: p.name == "asset.pdf" or original(p))
    with pytest.raises(ValueError, match="Linked"):
        verify(source)


def test_walk_error_not_silently_ignored(source, monkeypatch):
    def denied(*args, **kwargs):
        kwargs["onerror"](PermissionError("private directory"))

    monkeypatch.setattr(identity.os, "walk", denied)
    with pytest.raises(PermissionError):
        verify(source)


def runtime_spec():
    env = fixtures.envelope.__wrapped__()
    return fixtures.spec.__wrapped__(env)


@pytest.mark.parametrize("missing", [None, "python", *identity.COMPUTE_TOOLS])
def test_runtime_checks_compute_tools_not_git(missing, monkeypatch):
    spec = runtime_spec()
    paths = {spec["python"]: spec["python_sha256"]}
    paths.update({spec["tools"][k]: spec["tools_sha256"][k] for k in identity.COMPUTE_TOOLS})
    calls = []

    def checksum(path, *args):
        calls.append(path)
        assert path != spec["tools"]["git"]
        if missing and path == (spec["python"] if missing == "python" else spec["tools"][missing]):
            raise FileNotFoundError("unavailable executable")
        return paths[path]

    monkeypatch.setattr(a, "sha_file", checksum)
    if missing:
        with pytest.raises(FileNotFoundError):
            identity.verify_compute_runtime(spec)
    else:
        result = identity.verify_compute_runtime(spec)
        assert set(result["verified_tools_sha256"]) == set(identity.COMPUTE_TOOLS)
        assert result["login_only_tools"] == ["git", "sbatch"]
        assert result["execution_admitted"] is False
        assert len(calls) == 5


def test_compute_tool_drift_rejected(monkeypatch):
    monkeypatch.setattr(a, "sha_file", lambda *args: "0" * 64)
    with pytest.raises(ValueError, match="byte drift"):
        identity.verify_compute_runtime(runtime_spec())


def test_login_seal_uses_raw_git_gate_and_compute_rejects_extra_files(source, monkeypatch):
    root, manifest, _digest = source
    spec = runtime_spec()
    spec["checkout"] = str(root)
    # Windows fixture paths are not production POSIX paths; production validation
    # is covered separately by the existing strict spec suite.
    monkeypatch.setattr(a, "validate_spec", lambda item: item)
    original = a.sha_file
    monkeypatch.setattr(
        a,
        "sha_file",
        lambda p, *args: (
            spec["tools_sha256"]["git"] if p == spec["tools"]["git"] else original(p, *args)
        ),
    )
    calls = []

    def raw_gate(item, command):
        calls.append("raw_head")
        return manifest["source"]

    monkeypatch.setattr(a, "verify_checkout", raw_gate)

    def command(argv, **kwargs):
        calls.append(argv)
        if "ls-files" in argv:
            return "".join(
                "100644 " + "f" * 40 + " 0\t" + name + "\0" for name in manifest["files"]
            )
        return "a" * 40 + "\n"

    assert identity.seal_login_source(spec, command) == manifest
    assert calls[0] == "raw_head"
    (root / "untracked.py").write_bytes(b"shadow")
    with pytest.raises(ValueError, match="Extra"):
        identity.seal_login_source(spec, command)


@pytest.mark.parametrize("phase", ["require_host", "load_claim", "claim_batch"])
@pytest.mark.parametrize(
    "error", [FileNotFoundError("SECRET/path"), KeyError("SECRET"), KeyboardInterrupt()]
)
def test_early_batch_failure_is_redacted_and_has_no_dispatch(
    tmp_path, monkeypatch, capsys, phase, error
):
    def fail(*args, **kwargs):
        raise error

    def forbidden(*args, **kwargs):
        pytest.fail("No shared batch or worker after entry failure")

    monkeypatch.setattr(n, "require_host", fail if phase == "require_host" else lambda: None)
    monkeypatch.setattr(
        recovery, "load_claim", fail if phase == "load_claim" else lambda _: (tmp_path, {}, {})
    )
    if phase == "claim_batch":
        monkeypatch.setattr(Path, "mkdir", fail)
    monkeypatch.setattr(n, "batch_components", forbidden)
    with pytest.raises(SystemExit, match="2"):
        recovery.batch("a" * 40)
    captured = capsys.readouterr()
    assert captured.out == "" and "SECRET" not in captured.err and str(tmp_path) not in captured.err
    record = json.loads(captured.err.removeprefix("S2_RECOVERY_ENTRY_DIAGNOSTIC="))
    assert record["phase"] == phase
    assert record["status"] == "blocked_before_shared_batch"
    assert all(record[k] is False for k in n.FUTURE)
    assert not (tmp_path / "batch-outcome.json").exists()


def test_closed_component_cli_has_no_scheduler(tmp_path):
    script = Path(identity.__file__).resolve()
    result = subprocess.run(
        [sys.executable, "-B", "-I", str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode != 0
    assert "no execution admitted" in result.stderr
    assert list(tmp_path.iterdir()) == []


def test_isolated_process_missing_git_captures_real_file_error(tmp_path):
    root = Path(identity.__file__).resolve().parents[1]
    code = """
import hashlib, json, pathlib, sys
sys.path.insert(0, sys.argv[1])
from scripts import mvp2_s2_first_normal as n
from scripts import mvp2_s2_normal_recovery as r
python = str(pathlib.Path(sys.executable).resolve())
digest = hashlib.sha256(pathlib.Path(python).read_bytes()).hexdigest()
env = {'python': python, 'python_sha256': digest,
       'tools': {'git': sys.argv[2]}, 'tool_sha256': {'git': '0' * 64}}
n.require_host = lambda: None
def load(_):
    n.recheck(env)
    raise AssertionError('Must fail on unavailable Git before any scheduler access')
r.load_claim = load
r.batch('a' * 40)
"""
    result = subprocess.run(
        [sys.executable, "-B", "-I", "-c", code, str(root), str(tmp_path / "absent-git")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 2 and result.stdout == ""
    report = json.loads(result.stderr.removeprefix("S2_RECOVERY_ENTRY_DIAGNOSTIC="))
    assert report["phase"] == "load_claim" and report["error_kind"] == "os_error"
    assert report["site"]["module"] == "mvp2_s2_batch_adapter"
    assert "absent-git" not in result.stderr and "Traceback" not in result.stderr
    assert list(tmp_path.iterdir()) == []


@pytest.mark.skipif(sys.platform != "linux", reason="Real POSIX checkout/spec; no Slurm")
def test_real_git_seal_then_compute_without_git(source):
    import shutil

    root, _manifest, _digest = source
    git = str(Path(shutil.which("git")).resolve())
    prefix = (
        git,
        "-c",
        "core.autocrlf=false",
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "user.name=Offline fixture",
        "-c",
        "user.email=fixture@example.invalid",
    )

    def run(*args):
        return subprocess.run(prefix + args, cwd=root, check=True, capture_output=True, timeout=10)

    run("init")
    run("add", ".")
    run("commit", "-m", "Disposable identity fixture")
    spec = runtime_spec()
    spec["checkout"] = str(root)
    spec["source_commit"] = run("rev-parse", "HEAD").stdout.decode().strip()
    spec["tools"]["git"] = git
    spec["tools_sha256"]["git"] = hashlib.sha256(Path(git).read_bytes()).hexdigest()
    calls = []

    def command(argv, **kwargs):
        calls.append(argv)
        result = subprocess.run(argv, cwd=root, capture_output=True, check=True, timeout=10)
        return result.stdout if "cat-file" in argv else result.stdout.decode()

    manifest = identity.seal_login_source(spec, command)
    assert any("cat-file" in argv for argv in calls)
    assert (
        identity.verify_compute_source(root, manifest, spec["source_commit"], s.digest(manifest))
        == manifest["source"]
    )
    cache = root / "scripts" / "__pycache__"
    cache.mkdir()
    bytecode = cache / "mvp2_s2_synthetic_worker.cpython-313.pyc"
    bytecode.write_bytes(b"historical cache, never executed")
    (root / ".git" / "info" / "exclude").write_text("__pycache__/\n", encoding="utf-8")
    historical = identity.seal_historical_source(spec, command)
    assert historical["source"] == manifest["source"]
    assert (
        identity.verify_historical_source(
            root, historical, spec["source_commit"], s.digest(historical)
        )
        == manifest["source"]
    )
    assert bytecode.read_bytes() == b"historical cache, never executed"
    with pytest.raises(ValueError, match="Extra source directory"):
        identity.seal_login_source(spec, command)
    (root / "asset.pdf").write_bytes(b"drift after preparation")
    with pytest.raises(ValueError, match="changed"):
        identity.verify_historical_source(
            root, historical, spec["source_commit"], s.digest(historical)
        )
    with pytest.raises(ValueError):
        identity.seal_historical_source(spec, command)


def test_history_cache_is_preserved_but_not_current_execution_admission(source, monkeypatch):
    root, manifest, digest = source
    cache = root / "scripts" / "__pycache__"
    cache.mkdir()
    bytecode = cache / "mvp2_s2_synthetic_worker.cpython-313.pyc"
    bytecode.write_bytes(b"untrusted historical bytes; never import or execute")
    historical = {**manifest, "schema_version": "s2-historical-tracked-source-v1"}
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: pytest.fail("History execution"))
    assert (
        identity.verify_historical_source(root, historical, "a" * 40, s.digest(historical))
        == manifest["source"]
    )
    assert before == {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    with pytest.raises(ValueError, match="Extra source directory.*__pycache__"):
        identity.verify_compute_source(root, manifest, "a" * 40, digest)
    with pytest.raises(ValueError, match="binding"):
        identity.verify_compute_source(root, historical, "a" * 40, s.digest(historical))
    with pytest.raises(ValueError, match="binding"):
        identity.verify_historical_source(root, manifest, "a" * 40, digest)


@pytest.mark.parametrize("drift", ["changed", "missing", "digest", "commit", "bound"])
def test_historical_tracked_integrity_cannot_be_bypassed(source, monkeypatch, drift):
    root, original, _ = source
    manifest = {**original, "schema_version": "s2-historical-tracked-source-v1"}
    target = root / next(iter(manifest["files"]))
    if drift == "changed":
        target.write_bytes(b"drift")
    elif drift == "missing":
        target.unlink()
    elif drift == "bound":
        monkeypatch.setattr(identity, "TREE_LIMIT", 1)
    with pytest.raises((ValueError, OSError)):
        identity.verify_historical_source(
            root,
            manifest,
            "b" * 40 if drift == "commit" else "a" * 40,
            "0" * 64 if drift == "digest" else s.digest(manifest),
        )


def test_history_walk_rejects_tracked_link_path_without_reading_it(source, monkeypatch):
    root, original, _ = source
    historical = {**original, "schema_version": "s2-historical-tracked-source-v1"}
    target = root / next(iter(historical["files"]))
    original_safe = identity.q._safe_path

    def safe(path):
        if path == target:
            raise ValueError("Linked path")
        return original_safe(path)

    monkeypatch.setattr(identity.q, "_safe_path", safe)
    monkeypatch.setattr(a, "_file", lambda *a, **kw: pytest.fail("Read unsafe history"))
    with pytest.raises(ValueError, match="Linked"):
        identity.verify_historical_source(root, historical, "a" * 40, s.digest(historical))
