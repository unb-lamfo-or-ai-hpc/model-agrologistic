# Data lineage and artifact boundaries

## License and redistribution

Original project-authored metadata is covered by the root MIT License.
Inputs, source workbooks and derived road databases are not automatically
MIT-licensed. Preserve source attribution and redistribution restrictions.
See [licensing boundaries](../LICENSING.md). Frozen evidence and source hashes
must not change as a consequence of license documentation updates.

Data are part of the experiment, not interchangeable inputs. The
[frozen source contract](manifests/mvp_data_contract.json) distinguishes historical
benchmark assets from the canonical expanded workbook. Preserve these identities
through normalization, scenario construction and road-distance materialization.

| Location | Role | Repository policy |
|---|---|---|
| [manifests](manifests/README.md) | Source pins, schema and population contracts | Version controlled |
| [templates](templates/README.md) | Canonical input workbook | Version controlled; preserve baseline |
| `raw/` | Acquired source assets and registry copies | Local, ignored; verify source rights and hashes |
| `processed/` | Normalized instances and OSRM solver workbooks | Generated, ignored; retain transformation audits |
| `results/` | Runs, validation receipts and presentation outputs | Generated, ignored; archive successful and unsuccessful evidence |
| `osrm/` | Optional local routing artifacts | Ignored; use approved storage and quota limits |

Acquisition does not prove equivalence with a published generated instance.
For Artur's source pool, verify the pinned assets before sampling or normalizing
duplicate keys. Supply and finite domestic-demand totals must remain traceable.

The 215-warehouse anchor contains 146 existing and 69 candidate facilities.
Additional registry candidates are investment opportunities, not already usable
capacity. Their base static/reception/shipping capacities are zero; activation,
maximum capacity and canonical investment costs govern their use. Duplicate
coordinates need not mean duplicate facilities. Coordinate-pair cache counts
therefore differ from logical route counts.

OSRM output workbooks have new identities: never substitute a regenerated XLSX
under a historical run while retaining its old provenance. A cache preserves
ordered coordinate pairs and routing semantics; it is not the scientific result
or a guarantee that every possible route will be allowed by the MILP.

Use [repository hygiene](../docs/repository_hygiene.md) for reversible quarantine.
Do not delete source data, accepted releases, active-run outputs or checkpoints
needed by the selected pipeline. Compressed files still consume storage quota.

The [final comparison evidence](../docs/evidence/sprint_c_final_20260920/comparison_summary.md)
is a curated exported-record collection, not a replacement for source workbooks
or full solution archives. Source hashes, output hashes and run identities have
different roles; a matching reported workbook hash does not verify absent bytes.
The [artifact dictionary](../docs/artifact_dictionary.md) specifies these boundaries.

Keep new intermediate material in named project-owned subdirectories. Existing
virtual environments remain in place. Any later home-directory consolidation
starts with a read-only inventory and active-reference check. Failed solver
attempts remain scientific evidence; obsolete launch copies may be compressed
only after their provenance and replacement are identified. No automatic move,
deletion, environment relocation or Zenodo publication is implied by this policy.
