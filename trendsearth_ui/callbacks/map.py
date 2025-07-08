"""Map modal callbacks."""


from dash import Input, Output, State, html, no_update
import requests

from ..config import API_BASE


def register_callbacks(app):
    """Register map modal callbacks."""

    @app.callback(
        [
            Output("map-modal", "is_open"),
            Output("map-container", "children"),
            Output("map-info", "children"),
        ],
        [Input("executions-table", "cellClicked")],
        [State("token-store", "data"), State("executions-table-state", "data")],
        prevent_initial_call=True,
    )
    def show_map_modal(cell_clicked, token, table_state):
        """Show map modal for execution area visualization."""
        if not cell_clicked or not token:
            return False, [], ""

        col = cell_clicked.get("colId")
        if col != "map":
            return False, [], ""

        print("DEBUG: Processing map click for execution")
        # Try to get row data from cell click event first
        row_data = cell_clicked.get("data")
        execution_id = None

        if row_data:
            execution_id = row_data.get("id")
            print(f"DEBUG: Got execution ID from row data: {execution_id}")

        # If we don't have execution_id from row data, fall back to pagination approach
        if not execution_id:
            print("DEBUG: No execution ID from row data, trying pagination")
            row_index = cell_clicked.get("rowIndex")
            if row_index is None:
                print("DEBUG: No row index available")
                return False, [], "Could not get row index from cell click event."

            try:
                # Calculate which page this row is on
                headers = {"Authorization": f"Bearer {token}"}
                page_size = 50  # This should match DEFAULT_PAGE_SIZE
                page = (row_index // page_size) + 1
                row_in_page = row_index % page_size

                params = {
                    "page": page,
                    "per_page": page_size,
                    "exclude": "results",  # We need params for map, so exclude only results
                    "include": "script_name,user_name,user_email,duration",
                }

                # Apply the same sort and filter that the table is currently using
                if table_state:
                    if table_state.get("sort_sql"):
                        params["sort"] = table_state["sort_sql"]
                    if table_state.get("filter_sql"):
                        params["filter"] = table_state["filter_sql"]

                resp = requests.get(f"{API_BASE}/execution", params=params, headers=headers)
                if resp.status_code != 200:
                    return (
                        False,
                        [],
                        f"Failed to fetch execution data: {resp.status_code} - {resp.text}",
                    )

                result = resp.json()
                executions = result.get("data", [])

                if row_in_page >= len(executions):
                    return (
                        False,
                        [],
                        f"Row index {row_in_page} out of range for page {page} (found {len(executions)} executions)",
                    )

                execution = executions[row_in_page]
                execution_id = execution.get("id")

            except Exception as e:
                return False, [], f"Error fetching execution data: {str(e)}"

        if not execution_id:
            print("DEBUG: Could not get execution ID")
            return False, [], f"Could not get execution ID. Cell data: {cell_clicked}"

        print(f"DEBUG: Fetching execution details for ID: {execution_id}")
        try:
            headers = {"Authorization": f"Bearer {token}"}

            # Fetch full execution details including params directly using the execution ID
            resp = requests.get(
                f"{API_BASE}/execution/{execution_id}",
                headers=headers,
                params={"include": "params"},
            )
            print(f"DEBUG: Map execution API response: {resp.status_code}")
            if resp.status_code != 200:
                print(f"DEBUG: Failed to fetch execution details: {resp.status_code}")
                return (
                    False,
                    [],
                    f"Failed to fetch execution details: {resp.status_code} - {resp.text}",
                )

            execution_response = resp.json()
            # Handle API response structure - check if data is wrapped in a 'data' field
            if (
                isinstance(execution_response, dict)
                and "data" in execution_response
                and execution_response.get("data") is not None
            ):
                execution_data = execution_response["data"]
            else:
                execution_data = execution_response
            params_data = execution_data.get("params")
            print(f"DEBUG: Params data type: {type(params_data)}, has content: {bool(params_data)}")

            if not params_data:
                print("DEBUG: No parameters found for execution")
                return False, [], "No parameters found for this execution."

            # Parse geojsons field
            geojsons = None
            print("DEBUG: Parsing geojsons from params")
            if isinstance(params_data, dict):
                geojsons = params_data.get("geojsons")
                print(
                    f"DEBUG: Found geojsons in dict: {type(geojsons)} - {str(geojsons)[:100] if geojsons else 'None'}..."
                )
            elif isinstance(params_data, str):
                print("DEBUG: Params data is string, trying to parse JSON")
                try:
                    import json

                    params_dict = json.loads(params_data)
                    geojsons = params_dict.get("geojsons")
                    print(
                        f"DEBUG: Parsed geojsons from JSON: {type(geojsons)} - {str(geojsons)[:100] if geojsons else 'None'}..."
                    )
                except json.JSONDecodeError as e:
                    print(f"DEBUG: JSON decode error: {e}")
                    return False, [], "Could not parse parameters JSON."

            if not geojsons:
                print("DEBUG: No geojsons found in parameters")
                return False, [], "No geojsons found in execution parameters."

            print("DEBUG: Creating map from geojsons")
            # Create map with geojsons
            from ..utils.geojson import create_map_from_geojsons

            map_children = create_map_from_geojsons(geojsons, execution_id)
            print("DEBUG: Map children created successfully")

            # Create info text
            info_text = html.Div(
                [
                    html.P([html.Strong("Execution ID: "), str(execution_id)]),
                    html.P(
                        [
                            html.Strong("Number of areas: "),
                            str(len(geojsons) if isinstance(geojsons, list) else 1),
                        ]
                    ),
                ]
            )

            print("DEBUG: Map modal returning successfully")
            return True, map_children, info_text

        except Exception as e:
            print(f"DEBUG: Exception in map callback: {e}")
            import traceback

            traceback.print_exc()
            return False, [], f"Error creating map: {str(e)}"

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
