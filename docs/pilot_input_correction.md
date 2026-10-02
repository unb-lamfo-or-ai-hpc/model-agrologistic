# Audited correction of the 500-hub input

## Research contract

The pilot includes 215, 300, 400 and 500 hubs. A negative-distance input is corrected rather than excluded from the study. Accepted thesis-compatible and three-scenario inputs/results remain unchanged. A new nine-scenario campaign selects explicitly identified replacement workbooks without overwriting previous campaign manifests.

The historical 500-hub workbook with SHA256 `6fa1a28514b920f24e321a484a279d39158a3cb1946be903c783b636621c07eb` contains invalid negative distances. Preserve it as labeled development evidence. The existing OSRM client normalizes negative roundoff within its explicit one-metre tolerance, records normalization counts, and rejects non-finite or larger negative values. This applies to both fresh responses and cache reads. It is not an arbitrary Excel clipping operation, a geographic correction, or permission to substitute Haversine for numerical/API failures.

Rematerialization reuses the frozen PBF, image, profile, coordinates and persistent pair cache. Original cache records are not indiscriminately deleted. The output distance table is validated before writing and again after reading the persisted workbook. Input/output hashes and OSRM provenance identify the corrected artifact; a new hash alone does not establish scientific validity. The cache hash may change when legitimate new entries are added, so snapshot receipts describe a specific point in time. Run materializations sequentially when sharing that cache and its checksum receipts.

## 1. Verify identity and scheduling without submitting a job

Run the updated diagnostic block in [the sprint plan](research_delivery_sprints.md#immediate-npad-action-diagnostics-not-optimization). The actual source path is now known; require `matches_expected_sha256: true`. Previous `qos1` requests failed. Test the observed association QoS `preempt`, including its wall-time limits, before any real submission. A test-only success is not a reservation or protection from preemption.

The report `agrologistic-readiness-20260914T153047Z/scheduler/npad_readiness.json` confirms the expected source hash and successful `preempt` tests for both four and 25 CPUs at 192 GiB and twelve hours. Proceed to Step 2; repeating the complete diagnostic collection is unnecessary unless the environment changes. The immediate pre-submission check in Step 2 remains appropriate because queue state and admission can change.

## 2. Rematerialize 500 into a new output directory

The block below performs another scheduler test before submitting **one OSRM materialization job**, not an optimization campaign. Run only after reviewing the resource report. It retains the conservative 192-GiB allocation and the tested 25-CPU request for OSRM preprocessing. The scheduler also accepted the four-CPU request: the arithmetic estimate from `MaxMemPerCPU` is therefore not evidence that 25 CPUs are mandatory for every job. Solver threads remain four in the subsequent comparative campaign; this OSRM job uses its allocated CPUs for preprocessing. Record the actual allocation after submission.

The entire block is a subshell, so a failed check stops the block without closing the interactive terminal. No existing directory is overwritten. A repeat requires a new output path, not `--overwrite`.

```bash
(
set -e
cd /home/vrrcelestino/model-agrologistic
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
test -z "$(git status --porcelain)"
printf '%s  %s\n' \
  0d19865ac72eca0706960d10b6dbd1647a4951378a831715e39af8029ecb77f2 \
  /home/vrrcelestino/model-agrologistic-inputs/Warehouses_Existing_Candidate_All.xlsx \
  | sha256sum -c -
export SOURCE_COMMIT="$(git rev-parse HEAD)"
export TARGET_POPULATION=500
export INPUT_WORKBOOK=/home/vrrcelestino/model-agrologistic/data/processed/policy_population_v020/warehouses_500/model_input.xlsx
export FINAL_OUTPUT=/home/vrrcelestino/model-agrologistic/data/processed/nine_population_osrm_v1/warehouses_500
test -s "$INPUT_WORKBOOK"
test ! -e "$FINAL_OUTPUT"
sbatch --test-only --account=sxdsouza --partition=intel-256 --qos=preempt \
  --nodes=1 --ntasks=1 --cpus-per-task=25 --mem=192G --time=12:00:00 \
  scripts/materialize_policy_osrm_population.slurm
sbatch --parsable --account=sxdsouza --partition=intel-256 --qos=preempt \
  --nodes=1 --ntasks=1 --cpus-per-task=25 --mem=192G --time=12:00:00 \
  --export=ALL scripts/materialize_policy_osrm_population.slurm
)
```

Retain the returned job ID, Slurm output, and `osrm-agrologistic/audits/policy-500-job-<job ID>/policy-materialization-check.json`. Inspect the normalization count, persisted numeric validation, source counts, and output SHA256. The output includes `model_input.xlsx` and `osrm_materialization_audit.json`. These paths are not present until the job succeeds. Reaching `READY FOR REVIEW` does not automatically approve a Zenodo upload or solve the optimization model.

## 3. Build the missing populations and select corrected inputs

After verifying source identity, build only the missing 300/400 populations from the frozen ranking; do not resample or regenerate accepted results:

```bash
(
set -e
cd /home/vrrcelestino/model-agrologistic
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
/home/vrrcelestino/venv313/bin/python scripts/build_nine_population_workbooks.py \
  /home/vrrcelestino/model-agrologistic-inputs/Warehouses_Existing_Candidate_All.xlsx \
  --population-order data/processed/warehouse_population_v020/warehouse_population_order.csv \
  --output-dir data/processed/nine_population_inputs_v1 --populations 300 400
)
```

For each new level, use the materialization block above with `TARGET_POPULATION` set to 300 or 400, `INPUT_WORKBOOK` under `data/processed/nine_population_inputs_v1/warehouses_<population>/model_input.xlsx`, and `FINAL_OUTPUT` under `data/processed/nine_population_osrm_v1/warehouses_<population>`. Use absolute paths, wait for the preceding materialization to finish, and repeat the same resource checks. Do not submit a second 500 job while the first is running.

Once all three new workbooks have passed numeric/provenance review, generate a fresh eight-instance campaign:

```bash
(
set -e
cd /home/vrrcelestino/model-agrologistic
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
NINE_ROOT="data/results/hpc/nine-connectivity-corrected-$(date -u +%Y%m%dT%H%M%SZ)"
/home/vrrcelestino/venv313/bin/python scripts/prepare_nine_scenario_campaign.py \
  --campaign-root "$NINE_ROOT" \
  --workbook-override 300=data/processed/nine_population_osrm_v1/warehouses_300/model_input.xlsx \
  --workbook-override 400=data/processed/nine_population_osrm_v1/warehouses_400/model_input.xlsx \
  --workbook-override 500=data/processed/nine_population_osrm_v1/warehouses_500/model_input.xlsx
printf 'New campaign: %s/campaign.yaml\n' "$NINE_ROOT"
)
```

The 215-hub workbook remains at its existing path. Overrides resolve relative to the repository root and are recorded as explicit selections; they are not approvals and do not bypass numeric validation. Inspect all eight instances and the four interhub connectivity products before optimizing. The 25-million-variable guard remains a resource-review threshold, not a scientific exclusion of 500 hubs. If it is exceeded, report the estimated size and review memory before authorizing a larger construction budget. No claim is made that all populations will solve within eight hours or 10% gap.

## Acceptance and release

Separate input correction, resource admission, optimization quality and publication approval. Repaired inputs must have finite nonnegative distances, complete expected route counts, preserved non-distance data and explicit provenance. The model preflight must establish product-specific routes and directed multi-hop connectivity. Cross-solver comparisons require a qualified SCIP implementation, not merely an installed PySCIPOpt package. Zenodo remains a draft until rights, content, checksums and reproducibility have been reviewed.
