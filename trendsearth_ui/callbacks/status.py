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
    "summary": {"data": None, "timestamp": 0, "ttl": 30},  # 30 seconds
    "charts": {"data": {}, "timestamp": 0, "ttl": 60},  # 60 seconds for charts
}


def get_cached_data(cache_key, ttl=None):
    """Get cached data if still valid."""
    cache_entry = _status_cache.get(cache_key, {})
    if ttl is None:
        ttl = cache_entry.get("ttl", 30)
    
    current_time = time.time()
    if (cache_entry.get("data") is not None and 
        current_time - cache_entry.get("timestamp", 0) < ttl):
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
        prevent_initial_call=True,
    )
    def update_status_summary(_n_intervals, _refresh_clicks, token, active_tab):
        """Update the status summary from the most recent log entry with caching."""
        # Only update when status tab is active to avoid unnecessary API calls
        if active_tab != "status" or not token:
            return no_update

        # Check cache first (unless it's a manual refresh)
        ctx = callback_context
        is_manual_refresh = (ctx.triggered and 
                           ctx.triggered[0]["prop_id"].split(".")[0] == "refresh-status-btn")
        
        if not is_manual_refresh:
            cached_data = get_cached_data("summary")
            if cached_data is not None:
                return cached_data

        headers = {"Authorization": f"Bearer {token}"}

        try:
            # Try to get the most recent status log entry
            # This assumes there might be a status endpoint or we can get it from logs
            resp = requests.get(
                f"{API_BASE}/log",
                headers=headers,
                params={"per_page": 1, "sort": "-register_date"},
                timeout=5,  # Reduced timeout for faster response
            )

            if resp.status_code == 200:
                logs = resp.json().get("data", [])
                if logs:
                    latest_log = logs[0]
                    register_date = latest_log.get("register_date", "")
                    level = latest_log.get("level", "INFO")
                    text = latest_log.get("text", "No status information available")

                    # Format the date
                    try:
                        if register_date:
                            dt = datetime.fromisoformat(register_date.replace("Z", "+00:00"))
                            formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                        else:
                            formatted_date = "Unknown time"
                    except Exception:
                        formatted_date = register_date or "Unknown time"

                    # Create status display with appropriate color based on level
                    color = {
                        "ERROR": "danger",
                        "WARNING": "warning",
                        "INFO": "info",
                        "DEBUG": "secondary",
                    }.get(level, "secondary")

                    summary = html.Div(
                        [
                            html.P(
                                [html.Strong("Last Update: "), formatted_date], className="mb-2"
                            ),
                            html.P(
                                [
                                    html.Span("Level: ", className="me-2"),
                                    html.Span(level, className=f"badge bg-{color}"),
                                ],
                                className="mb-2",
                            ),
                            html.P([html.Strong("Status: "), text], className="mb-0"),
                        ]
                    )

                    # Cache the result
                    set_cached_data("summary", summary)
                    return summary
                else:
                    result = "No status logs found."
                    set_cached_data("summary", result)
                    return result
            else:
                # Fallback: try to get basic system info from executions endpoint
                resp = requests.get(
                    f"{API_BASE}/execution",
                    headers=headers,
                    params={
                        "per_page": 1,
                        "exclude": "params,results",
                        "include": "script_name,user_name,user_email,duration",
                    },
                    timeout=5,
                )
                if resp.status_code == 200:
                    result = resp.json()
                    total = result.get("total", 0)
                    fallback_result = html.Div(
                        [
                            html.P([html.Strong("System Status: "), "Online"], className="mb-2"),
                            html.P(
                                [html.Strong("Total Executions: "), str(total)], className="mb-0"
                            ),
                        ]
                    )
                    set_cached_data("summary", fallback_result)
                    return fallback_result
                else:
                    error_result = f"Failed to fetch status information. API responded with status {resp.status_code}."
                    set_cached_data("summary", error_result, ttl=10)  # Cache errors for shorter time
                    return error_result

        except requests.exceptions.Timeout:
            error_result = "Status update failed: Connection timeout."
            set_cached_data("summary", error_result, ttl=10)
            return error_result
        except requests.exceptions.ConnectionError:
            error_result = "Status update failed: Cannot connect to API server."
            set_cached_data("summary", error_result, ttl=10)
            return error_result
        except Exception as e:
            error_result = f"Status update failed: {str(e)}"
            set_cached_data("summary", error_result, ttl=10)
            return error_result

    @app.callback(
        Output("status-charts", "children"),
        [
            Input("status-auto-refresh-interval", "n_intervals"),
            Input("refresh-status-btn", "n_clicks"),
            Input("status-time-tabs", "active_tab"),
        ],
        [
            State("token-store", "data"),
            State("active-tab-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def update_status_charts(_n_intervals, _refresh_clicks, time_period, token, active_tab):
        """Update the status charts based on selected time period with caching."""
        # Only update when status tab is active to avoid unnecessary API calls
        if active_tab != "status" or not token:
            return no_update

        headers = {"Authorization": f"Bearer {token}"}

        # Calculate time range based on selected period
        now = datetime.now()
        if time_period == "hour":
            start_time = now - timedelta(hours=1)
            title_suffix = "Last Hour"
            per_page = 50  # Reduced for better performance
        elif time_period == "day":
            start_time = now - timedelta(days=1)
            title_suffix = "Last 24 Hours"
            per_page = 100  # Moderate limit
        elif time_period == "week":
            start_time = now - timedelta(weeks=1)
            title_suffix = "Last Week"
            per_page = 200  # Reduced from 1000 for better performance
        else:
            start_time = now - timedelta(hours=1)
            title_suffix = "Last Hour"
            per_page = 50

        try:
            # Create cache key based on time period and rounded start time for better caching
            cache_key = f"charts_{time_period}_{int(start_time.timestamp() // 300)}"  # 5-minute buckets
            
            # Check cache first (unless it's a manual refresh)
            ctx = callback_context
            is_manual_refresh = (ctx.triggered and 
                               ctx.triggered[0]["prop_id"].split(".")[0] == "refresh-status-btn")
            
            if not is_manual_refresh:
                cached_data = get_cached_data("charts")
                if cached_data and cache_key in cached_data:
                    return cached_data[cache_key]
            start_time_rounded = start_time.replace(second=0, microsecond=0)
            cache_key = f"status_chart_{time_period}_{start_time_rounded.isoformat()}"
            
            # Fetch execution data for the time period - only get essential fields
            start_time_str = start_time.isoformat()
            params = {
                "per_page": per_page,
                "start_date_gte": start_time_str,
                "exclude": "params,results,logs",  # Exclude all heavy fields including logs
                "fields": "status,start_date,id",  # Only get essential fields for chart
            }

            resp = requests.get(
                f"{API_BASE}/execution",
                headers=headers,
                params=params,
                timeout=5,  # Reduced timeout for faster response
            )

            if resp.status_code != 200:
                error_result = html.Div(
                    [
                        html.H5(f"Execution Status Trends - {title_suffix}", className="mb-3"),
                        html.Div(
                            f"Failed to fetch execution data. Status: {resp.status_code}",
                            className="alert alert-warning",
                        ),
                    ]
                )
                return error_result

            result = resp.json()
            executions = result.get("data", [])
            
            if executions is None:
                return html.Div(
                    [
                        html.H5(f"Execution Status Trends - {title_suffix}", className="mb-3"),
                        html.Div(
                            "Failed to fetch execution data.",
                            className="alert alert-warning",
                        ),
                    ]
                )

            if not executions:
                return html.Div(
                    [
                        html.H5(f"Execution Status Trends - {title_suffix}", className="mb-3"),
                        html.P(
                            "No execution data found for the selected time period.",
                            className="text-muted",
                        ),
                    ]
                )

            # Convert to DataFrame for easier analysis
            df_data = []
            for execution in executions:
                start_date = execution.get("start_date")
                status = execution.get("status", "UNKNOWN")

                if start_date:
                    try:
                        # Parse the date
                        dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                        df_data.append({"datetime": dt, "status": status, "count": 1})
                    except Exception:
                        continue

            if not df_data:
                return html.Div(
                    [
                        html.H5(f"Execution Status Trends - {title_suffix}", className="mb-3"),
                        html.P(
                            "No valid execution data found for the selected time period.",
                            className="text-muted",
                        ),
                    ]
                )

            df = pd.DataFrame(df_data)

            # Create time buckets
            if time_period == "hour":
                df["time_bucket"] = df["datetime"].dt.floor("5min")
            elif time_period == "day":
                df["time_bucket"] = df["datetime"].dt.floor("1H")
            else:  # week
                df["time_bucket"] = df["datetime"].dt.floor("6H")

            # Group by time bucket and status
            status_counts = df.groupby(["time_bucket", "status"]).size().reset_index(name="count")

            # Create the chart
            fig = px.line(
                status_counts,
                x="time_bucket",
                y="count",
                color="status",
                title=f"Execution Counts by Status - {title_suffix}",
                labels={"time_bucket": "Time", "count": "Number of Executions", "status": "Status"},
            )

            # Customize the chart
            fig.update_layout(
                height=400,
                showlegend=True,
                xaxis_title="Time",
                yaxis_title="Number of Executions",
                hovermode="x unified",
                margin={"l": 50, "r": 50, "t": 50, "b": 50},  # Optimize margins
            )

            # Color mapping for status
            status_colors = {
                "RUNNING": "#17a2b8",  # info blue
                "FINISHED": "#28a745",  # success green
                "FAILED": "#dc3545",  # danger red
                "PENDING": "#ffc107",  # warning yellow
                "CANCELLED": "#6c757d",  # secondary gray
            }

            # Update trace colors
            for trace in fig.data:
                status = trace.name
                if status in status_colors:
                    trace.line.color = status_colors[status]

            # Create summary statistics
            total_executions = len(executions)
            status_summary = df["status"].value_counts().to_dict()

            summary_cards = []
            for status, count in status_summary.items():
                percentage = (count / total_executions) * 100
                color_class = {
                    "RUNNING": "info",
                    "FINISHED": "success",
                    "FAILED": "danger",
                    "PENDING": "warning",
                    "CANCELLED": "secondary",
                }.get(status, "secondary")

                summary_cards.append(
                    html.Div(
                        [
                            html.H6(status, className="card-title"),
                            html.H4(str(count), className=f"text-{color_class}"),
                            html.Small(f"{percentage:.1f}%", className="text-muted"),
                        ],
                        className=f"card border-{color_class} text-center p-3 me-2 mb-2",
                        style={"minWidth": "120px"},
                    )
                )

            chart_result = html.Div(
                [
                    html.H5(f"Execution Status Trends - {title_suffix}", className="mb-3"),
                    html.Div(summary_cards, className="d-flex flex-wrap mb-4"),
                    dcc.Graph(
                        figure=fig,
                        config={
                            "displayModeBar": False,  # Hide toolbar for cleaner look
                            "responsive": True,
                        },
                    ),
                ]
            )

            # Cache the result
            cached_charts = get_cached_data("charts") or {}
            cached_charts[cache_key] = chart_result
            set_cached_data("charts", cached_charts)
            
            return chart_result

        except requests.exceptions.Timeout:
            return html.Div(
                [
                    html.H5(f"Execution Status Trends - {title_suffix}", className="mb-3"),
                    html.Div(
                        "Chart update failed: Connection timeout.", className="alert alert-warning"
                    ),
                ]
            )
        except requests.exceptions.ConnectionError:
            return html.Div(
                [
                    html.H5(f"Execution Status Trends - {title_suffix}", className="mb-3"),
                    html.Div(
                        "Chart update failed: Cannot connect to API server.",
                        className="alert alert-danger",
                    ),
                ]
            )
        except Exception as e:
            return html.Div(
                [
                    html.H5(f"Execution Status Trends - {title_suffix}", className="mb-3"),
                    html.Div(f"Chart update failed: {str(e)}", className="alert alert-danger"),
                ]
            )

    @app.callback(
        Output("status-countdown", "children"),
        Input("status-countdown-interval", "n_intervals"),
        State("active-tab-store", "data"),
        prevent_initial_call=True,
    )
    def update_status_countdown(n_intervals, active_tab):
        """Update the status auto-refresh countdown."""
        if active_tab != "status":
            return "60s"

        # Calculate remaining seconds (60 second cycle)
        remaining = 60 - (n_intervals % 60)
        return f"{remaining}s"
