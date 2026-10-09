#!/usr/bin/env bash
# Resource limits are supplied explicitly by the pinned one-shot driver.
set -euo pipefail
test "$#" -eq 5
SOURCE=$1
PYTHON=$2
SOURCE_SHA=$3
NONCE=$4
OUTPUT=$5
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
cd "$SOURCE"
exec "$PYTHON" -m scripts.mvp2_s2_containment_probe \
  --source-sha "$SOURCE_SHA" --nonce "$NONCE" --output "$OUTPUT"
