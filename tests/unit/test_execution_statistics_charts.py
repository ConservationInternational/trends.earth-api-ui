"""Tests for execution statistics chart rendering logic."""

from dash import html
import pytest

from trendsearth_ui.utils.stats_visualizations import create_execution_statistics_chart


@pytest.fixture
def sample_execution_stats():
    """Provide sample execution statistics payload."""
    return {
        "data": {
            "time_series": [
                {
                    "timestamp": "2024-01-01T00:00:00Z",
                    "by_status": {"FINISHED": 2, "FAILED": 1},
                },
                {
                    "timestamp": "2024-02-01T00:00:00Z",
                    "by_status": {"FINISHED": 3, "FAILED": 0},
                },
            ],
            "task_performance": [],
            "top_users": [],
        }
    }


def _extract_chart_titles(components):
    titles: list[str] = []
    for component in components:
        if isinstance(component, html.Div) and component.children:
            header = component.children[0]
            if isinstance(header, html.H6):
                title_text = header.children if isinstance(header.children, str) else ""
                titles.append(title_text)
    return titles


def test_year_period_uses_cumulative_task_charts(sample_execution_stats):
    """Verify that year period swaps out running/cumulative charts with task totals."""
    charts = create_execution_statistics_chart(
        sample_execution_stats,
        status_time_series_data=[
            {
                "timestamp": "2024-01-01T00:00:00Z",
                "executions_running": 2,
                "executions_pending": 1,
            }
        ],
        user_timezone="UTC",
        ui_period="year",
    )

    titles = _extract_chart_titles(charts)

    cumulative_titles = [title for title in titles if "Cumulative" in title]
    assert any("Cumulative completed tasks" in title for title in cumulative_titles)
    assert len(cumulative_titles) == 1
    assert any("Weekly aggregation" in title for title in titles)
    assert all("Running executions" not in title for title in titles)


def test_month_period_retains_running_chart(sample_execution_stats):
    """Ensure shorter periods retain the running executions chart."""
    charts = create_execution_statistics_chart(
        sample_execution_stats,
        status_time_series_data=[
            {
                "timestamp": "2024-01-01T00:00:00Z",
                "executions_running": 2,
                "executions_pending": 0,
                "executions_ready": 1,
            }
        ],
        user_timezone="UTC",
        ui_period="month",
    )

    titles = _extract_chart_titles(charts)

    assert any(title == "Running executions" for title in titles)
    assert any("Completed executions (cumulative)" in title for title in titles)


def test_all_period_uses_monthly_aggregation_label(sample_execution_stats):
    """All-time cumulative charts should keep monthly aggregation label."""
    charts = create_execution_statistics_chart(
        sample_execution_stats,
        status_time_series_data=None,
        user_timezone="UTC",
        ui_period="all",
    )

    titles = _extract_chart_titles(charts)

    cumulative_titles = [title for title in titles if "Cumulative" in title]
    assert any("Cumulative completed tasks" in title for title in cumulative_titles)
    assert len(cumulative_titles) == 1
    assert any("Monthly aggregation" in title for title in titles)
