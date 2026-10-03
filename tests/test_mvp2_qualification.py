"""Fail-closed NPAD miniature qualification and portable worker contracts."""

from pathlib import Path

from scripts.qualify_scip_backend import qualification_status

ROOT = Path(__file__).resolve().parents[1]


def test_mvp2_worker_has_no_compute_git_or_required_memory_environment():
    worker = (ROOT / "scripts/run_mvp2_qualification.slurm").read_text()
    assert "git rev-parse" not in worker
    assert 'os.environ["SLURM_MEM_PER_NODE"]' not in worker
    assert "SLURM_MEM_PER_NODE:?" not in worker
    assert 'scontrol show job "$SLURM_JOB_ID"' in worker
    assert 'scontrol show node "${SLURMD_NODENAME:?}"' in worker
    assert 'os.environ["MVP2_IDENTITY"]' in worker


def test_submission_uses_existing_environment_and_no_hardcoded_qos():
    submit = (ROOT / "scripts/submit_mvp2_qualification.sh").read_text()
    assert "--qos" not in submit
    assert "SBATCH_QOS" in submit
    assert "/home/vrrcelestino/venv313/bin/python" in submit
    assert "pip install" not in submit
    assert "--test-only" in submit
    assert 'mkdir "$MVP2_REPORT/.submission-claimed"' in submit
    assert "--mem=16G" in submit


def test_licensed_qualification_cannot_accept_skipped_parity(tmp_path):
    junit = tmp_path / "pytest.xml"
    junit.write_text(
        '<testsuites><testsuite tests="2" failures="0" errors="0" skipped="1">'
        '<testcase name="parity"><skipped/></testcase></testsuite></testsuites>'
    )
    status, _, skipped = qualification_status([0, 0], junit, runtime_available=True)
    assert status != "accepted"
    assert skipped == 1


def test_analytical_filter_and_large_campaign_gate_are_explicit():
    source = (ROOT / "scripts/qualify_mvp2_resources.py").read_text()
    assert "not gurobi and not licensed_stagewise_parity" in source
    assert '"production_explicit_lifecycle_allowed": False' in source
    assert '"large_instance_submission_allowed": False' in source
