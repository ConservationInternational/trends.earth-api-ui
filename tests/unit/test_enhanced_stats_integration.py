"""
Unit tests for enhanced statistics integration in the status tab.
Tests the reorganization of enhanced statistics under System Status Trends.
"""

from unittest.mock import MagicMock, patch

from dash import html
import pytest

from trendsearth_ui.callbacks.status import register_callbacks
from trendsearth_ui.components.tabs import status_tab_content


class TestEnhancedStatsIntegration:
    """Test the integration of enhanced statistics in the status tab."""

    def test_enhanced_stats_components_in_status_tab(self):
        """Test that enhanced statistics components are present in status tab for SUPERADMIN users."""
        content = status_tab_content(is_admin=True, role="SUPERADMIN")
        content_str = str(content)

        # Should contain all three enhanced statistics components
        assert "stats-summary-cards" in content_str
        assert "stats-user-map" in content_str
        assert "stats-additional-charts" in content_str

        # Should contain the section headers
        assert "System Overview" in content_str
        assert "User Geographic Distribution" in content_str
        assert "Detailed Analytics" in content_str

    def test_enhanced_stats_components_for_superadmin(self):
        """Test that enhanced statistics components are present for SUPERADMIN users."""
        content = status_tab_content(is_admin=True, role="SUPERADMIN")
        content_str = str(content)

        # Should contain all three enhanced statistics components
        assert "stats-summary-cards" in content_str
        assert "stats-user-map" in content_str
        assert "stats-additional-charts" in content_str

    def test_enhanced_stats_not_shown_for_non_admin(self):
        """Test that enhanced statistics are not shown for non-admin users."""
        content = status_tab_content(is_admin=False, role="USER")
        content_str = str(content)

        # Should contain access denied message for non-admin
        assert "Access denied" in content_str
        assert "Administrator privileges required" in content_str

        # Should NOT contain enhanced statistics components
        assert "stats-summary-cards" not in content_str
        assert "stats-user-map" not in content_str
        assert "stats-additional-charts" not in content_str

    def test_enhanced_stats_layout_structure(self):
        """Test the layout structure of enhanced statistics in the status tab."""
        content = status_tab_content(is_admin=True, role="SUPERADMIN")
        content_str = str(content)

        # Should have the enhanced statistics sections before the status trends
        assert "System Overview" in content_str
        assert "System Status Trends" in content_str

        # Should have loading components for each section
        assert "loading-stats-summary" in content_str
        assert "loading-stats-map" in content_str
        assert "loading-stats-charts" in content_str

    def test_time_period_tabs_still_present(self):
        """Test that time period tabs are still present and functional."""
        content = status_tab_content(is_admin=True, role="SUPERADMIN")
        content_str = str(content)

        # Should contain time period tabs
        assert "Last 24 Hours" in content_str
        assert "Last Week" in content_str
        assert "Last Month" in content_str

        # Should contain tab IDs for interaction
        assert "status-tab-day" in content_str
        assert "status-tab-week" in content_str
        assert "status-tab-month" in content_str

        # Should contain the data store for tab state
        assert "status-time-tabs-store" in content_str

    def test_enhanced_stats_callback_admin_access(self):
        """Test that the enhanced statistics callback works for SUPERADMIN users only."""
        # Create a mock app
        app = MagicMock()
        app.callback = MagicMock()

        # Register callbacks
        register_callbacks(app)

        # Verify that the enhanced statistics callback was registered
        assert app.callback.called

        # Check if any of the calls included the enhanced stats outputs
        callback_calls = app.callback.call_args_list
        enhanced_stats_registered = False

        for call in callback_calls:
            if len(call[0]) > 0:  # Check if there are positional arguments
                outputs = call[0][0]  # First argument should be outputs
                if hasattr(outputs, "__iter__"):
                    output_ids = []
                    for output in outputs:
                        if hasattr(output, "component_id"):
                            output_ids.append(output.component_id)

                    if (
                        "stats-summary-cards" in output_ids
                        and "stats-user-map" in output_ids
                        and "stats-additional-charts" in output_ids
                    ):
                        enhanced_stats_registered = True
                        break

        assert enhanced_stats_registered, "Enhanced statistics callback should be registered"

    def test_no_separate_enhanced_stats_card(self):
        """Test that there is no separate Enhanced Statistics card anymore."""
        content = status_tab_content(is_admin=True, role="SUPERADMIN")
        content_str = str(content)

        # Should NOT contain a separate "Enhanced Statistics" card header
        assert "Enhanced Statistics" not in content_str

        # Should contain the components within the System Status Trends section
        assert "System Status Trends" in content_str
        assert "stats-summary-cards" in content_str


class TestEnhancedStatsAccessControl:
    """Test access control for enhanced statistics."""

    def test_admin_has_no_access_to_enhanced_stats(self):
        """Test that ADMIN users don't have access to enhanced statistics (API requires SUPERADMIN)."""
        content = status_tab_content(is_admin=True, role="ADMIN")
        content_str = str(content)

        # Should NOT contain enhanced statistics components for ADMIN users
        assert "stats-summary-cards" not in content_str
        assert "stats-user-map" not in content_str
        assert "stats-additional-charts" not in content_str

        # But should still show basic status functionality
        assert "System Status Summary" in content_str
        assert "System Status Trends" in content_str

    def test_superadmin_has_access_to_enhanced_stats(self):
        """Test that SUPERADMIN users have access to enhanced statistics."""
        content = status_tab_content(is_admin=True, role="SUPERADMIN")
        content_str = str(content)

        # Should contain enhanced statistics components
        assert "stats-summary-cards" in content_str
        assert "stats-user-map" in content_str
        assert "stats-additional-charts" in content_str

    def test_regular_user_no_access_to_enhanced_stats(self):
        """Test that regular users don't have access to enhanced statistics."""
        content = status_tab_content(is_admin=False, role="USER")
        content_str = str(content)

        # Should show access denied
        assert "Access denied" in content_str

        # Should NOT contain enhanced statistics components
        assert "stats-summary-cards" not in content_str
        assert "stats-user-map" not in content_str
        assert "stats-additional-charts" not in content_str


if __name__ == "__main__":
    pytest.main([__file__])
