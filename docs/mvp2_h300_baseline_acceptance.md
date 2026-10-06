# H300 baseline: accepted retrospective evidence review

## Disposition and immutable provenance — 6 October 2026

Job **2198528** completed successfully (`COMPLETED`, `0:0`) on `r1i3n3`.
The optimization and original independent/hierarchy audits succeeded. The
original collector nevertheless recorded `evidence_rejected` because it
incorrectly required the post-solve `model_audit.json` to have the input-only
file's byte hash. This document records a **separate retrospective acceptance**,
not a rewritten collection receipt or a repeat optimization.

| Identity | Value |
| --- | --- |
| Execution source | `d70cade148e190e98d41a5ac3d4e040353f2c6ec` |
| Transferred archive SHA-256 | `43311a0000a3fb09f535ea273bd889ba1a6e09bf728460f0f28b764242e400c2` |
| Baseline plan SHA-256 | `833aab62709aae6ee4abeaa93af9962f6005ed48426e267085191fdf46a96f6e` |
| Campaign SHA-256 | `9ba56d27d736cc1dfe7785b4b7eba8d5a3efc428e24ec7aa25f8bf40b4c46ca7` |
| Canonical implementation/runtime | `b4de41ade0b3c55f8f20a66480cffa275421f8157444b1db3000a9eb50f2d351` |
| Completed run identity | `ec9ddef3b5ff05ee828597ec8ed09ade5b8c36ee14cc5bfd1b05f4cae28bd6cf` |
| Completed result SHA-256 | `f378c3dd6b58ad7b75fcbb7f9b41a88642f4e03dd4380e88effeaee55055f4e1` |
| Independent report SHA-256 | `7a5e41e7f010312ad812741d7b7d22d30de5d148476cc9d899ea9f0fdf24ca43` |
| Original collector SHA-256 | `33f0db5ddb466c6a60b1fd88577a751fa49f5e38c211b4f6d4f03ef178d7806e` |

The accepted input-only job remains **2198085**, execution source
`3957f84ff49ac500eecf25b85e6b710b4b3b1010`, archive
`97395d29b802e558d3ac88db8c8e74cf3447d165782530a9c8d7cafd59f106fb`.
Its [input acceptance](mvp2_h300_input_acceptance.md), receipt and original
25-million guard were not altered. New correction/documentation commits are
**not** the source of either historical execution.

## Collector correction and review method

`experiment_runner` intentionally calls `build_model_audit(data, config, result)`
after solving. The audit retains its full `input` mapping, but adds `solution`,
independent-validation status, solution findings and updated severity counts.
Comparing entire input-only and final files was therefore a lifecycle error.

The corrected completion gate requires all of the following:

- Original input audit still matches its accepted receipt's byte hash.
- Schema 3 and the **entire nonempty input mapping** match exactly.
- All original findings are retained in order; severity counts are consistent,
  there are no error findings, and accepted solution enrichment is present.
- Four connectivity products remain byte-identical to the input receipt.
- The complete final audit, including warnings, remains covered by the final
  run-completion hash and the transfer hash. Independent and hierarchy gates
  remain required; no warning is suppressed to obtain acceptance.

[`review_mvp2_h300_baseline.py`](../scripts/review_mvp2_h300_baseline.py)
is a read-only, deliberately **job-specific** retrospective reviewer. It accepts
only the pinned transferred checksum and original execution source. It verifies
21 controls: safe/unique/bounded allowlisted archive members; all 57 transfer
hashes; terminal accounting; submission; original tool bytes; accepted input
receipt and its 12 products; plan/policy/accounting; exact control derivation;
fresh scheduler/cgroup/license/admission; worker exit; all 33 completed products;
44 normalized source files and original runtime; serialized experiment;
recomputed completed-run identity; normalized preflight; input-audit/connectivity
parity; original independent validation; independently reclassified hierarchy;
closed native-resource catalog; telemetry integrity and sampler isolation.

The transferred archive has **59 regular members**, no extra workbook/license,
no extraction links and no missing catalogued products. Six resource payload
hashes also match their closed resource manifest. The run identity is recomputed
with the archived NPAD runtime, not with the local review machine's packages.
Original Python 3.13.15, Gurobi 13.0.3, PySCIPOpt 6.2.1, NumPy 2.5.2, pandas
2.3.3 and openpyxl 3.1.5 identities are retained.

This review **verifies the original NPAD residual-validation report** and its
provenance; it does not claim a fresh evaluation against the private workbook
on the review machine. The original report has 32 families, zero failed checks
and no failure samples. Its mathematical contract matches the result metadata.
Absolute tolerance is `1e-5`, relative tolerance `1e-8`, sparse-export threshold
`1e-7`, with component-specific cost-rounding budgets. A reported maximum cost
residual of 0.025390625 must be read under those budgets and relative tolerance,
not compared in isolation with the absolute feasibility tolerance.

To reproduce the review locally, retain the downloaded archive, unchanged
extracted input evidence, and an original `d70cade` checkout (or verified source
snapshot) outside the current development checkout:

```bash
python scripts/review_mvp2_h300_baseline.py \
  --archive /absolute/path/h300-baseline-evidence-2198528.tar.gz \
  --input-run /absolute/path/preserved-input-2198085 \
  --execution-checkout /absolute/path/original-d70cade-checkout
```

The command reads evidence and prints JSON to stdout. It does not extract the
archive, change any receipt, probe a license, optimize, invoke Slurm or submit a
job. **No NPAD command is required for this disposition.** Do not switch the
archived checkout to the corrected head or run its new collector against an old
plan: the tool-identity gate correctly rejects that mismatch. The original
archive/collection/claim/run must be preserved, including the rejected receipt.

## Observed computational result

This is one uncompacted warehouse-only stochastic control: 300 hubs (146
existing, 154 candidate), nine scenarios, 60 periods and two products. Direct
origin/customer arcs remain off; audited interhub repair count is zero. Original
matrix: **25,107,544 variables**, 392 integer variables including binaries,
890,642 linear constraints, 94,635,126 nonzeros; 166,320 general constraints
are reported separately. The exact reviewed execution guard was attained, not
raised further. All-barrier `Method=2`, four solver threads, seed 42, inherited
`MIPGap=0.1`, `SoftMemLimit=128` decimal GB and eight-hour optimization budget
remain unchanged.

| Measure | Observed |
| --- | ---: |
| Data read | 18.83 s |
| Model build | 440.39 s (7.34 min) |
| Optimization | 20,673.07 s (5.74 h) |
| End-to-end application | 21,322.33 s (5.92 h) |
| Slurm elapsed | 05:55:41 |
| Application high-water RSS | 61,170.36 MiB = **59.74 GiB** |
| Slurm batch MaxRSS | 60,982,612 KiB = 58.16 GiB |
| Highest sampled live process-tree RSS | 58.41 GiB |
| Highest sampled actual cgroup use | 58.55 GiB |
| Highest reported native solver memory | 39.93 GiB |

These memory measures have different scopes and collection times; differences
are not inconsistent hashes or proof of a measurement defect. Sampled peaks
are lower bounds on the true instantaneous peaks. Native solver memory is not
the Python process RSS. Slurm requested/allocated memory and the finite actual
cgroup cap are **192 GiB**, not the native decimal-GB soft limit.

| Phase | Samples | Sampled tree RSS peak, GiB | Sampled cgroup peak, GiB |
| --- | ---: | ---: | ---: |
| Model build | 10 | 20.23 | 20.30 |
| Service priority | 176 | 41.06 | 41.17 |
| Capacity priority | 2,354 | 56.94 | 57.08 |
| Economic priority | 1,508 | 58.41 | 58.55 |
| Result extraction | 2 | 27.52 | 27.60 |
| Native disposal | 3 | 17.68 | 17.75 |
| Independent validation | 1 | 4.47 | 4.51 |
| Artifact export | 4 | 4.56 | 4.73 |

The closed telemetry contains 4,122 resource observations and 71 progress
records, zero dropped samples and no recorded inspection errors. The nominal
five-second interval is not a guarantee of uniform observations, particularly
during model construction. Recorded sampler inspection work is 756.31 seconds;
this is **not** a causal estimate of runtime overhead without an uninstrumented
matched control. The node allocated 24 CPUs but the solver used a configured
four-thread ceiling. At most seven native process threads were observed, not
seven active solver workers. The last live-tree cumulative CPU observation is
34,231.92 seconds; it is not a complete lifetime accounting of all exited
children and cannot establish parallel speedup or efficiency. Sampler solver-API
calls are disabled in the capabilities receipt. No compaction benefit is
measured by this single control.

## Priority outcomes and scientific interpretation

All three solver passes ended `OPTIMAL` **under the configured tolerances**;
the original hierarchy audit and fresh pure stage classification are
`accepted_at_ten_percent`. This is not an exact-global-optimality certificate.

| Priority | Pass incumbent | Pass bound | Pass relative gap | Final recomputed objective |
| --- | ---: | ---: | ---: | ---: |
| Unmet domestic demand | 0 | -5.3842e-9 | Sentinel, not meaningful near zero | 9.98546e-7 |
| Emergency-capacity score | 328,334,362.50045 | 327,520,771.94552 | **0.247793%** | **360,354,208.19556** |
| Economic cost | 396,098,981,252.41626 | 395,769,768,427.92761 | **0.083114%** | 396,098,981,252.42310 |

Domestic service is certified zero-shortfall **within the declared absolute
`1e-6` objective tolerance**, not literally zero in every floating-point output.
The minimum scenario service fraction is 0.9999999999999875. The service
`mip_gap=1e100` sentinel is not a 100% shortfall or grounds to reject a near-zero
service certificate. Material balances passed independent validation.

Final capacity increased **9.752207%** over the pass-2 incumbent. Its relative
difference from the preserved pass-2 bound, divided by the final objective,
is **9.111434%**. The inherited permitted next-pass capacity limit was
360,354,208.1955612; the final value differs only within the numerical check
tolerance. `ObjNRelTol=0` does not remove the inherited MIP base degradation.
Consequently **0.247793% is an intermediate pass gap, not the final capacity
gap**. The contract is unchanged; see the existing
[hierarchy interpretation](mvp2_h300_baseline.md).

Two meaningful model findings remain in the accepted audit:

- `EMERGENCY_CAPACITY_REQUIRED`: all nine scenarios depend on relaxed capacity.
- `INVESTMENT_CAPACITY_SATURATED`: all eligible candidates attain their configured
  capacity upper bound for at least one investment type.

The expected static-overflow sum is 321,520,043.66 and reception-overflow sum is
38,834,164.53. Their aggregate 360,354,208.20 is an emergency-violation score
summed across periods and expected across scenarios, **not installed storage
capacity, a unique physical deficit or a procurement requirement**. Reception
slack is already period overflow; do not multiply it by operating days again.
The penalized scalar accounting total is 16,612,038,350,052.70; 97.615591% is
penalty dependent. Economic cost is 396,098,981,252.42 in model currency units;
the two quantities must not be presented as equivalent observed market costs.

EVPI/VSS were not requested or computed. No direct-enabled h300 comparison,
compact arm, h400 solve, thread sweep, new forecast or lifecycle-production
profile is certified by this result. Historical MVP1 results remain separate.

## Development closure and next boundary

Local repository Ruff and changed-file formatter checks passed. The selected
Python-only six-module gate passed **270 tests**, with 31 Bash-executing cases
explicitly deselected because this session's Windows sandbox blocks Git Bash
startup (`NtCreateDirectoryObject`, access denied). Those 31 cases are **not**
claimed as local passes; the unchanged Linux GitHub CI suite must cover them
before readiness. No test weakening, blanket skip or workflow change is used.
Exact-head CI and the final diff disposition are recorded in PR #48's closing
comment, avoiding relabelling old executions with the correction head.

The collector lifecycle bug is corrected with synthetic regression coverage
for legitimate solution enrichment and self-rehashed input/schema/status/error/
summary drift, retained input findings, unsafe archive paths, links, duplicates,
checksums and catalog changes. Current development changes are limited to
scripts/tests/documentation; formulation, core `src/logic` fingerprints,
solver settings, dependencies and frozen MVP1 remain untouched.

After the corrected exact head passes GitHub CI and diff review, PR #48 may be
promoted **Ready for review** and a separate merge approval requested. It does
not authorize its own merge or a new NPAD optimization. The next scoped PR can
qualify a matched **h300 control/compact contrast**, reusing the accepted input
definition but keeping new runs/receipts and the exact resource contract.
Admission/order/duplicate guards and terminal evidence must be qualified before
the maintainer receives a pinned CLI command. Compaction remains optional.
Do not combine this with h400 scaling or 1/2/4/8/16-thread experiments.
