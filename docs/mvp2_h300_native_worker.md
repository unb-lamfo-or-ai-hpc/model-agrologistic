# S2 closed native worker: software integration qualification

## Authority and provenance

PR #55 was merged into develop at `af7271962d314d5c1e26f1c7745147ea071c4c7f`.
This next gate integrates its [controls and partial collector](mvp2_h300_runtime_controls.md)
with the existing stochastic Gurobi backend. It provides **software qualification,
not licensed native qualification or production admission**. There is no CLI,
launcher, scheduler call, license probe, workbook load, optimization campaign or
repeat. `execute_native_worker` always raises before native import or file creation;
the private integration seam is not an admission interface. No existing runner is
redirected through it. Existing general runners are not new S2 authority.

Three `src/logic` files change: optional synchronous phase hooks in the native
observer/stochastic dispatch and failure-safe native ownership cleanup. This
changes the implementation fingerprint even though formulation, route selection,
extraction thresholds, objectives and tolerance settings are untouched. Do not
rewrite any accepted S1/S2 source identity or archived result. The design policy's
historical reference hash remains historical, not the hash of this integration.
A later source/cohort qualification must reconcile the new exact implementation
before admission; AST review or CI alone cannot establish numerical parity.

Workbooks, dependencies, scientific validator, design policy, manifests, article
and presentation remain unchanged. No EVPI/VSS computation or editorial removal
is performed; the agreed editorial gate remains S6.

## Native seams and one global window

The worker creates a fresh phase journal and enters build before native import
and construction. After the model has its global parameters, the optional native
hook checks effective `TimeLimit=1800`, selected Threads, `Seed=42`, `MIPGap=0.1`,
`SoftMemLimit=128` decimal GB and `NumericFocus=1`, before per-pass environments
are copied. The exact generated solver configuration is independently compared
with a fresh frozen profile. Extra global options, per-pass time limits, IIS,
compaction, warm starts and direct origin-to-customer arcs are not introduced.
The three priority environments receive only the inherited all-barrier Method=2.

The strict optimization transition is immediately before the **single** existing
multiobjective `model.optimize(callback)` call, after callback checks and priority
setup. No priority pass receives a renewed 1800-second window. The existing
fine-grained telemetry marker precedes setup and remains a different observation;
it must not be substituted for this strict journal seam. Default callers have no
hook and preserve their previous invocation path.

Immediately after native optimize returns, before diagnostics completion or sparse
extraction, export/validation starts. Native integer Status and SolCount are read
while the model is alive; a write-once `native-terminal.json` is published in the
phase directory. Available native Runtime and MaxMemUsed are separately labelled;
missing or nonfinite optional values stay null. The snapshot does not contain a
vector, a complete hierarchy certificate or admission authority. In particular,
SolCount=0 cannot create a fictitious incumbent after TIME_LIMIT/MEM_LIMIT.

The backend retains ownership through extraction and disposes its model before
returning sparse values to the worker. Native disposal therefore belongs to
export/validation, followed by independent validation and immutable partial
products. Cleanup is the final worker phase. Earlier exceptions publish failure
cleanup without fabricating skipped phases. Interrupted/failed extraction may
leave a native terminal snapshot but never a completed solution closure.
The private failure-cleanup hook publishes this transition **before** managed
native disposal begins, so the parent's separate cleanup cap can cover a failing
native solve rather than starting only after disposal returns. A failed receipt
write cannot manufacture closure; the original interruption/exception remains
primary and secondary publication errors are attached as exception notes.

The outer owner now attempts disposal even when disposal-phase/event telemetry
raises, attempts remaining owned models after a disposal interruption, and resets
its ContextVar in a finally clause. An earlier solve exception
remains primary; otherwise the observation failure propagates after cleanup.
Disposal does not prove allocator release, shared-default-environment disposal,
allocation containment or total resource recovery.

## Products and independent closure

The result count/status code and symbolic name must match the live terminal
snapshot (the symbolic name is derived using the native GRB constants), and one
successful managed Gurobi disposal record is required before export. Values are
passed to the unchanged partial exporter and independent validator; the worker
cannot write its parent's control receipt. Portable review still requires the
separate post-supervision parent closure and external anchor/accounting evidence.

Native terminal/failure snapshots remain in the original phase directory and are
not silently added to PR #55's allowlisted transfer protocol. The partial archive
contains its original result/validation/closure products only. A future complete
worker-evidence protocol must bind/transfer these native diagnostic snapshots and
their source identity explicitly, including rejected/incomplete outcomes.

No live sampler is created here. A terminal native memory observation is not
OS/tree/cgroup RSS, lifetime CPU-hours or continuous peak coverage. The parent
caps remain 900/1800/900/300 seconds, 3900 per child and the earlier block deadline;
this cooperative private seam does not enforce them by itself. Kill during
extraction/disposal must be externally supervised and can leave incomplete bytes.

## What the tests qualify

All new tests are solver-free: the public entry is unconditionally denied, solver
and effective-native profiles reject drift, actual stochastic dispatch/native
observer are exercised using a fake native API, one optimize call and ordered
priorities are checked, and native count branches retain or omit incumbents.
Other tests use a managed backend double and the existing public miniature fixture
to export, freshly validate, collect and review complete/partial/no-incumbent
products. These synthetic vectors are not new agricultural outcomes.

Construction, native-call, extraction, validation and interruption failures retain
failure provenance without solution closure. Telemetry phase/event failures test
disposal and ownership reset. Optional native observations, missing hooks, result
drift and data/configuration-anchor drift are negative paths. Tests do not establish
native callback delivery, licensed numerical parity, h300 export volume, native
time-limit behavior or resource adequacy. In particular fake algebra and fake
optimization never validate a mathematical formulation.

Local Python 3.13.15 qualification on Windows: 50 new worker tests passed; the
combined thread/design/control/partial/ownership regressions passed 358 tests
with 15 explicit skips (5 POSIX/Bash-only, 3 missing PySCIPOpt and 7 unavailable
Gurobi license). Ruff and wheel/sdist build passed. A normalized AST projection
removing only the optional phase-hook argument/calls matches both previous native
backend files; other scientific modules, data, experiments, manuscript and
dependency declarations are unchanged. Ownership error handling is intentionally
different. This review is not licensed numerical parity; Linux CI must qualify
the platform-specific software paths before Ready.

## Next closed gate

Qualify the full worker-evidence envelope, new source/tools/dependency/cohort
binding, production resource sampling and allocation-wide containment/cleanup.
Specify an exact, separately authorized miniature integration protocol before any
licensed exercise. Only audited miniature evidence plus fresh allocation/license/
homogeneity gates can support a later, separately admitted h300 diagnostic block.
No job or repeat is admitted by this PR; S2 remains open and no speedup is claimed.
