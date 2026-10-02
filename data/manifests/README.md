# Versioned source manifests

- [mvp_data_contract.json](mvp_data_contract.json) pins the historical source pool
  and canonical workbook, including structural and identity expectations.
- [artur_reproduction_instances.json](artur_reproduction_instances.json) defines
  bounded reconstruction instances; it does not restore the missing historical
  forecasting path or prove equality with thesis tables.
- [warehouse_population_source_v020.json](warehouse_population_source_v020.json)
  records registry provenance for nested population construction.

These are source/data contracts. Experiment selection belongs in
[experiments](../../experiments/README.md); run-specific identities and completion
receipts belong beside generated results. Do not edit a pin simply to make an
incompatible input pass. Record a reviewed data revision and a new experiment.
