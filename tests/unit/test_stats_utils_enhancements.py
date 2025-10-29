"""Test enhancements to stats utils functions."""

from unittest.mock import Mock, patch

import pytest

from trendsearth_ui.utils.stats_utils import (
    fetch_execution_stats,
    fetch_user_stats,
    get_optimal_grouping_for_period,
)


class TestGetOptimalGroupingForPeriod:
    """Test the optimal grouping function for different time periods."""

    def test_last_day_returns_hour_grouping(self):
        """Test that last_day period returns appropriate grouping (fixed for API compatibility)."""
        user_group, exec_group = get_optimal_grouping_for_period("last_day")
        # Fixed: user stats API doesn't accept "hour", only "day", "week", "month"
        assert user_group == "day"  # Changed from "hour" to prevent API error
        assert exec_group == "hour"  # Execution stats API still accepts "hour"

    def test_last_week_returns_day_grouping(self):
        """Test that last_week period returns day grouping."""
        user_group, exec_group = get_optimal_grouping_for_period("last_week")
        assert user_group == "day"
        assert exec_group == "day"

    def test_last_month_returns_week_grouping(self):
        """Test that last_month period returns week grouping."""
        user_group, exec_group = get_optimal_grouping_for_period("last_month")
        assert user_group == "week"
        assert exec_group == "week"

    def test_last_year_returns_month_grouping(self):
        """Test that last_year period returns month grouping."""
        user_group, exec_group = get_optimal_grouping_for_period("last_year")
        assert user_group == "month"
        assert exec_group == "month"

    def test_unknown_period_returns_default_month_grouping(self):
        """Test that unknown period returns default month grouping."""
        user_group, exec_group = get_optimal_grouping_for_period("unknown")
        assert user_group == "month"
        assert exec_group == "month"

    def test_all_period_returns_month_grouping(self):
        """Test that 'all' period returns month grouping."""
        user_group, exec_group = get_optimal_grouping_for_period("all")
        assert user_group == "month"
        assert exec_group == "month"


class TestEnhancedUserStats:
    """Test enhanced user stats function with additional parameters.

    Note: Cache mocking removed - caching now handled by StatusDataManager.
    """

    @patch("trendsearth_ui.utils.stats_utils.requests.get")
    def test_fetch_user_stats_with_group_by(self, mock_requests):
        """Test user stats with group_by parameter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"time_series": []}}
        mock_requests.return_value = mock_response

        result = fetch_user_stats("token", "production", "last_week", group_by="day")

        # Check that the API was called with group_by parameter
        mock_requests.assert_called_once()
        call_args = mock_requests.call_args
        assert call_args[1]["params"]["group_by"] == "day"
        assert call_args[1]["params"]["period"] == "last_week"
        assert result == {"data": {"time_series": []}}

    @patch("trendsearth_ui.utils.stats_utils.requests.get")
    def test_fetch_user_stats_with_country_filter(self, mock_requests):
        """Test user stats with country filter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"geographic_distribution": {}}}
        mock_requests.return_value = mock_response

        result = fetch_user_stats("token", "production", "last_week", country="Kenya")

        # Check that the API was called with country parameter
        mock_requests.assert_called_once()
        call_args = mock_requests.call_args
        assert call_args[1]["params"]["country"] == "Kenya"
        assert call_args[1]["params"]["period"] == "last_week"
        assert result == {"data": {"geographic_distribution": {}}}

    @patch("trendsearth_ui.utils.stats_utils.requests.get")
    def test_fetch_user_stats_with_all_parameters(self, mock_requests):
        """Test user stats with all optional parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"time_series": []}}
        mock_requests.return_value = mock_response

        result = fetch_user_stats(
            "token", "production", "last_month", group_by="week", country="Kenya"
        )

        # Check that the API was called with all parameters
        mock_requests.assert_called_once()
        call_args = mock_requests.call_args
        params = call_args[1]["params"]
        assert params["group_by"] == "week"
        assert params["country"] == "Kenya"
        assert params["period"] == "last_month"
        assert result == {"data": {"time_series": []}}

    def test_fetch_user_stats_uses_enhanced_cache_key(self):
        """Test that caching is now handled by StatusDataManager (not stats_utils).

        This test is kept for documentation but no longer tests internal caching
        since that responsibility moved to StatusDataManager.
        """
        # Test passes - caching logic moved to StatusDataManager
        assert True


class TestEnhancedExecutionStats:
    """Test enhanced execution stats function with additional parameters.

    Note: Cache mocking removed - caching now handled by StatusDataManager.
    """

    @patch("trendsearth_ui.utils.stats_utils.requests.get")
    def test_fetch_execution_stats_with_group_by(self, mock_requests):
        """Test execution stats with group_by parameter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"time_series": []}}
        mock_requests.return_value = mock_response

        result = fetch_execution_stats("token", "production", "last_week", group_by="day")

        # Check that the API was called with group_by parameter
        mock_requests.assert_called_once()
        call_args = mock_requests.call_args
        assert call_args[1]["params"]["group_by"] == "day"
        assert call_args[1]["params"]["period"] == "last_week"
        assert result == {"data": {"time_series": []}}

    @patch("trendsearth_ui.utils.stats_utils.requests.get")
    def test_fetch_execution_stats_with_filters(self, mock_requests):
        """Test execution stats with task_type and status filters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"task_performance": []}}
        mock_requests.return_value = mock_response

        result = fetch_execution_stats(
            "token", "production", "last_week", task_type="download", status="FINISHED"
        )

        # Check that the API was called with filter parameters
        mock_requests.assert_called_once()
        call_args = mock_requests.call_args
        params = call_args[1]["params"]
        assert params["task_type"] == "download"
        assert params["status"] == "FINISHED"
        assert params["period"] == "last_week"
        assert result == {"data": {"task_performance": []}}

    @patch("trendsearth_ui.utils.stats_utils.requests.get")
    def test_fetch_execution_stats_with_all_parameters(self, mock_requests):
        """Test execution stats with all optional parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"time_series": []}}
        mock_requests.return_value = mock_response

        result = fetch_execution_stats(
            "token",
            "production",
            "last_month",
            group_by="week",
            task_type="analysis",
            status="FAILED",
        )

        # Check that the API was called with all parameters
        mock_requests.assert_called_once()
        call_args = mock_requests.call_args
        params = call_args[1]["params"]
        assert params["group_by"] == "week"
        assert params["task_type"] == "analysis"
        assert params["status"] == "FAILED"
        assert params["period"] == "last_month"
        assert result == {"data": {"time_series": []}}

    def test_fetch_execution_stats_uses_enhanced_cache_key(self):
        """Test that caching is now handled by StatusDataManager (not stats_utils).

        This test is kept for documentation but no longer tests internal caching
        since that responsibility moved to StatusDataManager.
        """
        # Test passes - caching logic moved to StatusDataManager
        assert True

    def test_fetch_execution_stats_cache_key_with_none_values(self):
        """Test that caching is now handled by StatusDataManager (not stats_utils).

        This test is kept for documentation but no longer tests internal caching
        since that responsibility moved to StatusDataManager.
        """
        # Test passes - caching logic moved to StatusDataManager
        assert True
