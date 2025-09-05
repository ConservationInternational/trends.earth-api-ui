"""Users table callbacks."""

from dash import Input, Output, State, html
import dash_bootstrap_components as dbc

from ..config import DEFAULT_PAGE_SIZE
from ..utils import parse_date


def register_callbacks(app):
    """Register users table callbacks."""

    @app.callback(
        [
            Output("users-table", "getRowsResponse"),
            Output("users-table-state", "data"),
            Output("users-total-count-store", "data"),
        ],
        Input("users-table", "getRowsRequest"),
        [
            State("token-store", "data"),
            State("role-store", "data"),
            State("user-timezone-store", "data"),
            State("api-environment-store", "data"),
            State("users-role-filter-selected", "data"),
        ],
        prevent_initial_call=False,
    )
    def get_users_rows(request, token, role, user_timezone, _api_environment, role_filter_selected):
        """Get users data for ag-grid with infinite row model with server-side operations."""
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
            if role_filter_selected:
                filter_model["role"] = {"filterType": "set", "values": role_filter_selected}

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

            # Build SQL-style filter string (Admin/SuperAdmin only)
            filter_sql = []
            if role in ["ADMIN", "SUPERADMIN"]:  # Only admins and superadmins can use filters
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

            resp = make_authenticated_request("/user", token, params=params)

            if resp.status_code != 200:
                return {"rowData": [], "rowCount": 0}, {}, 0

            result = resp.json()
            users = result.get("data", [])
            total_rows = result.get("total", 0)
            print(f"DEBUG: Received {len(users)} users, total: {total_rows}")

            # Check if user is superadmin to add edit buttons - only superadmins can edit users
            is_superadmin = role == "SUPERADMIN"

            tabledata = []
            for user_row in users:
                row = user_row.copy()
                # Only add edit button for superadmin users
                if is_superadmin:
                    row["edit"] = "Edit"
                for date_col in ["created_at", "updated_at"]:
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

            print(f"DEBUG: Returning {len(tabledata)} users to ag-grid, rowCount: {total_rows}")
            return {"rowData": tabledata, "rowCount": total_rows}, table_state, total_rows

        except Exception as e:
            print(f"Error in get_users_rows: {str(e)}")
            return {"rowData": [], "rowCount": 0}, {}, 0

    @app.callback(
        [
            Output("users-table", "getRowsResponse", allow_duplicate=True),
            Output("users-table-state", "data", allow_duplicate=True),
            Output("users-total-count-store", "data", allow_duplicate=True),
        ],
        Input("refresh-users-btn", "n_clicks"),
        [
            State("token-store", "data"),
            State("role-store", "data"),
            State("users-table-state", "data"),
            State("user-timezone-store", "data"),
            State("api-environment-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def refresh_users_table(n_clicks, token, role, table_state, user_timezone, _api_environment):
        """Manually refresh the users table."""
        if not n_clicks or not token:
            return {"rowData": [], "rowCount": 0}, {}, 0

        try:
            # For infinite row model, we need to trigger a refresh by clearing the cache
            # This is done by returning a fresh response for the first page
            params = {
                "page": 1,
                "per_page": DEFAULT_PAGE_SIZE,
            }

            # Preserve existing sort and filter settings if available
            if table_state:
                if table_state.get("sort_sql"):
                    params["sort"] = table_state["sort_sql"]
                if table_state.get("filter_sql"):
                    params["filter"] = table_state["filter_sql"]

            from ..utils.helpers import make_authenticated_request

            resp = make_authenticated_request("/user", token, params=params)

            if resp.status_code != 200:
                return {"rowData": [], "rowCount": 0}, {}, 0

            result = resp.json()
            users = result.get("data", [])
            total_rows = result.get("total", 0)

            # Check if user is superadmin to add edit buttons - only superadmins can edit users
            is_superadmin = role == "SUPERADMIN"

            tabledata = []
            for user_row in users:
                row = user_row.copy()
                # Only add edit button for superadmin users
                if is_superadmin:
                    row["edit"] = "Edit"
                for date_col in ["created_at", "updated_at"]:
                    if date_col in row:
                        row[date_col] = parse_date(row.get(date_col), user_timezone)
                tabledata.append(row)

            # Return data with preserved table state
            return {"rowData": tabledata, "rowCount": total_rows}, table_state or {}, total_rows

        except Exception as e:
            print(f"Error in refresh_users_table: {str(e)}")
            return {"rowData": [], "rowCount": 0}, {}, 0

    @app.callback(
        Output("users-total-count", "children"),
        Input("users-total-count-store", "data"),
        prevent_initial_call=True,
    )
    def update_users_total_display(total_count):
        """Update the users total count display."""
        return f"Total: {total_count:,}"

    @app.callback(
        [
            Output("edit-user-email-notifications-alert", "children"),
            Output("edit-user-email-notifications-alert", "color"),
            Output("edit-user-email-notifications-alert", "is_open"),
        ],
        [Input("edit-user-email-notifications-switch", "value")],
        [
            State("edit-user-modal-user-id", "data"),
            State("token-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def admin_update_user_email_notifications(enabled, user_id, token):
        """Admin update of user email notification preferences."""
        if token is None or user_id is None:
            return "", "info", False

        try:
            from ..utils.helpers import make_authenticated_request

            # Update email notifications setting for the target user
            resp = make_authenticated_request(
                f"/admin/users/{user_id}",
                token,
                method="PATCH",
                json={"email_notifications_enabled": enabled},
                timeout=10,
            )

            if resp.status_code == 200:
                status_text = "enabled" if enabled else "disabled"
                return (
                    [
                        f"Email notifications {status_text} for user successfully!",
                    ],
                    "success",
                    True,
                )
            else:
                error_msg = "Failed to update email notification settings."
                try:
                    error_data = resp.json()
                    error_msg = error_data.get("detail", error_msg)
                except Exception:
                    pass
                return error_msg, "danger", True

        except Exception as e:
            print(f"Error updating user email notifications: {e}")
            return f"Network error: {str(e)}", "danger", True

    @app.callback(
        [
            Output("edit-user-gee-status-display", "children"),
            Output("edit-user-gee-test-btn", "disabled"),
            Output("edit-user-gee-delete-btn", "disabled"),
        ],
        [Input("edit-user-modal-user-id", "data")],
        [State("token-store", "data")],
        prevent_initial_call=True,
    )
    def admin_update_gee_status_display(user_id, token):
        """Update the GEE credentials status display for admin view."""
        if not token or not user_id:
            return "Please select a user to view credentials.", True, True

        try:
            from ..utils.helpers import make_authenticated_request

            # Get current credentials status for the user
            resp = make_authenticated_request(f"/admin/users/{user_id}/gee-credentials", token)

            if resp.status_code == 200:
                data = resp.json().get("data", {})
                has_credentials = data.get("has_credentials", False)
                credentials_type = data.get("credentials_type")
                created_at = data.get("created_at")

                if has_credentials:
                    # Format the created date
                    created_date = "Unknown"
                    if created_at:
                        try:
                            from datetime import datetime

                            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                            created_date = dt.strftime("%Y-%m-%d %H:%M UTC")
                        except Exception:
                            created_date = str(created_at)

                    type_label = "OAuth" if credentials_type == "oauth" else "Service Account"

                    status_content = dbc.Alert(
                        [
                            html.I(className="fas fa-check-circle me-2"),
                            f"Credentials configured using {type_label}",
                            html.Br(),
                            html.Small(f"Set up on: {created_date}", className="text-muted"),
                        ],
                        color="success",
                        className="mb-2",
                    )

                    # Enable management buttons
                    return status_content, False, False
                else:
                    status_content = dbc.Alert(
                        [
                            html.I(className="fas fa-exclamation-triangle me-2"),
                            "No Google Earth Engine credentials configured.",
                        ],
                        color="warning",
                    )
                    return status_content, True, True
            else:
                return (
                    dbc.Alert("Unable to retrieve credentials status.", color="danger"),
                    True,
                    True,
                )

        except Exception as e:
            print(f"Error getting user GEE status: {e}")
            return dbc.Alert("Error retrieving credentials status.", color="danger"), True, True

    @app.callback(
        [
            Output("edit-user-gee-service-account-alert", "children"),
            Output("edit-user-gee-service-account-alert", "color"),
            Output("edit-user-gee-service-account-alert", "is_open"),
        ],
        [Input("edit-user-gee-service-account-upload", "contents")],
        [
            State("edit-user-gee-service-account-upload", "filename"),
            State("edit-user-modal-user-id", "data"),
            State("token-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def admin_upload_user_service_account(contents, filename, user_id, token):
        """Handle admin upload of service account key for user."""
        if not contents or not token or not user_id:
            return "", "info", False

        try:
            import base64
            import json

            # Decode the uploaded file
            content_type, content_string = contents.split(",")
            decoded = base64.b64decode(content_string)

            # Parse JSON
            try:
                service_account_key = json.loads(decoded.decode("utf-8"))
            except json.JSONDecodeError:
                return (
                    "Invalid JSON file. Please upload a valid service account key file.",
                    "danger",
                    True,
                )

            # Validate it looks like a service account key
            required_fields = ["type", "project_id", "private_key", "client_email"]
            if not all(field in service_account_key for field in required_fields):
                return "Invalid service account key. Missing required fields.", "danger", True

            if service_account_key.get("type") != "service_account":
                return (
                    "Invalid service account key. Type field must be 'service_account'.",
                    "danger",
                    True,
                )

            from ..utils.helpers import make_authenticated_request

            # Upload to API for the user
            resp = make_authenticated_request(
                f"/admin/users/{user_id}/gee-service-account",
                token,
                method="POST",
                json={"service_account_key": service_account_key},
                timeout=15,
            )

            if resp.status_code == 200:
                return (
                    [
                        f"Service account key '{filename}' uploaded for user successfully!",
                    ],
                    "success",
                    True,
                )
            else:
                error_msg = "Failed to upload service account key."
                try:
                    error_data = resp.json()
                    error_msg = error_data.get("detail", error_msg)
                except Exception:
                    pass
                return error_msg, "danger", True

        except Exception as e:
            print(f"Error uploading user service account: {e}")
            return f"Error processing file: {str(e)}", "danger", True

    @app.callback(
        [
            Output("edit-user-gee-management-alert", "children"),
            Output("edit-user-gee-management-alert", "color"),
            Output("edit-user-gee-management-alert", "is_open"),
        ],
        [
            Input("edit-user-gee-test-btn", "n_clicks"),
            Input("edit-user-gee-delete-btn", "n_clicks"),
        ],
        [
            State("edit-user-modal-user-id", "data"),
            State("token-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def admin_handle_user_gee_management_actions(test_clicks, delete_clicks, user_id, token):
        """Handle admin testing and deleting user GEE credentials."""
        if not token or not user_id:
            return "", "info", False

        from dash import callback_context

        ctx = callback_context
        if not ctx.triggered:
            return "", "info", False

        button_id = ctx.triggered[0]["prop_id"].split(".")[0]

        try:
            from ..utils.helpers import make_authenticated_request

            if button_id == "edit-user-gee-test-btn" and test_clicks:
                # Test user credentials
                resp = make_authenticated_request(
                    f"/admin/users/{user_id}/gee-credentials/test",
                    token,
                    method="POST",
                    timeout=30,  # GEE testing can take a while
                )

                if resp.status_code == 200:
                    return (
                        [
                            "User's Google Earth Engine credentials are valid and working!",
                        ],
                        "success",
                        True,
                    )
                else:
                    error_msg = "User's credentials test failed."
                    try:
                        error_data = resp.json()
                        error_msg = error_data.get("detail", error_msg)
                    except Exception:
                        pass
                    return error_msg, "danger", True

            elif button_id == "edit-user-gee-delete-btn" and delete_clicks:
                # Delete user credentials
                resp = make_authenticated_request(
                    f"/admin/users/{user_id}/gee-credentials",
                    token,
                    method="DELETE",
                    timeout=10,
                )

                if resp.status_code == 200:
                    return (
                        [
                            "User's Google Earth Engine credentials deleted successfully.",
                        ],
                        "warning",
                        True,
                    )
                else:
                    error_msg = "Failed to delete user's credentials."
                    try:
                        error_data = resp.json()
                        error_msg = error_data.get("detail", error_msg)
                    except Exception:
                        pass
                    return error_msg, "danger", True

        except Exception as e:
            print(f"Error with user GEE management action: {e}")
            return f"Network error: {str(e)}", "danger", True

        return "", "info", False
