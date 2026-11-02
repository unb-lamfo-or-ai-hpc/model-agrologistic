# Public serial qualification v3: isolated test imports

Job2231675 is preserved as rejected: infrastructure checks passed but four new
test modules could not be collected because the original `tests` package was
already loaded from another source tree. The same four errors were reproduced
locally with the published package marker. `--import-mode=importlib` collects
both trees without moving tests into, or changing, the qualified engine.

Code: `8f1a9c9a6f8cfbe25d92648c3c306b7300d7d0c1`; engine:c493be8c unchanged.
Ruff and137 local tests passed; public acceptance requires248 tests without
failures/errors/skips (111 original native+137 current controls).

Run the following wrapper once on NPAD login. It creates public-v3, binds the
six supplied v2 receipt hashes, preserves its rejection, verifies original
v1/v2 source bytes and reuses the completed probe records. It does not submit,
release or cancel any probe, and does not repeat a scientific start. Only one
new public qualification job is submitted. It uses the existing environment,
16logicalCPUs/32GiB/45min and a fresh public license-capacity check.

Wrapper SHA-256:`1344e33c9163e06294e3908d650e61ff06d8449ea1c5da448fbd6ce74e660842`; `bash -n` passed.
Existing v3 or any ambiguous response means preserve/inspect, never retry.

```bash
#!/bin/bash
# Human NPAD login only. One new main job; never submit/release the closed probes.
(
set -euo pipefail
umask 077
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
PY=/home/vrrcelestino/venv313/bin/python
SOURCE_SHA=8f1a9c9a6f8cfbe25d92648c3c306b7300d7d0c1
PUBLIC="$BASE/.mvp2-pyomo-scaling-serial-public-v3"
test -d "$BASE"
test -x "$PY"
if [[ -e "$PUBLIC" || -L "$PUBLIC" ]]; then
  printf 'PRESERVE_EXISTING_PUBLIC_CLAIM=%s; nao repita a submissao\n' "$PUBLIC"
  exit 2
fi
PREP=$(mktemp -d "$BASE/pyomo-serial-importlib-cli-XXXXXXXX")
printf 'PRESERVE_BOOTSTRAP=%s\n' "$PREP"
cd "$PREP"
curl --fail --location --retry 0 --connect-timeout 20 --max-time 300 \
  "https://codeload.github.com/unb-lamfo-or-ai-hpc/model-agrologistic/tar.gz/$SOURCE_SHA" -o source.tar.gz
for SCRIPT in pyomo_serial_queue.py pyomo_serial_smoke.py qualify_pyomo_serial.py pyomo_serial_storage.py
do
  curl --fail --location --retry 0 --connect-timeout 20 --max-time 120 \
    "https://raw.githubusercontent.com/unb-lamfo-or-ai-hpc/model-agrologistic/$SOURCE_SHA/scripts/$SCRIPT" -o "$SCRIPT"
done
printf '%s  pyomo_serial_queue.py\n' '0a1daf294b763c1782a5b06f91720dfc9036e2aec3032d3db20d4c83e02ad998' | sha256sum -c -
printf '%s  pyomo_serial_smoke.py\n' 'b6266514bb8eb36cd3769401f554843f2e05a725c42647fe5c1feffcd6566d86' | sha256sum -c -
printf '%s  qualify_pyomo_serial.py\n' 'd49f96675f36024300472e93b2c92c60a4111793a4fb0a2249c9fb0f1135002b' | sha256sum -c -
printf '%s  pyomo_serial_storage.py\n' 'b6ed67eff404760365d03c55a2e3cbfccd96d831476a721352bd3a1ffb84d363' | sha256sum -c -
"$PY" -B -I "$PREP/qualify_pyomo_serial.py" prepare \
  --claim "$PUBLIC" --source-sha "$SOURCE_SHA" --source-archive "$PREP/source.tar.gz"
"$PY" -B -I "$PUBLIC/source/scripts/qualify_pyomo_serial.py" attach-terminal \
  --claim "$PUBLIC" --source-sha "$SOURCE_SHA"
DEPENDENCY=$(cat "$PUBLIC/qualification-dependency.txt")
DEPENDENCY_ARGS=()
if [[ -n "$DEPENDENCY" ]]; then
  [[ "$DEPENDENCY" =~ ^afterany:[1-9][0-9]*$ ]]
  DEPENDENCY_ARGS=("--dependency=$DEPENDENCY")
fi
mkdir "$PUBLIC/submission-intent"
printf '%s\n' "$DEPENDENCY" > "$PUBLIC/submission-intent/dependency.txt"
SUBMITTED=$(sbatch --parsable --account=sxdsouza --partition=intel-256 --qos=preempt \
  --nodes=1 --ntasks=1 --cpus-per-task=16 --mem=32G --time=00:45:00 \
  --exclusive --no-requeue --kill-on-invalid-dep=yes "${DEPENDENCY_ARGS[@]}" \
  --chdir="$PUBLIC" --output="$PUBLIC/slurm-%j.out" --error="$PUBLIC/slurm-%j.err" \
  "$PUBLIC/qualification.sh")
printf '%s\n' "$SUBMITTED" > "$PUBLIC/submitted-job.txt"
JOB="${SUBMITTED%%;*}"
[[ "$JOB" =~ ^[1-9][0-9]*$ ]]
printf 'PUBLIC_SERIAL_QUALIFICATION_JOB=%s\nPRESERVE_CLAIM=%s\n' "$JOB" "$PUBLIC"
printf 'STATUS_COMMAND=sacct -j %s --format=JobID,State,Elapsed,ExitCode,MaxRSS,AllocCPUs\n' "$JOB"
printf 'REPORT_COMMAND=cat %s/result.json\n' "$PUBLIC"
printf 'EXPECTED=248_TESTS_ZERO_FAILURES_ERRORS_SKIPS\n'
printf 'CLOSED_PROBES_REUSED_READ_ONLY; ONE_MAIN_JOB_ONLY; NO_PRIVATE_START_OR_RETRY\n'
)
```

After the main job is terminal, send the printed STATUS_COMMAND/REPORT_COMMAND,
the following hashes and original reports. No further submission is needed.

```bash
(
set -euo pipefail
C=/home/vrrcelestino/model-agrologistic-hygiene-audit/.mvp2-pyomo-scaling-serial-public-v3
sha256sum "$C/plan.json" "$C/result.json" "$C/qualification.xml" \
  "$C/license-capability.json" "$C/public-allocation.json" "$C/smoke-jobs.json"
cat "$C/result.json"
cat "$C/license-capability.json"
cat "$C/public-allocation.json"
)
```

The v1 hold-profile failure and v2 package-collection rejection remain
independent preserved outcomes. New acceptance cannot be inferred from them.
No private admission, merge, quota change, deletion, environment installation
or PDF generation is implied. Every merge still needs explicit approval.
