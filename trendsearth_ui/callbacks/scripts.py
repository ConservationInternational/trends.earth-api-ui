"""Scripts table callbacks."""

from dash import Input, Output, State

from ..config import DEFAULT_PAGE_SIZE
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
        [
            State("token-store", "data"),
            State("role-store", "data"),
            State("user-timezone-store", "data"),
            State("api-environment-store", "data"),
        ],
        prevent_initial_call=False,
    )
    def get_scripts_rows(request, token, role, user_timezone, _api_environment):
        """Get scripts data for ag-grid with infinite row model with server-side operations."""
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
            }

            # Add admin-only fields if user is admin or superadmin
            if role in ["ADMIN", "SUPERADMIN"]:
                params["include"] = "user_name"

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
                if config.get("filterType") == "text":
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

            # Add filters to params if any
            if filter_sql:
                params["filter"] = ",".join(filter_sql)

            from ..utils.helpers import make_authenticated_request

            resp = make_authenticated_request("/script", token, params=params)

            if resp.status_code != 200:
                return {"rowData": [], "rowCount": 0}, {}, 0

            if resp.status_code != 200:
                return {"rowData": [], "rowCount": 0}, {}, 0

            result = resp.json()
            scripts = result.get("data", [])
            total_rows = result.get("total", 0)

            # Check if user is admin to add edit buttons
            is_admin = role in ["ADMIN", "SUPERADMIN"]

            tabledata = []
            for script_row in scripts:
                row = script_row.copy()
                row["logs"] = "Show Logs"

                # Add access control status indicator
                script_id = row.get("id")
                if script_id:
                    try:
                        # Check if script has access control restrictions
                        ac_resp = make_authenticated_request(f"/script/{script_id}/access", token)
                        if ac_resp.status_code == 200:
                            ac_data = ac_resp.json().get("data", {})
                            is_restricted = ac_data.get("restricted", False)
                            if is_restricted:
                                allowed_roles = ac_data.get("allowed_roles", [])
                                allowed_users = ac_data.get("allowed_users", [])
                                if allowed_roles and allowed_users:
                                    row["access_control"] = "🔒 Role, User"
                                elif allowed_roles:
                                    row["access_control"] = "🔒 Role"
                                elif allowed_users:
                                    row["access_control"] = "🔒 User"
                                else:
                                    row["access_control"] = "🔒 Restricted"
                            else:
                                row["access_control"] = "🔓 Open"
                        elif ac_resp.status_code == 404:
                            # 404 means no access control configured, so it's unrestricted
                            row["access_control"] = "🔓 Open"
                        else:
                            row["access_control"] = "❓ Unknown"
                    except Exception:
                        row["access_control"] = "❓ Unknown"
                else:
                    row["access_control"] = "❓ Unknown"

                # Only add edit button for admin users
                if is_admin:
                    row["edit"] = "Edit"
                for date_col in ["start_date", "end_date", "created_at", "updated_at"]:
                    if date_col in row:
                        row[date_col] = parse_date(row.get(date_col), user_timezone)
                tabledata.append(row)

            # Store the current table state for use in edit callbacks
            table_state = {
                "sort_model": sort_model,
                "filter_model": filter_model,
                "sort_sql": ",".join(sort_sql) if sort_sql else None,
                "filter_sql": ",".join(filter_sql) if filter_sql else None,
            }

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
        [
            State("token-store", "data"),
            State("role-store", "data"),
            State("scripts-table-state", "data"),
            State("user-timezone-store", "data"),
            State("api-environment-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def refresh_scripts_table(n_clicks, token, role, table_state, user_timezone, _api_environment):
        """Manually refresh the scripts table."""
        if not n_clicks or not token:
            return {"rowData": [], "rowCount": 0}, {}, 0

        try:
            # For infinite row model, we need to trigger a refresh by clearing the cache
            # This is done by returning a fresh response for the first page

            params = {
                "page": 1,
                "per_page": DEFAULT_PAGE_SIZE,
            }

            # Add admin-only fields if user is admin or superadmin
            if role in ["ADMIN", "SUPERADMIN"]:
                params["include"] = "user_name"

            # Preserve existing sort and filter settings if available
            if table_state:
                if table_state.get("sort_sql"):
                    params["sort"] = table_state["sort_sql"]
                if table_state.get("filter_sql"):
                    params["filter"] = table_state["filter_sql"]

            from ..utils.helpers import make_authenticated_request

            resp = make_authenticated_request("/script", token, params=params)

            if resp.status_code != 200:
                return {"rowData": [], "rowCount": 0}, {}, 0

            result = resp.json()
            scripts = result.get("data", [])
            total_rows = result.get("total", 0)

            # Check if user is admin to add edit buttons
            is_admin = role in ["ADMIN", "SUPERADMIN"]

            tabledata = []
            for script_row in scripts:
                row = script_row.copy()
                row["logs"] = "Show Logs"

                # Add access control status indicator
                script_id = row.get("id")
                if script_id:
                    try:
                        # Check if script has access control restrictions
                        ac_resp = make_authenticated_request(f"/script/{script_id}/access", token)
                        if ac_resp.status_code == 200:
                            ac_data = ac_resp.json().get("data", {})
                            is_restricted = ac_data.get("restricted", False)
                            if is_restricted:
                                allowed_roles = ac_data.get("allowed_roles", [])
                                allowed_users = ac_data.get("allowed_users", [])
                                if allowed_roles and allowed_users:
                                    row["access_control"] = "🔒 Role, User"
                                elif allowed_roles:
                                    row["access_control"] = "🔒 Role"
                                elif allowed_users:
                                    row["access_control"] = "🔒 User"
                                else:
                                    row["access_control"] = "🔒 Restricted"
                            else:
                                row["access_control"] = "🔓 Open"
                        elif ac_resp.status_code == 404:
                            # 404 means no access control configured, so it's unrestricted
                            row["access_control"] = "🔓 Open"
                        else:
                            row["access_control"] = "❓ Unknown"
                    except Exception:
                        row["access_control"] = "❓ Unknown"
                else:
                    row["access_control"] = "❓ Unknown"

                # Only add edit button for admin users
                if is_admin:
                    row["edit"] = "Edit"
                for date_col in ["start_date", "end_date", "created_at", "updated_at"]:
                    if date_col in row:
                        row[date_col] = parse_date(row.get(date_col), user_timezone)
                tabledata.append(row)

            # Return data with preserved table state
            return {"rowData": tabledata, "rowCount": total_rows}, table_state or {}, total_rows

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
