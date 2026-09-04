# Artur benchmark reproduction protocol

## Purpose

This protocol separates scientific reproduction from model extension. It uses
the historical SiloDSS benchmark as the reference track and the gold workbook
as the current MVP track. The first track asks whether the thesis cases can be
reconstructed under documented historical assumptions. The second asks whether
the extended model remains useful and robust with a richer network and explicit
model parameters.

The two tracks share source data, but they are not numerically interchangeable.

## Immutable source contract

The historical source is pinned to SiloDSS commit
`9d190ce91bb60c192329c4bbd5638f24909cb1e2`. The contract records the exact Git
blob SHA and byte size for every benchmark file. It also pins three dependencies
that are outside the historical `benchmark/` directory but are required by the
generator:

- `scripts/benchmark_model.py`;
- `src/view/assets/data/municipios.csv`;
- `src/view/assets/data/estados.csv`.

The acquisition command downloads files from the immutable commit and rejects
any file whose bytes do not match the contract:

```bash
python scripts/reconcile_artur_benchmark.py --fetch
```

Subsequent offline verification omits `--fetch`:

```bash
python scripts/reconcile_artur_benchmark.py
```

The first named benchmark iteration can then be generated and persisted:

```bash
python scripts/build_artur_instance.py --name artur_legacy_i001
```

The default cache is `data/raw/artur_benchmark/<commit>/`. The generated JSON
and CSV reports are written to `data/results/reproducibility/`. Raw and result
artifacts are local evidence and should not be treated as source code.

## Established data lineage

The executable reconciliation establishes the following relationship between
the pinned source pool and `model_agrologistic_padrao_ouro.xlsx`:

| Dataset | Artur source pool | Gold workbook | Relationship |
|---|---:|---:|---|
| Supply rows | 6,300 | 6,300 | Preserved |
| Supply nodes | 37 | 37 | Preserved |
| Supply total (t) | 1,374,420,353.085 | 1,374,420,353.085 | Preserved |
| Demand rows | 4,440 | 4,440 | Preserved |
| Domestic nodes | 27 | 27 | Preserved |
| Export nodes | 10 | 10 | Preserved |
| Domestic demand (t) | 677,712,425.652 | 677,712,425.652 | Preserved |
| Warehouses | 141 | 215 | Extended by 74 |
| Existing warehouses | 90 | 146 | Extended by 56 |
| Candidate warehouses | 51 | 69 | Extended by 18 |

The supply records are identical row by row. Demand keys and every finite
domestic value are also identical. The historical 1,200 export-demand cells
containing `∞` are represented in the gold workbook by 1,200 explicit export
rows with a machine-readable upper-bound rule. This is a schema transformation,
not a change in the intended non-binding export-market assumption.

All 141 historical warehouse identifiers remain in the gold workbook. The
additional 74 warehouses and the explicit expansion, bulkification, emergency,
and candidate-cost parameters make gold-workbook runs an extension and
robustness test rather than a direct numerical replica.

## Why reproduction is currently bounded

The historical benchmark starts with a small sampled instance and increases
its size until solve time reaches 600 seconds. It then writes `last_*` files for
the terminal instance. Those generated files are not available at the pinned
commit, so the exact terminal instance used for a thesis result cannot be
identified from the source pool alone.

The generator fixes Python and NumPy seed 42 and uses recorded sampling states
42, 43, and 44. It also applies an optional supply-to-demand feasibility factor
of 1.5. These controls are now recorded in the contract. However, route distances
were obtained dynamically from OSRM and no versioned distance matrix is present.
OSRM data and routing-engine versions can change distances even when sampled
nodes are identical.

Accordingly, the present evidence supports a bounded reconstruction of data,
rules, and instance families. It does not support a claim of exact numerical
replication of the thesis.

## Sprint 2 validation gates

### Gate 2A: source and lineage integrity

- Verify all pinned files by Git blob identity.
- Produce the structural reconciliation report.
- Confirm the preserved supply and domestic-demand lineage.
- Record the warehouse and schema extensions explicitly.

### Gate 2B: controlled deterministic reconstruction

- Recreate named benchmark sizes from the pinned generator rules.
- Persist each generated instance before solving it.
- Replace dynamic routing with a versioned distance matrix or record the exact
  routing service and response cache.
- Compare feasibility, objective components, decisions, DynCap, Turnover,
  service, runtime, and memory with the available thesis evidence.

The versioned `artur_legacy_i001` specification reproduces the historical
request for 5 supply nodes, 5 domestic-demand nodes, 1 export node, and 20
warehouses. It persists the sampled supply, demand, warehouse, and distance
tables as CSV files and records a SHA-256 digest for each table. Distances use a
frozen Haversine definition at this gate and are explicitly marked as not
equivalent to the historical OSRM distances.

#### Initial-instance semantic audit

Faithful execution of the pinned sampling rules exposed historical input
ambiguities that must be resolved before solving:

- the five sampled supply cities produce 1,020 rows, including 300 duplicated
  product-city-period key groups and 900 rows participating in duplicates;
- the legacy demand pool mixes finite domestic demand with unbounded export
  rows; the five requested domestic nodes therefore realize only three finite
  domestic nodes and two unbounded export nodes;
- the separately generated Santos export node overlaps a sampled legacy node,
  producing 120 duplicated demand key groups and 240 rows participating in
  duplicates;
- the historical forecasting path has not yet been reconstructed.

The raw sampled tables are retained as evidence. They must not be passed to the
current solver through an implicit last-write-wins mapping. The next gate must
choose and document one normalization policy:

1. preserve legacy rows only for forensic reconstruction;
2. aggregate duplicate supply keys, classify demand by finite or unbounded
   value, and deduplicate export keys for the bounded-reproduction model;
3. resample domestic nodes from finite rows only, which is a corrected model
   extension rather than reproduction of the historical sampler.

Policy 2 is the recommended primary bounded-reproduction path. Policies 1 and
3 remain useful sensitivity references. All policies must retain the raw bundle
hashes and publish a transformation audit.

### Gate 2C: stochastic extension

- Apply the documented three- and nine-scenario structures to a persisted Gate
  2B instance.
- Run the penalty objective for scalar RP, WS, EV, EEV, EVPI, and VSS values.
- Run the lexicographic policy only as a separate service-policy sensitivity
  analysis because its multiobjective value is not monetarily comparable with
  EVPI or VSS.
- Report gold-workbook results as extensions and robustness tests.

## Acceptance rule

A run may be called an exact replication only if its generated input tables,
distance matrix, transformations, solver configuration, and comparison target
are all versioned and identical to the historical case. Otherwise it must be
labelled either a bounded reproduction or a model extension.

