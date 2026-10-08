"""Native integration software qualification only: no licensed solver calls."""

from types import SimpleNamespace

import pytest

from scripts import mvp2_h300_native_worker as worker
from src.logic import model_lifecycle as ownership
from src.logic import optimization_gurobipy as core
from src.logic import optimization_gurobipy_stochastic as stochastic
from tests.test_mvp2_h300_partial import fixture, synthetic_control


def status_codes():
    return SimpleNamespace(OPTIMAL=2, TIME_LIMIT=9, MEM_LIMIT=17, INTERRUPTED=11)


def fake_model(solver, calls, *, count=1, status=9):
    return SimpleNamespace(
        Params=SimpleNamespace(
            TimeLimit=1800,
            Threads=solver.threads,
            Seed=42,
            MIPGap=0.1,
            SoftMemLimit=128,
            NumericFocus=1,
        ),
        SolCount=count,
        Status=status,
        Runtime=1799.5,
        MaxMemUsed=1.25,
        dispose=lambda: calls.append("dispose"),
    )


def install_backend(monkeypatch, result, calls, *, fail=None, seam=True, drift=False):
    @ownership.managed_model_solve
    def backend(data, config, solver, *, native_phase_hook):
        calls.append("build")
        if fail == "before_model":
            raise ValueError("build failed")
        model = ownership.own_model(
            fake_model(
                solver,
                calls,
                count=result.metadata["solution_count"],
                status=getattr(status_codes(), result.metadata["gurobi_status_name"]),
            ),
            "gurobipy",
        )
        if fail == "construction":
            raise ValueError("construction failed")
        if seam:
            native_phase_hook("native_ready", model, status_codes())
            native_phase_hook("optimization", model, status_codes())
        calls.append("optimize")
        if fail == "optimization":
            raise ValueError("optimization failed")
        if seam:
            native_phase_hook("export_validation", model, status_codes())
        if fail == "extraction":
            raise ValueError("extraction failed")
        result.metadata["gurobi_status_code"] = model.Status + int(drift)
        calls.append("extract" if model.SolCount else "no_incumbent")
        return result

    monkeypatch.setattr(stochastic, "solve_stochastic_model_gurobipy", backend)


@pytest.mark.parametrize("threads", worker.design.GRID)
def test_global_profile(threads):
    solver = worker.solver_profile(threads)
    assert solver.time_limit == 1800
    assert solver.threads == threads
    assert solver.seed == 42 and solver.mip_gap == 0.1
    assert solver.solver_options == {"SoftMemLimit": 128, "NumericFocus": 1}
    assert solver.multiobjective_stage_options == {r: {"Method": 2} for r in worker.design.ROLES}
    assert not solver.compute_iis and not solver.compact_python_indices


def test_public_entry_denies_without_import_or_files(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        pytest.fail("Backend reached through closed public entry.")

    monkeypatch.setattr(stochastic, "solve_stochastic_model_gurobipy", forbidden)
    for flags in ({}, {"accepted": True, "production_admitted": True}, {"miniature": True}):
        with pytest.raises(PermissionError):
            worker.execute_native_worker(tmp_path / "run", **flags)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "native,count,stages",
    [
        ("OPTIMAL", 1, 3),
        ("TIME_LIMIT", 1, 1),
        ("TIME_LIMIT", 0, 0),
        ("MEM_LIMIT", 1, 1),
        ("MEM_LIMIT", 0, 0),
        ("INTERRUPTED", 1, 1),
    ],
)
def test_native_partial_pipeline(native, count, stages, monkeypatch, tmp_path):
    result, data, config, anchor = fixture(native, count, stages)
    calls = []
    install_backend(monkeypatch, result, calls)
    directory = tmp_path / "worker"
    report = worker._integrate_native(directory, data, config, anchor)
    identity = worker.design.digest(anchor)
    assert worker.controls.phase_events(directory, identity) == list(worker.controls.PHASES)
    assert calls == ["build", "optimize", "extract" if count else "no_incumbent", "dispose"]
    snapshot = worker.controls.read_json(directory / "native-terminal.json")
    assert snapshot["solution_count"] == count
    assert snapshot["native_runtime_seconds"] == 1799.5
    products = directory / "products"
    assert (products / "incumbent.json").exists() is bool(count)
    assert not (products / "control.json").exists()  # The worker cannot close its parent.
    assert not (products / "run_completion.json").exists()
    worker.partial.seal_control(products, synthetic_control(anchor), anchor)
    archive, checksum, _receipt = worker.partial.collect(
        products,
        tmp_path / "transfer",
        "123|COMPLETED|0:0\n",
        "123",
        data,
        config,
        anchor,
    )
    reviewed = worker.partial.review_transfer(archive, checksum, "123", data, config, anchor)
    assert reviewed["classification"]["disposition"] == report["classification"]["disposition"]
    assert reviewed["classification"]["production_admitted"] is False
    assert ownership.OWNED.get() is None


@pytest.mark.parametrize(
    "fail,phases,snapshot,disposals",
    [
        ("before_model", 1, False, 0),
        ("construction", 1, False, 1),
        ("optimization", 2, False, 1),
        ("extraction", 4, True, 1),
    ],
)
def test_failure_is_not_fabricated_solution(
    fail,
    phases,
    snapshot,
    disposals,
    monkeypatch,
    tmp_path,
):
    result, data, config, anchor = fixture()
    calls = []
    install_backend(monkeypatch, result, calls, fail=fail)
    directory = tmp_path / "worker"
    with pytest.raises(ValueError, match="failed"):
        worker._integrate_native(directory, data, config, anchor)
    assert calls.count("dispose") == disposals
    assert len(worker.controls.phase_events(directory, worker.design.digest(anchor))) == phases
    assert (directory / "native-terminal.json").exists() is snapshot
    assert not (directory / "products/closure.json").exists()
    assert worker.controls.read_json(directory / "failure.json")["exception_type"] == "ValueError"
    assert ownership.OWNED.get() is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("time_limit", 1801),
        ("threads", True),
        ("compute_iis", True),
        ("solver_options", {"TimeLimit": 1800}),
        ("multiobjective_stage_options", {"economic_cost": {"Method": 2}}),
    ],
)
def test_profile_rejection_before_native_or_files(field, value, tmp_path, monkeypatch):
    result, data, config, anchor = fixture()
    calls = []
    install_backend(monkeypatch, result, calls)
    solver = worker.solver_profile(4)
    setattr(solver, field, value)
    with pytest.raises(ValueError, match="profile"):
        worker._integrate_native(tmp_path / "run", data, config, anchor, solver=solver)
    assert not calls and not list(tmp_path.iterdir())


@pytest.mark.parametrize("kind", ["data", "config", "direct", "missing_seams", "native_drift"])
def test_anchor_and_terminal_rejections(kind, tmp_path, monkeypatch):
    result, data, config, anchor = fixture()
    calls = []
    install_backend(
        monkeypatch,
        result,
        calls,
        seam=kind != "missing_seams",
        drift=kind == "native_drift",
    )
    if kind in {"data", "config"}:
        anchor[kind + "_sha256"] = "0" * 64
    if kind == "direct":
        config.use_direct_origin_customer = True
    with pytest.raises(ValueError):
        worker._integrate_native(tmp_path / "run", data, config, anchor)
    assert not (tmp_path / "run/products/closure.json").exists()
    if kind in {"data", "config", "direct"}:
        assert not calls and not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "parameter",
    [
        "TimeLimit",
        "Threads",
        "Seed",
        "MIPGap",
        "SoftMemLimit",
        "NumericFocus",
    ],
)
def test_effective_native_guard_before_per_pass_copy(parameter, tmp_path):
    solver = worker.solver_profile(4)
    journal = worker.controls.PhaseJournal(tmp_path / "phases", "a" * 64)
    journal.enter("build")
    hook = worker.NativeHooks(journal, solver)
    model = fake_model(solver, [])
    setattr(model.Params, parameter, -1)
    with pytest.raises(ValueError, match="parameter drift"):
        hook("native_ready", model, status_codes())
    assert journal.index == 1 and not hook.ready


def callback_codes():
    names = (
        "MULTIOBJ",
        "MULTIOBJ_OBJCNT",
        "MULTIOBJ_STATUS",
        "MULTIOBJ_OBJBST",
        "MULTIOBJ_OBJBND",
        "MULTIOBJ_MIPGAP",
        "MULTIOBJ_ITRCNT",
        "MULTIOBJ_NODCNT",
        "MULTIOBJ_NODLFT",
        "MULTIOBJ_SOLCNT",
        "MULTIOBJ_RUNTIME",
        "MULTIOBJ_WORK",
    )
    return SimpleNamespace(**dict(zip(names, range(len(names)), strict=True)))


def test_real_observer_single_call_global_window_and_priority_order(monkeypatch, tmp_path):
    """Call the actual core observer against a fake native model, not a solver."""
    calls = []
    solver = worker.solver_profile(4)
    journal = worker.controls.PhaseJournal(tmp_path / "phases", "a" * 64)
    journal.enter("build")
    hook = worker.NativeHooks(journal, solver)
    codes = callback_codes()
    model = fake_model(solver, calls)
    values = {}
    model.cbGet = lambda code: values[code]
    model.getMultiobjEnv = lambda index: SimpleNamespace(
        setParam=lambda name, value: calls.append(("pass_param", index, name, value)),
    )

    def optimize(callback):
        assert journal.index == 2 and hook.ready
        calls.append("single_native_optimize")
        for i in range(1, 4):
            values.update(dict.fromkeys(range(12), 0))
            values.update(
                {
                    codes.MULTIOBJ_OBJCNT: i,
                    codes.MULTIOBJ_STATUS: 2,
                    codes.MULTIOBJ_OBJBST: 200 if i == 3 else 0,
                    codes.MULTIOBJ_OBJBND: 200 if i == 3 else 0,
                    codes.MULTIOBJ_SOLCNT: 1,
                }
            )
            callback(model, codes.MULTIOBJ)

    model.optimize = optimize
    monkeypatch.setattr(core, "observed_matrix", lambda *_: calls.append("matrix"))
    monkeypatch.setattr(core, "gurobi_message", lambda *_: None)
    roles = worker.design.ROLES
    stages = core._optimize_with_stage_observer(
        model=model,
        GRB=SimpleNamespace(Callback=codes, OPTIMAL=2, TIME_LIMIT=9),
        objective_policy="lexicographic",
        objective_names=roles,
        objective_roles=roles,
        solver_config=solver,
        native_phase_hook=hook,
    )
    assert [s["stage_role"] for s in stages] == list(roles)
    assert calls == [
        "matrix",
        *(("pass_param", i, "Method", 2) for i in range(3)),
        "single_native_optimize",
    ]
    assert model.Params.TimeLimit == 1800
    assert journal.index == 3 and hook.terminal["solution_count"] == 1


@pytest.mark.parametrize("site", ["phase", "event"])
@pytest.mark.parametrize("earlier_failure", [False, True])
def test_observer_failure_cannot_skip_disposal_or_context_reset(site, earlier_failure, monkeypatch):
    calls = []

    def broken(*args, **kwargs):
        # Construction telemetry is not the cleanup failure being injected.
        if site == "phase" and args[0] != "native_model_disposal":
            return
        raise OSError("telemetry failed")

    monkeypatch.setattr(ownership, site, broken)

    @ownership.managed_model_solve
    def backend():
        for _ in range(2):
            model = SimpleNamespace(dispose=lambda: calls.append("dispose"))
            ownership.own_model(model, "gurobipy")
        if earlier_failure:
            raise ValueError("original failure")
        return SimpleNamespace(metadata={})

    with pytest.raises(ValueError if earlier_failure else OSError):
        backend()
    assert calls == ["dispose", "dispose"]
    assert ownership.OWNED.get() is None


def test_public_profile_isolated_and_not_mutable_policy():
    before = worker.design.policy()
    first = worker.solver_profile(4)
    first.multiobjective_stage_options["economic_cost"]["Method"] = 0
    assert worker.solver_profile(4).multiobjective_stage_options["economic_cost"] == {"Method": 2}
    assert worker.design.policy() == before


def test_validation_exception_never_closes_products(tmp_path, monkeypatch):
    result, data, config, anchor = fixture()
    calls = []
    install_backend(monkeypatch, result, calls)

    def broken(*args, **kwargs):
        assert calls[-1] == "dispose"
        raise ValueError("validation failed")

    monkeypatch.setattr(worker.partial, "export_partial", broken)
    with pytest.raises(ValueError):
        worker._integrate_native(tmp_path / "worker", data, config, anchor)
    assert not (tmp_path / "worker/products/closure.json").exists()
    assert worker.controls.read_json(tmp_path / "worker/failure.json")["native_terminal_captured"]


def test_optional_native_observations_are_missing_not_zero(tmp_path):
    journal = worker.controls.PhaseJournal(tmp_path / "phases", "a" * 64)
    journal.enter("build")
    hook = worker.NativeHooks(journal, worker.solver_profile(4))
    model = fake_model(hook.solver, [])
    del model.Runtime
    model.MaxMemUsed = float("nan")
    hook("native_ready", model, status_codes())
    hook("optimization", model, status_codes())
    hook("export_validation", model, status_codes())
    assert hook.terminal["native_runtime_seconds"] is None
    assert hook.terminal["native_peak_decimal_gb"] is None


def test_default_observer_preserves_legacy_no_hook_behavior(monkeypatch):
    calls = []
    monkeypatch.setattr(core, "observed_matrix", lambda *_: None)
    model = SimpleNamespace(optimize=lambda: calls.append("optimize"))
    assert (
        core._optimize_with_stage_observer(
            model=model,
            GRB=SimpleNamespace(),
            objective_policy="penalty",
            objective_names=("cost",),
        )
        == []
    )
    assert calls == ["optimize"]


@pytest.mark.parametrize("count", [0, 1])
def test_actual_stochastic_dispatch_and_owner_with_fake_native_api(count, monkeypatch, tmp_path):
    """Exercise actual dispatch/build/observer/count branch; fake algebra is not a MILP solve."""
    result, data, config, anchor = fixture(count=count, stage_count=0)
    calls = []
    solver = worker.solver_profile(4)
    model = fake_model(solver, calls, count=count)

    class FakeVars(dict):
        def sum(self, *_args):
            return 0.0

    def add_vars(keys, **_kwargs):
        return FakeVars(dict.fromkeys(keys, 0.0))

    model.addVars = add_vars
    model.addConstr = lambda *_args, **_kwargs: None
    model.addGenConstrIndicator = lambda *_args, **_kwargs: None
    model.setObjectiveN = lambda *_args, **kwargs: calls.append(("objective", kwargs["priority"]))
    model.setParam = lambda name, value: setattr(model.Params, name, value)
    model.getMultiobjEnv = lambda index: SimpleNamespace(
        setParam=lambda name, value: calls.append(("pass_param", index, name, value)),
    )
    model.optimize = lambda callback: calls.append("single_native_optimize")
    gp = SimpleNamespace(Model=lambda *_: model, quicksum=sum)
    grb = SimpleNamespace(
        Callback=callback_codes(),
        BINARY="B",
        CONTINUOUS="C",
        INFINITY=1e100,
        MINIMIZE=1,
        OPTIMAL=2,
        INFEASIBLE=3,
        UNBOUNDED=5,
        TIME_LIMIT=9,
    )
    monkeypatch.setattr(stochastic, "_import_gurobi", lambda: (gp, grb))
    monkeypatch.setattr(core, "observed_matrix", lambda *_: None)

    def extract(**kwargs):
        assert count > 0
        assert (tmp_path / "worker/native-terminal.json").exists()
        calls.append("sparse_extract")
        result.metadata.update(kwargs["metadata"])
        return result

    monkeypatch.setattr(stochastic, "_extract_stochastic_result", extract)
    report = worker._integrate_native(tmp_path / "worker", data, config, anchor)
    assert calls.count("single_native_optimize") == 1
    assert calls.count("sparse_extract") == count
    assert calls[-1] == "dispose"
    assert [c for c in calls if isinstance(c, tuple) and c[0] == "objective"] == [
        ("objective", 3),
        ("objective", 2),
        ("objective", 1),
    ]
    assert report["classification"]["independently_feasible"] is bool(count)
    assert ownership.OWNED.get() is None


def test_interrupt_during_native_call_disposes_and_records_failure(monkeypatch, tmp_path):
    result, data, config, anchor = fixture()

    @ownership.managed_model_solve
    def backend(data, config, solver, *, native_phase_hook):
        model = ownership.own_model(fake_model(solver, calls), "gurobipy")
        native_phase_hook("native_ready", model, status_codes())
        native_phase_hook("optimization", model, status_codes())
        raise KeyboardInterrupt()

    calls = []
    monkeypatch.setattr(stochastic, "solve_stochastic_model_gurobipy", backend)
    with pytest.raises(KeyboardInterrupt):
        worker._integrate_native(tmp_path / "worker", data, config, anchor)
    assert calls == ["dispose"]
    assert ownership.OWNED.get() is None
    assert (tmp_path / "worker/failure-cleanup.json").exists()
    assert not (tmp_path / "worker/products/closure.json").exists()


def test_symbolic_status_cannot_contradict_native_code(monkeypatch, tmp_path):
    result, data, config, anchor = fixture()
    calls = []
    install_backend(monkeypatch, result, calls)
    original = stochastic.solve_stochastic_model_gurobipy

    def changed(*args, **kwargs):
        solved = original(*args, **kwargs)
        solved.metadata["gurobi_status_name"] = "MEM_LIMIT"
        return solved

    monkeypatch.setattr(stochastic, "solve_stochastic_model_gurobipy", changed)
    with pytest.raises(ValueError, match="Symbolic status drift"):
        worker._integrate_native(tmp_path / "worker", data, config, anchor)
    assert not (tmp_path / "worker/products/closure.json").exists()


@pytest.mark.parametrize("failed_site", ["failure_receipt", "cleanup_receipt", "both"])
def test_receipt_errors_do_not_replace_original_interrupt(failed_site, monkeypatch, tmp_path):
    result, data, config, anchor = fixture()
    calls = []
    original_write = worker.controls.write_once

    def broken(path, value):
        name = worker.partial.Path(path).name
        if (name == "failure.json" and failed_site in {"failure_receipt", "both"}) or (
            name == "failure-cleanup.json" and failed_site in {"cleanup_receipt", "both"}
        ):
            raise OSError("full filesystem")
        return original_write(path, value)

    monkeypatch.setattr(worker.controls, "write_once", broken)

    @ownership.managed_model_solve
    def backend(data, config, solver, *, native_phase_hook):
        model = ownership.own_model(fake_model(solver, calls), "gurobipy")
        native_phase_hook("native_ready", model, status_codes())
        native_phase_hook("optimization", model, status_codes())
        raise KeyboardInterrupt("original interruption")

    monkeypatch.setattr(stochastic, "solve_stochastic_model_gurobipy", backend)
    with pytest.raises(KeyboardInterrupt, match="original interruption") as captured:
        worker._integrate_native(tmp_path / "worker", data, config, anchor)
    assert captured.value.__notes__
    assert calls == ["dispose"] and ownership.OWNED.get() is None
    assert not (tmp_path / "worker/products/closure.json").exists()


def test_failure_transition_precedes_native_disposal(monkeypatch, tmp_path):
    result, data, config, anchor = fixture()
    calls = []

    def dispose():
        assert (tmp_path / "worker/failure-cleanup.json").exists()
        calls.append("dispose")

    @ownership.managed_model_solve
    def backend(data, config, solver, *, native_phase_hook):
        model = fake_model(solver, calls)
        model.dispose = dispose
        ownership.own_model(model, "gurobipy")
        native_phase_hook("native_ready", model, status_codes())
        native_phase_hook("optimization", model, status_codes())
        raise ValueError("original failure")

    monkeypatch.setattr(stochastic, "solve_stochastic_model_gurobipy", backend)
    with pytest.raises(ValueError, match="original failure"):
        worker._integrate_native(tmp_path / "worker", data, config, anchor)
    assert calls == ["dispose"]


def test_interrupted_disposal_still_attempts_other_owners_and_resets_context():
    calls = []

    def interrupted():
        calls.append("interrupt")
        raise KeyboardInterrupt("disposal interruption")

    @ownership.managed_model_solve
    def backend():
        ownership.own_model(SimpleNamespace(dispose=lambda: calls.append("dispose")), "gurobipy")
        ownership.own_model(SimpleNamespace(dispose=interrupted), "gurobipy")
        return SimpleNamespace(metadata={})

    with pytest.raises(KeyboardInterrupt, match="disposal interruption"):
        backend()
    assert calls == ["interrupt", "dispose"]
    assert ownership.OWNED.get() is None
