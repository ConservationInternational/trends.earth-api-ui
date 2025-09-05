"""Executions table callbacks."""

from dash import Input, Output, State, html, no_update
import requests  # noqa: F401

from ..config import DEFAULT_PAGE_SIZE
from ..utils import make_authenticated_request, parse_date


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


def process_execution_data(executions, role, user_timezone):
    """Process execution data consistently across all callbacks.

    Args:
        executions: List of execution dictionaries from API
        role: User role for admin-specific fields
        user_timezone: User's timezone for date formatting

    Returns:
        List of processed execution dictionaries ready for AG-Grid
    """
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

    return tabledata


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
            State("executions-status-filter-selected", "data"),
        ],
        prevent_initial_call=False,
    )
    def get_execution_rows(request, token, role, user_timezone, status_filter_selected):
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

            # Add custom filter to filter_model if active
            if status_filter_selected:
                filter_model["status"] = {"filterType": "set", "values": status_filter_selected}

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
                if config.get("filterType") == "set":
                    # Set filters (checkboxes) - handle multiple selected values
                    values = config.get("values", [])
                    if values:
                        # Create OR condition for multiple selected values
                        value_conditions = [f"{field}='{val}'" for val in values]
                        if value_conditions:
                            filter_sql.append(f"({' OR '.join(value_conditions)})")
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
                    # Number filters (for duration column)
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

            # Process execution data consistently
            tabledata = process_execution_data(executions, role, user_timezone)

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
            State("executions-status-filter-selected", "data"),
        ],
        prevent_initial_call=True,
    )
    def refresh_executions_table(
        n_clicks, token, role, table_state, user_timezone, status_filter_selected
    ):
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

        # Add custom filter from the status filter if active (similar to main callback)
        if status_filter_selected and table_state:
            # Add custom filter to existing table state filter logic
            filter_model = table_state.get("filter_model", {})
            filter_model["status"] = {"filterType": "set", "values": status_filter_selected}
            # Rebuild filter SQL from the updated filter model (simplified approach)
            filter_sql = []
            for field, config in filter_model.items():
                if config.get("filterType") == "set":
                    values = config.get("values", [])
                    if values:
                        value_conditions = [f"{field}='{val}'" for val in values]
                        if value_conditions:
                            filter_sql.append(f"({' OR '.join(value_conditions)})")
            if filter_sql:
                params["filter"] = ",".join(filter_sql)

        from ..utils.helpers import make_authenticated_request

        resp = make_authenticated_request("/execution", token, params=params)

        if resp.status_code != 200:
            return {"rowData": [], "rowCount": 0}, {}, 0, 0

        result = resp.json()
        executions = result.get("data", [])
        total_rows = result.get("total", 0)

        # Process execution data consistently
        tabledata = process_execution_data(executions, role, user_timezone)

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
            State("executions-status-filter-selected", "data"),
        ],
        prevent_initial_call=True,
    )
    def auto_refresh_executions_table(
        _n_intervals, token, role, active_tab, table_state, user_timezone, status_filter_selected
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

            # Add custom filter from the status filter if active (similar to main callback)
            if status_filter_selected and table_state:
                # Add custom filter to existing table state filter logic
                filter_model = table_state.get("filter_model", {})
                filter_model["status"] = {"filterType": "set", "values": status_filter_selected}
                # Rebuild filter SQL from the updated filter model (simplified approach)
                filter_sql = []
                for field, config in filter_model.items():
                    if config.get("filterType") == "set":
                        values = config.get("values", [])
                        if values:
                            value_conditions = [f"{field}='{val}'" for val in values]
                            if value_conditions:
                                filter_sql.append(f"({' OR '.join(value_conditions)})")
                if filter_sql:
                    params["filter"] = ",".join(filter_sql)

            from ..utils.helpers import make_authenticated_request

            resp = make_authenticated_request("/execution", token, params=params)

            if resp.status_code != 200:
                return {"rowData": [], "rowCount": 0}, table_state or {}, 0

            result = resp.json()
            executions = result.get("data", [])
            total_rows = result.get("total", 0)

            # Process execution data consistently
            tabledata = process_execution_data(executions, role, user_timezone)

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

    @app.callback(
        [
            Output("cancel-execution-modal", "is_open"),
            Output("cancel-execution-id", "children"),
            Output("cancel-execution-script", "children"),
            Output("cancel-execution-status", "children"),
            Output("cancel-execution-store", "data"),
        ],
        Input("executions-table", "cellClicked"),
        [
            State("cancel-execution-modal", "is_open"),
            State("token-store", "data"),
            State("executions-table-state", "data"),
            State("user-store", "data"),
            State("role-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def show_cancel_confirmation_modal(cell, is_open, token, table_state, user_data, role):
        """Show the cancel confirmation modal when status is clicked for cancellable executions."""
        print("🎯 Cancel modal callback triggered!")
        print(f"   Cell: {cell}")

        if not cell:
            print("❌ No cell data, returning current state")
            return is_open, no_update, no_update, no_update, no_update

        col = cell.get("colId")
        print(f"   Column ID: {col}")

        if col != "status":
            print("❌ Column is not 'status', returning current state")
            return is_open, no_update, no_update, no_update, no_update

        # Get row data
        row_data = cell.get("data")
        execution_id = None
        script_name = "Unknown Script"
        status = "Unknown"
        execution_user_id = None

        print(f"   Row data from cell: {row_data}")

        if row_data:
            execution_id = row_data.get("id")
            script_name = row_data.get("script_name", "Unknown Script")
            status = row_data.get("status", "Unknown")
            execution_user_id = row_data.get("user_id")
            print(
                f"   ✅ Got data from cell - ID: {execution_id}, Script: {script_name}, Status: {status}, User: {execution_user_id}"
            )
        else:
            print("🔍 No row data in cell, trying API fallback like logs callback...")

            # Use exact same pattern as logs callback - get row index and try pagination
            row_index = cell.get("rowIndex", 0)

            # Calculate which page this row is on (same logic as logs callback)
            page_size = 50  # This should match DEFAULT_PAGE_SIZE
            page = (row_index // page_size) + 1
            row_in_page = row_index % page_size

            print(f"   Row index: {row_index}")
            print(f"   Page: {page}, row_in_page: {row_in_page}")

            if token:
                try:
                    # Build params exactly like logs callback does
                    params = {
                        "page": page,
                        "per_page": page_size,
                        "exclude": "params,results",
                        "include": "script_name,user_name,user_email,user_id,duration",
                    }

                    # Add table state params exactly like logs callback
                    if table_state:
                        if table_state.get("sort_sql"):
                            params["sort"] = table_state["sort_sql"]
                        if table_state.get("filter_sql"):
                            params["filter"] = table_state["filter_sql"]

                    print(f"   API params: {params}")

                    # Make API request exactly like logs callback
                    response = make_authenticated_request(
                        "/execution",
                        token,
                        method="GET",
                        params=params,
                        timeout=10,
                    )

                    print(f"   API response status: {response.status_code}")

                    if response.status_code == 200:
                        data = response.json()
                        results = data.get(
                            "data", []
                        )  # Note: logs callback uses "data" not "results"
                        print(f"   Found {len(results)} executions on page {page}")

                        # Get the specific execution at the row_in_page index
                        if row_in_page < len(results):
                            execution = results[row_in_page]
                            execution_id = execution.get("id")
                            script_name = execution.get("script_name", "Unknown Script")
                            status = execution.get("status", "Unknown")
                            execution_user_id = execution.get("user_id")
                            print(
                                f"   ✅ Found execution at row_in_page {row_in_page} - ID: {execution_id}, Script: {script_name}, Status: {status}, User: {execution_user_id}"
                            )
                        else:
                            print(
                                f"   ❌ Row {row_in_page} not found in page with {len(results)} executions"
                            )
                    else:
                        print(f"   ❌ API request failed: {response.status_code}")

                except Exception as e:
                    print(f"   ❌ Error in API fallback: {str(e)}")

        if not execution_id:
            print("❌ Still no execution_id found, returning current state")
            return is_open, no_update, no_update, no_update, no_update

        # Check if status is cancellable
        cancellable_statuses = ["READY", "PENDING", "RUNNING"]
        if status not in cancellable_statuses:
            print(f"❌ Status '{status}' is not cancellable, returning current state")
            return is_open, no_update, no_update, no_update, no_update

        # Check permissions: user can cancel their own tasks OR user is admin/superadmin
        current_user_id = user_data.get("id") if user_data else None
        is_admin = role in ["ADMIN", "SUPERADMIN"] if role else False

        if not is_admin and execution_user_id != current_user_id:
            print(
                f"❌ Permission denied: user {current_user_id} cannot cancel execution by user {execution_user_id}"
            )
            return is_open, no_update, no_update, no_update, no_update

        print(
            f"✅ Permission granted and status is cancellable! Opening modal for execution {execution_id}"
        )

        execution_data = {
            "id": execution_id,
            "script": script_name,
            "status": status,
        }

        return True, execution_id, script_name, status, execution_data

    @app.callback(
        Output("cancel-execution-modal", "is_open", allow_duplicate=True),
        Input("cancel-execution-close-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def close_cancel_modal(n_clicks):
        """Close the cancel confirmation modal."""
        if n_clicks:
            return False
        return no_update

    @app.callback(
        [
            Output("cancel-execution-modal", "is_open", allow_duplicate=True),
            Output("cancel-execution-result-modal", "is_open"),
            Output("cancel-execution-result-body", "children"),
            Output("executions-table", "getRowsResponse", allow_duplicate=True),
        ],
        Input("cancel-execution-confirm-btn", "n_clicks"),
        [
            State("cancel-execution-store", "data"),
            State("token-store", "data"),
            State("executions-table-state", "data"),
            State("role-store", "data"),
            State("user-timezone-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def cancel_execution(n_clicks, execution_data, token, table_state, role, user_timezone):
        """Cancel the execution and show the result."""
        if not n_clicks or not execution_data or not token:
            return no_update, no_update, no_update, no_update

        execution_id = execution_data.get("id")
        if not execution_id:
            return no_update, no_update, no_update, no_update

        try:
            from ..utils.helpers import make_authenticated_request

            # Make the cancel request
            resp = make_authenticated_request(
                f"/execution/{execution_id}/cancel", token, method="POST"
            )

            if resp.status_code == 200:
                result = resp.json()
                execution_info = result.get("data", {}).get("execution", {})
                cancellation_details = result.get("data", {}).get("cancellation_details", {})

                # Format the result for display
                result_content = []

                # Execution info
                result_content.extend(
                    [
                        html.H5("Execution Cancelled Successfully", className="text-success mb-3"),
                        html.Div(
                            [
                                html.Strong("Execution ID: "),
                                html.Span(execution_info.get("id", "Unknown")),
                            ],
                            className="mb-2",
                        ),
                        html.Div(
                            [
                                html.Strong("Script: "),
                                html.Span(execution_info.get("script_id", "Unknown")),
                            ],
                            className="mb-2",
                        ),
                        html.Div(
                            [
                                html.Strong("Previous Status: "),
                                html.Span(cancellation_details.get("previous_status", "Unknown")),
                            ],
                            className="mb-2",
                        ),
                        html.Div(
                            [
                                html.Strong("New Status: "),
                                html.Span(
                                    execution_info.get("status", "Unknown"),
                                    className="text-danger fw-bold",
                                ),
                            ],
                            className="mb-4",
                        ),
                    ]
                )

                # Docker service info
                docker_stopped = cancellation_details.get("docker_service_stopped", False)
                container_stopped = cancellation_details.get("docker_container_stopped", False)

                result_content.extend(
                    [
                        html.H6("Infrastructure Cleanup", className="mb-2"),
                        html.Div(
                            [
                                html.I(
                                    className=f"fas fa-{'check text-success' if docker_stopped else 'times text-danger'} me-2"
                                ),
                                f"Docker service {'stopped' if docker_stopped else 'not found/stopped'}",
                            ],
                            className="mb-1",
                        ),
                        html.Div(
                            [
                                html.I(
                                    className=f"fas fa-{'check text-success' if container_stopped else 'times text-warning'} me-2"
                                ),
                                f"Docker container {'stopped' if container_stopped else 'not found/stopped'}",
                            ],
                            className="mb-3",
                        ),
                    ]
                )

                # GEE tasks info
                gee_tasks = cancellation_details.get("gee_tasks_cancelled", [])
                if gee_tasks:
                    result_content.extend(
                        [
                            html.H6("Google Earth Engine Tasks", className="mb-2"),
                            html.Div(
                                [
                                    html.P(
                                        f"Found and processed {len(gee_tasks)} GEE tasks:",
                                        className="mb-2",
                                    ),
                                ]
                            ),
                        ]
                    )

                    for task in gee_tasks:
                        task_success = task.get("success", False)
                        result_content.append(
                            html.Div(
                                [
                                    html.I(
                                        className=f"fas fa-{'check text-success' if task_success else 'times text-danger'} me-2"
                                    ),
                                    html.Code(task.get("task_id", "Unknown"), className="me-2"),
                                    html.Span(
                                        f"Status: {task.get('status', 'Unknown')}",
                                        className="text-muted",
                                    ),
                                    html.Div(task.get("error", ""), className="text-danger small")
                                    if task.get("error")
                                    else None,
                                ],
                                className="mb-1",
                            )
                        )
                else:
                    result_content.append(
                        html.Div(
                            [
                                html.H6("Google Earth Engine Tasks", className="mb-2"),
                                html.P(
                                    "No GEE tasks found in execution logs.", className="text-muted"
                                ),
                            ],
                            className="mb-3",
                        )
                    )

                # Errors if any
                errors = cancellation_details.get("errors", [])
                if errors:
                    result_content.extend(
                        [
                            html.H6("Errors Encountered", className="mb-2 text-warning"),
                            html.Ul([html.Li(error, className="text-warning") for error in errors]),
                        ]
                    )

            else:
                # Error response
                error_data = (
                    resp.json() if resp.headers.get("content-type") == "application/json" else {}
                )
                result_content = [
                    html.H5("Cancellation Failed", className="text-danger mb-3"),
                    html.Div(
                        [
                            html.Strong("Error: "),
                            html.Span(error_data.get("detail", f"HTTP {resp.status_code}")),
                        ],
                        className="mb-2",
                    ),
                    html.Div(
                        [html.Strong("Execution ID: "), html.Span(execution_id)], className="mb-2"
                    ),
                ]

            # Refresh the table data
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

            refresh_resp = make_authenticated_request("/execution", token, params=params)
            table_response = {"rowData": [], "rowCount": 0}

            if refresh_resp.status_code == 200:
                refresh_result = refresh_resp.json()
                refresh_executions = refresh_result.get("data", [])
                total_rows = refresh_result.get("total", 0)

                # Process execution data consistently
                tabledata = process_execution_data(refresh_executions, role, user_timezone)

                table_response = {"rowData": tabledata, "rowCount": total_rows}

            return False, True, result_content, table_response

        except Exception as e:
            error_content = [
                html.H5("Cancellation Failed", className="text-danger mb-3"),
                html.Div([html.Strong("Error: "), html.Span(str(e))], className="mb-2"),
                html.Div(
                    [html.Strong("Execution ID: "), html.Span(execution_id)], className="mb-2"
                ),
            ]
            return False, True, error_content, no_update

    @app.callback(
        Output("cancel-execution-result-modal", "is_open", allow_duplicate=True),
        Input("cancel-result-close-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def close_cancel_result_modal(n_clicks):
        """Close the cancel result modal."""
        if n_clicks:
            return False
        return no_update


# Legacy callback decorators for backward compatibility (these won't be executed)
