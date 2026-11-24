#!/bin/bash
# Source this file from the operator's Conda-enabled shell.
# One environment clone only. No license session, optimizer or scheduler call.
(
set -euo pipefail
umask 077
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
OLD=/home/vrrcelestino/venv313
NEW=/home/vrrcelestino/venv313_g14
C="$BASE/.mvp3-gurobi14-environment-v1"

test -z "$(printenv SLURM_JOB_ID || true)"
test -d "$BASE"
test -x "$OLD/bin/python"
test -d "$OLD/conda-meta"
command -v conda >/dev/null
if [ -e "$NEW" ] || [ -L "$NEW" ] || [ -e "$C" ] || [ -L "$C" ]; then
    printf 'STOP_EXISTING_ENV_OR_CLAIM; PRESERVE=%s %s\n' "$NEW" "$C"
    exit 1
fi
mkdir -- "$C"
mkdir -- "$C/tmp" "$C/conda-pkgs" "$C/conda-envs" "$C/cache"
trap 'code=$?; printf "ENVIRONMENT_PREPARATION_EXIT=%s\nPRESERVE_CLAIM=%s\nPRESERVE_ENV=%s\nNO_JOB_OR_AUTOMATIC_RETRY\n" "$code" "$C" "$NEW"' EXIT
export PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1
export TMPDIR="$C/tmp" XDG_CACHE_HOME="$C/cache"
export CONDA_PKGS_DIRS="$C/conda-pkgs" CONDA_ENVS_PATH="$C/conda-envs"
export CONDA_REGISTER_ENVS=false CONDA_AUTO_UPDATE_CONDA=false
cd "$C"

snapshot() {
    "$1/bin/python" -B -I - <<'PY'
import hashlib, importlib.metadata as md, json, pathlib, platform, re, sys
def digest(path):
    with pathlib.Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()
prefix = pathlib.Path(sys.prefix).resolve()
packages = {}
for dist in md.distributions():
    name = re.sub(r"[-_.]+", "-", dist.metadata["Name"]).lower()
    if name in packages:
        raise ValueError("Duplicate installed distribution")
    files = []
    for item in dist.files or ():
        p = pathlib.Path(dist.locate_file(item))
        if p.suffix in {".pyc", ".lic"} or "__pycache__" in p.parts or not p.is_file():
            continue
        if name == "gurobipy" and not p.resolve().is_relative_to(prefix):
            raise ValueError("Gurobi package refers outside its environment")
        files.append([str(item), digest(p)])
    packages[name] = {
        "version": dist.version,
        "files_sha256": hashlib.sha256(
            json.dumps(sorted(files), separators=(",", ":")).encode()
        ).hexdigest()
    }
print(json.dumps({
    "python": platform.python_version(), "executable": sys.executable,
    "python_sha256": digest(sys.executable), "prefix": str(prefix),
    "conda_environment": (prefix/"conda-meta").is_dir(),
    "packages": dict(sorted(packages.items()))
}, indent=2, sort_keys=True))
PY
}

snapshot "$OLD" > "$C/original-before.json"
conda create --yes --copy --no-default-packages --clone "$OLD" --prefix "$NEW" \
    > "$C/conda-clone.stdout" 2> "$C/conda-clone.stderr"
test -x "$NEW/bin/python"
snapshot "$NEW" > "$C/clone-before.json"

"$OLD/bin/python" -B -I - "$C" <<'PY'
import json, pathlib, sys
c = pathlib.Path(sys.argv[1])
a = json.loads((c/"original-before.json").read_text())
b = json.loads((c/"clone-before.json").read_text())
assert a["python"] == b["python"] == "3.13.15", "Python differs"
assert a["conda_environment"] and b["conda_environment"], "Conda identity differs"
assert {k:v["version"] for k,v in a["packages"].items()} == {
    k:v["version"] for k,v in b["packages"].items()
}, "Clone distribution versions differ"
assert a["packages"]["gurobipy"]["version"] == "13.0.3", "Source Gurobi differs"
PY

"$NEW/bin/python" -B -I -m pip --disable-pip-version-check install \
    --index-url https://pypi.org/simple --no-deps --only-binary=:all: \
    --no-cache-dir --no-compile --upgrade --report "$C/pip-report.json" \
    gurobipy==14.0.0 > "$C/pip-install.stdout" 2> "$C/pip-install.stderr"

snapshot "$NEW" > "$C/clone-after.json"
snapshot "$OLD" > "$C/original-after.json"

"$NEW/bin/python" -B -I - "$C" <<'PY'
import hashlib, json, pathlib, sys
import gurobipy as gp
c = pathlib.Path(sys.argv[1])
a, b, before, after = (
    json.loads((c/f).read_text()) for f in (
        "original-before.json", "original-after.json",
        "clone-before.json", "clone-after.json"
    )
)
assert a == b, "Original environment changed; preserve receipts"
for key in ("python", "python_sha256", "executable", "prefix", "conda_environment"):
    assert before[key] == after[key], "Cloned interpreter changed"
assert before["packages"].keys() == after["packages"].keys(), "Package set changed"
changed = [k for k in before["packages"] if before["packages"][k] != after["packages"][k]]
assert changed == ["gurobipy"], "Other installed package files or versions changed"
assert after["packages"]["gurobipy"]["version"] == "14.0.0", "Wrong target"
assert tuple(gp.gurobi.version()) == (14, 0, 0), "Wrong loaded native version"
assert pathlib.Path(gp.__file__).resolve().is_relative_to(
    pathlib.Path("/home/vrrcelestino/venv313_g14").resolve()
), "Loaded module outside clone"
result = {
    "status": "cloned_environment_verified",
    "original_environment_preserved": True,
    "only_changed_distribution": "gurobipy",
    "source_version": "13.0.3", "target_version": "14.0.0",
    "gurobi_loaded": list(gp.gurobi.version()),
    "python": after["python"], "new_prefix": after["prefix"],
    "license_tested": False, "optimizer_called": False, "hpc_job_submitted": False
}
with (c/"environment-result.json").open("x") as stream:
    json.dump(result, stream, indent=2)
    stream.write("\n")
files = [
    "original-before.json", "original-after.json", "clone-before.json",
    "clone-after.json", "environment-result.json", "pip-report.json"
]
with (c/"SHA256SUMS").open("x") as stream:
    for name in files:
        stream.write(hashlib.sha256((c/name).read_bytes()).hexdigest()+"  "+name+"\n")
print(json.dumps(result, indent=2))
PY
printf 'REPORT_COMMAND=cat %s/environment-result.json\n' "$C"
printf 'HASH_COMMAND=cd %s && sha256sum --strict -c SHA256SUMS\n' "$C"
)
