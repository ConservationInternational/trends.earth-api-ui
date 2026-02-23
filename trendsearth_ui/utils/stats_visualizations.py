"""Visualization utilities for stats charts and maps."""

import logging
import re
from typing import Any, Callable, Optional

from dash import dcc, html
import pandas as pd
import plotly.graph_objects as go

from .boundaries_utils import COUNTRY_NAME_OVERRIDES, CountryIsoResolver


def _build_message_block(
    message: str,
    *,
    detail: str | None = None,
    message_class: str = "text-muted text-center",
    detail_class: str = "text-muted text-center d-block",
    container_class: str = "p-4",
) -> html.Div:
    """Build a reusable message block for empty/error states."""

    children: list[Any] = [html.P(message, className=message_class)]
    if detail:
        children.append(html.Small(detail, className=detail_class))
    return html.Div(children, className=container_class)


def _resolve_error_detail(
    payload: dict[str, Any],
    *,
    forbidden_detail: str,
    unauthorized_detail: str,
    default_message: str,
) -> str:
    """Generate detailed error message based on API response payload."""

    status_code = payload.get("status_code")
    message = payload.get("message", "No data available")

    if status_code == 403:
        return forbidden_detail
    if status_code == 401:
        return unauthorized_detail
    return default_message.format(error_msg=message)


def _extract_stats_data(
    payload: Any,
    *,
    empty_response: html.Div,
    unexpected_response: html.Div,
    error_response_builder: Callable[[dict[str, Any]], html.Div],
    logger: logging.Logger,
    log_prefix: str,
) -> tuple[dict[str, Any] | None, html.Div | None]:
    """Normalize payload validation and data extraction for stats endpoints."""

    logger.info(f"{log_prefix}: Received data type: {type(payload)}")

    if not payload:
        return None, empty_response

    if isinstance(payload, list):
        logger.warning(f"{log_prefix}: Unexpected list payload; cannot parse data.")
        return None, unexpected_response

    if not isinstance(payload, dict):
        logger.warning(f"{log_prefix}: Unexpected payload type: {payload!r}")
        return None, unexpected_response

    if payload.get("error"):
        logger.warning(
            f"{log_prefix}: Error flag set with status {payload.get('status_code')} and message {payload.get('message')}"
        )
        return None, error_response_builder(payload)

    data = payload.get("data", {})
    logger.info(
        f"{log_prefix}: Data section keys: {list(data.keys()) if isinstance(data, dict) else 'No data section'}"
    )

    if not isinstance(data, dict):
        logger.warning(f"{log_prefix}: Data section is not a dict: {data!r}")
        return None, unexpected_response

    return data, None


_FALLBACK_COUNTRY_CODE_MAP_LOWER = {
    name.lower(): iso for name, iso in COUNTRY_NAME_OVERRIDES.items()
}
_FALLBACK_COUNTRY_CODE_VALUES = {iso.upper() for iso in COUNTRY_NAME_OVERRIDES.values()}
_ISO_SPLIT_PATTERN = re.compile(r"[^A-Za-z]+")


def _coerce_user_count(value: Any) -> int:
    """Safely coerce counts to non-negative integers."""

    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0
    if numeric <= 0:
        return 0
    return int(numeric)


def _extract_iso_candidate(country_name: str) -> str | None:
    """Extract a likely ISO-3 token from a free-form country string."""

    if not country_name:
        return None
    for token in _ISO_SPLIT_PATTERN.split(country_name):
        candidate = token.strip()
        if len(candidate) == 3 and candidate.isalpha():
            return candidate.upper()
    return None


def _resolve_country_iso(
    country_name: str,
    iso_resolver: Optional[CountryIsoResolver],
) -> tuple[str | None, str | None]:
    """Resolve a country name to an ISO code and display label using available data."""

    if not isinstance(country_name, str):
        return None, None

    candidate = country_name.strip()
    if not candidate:
        return None, None

    # Replace non-breaking spaces and collapse repeated whitespace so that variants using
    # non-standard spacing (e.g. S.&nbsp;Sudan) resolve consistently.
    normalized_candidate = " ".join(candidate.replace("\u00a0", " ").split())

    iso_candidate = _extract_iso_candidate(normalized_candidate)
    if iso_candidate:
        iso_candidate = iso_candidate.upper()
        if iso_resolver and iso_candidate in iso_resolver.iso_codes:
            display = iso_resolver.display_name(iso_candidate)
            return iso_candidate, display or candidate
        if iso_candidate in _FALLBACK_COUNTRY_CODE_VALUES:
            display = iso_resolver.display_name(iso_candidate) if iso_resolver else candidate
            return iso_candidate, display or candidate

    exact_iso = COUNTRY_NAME_OVERRIDES.get(normalized_candidate)
    if exact_iso:
        display = iso_resolver.display_name(exact_iso) if iso_resolver else candidate
        return exact_iso, display or candidate

    lowered_iso = _FALLBACK_COUNTRY_CODE_MAP_LOWER.get(normalized_candidate.lower())
    if lowered_iso:
        display = iso_resolver.display_name(lowered_iso) if iso_resolver else candidate
        return lowered_iso, display or candidate

    if iso_resolver:
        resolved_iso = iso_resolver.resolve(normalized_candidate)
        if resolved_iso:
            display = iso_resolver.display_name(resolved_iso)
            return resolved_iso, display or candidate

    if iso_candidate and iso_resolver is None:
        # Accept well-formed ISO-3 codes even when the resolver could not be
        # loaded. Use the raw country label as a fallback display name.
        return iso_candidate, candidate

    return None, None


def create_user_geographic_map(
    user_stats_data,
    iso_resolver: Optional[CountryIsoResolver] = None,
):
    """Render a choropleth map of user registrations by country."""

    import logging

    logger = logging.getLogger(__name__)

    empty_response = _build_message_block(
        "No geographic data available.", detail="No data provided."
    )
    unexpected_response = _build_message_block(
        "No geographic data available.", detail="Received unexpected data format from API."
    )

    def _build_error_response(payload: dict[str, Any]) -> html.Div:
        detail = _resolve_error_detail(
            payload,
            forbidden_detail="You need SUPERADMIN privileges to access geographic user data.",
            unauthorized_detail="Authentication failed. Please log in again.",
            default_message="Geographic user data unavailable: {error_msg}",
        )
        return _build_message_block("No geographic user data available.", detail=detail)

    try:
        data, message = _extract_stats_data(
            user_stats_data,
            empty_response=empty_response,
            unexpected_response=unexpected_response,
            error_response_builder=_build_error_response,
            logger=logger,
            log_prefix="User geographic map",
        )

        if message:
            return message

        if data is None:
            # Defensive guard; should not occur but keeps the return contract explicit.
            return _build_message_block(
                "No geographic user data available.",
                detail="User statistics response missing data section.",
            )

        geographic_data = data.get("geographic_distribution", {})
        logger.info(
            "User geographic map: Geographic section keys: %s",
            list(geographic_data.keys())
            if isinstance(geographic_data, dict)
            else "No geographic section",
        )

        if not geographic_data:
            return _build_message_block(
                "No geographic user data available.",
                detail=(
                    "User location data may not be configured, or you may need SUPERADMIN "
                    "privileges to access this data."
                ),
            )

        countries_data = geographic_data.get("countries", {})

        preview_items: list[tuple[Any, Any]] = []
        if countries_data:
            preview_items = list(countries_data.items())[:10]
            logger.info(
                "Countries data sample (%s entries): %s",
                len(countries_data),
                preview_items,
            )

        if isinstance(countries_data, list):
            # Some endpoints may return a list of country/count mappings instead of a dict
            extracted = {}
            for item in countries_data:
                if isinstance(item, dict):
                    country = item.get("country", item.get("country_code", ""))
                    count = item.get("user_count", item.get("count", 0))
                    if country:
                        extracted[country] = count
            countries_data = extracted
            preview_items = list(countries_data.items())[:10] if countries_data else []

        logger.info(
            "Final countries sample (%s entries): %s",
            len(countries_data),
            preview_items,
        )

        if not countries_data:
            return _build_message_block(
                "No country data available.",
                detail=(
                    "User country information not available for this period. This may be due to "
                    "insufficient privileges or no user data for the selected timeframe."
                ),
            )

        iso_counts_map: dict[str, int] = {}
        iso_labels: dict[str, str] = {}
        iso_aliases: dict[str, set[str]] = {}
        unmatched_countries: list[str] = []

        for country, count in countries_data.items():
            numeric_count = _coerce_user_count(count)
            if numeric_count == 0:
                continue

            iso_code, display_name = _resolve_country_iso(country, iso_resolver)
            if iso_code:
                iso_counts_map[iso_code] = iso_counts_map.get(iso_code, 0) + numeric_count
                if display_name:
                    iso_labels[iso_code] = display_name
                iso_aliases.setdefault(iso_code, set()).add(str(country))
            else:
                unmatched_countries.append(str(country))

        if unmatched_countries:
            logger.warning(
                "No ISO-3 code mapping found for countries: %s",
                ", ".join(sorted({name for name in unmatched_countries if name})),
            )

        if not iso_counts_map:
            if unmatched_countries:
                missing_names = sorted({name for name in unmatched_countries if name})
                missing_display = ", ".join(missing_names) if missing_names else "unknown countries"
                detail = (
                    "Countries without ISO-3 mapping: "
                    f"{missing_display}. Update the boundary metadata or mapping overrides."
                )
            else:
                detail = (
                    "Countries found: "
                    f"{', '.join(sorted(str(key) for key in countries_data))}. "
                    "These countries need ISO-3 code mapping."
                )

            return _build_message_block(
                "No mappable country data available.",
                detail=detail,
            )

        sorted_iso_entries = sorted(
            iso_counts_map.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        iso_countries = [iso for iso, _ in sorted_iso_entries]
        iso_counts = [iso_counts_map[iso] for iso in iso_countries]
        country_labels: list[str] = []
        for iso in iso_countries:
            display_name = iso_labels.get(iso)
            if not display_name and iso_resolver:
                display_name = iso_resolver.display_name(iso)
            if not display_name:
                display_name = iso
            aliases = {
                alias
                for alias in iso_aliases.get(iso, set())
                if alias and alias.lower() != display_name.lower()
            }
            alias_suffix = f" ({', '.join(sorted(aliases))})" if aliases else ""
            country_labels.append(f"{display_name}{alias_suffix}: {iso_counts_map[iso]} users")

        logger.info(
            "Mapped ISO sample (%s entries): %s",
            len(iso_counts_map),
            list(iso_counts_map.items())[:10],
        )

        fig = go.Figure(
            data=go.Choropleth(
                locations=iso_countries,
                z=iso_counts,
                locationmode="ISO-3",
                colorscale="Viridis",
                text=country_labels,
                hovertemplate="<b>%{text}</b><extra></extra>",
                colorbar={
                    "title": {"text": "Number of Users", "side": "right"},
                    "thickness": 15,
                    "len": 0.8,
                },
            )
        )

        fig.update_layout(
            geo={"showframe": False, "showcoastlines": True, "projection_type": "natural earth"},
            height=400,
            margin={"l": 0, "r": 0, "t": 40, "b": 0},
        )

        return dcc.Graph(figure=fig, config={"displayModeBar": False, "responsive": True})

    except Exception:  # pragma: no cover - safeguarding unexpected runtime failures
        logger.exception("Error creating geographic user map")
        return _build_message_block(
            "Error creating geographic map.",
            detail="An unexpected error occurred while rendering the map.",
            message_class="text-danger text-center",
        )


def create_execution_statistics_chart(
    execution_stats_data,
    status_time_series_data=None,
    title_suffix="",
    user_timezone="UTC",
    *,
    ui_period: str | None = None,
):
    """
    Create execution statistics charts showing trends and distribution.

    Args:
    execution_stats_data: Execution statistics data from the API or error response structure
    status_time_series_data: Optional status time series data providing instantaneous counts
        title_suffix: Additional text for the chart title
        user_timezone: User's timezone (IANA timezone name)
        ui_period: Selected UI period (day, week, month, year, all)

    Returns:
        list: List of chart components
    """
    import logging

    from .timezone_utils import convert_timestamp_series_to_local, get_chart_axis_label

    suffix_label = f" ({title_suffix})" if title_suffix else ""

    logger = logging.getLogger(__name__)
    normalized_period = (ui_period or "").lower()
    use_extended_cumulative = normalized_period in {"year", "all"}
    if normalized_period == "year":
        aggregation_label = "Weekly"
    elif normalized_period == "all":
        aggregation_label = "Monthly"
    else:
        aggregation_label = None

    try:
        # Debug logging - show what we actually received
        logger.info(f"Execution statistics: Received data type: {type(execution_stats_data)}")
        if execution_stats_data:
            logger.info(
                f"Execution statistics: Data keys: {list(execution_stats_data.keys()) if isinstance(execution_stats_data, dict) else 'Not a dict'}"
            )

        # Handle error response structure
        if not execution_stats_data:
            return [
                html.Div(
                    [
                        html.P(
                            "No execution statistics available.", className="text-muted text-center"
                        ),
                        html.Small(
                            "No data provided.",
                            className="text-muted text-center d-block",
                        ),
                    ],
                    className="p-4",
                )
            ]

        # Check if data is a list (unexpected format) and handle gracefully
        if isinstance(execution_stats_data, list):
            return [
                html.Div(
                    [
                        html.P(
                            "No execution statistics available.", className="text-muted text-center"
                        ),
                        html.Small(
                            "Received unexpected data format from API.",
                            className="text-muted text-center d-block",
                        ),
                    ],
                    className="p-4",
                )
            ]

        # Handle error response structure (should be a dict)
        if execution_stats_data.get("error", False):
            error_msg = execution_stats_data.get("message", "No data available")
            status_code = execution_stats_data.get("status_code", "unknown")

            if status_code == 403:
                error_detail = "You need SUPERADMIN privileges to access execution statistics."
            elif status_code == 401:
                error_detail = "Authentication failed. Please log in again."
            else:
                error_detail = f"Execution statistics unavailable: {error_msg}"

            return [
                html.Div(
                    [
                        html.P(
                            "No execution statistics available.", className="text-muted text-center"
                        ),
                        html.Small(
                            error_detail,
                            className="text-muted text-center d-block",
                        ),
                    ],
                    className="p-4",
                )
            ]

        data = execution_stats_data.get("data", {})
        logger.info(
            f"Execution statistics: Data section keys: {list(data.keys()) if isinstance(data, dict) else 'No data section'}"
        )

        if not data:
            return [
                html.Div(
                    [
                        html.P(
                            "No execution statistics available.", className="text-muted text-center"
                        ),
                        html.Small(
                            "Execution data may not be available for this period.",
                            className="text-muted text-center d-block",
                        ),
                    ],
                    className="p-4",
                )
            ]

        charts: list[Any] = []

        execution_charts: list[html.Div] = []

        status_colors = {
            "FINISHED": "#43a047",
            "FAILED": "#e53935",
            "CANCELLED": "#8e24aa",
            "RUNNING": "#1e88e5",
            "PENDING": "#ffa726",
            "READY": "#6d4c41",
        }

        # 1. Running executions from status time series data
        status_series = status_time_series_data or []
        if isinstance(status_series, dict):
            status_series = status_series.get("data", [])

        if status_series and not use_extended_cumulative:
            status_df = pd.DataFrame(status_series)

            if not status_df.empty and "timestamp" in status_df.columns:
                # Log original data for debugging
                logger.info(f"Status time series original data points: {len(status_df)}")
                if len(status_df) > 0:
                    logger.info(
                        f"Status timestamp range before conversion: {status_df['timestamp'].min()} to {status_df['timestamp'].max()}"
                    )

                status_df["timestamp"] = pd.to_datetime(status_df["timestamp"], errors="coerce")

                # Log after datetime conversion
                before_dropna = len(status_df)
                status_df = (
                    status_df.dropna(subset=["timestamp"])
                    .sort_values("timestamp")
                    .reset_index(drop=True)
                )
                after_dropna = len(status_df)

                if before_dropna != after_dropna:
                    logger.warning(
                        f"Status time series: Dropped {before_dropna - after_dropna} rows with invalid timestamps"
                    )

                if len(status_df) > 0:
                    logger.info(
                        f"Status timestamp range after datetime conversion: {status_df['timestamp'].min()} to {status_df['timestamp'].max()}"
                    )

                # Convert timestamps to local timezone
                status_df["timestamp"] = convert_timestamp_series_to_local(
                    status_df["timestamp"], user_timezone
                )

                # Log after timezone conversion
                if len(status_df) > 0:
                    logger.info(
                        f"Status timestamp range after timezone conversion to {user_timezone}: {status_df['timestamp'].min()} to {status_df['timestamp'].max()}"
                    )
                    logger.info(f"Status final data points: {len(status_df)}")

                in_process_columns = [
                    column
                    for column in [
                        "executions_ready",
                        "executions_pending",
                        "executions_running",
                    ]
                    if column in status_df.columns
                ]

                if in_process_columns:
                    fig_in_process = go.Figure()
                    for column in in_process_columns:
                        values = pd.to_numeric(status_df[column], errors="coerce").fillna(0)
                        status_name = column.replace("executions_", "").replace("_", " ").title()
                        fig_in_process.add_trace(
                            go.Scatter(
                                x=status_df["timestamp"],
                                y=values,
                                mode="lines",
                                name=status_name,
                                line={
                                    "color": status_colors.get(status_name.upper(), "#666666"),
                                    "width": 3,
                                },
                                line_shape="hv",
                                hovertemplate=(
                                    "<b>"
                                    + status_name
                                    + "</b><br>%{x}<br>Count: %{y}<extra></extra>"
                                ),
                            )
                        )

                    fig_in_process.update_layout(
                        xaxis_title=get_chart_axis_label(user_timezone),
                        yaxis_title="Number of Executions",
                        height=360,
                        hovermode="x unified",
                        legend={
                            "orientation": "h",
                            "yanchor": "bottom",
                            "y": 1.02,
                            "xanchor": "center",
                            "x": 0.5,
                        },
                        margin={"l": 40, "r": 40, "t": 60, "b": 40},
                        template="plotly_white",
                        xaxis={
                            "showgrid": True,
                            "type": "date",
                        },  # Ensure proper date axis handling
                        yaxis={"showgrid": True},
                    )

                    execution_charts.append(
                        html.Div(
                            [
                                html.H6(f"Running executions{suffix_label}"),
                                dcc.Graph(
                                    figure=fig_in_process,
                                    config={"displayModeBar": False, "responsive": True},
                                ),
                            ],
                            className="mb-3",
                        )
                    )
                else:
                    execution_charts.append(
                        _build_message_block(
                            "No in-progress execution data available.",
                            detail=(
                                "Status time series data did not include ready, pending, or running counts for this period."
                            ),
                        )
                    )
            else:
                execution_charts.append(
                    _build_message_block(
                        "No in-progress execution data available.",
                        detail="Status timestamps could not be parsed from the API response.",
                    )
                )
        elif not use_extended_cumulative:
            execution_charts.append(
                _build_message_block(
                    "No in-progress execution data available.",
                    detail="Status time series data was not provided for this period.",
                )
            )

        # 1. Completed executions (cumulative) from execution stats time series
        trends_data = data.get("time_series", [])
        if trends_data:
            flattened_data = []
            status_lookup: dict[str, str] = {}
            for entry in trends_data:
                row = {"date": entry.get("timestamp")}
                by_status = entry.get("by_status", {})
                for status_key, count in by_status.items():
                    normalized_key = status_key.lower()
                    row[normalized_key] = count
                    status_lookup.setdefault(normalized_key, status_key)
                flattened_data.append(row)

            df = pd.DataFrame(flattened_data)

            if not df.empty and "date" in df.columns:
                # Log original data for debugging
                logger.info(f"Original data points before processing: {len(df)}")
                if len(df) > 0:
                    logger.info(
                        f"Date range before conversion: {df['date'].min()} to {df['date'].max()}"
                    )

                df["date"] = pd.to_datetime(df["date"], errors="coerce")

                # Log after datetime conversion
                before_dropna = len(df)
                df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
                after_dropna = len(df)

                if before_dropna != after_dropna:
                    logger.warning(
                        f"Dropped {before_dropna - after_dropna} rows with invalid dates"
                    )

                if len(df) > 0:
                    logger.info(
                        f"Date range after datetime conversion: {df['date'].min()} to {df['date'].max()}"
                    )

                # Convert timestamps to local timezone
                df["date"] = convert_timestamp_series_to_local(df["date"], user_timezone)

                # Log after timezone conversion
                if len(df) > 0:
                    logger.info(
                        f"Date range after timezone conversion to {user_timezone}: {df['date'].min()} to {df['date'].max()}"
                    )
                    logger.info(f"Final data points: {len(df)}")

                status_columns = [col for col in df.columns if col != "date"]
                completed_columns = [
                    col for col in status_columns if col in {"finished", "failed", "cancelled"}
                ]

                def _display_name(column: str) -> str:
                    original = status_lookup.get(column, column)
                    return original.replace("_", " ").title()

                def _color_for(column: str) -> str:
                    original = status_lookup.get(column, column).upper()
                    return status_colors.get(original, "#666666")

                def _coerce_series(column_name: str) -> pd.Series:
                    return pd.to_numeric(df[column_name], errors="coerce").fillna(0)

                if completed_columns:
                    cumulative_series = {
                        column: _coerce_series(column).cumsum() for column in completed_columns
                    }

                    if use_extended_cumulative:
                        agg_suffix = (
                            f" ({aggregation_label} aggregation)" if aggregation_label else ""
                        )

                        line_columns = [
                            column
                            for column in ("finished", "failed", "cancelled")
                            if column in cumulative_series
                        ]

                        if not line_columns:
                            execution_charts.append(
                                _build_message_block(
                                    "No completed task data available.",
                                    detail=(
                                        "Execution statistics did not include finished, failed, or cancelled status counts for this period."
                                    ),
                                )
                            )
                        else:
                            figure = go.Figure()
                            for column in line_columns:
                                figure.add_trace(
                                    go.Scatter(
                                        x=df["date"],
                                        y=cumulative_series[column],
                                        mode="lines",
                                        name=_display_name(column),
                                        line={"color": _color_for(column), "width": 3},
                                        line_shape="hv",
                                        hovertemplate=(
                                            "<b>"
                                            + _display_name(column)
                                            + "</b><br>%{x}<br>Cumulative Count: %{y}<extra></extra>"
                                        ),
                                    )
                                )

                            figure.update_layout(
                                xaxis_title=get_chart_axis_label(user_timezone),
                                yaxis_title="Cumulative Executions",
                                height=360,
                                hovermode="x unified",
                                legend={
                                    "orientation": "h",
                                    "yanchor": "bottom",
                                    "y": 1.02,
                                    "xanchor": "center",
                                    "x": 0.5,
                                },
                                margin={"l": 40, "r": 40, "t": 60, "b": 40},
                                template="plotly_white",
                                xaxis={"showgrid": True, "type": "date"},
                                yaxis={"showgrid": True},
                                showlegend=True,
                            )

                            execution_charts.append(
                                html.Div(
                                    [
                                        html.H6(
                                            f"Cumulative completed tasks{suffix_label}{agg_suffix}"
                                        ),
                                        dcc.Graph(
                                            figure=figure,
                                            config={
                                                "displayModeBar": False,
                                                "responsive": True,
                                            },
                                        ),
                                    ],
                                    className="mb-3",
                                )
                            )
                    else:
                        fig_completed = go.Figure()
                        for column in completed_columns:
                            cumulative_values = cumulative_series[column]
                            fig_completed.add_trace(
                                go.Scatter(
                                    x=df["date"],
                                    y=cumulative_values,
                                    mode="lines",
                                    name=_display_name(column),
                                    line={"color": _color_for(column), "width": 3},
                                    line_shape="hv",
                                    hovertemplate=(
                                        "<b>"
                                        + _display_name(column)
                                        + "</b><br>%{x}<br>Cumulative Count: %{y}<extra></extra>"
                                    ),
                                )
                            )

                        fig_completed.update_layout(
                            xaxis_title=get_chart_axis_label(user_timezone),
                            yaxis_title="Cumulative Executions",
                            height=360,
                            hovermode="x unified",
                            legend={
                                "orientation": "h",
                                "yanchor": "bottom",
                                "y": 1.02,
                                "xanchor": "center",
                                "x": 0.5,
                            },
                            margin={"l": 40, "r": 40, "t": 60, "b": 40},
                            template="plotly_white",
                            xaxis={
                                "showgrid": True,
                                "type": "date",
                            },  # Ensure proper date axis handling
                            yaxis={"showgrid": True},
                        )

                        execution_charts.append(
                            html.Div(
                                [
                                    html.H6(f"Completed executions (cumulative){suffix_label}"),
                                    dcc.Graph(
                                        figure=fig_completed,
                                        config={"displayModeBar": False, "responsive": True},
                                    ),
                                ],
                                className="mb-3",
                            )
                        )
                else:
                    execution_charts.append(
                        _build_message_block(
                            "No cumulative execution data available.",
                            detail=(
                                "The execution statistics time series did not include finished, failed, or "
                                "cancelled statuses."
                            ),
                        )
                    )
            else:
                execution_charts.append(
                    _build_message_block(
                        "No execution trend data available.",
                        detail="Execution timestamps could not be parsed from the API response.",
                    )
                )

        if execution_charts:
            charts.extend(execution_charts)

        # 3. Execution Performance - handle actual data structure
        # API returns a list of task objects, not a dict with by_status
        task_performance_data = data.get("task_performance", [])
        logger.info(f"Task performance data: {task_performance_data}")

        if task_performance_data and isinstance(task_performance_data, list):
            # Create a chart showing tasks by execution count
            task_names = []
            execution_counts = []
            success_rates = []

            for task in task_performance_data[:10]:  # Top 10 tasks
                if isinstance(task, dict):
                    name = task.get("task", "Unknown")
                    total_execs = task.get("total_executions", 0)
                    success_rate = task.get("success_rate", 0)

                    task_names.append(name)
                    execution_counts.append(total_execs)
                    success_rates.append(success_rate)

            if task_names and execution_counts:
                # Create horizontal bar chart for task performance
                fig_tasks = go.Figure(
                    data=[
                        go.Bar(
                            x=execution_counts,
                            y=task_names,
                            orientation="h",
                            hovertemplate="<b>%{y}</b><br>Executions: %{x}<br>Success Rate: %{customdata}%<extra></extra>",
                            customdata=success_rates,
                        )
                    ]
                )

                fig_tasks.update_layout(
                    xaxis_title="Number of Executions",
                    height=max(300, len(task_names) * 30),
                    margin={"l": 40, "r": 40, "t": 40, "b": 40},
                )

                charts.append(
                    html.Div(
                        [
                            html.H6(f"Execution count{suffix_label}"),
                            dcc.Graph(
                                figure=fig_tasks,
                                config={"displayModeBar": False, "responsive": True},
                            ),
                        ],
                        className="mb-3",
                    )
                )

            # Create a second chart for task duration
            if task_names:
                durations = []
                for task in task_performance_data[:10]:  # Top 10 tasks
                    if isinstance(task, dict):
                        duration_str = task.get("avg_duration_minutes", "0")
                        try:
                            if isinstance(duration_str, str):
                                duration = float(duration_str)
                            else:
                                duration = float(duration_str) if duration_str else 0
                        except (ValueError, TypeError):
                            duration = 0
                        durations.append(duration)

                fig_duration = go.Figure(
                    data=[
                        go.Bar(
                            x=durations,
                            y=task_names,
                            orientation="h",
                            hovertemplate="<b>%{y}</b><br>Avg Duration: %{x:.1f} minutes<br>Success Rate: %{customdata}%<extra></extra>",
                            customdata=success_rates,
                            marker_color="#ff7043",
                        )
                    ]
                )

                fig_duration.update_layout(
                    xaxis_title="Average Duration (minutes)",
                    height=max(300, len(task_names) * 30),
                    margin={"l": 40, "r": 40, "t": 40, "b": 40},
                )

                charts.append(
                    html.Div(
                        [
                            html.H6(f"Execution duration{suffix_label}"),
                            dcc.Graph(
                                figure=fig_duration,
                                config={"displayModeBar": False, "responsive": True},
                            ),
                        ],
                        className="mb-3",
                    )
                )

                # Top 10 scripts by failure count with failure-rate bars
                failure_entries: list[dict[str, Any]] = []
                for task in task_performance_data:
                    if not isinstance(task, dict):
                        continue
                    total = task.get("total_executions", 0) or 0
                    rate = task.get("success_rate", 100)
                    try:
                        failure_rate = round(100 - float(rate), 1)
                    except (ValueError, TypeError):
                        failure_rate = 0.0
                    failures = round(total * failure_rate / 100)
                    if failures > 0:
                        failure_entries.append(
                            {
                                "task": task.get("task", "Unknown"),
                                "failure_rate": failure_rate,
                                "failures": failures,
                                "total": total,
                            }
                        )

                if failure_entries:
                    failure_entries.sort(key=lambda e: e["failures"], reverse=True)
                    top_failures = failure_entries[:10]
                    # Reverse so largest is at top of horizontal bar chart
                    top_failures.reverse()

                    fig_failure = go.Figure(
                        data=[
                            go.Bar(
                                x=[e["failure_rate"] for e in top_failures],
                                y=[e["task"] for e in top_failures],
                                orientation="h",
                                marker_color="#e53935",
                                hovertemplate=(
                                    "<b>%{y}</b><br>"
                                    "Failure rate: %{x:.1f}%<br>"
                                    "Failures: %{customdata[0]}<br>"
                                    "Total: %{customdata[1]}"
                                    "<extra></extra>"
                                ),
                                customdata=[[e["failures"], e["total"]] for e in top_failures],
                            )
                        ]
                    )

                    fig_failure.update_layout(
                        xaxis_title="Failure Rate (%)",
                        xaxis={"range": [0, 100]},
                        height=max(300, len(top_failures) * 30),
                        margin={"l": 40, "r": 40, "t": 40, "b": 40},
                        template="plotly_white",
                    )

                    charts.append(
                        html.Div(
                            [
                                html.H6(f"Top scripts by failure count{suffix_label}"),
                                dcc.Graph(
                                    figure=fig_failure,
                                    config={
                                        "displayModeBar": False,
                                        "responsive": True,
                                    },
                                ),
                            ],
                            className="mb-3",
                        )
                    )

        return (
            charts
            if charts
            else [
                html.Div(
                    [
                        html.P(
                            "No chart data available for this period.",
                            className="text-muted text-center",
                        ),
                        html.Small(
                            "This may be due to insufficient privileges, no data for the selected timeframe, or API access restrictions.",
                            className="text-muted text-center d-block",
                        ),
                    ],
                    className="p-4",
                )
            ]
        )

    except Exception as e:
        return [
            html.Div(
                [
                    html.P(
                        "Error creating execution statistics charts.",
                        className="text-danger text-center",
                    ),
                    html.Small(f"Error: {str(e)}", className="text-muted text-center d-block"),
                ],
                className="p-4",
            )
        ]


def create_top_users_chart(
    execution_stats_data: dict | None,
    title_suffix: str = "",
) -> list:
    """Create a horizontal bar chart of the top users by execution count.

    Args:
        execution_stats_data: Execution statistics dict as returned by the API
            (expects ``data.top_users``).
        title_suffix: Optional label appended to the chart title.

    Returns:
        list: Dash component(s) containing the chart, or an empty list.
    """
    suffix_label = f" ({title_suffix})" if title_suffix else ""

    if not execution_stats_data or not isinstance(execution_stats_data, dict):
        return []
    if execution_stats_data.get("error"):
        return []

    data = execution_stats_data.get("data", {})
    top_users_data = data.get("top_users", []) if isinstance(data, dict) else []
    if not top_users_data or not isinstance(top_users_data, list):
        return []

    user_names = []
    execution_counts = []
    for user_data in top_users_data[:10]:
        if isinstance(user_data, dict):
            name = user_data.get("name", user_data.get("email", "Unknown"))
            count = user_data.get("execution_count", user_data.get("count", 0))
            user_names.append(name)
            execution_counts.append(count)

    if not user_names or not execution_counts:
        return []

    fig_users = go.Figure(
        data=[
            go.Bar(
                x=execution_counts,
                y=user_names,
                orientation="h",
                hovertemplate="<b>%{y}</b><br>Executions: %{x}<extra></extra>",
            )
        ]
    )
    fig_users.update_layout(
        xaxis_title="Number of Executions",
        height=max(300, len(user_names) * 30),
        margin={"l": 40, "r": 40, "t": 40, "b": 40},
    )

    return [
        html.Div(
            [
                html.H6(f"Top users by activity{suffix_label}"),
                dcc.Graph(
                    figure=fig_users,
                    config={"displayModeBar": False, "responsive": True},
                ),
            ],
            className="mb-3",
        )
    ]


# ---------------------------------------------------------------------------
# Regex for extracting a version from a script slug or name.
#
# Matches patterns like:
#   "productivity-v2.1.0"  → "2.1.0"
#   "land_cover_1_2_3"     → "1.2.3"  (trailing _X_Y_Z)
#   "script-v10.0"         → "10.0"
#
def _parse_script_version(name: str) -> str | None:
    """Extract a dotted version string from a task name.

    Handles trailing dash-separated digit groups, e.g.
    ``time-series-2-2-2`` → ``2.2.2``.

    Returns the version as a dotted string or *None* if no version pattern is
    found.
    """
    if not name:
        return None

    parts = name.split("-")
    version_parts: list[str] = []
    for part in reversed(parts):
        if part.isdigit():
            version_parts.append(part)
        else:
            break
    if len(version_parts) >= 2:
        version_parts.reverse()
        return ".".join(version_parts)

    return None


def create_script_version_histogram(
    execution_stats_data: dict | None,
    title_suffix: str = "",
) -> list:
    """Create a histogram of execution script versions from task performance data.

    Parses version strings from the ``task`` field in ``task_performance``
    entries (already filtered by the user's selected time period) and weights
    each version by its ``total_executions`` count.

    Args:
        execution_stats_data: Execution statistics dict as returned by the API
            (expects ``data.task_performance`` with ``task`` and
            ``total_executions`` fields).
        title_suffix: Optional label appended to the chart title.

    Returns:
        list: Dash component(s) containing the histogram chart.
    """
    _logger = logging.getLogger(__name__)

    suffix_label = f" ({title_suffix})" if title_suffix else ""

    if not execution_stats_data or not isinstance(execution_stats_data, dict):
        return [
            _build_message_block(
                "No script version data available.",
                detail="Execution statistics were not provided.",
            )
        ]

    if execution_stats_data.get("error"):
        return []  # Execution chart already shows the error

    data = execution_stats_data.get("data", {})
    task_performance = data.get("task_performance", []) if isinstance(data, dict) else []

    if not task_performance:
        return [
            _build_message_block(
                "No script version data available.",
                detail="No task performance data for the selected period.",
            )
        ]

    try:
        version_executions: dict[str, int] = {}
        unparsed_executions = 0
        total_tasks = 0

        for entry in task_performance:
            if not isinstance(entry, dict):
                continue
            total_tasks += 1
            task = entry.get("task", "") or ""
            executions = int(entry.get("total_executions", 0))

            version = _parse_script_version(task)
            if version:
                version_executions[version] = version_executions.get(version, 0) + executions
            else:
                unparsed_executions += executions

        if not version_executions:
            return [
                _build_message_block(
                    "No version information found in script names.",
                    detail=(
                        f"Examined {total_tasks} scripts but could not parse "
                        f"a version from any slug."
                    ),
                )
            ]

        # Sort versions using tuple comparison for natural ordering
        def _version_sort_key(v: str):
            try:
                return tuple(int(p) for p in v.split("."))
            except ValueError:
                return (0,)

        sorted_versions = sorted(version_executions.keys(), key=_version_sort_key)
        counts = [version_executions[v] for v in sorted_versions]

        fig = go.Figure(
            data=[
                go.Bar(
                    x=sorted_versions,
                    y=counts,
                    marker_color="#1e88e5",
                    hovertemplate=("<b>Version %{x}</b><br>Executions: %{y}<extra></extra>"),
                )
            ]
        )

        fig.update_layout(
            xaxis_title="Script Version",
            yaxis_title="Number of Executions",
            height=360,
            margin={"l": 40, "r": 40, "t": 40, "b": 40},
            template="plotly_white",
            bargap=0.15,
        )

        total_execs = sum(counts)
        detail_parts = [f"{len(version_executions)} distinct versions, {total_execs:,} executions"]
        if unparsed_executions:
            detail_parts.append(
                f"{unparsed_executions:,} executions from scripts with no parseable version"
            )

        return [
            html.Div(
                [
                    html.H6(f"Execution script version distribution{suffix_label}"),
                    html.P(
                        "; ".join(detail_parts) + ".",
                        className="text-muted small mb-2",
                    ),
                    dcc.Graph(
                        figure=fig,
                        config={"displayModeBar": False, "responsive": True},
                    ),
                ],
                className="mb-3",
            )
        ]

    except Exception as e:
        _logger.error(f"Error creating script version histogram: {e}")
        return [
            html.Div(
                [
                    html.P(
                        "Error creating script version histogram.",
                        className="text-danger text-center",
                    ),
                    html.Small(f"Error: {str(e)}", className="text-muted text-center d-block"),
                ],
                className="p-4",
            )
        ]


def create_user_statistics_chart(
    user_stats_data,
    title_suffix="",
    user_timezone="UTC",
    *,
    status_time_series=None,
    ui_period=None,
):
    """
    Create user statistics charts showing registration trends.

    Args:
        user_stats_data: User statistics data from the API or error response structure
        title_suffix: Additional text for the chart title
        user_timezone: User's timezone (IANA timezone name)
        status_time_series: Optional status endpoint time series data for enhanced resolution
        ui_period: Selected UI period (day, week, month) used to determine target resolution

    Returns:
        list: List of chart components
    """
    from .timezone_utils import convert_timestamp_series_to_local, get_chart_axis_label

    suffix_label = f" ({title_suffix})" if title_suffix else ""
    target_freq = {
        "day": "15min",
        "week": "1h",
        "month": "1D",
    }.get(ui_period or "")

    logger = logging.getLogger(__name__)

    try:
        # Handle error response structure
        if not user_stats_data:
            return [
                html.Div(
                    [
                        html.P("No user statistics available.", className="text-muted text-center"),
                        html.Small(
                            "No data provided.",
                            className="text-muted text-center d-block",
                        ),
                    ],
                    className="p-4",
                )
            ]

        # Check if data is a list (unexpected format) and handle gracefully
        if isinstance(user_stats_data, list):
            return [
                html.Div(
                    [
                        html.P("No user statistics available.", className="text-muted text-center"),
                        html.Small(
                            "Received unexpected data format from API.",
                            className="text-muted text-center d-block",
                        ),
                    ],
                    className="p-4",
                )
            ]

        # Handle error response structure (should be a dict)
        if user_stats_data.get("error", False):
            error_msg = user_stats_data.get("message", "No data available")
            status_code = user_stats_data.get("status_code", "unknown")

            if status_code == 403:
                error_detail = "You need SUPERADMIN privileges to access user statistics."
            elif status_code == 401:
                error_detail = "Authentication failed. Please log in again."
            else:
                error_detail = f"User statistics unavailable: {error_msg}"

            return [
                html.Div(
                    [
                        html.P("No user statistics available.", className="text-muted text-center"),
                        html.Small(
                            error_detail,
                            className="text-muted text-center d-block",
                        ),
                    ],
                    className="p-4",
                )
            ]

        data = user_stats_data.get("data", {})

        if not data:
            return [
                html.Div(
                    "No user statistics available for this period.",
                    className="text-muted text-center p-4",
                )
            ]

        charts = []

        def _normalize_records(records):
            if not records:
                return None

            df = pd.DataFrame(records)
            if df.empty:
                return None

            time_col = None
            for candidate in ("timestamp", "date", "datetime"):
                if candidate in df.columns:
                    time_col = candidate
                    break

            if time_col is None:
                logger.info("Registration data missing timestamp column")
                return None

            df["timestamp"] = pd.to_datetime(df[time_col], errors="coerce")
            df = df.dropna(subset=["timestamp"]).sort_values("timestamp")

            if df.empty:
                return None

            if "new_users" not in df.columns:
                if "total_users" in df.columns:
                    df["new_users"] = (
                        pd.to_numeric(df["total_users"], errors="coerce").ffill().diff()
                    )
                    df.loc[df["new_users"].isna(), "new_users"] = pd.to_numeric(
                        df.loc[df["new_users"].isna(), "total_users"], errors="coerce"
                    ).fillna(0)
                elif "count" in df.columns:
                    df["new_users"] = pd.to_numeric(df["count"], errors="coerce")
                else:
                    logger.info("Registration data missing new_users column")
                    return None

            df["new_users"] = (
                pd.to_numeric(df["new_users"], errors="coerce").fillna(0).clip(lower=0)
            )

            return df[["timestamp", "new_users"]]

        def _derive_from_status(status_records):
            if not status_records:
                return None

            df_status = pd.DataFrame(status_records)
            if df_status.empty or "timestamp" not in df_status.columns:
                return None

            user_col = next(
                (
                    col
                    for col in [
                        "users_count",
                        "total_users",
                        "user_count",
                        "users",
                    ]
                    if col in df_status.columns
                ),
                None,
            )

            if user_col is None:
                return None

            df_status["timestamp"] = pd.to_datetime(df_status["timestamp"], errors="coerce")
            df_status[user_col] = pd.to_numeric(df_status[user_col], errors="coerce")
            df_status = df_status.dropna(subset=["timestamp", user_col]).sort_values("timestamp")

            if df_status.empty:
                return None

            df_status["new_users"] = df_status[user_col].diff().fillna(0)
            df_status["new_users"] = df_status["new_users"].clip(lower=0)

            return df_status[["timestamp", "new_users"]]

        def _choose_registration_df(primary_df, status_df):
            if primary_df is None or primary_df.empty:
                return status_df
            if status_df is None or status_df.empty:
                return primary_df

            if target_freq is None:
                return primary_df

            primary_diff = primary_df["timestamp"].diff().dropna()
            status_diff = status_df["timestamp"].diff().dropna()

            primary_min = primary_diff.min() if not primary_diff.empty else None
            status_min = status_diff.min() if not status_diff.empty else None

            if status_min is None:
                return primary_df
            if primary_min is None:
                return status_df

            return status_df if status_min < primary_min else primary_df

        # 1. New user registrations - enhanced to handle group_by data
        # Look for time series data first (when group_by parameter is used)
        time_series_data = data.get("time_series", [])
        trends_data = data.get("registration_trends", [])

        # Prefer time_series data if available (more detailed from group_by)
        chart_data = time_series_data if time_series_data else trends_data
        chart_title = f"New user registrations{suffix_label}"

        registration_df = _normalize_records(chart_data)
        status_df = _derive_from_status(status_time_series)
        registration_df = _choose_registration_df(registration_df, status_df)

        if registration_df is not None and not registration_df.empty:
            registration_df = registration_df.sort_values("timestamp")
            registration_df["timestamp"] = convert_timestamp_series_to_local(
                registration_df["timestamp"], user_timezone
            )

            if target_freq:
                freq_delta = pd.Timedelta(target_freq)
                diffs = registration_df["timestamp"].diff().dropna()
                min_diff = diffs.min() if not diffs.empty else None

                series = registration_df.set_index("timestamp")["new_users"].copy()
                if min_diff is not None and min_diff <= freq_delta:
                    resampled = series.resample(target_freq).sum()
                else:
                    resampled = series.resample(target_freq).sum(min_count=1)
                resampled = resampled.fillna(0)
                registration_plot_df = resampled.reset_index()
            else:
                registration_plot_df = registration_df.copy()

            if not registration_plot_df.empty:
                registration_plot_df["cumulative_users"] = (
                    registration_plot_df["new_users"].cumsum().fillna(0)
                )
                fig_users = go.Figure()
                fig_users.add_trace(
                    go.Scatter(
                        x=registration_plot_df["timestamp"],
                        y=registration_plot_df["cumulative_users"],
                        mode="lines",
                        name="Cumulative New Users",
                        line={"color": "#4caf50", "width": 3},
                        marker={"size": 5},
                        line_shape="hv",
                        hovertemplate=(
                            "<b>Cumulative New Users</b><br>Time: %{x}<br>Total: %{y}<extra></extra>"
                        ),
                    )
                )

                fig_users.update_layout(
                    xaxis_title=get_chart_axis_label(user_timezone),
                    yaxis_title="Cumulative New Users",
                    height=300,
                    hovermode="x unified",
                    margin={"l": 40, "r": 40, "t": 40, "b": 40},
                )

                charts.append(
                    html.Div(
                        [
                            html.H6(chart_title),
                            dcc.Graph(
                                figure=fig_users,
                                config={"displayModeBar": False, "responsive": True},
                            ),
                        ],
                        className="mb-3",
                    )
                )
        else:
            charts.append(
                _build_message_block(
                    "No new user registration data available.",
                    detail="The API did not return registration trends for this period.",
                )
            )

        # 2. Top Countries by User Count
        # API uses 'geographic_distribution' instead of 'geographic'
        geographic_data = data.get("geographic_distribution", {})
        if geographic_data:
            countries_data = geographic_data.get("countries", geographic_data.get("by_country", {}))
            if countries_data:
                # Sort and take top 10 countries
                sorted_countries = sorted(countries_data.items(), key=lambda x: x[1], reverse=True)[
                    :10
                ]

                if sorted_countries:
                    countries, counts = zip(*sorted_countries)

                    fig_countries = go.Figure(
                        data=[
                            go.Bar(
                                x=list(countries),
                                y=list(counts),
                                hovertemplate="<b>%{x}</b><br>Users: %{y}<extra></extra>",
                            )
                        ]
                    )

                    fig_countries.update_layout(
                        xaxis_title="Country",
                        yaxis_title="Number of Users",
                        height=300,
                        margin={"l": 40, "r": 40, "t": 40, "b": 40},
                    )

                    charts.append(
                        html.Div(
                            [
                                html.H6(f"Top countries{suffix_label}"),
                                dcc.Graph(
                                    figure=fig_countries,
                                    config={"displayModeBar": False, "responsive": True},
                                ),
                            ],
                            className="mb-3",
                        )
                    )

        return (
            charts
            if charts
            else [
                html.Div(
                    [
                        html.P(
                            "No chart data available for this period.",
                            className="text-muted text-center",
                        ),
                        html.Small(
                            "This may be due to insufficient privileges, no data for the selected timeframe, or API access restrictions.",
                            className="text-muted text-center d-block",
                        ),
                    ],
                    className="p-4",
                )
            ]
        )

    except Exception as e:
        return [
            html.Div(
                [
                    html.P(
                        "Error creating user statistics charts.",
                        className="text-danger text-center",
                    ),
                    html.Small(f"Error: {str(e)}", className="text-muted text-center d-block"),
                ],
                className="p-4",
            )
        ]


def create_system_overview(dashboard_stats_data, status_data=None):
    """
    Create system overview content with key metrics including total scripts.

    Args:
        dashboard_stats_data: Dashboard statistics data from the API or error response structure
        status_data: Status data from the status endpoint (optional, contains scripts_count)

    Returns:
        html.Div: System overview content
    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Debug logging - show what we actually received
        logger.info(f"System overview: Received data type: {type(dashboard_stats_data)}")
        if dashboard_stats_data:
            logger.info(
                f"System overview: Data keys: {list(dashboard_stats_data.keys()) if isinstance(dashboard_stats_data, dict) else 'Not a dict'}"
            )

        # Handle error response structure
        if not dashboard_stats_data or dashboard_stats_data.get("error", False):
            error_msg = (
                dashboard_stats_data.get("message", "No data available")
                if dashboard_stats_data
                else "No data available"
            )
            status_code = (
                dashboard_stats_data.get("status_code", "unknown")
                if dashboard_stats_data
                else "unknown"
            )

            if status_code == 403:
                error_detail = "You need SUPERADMIN privileges to access system overview."
            elif status_code == 401:
                error_detail = "Authentication failed. Please log in again."
            else:
                error_detail = f"System overview unavailable: {error_msg}"

            return html.Div(
                [
                    html.P("System overview not available.", className="text-muted"),
                    html.Small(error_detail, className="text-muted"),
                ],
                className="p-3",
            )

        data = dashboard_stats_data.get("data", {})
        logger.info(
            f"System overview: Data section keys: {list(data.keys()) if isinstance(data, dict) else 'No data section'}"
        )

        summary = data.get("summary", {})
        logger.info(
            f"System overview: Summary section keys: {list(summary.keys()) if isinstance(summary, dict) else 'No summary section'}"
        )

        if not summary:
            return html.Div("No system data available.", className="text-muted p-3")

        # Extract summary metrics - use actual API field names
        total_users = summary.get("total_users", 0)
        total_executions = summary.get(
            "total_jobs", 0
        )  # API uses 'total_jobs' not 'total_executions'

        # Get scripts count from status data if available, otherwise try dashboard stats
        total_scripts = 0
        if status_data:
            total_scripts = status_data.get("scripts_count", 0)
        else:
            total_scripts = summary.get("total_scripts", 0)  # Fallback to dashboard stats

        recent_executions = summary.get("jobs_last_day", 0)  # Recent activity
        recent_users = summary.get("users_last_day", 0)  # Recent user activity

        return html.Div(
            [
                # Header section
                html.Div(
                    [
                        html.H5("System Overview", className="mb-3 text-center"),
                    ],
                    className="mb-3",
                ),
                # Main metrics section - organized in logical groups
                html.Div(
                    [
                        # Total counts section
                        html.Div(
                            [
                                html.H6("Total Resources", className="text-muted mb-3 text-center"),
                                html.Div(
                                    [
                                        # Users card
                                        html.Div(
                                            [
                                                html.Div(
                                                    [
                                                        html.H4(
                                                            f"{total_users:,}",
                                                            className="text-primary mb-0",
                                                        ),
                                                        html.Small("Users", className="text-muted"),
                                                    ],
                                                    className="text-center",
                                                ),
                                            ],
                                            className="col-md-4 mb-3",
                                        ),
                                        # Scripts card
                                        html.Div(
                                            [
                                                html.Div(
                                                    [
                                                        html.H4(
                                                            f"{total_scripts:,}",
                                                            className="text-info mb-0",
                                                        ),
                                                        html.Small(
                                                            "Scripts", className="text-muted"
                                                        ),
                                                    ],
                                                    className="text-center",
                                                ),
                                            ],
                                            className="col-md-4 mb-3",
                                        ),
                                        # Executions card
                                        html.Div(
                                            [
                                                html.Div(
                                                    [
                                                        html.H4(
                                                            f"{total_executions:,}",
                                                            className="text-success mb-0",
                                                        ),
                                                        html.Small(
                                                            "Executions", className="text-muted"
                                                        ),
                                                    ],
                                                    className="text-center",
                                                ),
                                            ],
                                            className="col-md-4 mb-3",
                                        ),
                                    ],
                                    className="row",
                                ),
                            ],
                            className="mb-4",
                        ),
                        # Recent activity section
                        html.Div(
                            [
                                html.H6(
                                    "Recent Activity (24h)", className="text-muted mb-3 text-center"
                                ),
                                html.Div(
                                    [
                                        # Recent users card
                                        html.Div(
                                            [
                                                html.Div(
                                                    [
                                                        html.H4(
                                                            f"{recent_users:,}",
                                                            className="text-warning mb-0",
                                                        ),
                                                        html.Small(
                                                            "New Users", className="text-muted"
                                                        ),
                                                    ],
                                                    className="text-center",
                                                ),
                                            ],
                                            className="col-md-6 mb-3",
                                        ),
                                        # Recent executions card
                                        html.Div(
                                            [
                                                html.Div(
                                                    [
                                                        html.H4(
                                                            f"{recent_executions:,}",
                                                            className="text-secondary mb-0",
                                                        ),
                                                        html.Small(
                                                            "New Executions", className="text-muted"
                                                        ),
                                                    ],
                                                    className="text-center",
                                                ),
                                            ],
                                            className="col-md-6 mb-3",
                                        ),
                                    ],
                                    className="row justify-content-center",
                                ),
                            ],
                        ),
                    ],
                ),
            ],
            className="p-4 bg-light rounded border",
        )

    except Exception as e:
        logger.error(f"Error creating system overview: {str(e)}")
        return html.Div(
            [
                html.P("Error loading system overview.", className="text-danger"),
                html.Small(f"Error: {str(e)}", className="text-muted"),
            ],
            className="p-3",
        )


def create_dashboard_summary_cards(dashboard_stats_data, scripts_count=None):
    """
    Create summary cards from dashboard statistics.

    Args:
        dashboard_stats_data: Dashboard statistics data from the API or error response structure
        scripts_count: Total number of scripts (optional)

    Returns:
        html.Div: Dashboard summary cards layout
    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Debug logging - show what we actually received
        logger.info(f"Dashboard summary cards: Received data type: {type(dashboard_stats_data)}")
        if dashboard_stats_data:
            logger.info(
                f"Dashboard summary cards: Data keys: {list(dashboard_stats_data.keys()) if isinstance(dashboard_stats_data, dict) else 'Not a dict'}"
            )

        # Handle error response structure
        if not dashboard_stats_data or dashboard_stats_data.get("error", False):
            error_msg = (
                dashboard_stats_data.get("message", "No data available")
                if dashboard_stats_data
                else "No data available"
            )
            status_code = (
                dashboard_stats_data.get("status_code", "unknown")
                if dashboard_stats_data
                else "unknown"
            )

            if status_code == 403:
                error_detail = "You need SUPERADMIN privileges to access dashboard statistics."
            elif status_code == 401:
                error_detail = "Authentication failed. Please log in again."
            else:
                error_detail = f"Dashboard statistics unavailable: {error_msg}"

            return html.Div(
                [
                    html.P("No dashboard summary available.", className="text-muted text-center"),
                    html.Small(error_detail, className="text-muted text-center d-block"),
                ],
                className="p-4",
            )

        data = dashboard_stats_data.get("data", {})
        logger.info(
            f"Dashboard summary cards: Data section keys: {list(data.keys()) if isinstance(data, dict) else 'No data section'}"
        )

        summary = data.get("summary", {})
        logger.info(
            f"Dashboard summary cards: Summary section keys: {list(summary.keys()) if isinstance(summary, dict) else 'No summary section'}"
        )

        if not summary:
            return html.Div("No summary data available.", className="text-muted text-center p-4")

        # Extract summary metrics - use actual API field names
        total_users = summary.get("total_users", 0)
        total_executions = summary.get(
            "total_jobs", 0
        )  # API uses 'total_jobs' not 'total_executions'
        active_executions = summary.get("jobs_last_day", 0)  # Use recent jobs as proxy for active
        recent_users = summary.get("users_last_day", 0)  # API uses 'users_last_day'
        total_scripts = scripts_count if scripts_count is not None else 0

        return html.Div(
            [
                # First row: 3 main cards
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.H6("Total Users", className="card-title"),
                                                html.H4(str(total_users), className="text-primary"),
                                            ],
                                            className="card-body text-center",
                                        )
                                    ],
                                    className="card",
                                ),
                            ],
                            className="col-md-4 mb-3",
                        ),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.H6("Total Scripts", className="card-title"),
                                                html.H4(str(total_scripts), className="text-info"),
                                            ],
                                            className="card-body text-center",
                                        )
                                    ],
                                    className="card",
                                ),
                            ],
                            className="col-md-4 mb-3",
                        ),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.H6("Total Executions", className="card-title"),
                                                html.H4(
                                                    str(total_executions), className="text-success"
                                                ),
                                            ],
                                            className="card-body text-center",
                                        )
                                    ],
                                    className="card",
                                ),
                            ],
                            className="col-md-4 mb-3",
                        ),
                    ],
                    className="row",
                ),
                # Second row: 2 activity cards (centered)
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.H6(
                                                    "Active Executions", className="card-title"
                                                ),
                                                html.H4(
                                                    str(active_executions), className="text-warning"
                                                ),
                                            ],
                                            className="card-body text-center",
                                        )
                                    ],
                                    className="card",
                                ),
                            ],
                            className="col-md-6 mb-3",
                        ),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.H6("Recent Users", className="card-title"),
                                                html.H4(
                                                    str(recent_users), className="text-secondary"
                                                ),
                                            ],
                                            className="card-body text-center",
                                        )
                                    ],
                                    className="card",
                                ),
                            ],
                            className="col-md-6 mb-3",
                        ),
                    ],
                    className="row justify-content-center",
                ),
            ],
            className="row",
        )

    except Exception as e:
        return html.Div(
            [
                html.P("Error creating summary cards.", className="text-danger text-center"),
                html.Small(f"Error: {str(e)}", className="text-muted text-center d-block"),
            ],
            className="p-4",
        )


def create_deployment_information(api_environment="production"):
    """
    Create deployment information section showing API and API UI details.

    Args:
        api_environment: Environment to fetch deployment info from

    Returns:
        html.Div: Deployment information cards
    """
    import logging

    from trendsearth_ui.config import get_api_base
    from trendsearth_ui.utils.http_client import apply_default_headers, get_session

    logger = logging.getLogger(__name__)

    try:
        # Get API deployment information
        api_info = {"environment": "Unknown", "branch": "Unknown", "commit_sha": "Unknown"}
        try:
            # API health endpoint is at root level, not under /api/v1
            api_base_root = get_api_base(api_environment).replace("/api/v1", "")
            api_url = f"{api_base_root}/api-health"
            logger.info(f"Fetching API deployment info from: {api_url}")
            resp = get_session().get(api_url, headers=apply_default_headers(), timeout=5)
            logger.info(f"API health response status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                logger.info(f"API health response data: {data}")
                deployment = data.get("deployment", {})
                logger.info(f"API deployment section: {deployment}")
                api_info = {
                    "environment": deployment.get("environment", "Unknown"),
                    "branch": deployment.get("branch", "Unknown"),
                    "commit_sha": deployment.get("commit_sha", "Unknown")[:8]
                    if deployment.get("commit_sha", "Unknown") != "Unknown"
                    else "Unknown",
                }
                logger.info(f"Processed API info: {api_info}")
            else:
                logger.warning(
                    f"API health endpoint returned status {resp.status_code}: {resp.text}"
                )
        except Exception as e:
            logger.warning(f"Could not fetch API deployment info: {e}")

        def format_value(val):
            return val if val and val != "Unknown" else "-"

        def commit_link(repo_url, sha):
            if sha and sha != "Unknown":
                return html.A(
                    sha,
                    href=f"{repo_url}/commit/{sha}",
                    target="_blank",
                    className="text-decoration-underline text-primary",
                )
            return "-"

        return html.Div(
            [
                html.H4("Deployment Information", className="mb-3"),
                html.Div(
                    [
                        # API Information Card
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.H6("Trends.Earth API", className="card-title"),
                                                html.P(
                                                    f"Environment: {format_value(api_info['environment'])}",
                                                    className="mb-1",
                                                ),
                                                html.P(
                                                    f"Branch: {format_value(api_info['branch'])}",
                                                    className="mb-1",
                                                ),
                                                html.P(
                                                    [
                                                        "Commit: ",
                                                        commit_link(
                                                            "https://github.com/ConservationInternational/trends.earth-api",
                                                            api_info["commit_sha"],
                                                        ),
                                                    ],
                                                    className="mb-0",
                                                ),
                                            ],
                                            className="card-body",
                                        )
                                    ],
                                    className="card",
                                ),
                            ],
                            className="col-md-12 mb-3",
                        ),
                    ],
                    className="row",
                ),
            ]
        )

    except Exception as e:
        return html.Div(
            [
                html.H4("Deployment Information", className="mb-3"),
                html.P(
                    "Error fetching deployment information.", className="text-danger text-center"
                ),
                html.Small(f"Error: {str(e)}", className="text-muted text-center d-block"),
            ],
            className="p-4",
        )


def create_docker_swarm_status_table(swarm_data):
    """
    Create a table showing Docker swarm nodes and their details.

    Args:
        swarm_data: Docker swarm data from the API

    Returns:
        html.Div: Table showing swarm node details
    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        if not swarm_data or not isinstance(swarm_data, dict):
            return html.Div(
                [
                    html.P("No swarm data available.", className="text-muted text-center"),
                ],
                className="p-4",
            )

        # Handle error response structure
        error_msg = swarm_data.get("error")
        if error_msg:
            return html.Div(
                [
                    html.P("Docker swarm status unavailable.", className="text-muted text-center"),
                    html.Small(f"Error: {error_msg}", className="text-muted text-center d-block"),
                ],
                className="p-4",
            )

        # Extract swarm information directly (data layer already extracted in callback)
        nodes = swarm_data.get("nodes", [])
        swarm_active = swarm_data.get("swarm_active", False)

        if not swarm_active:
            error_msg = swarm_data.get("error", "Swarm not active")
            return html.Div(
                [
                    html.P(
                        f"Docker Swarm Status: {error_msg}", className="text-warning text-center"
                    ),
                    html.P("No nodes to display.", className="text-muted text-center"),
                ],
                className="p-4",
            )

        if not nodes:
            return html.Div(
                [
                    html.P("No swarm nodes available.", className="text-muted text-center"),
                ],
                className="p-4",
            )

        # Create table headers
        table_header = html.Thead(
            [
                html.Tr(
                    [
                        html.Th("Hostname", scope="col"),
                        html.Th("Role", scope="col"),
                        html.Th("State", scope="col"),
                        html.Th("Availability", scope="col"),
                        html.Th("CPU", scope="col"),
                        html.Th("Memory (GB)", scope="col"),
                        html.Th("Running Tasks", scope="col"),
                        html.Th("Leader", scope="col"),
                    ]
                )
            ]
        )

        # Create table rows
        table_rows = []
        for node in nodes:
            # Determine state color
            state = node.get("state", "unknown")
            state_class = "text-success" if state == "ready" else "text-warning"

            # Determine role color and badge
            role = node.get("role", "worker")
            is_manager = node.get("is_manager", False)
            role_class = "badge bg-primary" if is_manager else "badge bg-secondary"

            # Leader indicator
            is_leader = node.get("is_leader", False)
            leader_indicator = "✓" if is_leader else "-"
            leader_class = "text-success fw-bold" if is_leader else "text-muted"

            # Availability color
            availability = node.get("availability", "unknown")
            avail_class = "text-success" if availability == "active" else "text-warning"

            row = html.Tr(
                [
                    html.Td(node.get("hostname", "Unknown")),
                    html.Td(html.Span(role.title(), className=role_class)),
                    html.Td(state.title(), className=state_class),
                    html.Td(availability.title(), className=avail_class),
                    html.Td(f"{node.get('cpu_count', 0):.1f}"),
                    html.Td(f"{node.get('memory_gb', 0):.1f}"),
                    html.Td(str(node.get("running_tasks", 0))),
                    html.Td(leader_indicator, className=leader_class),
                ]
            )
            table_rows.append(row)

        table_body = html.Tbody(table_rows)

        # Calculate swarm summary statistics using actual resource usage data
        total_cpu = sum(node.get("cpu_count", 0) for node in nodes)
        total_memory_gb = sum(node.get("memory_gb", 0) for node in nodes)
        total_running_tasks = sum(node.get("running_tasks", 0) for node in nodes)

        # Calculate actual resource usage from nodes that have resource_usage data
        total_used_cpu_nanos = 0
        total_used_memory_bytes = 0
        total_available_cpu_nanos = 0
        total_available_memory_bytes = 0
        total_available_capacity = 0

        for node in nodes:
            resource_usage = node.get("resource_usage", {})
            if resource_usage:
                # Use actual resource usage data from the API
                total_used_cpu_nanos += resource_usage.get("used_cpu_nanos", 0)
                total_used_memory_bytes += resource_usage.get("used_memory_bytes", 0)
                total_available_cpu_nanos += resource_usage.get("available_cpu_nanos", 0)
                total_available_memory_bytes += resource_usage.get("available_memory_bytes", 0)

            # Sum up the available capacity calculated by the API (based on 1e8 units per task)
            total_available_capacity += node.get("available_capacity", 0)

        # Convert to human-readable units
        used_cpu_cores = total_used_cpu_nanos / 1_000_000_000  # nanoseconds to cores
        used_memory_gb = total_used_memory_bytes / (1024**3)  # bytes to GB
        available_cpu_cores = total_available_cpu_nanos / 1_000_000_000
        available_memory_gb = total_available_memory_bytes / (1024**3)

        # Calculate total possible capacity (running + available)
        total_possible_capacity = total_running_tasks + total_available_capacity

        # Create summary section with actual resource usage
        summary_section = html.Div(
            [
                html.P(
                    f"Total Resources: {total_cpu:.1f} CPUs ({used_cpu_cores:.1f} used, {available_cpu_cores:.1f} available), "
                    f"{total_memory_gb:.1f} GB Memory ({used_memory_gb:.1f} GB used, {available_memory_gb:.1f} GB available)",
                    className="mb-1",
                ),
                html.P(
                    f"Tasks: {total_running_tasks} running | Capacity: {total_possible_capacity} total tasks ({total_available_capacity} additional)",
                    className="mb-0 text-muted",
                ),
            ],
            className="mb-3 p-2 bg-light rounded",
        )

        return html.Div(
            [
                summary_section,
                html.Div(
                    [
                        html.Table(
                            [table_header, table_body],
                            className="table table-striped table-hover",
                        )
                    ],
                    className="table-responsive",
                ),
            ]
        )

    except Exception as e:
        logger.error(f"Error creating Docker swarm status table: {e}")
        return html.Div(
            [
                html.P("Error creating swarm status table.", className="text-danger text-center"),
                html.Small(f"Error: {str(e)}", className="text-muted text-center d-block"),
            ],
            className="p-4",
        )
