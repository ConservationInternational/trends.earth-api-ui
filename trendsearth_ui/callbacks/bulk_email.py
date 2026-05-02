"""Bulk email manager callbacks.

All endpoints are SUPERADMIN-only on the backend; the UI shows the tab only
when role == "SUPERADMIN" and simply forwards the JWT for every request.
"""

import logging

from dash import Input, Output, State, html, no_update

from ..config import DEFAULT_PAGE_SIZE
from ..utils import make_authenticated_request
from ..utils.aggrid import build_aggrid_request_params

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _api(token: str, method: str, path: str, **kwargs):
    """Thin wrapper around make_authenticated_request for bulk email endpoints."""
    return make_authenticated_request(path, token, method=method, **kwargs)


_PREVIEW_ALLOWED_SORT_COLUMNS = {
    "email",
    "name",
    "role",
    "email_verified",
    "created_at",
    "last_activity_at",
}


def _ok_rows(resp):
    """Return list of dicts from a paginated or list API response, or []."""
    try:
        body = resp.json()
        if isinstance(body, list):
            return body
        return body.get("data", []) or []
    except Exception:
        return []


def _fetch_preview_page(token, filter_criteria, params):
    """Fetch one page of preview recipients.  ``params`` must contain at least
    ``page`` and ``per_page``; ``sort`` is optional.
    Follows the same pattern as ``_fetch_users_page`` in users.py.
    """
    try:
        resp = _api(
            token,
            "POST",
            "/bulk-email/recipient-list/preview",
            json={"filter_criteria": filter_criteria, **params},
        )
        if resp.status_code == 200:
            data = resp.json().get("data", {}) or {}
            return data.get("sample", []) or [], data.get("total", 0)
    except Exception:
        logger.exception("Failed to fetch preview page")
    return [], 0


def register_callbacks(app):
    """Register all bulk email callbacks."""

    # -----------------------------------------------------------------------
    # Load bulk email config (threshold info) when the tab becomes active
    # -----------------------------------------------------------------------
    @app.callback(
        Output("bulk-email-threshold-info", "children"),
        Input("active-tab-store", "data"),
        State("token-store", "data"),
        prevent_initial_call=True,
    )
    def load_bulk_email_config(active_tab, token):
        if active_tab != "bulk-email" or not token:
            return no_update
        try:
            resp = _api(token, "GET", "/bulk-email/config")
            if resp.status_code == 200:
                cfg = resp.json()
                max_r = cfg.get("max_recipients", "?")
                from_email = cfg.get("from_email", "")
                return (
                    f"Bulk emails with more than {max_r} recipients require a verification code. "
                    f"Emails sent from: {from_email}"
                )
        except Exception:
            logger.exception("Failed to load bulk email config")
        return ""

    # -----------------------------------------------------------------------
    # Preview button — store filter criteria and load first page
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-preview-grid", "getRowsResponse"),
            Output("bulk-email-preview-count", "children"),
            Output("bulk-email-preview-filter-store", "data"),
        ],
        Input("bulk-email-preview-btn", "n_clicks"),
        [
            State("token-store", "data"),
            State("bulk-email-rlist-roles", "value"),
            State("bulk-email-rlist-verified", "value"),
            State("bulk-email-rlist-min-created", "value"),
            State("bulk-email-rlist-max-created", "value"),
            State("bulk-email-rlist-min-activity", "value"),
            State("bulk-email-rlist-max-activity", "value"),
        ],
        prevent_initial_call=True,
    )
    def preview_recipient_group(
        _n, token, roles, verified, min_created, max_created, min_activity, max_activity
    ):
        if not token:
            return {"rowData": [], "rowCount": 0}, "", {}
        filter_criteria = _build_filter_criteria(
            roles, verified, min_created, max_created, min_activity, max_activity
        )
        rows, total = _fetch_preview_page(
            token, filter_criteria, {"page": 1, "per_page": DEFAULT_PAGE_SIZE}
        )
        return {"rowData": rows, "rowCount": total}, f"{total} recipients", filter_criteria

    # -----------------------------------------------------------------------
    # Infinite scroll — subsequent pages requested by AG Grid
    # Uses build_aggrid_request_params to handle pagination and column sorting.
    # -----------------------------------------------------------------------
    @app.callback(
        Output("bulk-email-preview-grid", "getRowsResponse", allow_duplicate=True),
        Input("bulk-email-preview-grid", "getRowsRequest"),
        [
            State("token-store", "data"),
            State("bulk-email-preview-filter-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def get_preview_rows(request, token, filter_criteria):
        if not request or filter_criteria is None or not token:
            return no_update
        params, _ = build_aggrid_request_params(
            request,
            allow_filters=False,
            allowed_sort_columns=_PREVIEW_ALLOWED_SORT_COLUMNS,
        )
        rows, total = _fetch_preview_page(token, filter_criteria, params)
        return {"rowData": rows, "rowCount": total}

    # -----------------------------------------------------------------------
    # Save recipient group
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-rlist-alert", "children"),
            Output("bulk-email-rlist-alert", "is_open"),
            Output("bulk-email-rlist-alert", "color"),
            Output("bulk-email-rlist-grid", "rowData"),
        ],
        Input("bulk-email-save-rlist-btn", "n_clicks"),
        [
            State("token-store", "data"),
            State("bulk-email-rlist-name", "value"),
            State("bulk-email-rlist-desc", "value"),
            State("bulk-email-rlist-roles", "value"),
            State("bulk-email-rlist-verified", "value"),
            State("bulk-email-rlist-min-created", "value"),
            State("bulk-email-rlist-max-created", "value"),
            State("bulk-email-rlist-min-activity", "value"),
            State("bulk-email-rlist-max-activity", "value"),
        ],
        prevent_initial_call=True,
    )
    def save_recipient_list(
        _n,
        token,
        name,
        desc,
        roles,
        verified,
        min_created,
        max_created,
        min_activity,
        max_activity,
    ):
        if not token or not name:
            return "Please enter a group name.", True, "warning", no_update
        filter_criteria = _build_filter_criteria(
            roles, verified, min_created, max_created, min_activity, max_activity
        )
        try:
            resp = _api(
                token,
                "POST",
                "/bulk-email/recipient-list",
                json={"name": name, "description": desc or "", "filter_criteria": filter_criteria},
            )
            if resp.status_code in (200, 201):
                rows = _load_recipient_lists(token)
                return f"Group '{name}' saved.", True, "success", rows
            msg = _extract_error(resp)
            return f"Error: {msg}", True, "danger", no_update
        except Exception:
            logger.exception("Failed to save recipient list")
            return "An unexpected error occurred.", True, "danger", no_update

    # -----------------------------------------------------------------------
    # Load recipient lists on tab open
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-rlist-grid", "rowData", allow_duplicate=True),
            Output("bulk-email-send-rlist-select", "options"),
        ],
        Input("active-tab-store", "data"),
        State("token-store", "data"),
        prevent_initial_call=True,
    )
    def load_recipient_lists(active_tab, token):
        if active_tab != "bulk-email" or not token:
            return no_update, no_update
        rows = _load_recipient_lists(token)
        options = [{"label": r["name"], "value": r["id"]} for r in rows if "id" in r]
        return rows, options

    # -----------------------------------------------------------------------
    # Delete selected recipient list
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-rlist-alert", "children", allow_duplicate=True),
            Output("bulk-email-rlist-alert", "is_open", allow_duplicate=True),
            Output("bulk-email-rlist-alert", "color", allow_duplicate=True),
            Output("bulk-email-rlist-grid", "rowData", allow_duplicate=True),
        ],
        Input("bulk-email-delete-rlist-btn", "n_clicks"),
        [
            State("token-store", "data"),
            State("bulk-email-rlist-grid", "selectedRows"),
        ],
        prevent_initial_call=True,
    )
    def delete_recipient_list(_n, token, selected_rows):
        if not token or not selected_rows:
            return "Select a group to delete.", True, "warning", no_update
        row = selected_rows[0]
        list_id = row.get("id")
        if not list_id:
            return "Invalid selection.", True, "warning", no_update
        try:
            resp = _api(token, "DELETE", f"/bulk-email/recipient-list/{list_id}")
            if resp.status_code in (200, 204):
                rows = _load_recipient_lists(token)
                return f"Group '{row.get('name', list_id)}' deleted.", True, "success", rows
            msg = _extract_error(resp)
            return f"Error: {msg}", True, "danger", no_update
        except Exception:
            logger.exception("Failed to delete recipient list")
            return "An unexpected error occurred.", True, "danger", no_update

    # -----------------------------------------------------------------------
    # Live HTML preview (sample substitutions)
    # -----------------------------------------------------------------------
    @app.callback(
        Output("bulk-email-preview-html", "children"),
        Input("bulk-email-html-source", "html"),
        prevent_initial_call=True,
    )
    def render_email_preview(html_content):
        if not html_content:
            return html.Em("No content to preview.")
        preview = (
            (html_content or "")
            .replace("{{name}}", "Jane Smith")
            .replace("{{email}}", "jane@example.com")
        )
        return html.Iframe(
            srcDoc=preview,
            style={"width": "100%", "minHeight": "200px", "border": "none"},
        )

    # -----------------------------------------------------------------------
    # Save draft bulk email
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-composer-alert", "children"),
            Output("bulk-email-composer-alert", "is_open"),
            Output("bulk-email-composer-alert", "color"),
            Output("bulk-email-send-select", "options", allow_duplicate=True),
            Output("bulk-email-load-draft-select", "options", allow_duplicate=True),
            Output("bulk-email-loaded-draft-id", "data", allow_duplicate=True),
            Output("bulk-email-draft-mode-label", "children", allow_duplicate=True),
        ],
        Input("bulk-email-save-draft-btn", "n_clicks"),
        [
            State("token-store", "data"),
            State("bulk-email-name", "value"),
            State("bulk-email-subject", "value"),
            State("bulk-email-html-source", "html"),
            State("bulk-email-loaded-draft-id", "data"),
        ],
        prevent_initial_call=True,
    )
    def save_draft_bulk_email(_n, token, name, subject, html_content, loaded_draft_id):
        if not token or not name or not subject:
            return (
                "Name and subject are required.",
                True,
                "warning",
                no_update,
                no_update,
                no_update,
                no_update,
            )
        payload = {"name": name, "subject": subject, "html_content": html_content or ""}
        try:
            if loaded_draft_id:
                resp = _api(token, "PATCH", f"/bulk-email/{loaded_draft_id}", json=payload)
                action = "updated"
            else:
                resp = _api(token, "POST", "/bulk-email", json=payload)
                action = "saved"
            if resp.status_code in (200, 201):
                saved_id = resp.json().get("data", {}).get("id") or loaded_draft_id
                options = _load_draft_options(token)
                label = f"Editing: {name}"
                return (
                    f"Draft '{name}' {action}.",
                    True,
                    "success",
                    options,
                    options,
                    saved_id,
                    label,
                )
            msg = _extract_error(resp)
            return f"Error: {msg}", True, "danger", no_update, no_update, no_update, no_update
        except Exception:
            logger.exception("Failed to save draft bulk email")
            return (
                "An unexpected error occurred.",
                True,
                "danger",
                no_update,
                no_update,
                no_update,
                no_update,
            )

    # -----------------------------------------------------------------------
    # Load draft bulk emails on tab open
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-send-select", "options", allow_duplicate=True),
            Output("bulk-email-load-draft-select", "options", allow_duplicate=True),
            Output("bulk-email-history-grid", "rowData"),
        ],
        [
            Input("active-tab-store", "data"),
            Input("bulk-email-history-refresh-btn", "n_clicks"),
        ],
        State("token-store", "data"),
        prevent_initial_call=True,
    )
    def load_bulk_emails(active_tab, _refresh, token):
        if active_tab != "bulk-email" or not token:
            return no_update, no_update
        try:
            resp = _api(token, "GET", "/bulk-email")
            bulk_emails = _ok_rows(resp)
        except Exception:
            logger.exception("Failed to load bulk emails")
            bulk_emails = []
        draft_options = [
            {"label": c["name"], "value": c["id"]}
            for c in bulk_emails
            if c.get("status") == "DRAFT"
        ]
        return draft_options, draft_options, bulk_emails

    # -----------------------------------------------------------------------
    # Load a draft into the composer
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-name", "value"),
            Output("bulk-email-subject", "value"),
            Output("bulk-email-html-source", "html"),
            Output("bulk-email-loaded-draft-id", "data"),
            Output("bulk-email-draft-mode-label", "children"),
            Output("bulk-email-composer-alert", "children", allow_duplicate=True),
            Output("bulk-email-composer-alert", "is_open", allow_duplicate=True),
            Output("bulk-email-composer-alert", "color", allow_duplicate=True),
        ],
        Input("bulk-email-load-draft-btn", "n_clicks"),
        [
            State("token-store", "data"),
            State("bulk-email-load-draft-select", "value"),
        ],
        prevent_initial_call=True,
    )
    def load_draft_into_composer(_n, token, draft_id):
        if not token or not draft_id:
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                "Select a draft to load.",
                True,
                "warning",
            )
        try:
            resp = _api(token, "GET", f"/bulk-email/{draft_id}")
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                name = data.get("name", "")
                subject = data.get("subject", "")
                html_content = data.get("html_content", "")
                label = f"Editing: {name}"
                return name, subject, html_content, draft_id, label, "", False, "success"
            msg = _extract_error(resp)
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                f"Error loading draft: {msg}",
                True,
                "danger",
            )
        except Exception:
            logger.exception("Failed to load draft")
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                "An unexpected error occurred.",
                True,
                "danger",
            )

    # -----------------------------------------------------------------------
    # Clear the composer (new draft)
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-name", "value", allow_duplicate=True),
            Output("bulk-email-subject", "value", allow_duplicate=True),
            Output("bulk-email-html-source", "html", allow_duplicate=True),
            Output("bulk-email-loaded-draft-id", "data", allow_duplicate=True),
            Output("bulk-email-draft-mode-label", "children", allow_duplicate=True),
        ],
        Input("bulk-email-clear-draft-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def clear_composer(_n):
        return "", "", "", None, ""

    # -----------------------------------------------------------------------
    # Initiate send — opens verify modal on 428, shows success/error otherwise
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-send-alert", "children"),
            Output("bulk-email-send-alert", "is_open"),
            Output("bulk-email-send-alert", "color"),
            Output("bulk-email-verify-modal", "is_open"),
            Output("bulk-email-verify-modal-title", "children"),
            Output("bulk-email-verify-modal-body", "children"),
            Output("bulk-email-pending-id", "data"),
        ],
        Input("bulk-email-send-btn", "n_clicks"),
        [
            State("token-store", "data"),
            State("bulk-email-send-select", "value"),
            State("bulk-email-send-rlist-select", "value"),
        ],
        prevent_initial_call=True,
    )
    def initiate_send(_n, token, bulk_email_id, recipient_list_id):
        if not token:
            return "Not authenticated.", True, "danger", False, "", "", None
        if not bulk_email_id:
            return "Select a bulk email.", True, "warning", False, "", "", None
        payload = {}
        if recipient_list_id:
            payload["recipient_list_id"] = recipient_list_id
        try:
            resp = _api(token, "POST", f"/bulk-email/{bulk_email_id}/send", json=payload)
            if resp.status_code == 200:
                return "Bulk email sent successfully!", True, "success", False, "", "", None
            if resp.status_code == 428:
                body = resp.json()
                count = body.get("recipient_count", "?")
                title = "Verification Required"
                msg = (
                    f"This bulk email targets {count} recipients, which exceeds the threshold. "
                    "A verification code will be sent to your email. "
                    "Click 'Request Code' to receive it, then enter it below and click 'Confirm Send'."
                )
                return no_update, False, no_update, True, title, msg, bulk_email_id
            msg = _extract_error(resp)
            return f"Error: {msg}", True, "danger", False, "", "", None
        except Exception:
            logger.exception("Failed to initiate bulk email send")
            return "An unexpected error occurred.", True, "danger", False, "", "", None

    # -----------------------------------------------------------------------
    # Request verification code
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-verify-modal-alert", "children"),
            Output("bulk-email-verify-modal-alert", "is_open"),
            Output("bulk-email-verify-modal-alert", "color"),
        ],
        Input("bulk-email-request-code-btn", "n_clicks"),
        [
            State("token-store", "data"),
            State("bulk-email-pending-id", "data"),
        ],
        prevent_initial_call=True,
    )
    def request_verification_code(_n, token, bulk_email_id):
        if not token or not bulk_email_id:
            return "No bulk email selected.", True, "warning"
        try:
            resp = _api(token, "POST", f"/bulk-email/{bulk_email_id}/send-verification")
            if resp.status_code == 200:
                return "Verification code sent to your email address.", True, "success"
            msg = _extract_error(resp)
            return f"Error: {msg}", True, "danger"
        except Exception:
            logger.exception("Failed to request verification code")
            return "An unexpected error occurred.", True, "danger"

    # -----------------------------------------------------------------------
    # Confirm send with OTP
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-verify-modal", "is_open", allow_duplicate=True),
            Output("bulk-email-send-alert", "children", allow_duplicate=True),
            Output("bulk-email-send-alert", "is_open", allow_duplicate=True),
            Output("bulk-email-send-alert", "color", allow_duplicate=True),
            Output("bulk-email-verify-modal-alert", "children", allow_duplicate=True),
            Output("bulk-email-verify-modal-alert", "is_open", allow_duplicate=True),
            Output("bulk-email-verify-modal-alert", "color", allow_duplicate=True),
        ],
        Input("bulk-email-verify-submit", "n_clicks"),
        [
            State("token-store", "data"),
            State("bulk-email-pending-id", "data"),
            State("bulk-email-verify-code", "value"),
            State("bulk-email-send-rlist-select", "value"),
        ],
        prevent_initial_call=True,
    )
    def confirm_send(_n, token, bulk_email_id, code, recipient_list_id):
        if not token or not bulk_email_id:
            return True, no_update, False, no_update, "No bulk email selected.", True, "warning"
        if not code or len(code.strip()) != 6:
            return True, no_update, False, no_update, "Enter a valid 6-digit code.", True, "warning"
        payload = {"code": code.strip()}
        if recipient_list_id:
            payload["recipient_list_id"] = recipient_list_id
        try:
            resp = _api(token, "POST", f"/bulk-email/{bulk_email_id}/send", json=payload)
            if resp.status_code == 200:
                return False, "Bulk email sent successfully!", True, "success", "", False, "success"
            msg = _extract_error(resp)
            return True, no_update, False, no_update, f"Error: {msg}", True, "danger"
        except Exception:
            logger.exception("Failed to confirm bulk email send")
            return (
                True,
                no_update,
                False,
                no_update,
                "An unexpected error occurred.",
                True,
                "danger",
            )

    # -----------------------------------------------------------------------
    # Cancel verify modal
    # -----------------------------------------------------------------------
    @app.callback(
        Output("bulk-email-verify-modal", "is_open", allow_duplicate=True),
        Input("bulk-email-verify-cancel", "n_clicks"),
        prevent_initial_call=True,
    )
    def cancel_verify_modal(_n):
        return False

    # -----------------------------------------------------------------------
    # Send test to superadmins
    # -----------------------------------------------------------------------
    @app.callback(
        [
            Output("bulk-email-send-alert", "children", allow_duplicate=True),
            Output("bulk-email-send-alert", "is_open", allow_duplicate=True),
            Output("bulk-email-send-alert", "color", allow_duplicate=True),
        ],
        Input("bulk-email-send-test-btn", "n_clicks"),
        [
            State("token-store", "data"),
            State("bulk-email-send-select", "value"),
        ],
        prevent_initial_call=True,
    )
    def send_test_bulk_email(_n, token, bulk_email_id):
        if not token:
            return "Not authenticated.", True, "danger"
        if not bulk_email_id:
            return "Select a bulk email first.", True, "warning"
        try:
            resp = _api(token, "POST", f"/bulk-email/{bulk_email_id}/send-test")
            if resp.status_code == 200:
                return "Test email sent to all superadmins.", True, "success"
            msg = _extract_error(resp)
            return f"Error: {msg}", True, "danger"
        except Exception:
            logger.exception("Failed to send test bulk email")
            return "An unexpected error occurred.", True, "danger"


# ---------------------------------------------------------------------------
# Private helpers (module-level to keep callbacks concise)
# ---------------------------------------------------------------------------


def _build_filter_criteria(roles, verified, min_created, max_created, min_activity, max_activity):
    criteria = {}
    if roles:
        criteria["roles"] = roles
    if verified and verified not in ("", "any"):
        criteria["email_verified"] = verified == "true"
    if min_created:
        criteria["min_created_at"] = min_created
    if max_created:
        criteria["max_created_at"] = max_created
    if min_activity:
        criteria["min_last_activity_at"] = min_activity
    if max_activity:
        criteria["max_last_activity_at"] = max_activity
    return criteria


def _load_recipient_lists(token):
    try:
        resp = make_authenticated_request("/bulk-email/recipient-list", token)
        return _ok_rows(resp)
    except Exception:
        logger.exception("Failed to load recipient lists")
        return []


def _load_draft_options(token):
    try:
        resp = make_authenticated_request("/bulk-email", token)
        bulk_emails = _ok_rows(resp)
        return [
            {"label": c["name"], "value": c["id"]}
            for c in bulk_emails
            if c.get("status") == "DRAFT"
        ]
    except Exception:
        logger.exception("Failed to load draft options")
        return []


def _extract_error(resp):
    try:
        body = resp.json()
        return body.get("message") or body.get("error") or resp.text
    except Exception:
        return resp.text or "Unknown error"
