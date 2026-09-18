"""Runtime inventory must never claim solver/model qualification."""

from importlib.metadata import PackageNotFoundError
from types import SimpleNamespace

import pytest

from scripts.probe_scip_runtime import inspect_runtime


class RuntimeModel:
    freed = False

    def getMajorVersion(self):
        return 10

    def getMinorVersion(self):
        return 0

    def getTechVersion(self):
        return 1

    def getParams(self):
        return {"limits/gap": 0.0, "limits/time": 1e20}

    def freeProb(self):
        self.freed = True

    def optimize(self):
        raise AssertionError("A runtime inventory must never optimize.")


def test_available_runtime_does_not_qualify_backend():
    model = RuntimeModel()
    report = inspect_runtime(
        import_module=lambda _: SimpleNamespace(Model=lambda _: model),
        package_version=lambda _: "6.2.0",
    )
    assert report["status"] == "runtime_available"
    assert report["scip_version"] == "10.0.1"
    assert report["pyscipopt_version"] == "6.2.0"
    assert report["missing_parameters"]
    assert report["observed_parameter_defaults"]["lp/threads"] is None
    assert report["optimization_executed"] is False
    assert report["large_instance_submission_allowed"] is False
    assert report["agrologistic_backend_status"] == "not_implemented"
    assert report["lp_backend"] is None
    assert model.freed


@pytest.mark.parametrize(
    "error,status",
    [
        (ModuleNotFoundError(name="pyscipopt"), "not_installed"),
        (ModuleNotFoundError(name="dependency"), "import_failed"),
        (OSError("private path must not be exported"), "runtime_probe_failed"),
    ],
)
def test_missing_or_broken_runtime(error, status):
    def fail_import(_):
        raise error

    def missing_package(_):
        raise PackageNotFoundError("pyscipopt")

    report = inspect_runtime(import_module=fail_import, package_version=missing_package)
    assert report["status"] == status
    assert report["pyscipopt_version"] is None
    assert "private path" not in str(report)
    assert report["large_instance_submission_allowed"] is False


def test_failed_version_query_releases_model():
    class Broken(RuntimeModel):
        def getMinorVersion(self):
            raise RuntimeError("unexpected API")

    model = Broken()
    report = inspect_runtime(
        import_module=lambda _: SimpleNamespace(Model=lambda _: model),
        package_version=lambda _: "6.2.0",
    )
    assert report["status"] == "runtime_probe_failed"
    assert model.freed


def test_cleanup_failure_is_not_reported_as_ready():
    class Broken(RuntimeModel):
        def freeProb(self):
            raise RuntimeError("cleanup")

    report = inspect_runtime(
        import_module=lambda _: SimpleNamespace(Model=lambda _: Broken()),
        package_version=lambda _: "6.2.0",
    )
    assert report["status"] == "runtime_probe_failed"
    assert report["cleanup_error_type"] == "RuntimeError"
