"""Scripts table callbacks."""

import logging
from typing import Any

from dash import Input, Output, State

from ..config import DEFAULT_PAGE_SIZE
from ..utils import parse_date
from ..utils.aggrid import build_aggrid_request_params, build_refresh_request_params
from ..utils.helpers import make_authenticated_request

logger = logging.getLogger(__name__)

SCRIPT_ENDPOINT = "/script"
SCRIPT_INCLUDE_FIELDS = "user_name,access_control"
DATE_COLUMNS = ("start_date", "end_date", "created_at", "updated_at")

# Must match the API's SCRIPT_ALLOWED_FILTER_FIELDS / SORT_FIELDS
SCRIPT_ALLOWED_SORT_COLUMNS = {
    "id",
    "name",
    "slug",
    "status",
    "public",
    "restricted",
    "created_at",
    "updated_at",
    "environment",
    "environment_version",
    "user_name",
    "user_email",
}
SCRIPT_ALLOWED_FILTER_COLUMNS = {
    "id",
    "name",
    "slug",
    "status",
    "public",
    "restricted",
    "created_at",
    "updated_at",
    "environment",
    "environment_version",
    "user_name",
    "user_email",
}


def _access_control_label(script_row: dict[str, Any]) -> str:
    """Return a compact label describing script access restrictions."""
    if not script_row.get("restricted", False):
        return "🔓 Open"

    allowed_roles = script_row.get("allowed_roles") or []
    allowed_users = script_row.get("allowed_users") or []
    if allowed_roles and allowed_users:
        return "🔒 Role, User"
    if allowed_roles:
        return "🔒 Role"
    if allowed_users:
        return "🔒 User"
    return "🔒 Restricted"


def _format_scripts_rows(
    scripts: list[dict[str, Any]], is_admin: bool, user_timezone: str | None
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    timezone = user_timezone or "UTC"
    for script_row in scripts:
        row = script_row.copy()
        row["logs"] = "Show Logs"
        row["access_control"] = _access_control_label(script_row)
        if is_admin:
            row["edit"] = "Edit"
        for date_col in DATE_COLUMNS:
            if date_col in row:
                row[date_col] = parse_date(row.get(date_col), timezone)
        rows.append(row)
    return rows


def _fetch_scripts_page(
    token: str,
    params: dict[str, Any],
    *,
    is_admin: bool,
    user_timezone: str | None,
):
    response = make_authenticated_request(SCRIPT_ENDPOINT, token, params=params)
    if response.status_code != 200:
        logger.error("Scripts API error: %s - %s", response.status_code, response.text)
        return [], 0

    payload = response.json()
    scripts = payload.get("data", [])
    total_rows = payload.get("total", 0)
    tabledata = _format_scripts_rows(scripts, is_admin, user_timezone)
    return tabledata, total_rows


def register_callbacks(app):
    """Register scripts table callbacks."""

    @app.callback(
        [
            Output("scripts-table", "getRowsResponse"),
            Output("scripts-table-state", "data"),
            Output("scripts-total-count-store", "data"),
        ],
        Input("scripts-table", "getRowsRequest"),
        [
            State("token-store", "data"),
            State("role-store", "data"),
            State("user-timezone-store", "data"),
            State("api-environment-store", "data"),
        ],
        prevent_initial_call=False,
    )
    def get_scripts_rows(request, token, role, user_timezone, _api_environment):
        """Get scripts data for ag-grid with infinite row model."""
        try:
            if not token:
                return {"rowData": [], "rowCount": 0}, {}, 0
            if not request:
                return {"rowData": [], "rowCount": None}, {}, 0

            params, table_state = build_aggrid_request_params(
                request,
                base_params={"include": SCRIPT_INCLUDE_FIELDS},
                allowed_sort_columns=SCRIPT_ALLOWED_SORT_COLUMNS,
                allowed_filter_columns=SCRIPT_ALLOWED_FILTER_COLUMNS,
            )

            is_admin = role in ["ADMIN", "SUPERADMIN"]
            tabledata, total_rows = _fetch_scripts_page(
                token,
                params,
                is_admin=is_admin,
                user_timezone=user_timezone,
            )

            return {"rowData": tabledata, "rowCount": total_rows}, table_state, total_rows

        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Error in get_scripts_rows: %s", exc)
            return {"rowData": [], "rowCount": 0}, {}, 0

    @app.callback(
        [
            Output("scripts-table", "getRowsResponse", allow_duplicate=True),
            Output("scripts-table-state", "data", allow_duplicate=True),
            Output("scripts-total-count-store", "data", allow_duplicate=True),
        ],
        Input("refresh-scripts-btn", "n_clicks"),
        [
            State("token-store", "data"),
            State("role-store", "data"),
            State("scripts-table-state", "data"),
            State("user-timezone-store", "data"),
            State("api-environment-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def refresh_scripts_table(n_clicks, token, role, table_state, user_timezone, _api_environment):
        """Manually refresh the scripts table."""
        if not n_clicks or not token:
            return {"rowData": [], "rowCount": 0}, {}, 0

        try:
            base_params = {
                "page": 1,
                "per_page": DEFAULT_PAGE_SIZE,
                "include": SCRIPT_INCLUDE_FIELDS,
            }
            params = build_refresh_request_params(
                base_params=base_params,
                table_state=table_state,
                allowed_filter_columns=SCRIPT_ALLOWED_FILTER_COLUMNS,
            )

            is_admin = role in ["ADMIN", "SUPERADMIN"]
            tabledata, total_rows = _fetch_scripts_page(
                token,
                params,
                is_admin=is_admin,
                user_timezone=user_timezone,
            )

            return {"rowData": tabledata, "rowCount": total_rows}, table_state or {}, total_rows

        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Error in refresh_scripts_table: %s", exc)
            return {"rowData": [], "rowCount": 0}, {}, 0

    @app.callback(
        Output("scripts-total-count", "children"),
        Input("scripts-total-count-store", "data"),
        prevent_initial_call=True,
    )
    def update_scripts_total_display(total_count):
        """Update the scripts total count display."""
        return f"Total: {total_count:,}"
