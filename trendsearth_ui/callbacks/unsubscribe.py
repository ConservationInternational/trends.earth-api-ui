"""Unsubscribe / email preference callbacks.

These callbacks handle the public unsubscribe page — accessible directly from
the link embedded in bulk email footers.  No login token is required; the
signed JWT in the URL authenticates the request to the API.
"""

import logging

import requests

from ..config import get_api_base
from ..i18n import gettext as _

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
            Output("unsubscribe-sub-automated", "value"),
            Output("unsubscribe-sub-news", "value"),
            Output("unsubscribe-sub-engagement", "value"),
            Output("unsubscribe-sub-system-updates", "value"),
            Output("unsubscribe-alert", "children", allow_duplicate=True),
            Output("unsubscribe-alert", "color", allow_duplicate=True),
            Output("unsubscribe-alert", "is_open", allow_duplicate=True),
        ],
        [Input("unsubscribe-token-store", "data")],
        [State("unsubscribe-api-env", "data")],
        prevent_initial_call=True,
    )
    def load_unsubscribe_prefs(token, api_environment):
        """Fetch the user's current subscription preferences from the API."""
        if not token:
            return (
                True,
                True,
                True,
                True,
                _("No unsubscribe token found. Please use the link from your email."),
                "warning",
                True,
            )

        url = f"{_api_base(api_environment)}/api/v1/unsubscribe?token={token}"
        try:
            resp = requests.get(url, timeout=_DEFAULT_TIMEOUT)
        except Exception as exc:
            logger.exception("Error fetching unsubscribe prefs: %s", exc)
            return (
                True,
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
                data.get("automated", True),
                data.get("news", True),
                data.get("engagement", True),
                data.get("system_updates", True),
                no_update,
                no_update,
                False,
            )
        else:
            error_msg = _("Failed to load preferences.")
            import contextlib

            with contextlib.suppress(Exception):
                error_msg = resp.json().get("detail", error_msg)
            return (
                True,
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
            State("unsubscribe-sub-automated", "value"),
            State("unsubscribe-sub-news", "value"),
            State("unsubscribe-sub-engagement", "value"),
            State("unsubscribe-sub-system-updates", "value"),
            State("unsubscribe-api-env", "data"),
        ],
        prevent_initial_call=True,
    )
    def save_unsubscribe_prefs(
        n_clicks, token, automated, news, engagement, system_updates, api_environment
    ):
        """Save the user's subscription preferences via the public API endpoint."""
        if not n_clicks:
            raise PreventUpdate

        if not token:
            return (
                _("No unsubscribe token found. Please use the link from your email."),
                "warning",
                True,
            )

        url = f"{_api_base(api_environment)}/api/v1/unsubscribe?token={token}"
        payload = {
            "automated": bool(automated),
            "news": bool(news),
            "engagement": bool(engagement),
            "system_updates": bool(system_updates),
        }
        try:
            resp = requests.patch(url, json=payload, timeout=_DEFAULT_TIMEOUT)
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
            error_msg = _("Failed to save preferences.")
            import contextlib

            with contextlib.suppress(Exception):
                error_msg = resp.json().get("detail", error_msg)
            return error_msg, "danger", True

    @app.callback(
        [
            Output("unsubscribe-sub-automated", "value", allow_duplicate=True),
            Output("unsubscribe-sub-news", "value", allow_duplicate=True),
            Output("unsubscribe-sub-engagement", "value", allow_duplicate=True),
            Output("unsubscribe-sub-system-updates", "value", allow_duplicate=True),
            Output("unsubscribe-alert", "children", allow_duplicate=True),
            Output("unsubscribe-alert", "color", allow_duplicate=True),
            Output("unsubscribe-alert", "is_open", allow_duplicate=True),
        ],
        [Input("unsubscribe-all-btn", "n_clicks")],
        [
            State("unsubscribe-token-store", "data"),
            State("unsubscribe-api-env", "data"),
        ],
        prevent_initial_call=True,
    )
    def unsubscribe_from_all(n_clicks, token, api_environment):
        """Unsubscribe from all email types in one click."""
        if not n_clicks:
            raise PreventUpdate

        if not token:
            return (
                True,
                True,
                True,
                True,
                _("No unsubscribe token found. Please use the link from your email."),
                "warning",
                True,
            )

        url = f"{_api_base(api_environment)}/api/v1/unsubscribe?token={token}"
        payload = {"automated": False, "news": False, "engagement": False, "system_updates": False}
        try:
            resp = requests.patch(url, json=payload, timeout=_DEFAULT_TIMEOUT)
        except Exception as exc:
            logger.exception("Error saving unsubscribe prefs: %s", exc)
            return True, True, True, _("Network error. Please try again."), "danger", True

        if resp.status_code == 200:
            return (
                False,
                False,
                False,
                False,
                _("You have been unsubscribed from all emails."),
                "success",
                True,
            )
        else:
            error_msg = _("Failed to save preferences.")
            import contextlib

            with contextlib.suppress(Exception):
                error_msg = resp.json().get("detail", error_msg)
            return True, True, True, True, error_msg, "danger", True
