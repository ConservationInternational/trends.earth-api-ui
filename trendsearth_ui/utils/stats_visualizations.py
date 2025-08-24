"""Visualization utilities for stats charts and maps."""

from dash import dcc, html
import pandas as pd
import plotly.graph_objects as go


def create_user_geographic_map(user_stats_data, title_suffix=""):
    """
    Create a geographic map showing countries from which recent users have joined.

    Args:
        user_stats_data: User statistics data from the API
        title_suffix: Additional text for the chart title

    Returns:
        dcc.Graph: Plotly map figure
    """
    try:
        # Handle error responses from API
        if user_stats_data and user_stats_data.get("error", False):
            error_msg = user_stats_data.get("message", "Unknown API error")
            status_code = user_stats_data.get("status_code", "unknown")

            return html.Div(
                [
                    html.P(
                        "No geographic user data available.", className="text-muted text-center"
                    ),
                    html.Small(
                        f"API Error ({status_code}): {error_msg}",
                        className="text-muted text-center d-block",
                    ),
                ],
                className="p-4",
            )

        # Extract geographic data from user stats
        data = user_stats_data.get("data", {}) if user_stats_data else {}
        geographic_data = data.get("geographic", {})

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
                colorbar={"title": "Number of Users"},
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
        execution_stats_data: Execution statistics data from the API
        title_suffix: Additional text for the chart title

    Returns:
        list: List of chart components
    """
    try:
        # Handle error responses from API
        if execution_stats_data and execution_stats_data.get("error", False):
            error_msg = execution_stats_data.get("message", "Unknown API error")
            status_code = execution_stats_data.get("status_code", "unknown")

            return [
                html.Div(
                    [
                        html.P(
                            "No chart data available for this period.",
                            className="text-muted text-center",
                        ),
                        html.Small(
                            f"API Error ({status_code}): {error_msg}",
                            className="text-muted text-center d-block",
                        ),
                    ],
                    className="p-4",
                )
            ]

        data = execution_stats_data.get("data", {}) if execution_stats_data else {}

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

        # 1. Execution Status Distribution
        status_data = data.get("status_distribution", {})
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

        # 2. Execution Trends Over Time
        trends_data = data.get("trends", [])
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

        # 3. Task Type Distribution (if available)
        task_types_data = data.get("task_types", {})
        if task_types_data:
            task_names = list(task_types_data.keys())
            task_counts = list(task_types_data.values())

            # Create horizontal bar chart for task types
            fig_tasks = go.Figure(
                data=[
                    go.Bar(
                        x=task_counts,
                        y=task_names,
                        orientation="h",
                        hovertemplate="<b>%{y}</b><br>Executions: %{x}<extra></extra>",
                    )
                ]
            )

            fig_tasks.update_layout(
                title=f"Popular Task Types{title_suffix}",
                xaxis_title="Number of Executions",
                height=max(
                    300, len(task_names) * 30
                ),  # Dynamic height based on number of task types
                margin={"l": 40, "r": 40, "t": 40, "b": 40},
            )

            charts.append(
                html.Div(
                    [
                        html.H6("Task Type Distribution"),
                        dcc.Graph(
                            figure=fig_tasks, config={"displayModeBar": False, "responsive": True}
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
        user_stats_data: User statistics data from the API
        title_suffix: Additional text for the chart title

    Returns:
        list: List of chart components
    """
    try:
        # Handle error responses from API
        if user_stats_data and user_stats_data.get("error", False):
            error_msg = user_stats_data.get("message", "Unknown API error")
            status_code = user_stats_data.get("status_code", "unknown")

            return [
                html.Div(
                    [
                        html.P(
                            "No chart data available for this period.",
                            className="text-muted text-center",
                        ),
                        html.Small(
                            f"API Error ({status_code}): {error_msg}",
                            className="text-muted text-center d-block",
                        ),
                    ],
                    className="p-4",
                )
            ]

        data = user_stats_data.get("data", {}) if user_stats_data else {}

        if not data:
            return [
                html.Div(
                    "No user statistics available for this period.",
                    className="text-muted text-center p-4",
                )
            ]

        charts = []

        # 1. User Registration Trends
        trends_data = data.get("trends", [])
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
        geographic_data = data.get("geographic", {})
        if geographic_data:
            countries_data = geographic_data.get("countries", {})
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


def create_dashboard_summary_cards(dashboard_stats_data):
    """
    Create summary cards from dashboard statistics.

    Args:
        dashboard_stats_data: Dashboard statistics data from the API

    Returns:
        html.Div: Summary cards layout
    """
    try:
        # Handle error responses from API
        if dashboard_stats_data and dashboard_stats_data.get("error", False):
            error_msg = dashboard_stats_data.get("message", "Unknown API error")
            status_code = dashboard_stats_data.get("status_code", "unknown")

            return html.Div(
                [
                    html.P("Dashboard statistics not available.", className="text-muted text-center"),
                    html.Small(f"API Error ({status_code}): {error_msg}", className="text-muted text-center d-block"),
                ],
                className="p-4"
            )

        data = dashboard_stats_data.get("data", {}) if dashboard_stats_data else {}
        summary = data.get("summary", {})

        if not summary:
            return html.Div("No summary data available.", className="text-muted text-center p-4")

        # Extract summary metrics
        total_users = summary.get("total_users", 0)
        total_executions = summary.get("total_executions", 0)
        active_executions = summary.get("active_executions", 0)
        recent_users = summary.get("recent_users", 0)

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
