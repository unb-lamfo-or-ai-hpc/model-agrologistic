# S1 public native v2: license initialization rejected; start consumed

The researcher authorized exactly one execution of the fixed v2 public capsule,
preserving v1 and excluding h215, HPC and merge. V2 uses runtime
`fc89f3d3b7bdd606581d49a82e1a58384f346428` and plan SHA-256
`41649e0771d47c670f607df64e0447d9f79b1b88f5ff97e884d38aa2caa040ed`.
Its source, command digest, unused-start state and original v1 hashes were
verified before execution. The original v1 and v2 capsules remain frozen.

## Actual return and limits of the diagnosis

The terminal record reports `rejected`, a consumed start, worker return code 1
and 0.508203199977288 seconds. It finished at
2026-11-26T17:54:41.804225Z (14:54:41 America/Sao_Paulo). The new failure receipt
records `phase=environment_start`, `GurobiError`, native code 10009, native import
completed, environment start not completed and zero control receipts. Its digest
is bound to the terminal record and validated by read-only collection.

The installed code defines 10009 as `NO_LICENSE`. Gurobi's
[official explanation](https://support.gurobi.com/hc/en-us/articles/20183546353169-How-do-I-resolve-ERROR-10009)
covers failure to obtain a valid license or licensing token; the number alone
does not distinguish absent/expired/incompatible licenses, token availability
or other licensing subtypes. No exception text or license contents were retained.

The source starts the environment before entering the fixed control loop.
Consequently this v2 attempt reached zero model construction/optimization calls;
none of the 32 numerical controls is qualified. This observed v2 phase does not
retroactively resolve v1's unknown native-activity counts or cause.

Read the [v2 return audit](../evidence/mvp3_s1_public_native_v2_rejected_20261126.json).
All v2 source hashes and original receipts were checked after execution; v1's
original source and receipt hashes were rechecked unchanged. No retry occurred.

## Read-only path finding

Existence-only inspection found that the process and user `GRB_LICENSE_FILE`
settings do not point to an existing file. The process value is an absolute `.lic`
path, without an unexpanded percent variable or server marker. A file exists at
the documented Gurobi14 default location `C:\gurobi1400\gurobi.lic`. No license
contents were opened, copied or hashed, and no variable or registry value changed.

This is an actionable selection discrepancy, consistent with the observed error.
It does not establish the existing candidate file's entitlement, version coverage,
expiry or validity. Gurobi documents explicit path selection through
[`GRB_LICENSE_FILE`](https://support.gurobi.com/hc/en-us/articles/360013417211-Where-do-I-place-the-Gurobi-license-file-gurobi-lic).

## Prepared correction, not executed

The prospective plan schema now includes a license selection. Preparation can
pin an existing local file with `--license-file`; it never reads, copies or hashes
that file. Execute cannot redefine the selection. Before consuming a new start,
the parent checks that a selected file is still present, then overrides
`GRB_LICENSE_FILE` only in the owned child's environment. The parent, user and
machine environment settings remain unchanged. Collection does not require the
license file to remain present later. Frozen older plans use their original
capsule scripts for collection.

Solver-free tests check path pinning without contents, actual child-environment
forwarding through a subprocess double, unchanged parent settings, refusal before
start when a selected file is absent and independent later collection. The native
model, literal 32 controls, 60-second model budget, 2,700-second worker ceiling,
Method=-1/Threads=0 and scientific eight-hour reference are unchanged.

The v2 authorization is consumed. No further license initialization or solve is
authorized. A prospective v3 capsule may pin the existing candidate path, but any
execution needs its own explicit researcher authorization. Do not replace or
retry v1/v2, change global environment settings, install tools, run h215/HPC or
merge. PR167 remains Draft and remote CI stays withheld. License capacity,
production admission and current source consistency remain unqualified.
