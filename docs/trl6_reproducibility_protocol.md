# TRL 6 Reproducibility Protocol

> Historical development record. Results and commands below refer to their named
> earlier campaigns, not automatic v0.2 acceptance. Use the
> [current mathematical contract](v020_mathematical_contract.md),
> [validation report](v020_validation_report.md) and
> [results interpretation](results_interpretation.md) for current claims.
> In particular, old objective ordering, slack-unit labels and complete-recourse
> language must not be transferred to new evidence without checking the contract.

## Purpose

This protocol freezes the version 0.1.0 research demonstrator and produces an
auditable evidence bundle from a clean source revision. It is designed for the
NPAD Slurm environment with native Gurobi and can run its solver-independent
phases on another Python 3.13 environment.

The protocol demonstrates the software in a relevant computational environment.
It does not certify production readiness or claim exact reconstruction of every
historical input used in Artur's thesis.

## Frozen scientific contract

Version 0.1.0 does not introduce new model semantics. It preserves:

- full domestic-demand service as an acceptance condition for the controlled gates;
- full allocation of supply to domestic demand, export, or terminal inventory;
- complete recourse through explicitly reported emergency-capacity slack;
- separate observed economic and non-observed Big-M penalty components;
- deterministic Gate 2B as bounded reproduction;
- Gates 2C and 2D as controlled stochastic extensions;
- Gurobi as the only validated solver backend.

Emergency capacity does not reject a run. It identifies where the optimized
investment envelope is insufficient. Unmet domestic demand, invalid material
balance, incompatible provenance, and rejected scientific evidence are blocking.

## Protocol phases

The command `scripts/run_trl6_protocol.py` builds a fixed ordered plan:

1. quality: Ruff and the complete Pytest suite;
2. data: pinned-asset reconciliation and isolated Artur-instance construction;
3. preflight: Gate 2B and all four stochastic experiment specifications;
4. solve: deterministic, three-scenario RP/EVPI-VSS, and nine-scenario RP/EVPI-VSS;
5. evidence: audits, aggregation, scientific consolidation, and checksums.

The script stops after the first failed command and records the partial outcome.

## Candidate execution

Start from a clean checkout of the candidate branch:

```bash
git status --short --branch
export PYTHONNOUSERSITE=1
export PYTHONDONTWRITEBYTECODE=1
python scripts/run_trl6_protocol.py \
  --output-dir data/results/releases/trl6-v0.1.0-candidate \
  --fetch-artur-assets \
  --execute-solver
```

Never reuse an output directory from a different workbook or source commit. The
script deliberately builds the controlled instance beneath the selected release
directory and overrides the manifest workbook path for that run.

### Slurm nodes without Git

Some compute-node images do not expose the `git` executable. Verify the source
revision and clean tree on the submission node, then export the evidence to the
job:

```bash
export AGROLOGISTIC_SOURCE_COMMIT="$(git rev-parse HEAD)"
test -z "$(git status --porcelain)"
export AGROLOGISTIC_SOURCE_IS_CLEAN=1
```

The protocol records `source_provenance_method = scheduler_environment` in this
case. If either value is absent or invalid, provenance is not accepted; a
missing Git executable is never interpreted as evidence of a clean tree.

Repository-hygiene integration tests that create temporary Git repositories
are skipped when the compute-node image has no Git executable. They must pass
on GitHub Actions for the exact candidate commit; all solver-independent tests
that do not require Git continue to run on the compute node.

## Acceptance evidence

Inspect at minimum:

```text
environment.json
protocol_manifest.json
SHA256SUMS
evidence/mvp_evidence_manifest.json
evidence/mvp_acceptance_checks.csv
evidence/mvp_gate_summary.csv
evidence/mvp_gate_comparison.csv
evidence/mvp_evpi_vss_decomposition.csv
evidence/mvp_investment_decisions.csv
evidence/mvp_investment_changes.csv
```

The accepted candidate must have:

- `protocol_manifest.overall_status = accepted`;
- a non-empty source commit and a clean source tree;
- no failed protocol steps;
- `mvp_evidence_manifest.overall_status = accepted`;
- domestic service equal to 1 within the declared tolerance;
- zero unmet domestic demand within tolerance;
- valid material balance;
- non-negative EVPI and VSS within tolerance;
- complete capacity-gap and investment reporting.

A solver-free execution ends with `overall_status = preflight_passed`. This is
a successful structural check, but it is not sufficient to accept or tag the
TRL 6 release candidate.

## Release sequence

1. Validate the final pull-request head on NPAD.
2. Merge the release branch into `develop`.
3. Merge `develop` into `main` through a release pull request.
4. Check out the exact resulting `main` commit on NPAD.
5. Repeat the complete protocol in a new output directory.
6. Create tag `v0.1.0` only if the final run is accepted.
7. Publish the evidence archive and `SHA256SUMS` as GitHub Release assets.

The tag must identify the validated `main` commit, not the feature branch or an
earlier candidate commit.

## Reproducibility boundary

Reproducibility means that a clean checkout can rebuild the controlled input,
execute the same mathematical configurations, and reproduce scientific outcomes
within declared numerical tolerances. Solver logs, timestamps, runtimes, memory
measurements, and floating-point tails are not expected to be byte-identical.

The release must continue to disclose that historical OSRM evidence and the
original forecasting path were not reconstructed. Consequently, the stochastic
results are extensions and robustness tests rather than direct numerical
validation of the thesis results.
