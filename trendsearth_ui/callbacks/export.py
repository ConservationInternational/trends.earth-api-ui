"""CSV export callbacks for admin tables (users, executions, scripts)."""

from datetime import datetime
import logging

from dash import Input, Output, State, callback_context, dcc, no_update

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
    # 1. Open modal when any export button is clicked
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
        [
            Input("export-users-btn", "n_clicks"),
            Input("export-executions-btn", "n_clicks"),
            Input("export-scripts-btn", "n_clicks"),
            Input("csv-export-cancel-btn", "n_clicks"),
        ],
        prevent_initial_call=True,
    )
    def toggle_export_modal(_users_clicks, _executions_clicks, _scripts_clicks, _cancel_clicks):
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update, no_update, no_update, no_update

        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

        if trigger_id == "csv-export-cancel-btn":
            return False, no_update, no_update, no_update, no_update, no_update

        table_map = {
            "export-users-btn": "users",
            "export-executions-btn": "executions",
            "export-scripts-btn": "scripts",
        }
        table_type = table_map.get(trigger_id)
        if not table_type:
            return no_update, no_update, no_update, no_update, no_update, no_update

        cfg = _TABLE_CONFIG[table_type]
        return (
            True,
            table_type,
            cfg["date_field_options"],
            cfg["default_date_field"],
            None,
            None,
        )

    # ------------------------------------------------------------------
    # 2. Perform the export when the user confirms
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
            query_string = "&".join(f"{k}={v}" for k, v in params.items())
            endpoint = f"{endpoint}?{query_string}"

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
