"""
Test to verify the fix for executions-status-filter-selected missing component error.

This test specifically validates that the Store components required by executions
callbacks are present in the executions tab layout.
"""

from dash import html
import pytest

from trendsearth_ui.components.tabs import executions_tab_content


class TestExecutionsStatusFilterFix:
    """Test the fix for missing executions-status-filter-selected Store component."""

    def test_executions_status_filter_stores_exist(self):
        """Test that required Store components for status filter are present."""
        content = executions_tab_content()

        # Convert to string to search for the required Store components
        content_str = str(content)

        # Verify that the required Store components exist
        assert "executions-status-filter-selected" in content_str, (
            "executions-status-filter-selected Store component should be present"
        )
        assert "executions-status-filter-active" in content_str, (
            "executions-status-filter-active Store component should be present"
        )

    def test_executions_status_filter_stores_have_correct_defaults(self):
        """Test that Store components have the correct default values."""
        content = executions_tab_content()
        content_str = str(content)

        # Check for the specific default values
        assert "data=[]" in content_str, (
            "executions-status-filter-selected should have empty list as default"
        )
        assert "data=False" in content_str, (
            "executions-status-filter-active should have False as default"
        )

    def test_executions_tab_structure_unchanged(self):
        """Test that the tab structure is not significantly changed by the fix."""
        content = executions_tab_content()

        # Ensure the tab still contains expected components
        assert hasattr(content, "children")
        assert isinstance(content.children, list)

        content_str = str(content)

        # Verify key components still exist
        assert "executions-table" in content_str
        assert "refresh-executions-btn" in content_str
        assert "cancel-execution-store" in content_str
        assert "executions-countdown" in content_str
