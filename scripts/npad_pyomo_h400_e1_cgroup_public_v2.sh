#!/bin/bash
set -euo pipefail
umask 077

SOURCE=${1:?Expected pinned source commit}
PROBE_SHA=${2:?Expected pinned probe SHA-256}
[[ "$SOURCE" =~ ^[0-9a-f]{40}$ && "$PROBE_SHA" =~ ^[0-9a-f]{64}$ ]]
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
PY=/home/vrrcelestino/venv313/bin/python
V1="$BASE/.mvp2-pyomo-h400-e1-cgroup-public-v1"
CLAIM="$BASE/.mvp2-pyomo-h400-e1-cgroup-public-v2"
PROBE="$CLAIM/npad_pyomo_h400_e1_cgroup_probe.py"

test -x "$PY"
if [[ -e "$CLAIM" || -L "$CLAIM" ]]; then
    printf 'PRESERVE_EXISTING_CLAIM=%s\n' "$CLAIM"
    exit 2
fi
test -d "$V1" && test ! -L "$V1"
for NAME in slurm-2247610.out slurm-2247610.err; do
    test -f "$V1/$NAME" && test ! -L "$V1/$NAME"
done
printf '%s  %s\n' \
    '22644dc041c6117a816703168e72f26e4564a61b29ebef39cd0e240bfefc8e52' "$V1/slurm-2247610.out" \
    'c15307834fb77656d0465d2667a8a62f564f7c97febe532104e7de677c426d8' "$V1/slurm-2247610.err" \
    | sha256sum -c -

mkdir "$CLAIM"
printf 'PRESERVE_CLAIM=%s\n' "$CLAIM"
curl --fail --location --retry 0 --connect-timeout 20 --max-time 120 \
    "https://raw.githubusercontent.com/unb-lamfo-or-ai-hpc/model-agrologistic/$SOURCE/scripts/npad_pyomo_h400_e1_cgroup_probe.py" \
    -o "$PROBE"
printf '%s  %s\n' "$PROBE_SHA" "$PROBE" | sha256sum -c -
printf 'source=%s\nprobe_sha256=%s\n' "$SOURCE" "$PROBE_SHA" > "$CLAIM/source-identity.txt"
mkdir "$CLAIM/submission-intent"
SUBMITTED=$(
    sbatch --parsable --account=sxdsouza --partition=intel-256 --qos=preempt \
        --nodes=1 --ntasks=1 --cpus-per-task=24 --mem=192G --time=00:05:00 \
        --exclusive --no-requeue --job-name=h400-e1-cgroup-public-v2 \
        --chdir="$CLAIM" --output="$CLAIM/slurm-%j.out" --error="$CLAIM/slurm-%j.err" \
        --export="ALL,E1_PROBE=$PROBE" <<'BATCH'
#!/bin/bash
set -euo pipefail
PY=/home/vrrcelestino/venv313/bin/python
batch_rc=0
step_rc=0
final_rc=0
"$PY" -B -I "$E1_PROBE" || batch_rc=$?
srun --exact --ntasks=1 --cpus-per-task=16 --cpu-bind=threads \
    "$PY" -B -I "$E1_PROBE" --exercise || step_rc=$?
"$PY" -B -I "$E1_PROBE" || final_rc=$?
(( batch_rc == 0 && step_rc == 0 && final_rc == 0 ))
BATCH
)
printf '%s\n' "$SUBMITTED" > "$CLAIM/submitted-job.txt"
JOB="${SUBMITTED%%;*}"
[[ "$JOB" =~ ^[1-9][0-9]*$ ]]
printf 'PUBLIC_E1_CGROUP_JOB=%s\nPRESERVE_ORIGINAL=%s\n' "$JOB" "$V1"
printf 'STATUS_COMMAND=sacct -j %s --parsable2 --format=JobIDRaw,State,ElapsedRaw,ExitCode,ReqMem,MaxRSS,AllocCPUS,NodeList\n' "$JOB"
printf 'REPORT_COMMAND=cat %s/slurm-%s.out %s/slurm-%s.err\n' "$CLAIM" "$JOB" "$CLAIM" "$JOB"
printf 'HASH_COMMAND=sha256sum %s/source-identity.txt %s/slurm-%s.out %s/slurm-%s.err\n' "$CLAIM" "$CLAIM" "$JOB" "$CLAIM" "$JOB"
printf 'PUBLIC_ONLY; NO_SOLVER_OR_PRIVATE_INPUTS; NO_PILOT_START\n'
