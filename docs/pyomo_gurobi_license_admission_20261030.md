# Pyomo Gurobi license admission repair — 30 October 2026

## Accepted NPAD public license qualification

The researcher supplied complete records for public job **2228385**, step **0**,
on 30 October 2026. Gurobi **13.0.3** returned native status **2** and objective
**2001.0** for the public LP with **2001 variables and 2001 rows**. The process
default environment is the route used by APPSI; no private input was accessed.

The source-identity file selects
`fe37669c24895a0bb2a45ff18e99ae7028722c2f`, and both public-file SHA-256s
match the pinned recipe. Reconstructing the posted JSON with the producer's
serialization matches its supplied original-file hash
`a2a8aaa52f262f7cee2829efb19736973146653ce51b7d8b1dd33f480e2d3223`.
Root, batch, extern and step all report **COMPLETED, 0:0, 3 seconds**, with
one CPU. These are researcher-supplied records, not direct NPAD file access;
the short public probe is not a scientific runtime or memory comparison.

The [closed public receipt](evidence/pyomo_gurobi_license_public_2228385_reported.json)
therefore supports both license capacity and operational closure. Its executed
source passed five GitHub checks, including **315 Pyomo tests** and **1715 full
native tests** without skips. Subsequent commits record evidence/documentation
only. Finish exact-head checks, mark the correction ready and request its own
merge authorization. No public resubmission or private h215 start is admitted.
The original Gurobi failure and the independent SCIP arm remain preserved.

Job 2228189 did not produce a numerical Gurobi result. Its original worker
trace ends in `GurobiError: Model too large for size-limited license` at
APPSI's native `Model.optimize()`. The original archive, consumed v1 claim,
source and independent SCIP job remain preserved. The evidence and integrity
audit are in [PR142](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/pull/142),
including the [original failure report](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/docs/h215-evidence-and-mvp2-plan-20261030/docs/pyomo_gurobi_h215_2228189_license_failure.md).

## Cause and scope of the repair

The native launchers explicitly selected
`/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic`.
The common-Pyomo launcher omitted that selection. The researcher confirmed
this existing license path on 30 October. The retained trace proves that
the active native model had restricted size capability; it does not prove
the original inherited environment value, or today's designated license validity.

Pyomo 6.10.1 APPSI constructs Gurobi models with the process default environment.
Its truthy `Availability.LimitedLicense` permits public miniature models.
A version check and passing miniature tests therefore do not admit a large
instance. A probe using a separate custom Gurobi environment would not prove
that APPSI's actual default environment is capable.

The repair selects the designated existing file only for a prospective Gurobi
start, before SDK initialization. Login checks file metadata/access only.
An additional compute-worker admission gate then solves a public bounded LP
with 2001 variables and 2001 rows, exceeding the bundled 2000 limits.
Its known optimum is 2001, with one thread and a ten-second optimization cap.
It uses `gp.Model()` without a custom `Env`, exactly the environment route
used by APPSI. Only the owned probe model is disposed; the default environment
is kept for the later adapter. No full license is required by the generic
miniature-model API.

The gate runs in the existing timed `native_identity` stage before public
math controls and private construction. It retains an identity-bound,
redacted capability receipt before refusing an unsuccessful probe. Successful
operational replay requires the same owned receipt and checks its dimensions,
native version, status, objective and environment scope. Startup output is
discarded, and reports retain safe error types/integer codes rather than raw
exception strings. License contents are never read, hashed, copied or uploaded.

## Qualification and release boundary

Local mocked fault controls cover restricted licenses, incorrect objective,
nonoptimal return, wrong/default environment evidence, redacted initialization,
other-engine isolation and refusal before a private build. A separate real
local restricted-license control reproduced error 10010 with the public LP
and confirmed that a miniature APPSI model remains usable afterwards.
Its compute/file-policy guards were mocked for that local negative control;
it is not a positive NPAD qualification or a license-file test.

The original job's traceback does not retain a numeric error code; 10010 is
observed only in the separate local negative control. Windows cannot execute
the Linux `/proc` cold-worker controls or import Unix `resource`; Linux CI
covers the related controls. The compute-node LP capacity, source identity and terminal accounting are now
accepted for this bounded public license qualification; no private admission follows.

No mathematical builder, adapter, model/data file, parameter/seed contract,
validator, original source or evidence package changes in this repair.
It does not tune Gurobi, alter the SCIP arm, admit CBC or restart HiGHS.
The old Gurobi v1 claim remains consumed. The existing qualification freezes
its original execution bytes and cannot qualify this changed launcher.
Any later private attempt needs a separately reviewed source qualification,
a new claim and manual execution instructions. No h215 start is released here.

## References

- [Gurobi's explanation of restricted-size errors](https://support.gurobi.com/hc/en-us/articles/360051597492-How-do-I-resolve-a-Model-too-large-for-size-limited-Gurobi-license-error).
- [APPSI Gurobi source](https://pyomo.readthedocs.io/en/stable/_modules/pyomo/contrib/appsi/solvers/gurobi.html);
  exact installed version 6.10.1 was inspected during the diagnosis.
- [Gurobi model/default environment API](https://docs.gurobi.com/projects/optimizer/en/current/reference/python/model.html).

