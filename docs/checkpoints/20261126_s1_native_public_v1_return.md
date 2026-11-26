# S1 public native v1: consumed, rejected, not qualified

The researcher explicitly authorized one local execution of the prepared 32
public controls, under its existing limits, with no h215, HPC or merge.
The original capsule uses runtime commit
`aff3d69b9c84650bdcb807c2b546f24112788346` and plan SHA-256
`2e17397dd7352386edbb578704fd7abeb2e1484b1cd3e88ddab2ea18847bcc88`.
Its source and unused-start state were verified before the single execute call.

## Observed return

The parent recorded `rejected`, `claim_consumed=true` and a wall duration of
0.5780661000171676 seconds. Start/finish were
2026-11-26T16:36:42.373229Z / 2026-11-26T16:36:42.951269Z
(13:36:42 in America/Sao_Paulo). The expected plan, start and terminal records
are present, but there are zero per-control receipts and no worker summary.
Read-only collection reproduces the rejection; all frozen source hashes still
match. The original files and prepared capsule remain unchanged.

This does not qualify any of the 32 controls. It is not an observed mathematical
infeasibility or a demonstrated license failure. The v1 wrapper discarded child
stdout/stderr and persisted no failure phase/class, so the rejection cause and
the number of native imports, license initializations or optimizer calls cannot
be established. Do not replace those unknowns by zero or infer that the first
model reached optimization. Metadata-only inspection after the return reports
Python 3.13.15 and gurobipy distribution 14.0.0 in both normal and isolated
startup; that inspection did not import the native package or open a license.

The audit and original receipt digests are recorded in
[the return evidence](../evidence/mvp3_s1_public_native_v1_rejected_20261126.json).
The prior local preparation/test receipt remains evidence of its own scope;
passing software tests did not predict this native return.

## Prepared diagnostic correction

The working qualification script now preserves a separate failure receipt after
source/owner verification. It contains only the last execution phase, public
control identifier, completed-receipt count, native-import/environment-start
flags, exception class and, for native Gurobi exceptions, an integer error code.
No exception text, traceback, license contents or connection values are stored.
The parent retains the worker return code and failure digest, and read-only
collection verifies that binding. Diagnostic files are written exclusively.

Solver-free tests cover a synthetic native error containing deliberately secret
text, preservation of its safe fields without the text, refusal to overwrite an
original failure, owned-worker import failure and tampered failure collection.
The synthetic error code is test data, not an observed v1 license diagnosis.
The native builder, mathematical controls, analytical targets, strict parameter
checks and one-use budgets are unchanged. This correction has not been exercised
against a native engine and does not retroactively diagnose v1.

## Continuation gate

The authorized attempt is consumed. No retry, replacement native attempt,
environment installation, license change, h215/HPC action or merge was performed.
PR167 stays Draft and remote CI remains withheld. Any future native attempt
requires a fresh source-bound capsule and explicit researcher CLI authorization;
the rejected v1 claim must never be reused. No new native capsule is executed by
preparing this diagnostic correction. Production admission, large-license
capacity and live-source consistency remain unqualified.
