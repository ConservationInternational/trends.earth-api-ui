"""Visualization utilities for stats charts and maps."""

from dash import dcc, html
import pandas as pd
import plotly.graph_objects as go


def create_user_geographic_map(user_stats_data, title_suffix=""):
    """
    Create a geographic map showing countries from which recent users have joined.

    Args:
        user_stats_data: User statistics data from the API or error response structure
        title_suffix: Additional text for the chart title

    Returns:
        dcc.Graph: Plotly map figure or error message div
    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Debug logging - show what we actually received
        logger.info(f"User geographic map: Received data type: {type(user_stats_data)}")
        if user_stats_data:
            logger.info(
                f"User geographic map: Data keys: {list(user_stats_data.keys()) if isinstance(user_stats_data, dict) else 'Not a dict'}"
            )

        # Handle error response structure
        if not user_stats_data or user_stats_data.get("error", False):
            error_msg = (
                user_stats_data.get("message", "No data available")
                if user_stats_data
                else "No data available"
            )
            status_code = (
                user_stats_data.get("status_code", "unknown") if user_stats_data else "unknown"
            )

            if status_code == 403:
                error_detail = "You need SUPERADMIN privileges to access geographic user data."
            elif status_code == 401:
                error_detail = "Authentication failed. Please log in again."
            else:
                error_detail = f"Geographic user data unavailable: {error_msg}"

            return html.Div(
                [
                    html.P(
                        "No geographic user data available.", className="text-muted text-center"
                    ),
                    html.Small(
                        error_detail,
                        className="text-muted text-center d-block",
                    ),
                ],
                className="p-4",
            )

        # Extract geographic data from user stats
        data = user_stats_data.get("data", {})
        logger.info(
            f"User geographic map: Data section keys: {list(data.keys()) if isinstance(data, dict) else 'No data section'}"
        )

        # API uses 'geographic_distribution' not 'geographic'
        geographic_data = data.get("geographic_distribution", {})
        logger.info(
            f"User geographic map: Geographic section keys: {list(geographic_data.keys()) if isinstance(geographic_data, dict) else 'No geographic section'}"
        )

        if not geographic_data:
            return html.Div(
                [
                    html.P(
                        "No geographic user data available.", className="text-muted text-center"
                    ),
                    html.Small(
                        "User location data may not be configured, or you may need SUPERADMIN privileges to access this data.",
                        className="text-muted text-center d-block",
                    ),
                ],
                className="p-4",
            )

        # Process geographic data - expect format like:
        # {"countries": {"US": 45, "CA": 12, "GB": 8, ...}}
        countries_data = geographic_data.get("countries", {})

        if not countries_data:
            return html.Div(
                [
                    html.P("No country data available.", className="text-muted text-center"),
                    html.Small(
                        "User country information not available for this period. This may be due to insufficient privileges or no user data for the selected timeframe.",
                        className="text-muted text-center d-block",
                    ),
                ],
                className="p-4",
            )

        # Convert to lists for plotly
        countries = list(countries_data.keys())
        user_counts = list(countries_data.values())

        # Create the choropleth map
        fig = go.Figure(
            data=go.Choropleth(
                locations=countries,
                z=user_counts,
                locationmode="ISO-3",
                colorscale="Blues",
                text=[
                    f"{country}: {count} users" for country, count in zip(countries, user_counts)
                ],
                hovertemplate="<b>%{text}</b><extra></extra>",
                colorbar={"title": "Number of Users", "titleside": "right"},
            )
        )

        fig.update_layout(
            title=f"User Registrations by Country{title_suffix}",
            geo={"showframe": False, "showcoastlines": True, "projection_type": "natural earth"},
            height=400,
            margin={"l": 0, "r": 0, "t": 40, "b": 0},
        )

        return dcc.Graph(figure=fig, config={"displayModeBar": False, "responsive": True})

    except Exception as e:
        return html.Div(
            [
                html.P("Error creating geographic map.", className="text-danger text-center"),
                html.Small(f"Error: {str(e)}", className="text-muted text-center d-block"),
            ],
            className="p-4",
        )


def create_execution_statistics_chart(execution_stats_data, title_suffix=""):
    """
    Create execution statistics charts showing trends and distribution.

    Args:
        execution_stats_data: Execution statistics data from the API or error response structure
        title_suffix: Additional text for the chart title

    Returns:
        list: List of chart components
    """
    import logging

    logger = logging.getLogger(__name__)

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

        charts = []

        # 1. Task Performance (instead of status distribution)
        # API has 'task_performance' instead of 'status_distribution'
        task_performance_data = data.get("task_performance", {})
        if task_performance_data:
            # Check if there's status information in task_performance
            status_data = task_performance_data.get("by_status", {})
            if status_data:
                statuses = list(status_data.keys())
                counts = list(status_data.values())

                # Create pie chart for status distribution
                fig_pie = go.Figure(
                    data=[
                        go.Pie(
                            labels=statuses,
                            values=counts,
                            hole=0.3,
                            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>",
                        )
                    ]
                )

                fig_pie.update_layout(
                    title=f"Execution Status Distribution{title_suffix}",
                    height=300,
                    margin={"l": 40, "r": 40, "t": 40, "b": 40},
                )

                charts.append(
                    html.Div(
                        [
                            html.H6("Execution Status Distribution"),
                            dcc.Graph(
                                figure=fig_pie, config={"displayModeBar": False, "responsive": True}
                            ),
                        ],
                        className="mb-3",
                    )
                )

        # 2. Time Series Trends (instead of trends)
        # API has 'time_series' instead of 'trends'
        trends_data = data.get("time_series", [])
        if trends_data:
            # Convert to DataFrame for easier handling
            df = pd.DataFrame(trends_data)

            if not df.empty and "date" in df.columns:
                fig_trend = go.Figure()

                # Add traces for different execution statuses
                for status in ["FINISHED", "FAILED", "CANCELLED"]:
                    if status.lower() in df.columns:
                        fig_trend.add_trace(
                            go.Scatter(
                                x=df["date"],
                                y=df[status.lower()],
                                mode="lines+markers",
                                name=status.title(),
                                line={"width": 2},
                            )
                        )

                fig_trend.update_layout(
                    title=f"Execution Trends{title_suffix}",
                    xaxis_title="Date",
                    yaxis_title="Number of Executions",
                    height=300,
                    hovermode="x unified",
                    margin={"l": 40, "r": 40, "t": 40, "b": 40},
                )

                charts.append(
                    html.Div(
                        [
                            html.H6("Execution Trends"),
                            dcc.Graph(
                                figure=fig_trend,
                                config={"displayModeBar": False, "responsive": True},
                            ),
                        ],
                        className="mb-3",
                    )
                )

        # 3. Top Users (instead of task types)
        # API has 'top_users' instead of 'task_types'
        top_users_data = data.get("top_users", [])
        if top_users_data and isinstance(top_users_data, list):
            # Extract user data for chart
            user_names = []
            execution_counts = []

            for user_data in top_users_data[:10]:  # Top 10 users
                if isinstance(user_data, dict):
                    name = user_data.get("name", user_data.get("email", "Unknown"))
                    count = user_data.get("execution_count", user_data.get("count", 0))
                    user_names.append(name)
                    execution_counts.append(count)

            if user_names and execution_counts:
                # Create horizontal bar chart for top users
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
                    title=f"Top Users by Execution Count{title_suffix}",
                    xaxis_title="Number of Executions",
                    height=max(
                        300, len(user_names) * 30
                    ),  # Dynamic height based on number of users
                    margin={"l": 40, "r": 40, "t": 40, "b": 40},
                )

                charts.append(
                    html.Div(
                        [
                            html.H6("Top Users by Activity"),
                            dcc.Graph(
                                figure=fig_users,
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
                        "Error creating execution statistics charts.",
                        className="text-danger text-center",
                    ),
                    html.Small(f"Error: {str(e)}", className="text-muted text-center d-block"),
                ],
                className="p-4",
            )
        ]


def create_user_statistics_chart(user_stats_data, title_suffix=""):
    """
    Create user statistics charts showing registration trends.

    Args:
        user_stats_data: User statistics data from the API or error response structure
        title_suffix: Additional text for the chart title

    Returns:
        list: List of chart components
    """
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

        # 1. User Registration Trends
        # API uses 'registration_trends' instead of 'trends'
        trends_data = data.get("registration_trends", [])
        if trends_data:
            df = pd.DataFrame(trends_data)

            if not df.empty and "date" in df.columns:
                fig_users = go.Figure()

                # Add user registration trend
                if "new_users" in df.columns:
                    fig_users.add_trace(
                        go.Scatter(
                            x=df["date"],
                            y=df["new_users"],
                            mode="lines+markers",
                            name="New Users",
                            line={"color": "#28a745", "width": 2},
                            fill="tonexty" if len(df) > 1 else None,
                            hovertemplate="<b>New Users</b><br>Date: %{x}<br>Count: %{y}<extra></extra>",
                        )
                    )

                # Add cumulative users if available
                if "total_users" in df.columns:
                    fig_users.add_trace(
                        go.Scatter(
                            x=df["date"],
                            y=df["total_users"],
                            mode="lines+markers",
                            name="Total Users",
                            line={"color": "#007bff", "width": 2},
                            yaxis="y2",
                            hovertemplate="<b>Total Users</b><br>Date: %{x}<br>Count: %{y}<extra></extra>",
                        )
                    )

                fig_users.update_layout(
                    title=f"User Registration Trends{title_suffix}",
                    xaxis_title="Date",
                    yaxis_title="New Users",
                    yaxis2={
                        "title": "Total Users",
                        "overlaying": "y",
                        "side": "right",
                        "showgrid": False,
                    },
                    height=300,
                    hovermode="x unified",
                    margin={"l": 40, "r": 40, "t": 40, "b": 40},
                )

                charts.append(
                    html.Div(
                        [
                            html.H6("User Registration Trends"),
                            dcc.Graph(
                                figure=fig_users,
                                config={"displayModeBar": False, "responsive": True},
                            ),
                        ],
                        className="mb-3",
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
                        title=f"Top Countries by User Count{title_suffix}",
                        xaxis_title="Country",
                        yaxis_title="Number of Users",
                        height=300,
                        margin={"l": 40, "r": 40, "t": 40, "b": 40},
                    )

                    charts.append(
                        html.Div(
                            [
                                html.H6("Top Countries"),
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
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Span("Total Users: ", className="fw-bold"),
                                        html.Span(
                                            f"{total_users:,}", className="text-primary fw-bold"
                                        ),
                                    ],
                                    className="mb-2",
                                ),
                                html.Div(
                                    [
                                        html.Span("Total Scripts: ", className="fw-bold"),
                                        html.Span(
                                            f"{total_scripts:,}", className="text-info fw-bold"
                                        ),
                                    ],
                                    className="mb-2",
                                ),
                                html.Div(
                                    [
                                        html.Span("Total Executions: ", className="fw-bold"),
                                        html.Span(
                                            f"{total_executions:,}",
                                            className="text-success fw-bold",
                                        ),
                                    ],
                                    className="mb-2",
                                ),
                            ],
                            className="col-md-6",
                        ),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Span("Recent Users (24h): ", className="fw-bold"),
                                        html.Span(
                                            f"{recent_users:,}", className="text-warning fw-bold"
                                        ),
                                    ],
                                    className="mb-2",
                                ),
                                html.Div(
                                    [
                                        html.Span("Recent Executions (24h): ", className="fw-bold"),
                                        html.Span(
                                            f"{recent_executions:,}",
                                            className="text-secondary fw-bold",
                                        ),
                                    ],
                                    className="mb-2",
                                ),
                            ],
                            className="col-md-6",
                        ),
                    ],
                    className="row",
                ),
            ],
            className="p-3 bg-light rounded",
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


def create_dashboard_summary_cards(dashboard_stats_data):
    """
    Create summary cards from dashboard statistics.

    Args:
        dashboard_stats_data: Dashboard statistics data from the API or error response structure

    Returns:
        html.Div: Summary cards layout
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

        return html.Div(
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
                    className="col-md-3 mb-3",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.H6("Total Executions", className="card-title"),
                                        html.H4(str(total_executions), className="text-info"),
                                    ],
                                    className="card-body text-center",
                                )
                            ],
                            className="card",
                        ),
                    ],
                    className="col-md-3 mb-3",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.H6("Active Executions", className="card-title"),
                                        html.H4(str(active_executions), className="text-warning"),
                                    ],
                                    className="card-body text-center",
                                )
                            ],
                            className="card",
                        ),
                    ],
                    className="col-md-3 mb-3",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.H6("Recent Users", className="card-title"),
                                        html.H4(str(recent_users), className="text-success"),
                                    ],
                                    className="card-body text-center",
                                )
                            ],
                            className="card",
                        ),
                    ],
                    className="col-md-3 mb-3",
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
