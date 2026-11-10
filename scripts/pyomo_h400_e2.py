"""Freeze the six h400 E2 cells and bind admission to the closed E1 evidence."""

from scripts import pyomo_h400_e1 as e1
from scripts import pyomo_scaling_contract as contract

CAMPAIGN = ".mvp2-pyomo-h400-e2-native8h-v1"
QUALIFICATION = ".mvp2-pyomo-h400-e2-public-v1"
QUEUE = ".mvp2-pyomo-h400-e2-queue-v1"
STORAGE_GIB = 40
CASES = tuple(
    contract.cell(400, solver, threads, 1)
    for threads in (2, 4, 8)
    for solver in ("gurobi", "highs")
)
E1_CAMPAIGN = ".mvp2-pyomo-h400-e1-native8h-v1"
E1_QUEUE = ".mvp2-pyomo-h400-e1-queue-v1"
E1_SOURCE = "9dbfe04b81d80ae6a9ee4a9136b6f198d2180662"
E1_CAMPAIGN_SHA = "e2baeae5c30699fc3e701c577f6e196a9a7b2f4ca2d95f69224e90a5134272dd"
E1_GATE_SHA = "1c532269480f4f7fd4ff3fc820dc4bed405478fb077181a84e20e4bb7cd87616"
E1_GATE_JOB = "2247728"
E1_SOLVE_JOBS = ("2247718", "2247723", "2247725", "2247727")
E1_ARCHIVES = (
    "e21eec239a2c40406c75e3cdc0c55bffb9e7412cf163d508a0a90fc9059d1ee3",
    "8a6f8d6ed99c80523e1c7d5aa00361f1667d810909c6a67133eb8b676353b4bd",
    "7d7f42dcc807d15181fba9b6e02282ae77ef1b604ab48f8bb22bf5713402ad5a",
    "4104c2ffadd284f4d7a7f3d133e6ae0cec9db10b5443b9e2a210df9924d2d5c2",
)


def predecessor(base, *, digest, read, audit=False):
    campaign = base / E1_CAMPAIGN
    queue = base / E1_QUEUE
    gate_path = queue / "gate-4/gate_result.json"
    contract.require(
        not campaign.is_symlink() and not queue.is_symlink()
        and not gate_path.parent.is_symlink()
        and digest(campaign / "campaign.json") == E1_CAMPAIGN_SHA
        and digest(gate_path) == E1_GATE_SHA
        and read(queue / "gate-4.json")["job_id"] == E1_GATE_JOB,
        "Preserved E1 campaign or closing gate differs.",
    )
    gate = read(gate_path)
    proof = gate["proof"]
    ids = [cell["id"] for cell in e1.CASES]
    contract.require(
        gate["status"] == "accepted" and gate["cell"] == ids[-1]
        and proof["status"] == "e1_resource_criteria_met"
        and set(proof["cells"]) == set(ids)
        and tuple(proof["cells"][cell]["job_id"] for cell in ids) == E1_SOLVE_JOBS,
        "Four accepted E1 pilot receipts required.",
    )
    archives = dict(zip(ids, E1_ARCHIVES, strict=True))
    for cell, sha in archives.items():
        claim = campaign / cell
        contract.require(
            not claim.is_symlink() and read(claim / "collection.json")["sha256"] == sha,
            "Preserved E1 archive digest differs.",
        )
    if audit:
        actual = e1.evaluate(e1.read_bundle(campaign), E1_CAMPAIGN_SHA, E1_SOURCE)
        contract.require(actual == proof, "Archived E1 closure replay differs.")
    return {
        "campaign_sha256": E1_CAMPAIGN_SHA, "gate_job_id": E1_GATE_JOB,
        "gate_result_sha256": E1_GATE_SHA, "solve_jobs": list(E1_SOLVE_JOBS),
        "archive_sha256": archives,
    }
