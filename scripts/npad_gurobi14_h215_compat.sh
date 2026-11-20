#!/bin/bash
# Human-only launch, after the researcher's explicit CLI authorization.
# The sole submission is held until its receipt is recorded; never retries.
(
set -euo pipefail
umask 077
SOURCE=${1:?Full reviewed source commit required}
ARCHIVE_SHA=${2:?Reviewed source tarball SHA-256 required}
EXPECTED_LICENSE_ID=${3:?Designated license identity required; never pass credentials}
[[ "$SOURCE" =~ ^[0-9a-f]{40}$ ]]
[[ "$ARCHIVE_SHA" =~ ^[0-9a-f]{64}$ ]]
[[ "$EXPECTED_LICENSE_ID" =~ ^[0-9]+$ ]]
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
PY=/home/vrrcelestino/venv313_g14/bin/python
C="$BASE/.mvp3-gurobi14-h215-compat-v2-shared106"
test -z "${SLURM_JOB_ID:-}"
test -d "$BASE"
test -x "$PY"
if [ -e "$C" ] || [ -L "$C" ]; then
    printf 'PRESERVE_EXISTING_CLAIM=%s; STOP_NO_RESUBMISSION\n' "$C"
    exit 1
fi
FETCH=$(mktemp -d "$BASE/gurobi14-h215-source-XXXXXXXX")
printf 'PRESERVE_BOOTSTRAP=%s\n' "$FETCH"
curl --fail --location --retry 0 \
  "https://codeload.github.com/unb-lamfo-or-ai-hpc/model-agrologistic/tar.gz/$SOURCE" \
  --output "$FETCH/source.tar.gz"
printf '%s  %s\n' "$ARCHIVE_SHA" "$FETCH/source.tar.gz" | sha256sum --strict -c -
tar -xzf "$FETCH/source.tar.gz" -C "$FETCH"
ENTRY="$FETCH/model-agrologistic-$SOURCE/scripts/gurobi14_h215_compat.py"
export PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1
"$PY" -B -I "$ENTRY" prepare --source-sha "$SOURCE" \
  --archive "$FETCH/source.tar.gz" --archive-sha256 "$ARCHIVE_SHA" \
  --expected-license-id "$EXPECTED_LICENSE_ID"
bash -n "$C/job.sh"
"$PY" -B -I - "$C" "$SOURCE" <<'PY'
import hashlib, json, pathlib, sys
c = pathlib.Path(sys.argv[1])
with (c/'submission-intent.json').open('x') as f:
    json.dump({'source_sha':sys.argv[2], 'new_jobs':1, 'automatic_retry':False,
               'plan_sha256':hashlib.sha256((c/'plan.json').read_bytes()).hexdigest()}, f)
PY
set -o noclobber
sbatch --parsable --hold "$C/job.sh" > "$C/submission.stdout" 2> "$C/submission.stderr"
JOB=$(cut -d';' -f1 "$C/submission.stdout")
[[ "$JOB" =~ ^[0-9]+$ ]]
printf '%s\n' "$JOB" > "$C/job-id.txt"
scontrol release "$JOB" > "$C/release.stdout" 2> "$C/release.stderr"
printf 'COMPATIBILITY_JOB=%s\nPRESERVE_CLAIM=%s\n' "$JOB" "$C"
printf 'STATUS_COMMAND=sacct -j %s --parsable2 --format=JobIDRaw,State,ElapsedRaw,ExitCode,ReqMem,MaxRSS,AllocCPUS,NodeList\n' "$JOB"
printf 'COLLECT_COMMAND=%q -B -I %q collect --source-sha %s\n' "$PY" "$ENTRY" "$SOURCE"
printf 'ONE_H215_DET_W_JOB_ONLY; NO_AUTOMATIC_RETRY\n'
)
