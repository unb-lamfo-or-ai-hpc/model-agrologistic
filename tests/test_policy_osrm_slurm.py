SCRIPT = __file__.replace("\\", "/").replace(
    "tests/test_policy_osrm_slurm.py",
    "scripts/materialize_policy_osrm_215.slurm",
)


def test_policy_osrm_launcher_is_bounded_and_reproducible():
    with open(SCRIPT, "rb") as stream:
        raw = stream.read()
    text = raw.decode("utf-8")

    assert b"\r" not in raw
    assert "#SBATCH --time=12:00:00" in text
    assert "#SBATCH --mem=192G" in text
    assert "policy_population_v020/warehouses_215/model_input.xlsx" in text
    assert "materialize_policy_osrm_workbook.py" in text
    assert "policy-pairs-v020.sqlite3" in text
    assert 'expected_counts = {"OD": 7_955' in text
    assert "OSRM POLICY 215 MATERIALIZATION GATE: READY FOR REVIEW" in text
    assert "build_artur_solver_workbook.py" not in text
    assert "run_batch_hpc.py" not in text
