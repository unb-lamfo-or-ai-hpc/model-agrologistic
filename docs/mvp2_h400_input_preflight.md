# S1-B: qualify h400 direct-enabled inputs before any optimization

PR #49 is merged into develop at `98658f501a67da83197c67add1da9bf884568e46`.
Its accepted h300 pair closes S1-A, not all of Sprint 1. This next scope admits
**one input-only inspection of one h400 direct-enabled control**, not another
compaction pair. Historical h400 incumbents do not meet the complete hierarchical
quality criterion; this inspection does not change their disposition.

## Fixed question and input contract

Can the current unchanged core and qualified NPAD runtime load the original
h400 direct-enabled workbook and reproduce its reviewed dimensions, routes,
potential interhub connectivity and error-free input audit? The
[dedicated policy](mvp2_h400_input_policy.json) binds the original manifest,
licensed miniature qualification and workbook hashes. It selects exactly one
h400 direct-enabled reference index (5) and derives a single control manifest.
Model and loader policies remain fixed; only output/name/provenance and the
already qualified all-barrier/diagnostic profile are derived. There is no solver
model construction, optimization, fresh license probe or solver memory measurement.

| Property | Reviewed input-only contract |
| --- | --- |
| Population | 400 hubs: 146 existing, 254 candidates |
| Other dimensions | 37 origins, 27 domestic and ten export customers, two products |
| Uncertainty / periods | Nine Cartesian scenarios, sixty periods |
| Selected OD / DC / DD / OC routes | 5,920 / 6,400 / 64,000 / 592 |
| Repair routes | Zero in each family |
| Estimated variables | 42,426,624, including 41,532,480 flow variables |
| Remaining variable families | Inventory 432,000; emergency 432,000; investment 984; unmet 29,160 |
| Potential interhub graph | Strongly connected for each product; 32,000 selected edges each |
| Slurm envelope | intel-256, one task, four CPUs requested, 16 GiB, thirty minutes |
| Solver record only | Gurobi, four threads, seed 42, Method 2 all passes, MIPGap .1, 28,800 s |
| Compact flag | False; no treatment arm |

The reference solver size guard remains **25,000,000**. The exact input snapshot
is inspected even though its estimate exceeds that guard by **17,426,624**;
the receipt explicitly reports `within_reference_limit=false` and
`optimization_allowed=false`. Inspection does not call the solver size admission
or increase any guard. This is neither a general size-limit relaxation nor
acceptance of a future solve. The existing h215/h300 gates and their receipts
remain unchanged and cannot admit h400.

Potential graph connectivity does not establish active-network connectivity,
throughput feasibility or unconditional recourse. Input audit warnings and loader
warning counts remain visible; zero errors does not mean zero warnings. An
estimated variable count is not an actual built matrix. Input MaxRSS cannot
justify a solver allocation or predict its optimization peak.

## Safe executable lifecycle

The versioned [driver](../scripts/npad_mvp2_h400_input.sh) uses the existing Conda
Python at `/home/vrrcelestino/venv313/bin/python`; it does not install or upgrade
dependencies or edit preserved reference data. The PR's maintained comment gives
the full CI-passed source, exact driver SHA-256 and complete start/collect commands.
Use that immutable handoff rather than a moving branch or historical command.

`start FULL_SOURCE_SHA` creates one global durable claim
`.mvp2-h400-input-s1b`, a fresh run and detached checkout. It verifies tracked raw
Git bytes, Ruff and the focused Linux regression gate with no failures/errors/
skips; then rehashes original reference/workbook/qualification, verifies licensed
miniature evidence against the unchanged implementation/runtime and prepares the
single control. No miniature or large optimization is run by this driver.

The submitter accepts only an empty new audit directory and a clean pinned
checkout. It performs `sbatch --test-only`, claims submission before the one real
`sbatch`, validates the parsable job ID and preserves source/tool receipts. It
never creates an array. An ambiguous submission or incomplete claim stops;
do not delete a claim or manually retry to force another submission.

The worker captures the actual running standalone scheduler/node records,
verifies the 16-GiB allocation and checks the pinned plan. It calls only
`inspect_experiment`, exports six named input products and validates the exact
snapshot. It rechecks original identities after loading before acceptance.
Exceptions retain the failing phase and diagnostic; an EXIT trap retains the
worker return code. External termination can prevent a worker receipt, and such
an attempt remains terminal failure evidence rather than accepted inputs.

After submission, Ctrl-C interrupts waiting safely, not the Slurm job. Repeat
the **identical start command** to collect through the original claim; it cannot
submit again. Alternatively:

```bash
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
RUN=$(cat "$BASE/.mvp2-h400-input-s1b/run.txt")
bash "$RUN/source/scripts/npad_mvp2_h400_input.sh" collect "$RUN"
```

Collection waits for exact root-job terminal accounting, then creates a new
`collection-XXXXXXXX/evidence` directory and packages only named plan/campaign,
receipts, scheduler/logs and input products. It prints `COLLECTION_STATUS`,
`SHA256`, `DOWNLOAD`, `TRANSFER_ARCHIVE` and `TRANSFER_CHECKSUM`. Download that
`.tar.gz` and adjacent `.sha256` with MobaXterm and attach both for review.
Failed/preempted/timed-out attempts are packaged too. Rejected completed evidence
does not become an accepted run by exit zero and never triggers resubmission.

## Portable review and acceptance boundary

The [collector/reviewer](../scripts/collect_mvp2_h400_input.py) has no submission
API. Review verifies the archive SHA-256, safe regular members, bounded expansion,
complete allowlisted catalog, source/tool/policy/core identities, exact standalone
allocation, worker and diagnostics, six input hashes and reconstructed semantic
snapshot/size checks. Failures are preserved as failures. Archives contain no
workbook bytes, credentials or checkout. A read-only manual replay is:

```bash
python scripts/collect_mvp2_h400_input.py --archive "$ARCHIVE" \
  --sha256 "$SHA256" --review-output "$NEW_REVIEW_JSON"
```

Portable replay verifies original worker claims. The absent original manifest,
workbook and licensed qualification files are rehashed on NPAD before/after
inspection, **not** locally from missing data. Core source hashes are replayed
locally; original NPAD package/Python identities are retained, not compared to
the reviewer's potentially different runtime. No solution validator runs because
no solution exists. Local synthetic tests and Linux CI qualify the software,
not an unperformed h400 observation.

## What happens after transfer

Keep this PR Draft until the terminal input archive is independently reviewed,
the acceptance/rejection and limitations are documented and final checks pass.
Then Ready for review and request separate merge authorization. No NPAD solve
command is qualified by this PR.

After accepted inputs and integration, prepare a **separate S1-B solve gate** for
one instrumented h400 direct-enabled control. Decide exact size exception,
allocation/cgroup/license, finite budgets, source/data fingerprints, three-stage
quality audit, independent validation and complete terminal telemetry before
requesting another CLI execution. Current inputs, if accepted, are necessary but
not sufficient. If memory/time admission cannot be defended, record that limit
and stop rather than launch a campaign. S1-C then reconciles Sprint 1 exit items;
thread screening stays in S2. No manuscript/MVP1 edits or EVPI/VSS removal occur
here; the latter editorial change remains S6.
