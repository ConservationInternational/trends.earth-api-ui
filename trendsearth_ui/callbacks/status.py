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
    create_deployment_information,
    create_docker_swarm_status_table,
    create_execution_statistics_chart,
    create_system_overview,
    create_user_geographic_map,
    create_user_statistics_chart,
)
from ..utils.status_helpers import (
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
                # Even for cached data, get the fresh timestamp from swarm endpoint
                try:
                    headers = {"Authorization": f"Bearer {token}"} if token else {}
                    resp = requests.get(
                        f"{get_api_base(api_environment)}/status/swarm",
                        headers=headers,
                        timeout=5,
                    )
                    if resp.status_code == 200:
                        swarm_data = resp.json().get("data", {})
                        cache_info = swarm_data.get("cache_info", {})
                        cached_at = cache_info.get("cached_at", "")
                        swarm_cached_time = f" (Updated: {cached_at[:19]})" if cached_at else ""
                    else:
                        swarm_cached_time = ""
                except Exception:
                    swarm_cached_time = ""

                swarm_title = html.H5(
                    f"Docker Swarm Status{swarm_cached_time}", className="card-title mt-4"
                )
                return cached_summary, cached_deployment, cached_swarm, swarm_title

        # Fetch deployment info from api-health endpoint
        deployment_info = create_deployment_information(api_environment)

        # Fetch Docker Swarm information
        try:
            # Fetch raw swarm data from API
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            resp = requests.get(
                f"{get_api_base(api_environment)}/status/swarm",
                headers=headers,
                timeout=5,
            )

            if resp.status_code == 200:
                swarm_data = resp.json().get("data", {})
                swarm_info = create_docker_swarm_status_table(swarm_data)
                cache_info = swarm_data.get("cache_info", {})
                cached_at = cache_info.get("cached_at", "")
                swarm_cached_time = f" (Updated: {cached_at[:19]})" if cached_at else ""
            elif resp.status_code == 401:
                # Handle authentication error
                swarm_info = html.Div(
                    [
                        html.P("Authentication failed", className="mb-1 text-warning"),
                        html.P("Please check your login status", className="mb-1 text-muted"),
                    ]
                )
                swarm_cached_time = " (Auth Error)"
            elif resp.status_code == 403:
                # Handle permission error
                swarm_info = html.Div(
                    [
                        html.P("Access denied", className="mb-1 text-warning"),
                        html.P(
                            "Admin privileges required for swarm status",
                            className="mb-1 text-muted",
                        ),
                    ]
                )
                swarm_cached_time = " (Access Denied)"
            else:
                # Handle other errors
                swarm_info = html.Div(
                    [
                        html.P(
                            f"Swarm Status: Error ({resp.status_code})",
                            className="mb-1 text-danger",
                        ),
                        html.P("Unable to retrieve swarm information", className="mb-1 text-muted"),
                    ]
                )
                swarm_cached_time = " (Error)"
        except Exception:
            # Handle connection errors
            swarm_info = html.Div(
                [
                    html.P("Swarm Status: Connection Error", className="mb-1 text-danger"),
                    html.P("Unable to reach swarm status endpoint", className="mb-1 text-muted"),
                ]
            )
            swarm_cached_time = " (Connection Error)"

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
                params={
                    "per_page": 1,
                    "sort": "-timestamp",
                    "exclude": "metadata,logs",  # Exclude large fields for performance
                },
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

                    # Extract status details for different sections
                    executions_active = latest_status.get("executions_active", 0)
                    executions_ready = latest_status.get("executions_ready", 0)
                    executions_running = latest_status.get("executions_running", 0)
                    executions_finished = latest_status.get("executions_finished", 0)

                    # Create summary layout with expected section headers
                    summary_layout = html.Div(
                        [
                            # Active Executions Section
                            html.H5("Active Executions", className="text-center mb-3 text-muted"),
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.H6("Running", className="mb-2"),
                                            html.P(
                                                str(executions_running),
                                                className="text-primary mb-1",
                                            ),
                                        ],
                                        className="col-md-4 text-center",
                                    ),
                                    html.Div(
                                        [
                                            html.H6("Ready", className="mb-2"),
                                            html.P(
                                                str(executions_ready),
                                                className="text-info mb-1",
                                            ),
                                        ],
                                        className="col-md-4 text-center",
                                    ),
                                    html.Div(
                                        [
                                            html.H6("Active Total", className="mb-2"),
                                            html.P(
                                                str(executions_active),
                                                className="text-success mb-1",
                                            ),
                                        ],
                                        className="col-md-4 text-center",
                                    ),
                                ],
                                className="row mb-4",
                            ),
                            # Completed Executions Section
                            html.H5(
                                "Completed Executions", className="text-center mb-3 text-muted"
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.H6("Finished", className="mb-2"),
                                            html.P(
                                                str(executions_finished),
                                                className="text-success mb-1",
                                            ),
                                        ],
                                        className="col-md-6 text-center",
                                    ),
                                    html.Div(
                                        [
                                            html.H6("Last Updated", className="mb-2"),
                                            timestamp_display,
                                        ],
                                        className="col-md-6 text-center",
                                    ),
                                ],
                                className="row mb-4",
                            ),
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
        Output("system-overview-content", "children"),
        Output("stats-user-map", "children"),
        Output("stats-additional-charts", "children"),
        [
            Input("status-auto-refresh-interval", "n_intervals"),
            Input("refresh-status-btn", "n_clicks"),
            Input("status-time-tabs-store", "data"),  # Add time period selection
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
        _n_intervals,
        _refresh_clicks,
        time_period,
        token,
        active_tab,
        _user_timezone,
        role,
        api_environment,
    ):
        """Update the status summary and enhanced statistics."""
        # Guard: Skip if not logged in (prevents execution after logout)
        if not token or role not in ["ADMIN", "SUPERADMIN"]:
            return no_update, no_update, no_update

        # Only update when status tab is active to avoid unnecessary API calls
        if active_tab != "status":
            return no_update, no_update, no_update

        # Check if user has required permissions for enhanced stats (SUPERADMIN only)
        if role != "SUPERADMIN":
            # Show permission message for enhanced stats
            permission_msg = html.Div(
                [
                    html.P("Enhanced Statistics", className="text-muted text-center"),
                    html.Small(
                        "SUPERADMIN privileges required to access detailed analytics.",
                        className="text-muted text-center d-block",
                    ),
                ],
                className="p-4",
            )
            return permission_msg, permission_msg, [permission_msg]

        # Map UI time period to API period
        api_period_map = {"day": "last_day", "week": "last_week", "month": "last_month"}
        api_period = api_period_map.get(time_period, "last_day")

        # Check cache first (unless it's a manual refresh or time period changed)
        ctx = callback_context
        is_manual_refresh = (
            ctx.triggered and ctx.triggered[0]["prop_id"].split(".")[0] == "refresh-status-btn"
        )
        is_time_period_change = (
            ctx.triggered and ctx.triggered[0]["prop_id"].split(".")[0] == "status-time-tabs-store"
        )

        cache_key = f"stats_summary_{api_period}"
        if not is_manual_refresh and not is_time_period_change:
            cached_statistics = _stats_cache.get(cache_key)
            if cached_statistics is not None:
                return cached_statistics

        # Quick check if status endpoint is available
        if not is_status_endpoint_available(token, api_environment):
            return (
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
                params={
                    "per_page": 1,
                    "sort": "-timestamp",
                    "exclude": "metadata,logs",  # Exclude large fields for performance
                },
                timeout=5,  # Reduced from 10 seconds
            )

            if resp.status_code == 200:
                status_data = resp.json().get("data", [])
                if status_data:
                    # Fetch enhanced statistics for SUPERADMIN users with selected time period
                    dashboard_stats = fetch_dashboard_stats(token, api_environment, api_period)
                    user_stats = fetch_user_stats(token, api_environment, api_period)
                    execution_stats = fetch_execution_stats(token, api_environment, api_period)

                    # Debug logging to see what we actually get
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.info(f"Dashboard stats type: {type(dashboard_stats)}")
                    logger.info(f"User stats type: {type(user_stats)}")
                    logger.info(f"Execution stats type: {type(execution_stats)}")

                    if isinstance(dashboard_stats, dict):
                        logger.info(f"Dashboard stats keys: {list(dashboard_stats.keys())}")
                    if isinstance(user_stats, dict):
                        logger.info(f"User stats keys: {list(user_stats.keys())}")
                    if isinstance(execution_stats, dict):
                        logger.info(f"Execution stats keys: {list(execution_stats.keys())}")

                    # Format and cache the enhanced statistics with period-specific key
                    # Get the latest status for scripts count
                    latest_status = status_data[0] if status_data else {}
                    system_overview = create_system_overview(dashboard_stats, latest_status)
                    user_map = create_user_geographic_map(user_stats)
                    additional_charts = create_user_statistics_chart(
                        user_stats
                    ) + create_execution_statistics_chart(execution_stats)

                    _stats_cache[cache_key] = (system_overview, user_map, additional_charts)

                    return (
                        system_overview,
                        user_map,
                        additional_charts,
                    )
                else:
                    return (
                        no_update,
                        no_update,
                        no_update,
                    )
            else:
                return (
                    no_update,
                    no_update,
                    no_update,
                )
        except requests.exceptions.RequestException:
            return (
                no_update,
                no_update,
                no_update,
            )

    @app.callback(
        Output("status-charts", "children"),
        [
            Input("status-time-tabs-store", "data"),
            Input("status-auto-refresh-interval", "n_intervals"),
            Input("refresh-status-btn", "n_clicks"),
        ],
        [
            State("token-store", "data"),
            State("user-timezone-store", "data"),
            State("api-environment-store", "data"),
            State("active-tab-store", "data"),
        ],
    )
    def update_status_charts(
        time_tab, _n_intervals, _refresh_clicks, token, user_timezone, api_environment, active_tab
    ):
        """Update the status charts for the selected time range."""
        # Guard: Skip if not logged in (prevents execution after logout)
        if not token:
            return no_update

        # Only update when status tab is active to avoid unnecessary API calls
        if active_tab != "status":
            return no_update

        headers = {"Authorization": f"Bearer {token}"}

        # Get safe timezone
        safe_timezone = get_safe_timezone(user_timezone)

        # Define time ranges for API query
        end_time = datetime.now(timezone.utc)
        if time_tab == "month":
            start_time = end_time - timedelta(days=30)
        elif time_tab == "week":
            start_time = end_time - timedelta(days=7)
        else:  # Default to day
            start_time = end_time - timedelta(days=1)

        # Format for API query
        start_iso = start_time.isoformat()
        end_iso = end_time.isoformat()

        try:
            resp = requests.get(
                f"{get_api_base(api_environment)}/status",
                headers=headers,
                params={
                    "start_date": start_iso,
                    "end_date": end_iso,
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
            # IMPORTANT: This was creating tuples, let's fix it to return proper datetime objects
            local_timestamps = []
            for timestamp in df["timestamp"]:
                local_dt, tz_abbrev = convert_utc_to_local(timestamp, safe_timezone)
                local_timestamps.append(local_dt)  # Only append the datetime object, not the tuple

            df["local_timestamp"] = pd.to_datetime(local_timestamps)

            # Debug: Log what data we received
            logger.info(f"Status data received: {len(status_data)} records")
            if status_data:
                logger.info(f"Available columns: {list(df.columns)}")
                logger.info(f"Sample data (first record): {status_data[0]}")
                # Check specific fields we need
                first_record = status_data[0]
                execution_fields = [
                    "executions_running",
                    "executions_ready",
                    "executions_pending",  # Add pending for future API support
                    "executions_finished",
                    "executions_failed",
                    "executions_cancelled",
                    "executions_active",
                ]
                logger.info("Execution field values in first record:")
                for field in execution_fields:
                    value = first_record.get(field, "MISSING")
                    logger.info(f"  {field}: {value}")

                # Check what actual data is available
                logger.info("Other available fields:")
                other_fields = ["executions_count", "scripts_count", "users_count"]
                for field in other_fields:
                    value = first_record.get(field, "MISSING")
                    logger.info(f"  {field}: {value}")
            else:
                logger.warning("No status data records returned from API")

            # Create charts
            charts = []

            # Debug: Log DataFrame info for timeseries debugging
            logger.info(f"DataFrame shape: {df.shape}")
            logger.info(f"Timestamp range: {df['timestamp'].min()} to {df['timestamp'].max()}")
            if "local_timestamp" in df.columns:
                logger.info(
                    f"Local timestamp range: {df['local_timestamp'].min()} to {df['local_timestamp'].max()}"
                )

            # Debug specific fields for chart debugging
            for field in [
                "executions_running",
                "executions_ready",
                "executions_finished",
                "executions_failed",
            ]:
                if field in df.columns:
                    values = df[field]
                    logger.info(
                        f"{field}: min={values.min()}, max={values.max()}, std={values.std():.2f}"
                    )
                    logger.info(f"{field} first 10 values: {values.head(10).tolist()}")
                    logger.info(f"{field} last 10 values: {values.tail(10).tolist()}")
                    unique_count = len(values.unique())
                    logger.info(
                        f"{field} has {unique_count} unique values out of {len(values)} total"
                    )

            # Debug time axis - this might be the issue!
            logger.info("Time debugging:")
            logger.info(f"local_timestamp dtype: {df['local_timestamp'].dtype}")
            logger.info(f"First 5 timestamps: {df['local_timestamp'].head().tolist()}")
            logger.info(f"Last 5 timestamps: {df['local_timestamp'].tail().tolist()}")
            logger.info(
                f"Timestamp uniqueness: {len(df['local_timestamp'].unique())} unique out of {len(df)} total"
            )

            # Check if timestamps are sorted
            is_sorted = df["local_timestamp"].is_monotonic_increasing
            logger.info(f"Timestamps are sorted: {is_sorted}")
            if not is_sorted:
                logger.warning("Timestamps are NOT sorted - this could cause chart display issues!")
                df = df.sort_values("local_timestamp").reset_index(drop=True)
                logger.info("Sorted DataFrame by local_timestamp")

            # Chart 1: Total Executions Over Time (if available)
            if "executions_count" in df.columns:
                values = df["executions_count"].fillna(0)
                # Show total executions even if it doesn't change much - it shows system activity
                if values.max() > 0:  # Only show if there's actual data
                    fig1 = go.Figure()
                    fig1.add_trace(
                        go.Scatter(
                            x=df["local_timestamp"],
                            y=values,
                            mode="lines+markers",
                            name="Total Executions",
                            line={"color": "#007bff", "width": 3},
                            marker={"size": 4},
                            hovertemplate="<b>Total Executions</b><br>%{x}<br>Count: %{y}<extra></extra>",
                        )
                    )

                    fig1.update_layout(
                        title={
                            "text": "Total Executions Over Time",
                            "x": 0.5,
                            "xanchor": "center",
                        },
                        xaxis_title=get_chart_axis_label(safe_timezone),
                        yaxis_title="Total Executions",
                        margin={"l": 40, "r": 40, "t": 60, "b": 40},
                        template="plotly_white",
                        height=400,
                        hovermode="x unified",
                        showlegend=False,
                    )
                    charts.append(
                        html.Div(
                            [
                                dcc.Graph(
                                    figure=fig1,
                                    config={
                                        "displayModeBar": False,
                                        "responsive": True,
                                    },
                                )
                            ],
                            className="mb-4",
                        )
                    )

            # Chart 2: Scripts and Users Over Time
            system_metrics_available = any(
                col in df.columns for col in ["scripts_count", "users_count"]
            )
            if system_metrics_available:
                fig2 = go.Figure()

                if "scripts_count" in df.columns:
                    scripts_values = df["scripts_count"].fillna(0)
                    if scripts_values.max() > 0:
                        fig2.add_trace(
                            go.Scatter(
                                x=df["local_timestamp"],
                                y=scripts_values,
                                mode="lines+markers",
                                name="Scripts",
                                line={"color": "#28a745", "width": 2},
                                marker={"size": 4},
                                yaxis="y",
                                hovertemplate="<b>Scripts</b><br>%{x}<br>Count: %{y}<extra></extra>",
                            )
                        )

                if "users_count" in df.columns:
                    users_values = df["users_count"].fillna(0)
                    if users_values.max() > 0:
                        fig2.add_trace(
                            go.Scatter(
                                x=df["local_timestamp"],
                                y=users_values,
                                mode="lines+markers",
                                name="Users",
                                line={"color": "#dc3545", "width": 2},
                                marker={"size": 4},
                                yaxis="y2",
                                hovertemplate="<b>Users</b><br>%{x}<br>Count: %{y}<extra></extra>",
                            )
                        )

                # Only show chart if we added any traces
                if fig2.data:
                    fig2.update_layout(
                        title={
                            "text": "System Growth Over Time",
                            "x": 0.5,
                            "xanchor": "center",
                        },
                        xaxis_title=get_chart_axis_label(safe_timezone),
                        yaxis={"title": "Scripts Count", "side": "left", "color": "#28a745"},
                        yaxis2={
                            "title": "Users Count",
                            "side": "right",
                            "overlaying": "y",
                            "color": "#dc3545",
                        },
                        margin={"l": 40, "r": 40, "t": 60, "b": 40},
                        template="plotly_white",
                        height=400,
                        hovermode="x unified",
                        legend={
                            "orientation": "h",
                            "yanchor": "bottom",
                            "y": 1.02,
                            "xanchor": "center",
                            "x": 0.5,
                        },
                    )
                    charts.append(
                        html.Div(
                            [
                                dcc.Graph(
                                    figure=fig2,
                                    config={
                                        "displayModeBar": False,
                                        "responsive": True,
                                    },
                                )
                            ],
                            className="mb-4",
                        )
                    )

            # Chart 3: Active Execution Status (Running, Ready, Pending)
            active_status_metrics = [
                {"field": "executions_running", "name": "Running", "color": "#007bff"},
                {"field": "executions_ready", "name": "Ready", "color": "#17a2b8"},
                {
                    "field": "executions_pending",
                    "name": "Pending",
                    "color": "#ffc107",
                },  # Preparing for API update
            ]

            fig3 = go.Figure()
            has_active_data = False

            for metric in active_status_metrics:
                field = metric["field"]
                if field in df.columns:
                    values = df[field].fillna(0)
                    # Show all active status lines to provide context, even if low values
                    has_active_data = True
                    logger.info(
                        f"Adding {field} to active chart: min={values.min()}, max={values.max()}, unique_values={len(values.unique())}"
                    )

                    # Debug: Log the actual data being sent to Plotly
                    x_data = df["local_timestamp"]
                    y_data = values
                    logger.info(
                        f"X-axis data type: {type(x_data.iloc[0])}, sample: {x_data.iloc[0]}"
                    )
                    logger.info(
                        f"Y-axis data type: {type(y_data.iloc[0])}, sample: {y_data.iloc[0]}"
                    )
                    logger.info(
                        f"Data points being plotted: {len(x_data)} x-values, {len(y_data)} y-values"
                    )

                    fig3.add_trace(
                        go.Scatter(
                            x=x_data,
                            y=y_data,
                            mode="lines+markers",
                            name=metric["name"],
                            line={"color": metric["color"], "width": 3},  # Thicker lines
                            marker={"size": 6},  # Larger markers
                            hovertemplate=f"<b>{metric['name']}</b><br>%{{x}}<br>Count: %{{y}}<extra></extra>",
                        )
                    )

            if has_active_data:
                # Calculate y-axis range to make variations more visible
                all_active_values = []
                for metric in active_status_metrics:
                    field = metric["field"]
                    if field in df.columns:
                        values = df[field].fillna(0)
                        all_active_values.extend(values.tolist())

                if all_active_values:
                    min_val = min(all_active_values)
                    max_val = max(all_active_values)
                    # Add padding to make variations visible
                    padding = max(1, (max_val - min_val) * 0.1)  # 10% padding or at least 1
                    y_min = max(0, min_val - padding)
                    y_max = max_val + padding
                    logger.info(
                        f"Active chart y-axis range: {y_min} to {y_max} (data range: {min_val} to {max_val})"
                    )
                else:
                    y_min, y_max = 0, 150

                fig3.update_layout(
                    title={
                        "text": "Active Execution Status Over Time",
                        "x": 0.5,
                        "xanchor": "center",
                    },
                    xaxis_title=get_chart_axis_label(safe_timezone),
                    yaxis_title="Number of Active Executions",
                    yaxis={"range": [y_min, y_max]},  # Set explicit y-axis range
                    margin={"l": 40, "r": 40, "t": 60, "b": 40},
                    legend={
                        "orientation": "h",
                        "yanchor": "bottom",
                        "y": 1.02,
                        "xanchor": "center",
                        "x": 0.5,
                    },
                    template="plotly_white",
                    height=400,
                    hovermode="x unified",
                    showlegend=True,
                )
                charts.append(
                    html.Div(
                        [
                            dcc.Graph(
                                figure=fig3,
                                config={
                                    "displayModeBar": False,
                                    "responsive": True,
                                },
                            )
                        ],
                        className="mb-4",
                    )
                )
                logger.info(
                    f"Added active execution status chart to charts list. Total charts so far: {len(charts)}"
                )

            # Chart 3b: Completed Execution Status Rate (Show as bar chart for better visibility)
            completed_status_metrics = [
                {"field": "executions_finished", "name": "Finished", "color": "#28a745"},
                {"field": "executions_failed", "name": "Failed", "color": "#dc3545"},
                {"field": "executions_cancelled", "name": "Cancelled", "color": "#6c757d"},
            ]

            fig3b = go.Figure()
            has_completed_data = False

            # Calculate deltas to show the rate of change rather than cumulative totals
            df_sorted = df.sort_values("timestamp").reset_index(drop=True)

            for metric in completed_status_metrics:
                field = metric["field"]
                if field in df_sorted.columns:
                    # Calculate the delta (difference) between consecutive points
                    values = pd.to_numeric(df_sorted[field], errors="coerce").fillna(0)
                    delta_values = values.diff().fillna(0).clip(lower=0)  # Remove negative values

                    logger.info(
                        f"Delta values for {field}: min={delta_values.min()}, max={delta_values.max()}, sum={delta_values.sum()}"
                    )
                    logger.info(
                        f"Non-zero delta count for {field}: {(delta_values > 0).sum()} out of {len(delta_values)}"
                    )

                    # Show as bars instead of lines for better visibility of small values
                    if len(delta_values) > 0 and not delta_values.isna().all():
                        try:
                            max_delta = delta_values.max()
                            if max_delta > 0:
                                has_completed_data = True

                                # For sparse data (mostly zeros), use scatter plot instead of bars
                                nonzero_data = df_sorted[delta_values > 0].copy()
                                nonzero_deltas = delta_values[delta_values > 0]

                                if len(nonzero_data) > 0:
                                    if (
                                        len(nonzero_data) < len(df_sorted) * 0.1
                                    ):  # Less than 10% non-zero
                                        # Use scatter plot for very sparse data
                                        fig3b.add_trace(
                                            go.Scatter(
                                                x=nonzero_data["local_timestamp"],
                                                y=nonzero_deltas,
                                                mode="markers",
                                                name=f"{metric['name']} (New)",
                                                marker={"color": metric["color"], "size": 10},
                                                hovertemplate=f"<b>New {metric['name']}</b><br>%{{x}}<br>Count: %{{y}}<extra></extra>",
                                            )
                                        )
                                    else:
                                        # Use bar chart for denser data
                                        fig3b.add_trace(
                                            go.Bar(
                                                x=df_sorted["local_timestamp"],
                                                y=delta_values,
                                                name=f"{metric['name']} (New)",
                                                marker_color=metric["color"],
                                                hovertemplate=f"<b>New {metric['name']}</b><br>%{{x}}<br>Count: %{{y}}<extra></extra>",
                                                width=300000,  # 5 minutes in milliseconds
                                            )
                                        )
                                    logger.info(
                                        f"Added {field} chart with max value {max_delta}, non-zero points: {len(nonzero_data)}"
                                    )
                        except Exception as e:
                            logger.warning(f"Error processing {field}: {e}")
                            continue

            if has_completed_data:
                fig3b.update_layout(
                    title={
                        "text": "Completed Executions Rate Over Time",
                        "x": 0.5,
                        "xanchor": "center",
                    },
                    xaxis_title=get_chart_axis_label(safe_timezone),
                    yaxis_title="New Completions per Time Period",
                    margin={"l": 40, "r": 40, "t": 60, "b": 40},
                    legend={
                        "orientation": "h",
                        "yanchor": "bottom",
                        "y": 1.02,
                        "xanchor": "center",
                        "x": 0.5,
                    },
                    template="plotly_white",
                    height=400,
                    hovermode="x unified",
                    showlegend=True,
                )
                charts.append(
                    html.Div(
                        [
                            dcc.Graph(
                                figure=fig3b,
                                config={
                                    "displayModeBar": False,
                                    "responsive": True,
                                },
                            )
                        ],
                        className="mb-4",
                    )
                )
                logger.info(
                    f"Added completed execution rate chart to charts list. Total charts so far: {len(charts)}"
                )
            else:
                # Show informative message about execution status
                logger.info("No completed execution data found - showing info message")
                charts.append(
                    html.Div(
                        [
                            html.H5(
                                "Completed Execution Tracking",
                                className="text-center text-muted mb-3",
                            ),
                            html.Div(
                                [
                                    html.I(className="fas fa-info-circle fa-2x text-info mb-3"),
                                    html.P(
                                        "No completed executions detected during this period.",
                                        className="text-muted mb-2",
                                    ),
                                    html.Small(
                                        "This may indicate no new executions were completed or the tracking period is too short.",
                                        className="text-muted",
                                    ),
                                ],
                                className="text-center py-4",
                            ),
                        ],
                        className="border rounded p-3 mb-4 bg-light",
                    )
                )

            # Chart 4: Data Rate Analysis (if executions_count changes over time)
            if "executions_count" in df.columns:
                df_sorted = df.sort_values("timestamp").reset_index(drop=True)
                df_sorted["execution_rate"] = df_sorted["executions_count"].diff().fillna(0)
                df_sorted["execution_rate"] = df_sorted["execution_rate"].clip(
                    lower=0
                )  # Remove negative values

                if df_sorted["execution_rate"].sum() > 0:
                    fig4 = go.Figure()
                    fig4.add_trace(
                        go.Bar(
                            x=df_sorted["local_timestamp"],
                            y=df_sorted["execution_rate"],
                            name="New Executions",
                            marker_color="#6f42c1",
                            hovertemplate="<b>New Executions</b><br>%{x}<br>Count: %{y}<extra></extra>",
                        )
                    )

                    fig4.update_layout(
                        title={
                            "text": "Execution Activity Rate",
                            "x": 0.5,
                            "xanchor": "center",
                        },
                        xaxis_title=get_chart_axis_label(safe_timezone),
                        yaxis_title="New Executions per Period",
                        margin={"l": 40, "r": 40, "t": 60, "b": 40},
                        template="plotly_white",
                        height=350,
                        hovermode="x unified",
                        showlegend=False,
                    )
                    charts.append(
                        html.Div(
                            [
                                dcc.Graph(
                                    figure=fig4,
                                    config={
                                        "displayModeBar": False,
                                        "responsive": True,
                                    },
                                )
                            ],
                            className="mb-4",
                        )
                    )

            # Chart 2: Active vs Inactive Executions
            if "executions_active" in df.columns:
                # Calculate inactive executions
                df["executions_inactive"] = (
                    df["executions_finished"] + df["executions_failed"] + df["executions_cancelled"]
                )

                fig2 = go.Figure()
                fig2.add_trace(
                    go.Scatter(
                        x=df["local_timestamp"],
                        y=df["executions_active"],
                        mode="lines+markers",
                        name="Active Executions",
                        line={"color": "#fd7e14", "width": 3},
                        fill="tonexty",
                        hovertemplate="<b>Active</b><br>%{x}<br>Count: %{y}<extra></extra>",
                    )
                )

                fig2.update_layout(
                    title={
                        "text": "Active Executions Trend",
                        "x": 0.5,
                        "xanchor": "center",
                    },
                    xaxis_title=get_chart_axis_label(safe_timezone),
                    yaxis_title="Number of Active Executions",
                    margin={"l": 40, "r": 40, "t": 60, "b": 40},
                    template="plotly_white",
                    height=350,
                    hovermode="x unified",
                    showlegend=False,
                )
                charts.append(
                    html.Div(
                        [
                            dcc.Graph(
                                figure=fig2,
                                config={
                                    "displayModeBar": False,
                                    "responsive": True,
                                },
                            )
                        ],
                        className="mb-4",
                    )
                )

            # Chart 5: Success Rate Over Time (3-hour windows based on completion deltas)
            if all(field in df.columns for field in ["executions_finished", "executions_failed"]):
                # Sort by timestamp for proper delta calculation
                df_sorted = df.sort_values("timestamp").reset_index(drop=True)

                # Calculate deltas (new completions in each time period)
                df_sorted["finished_delta"] = df_sorted["executions_finished"].diff().fillna(0)
                df_sorted["failed_delta"] = df_sorted["executions_failed"].diff().fillna(0)

                # Remove negative deltas (data inconsistencies)
                df_sorted["finished_delta"] = df_sorted["finished_delta"].clip(lower=0)
                df_sorted["failed_delta"] = df_sorted["failed_delta"].clip(lower=0)

                # Create 3-hour time windows
                df_sorted["timestamp_3h"] = pd.to_datetime(df_sorted["timestamp"])
                df_sorted["window_start"] = df_sorted["timestamp_3h"].dt.floor("3h")

                # Group by 3-hour windows and sum the deltas
                window_stats = (
                    df_sorted.groupby("window_start")
                    .agg({"finished_delta": "sum", "failed_delta": "sum"})
                    .reset_index()
                )

                # Calculate total completions and success rate for each window
                window_stats["total_completions"] = (
                    window_stats["finished_delta"] + window_stats["failed_delta"]
                )
                window_stats = window_stats[
                    window_stats["total_completions"] > 0
                ]  # Only windows with completions

                if not window_stats.empty:
                    window_stats["success_rate"] = (
                        window_stats["finished_delta"] / window_stats["total_completions"] * 100
                    )

                    # Convert to local timezone for display
                    window_stats["local_window_start"] = (
                        window_stats["window_start"]
                        .dt.tz_localize("UTC")
                        .dt.tz_convert(safe_timezone)
                    )

                    # Calculate dynamic y-axis range
                    min_rate = window_stats["success_rate"].min()
                    max_rate = window_stats["success_rate"].max()
                    rate_range = max_rate - min_rate

                    if rate_range < 1.0:  # Less than 1% variation
                        padding = max(0.1, rate_range * 0.2)
                        y_min = max(0, min_rate - padding)
                        y_max = min(100, max_rate + padding)
                    else:
                        y_min, y_max = 0, 100

                    logger.info(
                        f"Success rate (3h windows): {len(window_stats)} windows, rate range {min_rate:.2f}%-{max_rate:.2f}%, y-axis: {y_min:.2f}-{y_max:.2f}"
                    )

                    fig5 = go.Figure()
                    fig5.add_trace(
                        go.Scatter(
                            x=window_stats["local_window_start"],
                            y=window_stats["success_rate"],
                            mode="lines+markers",
                            name="Success Rate",
                            line={"color": "#20c997", "width": 3},
                            marker={"size": 8},
                            customdata=window_stats["total_completions"],
                            hovertemplate="<b>Success Rate (3h window)</b><br>%{x}<br>Rate: %{y:.2f}%<br>Total Completions: %{customdata}<extra></extra>",
                        )
                    )

                    fig5.update_layout(
                        title={
                            "text": "Execution Success Rate (3-Hour Windows)",
                            "x": 0.5,
                            "xanchor": "center",
                        },
                        xaxis_title=get_chart_axis_label(safe_timezone),
                        yaxis_title="Success Rate (%)",
                        yaxis={"range": [y_min, y_max]},
                        margin={"l": 40, "r": 40, "t": 60, "b": 40},
                        template="plotly_white",
                        height=350,
                        hovermode="x unified",
                        showlegend=False,
                    )
                    charts.append(
                        html.Div(
                            [
                                dcc.Graph(
                                    figure=fig5,
                                    config={
                                        "displayModeBar": False,
                                        "responsive": True,
                                    },
                                )
                            ],
                            className="mb-4",
                        )
                    )
                    logger.info(
                        f"Added 3h-window success rate chart to charts list. Total charts so far: {len(charts)}"
                    )

            # Chart 6: Execution Throughput (1-hour windows) with improved visibility
            if all(field in df.columns for field in ["executions_finished", "executions_failed"]):
                # Sort by timestamp for proper delta calculation
                df_sorted = df.sort_values("timestamp").reset_index(drop=True)

                # Calculate deltas (new completions in each time period)
                df_sorted["finished_delta"] = df_sorted["executions_finished"].diff().fillna(0)
                df_sorted["failed_delta"] = df_sorted["executions_failed"].diff().fillna(0)

                # Remove negative deltas (data inconsistencies)
                df_sorted["finished_delta"] = df_sorted["finished_delta"].clip(lower=0)
                df_sorted["failed_delta"] = df_sorted["failed_delta"].clip(lower=0)

                # Calculate total throughput (finished + failed)
                df_sorted["throughput"] = df_sorted["finished_delta"] + df_sorted["failed_delta"]

                # Create 1-hour time windows
                df_sorted["timestamp_1h"] = pd.to_datetime(df_sorted["timestamp"])
                df_sorted["window_start"] = df_sorted["timestamp_1h"].dt.floor("1h")

                # Group by 1-hour windows and sum the throughput
                hourly_throughput = (
                    df_sorted.groupby("window_start").agg({"throughput": "sum"}).reset_index()
                )

                # Only show windows with actual throughput
                hourly_throughput = hourly_throughput[hourly_throughput["throughput"] > 0]

                if not hourly_throughput.empty:
                    # Convert to local timezone for display
                    hourly_throughput["local_window_start"] = (
                        hourly_throughput["window_start"]
                        .dt.tz_localize("UTC")
                        .dt.tz_convert(safe_timezone)
                    )

                    # Calculate y-axis range for better visibility
                    max_throughput = hourly_throughput["throughput"].max()
                    avg_throughput = hourly_throughput["throughput"].mean()
                    y_max = max(max_throughput * 1.1, 1)  # At least 1, with 10% padding

                    logger.info(
                        f"Throughput (1h windows): {len(hourly_throughput)} windows, max={max_throughput}, avg={avg_throughput:.1f}, y_max={y_max}"
                    )

                    fig6 = go.Figure()
                    fig6.add_trace(
                        go.Bar(
                            x=hourly_throughput["local_window_start"],
                            y=hourly_throughput["throughput"],
                            name="Executions Completed",
                            marker_color="#6f42c1",
                            hovertemplate="<b>Hourly Throughput</b><br>%{x}<br>Completions: %{y}<extra></extra>",
                        )
                    )

                    fig6.update_layout(
                        title={
                            "text": "Execution Throughput (Hourly Windows)",
                            "x": 0.5,
                            "xanchor": "center",
                        },
                        xaxis_title=get_chart_axis_label(safe_timezone),
                        yaxis_title="Executions Completed per Hour",
                        yaxis={"range": [0, y_max]},  # Dynamic range based on data
                        margin={"l": 40, "r": 40, "t": 60, "b": 40},
                        template="plotly_white",
                        height=350,
                        hovermode="x unified",
                        showlegend=False,
                    )
                    charts.append(
                        html.Div(
                            [
                                dcc.Graph(
                                    figure=fig6,
                                    config={
                                        "displayModeBar": False,
                                        "responsive": True,
                                    },
                                )
                            ],
                            className="mb-4",
                        )
                    )
                    logger.info(
                        f"Added hourly throughput chart to charts list. Total charts so far: {len(charts)}"
                    )

            if not charts:
                # If no charts were created, show a general message
                time_period_name = {"day": "24 hours", "week": "7 days", "month": "30 days"}.get(
                    time_tab, "selected period"
                )

                logger.info("No charts were created - showing fallback message")
                return html.Div(
                    [
                        html.Div(
                            [
                                html.I(
                                    className="fas fa-exclamation-triangle fa-3x text-warning mb-3"
                                ),
                                html.H5(
                                    "No System Status Data Available",
                                    className="text-muted mb-3",
                                ),
                                html.P(
                                    f"No status logs found for the last {time_period_name}.",
                                    className="text-muted mb-2",
                                ),
                                html.Small(
                                    "This could indicate that the system monitoring is not active or no status changes occurred during this period.",
                                    className="text-muted",
                                ),
                            ],
                            className="text-center py-5",
                        ),
                    ],
                    className="border rounded p-4 bg-light",
                )

            logger.info(f"Returning {len(charts)} charts to display")
            return html.Div(charts)

        except requests.exceptions.RequestException as e:
            return html.Div(
                f"Error fetching chart data: {e}",
                className="text-center text-danger p-4",
            )

    @app.callback(
        [
            Output("status-tab-day", "className"),
            Output("status-tab-week", "className"),
            Output("status-tab-month", "className"),
            Output("status-time-tabs-store", "data"),
        ],
        [
            Input("status-tab-day", "n_clicks"),
            Input("status-tab-week", "n_clicks"),
            Input("status-tab-month", "n_clicks"),
        ],
    )
    def switch_status_time_tabs(_day_clicks, _week_clicks, _month_clicks):
        """Update the visual style of the active status tab and store the active tab."""
        ctx = callback_context
        if not ctx.triggered:
            return "nav-link active", "nav-link", "nav-link", "day"

        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if button_id == "status-tab-week":
            return "nav-link", "nav-link active", "nav-link", "week"
        if button_id == "status-tab-month":
            return "nav-link", "nav-link", "nav-link active", "month"
        return "nav-link active", "nav-link", "nav-link", "day"

    @app.callback(
        Output("status-countdown", "children"),
        [
            Input("status-countdown-interval", "n_intervals"),
            Input("refresh-status-btn", "n_clicks"),
        ],
        [
            State("active-tab-store", "data"),
        ],
    )
    def update_status_countdown(n_intervals, _refresh_clicks, active_tab):
        """Update the countdown timer display."""
        ctx = callback_context

        # If refresh button was clicked, reset to 60s
        if ctx.triggered and any("refresh-status-btn" in t["prop_id"] for t in ctx.triggered):
            return "60s"

        # If not on status tab, return 60s
        if active_tab != "status":
            return "60s"

        # Normal countdown progression
        if n_intervals is None:
            return "60s"

        # Calculate remaining seconds (60 second intervals)
        seconds_remaining = 60 - (n_intervals % 60)
        return f"{seconds_remaining}s"
