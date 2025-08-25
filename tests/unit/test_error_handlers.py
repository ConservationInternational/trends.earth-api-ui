"""Tests for error handlers in the application."""

from unittest.mock import Mock, patch

import pytest

from trendsearth_ui.app import _is_bot_request, server


class TestBotDetection:
    """Test bot detection functionality."""

    def test_is_bot_request_with_known_bots(self):
        """Test bot detection with known bot user agents."""
        bot_user_agents = [
            "libredtail-http",
            "python-requests/2.25.1",
            "curl/7.68.0",
            "wget/1.20.3",
            "Go-http-client/1.1",
            "Apache-HttpClient/4.5.10",
            "Nikto/2.1.6",
            "sqlmap/1.5.1",
            "Nuclei/v2.5.0",
        ]

        for user_agent in bot_user_agents:
            assert _is_bot_request(user_agent), f"Should detect as bot: {user_agent}"

    def test_is_bot_request_with_legitimate_agents(self):
        """Test bot detection with legitimate user agents."""
        legitimate_user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)",
            "PostmanRuntime/7.28.4",
            "Chrome/91.0.4472.124",
            "Safari/605.1.15",
            "Edge/91.0.864.59",
        ]

        for user_agent in legitimate_user_agents:
            assert not _is_bot_request(user_agent), f"Should not detect as bot: {user_agent}"

    def test_is_bot_request_with_empty_or_none(self):
        """Test bot detection with empty or None user agent."""
        assert not _is_bot_request("")
        assert not _is_bot_request(None)

    def test_is_bot_request_case_insensitive(self):
        """Test bot detection is case insensitive."""
        assert _is_bot_request("PYTHON-REQUESTS/2.25.1")
        assert _is_bot_request("Python-Requests/2.25.1")
        assert _is_bot_request("LIBREDTAIL-HTTP")


class TestErrorHandlers:
    """Test error handling functionality."""

    def test_405_error_handler_exists(self):
        """Test that 405 error handler is registered."""
        # Check that the error handler is registered
        assert 405 in server.error_handler_spec[None]

    def test_405_error_handler_with_legitimate_user_agent(self):
        """Test 405 handler with legitimate user agent reports to Rollbar."""
        with server.test_client() as client:
            with patch("trendsearth_ui.utils.logging_config.log_exception") as mock_log:
                # Test POST to non-existent endpoint with legitimate user agent
                response = client.post(
                    "/nonexistent",
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                )

                assert response.status_code == 405
                # Should have called log_exception (which reports to Rollbar)
                assert mock_log.called

                # Check that the first call was for the 405 error
                first_call_args = mock_log.call_args_list[0][0]
                assert "405 Method Not Allowed" in first_call_args[1]
                assert "Path: /nonexistent" in first_call_args[1]
                assert "Method: POST" in first_call_args[1]

    def test_405_error_handler_with_bot_user_agent(self):
        """Test 405 handler with bot user agent does not report to Rollbar."""
        with server.test_client() as client:
            with patch("trendsearth_ui.utils.logging_config.log_exception") as mock_log:
                # Test POST to non-existent endpoint with bot user agent
                response = client.post("/hello.world", headers={"User-Agent": "libredtail-http"})

                assert response.status_code == 405
                # Should not have called log_exception for bot requests
                assert not mock_log.called

    def test_405_error_handler_with_various_bot_user_agents(self):
        """Test 405 handler filters various known bot user agents."""
        bot_user_agents = [
            "libredtail-http",
            "python-requests/2.25.1",
            "curl/7.68.0",
            "wget/1.20.3",
            "Go-http-client/1.1",
            "Apache-HttpClient/4.5.10",
            "Nikto",
            "sqlmap",
            "Nuclei",
        ]

        with server.test_client() as client:
            for user_agent in bot_user_agents:
                with patch("trendsearth_ui.utils.logging_config.log_exception") as mock_log:
                    response = client.post("/test-endpoint", headers={"User-Agent": user_agent})

                    assert response.status_code == 405
                    # Should not have called log_exception for bot requests
                    assert not mock_log.called, f"Should not log for user agent: {user_agent}"

    def test_405_error_handler_still_logs_locally(self):
        """Test 405 handler still logs locally even for bot requests."""
        with server.test_client() as client:
            with patch("trendsearth_ui.app.logger") as mock_logger:
                response = client.post("/hello.world", headers={"User-Agent": "libredtail-http"})

                assert response.status_code == 405
                # Should still log locally for debugging
                assert mock_logger.warning.called

                # Check the warning message
                call_args = mock_logger.warning.call_args[0]
                assert "405 Method Not Allowed (bot filtered)" in call_args[0]
                assert "libredtail-http" in call_args[0]

    def test_405_error_handler_with_api_endpoint(self):
        """Test 405 handler returns JSON for API endpoints."""
        with server.test_client() as client:
            response = client.post("/api/test", headers={"User-Agent": "Mozilla/5.0"})

            assert response.status_code == 405
            assert response.is_json
            data = response.get_json()
            assert data["status"] == "error"
            assert "not allowed" in data["message"]

    def test_405_error_handler_with_regular_endpoint(self):
        """Test 405 handler returns text for regular endpoints."""
        with server.test_client() as client:
            response = client.post("/test", headers={"User-Agent": "Mozilla/5.0"})

            assert response.status_code == 405
            assert not response.is_json
            assert "not allowed" in response.get_data(as_text=True)
