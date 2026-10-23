# Fixed scalar penalties: acceptance and interpretation

Maintainer decision, 20 October 2026: retain the actual PR115/R3-A h215
coefficients, accept job2217990 as a successful result of the approved scalar
contract, and proceed to h300. A calibration campaign is not approved or a
prerequisite. This document discusses the current MVP2 only.

| Component | Frozen coefficient | Physical unit |
| --- | ---: | --- |
| Unmet domestic demand |90000 | monetary units per tonne |
| Emergency static capacity |45000 | monetary units per tonne-period |
| Emergency reception capacity |45000 | monetary units per overflow tonne in a period |

The loader policy identifier remains `thesis_dynamic`; its name is a software
key, not a source citation. The h300 preparation checks the resulting vector
after route selection against these exact rates. It must reject drift rather
than silently recalibrate, override input data or change the scientific source.
New warehouses add vector entries; equality means identical per-unit coefficients
and identical values for common identifiers, not an identical vector hash across
different populations. Scenario probabilities remain nine Cartesian values1/9.

## Feasibility and interpretation

Positive unmet-demand, storage and reception variables are permitted decisions
in this formulation. They relax their own equations; they do not guarantee
feasibility of every input, relax shipping limits, or represent newly installed
infrastructure. Accepted original residuals certify the stated slack-enabled
equations. Report service, unmet tonnes, storage tonne-periods, reception overflow,
peaks and scenario dispersion alongside that accepted feasibility.

These coefficients express a trade-off. For example, one extra tonne requiring
both one period of emergency storage and emergency reception incurs45000+45000,
equal to90000 of avoided unmet-demand penalty before transportation. This is an
illustration, not a decomposition of every observed shortfall. Low slack or full
service is not an additional acceptance criterion approved for this campaign.

## Complexity and solution metrics

Slacks enlarge the feasible set and can help produce incumbents, but add variables
and interactions. Neither the signs nor magnitudes of these coefficients imply
a monotonic runtime improvement, an easier proof, or a causal explanation of
the measured solve time. Matrix dimensions, bounds, incumbent progress, node/
iteration/work counts and phase-specific resources characterize the computation.
Keep build, native solve, extraction, validation, export and allocation times
distinct. A single serial observation per thread level is descriptive; elapsed
time differences alone do not prove a universal ranking or controlled speedup.

The relative scalar gap certifies the penalized total, not service percentage,
zero slack or economic-subtotal accuracy. Preserve the native status and nonzero
gap together; `optimal` means the configured criterion was met. Report original
incumbent/bound, native/common gaps, economic subtotal and each artificial penalty.
Artificial amounts are modelling weights and must not be described as observed
financial losses. Changing weights would change the optimization problem, so
freeze them within the new size/thread comparisons.

## Successful h215 observation

Job2217990: both cold DET/STO arms passed the original independent validator
and the configured1% scalar-gap target. The researcher accepts this as success
under the current contract. DET native Runtime122.514958s/gap0.0008121363%; STO
Runtime2445.517971s/gap0.7401594783%. Service91.8611844%/92.2673837% and penalty
shares96.5917779%/96.9865311% are retained scientific descriptors, not rejection
criteria. Portable review replays original certificates; it does not claim a
fresh private-input residual recomputation. See the [review ledger](evidence/scalar_h215_2217990_review.json).

## Required discussion before each PR is finalized

The [complete scalar h300 block](mvp2_scalar_h300_results.md), job2218193, also
meets the original validators and1% quality targets at unchanged coefficients.
All arms have0.0041193549% scalar gap,91.32562288% service and95.84995396% penalty
share; their primary exported decisions coincide. These positive computational
results are compatible with allowed physical shortage/emergency capacity, not
proof of full service, economic-subtotal accuracy or uniquely optimal decisions.
The one-thread observation is a prospective computational candidate only.

Every subsequent experimental PR includes an explicit discussion of (1) which
feasibility equations allow slack, (2) expected/observed effects on model size
and search, and (3) penalized gap versus economic and physical diagnostics.
Use current-MVP2 evidence only; recovery or citation of earlier work is not
required. For software-only PRs, explain the mechanism and mark measurements
as pending. For evidence PRs, include actual coefficients, quantities, original
validation, quality status and resource scopes. Discussion does not silently
introduce a calibration, service floor, coefficient change or new acceptance rule.
