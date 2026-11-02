# Original public qualification2227457 and isolated repair

The original sourcefd4ef123 / plan9b5eb14b completed167public tests:
166passed,1failed,0errors,0skips in39.68s. Source integrity remained valid
afterward. Its original result remains REJECTED and claim-v1 is preserved.
No private h215 input or scientific experiment was executed.

The bounded human read-only diagnostic identifies exactly one failed case:
tests.test_scalar_highs_h215_8h_startup.test_existing_claim_never_submits_or_collects.
It expected the existing-claim guard, but inherited the real SLURM_JOB_ID from
the compute allocation. The production function first rejects calls from compute
with Login Python3.13 only, so this test never reached its intended login guard.
The diagnostic XML SHA256 is
68423e51c25488b5e209368440093f2f3395e2019b449a308506fcc42051ffac.

The repair changes the TEST fixture only: temporarily remove SLURM_JOB_ID to
simulate a login call, then let monkeypatch restore the real allocation identity.
A separate new test explicitly simulates compute context and confirms the login
guard still rejects start, preserves the sentinel and cannot call a scheduler.
No runtime guard, numerical acceptance criterion, source data or solver setting
is relaxed. The original167-test result is not retroactively promoted.

Local Ruff and both guard tests passed with an inherited simulated SLURM_JOB_ID.
The portable preparation/startup subset passed48tests;9Linux/path-specific
cases remain in the full target gate. Preparation now has12local safety controls,
including immutable predecessor checks. The full new target gate is168tests,
zero failures/errors/skips, with original/new source and executable integrity.

Requalification uses a NEW qualification-v2 claim and verifies the untouched
v1 plan, result and XML against their recorded identities before creation and
on compute. It does not reset, overwrite or repeat start on the consumed v1.
The result records failed testcase identities directly to reduce diagnostic
round trips. Only the researcher can submit the public qualification job.
PR140 stays draft; private h215 execution remains held until this gate and the
separately qualified operational package pass.

The future scientific arms remain one cold Pyomo Gurobi, SCIP and CBC h215 STO/W
observation each with the frozen W workbook/population/OSRM graph and common
bounded formulation. Preserve the existing HiGHS result and all original claims.
