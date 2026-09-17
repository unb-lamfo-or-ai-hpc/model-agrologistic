"""Opt-in, bounded observations of the existing extensive-form solve.

No presolved model copy is constructed. Matrix observations are read from
Gurobi's own MESSAGE stream; missing log observations remain missing. Memory
is Gurobi environment allocation in decimal GB, not operating-system RSS.
"""

from __future__ import annotations

import math
import re
from time import perf_counter

ROLES = ("unmet_demand", "emergency_capacity", "economic_cost")
ALLOWED = {"Method": {0, 2}, "PreSparsify": {0, 1, 2}}
MATRIX = re.compile(r"Presolved:\s*([\d,]+) rows,\s*([\d,]+) columns,\s*([\d,]+) nonzeros")
PHASE = re.compile(r"Multi-objectives: optimize objective (\d+)\b")


def validate_stage_options(options):
    """Reject tolerance, budget, priority, service-pass and dual-only overrides."""
    if not isinstance(options, dict):
        raise ValueError("multiobjective_stage_options must be a mapping.")
    for role, settings in options.items():
        if role not in ROLES[1:] or not isinstance(settings, dict) or not settings:
            raise ValueError("Only capacity/economic stage option mappings are supported.")
        for name, value in settings.items():
            if name not in ALLOWED or type(value) is not int or value not in ALLOWED[name]:
                raise ValueError(f"Unsupported stage parameter: {name}={value!r}.")


def configure_stages(model, options, roles):
    """Create per-pass environments only after global parameters are applied."""
    validate_stage_options(options)
    if tuple(roles) != ROLES:
        raise ValueError("Stage overrides require the three ordered policy priorities.")
    for role, settings in options.items():
        environment = model.getMultiobjEnv(ROLES.index(role))
        for name, value in settings.items():
            environment.setParam(name, value)


def finite(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) and abs(value) < 1e99 else None


class SolverDiagnostics:
    """Sample at most once per 30 wall seconds, plus stage termination events."""

    def __init__(self, model, callback, options, clock=perf_counter):
        self.callback = callback
        self.clock = clock
        self.last_sample = -math.inf
        self.stage = None
        self.progress = []
        self.matrices = []
        self.events = []
        self.dropped = 0
        self.errors = set()
        self.started = clock()
        model.update()
        self.original = {
            name: finite(getattr(model, attribute, None))
            for name, attribute in (
                ("rows", "NumConstrs"),
                ("columns", "NumVars"),
                ("nonzeros", "DNumNZs"),
                ("general_constraints", "NumGenConstrs"),
            )
        }
        self.settings = {}
        for role in ROLES:
            self.settings[role] = {}
            for name in (
                "Method",
                "PreSparsify",
                "Threads",
                "TimeLimit",
                "MIPGap",
                "MIPGapAbs",
                "SoftMemLimit",
                "NumericFocus",
            ):
                self.settings[role][name] = options.get(role, {}).get(
                    name, model.getParamInfo(name)[2]
                )

    def query(self, model, name):
        code = getattr(self.callback, name, None)
        if code is None:
            self.errors.add(name)
            return None
        try:
            return finite(model.cbGet(code))
        except Exception:  # noqa: BLE001
            self.errors.add(name)
            return None

    def context(self):
        return {
            "stage_number": self.stage,
            "stage_role": ROLES[self.stage - 1] if self.stage in (1, 2, 3) else None,
        }

    def message(self, text):
        for line in text.splitlines():
            phase = PHASE.search(line)
            if phase:
                self.stage = int(phase[1])
            matrix = MATRIX.search(line)
            if matrix and len(self.matrices) < 100:
                self.matrices.append(
                    {
                        **self.context(),
                        "scope": "objective_pass" if self.stage else "global_presolve",
                        "rows": int(matrix[1].replace(",", "")),
                        "columns": int(matrix[2].replace(",", "")),
                        "nonzeros": int(matrix[3].replace(",", "")),
                        "source": "gurobi_message",
                        "log_line": line.strip(),
                    }
                )
            if any(
                word in line
                for word in (
                    "Factor NZ",
                    "AA' NZ",
                    "Root relaxation:",
                    "Memory limit reached",
                    "Barrier statistics:",
                    "Concurrent LP",
                    "concurrent LP",
                )
            ):
                if len(self.events) < 300:
                    self.events.append({**self.context(), "log_line": line.strip()})

    def observe(self, model, where):
        # Telemetry must never interrupt the independent terminal-stage observer.
        try:
            self._observe(model, where)
        except Exception as exc:  # noqa: BLE001
            self.errors.add(f"observer:{type(exc).__name__}")

    def _observe(self, model, where):
        cb = self.callback
        if where == getattr(cb, "MESSAGE", None):
            self.message(model.cbGet(cb.MSG_STRING))
            return
        end = where == cb.MULTIOBJ
        if end:
            self.stage = int(model.cbGet(cb.MULTIOBJ_OBJCNT))
        supported = {
            getattr(cb, name, None)
            for name in ("MIP", "SIMPLEX", "BARRIER", "PRESOLVE", "MULTIOBJ")
        }
        if where not in supported:
            return
        now = self.clock()
        if not end and now - self.last_sample < 30:
            return
        if len(self.progress) >= 10000:
            self.dropped += 1
            return
        self.last_sample = now
        event = next(
            name
            for name in ("MIP", "SIMPLEX", "BARRIER", "PRESOLVE", "MULTIOBJ")
            if getattr(cb, name, None) == where
        )
        row = {
            **self.context(),
            "event": event,
            "observed_wall_seconds": now - self.started,
            "solver_runtime_seconds": self.query(model, "RUNTIME"),
            "solver_memory_decimal_gb": self.query(model, "MEMUSED"),
            "solver_peak_memory_decimal_gb": self.query(model, "MAXMEMUSED"),
        }
        if event in {"MIP", "MULTIOBJ"}:
            for field, suffix in (
                ("incumbent", "OBJBST"),
                ("bound", "OBJBND"),
                ("nodes", "NODCNT"),
                ("iterations", "ITRCNT"),
            ):
                row[field] = self.query(model, f"{event}_{suffix}")
            incumbent, bound = row["incumbent"], row["bound"]
            row["relative_gap"] = (
                abs(incumbent - bound) / abs(incumbent)
                if incumbent not in (None, 0.0) and bound is not None
                else None
            )
            if end:
                row["stage_runtime_seconds"] = self.query(model, "MULTIOBJ_RUNTIME")
                row["stage_status_code"] = self.query(model, "MULTIOBJ_STATUS")
            else:
                row["cut_count"] = self.query(model, "MIP_CUTCNT")
        elif event in {"SIMPLEX", "BARRIER"}:
            prefix = "SPX" if event == "SIMPLEX" else "BARRIER"
            row["iterations"] = self.query(model, f"{prefix}_ITRCNT")
            # LP iterates are deliberately not labelled valid MIP bounds.
        self.progress.append(row)

    def finish(self, model):
        return {
            "schema_version": "stagewise-solver-diagnostics-v1",
            "status": "recorded_with_missing_fields" if self.errors else "recorded",
            "original_matrix": self.original,
            "effective_stage_parameters": self.settings,
            "matrix_observations": self.matrices,
            "matrix_observation_status": "observed" if self.matrices else "not_observed",
            "progress": self.progress,
            "root_events": self.events,
            "unavailable_callback_fields": sorted(self.errors),
            "dropped_progress_samples": self.dropped,
            "sampling_interval_seconds": 30,
            "memory_scope": "Gurobi allocation; decimal GB; not process RSS",
            "final_solver_memory_decimal_gb": finite(getattr(model, "MemUsed", None)),
            "final_solver_peak_memory_decimal_gb": finite(getattr(model, "MaxMemUsed", None)),
            "matrix_qualification": "Observed log matrices only; no explicit presolve copy.",
        }
