"""Status dashboard callbacks."""

from datetime import datetime, timedelta
import time

from dash import Input, Output, State, callback_context, dcc, html, no_update
import pandas as pd
import plotly.express as px
import requests

from ..config import API_BASE

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


def get_fallback_summary(token):
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
                                    html.Small(
                                        datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
                                        className="text-muted",
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
        ],
    )
    def update_status_summary(_n_intervals, _refresh_clicks, token, active_tab):
        """Update the status summary from the status endpoint with caching."""
        # Only update when status tab is active to avoid unnecessary API calls
        if active_tab != "status" or not token:
            return no_update

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
            fallback_result = get_fallback_summary(token)
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

                    # Format the timestamp
                    try:
                        if timestamp:
                            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                            formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                        else:
                            formatted_date = "Unknown time"
                    except Exception:
                        formatted_date = timestamp or "Unknown time"

                    # Extract all the metrics with defaults
                    metrics = {
                        "executions_active": latest_status.get("executions_active", 0),
                        "executions_ready": latest_status.get("executions_ready", 0),
                        "executions_running": latest_status.get("executions_running", 0),
                        "executions_finished": latest_status.get("executions_finished", 0),
                        "users_count": latest_status.get("users_count", 0),
                        "scripts_count": latest_status.get("scripts_count", 0),
                        "memory_available_percent": latest_status.get(
                            "memory_available_percent", 0
                        ),
                        "cpu_usage_percent": latest_status.get("cpu_usage_percent", 0),
                    }

                    # Determine system health based on metrics
                    health_status = "Healthy"
                    health_color = "success"

                    if (
                        metrics["cpu_usage_percent"] > 90
                        or metrics["memory_available_percent"] < 10
                    ):
                        health_status = "Critical"
                        health_color = "danger"
                    elif (
                        metrics["cpu_usage_percent"] > 75
                        or metrics["memory_available_percent"] < 25
                    ):
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
                                            html.H6("CPU Usage", className="mb-2"),
                                            html.H4(
                                                f"{metrics['cpu_usage_percent']:.1f}%",
                                                className="text-info",
                                            ),
                                        ],
                                        className="col-md-3 text-center",
                                    ),
                                    html.Div(
                                        [
                                            html.H6("Memory Available", className="mb-2"),
                                            html.H4(
                                                f"{metrics['memory_available_percent']:.1f}%",
                                                className="text-info",
                                            ),
                                        ],
                                        className="col-md-3 text-center",
                                    ),
                                    html.Div(
                                        [
                                            html.H6("Last Updated", className="mb-2"),
                                            html.Small(formatted_date, className="text-muted"),
                                        ],
                                        className="col-md-3 text-center",
                                    ),
                                ],
                                className="row mb-4",
                            ),
                            html.Hr(),
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.H6("Active", className="mb-2"),
                                            html.H4(
                                                str(metrics["executions_active"]),
                                                className="text-primary",
                                            ),
                                        ],
                                        className="col-md-2 text-center",
                                    ),
                                    html.Div(
                                        [
                                            html.H6("Ready", className="mb-2"),
                                            html.H4(
                                                str(metrics["executions_ready"]),
                                                className="text-warning",
                                            ),
                                        ],
                                        className="col-md-2 text-center",
                                    ),
                                    html.Div(
                                        [
                                            html.H6("Running", className="mb-2"),
                                            html.H4(
                                                str(metrics["executions_running"]),
                                                className="text-info",
                                            ),
                                        ],
                                        className="col-md-2 text-center",
                                    ),
                                    html.Div(
                                        [
                                            html.H6("Finished", className="mb-2"),
                                            html.H4(
                                                str(metrics["executions_finished"]),
                                                className="text-success",
                                            ),
                                        ],
                                        className="col-md-2 text-center",
                                    ),
                                    html.Div(
                                        [
                                            html.H6("Users", className="mb-2"),
                                            html.H4(
                                                str(metrics["users_count"]),
                                                className="text-secondary",
                                            ),
                                        ],
                                        className="col-md-2 text-center",
                                    ),
                                    html.Div(
                                        [
                                            html.H6("Scripts", className="mb-2"),
                                            html.H4(
                                                str(metrics["scripts_count"]),
                                                className="text-secondary",
                                            ),
                                        ],
                                        className="col-md-2 text-center",
                                    ),
                                ],
                                className="row",
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
        ],
    )
    def update_status_charts(_n_intervals, _refresh_clicks, time_period, token, active_tab):
        """Update the status charts based on selected time period with caching."""
        # Only update when status tab is active to avoid unnecessary API calls
        if active_tab != "status" or not token:
            return no_update

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
                        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                        df_data.append(
                            {
                                "timestamp": dt,
                                "executions_active": log.get("executions_active", 0),
                                "executions_ready": log.get("executions_ready", 0),
                                "executions_running": log.get("executions_running", 0),
                                "executions_finished": log.get("executions_finished", 0),
                                "users_count": log.get("users_count", 0),
                                "scripts_count": log.get("scripts_count", 0),
                                "memory_available_percent": log.get("memory_available_percent", 0),
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

            # 1. Execution Status Chart (always show this)
            execution_fig = px.line(
                df,
                x="timestamp",
                y=[
                    "executions_active",
                    "executions_ready",
                    "executions_running",
                    "executions_finished",
                ],
                title=f"Execution Counts - {title_suffix}",
                labels={"timestamp": "Time", "value": "Count", "variable": "Status"},
            )

            execution_fig.update_layout(
                height=300,  # Reduced height for faster rendering
                showlegend=True,
                xaxis_title="Time",
                yaxis_title="Count",
                hovermode="x unified",
                margin={"l": 40, "r": 40, "t": 40, "b": 40},  # Smaller margins
            )

            # Color mapping for execution statuses
            execution_colors = {
                "executions_active": "#17a2b8",
                "executions_ready": "#ffc107",
                "executions_running": "#28a745",
                "executions_finished": "#6c757d",
            }

            # Update trace colors
            for trace in execution_fig.data:
                var_name = trace.name
                if var_name in execution_colors:
                    trace.line.color = execution_colors[var_name]

            charts.append(
                html.Div(
                    [
                        html.H6("Execution Status Over Time"),
                        dcc.Graph(
                            figure=execution_fig,
                            config={"displayModeBar": False, "responsive": True},
                        ),
                    ],
                    className="mb-3",
                )
            )

            # 2. System Resource Usage Chart (only if data exists)
            if df["cpu_usage_percent"].max() > 0 or df["memory_available_percent"].max() > 0:
                resource_fig = px.line(
                    df,
                    x="timestamp",
                    y=["cpu_usage_percent", "memory_available_percent"],
                    title=f"System Resource Usage - {title_suffix}",
                    labels={"timestamp": "Time", "value": "Percentage", "variable": "Resource"},
                )

                resource_fig.update_layout(
                    height=300,
                    showlegend=True,
                    xaxis_title="Time",
                    yaxis_title="Percentage (%)",
                    hovermode="x unified",
                    margin={"l": 40, "r": 40, "t": 40, "b": 40},
                    yaxis={"range": [0, 100]},
                )

                # Color mapping for resources
                resource_colors = {
                    "cpu_usage_percent": "#dc3545",
                    "memory_available_percent": "#17a2b8",
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

            # 3. Users and Scripts Chart (only for longer time periods to reduce clutter)
            if time_period in ["week", "month"] and (
                df["users_count"].max() > 0 or df["scripts_count"].max() > 0
            ):
                entities_fig = px.line(
                    df,
                    x="timestamp",
                    y=["users_count", "scripts_count"],
                    title=f"Users and Scripts Count - {title_suffix}",
                    labels={"timestamp": "Time", "value": "Count", "variable": "Entity Type"},
                )

                entities_fig.update_layout(
                    height=300,
                    showlegend=True,
                    xaxis_title="Time",
                    yaxis_title="Count",
                    hovermode="x unified",
                    margin={"l": 40, "r": 40, "t": 40, "b": 40},
                )

                # Color mapping for entities
                entity_colors = {
                    "users_count": "#28a745",
                    "scripts_count": "#fd7e14",
                }

                # Update trace colors
                for trace in entities_fig.data:
                    var_name = trace.name
                    if var_name in entity_colors:
                        trace.line.color = entity_colors[var_name]

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

            # Create summary statistics from the most recent data point
            latest_data = df.iloc[-1] if len(df) > 0 else None
            if latest_data is not None:
                total_executions = (
                    latest_data["executions_active"]
                    + latest_data["executions_ready"]
                    + latest_data["executions_running"]
                    + latest_data["executions_finished"]
                )

                summary_cards = []

                # Execution summary
                execution_summary = {
                    "Active": latest_data["executions_active"],
                    "Ready": latest_data["executions_ready"],
                    "Running": latest_data["executions_running"],
                    "Finished": latest_data["executions_finished"],
                }

                for status, count in execution_summary.items():
                    percentage = (count / total_executions) * 100 if total_executions > 0 else 0

                    color_class = {
                        "Active": "info",
                        "Ready": "warning",
                        "Running": "success",
                        "Finished": "secondary",
                    }.get(status, "secondary")

                    summary_cards.append(
                        html.Div(
                            [
                                html.H6(status, className="card-title mb-1"),
                                html.H5(str(int(count)), className=f"text-{color_class} mb-1"),
                                html.Small(f"{percentage:.1f}%", className="text-muted"),
                            ],
                            className=f"card border-{color_class} text-center p-2 me-2 mb-2",
                            style={"minWidth": "100px"},
                        )
                    )

                charts.insert(
                    0,
                    html.Div(
                        [
                            html.H6("Current Status Summary"),
                            html.Div(summary_cards, className="d-flex flex-wrap mb-3"),
                        ]
                    ),
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
