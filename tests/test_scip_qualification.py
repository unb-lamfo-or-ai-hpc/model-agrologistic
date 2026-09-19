"""A successful pytest exit alone does not establish native solver qualification."""

from pathlib import Path

import pytest

from scripts.qualify_scip_backend import qualification_status


def test_qualification_submission_uses_account_default_qos():
    root = Path(__file__).resolve().parents[1]
    worker = (root / "scripts/run_scip_qualification.slurm").read_text(encoding="utf-8")
    directives = [line.strip() for line in worker.splitlines() if line.startswith("#SBATCH")]
    assert not any("--qos" in line or " -q" in line for line in directives)
    protocol = (root / "docs/scip_qualification_protocol.md").read_text(encoding="utf-8")
    assert "unset SBATCH_QOS" in protocol


@pytest.mark.parametrize(
    "xml,codes,available,expected",
    [
        ("<testsuite><testcase/></testsuite>", [0, 0], True, "accepted"),
        ("<testsuite><testcase><skipped/></testcase></testsuite>", [0], True, "rejected"),
        ("<testsuite><testcase><failure/></testcase></testsuite>", [0], True, "rejected"),
        ("<testsuite/>", [0], True, "rejected"),
        ("<testsuite><testcase/></testsuite>", [1], True, "rejected"),
        ("<testsuite><testcase/></testsuite>", [0], False, "rejected"),
    ],
)
def test_fail_closed_qualification(tmp_path, xml, codes, available, expected):
    path = tmp_path / "pytest.xml"
    path.write_text(xml, encoding="utf-8")
    status, _, _ = qualification_status(codes, path, runtime_available=available)
    assert status == expected
