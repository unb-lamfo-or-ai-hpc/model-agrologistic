# Paired Gurobi–HiGHS scaling campaign

Public software qualification closed on 1 November 2026 at source c493be8c:
all 111 controls passed without skips, errors or failures. Job 2231201 and its
owned step ended COMPLETED/0:0. See
[the original-receipt review](../evidence/pyomo_scaling_public_2231201.json).
This does not submit or qualify a private population. Merge approval and the
progressive private pilots remain separate gates.

This prospective protocol uses the same bounded Pyomo scalar extensive form
for both solvers. It prepares90 fresh observations: two solvers, three warehouse
populations, five thread ceilings and three temporal repetitions. Original
native observations and the h215 observations remain separate reference cohorts.
No result of this new campaign is claimed here.

The preserved h215 inventory does not contain two-solver coverage of all four
W/D DET/STO configurations: native Gurobi covers all four, but the accepted
HiGHS and common-Pyomo Gurobi observations cover W/STO only. Additional h215
descriptive observations are outside these90cells and require their own
operational admission. The existing native h300 five-level observations and
h400/h500 one-thread observations used14400native seconds; none silently
counts as a new28800-second paired-Pyomo repetition.

## Scientific comparison

The frozen populations are h300, h400 and h500, warehouse-only, stochastic,
two products,60periods and nine equiprobable Cartesian scenarios. Each original
processed workbook fixes warehouse identities, all OSRM distance values and
eligible road pairs. The unchanged loader/model contract reapplies the same
screening rules. Nested warehouse sets do not imply nested screened arc sets.
The new input certificate must match the original membership, mathematical
contract and scenario-probability digests in
[the original-input ledger](../../experiments/pyomo_scaling_original_inputs.json).
It stops on drift rather than regenerating workbooks or routes.

Both adapters receive the same ordered linear matrix and the proved
bounded_scalar_slacks_v1 representatives. Record the matrix and bound identities
for every run; a population's four pilots must agree. Physical/investment
projection and optimal scalar-value equivalence do not imply identical native
presolved matrices, relaxations or search trajectories. Penalties remain
90000 for unmet demand and45000 for each emergency-capacity family, with the
original units and independent absolute1e-5/relative1e-8 validation tolerances.
Financial costs and penalized totals remain distinct.

## Solver settings

| Item | Gurobi/APPSI | HiGHS/APPSI |
|---|---|---|
| Installed versions | Pyomo6.10.1/Gurobi13.0.3 | Pyomo6.10.1/HiGHS1.15.1 |
| Native budget |28800s |28800s |
| Relative-gap target |0.01 |0.01 |
| Thread ceilings |1,2,4,8,16 |1,2,4,8,16 |
| Native seed | Seed=42 | random_seed=42 |
| Feasibility/integrality | FeasibilityTol=IntFeasTol=1e-9 | mip_feasibility_tolerance=1e-9 |
| Search strategy | Method/NodeMethod/Presolve/Cuts remain automatic(-1); Heuristics0.05; ConcurrentMIP1 | parallel=on; other algorithm choices retain version defaults |
| Warm start/fallback/tuning | None | None |

Gurobi still chooses its native presolve, LP methods and heuristics through
APPSI; Pyomo supplies a model, not a replacement optimizer. This is **automatic
algorithm selection with explicit resource, stopping, seed and tolerance
overrides**, rather than an all-default run. Native in-process introspection
must match the documented effective options. The original native Gurobi builder
does not participate in the primary paired comparison.

HiGHS1.15.1 supports the requested16-thread ceiling. The
[versioned parallelism guide](https://github.com/ERGO-Code/HiGHS/blob/v1.15.1/docs/src/parallel.md)
requires parallel=on for parallel tree exploration; the
[release notes](https://github.com/ERGO-Code/HiGHS/releases/tag/v1.15.1)
explain that parallel simplex is disabled for MIP LP relaxations. Configured
threads therefore do not prove simultaneous utilization or predict speedup.
Retain logs and phase-level CPU/RSS observations. A root-LP-dominated run can
benefit little from additional search workers. The old h215 four-thread
parallel-search-off observation is not relabeled as a parallel-search run.

Seed42 controls each solver's own pseudorandom choices, not a shared initial
incumbent. Fixed seeds and fresh processes do not guarantee identical elapsed
times, parallel trajectories or incumbents. The three runs are temporal
repetitions conditional on a fixed seed. A separate scheduling seed42031
provides a balanced proposed order. Manual deviations are possible and the
planned and actual submission indices are retained; do not describe an altered
order as enforced randomization. Repetitions should span job/day blocks.

## Progressive admission and memory

1. Qualify the new exact source on a public16-logical-CPU NPAD job. All111
   selected controls must pass with no errors, failures or skips. They include
   cold native probes at all five ceilings, public objective/residual/matrix
   controls, lifecycle collection and adverse operational tests. A fresh public
   Gurobi default-environment capacity probe precedes them. No private input is
   built by this job. Local qualification does not replace this gate.
2. Initialize one new campaign from that immutable qualified source. Verify all
   three original workbooks/materialization audits, population/order files,
   runtime package bytes (including optional highspy-extras), tools and source.
3. Admit four h300 pilots: Gurobi/HiGHS at1and16threads, repetition1. Each has
   its own immutable run claim, plan, job and collection. At most two campaign
   jobs may be queued/running concurrently. Existing or uncertain claims are
   never automatically resubmitted.
4. Only closed pilots with timely observations and sampled worker-tree RSS
   at or below80% of the192GiB envelope admit the remaining h300 cells and
   h400 pilots. Matrix/bound identities and CPU/SMT class must agree. Apply
   the same gate from h400 to h500 and before each population's remaining cells.
5. These are measured qualification gates, **not memory extrapolation or
   guaranteed feasibility**. A clean native time limit without an incumbent is
   a recorded censored observation and can supply resource evidence; an
   interrupted/OOM/invalid-incumbent run cannot open the next gate. A numerical
   difficulty is not silently converted into an operational failure or dropped.

The four pilots are part of the90 only under this same frozen protocol/source
and resource profile. Any repair or resource-profile change needs a new
qualified namespace and explicit accounting of which results remain comparable.
The current192GiB profile is provisional until actual population pilots;
h500 native memory observations do not qualify Pyomo or16threads. There is
no automatic512GiB allocation or hidden guard increase.

## Time, ownership and collection

Each human start submits exactly one12h Slurm job: one node, exclusive request,
24logical CPUs requested, a common16-logical-CPU worker pool,192GiB,
intel-256/preempt/sxdsouza, no requeue. Exclusive allocation may report more
CPUs than requested; record actual allocation separately. A test-only scheduler
admission precedes claim creation. Actual exclusive-node policy and resource
availability must be confirmed on NPAD. If rejected, stop for a reviewed profile.
No extra memory/node/partition is selected automatically.

The11h worker ledger contains2h input/build/identity/transfer,8h native,
30min shared late-return/extraction/export and30min validation. Setup/cleanup
has30min and job contingency30min. Native optimization never receives a reset
or extension from unused Slurm time. Record separate native, construction,
ordered-matrix, transfer, extraction, validation, export and end-to-end clocks;
do not sum overlapping counters. CPU topology distinguishes logical CPUs,
physical cores and SMT siblings; process sampling remains an observed scope,
not production-isolation certification.

The cold minimal bootstrap publishes identity before site imports. Only the
proven owned numeric Slurm step is released or signaled by the supervisor.
Collection requires terminal accounting, reconstructs product hashes and
original validation, and preserves successful, time-censored and forensic
outcomes. Large products are streamed into an archive with a4GiB expanded
limit and4096-member cap; structured JSON parsing has an explicit1GiB cap.
No truncation, input workbook, database, license or native scratch is archived.
An incomplete previous collection is preserved for separate recovery, never
overwritten. Downloads use MobaXterm; raw packages remain local and are not
committed to GitHub. Collection is idempotent only after its complete checksum
and marker exist. Keep the entire claim if interruption leaves partial files.

## Analysis and delivery

The tables action writes all90 planned configurations and all outcomes,
including unstarted, uncollected and failed cells. Missing incumbent/objective/
gap values stay missing. Preserve attained gaps: native optimal means the
solver's configured tolerance, not exact zero gap. Report the common gap,
native gap, objective/bound, original validation, financial subtotal,
penalized total, native/full clocks, RSS scope, hardware and source identity.

Use the three temporal observations, median and range for each cell. Timeouts
are right-censored; do not treat failed/unfinished runs as completed-work
speedups or average them as zero. Statistical intervals are exploratory with
n=3. The90records are not90independent benchmark instances: there are three
related networks. Strong algorithmic-randomness claims require a separately
agreed multi-seed design.

The native upper budget is720hours. At12h envelopes, one serial lane could
require45days and two22.5days, excluding queues and interruptions. Early
returns can shorten this;30days is a scheduling objective, not a guarantee.
Individual12h jobs give clearer ownership than packing six8h solves into48h
without time for construction and export. No autonomous dispatcher is enabled.

## Sprint and PR continuation

| Workstream | Deliverable and exit |
|---|---|
| Current S6-A/X3, PR142 | Consolidate completed h215 evidence and preserve all originals; historical comparisons retain their distinct interfaces/settings |
| Current operational PR | Public NPAD qualification, source/CI review, explicit merge; then human starts of h300 pilots and progressive h400/h500 admission |
| S6-B/B3/D2, PR144, in parallel | Literature reconciliation, reader-oriented methodology/AppendicesC–E, maps, rights/access and pending author decisions; local revised article and supplement PDFs in Codex after review |
| Staged publication PR | After launch and editorial/evidence acceptance, separately approved develop/main reconciliation and Quarto/Pages publication of completed findings plus a dated, clearly prospective/ongoing campaign protocol |
| Final campaign consolidation PR | Audit all new archives, comparative configuration/outcome tables and qualified inference, then its own merge decision |

Neither this PR nor a public qualification submits a private campaign by
itself. Every merge requires the researcher's approval. Every NPAD command is
executed manually by the researcher. Preparation, observation, numerical quality
and publication are separate gates.

## Human CLI after the qualified merge

The public entry point is scripts/npad_pyomo_scaling_public.sh. Invoke it once
with the full reviewed source commit after checking its separately supplied
SHA-256. It downloads exact source, prepares only public controls and submits
one short job. If its claim already exists, collect its original result rather
than invoking it again. Send result.json, the printed scheduler status and the
hashes of plan.json, result.json, qualification.xml and license-capability.json.
The source remains under that public claim; no shared checkout is edited.

Private commands below describe the reviewed interface. They are **not a private
release before accepted public NPAD qualification and the authorized merge**.
Replace FULL_QUALIFIED_COMMIT with the exact40-character commit selected in
that handoff, never develop/latest:

```bash
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
PY=/home/vrrcelestino/venv313/bin/python
SOURCE_SHA=FULL_QUALIFIED_COMMIT
DRIVER="$BASE/.mvp2-pyomo-scaling-public-v1/source/scripts/pyomo_scaling_campaign.py"
CAMPAIGN="$BASE/.mvp2-pyomo-scaling-native8h-v1"

# Read existing metadata/hashes; no solver, scheduler or files created.
"$PY" -B -I "$DRIVER" inventory --directory "$CAMPAIGN" --source-sha "$SOURCE_SHA"
# One fresh campaign, no job; fails on any missing/different original input.
"$PY" -B -I "$DRIVER" init --directory "$CAMPAIGN" --source-sha "$SOURCE_SHA"
# Read the proposed eligible order; no automatic start.
"$PY" -B -I "$DRIVER" status --directory "$CAMPAIGN" --source-sha "$SOURCE_SHA"
# Example ONE pilot. Use only a fresh eligible cell printed by status.
CELL=h300-w-sto-gurobi-t1-r1
"$PY" -B -I "$DRIVER" start --directory "$CAMPAIGN" --source-sha "$SOURCE_SHA" \
  --cell "$CELL" --acknowledge-one-cell
# Only after that original job is terminal; never repeat start.
"$PY" -B -I "$DRIVER" collect --directory "$CAMPAIGN/$CELL" --source-sha "$SOURCE_SHA"
# Fresh table directory each time; no overwriting a previous table snapshot.
"$PY" -B -I "$DRIVER" tables --directory "$CAMPAIGN" --source-sha "$SOURCE_SHA" \
  --output "$CAMPAIGN/tables-v1"
```

All writes stay in model-agrologistic directories below the audit base. Default
input paths are the original data/processed/nine_population_osrm_v1 and
warehouse_population_v020 directories in the existing read-only input checkout.
A separately supplied --inputs JSON may relocate those same immutable files;
it cannot replace their hashes. Failed admission, uncertain submission,
incomplete collection, sparse sampling or a changed profile requires review;
do not remove locks/claims to force continuation. Record original scheduler
messages and retain packages. No command silently retries a solver or promotes
the next population.
