"""Admin functionality callbacks."""

import base64

from dash import Input, Output, State, callback_context, html, no_update
import dash_bootstrap_components as dbc
import requests


def register_callbacks(app):
    """Register admin-related callbacks."""

    @app.callback(
        [
            Output("admin-create-user-alert", "children"),
            Output("admin-create-user-alert", "color"),
            Output("admin-create-user-alert", "is_open"),
            Output("admin-new-user-name", "value"),
            Output("admin-new-user-email", "value"),
            Output("admin-new-user-password", "value"),
            Output("admin-new-user-confirm-password", "value"),
            Output("admin-new-user-institution", "value"),
            Output("admin-new-user-country", "value"),
            Output("admin-new-user-role", "value"),
        ],
        [
            Input("admin-create-user-btn", "n_clicks"),
            Input("admin-clear-user-form-btn", "n_clicks"),
        ],
        [
            State("admin-new-user-name", "value"),
            State("admin-new-user-email", "value"),
            State("admin-new-user-password", "value"),
            State("admin-new-user-confirm-password", "value"),
            State("admin-new-user-institution", "value"),
            State("admin-new-user-country", "value"),
            State("admin-new-user-role", "value"),
            State("token-store", "data"),
            State("role-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def handle_create_user(
        create_clicks,
        _clear_clicks,
        name,
        email,
        password,
        confirm_password,
        institution,
        country,
        role,
        token,
        user_role,
    ):
        """Handle user creation and form clearing."""
        ctx = callback_context
        if not ctx.triggered:
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
            )

        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

        # Check superadmin permissions for user creation
        if user_role != "SUPERADMIN":
            return (
                "Access denied. Super administrator privileges required.",
                "danger",
                True,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
            )

        if trigger_id == "admin-clear-user-form-btn":
            # Clear the form
            return "", "info", False, "", "", "", "", "", "", "USER"

        if trigger_id == "admin-create-user-btn" and create_clicks:
            # Validate inputs
            if not name or not email or not password:
                return (
                    "Please fill in all required fields (Name, Email, Password).",
                    "warning",
                    True,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                )

            if password != confirm_password:
                return (
                    "Passwords do not match.",
                    "warning",
                    True,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                )

            if len(password) < 6:
                return (
                    "Password must be at least 6 characters long.",
                    "warning",
                    True,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                )

            try:
                # Create user via API
                user_data = {
                    "name": name.strip(),
                    "email": email.strip().lower(),
                    "password": password,
                    "institution": institution.strip() if institution else None,
                    "country": country.strip() if country else None,
                    "role": role,
                    "is_active": True,
                }

                from ..utils.helpers import make_authenticated_request

                response = make_authenticated_request(
                    "/user", token, method="POST", json=user_data, timeout=10
                )

                if response.status_code in [200, 201]:
                    # Success - clear form and show success message
                    return (
                        f"User '{name}' created successfully with email '{email}'.",
                        "success",
                        True,
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "USER",
                    )
                elif response.status_code == 409:
                    return (
                        "A user with this email already exists.",
                        "warning",
                        True,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                    )
                elif response.status_code == 400:
                    error_detail = response.json().get("detail", "Invalid user data.")
                    return (
                        f"Error creating user: {error_detail}",
                        "danger",
                        True,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                    )
                else:
                    return (
                        f"Failed to create user. Server responded with status {response.status_code}.",
                        "danger",
                        True,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                    )

            except requests.exceptions.Timeout:
                return (
                    "Request timed out. Please try again.",
                    "danger",
                    True,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                )
            except requests.exceptions.ConnectionError:
                return (
                    "Cannot connect to server. Please check your connection.",
                    "danger",
                    True,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                )
            except Exception as e:
                return (
                    f"Unexpected error: {str(e)}",
                    "danger",
                    True,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                )

        return (
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
        )

    @app.callback(
        [
            Output("admin-script-upload-status", "children"),
            Output("admin-upload-script-btn", "disabled"),
        ],
        [Input("admin-script-upload", "contents")],
        [State("admin-script-upload", "filename")],
        prevent_initial_call=True,
    )
    def handle_script_upload_preview(contents, filename):
        """Handle script file upload preview."""
        if contents is None:
            return "", True

        if filename:
            # Get file size from base64 content
            content_string = contents.split(",")[1]
            decoded = base64.b64decode(content_string)
            file_size = len(decoded)
            file_size_mb = file_size / (1024 * 1024)

            if file_size_mb > 10:  # 10MB limit
                return html.Div(
                    [
                        html.I(className="fas fa-exclamation-triangle text-warning me-2"),
                        f"File too large: {filename} ({file_size_mb:.1f}MB). Maximum 10MB allowed.",
                    ]
                ), True

            return html.Div(
                [
                    html.I(className="fas fa-check-circle text-success me-2"),
                    f"File ready: {filename} ({file_size_mb:.2f}MB)",
                ]
            ), False

        return "", True

    @app.callback(
        [
            Output("admin-upload-script-alert", "children"),
            Output("admin-upload-script-alert", "color"),
            Output("admin-upload-script-alert", "is_open"),
            Output("admin-new-script-name", "value"),
            Output("admin-new-script-description", "value"),
            Output("admin-new-script-status", "value"),
            Output("admin-script-upload", "contents"),
            Output("admin-script-upload", "filename"),
        ],
        [
            Input("admin-upload-script-btn", "n_clicks"),
            Input("admin-clear-script-form-btn", "n_clicks"),
        ],
        [
            State("admin-new-script-name", "value"),
            State("admin-new-script-description", "value"),
            State("admin-new-script-status", "value"),
            State("admin-script-upload", "contents"),
            State("admin-script-upload", "filename"),
            State("token-store", "data"),
            State("role-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def handle_upload_script(
        upload_clicks,
        _clear_clicks,
        name,
        description,
        status,
        contents,
        filename,
        token,
        user_role,
    ):
        """Handle script upload and form clearing."""
        ctx = callback_context
        if not ctx.triggered:
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
            )

        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

        # Check admin permissions for script management
        if user_role not in ["ADMIN", "SUPERADMIN"]:
            return (
                "Access denied. Administrator privileges required.",
                "danger",
                True,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
            )

        if trigger_id == "admin-clear-script-form-btn":
            # Clear the form
            return "", "info", False, "", "", "DRAFT", None, None

        if trigger_id == "admin-upload-script-btn" and upload_clicks:
            # Validate inputs
            if not name or not contents or not filename:
                return (
                    "Please fill in the script name and select a file to upload.",
                    "warning",
                    True,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                )

            try:
                # Prepare script data
                content_string = contents.split(",")[1]
                decoded_content = base64.b64decode(content_string)

                script_data = {
                    "name": name.strip(),
                    "description": description.strip() if description else "",
                    "status": status,
                    "filename": filename,
                }

                # Create multipart form data
                files = {"file": (filename, decoded_content)}

                from ..utils.helpers import make_authenticated_request

                response = make_authenticated_request(
                    "/script", token, method="POST", data=script_data, files=files, timeout=30
                )

                if response.status_code in [200, 201]:
                    # Success - clear form and show success message
                    return (
                        f"Script '{name}' uploaded successfully.",
                        "success",
                        True,
                        "",
                        "",
                        "DRAFT",
                        None,
                        None,
                    )
                elif response.status_code == 409:
                    return (
                        "A script with this name already exists.",
                        "warning",
                        True,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                    )
                elif response.status_code == 400:
                    error_detail = response.json().get("detail", "Invalid script data.")
                    return (
                        f"Error uploading script: {error_detail}",
                        "danger",
                        True,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                    )
                else:
                    return (
                        f"Failed to upload script. Server responded with status {response.status_code}.",
                        "danger",
                        True,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                    )

            except requests.exceptions.Timeout:
                return (
                    "Upload timed out. Please try again with a smaller file.",
                    "danger",
                    True,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                )
            except requests.exceptions.ConnectionError:
                return (
                    "Cannot connect to server. Please check your connection.",
                    "danger",
                    True,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                )
            except Exception as e:
                return (
                    f"Unexpected error: {str(e)}",
                    "danger",
                    True,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                )

        return (
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
        )

    @app.callback(
        [
            Output("admin-total-users", "children"),
            Output("admin-total-scripts", "children"),
            Output("admin-active-executions", "children"),
        ],
        [
            Input("admin-refresh-stats-btn", "n_clicks"),
        ],
        [
            State("token-store", "data"),
            State("role-store", "data"),
            State("active-tab-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def refresh_admin_stats(refresh_clicks, token, user_role, active_tab):
        """Refresh admin statistics."""
        # Guard: Skip if not logged in or not admin (prevents execution after logout)
        if not token or user_role != "ADMIN":
            return no_update, no_update, no_update

        # Only update when admin tab is active or refresh button is clicked
        if active_tab != "admin" and not refresh_clicks:
            return no_update, no_update, no_update

        try:
            from ..utils.helpers import make_authenticated_request

            # Get user count
            user_response = make_authenticated_request("/user?per_page=1", token, timeout=5)
            total_users = (
                user_response.json().get("total", 0)
                if user_response.status_code == 200
                else "Error"
            )

            # Get script count
            script_response = make_authenticated_request("/script?per_page=1", token, timeout=5)
            total_scripts = (
                script_response.json().get("total", 0)
                if script_response.status_code == 200
                else "Error"
            )

            # Get active execution count (READY, RUNNING, and PENDING)
            exec_response = make_authenticated_request(
                "/execution?filter=status=READY,status=RUNNING,status=PENDING&per_page=1",
                token,
                timeout=5,
            )
            active_executions = (
                exec_response.json().get("total", 0)
                if exec_response.status_code == 200
                else "Error"
            )

            return str(total_users), str(total_scripts), str(active_executions)

        except Exception as e:
            print(f"Error fetching admin stats: {e}")
            return "Error", "Error", "Error"

    @app.callback(
        Output("reset-rate-limits-modal", "is_open"),
        [
            Input("admin-reset-rate-limits-btn", "n_clicks"),
            Input("cancel-reset-rate-limits", "n_clicks"),
            Input("confirm-reset-rate-limits", "n_clicks"),
        ],
        [State("reset-rate-limits-modal", "is_open")],
        prevent_initial_call=True,
    )
    def toggle_reset_rate_limits_modal(_btn_clicks, _cancel_clicks, _confirm_clicks, _is_open):
        """Toggle the rate limits reset confirmation modal."""
        ctx = callback_context
        if not ctx.triggered:
            return no_update

        # Get the triggered component ID
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]

        # Only respond to actual button clicks (not initial None values)
        triggered_value = ctx.triggered[0]["value"]
        if triggered_value is None:
            return no_update

        if button_id == "admin-reset-rate-limits-btn":
            return True
        elif button_id in ["cancel-reset-rate-limits", "confirm-reset-rate-limits"]:
            return False

        return no_update

    @app.callback(
        [
            Output("admin-reset-rate-limits-alert", "children"),
            Output("admin-reset-rate-limits-alert", "color"),
            Output("admin-reset-rate-limits-alert", "is_open"),
        ],
        [Input("confirm-reset-rate-limits", "n_clicks")],
        [
            State("token-store", "data"),
            State("role-store", "data"),
            State("api-environment-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def reset_rate_limits(confirm_clicks, token, role, _api_environment):
        """Reset all rate limits via API call."""
        if not confirm_clicks or not token or role != "SUPERADMIN":
            return no_update, no_update, no_update

        try:
            from ..utils.helpers import make_authenticated_request

            # Make API call to reset rate limits
            resp = make_authenticated_request("/rate-limit/reset", token, method="POST", json={})

            if resp.status_code == 200:
                return (
                    [
                        html.I(className="fas fa-check-circle me-2"),
                        "Rate limits have been successfully reset for all users and endpoints.",
                    ],
                    "success",
                    True,
                )
            else:
                error_msg = f"Failed to reset rate limits. Status: {resp.status_code}"
                try:
                    error_data = resp.json()
                    if "detail" in error_data:
                        error_msg += f" - {error_data['detail']}"
                except (ValueError, KeyError):
                    error_msg += f" - {resp.text}"

                return (
                    [html.I(className="fas fa-exclamation-triangle me-2"), error_msg],
                    "danger",
                    True,
                )

        except Exception as e:
            return (
                [
                    html.I(className="fas fa-exclamation-triangle me-2"),
                    f"Error resetting rate limits: {str(e)}",
                ],
                "danger",
                True,
            )

    @app.callback(
        [
            Output("rate-limit-status", "children"),
            Output("rate-limit-storage", "children"),
            Output("rate-limit-count", "children"),
            Output("rate-limits-table-container", "children"),
        ],
        [
            Input("refresh-rate-limit-status-btn", "n_clicks"),
            Input("active-tab-store", "data"),
        ],
        [
            State("token-store", "data"),
            State("role-store", "data"),
            State("api-environment-store", "data"),
        ],
        prevent_initial_call=False,
    )
    def fetch_rate_limit_status(_refresh_clicks, active_tab, token, role, _api_environment):
        """Fetch and display rate limiting status."""
        # Only load when admin tab is active and user is SUPERADMIN
        if active_tab != "admin" or not token or role != "SUPERADMIN":
            return (
                "N/A",
                "N/A",
                "0",
                html.Div(
                    "Rate limiting status not available.", className="text-muted text-center p-3"
                ),
            )

        try:
            from ..utils.helpers import make_authenticated_request

            # Fetch rate limiting status
            resp = make_authenticated_request("/rate-limit/status", token, method="GET")

            if resp.status_code == 200:
                data = resp.json()

                # Extract status information
                enabled_status = "Enabled" if data.get("enabled", False) else "Disabled"
                storage_type = data.get("storage_type", "Unknown")
                total_active = data.get("total_active_limits", 0)
                active_limits = data.get("active_limits", [])

                # Create table for active limits
                if active_limits:
                    table_rows = []
                    for limit in active_limits:
                        # Get user info if available
                        user_info = limit.get("user_info", {})
                        identifier_display = limit.get("identifier", "Unknown")

                        # Format identifier with user info if available
                        if user_info:
                            user_name = user_info.get("name", "")
                            user_email = user_info.get("email", "")
                            if user_name and user_email:
                                identifier_display = f"{user_name} ({user_email})"
                            elif user_email:
                                identifier_display = user_email

                        # Format time window
                        time_window = limit.get("time_window_seconds", 0)
                        if time_window >= 3600:
                            time_display = f"{time_window // 3600}h"
                        elif time_window >= 60:
                            time_display = f"{time_window // 60}m"
                        else:
                            time_display = f"{time_window}s"

                        table_rows.append(
                            html.Tr(
                                [
                                    html.Td(limit.get("type", "").title()),
                                    html.Td(identifier_display),
                                    html.Td(
                                        f"{limit.get('current_count', 0)}/{limit.get('limit', 'N/A')}"
                                    ),
                                    html.Td(time_display),
                                    html.Td(
                                        dbc.Badge(
                                            user_info.get("role", "N/A") if user_info else "N/A",
                                            color="secondary" if not user_info else "primary",
                                            className="me-1",
                                        )
                                    ),
                                ]
                            )
                        )

                    table_content = dbc.Table(
                        [
                            html.Thead(
                                [
                                    html.Tr(
                                        [
                                            html.Th("Type"),
                                            html.Th("User/IP"),
                                            html.Th("Usage"),
                                            html.Th("Window"),
                                            html.Th("Role"),
                                        ]
                                    )
                                ]
                            ),
                            html.Tbody(table_rows),
                        ],
                        striped=True,
                        bordered=True,
                        hover=True,
                        responsive=True,
                        size="sm",
                    )
                else:
                    table_content = html.Div(
                        [
                            html.I(className="fas fa-check-circle me-2 text-success"),
                            "No active rate limits found.",
                        ],
                        className="text-center text-muted p-4",
                    )

                return enabled_status, storage_type, str(total_active), table_content

            elif resp.status_code == 404:
                # Graceful fallback for missing endpoint
                fallback_div = html.Div(
                    [
                        html.Div(
                            [
                                html.I(className="fas fa-info-circle me-2 text-info"),
                                html.Strong("Rate limiting status endpoint not available."),
                            ],
                            className="mb-2",
                        ),
                        html.Small(
                            [
                                "This feature requires API version with rate limiting management support. ",
                                "The rate limiting system may still be active, but status monitoring is not available.",
                            ],
                            className="text-muted",
                        ),
                    ],
                    className="text-center p-3",
                )
                return "Unknown", "Unknown", "N/A", fallback_div

            elif resp.status_code == 403:
                # Permission denied
                permission_div = html.Div(
                    [
                        html.I(className="fas fa-lock me-2 text-warning"),
                        "Access denied. SuperAdmin privileges required to view rate limiting status.",
                    ],
                    className="text-center text-warning p-3",
                )
                return "Access Denied", "Access Denied", "N/A", permission_div

            else:
                # Other HTTP errors
                error_msg = f"Failed to fetch rate limit status. Status: {resp.status_code}"
                try:
                    error_data = resp.json()
                    if "detail" in error_data:
                        error_msg += f" - {error_data['detail']}"
                except (ValueError, KeyError):
                    if resp.text:
                        error_msg += f" - {resp.text[:200]}"

                error_div = html.Div(
                    [
                        html.Div(
                            [
                                html.I(className="fas fa-exclamation-triangle me-2 text-danger"),
                                html.Strong("Error fetching rate limit status"),
                            ],
                            className="mb-2",
                        ),
                        html.Small(error_msg, className="text-muted"),
                        html.Br(),
                        html.Small(
                            [
                                "Try refreshing or check if the API endpoint is available. ",
                                "Request URL: /api/v1/rate-limit/status",
                            ],
                            className="text-muted mt-2",
                        ),
                    ],
                    className="text-center text-danger p-3",
                )
                return "Error", "Error", "Error", error_div

        except requests.exceptions.Timeout:
            error_div = html.Div(
                [
                    html.Div(
                        [
                            html.I(className="fas fa-clock me-2 text-warning"),
                            html.Strong("Request timeout"),
                        ],
                        className="mb-2",
                    ),
                    html.Small(
                        "The rate limiting status request timed out. Please try again.",
                        className="text-muted",
                    ),
                ],
                className="text-center text-warning p-3",
            )
            return "Timeout", "Timeout", "Timeout", error_div

        except requests.exceptions.ConnectionError:
            error_div = html.Div(
                [
                    html.Div(
                        [
                            html.I(className="fas fa-wifi me-2 text-danger"),
                            html.Strong("Connection error"),
                        ],
                        className="mb-2",
                    ),
                    html.Small(
                        "Unable to connect to the API server. Check your network connection.",
                        className="text-muted",
                    ),
                ],
                className="text-center text-danger p-3",
            )
            return "Connection Error", "Connection Error", "Connection Error", error_div

        except Exception as e:
            error_div = html.Div(
                [
                    html.Div(
                        [
                            html.I(className="fas fa-exclamation-triangle me-2 text-danger"),
                            html.Strong("Unexpected error"),
                        ],
                        className="mb-2",
                    ),
                    html.Small(f"Error: {str(e)}", className="text-muted"),
                    html.Br(),
                    html.Small("Please check logs for more details.", className="text-muted mt-2"),
                ],
                className="text-center text-danger p-3",
            )
            return "Error", "Error", "Error", error_div
