# Canonical workbook

`model_agrologistic_padrao_ouro.xlsx` is the canonical expanded-network source,
not the historical generated thesis instance or an OSRM-materialized runtime
workbook. Its identity is recorded in
[the data contract](../manifests/mvp_data_contract.json).

The loader preserves the Portuguese sheet/column schema for compatibility.
See `REQUIRED_SHEETS` and `REQUIRED_COLUMNS` in
[excel_loader.py](../../src/logic/excel_loader.py) for the executable contract.
Do not translate identifiers while translating documentation.

Formula caches may be absent outside Excel. Only documented parameter-derived
fallbacks are allowed; missing investment costs are not automatically zero.
Keep derived solver workbooks under a new processed-data directory with an audit
and hash. Never overwrite this baseline during a solve or a plotting operation.
