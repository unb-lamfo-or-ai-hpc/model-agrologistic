# Final bounded validation evidence

The JSON validation report is the unchanged NPAD receipt for the selected
ten-reference experiment, generated on 13 September 2026. Its overall result
is **rejected**: levels 1-3 are accepted and level 4 remains pending in the
original validator's terminology. Nine references are accepted. No acceptance
threshold or mathematical implementation was changed to close development.

`closure.json` records the final trial's scheduler and stage observations and
the distinct bounded-MVP development conclusion. Job 2091731 completed the
service pass, reached the 14,400-second optimization budget during the capacity
pass, and did not execute the economic pass. Its independently checked incumbent
does not constitute a completed three-stage result.

The service pass's reported relative gap of `1e100` is not informative at its
zero objective. The absolute discrepancy between zero and its reported lower
bound is approximately 2.85e-9. Service certification is taken from the
independent validation receipt, not that relative-gap sentinel. The capacity
pass's gap is 1.0 (100%), not 1%. The economic gap is missing, not zero.

Slurm elapsed time is 14,746 seconds and maximum RSS is 28,572,324 KiB
(approximately 27.25 GiB). These are whole-job observations, distinct from
optimizer-stage times, requested 192 GiB and Gurobi's decimal-GB soft limit.
This final trial reports a time limit, not an out-of-memory event.

The report retains the original implementation fingerprint, reference identities,
quality receipt and qualifications. Raw scientific inputs and full solution
exports remain governed by their data-provenance and redistribution terms.
This receipt is sufficient for the stated validation outcomes, not for deriving
unreported cost, flow, inventory or investment comparisons.
