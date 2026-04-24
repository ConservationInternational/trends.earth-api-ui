"""Google Earth Engine credentials management callbacks."""

import base64
import contextlib
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
            Output("gee-oauth-redirect-url", "data"),
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
            return _("Network error: {error}").format(error=str(e)), "danger", True, no_update

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
            return _("Network error: {error}").format(error=str(e)), "danger", True

        return no_update, no_update, no_update

    @app.callback(
        [
            Output("gee-oauth-callback-alert", "children"),
            Output("gee-oauth-callback-alert", "color"),
            Output("gee-oauth-callback-alert", "is_open"),
            Output("gee-oauth-processing-container", "children"),
            Output("gee-project-load-interval", "max_intervals"),
            Output("gee-project-load-interval", "disabled"),
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
        On success, enables the project-load interval so the GCP project
        dropdown is populated automatically.
        """
        if not n_intervals:
            return no_update, no_update, no_update, no_update, no_update, no_update

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
                no_update,
                no_update,
            )

        if not code or not state:
            return (
                _("Invalid callback — missing authorization code or state parameter."),
                "danger",
                True,
                idle_spinner,
                no_update,
                no_update,
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
                            " Please select your GCP project below to complete setup."
                        ),
                    ],
                    "success",
                    True,
                    idle_spinner,
                    1,  # max_intervals=1 → fire once to fetch projects
                    False,  # disabled=False  → enable the interval
                )
            else:
                error_msg = _("Failed to complete Google Earth Engine authorization.")
                try:
                    error_data = resp.json()
                    error_msg = error_data.get("detail", error_msg)
                except Exception:
                    logger.debug("Could not parse OAuth callback response", exc_info=True)
                return error_msg, "danger", True, idle_spinner, no_update, no_update

        except Exception as e:
            logger.exception("Error completing GEE OAuth callback: %s", e)
            return (
                _("Network error while completing authorization: {error}").format(error=str(e)),
                "danger",
                True,
                idle_spinner,
                no_update,
                no_update,
            )

    @app.callback(
        [
            Output("gee-project-dropdown", "options"),
            Output("gee-project-dropdown", "value"),
            Output("gee-project-selection-container", "style"),
            Output("gee-project-manual-container", "style"),
        ],
        [Input("gee-project-load-interval", "n_intervals")],
        [State("token-store", "data")],
        prevent_initial_call=True,
    )
    def load_gee_projects(n_intervals, token):
        """Fetch the user's accessible GCP projects and populate the dropdown.

        Fired once by the project-load interval after OAuth completes.
        Projects are returned in ``{"value": projectId, "label": displayName}``
        format from the API.  The currently saved project (if any) is pre-selected.
        When the project list is empty or the API call fails, the manual-entry
        input is shown instead.
        """
        if not n_intervals or not token:
            return no_update, no_update, no_update, no_update

        shown = {"display": "block"}
        hidden = {"display": "none"}

        try:
            from ..utils.helpers import make_authenticated_request

            resp = make_authenticated_request("/user/me/gee-projects", token, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                options = data.get("data", [])  # [{value, label}, ...]
                current = data.get("current")  # currently saved project ID or null
                if options:
                    return options, current, shown, hidden
                # No projects — fall through to manual entry
                return [], None, shown, shown
            else:
                logger.warning("Failed to load GCP projects: %s", resp.status_code)
                return [], None, shown, shown

        except Exception as e:
            logger.exception("Error loading GCP projects: %s", e)
            return [], None, shown, shown

    @app.callback(
        [
            Output("gee-project-save-alert", "children"),
            Output("gee-project-save-alert", "color"),
            Output("gee-project-save-alert", "is_open"),
        ],
        [Input("gee-project-save-btn", "n_clicks")],
        [
            State("gee-project-dropdown", "value"),
            State("gee-project-manual-input", "value"),
            State("token-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def save_gee_project(n_clicks, project_id, manual_project_id, token):
        """Save the user's selected GCP project via the API.

        Uses the dropdown value when available; falls back to the manual
        text input when the project list could not be loaded.
        """
        # Use manual input as fallback when dropdown has no selection
        project_id = project_id or (manual_project_id or "").strip() or None
        if not n_clicks or not project_id or not token:
            return no_update, no_update, no_update

        try:
            from ..utils.helpers import make_authenticated_request

            payload: dict = {"cloud_project": project_id}

            resp = make_authenticated_request(
                "/user/me/gee-credentials/project",
                token,
                method="PATCH",
                json=payload,
                timeout=10,
            )
            if resp.status_code == 200:
                resp_json = {}
                with contextlib.suppress(Exception):
                    resp_json = resp.json()
                if resp_json.get("gcs_write_access") is False:
                    detail = resp_json.get(
                        "detail",
                        _(
                            "Project saved, but bucket write access could not be"
                            " configured automatically."
                        ),
                    )
                    return detail, "warning", True
                return (
                    _(
                        "GCP project saved successfully. "
                        "Google Earth Engine setup is complete! "
                        "You can now close this page and return to the app."
                    ),
                    "success",
                    True,
                )
            else:
                error_msg = _("Failed to save project.")
                with contextlib.suppress(Exception):
                    error_msg = resp.json().get("detail", error_msg)
                return error_msg, "danger", True

        except Exception as e:
            logger.exception("Error saving GCP project: %s", e)
            return (
                _("Network error: {error}").format(error=str(e)),
                "danger",
                True,
            )

    @app.callback(
        [
            Output("profile-gee-project-section", "style"),
            Output("profile-gee-project-current-display", "children"),
        ],
        [Input("token-store", "data")],
        prevent_initial_call=False,
    )
    def update_profile_gee_project_section(token):
        """Show/hide the Cloud Project section based on whether OAuth credentials
        are active, and pre-display the currently saved project ID (if any).
        """
        hidden = {"display": "none"}
        visible = {"display": "block"}
        no_project = html.Span(
            _("No project selected."),
            className="text-muted small",
        )

        if not token:
            return hidden, no_project

        try:
            from ..utils.helpers import make_authenticated_request

            resp = make_authenticated_request("/user/me/gee-credentials", token)
            if resp.status_code != 200:
                return hidden, no_project

            data = resp.json().get("data", {})
            if data.get("credentials_type") != "oauth":
                return hidden, no_project

            cloud_project = data.get("cloud_project")
            if cloud_project:
                current_display = html.Span(
                    [
                        _("Current project: "),
                        html.Strong(cloud_project),
                    ],
                    className="small",
                )
            else:
                current_display = html.Span(
                    _("No project selected yet. Click 'Change Project' to choose one."),
                    className="text-warning small",
                )
            return visible, current_display

        except Exception as e:
            logger.exception("Error checking GEE credentials for project section: %s", e)
            return hidden, no_project

    @app.callback(
        [
            Output("profile-gee-project-dropdown", "options"),
            Output("profile-gee-project-dropdown", "value"),
            Output("profile-gee-project-dropdown", "style"),
            Output("profile-gee-project-manual-container", "style"),
            Output("profile-gee-project-update-btn", "style"),
            Output("profile-gee-project-load-alert", "children"),
            Output("profile-gee-project-load-alert", "color"),
            Output("profile-gee-project-load-alert", "is_open"),
        ],
        [Input("profile-gee-project-load-btn", "n_clicks")],
        [State("token-store", "data")],
        prevent_initial_call=True,
    )
    def load_profile_gee_projects(n_clicks, token):
        """Fetch the user's accessible GCP projects and populate the dropdown.

        Fired when the user clicks 'Change Project'. Pre-selects the
        currently saved project ID (if any).  When the project list is empty
        or fails to load, the manual-entry input is shown so the user can
        type their project ID directly.
        """
        if not n_clicks or not token:
            return (
                [],
                None,
                {"display": "none"},
                {"display": "none"},
                {"display": "none"},
                "",
                "",
                False,
            )

        shown = {"display": "block"}
        hidden = {"display": "none"}

        try:
            from ..utils.helpers import make_authenticated_request

            resp = make_authenticated_request("/user/me/gee-projects", token, timeout=15)
            if resp.status_code == 200:
                resp_data = resp.json()
                options = resp_data.get("data", [])
                current = resp_data.get("current")
                if options:
                    # Dropdown available — hide manual input
                    return options, current, shown, hidden, shown, "", "", False
                # No projects returned — show manual input
                return (
                    [],
                    None,
                    hidden,
                    shown,
                    shown,
                    _(
                        "No accessible GCP projects found. Make sure your Google "
                        "account has at least one project with Earth Engine API"
                        " enabled, or enter the project ID manually below."
                    ),
                    "warning",
                    True,
                )
            else:
                error_msg = _("Failed to load projects.")
                try:
                    error_msg = resp.json().get("detail", error_msg)
                except Exception:
                    logger.debug("Could not parse load projects response", exc_info=True)
                return [], None, hidden, shown, shown, error_msg, "danger", True

        except Exception as e:
            logger.exception("Error loading GCP projects for profile: %s", e)
            return (
                [],
                None,
                hidden,
                shown,
                shown,
                _("Network error: {error}").format(error=str(e)),
                "danger",
                True,
            )

    @app.callback(
        [
            Output("profile-gee-project-update-alert", "children"),
            Output("profile-gee-project-update-alert", "color"),
            Output("profile-gee-project-update-alert", "is_open"),
            Output("profile-gee-project-current-display", "children", allow_duplicate=True),
        ],
        [Input("profile-gee-project-update-btn", "n_clicks")],
        [
            State("profile-gee-project-dropdown", "value"),
            State("profile-gee-project-manual-input", "value"),
            State("token-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def save_profile_gee_project(n_clicks, project_id, manual_project_id, token):
        """Save the user's updated GCP project selection.

        Uses the dropdown value when available; falls back to the manual
        text input when the project list could not be loaded.
        """
        # Use manual input as fallback when dropdown has no selection
        project_id = project_id or (manual_project_id or "").strip() or None
        if not n_clicks or not project_id or not token:
            return no_update, no_update, no_update, no_update

        try:
            from ..utils.helpers import make_authenticated_request

            payload: dict = {"cloud_project": project_id}

            resp = make_authenticated_request(
                "/user/me/gee-credentials/project",
                token,
                method="PATCH",
                json=payload,
                timeout=10,
            )
            if resp.status_code == 200:
                new_display = html.Span(
                    [_("Current project: "), html.Strong(project_id)],
                    className="small",
                )
                resp_json = {}
                with contextlib.suppress(Exception):
                    resp_json = resp.json()
                if resp_json.get("gcs_write_access") is False:
                    detail = resp_json.get(
                        "detail",
                        _(
                            "Project saved, but bucket write access could not be"
                            " configured automatically."
                        ),
                    )
                    return detail, "warning", True, new_display
                return (
                    _("Project updated successfully."),
                    "success",
                    True,
                    new_display,
                )
            else:
                error_msg = _("Failed to save project.")
                with contextlib.suppress(Exception):
                    error_msg = resp.json().get("detail", error_msg)
                return error_msg, "danger", True, no_update

        except Exception as e:
            logger.exception("Error saving GCP project from profile: %s", e)
            return (
                _("Network error: {error}").format(error=str(e)),
                "danger",
                True,
                no_update,
            )

    # Clientside callback: navigate to external OAuth URL stored by initiate_gee_oauth.
    # dcc.Location uses history.pushState() which browsers block for cross-origin URLs,
    # so we must do the redirect from JavaScript instead.
    app.clientside_callback(
        """
        function(auth_url) {
            if (auth_url) {
                window.location.href = auth_url;
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("gee-oauth-redirect-url", "data", allow_duplicate=True),
        Input("gee-oauth-redirect-url", "data"),
        prevent_initial_call=True,
    )
