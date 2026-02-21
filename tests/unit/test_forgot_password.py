"""Unit tests for forgot password functionality."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from trendsearth_ui.callbacks.auth import register_callbacks
from trendsearth_ui.components.layout import login_layout


class TestForgotPasswordUI:
    """Test the forgot password UI components."""

    def test_forgot_password_modal_in_login_layout(self):
        """Test that the forgot password modal is included in login layout."""
        layout = login_layout()
        layout_str = str(layout)

        # Should contain forgot password modal components
        assert "forgot-password-modal" in layout_str
        assert "forgot-password-link" in layout_str
        assert "forgot-password-email" in layout_str
        assert "send-reset-btn" in layout_str
        assert "cancel-forgot-password" in layout_str
        assert "forgot-password-alert" in layout_str

    def test_forgot_password_link_in_login_form(self):
        """Test that the forgot password link is present in the login form."""
        layout = login_layout()
        layout_str = str(layout)

        # Should contain the forgot password link
        assert "Forgot your password?" in layout_str
        assert "forgot-password-link" in layout_str

    def test_forgot_password_modal_structure(self):
        """Test that the forgot password modal has the correct structure."""
        layout = login_layout()
        layout_str = str(layout)

        # Should contain modal components
        assert "Forgot Password" in layout_str
        assert "Enter your email address" in layout_str
        assert "Send Reset Instructions" in layout_str
        assert "Cancel" in layout_str


class TestForgotPasswordCallbacks:
    """Test the forgot password callback functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_app = Mock()
        self.mock_app.callback = Mock()

        # Mock callback_context
        self.mock_context = Mock()
        self.mock_context.triggered = []

        # Store the original callback decorators
        self.callbacks = []

        # Mock the callback decorator to capture callback functions
        def mock_callback(*args, **kwargs):
            def decorator(func):
                self.callbacks.append({"func": func, "args": args, "kwargs": kwargs})
                return func

            return decorator

        self.mock_app.callback = mock_callback

    def test_forgot_password_callbacks_registered(self):
        """Test that forgot password callbacks are registered."""
        with patch("trendsearth_ui.callbacks.auth.callback_context", self.mock_context):
            register_callbacks(self.mock_app)

        # Should have registered callbacks for forgot password functionality
        callback_names = [cb["func"].__name__ for cb in self.callbacks]

        assert "toggle_forgot_password_modal" in callback_names
        assert "send_password_reset" in callback_names

    def test_toggle_forgot_password_modal_callback(self):
        """Test the toggle forgot password modal callback."""
        with patch("trendsearth_ui.callbacks.auth.callback_context", self.mock_context):
            register_callbacks(self.mock_app)

        # Find the toggle modal callback
        toggle_callback = next(
            cb for cb in self.callbacks if cb["func"].__name__ == "toggle_forgot_password_modal"
        )

        # Test opening modal
        with patch("trendsearth_ui.callbacks.auth.callback_context", self.mock_context):
            self.mock_context.triggered = [{"prop_id": "forgot-password-link.n_clicks"}]
            result = toggle_callback["func"](1, 0, 0, False)
            assert result is True

        # Test closing modal
        with patch("trendsearth_ui.callbacks.auth.callback_context", self.mock_context):
            self.mock_context.triggered = [{"prop_id": "cancel-forgot-password.n_clicks"}]
            result = toggle_callback["func"](1, 1, 0, True)
            assert result is False

    @patch("trendsearth_ui.callbacks.auth.get_session")
    def test_send_password_reset_callback_success(self, mock_get_session):
        """Test the send password reset callback with successful response."""
        # Mock successful API response
        mock_session = mock_get_session.return_value
        mock_response = Mock()
        mock_response.status_code = 200
        mock_session.post.return_value = mock_response

        with patch("trendsearth_ui.callbacks.auth.callback_context", self.mock_context):
            register_callbacks(self.mock_app)

        # Find the send password reset callback
        reset_callback = next(
            cb for cb in self.callbacks if cb["func"].__name__ == "send_password_reset"
        )

        # Test with valid email
        result = reset_callback["func"](1, "test@example.com", "production")

        # Should return success message with 7 values
        assert len(result) == 7
        assert result[0].startswith("If an account exists with")
        assert result[1] == "success"
        assert result[2] is True
        assert result[3] == ""  # Email field should be cleared
        assert result[4] == {"display": "none"}  # Form should be hidden
        assert result[5] == {"display": "none"}  # Initial buttons should be hidden
        assert result[6] == {"display": "block"}  # Success buttons should be shown

    @patch("trendsearth_ui.callbacks.auth.get_session")
    def test_send_password_reset_callback_user_not_found(self, mock_get_session):
        """Test the send password reset callback with user not found."""
        # Mock 404 response
        mock_session = mock_get_session.return_value
        mock_response = Mock()
        mock_response.status_code = 404
        mock_session.post.return_value = mock_response

        with patch("trendsearth_ui.callbacks.auth.callback_context", self.mock_context):
            register_callbacks(self.mock_app)

        # Find the send password reset callback
        reset_callback = next(
            cb for cb in self.callbacks if cb["func"].__name__ == "send_password_reset"
        )

        # Test with email that doesn't exist
        result = reset_callback["func"](1, "nonexistent@example.com", "production")

        # Should return the same success message to prevent email enumeration with 7 values
        assert len(result) == 7
        assert result[0].startswith("If an account exists with")
        assert result[1] == "success"
        assert result[2] is True
        assert result[3] == ""  # Email field should be cleared
        assert result[4] == {"display": "none"}  # Form should be hidden
        assert result[5] == {"display": "none"}  # Initial buttons should be hidden
        assert result[6] == {"display": "block"}  # Success buttons should be shown

    def test_send_password_reset_callback_invalid_email(self):
        """Test the send password reset callback with invalid email."""
        with patch("trendsearth_ui.callbacks.auth.callback_context", self.mock_context):
            register_callbacks(self.mock_app)

        # Find the send password reset callback
        reset_callback = next(
            cb for cb in self.callbacks if cb["func"].__name__ == "send_password_reset"
        )

        # Test with invalid email
        result = reset_callback["func"](1, "invalid-email", "production")

        # Should return validation error with 7 values
        assert len(result) == 7
        assert result[0] == "Please enter a valid email address."
        assert result[1] == "warning"
        assert result[2] is True

    def test_send_password_reset_callback_empty_email(self):
        """Test the send password reset callback with empty email."""
        with patch("trendsearth_ui.callbacks.auth.callback_context", self.mock_context):
            register_callbacks(self.mock_app)

        # Find the send password reset callback
        reset_callback = next(
            cb for cb in self.callbacks if cb["func"].__name__ == "send_password_reset"
        )

        # Test with empty email
        result = reset_callback["func"](1, "", "production")

        # Should return validation error with 7 values
        assert len(result) == 7
        assert result[0] == "Please enter your email address."
        assert result[1] == "warning"
        assert result[2] is True

    @patch("trendsearth_ui.callbacks.auth.get_session")
    def test_send_password_reset_callback_network_error(self, mock_get_session):
        """Test the send password reset callback with network error."""
        # Mock network error
        mock_session = mock_get_session.return_value
        mock_session.post.side_effect = Exception("Network error")

        with patch("trendsearth_ui.callbacks.auth.callback_context", self.mock_context):
            register_callbacks(self.mock_app)

        # Find the send password reset callback
        reset_callback = next(
            cb for cb in self.callbacks if cb["func"].__name__ == "send_password_reset"
        )

        # Test with valid email but network error
        result = reset_callback["func"](1, "test@example.com", "production")

        # Should return network error message with 7 values
        assert len(result) == 7
        assert "Network error" in result[0]
        assert result[1] == "danger"
        assert result[2] is True

    @patch("trendsearth_ui.callbacks.auth.get_session")
    def test_send_password_reset_callback_timeout(self, mock_get_session):
        """Test the send password reset callback with timeout."""
        # Mock timeout error
        import requests

        mock_session = mock_get_session.return_value
        mock_session.post.side_effect = requests.exceptions.Timeout()

        with patch("trendsearth_ui.callbacks.auth.callback_context", self.mock_context):
            register_callbacks(self.mock_app)

        # Find the send password reset callback
        reset_callback = next(
            cb for cb in self.callbacks if cb["func"].__name__ == "send_password_reset"
        )

        # Test with valid email but timeout
        result = reset_callback["func"](1, "test@example.com", "production")

        # Should return timeout error message with 7 values
        assert len(result) == 7
        assert "Request timed out" in result[0]
        assert result[1] == "danger"
        assert result[2] is True

    @patch("trendsearth_ui.callbacks.auth.get_session")
    def test_send_password_reset_callback_connection_error(self, mock_get_session):
        """Test the send password reset callback with connection error."""
        # Mock connection error
        import requests

        mock_session = mock_get_session.return_value
        mock_session.post.side_effect = requests.exceptions.ConnectionError()

        with patch("trendsearth_ui.callbacks.auth.callback_context", self.mock_context):
            register_callbacks(self.mock_app)

        # Find the send password reset callback
        reset_callback = next(
            cb for cb in self.callbacks if cb["func"].__name__ == "send_password_reset"
        )

        # Test with valid email but connection error
        result = reset_callback["func"](1, "test@example.com", "production")

        # Should return connection error message with 7 values
        assert len(result) == 7
        assert "Cannot connect to the server" in result[0]
        assert result[1] == "danger"
        assert result[2] is True

    def test_email_validation_patterns(self):
        """Test email validation with various patterns."""
        import re

        # Valid email pattern from the callback
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        # Test valid emails
        valid_emails = [
            "test@example.com",
            "user.name+tag@example.co.uk",
            "user123@test-domain.org",
            "name@subdomain.example.com",
        ]

        for email in valid_emails:
            assert re.match(email_pattern, email), f"Valid email failed: {email}"

        # Test invalid emails
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "user@",
            "user@domain",
            "user@domain.",
            "user@.com",
            "",
            "user name@example.com",
        ]

        for email in invalid_emails:
            assert not re.match(email_pattern, email), f"Invalid email passed: {email}"

    def test_reset_modal_state_callback(self):
        """Test the reset modal state callback."""
        with patch("trendsearth_ui.callbacks.auth.callback_context", self.mock_context):
            register_callbacks(self.mock_app)

        # Find the reset modal state callback
        reset_callback = next(
            cb for cb in self.callbacks if cb["func"].__name__ == "reset_modal_state"
        )

        # Test modal opening (should reset state)
        result = reset_callback["func"](True)
        assert result[0] == {"display": "block"}  # Form shown
        assert result[1] == {"display": "block"}  # Initial buttons shown
        assert result[2] == {"display": "none"}  # Success buttons hidden
        assert result[3] is False  # Alert closed
        assert result[4] == ""  # Email field cleared

        # Test modal closing (should not update)
        from dash import no_update

        result = reset_callback["func"](False)
        assert result[0] is no_update
        assert result[1] is no_update
        assert result[2] is no_update
        assert result[3] is no_update
        assert result[4] is no_update
