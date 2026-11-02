# Gurobi2228189: original evidence audit and license diagnosis

The original archive and sidecar agree on SHA-256
`1e39227e78f6350e27243917808a81c1d550b92c1800ef170220e0b527bb8839`.
A read-only inspection verified 232 safe regular members, 231 inventory hashes,
nine plan-artifact hashes, original job/source/plan identity and all 648 source
file hashes against exact-source bytes. The original W mathematical contract,
effective scenario probabilities and complete warehouse-selection receipts match
the retained original W record. No archive content was extracted or executed;
the original files and claim remain unchanged.

## First failure and its meaning

The worker traceback ends in Pyomo APPSI's Gurobi call to Model.optimize:

> Model too large for size-limited license

This is the first reported worker error. The collector's ValueError describes
incomplete operational closure and does not identify the native cause by itself.
The startup record completes all twelve stages, including the public controls.
The optimization phase marker occurs 1185.43 s after worker entry, which includes
startup, input/model construction and transfer; it is not pure solve time.
The native log shows version 13.0.3 and the requested parameters, then ends
without a native matrix/search/termination report. No result.json or original
private independent-validation certificate was returned; run_completion remains
running in the preserved incomplete products.

The archive therefore supports a license-capability rejection before a native
search report, not mathematical infeasibility, an eight-hour no-incumbent result,
out-of-memory termination or a solver speed comparison. Objective, bound, gap,
validated service/cost and native solve runtime remain unavailable.

## Implementation diagnosis

The common-Pyomo wrapper does not select the designated NPAD license file,
whereas the native scalar wrappers explicitly exported that selection before
submission. The optimization facade can locate only its configured/default
locations; the input checkout's secret path is not automatically the temporary
worker checkout's path. The original inherited license variable was not retained,
so its absence or exact value is not independently reconstructed here.

In addition, APPSI's availability enum distinguishes FullLicense from a truthy
LimitedLicense. The existing adapter condition tests only whether availability
is false, allowing the latter to proceed to a large build. Passing small public
cases is consistent with this failure and does not prove unrestricted capacity.

The corrective scope is operational: explicitly bind the designated existing
file for Gurobi, check file selection/access without reading/copying/hashing
credentials, and probe capacity above the bundled limit on compute before any
private build. The probe must exercise the same default environment subsequently
used by APPSI and export only safe status/codes. Do not change the scientific
model, matrix, objective, solver strategy, gap target, seed or tolerances.
Current validity/accessibility of the designated full license remains a target
qualification question; it is not established by this archive.

## Preservation and continuation

The local original, NPAD claim, source checkout and collected archive stay
immutable. No repeated start or private solve is admitted by this diagnosis.
The separate SCIP source/claim is not modified or cancelled. PR142 records this
outcome; a distinct qualified correction PR handles operational code. Any future
Gurobi observation needs an explicitly reviewed fresh source/claim/admission,
not reuse of this consumed claim.

Slurm root/batch failed 1:0 after 1295 s; the numerical step failed 1:0 after
1247 s with MaxRSS 29841476K. The external observer retained 245 timely samples
and a 31221248000-byte worker-tree peak. These are pre-failure observations,
not estimates of the memory required to finish a full solve.

Primary technical references:
- [Gurobi size-limit error guidance](https://support.gurobi.com/hc/en-us/articles/360051597492-How-do-I-resolve-a-Model-too-large-for-size-limited-Gurobi-license-error)
- [Gurobi model/default environment](https://docs.gurobi.com/projects/optimizer/en/current/reference/python/model.html)
- [APPSI Gurobi implementation](https://pyomo.readthedocs.io/en/stable/_modules/pyomo/contrib/appsi/solvers/gurobi.html)
