"""Admin functionality callbacks."""

import base64
from datetime import datetime, timezone
import logging
from typing import Any

from dash import Input, Output, State, callback_context, html, no_update
import dash_bootstrap_components as dbc
import requests

from ..config import DEFAULT_PAGE_SIZE
from ..utils.aggrid import build_sort_clause, build_table_state
from ..utils.helpers import make_authenticated_request, parse_date

logger = logging.getLogger(__name__)

RATE_LIMIT_EVENTS_ENDPOINT = "/rate-limit/events"
MAX_RATE_LIMIT_EVENT_PAGE_SIZE = 500


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

    resolved_timezone = user_timezone or "UTC"
    rows: list[dict[str, Any]] = []

    for event in events:
        event = dict(event)
        occurred_display = parse_date(event.get("occurred_at"), resolved_timezone)
        event["occurred_at"] = occurred_display or "-"
        expires_display = parse_date(event.get("expires_at"), resolved_timezone)
        event["expires_at_display"] = expires_display or "-"
        event["time_window_display"] = _format_duration_label(event.get("time_window_seconds"))
        event["retry_after_display"] = _format_duration_label(event.get("retry_after_seconds"))
        event["limit_count_display"] = _format_limit_count(event.get("limit_count"))
        event["current_count_display"] = _format_limit_count(event.get("current_count"))
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


def _parse_iso_datetime(value: Any) -> datetime | None:
    """Safely parse ISO formatted timestamps into aware datetimes."""

    if value in (None, ""):
        return None

    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    text = str(value)
    if not text:
        return None

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _format_combined_rate_limit_rows(
    events: list[dict[str, Any]] | None,
    user_timezone: str | None,
) -> list[dict[str, Any]]:
    """Transform rate limit events (active + historical) for the unified table."""

    if not events:
        return []

    formatted_events = _format_rate_limit_events(events, user_timezone)
    now_utc = datetime.now(timezone.utc)
    timezone_label = user_timezone or "UTC"
    rows: list[dict[str, Any]] = []

    for idx, raw_event in enumerate(formatted_events):
        event = dict(raw_event or {})

        is_active = bool(event.get("is_active"))
        status_value = event.get("status") or event.get("state")
        if isinstance(status_value, str):
            is_active = status_value.strip().lower() == "active"
        else:
            active_flag = event.get("active")
            if isinstance(active_flag, bool):
                is_active = active_flag
            elif active_flag not in (None, ""):
                try:
                    is_active = bool(int(active_flag))
                except (TypeError, ValueError):
                    is_active = bool(active_flag)

        if not is_active:
            expires_dt = _parse_iso_datetime(event.get("expires_at"))
            if expires_dt and expires_dt > now_utc:
                is_active = True

        expires_display = event.get("expires_at_display") if is_active else "-"
        if is_active and (not expires_display or expires_display == "-"):
            expires_display = parse_date(event.get("expires_at"), timezone_label) or "-"

        user_info_raw = event.get("user_info")
        user_info = user_info_raw if isinstance(user_info_raw, dict) else {}
        user_name = (user_info.get("name") or event.get("user_name") or "").strip()
        user_email = (event.get("user_email") or user_info.get("email") or "").strip()

        identifier_candidates: list[str] = []
        if user_name and user_email:
            identifier_candidates.append(f"{user_name} ({user_email})")

        for candidate in (
            event.get("identifier"),
            user_email,
            user_name,
            event.get("ip_address"),
            event.get("limit_key"),
        ):
            if candidate:
                identifier_candidates.append(str(candidate))

        identifier_display = identifier_candidates[0] if identifier_candidates else "-"

        current_display = event.get("current_count_display") or _format_limit_count(
            event.get("current_count")
        )
        limit_total_display = event.get("limit_count_display") or _format_limit_count(
            event.get("limit_count")
        )

        if current_display in (None, ""):
            current_display = "-"
        if limit_total_display in (None, ""):
            limit_total_display = "-"

        if limit_total_display not in ("-", "0") and current_display not in ("-", "0"):
            usage_display = f"{current_display} / {limit_total_display}"
        elif limit_total_display not in ("-", "0"):
            usage_display = (
                f"{current_display} / {limit_total_display}"
                if current_display != "-"
                else limit_total_display
            )
        else:
            usage_display = current_display

        time_window_display = event.get("time_window_display") or _format_duration_label(
            event.get("time_window_seconds")
        )
        retry_after_display = event.get("retry_after_display") or _format_duration_label(
            event.get("retry_after_seconds")
        )

        limit_definition = event.get("limit_definition")
        if not limit_definition:
            if limit_total_display not in ("-", "0") and time_window_display != "-":
                limit_definition = f"{limit_total_display} per {time_window_display}"
            elif limit_total_display not in ("-", "0"):
                limit_definition = limit_total_display
            else:
                limit_definition = "-"

        raw_id = event.get("id") or event.get("limit_key") or event.get("identifier")
        if raw_id in (None, ""):
            raw_id = f"event-{idx}"

        row_id = str(raw_id)

        rows.append(
            {
                "id": f"{'active' if is_active else 'event'}:{row_id}",
                "is_active": is_active,
                "status_display": "Active" if is_active else "Historical",
                "occurred_at": event.get("occurred_at") or "-",
                "expires_at_display": expires_display,
                "identifier_display": identifier_display,
                "user_email": user_email or "-",
                "user_role": user_info.get("role") or event.get("user_role") or "-",
                "ip_address": event.get("ip_address") or "-",
                "endpoint": event.get("endpoint") or "-",
                "method": event.get("method") or "-",
                "limit_definition": limit_definition or "-",
                "limit_count_display": usage_display or "-",
                "time_window_display": time_window_display or "-",
                "retry_after_display": retry_after_display or "-",
                "rate_limit_type": _normalise_rate_limit_type(
                    event.get("rate_limit_type") or event.get("type")
                ),
                "limit_key": event.get("limit_key"),
                "cancel_allowed": is_active and bool(event.get("limit_key")),
            }
        )

    return rows


def _extract_rate_limit_events(payload: Any) -> tuple[list[dict[str, Any]], int | None]:
    """Normalise API payloads into a combined event list and total count."""

    events: list[dict[str, Any]] = []
    total_candidates: list[int] = []

    def _extend(items: Any, *, force_active: bool | None = None) -> None:
        if not isinstance(items, list):
            return
        for item in items:
            if not isinstance(item, dict):
                continue
            entry = dict(item)
            if force_active is not None and "is_active" not in entry:
                entry["is_active"] = force_active
            events.append(entry)

    if isinstance(payload, dict):
        events_list = payload.get("events")
        if isinstance(events_list, list):
            _extend(events_list)

        for key in ("items", "records"):
            value = payload.get(key)
            if isinstance(value, list):
                _extend(value)

        results_section = payload.get("results")
        if isinstance(results_section, dict):
            nested_events, nested_total = _extract_rate_limit_events(results_section)
            events.extend(nested_events)
            if nested_total is not None:
                total_candidates.append(int(nested_total))

        events_include_active = any(
            isinstance(item, dict)
            and (
                bool(item.get("is_active"))
                or str(item.get("status", "")).strip().lower() == "active"
                or str(item.get("state", "")).strip().lower() == "active"
            )
            for item in events
        )

        if not events_include_active:
            active_sources: list[dict[str, Any]] = []
            for key in ("active_limits", "active_events", "active"):
                candidate = payload.get(key)
                if isinstance(candidate, list):
                    active_sources.extend(candidate)
            if active_sources:
                _extend(active_sources, force_active=True)

        for key in (
            "total_combined",
            "total",
            "count",
            "row_count",
            "rowCount",
            "combined_total",
        ):
            value = payload.get(key)
            if isinstance(value, (int, float)):
                total_candidates.append(int(value))

        active_total = payload.get("total_active") or payload.get("active_total")
        hist_total = payload.get("total_historical") or payload.get("historical_total")
        if isinstance(active_total, (int, float)) and isinstance(hist_total, (int, float)):
            total_candidates.append(int(active_total) + int(hist_total))
        elif isinstance(active_total, (int, float)):
            total_candidates.append(int(active_total))
        elif isinstance(hist_total, (int, float)):
            total_candidates.append(int(hist_total))

    elif isinstance(payload, list):
        _extend(payload)

    total = max(total_candidates) if total_candidates else None
    return events, total


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

    default_block = stored_state.get("page_size")
    if not isinstance(default_block, int) or default_block <= 0:
        default_block = DEFAULT_PAGE_SIZE

    if end_row is None or end_row <= start_row:
        requested_block = max(default_block, DEFAULT_PAGE_SIZE)
        end_row = start_row + requested_block
    else:
        requested_block = end_row - start_row

    if start_row == 0 and requested_block < default_block:
        requested_block = max(default_block, DEFAULT_PAGE_SIZE)
        end_row = start_row + requested_block

    requested_block = max(requested_block, 1)
    page_size = max(requested_block, default_block, DEFAULT_PAGE_SIZE)
    page_size = min(page_size, MAX_RATE_LIMIT_EVENT_PAGE_SIZE)

    page = (start_row // page_size) + 1
    offset_within_page = start_row - ((page - 1) * page_size)
    remaining_needed = requested_block

    sort_model = request_data.get("sortModel")
    if sort_model is None:
        sort_model = stored_state.get("sort_model") if stored_state else []
    sort_model = list(sort_model or [])

    sort_sql = build_sort_clause(sort_model, allowed_columns=("occurred_at",))
    table_state = build_table_state(sort_model, {}, sort_sql, None)
    table_state["page_size"] = page_size

    combined_events: list[dict[str, Any]] = []
    seen_identifiers: set[str] = set()
    total_row_count: int | None = None
    current_page = page
    is_first_page = True
    last_raw_count = 0
    serial_counter = 0

    while remaining_needed > 0:
        params = {
            "page": current_page,
            "per_page": page_size,
            "include_active": "true",
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
            logger.exception("Error fetching rate limit events: %s", exc)
            combined_events = []
            total_row_count = 0
            break

        if response.status_code != 200:
            logger.warning("Failed to fetch rate limit events: status %s", response.status_code)
            combined_events = []
            total_row_count = 0
            break

        try:
            payload = response.json()
        except ValueError:
            payload = {}

        data_section = payload.get("data") if isinstance(payload, dict) else payload
        events_page_raw, total_candidate = _extract_rate_limit_events(data_section)

        if total_candidate is not None:
            total_row_count = (
                max(total_row_count or 0, int(total_candidate))
                if total_row_count is not None
                else int(total_candidate)
            )

        last_raw_count = len(events_page_raw)
        if not events_page_raw:
            break

        if is_first_page and offset_within_page:
            if offset_within_page >= last_raw_count:
                events_page = []
            else:
                events_page = events_page_raw[offset_within_page:]
            offset_within_page = 0
        else:
            events_page = events_page_raw

        if not events_page:
            if last_raw_count < page_size:
                break
            current_page += 1
            is_first_page = False
            continue

        filtered_events: list[dict[str, Any]] = []
        for event in events_page:
            if not isinstance(event, dict):
                continue
            unique_id: str | None = None

            event_id = event.get("id")
            if event_id not in (None, ""):
                unique_id = str(event_id)
            else:
                limit_key = event.get("limit_key")
                occurred_at = event.get("occurred_at")
                if limit_key not in (None, "") and occurred_at not in (None, ""):
                    unique_id = f"{limit_key}:{occurred_at}"
                else:
                    identifier = event.get("identifier")
                    if identifier not in (None, "") and occurred_at not in (None, ""):
                        unique_id = f"{identifier}:{occurred_at}"
                    elif occurred_at not in (None, ""):
                        unique_id = str(occurred_at)
                    elif limit_key not in (None, ""):
                        unique_id = str(limit_key)

            if unique_id is None:
                unique_id = f"event-{current_page}-{serial_counter}"
            serial_counter += 1
            if unique_id in seen_identifiers:
                continue
            seen_identifiers.add(unique_id)
            filtered_events.append(event)

        if not filtered_events:
            if last_raw_count < page_size:
                break
            current_page += 1
            is_first_page = False
            continue

        take = min(len(filtered_events), remaining_needed)
        combined_events.extend(filtered_events[:take])
        remaining_needed -= take

        if remaining_needed <= 0:
            break

        if last_raw_count < page_size:
            break

        current_page += 1
        is_first_page = False

    rows = _format_combined_rate_limit_rows(combined_events, user_timezone)

    produced_rows = len(rows)
    minimal_total = start_row + produced_rows

    if total_row_count is None:
        if remaining_needed <= 0 and last_raw_count == page_size:
            total_row_count = minimal_total + page_size
        else:
            total_row_count = minimal_total
    else:
        if total_row_count < minimal_total:
            total_row_count = minimal_total

    if total_row_count and start_row >= total_row_count:
        return {"rowData": [], "rowCount": total_row_count}, table_state, total_row_count

    return {"rowData": rows, "rowCount": total_row_count}, table_state, total_row_count


def register_callbacks(app):
    """Register admin-related callbacks."""

    @app.callback(
        Output("admin-new-user-country", "options"),
        [Input("token-store", "data")],
        prevent_initial_call=False,
    )
    def populate_admin_country_dropdown(token):
        """Populate the country dropdown for the admin new user form.

        Uses the boundaries API if available (with auth), otherwise falls back
        to the static country list.
        """
        from ..config import detect_api_environment_from_host
        from ..utils.boundaries_utils import get_country_options

        api_environment = detect_api_environment_from_host()
        return get_country_options(api_environment=api_environment, token=token)

    # Real-time password validation callback for admin new user form
    @app.callback(
        [
            Output("admin-new-user-req-length", "className"),
            Output("admin-new-user-req-uppercase", "className"),
            Output("admin-new-user-req-lowercase", "className"),
            Output("admin-new-user-req-number", "className"),
            Output("admin-new-user-req-special", "className"),
            Output("admin-new-user-req-match", "className"),
        ],
        [
            Input("admin-new-user-password", "value"),
            Input("admin-new-user-confirm-password", "value"),
        ],
        prevent_initial_call=True,
    )
    def validate_admin_new_user_password_requirements(password, confirm_password):
        """Validate password requirements in real-time and update UI indicators."""
        import re

        if not password:
            # Return all as muted when no password entered
            return ["text-muted"] * 6

        special_chars = r"!@#$%^&*()\-_=+\[\]{}|;:,.<>?/"

        # Check each requirement
        has_length = len(password) >= 12
        has_upper = bool(re.search(r"[A-Z]", password))
        has_lower = bool(re.search(r"[a-z]", password))
        has_number = bool(re.search(r"\d", password))
        has_special = bool(re.search(f"[{special_chars}]", password))
        passwords_match = bool(password and confirm_password and password == confirm_password)

        # Return success (green) or danger (red) class for each requirement
        return [
            "text-success" if has_length else "text-danger",
            "text-success" if has_upper else "text-danger",
            "text-success" if has_lower else "text-danger",
            "text-success" if has_number else "text-danger",
            "text-success" if has_special else "text-danger",
            "text-success" if passwords_match else "text-danger",
        ]

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

            # Validate password meets API requirements
            import re

            special_chars = r"!@#$%^&*()\-_=+\[\]{}|;:,.<>?/"
            password_errors = []
            if len(password) < 12:
                password_errors.append("at least 12 characters")
            if not re.search(r"[A-Z]", password):
                password_errors.append("an uppercase letter")
            if not re.search(r"[a-z]", password):
                password_errors.append("a lowercase letter")
            if not re.search(r"\d", password):
                password_errors.append("a number")
            if not re.search(f"[{special_chars}]", password):
                password_errors.append("a special character")

            if password_errors:
                return (
                    f"Password must contain {', '.join(password_errors)}.",
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
            # Validate file extension - API requires .tar.gz archives
            if not filename.endswith(".tar.gz"):
                return html.Div(
                    [
                        html.I(className="fas fa-exclamation-triangle text-warning me-2"),
                        f"Invalid file type: {filename}. Must be a .tar.gz archive containing configuration.json.",
                    ]
                ), True

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
                    f"Archive ready: {filename} ({file_size_mb:.2f}MB)",
                ]
            ), False

        return "", True

    @app.callback(
        [
            Output("admin-upload-script-alert", "children"),
            Output("admin-upload-script-alert", "color"),
            Output("admin-upload-script-alert", "is_open"),
            Output("admin-script-upload", "contents"),
            Output("admin-script-upload", "filename"),
        ],
        [
            Input("admin-upload-script-btn", "n_clicks"),
            Input("admin-clear-script-form-btn", "n_clicks"),
        ],
        [
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
            )

        if trigger_id == "admin-clear-script-form-btn":
            # Clear the form
            return "", "info", False, None, None

        if trigger_id == "admin-upload-script-btn" and upload_clicks:
            # Validate inputs - only file is required, name/description come from configuration.json in archive
            if not contents or not filename:
                return (
                    "Please select a .tar.gz script archive to upload.",
                    "warning",
                    True,
                    no_update,
                    no_update,
                )

            # Validate file extension
            if not filename.endswith(".tar.gz"):
                return (
                    "Invalid file type. The API requires a .tar.gz archive containing a configuration.json file.",
                    "warning",
                    True,
                    no_update,
                    no_update,
                )

            try:
                # Decode the file content
                content_string = contents.split(",")[1]
                decoded_content = base64.b64decode(content_string)

                # Create multipart form data - API only expects the file
                # Script metadata (name, description, etc.) is extracted from configuration.json inside the archive
                files = {"file": (filename, decoded_content, "application/gzip")}

                response = make_authenticated_request(
                    "/script", token, method="POST", files=files, timeout=60
                )

                if response.status_code in [200, 201]:
                    # Success - extract script name from response if available
                    try:
                        script_data = response.json().get("data", {})
                        script_name = script_data.get("name", filename)
                    except Exception:
                        script_name = filename
                    # Clear form and show success message
                    return (
                        f"Script '{script_name}' uploaded successfully.",
                        "success",
                        True,
                        None,
                        None,
                    )
                elif response.status_code == 400:
                    # Handle duplicate script (ScriptDuplicated) or invalid file (InvalidFile)
                    try:
                        error_detail = response.json().get("detail", "Invalid script archive.")
                    except Exception:
                        error_detail = response.text or "Invalid script archive."
                    return (
                        f"Error uploading script: {error_detail}",
                        "danger",
                        True,
                        no_update,
                        no_update,
                    )
                elif response.status_code == 403:
                    return (
                        "Permission denied. Only admins and superadmins can create scripts.",
                        "danger",
                        True,
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
                    )

            except requests.exceptions.Timeout:
                return (
                    "Upload timed out. Please try again with a smaller file.",
                    "danger",
                    True,
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
                )
            except Exception as e:
                return (
                    f"Unexpected error: {str(e)}",
                    "danger",
                    True,
                    no_update,
                    no_update,
                )

        return (
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
            logger.exception("Error fetching admin stats: %s", e)
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
