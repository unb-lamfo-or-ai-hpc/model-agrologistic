# One scalar SCIP STO h215 W observation and S6-A reconciliation

## Terminal correction — 28 October 2026

The one authorized original observation is complete and independently audited:
job2225638, native timelimit, zero solutions, no usable incumbent. Preserve the
original claim, source cbd64d86, plan1af2f262 and archive41557726.
The preparation/start instructions below are historical, not a new execution
handoff. Do not run start again or alter the consumed claim.
Read [the original results](mvp2_scalar_scip_h215_w_results.md).
The researcher's subsequent longer-window and multisolver planning request is
recorded in [the active completion plan](mvp2_completion_plan_20261028.md).
Its future operational package needs its own qualification, merge and human CLI.


27 October 2026. S5 closed by the authorized PR130 merge
`b031c3d1014df433020a6bb98534b9b9d8de4ffb`. The researcher requests one
SCIP h215 W test and parallel h500/manuscript reconciliation. This is the complete
preparation package; its own qualified merge precedes the pinned human CLI.
No agent accesses NPAD or runs a production instance. No local clone or
environment is edited and no package is installed.

## Question, comparison and interpretation registered before execution

Can this existing native SCIP implementation construct and solve the frozen
scalar STO h215 W model to an independently validated incumbent with a common
gap at most 1% within the declared envelope? Every outcome is retained,
including success. This is not an experiment designed to demonstrate failure.

Use historical Gurobi W STO job2217990, source5f73871b…, plan e9f9b26c…,
archive81890b546d720ad5999d11f44fd499337aad937e32773db39067796f73660534
as the unchanged descriptive control. Its native runtime is2445.52s and its
attained gap0.740159%; it is not rerun. Different node workload, implementation
overhead, solver numerical/search defaults and attained gaps preclude a causal
speedup claim or a controlled ranking. Build/API failure is an implementation
or construction outcome, not proof about a solver algorithm.

Historical hierarchical SCIP trials used different objectives/stopping rules.
Preserve them as a separate cohort. Do not migrate those old launchers, reuse
their claims or treat their no-incumbent results as scalar SCIP observations.
A single censored scalar test cannot establish that all open-source solvers,
all settings or all larger populations are unable to solve this model.

## Frozen science and prospective resource ledger

| Setting | One SCIP observation |
| --- | --- |
| Case | scalar_scip_h215_w, STO, warehouse-only W; no direct OC arcs |
| Input | Original h215 workbook SHA25640edb66585daca9cc393cab1f86bde6d4528a5f34b6afc57260cc1684396da4e |
| Population |215,146 existing/69 candidates; exact original membership/order |
| Horizon/scenarios |60 periods,two products,nine Cartesian scenarios,1/9 each |
| Graph | Original OD3182/DC3440/DD18490/OC0; exact mathematical-contract comparison |
| Objective | Scalar penalty, original90000/45000/45000 indexed rates/units |
| Validator | Existing original-unit validator, absolute1e-5/relative1e-8 |
| Native backend | PySCIPOpt6.2.1 / SCIP10.0.2 / SoPlex8.0.2, verified banner |
| Optimization | One cold sequential optimize call, native14400s wall-clock ceiling |
| Quality | Common incumbent-denominator gap <=0.01; native SCIP gap retained separately |
| Threads/seed | Four-thread ceiling/seed42; no observed parallelism inferred |
| Native memory | limits/memory=163840 SCIP MB, not process RSS or Gurobi SoftMemLimit |
| Pre-build guard |16M shared-formulation variables; no pruning/model/indicator rewrite |
| Allocation | One intel-256 node,24logical CPUs,192GiB,8h,account sxdsouza,QoS preempt,no requeue |
| Worker affinity |16logical-CPU srun pool; four solver threads within it |
| Phases | Input/build3600s; native14400s; shared late-return/export900s; validation1800s |
| Total step/setup/reserve |20700s/1800s/6300s =28800s reservation |
| Transfer |1GiB expanded/4096regular members; no truncation |

The current backend's strict native numerical settings are retained, including
the effective feasibility tolerance and native indicators. This package edits
no scientific source, scenario, cost, route, original certificate, accepted
manifest or old launcher. The case template changes only solver identity/options,
logging/name and prospective size guard relative to historical W STO.
Compaction remains off. No Gurobi environment, WLS probe or license file is used
for the SCIP observation.

SCIP documents a different native relative-gap denominator and warns that its
memory accounting can underestimate real memory; keep native/common gap and
SCIP memory/application RSS/Slurm MaxRSS separate. Thread parameters are ceilings,
not evidence of concurrent SCIP search or multithreaded SoPlex. See the official
[SCIP parameters](https://scipopt.org/doc/html/PARAMETERS.php) and
[PySCIPOpt model API](https://pyscipopt.readthedocs.io/en/v6.2.1/api/model.html).
The bound/common-gap policy is unchanged, including missing/nonfinite or inverted
bounds. No clipping or relaxed tolerance creates an accepted result.

## Complete operational chain

The new driver is `scripts/mvp2_scalar_scip_h215.py`; its human wrapper is
`scripts/npad_scalar_scip_h215_w.sh`. Both use a new exclusive claim
`.mvp2-scalar-scip-h215-w-8h-v1` inside the existing audit base. No old claim is
deleted, reset or repurposed.

Before submission, require the exact raw Git bytes, original W archive replay,
all scientific-source identities, input/membership/materialization hashes,
installed PySCIPOpt metadata/native-library fingerprints and Python identity.
Login preparation imports no solver and installs nothing. A durable submission
intent precedes exactly one sbatch. Any uncertain/rejected submission consumes
the claim; inspect it rather than retrying start. Existing start always refuses.

Batch/worker verify source bytes without Git on compute, interpreter/libraries,
allocation owner/node/CPU/memory/time and tool hashes. The worker waits for the
parent's exact numeric-step ownership/release. All logs and temporary outputs
are under the dedicated project directory. Native build provenance and nine
fresh scalar analytical/Excel/independent-validation tests run on compute before
the population model. Unexpected/missing libraries or a failed tiny gate stop
before that model and remain forensic evidence.

The unchanged backend emits existing resource phases. A worker-local observer
forwards those phase boundaries to the already-qualified parent watchdog;
it does not modify equations, indicators or SCIP optimization settings.
No-incumbent returns still complete the original export/validator path.
Only an owned exact numeric step may be signalled; no guessed PID/job or broad
scancel is used. Release, phase clocks, terminal step/accounting, original
validation and effective native parameters must agree in portable review.

A non-feasible observation may be operationally complete. The inherited
controller's internal closed_feasible_arm label indicates completed transport
and review only; it is not scientific feasibility or quality acceptance.
The final reviewer separately classifies:

| Observation | Interpretation |
| --- | --- |
| quality_target_met | Original independent validation accepted and common gap <=1% |
| validated_feasible_above_target_or_uncertified_bound | Accepted incumbent, insufficient quality/bound certificate |
| incumbent_validation_rejected | Returned candidate fails the unchanged validator |
| no_usable_incumbent | Solver returned no usable incumbent within its limits |
| build_or_execution_incomplete | Missing products, failed build, external kill, admission or runtime failure |

Scheduler TIMEOUT/OOM/preemption/cancellation, exceptions, phase stops and missing
receipts retain their accounting/controller/resources/native logs. Normal
scheduler completion alone is never quality acceptance. The collector preserves
negative/partial terminal evidence, reuses an existing immutable collection and
never overwrites a changed archive. Public miniature qualification workbooks are
retained only under their generated qualification directory; private population
workbooks/licenses/databases are excluded. Generated pytest internal aliases are
not followed or archived. Any transfer-cap violation stops without truncation.

## Manual read-only inventory before first execution

Run this at NPAD login and return its JSON. It creates no file, imports no solver,
queries no scheduler and submits nothing. If the existing default environment
lacks PySCIPOpt6.2.1, report the path of an EXISTING qualified SCIP Python; set
MVP2_SCIP_W_PYTHON to it after review. No installation/environment creation is
part of this handoff.

```bash
(
set -euo pipefail
PY=${MVP2_SCIP_W_PYTHON:-/home/vrrcelestino/venv313/bin/python}
"$PY" -B -I - <<'PY'
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import sys
base = Path("/home/vrrcelestino/model-agrologistic-hygiene-audit")
data = Path("/home/vrrcelestino/model-agrologistic/data/processed")
paths = {
    "h215_workbook": (data / "policy_population_v020_osrm/warehouses_215/model_input.xlsx",
        "40edb66585daca9cc393cab1f86bde6d4528a5f34b6afc57260cc1684396da4e"),
    "original_W_archive": (base / ".mvp2-scalar-r3a-h215-4h-v1/scalar-h215-evidence.tar.gz",
        "81890b546d720ad5999d11f44fd499337aad937e32773db39067796f73660534"),
    "population": (data / "warehouse_population_v020/warehouse_population_manifest.json",
        "4134147f45188d2e8722476dd325b40e584c3746affe99889e045a547d283505"),
    "order": (data / "warehouse_population_v020/warehouse_population_order.csv",
        "7a524b2ed69b41481264d8049842b37e27cd3b96cc20d4e96d98eaf2a39e7903"),
}
checks = {}
for name, (path, expected) in paths.items():
    row = {"regular_unlinked_file": path.is_file() and not path.is_symlink()}
    if row["regular_unlinked_file"]:
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        row.update(sha256=digest, expected_match=digest == expected)
    checks[name] = row
packages = {}
for name in ("pyscipopt", "numpy", "pandas", "openpyxl", "PyYAML", "pytest", "ruff"):
    try:
        packages[name] = metadata.version(name)
    except metadata.PackageNotFoundError:
        packages[name] = "missing"
sidecar = data / "policy_population_v020_osrm/warehouses_215/osrm_materialization_audit.json"
claim = base / ".mvp2-scalar-scip-h215-w-8h-v1"
print(json.dumps({
    "scope": "read_only_metadata_hashes_no_solver_scheduler_or_files_created",
    "python": sys.version.split()[0], "python_path": sys.executable,
    "packages": packages, "inputs": checks,
    "materialization_regular": sidecar.is_file() and not sidecar.is_symlink(),
    "claim_exists": claim.exists(), "claim_symlink": claim.is_symlink(),
    "execution_admitted": False,
}, indent=2))
PY
)
```

A missing original W archive can be transferred with MobaXterm to an explicit
project subdirectory; set MVP2_SCIP_W_PREDECESSOR to that SAME hash-bound archive.
Never regenerate inputs/OSRM or substitute a newer workbook.

## Pinned human CLI after this PR's authorized merge

Codex supplies the final exact source and wrapper SHA256 after all exact-head
Linux native/analytical/quality/manuscript gates pass. Replace the variables
below with those pins; a moving develop ref is not sufficient. A source checkout
below the NPAD audit base is separate from, and never modifies, the preserved
input checkout or the user's local clone.

```bash
(
set -euo pipefail
SOURCE_SHA=FULL_REVIEWED_40_HEX_SOURCE
WRAPPER_SHA256=FULL_REVIEWED_64_HEX_WRAPPER_DIGEST
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
test -d "$BASE"
CLI=$(mktemp -d "$BASE/scalar-scip-h215-w-cli-XXXXXXXX")
export TMPDIR="$CLI"
curl --fail --location --proto '=https' --tlsv1.2 \
  "https://raw.githubusercontent.com/unb-lamfo-or-ai-hpc/model-agrologistic/$SOURCE_SHA/scripts/npad_scalar_scip_h215_w.sh" \
  --output "$CLI/npad_scalar_scip_h215_w.sh"
printf '%s  %s\n' "$WRAPPER_SHA256" "$CLI/npad_scalar_scip_h215_w.sh" | sha256sum --check --strict
bash "$CLI/npad_scalar_scip_h215_w.sh" start "$SOURCE_SHA"
)
```

Save the printed JOB_ID, claim and driver paths. Use the printed status/wait/
collect commands for the same source/claim. Ctrl-C from wait is safe and does
not authorize start again. Transfer the terminal archive and external checksum
with MobaXterm for independent audit here; do not use scp or provide an SSH key.
No terminal file is assumed to exist before that actual execution.

## HiGHS and manuscript continuation

HiGHS is a conditional candidate after the SCIP observation is reviewed, not an
automatic fallback. Before a new backend/experiment, identify actual version/API
support for the indicator implications (or prove a bounded equivalent
reformulation), retain finite coefficient bounds and the independent validator,
qualify analytical/parity/resource/export/lifecycle cases and review a complete
separate resource package. No arbitrary Big-M, changed penalty or omitted
indicator is allowed. A failed SCIP build does not by itself justify declaring
a generic open-source computational limit. See the official
[HiGHS project](https://highs.dev/) for the solver's scope; there is no HiGHS
performance observation in this repository's current scalar cohort.

This same PR integrates original h500 into the scalar source and every relevant
table/abstract/conclusion, reconciles eleven observations with the separate D
pair, updates Appendix D traceability and keeps the h500 geographic figure
explicitly input-only. Appendix A bytes, author order, dataset publication
receipt, older certificates and historical comparison are preserved. The old
Pages approval belongs to the earlier source snapshot and is not rewritten:
rendering the draft is not deploying it.

Next: researcher executes the pinned one-shot CLI after qualified merge; audit
that original SCIP outcome in a results PR; finish integrated coauthor S6-A and
S6-B reproducibility/rights/declarations/author decisions. No additional
experiment is automatic, including HiGHS. GAMS compilation/numerical parity
remain unperformed; S3/S4 cancelled and EVPI/VSS excluded.
