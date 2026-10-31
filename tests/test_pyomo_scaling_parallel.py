"""Cold real-native public controls; no private workbook or scheduler access."""

import importlib.util
import json
import os
import subprocess
import sys

import pytest

from scripts import pyomo_scaling_contract as c
from scripts.qualify_pyomo_scaling import HERE, probe_command


def native_command(solver, threads, output):
    command = probe_command(solver, threads, output)
    # A temporary wheel directory is a local test dependency only. Production
    # compute qualification uses the already installed venv313 packages.
    local_site = os.environ.get("SCALING_LOCAL_TEST_SITE")
    if local_site and not os.environ.get("SLURM_JOB_ID"):
        code = (
            "import sys,runpy;sys.path.insert(0,sys.argv.pop(1));"
            "runpy.run_path(sys.argv.pop(1),run_name='__main__')"
        )
        command = [sys.executable, "-B", "-I", "-c", code, local_site, *command[3:]]
    return command


def require_native():
    required = os.environ.get("AGRO_REQUIRE_SCALING_SOLVERS") == "1"
    absent = importlib.util.find_spec("highspy") is None and not os.environ.get(
        "SCALING_LOCAL_TEST_SITE"
    )
    if absent:
        if required:
            pytest.fail("Installed HiGHS required; skips cannot qualify compute.")
        pytest.skip("Optional native HiGHS absent from this local test profile.")


def require_gurobi():
    from pyomo.contrib.appsi.solvers import Gurobi

    if not Gurobi().available():
        if os.environ.get("AGRO_REQUIRE_SCALING_SOLVERS") == "1":
            pytest.fail("Installed licensed Gurobi required; no compute skips.")
        pytest.skip("Local Gurobi license unavailable; NPAD qualification remains pending.")


@pytest.mark.parametrize("solver", c.SOLVERS)
@pytest.mark.parametrize("threads", c.THREADS)
def test_real_cold_native_threads_and_parallel_option(solver, threads, tmp_path):
    require_native()
    if solver == "gurobi":
        require_gurobi()
    output = tmp_path / "public.json"
    process = subprocess.run(
        native_command(solver, threads, output),
        cwd=HERE,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    assert process.returncode == 0, (process.stdout + process.stderr)[-8000:]
    record = json.loads(output.read_bytes())
    assert record["private_input_accessed"] is False
    assert record["validation"] == "accepted"
    assert record["objective"] == pytest.approx(167 + 10 / 3)
    parameters = record["effective_parameters"]
    if solver == "highs":
        assert parameters["threads"] == threads and parameters["parallel"] == "on"
        assert parameters["random_seed"] == 42
    else:
        assert parameters["Threads"] == threads and parameters["Seed"] == 42
        assert parameters["Method"] == parameters["NodeMethod"] == parameters["Presolve"] == -1


def test_both_real_solvers_receive_identical_public_ordered_matrix(tmp_path):
    require_native()
    require_gurobi()
    matrices = []
    for solver in c.SOLVERS:
        output = tmp_path / (solver + ".json")
        process = subprocess.run(
            native_command(solver, 4, output),
            cwd=HERE,
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        assert process.returncode == 0, (process.stdout + process.stderr)[-8000:]
        matrices.append(json.loads(output.read_bytes())["matrix"])
    assert matrices[0] == matrices[1]
