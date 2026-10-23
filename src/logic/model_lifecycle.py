"""Exception-safe ownership of native models without retaining solution handles."""

from contextvars import ContextVar
from functools import wraps
from time import perf_counter

from src.logic.resource_telemetry import event, phase

OWNED = ContextVar("agrologistic_owned_models", default=None)


def own_model(model, backend):
    owners = OWNED.get()
    if owners is None:
        raise RuntimeError("Native models must be created within managed_model_solve.")
    owners.append((model, backend))
    phase("model_build")
    return model


def managed_model_solve(function):
    """Dispose after value extraction, including no-incumbent and exception paths.

    Disposing is not a claim that a native allocator returns all memory to the OS.
    The default Gurobi environment remains shared and is never disposed here.
    """

    @wraps(function)
    def wrapped(*args, **kwargs):
        # Private worker seam: publication errors cannot prevent native disposal.
        on_failure_cleanup = kwargs.pop("_on_failure_cleanup", None)
        owners, records = [], []
        token = OWNED.set(owners)
        result, failure = None, None
        try:
            result = function(*args, **kwargs)
            return result
        except BaseException as exc:
            failure = exc
            raise
        finally:
            cleanup_errors = []
            cleanup_interrupts = []
            observation_errors = []
            try:
                if failure is not None and on_failure_cleanup is not None:
                    try:
                        on_failure_cleanup()
                    except BaseException as exc:
                        observation_errors.append(exc)
                try:
                    phase("native_model_disposal")
                except BaseException as exc:
                    observation_errors.append(exc)
                for model, backend in reversed(owners):
                    started = perf_counter()
                    try:
                        if backend == "gurobipy":
                            model.dispose()
                        else:
                            model.freeProb()
                        status = "disposed"
                    except BaseException as exc:
                        status = type(exc).__name__
                        cleanup_errors.append(status)
                        if not isinstance(exc, Exception):
                            cleanup_interrupts.append(exc)
                    records.append(
                        {
                            "backend": backend,
                            "status": status,
                            "disposal_seconds": perf_counter() - started,
                        }
                    )
                    try:
                        event("model_disposal", status=status)
                    except BaseException as exc:
                        observation_errors.append(exc)
            finally:
                OWNED.reset(token)
            if result is not None:
                result.metadata["native_model_lifecycle"] = records
            if cleanup_interrupts and failure is None:
                raise cleanup_interrupts[0]
            if cleanup_errors and failure is None:
                raise RuntimeError(f"Native model disposal failed: {cleanup_errors}")
            if observation_errors and failure is None:
                raise observation_errors[0]
            if failure is not None:
                for status in cleanup_errors:
                    failure.add_note(f"Secondary native disposal error: {status}")
                for error in observation_errors:
                    failure.add_note(f"Secondary cleanup observation error: {type(error).__name__}")

    return wrapped
