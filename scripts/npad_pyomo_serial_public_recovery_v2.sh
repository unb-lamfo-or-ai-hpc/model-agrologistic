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
