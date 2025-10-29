"""Test new status page features."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from trendsearth_ui.utils.http_client import DEFAULT_ACCEPT_ENCODING
from trendsearth_ui.utils.stats_utils import fetch_scripts_count
from trendsearth_ui.utils.stats_visualizations import create_dashboard_summary_cards
from trendsearth_ui.utils.status_helpers import _fetch_health_status


class TestScriptsCountFunctionality:
    """Test scripts count fetching functionality.

    Note: Cache management removed - now handled by StatusDataManager.
    """

    @patch("trendsearth_ui.utils.stats_utils.requests.get")
    def test_fetch_scripts_count_success(self, mock_get):
        """Test successful scripts count fetching."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"id": "script1"}, {"id": "script2"}],
            "total": 42,
            "page": 1,
            "per_page": 1,
        }
        mock_get.return_value = mock_response

        # Test the function
        result = fetch_scripts_count("fake_token", "production")

        # Verify the result
        assert result == 42
        mock_get.assert_called_once()
        headers = mock_get.call_args[1]["headers"]
        assert headers["Accept-Encoding"] == DEFAULT_ACCEPT_ENCODING

    @patch("trendsearth_ui.utils.stats_utils.requests.get")
    def test_fetch_scripts_count_no_total(self, mock_get):
        """Test scripts count when total is not in response."""
        # Mock response without total field
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"id": "script1"}, {"id": "script2"}]
            # No "total" field
        }
        mock_get.return_value = mock_response

        result = fetch_scripts_count("fake_token", "production")

        # Should fallback to length of data array
        assert result == 2
        mock_get.assert_called_once()
        headers = mock_get.call_args[1]["headers"]
        assert headers["Accept-Encoding"] == DEFAULT_ACCEPT_ENCODING

    def test_fetch_scripts_count_no_token(self):
        """Test scripts count without token."""
        result = fetch_scripts_count(None, "production")
        assert result == 0

    @patch("trendsearth_ui.utils.stats_utils.requests.get")
    def test_fetch_scripts_count_api_error(self, mock_get):
        """Test scripts count with API error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = fetch_scripts_count("fake_token", "production")
        assert result == 0
        mock_get.assert_called_once()
        headers = mock_get.call_args[1]["headers"]
        assert headers["Accept-Encoding"] == DEFAULT_ACCEPT_ENCODING


class TestDashboardSummaryCardsWithScripts:
    """Test dashboard summary cards with scripts count."""

    def test_create_dashboard_summary_cards_with_scripts(self):
        """Test dashboard summary cards with scripts count."""
        mock_dashboard_data = {
            "data": {
                "summary": {
                    "total_users": 100,
                    "total_jobs": 500,  # API uses total_jobs
                    "jobs_last_day": 25,
                    "users_last_day": 5,
                }
            }
        }

        result = create_dashboard_summary_cards(mock_dashboard_data, scripts_count=42)

        # Verify it's an HTML div
        assert hasattr(result, "children")

        # Convert to string to check content
        result_str = str(result)

        # Should contain all the expected values
        assert "100" in result_str  # total users
        assert "42" in result_str  # scripts count
        assert "500" in result_str  # total executions
        assert "25" in result_str  # active executions
        assert "5" in result_str  # recent users

    def test_create_dashboard_summary_cards_no_scripts_count(self):
        """Test dashboard summary cards without scripts count."""
        mock_dashboard_data = {
            "data": {
                "summary": {
                    "total_users": 100,
                    "total_jobs": 500,
                    "jobs_last_day": 25,
                    "users_last_day": 5,
                }
            }
        }

        result = create_dashboard_summary_cards(mock_dashboard_data, scripts_count=None)
        result_str = str(result)

        # Should default to 0 for scripts
        assert "0" in result_str  # scripts count should be 0


class TestHealthEndpointRetryLogic:
    """Test health endpoint retry logic improvements."""

    @patch("trendsearth_ui.utils.status_helpers.time.sleep")
    @patch("trendsearth_ui.utils.status_helpers.requests.get")
    def test_fetch_health_status_retry_on_timeout(self, mock_get, mock_sleep):
        """Test that health status retries on timeout."""
        import requests

        # Mock timeout exception for first two calls, success on third
        mock_get.side_effect = [
            requests.exceptions.Timeout("timeout"),  # First call fails
            requests.exceptions.Timeout("timeout"),  # Second call fails
            Mock(status_code=200, json=lambda: {"status": "ok"}),  # Third call succeeds
        ]

        success, data, status, error = _fetch_health_status("http://test.com")

        # Should have retried and eventually succeeded
        assert success is True
        assert data == {"status": "ok"}
        assert status == 200
        assert error is None
        assert mock_get.call_count == 3
        assert mock_sleep.call_count == 2  # Sleep between retries
        headers = mock_get.call_args_list[0][1]["headers"]
        assert headers["Accept-Encoding"] == DEFAULT_ACCEPT_ENCODING

    @patch("trendsearth_ui.utils.status_helpers.time.sleep")
    @patch("trendsearth_ui.utils.status_helpers.requests.get")
    def test_fetch_health_status_give_up_after_retries(self, mock_get, mock_sleep):
        """Test that health status gives up after max retries."""
        import requests

        # Mock timeout exception for all calls
        mock_get.side_effect = requests.exceptions.Timeout("persistent timeout")

        success, data, status, error = _fetch_health_status("http://test.com")

        # Should have failed after all retries
        assert success is False
        assert data is None
        assert status == 0
        assert error == "Timeout"
        assert mock_get.call_count == 3  # Initial + 2 retries
        assert mock_sleep.call_count == 2  # Sleep between retries
        headers = mock_get.call_args_list[0][1]["headers"]
        assert headers["Accept-Encoding"] == DEFAULT_ACCEPT_ENCODING

    @patch("trendsearth_ui.utils.status_helpers.requests.get")
    def test_fetch_health_status_no_retry_on_client_error(self, mock_get):
        """Test that health status doesn't retry on 4xx errors."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        success, data, status, error = _fetch_health_status("http://test.com")

        # Should not retry on 4xx error
        assert success is False
        assert data is None
        assert status == 404
        assert error == "HTTP 404"
        assert mock_get.call_count == 1  # No retries
        headers = mock_get.call_args[1]["headers"]
        assert headers["Accept-Encoding"] == DEFAULT_ACCEPT_ENCODING
