# P4: consolidated diagnostic and terminal-handoff software qualification

17 October 2026. PR106 is already merged at
`20f88399ed323d7c96fe9aa3f94eeb87a758eb3b`. This is its successor, not an edit to
the merged PR or permission to repeat job2214130. The complete
[forensic review](mvp2_s2_p4_2214130_forensic_review.md), redacted ledger and
checkpoint are included in this functional package rather than a bookkeeping PR.

## Evidence and what is not established

The externally anchored carrier reproduces `optimization_watchdog` on the first
4-thread arm. Four thread levels are unrun. The supplied private log tails show
step cancellation and academic WLS startup only. Batch already selects the
designated license before accepted capability probing; `srun --export=ALL`
inherits that environment. These logs do not demonstrate a license failure.
The worker did not independently preserve its exact license-selection receipt.
Native progress was disabled by the frozen `tee=False`/`OutputFlag=0` profile.
No native terminal/vector/accepted solution or exact interrupted subphase is known.

The current parent checks its OLD phase before consuming a late export event.
Its optimization cap and the native TimeLimit both equal1800s. Gurobi explicitly
warns that [TimeLimit can return later](https://docs.gurobi.com/projects/optimizer/en/current/reference/parameters.html#parameter.TimeLimit).
Equal limits cannot assure terminal delivery. This mechanism is demonstrated by
the actual unchanged `Deadlines` implementation, not asserted as a specific
internal Gurobi subphase or independent proof of the solver's terminal status.

## Complete software scope

[Diagnostic components](../scripts/mvp2_s2_p4_diagnostics.py) include:

- A private future worker seam binds a numeric Slurm step/source/plan/thread
  identity before selecting the designated file and invoking the original
  metadata/access checker. No file content is read/hashed, no capability model
  is built and no Gurobi initialization occurs. Fixed typed positive/negative
  records omit paths, identifiers, exception messages and WLS parameters.
- An optional hook decorator delegates to the UNCHANGED native parameter and
  terminal hooks. Three immutable, bounded synchronous milestones capture native
  readiness, optimize entry and native return. No callback, thread, parameter
  mutation, stdout capture or raw solver log is installed. Readiness/entry are
  not continuous progress, native return is not residual validation.
- An allowlisted prefix catalogue rejects unexpected files/directories,
  nonfinite/duplicate JSON, foreign bindings, malformed states and oversized
  records. Per-record2048bytes; entire diagnostic inventory16384bytes. It is
  NOT a portable scientific auditor or fresh capability certificate. The old
  agricultural exporter/allowlist is deliberately unchanged; prospective
  integration must add these bytes within, not above, the existing256MiB cap.
- A deterministic solver-free comparison exercises the actual installed guard
  for early/exact/late/absent return, export and cleanup boundaries. A separately
  labelled arithmetic proposal is compared, never used as an executor/guard.
  Every returned proposal/admission/repeat flag remains false.
- Tests, exact-head Linux qualification, checkpoint, dated status, roadmap,
  negative evidence and the next human decision are delivered together.

These components are **not wired into the installed PR106 worker or launcher**.
Public start/batch/worker/collect actions unconditionally deny before effects;
`check` only identifies the closed software. No new claim namespace, submission
wrapper, NPAD CLI, license access, native miniature or agricultural run is needed
to qualify this package. Software CI uses explicit local metadata/native doubles.
It does not claim live worker selection, licensed performance or export fit.

## Prospective terminal decision: preserve the science, disclose enforcement

The native profile, scientific source, objective hierarchy, seed, threads grid,
compaction-off design and independent validator remain byte-identical. Current
operational guard and every phase/budget/transport pin are also untouched.

| Boundary | Installed contract | Proposal for separate approval |
| --- | --- | --- |
| Native TimeLimit |1800s global across priorities |Same1800s; no parameter change |
| External optimization enforcement |Strict1800s, rejects late export |Allow bounded return tail charged against existing export reserve |
| Export reserve |900s starting after observed export |Native excess above1800s PLUS export must remain strictly below900s |
| Build / cleanup |900s /300s strict |Same |
| Arm / block ceiling |3900s /21600s |Same; no added reserve |
| Failure/no return |Targeted stop, forensic partial block |Still targeted bounded stop; exact integration not yet authorized |

Recommendation: qualify the **shared return/export reserve** in the next
integrated operational package, ONLY after the maintainer explicitly approves
this enforcement change. A proposed1850s native return plus100s export consumes
150s of the900s reserve. A1850s return plus850s export exhausts it and must stop.
A2700s native return with no export already exhausts it. Cleanup cannot extend
the arm/block ceiling. No-return is an unknown native outcome requiring stop,
not no-incumbent or infeasibility.

This is not an assertion of zero native computation beyond1800s. TimeLimit is
unchanged, but native overshoot may include internal work and cannot be called
"free finalization" or excluded from observed wall/CPU time. Actual return,
export, cleanup and guard timestamps must be reported. The tests establish
arithmetic/boundary behavior, not empirical sufficiency of900s or guaranteed
incumbent export. Detailed native callback logging would require another
explicit scientific-source change and is NOT proposed here.

Retaining the installed strict guard is a valid alternative, with the explicit
consequence that a censored arm may again lack terminal/vector evidence. Do not
silently lower native TimeLimit, grant1800s per objective, change Method2,
relabel failed evidence or call different allocations a homogeneous block.

## Qualification, handoff and remaining S2 work

The new focused suite is90 cases, with no license or Slurm requirement. The
existing642-case P4 suite remains unchanged; the combined Linux gate requires
732 cases with zero failures/errors/skips and physical source parity before/
after testing. General Quality/build and other repository checks remain required
on the exact PR head. Local Windows results and intentional platform skips are
recorded independently; they cannot substitute for Linux qualification.

Before Ready, compare all57 P3-protected files and all four frozen transport
hashes, replay the actual2214130 carrier with external anchors and preserve the
full historical checkpoint. No proprietary raw archive, workbook, license,
registrant information or private runtime path is committed.

Next owner after Ready is the maintainer: merge decision and explicit decision
on the proposed external enforcement policy are separate from job admission.
Then ONE integrated prospective package should wire worker selection/milestones,
bounded terminal handoff, source/transport requalification, independently audited
sidecar collection, exclusive replacement admission, full wrapper/tests/pinned
CLI together. It must explicitly authorize any replacement and disposition of
the unrun grid; this PR does not create or admit that claim. Preserve the consumed
job2214130 claim and all predecessor carriers unchanged.

P5 follows actual evidence; it cannot close S2/select a configuration from the
interrupted first arm. Later h400, bounded existing-SCIP/h215, conditional h500,
S6-A and S6-B remain planned; S3/S4 cancelled, EVPI/VSS excluded, article review
and final-only main/develop reconciliation unchanged. December is conditional,
not authority to reduce science. No new NPAD command is necessary now.
