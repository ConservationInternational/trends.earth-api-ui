"""Optimized status dashboard callbacks with reduced API calls and enhanced caching."""

from datetime import datetime, timezone
import logging

from cachetools import TTLCache
from dash import Input, Output, State, callback_context, dcc, html, no_update

from ..utils.stats_visualizations import (
    create_execution_statistics_chart,
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


def update_comprehensive_status_data(
    *,
    token: str | None,
    api_environment: str | None,
    time_period: str | None,
    role: str | None,
    user_timezone: str | None = "UTC",
    force_refresh: bool = False,
):
    """Compatibility helper that mirrors the optimized comprehensive data fetch."""

    safe_timezone = get_safe_timezone(user_timezone)
    period = time_period or "day"

    return _fetch_comprehensive_data_with_cache(
        token=token or "",
        api_environment=api_environment or "",
        time_period=period,
        role=role or "",
        safe_timezone=safe_timezone,
        force_refresh=force_refresh,
    )


def update_status_charts_optimized(
    time_series_data,
    user_timezone: str | None = "UTC",
    time_period: str | None = None,
):
    """Compatibility helper that builds status charts using the optimized renderer."""

    safe_timezone = get_safe_timezone(user_timezone)
    period = time_period or "day"
    return _build_status_charts(time_series_data, safe_timezone, period)


def _format_display_time(value, safe_timezone, *, include_seconds=True):
    """Format a datetime or ISO timestamp for display in the user's timezone."""

    if not value:
        return None

    try:
        if isinstance(value, str):
            # Handle potential Z suffix
            value = value.replace("Z", "+00:00")
            dt_utc = datetime.fromisoformat(value)
        elif isinstance(value, datetime):
            dt_utc = value
        else:
            return None

        if dt_utc.tzinfo is None:
            dt_utc = dt_utc.replace(tzinfo=timezone.utc)
        else:
            dt_utc = dt_utc.astimezone(timezone.utc)

        local_time_str, tz_abbrev = format_local_time(
            dt_utc,
            safe_timezone,
            include_seconds=include_seconds,
        )
        return f"{local_time_str} {tz_abbrev}".strip()
    except (ValueError, TypeError):
        return None


def _build_request_cache_key(
    token: str,
    api_environment: str,
    time_period: str,
    role: str,
    safe_timezone: str,
) -> tuple:
    """Create a request-level cache key for comprehensive status data."""

    return (
        token or "",
        api_environment or "",
        time_period or "",
        role or "",
        safe_timezone or "",
    )


def _fetch_comprehensive_data_with_cache(
    *,
    token: str,
    api_environment: str,
    time_period: str,
    role: str,
    safe_timezone: str,
    force_refresh: bool,
):
    """Fetch comprehensive status data with an additional request-level cache layer."""

    cache_key = _build_request_cache_key(token, api_environment, time_period, role, safe_timezone)

    if not force_refresh:
        cached_result = _request_cache.get(cache_key)
        if cached_result is not None:
            cached_result.setdefault("meta", {})["request_cache_hit"] = True
            return cached_result

    comprehensive_data = StatusDataManager.fetch_comprehensive_status_page_data(
        token=token,
        api_environment=api_environment,
        time_period=time_period,
        role=role,
        force_refresh=force_refresh,
        user_timezone=safe_timezone,
    )

    if not comprehensive_data.get("error"):
        _request_cache[cache_key] = comprehensive_data

    return comprehensive_data


def register_callbacks(app):
    """Register optimized status dashboard callbacks with reduced API calls."""

    @app.callback(
        [
            Output("current-system-status-title", "children"),
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
        prevent_initial_call=False,
    )
    def update_time_independent_status_data(
        _n_intervals,
        _refresh_clicks,
        token,
        active_tab,
        user_timezone,
        role,
        api_environment,
    ):
        """
            Update time-independent status components (not affected by time period selection).

        This includes: status summary, deployment info, and swarm info.
            These elements are only refreshed by auto-refresh or manual refresh button, not by time period changes.
        """
        # Guard: Skip if not logged in
        if not token or role not in ["ADMIN", "SUPERADMIN"]:
            return (no_update, no_update, no_update, no_update, no_update)

        # Only update when status tab is active
        if active_tab != "status":
            return (no_update, no_update, no_update, no_update, no_update)

        # Get safe timezone
        safe_timezone = get_safe_timezone(user_timezone)

        # Check if this is a manual refresh
        ctx = callback_context
        is_manual_refresh = bool(
            ctx.triggered and ctx.triggered[0]["prop_id"].split(".")[0] == "refresh-status-btn"
        )

        # If manual refresh, invalidate status cache
        if is_manual_refresh:
            StatusDataManager.invalidate_cache("status")
            _request_cache.clear()
            _request_cache.clear()

        try:
            # Fetch time-independent data (use default "day" period for any stats needed)
            comprehensive_data = _fetch_comprehensive_data_with_cache(
                token=token,
                api_environment=api_environment,
                time_period="day",  # Default period, not used for time-independent data
                role=role,
                safe_timezone=safe_timezone,
                force_refresh=is_manual_refresh,
            )

            # Log performance metrics
            meta = comprehensive_data.get("meta", {})
            logger.info(
                f"Time-independent status data fetch completed: "
                f"{meta.get('total_api_calls', 0)} API calls, "
                f"cache_hit={meta.get('cache_hit', False)}"
            )

            # Extract data components
            status_data = comprehensive_data.get("status_data", {})
            deployment_data = comprehensive_data.get("deployment_data")
            swarm_data = comprehensive_data.get("swarm_data", {})
            # 1. Build status summary
            status_summary, last_updated_label = _build_status_summary(status_data, safe_timezone)

            # Prefer the actual fetch time for display so the header reflects refreshes
            fetch_time = meta.get("fetch_time") if isinstance(meta, dict) else None
            header_label = _format_display_time(fetch_time, safe_timezone) or last_updated_label

            current_status_title = (
                f"Current System Status ({header_label})"
                if header_label
                else "Current System Status"
            )

            # 2. Deployment info is already formatted
            deployment_info = deployment_data

            # 3. Swarm info and title
            swarm_info = swarm_data.get("info", html.Div("Swarm data unavailable"))
            swarm_cached_time = swarm_data.get("cached_time", "")
            swarm_title = html.H5(
                f"Docker Swarm Status{swarm_cached_time}", className="card-title mt-4"
            )
            return (
                current_status_title,
                status_summary,
                deployment_info,
                swarm_info,
                swarm_title,
            )

        except Exception as e:
            logger.error(f"Error in time-independent status update: {e}")
            error_msg = html.Div(
                f"Error loading status data: {e}", className="text-center text-danger"
            )
            return (
                "Current System Status",
                error_msg,
                error_msg,
                error_msg,
                html.H5("Error"),
            )

    @app.callback(
        [
            Output("stats-summary-cards", "children"),
            Output("stats-user-map", "children"),
            Output("stats-additional-charts", "children"),
        ],
        [
            Input("status-time-tabs-store", "data"),
            Input("status-auto-refresh-interval", "n_intervals"),
            Input("refresh-status-btn", "n_clicks"),
        ],
        [
            State("token-store", "data"),
            State("active-tab-store", "data"),
            State("role-store", "data"),
            State("api-environment-store", "data"),
            State("user-timezone-store", "data"),
        ],
        prevent_initial_call=False,
    )
    def update_time_dependent_stats(
        time_period,
        _n_intervals,
        _refresh_clicks,
        token,
        active_tab,
        role,
        api_environment,
        user_timezone,
    ):
        """
        Update time-dependent statistics components (affected by time period selection).

        This includes: user map, additional charts, etc.
        These elements are refreshed when the time period changes, auto-refresh, or manual refresh.
        """
        # Guard: Skip if not logged in or not SUPERADMIN
        if not token or role != "SUPERADMIN":
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
            return (permission_msg, permission_msg, [permission_msg])

        # Only update when status tab is active
        if active_tab != "status":
            return (no_update, no_update, no_update)

        # Check if this is a manual refresh
        ctx = callback_context
        is_manual_refresh = bool(
            ctx.triggered and ctx.triggered[0]["prop_id"].split(".")[0] == "refresh-status-btn"
        )

        # If manual refresh, invalidate status cache
        if is_manual_refresh:
            StatusDataManager.invalidate_cache("status")
            _request_cache.clear()

        safe_timezone = get_safe_timezone(user_timezone)

        # Set default time period if not provided
        if not time_period:
            time_period = "day"

        try:
            # Fetch time-dependent stats data
            comprehensive_data = _fetch_comprehensive_data_with_cache(
                token=token,
                api_environment=api_environment,
                time_period=time_period,
                role=role,
                safe_timezone=safe_timezone,
                force_refresh=is_manual_refresh,
            )
            # Log performance metrics
            meta = comprehensive_data.get("meta", {})
            logger.info(
                f"Time-dependent stats fetch completed for {time_period}: "
                f"{meta.get('total_api_calls', 0)} API calls, "
                f"cache_hit={meta.get('cache_hit', False)}"
            )

            # Extract data components
            status_data = comprehensive_data.get("status_data") or {}
            stats_data = comprehensive_data.get("stats_data") or {}

            # Build time-dependent stats components
            if not stats_data.get("error"):
                (
                    stats_cards,
                    user_map,
                    additional_charts,
                ) = _build_stats_components(
                    stats_data,
                    status_data,
                    comprehensive_data.get("time_series_data"),
                    user_timezone,
                    time_period,
                )
            else:
                error_msg = html.Div(
                    [
                        html.P("Statistics unavailable.", className="text-muted text-center"),
                        html.Small(
                            f"Error: {stats_data.get('message', 'Unknown error')}",
                            className="text-muted text-center d-block",
                        ),
                    ],
                    className="p-4",
                )
                stats_cards = html.Div()
                user_map = error_msg
                additional_charts = [error_msg]

            return (stats_cards, user_map, additional_charts)

        except Exception as e:
            logger.error(f"Error in time-dependent stats update: {e}")
            error_msg = html.Div(
                f"Error loading statistics: {e}", className="text-center text-danger"
            )
            return (html.Div(), error_msg, [error_msg])

    # Register additional status callbacks
    _register_additional_status_callbacks(app)


def _format_count(value):
    """Format numeric values with thousands separators."""

    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)


def _summary_card_column(label, value):
    """Build a column containing a summary card."""

    return html.Div(
        html.Div(
            [
                html.Div(label, className="text-muted small mb-1"),
                html.Div(_format_count(value), className="h3 mb-0 fw-bold"),
            ],
            className="p-3 bg-light rounded text-center h-100",
        ),
        className="col-md-4 col-sm-12",
    )


def _metric_column(label, value, *, value_class="h5 mb-0", container_class="col text-center"):
    """Build a metric column with consistent styling."""

    return html.Div(
        [
            html.Div(label, className="text-muted small mb-1"),
            html.Div(_format_count(value), className=value_class),
        ],
        className=container_class,
    )


def _build_status_summary(status_data, safe_timezone):
    """Build the status summary component from status data."""
    if not status_data or status_data.get("summary") != "SUCCESS":
        return get_fallback_summary(), None

    latest_status = status_data.get("latest_status", {})
    if not latest_status:
        return html.Div("No status data available.", className="text-center text-muted"), None

    # Extract execution counts
    executions_ready = latest_status.get("executions_ready", 0)
    executions_running = latest_status.get("executions_running", 0)
    executions_finished = latest_status.get("executions_finished", 0)
    executions_failed = latest_status.get("executions_failed", 0)
    executions_cancelled = latest_status.get("executions_cancelled", 0)
    executions_pending = latest_status.get("executions_pending", 0)

    active_total = executions_running + executions_ready + executions_pending
    completed_total = executions_finished + executions_failed + executions_cancelled
    total_executions = latest_status.get("executions_count", active_total + completed_total)

    # Extract user and script counts
    users_count = latest_status.get("users_count", 0)
    scripts_count = latest_status.get("scripts_count", 0)

    # Format timestamp (local time only)
    timestamp = latest_status.get("timestamp")
    last_updated_label = _format_display_time(timestamp, safe_timezone, include_seconds=True)

    # Build the summary layout organized by category
    summary_component = html.Div(
        [
            # === SUMMARY SECTION ===
            html.Div(
                [
                    html.H5("Overview", className="mb-3 border-bottom pb-2"),
                    html.Div(
                        [
                            _summary_card_column("Total Executions", total_executions),
                            _summary_card_column("Total Users", users_count),
                            _summary_card_column("Total Scripts", scripts_count),
                        ],
                        className="row g-3",
                    ),
                ],
                className="mb-4",
            ),
            html.Div(
                [
                    html.H5("Executions", className="mb-3 border-bottom pb-2"),
                    html.Div(
                        [
                            html.H6("Active", className="text-muted mb-2"),
                            html.Div(
                                [
                                    _metric_column("Running", executions_running),
                                    _metric_column("Ready", executions_ready),
                                    _metric_column("Pending", executions_pending),
                                    _metric_column(
                                        "Total",
                                        active_total,
                                        value_class="h4 mb-0 fw-bold text-success",
                                    ),
                                ],
                                className="row mb-3",
                            ),
                        ],
                        className="mb-3",
                    ),
                    html.Div(
                        [
                            html.H6("Completed", className="text-muted mb-2"),
                            html.Div(
                                [
                                    _metric_column("Finished", executions_finished),
                                    _metric_column(
                                        "Failed",
                                        executions_failed,
                                        value_class="h5 mb-0 text-danger",
                                    ),
                                    _metric_column("Cancelled", executions_cancelled),
                                    _metric_column(
                                        "Total",
                                        completed_total,
                                        value_class="h4 mb-0 fw-bold",
                                    ),
                                ],
                                className="row mb-3",
                            ),
                        ],
                        className="mb-3",
                    ),
                ],
                className="mb-4",
            ),
        ]
    )

    return summary_component, last_updated_label


def _build_stats_components(
    stats_data,
    status_data,
    time_series_data,
    user_timezone="UTC",
    ui_period=None,
):
    """Build the enhanced statistics components."""

    if not stats_data or stats_data.get("error"):
        error_component = html.Div(
            [
                html.P("Statistics unavailable.", className="text-muted text-center"),
                html.Small(
                    f"Error: {stats_data.get('message', 'Unknown error')}"
                    if stats_data
                    else "No statistics available for the selected period.",
                    className="text-muted text-center d-block",
                ),
            ],
            className="p-4",
        )
        return html.Div(), error_component, [error_component]

    user_stats = stats_data.get("user_stats")
    execution_stats = stats_data.get("execution_stats")
    scripts_count = stats_data.get("scripts_count", 0)

    # Add scripts count to latest status so downstream visualizations stay in sync
    latest_status = status_data.get("latest_status", {})
    latest_status["scripts_count"] = scripts_count

    stats_cards = html.Div()  # Dashboard summary cards removed as duplicative
    user_map = create_user_geographic_map(user_stats)
    status_time_series = (
        time_series_data.get("data") if isinstance(time_series_data, dict) else time_series_data
    )

    additional_charts = create_execution_statistics_chart(
        execution_stats,
        status_time_series,
        title_suffix="",
        user_timezone=user_timezone,
    ) + create_user_statistics_chart(
        user_stats,
        title_suffix="",
        user_timezone=user_timezone,
        status_time_series=status_time_series,
        ui_period=ui_period,
    )

    return stats_cards, user_map, additional_charts


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


# Alias for backward compatibility with tests
register_optimized_callbacks = register_callbacks
