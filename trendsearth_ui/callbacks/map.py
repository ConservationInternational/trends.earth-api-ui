"""Map modal callbacks."""

import json

from dash import Input, Output, State, html, no_update
import requests

from ..config import API_BASE
from ..utils import create_map_from_geojsons


def register_callbacks(app):
    """Register map modal callbacks."""

    @app.callback(
        [
            Output("map-modal", "is_open"),
            Output("map-container", "children"),
            Output("map-info", "children"),
        ],
        [Input("executions-table", "cellClicked")],
        [State("token-store", "data")],
        prevent_initial_call=True,
    )
    def show_map_modal(cell_clicked, token):
        """Show map modal for execution area visualization."""
        if not cell_clicked or not token:
            return False, [], ""

        col = cell_clicked.get("colId")
        if col != "map":
            return False, [], ""

        # Get the row data to find the execution ID
        row_index = cell_clicked.get("rowIndex")
        if row_index is None:
            return False, [], "Could not get row index."

        headers = {"Authorization": f"Bearer {token}"}

        # Calculate which page this row is on
        page_size = 50  # This should match your cacheBlockSize
        page = (row_index // page_size) + 1
        row_in_page = row_index % page_size

        params = {
            "page": page,
            "per_page": page_size,
            "exclude": "results",  # We need params, so exclude only results
        }

        resp = requests.get(f"{API_BASE}/execution", params=params, headers=headers)
        if resp.status_code != 200:
            return False, [], f"Failed to fetch execution data: {resp.text}"

        result = resp.json()
        executions = result.get("data", [])

        if row_in_page >= len(executions):
            return False, [], f"Row index {row_in_page} out of range for page {page}"

        execution = executions[row_in_page]
        exec_id = execution.get("id")

        if not exec_id:
            return False, [], "Could not get execution ID from row data."

        # Fetch full execution details including params
        resp = requests.get(f"{API_BASE}/execution/{exec_id}", headers=headers)
        if resp.status_code != 200:
            return False, [], f"Failed to fetch execution details: {resp.text}"

        execution_data = resp.json().get("data", {})
        params_data = execution_data.get("params")

        if not params_data:
            return False, [], "No parameters found for this execution."

        # Parse geojsons field
        geojsons = None
        if isinstance(params_data, dict):
            geojsons = params_data.get("geojsons")
        elif isinstance(params_data, str):
            try:
                params_dict = json.loads(params_data)
                geojsons = params_dict.get("geojsons")
            except json.JSONDecodeError:
                return False, [], "Could not parse parameters JSON."

        if not geojsons:
            return False, [], "No geojsons found in execution parameters."

        # Create map with geojsons
        map_children = create_map_from_geojsons(geojsons, exec_id)

        # Create info text
        info_text = html.Div(
            [
                html.P([html.Strong("Execution ID: "), str(exec_id)]),
                html.P(
                    [
                        html.Strong("Number of areas: "),
                        str(len(geojsons) if isinstance(geojsons, list) else 1),
                    ]
                ),
            ]
        )

        return True, map_children, info_text

    @app.callback(
        Output("map-modal", "is_open", allow_duplicate=True),
        [Input("close-map-modal", "n_clicks")],
        prevent_initial_call=True,
    )
    def close_map_modal(n_clicks):
        """Close the map modal."""
        if n_clicks:
            return False
        return no_update


# Legacy callback decorators for backward compatibility (these won't be executed)
