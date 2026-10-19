# Consolidated S2 A/P2/P3: minimum academic qualification

## Authority and preserved evidence

Continuation15 October: PR99 merged at
`b6100b8120a60d21d49a5f308a8f929191e2238a`; normal job2212000 failed before srun.
The [negative audit and complete correction](mvp2_s2_academic_2212000_audit.md)
supersede the prospective transport namespace with academic-v2, preserving the
consumed v1 claim and its rejection. Compatibility with Slurm22.05 serialization
does not change the adopted resource/scientific criteria. New execution stays
blocked pending Ready/separate merge review and newly pinned human CLI.

15 October 2026. Base: develop `219233e2b116ffcc5eac5c462b4b863059eace14`
(PR #98 merged). The maintainer explicitly requests an alternative minimum
profile for trusted fixed research code, not production deployment, and one
consolidated A/P2/P3 delivery. This document and the
[versioned profile](mvp2_s2_academic_profile.json) supersede prospective whole-host
qualification requirements for **new academic attempts only**. Original claims,
negative certificates, accepted results and source identities keep their meaning.
No model/data/scientific tolerance/validator/dependency/article change is made.

Original job2211851 evidence was independently replayed with the unchanged auditor:

- Source: `1e2574605cb1d77987539461514ec391f7bee043`.
- Plan: `86037921f8f16efa130999ef6f17c4afc753fa8d78dc86563a3dc1a2ef696deb`.
- Archive: `77655cb3bf4da7521b9564c4985a8923ac0b69aed7a67f70eddb203a989fb9b8`.
- Disposition remains `blocked_environment`, all original downstream flags false.
  Root/batch6s, extern7s, all0:0; capture0.04676803667098284s, not a timeout.
- Measured max_user_namespaces1027175 violates the old zero requirement. All four
  PID1 namespace reads returned EACCES13. Controller placement/mapping/descriptors
  succeeded; inventory returned EACCES13; hierarchy invalid_evidence without a
  precise internal path. Unreadable is not different; invalid is not writable.
- This is not a solver/license/model failure, unsafe-host proof or escape proof.
  Raw evidence stays outside Git. Plan source hashes are declared provenance;
  replay is not a new independent comparison of all612 remote source blobs.

## Explicitly reduced assurance

Threat model: reviewed fixed Python/native research code, a trusted researcher
account and the site's Slurm. No hostile plugin, arbitrary executable/workbook,
service exposure or adversarial production-security qualification is supported.

| Required academic evidence | What it does and does not establish |
| --- | --- |
| Exact source/input/config/runtime identities, native version/license for C | Repeatable specified conditions, not guaranteed bitwise deterministic solutions |
| Fresh allocation/account/UID/node and requested/allocated CPU/memory/time, worker affinity | Scheduler observations; kernel enforcement is a site dependency, not independently certified |
| Walltime/memory request, parent watchdog, exact numeric-step TERM/KILL, local reap | Bounded operational control, not adversarial no-escape/global descendant absence |
| Root/batch/extern/known-step terminal accounting and nested identities observed absent | Scoped termination evidence, not the old allocation_tree_closed certificate |
| One-shot claims, intent before sbatch, independent archive replay | Unknown acknowledgement consumes the slot; no auto chain/retry |
| Unchanged residual/degradation checks, native count/status and phase/product binding | Scientific acceptance remains distinct from job completion; no incumbent is not infeasibility |
| Bounded immutable evidence, safe allowlists and cached same-byte replay | Corrupt/oversized originals retained, never repaired or silently truncated |

No longer mandatory: host-wide max_user_namespaces=0, PID1 namespace access,
whole-host cgroup hierarchy/ACL scans, hostile-worker no-escape certification,
persistent isolation certification, filesystem crash-durability proof or continuous
peak coverage. These guarantees are unproven, not manufactured from successful
accounting. No sudo/sysctl/chmod/cgroup migration, host/security or package change.
NoNewPrivs is not promoted to an isolation proof. New reviews explicitly keep
production_isolation_certified=false and h300_execution_admitted=false; old strong
auditors/certificates are not relaxed or reclassified.

## Complete package and sequential passage

The package contains [independent replay](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/5f9daa55b3afb5bbcb3449bc83c970cf10a28ca6/scripts/mvp2_s2_academic.py),
[fixed worker](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/5f9daa55b3afb5bbcb3449bc83c970cf10a28ca6/scripts/mvp2_s2_academic_worker.py),
[transport/collection](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/5f9daa55b3afb5bbcb3449bc83c970cf10a28ca6/scripts/mvp2_s2_academic_runtime.py),
[wrapper](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/5f9daa55b3afb5bbcb3449bc83c970cf10a28ca6/scripts/npad_s2_academic.sh) and
[regression](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/5f9daa55b3afb5bbcb3449bc83c970cf10a28ca6/tests/test_mvp2_s2_academic.py).

1. A: one normal stdlib worker; exact phases, worker/job/step binding and terminal
   independent acceptance. New academic namespace, no old-claim reset.
2. P2: build/optimization/export/disposal failure and nested setsid/TERM-ignore;
   each own immutable job/claim/expected outcome. Each entry needs A's externally
   anchored archive freshly replayed. Audit each outcome; unknown effects stop.
3. P3: one existing public analytical fixture through the actual integrated
   native worker. All six A/B archives must replay accepted at the same reviewed
   source, using external archive/checksum/source/plan/job anchors. Fresh designated
   license capability/version, unchanged effective global solver settings/priority
   setup, one optimize window, disposal and independent residual/hierarchy acceptance.
4. P4: separate reviewed release only after C acceptance and fresh large-input,
   source/runtime/license/allocation/export-volume qualification. Still blocked.

Minimal installed C requirement: **one complete independently accepted real native
miniature**. Complete/partial/no-incumbent branches are also software-qualified
with fixtures; do not force artificial native OOM/time exhaustion just to cover
every rare termination. Actual partial/negative C products remain preserved and
revalidated, but do not pass C. Synthetic phase failures are not agricultural
partial solutions. No h300 numerical parity or universal callback/limit proof.

The bridge reuses the existing native integration with only the fixed public
fixture and four threads. No arbitrary model/command/input is exposed. The legacy
anchor workbook-hash field contains the public fixture digest for this gate,
explicitly not a private workbook identity; input/config/source/runtime are
externally anchored and recomputed. The native solver profile is unchanged.

## Budgets, metrics and limitations

| Stage | Request | Limits |
| --- | --- | --- |
| A and each P2 | 2logicalCPUs/2048MiB/12min | 180s work; at most300s scoped cleanup, within batch budget |
| P3 | 4logicalCPUs/16384MiB/40min | 120s build/license,1800s global optimization,120s export/validation,300s cleanup;2340s plus60s reserve |
| Future P4, unchanged | 16CPU/192GiB/6h | Existing900/1800/900/300 per arm; five cold serial arms4,1,8,2,16 |

A/B/C proposed reservation totals112min and approximately5.067 requested CPU-h,
not measured usage, billing, calendar time or permission to reserve all slots.
The old390s full-isolation observation obligation is superseded prospectively by
300s scoped cleanup. This does not guarantee installed cleanup fits; insufficient
time/unknown effects remain negative, not an extension or a double use of reserve.
P3 keeps SoftMemLimit128 decimalGB inside a smaller16GiB outer fixture allocation;
this is not a changed large-model solver profile or h300 memory adequacy evidence.

Root pre-exit Linux getrusage RSS/CPU, native Runtime/MaxMemUsed, scheduler elapsed
and allocated resources have different scopes. Tree CPU/continuous coverage are
unavailable, not zero. P4 must qualify actual resource comparisons separately.
Censoring is not completed-work speedup. Shared-node effects stay disclosed.

## Operational handoff, preservation and software qualification

No NPAD execution occurs in this PR. Finish exact-head checks/Ready and obtain
separate merge authorization. Then provide the pinned40-character SHA/wrapper
checksum human CLI; merge alone never admits execution. The explicit interface
selects one stage: start STAGE SOURCE --one-reviewed-academic-slot, with five
anchors per predecessor. This operator acknowledgement is not a security token
and cannot bypass predecessor audit. Never pre-submit a Slurm afterok chain.

The wrapper verifies merged-develop ancestry, its own bytes and raw HEAD inventory
before/after external-output regression. Compute uses sealed source/runtime, not
Git or sbatch. status/wait/collect never submit; existing start is collection-only.
Only accounting-pending waits again; corrupt/unknown evidence stops. Ctrl-C during
wait is safe. New namespaces .mvp2-s2-academic-v2-STAGE are distinct from historical
claims, including consumed academic-v1-normal. Normal v2 first replays job2212000's
exact rejected archive. No repeated submission, reset, source replacement or old
archive rewrite.

Archive members: plan/job/accounting/records/review. Fixed worker JSON allowlist;
no raw native logs, private workbooks, environment dumps, license contents/path.
Malformed/oversized products block portable collection and preserve originals.
Interrupted/corrupt archive/sidecar/cache blocks replacement rather than repair.
Successful writes/fsync are ordering, not NPAD/NFS crash-durability certification.

Failure-cleanup publication now flushes a pending file before exposing the final
JSON name, like other phases. Tests verify visibility and publication-failure
handling. This fixes a source-visible race window, not a proven explanation of
PR97's intermittent CI failure. Old evidence pins and assertions are preserved.

Software qualification uses injected scheduler/native effects and disposable
directories, not NPAD, licensed scientific evidence or host changes. Include the
existing native/partial/control regressions and exact-head Linux CI. Platform/
license skips are disclosed. No acceptance criterion is satisfied merely by flags.

## Remaining deliveries

Local Python3.13/Windows qualification:244 cases in the academic/native/partial/
control cohort,242passed and two explicit POSIX-only skips. Ruff passes;186
relative documentation links and the16-file scope were inspected. No source
under src/, private data, experiment manifest, article or dependency declaration
changes. The broader Windows suite reaches Bash/MSYS NtCreateDirectoryObject
access failures; this is not Linux qualification or a passed full suite. Exact-head
Linux CI must exercise all244 cohort cases without skips before Ready. Publication/
CI/packaging status must be reported separately; no NPAD evidence is invented.

Baseline: this complete A/P2/P3 consolidation, P4, P5; corrections may still be
needed. Live A/B/C audits can be recorded with P4 admission, not one PR per adverse
case. P5 accounts for every h300 arm, solution quality/resources/censoring and an
accepted next configuration or explicit inconclusive decision. Positive speedup
is not required; unrun contracted arms cannot silently close S2.
Later h400, existing-SCIP/h215, conditional h500 and S6-A/S6-B remain. S3/S4
cancelled, EVPI/VSS excluded; article edits at S6, branch sync after article review.
