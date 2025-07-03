"""Scripts table callbacks."""

from dash import Input, Output, State
import requests

from ..config import API_BASE, DEFAULT_PAGE_SIZE
from ..utils import parse_date


def register_callbacks(app):
    """Register scripts table callbacks."""

    @app.callback(
        [
            Output("scripts-table", "getRowsResponse"),
            Output("scripts-table-state", "data"),
            Output("scripts-total-count-store", "data"),
        ],
        Input("scripts-table", "getRowsRequest"),
        [State("token-store", "data"), State("role-store", "data")],
        prevent_initial_call=False,
    )
    def get_scripts_rows(request, token, role):
        """Get scripts data for ag-grid with infinite row model with server-side operations."""
        print(
            f"DEBUG: get_scripts_rows called with request={request}, token={bool(token)}, role={role}"
        )
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
                "include": "user_name",
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

            # Build SQL-style filter string with proper escaping
            filter_sql = []
            for field, config in filter_model.items():
                # Skip action columns that don't exist in the API
                if field in ("logs", "edit"):
                    continue

                # Text filter
                if config.get("filterType") == "text":
                    val = config.get("filter", "").replace("'", "''")  # Escape single quotes
                    filter_type = config.get("type", "contains")
                    if val:  # Only add filter if value is not empty
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
                    if val is not None:  # Allow 0 as a valid filter value
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
                print(f"DEBUG: Applied filters: {params['filter']}")

            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.get(f"{API_BASE}/script", params=params, headers=headers)
            print(f"DEBUG: API call to {API_BASE}/script with params {params}")
            print(f"DEBUG: Response status: {resp.status_code}")

            if resp.status_code != 200:
                print(f"DEBUG: API call failed with status {resp.status_code}")
                return {"rowData": [], "rowCount": 0}, {}, 0

            result = resp.json()
            scripts = result.get("data", [])
            total_rows = result.get("total", 0)
            print(f"DEBUG: Received {len(scripts)} scripts, total: {total_rows}")

            # Check if user is admin to add edit buttons
            is_admin = role == "ADMIN"

            tabledata = []
            for script_row in scripts:
                row = script_row.copy()
                row["logs"] = "Show Logs"
                # Only add edit button for admin users
                if is_admin:
                    row["edit"] = "Edit"
                for date_col in ["start_date", "end_date", "created_at", "updated_at"]:
                    if date_col in row:
                        row[date_col] = parse_date(row.get(date_col))
                tabledata.append(row)

            # Store the current table state for use in edit callbacks
            table_state = {
                "sort_model": sort_model,
                "filter_model": filter_model,
                "sort_sql": ",".join(sort_sql) if sort_sql else None,
                "filter_sql": ",".join(filter_sql) if filter_sql else None,
            }

            print(f"DEBUG: Returning {len(tabledata)} scripts to ag-grid, rowCount: {total_rows}")
            return {"rowData": tabledata, "rowCount": total_rows}, table_state, total_rows

        except Exception as e:
            print(f"Error in get_scripts_rows: {str(e)}")
            return {"rowData": [], "rowCount": 0}, {}, 0

    @app.callback(
        [
            Output("scripts-table", "getRowsResponse", allow_duplicate=True),
            Output("scripts-table-state", "data", allow_duplicate=True),
            Output("scripts-total-count-store", "data", allow_duplicate=True),
        ],
        Input("refresh-scripts-btn", "n_clicks"),
        [State("token-store", "data"), State("role-store", "data")],
        prevent_initial_call=True,
    )
    def refresh_scripts_table(n_clicks, token, role):
        """Manually refresh the scripts table."""
        if not n_clicks or not token:
            return {"rowData": [], "rowCount": 0}, {}, 0

        try:
            # For infinite row model, we need to trigger a refresh by clearing the cache
            # This is done by returning a fresh response for the first page
            headers = {"Authorization": f"Bearer {token}"}

            params = {
                "page": 1,
                "per_page": DEFAULT_PAGE_SIZE,
                "include": "user_name",
            }

            resp = requests.get(f"{API_BASE}/script", params=params, headers=headers)

            if resp.status_code != 200:
                return {"rowData": [], "rowCount": 0}, {}, 0

            result = resp.json()
            scripts = result.get("data", [])
            total_rows = result.get("total", 0)

            # Check if user is admin to add edit buttons
            is_admin = role == "ADMIN"

            tabledata = []
            for script_row in scripts:
                row = script_row.copy()
                row["logs"] = "Show Logs"
                # Only add edit button for admin users
                if is_admin:
                    row["edit"] = "Edit"
                for date_col in ["start_date", "end_date", "created_at", "updated_at"]:
                    if date_col in row:
                        row[date_col] = parse_date(row.get(date_col))
                tabledata.append(row)

            # For refresh, we don't have sort/filter state, so return empty state
            return {"rowData": tabledata, "rowCount": total_rows}, {}, total_rows

        except Exception as e:
            print(f"Error in refresh_scripts_table: {str(e)}")
            return {"rowData": [], "rowCount": 0}, {}, 0

    @app.callback(
        Output("scripts-total-count", "children"),
        Input("scripts-total-count-store", "data"),
        prevent_initial_call=True,
    )
    def update_scripts_total_display(total_count):
        """Update the scripts total count display."""
        return f"Total: {total_count:,}"
