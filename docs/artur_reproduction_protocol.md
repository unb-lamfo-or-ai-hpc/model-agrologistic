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

The recommended policy is implemented as `bounded_reproduction_v1`. It first
verifies the SHA-256 and size of every raw instance table, then writes normalized
tables to a separate `normalized/` directory:

```bash
python scripts/normalize_artur_instance.py --name artur_legacy_i001
```

For the pinned initial instance, normalization produced the following audit:

| Dataset metric | Before | After | Interpretation |
|---|---:|---:|---|
| Supply rows | 1,020 | 420 | Duplicate keys aggregated |
| Supply duplicate key groups | 300 | 0 | Resolved |
| Supply total (t) | 151,325,494.505 | 151,325,494.505 | Conserved |
| Demand rows | 720 | 600 | Duplicate export keys removed |
| Demand duplicate typed-key groups | 120 | 0 | Resolved |
| Finite domestic demand (t) | 35,956,500.397 | 35,956,500.397 | Conserved |
| Unbounded export rows | 360 | 240 | One row retained per key |
| Warehouse rows | 20 | 20 | Preserved |
| Distance rows | 580 | 580 | Preserved |

The normalized demand explicitly labels finite rows as `DOMESTICA/FIXO` and
unbounded rows as `EXPORTACAO/AUTO_OFERTA_TOTAL_PRODUTO_PERIODO`. If a key has
both meanings, both typed rows are preserved. Conflicting coordinates cause a
hard failure rather than an arbitrary first-value selection.

After normalization, the remaining barriers to historical numerical comparison
are the Haversine-versus-OSRM distance difference and the unreconstructed
forecasting path. The normalized bundle is suitable for the next model-adapter
gate, but it is not yet an exact thesis instance.

#### Canonical solver adapter

The normalized tables can be converted into a solver workbook without changing
the raw or normalized evidence:

```bash
python scripts/build_artur_solver_workbook.py --name artur_legacy_i001
```

The command writes `solver/model_input.xlsx` and `solver/adapter_audit.json`
beside the instance. It verifies every normalized-table hash and every pinned
reference asset before adapting the schema. The workbook contains the frozen
Haversine distances in a long-form `Distancias` sheet; the experiment loader is
configured to read these values and is forbidden from recomputing them.

The adapter uses the pinned historical freight, storage, transshipment, and
investment reference tables. It translates only field names and status labels,
sets candidate opening cost to the historical fixed-total interpretation, and
records the benchmark expansion and bulkification assumptions explicitly. The
following semantic differences remain material:

- the frozen Haversine matrix is not the historical OSRM matrix;
- the historical forecasting path is not reconstructed;
- the current model's capacity coupling is not identical to the historical
  reception and shipping expansion ratio;
- the controlled pilot uses Gurobi with a 600-second limit. The historical
  benchmark configuration used CBC with a 1,800-second limit, but that fact is
  retained only as provenance and CBC is not reproduced or used in this project.

All current reproduction and extension results use Gurobi. A native PySCIPOpt
implementation may later provide independent backend validation, but it is
outside this gate and outside the frozen TRL 6 MVP.

Consequently, the resulting solve is a bounded reproduction of the initial
instance, not an exact numerical replication. It is useful for validating the
data lineage, feasibility, cost decomposition, decisions, service, DynCap,
Turnover, runtime, and memory under a controlled current-model interpretation.

The deterministic experiment is versioned in
`experiments/artur_bounded_reproduction.yaml`. Run its preflight first:

```bash
python scripts/run_batch_hpc.py \
  experiments/artur_bounded_reproduction.yaml \
  --index 0 \
  --dry-run
```

If the preflight signature agrees with the adapter audit, run the bounded solve:

```bash
python scripts/run_batch_hpc.py \
  experiments/artur_bounded_reproduction.yaml \
  --index 0
```

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

