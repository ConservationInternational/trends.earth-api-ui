"""Status dashboard callbacks."""

from datetime import datetime, timedelta
import time

from dash import Input, Output, State, callback_context, dcc, html, no_update
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests

from ..config import API_BASE
from ..utils.timezone_utils import format_local_time, get_chart_axis_label, get_safe_timezone

# Simple in-memory cache for status data with TTL
_status_cache = {
    "summary": {"data": None, "timestamp": 0, "ttl": 20},  # 20 seconds for faster updates
    "charts": {"data": {}, "timestamp": 0, "ttl": 45},  # 45 seconds for charts
    "status_available": {
        "data": None,
        "timestamp": 0,
        "ttl": 300,
    },  # 5 minutes for endpoint availability
}


def get_cached_data(cache_key, ttl=None):
    """Get cached data if still valid."""
    cache_entry = _status_cache.get(cache_key, {})
    if ttl is None:
        ttl = cache_entry.get("ttl", 30)

    current_time = time.time()
    if cache_entry.get("data") is not None and current_time - cache_entry.get("timestamp", 0) < ttl:
        return cache_entry["data"]
    return None


def set_cached_data(cache_key, data, ttl=None):
    """Set cached data with timestamp."""
    if cache_key not in _status_cache:
        _status_cache[cache_key] = {}

    _status_cache[cache_key]["data"] = data
    _status_cache[cache_key]["timestamp"] = time.time()
    if ttl is not None:
        _status_cache[cache_key]["ttl"] = ttl


def is_status_endpoint_available(token):
    """Check if the status endpoint is available (cached for 5 minutes)."""
    cached_availability = get_cached_data("status_available")
    if cached_availability is not None:
        return cached_availability

    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(
            f"{API_BASE}/status",
            headers=headers,
            params={"per_page": 1},
            timeout=3,  # Very short timeout for availability check
        )
        available = resp.status_code == 200
        set_cached_data("status_available", available, ttl=300)  # Cache for 5 minutes
        return available
    except Exception:
        set_cached_data("status_available", False, ttl=60)  # Cache failure for 1 minute
        return False


def get_fallback_summary(token, user_timezone="UTC"):
    """Get basic system info as fallback when status endpoint is unavailable."""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(
            f"{API_BASE}/execution",
            headers=headers,
            params={
                "per_page": 1,
                "exclude": "params,results,logs",  # Exclude all heavy fields
            },
            timeout=3,  # Short timeout
        )
        if resp.status_code == 200:
            result = resp.json()
            total = result.get("total", 0)

            # Format current time using Python timezone conversion
            utc_now = datetime.now()
            utc_time_str = utc_now.strftime("%Y-%m-%d %H:%M:%S UTC")
            local_time_str, tz_abbrev = format_local_time(
                utc_now, user_timezone, include_seconds=True
            )

            return html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.H6("System Status", className="mb-2"),
                                    html.Span(
                                        "Limited Data", className="badge bg-warning fs-6 px-3 py-2"
                                    ),
                                ],
                                className="col-md-4 text-center",
                            ),
                            html.Div(
                                [
                                    html.H6("Total Executions", className="mb-2"),
                                    html.H4(str(total), className="text-info"),
                                ],
                                className="col-md-4 text-center",
                            ),
                            html.Div(
                                [
                                    html.H6("Last Updated", className="mb-2"),
                                    html.Div(
                                        [
                                            html.Div(
                                                f"{local_time_str} {tz_abbrev}",
                                                className="fw-bold text-primary",
                                            ),
                                            html.Div(
                                                f"({utc_time_str})", className="text-muted small"
                                            ),
                                        ]
                                    ),
                                ],
                                className="col-md-4 text-center",
                            ),
                        ],
                        className="row",
                    ),
                    html.Hr(),
                    html.Small(
                        "Status endpoint unavailable. Basic system information shown.",
                        className="text-muted d-block text-center",
                    ),
                ]
            )
        else:
            return html.Div(
                [
                    html.P("System Status: Unknown", className="text-warning text-center"),
                    html.Small(
                        "Unable to connect to API services.",
                        className="text-muted d-block text-center",
                    ),
                ]
            )
    except Exception:
        return html.Div(
            [
                html.P("System Status: Offline", className="text-danger text-center"),
                html.Small("API server unavailable.", className="text-muted d-block text-center"),
            ]
        )


def register_callbacks(app):
    """Register status dashboard callbacks."""

    @app.callback(
        Output("status-summary", "children"),
        [
            Input("status-auto-refresh-interval", "n_intervals"),
            Input("refresh-status-btn", "n_clicks"),
        ],
        [
            State("token-store", "data"),
            State("active-tab-store", "data"),
            State("user-timezone-store", "data"),
            State("role-store", "data"),
        ],
        prevent_initial_call=False,  # Allow initial call to load status when tab is first accessed
    )
    def update_status_summary(
        _n_intervals, _refresh_clicks, token, active_tab, user_timezone, role
    ):
        """Update the status summary from the status endpoint with caching."""
        # Guard: Skip if not logged in (prevents execution after logout)
        if not token or role != "ADMIN":
            return no_update

        # Only update when status tab is active to avoid unnecessary API calls
        if active_tab != "status":
            return no_update

        # Get safe timezone
        safe_timezone = get_safe_timezone(user_timezone)

        # Check cache first (unless it's a manual refresh)
        ctx = callback_context
        is_manual_refresh = (
            ctx.triggered and ctx.triggered[0]["prop_id"].split(".")[0] == "refresh-status-btn"
        )

        if not is_manual_refresh:
            cached_data = get_cached_data("summary")
            if cached_data is not None:
                return cached_data

        # Quick check if status endpoint is available
        if not is_status_endpoint_available(token):
            fallback_result = get_fallback_summary(token, safe_timezone)
            set_cached_data("summary", fallback_result, ttl=20)  # Shorter cache for fallback
            return fallback_result

        headers = {"Authorization": f"Bearer {token}"}

        try:
            # Get the latest status data from the status endpoint with optimized parameters
            resp = requests.get(
                f"{API_BASE}/status",
                headers=headers,
                params={"per_page": 1, "sort": "-timestamp"},
                timeout=5,  # Reduced from 10 seconds
            )

            if resp.status_code == 200:
                status_data = resp.json().get("data", [])
                if status_data:
                    latest_status = status_data[0]
                    timestamp = latest_status.get("timestamp", "")

                    # Format the timestamp - show local time on top, UTC in parentheses
                    try:
                        if timestamp:
                            dt_utc = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                            utc_time_str = dt_utc.strftime("%Y-%m-%d %H:%M:%S UTC")

                            # Use Python to convert UTC to user's local time
                            local_time_str, tz_abbrev = format_local_time(
                                dt_utc, safe_timezone, include_seconds=True
                            )

                            formatted_date = html.Div(
                                [
                                    html.Div(
                                        f"{local_time_str} {tz_abbrev}",
                                        className="fw-bold text-primary",
                                    ),
                                    html.Div(f"({utc_time_str})", className="text-muted small"),
                                ]
                            )
                        else:
                            formatted_date = "Unknown time"
                    except Exception:
                        formatted_date = timestamp or "Unknown time"

                    # Extract all the metrics with defaults
                    metrics = {
                        "executions_active": latest_status.get("executions_active", 0),
                        "executions_ready": latest_status.get("executions_ready", 0),
                        "executions_running": latest_status.get("executions_running", 0),
                        "executions_count": latest_status.get("executions_count", 0),
                        "users_count": latest_status.get("users_count", 0),
                        "scripts_count": latest_status.get("scripts_count", 0),
                        "memory_available_percent": latest_status.get(
                            "memory_available_percent", 0
                        ),
                        # CPU and memory percentages will be calculated as 10-minute averages below
                    }

                    # Calculate 24-hour cumulative totals for finished and failed executions
                    try:
                        # Get 24-hour window data for cumulative calculations
                        now = datetime.now()
                        start_24h = now - timedelta(hours=24)

                        cumulative_resp = requests.get(
                            f"{API_BASE}/status",
                            headers=headers,
                            params={
                                "per_page": 144,  # Every 10 minutes for 24 hours
                                "start_date": start_24h.isoformat(),
                                "sort": "timestamp",
                            },
                            timeout=3,  # Short timeout for this additional request
                        )

                        executions_finished_24h = 0
                        executions_failed_24h = 0

                        if cumulative_resp.status_code == 200:
                            cumulative_data = cumulative_resp.json().get("data", [])
                            if cumulative_data:
                                # Calculate true cumulative totals by summing all 2-minute period totals
                                for entry in cumulative_data:
                                    # Each entry contains totals for a 2-minute period, so sum them all
                                    executions_finished_24h += entry.get("executions_finished", 0)
                                    executions_failed_24h += entry.get("executions_failed", 0)

                        # If cumulative calculation fails, fall back to current values
                        if cumulative_resp.status_code != 200 or not cumulative_data:
                            executions_finished_24h = latest_status.get("executions_finished", 0)
                            executions_failed_24h = latest_status.get("executions_failed", 0)

                    except Exception:
                        # Fallback to current status values if cumulative calculation fails
                        executions_finished_24h = latest_status.get("executions_finished", 0)
                        executions_failed_24h = latest_status.get("executions_failed", 0)

                    # Add 24-hour totals to metrics
                    metrics["executions_finished_24h"] = executions_finished_24h
                    metrics["executions_failed_24h"] = executions_failed_24h

                    # Calculate percentages within each execution group
                    # Active executions total (for percentage calculations within active box)
                    active_total = max(
                        1,
                        metrics["executions_active"]
                        + metrics["executions_ready"]
                        + metrics["executions_running"],
                    )

                    # Completed executions total (for percentage calculations within completed box)
                    completed_total = max(
                        1, metrics["executions_finished_24h"] + metrics["executions_failed_24h"]
                    )

                    # Calculate 10-minute averages for CPU and memory usage
                    try:
                        # Get 10-minute window data for average calculations
                        now = datetime.now()
                        start_10m = now - timedelta(minutes=10)

                        avg_resp = requests.get(
                            f"{API_BASE}/status",
                            headers=headers,
                            params={
                                "per_page": 10,  # Last 10 data points (approximately 10 minutes)
                                "start_date": start_10m.isoformat(),
                                "sort": "timestamp",
                            },
                            timeout=3,  # Short timeout for this additional request
                        )

                        cpu_usage_avg = latest_status.get("cpu_usage_percent", 0)
                        memory_used_avg = 100 - latest_status.get("memory_available_percent", 0)

                        if avg_resp.status_code == 200:
                            avg_data = avg_resp.json().get("data", [])
                            if avg_data and len(avg_data) > 1:
                                # Calculate averages from the 10-minute data
                                cpu_values = []
                                memory_values = []

                                for entry in avg_data:
                                    cpu_val = entry.get("cpu_usage_percent")
                                    memory_available = entry.get("memory_available_percent")

                                    if cpu_val is not None:
                                        cpu_values.append(cpu_val)
                                    if memory_available is not None:
                                        memory_values.append(100 - memory_available)

                                # Calculate averages if we have valid data
                                if cpu_values:
                                    cpu_usage_avg = sum(cpu_values) / len(cpu_values)
                                if memory_values:
                                    memory_used_avg = sum(memory_values) / len(memory_values)

                    except Exception:
                        # Fallback to current status values if average calculation fails
                        cpu_usage_avg = latest_status.get("cpu_usage_percent", 0)
                        memory_used_avg = 100 - latest_status.get("memory_available_percent", 0)

                    # Update metrics with averaged values
                    metrics["cpu_usage_percent"] = cpu_usage_avg
                    metrics["memory_used_percent"] = memory_used_avg

                    # Determine system health based on metrics
                    health_status = "Healthy"
                    health_color = "success"

                    if metrics["cpu_usage_percent"] > 90 or metrics["memory_used_percent"] > 90:
                        health_status = "Critical"
                        health_color = "danger"
                    elif metrics["cpu_usage_percent"] > 75 or metrics["memory_used_percent"] > 75:
                        health_status = "Warning"
                        health_color = "warning"

                    summary = html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.H6("System Health", className="mb-2"),
                                            html.Span(
                                                health_status,
                                                className=f"badge bg-{health_color} fs-6 px-3 py-2",
                                            ),
                                        ],
                                        className="col-md-3 text-center",
                                    ),
                                    html.Div(
                                        [
                                            html.H6("CPU Usage (10-min avg)", className="mb-2"),
                                            html.H4(
                                                f"{metrics['cpu_usage_percent']:.1f}%",
                                                className="text-info",
                                            ),
                                        ],
                                        className="col-md-3 text-center",
                                    ),
                                    html.Div(
                                        [
                                            html.H6("Memory Used (10-min avg)", className="mb-2"),
                                            html.H4(
                                                f"{metrics['memory_used_percent']:.1f}%",
                                                className="text-info",
                                            ),
                                        ],
                                        className="col-md-3 text-center",
                                    ),
                                    html.Div(
                                        [
                                            html.H6("Last Updated", className="mb-2"),
                                            formatted_date,
                                        ],
                                        className="col-md-3 text-center",
                                    ),
                                ],
                                className="row mb-4",
                            ),
                            html.Hr(),
                            # Execution Status Summary Cards
                            html.Div(
                                [
                                    html.H5(
                                        "Current Execution Status",
                                        className="text-center mb-4 text-muted",
                                    ),
                                    # Side-by-side execution groups
                                    html.Div(
                                        [
                                            # Active Executions Group (Left side)
                                            html.Div(
                                                [
                                                    html.Div(
                                                        [
                                                            html.H6(
                                                                "Active Executions",
                                                                className="text-center mb-3 text-primary fw-bold",
                                                            ),
                                                            html.Div(
                                                                [
                                                                    html.Div(
                                                                        [
                                                                            html.H6(
                                                                                "Pending",
                                                                                className="mb-2",
                                                                            ),
                                                                            html.H4(
                                                                                str(
                                                                                    metrics[
                                                                                        "executions_active"
                                                                                    ]
                                                                                ),
                                                                                className="text-primary",
                                                                            ),
                                                                            html.Small(
                                                                                f"{(metrics['executions_active'] / active_total * 100):.1f}%",
                                                                                className="text-muted",
                                                                            ),
                                                                        ],
                                                                        className="col-4 text-center mb-3",
                                                                    ),
                                                                    html.Div(
                                                                        [
                                                                            html.H6(
                                                                                "Ready",
                                                                                className="mb-2",
                                                                            ),
                                                                            html.H4(
                                                                                str(
                                                                                    metrics[
                                                                                        "executions_ready"
                                                                                    ]
                                                                                ),
                                                                                className="text-warning",
                                                                            ),
                                                                            html.Small(
                                                                                f"{(metrics['executions_ready'] / active_total * 100):.1f}%",
                                                                                className="text-muted",
                                                                            ),
                                                                        ],
                                                                        className="col-4 text-center mb-3",
                                                                    ),
                                                                    html.Div(
                                                                        [
                                                                            html.H6(
                                                                                "Running",
                                                                                className="mb-2",
                                                                            ),
                                                                            html.H4(
                                                                                str(
                                                                                    metrics[
                                                                                        "executions_running"
                                                                                    ]
                                                                                ),
                                                                                className="text-info",
                                                                            ),
                                                                            html.Small(
                                                                                f"{(metrics['executions_running'] / active_total * 100):.1f}%",
                                                                                className="text-muted",
                                                                            ),
                                                                        ],
                                                                        className="col-4 text-center mb-3",
                                                                    ),
                                                                ],
                                                                className="row",
                                                            ),
                                                        ],
                                                        className="p-3 rounded",
                                                        style={"border": "1px solid #dee2e6"},
                                                    ),
                                                ],
                                                className="col-md-6 mb-3",
                                            ),
                                            # Completed Executions Group (Right side)
                                            html.Div(
                                                [
                                                    html.Div(
                                                        [
                                                            html.H6(
                                                                "Completed Executions",
                                                                className="text-center mb-3 text-secondary fw-bold",
                                                            ),
                                                            html.Div(
                                                                [
                                                                    html.Div(
                                                                        [
                                                                            html.H6(
                                                                                "Finished",
                                                                                className="mb-2",
                                                                            ),
                                                                            html.H4(
                                                                                str(
                                                                                    metrics[
                                                                                        "executions_finished_24h"
                                                                                    ]
                                                                                ),
                                                                                className="text-success",
                                                                            ),
                                                                            html.Small(
                                                                                f"{(metrics['executions_finished_24h'] / completed_total * 100):.1f}%",
                                                                                className="text-muted",
                                                                            ),
                                                                        ],
                                                                        className="col-6 text-center mb-3",
                                                                    ),
                                                                    html.Div(
                                                                        [
                                                                            html.H6(
                                                                                "Failed",
                                                                                className="mb-2",
                                                                            ),
                                                                            html.H4(
                                                                                str(
                                                                                    metrics[
                                                                                        "executions_failed_24h"
                                                                                    ]
                                                                                ),
                                                                                className="text-danger",
                                                                            ),
                                                                            html.Small(
                                                                                f"{(metrics['executions_failed_24h'] / completed_total * 100):.1f}%",
                                                                                className="text-muted",
                                                                            ),
                                                                        ],
                                                                        className="col-6 text-center mb-3",
                                                                    ),
                                                                ],
                                                                className="row",
                                                            ),
                                                            html.Hr(className="mt-3 mb-2"),
                                                            html.Small(
                                                                "24-hour totals",
                                                                className="text-muted text-center d-block",
                                                            ),
                                                        ],
                                                        className="p-3 rounded",
                                                        style={"border": "1px solid #dee2e6"},
                                                    ),
                                                ],
                                                className="col-md-6 mb-3",
                                            ),
                                        ],
                                        className="row",
                                    ),
                                ],
                                className="mb-4",
                            ),
                            html.Hr(),
                            # Summary Totals Section
                            html.Div(
                                [
                                    html.H5(
                                        "Summary Totals", className="text-center mb-3 text-muted"
                                    ),
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    html.H6("Total Executions", className="mb-2"),
                                                    html.H4(
                                                        str(metrics["executions_count"]),
                                                        className="text-info",
                                                    ),
                                                ],
                                                className="col-md-4 text-center",
                                            ),
                                            html.Div(
                                                [
                                                    html.H6("Users", className="mb-2"),
                                                    html.H4(
                                                        str(metrics["users_count"]),
                                                        className="text-secondary",
                                                    ),
                                                ],
                                                className="col-md-4 text-center",
                                            ),
                                            html.Div(
                                                [
                                                    html.H6("Scripts", className="mb-2"),
                                                    html.H4(
                                                        str(metrics["scripts_count"]),
                                                        className="text-secondary",
                                                    ),
                                                ],
                                                className="col-md-4 text-center",
                                            ),
                                        ],
                                        className="row",
                                    ),
                                ],
                            ),
                        ]
                    )

                    # Cache the result for longer since we got valid data
                    set_cached_data("summary", summary, ttl=30)
                    return summary
                else:
                    result = html.Div(
                        [
                            html.P("No status data found.", className="text-muted text-center"),
                            html.Small(
                                "The system may be initializing or status monitoring is not configured.",
                                className="text-muted d-block text-center",
                            ),
                        ]
                    )
                    set_cached_data("summary", result, ttl=10)
                    return result
            else:
                # Fallback to basic system info
                fallback_result = get_fallback_summary(token)
                set_cached_data("summary", fallback_result, ttl=15)
                return fallback_result

        except requests.exceptions.Timeout:
            error_result = html.Div(
                [
                    html.P(
                        "Status update failed: Connection timeout.",
                        className="text-danger text-center",
                    ),
                    html.Small(
                        "The API server may be experiencing high load.",
                        className="text-muted d-block text-center",
                    ),
                ]
            )
            set_cached_data("summary", error_result, ttl=5)  # Short cache for errors
            return error_result
        except requests.exceptions.ConnectionError:
            error_result = html.Div(
                [
                    html.P(
                        "Status update failed: Cannot connect to API server.",
                        className="text-danger text-center",
                    ),
                    html.Small(
                        "Please check your internet connection and API server status.",
                        className="text-muted d-block text-center",
                    ),
                ]
            )
            set_cached_data("summary", error_result, ttl=5)
            return error_result
        except Exception as e:
            error_result = html.Div(
                [
                    html.P(f"Status update failed: {str(e)}", className="text-danger text-center"),
                    html.Small(
                        "An unexpected error occurred.", className="text-muted d-block text-center"
                    ),
                ]
            )
            set_cached_data("summary", error_result, ttl=5)
            return error_result

    @app.callback(
        Output("status-charts", "children"),
        [
            Input("status-auto-refresh-interval", "n_intervals"),
            Input("refresh-status-btn", "n_clicks"),
            Input("status-time-tabs-store", "data"),
        ],
        [
            State("token-store", "data"),
            State("active-tab-store", "data"),
            State("user-timezone-store", "data"),
            State("role-store", "data"),
        ],
        prevent_initial_call=False,  # Allow initial call to load status when tab is first accessed
    )
    def update_status_charts(
        _n_intervals, _refresh_clicks, time_period, token, active_tab, user_timezone, role
    ):
        """Update the status charts based on selected time period with caching."""
        # Guard: Skip if not logged in (prevents execution after logout)
        if not token or role != "ADMIN":
            return no_update

        # Only update when status tab is active to avoid unnecessary API calls
        if active_tab != "status":
            return no_update

        # Get safe timezone for chart labels
        safe_timezone = get_safe_timezone(user_timezone)

        headers = {"Authorization": f"Bearer {token}"}

        # Calculate time range based on selected period with optimized data points
        now = datetime.now()
        if time_period == "hour":
            start_time = now - timedelta(hours=1)
            title_suffix = "Last Hour"
            per_page = 30  # Reduced for faster loading
        elif time_period == "day":
            start_time = now - timedelta(days=1)
            title_suffix = "Last 24 Hours"
            per_page = 72  # Every 20 minutes for 24 hours
        elif time_period == "week":
            start_time = now - timedelta(weeks=1)
            title_suffix = "Last Week"
            per_page = 168  # Every hour for a week
        elif time_period == "month":
            start_time = now - timedelta(days=30)
            title_suffix = "Last Month"
            per_page = 360  # Every 2 hours for a month
        else:
            start_time = now - timedelta(hours=1)
            title_suffix = "Last Hour"
            per_page = 30

        try:
            # Check cache first (unless it's a manual refresh)
            ctx = callback_context
            is_manual_refresh = (
                ctx.triggered and ctx.triggered[0]["prop_id"].split(".")[0] == "refresh-status-btn"
            )

            start_time_rounded = start_time.replace(minute=0, second=0, microsecond=0)
            cache_key = f"status_chart_{time_period}_{start_time_rounded.isoformat()}"

            if not is_manual_refresh:
                cached_data = get_cached_data("charts")
                if cached_data and cache_key in cached_data:
                    return cached_data[cache_key]

            # Quick check if status endpoint is available
            if not is_status_endpoint_available(token):
                error_result = html.Div(
                    [
                        html.H5(f"System Status Trends - {title_suffix}", className="mb-3"),
                        html.Div(
                            "Status monitoring is not available. Please check admin privileges or API configuration.",
                            className="alert alert-info",
                        ),
                        html.Small(
                            "Charts require the status endpoint to be accessible.",
                            className="text-muted",
                        ),
                    ]
                )
                # Cache this result briefly to avoid repeated checks
                cached_charts = get_cached_data("charts") or {}
                cached_charts[cache_key] = error_result
                set_cached_data("charts", cached_charts, ttl=60)
                return error_result

            # Fetch status data from the status endpoint with optimized parameters
            start_time_str = start_time.isoformat()
            params = {
                "per_page": per_page,
                "start_date": start_time_str,
                "sort": "timestamp",  # Sort by timestamp ascending for proper chart ordering
            }

            resp = requests.get(
                f"{API_BASE}/status",
                headers=headers,
                params=params,
                timeout=7,  # Reduced timeout
            )

            if resp.status_code != 200:
                error_result = html.Div(
                    [
                        html.H5(f"System Status Trends - {title_suffix}", className="mb-3"),
                        html.Div(
                            f"Failed to fetch status data. Status: {resp.status_code}",
                            className="alert alert-warning",
                        ),
                        html.Small(
                            "The status endpoint may not be available or you may need admin privileges.",
                            className="text-muted",
                        ),
                    ]
                )
                return error_result

            result = resp.json()
            status_logs = result.get("data", [])

            if not status_logs:
                return html.Div(
                    [
                        html.H5(f"System Status Trends - {title_suffix}", className="mb-3"),
                        html.P(
                            "No status data found for the selected time period.",
                            className="text-muted",
                        ),
                        html.Small(
                            "Status monitoring may not be configured or running.",
                            className="text-muted",
                        ),
                    ]
                )

            # Convert to DataFrame for easier analysis with optimized data processing
            df_data = []
            for log in status_logs:
                timestamp = log.get("timestamp")
                if timestamp:
                    try:
                        # Keep timestamps as UTC datetime objects for plotting
                        dt_utc = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                        df_data.append(
                            {
                                "timestamp": dt_utc,
                                "executions_active": log.get("executions_active", 0),
                                "executions_ready": log.get("executions_ready", 0),
                                "executions_running": log.get("executions_running", 0),
                                "executions_finished": log.get("executions_finished", 0),
                                "executions_failed": log.get("executions_failed", 0),
                                "executions_count": log.get("executions_count", 0),
                                "users_count": log.get("users_count", 0),
                                "scripts_count": log.get("scripts_count", 0),
                                "memory_available_percent": log.get("memory_available_percent", 0),
                                "memory_used_percent": 100 - log.get("memory_available_percent", 0),
                                "cpu_usage_percent": log.get("cpu_usage_percent", 0),
                            }
                        )
                    except Exception:
                        continue

            if not df_data:
                return html.Div(
                    [
                        html.H5(f"System Status Trends - {title_suffix}", className="mb-3"),
                        html.P(
                            "No valid status data found for the selected time period.",
                            className="text-muted",
                        ),
                    ]
                )

            df = pd.DataFrame(df_data)

            # Create charts with optimized rendering
            charts = []

            # Calculate cumulative totals for finished and failed executions
            if len(df) > 0:
                # Since each data point represents totals for a 2-minute period,
                # calculate cumulative sums by adding all the period totals
                df = df.sort_values("timestamp")  # Ensure proper ordering

                # Calculate running cumulative sums by adding each 2-minute period total
                df["executions_finished_cumulative"] = df["executions_finished"].cumsum()
                df["executions_failed_cumulative"] = df["executions_failed"].cumsum()
            else:
                # Initialize empty cumulative columns for empty DataFrame
                df = pd.DataFrame(
                    {
                        "timestamp": [],
                        "executions_finished_cumulative": [],
                        "executions_failed_cumulative": [],
                    }
                )

            # 1. Active Execution Status Chart (Pending, Ready, Running)
            active_fig = go.Figure()

            # Add active execution traces only
            active_fig.add_trace(
                go.Scatter(
                    x=df["timestamp"],
                    y=df["executions_active"],
                    name="Pending",
                    line={"color": "#17a2b8"},
                    mode="lines",
                )
            )

            active_fig.add_trace(
                go.Scatter(
                    x=df["timestamp"],
                    y=df["executions_ready"],
                    name="Ready",
                    line={"color": "#ffc107"},
                    mode="lines",
                )
            )

            active_fig.add_trace(
                go.Scatter(
                    x=df["timestamp"],
                    y=df["executions_running"],
                    name="Running",
                    line={"color": "#28a745"},
                    mode="lines",
                )
            )

            # Update layout for active executions
            active_fig.update_layout(
                title=f"Active Execution Counts - {title_suffix}",
                height=300,
                showlegend=True,
                xaxis_title=get_chart_axis_label(safe_timezone, "Time"),
                yaxis_title="Active Execution Count",
                hovermode="x unified",
                margin={"l": 40, "r": 40, "t": 40, "b": 40},
                xaxis={"type": "date", "tickformat": "%H:%M\n%m/%d"},
            )

            charts.append(
                html.Div(
                    [
                        html.H6("Active Executions Over Time"),
                        dcc.Graph(
                            figure=active_fig,
                            config={"displayModeBar": False, "responsive": True},
                        ),
                    ],
                    className="mb-3",
                )
            )

            # 2. Completed Execution Cumulative Chart (Finished and Failed)
            completed_fig = go.Figure()

            completed_fig.add_trace(
                go.Scatter(
                    x=df["timestamp"],
                    y=df["executions_finished_cumulative"],
                    name="Finished (Cumulative)",
                    line={"color": "#28a745"},
                    mode="lines",
                    fill=None,
                )
            )

            completed_fig.add_trace(
                go.Scatter(
                    x=df["timestamp"],
                    y=df["executions_failed_cumulative"],
                    name="Failed (Cumulative)",
                    line={"color": "#dc3545"},
                    mode="lines",
                    fill=None,
                )
            )

            # Update layout for completed executions
            completed_fig.update_layout(
                title=f"Completed Executions (Cumulative) - {title_suffix}",
                height=300,
                showlegend=True,
                xaxis_title=get_chart_axis_label(safe_timezone, "Time"),
                yaxis_title="Cumulative Count",
                hovermode="x unified",
                margin={"l": 40, "r": 40, "t": 40, "b": 40},
                xaxis={"type": "date", "tickformat": "%H:%M\n%m/%d"},
                yaxis={"rangemode": "tozero"},  # Start y-axis from zero
            )

            charts.append(
                html.Div(
                    [
                        html.H6("Completed Executions Over Time (Cumulative)"),
                        dcc.Graph(
                            figure=completed_fig,
                            config={"displayModeBar": False, "responsive": True},
                        ),
                    ],
                    className="mb-3",
                )
            )

            # 3. System Resource Usage Chart (only if data exists)
            if df["cpu_usage_percent"].max() > 0 or df["memory_used_percent"].max() > 0:
                resource_fig = px.line(
                    df,
                    x="timestamp",
                    y=["cpu_usage_percent", "memory_used_percent"],
                    title=f"System Resource Usage - {title_suffix}",
                    labels={"timestamp": "Time", "value": "Percentage", "variable": "Resource"},
                )

                resource_fig.update_layout(
                    height=300,
                    showlegend=True,
                    xaxis_title=get_chart_axis_label(safe_timezone, "Time"),
                    yaxis_title="Percentage (%)",
                    hovermode="x unified",
                    margin={"l": 40, "r": 40, "t": 40, "b": 40},
                    yaxis={"range": [0, 100]},
                    xaxis={"type": "date", "tickformat": "%H:%M\n%m/%d"},
                )

                # Color mapping for resources
                resource_colors = {
                    "cpu_usage_percent": "#dc3545",
                    "memory_used_percent": "#17a2b8",
                }

                # Update trace colors
                for trace in resource_fig.data:
                    var_name = trace.name
                    if var_name in resource_colors:
                        trace.line.color = resource_colors[var_name]

                charts.append(
                    html.Div(
                        [
                            html.H6("System Resource Usage"),
                            dcc.Graph(
                                figure=resource_fig,
                                config={"displayModeBar": False, "responsive": True},
                            ),
                        ],
                        className="mb-3",
                    )
                )

            # 4. Users and Scripts Chart with dual y-axes (only for longer time periods to reduce clutter)
            if time_period in ["week", "month"] and (
                df["users_count"].max() > 0 or df["scripts_count"].max() > 0
            ):
                # Create subplot with secondary y-axis for Users and Scripts
                entities_fig = make_subplots(specs=[[{"secondary_y": True}]])

                # Add users count on left y-axis
                entities_fig.add_trace(
                    go.Scatter(
                        x=df["timestamp"],
                        y=df["users_count"],
                        name="users_count",
                        line={"color": "#28a745"},
                        mode="lines",
                    ),
                    secondary_y=False,
                )

                # Add scripts count on right y-axis
                entities_fig.add_trace(
                    go.Scatter(
                        x=df["timestamp"],
                        y=df["scripts_count"],
                        name="scripts_count",
                        line={"color": "#fd7e14"},
                        mode="lines",
                    ),
                    secondary_y=True,
                )

                # Set y-axes titles
                entities_fig.update_yaxes(title_text="Users Count", secondary_y=False)
                entities_fig.update_yaxes(title_text="Scripts Count", secondary_y=True)

                # Update layout
                entities_fig.update_layout(
                    title=f"Users and Scripts Count - {title_suffix}",
                    height=300,
                    showlegend=True,
                    xaxis_title=get_chart_axis_label(safe_timezone, "Time"),
                    hovermode="x unified",
                    margin={
                        "l": 40,
                        "r": 60,
                        "t": 40,
                        "b": 40,
                    },  # More right margin for secondary y-axis
                    xaxis={"type": "date", "tickformat": "%H:%M\n%m/%d"},
                )

                charts.append(
                    html.Div(
                        [
                            html.H6("Users and Scripts Count"),
                            dcc.Graph(
                                figure=entities_fig,
                                config={"displayModeBar": False, "responsive": True},
                            ),
                        ],
                        className="mb-3",
                    )
                )

            chart_result = html.Div(
                [
                    html.H5(f"System Status Trends - {title_suffix}", className="mb-3"),
                ]
                + charts
            )

            # Cache the result with longer TTL for successful data
            cached_charts = get_cached_data("charts") or {}
            cached_charts[cache_key] = chart_result
            set_cached_data("charts", cached_charts, ttl=60)

            return chart_result

        except requests.exceptions.Timeout:
            return html.Div(
                [
                    html.H5(f"System Status Trends - {title_suffix}", className="mb-3"),
                    html.Div(
                        "Chart update failed: Connection timeout.", className="alert alert-warning"
                    ),
                    html.Small(
                        "Try reducing the time period or check API performance.",
                        className="text-muted",
                    ),
                ]
            )
        except requests.exceptions.ConnectionError:
            return html.Div(
                [
                    html.H5(f"System Status Trends - {title_suffix}", className="mb-3"),
                    html.Div(
                        "Chart update failed: Cannot connect to API server.",
                        className="alert alert-danger",
                    ),
                ]
            )
        except Exception as e:
            return html.Div(
                [
                    html.H5(f"System Status Trends - {title_suffix}", className="mb-3"),
                    html.Div(f"Chart update failed: {str(e)}", className="alert alert-danger"),
                ]
            )

    @app.callback(
        Output("status-countdown", "children"),
        [
            Input("status-countdown-interval", "n_intervals"),
            Input("refresh-status-btn", "n_clicks"),
        ],
        State("active-tab-store", "data"),
        prevent_initial_call=True,
    )
    def update_status_countdown(n_intervals, _refresh_clicks, active_tab):
        """Update the status auto-refresh countdown."""
        # Guard: Skip if required components are not present (e.g., after logout)
        if active_tab is None:
            return no_update

        if active_tab != "status":
            return "60s"

        # Check if refresh button was clicked to reset countdown
        ctx = callback_context
        if ctx.triggered and ctx.triggered[0]["prop_id"].split(".")[0] == "refresh-status-btn":
            return "60s"  # Reset to full interval

        # Calculate remaining seconds (60 second cycle to match STATUS_REFRESH_INTERVAL)
        remaining = 60 - (n_intervals % 60)
        return f"{remaining}s"

    @app.callback(
        [
            Output("status-tab-hour", "className"),
            Output("status-tab-day", "className"),
            Output("status-tab-week", "className"),
            Output("status-tab-month", "className"),
            Output("status-time-tabs-store", "data"),
        ],
        [
            Input("status-tab-hour", "n_clicks"),
            Input("status-tab-day", "n_clicks"),
            Input("status-tab-week", "n_clicks"),
            Input("status-tab-month", "n_clicks"),
        ],
        prevent_initial_call=True,
    )
    def switch_status_time_tabs(_hour_clicks, _day_clicks, _week_clicks, _month_clicks):
        """Handle tab switching for status time period tabs."""
        ctx = callback_context
        if not ctx.triggered:
            return "nav-link active", "nav-link", "nav-link", "nav-link", "hour"

        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

        # Define tab mapping
        tab_map = {
            "status-tab-hour": ("hour", ("nav-link active", "nav-link", "nav-link", "nav-link")),
            "status-tab-day": ("day", ("nav-link", "nav-link active", "nav-link", "nav-link")),
            "status-tab-week": ("week", ("nav-link", "nav-link", "nav-link active", "nav-link")),
            "status-tab-month": ("month", ("nav-link", "nav-link", "nav-link", "nav-link active")),
        }

        active_tab, classes = tab_map.get(
            trigger_id, ("hour", ("nav-link active", "nav-link", "nav-link", "nav-link"))
        )

        return classes[0], classes[1], classes[2], classes[3], active_tab
