"""Tests for rollbar error reporting fixes."""

from unittest.mock import Mock, patch

import pytest
import requests

from trendsearth_ui.utils.stats_utils import (
    fetch_execution_stats,
    fetch_user_stats,
    get_optimal_grouping_for_period,
)


class TestOptimalGroupingFix:
    """Test fixes to get_optimal_grouping_for_period to prevent invalid group_by errors."""

    def test_last_day_returns_valid_user_group_by(self):
        """Test that last_day period returns valid group_by for user stats API."""
        user_group_by, execution_group_by = get_optimal_grouping_for_period("last_day")

        # User stats API only accepts: day, week, month (not hour)
        assert user_group_by == "day"
        assert execution_group_by == "hour"  # Execution stats API accepts hour

    def test_all_periods_return_valid_group_by(self):
        """Test that all periods return valid group_by values."""
        valid_user_values = {"day", "week", "month"}
        valid_execution_values = {"hour", "day", "week", "month"}

        test_periods = ["last_day", "last_week", "last_month", "last_year"]

        for period in test_periods:
            user_group_by, execution_group_by = get_optimal_grouping_for_period(period)
            assert user_group_by in valid_user_values, f"Invalid user group_by '{user_group_by}' for period '{period}'"
            assert execution_group_by in valid_execution_values, f"Invalid execution group_by '{execution_group_by}' for period '{period}'"

    def test_unknown_period_returns_default_valid_values(self):
        """Test that unknown periods return valid default values."""
        user_group_by, execution_group_by = get_optimal_grouping_for_period("unknown_period")

        assert user_group_by == "month"
        assert execution_group_by == "month"

    def test_function_documentation_updated(self):
        """Test that function documentation reflects the API constraints."""
        import inspect

        doc = inspect.getdoc(get_optimal_grouping_for_period)
        assert "User stats API accepts: day, week, month" in doc
        assert "Execution stats API accepts: hour, day, week, month" in doc


class TestEnhancedRollbarErrorReporting:
    """Test enhanced error reporting with Rollbar integration."""

    @patch("trendsearth_ui.utils.stats_utils.requests.get")
    @patch("trendsearth_ui.utils.stats_utils.get_cached_stats_data")
    @patch("trendsearth_ui.utils.stats_utils.log_error")
    def test_user_stats_api_error_reports_to_rollbar(self, mock_log_error, mock_cache, mock_requests):
        """Test that user stats API errors are reported to Rollbar with full context."""
        mock_cache.return_value = None
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = '{"detail":"Invalid group_by. Must be one of: day, week, month","status":400}'
        mock_requests.return_value = mock_response

        result = fetch_user_stats(
            token="test_token",
            api_environment="staging",
            period="last_week",
            group_by="invalid_group",
            country="Kenya"
        )

        # Verify error response structure
        assert result["error"] is True
        assert result["status_code"] == 400

        # Verify enhanced Rollbar reporting was called
        mock_log_error.assert_called_once()

        # Get the call arguments
        call_args = mock_log_error.call_args
        error_message = call_args[0][1]  # Second argument is the message
        extra_data = call_args[1]["extra_data"]  # Keyword argument

        # Verify error message
        assert "User stats: Failed to fetch data" in error_message
        assert "Status: 400" in error_message

        # Verify comprehensive error context
        expected_keys = {
            "api_environment",
            "status_code",
            "response_body",
            "request_params",
            "api_endpoint",
            "period",
            "group_by",
            "country"
        }
        assert all(key in extra_data for key in expected_keys)

        # Verify specific values
        assert extra_data["api_environment"] == "staging"
        assert extra_data["status_code"] == 400
        assert extra_data["period"] == "last_week"
        assert extra_data["group_by"] == "invalid_group"
        assert extra_data["country"] == "Kenya"

    @patch("trendsearth_ui.utils.stats_utils.requests.get")
    @patch("trendsearth_ui.utils.stats_utils.get_cached_stats_data")
    @patch("trendsearth_ui.utils.stats_utils.log_error")
    def test_user_stats_network_error_reports_to_rollbar(self, mock_log_error, mock_cache, mock_requests):
        """Test that user stats network errors are reported to Rollbar with context."""
        mock_cache.return_value = None
        mock_requests.side_effect = requests.exceptions.ConnectionError("Network error")

        result = fetch_user_stats(
            token="test_token",
            api_environment="production",
            period="last_month"
        )

        # Verify error response structure
        assert result["error"] is True
        assert result["status_code"] == "network_error"

        # Verify enhanced Rollbar reporting was called
        mock_log_error.assert_called_once()

        # Get the call arguments
        call_args = mock_log_error.call_args
        error_message = call_args[0][1]  # Second argument is the message
        extra_data = call_args[1]["extra_data"]  # Keyword argument

        # Verify error message
        assert "User stats: Request failed" in error_message
        assert "Network error" in error_message

        # Verify comprehensive error context
        expected_keys = {
            "api_environment",
            "exception_type",
            "request_params",
            "api_endpoint",
            "period",
            "group_by",
            "country"
        }
        assert all(key in extra_data for key in expected_keys)

        # Verify specific values
        assert extra_data["api_environment"] == "production"
        assert extra_data["exception_type"] == "ConnectionError"
        assert extra_data["period"] == "last_month"

    @patch("trendsearth_ui.utils.stats_utils.requests.get")
    @patch("trendsearth_ui.utils.stats_utils.get_cached_stats_data")
    @patch("trendsearth_ui.utils.stats_utils.log_error")
    def test_execution_stats_api_error_reports_to_rollbar(self, mock_log_error, mock_cache, mock_requests):
        """Test that execution stats API errors are reported to Rollbar with full context."""
        mock_cache.return_value = None
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = '{"detail":"Internal server error","status":500}'
        mock_requests.return_value = mock_response

        result = fetch_execution_stats(
            token="test_token",
            api_environment="staging",
            period="last_week",
            group_by="day",
            task_type="land_cover",
            status="FAILED"
        )

        # Verify error response structure
        assert result["error"] is True
        assert result["status_code"] == 500

        # Verify enhanced Rollbar reporting was called
        mock_log_error.assert_called_once()

        # Get the call arguments
        call_args = mock_log_error.call_args
        error_message = call_args[0][1]  # Second argument is the message
        extra_data = call_args[1]["extra_data"]  # Keyword argument

        # Verify error message
        assert "Execution stats: Failed to fetch data" in error_message
        assert "Status: 500" in error_message

        # Verify comprehensive error context
        expected_keys = {
            "api_environment",
            "status_code",
            "response_body",
            "request_params",
            "api_endpoint",
            "period",
            "group_by",
            "task_type",
            "status"
        }
        assert all(key in extra_data for key in expected_keys)

        # Verify specific values
        assert extra_data["api_environment"] == "staging"
        assert extra_data["status_code"] == 500
        assert extra_data["period"] == "last_week"
        assert extra_data["group_by"] == "day"
        assert extra_data["task_type"] == "land_cover"
        assert extra_data["status"] == "FAILED"
        assert "/stats/executions" in extra_data["api_endpoint"]

    @patch("trendsearth_ui.utils.stats_utils.requests.get")
    @patch("trendsearth_ui.utils.stats_utils.get_cached_stats_data")
    @patch("trendsearth_ui.utils.stats_utils.log_error")
    def test_successful_requests_do_not_report_to_rollbar(self, mock_log_error, mock_cache, mock_requests):
        """Test that successful requests do not trigger Rollbar error reporting."""
        mock_cache.return_value = None
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"users": 100}}
        mock_requests.return_value = mock_response

        result = fetch_user_stats(token="test_token")

        # Verify successful response
        assert "error" not in result
        assert result == {"data": {"users": 100}}

        # Verify Rollbar error reporting was NOT called
        mock_log_error.assert_not_called()


class TestIntegrationWithStatusDataManager:
    """Test that the fixes work correctly with StatusDataManager."""

    @patch("trendsearth_ui.utils.status_data_manager.fetch_scripts_count")
    @patch("trendsearth_ui.utils.status_data_manager.fetch_execution_stats")
    @patch("trendsearth_ui.utils.status_data_manager.fetch_dashboard_stats")
    @patch("trendsearth_ui.utils.status_data_manager.fetch_user_stats")
    def test_status_data_manager_uses_corrected_group_by(self, mock_fetch_user_stats, mock_fetch_dashboard_stats, mock_fetch_execution_stats, mock_fetch_scripts_count):
        """Test that StatusDataManager gets corrected group_by values."""
        from trendsearth_ui.utils.status_data_manager import StatusDataManager

        # Mock all the function calls
        mock_fetch_user_stats.return_value = {"data": {"users": 50}}
        mock_fetch_dashboard_stats.return_value = {"data": {"dashboard": "data"}}
        mock_fetch_execution_stats.return_value = {"data": {"executions": "data"}}
        mock_fetch_scripts_count.return_value = 10

        # This should use the corrected group_by values and not cause API errors
        StatusDataManager.fetch_consolidated_stats_data(
            token="test_token",
            api_environment="production",
            time_period="day",  # Maps to last_day API period
            role="SUPERADMIN"
        )

        # Verify the call was made with corrected group_by
        mock_fetch_user_stats.assert_called_once()
        call_args = mock_fetch_user_stats.call_args

        # Check positional and keyword arguments
        # The function is called with: token, api_environment, period, group_by=user_group_by
        positional_args = call_args[0]
        keyword_args = call_args[1]

        # Should be called with group_by="day" (not "hour")
        assert keyword_args["group_by"] == "day"
        assert positional_args[1] == "production"  # api_environment
        assert positional_args[2] == "last_day"    # period

    def test_get_optimal_grouping_prevents_original_error(self):
        """Test that the fix prevents the original invalid group_by error."""
        # The original error was caused by passing "hour" for user stats
        # Our fix should prevent this

        user_group_by, execution_group_by = get_optimal_grouping_for_period("last_day")

        # Should NOT be "hour" for user stats (this was the bug)
        assert user_group_by != "hour"
        assert user_group_by == "day"  # Should be a valid value

        # Execution stats can still use "hour"
        assert execution_group_by == "hour"
