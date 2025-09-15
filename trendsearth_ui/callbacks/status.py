"""Optimized status dashboard callbacks with reduced API calls and enhanced caching."""

from datetime import datetime
import logging

from cachetools import TTLCache
from dash import Input, Output, State, callback_context, dcc, html, no_update

from ..utils.stats_visualizations import (
    create_execution_statistics_chart,
    create_system_overview,
    create_user_geographic_map,
    create_user_statistics_chart,
)
from ..utils.status_data_manager import StatusDataManager
from ..utils.status_helpers import get_fallback_summary
from ..utils.timezone_utils import (
    convert_utc_to_local,
    format_local_time,
    get_chart_axis_label,
    get_safe_timezone,
)

logger = logging.getLogger(__name__)

# Request-level cache for sharing data between callbacks
_request_cache = TTLCache(maxsize=20, ttl=30)  # 30-second TTL for request-level sharing


def register_callbacks(app):
    """Register optimized status dashboard callbacks with reduced API calls."""

    @app.callback(
        [
            Output("status-summary", "children"),
            Output("deployment-info-summary", "children"),
            Output("swarm-info-summary", "children"),
            Output("swarm-status-title", "children"),
            Output("system-overview-content", "children"),
            Output("stats-summary-cards", "children"),
            Output("stats-user-map", "children"),
            Output("stats-additional-charts", "children"),
        ],
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
            State("api-environment-store", "data"),
        ],
        prevent_initial_call=False,
    )
    def update_comprehensive_status_data(
        _n_intervals,
        _refresh_clicks,
        time_period,
        token,
        active_tab,
        user_timezone,
        role,
        api_environment,
    ):
        """
        Update all status components in a single optimized callback.

        This consolidates multiple separate callbacks to minimize API calls
        and improve page load performance.
        """
        # Guard: Skip if not logged in
        if not token or role not in ["ADMIN", "SUPERADMIN"]:
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

        # Only update when status tab is active
        if active_tab != "status":
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

        # Get safe timezone
        safe_timezone = get_safe_timezone(user_timezone)

        # Check if this is a manual refresh
        ctx = callback_context
        is_manual_refresh = bool(
            ctx.triggered and ctx.triggered[0]["prop_id"].split(".")[0] == "refresh-status-btn"
        )

        # Set default time period if not provided
        if not time_period:
            time_period = "day"

        try:
            # Use comprehensive data fetching to minimize API calls
            comprehensive_data = StatusDataManager.fetch_comprehensive_status_page_data(
                token=token,
                api_environment=api_environment,
                time_period=time_period,
                role=role,
                force_refresh=is_manual_refresh,
            )

            # Log performance metrics
            meta = comprehensive_data.get("meta", {})
            logger.info(
                f"Status page data fetch completed: "
                f"{meta.get('total_api_calls', 0)} API calls, "
                f"cache_hit={meta.get('cache_hit', False)}, "
                f"optimizations={len(meta.get('optimizations_applied', []))}"
            )

            # Extract data components
            status_data = comprehensive_data.get("status_data", {})
            deployment_data = comprehensive_data.get("deployment_data")
            swarm_data = comprehensive_data.get("swarm_data", {})
            stats_data = comprehensive_data.get("stats_data", {})

            # 1. Build status summary
            status_summary = _build_status_summary(status_data, safe_timezone)

            # 2. Deployment info is already formatted
            deployment_info = deployment_data

            # 3. Swarm info and title
            swarm_info = swarm_data.get("info", html.Div("Swarm data unavailable"))
            swarm_cached_time = swarm_data.get("cached_time", "")
            swarm_title = html.H5(
                f"Docker Swarm Status{swarm_cached_time}", className="card-title mt-4"
            )

            # 4. Stats components (only for SUPERADMIN)
            if role == "SUPERADMIN" and not stats_data.get("error"):
                system_overview, stats_cards, user_map, additional_charts = _build_stats_components(
                    stats_data, status_data
                )
            else:
                # Permission message for non-SUPERADMIN
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
                system_overview = permission_msg
                stats_cards = html.Div()  # Empty div
                user_map = permission_msg
                additional_charts = [permission_msg]

            return (
                status_summary,
                deployment_info,
                swarm_info,
                swarm_title,
                system_overview,
                stats_cards,
                user_map,
                additional_charts,
            )

        except Exception as e:
            logger.error(f"Error in comprehensive status update: {e}")
            error_msg = html.Div(
                f"Error loading status data: {e}", className="text-center text-danger"
            )
            return (
                error_msg,
                error_msg,
                error_msg,
                html.H5("Error"),
                error_msg,
                error_msg,
                error_msg,
                [error_msg],
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
    def update_status_charts_optimized(
        time_tab, _n_intervals, _refresh_clicks, token, user_timezone, api_environment, active_tab
    ):
        """
        Update status charts with optimized data fetching and progressive loading.

        This callback uses pre-fetched time series data when possible
        to reduce redundant API calls and implements progressive loading.
        """
        # Guard: Skip if not logged in
        if not token:
            return no_update

        # Only update when status tab is active
        if active_tab != "status":
            return no_update

        # Set default time period
        if not time_tab:
            time_tab = "day"

        # Get safe timezone
        safe_timezone = get_safe_timezone(user_timezone)

        # Check if this is a manual refresh
        ctx = callback_context
        is_manual_refresh = ctx.triggered and any(
            "refresh-status-btn" in t["prop_id"] for t in ctx.triggered
        )

        try:
            # Progressive loading: Show immediate feedback
            if (
                not is_manual_refresh
                and ctx.triggered
                and "status-time-tabs-store" in str(ctx.triggered)
            ):
                # For time period changes, show a quick transition placeholder
                time_period_name = {"day": "24 Hours", "week": "7 Days", "month": "30 Days"}.get(
                    time_tab, "Selected Period"
                )

                # Return a temporary loading state with the new time period
                return html.Div(
                    [
                        html.Div(
                            [
                                html.Div(className="skeleton-text skeleton-title mb-3"),
                                html.Div(
                                    f"Loading {time_period_name} data...",
                                    className="text-muted text-center p-4",
                                ),
                                html.Div(
                                    className="chart-responsive",
                                    children=[
                                        html.Div(
                                            className="placeholder-efficient",
                                            children="Fetching chart data...",
                                        )
                                    ],
                                ),
                            ],
                            className="lazy-load-content",
                        )
                    ]
                )

            # Try to get time series data from comprehensive cache first
            comprehensive_cache_key = StatusDataManager.get_cache_key(
                "comprehensive_status",
                api_environment=api_environment,
                time_period=time_tab,
                role="USER",  # Charts don't require SUPERADMIN
            )

            cached_comprehensive = StatusDataManager.get_cached_data(comprehensive_cache_key)
            if cached_comprehensive and not is_manual_refresh:
                time_series_data = cached_comprehensive.get("time_series_data", {}).get("data", [])
                logger.info(
                    "Using time series data from comprehensive cache for optimized rendering"
                )
            else:
                # Fetch time series data separately if not in comprehensive cache
                time_series_result = StatusDataManager.fetch_time_series_status_data(
                    token, api_environment, time_tab, force_refresh=is_manual_refresh
                )
                time_series_data = time_series_result.get("data", [])
                logger.info("Fetched fresh time series data for optimized charts")

            if not time_series_data:
                time_period_name = {"day": "24 hours", "week": "7 days", "month": "30 days"}.get(
                    time_tab, "selected period"
                )
                return html.Div(
                    [
                        html.Div(
                            [
                                html.I(className="fas fa-info-circle fa-2x text-info mb-3"),
                                html.H5("No Chart Data Available", className="text-muted mb-3"),
                                html.P(
                                    f"No status logs found for the last {time_period_name}.",
                                    className="text-muted mb-2",
                                ),
                                html.Small(
                                    "Charts will appear when status data becomes available.",
                                    className="text-muted",
                                ),
                            ],
                            className="text-center py-5",
                        ),
                    ],
                    className="border rounded p-4 bg-light",
                )

            # Build charts using optimized chart generation
            charts = _build_optimized_status_charts(time_series_data, safe_timezone, time_tab)

            # Wrap charts in lazy-load container for performance
            return html.Div(
                [
                    html.Div(
                        charts,
                        className="lazy-load-content loaded",
                    )
                ],
                className="chart-container",
            )

        except Exception as e:
            logger.error(f"Error in optimized status charts update: {e}")
            return html.Div(
                [
                    html.Div(
                        [
                            html.I(className="fas fa-exclamation-triangle fa-2x text-warning mb-3"),
                            html.H5("Chart Loading Error", className="text-danger mb-3"),
                            html.P(f"Unable to load chart data: {str(e)}", className="text-muted"),
                            html.Small("Please try refreshing the page.", className="text-muted"),
                        ],
                        className="text-center py-4",
                    )
                ],
                className="border rounded p-4 bg-light",
            )

    # Register additional status callbacks
    _register_additional_status_callbacks(app)


def _build_status_summary(status_data, safe_timezone):
    """Build the status summary component from status data."""
    if not status_data or status_data.get("summary") != "SUCCESS":
        return get_fallback_summary()

    latest_status = status_data.get("latest_status", {})
    if not latest_status:
        return html.Div("No status data available.", className="text-center text-muted")

    # Extract execution counts
    executions_ready = latest_status.get("executions_ready", 0)
    executions_running = latest_status.get("executions_running", 0)
    executions_finished = latest_status.get("executions_finished", 0)
    executions_failed = latest_status.get("executions_failed", 0)
    executions_cancelled = latest_status.get("executions_cancelled", 0)
    executions_pending = latest_status.get("executions_pending", 0)

    active_total = executions_running + executions_ready + executions_pending
    completed_total = executions_finished + executions_failed + executions_cancelled

    # Format timestamp
    timestamp = latest_status.get("timestamp", "")
    try:
        if timestamp:
            dt_utc = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            utc_time_str = dt_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
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

    # Build the summary layout
    return html.Div(
        [
            # Active Executions Section
            html.H5("Active Executions", className="text-center mb-3 text-muted"),
            html.Div(
                [
                    html.Div(
                        [
                            html.H6("Running", className="mb-2"),
                            html.P(str(executions_running), className="text-primary mb-1"),
                        ],
                        className="col-md-4 text-center",
                    ),
                    html.Div(
                        [
                            html.H6("Ready", className="mb-2"),
                            html.P(str(executions_ready), className="text-info mb-1"),
                        ],
                        className="col-md-4 text-center",
                    ),
                    html.Div(
                        [
                            html.H6("Pending", className="mb-2"),
                            html.P(str(executions_pending), className="text-warning mb-1"),
                        ],
                        className="col-md-4 text-center",
                    ),
                ],
                className="row mb-3",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.H5("Active Total", className="mb-2 text-muted"),
                            html.H3(str(active_total), className="text-success mb-1 fw-bold"),
                        ],
                        className="col-12 text-center",
                    ),
                ],
                className="row mb-4",
            ),
            # Completed Executions Section
            html.H5("Completed Executions", className="text-center mb-3 text-muted"),
            html.Div(
                [
                    html.Div(
                        [
                            html.H6("Finished", className="mb-2"),
                            html.P(str(executions_finished), className="text-success mb-1"),
                        ],
                        className="col-md-4 text-center",
                    ),
                    html.Div(
                        [
                            html.H6("Failed", className="mb-2"),
                            html.P(str(executions_failed), className="text-danger mb-1"),
                        ],
                        className="col-md-4 text-center",
                    ),
                    html.Div(
                        [
                            html.H6("Cancelled", className="mb-2"),
                            html.P(str(executions_cancelled), className="text-secondary mb-1"),
                        ],
                        className="col-md-4 text-center",
                    ),
                ],
                className="row mb-3",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.H5("Completed Total", className="mb-2 text-muted"),
                            html.H3(str(completed_total), className="text-info mb-1 fw-bold"),
                        ],
                        className="col-12 text-center",
                    ),
                ],
                className="row mb-4",
            ),
            # Summary Totals Section
            html.H5("Summary Totals", className="text-center mb-3 text-muted"),
            html.Div(
                [
                    html.Div(
                        [
                            html.H6("Total Executions", className="mb-2"),
                            html.P(
                                str(
                                    latest_status.get(
                                        "executions_count", active_total + completed_total
                                    )
                                ),
                                className="text-primary mb-1",
                            ),
                        ],
                        className="col-md-6 text-center",
                    ),
                    html.Div(
                        [
                            html.H6("Users", className="mb-2"),
                            html.P(
                                str(latest_status.get("users_count", 0)), className="text-info mb-1"
                            ),
                        ],
                        className="col-md-6 text-center",
                    ),
                ],
                className="row mb-4",
            ),
            # Last Updated Section
            html.Div(
                [
                    html.Div(
                        [
                            html.H6("Last Updated", className="mb-2"),
                            timestamp_display,
                        ],
                        className="col-12 text-center",
                    ),
                ],
                className="row mb-4",
            ),
        ]
    )


def _build_stats_components(stats_data, status_data):
    """Build the enhanced statistics components."""
    dashboard_stats = stats_data.get("dashboard_stats")
    user_stats = stats_data.get("user_stats")
    execution_stats = stats_data.get("execution_stats")
    scripts_count = stats_data.get("scripts_count", 0)

    # Add scripts count to latest status
    latest_status = status_data.get("latest_status", {})
    latest_status["scripts_count"] = scripts_count

    # Build components
    system_overview = create_system_overview(dashboard_stats, latest_status)
    stats_cards = html.Div()  # Dashboard summary cards removed as duplicative
    user_map = create_user_geographic_map(user_stats)
    additional_charts = create_user_statistics_chart(
        user_stats
    ) + create_execution_statistics_chart(execution_stats)

    return system_overview, stats_cards, user_map, additional_charts


def _build_status_charts(time_series_data, safe_timezone, _time_tab):
    """Build status charts from time series data (simplified version)."""
    import pandas as pd
    import plotly.graph_objects as go

    if not time_series_data:
        return []

    # Convert to DataFrame
    df = pd.DataFrame(time_series_data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Convert to local timezone
    local_timestamps = []
    for timestamp in df["timestamp"]:
        local_dt, tz_abbrev = convert_utc_to_local(timestamp, safe_timezone)
        local_timestamps.append(local_dt)

    df["local_timestamp"] = pd.to_datetime(local_timestamps)

    charts = []

    # Simple active executions chart
    if "executions_active" in df.columns:
        fig_active = go.Figure()
        fig_active.add_trace(
            go.Scatter(
                x=df["local_timestamp"],
                y=df["executions_active"],
                mode="lines",
                name="Active Executions",
                line={"color": "#ff6f00", "width": 3},
            )
        )
        fig_active.update_layout(
            title="Active Executions Over Time",
            xaxis_title=get_chart_axis_label(safe_timezone),
            yaxis_title="Active Executions",
            template="plotly_white",
            height=350,
        )
        charts.append(html.Div([dcc.Graph(figure=fig_active)], className="mb-4"))

    return charts


def _build_optimized_status_charts(time_series_data, safe_timezone, time_tab):
    """Build optimized status charts with better performance and reduced complexity."""
    from dash import dcc, html
    import pandas as pd
    import plotly.graph_objects as go

    if not time_series_data:
        return []

    # Convert to DataFrame efficiently
    df = pd.DataFrame(time_series_data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Convert to local timezone efficiently
    local_timestamps = []
    for timestamp in df["timestamp"]:
        local_dt, tz_abbrev = convert_utc_to_local(timestamp, safe_timezone)
        local_timestamps.append(local_dt)

    df["local_timestamp"] = pd.to_datetime(local_timestamps)

    charts = []

    # Create configuration for optimized rendering
    chart_config = {
        "displayModeBar": False,
        "responsive": True,
        "staticPlot": False,
        # Optimize for performance
        "scrollZoom": False,
        "doubleClick": False,
        "showTips": False,
        "displaylogo": False,
    }

    # Chart 1: Active Executions (Primary metric)
    if "executions_active" in df.columns:
        active_values = df["executions_active"].fillna(0)
        if active_values.max() > 0 or len(active_values) > 1:  # Only show if meaningful data
            fig_active = go.Figure()
            fig_active.add_trace(
                go.Scatter(
                    x=df["local_timestamp"],
                    y=active_values,
                    mode="lines+markers",
                    name="Active Executions",
                    line={"color": "#ff6f00", "width": 2},
                    marker={"size": 4, "color": "#ff6f00"},
                    hovertemplate="<b>Active Executions</b><br>%{x}<br>Count: %{y}<extra></extra>",
                )
            )

            fig_active.update_layout(
                title={
                    "text": "Active Executions Over Time",
                    "x": 0.5,
                    "xanchor": "center",
                    "font": {"size": 16},
                },
                xaxis_title=get_chart_axis_label(safe_timezone),
                yaxis_title="Number of Active Executions",
                template="plotly_white",
                height=300,  # Reduced height for better performance
                margin={"l": 40, "r": 40, "t": 60, "b": 40},
                hovermode="x unified",
                showlegend=False,
            )

            charts.append(
                html.Div(
                    [
                        dcc.Graph(
                            figure=fig_active,
                            config=chart_config,
                            className="chart-responsive",
                        )
                    ],
                    className="mb-4",
                )
            )

    # Chart 2: Execution Status Breakdown (if data available)
    status_fields = [
        "executions_running",
        "executions_ready",
        "executions_finished",
        "executions_failed",
    ]
    available_fields = [field for field in status_fields if field in df.columns]

    if len(available_fields) >= 2:  # Only show if we have multiple status types
        fig_status = go.Figure()

        colors = {
            "executions_running": "#1e88e5",
            "executions_ready": "#ffa726",
            "executions_finished": "#43a047",
            "executions_failed": "#e53935",
        }

        names = {
            "executions_running": "Running",
            "executions_ready": "Ready",
            "executions_finished": "Finished",
            "executions_failed": "Failed",
        }

        for field in available_fields:
            values = df[field].fillna(0)
            if values.max() > 0:  # Only add traces with actual data
                fig_status.add_trace(
                    go.Scatter(
                        x=df["local_timestamp"],
                        y=values,
                        mode="lines",
                        name=names.get(field, field),
                        line={"color": colors.get(field, "#666"), "width": 2},
                        hovertemplate=f"<b>{names.get(field, field)}</b><br>%{{x}}<br>Count: %{{y}}<extra></extra>",
                    )
                )

        if len(fig_status.data) > 0:  # Only show if we have data
            fig_status.update_layout(
                title={
                    "text": "Execution Status Breakdown",
                    "x": 0.5,
                    "xanchor": "center",
                    "font": {"size": 16},
                },
                xaxis_title=get_chart_axis_label(safe_timezone),
                yaxis_title="Number of Executions",
                template="plotly_white",
                height=300,
                margin={"l": 40, "r": 40, "t": 60, "b": 40},
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
                            figure=fig_status,
                            config=chart_config,
                            className="chart-responsive",
                        )
                    ],
                    className="mb-4",
                )
            )

    # Show helpful message if no charts were generated
    if not charts:
        time_period_name = {"day": "24 hours", "week": "7 days", "month": "30 days"}.get(
            time_tab, "selected period"
        )

        charts.append(
            html.Div(
                [
                    html.Div(
                        [
                            html.I(className="fas fa-chart-line fa-3x text-muted mb-3"),
                            html.H5("Chart Data Not Available", className="text-muted mb-3"),
                            html.P(
                                f"No meaningful chart data found for the last {time_period_name}.",
                                className="text-muted mb-2",
                            ),
                            html.Small(
                                "Charts will appear when execution activity is detected.",
                                className="text-muted",
                            ),
                        ],
                        className="text-center py-5",
                    ),
                ],
                className="border rounded p-4 bg-light mb-4",
            )
        )

    return charts


def _register_additional_status_callbacks(app):
    """Register additional status callbacks for optimized version."""
    from dash import Input, Output, State, callback_context

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
    def switch_status_time_tabs_optimized(_day_clicks, _week_clicks, _month_clicks):
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
    def update_status_countdown_optimized(n_intervals, _refresh_clicks, active_tab):
        """Update the countdown timer display with minimal processing."""
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
