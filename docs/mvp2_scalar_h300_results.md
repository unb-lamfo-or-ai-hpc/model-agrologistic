# Scalar h300: complete accepted block and interpretation

21 October 2026. This is the terminal continuation of
[PR119](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/pull/119), not a
repeat, new solve or rewrite of its original certificates. The supplied archive
and sidecar agree with an independently computed SHA256:
`dc5969fa391dc81590210ef7e6f89abbb5df554e4bc5b2032ba9eafe1a67f3fc`.
Compressed size25,801,229 bytes;274 regular members;572,030,788 expanded bytes,
below the approved1GiB envelope. No private workbook or license is committed.

The [redacted machine-readable review](evidence/scalar_h300_2218193_review.json)
reproduces the existing portable verifier's `block_quality_target_met`, closed
operational receipts and all five original accepted residual certificates. The
supplementary [read-only reviewer](../scripts/review_scalar_h300_evidence.py)
streams bounded members, checks inventory, invokes that SAME original verifier,
then checks cost/gap/service arithmetic, quantities/units and common membership.
It neither reloads private inputs nor recomputes mathematical residuals afresh.

## What completed

- Job2218193, source `04ba9edccc93f40ab36cbc3264039a7edf2f6f51`.
- Plan `000a760b3c263cfd7e88fb75714ac5f125df9c4e27332045c761a75bd60bffb1`.
- Root/batch/extern plus numeric steps0–4: COMPLETED,0:0. Whole allocation5h51m36s,
  against the approved30h reservation; each native call below14400s.
- Five cold STO observations, execution order4/1/8/2/16, no unrun/rejected arm.
- Three hundred included warehouses:146 existing plus154 candidates, including
  the69 canonical anchors and85 additional frozen-ranked candidates. Exact lists,
  order, selection criterion/seed and original hashes remain in each attempt.
- Nine equiprobable Cartesian scenarios,60 periods, no direct origin/customer
  arcs, compaction off, gap target0.01,Seed42,SoftMemLimit160 decimal GB.

The source hook checks effective native Threads/TimeLimit/MIPGap/Seed/SoftMemLimit
before optimization; original runtime/phase/native-terminal receipts and actual
completion are consistent with the requested thread levels. Same worker affinity
pool:16 logical CPUs across12 observed physical cores, with SMT siblings. This
is neither16 physical cores nor disabled SMT. Each Slurm step allocated24 logical
CPUs; solver threads, affinity and allocated resources are different scopes.
Python3.13.15/Gurobi13.0.3 and CPU model Intel Xeon E5-2698v3 are preserved.

## Comparable observations, not a causal ranking

| Gurobi threads | Native Runtime (min) | Model build (min) | Application end-to-end (min) | Sampled application peak RSS (GiB) |
| ---: | ---: | ---: | ---: | ---: |
|1 |47.14 |7.19 |57.09 |46.35 |
|2 |53.01 |7.19 |63.07 |57.24 |
|4 |58.89 |6.96 |68.60 |77.96 |
|8 |67.45 |7.32 |77.72 |78.21 |
|16 |67.61 |7.30 |77.59 |78.37 |

Table order aids reading; it is not execution order. Native Runtime is the
original solver-reported duration, not allocation or build time. Application
end-to-end excludes earlier staging/preflight and later controller review; the
approximately microsecond `data_read_seconds` fields reflect already-loaded
input at that layer, NOT large-workbook ETL cost. Preserve original scopes.
Slurm step MaxRSS ranges45.62–77.51GiB and is separate from sampled application
RSS. Native-memory samples are a third scope, not total process RSS. Resource
receipts have zero dropped samples and no recorded inspection errors, but
sampling does not guarantee the true instantaneous peak. Sampler work is
recorded, not silently removed from phase wall times or treated as CPU time.

All five original objectives and bounds coincide:

- Penalized objective9,289,108,634,158.756; bound9,288,725,982,804.533.
- Native/common gap0.000041193549272912564, or **0.0041193549%**, below1%.
- Economic subtotal385,502,284,842.871; artificial penalties8,903,606,349,315.89.
- Every original residual validator accepted at absolute1e-5/relative1e-8,
  with zero failed checks. `optimal` retains this nonzero gap; not exact optimality.

The flow, inventory, unmet-demand and warehouse-decision CSVs are byte-identical
across all arms. This supports the SAME exported decision vectors in this block,
not uniqueness of the mathematical optimum or universal thread behavior.
The original matrix has25,107,544 variables (392 binary, included in integer
count),890,642 linear constraints,94,635,126 nonzeros and166,320 general
constraints. Presolve-log observations retain22,375,717 variables/839,812
constraints/85,548,653 nonzeros. Sampled maxima include3,314,428 iterations and
zero nodes; these sampled values are not a complete search transcript.

One thread was fastest and least memory-intensive OBSERVED here. Fixed serial
order, shared-node load, nonexclusive allocation, SMT and one observation per
level prevent a causal speedup/efficiency or universal ranking claim. Use one
thread as a separately reviewed h400 CANDIDATE, not an automatic selected setting.
Do not compare these times as scalar speedup over the archived hierarchy.

## Required penalty-effects discussion

Coefficients remain90000 unmet/45000 static/45000 reception, in their original
units. Domestic service is91.32562288%, scenario range89.42854906–93.93998926%.
The probability-weighted horizon quantities are58,787,331.5889 unmet tonnes,
46,444,009.1737 stock tonne-periods of emergency storage, and33,839,246.5222
overflow tonnes in periods. These are neither unweighted nine-scenario sums,
unique installed emergency capacity nor observed financial losses.

Artificial penalties represent95.84995396% of the reconstructed total. They
relax ONLY the stated demand/storage/reception equations; other hard constraints
remain. Accepted feasibility means the slack-enabled model is feasible, not full
service or no-slack feasibility. Positive slack is not a new rejection condition.
The low gap concerns penalized total, not a1%-accurate economic subtotal or a
service guarantee. Preserve every cost component, service and physical slack.
No calibration or implicit penalty increase is introduced.

Slacks enlarge the feasible set and add variables/interactions. They may aid
incumbent discovery, but their coefficients/observed magnitude do not establish
a monotonic runtime effect or prove that slack caused fast convergence. This
block demonstrates successful large scalar computation under the approved
trade-off, with explicit limits on its agricultural interpretation.

## Preserved boundary and next step

Keep `.mvp2-scalar-h300-30h-v1`, original source/run/archives, bootstrap
`scalar-h300-30h-driver-7VpKV8oU` (now identified by the bound plan), all older
claims and both failed pre-submission bootstraps unchanged. The source/plan in
this report are the ORIGINAL execution identities, not this review's new commit.
Original false execution/repeat/follow-on/selection flags remain false. All
scientific `src` and manuscript files are unchanged by this consolidation.

The [h400 proposal](mvp2_scalar_h400_proposal.md) is the next decision package.
No new job, repeat, h500 admission or automatic transition follows this success.
PR120 stays draft awaiting other coauthors and the maintainer's editorial return;
this results PR must not merge or edit that independent working branch.

To reproduce this documentary review locally (no solver, scheduler or extraction):

```bash
python -B -m scripts.review_scalar_h300_evidence \
  --archive /absolute/path/scalar-h300-30h-evidence.tar.gz \
  --sha256 dc5969fa391dc81590210ef7e6f89abbb5df554e4bc5b2032ba9eafe1a67f3fc \
  --output /absolute/path/NEW-review.json
```

Output creation is exclusive. Never overwrite original evidence to run a review.

## Qualification of the consolidation package

Local Python3.13.15:31 focused and193 related tests passed, zero failures/errors/
skips; Ruff and changed-document relative links passed. The stored redacted JSON
equals a second complete external replay of the transferred archive. Source/plan/
job bindings were separately checked against the original human handoff. The
scientific src tree666029ace80bd60417d91c43d4460a33326acf64 and manuscript tree
c33c6dbdb829580d1d0c8c9296814b1b7a38280b are unchanged from develop.

Initial local testing exposed missing synthetic accounting fields and sandbox
temporary-directory setup errors. The public fixture was corrected and explicit
workspace basetemp used; original scientific validation was not relaxed. Full
exact-head Linux native/SCIP/analytical and lint/distribution CI must pass before
Ready. The PR's final qualification comment records the exact head/run identities
and observed test counts. Tiny native CI is software qualification, not a new
NPAD or agricultural h400 experiment. No local license or solver is accessed by
the external receipt review. Historical resource budgets remain unchanged.
