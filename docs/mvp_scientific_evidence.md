# MVP scientific evidence package

## Purpose

This stage consolidates the accepted Artur experiments into one traceable
evidence package for the research MVP. It does not solve the optimization model
again. It reads completed structured artifacts and produces comparable tables,
acceptance checks, a methodological report, and a provenance manifest.

The scientific hierarchy is explicit:

1. Gate 2B is a bounded deterministic reproduction based on the normalized
   Artur instance.
2. Gate 2C is a controlled three-scenario stochastic extension.
3. Gate 2D is a controlled nine-scenario full-factorial extension.

Gates 2C and 2D test model robustness. They are not direct numerical
validations of the thesis forecasting process because the original fitted
distributions, sampled realizations, scenario-reduction path, and empirical
probabilities have not been reconstructed.

## Evidence contract

Run the consolidation only after all three accepted experiment directories are
available on the same checkout:

```bash
export PYTHONNOUSERSITE=1
export PYTHONDONTWRITEBYTECODE=1

python scripts/build_mvp_scientific_evidence.py
```

The default output directory is:

```text
data/results/reproducibility/mvp_scientific_evidence
```

The command writes:

- `mvp_gate_summary.csv`: one comparable record per gate;
- `mvp_gate_comparison.csv`: absolute and relative changes between consecutive
  gates;
- `mvp_acceptance_checks.csv`: physical and mathematical acceptance checks;
- `mvp_evpi_vss_decomposition.csv`: long-form RP, WS, EV, EEV, EVPI, VSS, and
  physical-recourse decomposition;
- `mvp_evidence_provenance.csv`: SHA-256 hashes for every available source
  artifact;
- `mvp_scientific_evidence.md`: a generated, human-readable summary;
- `mvp_evidence_manifest.json`: schema, interpretation contract, gate order,
  acceptance status, and output hashes.

The current exporter stores the EVPI/VSS payload under
`stochastic_performance` in each run's `result.json`. A separate
`evpi_vss.json` file is not required by this evidence contract.

## Acceptance policy

A stochastic gate is accepted when:

- the solver status is optimal;
- the declared scenario count is present;
- domestic service is at least `1 - tolerance`;
- unmet domestic demand is within tolerance;
- material balance is explicitly reported as valid;
- scenario probabilities exist and sum to one;
- EVPI and VSS are non-negative within tolerance.

Emergency capacity is deliberately not a rejection criterion. It preserves
complete recourse and quantifies the capacity gap that remains after admissible
first-stage investments. This is a strategic model output for public investment
planning.

Gate 2B predates some consolidated physical diagnostics. A missing
`material_balance_ok` field is therefore a warning for the deterministic gate,
not a blocking failure. Re-running Gate 2B with the current exporter removes
that warning and strengthens provenance.

## Cost and value-of-information interpretation

The evidence package separates three cost groups:

- investment costs;
- operating costs;
- non-observed Big-M penalty costs.

The first two groups are modeled economic quantities. The penalty group is a
feasibility device for unmet demand and emergency capacity; it is not an
observed market cost. Consequently, a penalty-dominated VSS is evidence that
the expected-value plan under-provisions capacity, but its total magnitude
cannot be presented as a literal monetary saving.

For this minimization model:

```text
EVPI = RP - WS
VSS  = EEV - RP
```

The decomposition uses the same sign conventions. Negative investment or
operation components may offset a positive penalty component, so an individual
component may exceed 100% of the net VSS without implying an inconsistency.

## Validated Gate 2D interpretation

The accepted nine-scenario run satisfies all domestic demand and material
balance conditions. It requires emergency reception capacity but no emergency
static capacity and no unmet-demand slack. Its VSS is dominated by the extra
emergency reception required by the expected-value investment plan.

The similarity between the three- and nine-scenario results is evidence that
the strategic conclusion is stable when the original three negatively
correlated states are expanded to the complete supply-demand Cartesian product.
This statement remains conditional on the synthetic multipliers and equal
experimental probabilities.

## NPAD validation

Validate the implementation before generating the evidence package:

```bash
python -m pytest tests/test_scientific_evidence.py
python -m pytest
python scripts/build_mvp_scientific_evidence.py
```

Inspect the acceptance result and the main tables:

```bash
python - <<'PY'
import json
from pathlib import Path

root = Path("data/results/reproducibility/mvp_scientific_evidence")
manifest = json.loads((root / "mvp_evidence_manifest.json").read_text())
print(json.dumps({
    "overall_status": manifest["overall_status"],
    "blocking_failure_count": manifest["blocking_failure_count"],
    "gate_order": manifest["gate_order"],
}, indent=2))
PY

cat data/results/reproducibility/mvp_scientific_evidence/mvp_gate_summary.csv
cat data/results/reproducibility/mvp_scientific_evidence/mvp_gate_comparison.csv
cat data/results/reproducibility/mvp_scientific_evidence/mvp_acceptance_checks.csv
```

Generated evidence remains an HPC artifact and should not be committed unless a
later publication snapshot explicitly freezes it with its provenance manifest.

