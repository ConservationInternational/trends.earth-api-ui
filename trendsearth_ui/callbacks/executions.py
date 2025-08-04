"""Executions table callbacks."""

from dash import Input, Output, State, no_update
import requests  # noqa: F401

from ..config import DEFAULT_PAGE_SIZE
from ..utils import parse_date


def format_duration(duration_seconds):
    """Format duration from seconds to Hours:Minutes:Seconds format."""
    if duration_seconds is None or duration_seconds == 0:
        return "-"

    try:
        # Convert to int if it's a float/string
        duration_seconds = int(float(duration_seconds))

        hours = duration_seconds // 3600
        remaining_seconds = duration_seconds % 3600
        minutes = remaining_seconds // 60
        seconds = remaining_seconds % 60

        return f"{hours}:{minutes:02d}:{seconds:02d}"
    except (ValueError, TypeError):
        return "-"


def register_callbacks(app):
    """Register executions table callbacks."""

    @app.callback(
        [
            Output("executions-table", "getRowsResponse"),
            Output("executions-table-state", "data"),
            Output("executions-total-count-store", "data"),
        ],
        Input("executions-table", "getRowsRequest"),
        [
            State("token-store", "data"),
            State("role-store", "data"),
            State("user-timezone-store", "data"),
        ],
        prevent_initial_call=False,
    )
    def get_execution_rows(request, token, role, user_timezone):
        """Get execution data for ag-grid with infinite row model."""
        try:
            if not token:
                return {"rowData": [], "rowCount": 0}, {}, 0
            if not request:
                # Return empty data but let ag-grid know there might be data
                return {"rowData": [], "rowCount": None}, {}, 0

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
                "include": "script_name,user_id,duration",
            }

            # Add admin-only fields if user is admin or superadmin
            if role in ["ADMIN", "SUPERADMIN"]:
                params["include"] += ",user_name,user_email"

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

            # Build SQL-style filter string for general filters
            filter_sql = []
            for field, config in filter_model.items():
                if field == "status" and config.get("filterType") == "text":
                    # Status filter - can use either dedicated parameter or general filter
                    val = config.get("filter", "").strip()
                    if val and val.upper() in ["PENDING", "RUNNING", "FINISHED", "FAILED"]:
                        filter_sql.append(f"status='{val.upper()}'")
                elif config.get("filterType") == "text":
                    # General text filters (user_name, user_email, user_id, etc.)
                    filter_type = config.get("type", "contains")
                    val = config.get("filter", "").strip()
                    if val:
                        if filter_type == "contains":
                            filter_sql.append(f"{field} like '%{val}%'")
                        elif filter_type == "equals":
                            filter_sql.append(f"{field}='{val}'")
                        elif filter_type == "notEquals":
                            filter_sql.append(f"{field}!='{val}'")
                        elif filter_type == "startsWith":
                            filter_sql.append(f"{field} like '{val}%'")
                        elif filter_type == "endsWith":
                            filter_sql.append(f"{field} like '%{val}'")
                elif config.get("filterType") == "number":
                    # Number filters
                    filter_type = config.get("type", "equals")
                    val = config.get("filter")
                    if val is not None:
                        if filter_type == "equals":
                            filter_sql.append(f"{field}={val}")
                        elif filter_type == "notEqual":
                            filter_sql.append(f"{field}!={val}")
                        elif filter_type == "greaterThan":
                            filter_sql.append(f"{field}>{val}")
                        elif filter_type == "greaterThanOrEqual":
                            filter_sql.append(f"{field}>={val}")
                        elif filter_type == "lessThan":
                            filter_sql.append(f"{field}<{val}")
                        elif filter_type == "lessThanOrEqual":
                            filter_sql.append(f"{field}<={val}")
                elif field in ["start_date", "end_date"] and config.get("filterType") == "date":
                    # Date filters - convert to API format
                    date_from = config.get("dateFrom")
                    date_to = config.get("dateTo")
                    filter_type = config.get("type", "equals")

                    if field == "start_date" and date_from:
                        if filter_type in ["greaterThan", "greaterThanOrEqual"]:
                            params["start_date_gte"] = date_from
                        elif filter_type in ["lessThan", "lessThanOrEqual"]:
                            params["start_date_lte"] = date_from
                    elif field == "end_date" and date_from:
                        if filter_type in ["greaterThan", "greaterThanOrEqual"]:
                            params["end_date_gte"] = date_from
                        elif filter_type in ["lessThan", "lessThanOrEqual"]:
                            params["end_date_lte"] = date_from

                    # Handle date range filters
                    if filter_type == "inRange":
                        if field == "start_date":
                            if date_from:
                                params["start_date_gte"] = date_from
                            if date_to:
                                params["start_date_lte"] = date_to
                        elif field == "end_date":
                            if date_from:
                                params["end_date_gte"] = date_from
                            if date_to:
                                params["end_date_lte"] = date_to

            # Add general filters to params
            if filter_sql:
                params["filter"] = ",".join(filter_sql)

            from ..utils.helpers import make_authenticated_request

            resp = make_authenticated_request("/execution", token, params=params)

            if resp.status_code != 200:
                return {"rowData": [], "rowCount": 0}, {}, 0

            result = resp.json()
            executions = result.get("data", [])
            total_rows = result.get("total", 0)

            tabledata = []
            for exec_row in executions:
                row = exec_row.copy()
                row["params"] = "Show Params"
                row["results"] = "Show Results"
                row["logs"] = "Show Logs"
                # Add docker logs column for admin/superadmin users only
                if role in ["ADMIN", "SUPERADMIN"]:
                    row["docker_logs"] = "Show Docker Logs"
                row["map"] = "Show Map"

                # Format duration in Hours:Minutes:Seconds format
                if "duration" in row:
                    row["duration"] = format_duration(row.get("duration"))

                for date_col in ["start_date", "end_date"]:
                    if date_col in row:
                        row[date_col] = parse_date(row.get(date_col), user_timezone)
                tabledata.append(row)

            # Store the current table state for use in modal callbacks
            table_state = {
                "sort_model": sort_model,
                "filter_model": filter_model,
                "sort_sql": ",".join(sort_sql) if sort_sql else None,
                "filter_sql": ",".join(filter_sql) if filter_sql else None,
            }

            return {"rowData": tabledata, "rowCount": total_rows}, table_state, total_rows

        except Exception as e:
            print(f"Error in get_execution_rows: {str(e)}")
            return {"rowData": [], "rowCount": 0}, {}, 0

    @app.callback(
        [
            Output("executions-table", "getRowsResponse", allow_duplicate=True),
            Output("executions-table-state", "data", allow_duplicate=True),
            Output("executions-countdown-interval", "n_intervals"),
            Output("executions-total-count-store", "data", allow_duplicate=True),
        ],
        Input("refresh-executions-btn", "n_clicks"),
        [
            State("token-store", "data"),
            State("role-store", "data"),
            State("executions-table-state", "data"),
            State("user-timezone-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def refresh_executions_table(n_clicks, token, role, table_state, user_timezone):
        """Manually refresh the executions table."""
        if not n_clicks or not token:
            return {"rowData": [], "rowCount": 0}, {}, 0, 0

        # For infinite row model, we need to trigger a refresh by clearing the cache
        # This is done by returning a fresh response for the first page
        params = {
            "page": 1,
            "per_page": DEFAULT_PAGE_SIZE,
            "exclude": "params,results",
            "include": "script_name,user_id,duration",
        }

        # Add admin-only fields if user is admin or superadmin
        if role in ["ADMIN", "SUPERADMIN"]:
            params["include"] += ",user_name,user_email"

        # Preserve existing sort and filter settings if available
        if table_state:
            if table_state.get("sort_sql"):
                params["sort"] = table_state["sort_sql"]
            if table_state.get("filter_sql"):
                params["filter"] = table_state["filter_sql"]

        from ..utils.helpers import make_authenticated_request

        resp = make_authenticated_request("/execution", token, params=params)

        if resp.status_code != 200:
            return {"rowData": [], "rowCount": 0}, {}, 0, 0

        result = resp.json()
        executions = result.get("data", [])
        total_rows = result.get("total", 0)

        tabledata = []
        for exec_row in executions:
            row = exec_row.copy()
            row["params"] = "Show Params"
            row["results"] = "Show Results"
            row["logs"] = "Show Logs"
            # Add docker logs column for admin/superadmin users only
            if role in ["ADMIN", "SUPERADMIN"]:
                row["docker_logs"] = "Show Docker Logs"
            row["map"] = "Show Map"

            # Format duration in Hours:Minutes:Seconds format
            if "duration" in row:
                row["duration"] = format_duration(row.get("duration"))

            for date_col in ["start_date", "end_date"]:
                if date_col in row:
                    row[date_col] = parse_date(row.get(date_col), user_timezone)
            tabledata.append(row)

        # Reset countdown timer to 0 when manually refreshed
        # Return data with preserved table state
        return {"rowData": tabledata, "rowCount": total_rows}, table_state or {}, 0, total_rows

    @app.callback(
        [
            Output("executions-table", "getRowsResponse", allow_duplicate=True),
            Output("executions-table-state", "data", allow_duplicate=True),
            Output("executions-total-count-store", "data", allow_duplicate=True),
        ],
        Input("executions-auto-refresh-interval", "n_intervals"),
        [
            State("token-store", "data"),
            State("role-store", "data"),
            State("active-tab-store", "data"),
            State("executions-table-state", "data"),  # Preserve existing table state
            State("user-timezone-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def auto_refresh_executions_table(
        _n_intervals, token, role, active_tab, table_state, user_timezone
    ):
        """Auto-refresh the executions table with preserved sorting/filtering state."""
        # Guard: Skip if not logged in (prevents execution after logout)
        if not token:
            return {"rowData": [], "rowCount": 0}, {}, 0

        # Only refresh if executions tab is active
        if active_tab != "executions":
            return {"rowData": [], "rowCount": 0}, {}, 0

        try:
            params = {
                "page": 1,
                "per_page": DEFAULT_PAGE_SIZE,
                "exclude": "params,results",
                "include": "script_name,user_id,duration",
            }

            # Add admin-only fields if user is admin or superadmin
            if role in ["ADMIN", "SUPERADMIN"]:
                params["include"] += ",user_name,user_email"

            # Preserve existing sort and filter settings if available
            if table_state:
                if table_state.get("sort_sql"):
                    params["sort"] = table_state["sort_sql"]
                if table_state.get("filter_sql"):
                    params["filter"] = table_state["filter_sql"]

            from ..utils.helpers import make_authenticated_request

            resp = make_authenticated_request("/execution", token, params=params)

            if resp.status_code != 200:
                return {"rowData": [], "rowCount": 0}, table_state or {}, 0

            result = resp.json()
            executions = result.get("data", [])
            total_rows = result.get("total", 0)

            tabledata = []
            for exec_row in executions:
                row = exec_row.copy()
                row["params"] = "Show Params"
                row["results"] = "Show Results"
                row["logs"] = "Show Logs"
                # Add docker logs column for admin/superadmin users only
                if role in ["ADMIN", "SUPERADMIN"]:
                    row["docker_logs"] = "Show Docker Logs"
                row["map"] = "Show Map"

                # Format duration in Hours:Minutes:Seconds format
                if "duration" in row:
                    row["duration"] = format_duration(row.get("duration"))

                for date_col in ["start_date", "end_date"]:
                    if date_col in row:
                        row[date_col] = parse_date(row.get(date_col), user_timezone)
                tabledata.append(row)

            # Preserve table state from current state
            return {"rowData": tabledata, "rowCount": total_rows}, table_state or {}, total_rows

        except Exception as e:
            print(f"Error in auto_refresh_executions_table: {str(e)}")
            return {"rowData": [], "rowCount": 0}, table_state or {}, 0

    @app.callback(
        Output("executions-countdown", "children"),
        Input("executions-countdown-interval", "n_intervals"),
        State("active-tab-store", "data"),
        prevent_initial_call=True,
    )
    def update_executions_countdown(n_intervals, active_tab):
        """Update the executions auto-refresh countdown."""
        # Guard: Skip if not logged in (prevents execution after logout)
        if active_tab is None:
            return no_update

        if active_tab != "executions":
            return "30s"

        # Calculate remaining seconds (30 second cycle)
        remaining = 30 - (n_intervals % 30)
        return f"{remaining}s"

    @app.callback(
        Output("executions-total-count", "children"),
        Input("executions-total-count-store", "data"),
        prevent_initial_call=True,
    )
    def update_executions_total_display(total_count):
        """Update the executions total count display."""
        return f"Total: {total_count:,}"


# Legacy callback decorators for backward compatibility (these won't be executed)
