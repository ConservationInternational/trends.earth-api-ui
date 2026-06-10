"""CSV export callbacks for admin tables (users, executions, scripts)."""

from datetime import datetime
import logging
from urllib.parse import urlencode

from dash import Input, Output, State, dcc, no_update

from ..utils.helpers import is_admin, make_authenticated_request

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Per-table configuration
# ---------------------------------------------------------------------------

_TABLE_CONFIG = {
    "users": {
        "endpoint": "/user/export",
        "filename_prefix": "users_export",
        "date_field_options": [
            {"label": "Created At", "value": "created_at"},
            {"label": "Updated At", "value": "updated_at"},
            {"label": "Email Verified At", "value": "email_verified_at"},
            {"label": "Last Login At", "value": "last_login_at"},
            {"label": "Last Activity At", "value": "last_activity_at"},
        ],
        "default_date_field": "created_at",
    },
    "executions": {
        "endpoint": "/execution/export",
        "filename_prefix": "executions_export",
        "date_field_options": [
            {"label": "Start Date", "value": "start_date"},
            {"label": "End Date", "value": "end_date"},
        ],
        "default_date_field": "start_date",
    },
    "scripts": {
        "endpoint": "/script/export",
        "filename_prefix": "scripts_export",
        "date_field_options": [
            {"label": "Created At", "value": "created_at"},
            {"label": "Updated At", "value": "updated_at"},
        ],
        "default_date_field": "created_at",
    },
}


def _build_export_params(date_field, date_from, date_to):
    """Build query parameter dict from date filter values."""
    params = {}
    if date_field:
        params["date_field"] = date_field
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to
    return params


def register_callbacks(app):
    """Register CSV export callbacks."""

    # ------------------------------------------------------------------
    # 1a-c. Each tab's export button writes the table type to a shared
    #       always-present store.  Using separate per-tab callbacks means
    #       no callback ever references a component from a different tab
    #       as an Input, which avoids the Dash client-side ReferenceError
    #       that fires when a tab's content is not yet in the DOM.
    # ------------------------------------------------------------------
    @app.callback(
        Output("csv-export-trigger", "data", allow_duplicate=True),
        Input("export-users-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def _trigger_users_export(_n):
        return "users"

    @app.callback(
        Output("csv-export-trigger", "data", allow_duplicate=True),
        Input("export-executions-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def _trigger_executions_export(_n):
        return "executions"

    @app.callback(
        Output("csv-export-trigger", "data", allow_duplicate=True),
        Input("export-scripts-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def _trigger_scripts_export(_n):
        return "scripts"

    # ------------------------------------------------------------------
    # 2. Open the modal when the trigger store is updated.
    # ------------------------------------------------------------------
    @app.callback(
        [
            Output("csv-export-modal", "is_open"),
            Output("csv-export-table-type-store", "data"),
            Output("csv-export-date-field", "options"),
            Output("csv-export-date-field", "value"),
            Output("csv-export-date-from", "value"),
            Output("csv-export-date-to", "value"),
        ],
        Input("csv-export-trigger", "data"),
        prevent_initial_call=True,
    )
    def open_export_modal(table_type):
        if not table_type:
            return no_update, no_update, no_update, no_update, no_update, no_update

        cfg = _TABLE_CONFIG.get(table_type)
        if not cfg:
            return no_update, no_update, no_update, no_update, no_update, no_update

        return (
            True,
            table_type,
            cfg["date_field_options"],
            cfg["default_date_field"],
            None,
            None,
        )

    # ------------------------------------------------------------------
    # 3. Close the modal when Cancel is clicked.
    # ------------------------------------------------------------------
    @app.callback(
        Output("csv-export-modal", "is_open", allow_duplicate=True),
        Input("csv-export-cancel-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def close_export_modal(_n_clicks):
        return False

    # ------------------------------------------------------------------
    # 4. Perform the export when the user confirms.
    # ------------------------------------------------------------------
    @app.callback(
        [
            Output("csv-export-download", "data"),
            Output("csv-export-modal", "is_open", allow_duplicate=True),
            Output("csv-export-error-alert", "children"),
            Output("csv-export-error-alert", "is_open"),
        ],
        Input("csv-export-confirm-btn", "n_clicks"),
        [
            State("csv-export-table-type-store", "data"),
            State("csv-export-date-field", "value"),
            State("csv-export-date-from", "value"),
            State("csv-export-date-to", "value"),
            State("token-store", "data"),
            State("role-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def perform_export(n_clicks, table_type, date_field, date_from, date_to, token, role):
        if not n_clicks or not token or not table_type:
            return no_update, no_update, no_update, no_update

        if not is_admin(role):
            return (
                no_update,
                no_update,
                "Admin privileges required to export data.",
                True,
            )

        cfg = _TABLE_CONFIG.get(table_type)
        if not cfg:
            return (
                no_update,
                no_update,
                f"Unknown table type: {table_type}",
                True,
            )

        params = _build_export_params(date_field, date_from, date_to)
        endpoint = cfg["endpoint"]
        if params:
            endpoint = f"{endpoint}?{urlencode(params)}"

        try:
            resp = make_authenticated_request(
                endpoint,
                token,
                method="GET",
                timeout=(5, 120),
            )
        except Exception as exc:
            logger.exception("CSV export request failed: %s", exc)
            return (
                no_update,
                no_update,
                "Export request failed. Please try again.",
                True,
            )

        if resp.status_code != 200:
            logger.warning("CSV export returned %s: %s", resp.status_code, resp.text[:200])
            return (
                no_update,
                no_update,
                f"Export failed (HTTP {resp.status_code}). Please try again.",
                True,
            )

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{cfg['filename_prefix']}_{timestamp}.csv"

        return (
            dcc.send_bytes(resp.content, filename),
            False,
            "",
            False,
        )
