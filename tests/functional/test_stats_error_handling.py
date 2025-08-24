"""
Functional tests for enhanced stats error handling.

Tests the fix for geographic distributions and detailed analytics showing
"No data available" messages even for superadmin users.
"""

import pytest

from trendsearth_ui.utils.stats_utils import (
    fetch_dashboard_stats,
    fetch_execution_stats,
    fetch_user_stats,
)
from trendsearth_ui.utils.stats_visualizations import (
    create_dashboard_summary_cards,
    create_execution_statistics_chart,
    create_user_geographic_map,
    create_user_statistics_chart,
)


class TestStatsErrorHandling:
    """Test enhanced error handling for stats endpoints."""

    def test_fetch_user_stats_returns_error_structure_on_403(self, mocker):
        """Test that fetch_user_stats returns error structure on 403."""
        # Mock requests.get to return 403
        mock_response = mocker.Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden: SUPERADMIN privileges required"
        mocker.patch("trendsearth_ui.utils.stats_utils.requests.get", return_value=mock_response)

        result = fetch_user_stats("fake_token", "production", "last_week")

        assert result is not None
        assert result["error"] is True
        assert result["status_code"] == 403
        assert "SUPERADMIN privileges required" in result["message"]
        assert "data" in result

    def test_fetch_dashboard_stats_returns_error_structure_on_401(self, mocker):
        """Test that fetch_dashboard_stats returns error structure on 401."""
        # Mock requests.get to return 401
        mock_response = mocker.Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized: Invalid token"
        mocker.patch("trendsearth_ui.utils.stats_utils.requests.get", return_value=mock_response)

        result = fetch_dashboard_stats("fake_token", "production", "last_week")

        assert result is not None
        assert result["error"] is True
        assert result["status_code"] == 401
        assert "Invalid token" in result["message"]

    def test_visualization_functions_handle_api_errors(self):
        """Test that visualization functions properly handle API error responses."""
        # Test data representing API error response
        api_error_data = {
            "error": True,
            "status_code": 403,
            "message": "Forbidden: SUPERADMIN privileges required",
            "data": {}
        }

        # Test geographic map with API error
        result = create_user_geographic_map(api_error_data)
        assert hasattr(result, 'children')
        # Should show the standard error message
        children_text = str(result.children)
        assert "No geographic user data available" in children_text

        # Test user statistics chart with API error
        result = create_user_statistics_chart(api_error_data)
        assert isinstance(result, list)
        assert len(result) == 1
        chart_text = str(result[0].children)
        assert "No chart data available" in chart_text

    def test_visualization_functions_work_with_valid_data(self):
        """Test that visualization functions still work correctly with valid data."""
        # Test data representing successful API response
        valid_data = {
            "data": {
                "geographic": {
                    "countries": {
                        "US": 45,
                        "CA": 12,
                        "GB": 8
                    }
                },
                "trends": [
                    {"date": "2024-01-01", "new_users": 10, "total_users": 100},
                    {"date": "2024-01-02", "new_users": 15, "total_users": 115}
                ],
                "summary": {
                    "total_users": 100,
                    "total_executions": 200,
                    "active_executions": 5,
                    "recent_users": 10
                }
            }
        }

        # Test geographic map with valid data
        result = create_user_geographic_map(valid_data)
        # Should return a dcc.Graph component when successful
        assert hasattr(result, 'figure')

        # Test user statistics chart with valid data
        result = create_user_statistics_chart(valid_data)
        assert isinstance(result, list)
        assert len(result) >= 1  # Should have chart components

        # Test dashboard summary cards with valid data
        result = create_dashboard_summary_cards(valid_data)
        assert hasattr(result, 'children')
        # Should have summary cards structure
        assert hasattr(result, 'className')

    def test_backward_compatibility_with_none_data(self):
        """Test that functions still handle None data correctly (backward compatibility)."""
        # Test with None (old behavior)
        result = create_user_geographic_map(None)
        assert hasattr(result, 'children')
        children_text = str(result.children)
        assert "No geographic user data available" in children_text

        result = create_user_statistics_chart(None)
        assert isinstance(result, list)

        result = create_dashboard_summary_cards(None)
        assert hasattr(result, 'children')

    def test_empty_data_structure_handling(self):
        """Test handling of empty data structures (no error flag, but no data)."""
        # Test with empty data structure (no error flag, but no actual data)
        empty_data = {"data": {}}

        result = create_user_geographic_map(empty_data)
        assert hasattr(result, 'children')
        children_text = str(result.children)
        assert "No geographic user data available" in children_text

        result = create_user_statistics_chart(empty_data)
        assert isinstance(result, list)

        result = create_dashboard_summary_cards(empty_data)
        # Should handle empty summary data
        assert hasattr(result, 'children')
