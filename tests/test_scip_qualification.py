"""A successful pytest exit alone does not establish native solver qualification."""

import pytest

from scripts.qualify_scip_backend import qualification_status


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
