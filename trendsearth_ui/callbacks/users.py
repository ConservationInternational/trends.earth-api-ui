"""Users table callbacks."""

from dash import Input, Output, State
import requests

from ..config import API_BASE, DEFAULT_PAGE_SIZE
from ..utils import parse_date


def register_callbacks(app):
    """Register users table callbacks."""

    @app.callback(
        Output("users-table", "getRowsResponse"),
        Input("users-table", "getRowsRequest"),
        [State("token-store", "data"), State("role-store", "data")],
        prevent_initial_call=True,
    )
    def get_users_rows(request, token, role):
        """Get users data for ag-grid with infinite row model with server-side operations."""
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
                # Skip action columns
                if field in ("edit",):
                    continue
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
            resp = requests.get(f"{API_BASE}/user", params=params, headers=headers)

            if resp.status_code != 200:
                return {"rowData": [], "rowCount": 0}

            result = resp.json()
            users = result.get("data", [])
            total_rows = result.get("total", 0)

            # Check if user is admin to add edit buttons
            is_admin = role == "ADMIN"

            tabledata = []
            for user_row in users:
                row = user_row.copy()
                # Only add edit button for admin users
                if is_admin:
                    row["edit"] = "Edit"
                for date_col in ["created_at", "updated_at"]:
                    if date_col in row:
                        row[date_col] = parse_date(row.get(date_col))
                tabledata.append(row)

            return {"rowData": tabledata, "rowCount": total_rows}

        except Exception as e:
            print(f"Error in get_users_rows: {str(e)}")
            return {"rowData": [], "rowCount": 0}

    @app.callback(
        Output("users-table", "getRowsResponse", allow_duplicate=True),
        Input("refresh-users-btn", "n_clicks"),
        [State("token-store", "data"), State("role-store", "data")],
        prevent_initial_call=True,
    )
    def refresh_users_table(n_clicks, token, role):
        """Manually refresh the users table."""
        if not n_clicks or not token:
            return {"rowData": [], "rowCount": 0}

        # For infinite row model, we need to trigger a refresh by clearing the cache
        # This is done by returning a fresh response for the first page
        headers = {"Authorization": f"Bearer {token}"}

        params = {
            "page": 1,
            "per_page": DEFAULT_PAGE_SIZE,
        }

        resp = requests.get(f"{API_BASE}/user", params=params, headers=headers)

        if resp.status_code != 200:
            return {"rowData": [], "rowCount": 0}

        result = resp.json()
        users = result.get("data", [])
        total_rows = result.get("total", 0)

        # Check if user is admin to add edit buttons
        is_admin = role == "ADMIN"

        tabledata = []
        for user_row in users:
            row = user_row.copy()
            # Only add edit button for admin users
            if is_admin:
                row["edit"] = "Edit"
            for date_col in ["created_at", "updated_at"]:
                if date_col in row:
                    row[date_col] = parse_date(row.get(date_col))
            tabledata.append(row)

        return {"rowData": tabledata, "rowCount": total_rows}
