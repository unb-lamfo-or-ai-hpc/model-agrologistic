# Single h300 warehouse-only control baseline

## Scope and evidence boundary

PR #47 qualified **inputs only** and was merged into `develop` at
`1184c43b71682d7325b9d9b76da02691c9ced9e1`. Its accepted job `2198085`
used source `3957f84ff49ac500eecf25b85e6b710b4b3b1010` and produced the archive
SHA-256 `97395d29b802e558d3ac88db8c8e74cf3447d165782530a9c8d7cafd59f106fb`.
See [the input qualification](mvp2_h300_input_preflight.md) and
[the accepted input audit](mvp2_h300_input_acceptance.md).
That job neither constructed nor optimized the large MILP. Its small RSS does
not establish a memory requirement for optimization or a speedup.

The next experiment is **one uncompacted control**, not a control/compact pair.
It measures whether the existing numerical formulation can build, solve,
export and validate the accepted 300-hub instance within a declared envelope.
Software tests qualify the admission machinery, not the large solve.
This PR remains Draft until its terminal NPAD evidence is independently reviewed.
Only after completion and Ready for review will a new merge authorization be requested.

No h400 solve, thread sweep, additional h215 pair, campaign expansion, dependency
upgrade, model change, or explicit staged-lifecycle experiment is admitted here.
The frozen MVP 1.0, original campaigns, original receipts and original guard remain intact.
Compaction remains optional and is **off** for this baseline.

## Exact execution contract

| Item | Reviewed value |
| --- | --- |
| Instance | 300 hubs: 146 existing, 154 candidate; 37 origins; 27 domestic and 10 export destinations |
| Products / periods / scenarios | 2 / 60 / 9 |
| Routing | Warehouse-only; OD/DC/DD/OC edges 4,440 / 4,800 / 36,000 / 0; zero repairs |
| Estimated variables | Exactly 25,107,544 |
| Baseline | `mvp2_h300_warehouse_baseline`, selected index 0, one experiment |
| Formulation | Existing stochastic three-priority lexicographic policy, unchanged |
| Algorithm | Existing all-barrier `Method=2`, four solver threads, seed 42 |
| Quality / optimization budget | Inherited `MIPGap=0.1`; 28,800 seconds (8 hours) |
| Native solver soft memory limit | Inherited `SoftMemLimit=128` (decimal GB, not process RSS or cgroup cap) |
| Slurm envelope | `intel-256`, one node/task, four CPUs per task, 192 GiB requested, 12-hour wall time |
| Actual cgroup | A readable finite cap of at least 206,158,430,208 bytes, checked before the license probe/build |
| License | Fresh designated-license 2,001-variable/2,001-constraint capability probe in the allocation |
| Observation | Existing OS/process-tree, actual cgroup, native solver memory, CPU, matrix and stage telemetry |

The reference guard of 25,000,000 is exceeded by 107,544 variables (0.430176%).
The earlier exception was input-only. The separate versioned
[baseline policy](mvp2_h300_baseline_policy.json) authorizes an execution guard of
**exactly 25,107,544 only for this one derived control**, conditional on fresh
allocation/license gates. It is not a generic ceiling increase to 26 million.
The original manifest, workbook, qualification, input preflight and guard are
revalidated without modification. The legacy h215 pair admitter remains unchanged.

The 12-hour job allows build/export/validation time in addition to the nominal
8-hour optimization budget; it does not guarantee completion or acceptance.
Allocated CPUs can exceed requested CPUs through site memory allocation rules;
this does not change the four solver threads or imply exclusive-node access.
The finite cgroup gate intentionally fails closed if its actual cap is missing,
unreadable or too small. A failed gate preserves evidence and does not auto-retry.

The inherited hierarchy contract is not strict equality between intermediate
and final objectives. In particular, the inherited MIP gap can allow capacity
degradation in a lower-priority pass even with `ObjNRelTol=0`. Report stage
incumbents/bounds and final recomputed objectives separately; an intermediate
gap is not a certificate of final capacity optimality.

## Complete NPAD workflow

Use the **full CI-passed head and driver SHA-256 recorded in the PR's operational
comment**, not a moving branch name. The small pinned bootstrap supplied with
that comment retrieves only the driver using `git show` in the preserved input
checkout, checks its SHA-256, then invokes:

```bash
bash /absolute/path/to/npad_mvp2_h300_baseline.sh start FULL_CI_PASSED_HEAD
```

The existing NPAD environment is `/home/vrrcelestino/venv313/bin/python`.
Do not install or upgrade packages. The original input run must remain at
`/home/vrrcelestino/model-agrologistic-hygiene-audit/mvp2-h300-input-retry-ppbN3rwH`.
Its private workbook/reference/qualification paths must remain available.

The driver performs, in order:

1. Acquire a durable global claim `.mvp2-h300-single-control-20261005` and print
   `PRESERVE_RUN`. The claim is independent of branch movement or a newer commit.
2. Clone into a new run, detach the pinned commit, apply only the inherited
   local raw-byte attributes for two historical manuscript files, and verify
   every tracked file against its HEAD blob. No archived checkout is switched.
3. Run repository Ruff and all six focused regression modules; require at least
   250 cases, zero failures, errors or skips. Keep the JUnit receipt outside Git.
4. Read successful terminal accounting for input job 2198085. Recheck original
   input products, canonical source/runtime, private workbook, reference and
   qualification, then derive a new single-control campaign and immutable plan.
5. Check metadata-only license availability, clean detached source, and plan;
   run Slurm `--test-only`; claim the submission atomically; submit exactly one
   standalone job. No array and no second arm are used.
6. In the allocation, capture scheduler and actual cgroup records, recheck all
   identities and execute the fresh license capability probe. Only accepted
   gates permit the single control optimization.
7. Run the existing independent solution validation and hierarchical auditor.
   Preserve phase/exit records, logs and all named solution/telemetry products.
8. Wait for terminal accounting and collect either success or failure evidence.
   Print `COLLECTION_STATUS`, `SHA256` and `DOWNLOAD` automatically. The adjacent
   `.tar.gz.sha256` and `collection.json` are also written.

`Ctrl-C` after submission only stops waiting. Repeating the **same pinned start
command** resumes collection and never submits again. Alternatively:

```bash
bash /absolute/path/to/npad_mvp2_h300_baseline.sh collect "$PRESERVE_RUN"
```

If preparation or submission fails, **do not delete the claim, alter receipts,
switch the run's checkout or invoke the submitter manually**. Preserve the
printed phase/run and share the error. An incomplete or ambiguous claim blocks
automatic recovery intentionally, because absence of a receipt alone does not
prove absence of a submitted job.

Download the printed archive and its `.sha256` via MobaXterm and share both.
No manual archive command is needed. The archive is allowlisted and contains
full solution products for independent review, not a license or workbook.
Because full flow tables are included, it may be larger than the input-only archive.

## Acceptance and next decision

The collector classifies a non-successful terminal job as `terminal_failure`,
a successful job with incomplete/inconsistent evidence as `evidence_rejected`,
and only a fully closed verified baseline as `accepted`. It verifies the fresh
admission, source/tools/plan, actual resources, worker completion, all **33**
named completion products, unchanged normalized inputs and input-audit bytes,
independent validation and the existing three-stage quality audit. It never
treats Slurm `COMPLETED` or a tarball alone as scientific acceptance.

After transfer, independently verify archive safety/checksum, all transfer and
completion hashes, mathematical validation, intermediate/final hierarchy,
native/process/cgroup memory by phase, sampling integrity and CPU exposure.
Document results and limitations on GitHub before marking this PR Ready.
Only then decide whether to prepare a separate matched h300 control/compact
contrast. An accepted baseline is not evidence of compaction benefit, speedup,
capacity adequacy or universal feasibility.
