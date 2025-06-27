"""Modal callbacks for JSON display, logs, and downloads."""

from dash import Input, Output, State, dcc, html, no_update
import requests

from ..config import API_BASE
from ..utils import parse_date, render_json_tree


def register_callbacks(app):
    """Register modal-related callbacks."""

    @app.callback(
        Output("json-modal", "is_open"),
        Output("json-modal-body", "children"),
        Output("json-modal-data", "data"),
        Output("json-modal-title", "children"),
        Output("refresh-logs-btn", "style"),
        Output("logs-refresh-interval", "disabled"),
        Output("current-log-context", "data"),
        Input("executions-table", "cellClicked"),
        State("token-store", "data"),
        State("json-modal", "is_open"),
        prevent_initial_call=True,
    )
    def show_json_modal(cell, token, is_open):
        """Show JSON/logs modal for execution cell clicks."""
        if not cell:
            return is_open, no_update, no_update, no_update, no_update, no_update, no_update

        col = cell.get("colId")
        if col not in ("params", "results", "logs"):
            return is_open, no_update, no_update, no_update, no_update, no_update, no_update

        # For infinite row model, we need to get the row data differently
        # We'll use the rowIndex to fetch from our current data
        row_index = cell.get("rowIndex")

        if row_index is None:
            return True, "Could not get row index.", None, "Error", {"display": "none"}, True, None

        # We need to make a request to get the row data since cellClicked doesn't provide it
        # Let's use a different approach - get all data and find the right row
        headers = {"Authorization": f"Bearer {token}"}

        # Calculate which page this row is on
        page_size = 50  # This should match your cacheBlockSize
        page = (row_index // page_size) + 1
        row_in_page = row_index % page_size

        params = {
            "page": page,
            "per_page": page_size,
            "exclude": "params,results",
        }

        resp = requests.get(f"{API_BASE}/execution", params=params, headers=headers)
        if resp.status_code != 200:
            return (
                True,
                f"Failed to fetch execution data: {resp.text}",
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
                f"Row index {row_in_page} out of range for page {page}",
                None,
                "Error",
                {"display": "none"},
                True,
                None,
            )

        execution = executions[row_in_page]
        exec_id = execution.get("id")

        if not exec_id:
            return (
                True,
                f"Could not get execution ID from row data. Row: {execution}",
                None,
                "Error",
                {"display": "none"},
                True,
                None,
            )

        if col == "logs":
            # Fetch logs from a different endpoint
            resp = requests.get(f"{API_BASE}/execution/{exec_id}/log", headers=headers)
            if resp.status_code != 200:
                return (
                    True,
                    f"Failed to fetch execution logs: {resp.text}",
                    None,
                    "Execution Logs",
                    {"display": "none"},
                    True,
                    None,
                )

            logs_data = resp.json().get("data", [])
            if not logs_data:
                return (
                    True,
                    "No logs found for this execution.",
                    None,
                    "Execution Logs",
                    {"display": "none"},
                    True,
                    None,
                )

            # Parse and format logs for display
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
            else:
                logs_content = str(logs_data)

            log_context = {"type": "execution", "id": exec_id, "status": execution.get("status")}

            # Disable auto-refresh if execution is finished
            disable_refresh = execution.get("status") in ["FINISHED", "FAILED"]

            return (
                True,
                html.Pre(logs_content, style={"whiteSpace": "pre-wrap", "fontSize": "12px"}),
                logs_data,
                "Execution Logs",
                {"display": "inline-block"},
                disable_refresh,
                log_context,
            )
        else:
            # Handle params and results as before
            resp = requests.get(f"{API_BASE}/execution/{exec_id}", headers=headers)
            if resp.status_code != 200:
                return (
                    True,
                    f"Failed to fetch execution details: {resp.text}",
                    None,
                    "Error",
                    {"display": "none"},
                    True,
                    None,
                )

            execution_data = resp.json().get("data", {})
            json_data = execution_data.get(col)

            if json_data is None:
                return (
                    True,
                    f"'{col}' not found in execution data.",
                    None,
                    "Error",
                    {"display": "none"},
                    True,
                    None,
                )

            title = f"Execution {col.capitalize()}"
            return (
                True,
                dcc.Loading(render_json_tree(json_data)),
                json_data,
                title,
                {"display": "none"},
                True,
                None,
            )

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
        State("token-store", "data"),
        State("json-modal", "is_open"),
        prevent_initial_call=True,
    )
    def show_script_logs_modal(cell, token, is_open):
        """Show script logs modal using rowIndex and backend pagination (like executions)."""
        if not cell:
            return is_open, no_update, no_update, no_update, no_update, no_update, no_update

        col = cell.get("colId")
        if col != "logs":
            return is_open, no_update, no_update, no_update, no_update, no_update, no_update

        row_index = cell.get("rowIndex")
        if row_index is None:
            return True, "Could not get row index.", None, "Error", {"display": "none"}, True, None

        headers = {"Authorization": f"Bearer {token}"}
        page_size = 50  # This should match your cacheBlockSize
        page = (row_index // page_size) + 1
        row_in_page = row_index % page_size

        params = {"page": page, "per_page": page_size, "include": "user_name"}
        resp = requests.get(f"{API_BASE}/script", params=params, headers=headers)
        if resp.status_code != 200:
            return (
                True,
                f"Failed to fetch script data: {resp.text}",
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
                f"Row index {row_in_page} out of range for page {page}",
                None,
                "Error",
                {"display": "none"},
                True,
                None,
            )
        script = scripts[row_in_page]
        script_id = script.get("id")
        if not script_id:
            return (
                True,
                f"Could not get script ID from row data. Row: {script}",
                None,
                "Error",
                {"display": "none"},
                True,
                None,
            )
        # Fetch logs for the script
        resp = requests.get(f"{API_BASE}/script/{script_id}/log", headers=headers)
        if resp.status_code != 200:
            return (
                True,
                f"Failed to fetch script logs: {resp.text}",
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
        # Parse and format logs for display
        if isinstance(logs_data, list):
            parsed_logs = []
            for log in logs_data:
                if isinstance(log, dict):
                    register_date = log.get("register_date", "")
                    level = log.get("level", "")
                    text = log.get("text", "")
                    parsed_logs.append(f"[{register_date}] {level}: {text}")
                else:
                    parsed_logs.append(str(log))
            logs_display = html.Pre("\n".join(parsed_logs))
        else:
            logs_display = html.Pre(str(logs_data))
        return (
            True,
            logs_display,
            logs_data,
            "Script Logs",
            {"display": "inline-block"},
            False,
            {"script_id": script_id},
        )


# Legacy callback decorators for backward compatibility (these won't be executed)
