"""Admin functionality callbacks."""

import base64

from dash import Input, Output, State, callback_context, html, no_update
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
                headers = {"Authorization": f"Bearer {token}"}
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

                headers = {"Authorization": f"Bearer {token}"}
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
            State("active-tab-store", "data"),  # Changed from Input to State
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
            headers = {"Authorization": f"Bearer {token}"}

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

            # Get active execution count
            exec_response = make_authenticated_request(
                "/execution?status=RUNNING&per_page=1", token, timeout=5
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
