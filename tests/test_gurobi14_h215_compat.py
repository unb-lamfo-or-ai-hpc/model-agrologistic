"""No solver, license, private data or scheduler is used by these controls."""

import importlib.util
import tarfile
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "g14_compat", ROOT / "scripts/gurobi14_h215_compat.py"
)
c = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(c)

DEFAULTS = {
    "TimeLimit": 1e100,
    "Method": -1,
    "Threads": 0,
    "MIPGap": 1e-4,
    "Seed": 0,
    "ConcurrentMIP": 1,
    "Heuristics": 0.05,
    "Presolve": -1,
    "FeasibilityTol": 1e-6,
    "IntFeasTol": 1e-5,
    "SoftMemLimit": 1e100,
    "PDHGGPU": -1,
    "OutputFlag": 1,
    "LogFile": "",
    "ThreadLimit": 0,
}


class FakeModel:
    """A parameter/event double; it contains no mathematical model or optimizer."""

    def __init__(self):
        self.values = dict(DEFAULTS)
        self.set_calls = []
        self.SolCount = 0
        self.Status = 9
        self.Runtime = 300
        self.Work = 20
        self.NodeCount = 0
        self.ObjBound = 1000
        self.MemUsed = 2
        self.MaxMemUsed = 3

    def getParamInfo(self, name):
        value = self.values[name]
        return (name, type(value), value, 0, 1e100, DEFAULTS[name])

    def setParam(self, name, value):
        self.set_calls.append((name, value))
        self.values[name] = value


class ParameterControls(unittest.TestCase):
    def test_only_time_limit_is_set_and_seams_are_restored(self):
        model, events, constructed = FakeModel(), [], []

        def original_optimize(native, grb, *, native_phase_hook):
            for phase in ("native_ready", "optimization", "export_validation"):
                native_phase_hook(phase, native, grb)
            return {"observational_double": True}

        core = types.SimpleNamespace(
            _import_gurobi=object(),
            _apply_solver_parameters=object(),
            _optimize_scalar=original_optimize,
        )
        original = vars(core).copy()
        parameter_type = type("Params", (), {name: name for name in DEFAULTS})
        grb = types.SimpleNamespace(Param=parameter_type)

        def factory(*args, **kwargs):
            constructed.append((args, kwargs))
            return model

        gp = types.SimpleNamespace(GRB=grb, Model=factory)
        state = {"models": 0, "optimization_attempts": 0}
        environment = object()
        with c.native_binding(
            core, gp, environment, state, lambda n, v: events.append((n, v))
        ):
            proxy, native_grb = core._import_gurobi()
            native = proxy.Model("retained-native-constructor")
            config = types.SimpleNamespace(mip_gap=0.01)
            core._apply_solver_parameters(native, config)
            core._optimize_scalar(native, native_grb)
            self.assertEqual(config.mip_gap, 1e-4)
            self.assertEqual(model.set_calls, [("TimeLimit", 300)])
            self.assertEqual(constructed[0][1], {"env": environment})
            self.assertIsNone(state["native"]["incumbent"])
            self.assertIsNone(state["native"]["mip_gap"])
            self.assertTrue(state["optimization_returned"])
            with self.assertRaises(c.CompatibilityError):
                proxy.Model("forbidden-second-model")
        self.assertEqual(vars(core), original)
        self.assertEqual(len(events), 3)

    def test_extra_thread_or_heuristic_override_is_rejected(self):
        for name, value in (("Threads", 4), ("Heuristics", 0.5), ("ThreadLimit", 16)):
            model = FakeModel()
            model.setParam("TimeLimit", 300)
            model.values[name] = value
            with self.subTest(name=name), self.assertRaises(c.CompatibilityError):
                c.audit_defaults(model, DEFAULTS)

    def test_authentication_values_are_not_queried_or_exported(self):
        model = FakeModel()
        model.setParam("TimeLimit", 300)
        answer = c.audit_defaults(
            model, [*DEFAULTS, "WLSSecret", "WLSAccessID", "LicenseID"]
        )
        self.assertEqual(answer["nondefault_parameters"], ["TimeLimit"])
        self.assertNotIn("WLSSecret", str(answer))
        self.assertNotIn("LicenseID", str(answer))

    def test_scoped_seams_restore_on_exception(self):
        core = types.SimpleNamespace(
            _import_gurobi=object(),
            _apply_solver_parameters=object(),
            _optimize_scalar=object(),
        )
        original = vars(core).copy()
        gp = types.SimpleNamespace(GRB=types.SimpleNamespace(Param=object()))
        with (
            self.assertRaises(RuntimeError),
            c.native_binding(core, gp, object(), {}, lambda *_: None),
        ):
            raise RuntimeError("test-only failure")
        self.assertEqual(vars(core), original)


class VerdictAndAdmission(unittest.TestCase):
    def state(self):
        return {
            "license": {"status": "accepted_designated_wls"},
            "models": 1,
            "optimization_attempts": 1,
            "model_built": True,
            "optimization_returned": True,
            "native": {"status_code": 9, "runtime_seconds": 300, "solution_count": 0},
        }

    def test_timeout_without_incumbent_is_compatible(self):
        self.assertEqual(c.verdict(self.state()), "GO")

    def test_incumbent_requires_independent_validation(self):
        state = self.state()
        state["native"]["solution_count"] = 1
        self.assertEqual(c.verdict(state), "NO-GO")
        state["validation_status"] = "accepted"
        self.assertEqual(c.verdict(state), "GO")

    def test_missing_optimization_return_is_inconclusive(self):
        state = self.state()
        state["optimization_returned"] = False
        self.assertEqual(c.verdict(state), "INCONCLUSIVE")

    def test_critical_error_or_unexpected_infeasibility_is_not_go(self):
        state = self.state()
        state["native"]["status_code"] = 3
        self.assertEqual(c.verdict(state), "NO-GO")
        state["error"] = {"kind": "GurobiError", "native_or_os_error_code": 10009}
        self.assertEqual(c.verdict(state), "NO-GO")

    def test_login_run_is_refused_before_importing_gurobi(self):
        with (
            patch.dict(c.os.environ, {}, clear=True),
            self.assertRaises(c.CompatibilityError),
        ):
            c.run("f" * 40)

    def test_one_cpu_job_envelope_and_no_hidden_solver_options(self):
        batch = c.batch_text(Path("/audit/new-claim"), "f" * 40)
        self.assertEqual(batch.count("\nsrun "), 1)
        self.assertIn("--time=01:00:00", batch)
        self.assertIn("--mem=196608M", batch)
        self.assertIn("--exclusive", batch)
        self.assertIn("--no-requeue", batch)
        self.assertNotIn("sbatch", batch)
        self.assertNotIn("--array", batch)
        self.assertNotIn("MIPGap", batch)
        self.assertNotIn("SoftMemLimit", batch)


class SourceIntegrity(unittest.TestCase):
    def test_regular_source_identity_and_symbolic_link_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            file = root / "scripts/gurobi14_h215_compat.py"
            file.write_bytes(b"# retained source\n")
            sha = "a" * 40
            archive = root / "source.tar.gz"
            with tarfile.open(archive, "w:gz") as stream:
                stream.add(
                    file, arcname=f"model-agrologistic-{sha}/scripts/{file.name}"
                )
            with patch.object(c, "ROOT", root):
                inventory = c.source_inventory(archive, sha, c.digest(archive))
                self.assertEqual(inventory, {"scripts/" + file.name: c.digest(file)})
            with tarfile.open(archive, "w:gz") as stream:
                member = tarfile.TarInfo(f"model-agrologistic-{sha}/link")
                member.type = tarfile.SYMTYPE
                member.linkname = "/outside/source"
                stream.addfile(member)
            with patch.object(c, "ROOT", root), self.assertRaises(c.CompatibilityError):
                c.source_inventory(archive, sha, c.digest(archive))


if __name__ == "__main__":
    unittest.main()
