# PR #25: mathematical contract and four-level validation report

Status (2026-09-13): **levels 1-3 accepted in the latest supplied NPAD report;
level 4 remains pending and the overall report is rejected**. Nine references
are accepted. The warehouse-only nine-scenario retry stopped at Gurobi's
soft-memory limit; its incomplete objective hierarchy is not accepted.
Read the [dual/four-thread retry runbook](pr25_warehouse_dual_retry.md) before submitting
anything; do not repeat the nine accepted runs or the licensed quality suite.
This report supersedes the earlier claim that reception slack needed another
30-day multiplier. It does not supersede or modify the archived v0.1.0 evidence.

## Executive conclusion

### Latest result: the larger-memory attempt also stopped

The report `report-memory128-20260913T171425Z/v020_validation_report.json`
confirms nine accepted references and one rejected warehouse-only nine-scenario
run. Levels 1–3 are accepted, level 4 is pending, and overall status is rejected.
Job 2089838 used a 192 GiB allocation but reached Gurobi's 128 decimal GB soft
limit after 12650.56 optimization seconds; it explored 16 nodes and retained
economic incumbent 764469455725.4, bound 410003580551.1, gap 46.3676%.
MaxRSS was 116192580 KiB (approximately 110.8 GiB). The only failed run check
remains `three_completed_passes`; no local residual, cost, service or provenance
failure was reported. The allocation itself did not report a Slurm OOM kill.

The next bounded numerical experiment explicitly sets `Method=1` (dual simplex
for the root relaxation) and `Threads=4`, keeping SoftMemLimit=128, Slurm memory
192 GiB, 14400 seconds and every mathematical/acceptance setting unchanged.
This jointly changes algorithm and parallelism, not the mathematical model;
runtime differences cannot be attributed to one change alone. Neither lower
memory usage nor successful convergence is presumed. The previous plan and
both partial runs remain archived. The final plan still preserves exactly nine
accepted references. No `src/logic` or dependency change is made.

### Historical resource-only attempt (superseded for execution)

The supplied tail of `slurm-pr25-nine-retry-2088823_0.out` explicitly reports
`Memory limit reached` after 11393.77 optimization seconds. The final displayed
economic incumbent is 764469455725.4, with bound 409973108225.9 and gap 46.3716%.
The run assessor accepts the contract, independent residuals/costs, network and
penalties, incumbent, per-scenario domestic service, service certification,
final-stage values, timing and HPC identity; only `three_completed_passes`
fails. This is not evidence of infeasibility or a Slurm out-of-memory kill.
Slurm exit 1 is consistent with post-solve rejection of the incomplete hierarchy.

The next execution changes only `SoftMemLimit` from 56 to 128 decimal GB,
requests 192 GiB from Slurm, and preserves 16 threads, 14400 seconds, all
tolerances and mathematical settings. A new run identity and output root
preserve the partial evidence. Nine accepted references retain their exact
specifications and paths; the preceding plan is archived as
`experiments/v020_validation_reference_t14400.yaml`.

No optimization/validation implementation source or dependency is changed.
The approved implementation/runtime receipt remains applicable if its hash
still matches; new orchestration tests are verified separately. More memory
does not guarantee convergence within the time budget. The final four-level
report is still required. PRs #26 and #27 are frozen by maintainer instruction.

The two bounded implementation commits add a frozen mathematical contract and
an independent solution checker. Their purpose is to make incorrect results
detectable and to qualify scientific claims, not to guarantee zero emergency
use or to manufacture a numerical match with Artur's published tables.

The first commit is `58e5f49c74e2dba166ce4542f33486ec4681928c`.
Its GitHub Quality workflow passed:
[run 34651985438](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/actions/runs/34651985438).
The second commit contains this report and the executable validation protocol.
Final CI and NPAD receipts are recorded in the PR conversation without rewriting
the immutable execution artifacts.

## Level 1 — mathematical and data contract

Implemented and covered by analytical regression tests:

- Reception capacity enters a period constraint as daily nominal capacity
  multiplied by operating days, followed by **period overflow in tonnes**.
  The overflow must not be multiplied by operating days again. Its daily
  equivalent is overflow divided by days, only for reporting.
- Static emergency quantities are stock exceedances indexed by warehouse and
  period. Their sum over time is not installed capacity. The secondary policy
  objective is an explicitly chosen equal-weight violation score combining
  different operational mechanisms, not a physical construction target.
- Historical shared slack and approved separate slacks are distinguished:
  for fixed exceedances `a` and `b`, a common penalty rate gives
  `P * max(a, b)` versus `P * (a + b)`. This extension is not numerically neutral.
- Dynamic unmet-demand penalties use the selected network, not discarded long
  routes. The selected OD/DC/DD/OC sets, connectivity repairs and penalty vector
  are frozen before RP, EV, WS or EEV projections. Hashes and the actual penalty
  vector are exported. Different configurations can still have different
  dynamic penalties; cross-configuration penalized costs need that qualification.
- Only the implemented free-terminal-inventory policy is accepted. Unsupported
  zero, target and penalized options fail before optimization rather than being
  silently ignored.
- Candidate opening, investment eligibility, expansion/bulkification exclusion,
  supply conservation and export upper bounds are retained. No new slack family
  or route-expansion experiment was introduced.
- Bulkification's daily coupling factor has units `1/day` when the investment
  decision and cost basis are tonnes. Under `daily_factors`, bulkification does
  not automatically increase static capacity.

**Qualification:** the model does not have unconditional complete recourse.
Shipping remains hard, candidates require activation, and all supply requires
an allowed outlet. Emergency use is a diagnostic finding, not a rejection rule.

## Level 2 — software verification

The local Python 3.13 suite and distribution build are run through
`scripts/run_validation_suite.py`. The receipt binds the checks to normalized
implementation source and relevant runtime versions, retaining command logs
and JUnit results. A final certificate rejects a receipt with skipped tests.

New tests cover:

- 28-, 30- and 31-day capacity conversions;
- both deterministic and stochastic Gurobi formulations on small analytical instances;
- non-equivalence of common and separate penalty slacks;
- frozen route/penalty semantics across scenario projections;
- local residuals that cancel in aggregate but still must be rejected;
- negative/nonfinite, duplicate and unknown-index records;
- candidate activation, disabled slacks, shipping, static and reception limits;
- independent transport, inventory, investment and penalty cost reconstruction;
- probability-weighted recourse with first-stage investment charged once;
- stale or corrupted artifact exclusion and objective-bound consistency;
- four-level acceptance remaining pending when required evidence is missing.

Local Gurobi is installed, but the available license is expired. Licensed tests
are therefore explicitly skipped locally. This is not recorded as an NPAD pass.
Final local receipt (2026-09-11): **280 passed, 49 skipped, 4 warnings**, in
59.44 seconds; Ruff and distribution build both passed. The executable
four-level report returned `pending`, as required without current NPAD evidence.
The implementation/runtime fingerprint was
`c34d41e9856bc9d23eff3787ef8ffac9c033f6e4552dc2ca4d720d4f5b195313`.
The PR conversation records the corresponding remote commit and CI results.

## Level 3 — independent mathematical solution validation

`src/logic/solution_validation.py` imports neither Gurobi expressions nor the
optimization model's capacity/cost helpers. It reconstructs the following from
canonical input and sparse structured solution records:

| Family | Independent check |
|---|---|
| Input/output indexing | Scenario, route, product, period and node membership; duplicate records |
| Supply | All origin/product/period equalities, including zero supply |
| Inventory | Warehouse/product/period recurrence, including initial inventory and DD inflow/outflow |
| Domestic demand | Delivered volume plus shortage equals input demand, including zero demand |
| Export | Deliveries do not exceed the declared market upper bound |
| Capacity | Static stock, period reception overflow and hard period shipping constraints |
| Investment | Binary/activation/bound/eligibility checks and expansion-bulkification exclusion |
| Stochastic structure | Probability sum and nonnegative weights; one shared first-stage decision set |
| Costs | All 14 monetary components reconstructed; investments counted once, recourse weighted once |
| Value analysis | RP/EV/EEV/each WS validated; EEV decisions compared with the EV plan |

The default local residual tolerance is `1e-5 + 1e-8 * max(abs(lhs), abs(rhs))`.
Cost checks additionally disclose a conservative coefficient-based error budget
for the native sparse export threshold of `1e-7`. Investment records are dense
and receive no sparse-export allowance. The checker reports every family count,
maximum residual and a bounded failure sample. Passing means consistency within
the disclosed tolerances, not exact arithmetic or proof of global optimality.

Service denominators in this independent report come from input demand, not
from adding served and unmet quantities extracted from the solution. Legacy
summary columns remain available; the independent report is the new acceptance
authority. A retrospective audit writes `independent_validation_reaudit.json`
without upgrading the provenance of the original solve.

Classical EVPI/VSS remains restricted to the common scalar penalty objective.
Nonfinite bounds are unavailable; materially reversed minimization bounds are
rejected. An interval crossing zero remains numerically indeterminate, not a
certified positive value. Big-M-dominated values are not calibrated monetary
benefits. Lexicographic policy runs do not receive classical EVPI/VSS labels.

## Level 4 — HPC execution and scientific evidence

Implemented controls, awaiting final NPAD receipts:

- Run fingerprints include workbook/configuration and normalized implementation
  plus runtime versions. Value-analysis checkpoint fingerprints additionally
  bind canonical data, selected graph and penalties.
- A completion marker is written last with artifact checksums. Manifest-aware
  CLI aggregation excludes interrupted, altered and old-contract outputs, writes
  `aggregation_audit.json`, and never deletes excluded evidence. The legacy
  Python aggregation API without a manifest is retrospective, not certification.
- Timings distinguish data reading, model construction, measured `optimize()`
  wall time, solver-reported runtime, result extraction, independent validation,
  bulk artifact export and end-to-end time. The latter excludes final metadata
  refresh and checksum bookkeeping. Nested timers must not be added twice.
  Backend model-build time excludes the runner's initial frozen-network
  preparation, which remains included in end-to-end time. These timers are
  observational regions, not an exhaustive additive partition of wall time.
- Post-optimality time starts after RP and covers EV/EEV/WS plus analysis.
  Original component timings and current solve/restore durations are separate;
  `value_analysis_timings.csv` makes this distinction inspectable.
- Lexicographic pass-end values and final-incumbent values are both retained.
  Configured MIPGap/MIPGapAbs and objective tolerances are exported. The
  inherited MIP base follows Gurobi's documented rule; `ObjNRelTol=0` alone
  does not impose an exact lock on the earlier incumbent. LP-only semantics
  must not be inferred from this MIP diagnostic.
- Slurm job/array/task IDs, partition, CPU/memory requests and process-lifetime
  peak-RSS scope are reported. A submission-supplied source commit is labeled
  as a declaration; implementation content hashes remain independently computed.

The reference plan is `experiments/v020_validation_reference.yaml`: four
alpha=0.8 thesis-method cases, two service-first deterministic cases and four
three-/nine-scenario policy cases, at 215 warehouses and the 20% topology.
This is a bounded reference scope, not all six historical configurations, a
500-warehouse solve certificate or a definitive scalability frontier.

The executable report cannot be accepted until all selected current-contract
artifacts, licensed quality checks, local residuals, service requirements,
stage evidence and timing/provenance checks are present. Emergency use does
not block acceptance. Missing reference runs remain pending; the archived
v0.1 certificate is never substituted for them.

## Final NPAD validation

The commands in this section describe the initial protocol bootstrap. That
quality gate has now passed on NPAD with zero skipped tests. The next action
is only the [two-run, 14400-second retry](pr25_nine_scenario_retry.md).
The default reference plan now retains eight unchanged accepted references and
selects the two explicitly named retries. The old selection is preserved in
`experiments/v020_validation_reference_t3600.yaml` for historical inspection.

Run from `/home/vrrcelestino/model-agrologistic`, in the established conda
environment `/home/vrrcelestino/venv313`. Do not paste Markdown fence markers
into the terminal and do not execute these commands from quarantine directories.

```bash
cd /home/vrrcelestino/model-agrologistic
conda activate /home/vrrcelestino/venv313
git fetch origin
git switch feature/v0.2-mathematical-reformulation
git pull --ff-only origin feature/v0.2-mathematical-reformulation
export PYTHONNOUSERSITE=1
export PYTHONDONTWRITEBYTECODE=1
export GRB_LICENSE_FILE=/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic
export AGROLOGISTIC_SOURCE_COMMIT="$(git rev-parse HEAD)"
python scripts/run_validation_suite.py \
  --output-dir data/results/validation/pr25-final/quality
```

First inspect `quality_report.json`: zero failed commands and zero skipped
licensed tests are required. Only then run the selected references via Slurm,
using the manifests and indices in the reference plan and its **new** output
directories. For example, the first small reference is:

```bash
python scripts/run_batch_hpc.py \
  experiments/v020_thesis_compatible.yaml \
  --index 0 --output-dir data/results/validation/pr25-final/thesis
```

Do not change Slurm memory requests as a substitute for changing Gurobi's
SoftMemLimit, nor the scheduler wall limit as a substitute for solver TimeLimit.
Large policy references belong on compute nodes; do not submit them merely to
check the quality receipt. Preserve all historical result directories.

After the planned references are available:

```bash
python scripts/validate_v020_evidence.py \
  --quality-report data/results/validation/pr25-final/quality/quality_report.json \
  --output-dir data/results/validation/pr25-final/report
```

The command returns nonzero for pending/rejected evidence but does not close
the parent interactive shell. It never starts a solver or silently fills gaps.

## Publication boundaries and next work

Exact reproduction of Artur's numerical tables is **not established**. The
pinned source supports a methodological comparison, but the historical OSM
snapshot and forecasting path are not reconstructed and separate slacks change
the penalty objective. Report bounded method-compatible results separately
from the policy extension. Extreme DynCap/Turnover under emergency use are not
proof of nominal-network efficiency; DD handling and the nominal denominator
must remain visible in figure/table captions.

No v0.2 merge or release certification follows from code review alone. After
the bounded NPAD gate: freeze the accepted run set for tables/plots, complete
PR #26's English-only documentation/comment review, and draft PR #27's Quarto
Manuscript using `cvictorr2508/quarto-sbc`. Networks above 500 warehouses, SCIP,
the full 15/20/25% campaign and the definitive 14,400-second scalability frontier
remain outside the MVP critical path.
