# Original scalar SCIP h215 W observation — 28 October 2026

The original job **2225638** returned normally but did **not** return a usable
incumbent. Its negative computational outcome is accepted as an audited
observation, never as an accepted feasible solution. The original four-hour
observation is complete; no restart, reset or replacement of its claim follows.

## Original evidence and independent review

| Identity | Value |
| --- | --- |
| Original source | `cbd64d86914dd416ed16b6a58ffe1069401e3aad` |
| Preparation merge PR131 | `083e5759ee5bb4d4d2982c4dcf2ffd12f2afb476` |
| Plan SHA-256 | `1af2f262961cfcca46edfca6a2663e5e82267b3dab0dcefedebea3785761a7fe` |
| Transferred archive SHA-256 | `41557726ecd93ab67a5764077ea18a35e08db4d6f97123a03ebd6b72930ebf68` |
| Original review SHA-256 | `832fa7a9a0466ab20a45127ddb2c860d31dfc6b8b53ad056d846c6ef2ebf7728` |
| Original validation SHA-256 | `04512dc888d48746b1db5cd09a430f4f8a39ee15c45839a52ff4b62bb80f4f39` |

The externally supplied checksum matches the archive. The bounded regular-member
reader accepted **111 unique safe members**, **769,739 expanded bytes** and
**110 inventory digests**. All **562 original source files** match a separately
downloaded, pinned public GitHub source snapshot. The unmodified original
portable reviewer reproduces archived `review.json` exactly, including full
owned-step/phase/batch/accounting closure and all false follow-on flags.
The audit refused native-solver imports, subprocess execution and network
connections; no raw archive member was extracted or executed. A disposable
trusted public source snapshot was used only for audit, without a local clone,
environment creation, installation or NPAD access.

The redacted [machine-readable review](evidence/scalar_scip_h215_w_2225638_review.json)
retains original identities and measured scopes. Reproduce with
`python -B -m scripts.review_scalar_scip_h215_evidence ARCHIVE --sha256 SHA256
--original-source-root TRUSTED_ORIGINAL_SOURCE_SNAPSHOT`.
Use a clean source snapshot of the original pinned commit, not this later PR's
tree. This replays original certificates/logs; it does not recompute private-input
residuals. Private inputs, full row IDs, host identities and raw archives stay
outside Git.

## Observed result

| Observation | Original evidence |
| --- | --- |
| Backend | PySCIPOpt 6.2.1 / SCIP 10.0.2 / SoPlex 8.0.2 |
| Input/model | Same frozen scalar STO/W h215, 9 equiprobable scenarios |
| Construction | 249.8276 s |
| Native ceiling / returned native runtime | 14,400 / 14,410.764462 s |
| End-to-end / root Slurm elapsed | 14,939.748946 / 15,031 s |
| Native termination / solutions / processed nodes | timelimit / 0 / 1 |
| Original native matrix | 14,129,174 variables; 307 binaries; 810,097 constraints |
| Presolved native matrix | 12,708,003 variables; 92 binaries; 626,547 constraints |
| Presolve time in native log | 608.24 s |
| Native dual bound | -1,779,457,702,122,698.2 BRL |
| Incumbent, economic cost, physical service and computable gap | unavailable |
| Scientific classification | no_usable_incumbent; quality target not met |
| Operational accounting | COMPLETED 0:0, including exact worker step 2225638.0 |

The native runtime exceeds its requested ceiling by about 10.76 seconds and is
retained as observed, not rounded to the budget. One processed node and 316,394
sampled simplex iterations describe a root-level limited observation; they do
not prove root-LP completion, a solved root bound of useful quality, or a precise
root bottleneck. The negative lower bound is retained unchanged, not a negative
incumbent, economic result or impossibility certificate.

The independent validator rejects the empty candidate exports (41,066 failed
checks including the usable-incumbent check). These are not 41,066 violations of
an allegedly feasible returned solution. Placeholder summary values such as
scenario service=1 and penalty share=0 are explicitly excluded from scientific
results. Objective, costs, service and gaps remain null rather than zero.

## Resource limits and comparison boundaries

The exact-step Slurm MaxRSS is **93,214,788 KiB = 88.89655 GiB**. The separate
sampled application maximum is **91,169,603,584 bytes = 84.90831 GiB**. These are
different scopes and do not establish production containment or a smaller safe
allocation. The reservation was 24 logical CPUs / 192 GiB; worker affinity
contained 16 logical CPUs; configured solver-thread ceiling was four.
Neither those ceilings nor observed native thread counts prove parallel search
or four effective SoPlex threads.

Only 20 application resource samples were retained. The largest adjacent
interval was **14,414.8056 s**, almost the full optimization window. Reported
sampler work (14,681.03 s) and inspection elapsed time include time across the
solve; they cannot be charged as proven CPU/observer overhead or used to infer
causal slowdown. No continuous utilization, unobserved phase peak or
root-LP-completion claim is made. The next operational qualification must make
this sampling limitation explicit and assess independent external observation.

Historical Gurobi STO/W h215 returned an accepted incumbent in 2,445.52 s with
0.740159% gap. It is a historical control, not a contemporaneous replicate:
different native representations, execution dates and shared-node conditions
preclude causal speedup attribution. The SCIP native variable/constraint counts
include backend representation details and are not interchangeable with Gurobi
linear/general-constraint counts. One resource-limited SCIP observation supports
a bounded difficulty statement for this configuration, not general inability
of SCIP or open-source solvers.

The accepted feasible scalar inventory remains **eleven Gurobi observations**
(nine W plus two D). This new negative SCIP observation is separately counted,
not promoted into those eleven or pooled with the old hierarchical campaign.

## Researcher's new continuation request

After reviewing the supplied terminal output, the researcher requests planning
one longer SCIP observation and other free solvers, including HiGHS and an
agnostic multisolver design. This prospective scope supersedes the former
blanket no-repeat planning hold only for these explicitly requested preparations.
It never changes the original receipts' false admission flags.

See the [revised sprint/PR plan](mvp2_completion_plan_20261028.md) and
[multisolver design](mvp2_multisolver_plan.md). The immediate longer-test proposal
is native 8 h / Slurm 12 h, unchanged input/science/192 GiB/four-thread ceiling,
a fresh distinct claim and immutable binding to this predecessor. It is a cold
restart observation, not a resumed SCIP search or controlled replicate.
No new job or command is released by this results/checkpoint PR.
