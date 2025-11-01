"""Map modal callbacks."""

from dash import MATCH, Input, Output, State, html, no_update

from ..config import DEFAULT_PAGE_SIZE


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

        # Try to get row data from cell click event first
        row_data = cell_clicked.get("data")
        execution_id = None

        if row_data:
            execution_id = row_data.get("id")

        # If we don't have execution_id from row data, fall back to pagination approach
        if not execution_id:
            row_index = cell_clicked.get("rowIndex")
            if row_index is None:
                return False, [], "Could not get row index from cell click event."

            try:
                # Calculate which page this row is on
                page_size = DEFAULT_PAGE_SIZE
                page = (row_index // page_size) + 1
                row_in_page = row_index % page_size

                params = {
                    "page": page,
                    "per_page": page_size,
                    "exclude": "results",  # We need params for map, so exclude only results
                    "include": "script_name,user_name,user_email,user_id,duration",
                }

                # Apply the same sort and filter that the table is currently using
                if table_state:
                    if table_state.get("sort_sql"):
                        params["sort"] = table_state["sort_sql"]
                    if table_state.get("filter_sql"):
                        params["filter"] = table_state["filter_sql"]

                # Get execution data using the authenticated helper
                from ..utils.helpers import make_authenticated_request

                resp = make_authenticated_request("/execution", token, params=params)
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
            from ..utils.helpers import make_authenticated_request

            # First try with include=params
            resp = make_authenticated_request(
                f"/execution/{execution_id}",
                token,
                params={"include": "params"},
            )

            if resp.status_code != 200:
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

            # If no params with include, try without include parameter
            if not params_data:
                resp2 = make_authenticated_request(f"/execution/{execution_id}", token)

                if resp2.status_code == 200:
                    execution_response2 = resp2.json()

                    if (
                        isinstance(execution_response2, dict)
                        and "data" in execution_response2
                        and execution_response2.get("data") is not None
                    ):
                        execution_data2 = execution_response2["data"]
                    else:
                        execution_data2 = execution_response2

                    params_data = execution_data2.get("params")

            if not params_data:
                return (
                    False,
                    [],
                    f"No parameters found for execution {execution_id}. The execution may not have geojson data required for mapping.",
                )

            # Parse geojsons field - check both 'geojsons' and 'geojson' keys
            geojsons = None
            if isinstance(params_data, dict):
                # Try both 'geojsons' (plural) and 'geojson' (singular)
                geojsons = params_data.get("geojsons") or params_data.get("geojson")
            elif isinstance(params_data, str):
                try:
                    import json

                    params_dict = json.loads(params_data)
                    # Try both 'geojsons' (plural) and 'geojson' (singular)
                    geojsons = params_dict.get("geojsons") or params_dict.get("geojson")
                except json.JSONDecodeError:
                    return (
                        False,
                        [],
                        f"Could not parse parameters JSON for execution {execution_id}.",
                    )

            if not geojsons:
                available_keys = (
                    list(params_data.keys()) if isinstance(params_data, dict) else "Not a dict"
                )
                return (
                    False,
                    [],
                    f"No geojsons found in execution {execution_id} parameters. Available params: {available_keys}",
                )

            # Create map with geojsons
            from ..utils.geojson import create_map_from_geojsons

            map_children = create_map_from_geojsons(geojsons, execution_id)

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

            return True, map_children, info_text

        except Exception as e:
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

    # Add server-side callback for closing minimaps using pattern matching
    @app.callback(
        Output({"type": "minimap-container", "index": MATCH}, "style"),
        Input({"type": "minimap-close", "index": MATCH}, "n_clicks"),
        prevent_initial_call=True,
    )
    def close_minimap(n_clicks):
        """Close the minimap by hiding the container."""
        if n_clicks and n_clicks > 0:
            return {"display": "none"}
        return no_update


# Legacy callback decorators for backward compatibility (these won't be executed)
