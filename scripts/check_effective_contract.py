"""Run only declared local data/algebra tests; no optimizer or child process."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.no_solver_guard import NoSolverGuard  # noqa: E402

TESTS = (
    "tests/test_effective_baseline.py", "tests/test_excel_loader.py",
    "tests/test_warehouse_population.py", "tests/test_warehouse_workbook.py",
    "tests/test_route_filtering.py", "tests/test_effective_ci.py",
    "tests/test_effective_proposal.py",
    "tests/test_effective_policy.py",
    "tests/test_effective_h215_preparation.py",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    os.chdir(ROOT)
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    # Windows' first platform query may use `cmd /c ver`; cache host metadata
    # before entering the test-only no-child-process boundary.
    platform.uname()
    guard = NoSolverGuard()
    guard.install()
    import pytest

    result = pytest.main(["-q", "-p", "no:cacheprovider", *TESTS,
                          f"--junitxml={output / 'tests.xml'}"])
    suites = list(ET.parse(output / "tests.xml").getroot().iter("testsuite"))
    counts = {k: sum(int(s.get(k, 0)) for s in suites)
              for k in ("tests", "errors", "failures", "skipped")}
    accepted = result == 0 and guard.execution_blocks == 0 and counts["tests"] > 0 and all(
        counts[k] == 0 for k in ("errors", "failures", "skipped"))
    hashes = {str(p.relative_to(ROOT)).replace("\\", "/"):
              hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted((ROOT / "src/logic").glob("*.py"))}
    hashes.update({name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                   for name in (*TESTS, "scripts/no_solver_guard.py",
                                "scripts/check_effective_contract.py",
                                "scripts/effective_ci_scope.py")})
    report = {"status": "accepted" if accepted else "rejected", **counts,
              "test_inventory": TESTS, "source_files": hashes,
              "guard_blocks_during_tests": guard.blocked, "optimizer_calls": 0,
              "native_import_probes_blocked": guard.import_blocks,
              "forbidden_execution_attempts": guard.execution_blocks,
              "scope": "Data/schema and tiny algebra construction; not numerical qualification"}
    (output / "result.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k != "source_files"}))
    return 0 if accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
