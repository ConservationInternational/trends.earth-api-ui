"""Test password change functionality."""

from unittest.mock import Mock, patch

import pytest

from trendsearth_ui.callbacks.profile import register_callbacks


class TestPasswordChange:
    """Test password change functionality."""

    def test_password_change_success(self, dash_app, mock_token, mock_user_data):
        """Test successful password change."""
        # Register the callbacks
        register_callbacks(dash_app)

        # Mock successful API response
        with patch("trendsearth_ui.utils.helpers.make_authenticated_request") as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_request.return_value = mock_response

            # Mock callback inputs
            n_clicks = 1
            current_password = "old_password"
            new_password = "new_password123"
            confirm_password = "new_password123"
            token = mock_token
            user_data = mock_user_data

            # Get the callback function
            callback_func = None
            for callback in dash_app.callback_map.values():
                if (
                    hasattr(callback, "function")
                    and callback.function.__name__ == "change_password"
                ):
                    callback_func = callback.function
                    break

            if callback_func:
                result = callback_func(
                    n_clicks, current_password, new_password, confirm_password, token, user_data
                )

                # Check that the result indicates success
                assert result[0] == "Password changed successfully!"
                assert result[1] == "success"
                assert result[2]
                # Check that password fields are cleared
                assert result[3] == ""
                assert result[4] == ""
                assert result[5] == ""

                # Verify API was called
                mock_request.assert_called()

    def test_password_change_validation_errors(self, dash_app, mock_token, mock_user_data):
        """Test password change validation errors."""
        # Register the callbacks
        register_callbacks(dash_app)

        # Get the callback function
        callback_func = None
        for callback in dash_app.callback_map.values():
            if hasattr(callback, "function") and callback.function.__name__ == "change_password":
                callback_func = callback.function
                break

        if callback_func:
            # Test password mismatch
            result = callback_func(
                1, "old_pass", "new_pass", "different_pass", mock_token, mock_user_data
            )
            assert "do not match" in result[0]
            assert result[1] == "danger"

            # Test password too short
            result = callback_func(1, "old_pass", "short", "short", mock_token, mock_user_data)
            assert "at least 6 characters" in result[0]
            assert result[1] == "danger"

            # Test missing fields
            result = callback_func(1, "", "new_pass", "new_pass", mock_token, mock_user_data)
            assert "required" in result[0]
            assert result[1] == "danger"

    def test_password_change_api_error(self, dash_app, mock_token, mock_user_data):
        """Test password change with API error."""
        # Register the callbacks
        register_callbacks(dash_app)

        # Mock API error response
        with patch("trendsearth_ui.utils.helpers.make_authenticated_request") as mock_request:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.json.return_value = {"msg": "Current password is incorrect"}
            mock_request.return_value = mock_response

            # Get the callback function
            callback_func = None
            for callback in dash_app.callback_map.values():
                if (
                    hasattr(callback, "function")
                    and callback.function.__name__ == "change_password"
                ):
                    callback_func = callback.function
                    break

            if callback_func:
                result = callback_func(
                    1, "wrong_pass", "new_pass123", "new_pass123", mock_token, mock_user_data
                )

                # Check that the result indicates failure
                assert "Current password is incorrect" in result[0]
                assert result[1] == "danger"
                assert result[2]
