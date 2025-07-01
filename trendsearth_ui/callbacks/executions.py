"""Executions table callbacks."""

from dash import Input, Output, State
import requests

from ..config import API_BASE, DEFAULT_PAGE_SIZE
from ..utils import parse_date


def register_callbacks(app):
    """Register executions table callbacks."""

    @app.callback(
        Output("executions-table", "getRowsResponse"),
        Input("executions-table", "getRowsRequest"),
        State("token-store", "data"),
        prevent_initial_call=True,
    )
    def get_execution_rows(request, token):
        """Get execution data for ag-grid with infinite row model."""
        try:
            if not request or not token:
                return {"rowData": [], "rowCount": 0}

            start_row = request.get("startRow", 0)
            end_row = request.get("endRow", 10000)
            page_size = end_row - start_row
            page = (start_row // page_size) + 1

            sort_model = request.get("sortModel", [])
            filter_model = request.get("filterModel", {})

            params = {
                "page": page,
                "per_page": page_size,
                "exclude": "params,results",
                "include": "user_name,script_name",
            }

            # Build SQL-style sort string
            sort_sql = []
            for sort in sort_model:
                col = sort.get("colId")
                direction = sort.get("sort", "asc")
                if direction == "desc":
                    sort_sql.append(f"{col} desc")
                else:
                    sort_sql.append(f"{col} asc")
            if sort_sql:
                params["sort"] = ",".join(sort_sql)

            # Build SQL-style filter string
            filter_sql = []
            for field, config in filter_model.items():
                # Text filter
                if config.get("filterType") == "text":
                    val = config.get("filter", "")
                    filter_type = config.get("type", "contains")
                    if filter_type == "equals":
                        filter_sql.append(f"{field}='{val}'")
                    elif filter_type == "notEqual":
                        filter_sql.append(f"{field}!='{val}'")
                    elif filter_type == "contains":
                        filter_sql.append(f"{field} like '%{val}%'")
                    elif filter_type == "notContains":
                        filter_sql.append(f"{field} not like '%{val}%'")
                    elif filter_type == "startsWith":
                        filter_sql.append(f"{field} like '{val}%'")
                    elif filter_type == "endsWith":
                        filter_sql.append(f"{field} like '%{val}'")
                # Number filter
                elif config.get("filterType") == "number":
                    val = config.get("filter")
                    filter_type = config.get("type", "equals")
                    if filter_type == "equals":
                        filter_sql.append(f"{field}={val}")
                    elif filter_type == "notEqual":
                        filter_sql.append(f"{field}!={val}")
                    elif filter_type == "greaterThan":
                        filter_sql.append(f"{field}>{val}")
                    elif filter_type == "lessThan":
                        filter_sql.append(f"{field}<{val}")
                    elif filter_type == "greaterThanOrEqual":
                        filter_sql.append(f"{field}>={val}")
                    elif filter_type == "lessThanOrEqual":
                        filter_sql.append(f"{field}<={val}")
                # Date filter
                elif config.get("filterType") == "date":
                    date_from = config.get("dateFrom")
                    date_to = config.get("dateTo")
                    filter_type = config.get("type", "equals")
                    if filter_type == "equals" and date_from:
                        filter_sql.append(f"{field}='{date_from}'")
                    elif filter_type == "notEqual" and date_from:
                        filter_sql.append(f"{field}!='{date_from}'")
                    elif filter_type == "greaterThan" and date_from:
                        filter_sql.append(f"{field}>'{date_from}'")
                    elif filter_type == "lessThan" and date_from:
                        filter_sql.append(f"{field}<'{date_from}'")
                    elif filter_type == "greaterThanOrEqual" and date_from:
                        filter_sql.append(f"{field}>='{date_from}'")
                    elif filter_type == "lessThanOrEqual" and date_from:
                        filter_sql.append(f"{field}<='{date_from}'")
                    elif filter_type == "inRange":
                        if date_from:
                            filter_sql.append(f"{field}>='{date_from}'")
                        if date_to:
                            filter_sql.append(f"{field}<='{date_to}'")
            if filter_sql:
                params["filter"] = ",".join(filter_sql)

            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.get(f"{API_BASE}/execution", params=params, headers=headers)

            if resp.status_code != 200:
                return {"rowData": [], "rowCount": 0}

            result = resp.json()
            executions = result.get("data", [])
            total_rows = result.get("total", 0)

            tabledata = []
            for exec_row in executions:
                row = exec_row.copy()
                row["params"] = "Show Params"
                row["results"] = "Show Results"
                row["logs"] = "Show Logs"
                row["map"] = "Show Map"
                for date_col in ["start_date", "end_date"]:
                    if date_col in row:
                        row[date_col] = parse_date(row.get(date_col))
                tabledata.append(row)

            return {"rowData": tabledata, "rowCount": total_rows}

        except Exception as e:
            print(f"Error in get_execution_rows: {str(e)}")
            return {"rowData": [], "rowCount": 0}

    @app.callback(
        Output("executions-table", "getRowsResponse", allow_duplicate=True),
        Output("executions-countdown-interval", "n_intervals"),
        Input("refresh-executions-btn", "n_clicks"),
        [
            State("token-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def refresh_executions_table(n_clicks, token):
        """Manually refresh the executions table."""
        if not n_clicks or not token:
            return {"rowData": [], "rowCount": 0}, 0

        # For infinite row model, we need to trigger a refresh by clearing the cache
        # This is done by returning a fresh response for the first page
        headers = {"Authorization": f"Bearer {token}"}

        params = {
            "page": 1,
            "per_page": DEFAULT_PAGE_SIZE,
            "exclude": "params,results",
            "include": "script_name,user_name",
        }

        resp = requests.get(f"{API_BASE}/execution", params=params, headers=headers)

        if resp.status_code != 200:
            return {"rowData": [], "rowCount": 0}, 0

        result = resp.json()
        executions = result.get("data", [])
        total_rows = result.get("total", 0)

        tabledata = []
        for exec_row in executions:
            row = exec_row.copy()
            row["params"] = "Show Params"
            row["results"] = "Show Results"
            row["logs"] = "Show Logs"
            row["map"] = "Show Map"
            for date_col in ["start_date", "end_date"]:
                if date_col in row:
                    row[date_col] = parse_date(row.get(date_col))
            tabledata.append(row)

        # Reset countdown timer to 0 when manually refreshed
        return {"rowData": tabledata, "rowCount": total_rows}, 0

    @app.callback(
        Output("executions-table", "getRowsResponse", allow_duplicate=True),
        Input("executions-auto-refresh-interval", "n_intervals"),
        [
            State("token-store", "data"),
            State("active-tab-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def auto_refresh_executions_table(_n_intervals, token, active_tab):
        """Auto-refresh the executions table."""
        # Only refresh if executions tab is active
        if active_tab != "executions" or not token:
            return {"rowData": [], "rowCount": 0}

        headers = {"Authorization": f"Bearer {token}"}

        params = {
            "page": 1,
            "per_page": DEFAULT_PAGE_SIZE,
            "exclude": "params,results",
            "include": "script_name,user_name",
        }

        resp = requests.get(f"{API_BASE}/execution", params=params, headers=headers)

        if resp.status_code != 200:
            return {"rowData": [], "rowCount": 0}

        result = resp.json()
        executions = result.get("data", [])
        total_rows = result.get("total", 0)

        tabledata = []
        for exec_row in executions:
            row = exec_row.copy()
            row["params"] = "Show Params"
            row["results"] = "Show Results"
            row["logs"] = "Show Logs"
            row["map"] = "Show Map"
            for date_col in ["start_date", "end_date"]:
                if date_col in row:
                    row[date_col] = parse_date(row.get(date_col))
            tabledata.append(row)

        return {"rowData": tabledata, "rowCount": total_rows}

    @app.callback(
        Output("executions-countdown", "children"),
        Input("executions-countdown-interval", "n_intervals"),
        State("active-tab-store", "data"),
        prevent_initial_call=True,
    )
    def update_executions_countdown(n_intervals, active_tab):
        """Update the executions auto-refresh countdown."""
        if active_tab != "executions":
            return "30s"

        # Calculate remaining seconds (30 second cycle)
        remaining = 30 - (n_intervals % 30)
        return f"{remaining}s"


# Legacy callback decorators for backward compatibility (these won't be executed)
