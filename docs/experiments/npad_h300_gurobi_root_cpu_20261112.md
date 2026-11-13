# h300 Gurobi root LP campaign on NPAD

The frozen h300 W STO matrix is evaluated with Gurobi 13.0.3 and Pyomo/APPSI 6.10.1. The matrix and four input files are checked against the earlier campaign before construction and optimization. Native gurobipy observations remain a separate reference cohort.

| Factor | Levels |
| --- | --- |
| Initial LP algorithm | 1 dual simplex, 2 barrier, 4 deterministic concurrent, 6 PDHG |
| Heuristic profile | Standard effort 0.05; standard effort 0; effort 0.05 with NoRel work limit 600 |
| Solver threads | 1, 2, 4, 8, 16 |
| Repetition | Three temporal blocks, each with a seeded permutation of 60 cells |

The work limit is in Gurobi work units. It does not specify a duration or equal CPU expenditure across thread ceilings. The standard effort of zero is a control for the Heuristics parameter. Presolve, cuts and all other specialized heuristics use their existing defaults. ConcurrentMIP is 1. PDHGGPU is 0. PDHGMIPHeur parameters are outside the pinned 13.0 experiment.

Each cell reserves 192 GiB on one exclusive intel-256 node. The allocation must expose 16 distinct physical cores on one socket. The process and its children inherit a mask of the selected number of physical cores, with one logical CPU per core. The solver budget is eight hours. A 12-hour allocation includes construction, validation and export. The cgroup guard samples the whole job and stops the owned worker when it reaches the E1 job threshold. SoftMemLimit is a separate Gurobi limit of 160 decimal GB. The analysis uses the original solution validator and the 1% common MIP gap.

The plan has 180 solves in one Slurm array with concurrency capped at one. Slurm controls the order in which array tasks run. The scheduler dependency admits the array after a public job checks the 192 GiB cgroup, physical affinity, license capacity, version and the method/heuristic settings on small models. Treat missing, failed, censored and validated outcomes separately. Array task failures remain visible and do not trigger retries. A conservative storage check runs before and after every task. 48 GiB is the default campaign budget with the existing external reserve. Review current quota and maximum array size before launch.

## NPAD operator commands

Execute from the login node. Set SOURCE to the full reviewed commit of this PR. The workflow makes one fresh claim under the audit directory. The submit command stages the public control and the held array, then releases the array with the public job dependency. Keep the printed job IDs and the path to this checkout.

```bash
set -euo pipefail
umask 077
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
PY=/home/vrrcelestino/venv313/bin/python
SOURCE='<full reviewed 40-character commit>'
test -d "$BASE"
[[ "$SOURCE" =~ ^[a-f0-9]{40}$ ]]
mkdir -p "$BASE"
SRC=$(mktemp -d "$BASE/h300-root-cpu-source-XXXXXXXX")
git -C "$SRC" init -q
git -C "$SRC" fetch --depth=1 https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic.git "$SOURCE"
git -C "$SRC" checkout --detach FETCH_HEAD
test "$(git -C "$SRC" rev-parse HEAD)" = "$SOURCE"
sinfo -p intel-256 -N -o '%N %T %c %m'
scontrol show config | awk '/MaxArraySize|MaxJobCount|MaxSubmitJobs/'
quota -s
"$PY" -B -I "$SRC/scripts/h300_gurobi_root_campaign.py" plan > "$SRC/grid.json"
"$PY" -B -I "$SRC/scripts/h300_gurobi_root_campaign.py" submit "$SOURCE" --budget-gib 48
```

Use the same checkout and source SHA for readback. If launch is interrupted or reports an error, preserve the claim and inspect its submission receipts before any further scheduler action.

```bash
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
PY=/home/vrrcelestino/venv313/bin/python
CLAIM="$BASE/.mvp2-h300-gurobi-root-cpu-v1"
cat "$CLAIM/submission.json"
test ! -f "$CLAIM/qualification.json" || cat "$CLAIM/qualification.json"
OUT=$(mktemp -d "$BASE/h300-root-cpu-readback-XXXXXXXX")
"$PY" -B -I "$SRC/scripts/h300_gurobi_root_campaign.py" report "$SOURCE" \
  > "$OUT/configurations.csv" 2> "$OUT/accounting.txt"
sha256sum "$OUT/configurations.csv" "$OUT/accounting.txt"
```

The summary reports final objective, bound, common gap, validation, timing and cgroup memory where observed. Native logs remain in each cell directory and provide root relaxation and incumbent events at logged precision. A log event can supply a time to a recorded incumbent or gap. Its interpretation still depends on which exported solution was independently validated. Compare speedup against the one-thread run of the same method and heuristic profile. Report the full-MIP and root clocks, memory and the count attaining the common target together.

