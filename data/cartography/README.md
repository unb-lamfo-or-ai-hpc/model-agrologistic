# IBGE 2023 administrative context

`ibge_2023_simplified.json.gz` is a permanent, versioned cartographic derivative, not an optimization input or a temporary rendered figure. It contains Brazil and all 27 federative units, including official UF codes/names and original/display geometry identities.

Source: Instituto Brasileiro de Geografia e Estatistica (IBGE), Malha Municipal Digital 2023, `BR_UF_2023.zip` and `BR_Pais_2023.zip` from the [official 2023 Brasil catalogue](https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2023/Brasil/). Source archive hashes and individual geometry hashes are inside the dataset. Original high-resolution archives are not committed.

The source CRS is SIRGAS 2000 (EPSG:4674), verified from both original PRJ records. Preparation transforms to SIRGAS 2000 / Brazil Polyconic (EPSG:5880) for shared-edge coverage simplification, then to WGS84 (EPSG:4326). The display transform is separately declared spherical Albers equal-area, with standard parallels -2 and -22 degrees, central longitude -54, latitude origin -12 and radius 6371008.8 m. It is a display projection, not a road-distance or surveyed-area measurement.

Shapely/GEOS coverage simplification uses a 1000 m tolerance parameter. It preserves edge matching and valid coverage; the parameter is approximately the square root of eliminated triangle area, not a maximum displacement guarantee. No separate ring rounding is applied. The national silhouette is derived from the simplified UF union, after verifying that the ORIGINAL national geometry exactly equals the ORIGINAL UF union.

The derivative has 28698 UF vertices versus 1137745 originally; projected union area changes by -0.0008110471%. Every displayed polygon was rechecked for validity and coverage after the CRS transformation.

## Attribution and redistribution

**IBGE (2023), adapted; CC BY 4.0.** Retain this attribution, [license link](https://creativecommons.org/licenses/by/4.0/), source URLs and the notice that simplification and projection have been applied. The [IBGE technical/legal note, page 8](https://www.ibge.gov.br/biblioteca/visualizacao/livros/liv102152.pdf) explicitly states CC BY 4.0-compatible licensing for the municipal digital mesh and derivative products. This derivative is not relicensed as MIT. IBGE does not endorse the optimization results.

## Offline reuse

Populate the existing geographic database explicitly, once:

```text
python -m scripts.prepare_ibge_boundaries --context data/cartography/ibge_2023_simplified.json.gz --sqlite PATH_TO_GEOGRAPHIC_SQLITE
```

This command needs only the Python standard library. It adds three context tables without changing the existing scientific snapshots or SQLite user_version 1. An identical dataset causes no write; a new source/projection/configuration identity adds a new dataset and retains its predecessor. Dashboard callbacks and figure definitions only read the selected context.

Rebuilding the derivative from the two original archives is optional and uses the separate `cartography-prepare` dependency group. It does not execute a solver or contact a routing service.
