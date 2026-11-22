"""No solver, license, private data or scheduler is used by these controls."""

import ast
import importlib.util
import json
import math
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
    "TimeLimit": math.inf,
    "Method": -1,
    "Threads": 0,
    "MIPGap": 1e-4,
    "Seed": 0,
    "ConcurrentMIP": 1,
    "Heuristics": 0.05,
    "Presolve": -1,
    "FeasibilityTol": 1e-6,
    "IntFeasTol": 1e-5,
    "SoftMemLimit": math.inf,
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


class ReceiptEncoding(unittest.TestCase):
    def test_historical_collection_helper_parses_without_scientific_imports(self):
        text = (ROOT / "scripts/collect_gurobi14_2278573.sh").read_text()
        body = text.split("<<'PY'\n", 1)[1].rsplit("\nPY\n", 1)[0]
        tree = ast.parse(body)
        modules = {
            alias.name.split(".")[0]
            for node in ast.walk(tree) if isinstance(node, ast.Import)
            for alias in node.names
        }
        self.assertTrue(modules.isdisjoint({"gurobipy", "torch", "pyomo", "highspy"}))
        for forbidden in ("sbatch", "scontrol release", "scancel", "pip install"):
            self.assertNotIn(forbidden, text)

    def test_default_infinite_memory_is_metadata_and_does_not_set_a_limit(self):
        model = FakeModel()
        model.setParam("TimeLimit", 300)
        audit = c.audit_defaults(model, DEFAULTS)
        self.assertEqual(audit["parameters"]["SoftMemLimit"], "Infinity")
        self.assertTrue(math.isinf(model.values["SoftMemLimit"]))
        self.assertEqual(model.set_calls, [("TimeLimit", 300)])
        self.assertEqual(json.loads(c.encoded(audit)), audit)

    def test_special_parameter_values_retain_their_meaning(self):
        for native, expected in ((math.inf, "Infinity"), (-math.inf, "-Infinity"),
                                 (math.nan, "NaN"), (1e100, 1e100), (-1, -1), ("", "")):
            with self.subTest(expected=expected):
                self.assertEqual(c.parameter_record(native), expected)

    def test_failed_encoding_does_not_leave_an_empty_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            with self.assertRaises(ValueError):
                c.publish(path, {"unexpected_nonfinite_statistic": math.inf})
            self.assertFalse(path.exists())

    def test_publishing_cannot_overwrite_an_original_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            original = b"original incomplete evidence"
            path.write_bytes(original)
            with self.assertRaises(FileExistsError):
                c.publish(path, {"replacement": "forbidden"})
            self.assertEqual(path.read_bytes(), original)

    def test_collection_distinguishes_missing_empty_invalid_and_nonobject_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            self.assertEqual(c.json_receipt_status(path)["status"], "absent_or_linked")
            for raw, expected in ((b"", "empty"), (b"{", "invalid_json"),
                                  (b'{"gap":Infinity}', "invalid_json"),
                                  (b'{"gap":NaN}', "invalid_json"),
                                  (b"\xff", "invalid_json"), (b"null", "nonobject_json"),
                                  (b"{}", "valid_json_object")):
                path.write_bytes(raw)
                answer = c.json_receipt_status(path)
                self.assertEqual(answer["status"], expected)
                self.assertEqual(answer["bytes"], len(raw))
                self.assertEqual(path.read_bytes(), raw)

    def test_real_receipt_encoding_follows_all_three_fake_native_phases(self):
        model = FakeModel()

        def original_optimize(native, grb, *, native_phase_hook):
            for phase in ("native_ready", "optimization", "export_validation"):
                native_phase_hook(phase, native, grb)

        core = types.SimpleNamespace(_import_gurobi=None, _apply_solver_parameters=None,
                                     _optimize_scalar=original_optimize)
        parameter_type = type("Params", (), {name: name for name in DEFAULTS})
        gp = types.SimpleNamespace(GRB=types.SimpleNamespace(Param=parameter_type),
                                   Model=lambda *args, **kwargs: model)
        state = {"models": 0, "optimization_attempts": 0}
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with c.native_binding(core, gp, object(), state,
                                  lambda name, value: c.publish(folder / name, value)):
                proxy, grb = core._import_gurobi()
                native = proxy.Model("public-api-double")
                core._apply_solver_parameters(native, types.SimpleNamespace(mip_gap=None))
                core._optimize_scalar(native, grb)
            self.assertEqual(len(list(folder.glob("*.json"))), 3)
            self.assertTrue(state["optimization_returned"])
            self.assertEqual(state["optimization_attempts"], 1)
            self.assertEqual(json.loads((folder / "native-ready.json").read_bytes())[
                "parameter_audit"]["parameters"]["SoftMemLimit"], "Infinity")
            self.assertEqual(model.set_calls, [("TimeLimit", 300)])


    def test_terminal_failed_collection_keeps_invalid_originals_and_never_accepts_them(self):
        for content, expected in ((None, "absent_or_linked"), (b"", "empty"),
                                  (b"{", "invalid_json"), (b"{}", "valid_json_object")):
            with self.subTest(status=expected), tempfile.TemporaryDirectory() as directory:
                base = Path(directory)
                claim = base / "original-claim"
                claim.mkdir()
                (claim / "job-id.txt").write_text("2278573")
                (claim / "native-ready.json").write_bytes(b"")
                if content is not None:
                    (claim / "result.json").write_bytes(content)
                accounting = types.SimpleNamespace(
                    stdout="JobIDRaw|State|ElapsedRaw\n2278573|FAILED|78\n"
                )
                with (
                    patch.dict(c.os.environ, {}, clear=True),
                    patch.object(c, "BASE", base), patch.object(c, "CLAIM", claim),
                    patch.object(c, "load_plan", return_value={}),
                    patch.object(c.subprocess, "run", return_value=accounting) as command,
                ):
                    report = c.collect("f" * 40)
                command.assert_called_once()
                self.assertEqual(command.call_args.args[0][0], "sacct")
                self.assertEqual(report["native_result_present"], content is not None)
                self.assertEqual(report["native_result_json_status"]["status"], expected)
                target = Path(report["transfer_dir"])
                review = json.loads((target / "collection-review.json").read_bytes())
                self.assertEqual(review["compatibility_verdict"], "pending_original_receipt_review")
                self.assertIsNone(review["receipt_hashes_verified"])
                self.assertEqual(review["json_receipts"]["native-ready.json"]["status"], "empty")
                self.assertFalse((claim / "SHA256SUMS").exists())
                if content is not None:
                    self.assertEqual((claim / "result.json").read_bytes(), content)
                    self.assertEqual((target / "result.json").read_bytes(), content)
                self.assertTrue((target / "TRANSFER_SHA256SUMS").is_file())


if __name__ == "__main__":
    unittest.main()
