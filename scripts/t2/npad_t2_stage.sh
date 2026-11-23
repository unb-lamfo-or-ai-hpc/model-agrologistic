#!/usr/bin/env bash
# Private custody and exploratory reconciliation only. No solver or scheduler.
set -euo pipefail
umask 077
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
PY=/home/vrrcelestino/venv313_g14/bin/python
SOURCE="${1:?Supply the reviewed full commit SHA}"
[[ "$SOURCE" =~ ^[0-9a-f]{40}$ ]]
cd "$BASE"
INPUT="$BASE/mvp3-t2-review-inputs-v1.tar.gz"
INPUT_SHA=10136eb9888c5b20532b1eb8d8fca4274c5b381fa74d5e892320d75a591c13e9
test -f "$INPUT"
printf '%s  %s\n' "$INPUT_SHA" "$INPUT" | sha256sum --strict -c -
WORK=$(mktemp -d "$BASE/t2-offline-cli-XXXXXXXX")
printf 'PRESERVE_CLI=%s\n' "$WORK"
URL=https://raw.githubusercontent.com/unb-lamfo-or-ai-hpc/model-agrologistic
curl --fail --location --proto '=https' --tlsv1.2 \
  "$URL/$SOURCE/scripts/t2/reconcile_inputs.py" -o "$WORK/reconcile_inputs.py"
curl --fail --location --proto '=https' --tlsv1.2 \
  "$URL/$SOURCE/scripts/t2/stage_offline_reconciliation.py" \
  -o "$WORK/stage_offline_reconciliation.py"
HELPER=d27936d62242b83b78d60cf333400c3710d662e9996da33fa2b500ddbb140024
CONTROLLER=8cec8446bc07d60da66a251dd0c096fa187c4381859226630fe47fb7880ac551
printf '%s  %s\n' \
  "$HELPER" "$WORK/reconcile_inputs.py" \
  "$CONTROLLER" "$WORK/stage_offline_reconciliation.py" | sha256sum --strict -c -
"$PY" -B -I -S "$WORK/stage_offline_reconciliation.py" \
  --inputs "$INPUT" --inputs-sha256 "$INPUT_SHA" --controller-sha256 "$CONTROLLER"
printf 'CANDIDATE_CAPTURE_ONLY; NO_SOLVER_OR_JOB; ORIGINALS_PRESERVED\n'
