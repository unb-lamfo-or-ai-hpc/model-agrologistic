# One extended native SCIP h215 W observation — 28 October 2026

PR132 was merged by the researcher at
`f9dddaee2bfe76b18d7692eec4e3f14597abaf04`. Its original four-hour SCIP
observation is immutable: job2225638/source cbd64d86/plan1af2f262/
archive41557726, native timelimit, zero solutions, operational closure.
The researcher requests ONE new, longer cold observation, and a separate
parallel Pyomo multisolver implementation PR. This native experiment does not
use Pyomo or incorporate that other PR's formulation.

## Scientific and resource contract

The existing native scientific src and old launchers/readers remain unchanged.
Keep original h215 W/STO workbook/membership/OD3182/DC3440/DD18490/OC0,
nine equiprobable scenarios, penalties90000/45000/45000, Seed42,
gap0.01, residual tolerances1e-5/1e-8, PySCIPOpt6.2.1/SCIP10.0.2/SoPlex8.0.2,
sequential optimize(), four-thread ceilings and SCIP memory163840 MB.
No warm start, concurrent driver, parameter tuning, DET/D arm or larger instance.
One observation cannot establish general open-source inability or causal speedup.

| Budget | Ceiling |
| --- | --- |
| Input/build | 3600 s |
| Native optimization | 28800 s (8 h) |
| Return/disposal/export | 900 s |
| Independent validation/review | 1800 s |
| Numeric worker step | 35100 s (9 h 45 min) |
| Setup/cleanup | 1800 s |
| Planned / reserve / Slurm reservation | 36900 /6300 /43200 s (12 h) |
| Allocation / worker pool / solver ceiling | 24 logical CPUs /16 logical CPUs /4 threads |
| Allocation memory | 192 GiB |
| Allocation product | 288 logical CPU-hours, not measured utilization |
| Transfer cap | 4096 regular members /1 GiB expanded; no truncation |

The later human start validates this exact account/partition/QoS/12h profile
using sbatch --test-only before creating the claim. This does not submit a job
or execute the wrapped program. A rejection leaves no claim/job and must be
reported; do not silently lower requirements or retry a submitted/uncertain job.

## Immutable predecessor, source and ownership

New claim: `.mvp2-scalar-scip-h215-w-native8h-v1`.
New archive: `scalar-scip-h215-w-native8h-evidence.tar.gz`.
New case: `scalar_scip_h215_w_native8h`.
Only the future pinned human CLI may create it below the allowed project audit
directory. Preserve the original four-hour claim, bootstrap, source and plan.
An existing/unknown new claim refuses start before submission or collection.

Original SCIP predecessor SHA256:
`41557726ecd93ab67a5764077ea18a35e08db4d6f97123a03ebd6b72930ebf68`.
Its original portable review is reproduced before the new claim; store a sealed
derivative and bind its hash, original source/plan/job and source-file inventory.
The exact original archive is rehashed on login/compute and after return.
Historical W archive81890b54… and all original workbook/population/order/
materialization hashes remain prerequisites. Compute verification never runs Git.

Keep exact numeric-step ownership and explicit release, local srun reaping,
phase and whole-step watchdogs, terminal Slurm accounting, independent product
review, and immutable positive/negative/partial collection. Operational
closed_feasible_arm remains a transport label, never scientific feasibility.
A no-incumbent result has null objective/economics/service/gaps; no raw placeholder
is a result. Native and common gap definitions remain distinct. Native return
may slightly exceed its requested ceiling; record actual times within the
separate late-return reserve rather than replacing them by the limit.

## External resource observation

The batch supervisor samples the released worker process tree from its own
process, independently of the solver's Python thread/GIL. No scientific module,
native setting, solver API callback or legacy sampling implementation is changed.
The observer verifies source/plan/job/step/release/PID and /proc start ticks
before probing; PID reuse or identity drift is rejected. It records nominal5s
samples, actual elapsed times, process-tree RSS/CPU/thread counts and inspection
errors. No worker cgroup memory is inferred from the batch process's cgroup.
CSV writes are streamed/bounded9000 samples; no synthetic zero for a disappeared
worker. Its final receipt and raw CSV travel with original evidence.

The portable review reports actual intervals and sampled peak; sparse/missing/
rejected observation remains explicit. It does not certify production isolation,
unobserved peaks, effective parallelism, lifetime utilization or causal observer
overhead. The original four-hour sampling limitation is not retrospectively fixed.
Scientific outcome, operational closure and observation completeness are distinct.

## Human-only handoff after this PR's qualified merge

No Codex NPAD connection, query, job or cancellation. No local clone/environment/
installation. All HPC files must be below the audit base or another allowed
model-agrologistic sibling. Transfer via MobaXterm, not scp.

Existing defaults:
- Base: /home/vrrcelestino/model-agrologistic-hygiene-audit
- Python: /home/vrrcelestino/venv313/bin/python
- Original W archive: .mvp2-scalar-r3a-h215-4h-v1/scalar-h215-evidence.tar.gz
- Original SCIP archive: .mvp2-scalar-scip-h215-w-8h-v1/scalar-scip-h215-w-evidence.tar.gz

Overrides use MVP2_SCIP8_W_BASE, MVP2_SCIP8_W_PYTHON,
MVP2_SCIP8_W_PREDECESSOR (original W) and
MVP2_SCIP8_W_SCIP_PREDECESSOR (original SCIP), always the same hash-bound files.
Inspect existing metadata/files read-only and ensure the new claim is absent.
Missing packages require human intervention; this wrapper installs nothing.

After exact-head qualification, obtain the full source pin and wrapper digest
from this PR's final review receipt. They are not develop or its moving merge
commit. The later human bootstrap is:

```bash
(
set -euo pipefail
SOURCE_SHA=FULL_QUALIFIED_40_HEX_SHA
WRAPPER_SHA256=FULL_QUALIFIED_64_HEX_DIGEST
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
test -d "$BASE"
CLI=$(mktemp -d "$BASE/scalar-scip-h215-w-native8h-cli-XXXXXXXX")
export TMPDIR="$CLI"
curl --fail --location --proto '=https' --tlsv1.2 \
  "https://raw.githubusercontent.com/unb-lamfo-or-ai-hpc/model-agrologistic/$SOURCE_SHA/scripts/npad_scalar_scip_h215_w_native8h.sh" \
  --output "$CLI/npad_scalar_scip_h215_w_native8h.sh"
printf '%s  %s\n' "$WRAPPER_SHA256" "$CLI/npad_scalar_scip_h215_w_native8h.sh" | sha256sum --check --strict
bash "$CLI/npad_scalar_scip_h215_w_native8h.sh" start "$SOURCE_SHA"
)
```

Save printed status/wait/collect commands for that SAME source/claim/job.
Ctrl-C from wait is safe; never rerun start. Transfer the new archive and external
.sha256 after terminal collection. Audit before interpreting or proposing a
further attempt. Preserve all limited/failed/preempted/OOM/rejected outcomes.
No third SCIP run, automatic HiGHS fallback, solver sweep or additional arm follows.

## Qualification before Ready

Public nonnative predecessor/design/budget/one-shot/terminal/forensic controls;
real separate-process /proc observation; real public tiny native SCIP worker/
controller/validation/collection and original portable replay; retained full
exact-head zero-skip Linux native gate and normal quality/analytical gates.
This is software qualification, not an NPAD observation or execution result.
Ask only for this PR's merge after Ready; supply its own pinned CLI afterwards.
