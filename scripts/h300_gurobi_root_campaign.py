"""Plan and run the CPU-only h300 Gurobi factorial on NPAD."""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import os
import random
import re
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import pyomo_scaling_campaign as campaign  # noqa: E402
from scripts import pyomo_scaling_contract as contract  # noqa: E402
from scripts import pyomo_serial_storage as storage  # noqa: E402
from scripts.probe_npad_gurobi_license import (  # noqa: E402
    LICENSE_FILE,
    probe,
)
from scripts.pyomo_h400_e1_memory import JobMemoryGuard  # noqa: E402

BASE = campaign.BASE
CLAIM = BASE / ".mvp2-h300-gurobi-root-cpu-v2"
BLOCK_SIZE = 60
PYTHON = Path("/home/vrrcelestino/venv313/bin/python")
MATRIX = "b3c92c54f12ad710fffc4983a832c4e503a5b84e4615c51abcf61a1c0927e1ed"
PROFILES = {
    "standard": {"Heuristics": 0.05, "NoRelHeurWork": 0},
    "heuristics_off": {"Heuristics": 0.0, "NoRelHeurWork": 0},
    "norel": {"Heuristics": 0.05, "NoRelHeurWork": 600},
}
COMMAND = campaign.r.r2.command


def require(value, message):
    if not value:
        raise ValueError(message)


def schedule():
    rows = []
    for repetition in (1, 2, 3):
        block = [
            {
                **contract.cell(300, "gurobi", threads, repetition),
                "id": f"h300-m{method}-{name}-t{threads}-r{repetition}",
                "profile": name,
                "options": {
                    "Method": method, "ConcurrentMIP": 1,
                    "PDHGGPU": 0, "NoRelHeurTime": 0, "SoftMemLimit": 160,
                    **options,
                },
            }
            for method, threads, (name, options) in itertools.product(
                (1, 2, 4, 6), (1, 2, 4, 8, 16), PROFILES.items()
            )
        ]
        random.Random(42031 + repetition).shuffle(block)
        rows.extend(block)
    return rows


def write(path, payload):
    with path.open("xb") as stream:
        stream.write(contract.encoded(payload))


def read(path):
    return json.loads(campaign.regular(path).read_bytes())


def capture(argv, **kwargs):
    result = COMMAND(argv, **kwargs)
    if result.returncode:
        raise ValueError(f"{argv[0]} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def source_inventory(sha):
    require(re.fullmatch(r"[a-f0-9]{40}", sha), "Expected full source commit.")
    require(ROOT.is_relative_to(BASE.resolve()), "Use source under the NPAD audit directory.")
    marker = campaign.regular(ROOT / "source-identity.txt").read_text(encoding="ascii").strip()
    require(marker == sha, "Source archive identity differs.")
    return {
        "source_commit": sha,
        "files": {
            path.relative_to(ROOT).as_posix(): campaign.digest(campaign.regular(path))
            for path in sorted(ROOT.rglob("*")) if path.is_file()
        },
    }


def check_source(sha):
    plan = read(CLAIM / "plan.json")
    inventory = plan["source_inventory"]
    require(
        sha == plan["source"] == inventory["source_commit"]
        and str(ROOT) == plan["source_root"], "Prepared source identity differs.",
    )
    campaign.r.r2.verify_source(inventory, root=ROOT)


def block_receipt(directory, task):
    return read(directory / f"block-{task // BLOCK_SIZE + 1}.json")


def topology(count):
    affinity = sorted(os.sched_getaffinity(0))
    mapping = campaign.cpu_topology(affinity)["mapping"]
    sockets = {}
    for row in mapping:
        sockets.setdefault(row["package"], {}).setdefault(row["core"], row["logical_cpu"])
    suitable = [cores for cores in sockets.values() if len(cores) >= 16]
    require(suitable, "Allocation exposes fewer than 16 distinct physical cores on one socket.")
    os.sched_setaffinity(0, sorted(suitable[0].values())[:count])
    observed = campaign.cpu_topology(sorted(os.sched_getaffinity(0)))
    require(observed["physical_cores"] == count, "Physical core affinity differs.")
    return observed


def allocation(walltime):
    job_id = os.environ["SLURM_JOB_ID"]
    fields = capture(["scontrol", "show", "job", "-o", job_id])
    return campaign.allocation(fields, job_id, os.getuid(), walltime=walltime)


def qualify(directory):
    from importlib.metadata import version

    import gurobipy as gp

    resources = allocation("00:15:00")
    memory = JobMemoryGuard(os.environ["SLURM_JOB_ID"])
    placement = topology(16)
    receipt = probe()
    require(
        receipt["status"] == "accepted" and gp.gurobi.version() == (13, 0, 3)
        and version("pyomo") == "6.10.1", "Public license or version qualification failed.",
    )
    with gp.Env(empty=True) as env:
        env.setParam("OutputFlag", 0)
        env.start()
        for method, (name, options) in itertools.product((1, 2, 4, 6), PROFILES.items()):
            with gp.Model(env=env) as model:
                model.setParam("Method", method)
                model.setParam("PDHGGPU", 0)
                model.setParam("Threads", 16)
                model.setParam("Presolve", 0)
                for key, value in options.items():
                    model.setParam(key, value)
                x = model.addVar(vtype=gp.GRB.BINARY)
                y = model.addVar(lb=0, ub=3)
                model.addConstr(y >= 1 - 2 * x)
                model.setObjective(y + 2 * x)
                model.optimize()
                require(model.Status == gp.GRB.OPTIMAL and abs(model.ObjVal - 1) < 1e-8,
                        f"Public control failed for method {method}, {name}.")
    memory.check()
    check_source(read(directory / "plan.json")["source"])
    write(directory / "qualification.json", {
        "source": read(directory / "plan.json")["source"],
        "job_id": os.environ["SLURM_JOB_ID"], "status": "accepted",
        "topology": placement, "license": receipt, "memory": memory.receipt(),
        "allocation": resources,
    })


def worker(directory, task):
    from src.logic.experiment_runner import run_experiment
    from src.logic.optimization_pyomo import GUROBI_ROOT_EXPERIMENT

    plan = read(directory / "plan.json")
    item = plan["rows"][task]
    leaf = directory / item["id"]
    paths = plan["inputs"]
    require(campaign.check_inputs(300, paths) == plan["input_sha256"], "Input drift.")
    selected = campaign.selection(300, paths)
    spec = contract.specification(item, paths["workbook"])
    with (leaf / "runtime.json").open("xb") as stream:
        stream.write(contract.encoded({
            "topology": topology(item["threads"]), "cell": item,
            "job_id": os.environ["SLURM_JOB_ID"],
        }))
    os.chdir(leaf)
    os.environ["TMPDIR"] = str(leaf)
    token = GUROBI_ROOT_EXPERIMENT.set({"matrix_sha256": MATRIX, "options": item["options"]})
    try:
        campaign.r.run_case_software(
            spec, leaf / "case", {"warehouses": 300, "periods": 60, "sto_scenarios": 9},
            selected, runner=run_experiment,
            input_reviewer=lambda data, receipt: contract.input_certificate(300, receipt),
        )
    finally:
        GUROBI_ROOT_EXPERIMENT.reset(token)


def execute(directory, task):
    resources = allocation("12:00:00")
    plan = read(directory / "plan.json")
    qualified = read(directory / "qualification.json")
    require(qualified["status"] == "accepted" and qualified["source"] == plan["source"],
            "Matching public qualification required.")
    require(qualified["job_id"] == read(directory / "public-job.json")["public_job"],
            "Public job receipt differs.")
    leaf = directory / plan["rows"][task]["id"]
    leaf.mkdir(mode=0o700)
    storage.check_growth(BASE, directory, plan, command=COMMAND)
    guard = JobMemoryGuard(os.environ["SLURM_JOB_ID"])
    write(leaf / "allocation.json", resources)
    license_receipt = probe()
    require(license_receipt["status"] == "accepted" and
            license_receipt["gurobi_version"] == [13, 0, 3], "Compute license/version differs.")
    with (leaf / "worker.out").open("xb") as out, (leaf / "worker.err").open("xb") as err:
        process = subprocess.Popen(
            [str(PYTHON), "-B", "-I", __file__, "worker", plan["source"], str(task)],
            stdout=out, stderr=err, start_new_session=True,
        )
        try:
            while process.poll() is None:
                guard.check()
                time.sleep(2)
            guard.check()
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
            write(leaf / "memory.json", guard.receipt())
        require(process.returncode == 0, "Worker failed. Inspect its original receipts.")
    check_source(plan["source"])
    storage.check_growth(BASE, directory, plan, command=COMMAND)


def submit(sha, budget):
    campaign.login()
    inputs = campaign.default_inputs()["300"]
    hashes = campaign.check_inputs(300, inputs)
    space = storage.check_initial(BASE, budget, command=COMMAND)
    config = capture(["scontrol", "show", "config"])
    size = re.search(r"(?m)^MaxArraySize\s*=\s*(\d+)", config)
    require(size and int(size[1]) >= len(schedule()), "Slurm array size is insufficient.")
    partition = capture(["scontrol", "show", "partition", "intel-256"])
    require("State=UP" in partition, "intel-256 is unavailable.")
    require(BASE.is_dir() and not BASE.is_symlink(), "NPAD audit directory differs.")
    inventory = source_inventory(sha)
    CLAIM.mkdir(mode=0o700)
    write(CLAIM / "plan.json", {
        "source_inventory": inventory, "source_root": str(ROOT),
        "source": sha, "rows": schedule(), "inputs": inputs, "input_sha256": hashes,
        "initial_storage": space, "storage_budget_gib_confirmed_in_human_CLI": budget,
        "campaign_allocated_bytes_at_prepare": 0,
    })
    write(CLAIM / "public-intent.json", {"source": sha, "purpose": "public qualification"})
    public = scheduler_submit(
        "h300-root-public-v2", ("--time=00:15:00",), sha, "qualify"
    )
    write(CLAIM / "public-job.json", {"public_job": public})
    print(json.dumps({"public_job": public, "claim": str(CLAIM)}, indent=2))


def scheduler_submit(name, flags, sha, action):
    exports = f"export GRB_LICENSE_FILE={shlex.quote(LICENSE_FILE)}; "
    entry = shlex.join([str(PYTHON), "-B", "-I", str(Path(__file__).resolve())])
    srun = (
        "srun --ntasks=1 --cpus-per-task=16 --threads-per-core=1 "
        "--distribution=block:block --cpu-bind=cores"
    )
    command = f"{exports}{srun} {entry} {action} {sha}"
    if action == "execute":
        command += ' "$SLURM_ARRAY_TASK_ID"'
    job = capture([
        "sbatch", *campaign.scheduler_arguments(), "--threads-per-core=1",
        f"--chdir={CLAIM}", f"--output={CLAIM}/slurm-%j.out",
        f"--error={CLAIM}/slurm-%j.err", "--parsable", f"--job-name={name}",
        *flags, "--wrap", command,
    ]).split(";")[0]
    require(job.isdecimal(), "Ambiguous submission. Preserve receipts and reconcile.")
    return job


def accounting(job):
    raw = capture(["sacct", "-j", job, "-n", "-P", "--format=JobID%40,State%60,ExitCode"])
    return {
        identity.strip(): [state.strip(), exit_code.strip()]
        for identity, state, exit_code in (line.split("|") for line in raw.splitlines())
    }


def submit_block(sha, block):
    campaign.login()
    require(block in (1, 2, 3), "Select block 1, 2, or 3.")
    path = CLAIM / f"block-{block}.json"
    intent = CLAIM / f"block-{block}-intent.json"
    with campaign.submission_lock(CLAIM):
        require(not path.exists() and not intent.exists(), "Block already attempted.")
        public = read(CLAIM / "public-job.json")["public_job"]
        qualified = read(CLAIM / "qualification.json")
        records = accounting(public)
        require(
            qualified["source"] == sha and qualified["job_id"] == public
            and qualified["status"] == "accepted"
            and all(records.get(key) == ["COMPLETED", "0:0"]
                    for key in (public, public + ".batch", public + ".0")),
            "Public qualification is not closed and accepted.",
        )
        if block > 1:
            previous = read(CLAIM / f"block-{block - 1}.json")["array_job"]
            records = accounting(previous)
            first = (block - 2) * BLOCK_SIZE
            terminal = {
                "COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY",
                "NODE_FAIL", "PREEMPTED", "BOOT_FAIL", "DEADLINE", "REVOKED",
            }
            require(all(
                records.get(f"{previous}_{index}", [""])[0].split(" ", 1)[0].rstrip("+")
                in terminal for index in range(first, first + BLOCK_SIZE)
            ), "Previous block accounting is incomplete or still active.")
        storage.check_growth(BASE, CLAIM, read(CLAIM / "plan.json"), command=COMMAND)
        active = capture(["squeue", "-r", "-h", "-u", str(os.getuid()), "-o", "%i"])
        require(
            len(active.splitlines()) + BLOCK_SIZE <= 95,
            "Current user queue leaves too few slots for a 60-task block.",
        )
        first = (block - 1) * BLOCK_SIZE
        last = first + BLOCK_SIZE - 1
        write(intent, {"block": block, "first": first, "last": last, "source": sha})
        job = scheduler_submit(
            f"h300-root-block-{block}",
            ("--hold", f"--array={first}-{last}%1"),
            sha, "execute",
        )
        write(path, {"block": block, "array_job": job, "public_job": public})
        capture(["scontrol", "release", job])
        write(CLAIM / f"block-{block}-release.json", {"array_job": job})
    print(json.dumps({"block": block, "array_job": job, "claim": str(CLAIM)}, indent=2))


def report():
    jobs = [read(CLAIM / "public-job.json")["public_job"]]
    for block in (1, 2, 3):
        receipt = CLAIM / f"block-{block}.json"
        if receipt.is_file():
            jobs.append(read(receipt)["array_job"])
    plan = read(CLAIM / "plan.json")
    print(capture(["sacct", "-j", ",".join(jobs),
                   "-P", "--format=JobIDRaw,State,ElapsedRaw,ExitCode,MaxRSS,AllocCPUS"]),
          file=sys.stderr)
    writer = csv.writer(sys.stdout)
    writer.writerow([
        "case", "method", "profile", "threads", "repetition", "status",
        "validation", "objective", "bound", "gap", "native_seconds", "end_to_end_seconds",
        "cgroup_peak_bytes", "root_log_events", "case_receipt",
    ])
    for item in plan["rows"]:
        leaf = CLAIM / item["id"]
        case = leaf / "case"
        products = case / "products" / item["id"]
        summary_path = products / "run_summary.json"
        summary = read(summary_path) if summary_path.is_file() else {}
        memory = read(leaf / "memory.json") if (leaf / "memory.json").is_file() else {}
        log = leaf / "gurobi-native.log"
        events = []
        if log.is_file():
            with log.open(encoding="utf-8", errors="replace") as lines:
                for line in lines:
                    if line.startswith((
                        "Presolve time:", "Root relaxation:", "Solved with", "Explored ",
                        "Concurrent spin time:", "NoRel heuristic",
                    )) and len(events) < 30:
                        events.append(line.strip())
        writer.writerow([
            item["id"], item["options"]["Method"], item["profile"], item["threads"],
            item["repetition"], summary.get("status"), summary.get("independent_validation_status"),
            summary.get("objective_value"), summary.get("objective_bound"), summary.get("mip_gap"),
            summary.get("runtime_seconds"), summary.get("end_to_end_seconds"),
            memory.get("peak_bytes"), " | ".join(events), str(case) if case.is_dir() else "",
        ])



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("plan", "submit", "block", "qualify", "execute", "worker", "report")
    )
    parser.add_argument("source", nargs="?")
    parser.add_argument("index", nargs="?", type=int)
    parser.add_argument("--budget-gib", type=int, default=48)
    args = parser.parse_args()
    if args.action == "plan":
        print(json.dumps(schedule(), indent=2))
        return
    if args.action == "submit":
        submit(args.source or "", args.budget_gib)
        return
    check_source(args.source or "")
    if args.action == "report":
        report()
    elif args.action == "block":
        submit_block(args.source, args.index)
    else:
        require(os.environ.get("SLURM_JOB_ID"), "Compute action requires Slurm.")
        if args.action == "qualify":
            qualify(CLAIM)
        else:
            require(args.index is not None and 0 <= args.index < len(schedule()),
                    "Array index outside the frozen grid.")
            require(os.environ.get("SLURM_ARRAY_TASK_ID") == str(args.index),
                    "Array task identity differs.")
            array_job = block_receipt(CLAIM, args.index)["array_job"]
            require(os.environ.get("SLURM_ARRAY_JOB_ID") == array_job, "Array job differs.")
            (execute if args.action == "execute" else worker)(CLAIM, args.index)


if __name__ == "__main__":
    main()
