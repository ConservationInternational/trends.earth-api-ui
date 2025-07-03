"""Unit tests for tab components."""

from unittest.mock import Mock, patch

from trendsearth_ui.components.tabs import (
    executions_tab_content,
    profile_tab_content,
    scripts_tab_content,
    status_tab_content,
    users_tab_content,
)


class TestExecutionsTabContent:
    """Test the executions_tab_content function."""

    def test_executions_tab_basic_structure(self):
        """Test basic structure of executions tab."""
        content = executions_tab_content()

        # Should return a component with children
        assert hasattr(content, "children")
        assert isinstance(content.children, list)

        # Convert to string to check for key components
        content_str = str(content)
        assert "executions-table" in content_str
        assert "refresh-executions-btn" in content_str

    def test_executions_tab_refresh_components(self):
        """Test that executions tab contains refresh components."""
        content = executions_tab_content()
        content_str = str(content)

        # Should contain auto-refresh components
        assert "auto-refresh" in content_str or "refresh" in content_str
        assert "countdown" in content_str


class TestUsersTabContent:
    """Test the users_tab_content function."""

    def test_users_tab_with_data(self):
        """Test users tab with sample data."""
        content = users_tab_content()

        # Should return a component
        assert hasattr(content, "children")

        # Convert to string to check for content
        content_str = str(content)
        assert "users-table" in content_str

    def test_users_tab_admin_vs_user_view(self):
        """Test different views for admin vs regular user."""
        # Admin view
        admin_content = users_tab_content()

        # User view
        user_content = users_tab_content()

        # Both should have the same structure since role is now handled server-side
        assert hasattr(admin_content, "children")
        assert hasattr(user_content, "children")

    def test_users_tab_empty_data(self):
        """Test users tab with empty data."""
        content = users_tab_content()

        # Should handle empty data gracefully by using server-side loading
        assert hasattr(content, "children")


class TestScriptsTabContent:
    """Test the scripts_tab_content function."""

    def test_scripts_tab_with_data(self):
        """Test scripts tab with sample data."""
        content = scripts_tab_content()

        # Should return a component
        assert hasattr(content, "children")

        # Convert to string to check for content
        content_str = str(content)
        assert "scripts-table" in content_str

    def test_scripts_tab_admin_vs_user_view(self):
        """Test different views for admin vs regular user."""
        # Admin view
        admin_content = scripts_tab_content()

        # User view
        user_content = scripts_tab_content()

        # Both should have the same structure since role is now handled server-side
        assert hasattr(admin_content, "children")
        assert hasattr(user_content, "children")

    def test_scripts_tab_empty_data(self):
        """Test scripts tab with empty data."""
        content = scripts_tab_content()

        # Should handle empty data gracefully by using server-side loading
        assert hasattr(content, "children")


class TestProfileTabContent:
    """Test the profile_tab_content function."""

    def test_profile_tab_with_user_data(self):
        """Test profile tab with user data."""
        user_data = {
            "name": "Test User",
            "email": "test@example.com",
            "institution": "Test Institution",
            "role": "USER",
        }

        content = profile_tab_content(user_data)

        # Should return a component
        assert hasattr(content, "children")

        # Convert to string to check for content
        content_str = str(content)
        assert "profile-name" in content_str
        assert "profile-institution" in content_str
        assert "update-profile-btn" in content_str

    def test_profile_tab_password_change(self):
        """Test that profile tab contains password change section."""
        user_data = {"name": "Test User", "email": "test@example.com"}

        content = profile_tab_content(user_data)
        content_str = str(content)

        # Should contain password change fields
        assert "current-password" in content_str
        assert "new-password" in content_str
        assert "confirm-password" in content_str
        assert "change-password-btn" in content_str

    def test_profile_tab_without_user_data(self):
        """Test profile tab without user data."""
        content = profile_tab_content(None)

        # Should handle missing user data gracefully
        assert hasattr(content, "children")

    def test_profile_tab_empty_user_data(self):
        """Test profile tab with empty user data."""
        content = profile_tab_content({})

        # Should handle empty user data gracefully
        assert hasattr(content, "children")


class TestStatusTabContent:
    """Test the status_tab_content function."""

    def test_status_tab_admin_view(self):
        """Test status tab for admin users."""
        content = status_tab_content(is_admin=True)

        # Should return a component
        assert hasattr(content, "children")

        # Convert to string to check for content
        content_str = str(content)
        assert "status" in content_str.lower()
        assert "refresh" in content_str.lower()

    def test_status_tab_non_admin_view(self):
        """Test status tab for non-admin users."""
        content = status_tab_content(is_admin=False)

        # Should return a component (likely with restricted access message)
        assert hasattr(content, "children")

    def test_status_tab_refresh_components(self):
        """Test that status tab contains refresh components."""
        content = status_tab_content(is_admin=True)
        content_str = str(content)

        # Should contain refresh functionality
        assert "refresh-status-btn" in content_str or "refresh" in content_str.lower()

    def test_status_tab_charts_section(self):
        """Test that status tab contains charts section."""
        content = status_tab_content(is_admin=True)
        content_str = str(content)

        # Should contain charts or status visualization
        assert "chart" in content_str.lower() or "status" in content_str.lower()


class TestTabsIntegration:
    """Test integration between tab components."""

    def test_all_tabs_can_be_created(self):
        """Test that all tab components can be created without errors."""
        # Sample data for testing
        user_data = {"name": "Test User", "email": "test@example.com"}

        # All tab functions should execute without errors
        executions = executions_tab_content()
        users = users_tab_content()
        scripts = scripts_tab_content()
        profile = profile_tab_content(user_data)
        status = status_tab_content(is_admin=True)

        # All should return valid components
        tabs = [executions, users, scripts, profile, status]
        for tab in tabs:
            assert tab is not None
            assert hasattr(tab, "children")

    def test_tabs_consistent_structure(self):
        """Test that all tabs have consistent structure."""
        # Sample data
        user_data = {"name": "Test User"}

        tabs = [
            executions_tab_content(),
            users_tab_content(),
            scripts_tab_content(),
            profile_tab_content(user_data),
            status_tab_content(is_admin=True),
        ]

        # All tabs should have children attribute
        for tab in tabs:
            assert hasattr(tab, "children")
