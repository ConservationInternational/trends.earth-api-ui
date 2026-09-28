"""Per-application access management callbacks for the edit user modal."""

import logging
from typing import Any

from dash import Input, Output, State, html, no_update
import dash_bootstrap_components as dbc

from ..utils.helpers import extract_api_error, is_superadmin, make_authenticated_request

logger = logging.getLogger(__name__)

APPS_ENDPOINT = "/admin/app-access/apps"
GRANTS_ENDPOINT = "/admin/app-access"

STATUS_COLORS = {"active": "success", "pending": "warning", "revoked": "secondary"}


def _fetch_apps(token: str) -> list[dict[str, Any]]:
    """Return the registry of gated applications and their role vocabularies."""
    resp = make_authenticated_request(APPS_ENDPOINT, token, timeout=10)
    if resp.status_code != 200:
        logger.warning("Failed to fetch app registry: %s %s", resp.status_code, resp.text)
        return []
    return resp.json().get("data", []) or []


def _fetch_grants(token: str, user_id: str) -> list[dict[str, Any]]:
    """Return every access grant recorded for a user."""
    resp = make_authenticated_request(
        GRANTS_ENDPOINT,
        token,
        params={"user_id": user_id, "per_page": 100},
        timeout=10,
    )
    if resp.status_code != 200:
        logger.warning("Failed to fetch app access grants: %s %s", resp.status_code, resp.text)
        return []
    return resp.json().get("data", []) or []


def _render_grants(apps: list[dict[str, Any]], grants: list[dict[str, Any]]):
    """Build the read-only summary of a user's current access."""
    labels = {app.get("app_key"): app.get("label") for app in apps}
    by_app = {grant.get("app_key"): grant for grant in grants}
    app_keys = list(labels) or list(by_app)
    if not app_keys:
        return html.Small("No gated applications are configured.", className="text-muted")

    items = []
    for app_key in app_keys:
        grant = by_app.get(app_key)
        status = (grant or {}).get("status")
        badge_text = status or "no access"
        details = ""
        if status == "active" and grant.get("role"):
            details = f" \u2013 role: {grant['role']}"
        items.append(
            html.Li(
                [
                    html.Span(labels.get(app_key) or app_key, className="fw-bold me-2"),
                    dbc.Badge(
                        badge_text,
                        color=STATUS_COLORS.get(status, "light"),
                        text_color="dark" if status is None else None,
                        className="me-1",
                    ),
                    html.Small(details, className="text-muted"),
                ],
                className="mb-1",
            )
        )
    return html.Ul(items, className="list-unstyled mb-0")


def register_callbacks(app):
    """Register application access callbacks."""

    @app.callback(
        Output("edit-user-app-access-section", "style"),
        Input("role-store", "data"),
        prevent_initial_call=False,
    )
    def toggle_app_access_section(role):
        """Only superadmins may view or change per-application access."""
        return {"display": "block"} if is_superadmin(role) else {"display": "none"}

    @app.callback(
        [
            Output("edit-user-app-access-current", "children"),
            Output("edit-user-app-access-apps", "data"),
            Output("edit-user-app-access-app", "options"),
            Output("edit-user-app-access-app", "value"),
        ],
        [
            Input("edit-user-modal-user-id", "data"),
            Input("edit-user-app-access-refresh", "data"),
        ],
        [
            State("token-store", "data"),
            State("role-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def load_app_access(user_id, _refresh, token, role):
        """Load the app registry and the target user's grants when the modal opens."""
        if not user_id or not token or not is_superadmin(role):
            return "", [], [], None

        try:
            apps = _fetch_apps(token)
            grants = _fetch_grants(token, user_id)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Error loading app access: %s", exc)
            return (
                html.Small(f"Could not load access: {exc}", className="text-danger"),
                [],
                [],
                None,
            )

        options = [
            {"label": app.get("label") or app.get("app_key"), "value": app.get("app_key")}
            for app in apps
            if app.get("app_key")
        ]
        default_app = options[0]["value"] if options else None
        return _render_grants(apps, grants), apps, options, default_app

    @app.callback(
        [
            Output("edit-user-app-access-role", "options"),
            Output("edit-user-app-access-role", "value"),
        ],
        Input("edit-user-app-access-app", "value"),
        State("edit-user-app-access-apps", "data"),
        prevent_initial_call=True,
    )
    def update_role_options(app_key, apps):
        """Restrict the app role choices to the selected application's vocabulary."""
        roles = []
        for entry in apps or []:
            if entry.get("app_key") == app_key:
                roles = entry.get("roles") or []
                break
        options = [{"label": r, "value": r} for r in roles]
        default = "member" if "member" in roles else (roles[0] if roles else None)
        return options, default

    @app.callback(
        [
            Output("edit-user-app-access-alert", "children"),
            Output("edit-user-app-access-alert", "color"),
            Output("edit-user-app-access-alert", "is_open"),
            Output("edit-user-app-access-refresh", "data"),
            Output("refresh-users-btn", "n_clicks", allow_duplicate=True),
        ],
        Input("edit-user-app-access-apply-btn", "n_clicks"),
        [
            State("edit-user-modal-user-id", "data"),
            State("edit-user-app-access-app", "value"),
            State("edit-user-app-access-status", "value"),
            State("edit-user-app-access-role", "value"),
            State("edit-user-app-access-note", "value"),
            State("edit-user-app-access-refresh", "data"),
            State("token-store", "data"),
            State("role-store", "data"),
            State("refresh-users-btn", "n_clicks"),
        ],
        prevent_initial_call=True,
    )
    def apply_app_access(
        n_clicks,
        user_id,
        app_key,
        status,
        app_role,
        note,
        refresh_count,
        token,
        role,
        users_refresh_clicks,
    ):
        """Grant, update, or revoke the selected application access for the user."""
        if not n_clicks or not token or not user_id:
            return no_update, no_update, no_update, no_update, no_update
        if not is_superadmin(role):
            return (
                "Only superadmins can change application access.",
                "danger",
                True,
                no_update,
                no_update,
            )
        if not app_key:
            return "Select an application first.", "warning", True, no_update, no_update

        try:
            if status == "revoked":
                resp = make_authenticated_request(
                    f"/admin/users/{user_id}/app-access/{app_key}",
                    token,
                    method="DELETE",
                    json={"note": note} if note else {},
                    timeout=10,
                )
            else:
                payload = {"app_key": app_key, "status": status}
                if app_role:
                    payload["role"] = app_role
                if note:
                    payload["note"] = note
                resp = make_authenticated_request(
                    f"/admin/users/{user_id}/app-access",
                    token,
                    method="POST",
                    json=payload,
                    timeout=10,
                )
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Error updating app access: %s", exc)
            return f"Network error: {exc}", "danger", True, no_update, no_update

        if resp.status_code in (200, 201):
            return (
                f"Access for {app_key} set to {status}.",
                "success",
                True,
                (refresh_count or 0) + 1,
                (users_refresh_clicks or 0) + 1,
            )

        error_msg = extract_api_error(resp, "Failed to update application access.")
        return error_msg, "danger", True, no_update, no_update
