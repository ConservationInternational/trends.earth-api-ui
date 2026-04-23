"""OpenEO credentials management callbacks."""

import logging

from dash import Input, Output, State, callback_context, html, no_update
import dash_bootstrap_components as dbc

from ..i18n import gettext as _

logger = logging.getLogger(__name__)

_OPENEO_ENDPOINT = "/user/me/openeo-credentials"
_OPENEO_CHECK_ENDPOINT = "/user/me/openeo-credentials/check"


def register_callbacks(app):
    """Register openEO credentials callbacks."""

    @app.callback(
        Output("profile-openeo-status-display", "children"),
        [Input("token-store", "data")],
        prevent_initial_call=False,
    )
    def update_openeo_status_display(token):
        """Update the openEO credentials status display."""
        if not token:
            return html.Div(_("Please log in to view credentials status."), className="text-muted")

        try:
            from ..utils.helpers import make_authenticated_request

            resp = make_authenticated_request(_OPENEO_ENDPOINT, token)

            if resp.status_code == 200:
                data = resp.json().get("data", {})
                has_credentials = data.get("has_credentials", False)
                credential_type = data.get("credential_type")

                if has_credentials:
                    type_labels = {
                        "oidc_refresh_token": _("OIDC Refresh Token"),
                        "basic": _("Basic Auth"),
                    }
                    type_label = type_labels.get(credential_type, credential_type or _("Unknown"))

                    return [
                        dbc.Alert(
                            [
                                html.I(className="fas fa-check-circle me-2"),
                                _("openEO credentials configured ({type_label})").format(
                                    type_label=type_label
                                ),
                            ],
                            color="success",
                            className="mb-2",
                        )
                    ]
                else:
                    return dbc.Alert(
                        [
                            html.I(className="fas fa-exclamation-triangle me-2"),
                            _("No openEO credentials configured."),
                            html.Br(),
                            html.Small(
                                _("Choose a credential type below to set up access."),
                                className="text-muted",
                            ),
                        ],
                        color="warning",
                    )
            else:
                return dbc.Alert(
                    _("Unable to retrieve openEO credentials status."),
                    color="danger",
                )

        except Exception as e:
            logger.exception("Error getting openEO status: %s", e)
            return dbc.Alert(
                _("Error retrieving openEO credentials status."),
                color="danger",
            )

    @app.callback(
        [
            Output("profile-openeo-check-btn", "disabled"),
            Output("profile-openeo-delete-btn", "disabled"),
        ],
        [Input("profile-openeo-status-display", "children")],
        prevent_initial_call=True,
    )
    def update_openeo_button_states(status_children):
        """Enable/disable management buttons based on credentials status."""
        has_credentials = False
        if status_children and isinstance(status_children, list):
            for child in status_children:
                if hasattr(child, "props") and child.props.get("color") == "success":
                    has_credentials = True
                    break

        return not has_credentials, not has_credentials

    # Show/hide the OIDC vs Basic form sections based on credential type selection
    app.clientside_callback(
        """
        function(cred_type) {
            var nu = window.dash_clientside.no_update;
            if (!cred_type) return [nu, nu];
            var oidc_style = cred_type === "oidc_refresh_token" ? {"display": "block"} : {"display": "none"};
            var basic_style = cred_type === "basic" ? {"display": "block"} : {"display": "none"};
            return [oidc_style, basic_style];
        }
        """,
        [
            Output("profile-openeo-oidc-fields", "style"),
            Output("profile-openeo-basic-fields", "style"),
        ],
        Input("profile-openeo-cred-type", "value"),
        prevent_initial_call=False,
    )

    @app.callback(
        [
            Output("profile-openeo-save-alert", "children"),
            Output("profile-openeo-save-alert", "color"),
            Output("profile-openeo-save-alert", "is_open"),
            Output("profile-openeo-status-display", "children", allow_duplicate=True),
        ],
        [Input("profile-openeo-save-btn", "n_clicks")],
        [
            State("profile-openeo-cred-type", "value"),
            # OIDC fields
            State("profile-openeo-oidc-client-id", "value"),
            State("profile-openeo-oidc-client-secret", "value"),
            State("profile-openeo-oidc-refresh-token", "value"),
            State("profile-openeo-oidc-provider-id", "value"),
            # Basic auth fields
            State("profile-openeo-basic-username", "value"),
            State("profile-openeo-basic-password", "value"),
            State("token-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def save_openeo_credentials(
        n_clicks,
        cred_type,
        oidc_client_id,
        oidc_client_secret,
        oidc_refresh_token,
        oidc_provider_id,
        basic_username,
        basic_password,
        token,
    ):
        """Save openEO credentials."""
        _no_change = no_update, no_update, no_update, no_update
        if not n_clicks or not token:
            return _no_change

        if not cred_type:
            return (
                _("Please select a credential type."),
                "danger",
                True,
                no_update,
            )

        if cred_type == "oidc_refresh_token":
            if not oidc_client_id or not oidc_refresh_token:
                return (
                    _("Client ID and Refresh Token are required for OIDC credentials."),
                    "danger",
                    True,
                    no_update,
                )
            payload = {
                "type": "oidc_refresh_token",
                "client_id": oidc_client_id.strip(),
                "refresh_token": oidc_refresh_token.strip(),
            }
            if oidc_client_secret and oidc_client_secret.strip():
                payload["client_secret"] = oidc_client_secret.strip()
            if oidc_provider_id and oidc_provider_id.strip():
                payload["provider_id"] = oidc_provider_id.strip()
        else:  # basic
            if not basic_username or not basic_password:
                return (
                    _("Username and Password are required for Basic Auth credentials."),
                    "danger",
                    True,
                    no_update,
                )
            payload = {
                "type": "basic",
                "username": basic_username.strip(),
                "password": basic_password,
            }

        try:
            from ..utils.helpers import make_authenticated_request

            resp = make_authenticated_request(
                _OPENEO_ENDPOINT,
                token,
                method="POST",
                json=payload,
                timeout=15,
            )

            if resp.status_code == 200:
                # Rebuild the status display to show the new credential
                type_labels = {
                    "oidc_refresh_token": _("OIDC Refresh Token"),
                    "basic": _("Basic Auth"),
                }
                type_label = type_labels.get(cred_type, cred_type)
                new_status = [
                    dbc.Alert(
                        [
                            html.I(className="fas fa-check-circle me-2"),
                            _("openEO credentials configured ({type_label})").format(
                                type_label=type_label
                            ),
                        ],
                        color="success",
                        className="mb-2",
                    )
                ]
                return (
                    [
                        html.I(className="fas fa-check-circle me-2"),
                        _("openEO credentials saved successfully."),
                    ],
                    "success",
                    True,
                    new_status,
                )
            else:
                error_msg = _("Failed to save openEO credentials.")
                try:
                    error_data = resp.json()
                    error_msg = error_data.get("detail", error_msg)
                except Exception:
                    logger.debug("Could not parse API error response", exc_info=True)
                return error_msg, "danger", True, no_update

        except Exception as e:
            logger.exception("Error saving openEO credentials: %s", e)
            return _("Network error: {error}").format(error=str(e)), "danger", True, no_update

    @app.callback(
        [
            Output("profile-openeo-management-alert", "children"),
            Output("profile-openeo-management-alert", "color"),
            Output("profile-openeo-management-alert", "is_open"),
            Output("profile-openeo-status-display", "children", allow_duplicate=True),
        ],
        [
            Input("profile-openeo-check-btn", "n_clicks"),
            Input("profile-openeo-delete-btn", "n_clicks"),
        ],
        [State("token-store", "data")],
        prevent_initial_call=True,
    )
    def handle_openeo_management_actions(check_clicks, delete_clicks, token):
        """Handle checking and deleting openEO credentials."""
        _no_change = no_update, no_update, no_update, no_update
        if not token:
            return _no_change

        ctx = callback_context
        if not ctx.triggered:
            return _no_change

        button_id = ctx.triggered[0]["prop_id"].split(".")[0]

        try:
            from ..utils.helpers import make_authenticated_request

            if button_id == "profile-openeo-check-btn" and check_clicks:
                resp = make_authenticated_request(
                    _OPENEO_CHECK_ENDPOINT,
                    token,
                    timeout=30,
                )
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    valid = data.get("valid", False)
                    message = data.get("message", "")
                    if valid:
                        return (
                            [
                                html.I(className="fas fa-check-circle me-2"),
                                _("openEO credentials are valid. {message}").format(
                                    message=message
                                ),
                            ],
                            "success",
                            True,
                            no_update,
                        )
                    else:
                        return (
                            [
                                html.I(className="fas fa-times-circle me-2"),
                                _("openEO credentials check failed. {message}").format(
                                    message=message
                                ),
                            ],
                            "danger",
                            True,
                            no_update,
                        )
                else:
                    error_msg = _("Credentials check failed.")
                    try:
                        error_data = resp.json()
                        error_msg = error_data.get("detail", error_msg)
                    except Exception:
                        logger.debug("Could not parse API error response", exc_info=True)
                    return error_msg, "danger", True, no_update

            elif button_id == "profile-openeo-delete-btn" and delete_clicks:
                resp = make_authenticated_request(
                    _OPENEO_ENDPOINT,
                    token,
                    method="DELETE",
                    timeout=10,
                )
                if resp.status_code == 200:
                    deleted_status = dbc.Alert(
                        [
                            html.I(className="fas fa-exclamation-triangle me-2"),
                            _("No openEO credentials configured."),
                            html.Br(),
                            html.Small(
                                _("Choose a credential type below to set up access."),
                                className="text-muted",
                            ),
                        ],
                        color="warning",
                    )
                    return (
                        [
                            html.I(className="fas fa-trash me-2"),
                            _("openEO credentials deleted successfully."),
                        ],
                        "warning",
                        True,
                        deleted_status,
                    )
                else:
                    error_msg = _("Failed to delete credentials.")
                    try:
                        error_data = resp.json()
                        error_msg = error_data.get("detail", error_msg)
                    except Exception:
                        logger.debug("Could not parse API error response", exc_info=True)
                    return error_msg, "danger", True, no_update

        except Exception as e:
            logger.exception("Error with openEO management action: %s", e)
            return _("Network error: {error}").format(error=str(e)), "danger", True, no_update

        return _no_change
