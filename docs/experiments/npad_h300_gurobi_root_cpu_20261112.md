# h300 Gurobi CPU campaign on NPAD

The 180 frozen h300 W STO cells cross Method 1, 2, 4 and 6, physical-core
ceilings of 1, 2, 4, 8 and 16, and three heuristic profiles. The profiles
use default effort, standard heuristic effort zero, and default effort
with NoRelHeurWork=600. Each of three temporal blocks has 60 cells.
Gurobi 13.0.3 uses CPU, 192 GiB on an exclusive intel-256 node, eight
hours of solver time and the existing independent validator.

The original v1 claim and job 2252602 are historical evidence. The v1
public job failed because Git was unavailable on the compute node, and
the 180-task array was rejected by the per-user QoS submission limit.
The v2 launcher uses a pinned source archive and records source hashes
on the login node. Compute verifies those hashes with Python. The
three 60-task blocks are submitted individually after the preceding
block reaches terminal accounting. Each array runs at concurrency one.
The scheduler remains authoritative for the effective limits. The prior
observed submission limit was 100 under preempt.

Run the qualification with a new source directory under the audit root.
Use the full commit and SHA-256 from the operator handoff.

```bash
(
set -euo pipefail
umask 077
BASE=/home/vrrcelestino/model-agrologistic-hygiene-audit
PY=/home/vrrcelestino/venv313/bin/python
SOURCE='<full commit>'
ARCHIVE_SHA='<archive sha256>'
test -d "$BASE"
BOOT=$(mktemp -d "$BASE/h300-root-cpu-v2-source-XXXXXXXX")
SRC="$BOOT/source"
mkdir "$SRC"
curl --fail --location --retry 0 --connect-timeout 20 --max-time 120 \
  "https://codeload.github.com/unb-lamfo-or-ai-hpc/model-agrologistic/tar.gz/$SOURCE" \
  -o "$BOOT/source.tar.gz"
printf '%s  %s\n' "$ARCHIVE_SHA" "$BOOT/source.tar.gz" | sha256sum --strict -c -
tar -xzf "$BOOT/source.tar.gz" --strip-components=1 -C "$SRC"
printf '%s\n' "$SOURCE" > "$SRC/source-identity.txt"
printf 'PRESERVE_SOURCE=%s\n' "$SRC"
"$PY" -B -I "$SRC/scripts/h300_gurobi_root_campaign.py" submit "$SOURCE" --budget-gib 48
)
```

After public qualification passes with accepted JSON and terminal
accounting, submit block 1. After all 60 tasks are terminal, submit
block 2. Repeat for block 3.

```bash
"$PY" -B -I "$SRC/scripts/h300_gurobi_root_campaign.py" block "$SOURCE" 1
```

The corresponding invocations for subsequent blocks use 2 and 3.
A block's durable intent prevents duplicate submission. Preserve its
receipts if a scheduler response or release is uncertain. The report
can be taken before any array has been accepted and includes accounting
for all accepted blocks.

```bash
OUT=$(mktemp -d "$BASE/h300-root-cpu-v2-readback-XXXXXXXX")
"$PY" -B -I "$SRC/scripts/h300_gurobi_root_campaign.py" report "$SOURCE" \
  > "$OUT/configurations.csv" 2> "$OUT/accounting.txt"
sha256sum "$OUT/configurations.csv" "$OUT/accounting.txt"
```
