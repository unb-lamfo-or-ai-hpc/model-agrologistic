"""No network, NPAD filesystem, job, worker, solver or license is exercised."""

import ast
import re
import subprocess
import sys
from pathlib import Path

import pytest

DRIVER = Path(__file__).resolve().parents[1] / "scripts/npad_s2_envelope.sh"


def test_envelope_driver_preserves_evidence_and_uses_only_readonly_probe():
    text = DRIVER.read_text(encoding="utf-8")
    assert "\r" not in text
    assert 'git -C "$SRC" merge-base --is-ancestor "$SOURCE_SHA" origin/develop' in text
    assert 'test -z "$(git -C "$SRC" status --porcelain --untracked-files=all)"' in text
    assert '--basetemp="$RUN/tests"' in text
    assert "run-location.txt" in text and "RUN_PATH_PRESENT_ON_EXIT=" in text
    assert "bootstrap-phases.txt" in text and "trap finish EXIT" in text
    assert "-B -I" in text and "probe-envelope" in text
    assert not re.search(r"(?m)^\s*(?:rm|rmdir|mv|sbatch|srun|scancel|kill|pkill|pip)\b", text)
    assert "GRB_LICENSE_FILE" not in text
    assert text.index("phase regression") < text.index("phase read_only_probe")
    assert text.index("merge-base --is-ancestor") < text.index("phase regression")


def test_envelope_driver_embedded_python_is_syntactically_valid():
    text = DRIVER.read_text(encoding="utf-8")
    chunks = re.findall(r"<<'PY'\n(.*?)\nPY\n", text, re.S)
    assert len(chunks) == 1
    ast.parse(chunks[0])
    assert "len(cases) == 170" in chunks[0]
    assert "len(skips) == 1" in chunks[0]


@pytest.mark.skipif(sys.platform != "linux", reason="Linux Bash syntax only; no driver execution")
def test_envelope_driver_bash_syntax():
    result = subprocess.run(
        ["bash", "-n", str(DRIVER)], capture_output=True, timeout=10, check=False
    )
    assert result.returncode == 0, result.stderr.decode()


@pytest.mark.skipif(
    sys.platform != "linux", reason="Linux invalid-argument denial before any effects"
)
@pytest.mark.parametrize("arguments", [[], ["bad"], ["a" * 40, "extra"]])
def test_envelope_driver_invalid_arguments_stop_before_any_effect(arguments):
    result = subprocess.run(
        ["bash", str(DRIVER), *arguments], capture_output=True, timeout=10, check=False
    )
    assert result.returncode == 64
    assert result.stdout == b"" and b"Usage:" in result.stderr
