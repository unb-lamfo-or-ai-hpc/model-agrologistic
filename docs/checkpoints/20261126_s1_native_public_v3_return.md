# S1 public v3: explicit license starts; first DET solve rejected

The researcher authorized the fixed v3 capsule with
`GRB_LICENSE_FILE=C:\gurobi1400\gurobi.lic` only in its child, explicitly selecting
the supplied address rather than relying on discovery. V1/v2 were preserved;
h215, HPC and merge were excluded. V3 uses runtime
`818f63f6918795161919c59948ab9956edbb464f`, plan SHA-256
`0dca74c004b2adf23ce88c12bce235b90252e7a0b335326a93e1a34a75963ee4`.
The source, plan, command and unused-start state were checked before execution.

## Observed result

The child imported Gurobi and successfully started its environment with the
explicit selection. It then returned `ValueError` in `control_solve` for
`public-native-det-policy-0`, with zero control receipts. The parent recorded
`rejected`, worker return code 1 and a consumed start, in 0.8374284000019543
seconds. Finish was 2026-11-26T20:47:45.315149Z
(17:47:45 America/Sao_Paulo). Read-only collection validates the failure digest
and reproduces the rejection. All v1/v2/v3 originals remain unchanged.

Environment startup establishes that the explicit selection cleared that gate
for this attempt. It does not establish large-license capacity or numerical
qualification. No public control has an accepted native receipt. The v3
diagnostic does not locate the ValueError within the facade; actual model/
optimizer activity counts are unknown. Do not replace them with zero or infer a
mathematical failure. V1's unknowns and v2's earlier licensing rejection remain
independent evidence.

Read [the original v3 audit](../evidence/mvp3_s1_public_native_v3_rejected_20261126.json).

## Local diagnosis and prospective correction

A solver-free replay of the original frozen input, embedding and prepared-data
guards accepts the first DET control. Mocked tests of the real facade and core
reach the pre-optimization boundary across all 32 controls, with a symbolic API,
parameter doubles and an intentional stop before any engine call. Those tests
are not native numerical observations.

Source inspection found a definite exclusion defect in the full default audit:
it used case-sensitive `Username`, while the installed Gurobi parameter constants
declare `UserName`. The guard could therefore query a connection parameter that
was intended to be excluded. The correction normalizes case and underscores
before any query, including prefixed connection/credential parameters. This
defect is a plausible contributor to v3, but its exact causal role cannot be
proven from the original phase-only receipt. No connection values were retained
or exported in the v3 receipts; whether they were queried is unknown.

The optimizer/default gate is not relaxed: at least 100 software parameters are
still required, only OutputFlag/TimeLimit may differ from defaults, and unavailable
introspection or unexpected algorithm settings still rejects the control.
Prospective failures retain safe reason codes, software parameter names/counts
and the final public source file/function/line. They do not retain parameter
values, exception messages, raw traceback text, frame locals or license contents.

The facade also forwards the existing optional native phase hook. The public
worker records the native-ready, optimization-entry and optimization-return
events for the current control. It neither replaces nor adds optimizer calls;
the retained scalar optimize function and mathematical builder are unchanged.
These finer diagnostics apply only to future authorized capsules and do not
retroactively fill the v3 record.

Regression controls cover mixed-case/underscore connection names without reading
their values, rejection of genuinely changed software parameters, safe diagnostic
origin, unavailable introspection and full mocked construction/hook forwarding.
No further native import, license start or optimizer call occurred during this
follow-up. The native scientific eight-hour reference and fixed public limits
are unchanged.

## Continuation

The v3 start is consumed and must never be retried. Preserve all original v1/v2/v3
claims and receipts. A fresh prospective capsule may include the corrected audit
and finer diagnostics, retaining the same explicit child-only license path,
32 controls, 60 seconds/model and 2,700-second worker ceiling. Any execution needs
its own researcher authorization. PR167 remains Draft; remote CI, h215/HPC,
environment installation, shared-setting changes and merge remain excluded.
Production admission, large-license capacity and source consistency are not
qualified by preparation or by the successful environment startup.
