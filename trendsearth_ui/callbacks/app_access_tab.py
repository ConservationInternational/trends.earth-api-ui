"""Callbacks for the App Access tab.

ADMIN/SUPERADMIN users review per-application access requests here; SUPERADMIN
users also manage each application's access-request notification recipients.
Notification emails from the API deep-link to this tab with
``?tab=app-access&app=<app_key>&status=pending``.
"""

import logging
import re
from typing import Any
from urllib.parse import parse_qs

from dash import ALL, Input, Output, State, callback_context, dcc, html, no_update
import dash_bootstrap_components as dbc

from ..utils.helpers import (
    extract_api_error,
    is_admin,
    is_superadmin,
    make_authenticated_request,
)
from .app_access import GRANTS_ENDPOINT, STATUS_COLORS, _fetch_apps

logger = logging.getLogger(__name__)

VALID_STATUS_FILTERS = ("pending", "active", "revoked", "all")
_APP_KEY_RE = re.compile(r"^[a-z0-9_]{1,50}$")
REQUESTS_PAGE_SIZE = 200
RECIPIENT_CANDIDATE_FILTER = "(role='ADMIN' OR role='SUPERADMIN')"
CANDIDATE_PAGE_SIZE = 100  # API maximum for paginated /user
CANDIDATE_MAX_PAGES = 10
CANDIDATE_TIMEOUT = 30


def recipients_endpoint(app_key: str) -> str:
    return f"/admin/app-access/apps/{app_key}/notification-recipients"


def parse_app_access_deeplink(search: str | None) -> dict[str, Any] | None:
    """Parse ``?tab=app-access&app=...&status=...`` into validated filters.

    Returns ``None`` when the query string does not target the App Access tab.
    Unknown/malformed values are dropped rather than trusted.
    """
    if not search:
        return None
    params = parse_qs(search[1:] if search.startswith("?") else search)
    if params.get("tab", [None])[0] != "app-access":
        return None
    app_key = params.get("app", [None])[0]
    if not app_key or not _APP_KEY_RE.match(app_key):
        app_key = None
    status = params.get("status", [None])[0]
    if status not in VALID_STATUS_FILTERS:
        status = "pending"
    return {"app": app_key, "status": status}


def _role_options(apps: list[dict[str, Any]], app_key: str | None) -> list[dict[str, str]]:
    for entry in apps or []:
        if entry.get("app_key") == app_key:
            return [{"label": r, "value": r} for r in entry.get("roles") or []]
    return []


def _default_role(options: list[dict[str, str]], current: str | None = None) -> str | None:
    values = [o["value"] for o in options]
    if current in values:
        return current
    if "member" in values:
        return "member"
    return values[0] if values else None


def _fetch_requests(
    token: str, app_key: str, status: str
) -> tuple[list[dict[str, Any]], int, str | None]:
    """Return ``(grants, total, error)`` for the selected app and status."""
    params: dict[str, Any] = {"app": app_key, "include": "user", "per_page": REQUESTS_PAGE_SIZE}
    if status and status != "all":
        params["status"] = status
    resp = make_authenticated_request(GRANTS_ENDPOINT, token, params=params, timeout=15)
    if resp.status_code != 200:
        return [], 0, extract_api_error(resp, "Failed to load access requests.")
    body = resp.json() or {}
    grants = body.get("data", []) or []
    return grants, body.get("total", len(grants)), None


def _format_timestamp(value: str | None) -> str:
    if not value:
        return ""
    return value.replace("T", " ")[:16]


def _row_actions(grant: dict[str, Any], role_options: list[dict[str, str]]):
    user_id = grant.get("user_id")
    app_key = grant.get("app_key")
    status = grant.get("status")
    key = {"user_id": user_id, "app_key": app_key}
    approve_label = {"pending": "Approve", "active": "Update role", "revoked": "Restore"}.get(
        status, "Approve"
    )
    controls = [
        html.Div(
            _role_dropdown(key, role_options, _default_role(role_options, grant.get("role"))),
            style={"minWidth": "140px"},
            className="me-2",
        )
        if role_options
        else None,
        dbc.Button(
            approve_label,
            id={"type": "app-access-approve-btn", **key},
            color="success",
            size="sm",
            className="me-1",
        ),
    ]
    if status != "revoked":
        controls.append(
            dbc.Button(
                "Deny" if status == "pending" else "Revoke",
                id={"type": "app-access-revoke-btn", **key},
                color="danger",
                outline=True,
                size="sm",
            )
        )
    return html.Div([c for c in controls if c is not None], className="d-flex align-items-center")


def _role_dropdown(key: dict[str, Any], options: list[dict[str, str]], value: str | None):
    return dcc.Dropdown(
        id={"type": "app-access-row-role", **key},
        options=options,
        value=value,
        clearable=False,
    )


def render_requests_table(
    grants: list[dict[str, Any]],
    apps: list[dict[str, Any]],
    app_key: str | None,
    total: int | None = None,
):
    """Render the access requests table for one application."""
    if not app_key:
        return html.Small("Select an application.", className="text-muted")
    if not grants:
        return html.Small("No matching access requests.", className="text-muted")

    role_options = _role_options(apps, app_key)
    header = html.Thead(
        html.Tr(
            [
                html.Th("User"),
                html.Th("Institution / country"),
                html.Th("Requested"),
                html.Th("Request note"),
                html.Th("Status"),
                html.Th("Actions"),
            ]
        )
    )
    rows = []
    for grant in grants:
        user = grant.get("user") or {}
        status = grant.get("status")
        status_text = status or ""
        if status == "active" and grant.get("role"):
            status_text = f"{status} ({grant['role']})"
        affiliation = ", ".join(v for v in (user.get("institution"), user.get("country")) if v)
        rows.append(
            html.Tr(
                [
                    html.Td(
                        [
                            html.Div(user.get("name") or "", className="fw-bold"),
                            html.Small(user.get("email") or grant.get("user_id") or ""),
                        ]
                    ),
                    html.Td(affiliation),
                    html.Td(
                        _format_timestamp(grant.get("requested_at") or grant.get("created_at"))
                    ),
                    html.Td(grant.get("request_note") or ""),
                    html.Td(dbc.Badge(status_text, color=STATUS_COLORS.get(status, "light"))),
                    html.Td(_row_actions(grant, role_options)),
                ]
            )
        )
    children = [
        dbc.Table(
            [header, html.Tbody(rows)],
            bordered=False,
            hover=True,
            responsive=True,
            size="sm",
            className="align-middle",
        )
    ]
    if total is not None and total > len(grants):
        children.append(
            html.Small(f"Showing {len(grants)} of {total} requests.", className="text-muted")
        )
    return html.Div(children)


def _fetch_recipient_candidates(token: str) -> tuple[list[dict[str, Any]], str | None]:
    """Return ``(users, error)`` for every ADMIN/SUPERADMIN account.

    Uses the paginated form of ``/user`` (as the Users table does); the
    unpaginated form can be slow on large deployments.
    """
    users: list[dict[str, Any]] = []
    for page in range(1, CANDIDATE_MAX_PAGES + 1):
        resp = make_authenticated_request(
            "/user",
            token,
            params={
                "filter": RECIPIENT_CANDIDATE_FILTER,
                "page": page,
                "per_page": CANDIDATE_PAGE_SIZE,
            },
            timeout=CANDIDATE_TIMEOUT,
        )
        if resp.status_code != 200:
            logger.warning(
                "Failed to fetch recipient candidates: %s %s", resp.status_code, resp.text
            )
            return users, extract_api_error(resp, "Could not load admin accounts.")
        body = resp.json() or {}
        data = body.get("data", []) or []
        users.extend(u for u in data if is_admin(u.get("role")))
        total = body.get("total")
        if len(data) < CANDIDATE_PAGE_SIZE or (
            total is not None and page * CANDIDATE_PAGE_SIZE >= total
        ):
            break
    return users, None


def _user_label(user: dict[str, Any]) -> str:
    name = user.get("name") or ""
    email = user.get("email") or user.get("id") or user.get("user_id") or ""
    role = user.get("role")
    label = f"{name} <{email}>" if name else email
    return f"{label} ({role})" if role else label


def build_recipient_options(
    candidates: list[dict[str, Any]], listed: list[dict[str, Any]]
) -> tuple[list[dict[str, str]], list[str]]:
    """Return dropdown ``(options, value)`` for the recipients editor.

    Listed recipients that are no longer eligible (demoted/inactive) stay
    visible, flagged, so a superadmin can see and remove them.
    """
    options: dict[str, dict[str, str]] = {}
    for user in candidates:
        user_id = str(user.get("id") or "")
        if user_id:
            options[user_id] = {"label": _user_label(user), "value": user_id}
    value = []
    for entry in listed:
        user_id = str(entry.get("user_id") or "")
        if not user_id:
            continue
        value.append(user_id)
        if not entry.get("eligible", True):
            options[user_id] = {
                "label": f"{_user_label(entry)} \u2013 no longer eligible, remove",
                "value": user_id,
            }
        elif user_id not in options:
            options[user_id] = {"label": _user_label(entry), "value": user_id}
    return sorted(options.values(), key=lambda o: o["label"].lower()), value


def render_recipients_summary(payload: dict[str, Any]):
    """Explain who will actually be emailed for the selected application."""
    effective = payload.get("effective_recipients") or []
    auto_admins = payload.get("auto_app_admins") or []
    if payload.get("using_default"):
        basis = html.P(
            "No eligible recipients are listed, so all superadmins are notified.",
            className="mb-2",
        )
    else:
        basis = html.P("The listed recipients above are notified.", className="mb-2")

    auto_section = [html.Strong("Application admins notified automatically: ")]
    if auto_admins:
        auto_section.append(
            html.Span(", ".join(a.get("email") or a.get("user_id") or "" for a in auto_admins))
        )
    else:
        auto_section.append(html.Span("none", className="text-muted"))

    effective_section = [html.Strong("Everyone emailed for a new request: ")]
    if effective:
        effective_section.append(html.Span(", ".join(effective)))
    else:
        effective_section.append(
            html.Span("nobody \u2013 no eligible recipients exist", className="text-danger")
        )

    return html.Div(
        [
            basis,
            html.P(auto_section, className="mb-2 small"),
            html.P(effective_section, className="mb-0 small"),
        ]
    )


def register_callbacks(app):
    """Register App Access tab callbacks."""

    @app.callback(
        [
            Output("active-tab-store", "data", allow_duplicate=True),
            Output("app-access-deeplink-store", "data", allow_duplicate=True),
        ],
        [Input("url", "search"), Input("role-store", "data")],
        [State("token-store", "data"), State("app-access-deeplink-store", "data")],
        prevent_initial_call=True,
    )
    def apply_app_access_deeplink(search, role, token, current):
        """Open the App Access tab from notification-email links.

        Runs when the URL or the role changes (the role is set after login, so
        links opened while logged out still apply once the user signs in). Each
        query string is applied once so later tab clicks are not overridden.
        """
        filters = parse_app_access_deeplink(search)
        if not filters or not token or not is_admin(role):
            return no_update, no_update
        if (current or {}).get("search") == search:
            return no_update, no_update
        return "app-access", {**filters, "search": search, "applied": False}

    @app.callback(
        [
            Output("app-access-apps-store", "data"),
            Output("app-access-app-filter", "options"),
            Output("app-access-app-filter", "value"),
            Output("app-access-status-filter", "value"),
            Output("app-access-deeplink-store", "data", allow_duplicate=True),
        ],
        Input("app-access-tab-rendered", "data"),
        [
            State("token-store", "data"),
            State("role-store", "data"),
            State("app-access-deeplink-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def init_app_access_tab(_rendered, token, role, deeplink):
        if not token or not is_admin(role):
            return [], [], None, no_update, no_update
        try:
            apps = _fetch_apps(token)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Error loading app registry: %s", exc)
            apps = []
        options = [
            {"label": a.get("label") or a.get("app_key"), "value": a.get("app_key")}
            for a in apps
            if a.get("app_key")
        ]
        app_keys = [o["value"] for o in options]
        selected = app_keys[0] if app_keys else None
        status = no_update
        deeplink_out = no_update
        if deeplink and not deeplink.get("applied"):
            if deeplink.get("app") in app_keys:
                selected = deeplink["app"]
            status = deeplink.get("status") or "pending"
            deeplink_out = {**deeplink, "applied": True}
        return apps, options, selected, status, deeplink_out

    @app.callback(
        Output("app-access-requests-container", "children"),
        [
            Input("app-access-app-filter", "value"),
            Input("app-access-status-filter", "value"),
            Input("app-access-refresh-store", "data"),
            Input("app-access-refresh-btn", "n_clicks"),
        ],
        [
            State("app-access-apps-store", "data"),
            State("token-store", "data"),
            State("role-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def load_access_requests(app_key, status, _refresh, _clicks, apps, token, role):
        if not token or not is_admin(role):
            return html.Small("Administrator privileges required.", className="text-danger")
        if not app_key:
            return render_requests_table([], apps or [], None)
        try:
            grants, total, err = _fetch_requests(token, app_key, status or "pending")
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Error loading access requests: %s", exc)
            return html.Small(f"Could not load access requests: {exc}", className="text-danger")
        if err:
            return html.Small(err, className="text-danger")
        return render_requests_table(grants, apps or [], app_key, total)

    @app.callback(
        [
            Output("app-access-alert", "children"),
            Output("app-access-alert", "color"),
            Output("app-access-alert", "is_open"),
            Output("app-access-refresh-store", "data", allow_duplicate=True),
        ],
        [
            Input({"type": "app-access-approve-btn", "user_id": ALL, "app_key": ALL}, "n_clicks"),
            Input({"type": "app-access-revoke-btn", "user_id": ALL, "app_key": ALL}, "n_clicks"),
        ],
        [
            State({"type": "app-access-row-role", "user_id": ALL, "app_key": ALL}, "value"),
            State({"type": "app-access-row-role", "user_id": ALL, "app_key": ALL}, "id"),
            State("app-access-action-note", "value"),
            State("app-access-refresh-store", "data"),
            State("token-store", "data"),
            State("role-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def apply_request_action(_approve, _revoke, role_values, role_ids, note, refresh, token, role):
        ctx = callback_context
        trigger = ctx.triggered_id
        # Re-rendering the table recreates buttons with n_clicks=None; ignore that.
        if not trigger or not ctx.triggered or not ctx.triggered[0].get("value"):
            return no_update, no_update, no_update, no_update
        if not token or not is_admin(role):
            return "Administrator privileges required.", "danger", True, no_update

        user_id = trigger.get("user_id")
        app_key = trigger.get("app_key")
        try:
            if trigger.get("type") == "app-access-revoke-btn":
                action = "revoked"
                resp = make_authenticated_request(
                    f"/admin/users/{user_id}/app-access/{app_key}",
                    token,
                    method="DELETE",
                    json={"note": note} if note else {},
                    timeout=10,
                )
            else:
                action = "approved"
                app_role = None
                for rid, value in zip(role_ids or [], role_values or [], strict=False):
                    if rid.get("user_id") == user_id and rid.get("app_key") == app_key:
                        app_role = value
                        break
                payload = {"app_key": app_key, "status": "active"}
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
            return f"Network error: {exc}", "danger", True, no_update

        if resp.status_code in (200, 201):
            return f"Access {action}.", "success", True, (refresh or 0) + 1
        return (
            extract_api_error(resp, "Failed to update application access."),
            "danger",
            True,
            no_update,
        )

    @app.callback(
        [
            Output("app-access-recipient-candidates-store", "data"),
            Output("app-access-recipients-candidates-status", "children"),
        ],
        [
            Input("app-access-tab-rendered", "data"),
            Input("app-access-refresh-btn", "n_clicks"),
        ],
        [State("token-store", "data"), State("role-store", "data")],
        prevent_initial_call=True,
    )
    def load_recipient_candidates(_rendered, _refresh_clicks, token, role):
        """Load eligible (ADMIN/SUPERADMIN) accounts once per tab render."""
        if not token or not is_superadmin(role):
            return [], ""
        try:
            users, err = _fetch_recipient_candidates(token)
        except Exception as exc:
            logger.exception("Error loading recipient candidates: %s", exc)
            users, err = [], f"Could not load admin accounts: {exc}"
        candidates = [
            {k: u.get(k) for k in ("id", "email", "name", "role")} for u in users if u.get("id")
        ]
        status = ""
        if err:
            status = html.Small(
                f"{err} Only currently listed recipients can be shown; use Refresh to retry.",
                className="text-warning",
            )
        return candidates, status

    @app.callback(
        [
            Output("app-access-recipients-summary", "children"),
            Output("app-access-recipients-listed-store", "data"),
        ],
        [
            Input("app-access-app-filter", "value"),
            Input("app-access-refresh-store", "data"),
            Input("app-access-refresh-btn", "n_clicks"),
        ],
        [State("token-store", "data"), State("role-store", "data")],
        prevent_initial_call=True,
    )
    def load_recipients(app_key, _refresh, _refresh_clicks, token, role):
        if not token or not is_superadmin(role) or not app_key:
            return "", []
        try:
            resp = make_authenticated_request(recipients_endpoint(app_key), token, timeout=15)
        except Exception as exc:
            logger.exception("Error loading notification recipients: %s", exc)
            return html.Small(f"Could not load recipients: {exc}", className="text-danger"), None
        if resp.status_code != 200:
            err = extract_api_error(resp, "Failed to load notification recipients.")
            return html.Small(err, className="text-danger"), None
        payload = (resp.json() or {}).get("data", {}) or {}
        return render_recipients_summary(payload), payload.get("listed_recipients") or []

    @app.callback(
        [
            Output("app-access-recipients-select", "options"),
            Output("app-access-recipients-select", "value"),
            Output("app-access-recipients-save-btn", "disabled"),
        ],
        [
            Input("app-access-recipient-candidates-store", "data"),
            Input("app-access-recipients-listed-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def update_recipient_options(candidates, listed):
        # listed is None when the current list could not be loaded; block saving
        # so an unknown list is never overwritten.
        if listed is None:
            return [], [], True
        options, value = build_recipient_options(candidates or [], listed)
        return options, value, False

    @app.callback(
        [
            Output("app-access-recipients-alert", "children"),
            Output("app-access-recipients-alert", "color"),
            Output("app-access-recipients-alert", "is_open"),
            Output("app-access-refresh-store", "data", allow_duplicate=True),
        ],
        Input("app-access-recipients-save-btn", "n_clicks"),
        [
            State("app-access-app-filter", "value"),
            State("app-access-recipients-select", "value"),
            State("app-access-refresh-store", "data"),
            State("token-store", "data"),
            State("role-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def save_recipients(n_clicks, app_key, user_ids, refresh, token, role):
        if not n_clicks or not token:
            return no_update, no_update, no_update, no_update
        if not is_superadmin(role):
            return "Only superadmins can change notification recipients.", "danger", True, no_update
        if not app_key:
            return "Select an application first.", "warning", True, no_update
        try:
            resp = make_authenticated_request(
                recipients_endpoint(app_key),
                token,
                method="PUT",
                json={"user_ids": list(user_ids or [])},
                timeout=10,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Error saving notification recipients: %s", exc)
            return f"Network error: {exc}", "danger", True, no_update

        if resp.status_code == 200:
            msg = (
                "Recipients saved."
                if user_ids
                else "Recipient list cleared; all superadmins will be notified."
            )
            return msg, "success", True, (refresh or 0) + 1

        message = extract_api_error(resp, "Failed to save notification recipients.")
        try:
            invalid = (resp.json() or {}).get("invalid_user_ids") or []
        except Exception:
            invalid = []
        if invalid:
            message = f"{message} Invalid users: {', '.join(map(str, invalid))}"
        return message, "danger", True, no_update
