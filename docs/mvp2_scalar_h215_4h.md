# Scalar R3-A operational h215 DET/STO pair — four hours per arm

20 October2026. Complete consolidated operational software delivery based on
merged PR114 (`ed126e59d5cc94ff5026ad7c19d88886847631df`). The maintainer selects
the historical OSRM workbook and explicitly approves the14,400s-per-arm/14h
reservation proposal. The [redacted input/decision ledger](evidence/scalar_h215_input_20261020.json)
records the human-pasted checksums and audit. No agent NPAD access, live probe,
submission, optimization or repeat occurs during this PR. Software tests are not
live private-input qualification. Ready and explicit merge precede separately
admitted human execution. Do not run old hierarchical or PR114 proposal drivers.

## Why the larger budget, and what it does not promise

Historical PR110 consolidated h300 hierarchy job2215308: five thread levels,
each global3600s, independently feasible incumbents, capacity TIME_LIMIT/gap100%,
no economic priority. That is useful censored evidence but not an acceptable
economic-quality baseline. It neither forecasts the scalar h215 gap nor shows
that four times as much time will resolve a zero-bound bottleneck. Formulation,
objective and population differ; do not call the next pair a controlled speedup
or claim an old configuration winner. See [original P5 interpretation](mvp2_s2_p5_closure.md).

The prospective pair has one scalar call per arm, native TimeLimit14,400s and
unchanged MIPGap0.01 target. Gurobi can return after TimeLimit; the retained900s
reserve covers delayed native return plus extraction/disposal and artifact
export, not a second call or a larger native TimeLimit. See the primary
[TimeLimit documentation](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html#parameter:TimeLimit)
and [MIPGap definition](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html#parameter:MIPGap).
No parameter sweep, MIPFocus/Method change, objective reweighting, tolerance
relaxation or automatic retry is introduced.

## Confirmed serial envelope

| Item | Per arm | Whole allocation / interpretation |
| --- | ---: | --- |
| Input, fresh WLS capability and construction |1800s | Includes preflight, build and bounded startup |
| Native scalar optimizer |14,400s | DET then STO; eight hours maximum configured optimization in total |
| Shared late return/extraction/export reserve |900s | Overshoot beyond native TimeLimit and return/export charge the SAME reserve; validation does not spend this reserve |
| Original independent validation plus product receipt review |1800s | Sum of worker validation/metrics and post-worker review; no fresh second solve |
| Arm step ceiling |18,900s (5h15) | Slurm-owned finite step ceiling plus controller phase budgets |
| Shared setup/cleanup |—|1800s planned |
| Planned total |—|39,600s (11h) |
| Unallocated contingency |—|10,800s (3h), NOT extra optimizer time |
| Reservation |—|50,400s (14h), below24h; one node,24 allocated logical CPUs,192GiB |
| Solver |4 threads | SoftMemLimit160 decimal GB, seed42, compaction off |
| Reservation bound |—|336 allocated logical-CPU hours, not measured CPU/billing or useful solver work |
| Transfer |—|1GiB expanded total,4096 regular members; no omission/truncation to fit |

Only one cold DET/STO pair is planned, not five thread configurations, replications,
resumes or repetitions. Extra reservation time cannot launch other populations.
The first scalar h215 pair must be audited before a separately designed h300
contrast. Existing input/hash and native quality targets are not changed to force
acceptance.14h admission may still fail or be preempted; the approved budget is
not evidence that Slurm accepted or guaranteed an uninterrupted allocation.
Do not automatically apply this envelope to a five-arm thread grid: five4h
native calls already total20h BEFORE build/validation/export, and the present
per-arm ceilings would not fit24h. Review later h300 grouping using the measured
scalar h215 phases and a separately approved contrast budget.

## Frozen input and provenance

Selected processed workbook: policy_population_v020_osrm/warehouses_215/model_input.xlsx,
SHA256 `40edb66585daca9cc393cab1f86bde6d4528a5f34b6afc57260cc1684396da4e`.
Population manifest SHA2564134147f... and order CSV SHA2567a524b2e... are pinned
in the operational module and full decision ledger. Same bytes/configurations
except mode/name; DET uses its original deterministic arrays, STO the approved
nine Cartesian levels,1/9 each.60 periods; no direct origin/customer arcs.

The human supplied the original materialization timestamp11 September08:43:42
America/Sao_Paulo, resolving the earlier unknown creation date.63,289 exported
routes are OSRM-sourced (DD46,010; OD/DC7,955 each; OC1,369);63,504 cache hits,
zero misses/writes/API requests/fallbacks. The difference215 is consistent with
DD diagonal lookups omitted from export, not extra transportation arcs. Four
roundoff-normalization occurrences are processing counts, not four unique bad
routes. Dataset/PBF/profile/image identities are checked exactly. SQLite presence
at203M is not a database hash or a new matrix snapshot certificate.

No SQLite write/read, OSRM service request, rematerialization or XLSX modification
is performed by the launcher. Original audit bytes are copied, hashed and retained
without rewriting; original source/workbook files stay untouched. Fresh compute
preflight verifies actual loaded membership,215 warehouses,60 periods, effective
scenario counts/probabilities, size bound, OSRM-primary provenance and original
finite mathematical contract. Every case preserves selection intent, observed
and included warehouse lists/roles/order/criterion/rank/seed/hashes. The list means
included facilities, not facilities opened by the optimizer.

## Complete lifecycle and failure handling

New exclusive claim: `.mvp2-scalar-r3a-h215-4h-v1`. It is distinct from the
PR114 proposal, R2 and all historical claims. Source/input/predecessor hashes,
resolved settings, runtime/tool identity and a durable submission intent precede
one sbatch. Uncertain/nonparsable submission consumes the slot; never retry or
guess a job from unrelated queue entries. Re-entry collects only.

The batch persists the actual scheduler query before parsing it. Validate owner,
job, one node,24 logical CPUs,192GiB,14h, account/partition/QOS; preserve NPAD's
Slurm22 TRES field without pretending it is ReqTRES. Compute requires no Git.
Each native worker announces its numeric step and waits. The controller verifies
that exact step/owner/node/CPU record before releasing it. The designated existing
WLS file is explicitly selected; a fresh quiet2001-variable/constraint capability
probe runs in compute, separately labelled from the one agricultural optimizer
call. Credentials/license bytes are never hashed or transferred.

The existing native phase hook emits durable ordered markers without changing
scientific source. Parent deadlines separate build, optimization, return,
validation and export. Only a verified exact numeric step can receive TERM/KILL;
reaping a local srun client is never global cleanup proof. Unbound startup,
malformed phases, expired budgets, failed source/input/validation or uncertain
cleanup stops the serial pair and preserves unrun arms. A normally returned,
independently feasible but gap-censored DET may be followed by the planned STO;
quality remains partial and no downstream experiment is admitted.

The collector waits for terminal root/batch and every launched step, preserving
full CANCELLED-by-UID grammar. Scheduler failure does not discard a returned
incumbent or missing-worker diagnostics. Include batch/worker/review logs, raw
queries, phases, original products, selection receipts and first terminal accounting.
Missing accounting remains pending, not success. Seal once, preserve all originals,
return the same SHA on repeated collection; reject links/traversal/duplicates/
over-cap artifacts and never include private XLSX/database/license files.

## Acceptance is multidimensional

1. Operational closure: bound fresh admission/runtime, exact returned/reaped
   steps, closed phases, terminal accounting, source/input integrity and complete
   inventory. Miniature/mock transport CI does not prove actual NPAD closure.
2. Scientific feasibility: original independent residual/cost reports accepted
   under unchanged1e-5/1e-8 tolerances, original completion hashes, usable incumbent.
3. Quality: common incumbent-denominator scalar gap at most1% for EACH arm.
   Preserve native gap, objective, best bound, actual native Runtime and phase clocks.
   A feasible100% or other above-target gap is censored evidence, not quality success.
4. Pair interpretation: both feasible but target missed =>
   pair_feasible_quality_censored; missing/rejected arm => partial/rejected; failed
   lifecycle => forensic_partial_pair_preserved. No-incumbent is not infeasibility.
   No automatic larger instance, repeat, speedup, VSS/EVPI or economic-impact claim.

Portable audit checks original receipts/inventory, not a fresh private workbook
reload/residual calculation. Solver-sequence runtime is labelled separately from
solver-reported native Runtime. RSS, native decimal-GB memory, cgroup and Slurm
MaxRSS have different scopes; requested CPUs, logical affinity/SMT and solver
threads are not interchangeable or evidence of parallel speedup.
The native tiny fixture can report OPTIMAL/native gap0 while raw ObjBound is
about7e-10 above ObjVal near33,931. The unchanged conservative common-gap
function returns null for ANY reversed bound order; retain that raw distinction
and explicit quality_reason, without clipping, relaxing tolerances or forcing
quality success. Native tests check this outcome rather than assuming both gap
definitions always agree. This is a rounding diagnostic, not a100% MIP gap or
time-censoring observation. Missing common quality still requires review.

## Human runbook boundary

The complete wrapper is [npad_scalar_h215_4h.sh](../scripts/npad_scalar_h215_4h.sh).
It carries the selected historical paths and existing Python/WLS defaults,
performs login-safe orchestration regressions and post-test raw-source closure,
does not install packages and prints fresh-shell status/wait/collect commands.
Old claims are never removed. The start acknowledgement means exactly one
reviewed pair; it is not automatically issued by CI, prepare, collection or merge.

After Ready, authorized merge and separate execution admission, supply the
reviewed FULL40-character source and SHA256-verified wrapper through a subshell
safe download command; do not use top-level set-e in the interactive shell.
Then use start once, status as needed and wait/collect for that SAME source/claim.
Ctrl-C during wait is safe. Transfer the printed download and checksum via
MobaXterm. No execution CLI is being issued during this software preparation.

## Qualification disclosure

T1 covers actual Slurm22 field examples, mismatches, uncertain submission/reentry,
ownership/release, shared-reserve arithmetic, cancellation grammar, phase/time
corruption, censored quality, missing diagnostics, bounded immutable transfer and
source/selection/certificate corruption. No solver or live scheduler in login tests.
T2 native CI exercises tiny public Excel DET/STO through the actual worker,
parent handshake/phase controller, original scalar backend/validation/completion,
terminal collector and portable audit with controlled local transport/capability/
affinity fixtures. Those fixtures are explicitly not real Slurm/WLS/hardware
observations; production shape and config are tested separately and cannot be
changed by a CLI flag. T3 requires full exact-head Linux native suite with zero
native skips, Ruff, source closure, all Bash syntax and distribution build.
Local Windows expired-license skips are disclosed separately, not native acceptance.
Record actual final-head results before Ready; no scientific/NPAD result is claimed.
