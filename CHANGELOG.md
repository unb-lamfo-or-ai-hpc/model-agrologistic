# Changelog

All notable changes to tagged research releases are documented here.

## [Unreleased]

- Freeze the TRL 6 reproducibility protocol and international documentation.

## [0.1.0] - Pending

### Added

- canonical Excel ingestion and model validation;
- deterministic native Gurobi formulation;
- two-stage stochastic extensive form with configurable scenarios;
- warehouse transshipment and optional direct origin-demand routes;
- candidate opening, capacity expansion, and bulkification decisions;
- complete-recourse diagnostics for unmet demand and emergency capacity;
- DynCap, Turnover, EVPI, and VSS metrics and decomposition;
- structured local and Slurm experiment execution;
- controlled Artur benchmark reconstruction and normalization;
- deterministic, three-scenario, and nine-scenario evidence gates;
- repository hygiene and scientific-evidence consolidation.

### Scientific interpretation

- Gate 2B is a bounded reproduction of a controlled Artur instance.
- Gates 2C and 2D are controlled stochastic extensions.
- Emergency capacity is an infrastructure-gap indicator, not a release failure.
- Big-M penalty components are not interpreted as observed monetary costs.

### Known limitations

- the historical OSRM snapshot and forecasting path were not reconstructed;
- only native Gurobi is validated for the TRL 6 demonstrator.
