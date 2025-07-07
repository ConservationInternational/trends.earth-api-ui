"""Modal callbacks for JSON display, logs, and downloads."""

from dash import Input, Output, State, html, no_update
import requests

from ..config import API_BASE
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
        ],
        prevent_initial_call=True,
    )
    def show_json_modal(cell, token, is_open, table_state):
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
                # Calculate which page this row is on
                headers = {"Authorization": f"Bearer {token}"}
                page_size = 50  # This should match DEFAULT_PAGE_SIZE
                page = (row_index // page_size) + 1
                row_in_page = row_index % page_size

                # For executions, we only need basic info to get the ID
                params = {
                    "page": page,
                    "per_page": page_size,
                    "exclude": "params,results",  # Exclude large fields for pagination
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

                execution = executions[row_in_page]
                execution_id = execution.get("id")

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
                f"Could not get execution ID. Cell data: {cell}",
                None,
                "Error",
                {"display": "none"},
                True,
                None,
            )

        try:
            headers = {"Authorization": f"Bearer {token}"}

            # Now fetch the specific execution data based on the column clicked
            if col == "params":
                resp = requests.get(f"{API_BASE}/execution/{execution_id}", headers=headers)
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
                params = execution.get("params", {})
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
                resp = requests.get(f"{API_BASE}/execution/{execution_id}", headers=headers)
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
                results = execution.get("results", {})
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
                # For logs, we'll show the initial logs and enable refresh
                resp = requests.get(
                    f"{API_BASE}/log",
                    headers=headers,
                    params={"execution_id": execution_id, "per_page": 50, "sort": "register_date"},
                )
                if resp.status_code != 200:
                    return (
                        True,
                        f"Failed to fetch logs: {resp.status_code} - {resp.text}",
                        None,
                        f"Execution {execution_id} - Logs",
                        {"display": "none"},
                        True,
                        {"execution_id": execution_id, "type": "logs"},
                    )

                result = resp.json()
                logs = result.get("data", [])

                if not logs:
                    log_content = [html.P("No logs found for this execution.")]
                else:
                    log_content = []
                    for log in logs:
                        log_content.append(
                            html.Div(
                                [
                                    html.Span(
                                        f"[{parse_date(log.get('register_date', ''))}] ",
                                        style={"fontWeight": "bold", "color": "#666"},
                                    ),
                                    html.Span(
                                        f"{log.get('level', 'INFO')}: ",
                                        style={
                                            "fontWeight": "bold",
                                            "color": {
                                                "ERROR": "#dc3545",
                                                "WARNING": "#ffc107",
                                                "INFO": "#17a2b8",
                                                "DEBUG": "#6c757d",
                                            }.get(log.get("level", "INFO"), "#17a2b8"),
                                        },
                                    ),
                                    html.Span(log.get("text", "")),
                                ],
                                style={"marginBottom": "10px", "fontFamily": "monospace"},
                            )
                        )

                return (
                    True,
                    log_content,
                    None,
                    f"Execution {execution_id} - Logs",
                    {"display": "inline-block"},
                    False,
                    {"execution_id": execution_id, "type": "logs"},
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
            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.get(f"{API_BASE}/execution/{execution_id}/log", headers=headers)

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
        ],
        prevent_initial_call=True,
    )
    def show_script_logs_modal(cell, token, is_open, table_state):
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
                # Calculate which page this row is on
                headers = {"Authorization": f"Bearer {token}"}
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

                resp = requests.get(f"{API_BASE}/script", params=params, headers=headers)
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
            headers = {"Authorization": f"Bearer {token}"}

            # Get the logs for this script
            resp = requests.get(f"{API_BASE}/script/{script_id}/log", headers=headers)
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
                        formatted_date = parse_date(register_date) or register_date

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
