# Nine-scenario research delivery plan

## Scope and baseline

The accepted thesis-compatible and three-scenario results remain frozen. The new study uses nine scenarios, populations of 215, 300, 400 and 500 hubs, and direct arcs enabled/disabled. The nearest-20% interhub baseline plus explicitly audited directed connectivity repair remains the network contract. Larger populations, Benders and a definitive scalability frontier are outside this delivery cycle.

Each solver receives 28,800 seconds of optimization time across the complete objective hierarchy. The intended Slurm allocation is twelve hours, allowing preprocessing, construction and output validation. A relative gap target of 0.10 does not replace domestic-service, material-balance, activation, unit or independent feasibility requirements. Report pass incumbent/bound/gap and final-solution degradation separately. Missing or undefined gaps must not become zero.

## Three short sprints

| Sprint | Deliverables | Exit evidence | Indicative active effort |
|---|---|---|---|
| 1. Qualify inputs and resources | Reconcile the original population workbook by hash; construct 300/400 inputs using the frozen rank; rematerialize the invalid 500-hub OSRM input into a new directory; inspect all eight models; verify account/QoS/memory constraints; prepare per-file Zenodo review plan | Source identity confirmed; nonnegative finite distances; four connectivity products; exact model counts; scheduler test-only receipts; curator review list | 1–2 working days, plus OSRM queue time |
| 2. Qualify SCIP and measure the bounded campaign | Implement native PySCIPOpt backend; analytical and cross-solver parity; same frozen graph and hierarchy; run 215-hub pilots, then 300/400/500 only after resource gates; collect stage bounds, gaps, timers and memory | Cross-solver fixtures pass; each requested instance has a success or explicit censored/failure record; no silent omission | 3–5 working days of implementation and analysis, plus HPC queue/execution time |
| 3. Freeze and communicate evidence | Reconcile tables/figures and manuscript; label historical and new results; create reviewed, checksum-verified archives; reproduce selected outputs from the packaged inputs; upload draft and publish a frozen dataset version after release review | Paper-to-run traceability, archive checksums, license/attribution matrix, reproduction receipt and public dataset record | 1–2 working days; curation can start during Sprint 2 |

These are planning estimates, not a completion guarantee. Sixteen full cross-solver runs have a maximum nominal optimization allowance of 128 job-hours. At two concurrent tasks this alone is up to 64 elapsed hours, excluding queueing, data preparation, setup and reruns. Failure due to memory can prevent an optimization from reaching its time budget. The study should report that outcome rather than repeatedly increasing resources without a decision gate.

SCIP is currently an integration point, not an implemented backend. Installing `pyscipopt` does not release the SCIP campaign. Freeze identical graph/scenario/input hashes, solver versions, solver threads, allocated CPUs, memory limits, numerical tolerances and objective degradation semantics for the comparison. Do not transfer Gurobi-specific parameter names directly to SCIP. Use a single remaining-time budget across sequential objective passes, and retain independent validation even when a solve reaches a time or memory limit.

## Current evidence and blockers

Update from the NPAD report dated 14 September 2026 at 15:30 UTC: all 50 focused tests passed on `ee8a8bd`, the external source workbook matches its expected SHA256, and both four-CPU and 25-CPU requests with `preempt`, 192 GiB and a twelve-hour wall time passed `sbatch --test-only`. No job was submitted by these checks. GitHub Actions run `34862312153` also succeeded. This qualifies the next materialization request, not the resulting distances or optimization campaign. Earlier observations below retain their historical context. See [the readiness receipt](pr29_readiness_evidence.md).

- NPAD targeted regression: 50 tests passed on commit `73ec72c`; a further 30 readiness/campaign tests passed on `fb552d3`.
- 215-hub preflight: 14,054,654 variables without direct arcs and 14,374,334 with direct arcs. No added repair edges were reported. An active/open network remains distinct from the potential graph.
- 300/400: required OSRM workbooks absent.
- 500: workbook SHA256 `6fa1a28514b920f24e321a484a279d39158a3cb1946be903c783b636621c07eb` fails nonnegative DD-distance validation. Retain the old input as evidence, not as a validated release asset. Use the existing audited OSRM numeric-normalization path; do not replace arbitrary negative distances with zero in Excel.
- The population registry workbook was located outside the inventoried data tree at `/home/vrrcelestino/model-agrologistic-inputs/Warehouses_Existing_Candidate_All.xlsx`. Its expected SHA256 is `0d19865ac72eca0706960d10b6dbd1647a4951378a831715e39af8029ecb77f2`; existence does not establish hash identity or redistribution rights.
- Association output reports `sxdsouza` / `preempt`, whereas the proposed job requests `qos1`. Partition `AllowQos=ALL` does not establish user association permission.
- Both four-CPU and 25-CPU test-only requests with `qos1` failed with `Invalid qos specification`. Test `preempt` explicitly before submission. The observed partition `PreemptMode=CANCEL` must be retained in the resource record; it does not establish when a particular job will be preempted. Interrupted runs must remain identifiable and cannot be reported as completed optimization budgets.
- The partition reports `MaxMemPerCPU=8000`. At 192 GiB, the simple arithmetic floor is 25 allocated CPUs. This is an advisory calculation, not a prediction of Slurm allocation. Keep solver threads at four during the comparison and report any additional CPU reservation required for memory. Confirm by `sbatch --test-only` and the eventual allocation receipt.

The older unconditional pilot submission example must not be used until these resource checks are resolved. A successful test-only response means the request passed that scheduler check; it does not reserve resources or guarantee eventual availability.

## Immediate NPAD action: diagnostics, not optimization

Use the dependent PR branch `research/pilot-readiness-curation`. This branch includes PR28 changes; neither PR needs to be merged to run read-only diagnostics. Keep the outputs outside `data` to avoid recursive inventories.

```bash
(
set -e
cd /home/vrrcelestino/model-agrologistic
git fetch origin
git switch research/pilot-readiness-curation
git pull --ff-only origin research/pilot-readiness-curation
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
PYTHON=/home/vrrcelestino/venv313/bin/python
"$PYTHON" -m ruff check .
"$PYTHON" -m pytest tests/test_release_readiness.py tests/test_nine_campaign.py
REPORT_ROOT="/home/vrrcelestino/agrologistic-readiness-$(date -u +%Y%m%dT%H%M%SZ)"
"$PYTHON" scripts/collect_npad_readiness.py \
  --output-dir "$REPORT_ROOT/scheduler" \
  --account sxdsouza --partition intel-256 --qos preempt --test-scheduler \
  --source-workbook /home/vrrcelestino/model-agrologistic-inputs/Warehouses_Existing_Candidate_All.xlsx \
  --campaign-manifest /home/vrrcelestino/model-agrologistic/data/results/hpc/nine-connectivity-20260914T144027Z/campaign.yaml
"$PYTHON" scripts/plan_zenodo_deposit.py \
  /home/vrrcelestino/zenodo-agrologistic-inventory-20260914T145244Z/data_inventory.json \
  --output-dir "$REPORT_ROOT/zenodo"
printf 'Readiness reports: %s\n' "$REPORT_ROOT"
cat "$REPORT_ROOT/scheduler/npad_readiness.json"
)
```

Return `npad_readiness.json`, particularly source-hash matching and test-only responses. Do not print license files or environment secrets. The collector reports installed package versions without starting either solver. PySCIPOpt 6.2.1 is installed on the reported NPAD environment, but the project backend still requires implementation and parity validation.

`collect_npad_readiness.py --test-scheduler` issues only `sbatch --test-only`, comparing four CPUs with the arithmetic memory reservation when that limit is available. It does not submit or execute jobs, change QoS, load modules or alter data. Command failures remain in the report. The script deliberately does not certify all inputs from file existence alone.

## Zenodo release boundary

The existing draft is https://zenodo.org/uploads/22751909, reserved DOI `10.5281/zenodo.22751909`. It is not a published dataset. The inventory contains 1,378 files and 2,194,452,025 bytes; it is a metadata inventory, not a content or rights audit.

The curation planner proposes packages for canonical inputs, processed inputs, validation evidence, publication outputs, historical releases, negative results and ongoing experiments. All file approvals remain false. Sensitive filenames and regenerable software artifacts are excluded; the known invalid 500-hub input is blocked from publication as a validated input by hash, even if renamed. Duplicates are disclosed rather than deleted, because removing files can invalidate release checksum contracts. Directory names do not prove scientific acceptance.

The 500-hub population remains a required campaign level. The restriction concerns one defective artifact, not the experimental population. Correct it through audited OSRM rematerialization; retain the original and link its replacement by input/output hashes and normalization provenance. The received curation CSV contains 1,378 rows with all upload approvals false; neither this implementation nor source discovery changes those decisions. See [500-hub correction and new input selection](pilot_input_correction.md).

Before uploading, review source rights, private content, input validity and the exact executions supporting the paper. Include failed experiments as labeled evidence; do not place incomplete campaign outputs among final comparative results. MIT applies to project code, not automatically to registry or OSM-derived data. Finalize attribution and per-asset licensing before release.

Publication of the current paper's reproducible evidence need not wait for future SCIP or larger-hub results. New results may be released as a later version. Publication is gated on curated archives, checksum verification, reproduction from the package and curator approval. The planner neither compresses nor uploads files and never publishes a record.

## Pull request sequencing

PR28 provides graph repair and the pilot generator. The dependent readiness/curation PR delivers Sprint1 diagnostics and this plan without modifying model equations or accepted experiment definitions. Retarget it to develop after PR28 merges. The subsequent implementation PR supplies SCIP parity and campaign orchestration; a final evidence/publication PR updates reports and the manuscript. Review and acceptance are separate from job submission.

## References for operational policy

- Slurm resource-limit hierarchy: https://slurm.schedmd.com/resource_limits.html
- Slurm submission and test-only options: https://slurm.schedmd.com/sbatch.html
- Zenodo record/version boundaries: https://help.zenodo.org/docs/deposit/about-records/ and https://help.zenodo.org/docs/deposit/manage-versions/
