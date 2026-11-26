#!/usr/bin/env bash
# Read-only source inspection; no scheduler, optimizer or environment change.
set -euo pipefail
umask 077
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
PY=/home/vrrcelestino/venv313_g14/bin/python
SOURCE="${1:?Supply the reviewed full commit SHA}"
[[ "$SOURCE" =~ ^[0-9a-f]{40}$ ]]
test -d "$BASE"
test -x "$PY"
cd "$BASE"
BOOT=$(mktemp -d "$BASE/t2-reconciliation-cli-XXXXXXXX")
printf 'PRESERVE_BOOTSTRAP=%s\n' "$BOOT"
URL="https://raw.githubusercontent.com/unb-lamfo-or-ai-hpc/model-agrologistic"
curl --fail --location --proto '=https' --tlsv1.2 \
  "$URL/$SOURCE/scripts/t2/reconcile_inputs.py" -o "$BOOT/reconcile_inputs.py"
EXPECTED=a8ede44b2250a236c9525c06fcd6359e24dc9e1e5f08dfeeead341bcd9c70804
printf '%s  %s\n' "$EXPECTED" "$BOOT/reconcile_inputs.py" | sha256sum --strict -c -
"$PY" -B -I -S "$BOOT/reconcile_inputs.py" inventory --controller-sha256 "$EXPECTED"
printf 'NO_SOLVER; NO_JOB; NO_SOURCE_OR_ENVIRONMENT_CHANGE\n'
