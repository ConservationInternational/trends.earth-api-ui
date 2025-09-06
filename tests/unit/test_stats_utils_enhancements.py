"""Test enhancements to stats utils functions."""

import pytest
from unittest.mock import patch, Mock

from trendsearth_ui.utils.stats_utils import (
    fetch_user_stats,
    fetch_execution_stats,
    get_optimal_grouping_for_period,
)


class TestGetOptimalGroupingForPeriod:
    """Test the optimal grouping function for different time periods."""

    def test_last_day_returns_hour_grouping(self):
        """Test that last_day period returns hour grouping."""
        user_group, exec_group = get_optimal_grouping_for_period("last_day")
        assert user_group == "hour"
        assert exec_group == "hour"

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
    """Test enhanced user stats function with additional parameters."""

    @patch("trendsearth_ui.utils.stats_utils.requests.get")
    @patch("trendsearth_ui.utils.stats_utils.get_cached_stats_data")
    def test_fetch_user_stats_with_group_by(self, mock_cache, mock_requests):
        """Test user stats with group_by parameter."""
        mock_cache.return_value = None
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

    @patch("trendsearth_ui.utils.stats_utils.requests.get")
    @patch("trendsearth_ui.utils.stats_utils.get_cached_stats_data")
    def test_fetch_user_stats_with_country_filter(self, mock_cache, mock_requests):
        """Test user stats with country filter."""
        mock_cache.return_value = None
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

    @patch("trendsearth_ui.utils.stats_utils.requests.get")
    @patch("trendsearth_ui.utils.stats_utils.get_cached_stats_data")
    def test_fetch_user_stats_with_all_parameters(self, mock_cache, mock_requests):
        """Test user stats with all optional parameters."""
        mock_cache.return_value = None
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

    @patch("trendsearth_ui.utils.stats_utils.get_cached_stats_data")
    def test_fetch_user_stats_uses_enhanced_cache_key(self, mock_cache):
        """Test that enhanced caching uses all parameters in cache key."""
        mock_cache.return_value = {"cached": "data"}

        result = fetch_user_stats(
            "token", "production", "last_week", group_by="day", country="Kenya"
        )

        # Check that cache was called with enhanced key
        mock_cache.assert_called_once_with("users", "last_week_day_Kenya")
        assert result == {"cached": "data"}


class TestEnhancedExecutionStats:
    """Test enhanced execution stats function with additional parameters."""

    @patch("trendsearth_ui.utils.stats_utils.requests.get")
    @patch("trendsearth_ui.utils.stats_utils.get_cached_stats_data")
    def test_fetch_execution_stats_with_group_by(self, mock_cache, mock_requests):
        """Test execution stats with group_by parameter."""
        mock_cache.return_value = None
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

    @patch("trendsearth_ui.utils.stats_utils.requests.get")
    @patch("trendsearth_ui.utils.stats_utils.get_cached_stats_data")
    def test_fetch_execution_stats_with_filters(self, mock_cache, mock_requests):
        """Test execution stats with task_type and status filters."""
        mock_cache.return_value = None
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

    @patch("trendsearth_ui.utils.stats_utils.requests.get")
    @patch("trendsearth_ui.utils.stats_utils.get_cached_stats_data")
    def test_fetch_execution_stats_with_all_parameters(self, mock_cache, mock_requests):
        """Test execution stats with all optional parameters."""
        mock_cache.return_value = None
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
            status="FAILED"
        )

        # Check that the API was called with all parameters
        mock_requests.assert_called_once()
        call_args = mock_requests.call_args
        params = call_args[1]["params"]
        assert params["group_by"] == "week"
        assert params["task_type"] == "analysis"
        assert params["status"] == "FAILED"
        assert params["period"] == "last_month"

    @patch("trendsearth_ui.utils.stats_utils.get_cached_stats_data")
    def test_fetch_execution_stats_uses_enhanced_cache_key(self, mock_cache):
        """Test that enhanced caching uses all parameters in cache key."""
        mock_cache.return_value = {"cached": "data"}

        result = fetch_execution_stats(
            "token",
            "production",
            "last_week",
            group_by="day",
            task_type="download",
            status="FINISHED"
        )

        # Check that cache was called with enhanced key
        mock_cache.assert_called_once_with("executions", "last_week_day_download_FINISHED")
        assert result == {"cached": "data"}

    @patch("trendsearth_ui.utils.stats_utils.get_cached_stats_data")
    def test_fetch_execution_stats_cache_key_with_none_values(self, mock_cache):
        """Test cache key generation with None values."""
        mock_cache.return_value = {"cached": "data"}

        result = fetch_execution_stats("token", "production", "last_week")

        # Check that cache was called with 'none' for missing parameters
        mock_cache.assert_called_once_with("executions", "last_week_none_none_none")
        assert result == {"cached": "data"}