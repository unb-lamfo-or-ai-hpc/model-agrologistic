# Proposed revision: staged h215 experiments and empirical up-scale selection

**Status: proposal for researcher approval, 24 November 2026.** The official
English EN methodological plan approved earlier today remains unchanged in
`develop` through PR #159, merge `84f4d50e9876afeb83933ce8e235fec970bb53d6`.
This companion specifies replacement passages and tables for its experimental
design, analysis and scheduling sections. It becomes the scientific plan only
after approval. No optimization, job submission or environment change is made.

## Purpose and retained research contract

The revised sequence separates two questions. Stage A asks how greater
investment ceilings change service, economic cost and penalties when no new
service or export policy is imposed. Stage B asks how the approved policy
profiles change those outcomes at the reference investment ceiling. This
sequence is easier to interpret than the earlier full crossing of K and policy
profiles, and reduces the first h215 pass from 72 to 24 distinct cases.

The models remain the native Gurobi 14 DET/W and joint two-stage STO/W extensive
forms, with the existing scalar objective and unchanged economic coefficients
and three penalties. The computational reference is `Method=-1`, `Threads=0`,
and otherwise Gurobi 14 defaults, apart from the approved time control. No seed,
heuristic, MIPGap or concurrent-strategy override is introduced. The retained
historical default-applying helper must not silently reintroduce a fixed seed,
thread count or 1% stopping gap. There is no Benders or GPU arm and no study of
speedup as a function of threads.

## Proposed replacement: the h215 experimental matrix

Stage A uses K in {1, 1.25, 1.50, 2} with beta and alpha disabled in each model.
Stage B evaluates the nine profiles at K=1. Its P0 reference is exactly the
P0/K=1 case from Stage A; neither its first observation nor its planned
repetitions are submitted twice.

| Stage | Profiles | K | DET unique cases | STO unique cases | Total |
|---|---|---|---:|---:|---:|
| A: investment ceiling | P0; beta/alpha disabled | 1, 1.25, 1.50, 2 | 4 | 4 | 8 |
| B: domestic/export policy | P1–P8; P0 reused from A | 1 | 8 | 8 | 16 |
| Combined first pass | Union of A and B | As above | 12 | 12 | 24 |

| Profile | beta: minimum domestic service | alpha: maximum export/supply fraction |
|---|---:|---:|
| P0 | disabled | disabled |
| P1 | 0.90 | disabled |
| P2 | 0.95 | disabled |
| P3 | disabled | 0.60 |
| P4 | disabled | 0.50 |
| P5 | 0.90 | 0.60 |
| P6 | 0.90 | 0.50 |
| P7 | 0.95 | 0.60 |
| P8 | 0.95 | 0.50 |

Beta constrains unmet domestic demand per product and scenario over the full
horizon. Alpha constrains exports relative to exogenous supply over the same
scope; original destination-period limits remain in force. Probabilities weight
the STO objective, not these physical rows. A null control is disabled and does
not mean a zero fraction. The joint STO case still contains nine equiprobable
scenarios and shared first-stage decisions; it is one optimization observation,
not nine independently scheduled models.

K scales the frozen candidate-opening and existing-expansion ceilings once.
For existing sites, the reference 25% expansion allowance becomes 25% x K of
initial static capacity; for candidates, the investible reference capacity is
multiplied by K and initial capacity stays zero. Existing reception/shipping
coupling is retained. Unit BRL/t investment prices multiply tonnes actually
installed, without another K factor. K changes neither unit prices, initial
capacities, penalties nor the separate bulk-handling limit. No aggregate budget
constraint is added.

**Interpretive limit:** this sequential design does not estimate interactions
between K>1 and active alpha/beta profiles. No such combination is generated
automatically. If h215 indicates that joint changes merit investigation, a small
explicit supplementary design should be proposed for approval; up-scale must not
invent an untested combination and attribute it to this matrix.

## Proposed replacement: repetitions and progression

In accordance with slide 26 of the supplied Rev2 presentation, fix only the
initial 24 observations now. Define the repeated cases, contrasts and number of
observations after the initial h215 interpretation and before any follow-up
launch. The first-pass frontier is preliminary. Selection must include matched
reference contrasts and a documented check for first-pass selection bias; do not
repeat only favourable observations and infer general stability from them.

For budget comparison only, three temporal observations of every unique case
would give 72 h215 observations: 24 in Stage A and 48 in Stage B. This balanced
alternative would add 48 observations and remains optional, not a fixed matrix.
Any repeated observations use the same default parameter reference and immutable
inputs. They describe runtime variability and the stability of returned plans;
they are not independent agricultural samples, randomized-seed experiments or
evidence of statistical significance. No repetition or job is authorized here.

Within each pass, use a fixed, recorded A-then-B order, retain DET/STO labels and
record node, allocation, timestamps and contention observations. P0/K=1 serves
as the shared policy reference in every repetition. The first-pass interpretation
is reviewed before proceeding further. Failures and censoring remain in the
case inventory and are never replaced by unrecorded retries.

## Proposed replacement: an empirical cost–service frontier

The frontier contains **validated observed solutions**, not parameter settings
alone. Its two axes are economic cost in BRL, minimized, and domestic service,
maximized. Economic cost includes actual investment, transport and storage under
the model's accounting, excluding the three artificial penalty components.
Domestic service is delivered domestic tonnes divided by required domestic
tonnes. For STO, the aggregate ratio uses probability-weighted delivered tonnes
and probability-weighted demand; it is not an unweighted average of scenario
percentages. Also report each product/scenario ratio and the worst defined ratio.
A zero-demand ratio is undefined and is reported as such.

Keep the full scalar objective and its gap alongside these axes. Also retain
shortage/static/reception penalties and quantities, installed investment tonnes
and BRL, exports and their supply shares, terminal stock, validation status,
incumbent/bound quality, time, Work, nodes and peak memory. A scalar-objective
bound does not certify a gap for economic cost alone.

Build separate DET and STO frontiers because their demand realizations and
objective aggregation differ. Do not rank them together without an approved
common evaluation basis. Within a model, solution a dominates b when its cost is
no greater and its service is no lower, with a strict improvement in at least one
axis beyond the declared numerical/reconstruction tolerances. Derive those
tolerances from the accepted validation and export precision and report them;
do not create a material-service threshold retrospectively to favour a result.

For each observation: verify provenance and terminal accounting; validate the
complete service/export/cost vectors; compute axes; and perform the dominance
comparison. Retain every original observation and label equal points using
solution identities rather than deleting evidence. Exclude unvalidated or
incomplete vectors from the eligible frontier, while keeping their case rows in
the accounting. A time-limited incumbent can be eligible if independently
validated; its censoring and scalar gap remain visible. A run without an
incumbent has no frontier point. Infeasibility is a separate native outcome and
must not be inferred from an absent incumbent.

Plot actual feasible observations and identify their case/repetition. Runtime
medians and ranges can summarize repetitions, but component-wise median costs
and flows must not be presented as a feasible synthetic solution. Compare
frontier membership across repetitions to describe stability. The resulting
frontier is empirical: the scalar-penalty solves do not prove the complete
multiobjective Pareto frontier or global economic optimality.

## Proposed replacement: conditional up-scale

No fixed h300/h400/h500 matrix is admitted now. Once h215 is interpreted, select
observed control triples separately for DET and STO. The main sample should
cover non-dominated low-economic-cost and high-service outcomes and a meaningful
intermediate trade-off when it exists. Prefer stable, independently validated
points and document why each is scientifically representative. Preserve a
matched P0/K=1 reference even if dominated, explicitly as a comparison anchor
outside the selected frontier sample. Count an anchor only once if selected
already.

Evaluate the same selected controls at h300 before deciding whether to advance
to h400 and then h500. Qualification of each population's inputs, graph, native
construction and resource feasibility is required independently. Failure or
time/memory censoring is an outcome and may justify a revised proposal, not an
automatic larger-memory allocation, method change or retry.

Let m(h,DET) and m(h,STO) be the selected unique cases for population h, including
any reference anchor once. With r(h,mode) approved observations per case, the
larger-instance count is the sum of m(h,mode) x r(h,mode). Both m and r remain
unset until the h215 selection review; the preparation catalog contains zero
larger-instance cases. For illustration only, three cases per model/population
and three observations per case would mean 54 larger-instance observations.
This is a budget example, not a preselected sample or authorized queue.

## Proposed replacement: resource budget and schedule

Retain 192 GiB, an eight-hour native limit and at most twelve hours of Slurm wall
time per observation, including construction, export and independent validation.
The latter is a reservation ceiling, not an expected runtime. Keep a single
worker reference; no concurrency or extra licence session is assumed. Record
physical/logical CPUs, SMT, affinity, Gurobi's available-thread limit and observed
use. Automatic Threads=0 is not a measured number of active threads.

| h215 block | Observations | Native-limit hours | Allocation-limit hours | Serial allocation days |
|---|---:|---:|---:|---:|
| A, first pass | 8 | 64 | 96 | 4 |
| B, additional first-pass cases | 16 | 128 | 192 | 8 |
| Combined first pass | 24 | 192 | 288 | 12 |
| Optional: two additional balanced passes | 48 | 384 | 576 | 24 |
| Optional total: three observations/case | 72 | 576 | 864 | 36 |

The optional h215 three-observation ceiling is 165,888 GiB-hours (162 TiB-hours) of
reserved memory. CPU-hours equal the scheduler's actual allocated CPUs times
allocation hours; do not substitute Threads=0 or an unqualified physical-core
count. These ceilings exclude queue delay, public qualification, scientific
review and any separately approved diagnostic run. They are not a claim of
observed consumption or a commitment to occupy an allocation for its full limit.

The illustrative 54-observation larger-instance sample would add 432 native-limit
hours, 648 allocation-limit hours and 27 serial allocation days. Combined with
h215, that would be 126 observations, 1,512 allocation-limit hours and 63 serial
days, still conditional on the selection gates. The previous fixed 96-case
larger-instance matrix and 184-observation combined catalog are withdrawn from
this proposal; neither is a resource request.

Schedule the transition by gates rather than an unsupported calendar promise:

| Gate | Work and exit criterion | Timing basis |
|---|---|---|
| T3.0 | Researcher approves this design/repetition proposal; official plan then updated | No HPC |
| T3.1 | Close T2 provenance review and native alpha/beta/K construction and export/validation checks | Local, solver-free preparation |
| T3.2 | Prepare public qualification and finite claims for separate execution authorization | No job is launched by this proposal |
| H215-A | First-pass capacity-ceiling observations; validate A1–A5 accounting | Up to 4 allocation days, excluding queue |
| H215-B | First-pass policy observations with the shared reference reused | Up to 8 additional allocation days |
| H215-R | Review contrasts and approve repetition scope; balanced example only | Counts and budget still conditional |
| Review | Select model-specific cases and approve a revised larger-instance budget | Before h300 |
| Up-scale | Qualify and evaluate h300, then h400, then h500 | Conditional; no dates or case counts fixed |

This conservative h215 ceiling is longer than a short coauthor-review window.
Initial validated findings can support an interim meeting, but cannot be labelled
a completed repeated campaign. Verify licence validity for the intended window:
the previously supplied NPAD expiry was 9 December 2026 and no extension is
assumed here. No credential is read or licence session opened for this document.

## T3 software and data preparation accompanying the proposal

The source-bound proposal is
`experiments/proposals/mvp3_t3_staged_design_20261124.json`. The pure preparation
module produces the 24 distinct initial cases only,
with `scientific_approval=pending`, `execution_authorized=false` and no job IDs.
It binds the complete proposal hash and both v2 workbook hashes. K uses the
existing scenario multipliers; no independent mathematical formulation is added.
Canonical alpha/beta row specifications are compared to the retained effective
Pyomo algebra without importing Gurobi or optimizing. Integration into the
retained native extensive builder remains pending.

The read-only preflight checks these exact workbook pins:

| Workbook | SHA-256 |
|---|---|
| `agrologistic_effective_baseline_v2.xlsx` | `92698e05b869d67292cf7b080f56b43f7ccc93a27470b2eee559eadbeebd4a3d` |
| `agrologistic_warehouse_registry_v2.xlsx` | `68b9933cc171541b151b7ea60c5d0501d5cecc01675819777af1ffefc11cbe7b` |

Workbook edition 2 retains the computational schema
`agrologistic-effective-baseline-v1`. The effective workbook supplies the
normalized `ModelData` bundle; the registry remains the inspection/membership
reference, not an implicit second source of overrides. The seven normalized
payload hashes, workbook provenance and h215 DET/STO coefficient identities are
verified. This byte-level inspection does not close source/SQLite custody or an
atomic routing snapshot; those remain in Draft PR #164. No workbook is edited.

After approval, replace the official plan's experimental matrix, repetition,
frontier, up-scale and scheduling passages with this reviewed design, regenerate
the English EN PDF and editable package, and preserve the earlier approved
edition as historical evidence. Until then, this new Draft PR contains the
proposed changes only. PR #164 remains Draft and unmerged; no scientific result,
original receipt, environment or HPC campaign is modified.
