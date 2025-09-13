"""Status dashboard callbacks."""

from datetime import datetime, timedelta, timezone
import logging

from cachetools import TTLCache
from dash import Input, Output, State, callback_context, dcc, html, no_update
import pandas as pd
import plotly.graph_objects as go
import requests

from ..config import get_api_base
from ..utils.stats_visualizations import (
    create_execution_statistics_chart,
    create_system_overview,
    create_user_geographic_map,
    create_user_statistics_chart,
)
from ..utils.status_data_manager import StatusDataManager
from ..utils.status_helpers import (
    fetch_deployment_info,  # noqa: F401 (used in tests)
    fetch_swarm_info,
    get_fallback_summary,  # Used by StatusDataManager
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
        is_manual_refresh = bool(
            ctx.triggered and ctx.triggered[0]["prop_id"].split(".")[0] == "refresh-status-btn"
        )

        # If this is a manual refresh, invalidate the StatusDataManager cache too for coordination
        if is_manual_refresh:
            try:
                cleared_count = StatusDataManager.invalidate_cache("status")
                logger.info(
                    f"Manual refresh: invalidated {cleared_count} StatusDataManager cache entries"
                )
            except Exception as e:
                logger.warning(f"Failed to invalidate StatusDataManager cache: {e}")

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
                        params={
                            "per_page": 1,  # Optimization: limit response size
                            "exclude": "metadata,logs",  # Optimization: exclude unnecessary fields
                        },
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

        # Fetch deployment info from status helpers
        deployment_info = fetch_deployment_info(api_environment, token)

        # Fetch Docker Swarm information using helper function
        swarm_info, swarm_cached_time = fetch_swarm_info(api_environment, token)

        # Create swarm title with cached timestamp
        swarm_title = html.H5(
            f"Docker Swarm Status{swarm_cached_time}", className="card-title mt-4"
        )

        # Use StatusDataManager for consolidated status data fetching
        try:
            status_result = StatusDataManager.fetch_consolidated_status_data(
                token, api_environment, force_refresh=is_manual_refresh
            )

            # Check if status endpoint is available
            if not status_result["status_endpoint_available"]:
                fallback_result = get_fallback_summary()
                set_cached_data("summary", fallback_result)
                set_cached_data("deployment", deployment_info)
                set_cached_data("swarm", swarm_info)
                return fallback_result, deployment_info, swarm_info, swarm_title

            # Check if we have valid status data
            if status_result["summary"] == "SUCCESS" and status_result["latest_status"]:
                latest_status = status_result["latest_status"]
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
                executions_ready = latest_status.get("executions_ready", 0)
                executions_running = latest_status.get("executions_running", 0)
                executions_finished = latest_status.get("executions_finished", 0)
                executions_failed = latest_status.get("executions_failed", 0)
                executions_cancelled = latest_status.get("executions_cancelled", 0)
                executions_pending = latest_status.get("executions_pending", 0)
                active_total = executions_running + executions_ready + executions_pending
                completed_total = executions_finished + executions_failed + executions_cancelled

                # Create summary layout with expected section headers
                summary_layout = html.Div(
                    [
                        # Active Executions Section
                        html.H5("Active Executions", className="text-center mb-3 text-muted"),
                        # First row: Individual statuses
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
                                        html.H6("Pending", className="mb-2"),
                                        html.P(
                                            str(executions_pending),
                                            className="text-warning mb-1",
                                        ),
                                    ],
                                    className="col-md-4 text-center",
                                ),
                            ],
                            className="row mb-3",
                        ),
                        # Second row: Active Total (prominent and centered)
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.H5("Active Total", className="mb-2 text-muted"),
                                        html.H3(
                                            str(active_total),
                                            className="text-success mb-1 fw-bold",
                                        ),
                                    ],
                                    className="col-12 text-center",
                                ),
                            ],
                            className="row mb-4",
                        ),
                        # Completed Executions Section
                        html.H5("Completed Executions", className="text-center mb-3 text-muted"),
                        # First row: Individual statuses
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
                                    className="col-md-4 text-center",
                                ),
                                html.Div(
                                    [
                                        html.H6("Failed", className="mb-2"),
                                        html.P(
                                            str(executions_failed),
                                            className="text-danger mb-1",
                                        ),
                                    ],
                                    className="col-md-4 text-center",
                                ),
                                html.Div(
                                    [
                                        html.H6("Cancelled", className="mb-2"),
                                        html.P(
                                            str(executions_cancelled),
                                            className="text-secondary mb-1",
                                        ),
                                    ],
                                    className="col-md-4 text-center",
                                ),
                            ],
                            className="row mb-3",
                        ),
                        # Second row: Completed Total (prominent and centered)
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.H5("Completed Total", className="mb-2 text-muted"),
                                        html.H3(
                                            str(completed_total),
                                            className="text-info mb-1 fw-bold",
                                        ),
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
                                                    "executions_count",
                                                    active_total + completed_total,
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
                                            str(latest_status.get("users_count", 0)),
                                            className="text-info mb-1",
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
                set_cached_data("summary", summary_layout)
                set_cached_data("deployment", deployment_info)
                set_cached_data("swarm", swarm_info)
                return summary_layout, deployment_info, swarm_info, swarm_title
            elif status_result["summary"] == "NO_DATA":
                no_data_result = html.Div(
                    "No status data available.", className="text-center text-muted"
                )
                set_cached_data("summary", no_data_result)
                set_cached_data("deployment", deployment_info)
                set_cached_data("swarm", swarm_info)
                return no_data_result, deployment_info, swarm_info, swarm_title
            else:
                # Handle API errors or request errors
                error_message = status_result.get("error", "Unknown error occurred")
                error_result = html.Div(
                    f"Error fetching status: {error_message}",
                    className="text-center text-danger",
                )
                set_cached_data("summary", error_result)
                set_cached_data("deployment", deployment_info)
                set_cached_data("swarm", swarm_info)
                return error_result, deployment_info, swarm_info, swarm_title
        except Exception as e:
            logger.error(f"Unexpected error in update_status_summary: {e}")
            error_result = html.Div(
                f"Error fetching status: {e}", className="text-center text-danger"
            )
            set_cached_data("summary", error_result)
            set_cached_data("deployment", deployment_info)
            set_cached_data("swarm", swarm_info)
            return error_result, deployment_info, swarm_info, swarm_title

    @app.callback(
        Output("system-overview-content", "children"),
        Output("stats-summary-cards", "children"),
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
            return no_update, no_update, no_update, no_update

        # Only update when status tab is active to avoid unnecessary API calls
        if active_tab != "status":
            return no_update, no_update, no_update, no_update

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
            return permission_msg, permission_msg, permission_msg, [permission_msg]

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

        # Coordinate cache invalidation across different cache systems
        if is_manual_refresh:
            try:
                cleared_count = StatusDataManager.invalidate_cache("stats")
                logger.info(
                    f"Manual refresh: invalidated {cleared_count} StatusDataManager stats cache entries"
                )
            except Exception as e:
                logger.warning(f"Failed to invalidate StatusDataManager stats cache: {e}")

        cache_key = f"stats_summary_{api_period}"
        if not is_manual_refresh and not is_time_period_change:
            cached_statistics = _stats_cache.get(cache_key)
            if cached_statistics is not None:
                return cached_statistics

        # Use StatusDataManager for consolidated data fetching
        try:
            # Get consolidated status data first for latest_status
            status_result = StatusDataManager.fetch_consolidated_status_data(
                token, api_environment, force_refresh=is_manual_refresh
            )

            # Check if status endpoint is available
            if not status_result["status_endpoint_available"]:
                return (
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                )

            # Get consolidated stats data
            stats_result = StatusDataManager.fetch_consolidated_stats_data(
                token, api_environment, time_period, role, force_refresh=is_manual_refresh
            )

            # Check if user has required permissions
            if stats_result.get("requires_superadmin"):
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
                return permission_msg, permission_msg, permission_msg, [permission_msg]

            # Check if we have valid status and stats data
            if (
                status_result["summary"] == "SUCCESS"
                and status_result["latest_status"]
                and not stats_result.get("error")
            ):
                latest_status = status_result["latest_status"]
                dashboard_stats = stats_result["dashboard_stats"]
                user_stats = stats_result["user_stats"]
                execution_stats = stats_result["execution_stats"]
                scripts_count = stats_result["scripts_count"]

                # Debug logging to see what we actually get
                logger.info(f"Dashboard stats type: {type(dashboard_stats)}")
                logger.info(f"User stats type: {type(user_stats)}")
                logger.info(f"Execution stats type: {type(execution_stats)}")

                if isinstance(dashboard_stats, dict):
                    logger.info(f"Dashboard stats keys: {list(dashboard_stats.keys())}")
                    # Log available sections to ensure we're utilizing all data
                    data_section = dashboard_stats.get("data", {})
                    if isinstance(data_section, dict):
                        available_sections = list(data_section.keys())
                        logger.info(f"Available dashboard sections: {available_sections}")

                        # Log summary of each section to understand data completeness
                        for section in available_sections:
                            section_data = data_section.get(section, {})
                            if isinstance(section_data, dict):
                                section_keys = list(section_data.keys())
                                logger.info(f"Dashboard {section} section keys: {section_keys}")
                            else:
                                logger.info(
                                    f"Dashboard {section} section type: {type(section_data)}"
                                )
                if isinstance(user_stats, dict):
                    logger.info(f"User stats keys: {list(user_stats.keys())}")
                if isinstance(execution_stats, dict):
                    logger.info(f"Execution stats keys: {list(execution_stats.keys())}")

                # Format and cache the enhanced statistics with period-specific key
                # Add scripts count to latest status
                latest_status["scripts_count"] = scripts_count

                system_overview = create_system_overview(dashboard_stats, latest_status)
                # Dashboard summary cards removed as they are duplicative with system overview
                user_map = create_user_geographic_map(user_stats)
                additional_charts = create_user_statistics_chart(
                    user_stats
                ) + create_execution_statistics_chart(execution_stats)

                _stats_cache[cache_key] = (
                    system_overview,
                    html.Div(),  # Empty div to replace removed dashboard summary cards
                    user_map,
                    additional_charts,
                )

                return (
                    system_overview,
                    html.Div(),  # Empty div to replace removed dashboard summary cards
                    user_map,
                    additional_charts,
                )
            else:
                return (
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                )
        except Exception as e:
            logger.error(f"Unexpected error in update_status_and_statistics: {e}")
            return (
                no_update,
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
        # Debug: Log the received time_tab parameter
        logger.info(
            f"🕒 update_status_charts called with time_tab='{time_tab}', active_tab='{active_tab}'"
        )

        # Guard: Skip if not logged in (prevents execution after logout)
        if not token:
            logger.info("❌ update_status_charts: No token, returning no_update")
            return no_update

        # Only update when status tab is active to avoid unnecessary API calls
        if active_tab != "status":
            logger.info(
                f"❌ update_status_charts: Wrong tab '{active_tab}', expected 'status', returning no_update"
            )
            return no_update

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

        # Debug: Log the calculated time range
        days_diff = (end_time - start_time).days
        logger.info(
            f"📅 Calculated time range: {days_diff} days (from {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')})"
        )

        # Format for API query
        start_iso = start_time.isoformat()
        end_iso = end_time.isoformat()

        # Use StatusDataManager for optimized time series data fetching
        try:
            # Check if manual refresh was triggered
            ctx = callback_context
            is_manual_refresh = ctx.triggered and any(
                "refresh-status-btn" in t["prop_id"] for t in ctx.triggered
            )

            time_series_result = StatusDataManager.fetch_time_series_status_data(
                token, api_environment, time_tab, force_refresh=is_manual_refresh
            )

            if time_series_result.get("error"):
                return html.Div(
                    f"Error fetching chart data: {time_series_result['error']}",
                    className="text-center text-danger p-4",
                )

            status_data = time_series_result.get("data", [])

            if not status_data:
                # Get time period name for user feedback
                time_period_name = {"day": "24 hours", "week": "7 days", "month": "30 days"}.get(
                    time_tab, "selected period"
                )

                logger.warning(
                    f"❌ No status data received for time period '{time_tab}' ({time_period_name})"
                )

                return html.Div(
                    [
                        html.Div(
                            [
                                html.I(
                                    className="fas fa-exclamation-triangle fa-2x text-warning mb-3"
                                ),
                                html.H5("No Status Data Available", className="text-muted mb-3"),
                                html.P(
                                    f"No status logs found for the last {time_period_name}.",
                                    className="text-muted mb-2",
                                ),
                                html.Small(
                                    f"Requested time period: {time_tab}",
                                    className="text-muted",
                                ),
                            ],
                            className="text-center py-5",
                        ),
                    ],
                    className="border rounded p-4 bg-light",
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
            logger.info(
                f"📊 Status data received: {len(status_data)} records for time_tab='{time_tab}'"
            )
            if status_data:
                # Log time span of received data
                timestamps = [
                    record.get("timestamp") for record in status_data if record.get("timestamp")
                ]
                if timestamps:
                    first_timestamp = min(timestamps)
                    last_timestamp = max(timestamps)
                    logger.info(f"📅 Data time span: {first_timestamp} to {last_timestamp}")
                else:
                    logger.warning("⚠️ No timestamps found in status data")

                logger.info(f"🗂️ Available columns: {list(df.columns)}")
                logger.info(f"📝 Sample data (first record): {status_data[0]}")
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

            # First Priority Charts: Active Executions, Success Rate, and Throughput

            # Chart A: Active vs Inactive Executions
            if "executions_active" in df.columns:
                # Add text header
                charts.append(
                    html.Div(
                        [
                            html.H5(
                                "Active Executions Trend", className="text-center mb-3 text-primary"
                            ),
                        ],
                        className="mb-2",
                    )
                )

                # Calculate inactive executions
                df["executions_inactive"] = (
                    df["executions_finished"] + df["executions_failed"] + df["executions_cancelled"]
                )

                fig_active = go.Figure()
                fig_active.add_trace(
                    go.Scatter(
                        x=df["local_timestamp"],
                        y=df["executions_active"],
                        mode="lines",
                        name="Active Executions",
                        line={"color": "#ff6f00", "width": 3},
                        fill="tonexty",
                        hovertemplate="<b>Active</b><br>%{x}<br>Count: %{y}<extra></extra>",
                    )
                )

                fig_active.update_layout(
                    xaxis_title=get_chart_axis_label(safe_timezone),
                    yaxis_title="Number of Active Executions",
                    margin={"l": 40, "r": 40, "t": 20, "b": 40},
                    template="plotly_white",
                    height=350,
                    hovermode="x unified",
                    showlegend=False,
                )
                charts.append(
                    html.Div(
                        [
                            dcc.Graph(
                                figure=fig_active,
                                config={
                                    "displayModeBar": False,
                                    "responsive": True,
                                },
                            )
                        ],
                        className="mb-4",
                    )
                )

            # Chart B: Success Rate Over Time (1-hour windows based on completion deltas)
            if all(
                field in df.columns
                for field in ["executions_finished", "executions_failed", "executions_cancelled"]
            ):
                # Add text header
                charts.append(
                    html.Div(
                        [
                            html.H5(
                                "Execution Success Rate (1-Hour Windows)",
                                className="text-center mb-3 text-primary",
                            ),
                        ],
                        className="mb-2",
                    )
                )

                # Sort by timestamp for proper delta calculation
                df_sorted = df.sort_values("timestamp").reset_index(drop=True)

                # Convert to numeric and fill NaN values before calculating deltas
                df_sorted["executions_finished"] = pd.to_numeric(
                    df_sorted["executions_finished"], errors="coerce"
                ).fillna(0)
                df_sorted["executions_failed"] = pd.to_numeric(
                    df_sorted["executions_failed"], errors="coerce"
                ).fillna(0)
                df_sorted["executions_cancelled"] = pd.to_numeric(
                    df_sorted["executions_cancelled"], errors="coerce"
                ).fillna(0)

                # Calculate deltas (new completions in each time period)
                df_sorted["finished_delta"] = df_sorted["executions_finished"].diff().fillna(0)
                df_sorted["failed_delta"] = df_sorted["executions_failed"].diff().fillna(0)
                df_sorted["cancelled_delta"] = df_sorted["executions_cancelled"].diff().fillna(0)

                # Remove negative deltas (data inconsistencies)
                df_sorted["finished_delta"] = df_sorted["finished_delta"].clip(lower=0)
                df_sorted["failed_delta"] = df_sorted["failed_delta"].clip(lower=0)
                df_sorted["cancelled_delta"] = df_sorted["cancelled_delta"].clip(lower=0)

                # Create 1-hour time windows
                df_sorted["timestamp_1h"] = pd.to_datetime(df_sorted["timestamp"])
                df_sorted["window_start"] = df_sorted["timestamp_1h"].dt.floor("1h")

                # Group by 1-hour windows and sum the deltas
                window_stats = (
                    df_sorted.groupby("window_start")
                    .agg({"finished_delta": "sum", "failed_delta": "sum", "cancelled_delta": "sum"})
                    .reset_index()
                )

                # Calculate total completions and success rate for each window
                # Total completed = finished + failed + cancelled (all scripts that completed execution)
                window_stats["total_completions"] = (
                    window_stats["finished_delta"]
                    + window_stats["failed_delta"]
                    + window_stats["cancelled_delta"]
                )
                window_stats = window_stats[
                    window_stats["total_completions"] > 0
                ]  # Only windows with completions

                if not window_stats.empty:
                    # Success rate = only "finished" scripts / total completed scripts
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
                        f"Success rate (1h windows): {len(window_stats)} windows, rate range {min_rate:.2f}%-{max_rate:.2f}%, y-axis: {y_min:.2f}-{y_max:.2f}"
                    )

                    fig_success = go.Figure()
                    fig_success.add_trace(
                        go.Scatter(
                            x=window_stats["local_window_start"],
                            y=window_stats["success_rate"],
                            mode="lines",
                            name="Success Rate",
                            line={"color": "#00e676", "width": 3},
                            marker={"size": 8},
                            customdata=window_stats["total_completions"],
                            hovertemplate="<b>Success Rate (1h window)</b><br>%{x}<br>Rate: %{y:.2f}%<br>Total Completions: %{customdata}<extra></extra>",
                        )
                    )

                    fig_success.update_layout(
                        xaxis_title=get_chart_axis_label(safe_timezone),
                        yaxis_title="Success Rate (%)",
                        yaxis={"range": [y_min, y_max]},
                        margin={"l": 40, "r": 40, "t": 20, "b": 40},
                        template="plotly_white",
                        height=350,
                        hovermode="x unified",
                        showlegend=False,
                    )
                    charts.append(
                        html.Div(
                            [
                                dcc.Graph(
                                    figure=fig_success,
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
                        f"Added 1h-window success rate chart to charts list. Total charts so far: {len(charts)}"
                    )

            # Chart C: Execution Throughput (1-hour windows) with improved visibility
            if all(field in df.columns for field in ["executions_finished", "executions_failed"]):
                # Add text header
                charts.append(
                    html.Div(
                        [
                            html.H5(
                                "Execution Throughput (Hourly Windows)",
                                className="text-center mb-3 text-primary",
                            ),
                        ],
                        className="mb-2",
                    )
                )

                # Sort by timestamp for proper delta calculation
                df_sorted = df.sort_values("timestamp").reset_index(drop=True)

                # Convert to numeric and fill NaN values before calculating deltas
                df_sorted["executions_finished"] = pd.to_numeric(
                    df_sorted["executions_finished"], errors="coerce"
                ).fillna(0)
                df_sorted["executions_failed"] = pd.to_numeric(
                    df_sorted["executions_failed"], errors="coerce"
                ).fillna(0)

                # Calculate deltas (new completions in each time period)
                df_sorted["finished_delta"] = df_sorted["executions_finished"].diff().fillna(0)
                df_sorted["failed_delta"] = df_sorted["executions_failed"].diff().fillna(0)

                # Remove negative deltas (data inconsistencies)
                df_sorted["finished_delta"] = df_sorted["finished_delta"].clip(lower=0)
                df_sorted["failed_delta"] = df_sorted["failed_delta"].clip(lower=0)

                # Create 1-hour time windows
                df_sorted["timestamp_1h"] = pd.to_datetime(df_sorted["timestamp"])
                df_sorted["window_start"] = df_sorted["timestamp_1h"].dt.floor("1h")

                # Group by 1-hour windows and sum the deltas (total completions)
                hourly_throughput = (
                    df_sorted.groupby("window_start")
                    .agg({"finished_delta": "sum", "failed_delta": "sum"})
                    .reset_index()
                )

                # Calculate total throughput (finished + failed)
                hourly_throughput["throughput"] = (
                    hourly_throughput["finished_delta"] + hourly_throughput["failed_delta"]
                )

                # Only keep windows with actual throughput
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

                    fig_throughput = go.Figure()
                    fig_throughput.add_trace(
                        go.Bar(
                            x=hourly_throughput["local_window_start"],
                            y=hourly_throughput["throughput"],
                            name="Executions Completed",
                            marker_color="#3f51b5",
                            hovertemplate="<b>Hourly Throughput</b><br>%{x}<br>Completions: %{y}<extra></extra>",
                        )
                    )

                    fig_throughput.update_layout(
                        xaxis_title=get_chart_axis_label(safe_timezone),
                        yaxis_title="Executions Completed per Hour",
                        yaxis={"range": [0, y_max]},  # Dynamic range based on data
                        margin={"l": 40, "r": 40, "t": 20, "b": 40},
                        template="plotly_white",
                        height=350,
                        hovermode="x unified",
                        showlegend=False,
                    )
                    charts.append(
                        html.Div(
                            [
                                dcc.Graph(
                                    figure=fig_throughput,
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

            # Primary Charts: Most Important Metrics First

            # Add section header for primary analytics
            charts.append(
                html.Div(
                    [
                        html.Hr(className="my-4"),
                        html.H6("System Status Trends", className="text-center mb-4 text-muted"),
                    ],
                    className="mb-3",
                )
            )

            # Chart 1: Completed Execution Status Over Time (finished, failed, cancelled)
            # Updated to use brighter colors for better visibility - This should be first per issue #4
            completed_status_metrics = [
                {"field": "executions_finished", "name": "Finished", "color": "#43a047"},
                {"field": "executions_failed", "name": "Failed", "color": "#e53935"},
                {"field": "executions_cancelled", "name": "Cancelled", "color": "#8e24aa"},
            ]

            fig_completed_detailed = go.Figure()
            has_completed_detailed_data = False

            for metric in completed_status_metrics:
                field = metric["field"]
                if field in df.columns:
                    values = df[field].fillna(0)
                    has_completed_detailed_data = True

                    # Normalize to zero baseline by subtracting the initial value from each series
                    # This makes each line start from zero and show only changes from the starting point
                    if len(values) > 0:
                        initial_value = values.iloc[0]
                        normalized_values = values - initial_value
                    else:
                        normalized_values = values

                    logger.info(
                        f"Adding {field} to completed chart (normalized): original min={values.min()}, max={values.max()}, normalized min={normalized_values.min()}, max={normalized_values.max()}, unique_values={len(values.unique())}"
                    )

                    fig_completed_detailed.add_trace(
                        go.Scatter(
                            x=df["local_timestamp"],
                            y=normalized_values,
                            mode="lines",
                            name=metric["name"],
                            line={"color": metric["color"], "width": 3},
                            marker={"size": 6},
                            hovertemplate=f"<b>{metric['name']}</b><br>%{{x}}<br>Change from start: %{{y}}<extra></extra>",
                        )
                    )

            if has_completed_detailed_data:
                # Calculate y-axis range for completed executions (normalized to start from 0)
                all_completed_normalized_values = []
                for metric in completed_status_metrics:
                    field = metric["field"]
                    if field in df.columns:
                        values = df[field].fillna(0)
                        if len(values) > 0:
                            initial_value = values.iloc[0]
                            normalized_values = values - initial_value
                        else:
                            normalized_values = values
                        all_completed_normalized_values.extend(normalized_values.tolist())

                if all_completed_normalized_values:
                    min_val = min(all_completed_normalized_values)
                    max_val = max(all_completed_normalized_values)
                    # For normalized data, we know it starts at 0, so include 0 in the range
                    min_val = min(0, min_val)  # Ensure 0 is always visible
                    padding = max(1, abs(max_val - min_val) * 0.1)
                    y_min = min_val - padding
                    y_max = max_val + padding
                    logger.info(
                        f"Completed chart (normalized) y-axis range: {y_min} to {y_max} (data range: {min_val} to {max_val})"
                    )
                else:
                    y_min, y_max = -10, 10  # Default range for normalized data

                fig_completed_detailed.update_layout(
                    title={
                        "text": "Completed Execution Status Over Time (Changes from Start)",
                        "x": 0.5,
                        "xanchor": "center",
                    },
                    xaxis_title=get_chart_axis_label(safe_timezone),
                    yaxis_title="Change in Completed Executions (from start of period)",
                    yaxis={"range": [y_min, y_max]},
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
                                figure=fig_completed_detailed,
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
                    f"Added completed execution status chart as first chart. Total charts so far: {len(charts)}"
                )

            # Chart 2: Active Execution Status (Running, Ready, Pending)
            # Updated to use brighter colors for better visibility
            active_status_metrics = [
                {"field": "executions_running", "name": "Running", "color": "#1e88e5"},
                {"field": "executions_ready", "name": "Ready", "color": "#ffa726"},
                {
                    "field": "executions_pending",
                    "name": "Pending",
                    "color": "#8e24aa",
                },  # Preparing for API update
            ]

            fig_active_detailed = go.Figure()
            has_active_detailed_data = False

            for metric in active_status_metrics:
                field = metric["field"]
                if field in df.columns:
                    values = df[field].fillna(0)
                    # Show all active status lines to provide context, even if low values
                    has_active_detailed_data = True
                    logger.info(
                        f"Adding {field} to detailed active chart: min={values.min()}, max={values.max()}, unique_values={len(values.unique())}"
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

                    fig_active_detailed.add_trace(
                        go.Scatter(
                            x=x_data,
                            y=y_data,
                            mode="lines",
                            name=metric["name"],
                            line={"color": metric["color"], "width": 3},  # Thicker lines
                            marker={"size": 6},  # Larger markers
                            hovertemplate=f"<b>{metric['name']}</b><br>%{{x}}<br>Count: %{{y}}<extra></extra>",
                        )
                    )

            if has_active_detailed_data:
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
                        f"Detailed active chart y-axis range: {y_min} to {y_max} (data range: {min_val} to {max_val})"
                    )
                else:
                    y_min, y_max = 0, 150

                fig_active_detailed.update_layout(
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
                                figure=fig_active_detailed,
                                config={
                                    "displayModeBar": False,
                                    "responsive": True,
                                },
                            )
                        ],
                        className="mb-4",
                    )
                )

            # Add section header for supporting metrics
            charts.append(
                html.Div(
                    [
                        html.Hr(className="my-4"),
                        html.H6("Supporting Metrics", className="text-center mb-4 text-muted"),
                    ],
                    className="mb-3",
                )
            )

            # Chart removed: "Completed Executions Rate Over Time" was removed per issue #5 (duplicative)

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
                            mode="lines",
                            name="Total Executions",
                            line={"color": "#2196f3", "width": 3},
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

            # Chart 2: Scripts Over Time
            if "scripts_count" in df.columns:
                scripts_values = df["scripts_count"].fillna(0)
                if scripts_values.max() > 0:  # Only show if there's actual data
                    fig2 = go.Figure()
                    fig2.add_trace(
                        go.Scatter(
                            x=df["local_timestamp"],
                            y=scripts_values,
                            mode="lines",
                            name="Scripts",
                            line={"color": "#4caf50", "width": 2},
                            marker={"size": 4},
                            hovertemplate="<b>Scripts</b><br>%{x}<br>Count: %{y}<extra></extra>",
                        )
                    )

                    fig2.update_layout(
                        title={
                            "text": "Scripts Over Time",
                            "x": 0.5,
                            "xanchor": "center",
                        },
                        xaxis_title=get_chart_axis_label(safe_timezone),
                        yaxis_title="Scripts Count",
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

            # Chart removed: "Execution Activity Rate" was redundant with the new completed execution status chart

            if not charts:
                # If no charts were created, show a general message
                time_period_name = {"day": "24 hours", "week": "7 days", "month": "30 days"}.get(
                    time_tab, "selected period"
                )

                logger.warning(
                    f"⚠️ No charts were created for time_tab='{time_tab}', showing fallback message"
                )
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
                                    f"Requested time period: {time_tab} | API query: {start_iso} to {end_iso}",
                                    className="text-muted",
                                ),
                            ],
                            className="text-center py-5",
                        ),
                    ],
                    className="border rounded p-4 bg-light",
                )

            logger.info(f"✅ Returning {len(charts)} charts to display for time_tab='{time_tab}'")
            return html.Div(charts)

        except Exception as e:
            logger.error(f"Unexpected error in update_status_charts: {e}")
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

        # Debug: Log the callback trigger
        logger.info(f"🔄 switch_status_time_tabs called, triggered: {ctx.triggered}")

        if not ctx.triggered:
            logger.info("📅 switch_status_time_tabs: No trigger, returning default (day)")
            return "nav-link active", "nav-link", "nav-link", "day"

        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        logger.info(f"🔘 switch_status_time_tabs: button_id='{button_id}'")

        if button_id == "status-tab-week":
            logger.info("📅 switch_status_time_tabs: Setting week tab active, returning 'week'")
            return "nav-link", "nav-link active", "nav-link", "week"
        if button_id == "status-tab-month":
            logger.info("📅 switch_status_time_tabs: Setting month tab active, returning 'month'")
            return "nav-link", "nav-link", "nav-link active", "month"

        logger.info("📅 switch_status_time_tabs: Setting day tab active, returning 'day'")
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
