"""Unsubscribe / email preference callbacks.

These callbacks handle the public unsubscribe page — accessible directly from
the link embedded in bulk email footers.  No login token is required; the
signed JWT in the URL authenticates the request to the API.
"""

import logging

from ..config import get_api_base
from ..i18n import gettext as _
from ..utils.helpers import extract_api_error
from ..utils.http_client import get_session

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 10


def _api_base(api_environment):
    return get_api_base(api_environment or "production")


def register_callbacks(app):
    """Register unsubscribe page callbacks."""

    from dash import Input, Output, State, no_update
    from dash.exceptions import PreventUpdate

    @app.callback(
        [
            Output("unsubscribe-sub-news", "value"),
            Output("unsubscribe-sub-engagement", "value"),
            Output("unsubscribe-sub-system-updates", "value"),
            Output("unsubscribe-alert", "children", allow_duplicate=True),
            Output("unsubscribe-alert", "color", allow_duplicate=True),
            Output("unsubscribe-alert", "is_open", allow_duplicate=True),
        ],
        [Input("unsubscribe-token-store", "data")],
        [State("unsubscribe-api-env", "data")],
        prevent_initial_call="initial_duplicate",
    )
    def load_unsubscribe_prefs(token, api_environment):
        """Fetch the user's current subscription preferences from the API."""
        if not token:
            return (
                True,
                True,
                True,
                _("No unsubscribe token found. Please use the link from your email."),
                "warning",
                True,
            )

        url = f"{_api_base(api_environment)}/unsubscribe?token={token}"
        try:
            resp = get_session().get(url, timeout=_DEFAULT_TIMEOUT)
        except Exception as exc:
            logger.exception("Error fetching unsubscribe prefs: %s", exc)
            return (
                True,
                True,
                True,
                _("Network error. Please try again."),
                "danger",
                True,
            )

        if resp.status_code == 200:
            data = resp.json().get("data", {})
            return (
                data.get("news", True),
                data.get("engagement", True),
                data.get("system_updates", True),
                no_update,
                no_update,
                False,
            )
        else:
            error_msg = extract_api_error(resp, _("Failed to load preferences."))
            return (
                True,
                True,
                True,
                error_msg,
                "danger",
                True,
            )

    @app.callback(
        [
            Output("unsubscribe-alert", "children"),
            Output("unsubscribe-alert", "color"),
            Output("unsubscribe-alert", "is_open"),
        ],
        [Input("unsubscribe-save-btn", "n_clicks")],
        [
            State("unsubscribe-token-store", "data"),
            State("unsubscribe-sub-news", "value"),
            State("unsubscribe-sub-engagement", "value"),
            State("unsubscribe-sub-system-updates", "value"),
            State("unsubscribe-api-env", "data"),
        ],
        prevent_initial_call=True,
    )
    def save_unsubscribe_prefs(n_clicks, token, news, engagement, system_updates, api_environment):
        """Save the user's subscription preferences via the public API endpoint."""
        if not n_clicks:
            raise PreventUpdate

        if not token:
            return (
                _("No unsubscribe token found. Please use the link from your email."),
                "warning",
                True,
            )

        url = f"{_api_base(api_environment)}/unsubscribe?token={token}"
        payload = {
            "news": bool(news),
            "engagement": bool(engagement),
            "system_updates": bool(system_updates),
        }
        try:
            resp = get_session().patch(url, json=payload, timeout=_DEFAULT_TIMEOUT)
        except Exception as exc:
            logger.exception("Error saving unsubscribe prefs: %s", exc)
            return _("Network error. Please try again."), "danger", True

        if resp.status_code == 200:
            return (
                _("Your email preferences have been saved successfully."),
                "success",
                True,
            )
        else:
            error_msg = extract_api_error(resp, _("Failed to save preferences."))
            return error_msg, "danger", True
