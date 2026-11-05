# Read back the released Pyomo campaign while it runs

Paste the complete block into the NPAD login shell. It reads the original queue, submission and release receipts, queries Slurm accounting once, and maps each job to its declared node and cell. The graph includes 93 new jobs and two attached 16-thread pilots. The two one-thread anchors were reused outside this graph.

The output is one new owner-readable JSON report under the campaign's base directory, outside its original claims. Return the file printed as `PARTIAL_REPORT` and its SHA-256 for review. The report preserves original receipt digests and separates official collector metadata, terminal previews, absent products and accounting. Terminal previews read five small metadata files from a completed claim and bind the validation and summary to the completion receipt. They remain preliminary pending the official collector. The block reads no solution arrays and streams no original archives. Keep original `collection.json`, `evidence.tar.gz` and checksum files intact. The command's Python block was parsed locally against the pinned source schema, and requires a human run at NPAD.

The official queue owns its collection and gate stages. This procedure uses only `sacct` and bounded file reads. The metadata report can be regenerated under a fresh name if accounting changes.

```bash
(
set -euo pipefail
umask 077
BASE="$HOME/model-agrologistic-hygiene-audit"
PY="$HOME/venv313/bin/python"
REPORT=$(mktemp "$BASE/pyomo-partial-readback-XXXXXXXX.json")
"$PY" -B -I - "$BASE" > "$REPORT" <<'PY'
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

base = Path(sys.argv[1])
queue = base / ".mvp2-pyomo-scaling-serial-v1"
campaign = base / ".mvp2-pyomo-scaling-native8h-v1"
controller = "334827d5e3669b4fcdf2801fd4cea466e5a71d06"
engine = "c493be8cd127c5175fc7eb111400229e64b8e3c0"

def read(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("Expected regular file: " + path.name)
    if path.stat().st_size > 4 * 1024**2:
        raise ValueError("Metadata exceeds 4 MiB: " + path.name)
    data = path.read_bytes()
    return json.loads(data), hashlib.sha256(data).hexdigest()

def select(value, keys):
    return {key: value[key] for key in keys.split() if key in value}

manifest, queue_hash = read(queue / "queue.json")
submitted, submitted_hash = read(queue / "submitted.json")
released, released_hash = read(queue / "released.json")
nodes = {node["id"]: node for node in manifest["schedule"]["jobs"]}
receipts = submitted["receipts"]
attached = set(manifest["attached"])
if not (
    manifest["controller_commit"] == controller
    and manifest["engine_commit"] == engine
    and submitted["queue_sha256"] == released["queue_sha256"] == queue_hash
    and set(nodes) == set(receipts)
    and len(nodes) == 95 and len(attached) == 2 and attached <= set(nodes)
    and len({str(row["job_id"]) for row in receipts.values()}) == len(nodes)
    and set(map(str, released["job_ids"])) ==
        {str(row["job_id"]) for key, row in receipts.items() if key not in attached}
):
    raise SystemExit("Unexpected original queue or release identity.")
job_ids = {str(row["job_id"]) for row in receipts.values()}
if not all(re.fullmatch(r"[1-9][0-9]*", job) for job in job_ids):
    raise SystemExit("Unexpected job identifier.")
raw = subprocess.check_output(
    ["sacct", "-n", "-P", "-j", ",".join(sorted(job_ids)),
     "--format=JobIDRaw,State%80,ElapsedRaw,ExitCode,MaxRSS,AllocCPUS"],
    text=True, timeout=60,
)
accounting = {}
for line in raw.splitlines():
    parts = line.split("|")
    if len(parts) != 6:
        raise SystemExit("Unexpected accounting row.")
    ident, state, elapsed, code, rss, cpus = parts
    if ident.split(".")[0] in job_ids:
        row = dict(state=state, elapsed_raw=elapsed, exit_code=code,
                   max_rss_raw=rss or None, alloc_cpus=cpus)
        if ident in accounting and accounting[ident] != row:
            raise SystemExit("Ambiguous accounting row for " + ident)
        accounting[ident] = row

rows = []
for key, node in nodes.items():
    ident = str(receipts[key]["job_id"])
    root = accounting.get(ident, {})
    row = dict(node=key, kind=node["kind"], job_id=ident,
               attached=key in attached, accounting=root,
               worker_steps={k: v for k, v in accounting.items()
                             if re.fullmatch(re.escape(ident) + r"\.\d+", k)})
    rows.append(row)
    try:
        if not re.fullmatch(r"(?:solve|control):[a-z0-9-]+", key):
            raise ValueError("Unexpected node identity")
        cell = node.get("cell")
        if cell is None:
            stage = queue / "jobs" / key.replace(":", "__") / "stage_result.json"
            if stage.exists():
                state, digest = read(stage)
                row["stage"] = select(state, "status node error_kind population_gate")
                row["stage_result_sha256"] = digest
            continue
        if not re.fullmatch(r"h(?:300|400|500)-w-sto-(?:gurobi|highs)-t(?:1|2|4|8|16)-r[1-3]", cell):
            raise ValueError("Unexpected campaign cell")
        row["cell"] = cell
        claim = campaign / cell
        if claim.is_symlink():
            raise ValueError("Linked claim")
        marker = claim / "collection.json"
        if marker.exists():
            saved, digest = read(marker)
            obs = saved["observation"]
            if str(obs["job_id"]) != ident or obs["cell"]["id"] != cell or obs["source_commit"] != engine:
                raise ValueError("Official collection identity mismatch")
            row["evidence"] = "official_collection_receipt"
            row["collection_sha256"] = digest
            row["archive_sha256_reported"] = saved["sha256"]
            row["observation"] = select(obs, (
                "cell source_commit plan_sha256 campaign_sha256 status classification "
                "native_result_returned native_status has_usable_incumbent objective bound "
                "common_gap native_gap original_validation_status quality_target_met "
                "operational_receipts_closed input_binding matrix_sha256 bounds_sha256 "
                "hardware_class_sha256 worker_affinity_logical_cpus effective_parameters "
                "timings resource_observation economic_cost penalized_total"
            ))
        elif root.get("state") == "COMPLETED" and root.get("exit_code") == "0:0":
            products = claim / "cases" / cell / "products" / cell
            paths = {
                "job": claim / "job.json",
                "native": claim / "control" / "sto" / "native_terminal.json",
                "completion": products / "run_completion.json",
                "validation": products / "independent_validation.json",
                "summary": products / "run_summary.json",
            }
            if not all(path.is_file() for path in paths.values()):
                row["evidence"] = "terminal_products_not_visible"
                continue
            meta = {name: read(path) for name, path in paths.items()}
            job, terminal, completion, validation, summary = (
                meta[name][0] for name in paths
            )
            if not (
                str(job["job_id"]) == ident and job["source_commit"] == engine
                and all(terminal["entry"].get(k) == v for k, v in job.items())
                and completion["status"] == "complete"
                and summary["independent_validation_status"] == validation["status"]
                and all(completion["artifacts"][paths[name].name] == meta[name][1]
                        for name in ("validation", "summary"))
            ):
                raise ValueError("Terminal metadata identity mismatch")
            row["evidence"] = "terminal_preview_awaiting_official_collection"
            row["metadata_sha256"] = {name: pair[1] for name, pair in meta.items()}
            row["native"] = select(terminal, "status objective bound")
            row["native_metadata"] = select(
                terminal["metadata"],
                "solver_termination pyomo_native_gap timings common_linear_matrix",
            )
            row["validation"] = select(validation, "status failed_check_count")
            row["summary"] = select(summary, "economic_cost penalized_cost")
        else:
            row["evidence"] = "no_collected_result_visible"
    except (OSError, ValueError, KeyError, TypeError) as exc:
        row["evidence"] = "readback_requires_review"
        row["error_kind"] = type(exc).__name__
        row["error"] = str(exc).replace(str(base), "<BASE>")

report = dict(
    scope="read-only partial readback; original archives not reread",
    read_at_utc=datetime.now(timezone.utc).isoformat(),
    controller_commit=controller, engine_commit=engine,
    queue_sha256=queue_hash, submitted_sha256=submitted_hash,
    released_sha256=released_hash,
    scheduler_counts_new_jobs=dict(Counter(
        row["accounting"].get("state", "ACCOUNTING_ABSENT")
        for row in rows if not row["attached"]
    )),
    solve_evidence_counts=dict(Counter(
        row.get("evidence", "readback_requires_review")
        for row in rows if row["kind"] == "scientific_solve"
    )),
    jobs=rows,
)
print(json.dumps(report, indent=2, allow_nan=False))
PY
printf 'PARTIAL_REPORT=%s\n' "$REPORT"
sha256sum "$REPORT"
"$PY" -B -I -c 'import json,sys; d=json.load(open(sys.argv[1])); print(json.dumps({k:v for k,v in d.items() if k.endswith("_counts") or k.startswith("scheduler_counts")}, indent=2))' "$REPORT"
)
```

Sources. [Qualified queue controller](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/334827d5e3669b4fcdf2801fd4cea466e5a71d06/scripts/pyomo_serial_queue.py) · [Official collector](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/blob/334827d5e3669b4fcdf2801fd4cea466e5a71d06/scripts/pyomo_serial_collection.py) · [Release PR](https://github.com/unb-lamfo-or-ai-hpc/model-agrologistic/pull/148)
