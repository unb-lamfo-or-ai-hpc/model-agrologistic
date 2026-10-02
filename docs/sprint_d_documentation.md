# Documentation revision after the nine-scenario comparison

## Scientific narrative

The study examines the computational effort needed to obtain validated strategic
grain-logistics decisions under uncertainty as the warehouse network expands.
The contribution is a thesis-inspired, revised mathematical and computational
pipeline: explicit dimensional contracts, road-network provenance, audited sparse
connectivity, hierarchical objectives, native solver implementations and
independent solution validation. HPC execution is part of the experimental
method, not by itself evidence of mathematical novelty or practical optimality.

The comparison is complete for the supplied 13-attempt cohort. It supports a
quality-certified tested population of 300 warehouses for Gurobi, valid but
uncertified incumbents at 400, and no SCIP incumbent in the tested 215/300 cases.
It does not identify either solver's universal maximum. Report the original
300-warehouse unsuccessful Gurobi attempt alongside its successful all-barrier
repeat; preserve the two SCIP memory stops alongside larger-memory timeouts.

## Implemented documentation changes

- The root README distinguishes the later nine-scenario experiment from the
  historical PR25 certificate. The original rejected certificate is not rewritten.
- Root and implementation READMEs describe the implemented native stochastic SCIP
  backend, its qualification and its unsupported operations accurately.
- The documentation catalogue links the final comparison, input reconciliation
  and evidence inventory; the script catalogue distinguishes the final cohort
  generator from the preliminary subset generator.
- The earlier Sprint B/C chronology points to the final cohort and is retained
  as historical evidence rather than a request to rerun jobs.
- Intermediates belong in explicit project-owned directories. Existing virtual
  environments are not moved, and home-directory cleanup remains separate.

No numerical source comments or docstrings are changed in this documentation
increment: those edits change the implementation identity even when semantics
are unchanged. Preserve the original campaign source/runtime for replay.

## Completed Sprint D integration

1. Reconciled the experiment, test and data catalogues with the completed campaign,
   recording which gates establish software qualification, input readiness,
   independent feasibility and hierarchical solution quality.
2. Reviewed reader-facing examples so historical launch commands cannot be mistaken
   for pending execution. Keep original parameter choices and failures available
   in clearly dated protocols; do not rewrite frozen manifests.
3. Added an artifact dictionary covering outputs, units and objective terminology.
   It distinguishes scenario-weighted
   violation quantities from installed capacity, solver internal memory limits
   from process RSS, and configured threads from scheduler CPU allocations.
4. Generated the manuscript comparison directly from frozen machine-readable
   records. Missing evidence and unmatched measurement scopes remain limitations;
   unobserved economic outcomes are not replaced by default zero values.

## Sprint E implementation and editorial handoff

Preserve and refine the introduction and related-work coverage. Update methods,
experimental design, results, discussion and future work using the final table,
stage records and figures. The core question concerns validated solution quality
and computational requirements, not a checklist of development gates.

The implemented pipeline is input preparation -> OSRM/cache -> topology audit
and preflight -> optimization -> independent validation -> scientific reporting.
The present comparison has no learned component and no predictive performance
experiment. An offline-training/online-solver diagram or predictive results must
not be introduced without an actually implemented and evaluated learning module.

Report successful and unsuccessful solves in one cohort, without economic ratios
or speedups against SCIP runs lacking incumbents. Discuss the limitations of one
configured attempt per profile, differing runtime/hardware resources, changing
inherited objective limits and exported-summary rather than full matrix identity.
Larger networks, further algorithmic tuning and Benders decomposition belong to
future experiments; they are not demonstrated benefits. Dataset publication
remains subject to curation, source rights and an explicit release decision.

The revised English manuscript preserves the seven authors, the substantive
introduction, 35 cited references and deterministic/two-stage formulations.
Methods and results now contain the thirteen-attempt comparison, per-stage gaps
and times, conditional costs, resource settings and a diagram of the implemented
pipeline. Historical reference results remain in a separate Markdown supplement.

`scripts/build_manuscript_comparison.py --check` verifies the committed tables
and figure identities against the frozen comparison. Quarto renders HTML/PDF
without executing optimization. `scripts/package_manuscript.py` creates a
portable LaTeX project with bibliography, figures, rights notices and checksums;
it refuses to overwrite an existing review ZIP.

Remaining decisions are editorial: coauthor review, venue selection, formatting,
rights and release authorization. Implementation completion does not imply
journal submission, public deployment or acceptance of the historical rejected
validation certificate. No new NPAD campaign is required for this increment.

## Deferred NPAD housekeeping

No files are moved or deleted in this increment. A later read-only inventory
must distinguish active checkouts, environments, canonical inputs, accepted and
unsuccessful evidence, caches and superseded staging files. Preserve virtual
environments in place. Plan compression only for identified superseded material,
with hashes and an index; verify space for the archive before any operation.
Keep evidence paths traceable and obtain a reviewed target list before moving
material into a small number of project-owned archive or quarantine directories.
