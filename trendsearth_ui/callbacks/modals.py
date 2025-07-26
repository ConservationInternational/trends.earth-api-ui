"""Modal callbacks for JSON display, logs, and downloads."""

from dash import Input, Output, State, html, no_update

from ..utils import parse_date, render_json_tree


def register_callbacks(app):
    """Register modal-related callbacks."""

    @app.callback(
        Output("json-modal", "is_open", allow_duplicate=True),
        Output("json-modal-body", "children", allow_duplicate=True),
        Output("json-modal-data", "data", allow_duplicate=True),
        Output("json-modal-title", "children", allow_duplicate=True),
        Output("refresh-logs-btn", "style", allow_duplicate=True),
        Output("logs-refresh-interval", "disabled", allow_duplicate=True),
        Output("current-log-context", "data", allow_duplicate=True),
        Input("executions-table", "cellClicked"),
        [
            State("token-store", "data"),
            State("json-modal", "is_open"),
            State("executions-table-state", "data"),
            State("user-timezone-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def show_json_modal(cell, token, is_open, table_state, user_timezone):
        """Show JSON/logs modal for execution cell clicks."""
        if not cell:
            return is_open, no_update, no_update, no_update, no_update, no_update, no_update

        col = cell.get("colId")
        if col not in ("params", "results", "logs"):
            return is_open, no_update, no_update, no_update, no_update, no_update, no_update

        # Try to get row data from cell click event first
        row_data = cell.get("data")
        execution_id = None

        if row_data:
            execution_id = row_data.get("id")

        # If we don't have execution_id from row data, fall back to pagination approach
        if not execution_id:
            row_index = cell.get("rowIndex")
            if row_index is None:
                return (
                    True,
                    "Could not get row index from cell click event.",
                    None,
                    "Error",
                    {"display": "none"},
                    True,
                    None,
                )

            try:
                from ..utils.helpers import make_authenticated_request

                # Calculate which page this row is on
                page_size = 50  # This should match DEFAULT_PAGE_SIZE
                page = (row_index // page_size) + 1
                row_in_page = row_index % page_size

                # Use exclude=params,results for pagination since we'll fetch them separately
                params = {
                    "page": page,
                    "per_page": page_size,
                    "exclude": "params,results",
                    "include": "script_name,user_name,user_email,user_id,duration",
                }

                # Apply the same sort and filter that the table is currently using
                if table_state:
                    if table_state.get("sort_sql"):
                        params["sort"] = table_state["sort_sql"]
                    if table_state.get("filter_sql"):
                        params["filter"] = table_state["filter_sql"]

                resp = make_authenticated_request("/execution", token, params=params)
                if resp.status_code != 200:
                    return (
                        True,
                        f"Failed to fetch execution data: {resp.status_code} - {resp.text}",
                        None,
                        "Error",
                        {"display": "none"},
                        True,
                        None,
                    )

                result = resp.json()
                executions = result.get("data", [])

                if row_in_page >= len(executions):
                    return (
                        True,
                        f"Row index {row_in_page} out of range for page {page} (found {len(executions)} executions)",
                        None,
                        "Error",
                        {"display": "none"},
                        True,
                        None,
                    )

                execution_data = executions[row_in_page]
                execution_id = execution_data.get("id")

            except Exception as e:
                return (
                    True,
                    f"Error fetching execution data: {str(e)}",
                    None,
                    "Error",
                    {"display": "none"},
                    True,
                    None,
                )

        if not execution_id:
            return (
                True,
                "Could not get execution ID from row or pagination data.",
                None,
                "Error",
                {"display": "none"},
                True,
                None,
            )

        try:
            from ..utils.helpers import make_authenticated_request

            if col == "params":
                # Always fetch params from the individual execution endpoint
                resp = make_authenticated_request(
                    f"/execution/{execution_id}",
                    token,
                    params={"include": "params"},
                )
                if resp.status_code != 200:
                    return (
                        True,
                        f"Failed to fetch execution data: {resp.status_code} - {resp.text}",
                        None,
                        "Error",
                        {"display": "none"},
                        True,
                        None,
                    )
                execution = resp.json()
                # Handle API response structure - check if data is wrapped in a 'data' field
                if (
                    isinstance(execution, dict)
                    and "data" in execution
                    and execution.get("data") is not None
                ):
                    execution_data = execution["data"]
                else:
                    execution_data = execution
                params = execution_data.get("params", {})

                if not params:
                    return (
                        True,
                        html.P("No parameters found for this execution."),
                        {},
                        f"Execution {execution_id} - Parameters",
                        {"display": "none"},
                        True,
                        None,
                    )

                return (
                    True,
                    render_json_tree(params),
                    params,
                    f"Execution {execution_id} - Parameters",
                    {"display": "none"},
                    True,
                    None,
                )

            elif col == "results":
                # Always fetch results from the individual execution endpoint
                resp = make_authenticated_request(
                    f"/execution/{execution_id}",
                    token,
                    params={"include": "results"},
                )
                if resp.status_code != 200:
                    return (
                        True,
                        f"Failed to fetch execution data: {resp.status_code} - {resp.text}",
                        None,
                        "Error",
                        {"display": "none"},
                        True,
                        None,
                    )
                execution = resp.json()
                # Handle API response structure - check if data is wrapped in a 'data' field
                if (
                    isinstance(execution, dict)
                    and "data" in execution
                    and execution.get("data") is not None
                ):
                    execution_data = execution["data"]
                else:
                    execution_data = execution
                results = execution_data.get("results", {})

                if not results:
                    return (
                        True,
                        html.P("No results found for this execution."),
                        {},
                        f"Execution {execution_id} - Results",
                        {"display": "none"},
                        True,
                        None,
                    )

                return (
                    True,
                    render_json_tree(results),
                    results,
                    f"Execution {execution_id} - Results",
                    {"display": "none"},
                    True,
                    None,
                )

            elif col == "logs":
                from ..utils.helpers import make_authenticated_request

                # Get execution status from row data for auto-refresh control
                execution_status = None
                if row_data:
                    execution_status = row_data.get("status")

                # If we don't have status from row_data, we can try to fetch it
                if not execution_status and "execution_data" in locals():
                    execution_status = execution_data.get("status")

                # For logs, try the execution-specific endpoint first
                resp = make_authenticated_request(f"/execution/{execution_id}/log", token)

                if resp.status_code != 200:
                    # Fall back to general log endpoint with execution_id parameter
                    resp = make_authenticated_request(
                        "/log",
                        token,
                        params={
                            "execution_id": execution_id,
                            "per_page": 50,
                            "sort": "register_date",
                        },
                    )

                    if resp.status_code != 200:
                        return (
                            True,
                            f"Failed to fetch logs: {resp.status_code} - {resp.text}",
                            None,
                            f"Execution {execution_id} - Logs",
                            {"display": "none"},
                            True,
                            {
                                "execution_id": execution_id,
                                "type": "execution",
                                "id": execution_id,
                                "status": execution_status,
                            },
                        )

                result = resp.json()
                logs = result.get("data", [])

                if not logs:
                    log_content = html.P("No logs found for this execution.")
                else:
                    # Parse and format logs the same way as script logs
                    if isinstance(logs, list):
                        parsed_logs = []
                        for log in logs:
                            if isinstance(log, dict):
                                register_date = log.get("register_date", "")
                                level = log.get("level", "INFO")
                                text = log.get("text", "")

                                # Parse and format the date
                                formatted_date = (
                                    parse_date(register_date, user_timezone) or register_date
                                )

                                # Create formatted log line
                                log_line = f"{formatted_date} - {level} - {text}"
                                parsed_logs.append((register_date, log_line))
                            else:
                                # Fallback for non-dict log entries
                                parsed_logs.append(("", str(log)))

                        # Sort by register_date in descending order
                        parsed_logs.sort(key=lambda x: x[0], reverse=True)
                        logs_content = "\n".join([log_line for _, log_line in parsed_logs])
                        log_content = html.Pre(
                            logs_content,
                            style={
                                "whiteSpace": "pre-wrap",
                                "fontSize": "12px",
                                "fontFamily": "monospace",
                            },
                        )
                    else:
                        log_content = html.Pre(
                            str(logs),
                            style={
                                "whiteSpace": "pre-wrap",
                                "fontSize": "12px",
                                "fontFamily": "monospace",
                            },
                        )

                return (
                    True,
                    log_content,
                    None,
                    f"Execution {execution_id} - Logs",
                    {"display": "inline-block"},
                    False,
                    {
                        "execution_id": execution_id,
                        "type": "execution",
                        "id": execution_id,
                        "status": execution_status,
                    },
                )

        except Exception as e:
            return (
                True,
                f"Error processing {col} data: {str(e)}",
                None,
                "Error",
                {"display": "none"},
                True,
                None,
            )

    @app.callback(
        Output("json-modal-body", "children", allow_duplicate=True),
        Input("refresh-logs-btn", "n_clicks"),
        [State("current-log-context", "data"), State("token-store", "data")],
        prevent_initial_call=True,
    )
    def refresh_logs_content(n_clicks, log_context, token):
        """Refresh logs content in modal."""
        if not n_clicks or not log_context or not token:
            return no_update

        execution_id = log_context.get("execution_id")
        if not execution_id:
            return html.P("No execution context available")

        try:
            from ..utils.helpers import make_authenticated_request

            resp = make_authenticated_request(f"/execution/{execution_id}/log", token)

            if resp.status_code != 200:
                return html.P(f"Failed to fetch logs: {resp.status_code}")

            logs_data = resp.json()
            logs = logs_data.get("data", [])

            if not logs:
                return html.P("No logs available")

            log_content = html.Div(
                [
                    html.Div(
                        [
                            html.Strong(f"[{log.get('timestamp', 'Unknown')}] "),
                            html.Span(log.get("text", "")),
                        ],
                        style={"marginBottom": "10px", "fontFamily": "monospace"},
                    )
                    for log in logs
                ]
            )

            return log_content

        except Exception as e:
            return html.P(f"Error fetching logs: {str(e)}")

    @app.callback(
        Output("download-json", "data"),
        Input("download-json-btn", "n_clicks"),
        State("json-modal-data", "data"),
        prevent_initial_call=True,
    )
    def download_json(n, json_data):
        """Download JSON data as file."""
        if n and json_data is not None:
            try:
                import json

                json_str = json.dumps(json_data, indent=2)
            except Exception:
                json_str = str(json_data)
            return {"content": json_str, "filename": "data.json"}
        return no_update

    @app.callback(
        Output("json-modal", "is_open", allow_duplicate=True),
        Output("json-modal-body", "children", allow_duplicate=True),
        Output("json-modal-data", "data", allow_duplicate=True),
        Output("json-modal-title", "children", allow_duplicate=True),
        Output("refresh-logs-btn", "style", allow_duplicate=True),
        Output("logs-refresh-interval", "disabled", allow_duplicate=True),
        Output("current-log-context", "data", allow_duplicate=True),
        Input("scripts-table", "cellClicked"),
        [
            State("token-store", "data"),
            State("json-modal", "is_open"),
            State("scripts-table-state", "data"),
            State("user-timezone-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def show_script_logs_modal(cell, token, is_open, table_state, user_timezone):
        """Show script logs modal using rowIndex and backend pagination (like executions)."""
        if not cell:
            return is_open, no_update, no_update, no_update, no_update, no_update, no_update

        col = cell.get("colId")
        if col != "logs":
            return is_open, no_update, no_update, no_update, no_update, no_update, no_update

        # Try to get row data from cell click event first
        row_data = cell.get("data")
        script_id = None

        if row_data:
            script_id = row_data.get("id")

        # If we don't have row data or script_id, fall back to pagination approach
        if not script_id:
            row_index = cell.get("rowIndex")
            if row_index is None:
                return (
                    True,
                    "Could not get row index.",
                    None,
                    "Error",
                    {"display": "none"},
                    True,
                    None,
                )

            try:
                from ..utils.helpers import make_authenticated_request

                # Calculate which page this row is on
                page_size = 50  # This should match DEFAULT_PAGE_SIZE
                page = (row_index // page_size) + 1
                row_in_page = row_index % page_size

                params = {"page": page, "per_page": page_size, "include": "user_name"}

                # Apply the same sort and filter that the table is currently using
                if table_state:
                    if table_state.get("sort_sql"):
                        params["sort"] = table_state["sort_sql"]
                    if table_state.get("filter_sql"):
                        params["filter"] = table_state["filter_sql"]

                resp = make_authenticated_request("/script", token, params=params)
                if resp.status_code != 200:
                    return (
                        True,
                        f"Failed to fetch script data: {resp.status_code} - {resp.text}",
                        None,
                        "Error",
                        {"display": "none"},
                        True,
                        None,
                    )

                result = resp.json()
                scripts = result.get("data", [])
                if row_in_page >= len(scripts):
                    return (
                        True,
                        f"Row index {row_in_page} out of range for page {page} (found {len(scripts)} scripts)",
                        None,
                        "Error",
                        {"display": "none"},
                        True,
                        None,
                    )

                script = scripts[row_in_page]
                script_id = script.get("id")

            except Exception as e:
                return (
                    True,
                    f"Error fetching script data: {str(e)}",
                    None,
                    "Error",
                    {"display": "none"},
                    True,
                    None,
                )

        if not script_id:
            return True, "Could not get script ID.", None, "Error", {"display": "none"}, True, None

        try:
            from ..utils.helpers import make_authenticated_request

            # Get the logs for this script with automatic token refresh
            resp = make_authenticated_request(f"/script/{script_id}/log", token)

            if resp.status_code != 200:
                return (
                    True,
                    f"Failed to fetch script logs: {resp.status_code} - {resp.text}",
                    None,
                    "Script Logs",
                    {"display": "none"},
                    True,
                    None,
                )
            logs_data = resp.json().get("data", [])
            if not logs_data:
                return (
                    True,
                    "No logs found for this script.",
                    None,
                    "Script Logs",
                    {"display": "none"},
                    True,
                    None,
                )
            # Parse and format logs for display (same as execution logs)
            if isinstance(logs_data, list):
                parsed_logs = []
                for log in logs_data:
                    if isinstance(log, dict):
                        register_date = log.get("register_date", "")
                        level = log.get("level", "")
                        text = log.get("text", "")

                        # Parse and format the date
                        formatted_date = parse_date(register_date, user_timezone) or register_date

                        # Create formatted log line
                        log_line = f"{formatted_date} - {level} - {text}"
                        parsed_logs.append((register_date, log_line))
                    else:
                        # Fallback for non-dict log entries
                        parsed_logs.append(("", str(log)))

                # Sort by register_date in descending order
                parsed_logs.sort(key=lambda x: x[0], reverse=True)
                logs_content = "\n".join([log_line for _, log_line in parsed_logs])
                logs_display = html.Pre(
                    logs_content, style={"whiteSpace": "pre-wrap", "fontSize": "12px"}
                )
            else:
                logs_display = html.Pre(
                    str(logs_data), style={"whiteSpace": "pre-wrap", "fontSize": "12px"}
                )
            return (
                True,
                logs_display,
                logs_data,
                "Script Logs",
                {"display": "inline-block"},
                False,
                {"type": "script", "id": script_id, "status": "UNKNOWN"},
            )

        except Exception as e:
            return (
                True,
                f"Error processing script logs: {str(e)}",
                None,
                "Error",
                {"display": "none"},
                True,
                None,
            )


# Legacy callback decorators for backward compatibility (these won't be executed)
