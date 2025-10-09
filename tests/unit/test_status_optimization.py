"""Test status page optimization features."""

from unittest.mock import Mock, patch

import pytest

from trendsearth_ui.utils.status_data_manager import StatusDataManager


class TestStatusDataManager:
    """Test the StatusDataManager optimization utility."""

    def test_cache_key_generation(self):
        """Test that cache keys are generated correctly."""
        # Test basic cache key
        key = StatusDataManager.get_cache_key("test_type", param1="value1", param2="value2")
        assert key == "test_type_param1=value1_param2=value2"

        # Test cache key with None values
        key = StatusDataManager.get_cache_key("test_type", param1="value1", param2=None)
        assert key == "test_type_param1=value1"

        # Test cache key without parameters
        key = StatusDataManager.get_cache_key("test_type")
        assert key == "test_type"

    def test_cache_operations(self):
        """Test cache get and set operations."""
        # Test status cache
        StatusDataManager.set_cached_data("test_key", {"data": "test"}, cache_type="status")
        cached_data = StatusDataManager.get_cached_data("test_key", cache_type="status")
        assert cached_data == {"data": "test"}

        # Test stats cache
        StatusDataManager.set_cached_data("test_key_stats", {"stats": "test"}, cache_type="stats")
        cached_data = StatusDataManager.get_cached_data("test_key_stats", cache_type="stats")
        assert cached_data == {"stats": "test"}

        # Test cache miss
        cached_data = StatusDataManager.get_cached_data("nonexistent_key", cache_type="status")
        assert cached_data is None

    def test_cache_invalidation(self):
        """Test cache invalidation functionality."""
        # Clear existing cache first
        StatusDataManager.invalidate_cache()

        # Set up some test data
        StatusDataManager.set_cached_data("status_test1", {"data": "1"}, cache_type="status")
        StatusDataManager.set_cached_data("status_test2", {"data": "2"}, cache_type="status")
        StatusDataManager.set_cached_data("stats_test1", {"data": "3"}, cache_type="stats")

        # Test pattern-based invalidation
        cleared_count = StatusDataManager.invalidate_cache("status")
        assert cleared_count >= 2  # Should clear at least the two status entries (may have others)

        # Verify status cache was cleared but stats cache wasn't
        assert StatusDataManager.get_cached_data("status_test1", cache_type="status") is None
        assert StatusDataManager.get_cached_data("status_test2", cache_type="status") is None
        assert StatusDataManager.get_cached_data("stats_test1", cache_type="stats") is not None

        # Test full cache clear
        cleared_count = StatusDataManager.invalidate_cache()
        assert cleared_count >= 1  # Should clear remaining entries

    @patch("trendsearth_ui.utils.status_data_manager.requests.get")
    def test_consolidated_status_data_fetching(self, mock_get):
        """Test consolidated status data fetching with caching."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"timestamp": "2023-01-01", "executions_running": 5}]
        }
        mock_get.return_value = mock_response

        # Mock the helper functions
        with (
            patch(
                "trendsearth_ui.utils.status_data_manager.fetch_deployment_info"
            ) as mock_deployment,
            patch("trendsearth_ui.utils.status_data_manager.fetch_swarm_info") as mock_swarm,
            patch(
                "trendsearth_ui.utils.status_data_manager.is_status_endpoint_available"
            ) as mock_available,
        ):
            mock_deployment.return_value = {"deployment": "info"}
            mock_swarm.return_value = ({"swarm": "info"}, " (cached)")
            mock_available.return_value = True

            # First call should fetch from API
            result1 = StatusDataManager.fetch_consolidated_status_data(
                token="test_token", api_environment="test"
            )

            # Verify the result structure
            assert result1["summary"] == "SUCCESS"
            assert result1["deployment"] == {"deployment": "info"}
            assert result1["swarm"] == {"swarm": "info"}
            assert result1["status_endpoint_available"] is True
            assert result1["latest_status"]["executions_running"] == 5

            # Second call should use cache (no additional API call)
            result2 = StatusDataManager.fetch_consolidated_status_data(
                token="test_token", api_environment="test"
            )

            # Should be the same result
            assert result1 == result2

            # Should have only made one API call due to caching
            assert mock_get.call_count == 1

    def test_consolidated_stats_data_permission_check(self):
        """Test that stats data fetching checks for SUPERADMIN permissions."""
        # Test with non-SUPERADMIN role
        result = StatusDataManager.fetch_consolidated_stats_data(
            token="test_token", api_environment="test", time_period="day", role="ADMIN"
        )

        assert result["error"] == "Insufficient permissions"
        assert result["requires_superadmin"] is True

    @patch("trendsearth_ui.utils.status_data_manager.requests.get")
    def test_time_series_data_fetching_with_caching(self, mock_get):
        """Test time series data fetching with caching."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "data": [{"timestamp": "2023-01-01", "executions_active": 3}]
        }
        mock_get.return_value = mock_response

        # First call should fetch from API
        result1 = StatusDataManager.fetch_time_series_status_data(
            token="test_token", api_environment="test", time_period="day"
        )

        # Verify the result structure
        assert result1["data"] == [{"timestamp": "2023-01-01", "executions_active": 3}]
        assert result1["time_period"] == "day"
        assert result1["error"] is None

        # Second call should use cache
        result2 = StatusDataManager.fetch_time_series_status_data(
            token="test_token", api_environment="test", time_period="day"
        )

        # Should be the same result
        assert result1 == result2

        # Should have only made one API call due to caching
        assert mock_get.call_count == 1


class TestStatusCallbackOptimization:
    """Test that status callbacks use the optimization features."""

    @patch("trendsearth_ui.callbacks.status.StatusDataManager.invalidate_cache")
    def test_manual_refresh_invalidates_cache(self, mock_invalidate):
        """Test that manual refresh triggers cache invalidation."""
        from trendsearth_ui.callbacks.status import register_callbacks

        # Create a mock app
        mock_app = Mock()
        callback_functions = {}

        def capture_callback(*args, **kwargs):
            def decorator(func):
                callback_functions[func.__name__] = func
                return func

            return decorator

        mock_app.callback = capture_callback

        # Register callbacks
        register_callbacks(mock_app)

        # Get the time-independent status callback (renamed from update_comprehensive_status_data)
        status_summary_func = callback_functions.get("update_time_independent_status_data")
        assert status_summary_func is not None

        # Mock the callback context to simulate manual refresh
        with (
            patch("trendsearth_ui.callbacks.status.callback_context") as mock_ctx,
            patch("trendsearth_ui.utils.status_helpers.fetch_deployment_info") as mock_deployment,
            patch("trendsearth_ui.utils.status_helpers.fetch_swarm_info") as mock_swarm,
            patch(
                "trendsearth_ui.callbacks.status.StatusDataManager.fetch_comprehensive_status_page_data"
            ) as mock_status_data,
        ):
            # Set up mocks
            mock_ctx.triggered = [{"prop_id": "refresh-status-btn.n_clicks"}]
            mock_deployment.return_value = {"deployment": "info"}
            mock_swarm.return_value = ({"swarm": "info"}, "")
            mock_status_data.return_value = {
                "status_data": {"summary": "SUCCESS"},
                "deployment_data": {"deployment": "info"},
                "swarm_data": {"info": {"swarm": "info"}, "cached_time": ""},
                "stats_data": {},
                "meta": {"cache_hit": False},
            }

            # Call the function with manual refresh (time-independent callback doesn't need time_period)
            status_summary_func(
                _n_intervals=1,
                _refresh_clicks=1,
                token="test_token",
                active_tab="status",
                user_timezone="UTC",
                role="ADMIN",
                api_environment="test",
            )

            # Verify that cache invalidation was called
            mock_invalidate.assert_called_once_with("status")

    def test_optimization_integration_in_callbacks(self):
        """Test that StatusDataManager is properly imported and available in callbacks."""
        from trendsearth_ui.callbacks import status

        # Verify StatusDataManager is available
        assert hasattr(status, "StatusDataManager")
        assert status.StatusDataManager is not None

        # Verify key methods are available
        assert hasattr(status.StatusDataManager, "fetch_consolidated_status_data")
        assert hasattr(status.StatusDataManager, "fetch_consolidated_stats_data")
        assert hasattr(status.StatusDataManager, "fetch_time_series_status_data")
        assert hasattr(status.StatusDataManager, "invalidate_cache")
