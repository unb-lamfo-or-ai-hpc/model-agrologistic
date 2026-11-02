# Public NPAD serial-controller qualification — pinned recipe

Run this block once from the NPAD login shell, using the existing venv313. It launches five tiny dependency probes and one public native qualification job. It does not construct a population model, repeat any pilot start, install packages or release the private serial queue. One probe intentionally fails and its afterok child must be cancelled without execution; these are expected control outcomes. The native job waits for Gurobi 2231593 if that job remains active. An existing claim or ambiguous submission must be preserved and reported, not retried.

Qualified-code candidate: `35d8468d805d320e22de87565beb74b0f32e77bd`. Local controls: 98 passed. NPAD acceptance is pending and requires 209 tests with zero failures/errors/skips, accepted live dependency probes, allocation, source/runtime and original-receipt preservation. Bash syntax was checked with `bash -n`; no NPAD command was executed by Codex.

```bash
#!/bin/bash
# Human NPAD login only. Six finite public jobs; no private population solve.
(
set -euo pipefail
umask 077
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
PY=/home/vrrcelestino/venv313/bin/python
SOURCE_SHA=35d8468d805d320e22de87565beb74b0f32e77bd
PUBLIC="$BASE/.mvp2-pyomo-scaling-serial-public-v1"
test -d "$BASE"
test -x "$PY"
if [[ -e "$PUBLIC" || -L "$PUBLIC" ]]; then
  printf 'PRESERVE_EXISTING_PUBLIC_CLAIM=%s; nao repita a submissao\n' "$PUBLIC"
  exit 2
fi
printf '\nESPACO COMPARTILHADO; NAO COMPROVA QUOTA PESSOAL\n'
df -h "$BASE"
if command -v quota >/dev/null 2>&1; then quota -s || true; fi
PREP=$(mktemp -d "$BASE/pyomo-serial-public-cli-XXXXXXXX")
printf 'PRESERVE_BOOTSTRAP=%s\n' "$PREP"
cd "$PREP"
curl --fail --location --retry 0 --connect-timeout 20 --max-time 300 \
  "https://codeload.github.com/unb-lamfo-or-ai-hpc/model-agrologistic/tar.gz/$SOURCE_SHA" \
  -o source.tar.gz
for SCRIPT in pyomo_serial_queue.py pyomo_serial_smoke.py qualify_pyomo_serial.py
do
  curl --fail --location --retry 0 --connect-timeout 20 --max-time 120 \
    "https://raw.githubusercontent.com/unb-lamfo-or-ai-hpc/model-agrologistic/$SOURCE_SHA/scripts/$SCRIPT" \
    -o "$SCRIPT"
done
printf '%s  pyomo_serial_queue.py\n' \
  '921e85e0c600d60ec4f0607f0b76f2f1aecc5fe0c0d674213286caeca3ab9c0d' | sha256sum -c -
printf '%s  pyomo_serial_smoke.py\n' \
  '7b1e29583c58d935f185425fbe68ca4f1131a4a2bfba058695703fd02bf06bd3' | sha256sum -c -
printf '%s  qualify_pyomo_serial.py\n' \
  '32e153b4b6006396fbac5b2805902c1b502825aa5cd54a0241497afc8039ce59' | sha256sum -c -
"$PY" -B -I "$PREP/qualify_pyomo_serial.py" prepare \
  --claim "$PUBLIC" --source-sha "$SOURCE_SHA" --source-archive "$PREP/source.tar.gz"
"$PY" -B -I "$PUBLIC/source/scripts/qualify_pyomo_serial.py" smoke \
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
printf 'EXPECTED=209_TESTS_ZERO_FAILURES_ERRORS_SKIPS_PLUS_FIVE_DEPENDENCY_PROBES\n'
printf 'ONE_INTENTIONAL_FAILED_PROBE_AND_ONE_UNEXECUTED_CANCELLED_CHILD_ARE_EXPECTED\n'
printf 'PUBLIC_CONTROLS_ONLY; ORIGINAL_T1_T16_PRESERVED; NO_PRIVATE_START_OR_RETRY\n'
)
```

After the main job is terminal, supply the printed STATUS_COMMAND and REPORT_COMMAND, plus these existing receipts. If a file is absent or any result is rejected, preserve the directory and report the error without repeating the block.

```bash
(
set -euo pipefail
C=/home/vrrcelestino/model-agrologistic-hygiene-audit/.mvp2-pyomo-scaling-serial-public-v1
sha256sum "$C/plan.json" "$C/result.json" "$C/qualification.xml" \
  "$C/smoke-jobs.json" "$C/license-capability.json" "$C/public-allocation.json"
cat "$C/result.json"
cat "$C/license-capability.json"
cat "$C/public-allocation.json"
cat "$C/smoke-jobs.json"
)
```

The quota query is read-only. Shared free space is not a quota guarantee. A later private preparation requires the researcher to declare a supported storage budget of at least 768 GiB. This public block neither reserves that space nor admits private execution. No PDFs are generated or uploaded.
