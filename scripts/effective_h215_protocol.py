"""Materialize prospective h215 policy cases without constructing or solving MILPs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.logic.mathematical_contract import canonical_hash  # noqa: E402

PROTOCOL = ROOT / "experiments/h215_policy_protocol_v1.json"


def cases(protocol=None):
    protocol = protocol or json.loads(PROTOCOL.read_text())
    controls = [(None, None)]
    controls += [(b, None) for b in protocol["beta_levels"]]
    controls += [(None, a) for a in protocol["alpha_levels"]]
    controls += [(b, a) for b in protocol["beta_levels"] for a in protocol["alpha_levels"]]

    def name(value):
        return "off" if value is None else str(round(value * 100))

    records = []
    for mode in protocol["modes"]:
        for beta, alpha in controls:
            record = {
                "id": f"h215-w-{mode}-b{name(beta)}-a{name(alpha)}",
                "population": 215,
                "mode": mode,
                "topology": "W",
                "beta": beta,
                "alpha": alpha,
                "multipliers": {},
                "justification": "Approved horizon service/export scope; prospective h215 cycle.",
                "status": "not_submitted",
                "job_id": None,
            }
            record["specification_sha256"] = canonical_hash(record)
            records.append(record)
    if len(records) != protocol["observations"]:
        raise ValueError("Protocol case count differs.")
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    record = {
        "status": "prepared_no_job",
        "cases": cases(),
        "execution_authorized": False,
        "protocol_sha256": canonical_hash(json.loads(PROTOCOL.read_text())),
    }
    with args.output.open("x", encoding="utf-8") as f:
        f.write(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"status": record["status"], "observations": len(record["cases"])}))


if __name__ == "__main__":
    main()
