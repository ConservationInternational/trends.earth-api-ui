"""Integration tests for forgot password functionality."""

from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from trendsearth_ui.app import app
from trendsearth_ui.config import API_BASE


class TestForgotPasswordIntegration:
    """Integration tests for the forgot password feature."""

    @pytest.fixture
    def dash_app(self):
        """Create a test Dash app."""
        # Don't try to set config.testing after app creation
        # The app is already initialized in trendsearth_ui.app
        return app

    def test_forgot_password_components_in_layout(self, dash_app):
        """Test that forgot password components are present in the login layout."""
        # Get the login layout specifically, not the main app layout
        from trendsearth_ui.components.layout import login_layout

        layout = login_layout()
        layout_str = str(layout)

        # Should contain forgot password modal components
        assert "forgot-password-modal" in layout_str
        assert "forgot-password-link" in layout_str
        assert "forgot-password-email" in layout_str
        assert "send-reset-btn" in layout_str
        assert "cancel-forgot-password" in layout_str
        assert "forgot-password-alert" in layout_str

    def test_forgot_password_callbacks_registered(self, dash_app):
        """Test that forgot password callbacks are registered in the app."""
        # Get callback map
        callback_map = dash_app.callback_map
        callback_map_str = str(callback_map)

        # Should contain forgot password callbacks
        assert "forgot-password-modal" in callback_map_str
        assert "forgot-password-alert" in callback_map_str
        assert "send-reset-btn" in callback_map_str

    def test_forgot_password_security_anti_enumeration(self):
        """Test that forgot password doesn't reveal user existence."""
        # This test verifies the anti-enumeration behavior at the function level
        from unittest.mock import Mock, patch

        from trendsearth_ui.callbacks.auth import register_callbacks

        # Mock app and callbacks
        mock_app = Mock()
        callbacks = []

        def mock_callback(*args, **kwargs):
            def decorator(func):
                callbacks.append({"func": func, "args": args, "kwargs": kwargs})
                return func

            return decorator

        mock_app.callback = mock_callback

        # Register callbacks
        with patch("trendsearth_ui.callbacks.auth.callback_context", Mock()):
            register_callbacks(mock_app)

        # Find the send password reset callback
        send_reset_callback = None
        for cb in callbacks:
            if cb["func"].__name__ == "send_password_reset":
                send_reset_callback = cb["func"]
                break

        assert send_reset_callback is not None

        # Test both success and not found cases return same message
        with patch("trendsearth_ui.callbacks.auth.callback_context", Mock()):
            with patch("trendsearth_ui.callbacks.auth.requests.post") as mock_post:
                # Test success case
                mock_response = Mock()
                mock_response.status_code = 200
                mock_post.return_value = mock_response

                result_success = send_reset_callback(1, "existing@example.com")

                # Test not found case
                mock_response.status_code = 404
                result_not_found = send_reset_callback(1, "nonexistent@example.com")

                # Both should return identical success messages (ignoring the email address)
                # The important part is that both return the same message format and type
                assert result_success[0].startswith("If an account exists with")
                assert result_not_found[0].startswith("If an account exists with")
                assert "password recovery instructions have been sent" in result_success[0]
                assert "password recovery instructions have been sent" in result_not_found[0]
                assert result_success[1] == result_not_found[1] == "success"
                assert result_success[2] == result_not_found[2] is True
                assert result_success[3] == result_not_found[3] == ""
                assert result_success[4] == result_not_found[4] == {"display": "none"}  # Form hidden
                assert result_success[5] == result_not_found[5] == {"display": "none"}  # Initial buttons hidden
                assert (
                    result_success[6] == result_not_found[6] == {"display": "block"}
                )  # Success buttons shown

    def test_forgot_password_endpoint_url_construction(self):
        """Test that the correct API endpoint is constructed."""
        from unittest.mock import Mock, patch

        from trendsearth_ui.callbacks.auth import register_callbacks

        # Mock app and callbacks
        mock_app = Mock()
        callbacks = []

        def mock_callback(*args, **kwargs):
            def decorator(func):
                callbacks.append({"func": func, "args": args, "kwargs": kwargs})
                return func

            return decorator

        mock_app.callback = mock_callback

        # Register callbacks
        with patch("trendsearth_ui.callbacks.auth.callback_context", Mock()):
            register_callbacks(mock_app)

        # Find the send password reset callback
        send_reset_callback = None
        for cb in callbacks:
            if cb["func"].__name__ == "send_password_reset":
                send_reset_callback = cb["func"]
                break

        assert send_reset_callback is not None

        test_email = "test@example.com"
        expected_url = f"{API_BASE}/user/{test_email}/recover-password"

        with patch("trendsearth_ui.callbacks.auth.callback_context", Mock()):
            with patch("trendsearth_ui.callbacks.auth.requests.post") as mock_post:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_post.return_value = mock_response

                # Execute the callback
                send_reset_callback(1, test_email)

                # Verify the correct URL was called
                mock_post.assert_called_once_with(
                    expected_url,
                    timeout=10,
                )
