"""Local read-only Dash interface; no optimizer, routing client or write callback."""

from __future__ import annotations

import json

from .geography import catalogue, figure_definition, plotly_figure


def create_app(database, snapshot):
    from dash import Dash, Input, Output, State, dcc, html

    info = catalogue(database, snapshot)
    populations = info["metadata"]["available_populations"]
    app = Dash(__name__)
    app.layout = html.Main(
        [
            html.H1("Model Agrologistic geographic evidence"),
            html.P("Read-only view. Included candidates are not automatically opened facilities."),
            dcc.Dropdown(populations, populations[0], id="population", clearable=False),
            dcc.Dropdown(id="case", placeholder="Availability only"),
            dcc.Dropdown(id="product", placeholder="All products"),
            dcc.Dropdown(id="period", placeholder="All periods"),
            dcc.Dropdown(id="scenario", placeholder="Probability-weighted scenarios"),
            dcc.Dropdown(
                [{"label": f"Added at h{p}", "value": p} for p in populations],
                id="warehouse-layer",
                placeholder="All included warehouse layers",
            ),
            dcc.Graph(id="map", style={"height": "70vh"}),
            html.Pre(id="qualification", style={"whiteSpace": "pre-wrap"}),
            html.H2("Coincident node and investment details"),
            html.Pre(id="details", style={"whiteSpace": "pre-wrap"}),
        ],
        style={"fontFamily": "Arial,sans-serif", "maxWidth": "1500px", "margin": "auto"},
    )

    @app.callback(Output("case", "options"), Output("case", "value"), Input("population", "value"))
    def cases(population):
        return [
            {"label": c["id"] + " / " + c["mode"] + " / " + c["status"], "value": c["id"]}
            for c in info["cases"]
            if c["population"] == population
        ], None

    @app.callback(
        Output("product", "options"),
        Output("product", "value"),
        Output("period", "options"),
        Output("period", "value"),
        Output("scenario", "options"),
        Output("scenario", "value"),
        Input("case", "value"),
    )
    def dimensions(case_id):
        case = next((c for c in info["cases"] if c["id"] == case_id), {})
        return (
            case.get("products", []),
            None,
            [str(t) for t in case.get("periods", [])],
            None,
            list(case.get("probabilities", {})),
            None,
        )

    @app.callback(
        Output("map", "figure"),
        Output("qualification", "children"),
        Input("population", "value"),
        Input("case", "value"),
        Input("product", "value"),
        Input("period", "value"),
        Input("scenario", "value"),
        Input("warehouse-layer", "value"),
    )
    def update(population, case_id, product, period, scenario, warehouse_layer):
        selected = next(
            (c for c in info["cases"] if c["id"] == case_id and c["population"] == population), {}
        )
        # Dash may deliver a population change before its dependent dropdown resets.
        if not selected:
            case_id, product, period, scenario = None, None, None, None
        else:
            product = product if product in selected.get("products", []) else None
            period = period if str(period) in list(map(str, selected.get("periods", []))) else None
            scenario = scenario if scenario in selected.get("probabilities", {}) else None
        if warehouse_layer is not None and warehouse_layer > population:
            warehouse_layer = None
        definition = figure_definition(
            database,
            snapshot,
            population=population,
            case_id=case_id,
            product=product,
            period=period,
            scenario=scenario,
            warehouse_layer=warehouse_layer,
        )
        qualification = {
            k: definition[k]
            for k in ("evidence_status", "synthetic", "filters", "figure_sha256", "notes")
        }
        qualification["missing_geometry_count"] = len(definition["missing_geometry"])
        qualification["missing_geometry_examples"] = definition["missing_geometry"][:20]
        return plotly_figure(definition), json.dumps(qualification, indent=2)

    @app.callback(
        Output("details", "children"), Input("map", "clickData"), State("population", "value")
    )
    def details(click, population):
        return json.dumps(
            {
                "population": population,
                "nodes": [p.get("customdata") for p in (click or {}).get("points", [])],
            },
            indent=2,
        )

    return app
