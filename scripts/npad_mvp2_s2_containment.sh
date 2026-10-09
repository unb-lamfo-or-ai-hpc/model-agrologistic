#!/usr/bin/env bash
# Input-only observation. Never starts the native worker or admits h300.
set -euo pipefail
SOURCE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
PYTHON=${MVP2_CONTAINMENT_PYTHON:-python}
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
cd "$SOURCE"
exec "$PYTHON" -m scripts.mvp2_s2_containment_driver "$@"
