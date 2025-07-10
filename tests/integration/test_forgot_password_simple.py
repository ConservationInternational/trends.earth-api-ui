"""Integration tests for forgot password functionality."""

from unittest.mock import Mock, patch

import pytest

from trendsearth_ui.components.layout import login_layout


class TestForgotPasswordIntegration:
    """Integration tests for the forgot password feature."""

    def test_forgot_password_components_in_app_layout(self, dash_app):
        """Test that forgot password components are present in the login layout."""
        # Get the login layout (which contains the forgot password components)
        layout = login_layout()
        layout_str = str(layout)

        # Verify forgot password components exist
        required_components = [
            "forgot-password-modal",
            "forgot-password-link",
            "forgot-password-email",
            "send-reset-btn",
            "cancel-forgot-password",
            "forgot-password-alert",
        ]

        for component in required_components:
            assert component in layout_str, f"Missing component: {component}"

    def test_forgot_password_callbacks_registered(self, dash_app):
        """Test that forgot password callbacks are registered in the app."""
        # Get callback map
        try:
            callback_map = str(dash_app.callback_map)
        except AttributeError:
            callback_map = str(getattr(dash_app, "_callback_map", {}))

        # Should contain forgot password related callbacks
        assert "forgot-password-modal" in callback_map
        assert "forgot-password-alert" in callback_map

    def test_forgot_password_text_content(self, dash_app):
        """Test that forgot password has the correct text content."""
        layout = login_layout()
        layout_str = str(layout)

        # Verify required text is present
        required_text = [
            "Forgot your password?",
            "Forgot Password",
            "Enter your email address",
            "Send Reset Instructions",
            "Cancel",
        ]

        for text in required_text:
            assert text in layout_str, f"Missing text: {text}"
