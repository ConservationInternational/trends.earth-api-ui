"""Status dashboard callbacks."""

from datetime import datetime, timedelta, timezone
import logging

from cachetools import TTLCache
from dash import Input, Output, State, callback_context, dcc, html, no_update
import pandas as pd
import plotly.graph_objects as go
import requests

from ..config import get_api_base
from ..utils.stats_utils import (
    fetch_dashboard_stats,
    fetch_execution_stats,
    fetch_user_stats,
)
from ..utils.stats_visualizations import (
    create_dashboard_summary_cards,
    create_execution_statistics_chart,
    create_user_geographic_map,
    create_user_statistics_chart,
)
from ..utils.status_helpers import (
    fetch_deployment_info,
    fetch_swarm_info,
    get_fallback_summary,
    is_status_endpoint_available,
)
from ..utils.timezone_utils import (
    convert_utc_to_local,
    format_local_time,
    get_chart_axis_label,
    get_safe_timezone,
)

logger = logging.getLogger(__name__)
_status_cache = TTLCache(maxsize=10, ttl=60)
_stats_cache = TTLCache(maxsize=10, ttl=300)


def get_cached_data(key):
    """Get data from cache."""
    return _status_cache.get(key)


def set_cached_data(key, value):
    """Set data in cache."""
    _status_cache[key] = value


def register_callbacks(app):
    """Register status dashboard callbacks."""

    @app.callback(
        [
            Output("status-summary", "children"),
            Output("deployment-info-summary", "children"),
            Output("swarm-info-summary", "children"),
            Output("swarm-status-title", "children"),
        ],
        [
            Input("status-auto-refresh-interval", "n_intervals"),
            Input("refresh-status-btn", "n_clicks"),
        ],
        [
            State("token-store", "data"),
            State("active-tab-store", "data"),
            State("user-timezone-store", "data"),
            State("role-store", "data"),
            State("api-environment-store", "data"),
        ],
        prevent_initial_call=False,  # Allow initial call to load status when tab is first accessed
    )
    def update_status_summary(
        _n_intervals, _refresh_clicks, token, active_tab, user_timezone, role, api_environment
    ):
        """Update the status summary from the status endpoint with caching."""
        # Guard: Skip if not logged in (prevents execution after logout)
        if not token or role not in ["ADMIN", "SUPERADMIN"]:
            return no_update, no_update, no_update, no_update

        # Only update when status tab is active to avoid unnecessary API calls
        if active_tab != "status":
            return no_update, no_update, no_update, no_update

        # Get safe timezone
        safe_timezone = get_safe_timezone(user_timezone)

        # Check cache first (unless it's a manual refresh)
        ctx = callback_context
        is_manual_refresh = (
            ctx.triggered and ctx.triggered[0]["prop_id"].split(".")[0] == "refresh-status-btn"
        )

        if not is_manual_refresh:
            cached_summary = get_cached_data("summary")
            cached_deployment = get_cached_data("deployment")
            cached_swarm = get_cached_data("swarm")
            if (
                cached_summary is not None
                and cached_deployment is not None
                and cached_swarm is not None
            ):
                # Create swarm title (we need to get cached time, so fetch fresh for title)
                _, swarm_cached_time = fetch_swarm_info()
                swarm_title = html.H5(
                    f"Docker Swarm Status{swarm_cached_time}", className="card-title mt-4"
                )
                return cached_summary, cached_deployment, cached_swarm, swarm_title

        # Fetch deployment info from api-health endpoint
        deployment_info = fetch_deployment_info(api_environment)

        # Fetch Docker Swarm information
        swarm_info, swarm_cached_time = fetch_swarm_info()

        # Create swarm title with cached timestamp
        swarm_title = html.H5(
            f"Docker Swarm Status{swarm_cached_time}", className="card-title mt-4"
        )

        # Quick check if status endpoint is available
        if not is_status_endpoint_available(token, api_environment):
            fallback_result = get_fallback_summary()
            set_cached_data("summary", fallback_result)  # Shorter cache for fallback
            set_cached_data("deployment", deployment_info)  # Cache deployment for 5 min
            set_cached_data("swarm", swarm_info)  # Cache swarm for 5 min
            return fallback_result, deployment_info, swarm_info, swarm_title

        headers = {"Authorization": f"Bearer {token}"}

        try:
            # Get the latest status data from the status endpoint with optimized parameters
            resp = requests.get(
                f"{get_api_base(api_environment)}/status",
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

                            timestamp_display = html.Div(
                                [
                                    html.Div(
                                        f"{local_time_str} {tz_abbrev}",
                                        className="fw-bold text-primary",
                                    ),
                                    html.Div(f"({utc_time_str})", className="text-muted small"),
                                ]
                            )
                        else:
                            timestamp_display = "Not available"
                    except (ValueError, TypeError):
                        timestamp_display = "Invalid timestamp format"

                    # Extract status details
                    executions = latest_status.get("executions", {})
                    users = latest_status.get("users", {})
                    system = latest_status.get("system", {})

                    # Create summary layout
                    summary_layout = html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.H6("Executions", className="mb-2"),
                                            html.P(
                                                f"Total: {executions.get('total', 0)}",
                                                className="mb-1",
                                            ),
                                            html.P(
                                                f"Running: {executions.get('running', 0)}",
                                                className="text-primary mb-1",
                                            ),
                                            html.P(
                                                f"Finished: {executions.get('finished', 0)}",
                                                className="text-success mb-1",
                                            ),
                                            html.P(
                                                f"Failed: {executions.get('failed', 0)}",
                                                className="text-danger mb-1",
                                            ),
                                        ],
                                        className="col-md-3 text-center",
                                    ),
                                    html.Div(
                                        [
                                            html.H6("Users", className="mb-2"),
                                            html.P(
                                                f"Total: {users.get('total', 0)}",
                                                className="mb-1",
                                            ),
                                            html.P(
                                                f"Active (24h): {users.get('active_24h', 0)}",
                                                className="text-info mb-1",
                                            ),
                                        ],
                                        className="col-md-3 text-center",
                                    ),
                                    html.Div(
                                        [
                                            html.H6("System", className="mb-2"),
                                            html.P(
                                                f"CPU: {system.get('cpu_percent', 0)}%",
                                                className="mb-1",
                                            ),
                                            html.P(
                                                f"Memory: {system.get('memory_percent', 0)}%",
                                                className="mb-1",
                                            ),
                                        ],
                                        className="col-md-3 text-center",
                                    ),
                                    html.Div(
                                        [
                                            html.H6("Last Updated", className="mb-2"),
                                            timestamp_display,
                                        ],
                                        className="col-md-3 text-center",
                                    ),
                                ],
                                className="row",
                            )
                        ]
                    )
                    set_cached_data("summary", summary_layout)
                    set_cached_data("deployment", deployment_info)
                    set_cached_data("swarm", swarm_info)
                    return summary_layout, deployment_info, swarm_info, swarm_title
                else:
                    no_data_result = html.Div(
                        "No status data available.", className="text-center text-muted"
                    )
                    set_cached_data("summary", no_data_result)
                    set_cached_data("deployment", deployment_info)
                    set_cached_data("swarm", swarm_info)
                    return no_data_result, deployment_info, swarm_info, swarm_title
            else:
                error_result = html.Div(
                    f"Error fetching status: {resp.status_code}",
                    className="text-center text-danger",
                )
                set_cached_data("summary", error_result)
                set_cached_data("deployment", deployment_info)
                set_cached_data("swarm", swarm_info)
                return error_result, deployment_info, swarm_info, swarm_title
        except requests.exceptions.RequestException as e:
            error_result = html.Div(
                f"Error fetching status: {e}", className="text-center text-danger"
            )
            set_cached_data("summary", error_result)
            set_cached_data("deployment", deployment_info)
            set_cached_data("swarm", swarm_info)
            return error_result, deployment_info, swarm_info, swarm_title

    @app.callback(
        Output("stats-summary-cards", "children"),
        Output("stats-user-map", "children"),
        Output("stats-additional-charts", "children"),
        [
            Input("status-countdown-interval", "n_intervals"),
            Input("refresh-status-btn", "n_clicks"),
        ],
        [
            State("token-store", "data"),
            State("active-tab-store", "data"),
            State("user-timezone-store", "data"),
            State("role-store", "data"),
            State("api-environment-store", "data"),
        ],
        prevent_initial_call=False,
    )
    def update_status_and_statistics(
        _n_intervals, _refresh_clicks, token, active_tab, user_timezone, role, api_environment
    ):
        """Update the status summary and enhanced statistics."""
        # Guard: Skip if not logged in (prevents execution after logout)
        if not token or role not in ["ADMIN", "SUPERADMIN"]:
            return no_update, no_update, no_update

        # Only update when status tab is active to avoid unnecessary API calls
        if active_tab != "status":
            return no_update, no_update, no_update

        # Get safe timezone
        safe_timezone = get_safe_timezone(user_timezone)

        # Check cache first (unless it's a manual refresh)
        ctx = callback_context
        is_manual_refresh = (
            ctx.triggered and ctx.triggered[0]["prop_id"].split(".")[0] == "refresh-status-btn"
        )

        if not is_manual_refresh:
            cached_summary = get_cached_data("summary")
            cached_deployment = get_cached_data("deployment")
            cached_swarm = get_cached_data("swarm")
            cached_statistics = _stats_cache.get("stats_summary")
            if (
                cached_summary is not None
                and cached_deployment is not None
                and cached_swarm is not None
                and cached_statistics is not None
            ):
                # Create swarm title (we need to get cached time, so fetch fresh for title)
                _, swarm_cached_time = fetch_swarm_info()
                swarm_title = html.H5(
                    f"Docker Swarm Status{swarm_cached_time}", className="card-title mt-4"
                )
                return (
                    cached_summary,
                    cached_deployment,
                    cached_swarm,
                    swarm_title,
                    *cached_statistics,
                )

        # Fetch deployment info from api-health endpoint
        deployment_info = fetch_deployment_info(api_environment)

        # Fetch Docker Swarm information
        swarm_info, swarm_cached_time = fetch_swarm_info()

        # Create swarm title with cached timestamp
        swarm_title = html.H5(
            f"Docker Swarm Status{swarm_cached_time}", className="card-title mt-4"
        )

        # Quick check if status endpoint is available
        if not is_status_endpoint_available(token, api_environment):
            fallback_result = get_fallback_summary()
            set_cached_data("summary", fallback_result)  # Shorter cache for fallback
            set_cached_data("deployment", deployment_info)  # Cache deployment for 5 min
            set_cached_data("swarm", swarm_info)  # Cache swarm for 5 min
            return (
                fallback_result,
                deployment_info,
                swarm_info,
                swarm_title,
                no_update,
                no_update,
                no_update,
            )

        headers = {"Authorization": f"Bearer {token}"}

        try:
            # Get the latest status data from the status endpoint with optimized parameters
            resp = requests.get(
                f"{get_api_base(api_environment)}/status",
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

                            timestamp_display = html.Div(
                                [
                                    html.Div(
                                        f"{local_time_str} {tz_abbrev}",
                                        className="fw-bold text-primary",
                                    ),
                                    html.Div(f"({utc_time_str})", className="text-muted small"),
                                ]
                            )
                        else:
                            timestamp_display = "Not available"
                    except (ValueError, TypeError):
                        timestamp_display = "Invalid timestamp format"

                    # Extract status details
                    executions = latest_status.get("executions", {})
                    users = latest_status.get("users", {})
                    system = latest_status.get("system", {})

                    # Create summary layout
                    summary_layout = html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.H6("Executions", className="mb-2"),
                                            html.P(
                                                f"Total: {executions.get('total', 0)}",
                                                className="mb-1",
                                            ),
                                            html.P(
                                                f"Running: {executions.get('running', 0)}",
                                                className="text-primary mb-1",
                                            ),
                                            html.P(
                                                f"Finished: {executions.get('finished', 0)}",
                                                className="text-success mb-1",
                                            ),
                                            html.P(
                                                f"Failed: {executions.get('failed', 0)}",
                                                className="text-danger mb-1",
                                            ),
                                        ],
                                        className="col-md-3 text-center",
                                    ),
                                    html.Div(
                                        [
                                            html.H6("Users", className="mb-2"),
                                            html.P(
                                                f"Total: {users.get('total', 0)}",
                                                className="mb-1",
                                            ),
                                            html.P(
                                                f"Active (24h): {users.get('active_24h', 0)}",
                                                className="text-info mb-1",
                                            ),
                                        ],
                                        className="col-md-3 text-center",
                                    ),
                                    html.Div(
                                        [
                                            html.H6("System", className="mb-2"),
                                            html.P(
                                                f"CPU: {system.get('cpu_percent', 0)}%",
                                                className="mb-1",
                                            ),
                                            html.P(
                                                f"Memory: {system.get('memory_percent', 0)}%",
                                                className="mb-1",
                                            ),
                                        ],
                                        className="col-md-3 text-center",
                                    ),
                                    html.Div(
                                        [
                                            html.H6("Last Updated", className="mb-2"),
                                            timestamp_display,
                                        ],
                                        className="col-md-3 text-center",
                                    ),
                                ],
                                className="row",
                            )
                        ]
                    )
                    set_cached_data("summary", summary_layout)
                    set_cached_data("deployment", deployment_info)
                    set_cached_data("swarm", swarm_info)

                    # Fetch enhanced statistics
                    dashboard_stats = fetch_dashboard_stats(token, api_environment, "last_day")
                    user_stats = fetch_user_stats(token, api_environment, "last_day")
                    execution_stats = fetch_execution_stats(token, api_environment, "last_day")

                    # Format and cache the enhanced statistics
                    cards = create_dashboard_summary_cards(dashboard_stats)
                    user_map = create_user_geographic_map(user_stats)
                    additional_charts = create_user_statistics_chart(
                        user_stats
                    ) + create_execution_statistics_chart(execution_stats)

                    _stats_cache["stats_summary"] = (cards, user_map, additional_charts)

                    return (
                        summary_layout,
                        deployment_info,
                        swarm_info,
                        swarm_title,
                        cards,
                        user_map,
                        additional_charts,
                    )
                else:
                    no_data_result = html.Div(
                        "No status data available.", className="text-center text-muted"
                    )
                    set_cached_data("summary", no_data_result)
                    set_cached_data("deployment", deployment_info)
                    set_cached_data("swarm", swarm_info)
                    return (
                        no_data_result,
                        deployment_info,
                        swarm_info,
                        swarm_title,
                        no_update,
                        no_update,
                        no_update,
                    )
            else:
                error_result = html.Div(
                    f"Error fetching status: {resp.status_code}",
                    className="text-center text-danger",
                )
                set_cached_data("summary", error_result)
                set_cached_data("deployment", deployment_info)
                set_cached_data("swarm", swarm_info)
                return (
                    error_result,
                    deployment_info,
                    swarm_info,
                    swarm_title,
                    no_update,
                    no_update,
                    no_update,
                )
        except requests.exceptions.RequestException as e:
            error_result = html.Div(
                f"Error fetching status: {e}", className="text-center text-danger"
            )
            set_cached_data("summary", error_result)
            set_cached_data("deployment", deployment_info)
            set_cached_data("swarm", swarm_info)
            return (
                error_result,
                deployment_info,
                swarm_info,
                swarm_title,
                no_update,
                no_update,
                no_update,
            )

    @app.callback(
        Output("status-charts", "children"),
        [
            Input("active-tab-store", "data"),
            Input("status-countdown-interval", "n_intervals"),
            Input("refresh-status-btn", "n_clicks"),
        ],
        [
            State("token-store", "data"),
            State("user-timezone-store", "data"),
            State("api-environment-store", "data"),
        ],
    )
    def update_status_charts(
        active_tab, _n_intervals, _refresh_clicks, token, user_timezone, api_environment
    ):
        """Update the status charts for the selected time range."""
        # Guard: Skip if not logged in (prevents execution after logout)
        if not token:
            return no_update

        headers = {"Authorization": f"Bearer {token}"}

        # Get safe timezone
        safe_timezone = get_safe_timezone(user_timezone)

        # Define time ranges for API query
        end_time = datetime.now(timezone.utc)
        if active_tab == "month":
            start_time = end_time - timedelta(days=30)
        else:
            start_time = end_time - timedelta(days=1)

        # Format for API query
        start_iso = start_time.isoformat()
        end_iso = end_time.isoformat()

        try:
            resp = requests.get(
                f"{get_api_base(api_environment)}/status",
                headers=headers,
                params={
                    "timestamp_gte": start_iso,
                    "timestamp_lte": end_iso,
                    "per_page": 1000,  # Fetch up to 1000 data points
                    "sort": "timestamp",  # Sort by timestamp ascending
                },
                timeout=10,
            )
            resp.raise_for_status()
            status_data = resp.json().get("data", [])

            if not status_data:
                return html.Div(
                    "No status data available for the selected period.",
                    className="text-center text-muted p-4",
                )

            # Convert to DataFrame for easier manipulation
            df = pd.DataFrame(status_data)
            df["timestamp"] = pd.to_datetime(df["timestamp"])

            # Convert UTC timestamps to user's local timezone for plotting
            df["local_timestamp"] = df["timestamp"].apply(
                lambda x: convert_utc_to_local(x, safe_timezone)
            )

            # Create charts
            charts = []
            status_metrics = {
                "Executions": {"running": "primary", "finished": "success", "failed": "danger"},
                "Users": {"active_24h": "info"},
                "System": {"cpu_percent": "warning", "memory_percent": "secondary"},
            }

            for category, metrics in status_metrics.items():
                fig = go.Figure()
                for metric, color in metrics.items():
                    # Extract nested data from DataFrame
                    values = df[category.lower()].apply(lambda x, m=metric: x.get(m, 0))
                    fig.add_trace(
                        go.Scatter(
                            x=df["local_timestamp"],
                            y=values,
                            mode="lines+markers",
                            name=metric.replace("_", " ").title(),
                            line={"color": f"var(--bs-{color})"},
                            marker={"size": 4},
                        )
                    )

                fig.update_layout(
                    title=f"{category} Status",
                    xaxis_title=get_chart_axis_label(safe_timezone),
                    yaxis_title="Count" if category != "System" else "Percentage",
                    margin={"l": 40, "r": 20, "t": 40, "b": 30},
                    legend={"orientation": "h", "yanchor": "bottom", "y": 1.02},
                    template="plotly_white",
                    height=300,
                )
                charts.append(dcc.Graph(figure=fig))

            return html.Div(charts)

        except requests.exceptions.RequestException as e:
            return html.Div(
                f"Error fetching chart data: {e}",
                className="text-center text-danger p-4",
            )

    @app.callback(
        Output("status-time-tabs-store", "data"),
        [
            Input("status-tab-day", "n_clicks"),
            Input("status-tab-week", "n_clicks"),
            Input("status-tab-month", "n_clicks"),
        ],
    )
    def update_active_status_tab(_day_clicks, _week_clicks, _month_clicks):
        """Update the hidden store with the active status tab."""
        ctx = callback_context
        if not ctx.triggered:
            return "day"
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if button_id == "status-tab-week":
            return "week"
        if button_id == "status-tab-month":
            return "month"
        return "day"

    @app.callback(
        [
            Output("status-tab-day", "className"),
            Output("status-tab-week", "className"),
            Output("status-tab-month", "className"),
        ],
        [Input("status-time-tabs-store", "data")],
    )
    def update_status_tab_styles(active_tab):
        """Update the visual style of the active status tab."""
        if active_tab == "week":
            return "nav-link", "nav-link active", "nav-link"
        if active_tab == "month":
            return "nav-link", "nav-link", "nav-link active"
        return "nav-link active", "nav-link", "nav-link"

    @app.callback(
        Output("status-countdown", "children"),
        Input("status-countdown-interval", "n_intervals"),
        State("status-auto-refresh-interval", "interval"),
    )
    def update_countdown(n, interval_ms):
        """Update the countdown timer display."""
        if n is None:
            return "60s"
        seconds_remaining = (interval_ms / 1000) - (n % (interval_ms / 1000))
        return f"{int(seconds_remaining)}s"
