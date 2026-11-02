"""Transfer the common linear Pyomo model to the installed PySCIPOpt API."""

from types import SimpleNamespace

from src.logic.pyomo_linear_matrix import representation


class ScipAdapter:
    """Own one native problem; never invoke the native scientific model builder."""

    def __init__(self):
        self.native = None
        self.variables = []
        self.native_variables = []

    def set_instance(self, model, config):
        import pyomo.environ as pyo
        from pyscipopt import Model, quicksum

        self.native = Model("common_pyomo_scalar")
        native = self.native
        if not config.tee:
            native.hideOutput()
        if config.log_file:
            native.setLogfile(config.log_file)
        self.variables = list(model.component_data_objects(pyo.Var, active=True))
        index = {id(var): i for i, var in enumerate(self.variables)}
        for i, var in enumerate(self.variables):
            kind = "B" if var.is_binary() else "I" if var.is_integer() else "C"
            lb, ub = var.lb, var.ub
            if var.fixed:
                lb = ub = pyo.value(var)
            self.native_variables.append(native.addVar(
                name=f"x{i}", vtype=kind,
                lb=-native.infinity() if lb is None else float(lb),
                ub=native.infinity() if ub is None else float(ub),
            ))

        def expression(expr):
            constant, terms = representation(expr, index)
            return constant + quicksum(c * self.native_variables[i] for i, c in terms)

        objectives = list(model.component_data_objects(pyo.Objective, active=True))
        if len(objectives) != 1 or objectives[0].sense != pyo.minimize:
            raise ValueError("SCIP adapter requires one linear minimization objective.")
        native.setObjective(expression(objectives[0].expr), "minimize")
        for i, row in enumerate(model.component_data_objects(pyo.Constraint, active=True)):
            expr = expression(row.body)
            if row.equality:
                native.addCons(expr == float(pyo.value(row.lower)), name=f"r{i}")
            else:
                if row.has_lb():
                    native.addCons(expr >= float(pyo.value(row.lower)), name=f"r{i}l")
                if row.has_ub():
                    native.addCons(expr <= float(pyo.value(row.upper)), name=f"r{i}u")
        parameters = {
            "limits/gap": config.mip_gap, "limits/absgap": 1e-10,
            "timing/clocktype": 2, "numerics/feastol": 1e-9,
            "parallel/maxnthreads": config.threads or 1,
            "lp/threads": config.threads or 1,
            "randomization/randomseedshift": config.seed or 0,
        }
        if config.time_limit is not None:
            parameters["limits/time"] = config.time_limit
        for key, value in parameters.items():
            native.setParam(key, value)
        self.parameters = {key: native.getParam(key) for key in parameters}
        self.parameters.update({
            key: native.getParam(key) for key in (
                "randomization/permutationseed", "randomization/lpseed",
            )
        })

    def solve(self):
        from importlib.metadata import version

        native = self.native
        native.optimize()
        usable = native.getNSols() > 0
        solution = native.getBestSol() if usable else None
        if usable:
            for var, translated in zip(self.variables, self.native_variables, strict=True):
                var.set_value(float(native.getSolVal(solution, translated)))
        return SimpleNamespace(
            termination=str(native.getStatus()), usable=usable,
            objective=float(native.getObjVal()) if usable else None,
            bound=float(native.getDualbound()), gap=float(native.getGap()) if usable else None,
            runtime=float(native.getSolvingTime()), parameters=self.parameters,
            versions={
                "pyomo": version("pyomo"), "pyscipopt": version("pyscipopt"),
                "scip": ".".join(str(f()) for f in (
                    native.getMajorVersion, native.getMinorVersion, native.getTechVersion,
                )),
            },
            counters={"nodes": native.getNNodes(), "lp_iterations": native.getNLPIterations()},
        )

    def close(self):
        if self.native is not None:
            self.native.freeProb()
            self.native = None
        self.native_variables.clear()
        self.variables.clear()
