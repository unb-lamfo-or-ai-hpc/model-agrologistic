"""Closed native-worker integration. No CLI, admission, license probe or launcher.

Private seams are qualified with test doubles, not authorized production paths.
"""

from __future__ import annotations

from dataclasses import asdict

from scripts import mvp2_h300_controls as controls
from scripts import mvp2_h300_partial as partial
from scripts import mvp2_h300_thread_contract as design
from src.logic.model_config import SolverConfig


def solver_profile(threads):
    """One global native window; no caller-supplied override dictionary."""
    profile = design.arm_profile(threads)["solver"]
    return SolverConfig(
        backend="gurobipy",
        solver_name="gurobi",
        threads=threads,
        seed=profile["seed"],
        time_limit=profile["time_limit"],
        mip_gap=profile["mip_gap"],
        compact_python_indices=False,
        compute_iis=False,
        solver_options={"SoftMemLimit": 128, "NumericFocus": 1},
        multiobjective_stage_options=profile["multiobjective_stage_options"],
    )


def execute_native_worker(*_args, **_kwargs):
    """Unconditional deny BEFORE native import, input loading or file creation."""
    raise PermissionError("Native worker qualification is not execution admission.")


class NativeHooks:
    """Synchronous solve-thread seams, separate from detailed telemetry phases."""

    def __init__(self, journal, solver):
        self.journal = journal
        self.solver = solver
        self.ready = False
        self.terminal = None

    def __call__(self, phase, model, grb):
        if phase == "native_ready":
            design.require(not self.ready and self.journal.index == 1, "Repeated readiness.")
            expected = {
                "TimeLimit": 1800,
                "Threads": self.solver.threads,
                "Seed": 42,
                "MIPGap": 0.1,
                "SoftMemLimit": 128,
                "NumericFocus": 1,
            }
            for name, value in expected.items():
                observed = getattr(model.Params, name)
                design.require(
                    type(observed) in (int, float) and observed == value,
                    f"Effective native parameter drift: {name}.",
                )
            self.ready = True
        elif phase == "optimization":
            design.require(self.ready, "No effective native parameter check.")
            self.journal.enter(phase)
        elif phase == "export_validation":
            self.journal.enter(phase)
            # Mandatory status/count are captured while the native model is alive,
            # before extraction. Missing optional observations stay null, not zero.
            count, status = model.SolCount, model.Status
            design.require(type(count) is int and count >= 0, "Invalid native SolCount.")
            design.require(type(status) is int, "Invalid native status code.")
            optional = {}
            for name in ("Runtime", "MaxMemUsed"):
                try:
                    optional[name] = design.number(getattr(model, name), name, nullable=True)
                except Exception:
                    optional[name] = None
            self.terminal = {
                "identity": self.journal.identity,
                "native_status_code": status,
                "native_status_name": self.status_name(model, grb),
                "solution_count": count,
                "native_runtime_seconds": optional["Runtime"],
                "native_peak_decimal_gb": optional["MaxMemUsed"],
                "production_admitted": False,
                "repeats_admitted": False,
            }
            controls.write_once(self.journal.directory / "native-terminal.json", self.terminal)
        else:
            raise ValueError("Unknown native seam.")

    @staticmethod
    def status_name(model, grb):
        from src.logic.optimization_gurobipy import _gurobi_status_name

        return _gurobi_status_name(model, grb)


def _integrate_native(directory, data, config, expected_anchor, *, solver=None):
    """Private integration seam; NOT an admitted worker or production entry point.

    The only public execution function denies. Tests replace the backend before
    calling this seam; a future admission PR must supply authenticated containment,
    fresh license/cohort/runtime checks and real resource sampling.
    """
    threads = expected_anchor["threads"]
    frozen = solver_profile(threads)
    solver = frozen if solver is None else solver
    design.require(
        design.digest(asdict(solver)) == design.digest(asdict(frozen)),
        "Unqualified solver profile.",
    )
    design.require(
        config.mode == "sto"
        and config.objective_policy == "lexicographic"
        and config.use_direct_origin_customer is False,
        "Unqualified model mode/direct arcs.",
    )
    recomputed = partial.anchor(
        data,
        config,
        source_commit=expected_anchor["source_commit"],
        runtime_sha256=expected_anchor["runtime_sha256"],
        workbook_sha256=expected_anchor["workbook_sha256"],
        threads=threads,
    )
    design.require(recomputed == expected_anchor, "External scientific anchor drift.")
    journal = controls.PhaseJournal(directory, design.digest(expected_anchor))
    hooks = NativeHooks(journal, solver)
    cleanup_started = False
    failure = None

    def begin_cleanup():
        nonlocal cleanup_started
        if cleanup_started:
            return
        if journal.index == 3:
            journal.enter("cleanup")
        elif journal.index < 3:
            journal.failure_cleanup()
        cleanup_started = True

    try:
        journal.enter("build")
        from src.logic.optimization_gurobipy_stochastic import solve_stochastic_model_gurobipy

        result = solve_stochastic_model_gurobipy(
            data,
            config,
            solver,
            native_phase_hook=hooks,
            _on_failure_cleanup=begin_cleanup,
        )
        design.require(journal.index == 3 and hooks.terminal is not None, "Missing native seams.")
        design.require(
            type(result.metadata.get("solution_count")) is int
            and type(result.metadata.get("gurobi_status_code")) is int
            and result.metadata.get("solution_count") == hooks.terminal["solution_count"]
            and result.metadata.get("gurobi_status_code") == hooks.terminal["native_status_code"],
            "Result drift from live native terminal snapshot.",
        )
        design.require(
            result.metadata.get("gurobi_status_name") == hooks.terminal["native_status_name"],
            "Symbolic status drift from live native code.",
        )
        lifecycle = result.metadata.get("native_model_lifecycle")
        design.require(
            isinstance(lifecycle, list)
            and len(lifecycle) == 1
            and lifecycle[0]["backend"] == "gurobipy"
            and lifecycle[0]["status"] == "disposed",
            "Native ownership/disposal not established.",
        )
        # Native disposal already occurred inside the managed backend. Validation
        # uses sparse values only, never live handles. Parent closure remains separate.
        return partial.export_partial(
            journal.directory / "products",
            result,
            data,
            config,
            expected_anchor,
        )
    except BaseException as error:
        failure = error
        try:
            controls.write_once(
                journal.directory / "failure.json",
                {
                    "identity": journal.identity,
                    "exception_type": type(error).__name__,
                    "after_phase_count": journal.index,
                    "native_terminal_captured": hooks.terminal is not None,
                    "production_admitted": False,
                    "repeats_admitted": False,
                },
            )
        except BaseException as secondary:
            error.add_note(f"Failure receipt publication failed: {type(secondary).__name__}")
        raise
    finally:
        try:
            begin_cleanup()
        except BaseException as secondary:
            if failure is None:
                raise
            failure.add_note(f"Cleanup receipt publication failed: {type(secondary).__name__}")
