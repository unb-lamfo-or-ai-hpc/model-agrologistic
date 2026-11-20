# Minimal Gurobi 14 compatibility assessment

Date: 20 November 2026. Status: preparation only; NPAD execution pending.

This follows the researcher-authorized AGRO-MVP3-GRB14 mandate dated
19 November 2026. It is a compatibility test, not a performance comparison,
a new scientific campaign, or evidence that Gurobi 14 is already accepted.

## Scope and sequence

1. Confirm the existing NPAD interpreter, environment type, package versions
   and qualified h215 input identities with the read-only preflight.
2. Clone the historical environment into a fresh directory below
   /home/vrrcelestino/model-agrologistic-hygiene-audit/.
   Preserve the original environment and record its identity before and after.
3. Change only the cloned environment's gurobipy distribution to 14.0.0.
   Do not upgrade pip or resolve/install other dependencies.
   Use an exact package pin and --no-deps; compare installed distributions
   before and after. A clone command must match the actual environment type.
   Do not substitute a newly created environment for a clone.
4. Prepare a migration-specific, single-use execution entry reusing the existing
   native DET builder and independent validator. Review its parameter audit
   without opening a local or CI license session.
5. The operator may submit exactly one NPAD job under the normal reviewed
   human-execution procedure. No array, public capacity job, trial optimization,
   comparison against version 13, retry or automatic follow-on is permitted.
6. Read back the original accounting and compatibility receipt. Preserve
   failures and missing values. Append actual results to this PR.

The NPAD environment preflight is pending. A package listing withdrawn by
the researcher as belonging to another project is excluded from this assessment.

## Qualified real input

The test instance is the original h215 DET/W, using the accepted workbook:
data/processed/policy_population_v020_osrm/warehouses_215/model_input.xlsx

Its SHA-256 is:
40edb66585daca9cc393cab1f86bde6d4528a5f34b6afc57260cc1684396da4e

Frozen population manifest SHA-256:
4134147f45188d2e8722476dd325b40e584c3746affe99889e045a547d283505

Frozen population order SHA-256:
7a524b2ed69b41481264d8049842b37e27cd3b96cc20d4e96d98eaf2a39e7903

The implementation must preserve the accepted DET/W preparation contract,
215 warehouses, 60 periods, original coefficients and selected network.
The historical workbook is test input only. It does not replace the latest
qualified data/parameter workbooks chosen as the MVP3.0 starting point.
Stage byte-identical input copies below the audit directory before execution;
never overwrite original inputs or modify an active campaign's claim.

## Reuse of the native implementation

Existing source at the inspected develop commit:

- src/logic/optimization_gurobipy.py: solve_model_gurobipy dispatches DET through
  the shared extensive-form constructor with deterministic inputs.
- src/logic/optimization_gurobipy_stochastic.py: the existing native constructor
  used by that DET dispatch; its filename does not imply an STO test is allowed.
- src/logic/mathematical_contract.py: retained deterministic preparation.
- src/logic/solution_validation.py: independent constraint/objective validation.
- experiments/mvp2_scalar_r3a_h215.yaml: historical loader/model specification.
- scripts/mvp2_scalar_r3a.py and the operational h215 wrappers: reference for
  input receipts, population identity and execution/collection mechanisms.

Do not run the historical pair launcher: it launches DET and STO and applies
historical solver settings. Do not run PR159's Pyomo public qualification.
Neither is the authorized migration test.

The existing _apply_solver_parameters always sets MIPGap and can set threads,
seed, logging and additional options. Its normal campaign configuration is not
a Gurobi-14-default configuration. A narrowly scoped migration entry must
isolate this parameter application from the unchanged mathematical constructor,
use the version-14 defaults, set only TimeLimit=300, and audit effective
algorithmic parameters immediately before optimize. This entry is pending;
no unreviewed execution command is supplied by this preparation.

An audit must not dump credentials, environment variables, a license file,
a parameter file containing authentication fields, or unrestricted exceptions.
Licensing parameters are required environment configuration, distinct from
the optimization parameters that must remain at their defaults. Logging
redaction must not silently change the optimization configuration.

## Environment and license feasibility

Official Gurobi documentation supports Python 3.13 for gurobipy 14.0.0.
This establishes a plausible software path, not compatibility of the actual
NPAD environment, operating system, existing model or license.

Academic WLS licenses normally require no update for a new major release.
Acceptance of the researcher-designated WLS must still be observed within
the single authorized job. Do not inspect or publish credential contents.
Do not test maximum model size, thread capacity or concurrent sessions.
The reported expiry and two-session capacity are operator-supplied metadata,
not independently verified capacity evidence.

The repository's historical dependency constraint and environment remain
unchanged. Invoke the pinned source using the cloned interpreter; do not
install the project in a way that resolves its historical gurobipy constraint
and downgrades or changes the test environment. Broader packaging migration
belongs after the compatibility decision.

## Single-job envelope

Retain CPU-only execution in intel-256, 192 GiB and an exclusive node allocation
consistent with NPAD policy. Request no GPU and install no GPU build.
Do not set Method, Threads, MIPGap, Seed, ConcurrentMIP, heuristics,
SoftMemLimit or tolerances. Scheduler resource allocation is not a solver
parameter and must be reported separately.

Choose the job wall limit using retained h215 construction/validation times,
allowing setup, model construction, 300 native seconds, result extraction and
collection. It is not a five-minute wall job. The final reviewed batch command
and its wall envelope are pending NPAD preflight and execution preparation.

## Minimal evidence and decision

Record only the interpreter/environment identity; Python and loaded Gurobi
versions; environment change verification; acceptance/rejection of the existing
WLS; pinned source, command and instance identities; terminal native status;
incumbent, best bound and gap when available; native Runtime, Work and nodes;
observed memory with measurement scope/units; sanitized incompatibility/error
codes; and independent validation if an incumbent is usable.

Use null for unavailable numeric evidence. TimeLimit without an incumbent is
not a compatibility failure when construction and optimization started
correctly. Do not require optimality or a gap below one percent.

GO requires the isolated exact version, accepted WLS, qualified real input,
successful construction and optimization start, and no critical incompatibility.
A usable incumbent also requires an independent validation receipt.
A rejected license or critical construction/API/validation incompatibility
supports NO-GO for the tested configuration, with the cause stated.
An interrupted or incomplete receipt can leave the decision inconclusive.
No execution means no operational GO/NO-GO yet.

## Status and boundaries

- Read-only source and official documentation review: completed.
- Correct NPAD environment/input preflight: pending operator readback.
- Environment clone and one-dependency change: not performed.
- Real h215 job and license acceptance: not performed.
- Compatibility decision: pending.
- PR merge: not authorized by this preparation.

The methodological plan remains deferred until the two additional mandates
announced by the researcher have been received and reconciled. Its revised
version will be in English EN, with properly typeset mathematics, tables,
figures, editable source and GitHub documentation. Do not change manuscripts
or MVP2.0 results during this migration test.

## Primary sources

- [Gurobi Python installation and supported Python versions](https://support.gurobi.com/hc/en-us/articles/360044290292-How-do-I-install-Gurobi-for-Python)
- [Academic license upgrades, including WLS](https://support.gurobi.com/hc/en-us/articles/360041792251-How-do-I-update-my-academic-license-to-the-latest-Gurobi-version)
- [Gurobi 14 release changes](https://docs.gurobi.com/projects/optimizer/en/14.0/reference/releasenotes/changes.html)
- [Gurobi 14 parameter reference](https://docs.gurobi.com/projects/optimizer/en/14.0/reference/parameters.html)
- [Conda clone/copy options](https://docs.conda.io/projects/conda/en/stable/commands/create.html)
