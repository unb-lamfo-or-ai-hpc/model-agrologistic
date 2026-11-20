#!/usr/bin/env python3
"""Collect all original h300 block-1 files after terminal accounting; no solver."""

import csv
import hashlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
from pathlib import Path

BASE = Path("/home/vrrcelestino/model-agrologistic-hygiene-audit")
ARRAY = "2252608"
SOURCE = "9d43c963ed53b968e2e6c508de8dc06ed7e6693a"
PLAN_SHA = "de528d6ac5f15ecc4be37a6540d0d1159e2e6990049c25a574eb21567de60f32"
TERMINAL = {
    "COMPLETED",
    "FAILED",
    "CANCELLED",
    "TIMEOUT",
    "OUT_OF_MEMORY",
    "NODE_FAIL",
    "PREEMPTED",
    "BOOT_FAIL",
    "DEADLINE",
    "REVOKED",
}


class HashingReader:
    def __init__(self, stream):
        self.stream = stream
        self.digest = hashlib.sha256()

    def read(self, size):
        data = self.stream.read(size)
        self.digest.update(data)
        return data


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


def task_indices(job):
    """Decode only the explicit individual/range identity reported by Slurm."""
    single = re.fullmatch(rf"{ARRAY}_(\d+)", job)
    group = re.fullmatch(rf"{ARRAY}_\[([0-9,-]+)(?:%[1-9][0-9]*)?\]", job)
    if single:
        indices = [int(single[1])]
    elif group:
        indices = []
        for part in group[1].split(","):
            segment = re.fullmatch(r"(\d+)(?:-(\d+))?", part)
            if segment is None:
                raise SystemExit("Intervalo Slurm inválido; preservar a saída original.")
            first = int(segment[1])
            last = int(segment[2]) if segment[2] is not None else first
            if not 0 <= first <= last < 60:
                raise SystemExit("Intervalo Slurm fora do bloco original.")
            indices.extend(range(first, last + 1))
    elif job.startswith(f"{ARRAY}_") and "." not in job:
        raise SystemExit("Identificador Slurm truncado ou não suportado; preservar a saída.")
    else:
        return []
    if any(index not in range(60) for index in indices) or len(set(indices)) != len(indices):
        raise SystemExit("Tarefa Slurm inválida ou repetida no intervalo.")
    return indices


def report(base):
    claim = base / ".mvp2-h300-gurobi-root-cpu-v2"
    if not claim.is_dir() or claim.resolve() != claim:
        raise SystemExit("Diretório original da campanha não encontrado no caminho esperado.")

    def original(relative):
        path = claim / relative
        if path.resolve() != path:
            raise SystemExit(f"Redirecionamento inesperado no claim: {relative}")
        if not path.exists():
            return None
        if not path.is_file():
            raise SystemExit(f"Arquivo regular esperado: {relative}")
        return path

    plan_path = original("plan.json")
    receipt_path = original("block-1.json")
    if plan_path is None or receipt_path is None:
        raise SystemExit("Plano ou recibo original do bloco 1 ausente.")
    plan_data = plan_path.read_bytes()
    plan = json.loads(plan_data)
    receipt = json.loads(receipt_path.read_bytes())
    if (
        hashlib.sha256(plan_data).hexdigest() != PLAN_SHA
        or plan["source"] != SOURCE
        or receipt["array_job"] != ARRAY
        or len(plan["rows"]) != 180
    ):
        raise SystemExit("Identidade do plano ou do array diverge da coleta parcial.")

    columns = (
        "JobID%512,JobIDRaw%512,State%60,ExitCode,ElapsedRaw,MaxRSS,AllocCPUS,ReqMem,NodeList%120"
    )
    accounting = subprocess.check_output(
        ["sacct", "-j", ARRAY, "-n", "-P", f"--format={columns}"],
        text=True,
        env={**os.environ, "SLURM_BITSTR_LEN": "0"},
    )
    tasks = {}
    task_sources = {}
    for record in csv.reader(io.StringIO(accounting), delimiter="|"):
        if not record:
            continue
        job, raw, state, code, elapsed, *_ = (part.strip() for part in record)
        for index in task_indices(job):
            if index in tasks:
                raise SystemExit(f"Registro Slurm inesperado ou repetido: {job}")
            tasks[index] = (raw, state, code, elapsed)
            task_sources[str(index)] = {"reported_job": job, "reported_raw_job": raw}

    unfinished = [
        index
        for index in range(60)
        if index not in tasks or tasks[index][1].split()[0].rstrip("+") not in TERMINAL
    ]
    if unfinished:
        raise SystemExit(
            f"Coleta final ainda indisponível. Tarefas faltantes ou ativas: {unfinished}"
        )

    items = plan["rows"][:60]
    cells = [item["id"] for item in items]
    if len(set(cells)) != 60 or any(
        item["repetition"] != 1 or not re.fullmatch(r"[a-z0-9_-]+", item["id"]) for item in items
    ):
        raise SystemExit("Identificadores inválidos no primeiro bloco.")

    relatives = []
    total_bytes = 0
    for path in sorted(claim.rglob("*")):
        if path.is_symlink():
            raise SystemExit("Symbolic links require separate custody review.")
        mode = path.stat().st_mode
        if stat.S_ISDIR(mode):
            continue
        if not stat.S_ISREG(mode) or path.resolve() != path:
            raise SystemExit("Unexpected redirected or nonregular claim member.")
        relatives.append(path.relative_to(claim).as_posix())
        total_bytes += path.stat().st_size
    relative_set = set(relatives)
    # This check covers filesystem space; the operator also checks the home quota.
    if shutil.disk_usage(base).free < total_bytes * 1.02 + 5 * 1024**3:
        raise SystemExit(
            "Insufficient filesystem space for a conservative full snapshot; originals preserved."
        )
    output = Path(tempfile.mkdtemp(prefix="h300-2252608-closeout-", dir=base))
    bundle = output / "h300-2252608-closeout.tar.gz"
    ledger = io.StringIO(newline="")
    writer = csv.writer(ledger)
    writer.writerow(
        [
            "task",
            "job",
            "case",
            "method",
            "profile",
            "cores",
            "state",
            "exit_code",
            "elapsed_seconds",
        ]
    )
    hashes = {}
    missing = []

    with tarfile.open(bundle, "x:gz", compresslevel=1) as archive:

        def add_bytes(name, data):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o600
            archive.addfile(info, io.BytesIO(data))
            hashes[name] = hashlib.sha256(data).hexdigest()

        def copy(relative):
            path = original(relative)
            if path is None:
                missing.append(relative)
                return
            info = archive.gettarinfo(path, arcname=f"claim/{relative}")
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mode = 0o600
            if info.islnk():
                info.type = tarfile.REGTYPE
                info.linkname = ""
                info.size = path.stat().st_size
            before = path.stat()
            with path.open("rb") as stream:
                reader = HashingReader(stream)
                archive.addfile(info, reader)
                hashes[info.name] = reader.digest.hexdigest()
            after = path.stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise SystemExit(
                    "Original changed during collection; preserve partial archive for review."
                )

        # Retain every file, including decision vectors and interrupted artifacts.
        # Terminal accounting is required before reading the claim.
        for relative in relatives:
            copy(relative)
        for index, item in enumerate(items):
            raw, state, code, elapsed = tasks[index]
            job = f"{ARRAY}_{index}"
            case = item["id"]
            writer.writerow(
                [
                    index,
                    job,
                    case,
                    item["options"]["Method"],
                    item["profile"],
                    item["threads"],
                    state,
                    code,
                    elapsed,
                ]
            )
            expected = (
                "runtime.json",
                "memory.json",
                "worker.out",
                "worker.err",
                "gurobi-native.log",
                "case/case_outcome.json",
                f"case/products/{case}/run_summary.json",
                f"case/products/{case}/independent_validation.json",
            )
            missing.extend(
                f"{case}/{name}" for name in expected if f"{case}/{name}" not in relative_set
            )

        add_bytes("accounting.txt", (columns.replace(",", "|") + "\n" + accounting).encode())
        add_bytes("tasks.csv", ledger.getvalue().encode())
        add_bytes(
            "inventory.json",
            json_bytes(
                {
                    "array": ARRAY,
                    "source": SOURCE,
                    "plan_sha256": PLAN_SHA,
                    "terminal_tasks": 60,
                    "files_sha256": hashes,
                    "missing_originals": missing,
                    "task_accounting_sources": task_sources,
                    "grouped_accounting_policy": (
                        "Individual identities derived only from explicit Slurm ranges; "
                        "raw grouped rows retained, no distinct raw job IDs invented."
                    ),
                    "scope": (
                        "Complete regular-file claim snapshot, including all available "
                        "decision vectors, logs and receipts; private transfer only."
                    ),
                    "original_files": len(relatives),
                    "original_bytes": total_bytes,
                    "closure_reason": (
                        "Researcher requested ending MVP2 and cancelling remaining block-1 "
                        "tasks on 2026-11-20; actual states come only from sacct."
                    ),
                    "remaining_temporal_blocks": "Not executed under this closeout instruction",
                    "missing_originals_policy": (
                        "Absence is retained; cancelled/unstarted tasks may have no result files."
                    ),
                    "referenced_external_inputs_and_source": (
                        "Identified by original plan; not copied from outside the claim."
                    ),
                }
            ),
        )

    with bundle.open("rb") as stream:
        sha = hashlib.file_digest(stream, "sha256").hexdigest()
    sidecar = bundle.with_suffix(".gz.sha256")
    sidecar.write_text(f"{sha}  {bundle.name}\n", encoding="ascii")
    print(f"TRANSFER_DIR={output}\nARCHIVE={bundle}\nSIDECAR={sidecar}\nSHA256={sha}")
    print(f"TERMINAL_TASKS=60\nFILES_ABSENT={len(missing)}")


if __name__ == "__main__":
    report(BASE)
