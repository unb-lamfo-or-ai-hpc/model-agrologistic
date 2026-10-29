"""Read-only preparation safety without a scheduler, solver or NPAD connection."""

import hashlib
import io
import tarfile

import pytest

from scripts import qualify_pyomo_adapters as q

SHA = "a" * 40


def source_tar(path, extra=None):
    with tarfile.open(path, "w:gz") as archive:
        for name in q.TESTS:
            info = tarfile.TarInfo("model-agrologistic-" + SHA + "/" + name)
            data = b"# inert test fixture\n"
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
        if extra is not None:
            archive.addfile(extra, io.BytesIO(b""))


def test_safe_source_inventory_has_hashes_without_executing_any_member(tmp_path):
    archive = tmp_path / "source.tar.gz"
    source_tar(archive)
    output = tmp_path / "source"
    output.mkdir()
    files = q.extract_source(archive, output, SHA)
    assert set(files) == set(q.TESTS)
    assert all(value == hashlib.sha256(b"# inert test fixture\n").hexdigest()
               for value in files.values())


@pytest.mark.parametrize("name", ["/outside", "../outside", "model-agrologistic-wrong/x"])
def test_source_escape_or_wrong_identity_is_rejected(tmp_path, name):
    archive = tmp_path / "source.tar.gz"
    source_tar(archive, tarfile.TarInfo(name))
    output = tmp_path / "source"
    output.mkdir()
    with pytest.raises(ValueError, match="Unsafe"):
        q.extract_source(archive, output, SHA)
    assert not (tmp_path / "outside").exists()


def test_source_link_is_never_followed(tmp_path):
    archive = tmp_path / "source.tar.gz"
    link = tarfile.TarInfo("model-agrologistic-" + SHA + "/link")
    link.type = tarfile.SYMTYPE
    link.linkname = "../../outside"
    source_tar(archive, link)
    output = tmp_path / "source"
    output.mkdir()
    with pytest.raises(ValueError, match="Unsafe"):
        q.extract_source(archive, output, SHA)
    assert not (output / "link").exists()


def test_cbc_hash_failure_precedes_executable_write(tmp_path):
    archive = tmp_path / "wrong.tar.gz"
    archive.write_bytes(b"untrusted")
    target = tmp_path / "bin/cbc"
    with pytest.raises(ValueError, match="checksum"):
        q.extract_cbc(archive, target)
    assert not target.exists()


def test_qualification_is_public_and_not_an_h215_execution_admission():
    assert all(name.startswith("tests/test_") for name in q.TESTS)
    assert "tests/test_pyomo_solver_adapters.py" in q.TESTS
    assert "tests/test_scalar_highs_math.py" in q.TESTS
    assert q.EXPECTED_TESTS == 167


def test_human_home_root_cannot_be_a_qualification_claim(tmp_path):
    with pytest.raises(ValueError, match="dedicated"):
        q.location(tmp_path)
