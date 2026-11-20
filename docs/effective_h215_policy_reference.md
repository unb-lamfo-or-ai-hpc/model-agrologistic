# Historical h215 W service and export by product/scenario

This readback preceded optional-policy implementation. It uses three separate accepted
references: native DET, native STO and Pyomo STO. Original vector/member hashes and
accepted independent certificates were checked. No optimization was performed.

The [full CSV](evidence/h215_policy_reference_20261118.csv) contains all 38 rows,
tonnes, shortage penalties, probabilities and domestic/national balance residuals.
The [JSON receipt](evidence/h215_policy_reference_20261118.json) binds inputs and sources.
Only national aggregates are versioned; facility-level flow vectors remain in custody.

## Main diagnostic

The aggregate service reference near 92% masks full maize service and substantially
lower soybean service. The approved common beta/alpha contrasts mainly constrain
soybean in these retained incumbents. This does not predict how a new constrained
optimum or time-limited incumbent would respond.

| Reference | Product | Rows | Service range (%) | Export/supply range (%) | beta .90 met | beta .95 met | alpha .60 met | alpha .50 met |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| historical_native DET | Milho | 1 | 100.00000–100.00000 | 34.96672–34.96672 | 1/1 | 1/1 | 1/1 | 1/1 |
| historical_native DET | Soja | 1 | 80.14195–80.14195 | 70.51108–70.51108 | 0/1 | 0/1 | 0/1 | 0/1 |
| historical_native STO | Milho | 9 | 100.00000–100.00000 | 19.94330–46.10966 | 9/9 | 9/9 | 9/9 | 9/9 |
| historical_native STO | Soja | 9 | 73.28186–90.13119 | 66.69067–72.60320 | 1/9 | 0/9 | 0/9 | 0/9 |
| historical_pyomo STO | Milho | 9 | 100.00000–100.00000 | 19.94330–46.10966 | 9/9 | 9/9 | 9/9 | 9/9 |
| historical_pyomo STO | Soja | 9 | 73.28186–90.13119 | 66.69067–72.60320 | 1/9 | 0/9 | 0/9 | 0/9 |

Counts are retrospective checks of the retained vectors, not acceptance of a
new experiment. Ratios have no probability weighting within a scenario. The
display rounds values; CSV/JSON retain binary64 round-trip values.

## scalar_h215_det

| Product | Scenario | Demand (Mt) | Delivered (Mt) | Shortage (Mt) | Service (%) | Supply (Mt) | Export (Mt) | Export/supply (%) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Milho | deterministic | 399.952226 | 399.952226 | 0.000000 | 100.00000 | 619.552308 | 216.637108 | 34.96672 |
| Soja | deterministic | 277.760200 | 222.602435 | 55.157765 | 80.14195 | 754.868045 | 532.265609 | 70.51108 |

## scalar_h215_sto

| Product | Scenario | Demand (Mt) | Delivered (Mt) | Shortage (Mt) | Service (%) | Supply (Mt) | Export (Mt) | Export/supply (%) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Milho | oferta_baixo__demanda_baixo | 379.954614 | 379.954614 | 0.000000 | 100.00000 | 526.619462 | 144.812937 | 27.49859 |
| Soja | oferta_baixo__demanda_baixo | 263.872190 | 198.662559 | 65.209631 | 75.28742 | 641.637838 | 442.975279 | 69.03821 |
| Milho | oferta_baixo__demanda_base | 399.952226 | 399.952226 | 0.000000 | 100.00000 | 526.619462 | 124.873662 | 23.71231 |
| Soja | oferta_baixo__demanda_base | 277.760200 | 206.499742 | 71.260458 | 74.34461 | 641.637838 | 435.138096 | 67.81678 |
| Milho | oferta_baixo__demanda_alto | 419.949837 | 419.949837 | 0.000000 | 100.00000 | 526.619462 | 105.025319 | 19.94330 |
| Soja | oferta_baixo__demanda_alto | 291.648210 | 213.725240 | 77.922970 | 73.28186 | 641.637838 | 427.912598 | 66.69067 |
| Milho | oferta_base__demanda_baixo | 379.954614 | 379.954614 | 0.000000 | 100.00000 | 619.552308 | 236.313549 | 38.14263 |
| Soja | oferta_base__demanda_baixo | 263.872190 | 215.082519 | 48.789671 | 81.51011 | 754.868045 | 539.785526 | 71.50727 |
| Milho | oferta_base__demanda_base | 399.952226 | 399.952226 | 0.000000 | 100.00000 | 619.552308 | 216.614882 | 34.96313 |
| Soja | oferta_base__demanda_base | 277.760200 | 222.170780 | 55.589420 | 79.98654 | 754.868045 | 532.697265 | 70.56826 |
| Milho | oferta_base__demanda_alto | 419.949837 | 419.949837 | 0.000000 | 100.00000 | 619.552308 | 196.926900 | 31.78535 |
| Soja | oferta_base__demanda_alto | 291.648210 | 229.433940 | 62.214270 | 78.66804 | 754.868045 | 525.434105 | 69.60609 |
| Milho | oferta_alto__demanda_baixo | 379.954614 | 379.954614 | 0.000000 | 100.00000 | 712.485154 | 328.524508 | 46.10966 |
| Soja | oferta_alto__demanda_baixo | 263.872190 | 237.831157 | 26.041033 | 90.13119 | 868.098252 | 630.267095 | 72.60320 |
| Milho | oferta_alto__demanda_base | 399.952226 | 399.952226 | 0.000000 | 100.00000 | 712.485154 | 308.738663 | 43.33265 |
| Soja | oferta_alto__demanda_base | 277.760200 | 247.590767 | 30.169433 | 89.13832 | 868.098252 | 620.507485 | 71.47895 |
| Milho | oferta_alto__demanda_alto | 419.949837 | 419.949837 | 0.000000 | 100.00000 | 712.485154 | 288.778891 | 40.53122 |
| Soja | oferta_alto__demanda_alto | 291.648210 | 257.200983 | 34.447227 | 88.18877 | 868.098252 | 610.897269 | 70.37190 |

## pyomo_gurobi_h215_w_native8h_license_v2

| Product | Scenario | Demand (Mt) | Delivered (Mt) | Shortage (Mt) | Service (%) | Supply (Mt) | Export (Mt) | Export/supply (%) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Milho | oferta_baixo__demanda_baixo | 379.954614 | 379.954614 | 0.000000 | 100.00000 | 526.619462 | 144.812937 | 27.49859 |
| Soja | oferta_baixo__demanda_baixo | 263.872190 | 198.662559 | 65.209631 | 75.28742 | 641.637838 | 442.975279 | 69.03821 |
| Milho | oferta_baixo__demanda_base | 399.952226 | 399.952226 | 0.000000 | 100.00000 | 526.619462 | 124.873662 | 23.71231 |
| Soja | oferta_baixo__demanda_base | 277.760200 | 206.499742 | 71.260458 | 74.34461 | 641.637838 | 435.138096 | 67.81678 |
| Milho | oferta_baixo__demanda_alto | 419.949837 | 419.949837 | 0.000000 | 100.00000 | 526.619462 | 105.025319 | 19.94330 |
| Soja | oferta_baixo__demanda_alto | 291.648210 | 213.725240 | 77.922970 | 73.28186 | 641.637838 | 427.912598 | 66.69067 |
| Milho | oferta_base__demanda_baixo | 379.954614 | 379.954614 | 0.000000 | 100.00000 | 619.552308 | 236.313549 | 38.14263 |
| Soja | oferta_base__demanda_baixo | 263.872190 | 215.082519 | 48.789671 | 81.51011 | 754.868045 | 539.785526 | 71.50727 |
| Milho | oferta_base__demanda_base | 399.952226 | 399.952226 | 0.000000 | 100.00000 | 619.552308 | 216.614882 | 34.96313 |
| Soja | oferta_base__demanda_base | 277.760200 | 222.170780 | 55.589420 | 79.98654 | 754.868045 | 532.697265 | 70.56826 |
| Milho | oferta_base__demanda_alto | 419.949837 | 419.949837 | 0.000000 | 100.00000 | 619.552308 | 196.926900 | 31.78535 |
| Soja | oferta_base__demanda_alto | 291.648210 | 229.433940 | 62.214270 | 78.66804 | 754.868045 | 525.434105 | 69.60609 |
| Milho | oferta_alto__demanda_baixo | 379.954614 | 379.954614 | 0.000000 | 100.00000 | 712.485154 | 328.524508 | 46.10966 |
| Soja | oferta_alto__demanda_baixo | 263.872190 | 237.831157 | 26.041033 | 90.13119 | 868.098252 | 630.267095 | 72.60320 |
| Milho | oferta_alto__demanda_base | 399.952226 | 399.952226 | 0.000000 | 100.00000 | 712.485154 | 308.738663 | 43.33265 |
| Soja | oferta_alto__demanda_base | 277.760200 | 247.590767 | 30.169433 | 89.13832 | 868.098252 | 620.507485 | 71.47895 |
| Milho | oferta_alto__demanda_alto | 419.949837 | 419.949837 | 0.000000 | 100.00000 | 712.485154 | 288.778891 | 40.53122 |
| Soja | oferta_alto__demanda_alto | 291.648210 | 257.200983 | 34.447227 | 88.18877 | 868.098252 | 610.897269 | 70.37190 |

## Interpretation boundary

Full-horizon national service can hide annual/local deficits. The floor is per
product and scenario, not across products or expected scenarios. Export counts
only deliveries to the identified export destinations; OW receipts and WW transfers
are not added. Expected totals may be calculated separately using original weights.

New policies may redirect deliveries, increase investment, change stocks and alter
different penalty quantities in opposite directions. Report tonnes served and unmet,
stock tonne-periods, reception-overflow tonnes, economic subtotal and each penalty
separately. If coefficients change, raw objectives are not a common valuation.
A smaller objective or gap alone does not establish better agricultural service.

No accepted historical result is relabeled as satisfying the newly implemented
policies, and no exact optimality, new solver result or future feasibility is claimed.
