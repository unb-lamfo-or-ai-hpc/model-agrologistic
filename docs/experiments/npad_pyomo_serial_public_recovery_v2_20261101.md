# Public serial recovery v2 — same five probes, one new test job

The original v1 claim and source remain preserved. The field mismatch is now
confirmed: Slurm reports `NumNodes=1-1` for an exact one-node held request.
The corrected code accepts precisely `1` or `1-1`, retaining every other check.
Do not rerun the historical v1 preparation or smoke-submission block.

Code candidate: `63543161f2fc6864a157b9f68b6a9347c65813a9`.
Scientific engine remains `c493be8cd127c5175fc7eb111400229e64b8e3c0`.
Ruff and 132 local tests passed without failures/errors/skips. NPAD acceptance
requires 243 tests (111 original plus132 current), actual dependency semantics,
allocation/license/source/runtime and original-receipt preservation.

The block below checks the failed v1 plan, all15 supplied original receipt hashes,
script hashes and current held ownership/profile/dependencies, then releases only
**2231659,2231660,2231661,2231662,2231663**. It writes recovery records in a fresh
v2 claim and submits only one new main qualification job. A failed probe and
its never-started cancelled child are expected. Gurobi2231593 is waited upon
if still active. No population model, installation or private queue release occurs.

The standalone wrapper has SHA-256 `4cc656eb6cb14f93b24be3abacd78cefaef7f9c66008990a3b6f1d7c990d8fbe` and passed
`bash -n`. Run it once from human NPAD login. Any existing v2 claim or ambiguous
response must be preserved and reported; do not retry, overwrite or cancel jobs.

```bash
#!/bin/bash
# Human NPAD login only. Recover five existing probes; one new public test job.
(
set -euo pipefail
umask 077
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
PY=/home/vrrcelestino/venv313/bin/python
SOURCE_SHA=63543161f2fc6864a157b9f68b6a9347c65813a9
PUBLIC="$BASE/.mvp2-pyomo-scaling-serial-public-v2"
test -d "$BASE"
test -x "$PY"
if [[ -e "$PUBLIC" || -L "$PUBLIC" ]]; then
  printf 'PRESERVE_EXISTING_PUBLIC_CLAIM=%s; nao repita a submissao\n' "$PUBLIC"
  exit 2
fi
printf '\nESPACO COMPARTILHADO; NAO COMPROVA QUOTA PESSOAL\n'
df -h "$BASE"
if command -v quota >/dev/null 2>&1; then quota -s || true; fi
PREP=$(mktemp -d "$BASE/pyomo-serial-recovery-cli-XXXXXXXX")
printf 'PRESERVE_BOOTSTRAP=%s\n' "$PREP"
cd "$PREP"
curl --fail --location --retry 0 --connect-timeout 20 --max-time 300 \
  "https://codeload.github.com/unb-lamfo-or-ai-hpc/model-agrologistic/tar.gz/$SOURCE_SHA" \
  -o source.tar.gz
for SCRIPT in pyomo_serial_queue.py pyomo_serial_smoke.py qualify_pyomo_serial.py pyomo_serial_storage.py
do
  curl --fail --location --retry 0 --connect-timeout 20 --max-time 120 \
    "https://raw.githubusercontent.com/unb-lamfo-or-ai-hpc/model-agrologistic/$SOURCE_SHA/scripts/$SCRIPT" \
    -o "$SCRIPT"
done
printf '%s  pyomo_serial_queue.py\n' \
  '38bd7b97a346c0973554ea8ea2e3226ed82cdf3f27f807f7a7d8460de790225e' | sha256sum -c -
printf '%s  pyomo_serial_smoke.py\n' \
  '4505cee2a1ba7280808733f12f1dc63ec75f6c301b407c454a25acf1a86dc2e9' | sha256sum -c -
printf '%s  qualify_pyomo_serial.py\n' \
  'a58e3d36b6f376f1ef2616e9fe7a97bbf968779d459a601a418e04f9dad948a0' | sha256sum -c -
printf '%s  pyomo_serial_storage.py\n' \
  'b6ed67eff404760365d03c55a2e3cbfccd96d831476a721352bd3a1ffb84d363' | sha256sum -c -
"$PY" -B -I "$PREP/qualify_pyomo_serial.py" prepare \
  --claim "$PUBLIC" --source-sha "$SOURCE_SHA" --source-archive "$PREP/source.tar.gz"
"$PY" -B -I "$PUBLIC/source/scripts/qualify_pyomo_serial.py" recover \
  --claim "$PUBLIC" --source-sha "$SOURCE_SHA"
DEPENDENCY=$(cat "$PUBLIC/qualification-dependency.txt")
[[ "$DEPENDENCY" =~ ^afterany:[1-9][0-9]*(:[1-9][0-9]*){4,5}$ ]]
mkdir "$PUBLIC/submission-intent"
printf '%s\n' "$DEPENDENCY" > "$PUBLIC/submission-intent/dependency.txt"
SUBMITTED=$(sbatch --parsable --account=sxdsouza --partition=intel-256 --qos=preempt \
  --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=32G --time=00:45:00 \
  --exclusive --no-requeue --kill-on-invalid-dep=yes --dependency="$DEPENDENCY" \
  --chdir="$PUBLIC" --output="$PUBLIC/slurm-%j.out" --error="$PUBLIC/slurm-%j.err" \
  "$PUBLIC/qualification.sh")
printf '%s\n' "$SUBMITTED" > "$PUBLIC/submitted-job.txt"
JOB="${SUBMITTED%%;*}"
[[ "$JOB" =~ ^[1-9][0-9]*$ ]]
printf 'PUBLIC_SERIAL_QUALIFICATION_JOB=%s\nPRESERVE_CLAIM=%s\n' "$JOB" "$PUBLIC"
printf 'STATUS_COMMAND=sacct -j %s --format=JobID,State,Elapsed,ExitCode,MaxRSS,AllocCPUs\n' "$JOB"
printf 'REPORT_COMMAND=cat %s/result.json\n' "$PUBLIC"
printf 'EXPECTED=243_TESTS_ZERO_FAILURES_ERRORS_SKIPS_PLUS_FIVE_DEPENDENCY_PROBES\n'
printf 'ONE_INTENTIONAL_FAILED_PROBE_AND_ONE_NEVER_STARTED_CANCELLED_CHILD_ARE_EXPECTED\n'
printf 'PUBLIC_CONTROLS_ONLY; SAME_FIVE_PROBES_RECOVERED_ORIGINAL_V1_T1_T16_PRESERVED; NO_PRIVATE_START_OR_RETRY\n'
)
```

After the main job is terminal, send its printed STATUS_COMMAND and REPORT_COMMAND,
then the following receipts. Missing reports or rejected controls require manual
inspection of the same namespace, not another preparation/submission.

```bash
(
set -euo pipefail
C=/home/vrrcelestino/model-agrologistic-hygiene-audit/.mvp2-pyomo-scaling-serial-public-v2
sha256sum "$C/plan.json" "$C/result.json" "$C/qualification.xml" \
  "$C/smoke-jobs.json" "$C/license-capability.json" "$C/public-allocation.json"
cat "$C/result.json"
cat "$C/smoke-jobs.json"
cat "$C/license-capability.json"
cat "$C/public-allocation.json"
sacct -j 2231659,2231660,2231661,2231662,2231663 --parsable2 \
  --format=JobIDRaw,State,Start,ElapsedRaw,ExitCode,AllocCPUS
)
```

The private storage revision starts with a declared32GiB planning minimum, live
soft-quota checks, a16GiB live reserve and8GiB outside reserve. It does not assume
grace/permission to exceed soft100G, or guarantee all90cells fit. It cannot change
quota, delete originals or bound ongoing solver scratch. The 768GiB historical
worst-case transport-cap estimate is superseded. Private commands remain gated
on accepted public qualification, CI and explicit PR #148 merge approval.
PDFs remain deferred; no raw HPC archive is uploaded.
