# Finite serial campaign: human NPAD launch after PR148 merge

PR148 was merged into develop at48e2831693fc4abe0657c82197a2e884a61e99d2.
The merged controller's ten allowlisted files match qualified source334827d5;
public2231948 passed248tests without failures/errors/skips. Use the existing
public-v3 source at its original identity, not a newly copied or relabeled tree.
The current closure is recorded in pyomo_serial_public_2231948_accepted_20261102.json.

Execute the following once from the human NPAD login. It reuses all four
completed pilots: two immutable t1 anchors and two attached t16 jobs. It creates
86future scientific cells plus six control jobs and a final consolidation,
submits93newIDs in hold, verifies the entire graph and releases once. No
original start is repeated. The48GiB declared budget is accepted only if fresh
quota/free-space checks support it, including the qualified reserves.
If any step fails, preserve all directories/IDs/receipts and do not rerun the
block or individual submission/release commands; diagnose the original state.
This document is a recipe, not proof of private submission or release.

```bash
(
set -euo pipefail
umask 077
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
PY=/home/vrrcelestino/venv313/bin/python
PUBLIC="$BASE/.mvp2-pyomo-scaling-serial-public-v3"
QUEUE="$BASE/.mvp2-pyomo-scaling-serial-v1"
SOURCE_SHA=334827d5e3669b4fcdf2801fd4cea466e5a71d06
DRIVER="$PUBLIC/source/scripts/pyomo_serial_queue.py"
export GRB_LICENSE_FILE=/home/vrrcelestino/model-agrologistic/secrets/gurobi.lic
test -x "$PY"
test -f "$DRIVER"
if [[ -e "$QUEUE" || -L "$QUEUE" ]]; then
  printf 'PRESERVE_EXISTING_QUEUE=%s; nao repita prepare/submit/release\n' "$QUEUE"
  exit 2
fi
"$PY" -B -I - <<'PY'
import hashlib
import json
import pathlib
base = pathlib.Path('/home/vrrcelestino/model-agrologistic-hygiene-audit')
public = base / '.mvp2-pyomo-scaling-serial-public-v3'
assert public.is_dir() and not public.is_symlink()
expected = {
    'plan.json': '8e4947a89b0fd76dbaa1549c31ba1afcb9cbe964c63fd41e212102ad2dabc4d4',
    'result.json': 'f8ae47e8dd17b29e124287ee29a560e3b85d55d17f4ffc4c2375a784b94a4f9c',
}
records = {}
for name, digest in expected.items():
    path = public / name
    assert path.is_file() and not path.is_symlink(), name
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest, name
    records[name] = json.loads(raw)
plan = records['plan.json']
result = records['result.json']
source = '334827d5e3669b4fcdf2801fd4cea466e5a71d06'
assert plan['source_commit'] == result['source_commit'] == source
assert result['job_id'] == '2231948'
assert result['status'] == 'accepted' and result['pytest_exit'] == 0
assert result['counts'] == {
    'tests': 248, 'failures': 0, 'errors': 0, 'skipped': 0
}
root = public / 'source'
assert root.is_dir() and not root.is_symlink()
assert len(plan['controller_files']) == 10
for name, digest in plan['controller_files'].items():
    relative = pathlib.PurePosixPath(name)
    assert not relative.is_absolute() and '..' not in relative.parts
    path = root.joinpath(*relative.parts)
    assert path.is_file() and not path.is_symlink(), name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
print('PUBLIC_V3_AND_10_CONTROLLER_FILES=VERIFIED; NO_NEW_JOB_YET')
PY
"$PY" -B -I "$DRIVER" prepare \
  --queue "$QUEUE" --controller-sha "$SOURCE_SHA" \
  --storage-budget-gib 48
"$PY" -B -I "$DRIVER" submit \
  --queue "$QUEUE" --controller-sha "$SOURCE_SHA"
"$PY" -B -I "$DRIVER" release \
  --queue "$QUEUE" --controller-sha "$SOURCE_SHA"
printf '\nPRESERVE_QUEUE=%s\n' "$QUEUE"
printf 'EXPECTED=bounded_graph_released; NEW_JOBS=93; NO_PILOT_RESTART\n'
printf 'STATUS_COMMAND=%s -B -I %s status --queue %s --controller-sha %s\n' \
  "$PY" "$DRIVER" "$QUEUE" "$SOURCE_SHA"
)
```

Expected release result:statusbounded_graph_released,new_jobs93,attached_jobs2.
A failure after some submissions leaves original IDs held; do not generate
replacement jobs. A release ambiguity requires reading the same receipts,
never a blind retry. Worker/native/logical-allocation CPU scopes remain distinct.
Population/matrix/bounds/hardware/memory/closure and live storage gates apply.
A clean time limit without an incumbent is a censored observation with null
objective/gap; no solver removal or repeatedR1 follows from it.

## Read-only monitoring after a confirmed release

```bash
/home/vrrcelestino/venv313/bin/python -B -I \
 /home/vrrcelestino/model-agrologistic-hygiene-audit/.mvp2-pyomo-scaling-serial-public-v3/source/scripts/pyomo_serial_queue.py \
 status \
 --queue /home/vrrcelestino/model-agrologistic-hygiene-audit/.mvp2-pyomo-scaling-serial-v1 \
 --controller-sha 334827d5e3669b4fcdf2801fd4cea466e5a71d06
squeue -u vrrcelestino -o '%.18i %.9P %.30j %.10T %.12M %.6D %R'
```

The finite queue can proceed after logout, subject to those gates and scheduler
state. It does not guarantee30-day completion. Full outputs remain in original
NPAD claims; no automatic transfer, upload, cleanup, solver restart or PDF occurs.
