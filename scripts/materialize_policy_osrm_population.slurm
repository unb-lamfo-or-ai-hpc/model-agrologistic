#!/bin/bash
#SBATCH --job-name=osrm-policy
#SBATCH --partition=intel-256
#SBATCH --cpus-per-task=16
#SBATCH --mem=192G
#SBATCH --time=12:00:00
#SBATCH --output=slurm-osrm-policy-%j.out

set -eu

TARGET_POPULATION="${TARGET_POPULATION:-}"
case "$TARGET_POPULATION" in
  215|500|300|400|600|700|800|900|1000) ;;
  *)
    printf 'TARGET_POPULATION must be an approved level between 215 and 1000.\n' >&2
    false
    ;;
esac

PROJECT_ROOT="${PROJECT_ROOT:-/home/vrrcelestino/model-agrologistic}"
PYTHON="${PYTHON:-/home/vrrcelestino/venv313/bin/python}"
SINGULARITY="${SINGULARITY:-/opt/ohpc/pub/libs/singularity/3.7.1/bin/singularity}"

OSRM_ROOT="${OSRM_ROOT:-/home/vrrcelestino/osrm-agrologistic}"
OSRM_IMAGE="$OSRM_ROOT/images/osrm-backend-v6.0.0-amd64.sif"
OSRM_PBF="$OSRM_ROOT/data/brazil-260901/brazil-260901.osm.pbf"
OSRM_CACHE_PATH="${OSRM_CACHE_PATH:-$OSRM_ROOT/cache/policy-pairs-v020.sqlite3}"

EXPECTED_PBF_SIZE="2080086409"
EXPECTED_PBF_MD5="c59512453eae4bf48d8bb662f54b1127"
EXPECTED_PBF_SHA256="95c432ac3219338bbc7d4f5f7d20a5de709348ea928f656efd34609a51319fde"
EXPECTED_SIF_SHA256="1d6d8c47996ee31d1d2282433e13a94a1d48e9b218912fdf39741bf3b5b05249"
EXPECTED_PROFILE_SHA256="9809a111a8fc8c465c2d6ef3208938a2a7c35fab0d3cda407ffa7ff187a96477"

OSRM_DATA_VERSION="brazil-260901-osrm-v6.0.0-driving-mld"
OSRM_DATASET_ID="pbf:brazil-260901@sha256:${EXPECTED_PBF_SHA256};osrm:v6.0.0;oci:sha256:5116c66d814485be70bc7b239be890e4d36f62b1025a2f1c8139c20fa2697309;sif:sha256:${EXPECTED_SIF_SHA256};profile:driving@sha256:${EXPECTED_PROFILE_SHA256};algorithm:MLD"

INPUT_WORKBOOK="${INPUT_WORKBOOK:-$PROJECT_ROOT/data/processed/policy_population_v020/warehouses_${TARGET_POPULATION}/model_input.xlsx}"
# A corrected input is a new artifact; existing population outputs stay immutable.
FINAL_OUTPUT="${FINAL_OUTPUT:-$PROJECT_ROOT/data/processed/policy_population_v020_osrm/warehouses_${TARGET_POPULATION}}"
case "$INPUT_WORKBOOK:$FINAL_OUTPUT" in
  /*:/*) ;;
  *) printf 'INPUT_WORKBOOK and FINAL_OUTPUT must be absolute paths.\n' >&2; false ;;
esac
AUDIT_DIR="$OSRM_ROOT/audits/policy-${TARGET_POPULATION}-job-${SLURM_JOB_ID}"

mkdir -p "$AUDIT_DIR" "$(dirname "$OSRM_CACHE_PATH")"

printf 'job_id=%s\n' "$SLURM_JOB_ID"
printf 'host=%s\n' "$(hostname)"
printf 'target_population=%s\n' "$TARGET_POPULATION"
printf 'input_workbook=%s\noutput_directory=%s\n' "$INPUT_WORKBOOK" "$FINAL_OUTPUT"
printf 'source_commit=%s\n' "${SOURCE_COMMIT:-not-recorded}"
printf 'cpus=%s\n' "$SLURM_CPUS_PER_TASK"
printf '%s\n' "${SOURCE_COMMIT:-not-recorded}" \
  > "$AUDIT_DIR/source_commit.txt"
printf '%s\n' "$OSRM_DATASET_ID" \
  > "$AUDIT_DIR/osrm_dataset_id.txt"

test -n "${SOURCE_COMMIT:-}"
test -r "$OSRM_IMAGE"
test -r "$OSRM_PBF"
test -r "$INPUT_WORKBOOK"
test -x "$SINGULARITY"
test -x "$PYTHON"

if [ -e "$FINAL_OUTPUT" ]; then
  printf 'Protected output already exists: %s\n' "$FINAL_OUTPUT" >&2
  false
fi

OBSERVED_PBF_SIZE="$(stat -c '%s' "$OSRM_PBF")"
test "$OBSERVED_PBF_SIZE" -eq "$EXPECTED_PBF_SIZE"

printf '%s  %s\n' "$EXPECTED_PBF_MD5" "$OSRM_PBF" \
  | md5sum -c -
printf '%s  %s\n' "$EXPECTED_PBF_SHA256" "$OSRM_PBF" \
  | sha256sum -c -
printf '%s  %s\n' "$EXPECTED_SIF_SHA256" "$OSRM_IMAGE" \
  | sha256sum -c -

OSRM_VERSION="$(
  "$SINGULARITY" exec "$OSRM_IMAGE" osrm-routed --version
)"
printf 'osrm_version=%s\n' "$OSRM_VERSION"
printf '%s\n' "$OSRM_VERSION" > "$AUDIT_DIR/osrm_version.txt"

case "$OSRM_VERSION" in
  *v6.0.0*) ;;
  *)
    printf 'Unexpected OSRM version: %s\n' "$OSRM_VERSION" >&2
    false
    ;;
esac

PROFILE_SHA256="$(
  "$SINGULARITY" exec "$OSRM_IMAGE" \
    sh -c 'sha256sum /opt/car.lua' \
    | awk '{print $1}'
)"
printf 'profile_sha256=%s\n' "$PROFILE_SHA256"
test "$PROFILE_SHA256" = "$EXPECTED_PROFILE_SHA256"

AVAILABLE_KB="$(df -Pk /tmp | awk 'NR == 2 {print $4}')"
MINIMUM_KB="$((120 * 1024 * 1024))"

df -h /tmp | tee "$AUDIT_DIR/df-before.txt"
df -i /tmp | tee "$AUDIT_DIR/inodes-before.txt"

if [ "$AVAILABLE_KB" -lt "$MINIMUM_KB" ]; then
  printf 'Insufficient /tmp space: %s KB available; %s KB required.\n' \
    "$AVAILABLE_KB" "$MINIMUM_KB" >&2
  false
fi

WORK_DIR="$(mktemp -d "/tmp/osrm-policy-${TARGET_POPULATION}-${SLURM_JOB_ID}-XXXXXX")"
OSRM_PID=""

cleanup()
{
  if [ -n "$OSRM_PID" ]; then
    kill "$OSRM_PID" 2>/dev/null || true
    wait "$OSRM_PID" 2>/dev/null || true
  fi

  case "$WORK_DIR" in
    /tmp/osrm-policy-"${TARGET_POPULATION}"-"${SLURM_JOB_ID}"-*)
      rm -rf -- "$WORK_DIR"
      ;;
    *)
      printf 'Refusing to remove unexpected work directory: %s\n' \
        "$WORK_DIR" >&2
      ;;
  esac
}

trap cleanup EXIT INT TERM

printf '%s\n' "$WORK_DIR" > "$AUDIT_DIR/work_dir.txt"

export SINGULARITY_CACHEDIR="$WORK_DIR/singularity-cache"
export SINGULARITY_TMPDIR="$WORK_DIR/singularity-tmp"
export PYTHONNOUSERSITE=1
export PYTHONDONTWRITEBYTECODE=1

mkdir -p "$SINGULARITY_CACHEDIR" "$SINGULARITY_TMPDIR"
cp -- "$OSRM_IMAGE" "$WORK_DIR/osrm-backend.sif"
cp -- "$OSRM_PBF" "$WORK_DIR/brazil-260901.osm.pbf"

WORK_IMAGE="$WORK_DIR/osrm-backend.sif"

du -sh "$WORK_DIR" | tee "$AUDIT_DIR/scratch-after-copy.txt"

"$SINGULARITY" exec \
  --bind "$WORK_DIR:/data" \
  "$WORK_IMAGE" \
  osrm-extract \
  --profile /opt/car.lua \
  --threads "$SLURM_CPUS_PER_TASK" \
  --data_version "$OSRM_DATA_VERSION" \
  /data/brazil-260901.osm.pbf

du -sh "$WORK_DIR" | tee "$AUDIT_DIR/scratch-after-extract.txt"
df -h /tmp | tee "$AUDIT_DIR/df-after-extract.txt"

"$SINGULARITY" exec \
  --bind "$WORK_DIR:/data" \
  "$WORK_IMAGE" \
  osrm-partition /data/brazil-260901.osrm

du -sh "$WORK_DIR" | tee "$AUDIT_DIR/scratch-after-partition.txt"

"$SINGULARITY" exec \
  --bind "$WORK_DIR:/data" \
  "$WORK_IMAGE" \
  osrm-customize /data/brazil-260901.osrm

du -sh "$WORK_DIR" | tee "$AUDIT_DIR/scratch-after-customize.txt"
df -h /tmp | tee "$AUDIT_DIR/df-after-customize.txt"

"$SINGULARITY" exec \
  --bind "$WORK_DIR:/data" \
  "$WORK_IMAGE" \
  osrm-routed \
  --algorithm MLD \
  --mmap \
  --threads "$SLURM_CPUS_PER_TASK" \
  --ip 127.0.0.1 \
  --port 5000 \
  --max-table-size 100 \
  /data/brazil-260901.osrm \
  > "$AUDIT_DIR/osrm-routed.log" 2>&1 &

OSRM_PID="$!"
NEAREST_URL="http://127.0.0.1:5000/nearest/v1/driving/-47.8825,-15.7942?number=1"
TABLE_URL="http://127.0.0.1:5000/table/v1/driving/-47.8825,-15.7942;-49.2648,-16.6869?annotations=distance,duration"
READY="0"
ATTEMPT="1"

while [ "$ATTEMPT" -le 120 ]; do
  if "$PYTHON" -c \
    'import json, sys, urllib.request as u; data=json.load(u.urlopen(sys.argv[1], timeout=5)); assert data.get("code") == "Ok"' \
    "$NEAREST_URL" >/dev/null 2>&1
  then
    READY="1"
    break
  fi

  sleep 2
  ATTEMPT="$((ATTEMPT + 1))"
done

if [ "$READY" -ne 1 ]; then
  printf 'OSRM did not become ready.\n' >&2
  cat "$AUDIT_DIR/osrm-routed.log" >&2
  false
fi

"$PYTHON" -c \
  'import pathlib, sys, urllib.request as u; pathlib.Path(sys.argv[2]).write_bytes(u.urlopen(sys.argv[1], timeout=60).read())' \
  "$NEAREST_URL" "$AUDIT_DIR/nearest.json"
"$PYTHON" -c \
  'import pathlib, sys, urllib.request as u; pathlib.Path(sys.argv[2]).write_bytes(u.urlopen(sys.argv[1], timeout=60).read())' \
  "$TABLE_URL" "$AUDIT_DIR/table.json"

cd "$PROJECT_ROOT"
export OSRM_BASE_URL="http://127.0.0.1:5000"
export OSRM_DATASET_ID
export OSRM_CACHE_PATH

"$PYTHON" scripts/materialize_policy_osrm_workbook.py \
  "$INPUT_WORKBOOK" \
  --output-dir "$FINAL_OUTPUT" \
  --osrm-base-url "$OSRM_BASE_URL" \
  --osrm-dataset-id "$OSRM_DATASET_ID" \
  --osrm-cache-path "$OSRM_CACHE_PATH" \
  --osrm-profile driving \
  --osrm-max-table-size 100 \
  --osrm-timeout-seconds 60 \
  --osrm-retries 2 \
  --osrm-max-snap-distance-m 50000 \
  --haversine-fallback-factor 1.3

test -s "$FINAL_OUTPUT/model_input.xlsx"
test -s "$FINAL_OUTPUT/osrm_materialization_audit.json"

"$PYTHON" - \
  "$FINAL_OUTPUT/osrm_materialization_audit.json" \
  "$INPUT_WORKBOOK" \
  "$TARGET_POPULATION" \
  "$OSRM_DATASET_ID" \
  "$OSRM_DATA_VERSION" \
  > "$AUDIT_DIR/policy-materialization-check.json" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

from src.logic.policy_osrm import _validate_distance_table

audit = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
input_workbook = Path(sys.argv[2])
target_population = int(sys.argv[3])
expected_dataset_id = sys.argv[4]
expected_data_version = sys.argv[5]
provenance = audit["distance_provenance"]

sheets = pd.read_excel(
    input_workbook,
    sheet_name=["Oferta", "Demanda", "Warehouses"],
    engine="openpyxl",
)
origin_count = sheets["Oferta"]["Cidade"].dropna().astype(str).nunique()
warehouse_count = sheets["Warehouses"]["CDA"].dropna().astype(str).nunique()
customer_count = len(
    sheets["Demanda"][["Cidade", "Tipo_Demanda"]].drop_duplicates()
)
assert warehouse_count == target_population
expected_counts = {
    "OD": origin_count * warehouse_count,
    "DC": warehouse_count * customer_count,
    "DD": warehouse_count * (warehouse_count - 1),
    "OC": origin_count * customer_count,
}
accepted_sources = {"osrm", "haversine_fallback"}
accepted_fallbacks = {
    "osrm_no_route",
    "osrm_no_table",
    "osrm_snap_exceeds_limit",
}

assert audit["distance_status"] == "osrm_authoritative"
assert provenance["dataset_id"] == expected_dataset_id
assert expected_data_version in provenance["osrm_data_versions"]
assert provenance["route_count_by_arc_type"] == expected_counts
assert provenance["route_count"] == sum(expected_counts.values())
assert set(provenance["route_count_by_source"]) <= accepted_sources
assert set(provenance["fallback_count_by_reason"]) <= accepted_fallbacks

# Check the persisted artifact, not only in-memory counts or provenance labels.
output_workbook = Path(sys.argv[1]).parent / audit["output_workbook"]
with output_workbook.open("rb") as stream:
    assert hashlib.file_digest(stream, "sha256").hexdigest() == audit["output_workbook_sha256"]
saved_distances = pd.read_excel(output_workbook, sheet_name="Distancias", engine="openpyxl")
_validate_distance_table(saved_distances, sheets)

summary = {
    "status": "accepted",
    "persisted_distance_validation": "accepted",
    "output_workbook_sha256": audit["output_workbook_sha256"],
    "osrm_negative_distance_normalization_count": provenance.get(
        "osrm_negative_distance_normalization_count", 0),
    "target_population": target_population,
    "route_count": provenance["route_count"],
    "route_count_by_arc_type": provenance["route_count_by_arc_type"],
    "route_count_by_source": provenance["route_count_by_source"],
    "fallback_count": provenance["fallback_count"],
    "fallback_count_by_reason": provenance["fallback_count_by_reason"],
    "osrm_request_count": provenance["osrm_request_count"],
    "osrm_cache_hit_count": provenance["osrm_cache_hit_count"],
    "osrm_cache_miss_count": provenance["osrm_cache_miss_count"],
    "osrm_cache_write_count": provenance["osrm_cache_write_count"],
}
print(json.dumps(summary, indent=2, ensure_ascii=False))
PY

"$PYTHON" - "$OSRM_CACHE_PATH" \
  > "$AUDIT_DIR/cache-summary.json" <<'PY'
import json
import sqlite3
import sys
from pathlib import Path

path = Path(sys.argv[1])
with sqlite3.connect(path) as connection:
    connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    record_count = connection.execute(
        "SELECT COUNT(*) FROM osrm_pair_cache"
    ).fetchone()[0]

print(
    json.dumps(
        {"cache_path": str(path), "record_count": record_count},
        indent=2,
    )
)
PY

sha256sum \
  "$FINAL_OUTPUT/model_input.xlsx" \
  "$FINAL_OUTPUT/osrm_materialization_audit.json" \
  "$OSRM_CACHE_PATH" \
  | tee "$AUDIT_DIR/output-sha256.txt"

du -sh "$FINAL_OUTPUT" "$OSRM_CACHE_PATH" \
  | tee "$AUDIT_DIR/persistent-output-size.txt"
df -h /tmp | tee "$AUDIT_DIR/df-before-cleanup.txt"

printf 'OSRM POLICY %s MATERIALIZATION GATE: READY FOR REVIEW\n' \
  "$TARGET_POPULATION"
