"""The NPAD handoff resumes existing claims without any new submission."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import preflight_mvp2_resource_pair as gate
from tests.test_mvp2_preflight_collection import run_fixture


def shell_path(path):
    path = Path(path)
    if sys.platform == "win32":
        return f"/{path.drive[0].lower()}{path.as_posix()[2:]}"
    return str(path)


def bash_path():
    bash = "C:/Program Files/Git/bin/bash.exe" if sys.platform == "win32" else shutil.which("bash")
    if not bash:
        pytest.skip("Bash unavailable")
    return bash


@pytest.mark.parametrize("accepted", [True, False])
def test_repeated_start_collects_claim_without_git_clone_or_sbatch(tmp_path, accepted):
    run = run_fixture(tmp_path, accepted=accepted)
    run = run.rename(tmp_path / "mvp2-h300-input-retry-test")
    (run / "source/scripts").mkdir(parents=True)
    collector = (gate.ROOT / "scripts/collect_mvp2_pair_preflight.py").read_text()
    # Windows cannot launch shebang-only sacct from Python: mock that OS boundary.
    accounting = "123|" + ("COMPLETED|0:0" if accepted else "FAILED|1:0") + "\n"
    if sys.platform == "win32":
        collector = collector.replace(
            'if __name__ == "__main__":',
            f'subprocess.check_output = lambda *args, **kwargs: {accounting!r}\n'
            'if __name__ == "__main__":',
        )
    (run / "source/scripts/collect_mvp2_pair_preflight.py").write_text(collector)
    commit = "a" * 40
    claim = tmp_path / f".pr47-h300-input-retry-{commit}"
    claim.mkdir()
    (claim / "run.txt").write_text(shell_path(run) + "\n")
    driver = tmp_path / "driver.sh"
    body = (gate.ROOT / "scripts/npad_pr47_h300_input_retry.sh").read_text()
    body = body.replace("BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit",
                        f'BASE="{shell_path(tmp_path)}"').replace(
                            "PY=/home/vrrcelestino/venv313/bin/python",
                            f'PY="{shell_path(sys.executable)}"')
    driver.write_text(body, newline="\n")
    fake = tmp_path / "bin"
    fake.mkdir()
    forbidden = tmp_path / "forbidden-call"
    commands = {
        "sha256sum": (
            'case "$1" in */campaign.yaml) echo '
            '348c4c08c2c9e906cbd3a28df7753577ebed3cac30702aae30dfb8ce2ad25694;;\n'
            '*) echo b9e4b2a5bb7ecf66b0c54432986c3033bf381bdea223fc914ddefa7dcc24bde7;; esac\n'
        ),
        "git": ('if [ "$3" = rev-parse ]; then echo test-only-source; else '
                'echo git > "$FORBIDDEN"; exit 99; fi\n'),
        "sbatch": 'echo sbatch > "$FORBIDDEN"; exit 99\n',
        "sacct": 'echo "123|' + ("COMPLETED|0:0" if accepted else "FAILED|1:0") + '"\n',
    }
    for name, script in commands.items():
        target = fake / name
        target.write_text("#!/bin/bash\nset -eu\n" + script, newline="\n")
        target.chmod(0o755)
    env = dict(os.environ, FORBIDDEN=shell_path(forbidden))
    before = (run / "audit/submission.txt").read_bytes()
    for _ in range(2):
        result = subprocess.run([
            bash_path(), "-c", 'export PATH="$1:/usr/bin:/bin:$PATH"; exec bash "$2" start "$3"',
            "_", shell_path(fake), shell_path(driver), commit,
        ], env=env, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "no job will be submitted again" in result.stdout
        status = "accepted" if accepted else "terminal_failure"
        assert f"COLLECTION_STATUS={status}" in result.stdout
    assert not forbidden.exists()
    assert (run / "audit/submission.txt").read_bytes() == before
    assert len(list(run.glob("collection-*/evidence/*.tar.gz"))) == 2


@pytest.mark.parametrize("arguments", [[], ["start"], ["start", "develop"], ["solve"]])
def test_driver_rejects_missing_or_unpinned_start_before_np_ad_actions(arguments):
    result = subprocess.run([
        bash_path(), shell_path(gate.ROOT / "scripts/npad_pr47_h300_input_retry.sh"), *arguments,
    ], capture_output=True, text=True, timeout=30)
    assert result.returncode != 0
    assert "STOP:" in result.stderr
