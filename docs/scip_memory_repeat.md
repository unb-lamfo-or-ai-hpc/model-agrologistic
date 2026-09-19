# Selective 300-hub SCIP memory-sensitivity repeat

This revision replaces the four-case repeat at commit `e5a2334`. Only the two
unsuccessful 300-hub variants are resubmitted. The running 215-hub experiments
are neither modified nor dependencies of these new jobs. Any independently
accepted original-budget results remain valid evidence and need not be repeated.
Do not submit both revisions for the same intended experiment.

## Research rationale

The 131072 MB value was an experimental configuration of `limits/memory`, not an
intrinsic maximum supported by SCIP. Both 300-hub baselines stopped
during the first service pass with `MEM_LIMIT`, without an incumbent. Each therefore
establishes a failure under that resource budget, not mathematical infeasibility
or an unconditional scalability limit of SCIP. Increasing a Slurm allocation alone
does not change this separately configured solver parameter.

SCIP 10.0.2 accepts a much larger memory limit. Its parameter definition explicitly
warns that reported memory usage is lower than actual memory usage. A solver limit
equal to the complete node allocation would consequently leave insufficient
headroom for unaccounted allocations. See the
[versioned SCIP parameter definition](https://github.com/scipopt/scip/blob/v10.0.2/src/scip/set.c)
and the [Slurm allocation documentation](https://slurm.schedmd.com/sbatch.html).

The repeated experiment requests all allocatable memory on one `intel-512` node
using `--exclusive --mem=0`. The supplied NPAD configuration reports
`RealMemory=512000` MiB, equivalent to 500 GiB of scheduler-configured memory,
not an application budget of 512 GiB. The new internal SCIP limit is **393216 MB**,
three times the previous value. The versioned
[SCIP stopping check](https://github.com/scipopt/scip/blob/v10.0.2/src/scip/solve.c#L181-L182)
multiplies this parameter by1048576 bytes:393216 corresponds to384 GiB, leaving
116 GiB between that threshold and scheduler-configured memory.
SCIP-accounted memory, process RSS, and scheduler memory are distinct measurements;
this arithmetic is not a guarantee of safety or of usable physical memory.

This is a conservative full-node operating protocol, not a claim that 393216 MB
is the largest technically accepted or empirically safe SCIP setting. A further
increase requires observed headroom and another explicit resource experiment.
In particular, `--mem=0` means all node memory in **Slurm**; setting
`limits/memory=0` does **not** mean unlimited memory in SCIP.

## Fixed and changed experimental factors

| Factor | Original campaign | Memory repeat |
| --- | --- | --- |
| Populations | 215 and 300 warehouses | Only 300; identical frozen 300-hub workbook |
| Route variants | Warehouse-only and direct-enabled | Both variants retained |
| Scenarios and horizon | Nine scenarios, 60 periods | Unchanged |
| Interhub network | Nearest 20% with audited connectivity repair | Unchanged |
| Optimization time budget | 28800 seconds | Unchanged |
| Relative gap target | 0.10, with stage-specific acceptance checks | Unchanged |
| Solver and LP implementation | SCIP with SoPlex | Same qualified environment |
| Solver thread setting | Four | Unchanged; exclusive allocation may reserve more CPUs |
| Internal memory limit | 131072 MB | 393216 MB |
| Slurm memory request | 192G, `intel-256` | All node memory, exclusive `intel-512` |

The partition and available resources change together. This is not an equal-memory
Gurobi-versus-SCIP benchmark, nor a pure hardware-controlled timing comparison.
No barrier substitution, presolve change, model change, or time-budget increase
is introduced. The 400-hub inputs remain preflight-only and are not admitted here.

## Isolation and execution

Use a new detached worktree at the exact reviewed commit and a new output directory.
Reuse the qualified Python executable without installing packages or modifying its
environment. The preparation helper verifies the original pilot admission,
qualification hashes, implementation identity, workbook hashes, and regenerated
manifests. Existing jobs, their outputs, and their checkouts remain untouched.

Git is required only on the submission host for the detached checkout and its
HEAD/cleanliness check. The compute worker does not execute Git. It verifies the
qualified numerical implementation, runtime versions, orchestration and solver/audit
entry-point hashes, frozen inputs, and exact campaign contract using Python before
preflight or optimization. The declared commit is exported for provenance; it is
not substituted for the compute-side content checks.

The first selective submission, array `2107697`, terminated before Python or SCIP
started because Git was unavailable on the compute nodes. Both elements exited
in less than the accounting display resolution. This is a launcher portability
failure, not a memory or solver outcome. Preserve its campaign and logs, then use
a new detached worktree, regenerated plan, and new output directory for the corrected
worker. Do not requeue the old job or edit its hash-bound plan in place.

Two array elements are admitted under `scip-memory-repeat-v2`:

| Array index | Warehouses | Direct origin-to-customer arcs |
| --- | --- | --- |
| 0 | 300 | Disabled |
| 1 | 300 | Enabled |

At most two repeated instances may run simultaneously. The submission helper checks
accounting for the two baseline array elements `2107114_1` and `2107114_2` only.
If either is still active, it becomes an `afterany` dependency; already terminal
baselines require no dependency. Unknown or absent accounting states stop
submission for review. Neither `2107034` nor `2107114_0` is queried or awaited.
The repeat may therefore run concurrently with the original 215-hub jobs on
other nodes, subject to scheduler admission and account resource limits.
The helper does not cancel jobs. An inherited `SBATCH_QOS` is cleared; no explicit
QoS is requested. A scheduler `--test-only` check precedes real submission, but
does not guarantee start time or future resource availability.
Partition sharing policies take precedence over a job's exclusivity request;
the captured allocation must therefore accompany any performance comparison.

Each worker records the allocated job and node configuration, checks the
`intel-512` capacity and all-node memory request, freezes a preflight snapshot,
runs one instance, and exports its audit even when the solver command fails.
The scheduler wall-time allowance is 12 hours to include model construction,
export, and auditing; the optimizer remains limited to eight hours.

Submission and execution claim directories prevent accidental duplicate runs.
If a submission check fails, preserve the directory and diagnose the cause before
preparing a fresh campaign; do not remove a claim to bypass the review.

## NPAD commands

Set `SCIP_MEMORY_SOURCE` to the full commit supplied with the reviewed PR update.
The following commands run inside a subshell so errors do not close an interactive
terminal. They fetch a ref but do not switch or pull any running checkout.

```bash
(
  set -euo pipefail
  REPO=/home/vrrcelestino/model-agrologistic
  : "${SCIP_MEMORY_SOURCE:?Set the reviewed full commit SHA first}"
  export SCIP_MEMORY_SOURCE
  git -C "$REPO" fetch origin research/scip-qualification
  MEMORY_WORK="$(mktemp -d /home/vrrcelestino/agrologistic-scip-memory-XXXXXX)"
  export SCIP_MEMORY_CHECKOUT="$MEMORY_WORK/source"
  git -C "$REPO" worktree add --detach "$SCIP_MEMORY_CHECKOUT" "$SCIP_MEMORY_SOURCE"
  export SCIP_PYTHON=/home/vrrcelestino/agrologistic-scip-pr31-4N2wGy/venv/bin/python
  export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
  cd "$SCIP_MEMORY_CHECKOUT"
  "$SCIP_PYTHON" -m ruff check .
  "$SCIP_PYTHON" -m pytest tests/test_scip_memory_campaign.py tests/test_scip_pilot.py -q
  export SCIP_MEMORY_ROOT="$REPO/data/results/hpc/scip-h300-memory-$(date -u +%Y%m%dT%H%M%SZ)"
  "$SCIP_PYTHON" scripts/prepare_scip_memory_campaign.py \
    --campaign-root "$SCIP_MEMORY_ROOT" \
    --data-root "$REPO/data/processed" \
    --reference-manifest "$REPO/data/results/hpc/scip-h215-warehouse-20260919T131233Z/campaign.yaml"
  bash scripts/submit_scip_memory_campaign.sh
)
```

## Evidence and acceptance

Return `memory_plan.json`, `submission.txt`, the scheduler accounting table,
and each case's `audit` directory, `lexicographic_stages.csv`, native log,
`independent_validation.json`, `run_summary.json`, and completion manifest.
Preserve original unsuccessful runs alongside these resource-amended results.
The per-case native log is `case-N/scip.log`. The audit products are
`case-N/audit/nine_audit_manifest.json`, `nine_results.json`, and
`nine_stage_gaps.json`; `N` is0 or1. The native memory limit and Slurm allocation
must accompany both accepted and unsuccessful results in comparative tables.

Acceptance still requires a valid incumbent, successful independent validation,
service certification, and completion of all required lexicographic stages within
the declared gap criterion. Neither job completion nor successful presolve alone
is acceptance. A no-incumbent run must not be described as achieving full service,
even if a derived summary field contains a default service ratio.

This repeat temporarily extends Sprint B before the final cross-solver comparison.
It can establish a resource-qualified frontier for the tested configurations;
it cannot establish an unconditional maximum network size.
