"""Execution barriers for the explicit data/algebra CI test inventory."""

from __future__ import annotations

import importlib.abc
import sys

NATIVE_MODULES = {"gurobipy", "highspy", "pyscipopt", "cplex", "xpress", "mosek", "swiglpk", "cylp"}


class NoSolverViolation(RuntimeError):
    pass


class NativeSolverUnavailable(ModuleNotFoundError):
    """Optional dependency probes may catch this; no native module is loaded."""


class NoSolverGuard(importlib.abc.MetaPathFinder):
    def __init__(self):
        self.blocked = 0
        self.import_blocks = 0
        self.execution_blocks = 0

    def reject(self, message):
        self.blocked += 1
        self.execution_blocks += 1
        raise NoSolverViolation(message)

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in NATIVE_MODULES:
            self.blocked += 1
            self.import_blocks += 1
            raise NativeSolverUnavailable("Native solver import blocked in data/algebra CI.")
        return None

    def audit(self, event, args):
        if event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.exec", "os.spawn"}:
            self.reject("Child-process execution forbidden during data/algebra tests.")

    def profile(self, frame, event, arg):
        if event != "call":
            return
        module = frame.f_globals.get("__name__") or ""
        name = frame.f_code.co_name
        if (
            module.startswith("src.logic.") and (
                name.startswith(("solve_model", "solve_effective_", "solve_stochastic_model"))
                or name == "_optimize_scalar"
            )
        ) or (module.startswith("pyomo.") and name in {"solve", "_solve", "optimize"}):
            self.reject("Optimizer entry point forbidden in data/algebra CI.")

    def install(self):
        if any(m.split(".")[0] in NATIVE_MODULES for m in sys.modules):
            raise NoSolverViolation("Install the guard before importing native solvers.")
        sys.meta_path.insert(0, self)
        sys.addaudithook(self.audit)
        sys.setprofile(self.profile)
