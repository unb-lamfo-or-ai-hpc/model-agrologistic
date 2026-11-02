#!/usr/bin/env bash
# Human-invoked public controls only. No private input, large start or retry.
set -euo pipefail
umask 077
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
PY=/home/vrrcelestino/venv313/bin/python
SOURCE_SHA=${1:?Full reviewed source commit required}
[[ "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]]
test -d "$BASE"
test -x "$PY"
test -z "${SLURM_JOB_ID:-}"
CLAIM="$BASE/.mvp2-pyomo-scaling-public-v1"
if [[ -e "$CLAIM" || -L "$CLAIM" ]]; then
  printf 'PRESERVE_EXISTING_PUBLIC_CLAIM=%s; do not submit again\n' "$CLAIM"
  exit 2
fi
PREP=$(mktemp -d "$BASE/pyomo-scaling-public-cli-XXXXXXXX")
printf 'PRESERVE_BOOTSTRAP=%s\n' "$PREP"
curl --fail --location --retry 0 --connect-timeout 20 --max-time 300 \
  "https://codeload.github.com/unb-lamfo-or-ai-hpc/model-agrologistic/tar.gz/$SOURCE_SHA" \
  -o "$PREP/source.tar.gz"
# Extract only trusted regular source files, with exact prefix and bounded sizes.
"$PY" -B -I - "$PREP" "$SOURCE_SHA" <<'PY'
import pathlib, sys, tarfile
base, sha = pathlib.Path(sys.argv[1]), sys.argv[2]
prefix = 'model-agrologistic-' + sha
out = base / 'source'
out.mkdir()
seen, total = set(), 0
with tarfile.open(base / 'source.tar.gz', 'r:gz') as tar:
    for m in tar:
        p = pathlib.PurePosixPath(m.name)
        assert (p.parts and p.parts[0] == prefix and not p.is_absolute()
                and '..' not in p.parts and '\\' not in m.name and ':' not in m.name
                and (m.isdir() or m.isfile()) and m.name not in seen and len(seen) < 4096)
        seen.add(m.name)
        if m.isdir():
            continue
        total += m.size
        assert total <= 512 * 1024**2 and m.size <= 128 * 1024**2
        target = out.joinpath(*p.parts[1:])
        target.parent.mkdir(parents=True, exist_ok=True)
        with tar.extractfile(m) as src, target.open('xb') as dst:
            while block := src.read(1024 * 1024):
                dst.write(block)
print('PUBLIC_SOURCE_EXTRACTED; NO_SOLVER_OR_JOB')
PY
cmp -- "$0" "$PREP/source/scripts/npad_pyomo_scaling_public.sh"
sbatch --test-only --account=sxdsouza --partition=intel-256 --qos=preempt \
  --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=32G --time=00:45:00 \
  --exclusive --no-requeue --wrap=/usr/bin/true
"$PY" -B -I "$PREP/source/scripts/qualify_pyomo_scaling.py" prepare \
  --claim "$CLAIM" --source-sha "$SOURCE_SHA" --source-archive "$PREP/source.tar.gz"
mkdir "$CLAIM/submission-intent"
if ! sbatch --parsable --account=sxdsouza --partition=intel-256 --qos=preempt \
  --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=32G --time=00:45:00 --exclusive --no-requeue \
  --chdir="$CLAIM" --output="$CLAIM/slurm-%j.out" --error="$CLAIM/slurm-%j.err" \
  "$CLAIM/qualification.sh" > "$CLAIM/submitted-job.txt"; then
  printf 'SUBMISSION_UNCERTAIN; preserve claim and do not repeat\n'
  exit 2
fi
SUBMITTED=$(cat "$CLAIM/submitted-job.txt")
[[ "$SUBMITTED" =~ ^[1-9][0-9]*(\;[A-Za-z0-9_-]+)?$ ]]
JOB=${SUBMITTED%%;*}
printf 'PUBLIC_QUALIFICATION_JOB=%s\nPRESERVE_CLAIM=%s\n' "$JOB" "$CLAIM"
printf 'STATUS_COMMAND=sacct -j %s --format=JobID,State,Elapsed,ExitCode,MaxRSS,AllocCPUs\n' "$JOB"
printf 'REPORT_COMMAND=cat %s/result.json\n' "$CLAIM"
printf 'PUBLIC_16_CPU_CONTROLS_ONLY; NO_PRIVATE_START_OR_AUTOMATIC_RETRY\n'
