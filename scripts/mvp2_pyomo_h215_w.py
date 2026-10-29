"""One independently claimed common-form Pyomo h215 STO/W observation.

Static parameterization of the qualified HiGHS startup/phase/collection protocol.
Original launchers and scientific backends are unchanged. No solver sweep.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import time
from dataclasses import asdict, replace
from importlib.metadata import distribution
from pathlib import Path

from scripts import mvp2_scalar_wd_h215_gate as g
from scripts import mvp2_scalar_wd_h215_operational as d
from scripts import pyomo_campaign_contract as contract
from scripts import pyomo_worker_bootstrap as bootstrap
from scripts.scip_external_observer import ExternalObserver, review_external

o, r = (g.old, g.r)
ROOT = Path(__file__).resolve().parents[1]
MODES = ("sto",)
SOLVERS = ("gurobi", "scip", "cbc")
SHAPE = dict(o.SHAPE)
INPUT_KEYS = d.INPUT_KEYS
POLICY = "bounded_scalar_slacks_v1"
PYOMO_PATHS = {
    "src/logic/optimization_pyomo.py",
    "src/logic/pyomo_bounds.py",
    "src/logic/pyomo_linear_matrix.py",
    "src/logic/pyomo_scip_adapter.py",
}
PACKAGES = {"pyomo": "6.10.1", "gurobipy": "13.0.3", "pyscipopt": "6.2.1", "highspy": "1.15.1"}
ADMISSION_COMMAND = [
    "sbatch",
    "--test-only",
    "--account=sxdsouza",
    "--partition=intel-256",
    "--qos=preempt",
    "--nodes=1",
    "--ntasks=1",
    "--cpus-per-task=24",
    "--mem=192G",
    "--time=12:00:00",
    "--no-requeue",
    "--wrap=/usr/bin/true",
]


class Campaign:
    def __init__(self, solver):
        r.require(solver in SOLVERS, "Choose one reviewed Gurobi/SCIP/CBC arm.")
        self.solver = solver
        self.CLAIM = f".mvp2-pyomo-{solver}-h215-w-native8h-v1"
        self.CASE = f"pyomo_{solver}_h215_w_native8h"
        self.ARCHIVE = f"pyomo-{solver}-h215-w-native8h-evidence.tar.gz"
        self.PROFILE = {
            **{k: v for k, v in o.PROFILE.items() if k != "solver_soft_memory_decimal_gb"},
            "status": "one_common_pyomo_W_arm_requested_20261029",
            "slurm_wall_seconds": 43200,
            "build_input_seconds_per_arm": 3600,
            "native_time_limit_seconds_per_arm": 28800,
            "solver_threads": 4,
        }

    def recheck_inputs(self, plan, source_files=None):
        d.recheck_inputs(plan)
        raw, _, cbc = contract.read_qualification(Path(plan["cbc_path"]).parent.parent.parent)
        require_same = str(cbc.resolve()) == plan["cbc_path"]
        for name, content in raw.items():
            require_same = (
                require_same
                and r.r2.digest(content) == plan["artifact_sha256"]["qualification." + name]
            )
        r.require(require_same, "Original qualification/CBC changed.")
        # Read only the immutable plan-bound source inventory; do not execute Git on compute.
        if source_files is None:
            source_files = r.r2.read(Path(plan["claim_path"]) / "source.json")["files"]
        operational = contract.read_operational(Path(plan["claim_path"]).parent, source_files)
        r.require(
            all(
                r.r2.digest(content) == plan["artifact_sha256"]["operational." + name]
                for name, content in operational.items()
            ),
            "Original operational qualification changed.",
        )

    def admission_test(self):
        """Human CLI only: Slurm validation, no job or executable is launched."""
        result = r.r2.command(ADMISSION_COMMAND, timeout=30)
        r.require(result.returncode == 0, "12h scheduler preflight rejected; no claim/job created.")
        return {
            "argv": ADMISSION_COMMAND,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "job_submitted": False,
        }

    def closed(self):
        return {
            **r.closed(),
            "highs_execution_admitted": False,
            "additional_highs_execution_admitted": False,
            "additional_scip_execution_admitted": False,
            "additional_gurobi_execution_admitted": False,
            "additional_cbc_execution_admitted": False,
        }

    def budget(self):
        per = sum(
            self.PROFILE[k]
            for k in (
                "build_input_seconds_per_arm",
                "native_time_limit_seconds_per_arm",
                "late_return_export_seconds_per_arm",
                "validation_seconds_per_arm",
            )
        )
        planned = per + self.PROFILE["setup_cleanup_seconds"]
        r.require(per == 35100 and planned == 36900 and (planned < 43200), "Budget ledger.")
        return {
            "step_seconds": per,
            "planned_seconds": planned,
            "reserve_seconds": 6300,
            "reservation_logical_cpu_hours": 288,
            "scope": "One observation; allocation product, not measured utilization.",
            **self.closed(),
        }

    def spec(self, workbook):
        original = o.specs(workbook)[1]
        return replace(
            original,
            name=self.CASE,
            max_estimated_variables=16000000,
            solver=replace(
                original.solver,
                backend="pyomo",
                solver_name=self.solver,
                time_limit=28800,
                threads=4,
                tee=True,
                log_file=self.solver + "-native.log",
                collect_resource_diagnostics=False,
                solver_options={"indicator_reformulation": POLICY, "pyomo_max_variables": 16000000},
            ),
        )

    def case_contract(self, cases):
        from src.logic.experiment_runner import load_experiment_manifest

        template = load_experiment_manifest(r.MANIFEST).experiments[1]
        expected = {
            "name": self.CASE,
            "workbook_sha256": o.WORKBOOK_SHA,
            "loader": asdict(template.loader),
            "model": asdict(template.model),
            "solver": asdict(
                replace(
                    template.solver,
                    backend="pyomo",
                    solver_name=self.solver,
                    time_limit=28800,
                    threads=4,
                    tee=True,
                    log_file=self.solver + "-native.log",
                    collect_resource_diagnostics=False,
                    solver_options={
                        "indicator_reformulation": POLICY,
                        "pyomo_max_variables": 16000000,
                    },
                )
            ),
            "max_estimated_variables": 16000000,
            "metadata": template.metadata,
        }
        r.require(
            len(cases) == 1
            and {k: v for k, v in cases[0].items() if k != "workbook"}
            == r.strict_json(r.r2.encoded(expected)),
            "Frozen one-arm common Pyomo contract differs.",
        )

    def environment(self):
        """Installed metadata and package bytes only; no solver imports on login."""
        packages, fingerprints = ({}, {})
        for name, expected in PACKAGES.items():
            dist = distribution(name)
            r.require(
                dist.version == expected, "Existing " + name + expected + " required; no install."
            )
            packages[name] = dist.version
            files = {}
            for item in dist.files or []:
                relative = str(item)
                if ".." in Path(relative).parts:
                    continue
                if (
                    relative.endswith((".py", ".so", ".pyd", ".dll", ".dylib"))
                    or ".so." in relative
                ):
                    path = Path(dist.locate_file(item))
                    r.require(
                        path.is_file() and (not path.is_symlink()), "Dependency file/link differs."
                    )
                    files[relative] = r.file_hash(path)
            r.require(files, "Installed package fingerprint unavailable.")
            fingerprints[name] = r.r2.digest(r.r2.encoded(files))
        dependencies = {
            name: distribution(name).version for name in ("numpy", "pandas", "openpyxl", "PyYAML")
        }
        return {
            **packages,
            "python": platform.python_version(),
            "dependencies": dependencies,
            "package_sha256": fingerprints,
        }

    def output_location(self, claim):
        home = Path("/home/vrrcelestino").resolve()
        parent = claim.parent.resolve()
        r.require(
            not claim.is_symlink()
            and claim.name == self.CLAIM
            and (parent.parent == home)
            and parent.name.startswith("model-agrologistic")
            and (parent.name != "model-agrologistic"),
            "Use a dedicated model-agrologistic output sibling, never home/input checkout.",
        )

    def design(self, files):
        plan = r.strict_json(files["plan.json"])
        previous = r.strict_json(files["historical_w.json"])
        source = r.strict_json(files["source.json"])
        selection = r.strict_json(files["warehouse_selection.json"])
        r.require(
            plan["schema_version"] == "common-pyomo-h215-w-native8h-v1"
            and plan["profile"] == self.PROFILE
            and (plan["budget"] == self.budget())
            and (plan["expected_shape"] == SHAPE)
            and all((plan[k] == v for k, v in self.closed().items())),
            "Pyomo scope/resource/admission differs.",
        )
        self.case_contract(plan["cases"])
        qualified = contract.qualification(
            files["qualification.plan.json"], files["qualification.result.json"]
        )
        contract.operational_qualification(
            files["operational.plan.json"], files["operational.result.json"], source["files"]
        )
        r.require(plan["solver_name"] == self.solver, "Solver/claim binding differs.")
        r.require(
            {k: v for k, v in source["files"].items() if k.startswith("src/logic/")}
            == {k: v for k, v in qualified["source_files"].items() if k.startswith("src/logic/")},
            "Public-qualified scientific source bytes differ.",
        )
        probe = r.strict_json(files["admission_test.json"])
        r.require(
            probe["argv"] == ADMISSION_COMMAND
            and probe["returncode"] == 0
            and (probe["job_submitted"] is False),
            "12h admission preflight differs.",
        )
        for name in (
            "source.json",
            "historical_w.json",
            "warehouse_selection.json",
            "materialization.original.json",
            "admission_test.json",
            "qualification.plan.json",
            "qualification.result.json",
            "operational.plan.json",
            "operational.result.json",
        ):
            r.require(
                r.r2.digest(files[name]) == plan["artifact_sha256"][name], "Plan artifact drift."
            )
        r.require(
            re.fullmatch("[0-9a-f]{40}", plan["source_commit"])
            and source["source_commit"] == plan["source_commit"]
            and (previous["archive_sha256"] == g.W_SHA)
            and (previous["source_commit"] == g.W_SOURCE)
            and (previous["plan_sha256"] == g.W_PLAN)
            and (previous["review"]["job_id"] == "2217990")
            and (previous["review"]["status"] == "pair_quality_target_met"),
            "Historical W/source binding differs.",
        )
        r.require(
            {
                k: v
                for k, v in source["files"].items()
                if k.startswith("src/logic/") and k not in PYOMO_PATHS
            }
            == {k: v for k, v in previous["scientific_sources"].items() if k not in PYOMO_PATHS}
            and PYOMO_PATHS <= source["files"].keys(),
            "Native source changed; only disclosed Pyomo extension is allowed.",
        )
        o.materialization(r.strict_json(files["materialization.original.json"]))
        r.require(
            selection["target_population"] == 215
            and selection["population_manifest_sha256"] == o.POPULATION_SHA
            and (selection["population_order_sha256"] == o.ORDER_SHA),
            "Frozen h215 membership differs.",
        )
        r.require(
            plan["input_sha256"]
            == {
                "workbook": o.WORKBOOK_SHA,
                "population": o.POPULATION_SHA,
                "order": o.ORDER_SHA,
                "w_archive": g.W_SHA,
                "materialization": plan["artifact_sha256"]["materialization.original.json"],
            }
            and all(plan["environment"][k] == v for k, v in PACKAGES.items())
            and plan["cbc_sha256"] == contract.CBC_SHA,
            "Frozen inputs/runtime differ.",
        )
        return plan

    def plan_files(self, claim):
        return {
            n: o.regular(claim / n).read_bytes()
            for n in (
                "plan.json",
                "source.json",
                "historical_w.json",
                "warehouse_selection.json",
                "materialization.original.json",
                "admission_test.json",
                "qualification.plan.json",
                "qualification.result.json",
                "operational.plan.json",
                "operational.result.json",
            )
        }

    def prepare(self, claim, sha, **paths):
        self.output_location(claim)
        r.require(not claim.exists(), "Fresh exclusive Pyomo claim required; preserve old claim.")
        frozen = {k: o.regular(paths[k]) for k in INPUT_KEYS}
        hashes = {k: r.file_hash(p) for k, p in frozen.items()}
        r.require(hashes["workbook"] == o.WORKBOOK_SHA, "Original h215 workbook checksum differs.")
        material = frozen["materialization"].read_bytes()
        o.materialization(r.strict_json(material))
        selection = r.warehouses.read_policy(
            frozen["population"], frozen["order"], o.POPULATION_SHA, o.ORDER_SHA, 215
        )
        qualified, _, cbc = contract.read_qualification(claim.parent)
        previous = g.historical_w(frozen["w_archive"])
        inventory = g.source_inventory(ROOT)
        r.require(inventory["source_commit"] == sha, "Exact source SHA required.")
        operational = contract.read_operational(claim.parent, inventory["files"])
        r.require(
            self.solver != "cbc"
            or not r.strict_json(operational["result.json"])["cbc_capability"]["cbc_arm_cancelled"],
            "CBC h215 arm cancelled: the qualified binary does not accept threads.",
        )
        tools = {k: str(o.regular(Path(shutil.which(k) or "").resolve())) for k in o.TOOLS}
        artifacts = {
            "source.json": r.r2.encoded(inventory),
            "historical_w.json": r.r2.encoded(previous),
            "qualification.plan.json": qualified["plan.json"],
            "qualification.result.json": qualified["result.json"],
            "operational.plan.json": operational["plan.json"],
            "operational.result.json": operational["result.json"],
            "warehouse_selection.json": r.r2.encoded(selection),
            "materialization.original.json": material,
            "admission_test.json": r.r2.encoded(self.admission_test()),
        }
        plan = {
            "schema_version": "common-pyomo-h215-w-native8h-v1",
            "source_commit": sha,
            "solver_name": self.solver,
            "cbc_path": str(cbc.resolve()),
            "cbc_sha256": contract.CBC_SHA,
            "source_root": str(ROOT),
            "claim_path": str(claim),
            "python": sys.executable,
            "python_sha256": r.file_hash(sys.executable),
            "environment": self.environment(),
            "tools": tools,
            "tool_sha256": {k: r.file_hash(p) for k, p in tools.items()},
            "input_paths": {k: str(v.resolve()) for k, v in frozen.items()},
            "input_sha256": hashes,
            "artifact_sha256": {n: r.r2.digest(b) for n, b in artifacts.items()},
            "cases": [r.spec_payload(self.spec(frozen["workbook"]))],
            "profile": self.PROFILE,
            "budget": self.budget(),
            "expected_shape": SHAPE,
            **self.closed(),
        }
        artifacts["plan.json"] = r.r2.encoded(plan)
        self.design(artifacts)
        self.recheck_inputs(plan, inventory["files"])
        r.r2.verify_source(inventory, ROOT)
        claim.mkdir(mode=448)
        for name, content in artifacts.items():
            with (claim / name).open("xb") as stream:
                stream.write(content)
        return plan

    def load(self, claim, sha, *, startup=None):

        def measured(name, operation):
            return operation() if startup is None else startup.stage(name, operation)

        def read_plan():
            self.output_location(claim)
            files = self.plan_files(claim)
            plan = self.design(files)
            r.require(
                plan["source_commit"] == sha
                and Path(plan["source_root"]).resolve() == ROOT
                and Path(plan["claim_path"]) == claim,
                "Exact source/root mismatch.",
            )
            return (plan, files)

        plan, files = measured("plan_validation", read_plan)
        measured(
            "source_verification",
            lambda: r.r2.verify_source(r.strict_json(files["source.json"]), ROOT),
        )

        def runtime():
            r.require(
                r.file_hash(sys.executable) == plan["python_sha256"]
                and self.environment() == plan["environment"],
                "Existing interpreter/native distribution changed.",
            )

        measured("runtime_fingerprints", runtime)
        measured("input_hashes", lambda: self.recheck_inputs(plan))
        return plan

    def invocation(self, action, claim, sha, *extra):
        if action == "worker":
            return [
                sys.executable,
                "-B",
                "-I",
                "-S",
                str(ROOT / bootstrap.BOOTSTRAP),
                "--claim",
                str(claim),
                "--source-sha",
                sha,
                "--solver",
                self.solver,
                *extra,
            ]
        return [
            sys.executable,
            "-B",
            "-I",
            "-c",
            "import runpy,sys;sys.dont_write_bytecode=True;"
            "sys.path.insert(0,sys.argv.pop(1));"
            "runpy.run_module('scripts.mvp2_pyomo_h215_w',run_name='__main__')",
            str(ROOT),
            action,
            "--claim",
            str(claim),
            "--source-sha",
            sha,
            "--solver",
            self.solver,
            *extra,
        ]

    def start(self, claim, sha, acknowledged, paths, *, command=r.r2.command):
        r.require(acknowledged, "Explicit human one-reviewed-Pyomo-W acknowledgement required.")
        self.output_location(claim)
        r.require(
            sys.version_info[:2] == (3, 13) and (not os.environ.get("SLURM_JOB_ID")),
            "Login Python3.13 only.",
        )
        r.require(not claim.exists(), "Existing Pyomo claim: inspect/collect, never submit again.")
        plan = self.prepare(claim, sha, **paths)
        token = r.r2.digest(r.r2.encoded(plan))
        with (claim / "batch.sh").open("x", newline="\n") as stream:
            stream.write(
                "#!/bin/sh\nexec " + shlex.join(self.invocation("batch", claim, sha)) + "\n"
            )
        r.r2.write(
            claim / "submission_intent.json",
            {
                "plan_sha256": token,
                "solver": self.solver,
                "one_Pyomo_W_acknowledged": True,
                "automatic_retry": False,
            },
        )
        result = command(
            [
                "sbatch",
                "--parsable",
                "--account=sxdsouza",
                "--partition=intel-256",
                "--qos=preempt",
                "--nodes=1",
                "--ntasks=1",
                "--cpus-per-task=24",
                "--mem=192G",
                "--time=12:00:00",
                "--no-requeue",
                "--export=ALL",
                "--job-name=pyomo-" + self.solver + "-h215-W-native8h",
                "--chdir=" + str(claim),
                "--output=" + str(claim / "slurm.out"),
                "--error=" + str(claim / "slurm.err"),
                str(claim / "batch.sh"),
            ]
        )
        r.r2.write(
            claim / "submission.json",
            {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr},
        )
        match = re.fullmatch("([1-9][0-9]*)(?:;[A-Za-z0-9_.-]+)?\\s*", result.stdout)
        r.require(
            result.returncode == 0 and match, "Submission uncertain; preserve claim, never retry."
        )
        job = {"job_id": match[1], "source_commit": sha, "plan_sha256": token}
        o.publish(claim / "job.json", job)
        return {
            "status": "submitted_one_pyomo_W_only",
            "solver": self.solver,
            **job,
            **self.closed(),
        }

    def inspect_native(self):
        """Compute-only selected-engine identity; no population optimization."""
        if self.solver == "gurobi":
            import gurobipy

            version = ".".join(map(str, gurobipy.gurobi.version()))
            r.require(version == "13.0.3", "Pinned native Gurobi required.")
        elif self.solver == "scip":
            from pyscipopt import Model

            native = Model()
            try:
                version = ".".join(
                    str(f())
                    for f in (native.getMajorVersion, native.getMinorVersion, native.getTechVersion)
                )
            finally:
                native.freeProb()
            r.require(version == "10.0.2", "Pinned native SCIP required.")
        else:
            from pyomo.environ import SolverFactory

            adapter = SolverFactory("cbc")
            r.require(adapter.available(exception_flag=False), "Qualified CBC required.")
            version = ".".join(map(str, adapter.version()))
            r.require(version == "2.10.13.0", "Pinned native CBC required.")
        return {
            "pyomo": "6.10.1",
            "solver": self.solver,
            "native_version": version,
            "population_optimized": False,
        }

    def run_math(self, control):
        """Fresh real public parity controls on compute; never a private-input test."""
        import xml.etree.ElementTree as et

        report = control / "qualification.xml"
        with (
            (control / "qualification.out").open("xb") as out,
            (control / "qualification.err").open("xb") as err,
        ):
            checked = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-I",
                    "-c",
                    "import runpy,sys;sys.path.insert(0,sys.argv.pop(1));"
                    "runpy.run_module('pytest',run_name='__main__')",
                    str(ROOT),
                    str(ROOT / "tests/test_pyomo_multisolver.py"),
                    str(ROOT / "tests/test_pyomo_solver_adapters.py"),
                    str(ROOT / "tests/test_pyomo_campaign_contract.py")
                    + "::test_real_public_native_settings_match_operational_contract",
                    str(ROOT / "tests/test_pyomo_campaign_contract.py")
                    + "::test_real_cbc_public_control_requires_thread_capability",
                    "-p",
                    "no:cacheprovider",
                    "--basetemp=" + str(control / "qualification-cases"),
                    "--junitxml=" + str(report),
                    "-q",
                ],
                stdout=out,
                stderr=err,
                timeout=600,
                check=False,
                env={
                    **os.environ,
                    "AGRO_REQUIRE_PYOMO_SOLVERS": "1",
                    "AGRO_REQUIRE_NATIVE_SOLVERS": "1",
                    "PYTEST_ADDOPTS": "",
                    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
                },
            )
        cases = list(et.fromstring(report.read_bytes()).iter("testcase"))
        r.require(
            checked.returncode == 0
            and len(cases) == 71
            and all(not any(e.tag in {"failure", "error", "skipped"} for e in c) for c in cases),
            "Fresh common-form public gate failed/skipped.",
        )
        return {"tests": 71, "failures": 0, "errors": 0, "skipped": 0, "status": "accepted"}

    def compare_input(self, specification, data, receipt, previous):
        cell = g.inspect_cell(specification, loader=lambda *_: data)
        cell.pop("warehouse_data")
        prior = previous["receipts"]["sto"]
        r.require(
            receipt["warehouse_selection"] == prior["warehouse_selection"]
            and cell["contract"] == prior["mathematical_contract"]
            and (cell["effective_probabilities"] == prior["effective_scenario_probabilities"])
            and (len(cell["edges"]["oc"]) == 0)
            and (
                {k: len(v) for k, v in cell["edges"].items()}
                == {"od": 3182, "dc": 3440, "dd": 18490, "oc": 0}
            ),
            "Same original W input/membership/graph/objective/scenarios required.",
        )

    def run_case(self, selected, target, selection, control, entry, previous):
        """Observe existing resource phases; no mathematical/solver backend edits."""
        from src.logic.experiment_runner import run_experiment
        from src.logic.optimization import solve_model
        from src.logic.optimization_pyomo import PHASE_OBSERVER

        names = ["input_build"]
        origin = entry["started_monotonic"]

        def mark(name):
            r.require(name == o.PHASES[len(names)], "Phase order differs.")
            o.publish(
                control / f"phase-{len(names):02d}.json",
                {
                    "entry": entry,
                    "phase": name,
                    "elapsed_seconds": 0.0 if not names else time.monotonic() - origin,
                },
            )
            names.append(name)

        r.require(
            r.r2.read(control / "phase-00.json")
            == {"entry": entry, "phase": "input_build", "elapsed_seconds": 0.0},
            "Bootstrap must start the original build budget.",
        )

        def solve(*, data, model_config, solver_config):
            token = PHASE_OBSERVER.set(mark)
            try:
                result = solve_model(data, model_config, solver_config)
            finally:
                PHASE_OBSERVER.reset(token)
            metadata = result.metadata
            parameter_evidence = contract.metadata(
                self.solver,
                metadata,
                cbc_log=(control / "cbc-native.log").read_text(errors="replace")
                if self.solver == "cbc"
                else None,
            )
            proof = metadata["pyomo_reformulation"]
            r.require(
                proof["policy"] == POLICY
                and proof["equivalence"]
                == "physical_investment_projection_and_optimal_scalar_value"
                and (proof["entire_redundant_slack_region_preserved"] is False),
                "Disclosed reformulation proof differs.",
            )
            o.publish(
                control / "native_terminal.json",
                {
                    "entry": entry,
                    "status": metadata["solver_termination"],
                    "runtime_seconds": metadata["timings"]["solver_reported_runtime_seconds"],
                    "time_limit_seconds": solver_config.time_limit,
                    "parameter_evidence": parameter_evidence,
                    "reformulation": proof,
                    "common_linear_matrix": metadata["common_linear_matrix"],
                    "native_counters": metadata["native_counters"],
                },
            )
            mark("independent_validation")
            return result

        def progress(message):
            if "exporting structured artifacts" in message:
                mark("artifact_export")

        def runner(*args, **kwargs):
            kwargs.update(solver=solve, progress=progress)
            return run_experiment(*args, **kwargs)

        result = r.run_case_software(
            selected,
            target,
            SHAPE,
            selection,
            runner=runner,
            input_reviewer=lambda data, receipt: self.compare_input(
                selected, data, receipt, previous
            ),
        )
        mark("complete")
        return result

    def worker(self, claim, sha, mode, *, entry, startup):
        """Already bound bootstrap; all expensive checks are timed within input_build."""
        control = claim / "control/sto"
        r.require(
            mode == "sto"
            and r.r2.read(control / "entry.json") == entry
            and (r.r2.read(control / "release.json") == entry),
            "Minimal bootstrap and exact-step release required.",
        )
        plan = self.load(claim, sha, startup=startup)
        scratch = control / "native-temporary"
        scratch.mkdir(exist_ok=False)
        os.environ.update(
            {
                "TMPDIR": str(scratch),
                "TMP": str(scratch),
                "TEMP": str(scratch),
                "PATH": str(Path(plan["cbc_path"]).parent)
                + os.pathsep
                + os.environ.get("PATH", ""),
            }
        )
        job = o.job_receipt(claim, sha)
        r.require(
            all((entry[k] == v for k, v in job.items()))
            and entry["pid"] == os.getpid()
            and (entry["proc_start_ticks"] == bootstrap.proc_start(os.getpid()))
            and (os.environ.get("SLURM_JOB_ID") == job["job_id"])
            and (os.environ.get("SLURM_STEP_ID") == entry["step_id"]),
            "Released worker identity differs.",
        )
        startup.stage("tool_verification", lambda: o.verify_tools(plan))
        affinity = sorted(os.sched_getaffinity(0))
        r.require(4 <= len(affinity) == len(set(affinity)) <= 24, "Observed affinity differs.")
        native = startup.stage("native_identity", self.inspect_native)
        r.r2.write(control / "native_build.json", native)
        checked = startup.stage("public_qualification", lambda: self.run_math(control))
        r.r2.write(control / "qualification.json", checked)

        def runtime_receipt():
            r.r2.write(
                control / "runtime.json",
                {
                    "python": platform.python_version(),
                    "python_sha256": r.file_hash(sys.executable),
                    "affinity_logical_cpus": affinity,
                    "solver_threads": 4,
                    "native": native,
                    "hardware": d.hardware_observation(),
                    "scope": "Thread ceilings, not observed parallel execution.",
                },
            )

        startup.stage("runtime_receipt", runtime_receipt)
        selected = self.spec(Path(plan["cases"][0]["workbook"]))
        r.require(
            r.strict_json(r.r2.encoded(r.spec_payload(selected))) == plan["cases"][0],
            "Frozen Pyomo case drift.",
        )
        r.require(
            Path.cwd().resolve() == control.resolve(), "Native log must stay in owned control."
        )
        self.run_case(
            selected,
            claim / "cases" / selected.name,
            r.r2.read(claim / "warehouse_selection.json"),
            control,
            entry,
            r.r2.read(claim / "historical_w.json"),
        )
        self.load(claim, sha)

    def snapshot(self, claim):
        """Retain real pytest products once; only internal generated aliases are skipped."""
        files = {}
        scratch = {}
        for path in sorted(claim.rglob("*")):
            if path.is_symlink():
                r.require(
                    path.name.endswith("current")
                    and path.resolve().is_relative_to(
                        (claim / "control/sto/qualification-cases").resolve()
                    ),
                    "Linked evidence rejected.",
                )
                continue
            if not path.is_file():
                continue
            name = path.relative_to(claim).as_posix()
            if name.startswith("control/sto/native-temporary/"):
                scratch[name] = {"bytes": path.stat().st_size, "sha256": r.file_hash(path)}
                continue
            if name in {self.ARCHIVE, self.ARCHIVE + ".sha256", "collection.json"}:
                continue
            public_fixture = path.is_relative_to(claim / "control/sto/qualification-cases")
            r.require(
                r._safe_name(name)
                and path.suffix.lower() not in {".lic", ".sqlite3"}
                and (path.suffix.lower() != ".xlsx" or public_fixture),
                "Forbidden private evidence member.",
            )
            r.require(path.stat().st_size <= 1024**3, "Evidence cap, no truncation.")
            files[name] = path.read_bytes()
            r.require(
                len(files) <= 4094 and sum(map(len, files.values())) <= 1024**3, "Transfer cap."
            )
        files["native_temporary_inventory.json"] = r.r2.encoded(
            {
                "scope": "Generated native scratch remains preserved at NPAD; not transferred.",
                "files": scratch,
            }
        )
        return files

    def case_review(self, files, plan):
        base = "cases/" + self.CASE + "/products/" + self.CASE + "/"
        result = r.strict_json(files[base + "result.json"])
        native = result["result"]
        completion = r.strict_json(files[base + "run_completion.json"])
        validation = r.strict_json(files[base + "independent_validation.json"])
        summary = r.strict_json(files[base + "run_summary.json"])
        r.require(
            result["schema_version"] == 2
            and result["experiment"] == plan["cases"][0]
            and (native["solver_backend"] == "pyomo")
            and (native["solver_name"] == self.solver)
            and (native["model_mode"] == "sto")
            and (completion["status"] == "complete")
            and (completion["run_identity"] == native["metadata"]["run_identity"]),
            "Original scalar Pyomo completion/identity differs.",
        )
        required = {
            "result.json",
            "run_summary.json",
            "independent_validation.json",
            "preflight.json",
            "model_audit.json",
        }
        r.require(required <= completion["artifacts"].keys(), "Incomplete products.")
        for name, digest in completion["artifacts"].items():
            r.require(
                r._safe_name(name) and r.r2.digest(files[base + name]) == digest,
                "Original completion artifact drift.",
            )
        receipt = r.strict_json(files["cases/" + self.CASE + "/input_receipt.json"])
        population = r.strict_json(files["cases/" + self.CASE + "/warehouses_used.json"])
        historical = r.strict_json(files["historical_w.json"])["receipts"]["sto"]
        r.require(
            receipt["experiment"] == plan["cases"][0]
            and receipt["mathematical_contract"] == historical["mathematical_contract"]
            and (
                receipt["effective_scenario_probabilities"]
                == historical["effective_scenario_probabilities"]
            )
            and (receipt["warehouse_selection"] == population == historical["warehouse_selection"])
            and (
                files["cases/" + self.CASE + "/warehouses_used.csv"]
                == r.warehouses.csv_bytes(population["included"])
            ),
            "Original W input/selection/scenario certificate binding differs.",
        )
        metadata = native["metadata"]
        parameter_evidence = contract.metadata(
            self.solver,
            metadata,
            cbc_log=files["control/sto/cbc-native.log"].decode(errors="replace")
            if self.solver == "cbc"
            else None,
        )
        proof = metadata["pyomo_reformulation"]
        r.require(
            proof["policy"] == POLICY
            and (proof["equivalence"] == "physical_investment_projection_and_optimal_scalar_value")
            and (proof["entire_redundant_slack_region_preserved"] is False)
            and re.fullmatch("[0-9a-f]{64}", proof["bounds_sha256"])
            and isinstance(proof["candidate_slack_bounds"], int)
            and (proof["candidate_slack_bounds"] >= 0)
            and isinstance(proof["maximum_bound"], (int, float))
            and (0 <= proof["maximum_bound"] < float("inf")),
            "Pyomo reformulation/runtime provenance differs.",
        )
        from src.logic.optimization import OptimizationResult, scalar_mip_gap

        usable = OptimizationResult(
            status=native["status"], objective_value=native["objective_value"]
        ).has_solution
        accepted = (
            usable
            and validation["status"] == "accepted"
            and (validation["failed_check_count"] == 0)
        )
        r.require(
            summary["independent_validation_status"] == validation["status"], "Validation summary."
        )
        if accepted:
            r.require(
                validation["validator_version"] == "mvp2-scalar-independent-residuals-v1"
                and validation["absolute_tolerance"] == 1e-05
                and (validation["relative_tolerance"] == 1e-08)
                and all(f["failed"] == 0 for f in validation["families"].values()),
                "Original independent residual contract differs.",
            )
        gap = scalar_mip_gap(native["objective_value"], native.get("objective_bound"))
        quality = accepted and gap is not None and (gap <= 0.01)
        classification = (
            "quality_target_met"
            if quality
            else "validated_feasible_above_target_or_uncertified_bound"
            if accepted
            else "incumbent_validation_rejected"
            if usable
            else "no_usable_incumbent"
        )
        return {
            "classification": classification,
            "quality_target_met": quality,
            "has_usable_incumbent": usable,
            "original_validation_status": validation["status"],
            "objective": native["objective_value"],
            "bound": native.get("objective_bound"),
            "common_gap": gap,
            "native_gap": metadata.get("pyomo_native_gap"),
            "native_status": metadata["solver_termination"],
            "timings": metadata["timings"],
            "reformulation": proof,
            "common_linear_matrix": metadata["common_linear_matrix"],
            "parameter_evidence": parameter_evidence,
            "native_counters": metadata["native_counters"],
            "economic_cost": summary.get("economic_cost") if usable else None,
            "penalized_total": summary.get("penalized_cost") if usable else None,
            "solver": self.solver,
            "interpretation": "One common-form observation; compare attained gaps, full timing "
            "and shared-node qualifications before making performance claims.",
            **self.closed(),
        }

    def review_arm(self, claim, sha, mode):
        r.require(mode == "sto", "One STO arm only.")
        report = self.case_review(self.snapshot(claim), self.load(claim, sha))
        r.r2.write(claim / "control/sto/review.json", report)
        return report

    def review_process(self, claim, sha, mode, remaining):
        control = claim / "control" / mode
        with (control / "review.out").open("xb") as out, (control / "review.err").open("xb") as err:
            result = subprocess.run(
                self.invocation("review", claim, sha, "--mode", mode),
                stdout=out,
                stderr=err,
                timeout=remaining,
                check=False,
            )
        r.require(result.returncode == 0, "Original review failed; preserve diagnostics.")

    def batch(self, claim, sha):
        job_id = os.environ.get("SLURM_JOB_ID", "")
        result = {"status": "forensic_partial", "completed_modes": [], **self.closed()}
        try:
            r.require(job_id.isdigit(), "Compute allocation only.")
            plan = self.load(claim, sha)
            o.verify_tools(plan)
            job = o.job_receipt(claim, sha)
            r.require(job["job_id"] == job_id, "Job binding.")
            r.r2.write(claim / "batch_entry.json", job)
            query = r.r2.command(["scontrol", "-o", "show", "job", job_id], timeout=15)
            r.r2.write(
                claim / "allocation_query.json",
                {"returncode": query.returncode, "stdout": query.stdout, "stderr": query.stderr},
            )
            r.require(query.returncode == 0, "Allocation query failed.")
            allocated = o.allocation(query.stdout, job_id, os.getuid(), walltime="12:00:00")
            r.r2.write(claim / "allocation.json", allocated)
            control = claim / "control/sto"
            control.mkdir(parents=True, exist_ok=False)
            control.rmdir()

            def invoke(action, claim, sha, *extra):
                return [
                    "--chdir=" + str(claim / "control/sto"),
                    *self.invocation(action, claim, sha, *extra),
                ]

            observer = ExternalObserver(claim, job)
            try:
                outcome = o.supervise(
                    claim,
                    sha,
                    "sto",
                    allocated,
                    job,
                    invoke=invoke,
                    reviewer=self.review_process,
                    step_cpus=16,
                    bind_step=lambda *a: o.step_binding(*a, cpus=16),
                    whole_arm_seconds=35100,
                    phase_profile=self.PROFILE,
                    sleep=observer.sleep,
                )
            finally:
                observer.finish()
            r.require(
                outcome["status"] == "closed_feasible_arm", "Pyomo step not operationally closed."
            )
            self.load(claim, sha)
            result.update(
                status="one_pyomo_observation_returned",
                completed_modes=["sto"],
                source_verified_after=True,
            )
        except Exception as exc:
            result["error_kind"] = type(exc).__name__
        r.r2.write(claim / "batch_outcome.json", result)
        return int(result["status"] != "one_pyomo_observation_returned")

    def portable_review(self, files):
        plan = self.design(files)
        job = r.strict_json(files["job.json"])
        r.require(
            re.fullmatch("[1-9][0-9]*", job["job_id"])
            and job["source_commit"] == plan["source_commit"]
            and (job["plan_sha256"] == r.r2.digest(files["plan.json"])),
            "Original job/source/plan differs.",
        )
        rows = r.r2.accounting(files["accounting.txt"].decode(), job["job_id"])
        r.require(r.r2.terminal(rows, job["job_id"]), "Terminal accounting required.")
        assessment = {
            "classification": "build_or_execution_incomplete",
            "quality_target_met": False,
        }
        products = "cases/" + self.CASE + "/products/" + self.CASE + "/result.json"
        if products in files:
            try:
                assessment = self.case_review(files, plan)
            except (ValueError, KeyError, TypeError, IndexError) as exc:
                assessment["product_review_error_kind"] = type(exc).__name__
        else:
            assessment["product_status"] = "not_returned"
        operational, error = (False, None)
        try:
            query = r.strict_json(files["allocation_query.json"])
            allocated = r.strict_json(files["allocation.json"])
            owner = re.fullmatch("[^()]+\\(([0-9]+)\\)", o.fields(query["stdout"])["UserId"])
            r.require(query["returncode"] == 0 and owner, "Allocation owner/query.")
            r.require(
                o.allocation(query["stdout"], job["job_id"], int(owner[1]), walltime="12:00:00")
                == allocated,
                "Allocation replay.",
            )
            r.require(r.strict_json(files["batch_entry.json"]) == job, "Batch entry.")
            base = "control/sto/"
            entry = r.strict_json(files[base + "entry.json"])
            r.require(
                all((entry[k] == v for k, v in job.items()))
                and entry["mode"] == "sto"
                and (r.strict_json(files[base + "release.json"]) == entry),
                "Owned release.",
            )
            query = r.strict_json(files[base + "step_query.json"])
            r.require(query["returncode"] == 0, "Step query.")
            exact = o.step_binding(query["stdout"], entry, allocated, int(owner[1]), cpus=16)
            events = [
                r.strict_json(files[n]) for n in sorted(files) if n.startswith(base + "phase-")
            ]
            r.require(
                events
                and events[-1]["phase"] == "complete"
                and all(e["entry"] == entry for e in events),
                "Phase identity/closure.",
            )
            usage = o.phase_usage(events, events[-1]["elapsed_seconds"], profile=self.PROFILE)
            control = r.strict_json(files[base + "controller.json"])
            terminal = r.strict_json(files[base + "terminal_step.json"])
            r.require(
                terminal["row"] in r.r2.accounting(terminal["raw"], job["job_id"])
                and terminal["row"]["job_id"] == exact
                and (terminal["row"]["state"] == "COMPLETED")
                and (terminal["row"]["exit_code"] == "0:0"),
                "Owned-step terminal closure.",
            )
            r.require(
                control["status"] == "closed_feasible_arm"
                and control["local_client_reaped"]
                and (control["step_id"] == entry["step_id"])
                and (control["usage"] == usage)
                and (usage["stop_reason"] is None)
                and (control["product_review_seconds"] >= 0)
                and (
                    control["product_review_seconds"] + usage["seconds"]["independent_validation"]
                    <= 1800
                ),
                "Controller/phase budget.",
            )
            r.require(
                r.strict_json(files[base + "review.json"]) == assessment,
                "Post-worker review drift.",
            )
            runtime = r.strict_json(files[base + "runtime.json"])
            build = r.strict_json(files[base + "native_build.json"])
            r.require(
                build == runtime["native"]
                and build["pyomo"] == "6.10.1"
                and build["solver"] == self.solver
                and build["native_version"]
                == {"gurobi": "13.0.3", "scip": "10.0.2", "cbc": "2.10.13.0"}[self.solver]
                and build["population_optimized"] is False,
                "Native LP provenance.",
            )
            r.require(
                runtime["python"] == plan["environment"]["python"]
                and runtime["python_sha256"] == plan["python_sha256"]
                and (runtime["solver_threads"] == 4)
                and (
                    4
                    <= len(runtime["affinity_logical_cpus"])
                    == len(set(runtime["affinity_logical_cpus"]))
                    <= 24
                ),
                "Runtime/affinity.",
            )
            r.require(
                r.strict_json(files[base + "qualification.json"])
                == {"tests": 71, "failures": 0, "errors": 0, "skipped": 0, "status": "accepted"},
                "Fresh scalar math qualification.",
            )
            native = r.strict_json(files[base + "native_terminal.json"])
            r.require(
                native["entry"] == entry
                and native["parameter_evidence"] == assessment["parameter_evidence"]
                and (native["time_limit_seconds"] == 28800)
                and (native["reformulation"] == assessment["reformulation"])
                and native["common_linear_matrix"] == assessment["common_linear_matrix"]
                and native["native_counters"] == assessment["native_counters"]
                and (native["runtime_seconds"] is None or 0 <= native["runtime_seconds"] <= 29700),
                "Native budget/parameters.",
            )
            numerical = {
                x["job_id"]
                for x in rows
                if "." in x["job_id"] and x["job_id"].split(".")[-1].isdigit()
            }
            r.require(
                numerical == {exact}
                and {job["job_id"], job["job_id"] + ".batch", exact} <= {x["job_id"] for x in rows}
                and all(
                    x["state"] == "COMPLETED"
                    and x["exit_code"] == "0:0"
                    and (x["elapsed_seconds"] <= (35100 if x["job_id"] == exact else 43200))
                    for x in rows
                ),
                "Accounting closure.",
            )
            r.require(
                r.strict_json(files["batch_outcome.json"])["status"]
                == "one_pyomo_observation_returned",
                "Batch closure.",
            )
            operational = True
        except (ValueError, KeyError, TypeError, IndexError, StopIteration) as exc:
            error = type(exc).__name__
        try:
            startup_report = bootstrap.review(files, job)
        except (ValueError, KeyError, TypeError, IndexError, OSError) as exc:
            startup_report = {"status": "rejected", "error_kind": type(exc).__name__}
        if startup_report["status"] != "complete":
            operational = False
            error = "StartupIncomplete"
        return {
            **assessment,
            "solver": self.solver,
            "startup": startup_report,
            "external_observation": review_external(files, job),
            "status": "pyomo_quality_target_met"
            if operational and assessment["quality_target_met"]
            else "pyomo_returned_quality_not_met"
            if operational
            else "pyomo_forensic_partial_preserved",
            "operational_receipts_closed": operational,
            "operational_error_kind": error,
            "source_commit": plan["source_commit"],
            "job_id": job["job_id"],
            "accounting": rows,
            "production_isolation_certified": False,
            **self.closed(),
        }

    def collect(self, claim, sha, *, command=r.r2.command):
        self.load(claim, sha)
        marker = claim / "collection.json"
        if marker.exists():
            saved = r.r2.read(o.regular(marker))
            r.require(
                saved["archive"] == self.ARCHIVE
                and r.file_hash(o.regular(claim / self.ARCHIVE)) == saved["sha256"]
                and (
                    o.regular(Path(str(claim / self.ARCHIVE) + ".sha256")).read_text().strip()
                    == saved["sha256"] + "  " + self.ARCHIVE
                ),
                "Preserved transfer changed; never overwrite.",
            )
            return saved
        job = o.job_receipt(claim, sha)
        query = command(
            [
                "sacct",
                "-j",
                job["job_id"],
                "--noheader",
                "--parsable2",
                "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw,MaxRSS",
            ]
        )
        r.require(query.returncode == 0, "Accounting unavailable; preserve and collect later.")
        rows = r.r2.accounting(query.stdout, job["job_id"])
        wanted = {job["job_id"], job["job_id"] + ".batch"}
        for mode in MODES:
            path = claim / "control" / mode / "entry.json"
            if path.exists():
                entry = r.r2.read(o.regular(path))
                r.require(
                    entry["job_id"] == job["job_id"] and entry["step_id"].isdigit(),
                    "Step identity drift.",
                )
                wanted.add(job["job_id"] + "." + entry["step_id"])
        if not wanted <= {x["job_id"] for x in rows} or any(
            x["state"] not in r.r2.TERMINAL for x in rows
        ):
            return {"status": "nonterminal_or_accounting_pending", **self.closed()}
        terminal = claim / "terminal_accounting.json"
        if not terminal.exists():
            r.r2.write(terminal, {"raw": query.stdout, "rows": rows})
        files = self.snapshot(claim)
        files["accounting.txt"] = r.r2.read(terminal)["raw"].encode()
        report = self.portable_review(files)
        files["review.json"] = r.r2.encoded(report)
        files["inventory.json"] = r.r2.encoded({n: r.r2.digest(b) for n, b in files.items()})
        r.require(
            len(files) <= 4096 and sum(map(len, files.values())) <= 1024**3,
            "Transfer cap exceeded; no truncation.",
        )
        archive = claim / self.ARCHIVE
        with archive.open("xb") as stream, tarfile.open(fileobj=stream, mode="w:gz") as tar:
            for name, content in sorted(files.items()):
                member = tarfile.TarInfo(name)
                member.size, member.mode = (len(content), 384)
                tar.addfile(member, io.BytesIO(content))
        report.update(
            archive=self.ARCHIVE,
            sha256=r.file_hash(archive),
            download=str(archive),
            transfer_checksum=str(archive) + ".sha256",
        )
        with Path(str(archive) + ".sha256").open("x") as stream:
            stream.write(report["sha256"] + "  " + self.ARCHIVE + "\n")
        r.r2.write(marker, report)
        return report

    def audit(self, archive, checksum):
        from scripts.review_scalar_h300_evidence import read_archive

        files, _ = read_archive(archive, checksum)
        return self.portable_review(files)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "start",
            "batch",
            "worker",
            "review",
            "status",
            "wait",
            "collect",
            "audit",
            "budget",
        ),
    )
    parser.add_argument("--claim", type=Path)
    parser.add_argument("--source-sha")
    parser.add_argument("--mode", choices=MODES)
    parser.add_argument("--one-reviewed-pyomo-w", action="store_true")
    for name in (*INPUT_KEYS, "archive"):
        parser.add_argument("--" + name.replace("_", "-"), type=Path)
    parser.add_argument("--sha256")
    parser.add_argument("--solver", choices=SOLVERS, required=True)
    args = parser.parse_args(argv)
    campaign = Campaign(args.solver)
    if args.action == "budget":
        report = campaign.budget()
    elif args.action == "audit":
        report = campaign.audit(args.archive, args.sha256)
    else:
        r.require(
            args.claim is not None and args.source_sha is not None, "Claim/full source required."
        )
        claim = args.claim.absolute()
        if args.action == "start":
            report = campaign.start(
                claim,
                args.source_sha,
                args.one_reviewed_pyomo_w,
                {k: getattr(args, k) for k in INPUT_KEYS},
            )
        elif args.action == "batch":
            return campaign.batch(claim, args.source_sha)
        elif args.action == "worker":
            raise ValueError("Use the minimal -B -I -S bootstrap entry point.")
        elif args.action == "review":
            report = campaign.review_arm(claim, args.source_sha, args.mode)
        elif args.action == "status":
            campaign.load(claim, args.source_sha)
            job = o.job_receipt(claim, args.source_sha)
            query = r.r2.command(
                [
                    "sacct",
                    "-j",
                    job["job_id"],
                    "--noheader",
                    "--parsable2",
                    "--format=JobIDRaw,State%80,ExitCode,ElapsedRaw,MaxRSS",
                ]
            )
            report = {
                "status": "accounting_observed",
                "raw": query.stdout,
                "query_returncode": query.returncode,
                **job,
                **campaign.closed(),
            }
        else:
            while True:
                report = campaign.collect(claim, args.source_sha)
                if args.action != "wait" or report["status"] != "nonterminal_or_accounting_pending":
                    break
                print(
                    "NONTERMINAL; Ctrl-C safe; resume wait/collect, never reset a claim.",
                    flush=True,
                )
                time.sleep(20)
    print(json.dumps(report, sort_keys=True, allow_nan=False), flush=True)
    print("NO_W_REPEAT_ADDITIONAL_BLOCK_OR_AUTOMATIC_FOLLOW_ON_ADMITTED", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
