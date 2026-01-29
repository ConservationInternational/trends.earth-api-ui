"""Google Earth Engine credentials management callbacks."""

import base64
import json
import logging

from dash import Input, Output, State, callback_context, html, no_update
import dash_bootstrap_components as dbc

logger = logging.getLogger(__name__)


def register_callbacks(app):
    """Register GEE credentials callbacks."""

    @app.callback(
        Output("profile-gee-status-display", "children"),
        [Input("token-store", "data")],
        prevent_initial_call=False,
    )
    def update_gee_status_display(token):
        """Update the GEE credentials status display."""
        if not token:
            return html.Div("Please log in to view credentials status.", className="text-muted")

        try:
            from ..utils.helpers import make_authenticated_request

            # Get current credentials status
            resp = make_authenticated_request("/user/me/gee-credentials", token)

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

                    status_content = [
                        dbc.Alert(
                            [
                                html.I(className="fas fa-check-circle me-2"),
                                f"Credentials configured using {type_label}",
                                html.Br(),
                                html.Small(f"Set up on: {created_date}", className="text-muted"),
                            ],
                            color="success",
                            className="mb-2",
                        ),
                    ]

                    # Enable management buttons
                    return status_content
                else:
                    return dbc.Alert(
                        [
                            html.I(className="fas fa-exclamation-triangle me-2"),
                            "No Google Earth Engine credentials configured.",
                            html.Br(),
                            html.Small(
                                "Choose one of the setup options below.", className="text-muted"
                            ),
                        ],
                        color="warning",
                    )
            else:
                return dbc.Alert(
                    "Unable to retrieve credentials status.",
                    color="danger",
                )

        except Exception as e:
            logger.exception("Error getting GEE status: %s", e)
            return dbc.Alert(
                "Error retrieving credentials status.",
                color="danger",
            )

    @app.callback(
        [
            Output("profile-gee-test-btn", "disabled"),
            Output("profile-gee-delete-btn", "disabled"),
        ],
        [Input("profile-gee-status-display", "children")],
        prevent_initial_call=True,
    )
    def update_gee_button_states(status_children):
        """Enable/disable management buttons based on credentials status."""
        # Check if we have credentials by looking for success alert in status display
        has_credentials = False
        if status_children and isinstance(status_children, list):
            for child in status_children:
                if hasattr(child, "props") and child.props.get("color") == "success":
                    has_credentials = True
                    break

        return not has_credentials, not has_credentials

    @app.callback(
        [
            Output("profile-gee-oauth-alert", "children"),
            Output("profile-gee-oauth-alert", "color"),
            Output("profile-gee-oauth-alert", "is_open"),
        ],
        [Input("profile-gee-oauth-btn", "n_clicks")],
        [State("token-store", "data")],
        prevent_initial_call=True,
    )
    def initiate_gee_oauth(n_clicks, token):
        """Initiate Google Earth Engine OAuth flow."""
        if not n_clicks or not token:
            return no_update, no_update, no_update

        try:
            from ..utils.helpers import make_authenticated_request

            # Initiate OAuth flow
            resp = make_authenticated_request(
                "/user/me/gee-oauth/initiate",
                token,
                method="POST",
                timeout=10,
            )

            if resp.status_code == 200:
                data = resp.json().get("data", {})
                auth_url = data.get("auth_url")

                if auth_url:
                    # Open the OAuth URL in a new window
                    import webbrowser

                    webbrowser.open(auth_url)

                    return (
                        [
                            html.Div(
                                [
                                    html.I(className="fas fa-external-link-alt me-2"),
                                    "OAuth window opened. Please complete the authorization and return here.",
                                    html.Br(),
                                    html.Small(
                                        "After authorization, you may need to refresh this page to see the updated status.",
                                        className="text-muted",
                                    ),
                                ]
                            )
                        ],
                        "info",
                        True,
                    )
                else:
                    return (
                        "OAuth initiation failed - no authorization URL received.",
                        "danger",
                        True,
                    )
            else:
                error_msg = "Failed to initiate OAuth flow."
                try:
                    error_data = resp.json()
                    error_msg = error_data.get("detail", error_msg)
                except Exception:
                    pass
                return error_msg, "danger", True

        except Exception as e:
            logger.exception("Error initiating OAuth: %s", e)
            return f"Network error: {str(e)}", "danger", True

    @app.callback(
        [
            Output("profile-gee-service-account-alert", "children"),
            Output("profile-gee-service-account-alert", "color"),
            Output("profile-gee-service-account-alert", "is_open"),
        ],
        [Input("profile-gee-service-account-upload", "contents")],
        [
            State("profile-gee-service-account-upload", "filename"),
            State("token-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def upload_service_account(contents, filename, token):
        """Handle service account key upload."""
        if not contents or not token:
            return no_update, no_update, no_update

        try:
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

            # Upload to API
            resp = make_authenticated_request(
                "/user/me/gee-service-account",
                token,
                method="POST",
                json={"service_account_key": service_account_key},
                timeout=15,
            )

            if resp.status_code == 200:
                return (
                    [
                        html.I(className="fas fa-check-circle me-2"),
                        f"Service account key '{filename}' uploaded successfully!",
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
            logger.exception("Error uploading service account: %s", e)
            return f"Error processing file: {str(e)}", "danger", True

    @app.callback(
        [
            Output("profile-gee-management-alert", "children"),
            Output("profile-gee-management-alert", "color"),
            Output("profile-gee-management-alert", "is_open"),
        ],
        [
            Input("profile-gee-test-btn", "n_clicks"),
            Input("profile-gee-delete-btn", "n_clicks"),
        ],
        [State("token-store", "data")],
        prevent_initial_call=True,
    )
    def handle_gee_management_actions(test_clicks, delete_clicks, token):
        """Handle testing and deleting GEE credentials."""
        if not token:
            return no_update, no_update, no_update

        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update

        button_id = ctx.triggered[0]["prop_id"].split(".")[0]

        try:
            from ..utils.helpers import make_authenticated_request

            if button_id == "profile-gee-test-btn" and test_clicks:
                # Test credentials
                resp = make_authenticated_request(
                    "/user/me/gee-credentials/test",
                    token,
                    method="POST",
                    timeout=30,  # GEE testing can take a while
                )

                if resp.status_code == 200:
                    return (
                        [
                            html.I(className="fas fa-check-circle me-2"),
                            "Google Earth Engine credentials are valid and working!",
                        ],
                        "success",
                        True,
                    )
                else:
                    error_msg = "Credentials test failed."
                    try:
                        error_data = resp.json()
                        error_msg = error_data.get("detail", error_msg)
                    except Exception:
                        pass
                    return error_msg, "danger", True

            elif button_id == "profile-gee-delete-btn" and delete_clicks:
                # Delete credentials
                resp = make_authenticated_request(
                    "/user/me/gee-credentials",
                    token,
                    method="DELETE",
                    timeout=10,
                )

                if resp.status_code == 200:
                    return (
                        [
                            html.I(className="fas fa-trash me-2"),
                            "Google Earth Engine credentials deleted successfully.",
                        ],
                        "warning",
                        True,
                    )
                else:
                    error_msg = "Failed to delete credentials."
                    try:
                        error_data = resp.json()
                        error_msg = error_data.get("detail", error_msg)
                    except Exception:
                        pass
                    return error_msg, "danger", True

        except Exception as e:
            logger.exception("Error with GEE management action: %s", e)
            return f"Network error: {str(e)}", "danger", True

        return no_update, no_update, no_update
