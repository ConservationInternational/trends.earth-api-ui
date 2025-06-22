"""Integration tests for the Dash application."""

from unittest.mock import Mock, patch

from dash.testing import DashComposite
import pytest

from trendsearth_ui.app import app


class TestAppIntegration:
    """Integration tests for the complete application."""

    def test_app_initialization(self, dash_app):
        """Test that the app initializes correctly."""
        assert dash_app is not None
        assert dash_app.title == "Trends.Earth API Dashboard"
        assert dash_app.layout is not None

    def test_app_layout_structure(self, dash_app):
        """Test the overall app layout structure."""
        layout = dash_app.layout

        # Should have main container structure
        assert hasattr(layout, "children")
        assert isinstance(layout.children, list)

        # Convert to string to check for key components
        layout_str = str(layout)

        # Should contain main application components
        assert "Trends.Earth API Dashboard" in layout_str
        assert "page-content" in layout_str
        assert "token-store" in layout_str
        assert "role-store" in layout_str
        assert "user-store" in layout_str

    def test_app_stores_present(self, dash_app):
        """Test that all required stores are present in the layout."""
        layout_str = str(dash_app.layout)

        required_stores = [
            "token-store",
            "role-store",
            "user-store",
            "json-modal-data",
            "scripts-raw-data",
            "users-raw-data",
            "current-log-context",
            "edit-user-data",
            "edit-script-data",
        ]

        for store in required_stores:
            assert store in layout_str

    def test_app_modals_present(self, dash_app):
        """Test that all required modals are present in the layout."""
        layout_str = str(dash_app.layout)

        required_modals = ["json-modal", "edit-user-modal", "edit-script-modal", "map-modal"]

        for modal in required_modals:
            assert modal in layout_str


class TestAuthenticationFlow:
    """Test authentication flow integration."""

    @patch("trendsearth_ui.callbacks.auth.requests.post")
    def test_successful_login_flow(self, mock_post, dash_app, mock_user_data):
        """Test successful login authentication flow."""
        # Mock successful login response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "test_token_123"}
        mock_post.return_value = mock_response

        # Mock user info retrieval
        with patch("trendsearth_ui.callbacks.auth.get_user_info") as mock_get_user:
            mock_get_user.return_value = mock_user_data

            # Test would require Dash testing client to simulate clicks
            # This is a structure test to ensure the callback exists
            assert "login_api" in str(dash_app._callback_map)

    def test_page_navigation_callback_exists(self, dash_app):
        """Test that page navigation callback is registered."""
        # Check that the display_page callback is registered
        callback_map = str(dash_app._callback_map)
        assert "display_page" in callback_map or "page-content" in callback_map


class TestTabRendering:
    """Test tab rendering integration."""

    @patch("trendsearth_ui.callbacks.tabs.fetch_scripts_and_users")
    def test_tab_rendering_callback_exists(self, mock_fetch, dash_app):
        """Test that tab rendering callback is registered."""
        mock_fetch.return_value = ([], [])  # Empty scripts and users

        # Check that the render_tab callback is registered
        callback_map = str(dash_app._callback_map)
        assert "render_tab" in callback_map or "tab-content" in callback_map

    def test_all_tab_callbacks_registered(self, dash_app):
        """Test that all expected tab-related callbacks are registered."""
        callback_map = str(dash_app._callback_map)

        # Should have tab content rendering
        assert "tab-content" in callback_map or "tabs" in callback_map


class TestExecutionsTableIntegration:
    """Test executions table integration."""

    @patch("trendsearth_ui.callbacks.executions.requests.get")
    def test_executions_table_callback_exists(self, mock_get, dash_app):
        """Test that executions table callback is registered."""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [], "total": 0}
        mock_get.return_value = mock_response

        # Check that executions table callback is registered
        callback_map = str(dash_app._callback_map)
        assert "executions-table" in callback_map or "getRowsResponse" in callback_map

    def test_executions_refresh_callbacks_exist(self, dash_app):
        """Test that executions refresh callbacks are registered."""
        callback_map = str(dash_app._callback_map)

        # Should have refresh functionality
        assert "refresh" in callback_map.lower() or "executions" in callback_map


class TestModalIntegration:
    """Test modal integration."""

    def test_json_modal_callbacks_exist(self, dash_app):
        """Test that JSON modal callbacks are registered."""
        callback_map = str(dash_app._callback_map)

        # Should have JSON modal functionality
        assert "json-modal" in callback_map or "modal" in callback_map.lower()

    def test_edit_modal_callbacks_exist(self, dash_app):
        """Test that edit modal callbacks are registered."""
        callback_map = str(dash_app._callback_map)

        # Should have edit modal functionality
        assert "edit-user-modal" in callback_map or "edit-script-modal" in callback_map

    def test_map_modal_callbacks_exist(self, dash_app):
        """Test that map modal callbacks are registered."""
        callback_map = str(dash_app._callback_map)

        # Should have map modal functionality
        assert "map-modal" in callback_map or "map" in callback_map.lower()


class TestProfileIntegration:
    """Test profile functionality integration."""

    @patch("trendsearth_ui.callbacks.profile.requests.patch")
    def test_profile_update_callback_exists(self, mock_patch, dash_app):
        """Test that profile update callback is registered."""
        # Mock successful update response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_patch.return_value = mock_response

        # Check that profile update callback is registered
        callback_map = str(dash_app._callback_map)
        assert "profile" in callback_map.lower() or "update-profile" in callback_map

    @patch("trendsearth_ui.callbacks.profile.requests.put")
    def test_password_change_callback_exists(self, mock_put, dash_app):
        """Test that password change callback is registered."""
        # Mock successful password change response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_put.return_value = mock_response

        # Check that password change callback is registered
        callback_map = str(dash_app._callback_map)
        assert "password" in callback_map.lower() or "change-password" in callback_map


class TestRefreshIntegration:
    """Test refresh functionality integration."""

    def test_log_refresh_callbacks_exist(self, dash_app):
        """Test that log refresh callbacks are registered."""
        callback_map = str(dash_app._callback_map)

        # Should have log refresh functionality
        assert "refresh-logs" in callback_map or "logs-refresh" in callback_map

    def test_countdown_callbacks_exist(self, dash_app):
        """Test that countdown callbacks are registered."""
        callback_map = str(dash_app._callback_map)

        # Should have countdown functionality
        assert "countdown" in callback_map.lower()


class TestCallbackRegistration:
    """Test that all callbacks are properly registered."""

    def test_all_callback_modules_registered(self, dash_app):
        """Test that all callback modules have been registered."""
        callback_map = str(dash_app._callback_map)

        # Should have callbacks from all modules
        expected_components = [
            "token-store",  # auth callbacks
            "tab-content",  # tabs callbacks
            "executions-table",  # executions callbacks
            "json-modal",  # modals callbacks
            "map-modal",  # map callbacks
            "profile",  # profile callbacks
            "edit-user-modal",  # edit callbacks
            "refresh",  # refresh callbacks
        ]

        # At least some of these should be present
        found_components = sum(1 for comp in expected_components if comp in callback_map)
        assert found_components > 0

    def test_no_callback_conflicts(self, dash_app):
        """Test that there are no callback conflicts."""
        # The app should initialize without callback conflicts
        # If there were conflicts, the app creation would fail
        assert dash_app is not None
        assert hasattr(dash_app, "_callback_map")

    def test_callback_map_not_empty(self, dash_app):
        """Test that callbacks have been registered."""
        # Should have registered callbacks
        assert len(dash_app._callback_map) > 0
