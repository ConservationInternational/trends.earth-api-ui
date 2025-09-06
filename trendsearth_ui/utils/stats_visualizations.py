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
        if not user_stats_data:
            return html.Div(
                [
                    html.P("No geographic data available.", className="text-muted text-center"),
                    html.Small("No data provided.", className="text-muted text-center d-block"),
                ],
                className="p-4",
            )

        # Check if data is a list (unexpected format) and handle gracefully
        if isinstance(user_stats_data, list):
            return html.Div(
                [
                    html.P("No geographic data available.", className="text-muted text-center"),
                    html.Small(
                        "Received unexpected data format from API.",
                        className="text-muted text-center d-block",
                    ),
                ],
                className="p-4",
            )

        # Handle error response structure (should be a dict)
        if user_stats_data.get("error", False):
            error_msg = user_stats_data.get("message", "No data available")
            status_code = user_stats_data.get("status_code", "unknown")

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
        # {"top_countries": [{"country": "US", "count": 45}, {"country": "CA", "count": 12}, ...]}
        # or {"countries": {"US": 45, "CA": 12, "GB": 8, ...}}
        countries_data = geographic_data.get("countries", {})
        top_countries_data = geographic_data.get("top_countries", [])

        logger.info(f"Countries data: {countries_data}")
        logger.info(f"Top countries data: {top_countries_data}")

        # Handle both possible formats
        if top_countries_data and isinstance(top_countries_data, list):
            # Convert list format to dict format
            countries_data = {}
            for item in top_countries_data:
                if isinstance(item, dict):
                    country = item.get("country", item.get("country_code", ""))
                    count = item.get("user_count", item.get("count", 0))
                    if country:
                        countries_data[country] = count

        logger.info(f"Final countries data: {countries_data}")

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

        # Country name to ISO-3 code mapping for common countries
        country_code_mapping = {
            "China": "CHN",
            "Mozambique": "MOZ",
            "United States": "USA",
            "United States of America": "USA",
            "Canada": "CAN",
            "United Kingdom": "GBR",
            "Germany": "DEU",
            "France": "FRA",
            "Japan": "JPN",
            "Brazil": "BRA",
            "India": "IND",
            "Australia": "AUS",
            "South Africa": "ZAF",
            "Mexico": "MEX",
            "Russia": "RUS",
            "Italy": "ITA",
            "Spain": "ESP",
            "Netherlands": "NLD",
            "Sweden": "SWE",
            "Norway": "NOR",
            "Denmark": "DNK",
            "Finland": "FIN",
            "Kenya": "KEN",
            "Nigeria": "NGA",
            "Egypt": "EGY",
            "Argentina": "ARG",
            "Chile": "CHL",
            "Peru": "PER",
            "Colombia": "COL",
            "Ecuador": "ECU",
            "Bolivia": "BOL",
            "Venezuela": "VEN",
            "Thailand": "THA",
            "Indonesia": "IDN",
            "Philippines": "PHL",
            "Malaysia": "MYS",
            "Singapore": "SGP",
            "Vietnam": "VNM",
            "South Korea": "KOR",
            "Turkey": "TUR",
            "Poland": "POL",
            "Czech Republic": "CZE",
            "Hungary": "HUN",
            "Romania": "ROU",
            "Bulgaria": "BGR",
            "Greece": "GRC",
            "Portugal": "PRT",
            "Belgium": "BEL",
            "Austria": "AUT",
            "Switzerland": "CHE",
            "Ireland": "IRL",
            "New Zealand": "NZL",
            "Israel": "ISR",
            "Morocco": "MAR",
            "Algeria": "DZA",
            "Tunisia": "TUN",
            "Ghana": "GHA",
            "Ethiopia": "ETH",
            "Tanzania": "TZA",
            "Uganda": "UGA",
            "Rwanda": "RWA",
            "Zambia": "ZMB",
            "Zimbabwe": "ZWE",
            "Botswana": "BWA",
            "Namibia": "NAM",
            "Madagascar": "MDG",
        }

        # Convert country names to ISO-3 codes and filter valid ones
        iso_countries = []
        iso_counts = []
        country_labels = []

        for country, count in countries_data.items():
            iso_code = country_code_mapping.get(country)
            if iso_code:
                iso_countries.append(iso_code)
                iso_counts.append(count)
                country_labels.append(f"{country}: {count} users")
            else:
                logger.warning(f"No ISO-3 code mapping found for country: {country}")

        logger.info(f"Mapped to ISO codes: {dict(zip(iso_countries, iso_counts))}")

        if not iso_countries:
            return html.Div(
                [
                    html.P(
                        "No mappable country data available.", className="text-muted text-center"
                    ),
                    html.Small(
                        f"Countries found: {', '.join(countries_data.keys())}. These countries need ISO-3 code mapping.",
                        className="text-muted text-center d-block",
                    ),
                ],
                className="p-4",
            )

        # Create the choropleth map
        fig = go.Figure(
            data=go.Choropleth(
                locations=iso_countries,
                z=iso_counts,
                locationmode="ISO-3",
                colorscale="Blues",
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

        # 1. Task Performance - handle actual data structure
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
                    title="Task Performance by Execution Count",
                    xaxis_title="Number of Executions",
                    height=max(300, len(task_names) * 30),
                    margin={"l": 40, "r": 40, "t": 40, "b": 40},
                )

                charts.append(
                    html.Div(
                        [
                            html.H6("Task Performance"),
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
                        # Convert duration from string to float, handling potential formats
                        duration_str = task.get("avg_duration_minutes", "0")
                        try:
                            if isinstance(duration_str, str):
                                duration = float(duration_str)
                            else:
                                duration = float(duration_str) if duration_str else 0
                        except (ValueError, TypeError):
                            duration = 0
                        durations.append(duration)

                # Create horizontal bar chart for task duration
                fig_duration = go.Figure(
                    data=[
                        go.Bar(
                            x=durations,
                            y=task_names,
                            orientation="h",
                            hovertemplate="<b>%{y}</b><br>Avg Duration: %{x:.1f} minutes<br>Success Rate: %{customdata}%<extra></extra>",
                            customdata=success_rates,
                            marker_color="lightcoral",
                        )
                    ]
                )

                fig_duration.update_layout(
                    title="Average Task Duration",
                    xaxis_title="Average Duration (minutes)",
                    height=max(300, len(task_names) * 30),
                    margin={"l": 40, "r": 40, "t": 40, "b": 40},
                )

                charts.append(
                    html.Div(
                        [
                            html.H6("Task Duration Analysis"),
                            dcc.Graph(
                                figure=fig_duration,
                                config={"displayModeBar": False, "responsive": True},
                            ),
                        ],
                        className="mb-3",
                    )
                )

                # Create a combined scatter plot for execution count vs duration
                fig_combined = go.Figure()

                fig_combined.add_trace(
                    go.Scatter(
                        x=durations,
                        y=execution_counts,
                        mode="markers+text",
                        text=task_names,
                        textposition="top center",
                        hovertemplate="<b>%{text}</b><br>Duration: %{x:.1f} minutes<br>Executions: %{y}<br>Success Rate: %{customdata}%<extra></extra>",
                        customdata=success_rates,
                        marker={
                            "size": [max(8, min(20, count / 2)) for count in execution_counts],
                            "color": success_rates,
                            "colorscale": "RdYlGn",
                            "showscale": True,
                            "colorbar": {
                                "title": {"text": "Success Rate (%)", "side": "right"},
                                "thickness": 15,
                                "len": 0.8,
                            },
                        },
                    )
                )

                fig_combined.update_layout(
                    title="Task Performance Overview: Duration vs Execution Count",
                    xaxis_title="Average Duration (minutes)",
                    yaxis_title="Total Executions",
                    height=400,
                    margin={"l": 40, "r": 40, "t": 40, "b": 40},
                    showlegend=False,
                )

                charts.append(
                    html.Div(
                        [
                            html.H6("Task Performance Overview"),
                            html.P(
                                "Bubble size indicates execution count, color indicates success rate.",
                                className="text-muted small mb-2",
                            ),
                            dcc.Graph(
                                figure=fig_combined,
                                config={"displayModeBar": False, "responsive": True},
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

    import requests

    from trendsearth_ui.config import get_api_base

    logger = logging.getLogger(__name__)

    try:
        # Get API deployment information
        api_info = {"environment": "Unknown", "branch": "Unknown", "commit_sha": "Unknown"}
        try:
            # API health endpoint is at root level, not under /api/v1
            api_base_root = get_api_base(api_environment).replace("/api/v1", "")
            api_url = f"{api_base_root}/api-health"
            logger.info(f"Fetching API deployment info from: {api_url}")
            resp = requests.get(api_url, timeout=5)
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

        # Get API UI deployment information
        ui_info = {"environment": "Unknown", "branch": "Unknown", "commit_sha": "Unknown"}
        try:
            # Get UI health from the current application, not from API server
            from flask import request

            # Construct the UI health URL using current request context
            if request and hasattr(request, "host_url"):
                # Use the current request's host URL
                ui_url = f"{request.host_url.rstrip('/')}/api-ui-health"
            else:
                # Fallback: try localhost (for development or when no request context)
                ui_url = "http://127.0.0.1:8050/api-ui-health"

            logger.info(f"Fetching UI deployment info from current application: {ui_url}")
            resp = requests.get(ui_url, timeout=5)
            logger.info(f"UI health response status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                logger.info(f"UI health response data: {data}")
                deployment = data.get("deployment", {})
                logger.info(f"UI deployment section: {deployment}")
                ui_info = {
                    "environment": deployment.get("environment", "Unknown"),
                    "branch": deployment.get("branch", "Unknown"),
                    "commit_sha": deployment.get("commit_sha", "Unknown")[:8]
                    if deployment.get("commit_sha", "Unknown") != "Unknown"
                    else "Unknown",
                }
                logger.info(f"Processed UI info: {ui_info}")
            else:
                logger.warning(
                    f"UI health endpoint returned status {resp.status_code}: {resp.text}"
                )
        except Exception as e:
            logger.warning(f"Could not fetch API UI deployment info: {e}")

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
                            className="col-md-6 mb-3",
                        ),
                        # API UI Information Card
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.H6(
                                                    "Trends.Earth API UI", className="card-title"
                                                ),
                                                html.P(
                                                    f"Environment: {format_value(ui_info['environment'])}",
                                                    className="mb-1",
                                                ),
                                                html.P(
                                                    f"Branch: {format_value(ui_info['branch'])}",
                                                    className="mb-1",
                                                ),
                                                html.P(
                                                    [
                                                        "Commit: ",
                                                        commit_link(
                                                            "https://github.com/ConservationInternational/trends.earth-api-ui",
                                                            ui_info["commit_sha"],
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
                            className="col-md-6 mb-3",
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
                html.H4("Docker Swarm Nodes", className="mb-3"),
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
                html.H4("Docker Swarm Nodes", className="mb-3"),
                html.P("Error creating swarm status table.", className="text-danger text-center"),
                html.Small(f"Error: {str(e)}", className="text-muted text-center d-block"),
            ],
            className="p-4",
        )
