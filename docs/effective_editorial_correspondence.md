# Scientific correspondence and future editorial integration

The author-reviewed article/supplements and Draft PR156 are unchanged. This
matrix prepares later author review; it is not an editorial patch or a statement
that prospective sensitivities have been executed.

| Component/evidence | Article destination | Supplement destination | Current status |
| --- | --- | --- | --- |
| Original/effective/experimental layers | Methods: effective inputs | D: data lineage | Implemented data boundary; technical documentation |
| Derived gold/registry XLSX | Methods: concise reproducibility description | D: units, maps, membership and source identities | Local inspection artifacts; not deposited |
| Frozen normalized OSRM graph | Methods: network construction | D: distances versus selected arcs versus positive flows | Existing distances and policies preserved |
| CSV reader and same Pyomo builder | Methods: implementation | C: interfaces, provenance and verification | New ingestion, unchanged algebra helpers |
| Explicit parameter transformations | Methods: experimental design | C/D: equations, units and audit records | Neutral interface; levels not approved |
| h215 data/algebra equivalence | Methods: validation | C: construction-equivalence evidence | Report actual qualification scope; no new solve |
| beta/alpha restrictions | Methods after approval | C: exact constraints and validator | Proposed scopes; disabled in executable interface |
| Cost/service outcomes | Results after accepted execution | Numerical tables and E maps where justified | No new results generated |
| Economic calibration hypotheses | Discussion/future work after review | D: alternative parameter sources | Hypotheses; no replacement of baseline |
| New deposit contents | Data availability only after approval/deposit | F: availability/provenance | No dataset publication authorized |

## Proposed writing sequence

1. After technical qualification, propose a short Methods paragraph explaining
   explicit effective inputs, fixed topology and independent parameter changes.
2. Supply AppendixC/D implementation and provenance detail for author review.
3. Add approved beta/alpha definitions only after their scientific decision.
4. Integrate Results/Discussion only after accepted experiments and reconciliation.
5. Add geographic analyses only when accepted decisions/flows support them.

Preserve the research question, contributions, author-reviewed wording and
AppendixA. Implementation is not experimental evidence. A planned package is
not an available Zenodo deposit. No numerical claim is inferred from this PR.
