"""Google Earth Engine credentials management callbacks."""

import base64
import json
import logging

from dash import Input, Output, State, callback_context, html, no_update
import dash_bootstrap_components as dbc

from ..i18n import gettext as _

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
            return html.Div(_("Please log in to view credentials status."), className="text-muted")

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
                    created_date = _("Unknown")
                    if created_at:
                        try:
                            from datetime import datetime

                            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                            created_date = dt.strftime("%Y-%m-%d %H:%M UTC")
                        except Exception:
                            logger.debug("Could not parse date: %s", created_at, exc_info=True)
                            created_date = str(created_at)

                    type_label = _("OAuth") if credentials_type == "oauth" else _("Service Account")

                    status_content = [
                        dbc.Alert(
                            [
                                html.I(className="fas fa-check-circle me-2"),
                                _("Credentials configured using {type_label}").format(
                                    type_label=type_label
                                ),
                                html.Br(),
                                html.Small(
                                    _("Set up on: {created_date}").format(
                                        created_date=created_date
                                    ),
                                    className="text-muted",
                                ),
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
                            _("No Google Earth Engine credentials configured."),
                            html.Br(),
                            html.Small(
                                _("Choose one of the setup options below."), className="text-muted"
                            ),
                        ],
                        color="warning",
                    )
            else:
                return dbc.Alert(
                    _("Unable to retrieve credentials status."),
                    color="danger",
                )

        except Exception as e:
            logger.exception("Error getting GEE status: %s", e)
            return dbc.Alert(
                _("Error retrieving credentials status."),
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
            Output("url", "href"),
        ],
        [Input("profile-gee-oauth-btn", "n_clicks")],
        [State("token-store", "data")],
        prevent_initial_call=True,
    )
    def initiate_gee_oauth(n_clicks, token):
        """Initiate Google Earth Engine OAuth flow."""
        if not n_clicks or not token:
            return no_update, no_update, no_update, no_update

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
                    # Navigate the browser to Google's authorization page.
                    # The redirect_uri registered in the API points back to
                    # this UI's /gee-oauth-callback route, which will complete
                    # the exchange.
                    return no_update, no_update, no_update, auth_url
                else:
                    return (
                        _("OAuth initiation failed - no authorization URL received."),
                        "danger",
                        True,
                        no_update,
                    )
            else:
                error_msg = _("Failed to initiate OAuth flow.")
                try:
                    error_data = resp.json()
                    error_msg = error_data.get("detail", error_msg)
                except Exception:
                    logger.debug("Could not parse API error response", exc_info=True)
                return error_msg, "danger", True, no_update

        except Exception as e:
            logger.exception("Error initiating OAuth: %s", e)
            return _(
                "Network error: {error}"
            ).format(error=str(e)), "danger", True, no_update

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
                    _("Invalid JSON file. Please upload a valid service account key file."),
                    "danger",
                    True,
                )

            # Validate it looks like a service account key
            required_fields = ["type", "project_id", "private_key", "client_email"]
            if not all(field in service_account_key for field in required_fields):
                return _("Invalid service account key. Missing required fields."), "danger", True

            if service_account_key.get("type") != "service_account":
                return (
                    _("Invalid service account key. Type field must be 'service_account'."),
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
                        _("Service account key '{filename}' uploaded successfully!").format(
                            filename=filename
                        ),
                    ],
                    "success",
                    True,
                )
            else:
                error_msg = _("Failed to upload service account key.")
                try:
                    error_data = resp.json()
                    error_msg = error_data.get("detail", error_msg)
                except Exception:
                    logger.debug("Could not parse API error response", exc_info=True)
                return error_msg, "danger", True

        except Exception as e:
            logger.exception("Error uploading service account: %s", e)
            return _("Error processing file: {error}").format(error=str(e)), "danger", True

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
                            _("Google Earth Engine credentials are valid and working!"),
                        ],
                        "success",
                        True,
                    )
                else:
                    error_msg = _("Credentials test failed.")
                    try:
                        error_data = resp.json()
                        error_msg = error_data.get("detail", error_msg)
                    except Exception:
                        logger.debug("Could not parse API error response", exc_info=True)
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
                            _("Google Earth Engine credentials deleted successfully."),
                        ],
                        "warning",
                        True,
                    )
                else:
                    error_msg = _("Failed to delete credentials.")
                    try:
                        error_data = resp.json()
                        error_msg = error_data.get("detail", error_msg)
                    except Exception:
                        logger.debug("Could not parse API error response", exc_info=True)
                    return error_msg, "danger", True

        except Exception as e:
            logger.exception("Error with GEE management action: %s", e)
            return _(
                "Network error: {error}"
            ).format(error=str(e)), "danger", True

        return no_update, no_update, no_update

    @app.callback(
        [
            Output("gee-oauth-callback-alert", "children"),
            Output("gee-oauth-callback-alert", "color"),
            Output("gee-oauth-callback-alert", "is_open"),
            Output("gee-oauth-processing-container", "children"),
        ],
        [Input("gee-oauth-auto-process", "n_intervals")],
        [
            State("gee-oauth-callback-code", "data"),
            State("gee-oauth-callback-state", "data"),
            State("token-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def process_gee_oauth_callback(n_intervals, code, state, token):
        """Exchange the OAuth authorization code for tokens and store them.

        Triggered once by the auto-process Interval after the page loads,
        giving token-store time to be hydrated from the auth cookie.
        """
        if not n_intervals:
            return no_update, no_update, no_update, no_update

        idle_spinner = html.Div()  # replace the spinner with nothing on completion

        if not token:
            return (
                [
                    html.I(className="fas fa-exclamation-triangle me-2"),
                    _(
                        "You must be logged in to connect Google Earth Engine."
                        " Please log in and try again."
                    ),
                    html.Br(),
                    html.Small(
                        html.A(_("Back to login"), href="/", className="text-muted"),
                    ),
                ],
                "danger",
                True,
                idle_spinner,
            )

        if not code or not state:
            return (
                _(
                    "Invalid callback — missing authorization code or state parameter."
                ),
                "danger",
                True,
                idle_spinner,
            )

        try:
            from ..utils.helpers import make_authenticated_request

            resp = make_authenticated_request(
                "/user/me/gee-oauth/callback",
                token,
                method="POST",
                json={"code": code, "state": state},
                timeout=30,
            )

            if resp.status_code == 200:
                return (
                    [
                        html.I(className="fas fa-check-circle me-2"),
                        _(
                            "Google Earth Engine connected successfully!"
                            " You can close this page and return to the app."
                        ),
                    ],
                    "success",
                    True,
                    idle_spinner,
                )
            else:
                error_msg = _("Failed to complete Google Earth Engine authorization.")
                try:
                    error_data = resp.json()
                    error_msg = error_data.get("detail", error_msg)
                except Exception:
                    logger.debug("Could not parse OAuth callback response", exc_info=True)
                return error_msg, "danger", True, idle_spinner

        except Exception as e:
            logger.exception("Error completing GEE OAuth callback: %s", e)
            return (
                _(
                    "Network error while completing authorization: {error}"
                ).format(error=str(e)),
                "danger",
                True,
                idle_spinner,
            )
