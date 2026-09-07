# Model Agrologistic

Research software for deterministic and two-stage stochastic planning of
agricultural logistics networks.

The project provides a headless mixed-integer linear programming core for
evaluating long-horizon warehouse opening, capacity expansion, bulkification,
storage, domestic distribution, transshipment, direct transport, and export
decisions. Native `gurobipy` is the validated solver backend.

## Research status

Version `0.1.0` is the TRL 6 research demonstrator candidate. It has been
demonstrated on a Slurm-based HPC environment with controlled deterministic,
three-scenario, and nine-scenario experiments. TRL 6 is used here as a research
readiness claim supported by execution in a relevant computational environment;
it is not an independent certification or a production-readiness claim.

The code originated from the SiloDSS project and was refactored into a testable,
interface-independent optimization pipeline:

```text
Excel workbook
  -> canonical ModelData
  -> model validation
  -> route selection
  -> deterministic or stochastic MILP
  -> structured results
  -> DynCap, Turnover, EVPI, and VSS evidence
```

## Implemented scope

- deterministic and two-stage stochastic MILP formulations;
- one to nine configurable supply-demand scenarios;
- existing and candidate warehouses;
- opening, scalable candidate capacity, expansion, and bulkification decisions;
- origin-warehouse, warehouse-demand, warehouse-warehouse, and optional direct routes;
- period-specific inventory balance and terminal inventory;
- domestic and export demand classes;
- daily reception and shipping rates converted through `days_per_period`;
- unmet-demand and emergency-capacity slack for complete recourse;
- structured JSON and CSV outputs, model audits, IIS diagnostics, and HPC preflight;
- dynamic capacity (`DynCap`) and inventory turnover (`Turnover`);
- recourse problem, wait-and-see, expected-value, EEV, EVPI, and VSS calculations;
- reproducibility gates for the controlled Artur benchmark instance.

## Scientific policy

The frozen demonstrator follows four policies that are central to interpreting
its results:

1. Domestic demand is expected to be fully served in the accepted controlled
   experiments.
2. Every tonne of supply must be allocated to domestic demand, export flow, or
   terminal inventory.
3. Emergency static and reception capacity are feasibility-preserving slack
   variables. Their use is reported as an infrastructure-gap indicator and is
   not an automatic rejection criterion.
4. Big-M penalty values are not observed shortage prices. Monetary conclusions
   about VSS must therefore use the exported investment, operating, and penalty
   decomposition.

See [Service-level methodology](docs/service_level_methodology.md) and
[Methodological audit](docs/methodological_audit.md) for the full rationale.

## Data contract and lineage

The canonical input schema is:

```text
data/templates/model_agrologistic_padrao_ouro.xlsx
```

The workbook uses Portuguese sheet and column identifiers because those names
are part of the stable data contract. Documentation and source-code comments are
written in English.

Required deterministic sheets include:

```text
Oferta
Demanda
Warehouses
Frete
Tarifa_Armz
Custo_Invest
Parametros_Modelo
```

Stochastic inputs use:

```text
Cenarios
Oferta_Cenarios
Demanda_Cenarios
```

Export demand is represented by an explicit rule instead of an infinity token:

```text
Tipo_Demanda = EXPORTACAO
Regra_Limite = AUTO_OFERTA_TOTAL_PRODUTO_PERIODO
```

The frozen workbook identity, upstream Artur assets, and transformation rules
are recorded in `data/manifests/`. See
[MVP scope and data contract](docs/mvp_scope_and_data_contract.md) and
[Artur reproduction protocol](docs/artur_reproduction_protocol.md).

## Requirements

- Python 3.13;
- a platform supported by the declared Python packages;
- Gurobi 13 for validated optimization runs;
- a valid Gurobi license for model solution;
- Slurm only when using the supplied HPC submission script.

The complete dependency declaration is maintained in `pyproject.toml`.

Install the validated core and development tools:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Install every declared optional research dependency:

```bash
python -m pip install -e ".[all]"
```

`Pyomo` and native `PySCIPOpt` are optional post-MVP research dependencies.
They are not validated alternatives to the Gurobi backend in version `0.1.0`.
CBC is not a target backend.

### NPAD environment

The established NPAD environment is a Conda prefix despite its `venv313` name:

```bash
conda activate /home/vrrcelestino/venv313
```

Slurm jobs may invoke its interpreter directly and do not require interactive
activation. Set a different interpreter when needed:

```bash
export AGROLOGISTIC_PYTHON=/path/to/python
```

## Gurobi license

Configure a license without committing credentials:

```bash
export GRB_LICENSE_FILE=/absolute/path/to/gurobi.lic
```

WLS access IDs, secrets, license files, and credential values must never be
stored in manifests, logs, environment snapshots, or release artifacts.

## Quality checks

```bash
python -m ruff check .
python -m pytest
```

Tests that require an operational Gurobi environment are skipped when a license
is unavailable. The final licensed validation is performed on NPAD.

## TRL 6 reproducibility protocol

Inspect the ordered protocol without executing it:

```bash
python scripts/run_trl6_protocol.py --print-plan
```

Run quality checks, rebuild the controlled Artur input, and execute every
preflight without solving the models:

```bash
python scripts/run_trl6_protocol.py --fetch-artur-assets
```

Run the complete licensed protocol in a clean checkout:

```bash
python scripts/run_trl6_protocol.py \
  --fetch-artur-assets \
  --execute-solver
```

The default release output is isolated under:

```text
data/results/releases/trl6-v0.1.0/
```

Use a new `--output-dir` for every candidate run. Existing result directories
are not silently deleted or treated as evidence for a rebuilt workbook. The
protocol exports an environment snapshot, step manifest, scientific evidence,
and `SHA256SUMS` without copying Gurobi credentials.

See [TRL 6 reproducibility protocol](docs/trl6_reproducibility_protocol.md).

## HPC execution

Run one experiment interactively:

```bash
python scripts/run_batch_hpc.py experiments/artur_stochastic_extension.yaml --index 0
```

Submit through Slurm:

```bash
EXPERIMENT_MANIFEST=experiments/artur_stochastic_extension.yaml \
EXPERIMENT_INDEX=0 \
sbatch scripts/run_model_agrologistic.slurm
```

The supplied Slurm script defaults to `intel-128`, 16 CPUs, and 64 GiB. Adjust
resource requests to the selected manifest and cluster policy.

## Repository structure

```text
data/manifests/     frozen data identities and instance specifications
data/templates/     canonical Excel input schema
docs/               scientific and execution documentation
experiments/        versioned deterministic and stochastic manifests
scripts/            data preparation, execution, audit, and release commands
src/logic/          canonical data, formulations, metrics, and evidence logic
tests/              solver-independent and licensed integration tests
```

Raw source assets, generated instances, solver outputs, and large HPC artifacts
remain outside version control. The repository hygiene policy classifies them as
pipeline-required, protected, scientific archive, or safe-generated artifacts.

## Known limitations

- the historical OSRM snapshot used in the thesis was not recovered;
- the original forecasting path was not reconstructed;
- the three- and nine-scenario designs are controlled extensions, not recovered
  historical forecasts;
- Big-M penalty components are feasibility devices, not observed monetary costs;
- only the native Gurobi backend is validated for the TRL 6 demonstrator;
- the software is a research prototype and not an operational public-sector system.

These limitations preserve the distinction between bounded reproduction,
controlled extension, and direct numerical replication.

## Citation and license

Use the metadata in `CITATION.cff` when citing a tagged release. Release assets
record the exact source commit and checksums used for the reported results.

The source code is licensed under the GNU General Public License v3.0. See
`LICENSE`. Dataset provenance and third-party terms remain attached to their
respective source records and are not replaced by the software license.
