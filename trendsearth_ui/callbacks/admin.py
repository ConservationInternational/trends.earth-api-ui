"""Admin functionality callbacks."""

import base64
from typing import Any

from dash import Input, Output, State, callback_context, html, no_update
import dash_bootstrap_components as dbc
import requests

from ..config import DEFAULT_PAGE_SIZE
from ..utils.aggrid import build_sort_clause, build_table_state
from ..utils.helpers import make_authenticated_request, parse_date

RATE_LIMIT_EVENTS_ENDPOINT = "/rate-limit/events"


def _format_duration_label(value: Any) -> str:
    """Convert a numeric duration in seconds to a human readable label."""

    try:
        seconds = int(float(value))
    except (TypeError, ValueError):
        return "-"

    if seconds <= 0:
        return "-"

    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    parts: list[str] = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs and not hours:
        parts.append(f"{secs}s")
    if not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


def _format_limit_count(value: Any) -> str:
    """Format limit counts for display."""

    if value in (None, ""):
        return "-"
    try:
        numeric = int(float(value))
    except (TypeError, ValueError):
        return str(value)
    return f"{numeric:,}"


def _format_rate_limit_events(
    events: list[dict[str, Any]] | None,
    user_timezone: str | None,
) -> list[dict[str, Any]]:
    """Prepare rate limit event rows for the data grid."""

    if not events:
        return []

    timezone = user_timezone or "UTC"
    rows: list[dict[str, Any]] = []

    for event in events:
        event = dict(event)
        event["occurred_at"] = parse_date(event.get("occurred_at"), timezone)
        event["time_window_display"] = _format_duration_label(event.get("time_window_seconds"))
        event["retry_after_display"] = _format_duration_label(event.get("retry_after_seconds"))
        event["limit_count_display"] = _format_limit_count(event.get("limit_count"))
        rows.append(event)

    return rows


def _normalise_rate_limit_type(value: Any) -> str:
    """Convert a raw rate limit type into a readable label."""

    if not value:
        return "-"
    text = str(value).strip()
    if not text:
        return "-"
    return text.replace("_", " ").title()


def _fetch_rate_limit_status_data(token: str | None) -> dict[str, Any] | None:
    """Safely fetch rate limit status information from the API."""

    if not token:
        return None

    try:
        response = make_authenticated_request("/rate-limit/status", token, method="GET")
    except Exception as exc:  # pragma: no cover - defensive guard
        print(f"Error fetching rate limit status data: {exc}")
        return None

    if response.status_code != 200:
        return None

    try:
        payload = response.json()
    except ValueError:
        return None

    data = payload.get("data") if isinstance(payload, dict) else None
    return data if isinstance(data, dict) else None


def _format_active_limits_for_table(
    active_limits: list[dict[str, Any]] | None,
    user_timezone: str | None,
) -> list[dict[str, Any]]:
    """Transform active rate limits into rows compatible with the unified table."""

    if not active_limits:
        return []

    timezone = user_timezone or "UTC"
    rows: list[dict[str, Any]] = []

    for idx, raw_limit in enumerate(active_limits):
        limit = dict(raw_limit or {})

        key = limit.get("key") or limit.get("identifier") or f"active-{idx}"
        user_info = limit.get("user_info") or {}
        user_name = (user_info.get("name") or "").strip()
        user_email = (user_info.get("email") or "").strip()
        identifier = (limit.get("identifier") or "").strip()

        identifier_candidates = [
            f"{user_name} ({user_email})" if user_name and user_email else None,
            user_email or None,
            user_name or None,
            identifier or None,
            key,
        ]
        identifier_display = next((value for value in identifier_candidates if value), "Unknown")

        ip_address = limit.get("ip_address") or (
            identifier if identifier and "@" not in identifier else "-"
        )

        occurred_at = parse_date(limit.get("occurred_at"), timezone) or "-"
        expires_at = parse_date(limit.get("expires_at"), timezone) or "-"

        current_display = _format_limit_count(limit.get("current_count"))
        limit_cap_value = limit.get("limit") or limit.get("limit_count")
        limit_cap_display = _format_limit_count(limit_cap_value)

        if limit_cap_display not in ("-", "0") and current_display not in ("-", "0"):
            usage_display = f"{current_display} / {limit_cap_display}"
        elif limit_cap_display not in ("-", "0"):
            usage_display = (
                f"{current_display} / {limit_cap_display}"
                if current_display != "-"
                else limit_cap_display
            )
        else:
            usage_display = current_display

        time_window_display = _format_duration_label(limit.get("time_window_seconds"))
        retry_after_display = _format_duration_label(limit.get("retry_after_seconds"))

        limit_definition = limit.get("limit_definition")
        if not limit_definition:
            if limit_cap_display != "-" and time_window_display != "-":
                limit_definition = f"{limit_cap_display} per {time_window_display}"
            elif limit_cap_display != "-":
                limit_definition = limit_cap_display
            else:
                limit_definition = "-"

        rows.append(
            {
                "id": f"active:{key}",
                "is_active": True,
                "status_display": "Active",
                "occurred_at": occurred_at,
                "expires_at_display": expires_at,
                "identifier_display": identifier_display,
                "user_email": user_email or "-",
                "user_role": user_info.get("role") or "-",
                "ip_address": ip_address or "-",
                "endpoint": limit.get("endpoint") or "-",
                "method": limit.get("method") or "-",
                "limit_definition": limit_definition or "-",
                "limit_count_display": usage_display or "-",
                "time_window_display": time_window_display or "-",
                "retry_after_display": retry_after_display or "-",
                "rate_limit_type": _normalise_rate_limit_type(
                    limit.get("type") or limit.get("rate_limit_type")
                ),
                "limit_key": limit.get("key") or key,
                "cancel_allowed": bool(limit.get("key")),
            }
        )

    return rows


def _format_historical_events_for_table(
    events: list[dict[str, Any]] | None,
    user_timezone: str | None,
) -> list[dict[str, Any]]:
    """Transform historical rate limit events for the unified table."""

    formatted_events = _format_rate_limit_events(events, user_timezone)
    rows: list[dict[str, Any]] = []

    for idx, event in enumerate(formatted_events):
        event_id = event.get("id") or event.get("limit_key") or event.get("occurred_at")
        if not event_id:
            event_id = f"event-{idx}"

        identifier_candidates = [
            event.get("identifier"),
            event.get("user_email"),
            event.get("ip_address"),
            event.get("limit_key"),
        ]
        identifier_display = next((value for value in identifier_candidates if value), "-")

        rows.append(
            {
                "id": f"event:{event_id}",
                "is_active": False,
                "status_display": "Historical",
                "occurred_at": event.get("occurred_at") or "-",
                "expires_at_display": "-",
                "identifier_display": identifier_display,
                "user_email": event.get("user_email") or "-",
                "user_role": event.get("user_role") or "-",
                "ip_address": event.get("ip_address") or "-",
                "endpoint": event.get("endpoint") or "-",
                "method": event.get("method") or "-",
                "limit_definition": event.get("limit_definition") or "-",
                "limit_count_display": event.get("limit_count_display") or "-",
                "time_window_display": event.get("time_window_display") or "-",
                "retry_after_display": event.get("retry_after_display") or "-",
                "rate_limit_type": _normalise_rate_limit_type(event.get("rate_limit_type")),
                "limit_key": event.get("limit_key") or event.get("id"),
                "cancel_allowed": False,
            }
        )

    return rows


def _query_rate_limit_breaches(
    request_data: dict[str, Any] | None,
    token: str | None,
    role: str | None,
    user_timezone: str | None,
    *,
    stored_state: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], int]:
    """Fetch combined active and historical rate limit rows for the unified table."""

    if not token or role not in ("ADMIN", "SUPERADMIN"):
        return {"rowData": [], "rowCount": 0}, stored_state or {}, 0

    stored_state = stored_state or {}
    request_data = request_data or {}

    try:
        start_row = int(request_data.get("startRow") or 0)
    except (TypeError, ValueError):
        start_row = 0
    start_row = max(start_row, 0)

    try:
        raw_end_row = request_data.get("endRow")
        end_row = int(raw_end_row) if raw_end_row is not None else None
    except (TypeError, ValueError):
        end_row = None

    default_block = stored_state.get("page_size") or DEFAULT_PAGE_SIZE
    if end_row is None or end_row <= start_row:
        end_row = start_row + max(default_block, DEFAULT_PAGE_SIZE)

    page_size = max(end_row - start_row, 1)

    sort_model = request_data.get("sortModel")
    if sort_model is None:
        sort_model = stored_state.get("sort_model") if stored_state else []
    sort_model = list(sort_model or [])

    sort_sql = build_sort_clause(sort_model, allowed_columns=("occurred_at",))
    table_state = build_table_state(sort_model, {}, sort_sql, None)
    table_state["page_size"] = page_size

    status_data = _fetch_rate_limit_status_data(token)
    active_limits = status_data.get("active_limits", []) if status_data else []
    active_rows = _format_active_limits_for_table(active_limits, user_timezone)
    active_count = len(active_rows)

    hist_start_row = max(start_row - active_count, 0)
    hist_needed = max(0, end_row - max(start_row, active_count))

    hist_rows: list[dict[str, Any]] = []
    hist_total = 0

    fetch_historical = hist_needed > 0 or start_row == 0

    if fetch_historical:
        per_page = max(DEFAULT_PAGE_SIZE, hist_needed, 1)
        initial_page = (hist_start_row // per_page) + 1 if hist_needed > 0 else 1
        current_page = initial_page
        offset = hist_start_row % per_page if hist_needed > 0 else 0
        remaining_needed = hist_needed

        while True:
            params = {
                "page": current_page,
                "per_page": per_page,
            }
            if sort_sql:
                params["sort"] = sort_sql

            try:
                response = make_authenticated_request(
                    RATE_LIMIT_EVENTS_ENDPOINT,
                    token,
                    params=params,
                    timeout=10,
                )
            except Exception as exc:  # pragma: no cover - defensive guard
                print(f"Error fetching rate limit events: {exc}")
                hist_rows = []
                hist_total = 0
                break

            if response.status_code != 200:
                print(f"Failed to fetch rate limit events: status {response.status_code}")
                hist_rows = []
                hist_total = 0
                break

            try:
                payload = response.json()
            except ValueError:
                payload = {}

            data = payload.get("data", {}) if isinstance(payload, dict) else {}
            events = data.get("events", []) if isinstance(data, dict) else []
            if not hist_total:
                try:
                    hist_total = int(data.get("total", 0) or 0)
                except (TypeError, ValueError):
                    hist_total = 0

            formatted_events = _format_historical_events_for_table(events, user_timezone)

            if hist_needed > 0:
                chunk = (
                    formatted_events[offset:] if current_page == initial_page else formatted_events
                )
                if chunk:
                    take = min(len(chunk), remaining_needed)
                    hist_rows.extend(chunk[:take])
                    remaining_needed -= take
                else:
                    remaining_needed = 0

            if hist_needed == 0:
                break

            if remaining_needed <= 0:
                break

            if len(formatted_events) < per_page:
                break

            current_page += 1
            offset = 0

    total_row_count = active_count + hist_total
    if not total_row_count:
        total_row_count = active_count + len(hist_rows)

    if total_row_count and start_row >= total_row_count:
        return {"rowData": [], "rowCount": total_row_count}, table_state, total_row_count

    rows: list[dict[str, Any]] = []

    if active_count and start_row < active_count:
        active_slice_end = min(active_count, end_row)
        rows.extend(active_rows[start_row:active_slice_end])

    rows.extend(hist_rows)

    return {"rowData": rows, "rowCount": total_row_count}, table_state, total_row_count


def register_callbacks(app):
    """Register admin-related callbacks."""

    @app.callback(
        [
            Output("admin-create-user-alert", "children"),
            Output("admin-create-user-alert", "color"),
            Output("admin-create-user-alert", "is_open"),
            Output("admin-new-user-name", "value"),
            Output("admin-new-user-email", "value"),
            Output("admin-new-user-password", "value"),
            Output("admin-new-user-confirm-password", "value"),
            Output("admin-new-user-institution", "value"),
            Output("admin-new-user-country", "value"),
            Output("admin-new-user-role", "value"),
        ],
        [
            Input("admin-create-user-btn", "n_clicks"),
            Input("admin-clear-user-form-btn", "n_clicks"),
        ],
        [
            State("admin-new-user-name", "value"),
            State("admin-new-user-email", "value"),
            State("admin-new-user-password", "value"),
            State("admin-new-user-confirm-password", "value"),
            State("admin-new-user-institution", "value"),
            State("admin-new-user-country", "value"),
            State("admin-new-user-role", "value"),
            State("token-store", "data"),
            State("role-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def handle_create_user(
        create_clicks,
        _clear_clicks,
        name,
        email,
        password,
        confirm_password,
        institution,
        country,
        role,
        token,
        user_role,
    ):
        """Handle user creation and form clearing."""
        ctx = callback_context
        if not ctx.triggered:
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
            )

        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

        # Check superadmin permissions for user creation
        if user_role != "SUPERADMIN":
            return (
                "Access denied. Super administrator privileges required.",
                "danger",
                True,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
            )

        if trigger_id == "admin-clear-user-form-btn":
            # Clear the form
            return "", "info", False, "", "", "", "", "", "", "USER"

        if trigger_id == "admin-create-user-btn" and create_clicks:
            # Validate inputs
            if not name or not email or not password:
                return (
                    "Please fill in all required fields (Name, Email, Password).",
                    "warning",
                    True,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                )

            if password != confirm_password:
                return (
                    "Passwords do not match.",
                    "warning",
                    True,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                )

            if len(password) < 6:
                return (
                    "Password must be at least 6 characters long.",
                    "warning",
                    True,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                )

            try:
                user_data = {
                    "name": name.strip(),
                    "email": email.strip().lower(),
                    "password": password,
                    "institution": institution.strip() if institution else None,
                    "country": country.strip() if country else None,
                    "role": role,
                    "is_active": True,
                }

                response = make_authenticated_request(
                    "/user", token, method="POST", json=user_data, timeout=10
                )

                if response.status_code in [200, 201]:
                    # Success - clear form and show success message
                    return (
                        f"User '{name}' created successfully with email '{email}'.",
                        "success",
                        True,
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "USER",
                    )
                elif response.status_code == 409:
                    return (
                        "A user with this email already exists.",
                        "warning",
                        True,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                    )
                elif response.status_code == 400:
                    error_detail = response.json().get("detail", "Invalid user data.")
                    return (
                        f"Error creating user: {error_detail}",
                        "danger",
                        True,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                    )
                else:
                    return (
                        f"Failed to create user. Server responded with status {response.status_code}.",
                        "danger",
                        True,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                    )

            except requests.exceptions.Timeout:
                return (
                    "Request timed out. Please try again.",
                    "danger",
                    True,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                )
            except requests.exceptions.ConnectionError:
                return (
                    "Cannot connect to server. Please check your connection.",
                    "danger",
                    True,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                )
            except Exception as e:
                return (
                    f"Unexpected error: {str(e)}",
                    "danger",
                    True,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                )

        return (
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
        )

    @app.callback(
        [
            Output("admin-script-upload-status", "children"),
            Output("admin-upload-script-btn", "disabled"),
        ],
        [Input("admin-script-upload", "contents")],
        [State("admin-script-upload", "filename")],
        prevent_initial_call=True,
    )
    def handle_script_upload_preview(contents, filename):
        """Handle script file upload preview."""
        if contents is None:
            return "", True

        if filename:
            # Get file size from base64 content
            content_string = contents.split(",")[1]
            decoded = base64.b64decode(content_string)
            file_size = len(decoded)
            file_size_mb = file_size / (1024 * 1024)

            if file_size_mb > 10:  # 10MB limit
                return html.Div(
                    [
                        html.I(className="fas fa-exclamation-triangle text-warning me-2"),
                        f"File too large: {filename} ({file_size_mb:.1f}MB). Maximum 10MB allowed.",
                    ]
                ), True

            return html.Div(
                [
                    html.I(className="fas fa-check-circle text-success me-2"),
                    f"File ready: {filename} ({file_size_mb:.2f}MB)",
                ]
            ), False

        return "", True

    @app.callback(
        [
            Output("admin-upload-script-alert", "children"),
            Output("admin-upload-script-alert", "color"),
            Output("admin-upload-script-alert", "is_open"),
            Output("admin-new-script-name", "value"),
            Output("admin-new-script-description", "value"),
            Output("admin-new-script-status", "value"),
            Output("admin-script-upload", "contents"),
            Output("admin-script-upload", "filename"),
        ],
        [
            Input("admin-upload-script-btn", "n_clicks"),
            Input("admin-clear-script-form-btn", "n_clicks"),
        ],
        [
            State("admin-new-script-name", "value"),
            State("admin-new-script-description", "value"),
            State("admin-new-script-status", "value"),
            State("admin-script-upload", "contents"),
            State("admin-script-upload", "filename"),
            State("token-store", "data"),
            State("role-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def handle_upload_script(
        upload_clicks,
        _clear_clicks,
        name,
        description,
        status,
        contents,
        filename,
        token,
        user_role,
    ):
        """Handle script upload and form clearing."""
        ctx = callback_context
        if not ctx.triggered:
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
            )

        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

        # Check admin permissions for script management
        if user_role not in ["ADMIN", "SUPERADMIN"]:
            return (
                "Access denied. Administrator privileges required.",
                "danger",
                True,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
            )

        if trigger_id == "admin-clear-script-form-btn":
            # Clear the form
            return "", "info", False, "", "", "DRAFT", None, None

        if trigger_id == "admin-upload-script-btn" and upload_clicks:
            # Validate inputs
            if not name or not contents or not filename:
                return (
                    "Please fill in the script name and select a file to upload.",
                    "warning",
                    True,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                )

            try:
                # Prepare script data
                content_string = contents.split(",")[1]
                decoded_content = base64.b64decode(content_string)

                script_data = {
                    "name": name.strip(),
                    "description": description.strip() if description else "",
                    "status": status,
                    "filename": filename,
                }

                # Create multipart form data
                files = {"file": (filename, decoded_content)}

                response = make_authenticated_request(
                    "/script", token, method="POST", data=script_data, files=files, timeout=30
                )

                if response.status_code in [200, 201]:
                    # Success - clear form and show success message
                    return (
                        f"Script '{name}' uploaded successfully.",
                        "success",
                        True,
                        "",
                        "",
                        "DRAFT",
                        None,
                        None,
                    )
                elif response.status_code == 409:
                    return (
                        "A script with this name already exists.",
                        "warning",
                        True,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                    )
                elif response.status_code == 400:
                    error_detail = response.json().get("detail", "Invalid script data.")
                    return (
                        f"Error uploading script: {error_detail}",
                        "danger",
                        True,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                    )
                else:
                    return (
                        f"Failed to upload script. Server responded with status {response.status_code}.",
                        "danger",
                        True,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                        no_update,
                    )

            except requests.exceptions.Timeout:
                return (
                    "Upload timed out. Please try again with a smaller file.",
                    "danger",
                    True,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                )
            except requests.exceptions.ConnectionError:
                return (
                    "Cannot connect to server. Please check your connection.",
                    "danger",
                    True,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                )
            except Exception as e:
                return (
                    f"Unexpected error: {str(e)}",
                    "danger",
                    True,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                )

        return (
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
        )

    @app.callback(
        [
            Output("admin-total-users", "children"),
            Output("admin-total-scripts", "children"),
            Output("admin-active-executions", "children"),
        ],
        [
            Input("admin-refresh-stats-btn", "n_clicks"),
        ],
        [
            State("token-store", "data"),
            State("role-store", "data"),
            State("active-tab-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def refresh_admin_stats(refresh_clicks, token, user_role, active_tab):
        """Refresh admin statistics."""
        # Guard: Skip if not logged in or not admin (prevents execution after logout)
        if not token or user_role != "ADMIN":
            return no_update, no_update, no_update

        # Only update when admin tab is active or refresh button is clicked
        if active_tab != "admin" and not refresh_clicks:
            return no_update, no_update, no_update

        try:
            # Get user count
            user_response = make_authenticated_request("/user?per_page=1", token, timeout=5)
            total_users = (
                user_response.json().get("total", 0)
                if user_response.status_code == 200
                else "Error"
            )

            # Get script count
            script_response = make_authenticated_request("/script?per_page=1", token, timeout=5)
            total_scripts = (
                script_response.json().get("total", 0)
                if script_response.status_code == 200
                else "Error"
            )

            # Get active execution count (READY, RUNNING, and PENDING)
            exec_response = make_authenticated_request(
                "/execution?filter=status=READY,status=RUNNING,status=PENDING&per_page=1",
                token,
                timeout=5,
            )
            active_executions = (
                exec_response.json().get("total", 0)
                if exec_response.status_code == 200
                else "Error"
            )

            return str(total_users), str(total_scripts), str(active_executions)

        except Exception as e:
            print(f"Error fetching admin stats: {e}")
            return "Error", "Error", "Error"

    @app.callback(
        Output("reset-rate-limits-modal", "is_open"),
        [
            Input("admin-reset-rate-limits-btn", "n_clicks"),
            Input("cancel-reset-rate-limits", "n_clicks"),
            Input("confirm-reset-rate-limits", "n_clicks"),
        ],
        [State("reset-rate-limits-modal", "is_open")],
        prevent_initial_call=True,
    )
    def toggle_reset_rate_limits_modal(_btn_clicks, _cancel_clicks, _confirm_clicks, _is_open):
        """Toggle the rate limits reset confirmation modal."""
        ctx = callback_context
        if not ctx.triggered:
            return no_update

        # Get the triggered component ID
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]

        # Only respond to actual button clicks (not initial None values)
        triggered_value = ctx.triggered[0]["value"]
        if triggered_value is None:
            return no_update

        if button_id == "admin-reset-rate-limits-btn":
            return True
        elif button_id in ["cancel-reset-rate-limits", "confirm-reset-rate-limits"]:
            return False

        return no_update

    @app.callback(
        [
            Output("admin-reset-rate-limits-alert", "children"),
            Output("admin-reset-rate-limits-alert", "color"),
            Output("admin-reset-rate-limits-alert", "is_open"),
            Output("rate-limit-breaches-table", "getRowsResponse", allow_duplicate=True),
            Output("rate-limit-breaches-table-state", "data", allow_duplicate=True),
            Output("rate-limit-breaches-total-count-store", "data", allow_duplicate=True),
            Output("selected-rate-limit-data", "data", allow_duplicate=True),
        ],
        [Input("confirm-reset-rate-limits", "n_clicks")],
        [
            State("token-store", "data"),
            State("role-store", "data"),
            State("api-environment-store", "data"),
            State("rate-limit-breaches-table-state", "data"),
            State("user-timezone-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def reset_rate_limits(
        confirm_clicks, token, role, _api_environment, table_state, user_timezone
    ):
        """Reset all rate limits via API call."""
        if not confirm_clicks or not token or role != "SUPERADMIN":
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update

        try:
            # Make API call to reset rate limits
            resp = make_authenticated_request("/rate-limit/reset", token, method="POST", json={})

            refresh_request = {
                "startRow": 0,
                "endRow": (table_state or {}).get("page_size", DEFAULT_PAGE_SIZE),
                "sortModel": (table_state or {}).get("sort_model"),
            }

            grid_response = no_update
            new_table_state = no_update
            new_total = no_update

            if resp.status_code == 200:
                grid_response, new_table_state, new_total = _query_rate_limit_breaches(
                    refresh_request,
                    token,
                    role,
                    user_timezone,
                    stored_state=table_state or {},
                )
                return (
                    [
                        html.I(className="fas fa-check-circle me-2"),
                        "Rate limits have been successfully reset for all users and endpoints.",
                    ],
                    "success",
                    True,
                    grid_response,
                    new_table_state,
                    new_total,
                    None,
                )

            error_msg = f"Failed to reset rate limits. Status: {resp.status_code}"
            try:
                error_data = resp.json()
                if "detail" in error_data:
                    error_msg += f" - {error_data['detail']}"
            except (ValueError, KeyError):
                error_msg += f" - {resp.text}"

            return (
                [html.I(className="fas fa-exclamation-triangle me-2"), error_msg],
                "danger",
                True,
                grid_response,
                new_table_state,
                new_total,
                no_update,
            )

        except Exception as e:
            return (
                [
                    html.I(className="fas fa-exclamation-triangle me-2"),
                    f"Error resetting rate limits: {str(e)}",
                ],
                "danger",
                True,
                no_update,
                no_update,
                no_update,
                no_update,
            )

    @app.callback(
        [
            Output("rate-limit-breaches-table", "getRowsResponse"),
            Output("rate-limit-breaches-table-state", "data"),
            Output("rate-limit-breaches-total-count-store", "data"),
        ],
        Input("rate-limit-breaches-table", "getRowsRequest"),
        [
            State("token-store", "data"),
            State("role-store", "data"),
            State("user-timezone-store", "data"),
        ],
        prevent_initial_call=False,
    )
    def load_rate_limit_breaches(request, token, role, user_timezone):
        """Load combined active and historical rate limit data for the unified grid."""

        return _query_rate_limit_breaches(request, token, role, user_timezone)

    @app.callback(
        [
            Output("rate-limit-breaches-table", "getRowsResponse", allow_duplicate=True),
            Output("rate-limit-breaches-table-state", "data", allow_duplicate=True),
            Output("rate-limit-breaches-total-count-store", "data", allow_duplicate=True),
        ],
        Input("refresh-rate-limit-breaches-btn", "n_clicks"),
        [
            State("rate-limit-breaches-table-state", "data"),
            State("token-store", "data"),
            State("role-store", "data"),
            State("user-timezone-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def refresh_rate_limit_breaches(n_clicks, table_state, token, role, user_timezone):
        """Refresh the rate limit breaches grid while preserving sort state."""

        if not n_clicks:
            return no_update, table_state or {}, no_update

        request = {
            "startRow": 0,
            "endRow": (table_state or {}).get("page_size", DEFAULT_PAGE_SIZE),
            "sortModel": (table_state or {}).get("sort_model"),
        }

        response, new_state, total = _query_rate_limit_breaches(
            request,
            token,
            role,
            user_timezone,
            stored_state=table_state or {},
        )

        return response, new_state, total

    @app.callback(
        Output("rate-limit-breaches-total-count", "children"),
        Input("rate-limit-breaches-total-count-store", "data"),
        prevent_initial_call=False,
    )
    def update_rate_limit_breaches_total_display(total_count):
        """Display the combined total for active and historical rate limit entries."""

        try:
            numeric = int(total_count)
        except (TypeError, ValueError):
            numeric = 0
        return f"Total: {numeric:,}"

    @app.callback(
        [
            Output("selected-rate-limit-data", "data"),
            Output("reset-selected-rate-limit-btn", "disabled"),
        ],
        Input("rate-limit-breaches-table", "selectedRows"),
        State("role-store", "data"),
        prevent_initial_call=False,
    )
    def update_selected_rate_limit(selected_rows, role):
        """Persist selected row data and enable reset when appropriate."""

        if role != "SUPERADMIN":
            return None, True

        if not selected_rows:
            return None, True

        row = selected_rows[0]
        if not row or not row.get("cancel_allowed"):
            return None, True

        return row, False

    @app.callback(
        [
            Output("reset-individual-rate-limit-modal", "is_open"),
            Output("individual-rate-limit-details", "children"),
        ],
        [
            Input("reset-selected-rate-limit-btn", "n_clicks"),
            Input("cancel-reset-individual-rate-limit", "n_clicks"),
        ],
        [
            State("selected-rate-limit-data", "data"),
            State("role-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def open_reset_individual_rate_limit_modal(reset_clicks, _cancel_clicks, selected_row, role):
        """Open the confirmation modal for cancelling an active rate limit."""

        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update

        trigger = ctx.triggered[0]["prop_id"].split(".")[0]

        if trigger == "cancel-reset-individual-rate-limit" or role != "SUPERADMIN":
            return False, no_update

        if trigger != "reset-selected-rate-limit-btn" or not reset_clicks:
            return no_update, no_update

        if not selected_row or not selected_row.get("limit_key"):
            details = [
                dbc.Alert(
                    [
                        html.I(className="fas fa-info-circle me-2"),
                        "Select an active rate limit row to cancel.",
                    ],
                    color="warning",
                    className="mb-0",
                )
            ]
            return True, details

        details = html.Dl(
            [
                html.Dt("Identifier:", className="fw-bold"),
                html.Dd(selected_row.get("identifier_display", "-")),
                html.Dt("Type:", className="fw-bold"),
                html.Dd(selected_row.get("rate_limit_type", "-")),
                html.Dt("Usage:", className="fw-bold"),
                html.Dd(selected_row.get("limit_count_display", "-")),
                html.Dt("Limit Rule:", className="fw-bold"),
                html.Dd(selected_row.get("limit_definition", "-")),
                html.Dt("First Seen:", className="fw-bold"),
                html.Dd(selected_row.get("occurred_at", "-")),
                html.Dt("Expires:", className="fw-bold"),
                html.Dd(selected_row.get("expires_at_display", "-")),
            ]
        )

        return True, [details]

    @app.callback(
        [
            Output("admin-reset-rate-limits-alert", "children", allow_duplicate=True),
            Output("admin-reset-rate-limits-alert", "color", allow_duplicate=True),
            Output("admin-reset-rate-limits-alert", "is_open", allow_duplicate=True),
            Output("reset-individual-rate-limit-modal", "is_open", allow_duplicate=True),
            Output("rate-limit-breaches-table", "getRowsResponse", allow_duplicate=True),
            Output("rate-limit-breaches-table-state", "data", allow_duplicate=True),
            Output("rate-limit-breaches-total-count-store", "data", allow_duplicate=True),
            Output("selected-rate-limit-data", "data", allow_duplicate=True),
        ],
        [Input("confirm-reset-individual-rate-limit", "n_clicks")],
        [
            State("selected-rate-limit-data", "data"),
            State("token-store", "data"),
            State("role-store", "data"),
            State("rate-limit-breaches-table-state", "data"),
            State("user-timezone-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def reset_individual_rate_limit(
        confirm_clicks,
        rate_limit_data,
        token,
        role,
        table_state,
        user_timezone,
    ):
        """Reset a specific rate limit via API call."""
        if not confirm_clicks or not token or role != "SUPERADMIN" or not rate_limit_data:
            return (no_update,) * 8

        limit_key = rate_limit_data.get("limit_key")
        identifier_display = rate_limit_data.get("identifier_display", "")

        if not limit_key:
            return (
                [
                    html.I(className="fas fa-exclamation-triangle me-2"),
                    "Error: No rate limit selected.",
                ],
                "danger",
                True,
                False,
                no_update,
                no_update,
                no_update,
                no_update,
                rate_limit_data,
            )

        try:
            # Make API call to reset specific rate limit
            resp = make_authenticated_request(
                f"/rate-limit/reset/{limit_key}", token, method="POST", json={}
            )

            should_refresh_grid = resp.status_code in (200, 404)
            grid_response = no_update
            new_table_state = no_update
            new_total = no_update

            if should_refresh_grid:
                request = {
                    "startRow": 0,
                    "endRow": (table_state or {}).get("page_size", DEFAULT_PAGE_SIZE),
                    "sortModel": (table_state or {}).get("sort_model"),
                }
                grid_response, new_table_state, new_total = _query_rate_limit_breaches(
                    request,
                    token,
                    role,
                    user_timezone,
                    stored_state=table_state or {},
                )

            if resp.status_code == 200:
                return (
                    [
                        html.I(className="fas fa-check-circle me-2"),
                        f"Rate limit for {identifier_display} has been successfully reset.",
                    ],
                    "success",
                    True,
                    False,
                    grid_response,
                    new_table_state,
                    new_total,
                    None,
                )
            elif resp.status_code == 404:
                return (
                    [
                        html.I(className="fas fa-info-circle me-2"),
                        f"Rate limit for {identifier_display} not found. It may have already expired.",
                    ],
                    "info",
                    True,
                    False,
                    grid_response,
                    new_table_state,
                    new_total,
                    None,
                )
            else:
                error_msg = f"Failed to reset rate limit. Status: {resp.status_code}"
                try:
                    error_data = resp.json()
                    if "error" in error_data:
                        error_msg += f" - {error_data['error']}"
                    elif "detail" in error_data:
                        error_msg += f" - {error_data['detail']}"
                except (ValueError, KeyError):
                    if resp.text:
                        error_msg += f" - {resp.text[:200]}"

                return (
                    [html.I(className="fas fa-exclamation-triangle me-2"), error_msg],
                    "danger",
                    True,
                    False,
                    no_update,
                    no_update,
                    no_update,
                    rate_limit_data,
                )

        except Exception as e:
            return (
                [
                    html.I(className="fas fa-exclamation-triangle me-2"),
                    f"Error resetting rate limit: {str(e)}",
                ],
                "danger",
                True,
                False,
                no_update,
                no_update,
                no_update,
                rate_limit_data,
            )
