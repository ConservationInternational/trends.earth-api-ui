"""Users table callbacks."""

from typing import Any

from dash import Input, Output, State, callback_context, html
import dash_bootstrap_components as dbc

from ..config import DEFAULT_PAGE_SIZE
from ..utils import parse_date
from ..utils.aggrid import build_aggrid_request_params, build_refresh_request_params
from ..utils.helpers import make_authenticated_request

USER_ENDPOINT = "/user"
USER_DATE_COLUMNS = ("created_at", "updated_at")


def _format_user_rows(
    users: list[dict[str, Any]],
    current_user_role: str | None,
    user_timezone: str | None,
) -> list[dict[str, Any]]:
    """Normalize user rows for display in AG-Grid.

    Edit button visibility rules:
    - SUPERADMIN: Can edit all users
    - ADMIN: Can edit users except SUPERADMIN users
    """
    rows: list[dict[str, Any]] = []
    timezone = user_timezone or "UTC"
    is_superadmin = current_user_role == "SUPERADMIN"
    is_admin = current_user_role == "ADMIN"
    for user_row in users:
        row = user_row.copy()
        target_user_role = user_row.get("role", "USER")
        # SUPERADMIN can edit all users
        # ADMIN can edit users except SUPERADMIN
        if is_superadmin or (is_admin and target_user_role != "SUPERADMIN"):
            row["edit"] = "Edit"
        for date_col in USER_DATE_COLUMNS:
            if date_col in row:
                row[date_col] = parse_date(row.get(date_col), timezone)
        rows.append(row)
    return rows


def _fetch_users_page(
    token: str,
    params: dict[str, Any],
    *,
    current_user_role: str | None,
    user_timezone: str | None,
) -> tuple[list[dict[str, Any]], int]:
    """Fetch a page of users from the API and format the rows."""
    response = make_authenticated_request(USER_ENDPOINT, token, params=params)
    if response.status_code != 200:
        return [], 0

    payload = response.json()
    users = payload.get("data", [])
    total_rows = payload.get("total", 0)
    tabledata = _format_user_rows(users, current_user_role, user_timezone)
    return tabledata, total_rows


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
                return {"rowData": [], "rowCount": None}, {}, 0

            is_admin = role in ("ADMIN", "SUPERADMIN")
            filter_overrides = None
            if role_filter_selected and is_admin:
                filter_overrides = {"role": {"filterType": "set", "values": role_filter_selected}}

            params, table_state = build_aggrid_request_params(
                request,
                allow_filters=is_admin,
                filter_model_overrides=filter_overrides,
            )

            tabledata, total_rows = _fetch_users_page(
                token,
                params,
                current_user_role=role,
                user_timezone=user_timezone,
            )

            return {"rowData": tabledata, "rowCount": total_rows}, table_state, total_rows

        except Exception as exc:  # pragma: no cover - defensive guard
            print(f"Error in get_users_rows: {exc}")
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
            base_params = {
                "page": 1,
                "per_page": DEFAULT_PAGE_SIZE,
            }

            params = build_refresh_request_params(
                base_params=base_params,
                table_state=table_state,
                allow_filters=role in ("ADMIN", "SUPERADMIN"),
            )

            tabledata, total_rows = _fetch_users_page(
                token,
                params,
                current_user_role=role,
                user_timezone=user_timezone,
            )

            return {"rowData": tabledata, "rowCount": total_rows}, table_state or {}, total_rows

        except Exception as exc:  # pragma: no cover - defensive guard
            print(f"Error in refresh_users_table: {exc}")
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

            error_msg = "Failed to update email notification settings."
            try:
                error_data = resp.json()
                error_msg = error_data.get("detail", error_msg)
            except Exception:
                pass
            return error_msg, "danger", True

        except Exception as exc:  # pragma: no cover - defensive guard
            print(f"Error updating user email notifications: {exc}")
            return f"Network error: {exc}", "danger", True

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
            resp = make_authenticated_request(f"/admin/users/{user_id}/gee-credentials", token)

            if resp.status_code == 200:
                data = resp.json().get("data", {})
                has_credentials = data.get("has_credentials", False)
                credentials_type = data.get("credentials_type")
                created_at = data.get("created_at")

                if has_credentials:
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

                    return status_content, False, False

                status_content = dbc.Alert(
                    [
                        html.I(className="fas fa-exclamation-triangle me-2"),
                        "No Google Earth Engine credentials configured.",
                    ],
                    color="warning",
                )
                return status_content, True, True

            return (
                dbc.Alert("Unable to retrieve credentials status.", color="danger"),
                True,
                True,
            )

        except Exception as exc:  # pragma: no cover - defensive guard
            print(f"Error getting user GEE status: {exc}")
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

            _, content_string = contents.split(",")
            decoded = base64.b64decode(content_string)

            try:
                service_account_key = json.loads(decoded.decode("utf-8"))
            except json.JSONDecodeError:
                return (
                    "Invalid JSON file. Please upload a valid service account key file.",
                    "danger",
                    True,
                )

            required_fields = ["type", "project_id", "private_key", "client_email"]
            if not all(field in service_account_key for field in required_fields):
                return "Invalid service account key. Missing required fields.", "danger", True

            if service_account_key.get("type") != "service_account":
                return (
                    "Invalid service account key. Type field must be 'service_account'.",
                    "danger",
                    True,
                )

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

            error_msg = "Failed to upload service account key."
            try:
                error_data = resp.json()
                error_msg = error_data.get("detail", error_msg)
            except Exception:
                pass
            return error_msg, "danger", True

        except Exception as exc:  # pragma: no cover - defensive guard
            print(f"Error uploading user service account: {exc}")
            return f"Error processing file: {exc}", "danger", True

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

        ctx = callback_context
        if not ctx.triggered:
            return "", "info", False

        button_id = ctx.triggered[0]["prop_id"].split(".")[0]

        try:
            if button_id == "edit-user-gee-test-btn" and test_clicks:
                resp = make_authenticated_request(
                    f"/admin/users/{user_id}/gee-credentials/test",
                    token,
                    method="POST",
                    timeout=30,
                )

                if resp.status_code == 200:
                    return (
                        [
                            "User's Google Earth Engine credentials are valid and working!",
                        ],
                        "success",
                        True,
                    )

                error_msg = "User's credentials test failed."
                try:
                    error_data = resp.json()
                    error_msg = error_data.get("detail", error_msg)
                except Exception:
                    pass
                return error_msg, "danger", True

            if button_id == "edit-user-gee-delete-btn" and delete_clicks:
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

                error_msg = "Failed to delete user's credentials."
                try:
                    error_data = resp.json()
                    error_msg = error_data.get("detail", error_msg)
                except Exception:
                    pass
                return error_msg, "danger", True

        except Exception as exc:  # pragma: no cover - defensive guard
            print(f"Error with user GEE management action: {exc}")
            return f"Network error: {exc}", "danger", True

        return "", "info", False
