#!/bin/bash
# Human-run T1 source verification. No solver, job, environment change or cleanup.
(
set -euo pipefail
umask 077
SOURCE=${1:?Full reviewed source SHA required}
VERIFIER_SHA=${2:?Verifier SHA256 required}
AUDITOR_SHA=${3:?Auditor SHA256 required}
CLASSIFIER_SHA=${4:?Classifier SHA256 required}
[[ "$SOURCE" =~ ^[0-9a-f]{40}$ ]]
for value in "$VERIFIER_SHA" "$AUDITOR_SHA" "$CLASSIFIER_SHA"; do
  [[ "$value" =~ ^[0-9a-f]{64}$ ]]
done
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
PY=/home/vrrcelestino/venv313_g14/bin/python
INVENTORY="$BASE/npad-t1-inventory-sZMvghzZ/npad-t1-inventory.tar.gz"
test -x "$PY"
test -f "$INVENTORY"
test -z "${SLURM_JOB_ID:-}"
test "$(id -un)" = vrrcelestino
cd "$BASE"
FETCH=$(mktemp -d "$BASE/t1-hashdeps-source-XXXXXXXX")
WORKSPACE=$(mktemp -d "$BASE/t1-hashdeps-readback-XXXXXXXX")
printf 'PRESERVE_SOURCE=%s\nPRESERVE_WORKSPACE=%s\n' "$FETCH" "$WORKSPACE"
ROOT="https://raw.githubusercontent.com/unb-lamfo-or-ai-hpc/model-agrologistic/$SOURCE/scripts/t1"
for NAME in verify_hash_dependencies.py audit_inventory_bundle.py classify_inventory_metadata.py; do
  curl --fail --location --retry 0 "$ROOT/$NAME" --output "$FETCH/$NAME"
done
printf '%s  %s\n' \
  "$VERIFIER_SHA" "$FETCH/verify_hash_dependencies.py" \
  "$AUDITOR_SHA" "$FETCH/audit_inventory_bundle.py" \
  "$CLASSIFIER_SHA" "$FETCH/classify_inventory_metadata.py" \
  | sha256sum --strict -c -
ENTRY="$FETCH/verify_hash_dependencies.py"
"$PY" -B -I -S "$ENTRY" prepare --workspace "$WORKSPACE" \
  --inventory "$INVENTORY" --source-sha "$SOURCE"
printf 'VERIFY_COMMAND=%s -B -I -S %s verify --workspace %s --max-gib 24 --max-files 150000 --max-seconds 900\n' \
  "$PY" "$ENTRY" "$WORKSPACE"
printf 'COLLECT_COMMAND=%s -B -I -S %s collect --workspace %s\n' "$PY" "$ENTRY" "$WORKSPACE"
"$PY" -B -I -S "$ENTRY" verify --workspace "$WORKSPACE" \
  --max-gib 24 --max-files 150000 --max-seconds 900
"$PY" -B -I -S "$ENTRY" collect --workspace "$WORKSPACE"
printf 'NO_JOB_OR_SOLVER; NO_ENVIRONMENT_CHANGE; NO_DELETION_OR_SOURCE_ARCHIVING\n'
)
