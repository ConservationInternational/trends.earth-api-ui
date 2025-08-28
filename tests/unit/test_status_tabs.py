"""
Unit tests for the new status tab functionality including manual tab switching.
"""

from unittest.mock import MagicMock, Mock, patch

from dash import dcc, html
import pytest

from trendsearth_ui.callbacks.status import register_callbacks
from trendsearth_ui.components.tabs import status_tab_content


class TestStatusTabStructure:
    """Test the structure and visibility of status tabs."""

    def test_status_tab_contains_manual_nav_tabs(self):
        """Test that status tab contains proper Bootstrap nav tabs structure."""
        content = status_tab_content(is_admin=True)
        content_str = str(content)

        # Should contain Bootstrap nav tabs structure
        assert "nav nav-tabs" in content_str
        assert "nav-item" in content_str
        assert "nav-link" in content_str

    def test_status_tab_contains_all_time_period_tabs(self):
        """Test that all time period tabs are present."""
        content = status_tab_content(is_admin=True)
        content_str = str(content)

        # Should contain all time period tabs
        assert "Last 24 Hours" in content_str
        assert "Last Week" in content_str
        assert "Last Month" in content_str

    def test_status_tab_contains_tab_ids(self):
        """Test that all required tab IDs are present."""
        content = status_tab_content(is_admin=True)
        content_str = str(content)

        # Should contain all tab IDs
        assert "status-tab-day" in content_str
        assert "status-tab-week" in content_str
        assert "status-tab-month" in content_str

    def test_status_tab_contains_data_store(self):
        """Test that status tab contains the data store for tab state."""
        content = status_tab_content(is_admin=True)
        content_str = str(content)

        # Should contain the store component
        assert "status-time-tabs-store" in content_str

    def test_status_tab_default_active_tab(self):
        """Test that the default active tab is properly set."""
        content = status_tab_content(is_admin=True)
        content_str = str(content)

        # Should have "Last 24 Hours" as the default active tab
        # Look for the active class on the first tab
        assert "nav-link active" in content_str

    def test_status_tab_charts_container(self):
        """Test that status tab contains charts container."""
        content = status_tab_content(is_admin=True)
        content_str = str(content)

        # Should contain charts container
        assert "status-charts" in content_str
        assert "loading-status-charts" in content_str

    def test_status_tab_refresh_components(self):
        """Test that status tab contains refresh components."""
        content = status_tab_content(is_admin=True)
        content_str = str(content)

        # Should contain refresh button and countdown
        assert "refresh-status-btn" in content_str
        assert "status-countdown" in content_str
        assert "status-auto-refresh-interval" in content_str
        assert "status-countdown-interval" in content_str

    def test_status_tab_non_admin_access_denied(self):
        """Test that non-admin users see access denied message."""
        content = status_tab_content(is_admin=False)
        content_str = str(content)

        # Should contain access denied message
        assert "Access denied" in content_str
        assert "Administrator privileges required" in content_str

    def test_status_tab_manual_tabs_not_dbc_tabs(self):
        """Test that manual tabs are used instead of dbc.Tabs."""
        content = status_tab_content(is_admin=True)
        content_str = str(content)

        # Should NOT contain dbc.Tabs references (which were causing issues)
        assert "dbc.Tab(" not in content_str
        assert "dbc.Tabs(" not in content_str

        # Should contain manual HTML nav structure
        assert "html.Ul(" in content_str or "nav nav-tabs" in content_str


class TestStatusTabCallbacks:
    """Test the status tab callback functionality."""

    def test_tab_switching_callback_registration(self):
        """Test that tab switching callback is properly registered."""
        mock_app = Mock()
        mock_app.callback = Mock()

        register_callbacks(mock_app)

        # Should have registered callbacks
        assert mock_app.callback.called
        callback_calls = mock_app.callback.call_args_list

        # Find the tab switching callback
        tab_switching_callback = None
        for call in callback_calls:
            outputs = call[0][0] if call[0] else []
            if isinstance(outputs, list) and len(outputs) >= 4:
                # Check if this looks like our tab switching callback
                output_strs = [str(output) for output in outputs]
                if any("status-tab-day" in s for s in output_strs):
                    tab_switching_callback = call
                    break

        assert tab_switching_callback is not None, "Tab switching callback should be registered"

    @patch("trendsearth_ui.callbacks.status.callback_context")
    def test_tab_switching_logic(self, mock_ctx):
        """Test the tab switching logic."""
        from trendsearth_ui.callbacks.status import register_callbacks

        # Create a mock app
        mock_app = Mock()
        callback_functions = {}

        def capture_callback(*args, **kwargs):
            def decorator(func):
                # Store the function for testing
                callback_functions[func.__name__] = func
                return func

            return decorator

        mock_app.callback = capture_callback
        register_callbacks(mock_app)

        # Get the tab switching function
        tab_switch_func = callback_functions.get("switch_status_time_tabs")
        assert tab_switch_func is not None, "Tab switching function should exist"

        # Test day tab click
        mock_ctx.triggered = [{"prop_id": "status-tab-day.n_clicks"}]
        result = tab_switch_func(1, 0, 0)
        expected = ("nav-link active", "nav-link", "nav-link", "day")
        assert result == expected

        # Test week tab click
        mock_ctx.triggered = [{"prop_id": "status-tab-week.n_clicks"}]
        result = tab_switch_func(0, 1, 0)
        expected = ("nav-link", "nav-link active", "nav-link", "week")
        assert result == expected

        # Test month tab click
        mock_ctx.triggered = [{"prop_id": "status-tab-month.n_clicks"}]
        result = tab_switch_func(0, 0, 1)
        expected = ("nav-link", "nav-link", "nav-link active", "month")
        assert result == expected

    @patch("trendsearth_ui.callbacks.status.callback_context")
    def test_countdown_reset_on_refresh(self, mock_ctx):
        """Test that countdown resets when refresh button is clicked."""
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
        register_callbacks(mock_app)

        # Get the countdown function
        countdown_func = callback_functions.get("update_status_countdown")
        assert countdown_func is not None, "Countdown function should exist"

        # Test refresh button click (should reset to 60s)
        mock_ctx.triggered = [{"prop_id": "refresh-status-btn.n_clicks"}]
        result = countdown_func(30, 1, "status")
        assert result == "60s"

        # Test normal countdown progression
        mock_ctx.triggered = [{"prop_id": "status-countdown-interval.n_intervals"}]
        result = countdown_func(15, 0, "status")
        expected = f"{60 - (15 % 60)}s"
        assert result == expected


class TestStatusTabsIntegration:
    """Test integration of status tabs with the overall application."""

    def test_status_tab_components_compatibility(self):
        """Test that status tab components are compatible with Dash."""
        content = status_tab_content(is_admin=True)

        # Should be a valid Dash component
        assert hasattr(content, "children")

        # Should contain proper Dash component types
        def check_component_structure(component):
            if hasattr(component, "children") and component.children:
                if isinstance(component.children, list):
                    for child in component.children:
                        check_component_structure(child)
                else:
                    check_component_structure(component.children)

        # This should not raise any exceptions
        check_component_structure(content)

    def test_status_tab_css_classes(self):
        """Test that proper CSS classes are applied."""
        content = status_tab_content(is_admin=True)
        content_str = str(
            content
        )  # Should contain Bootstrap classes - check for Dash component representations
        bootstrap_classes = [
            "nav-tabs",
            "nav-link",
            "nav-item",
            "mb-3",
            "Card(",  # Dash component representation
            "CardHeader(",  # Dash component representation
            "CardBody(",  # Dash component representation
            "Button(",  # Dash component representation
            "color='primary'",
            "badge",
            "bg-secondary",
        ]

        for css_class in bootstrap_classes:
            assert css_class in content_str, f"Should contain Bootstrap class: {css_class}"

    def test_status_tab_accessibility(self):
        """Test accessibility features of status tabs."""
        content = status_tab_content(is_admin=True)
        content_str = str(content)

        # Should have proper navigation structure for tabs
        # While we can't test all ARIA attributes in string form,
        # we can ensure the structure supports accessibility
        assert "nav" in content_str
        # Check for clickable elements with cursor pointer style for accessibility
        assert "cursor" in content_str  # Tabs should have proper cursor styling
        assert "status-tab-" in content_str  # Should have tab IDs for accessibility

    def test_status_tab_responsive_design(self):
        """Test responsive design elements."""
        content = status_tab_content(is_admin=True)
        content_str = str(content)

        # Should contain responsive Bootstrap classes
        responsive_classes = ["col-", "Row(", "Col(", "d-flex", "justify-content-", "align-items-"]

        # At least some responsive classes should be present
        has_responsive = any(cls in content_str for cls in responsive_classes)
        assert has_responsive, "Should contain responsive design classes"


class TestStatusTabsErrorHandling:
    """Test error handling in status tab functionality."""

    def test_status_tab_with_invalid_admin_flag(self):
        """Test status tab with invalid admin flag."""
        # Should handle non-boolean values gracefully
        content = status_tab_content(is_admin=None)
        assert content is not None

        content = status_tab_content(is_admin="invalid")
        assert content is not None

    @patch("trendsearth_ui.callbacks.status.callback_context")
    def test_tab_switching_with_no_trigger(self, mock_ctx):
        """Test tab switching when no trigger is provided."""
        from trendsearth_ui.callbacks.status import register_callbacks

        mock_app = Mock()
        callback_functions = {}

        def capture_callback(*args, **kwargs):
            def decorator(func):
                callback_functions[func.__name__] = func
                return func

            return decorator

        mock_app.callback = capture_callback
        register_callbacks(mock_app)

        tab_switch_func = callback_functions.get("switch_status_time_tabs")

        # Test with no trigger
        mock_ctx.triggered = []
        result = tab_switch_func(0, 0, 0)
        expected = ("nav-link active", "nav-link", "nav-link", "day")
        assert result == expected

    @patch("trendsearth_ui.callbacks.status.callback_context")
    def test_countdown_with_non_status_tab(self, mock_ctx):
        """Test countdown when not on status tab."""
        from trendsearth_ui.callbacks.status import register_callbacks

        mock_app = Mock()
        callback_functions = {}

        def capture_callback(*args, **kwargs):
            def decorator(func):
                callback_functions[func.__name__] = func
                return func

            return decorator

        mock_app.callback = capture_callback
        register_callbacks(mock_app)

        countdown_func = callback_functions.get("update_status_countdown")

        # Test when not on status tab
        result = countdown_func(30, 0, "executions")
        assert result == "60s"

    @patch("trendsearth_ui.callbacks.status.callback_context")
    def test_status_tab_execution_status_grouping(self, mock_ctx):
        """Test that execution status structure is present in callback response."""
        # Mock the callback context
        mock_ctx.triggered = []

        # Import the callback function for testing
        from trendsearth_ui.callbacks.status import register_callbacks

        # Create a mock app and capture the callback
        mock_app = Mock()
        callback_functions = {}

        def capture_callback(*args, **kwargs):
            def decorator(func):
                callback_functions[func.__name__] = func
                return func

            return decorator

        mock_app.callback = capture_callback
        register_callbacks(mock_app)

        # Get the summary function
        summary_func = callback_functions.get("update_status_summary")
        assert summary_func is not None, "Summary function should exist"

        # Mock a successful response with test data
        with patch("trendsearth_ui.callbacks.status.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [
                    {
                        "timestamp": "2023-01-01T12:00:00Z",
                        "executions_active": 5,
                        "executions_ready": 3,
                        "executions_running": 2,
                        "executions_finished": 10,
                        "users_count": 15,
                        "scripts_count": 8,
                        "memory_available_percent": 75.0,
                        "cpu_usage_percent": 25.0,
                    }
                ]
            }
            mock_get.return_value = mock_response

            # Mock the availability check and helper functions
            with (
                patch(
                    "trendsearth_ui.callbacks.status.is_status_endpoint_available",
                    return_value=True,
                ),
                patch("trendsearth_ui.callbacks.status.fetch_deployment_info") as mock_deployment,
                patch("trendsearth_ui.callbacks.status.fetch_swarm_info") as mock_swarm,
            ):
                # Mock the helper function returns
                mock_deployment.return_value = "mock deployment info"
                mock_swarm.return_value = ("mock swarm info", " (Live)")

                result = summary_func(0, 0, "test_token", "status", "UTC", "ADMIN", "production")
                # The callback now returns four outputs: (summary, deployment_info, swarm_info, swarm_title)
                # We want to check the first output (summary)
                summary_result = (
                    result[0] if isinstance(result, (tuple, list)) and len(result) > 0 else result
                )
                result_str = str(summary_result)

                # Should contain execution status section content (without main header)
                assert "Active Executions" in result_str

    @patch("trendsearth_ui.callbacks.status.callback_context")
    def test_status_tab_summary_totals_section(self, mock_ctx):
        """Test that summary totals are properly grouped with a header."""
        # Mock the callback context
        mock_ctx.triggered = []

        # Import the callback function for testing
        from trendsearth_ui.callbacks.status import register_callbacks

        # Create a mock app and capture the callback
        mock_app = Mock()
        callback_functions = {}

        def capture_callback(*args, **kwargs):
            def decorator(func):
                callback_functions[func.__name__] = func
                return func

            return decorator

        mock_app.callback = capture_callback
        register_callbacks(mock_app)

        # Get the summary function
        summary_func = callback_functions.get("update_status_summary")
        assert summary_func is not None, "Summary function should exist"

        # Mock a successful response with test data
        with patch("trendsearth_ui.callbacks.status.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [
                    {
                        "timestamp": "2023-01-01T12:00:00Z",
                        "executions_active": 5,
                        "executions_ready": 3,
                        "executions_running": 2,
                        "executions_finished": 10,
                        "users_count": 15,
                        "scripts_count": 8,
                        "memory_available_percent": 75.0,
                        "cpu_usage_percent": 25.0,
                    }
                ]
            }
            mock_get.return_value = mock_response

            # Mock the availability check and helper functions
            with (
                patch(
                    "trendsearth_ui.callbacks.status.is_status_endpoint_available",
                    return_value=True,
                ),
                patch("trendsearth_ui.callbacks.status.fetch_deployment_info") as mock_deployment,
                patch("trendsearth_ui.callbacks.status.fetch_swarm_info") as mock_swarm,
            ):
                # Mock the helper function returns
                mock_deployment.return_value = "mock deployment info"
                mock_swarm.return_value = ("mock swarm info", " (Live)")

                result = summary_func(0, 0, "test_token", "status", "UTC", "ADMIN", "production")
                # The callback now returns four outputs: (summary, deployment_info, swarm_info, swarm_title)
                # We want to check the first output (summary)
                summary_result = (
                    result[0] if isinstance(result, (tuple, list)) and len(result) > 0 else result
                )
                result_str = str(summary_result)

                # Should contain summary totals section header
                assert "Summary Totals" in result_str

                # Should contain total executions count
                assert "Total Executions" in result_str

                # Should contain users
                assert "Users" in result_str

    @patch("trendsearth_ui.callbacks.status.callback_context")
    def test_status_tab_section_headers(self, mock_ctx):
        """Test that both section headers are present and properly styled."""
        # Mock the callback context
        mock_ctx.triggered = []

        # Import the callback function for testing
        from trendsearth_ui.callbacks.status import register_callbacks

        # Create a mock app and capture the callback
        mock_app = Mock()
        callback_functions = {}

        def capture_callback(*args, **kwargs):
            def decorator(func):
                callback_functions[func.__name__] = func
                return func

            return decorator

        mock_app.callback = capture_callback
        register_callbacks(mock_app)

        # Get the summary function
        summary_func = callback_functions.get("update_status_summary")
        assert summary_func is not None, "Summary function should exist"

        # Mock a successful response with test data
        with patch("trendsearth_ui.callbacks.status.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [
                    {
                        "timestamp": "2023-01-01T12:00:00Z",
                        "executions_active": 5,
                        "executions_ready": 3,
                        "executions_running": 2,
                        "executions_finished": 10,
                        "users_count": 15,
                        "scripts_count": 8,
                        "memory_available_percent": 75.0,
                        "cpu_usage_percent": 25.0,
                    }
                ]
            }
            mock_get.return_value = mock_response

            # Mock the availability check and helper functions
            with (
                patch(
                    "trendsearth_ui.callbacks.status.is_status_endpoint_available",
                    return_value=True,
                ),
                patch("trendsearth_ui.callbacks.status.fetch_deployment_info") as mock_deployment,
                patch("trendsearth_ui.callbacks.status.fetch_swarm_info") as mock_swarm,
            ):
                # Mock the helper function returns
                mock_deployment.return_value = "mock deployment info"
                mock_swarm.return_value = ("mock swarm info", " (Live)")

                result = summary_func(0, 0, "test_token", "status", "UTC", "ADMIN", "production")
                # The callback now returns four outputs: (summary, deployment_info, swarm_info, swarm_title)
                # We want to check the first output (summary)
                summary_result = (
                    result[0] if isinstance(result, (tuple, list)) and len(result) > 0 else result
                )
                result_str = str(summary_result)

                # Should contain section headers (Updated: main "Execution Status" header removed)
                assert "Active Executions" in result_str
                assert "Completed Executions" in result_str
                assert "Summary Totals" in result_str

                # Should contain proper styling classes for headers
                assert "text-center mb-3 text-muted" in result_str


if __name__ == "__main__":
    pytest.main([__file__])
