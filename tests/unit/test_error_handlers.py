"""Test error handlers in the Flask app."""

import json
from unittest.mock import MagicMock, patch

import pytest

# Import the actual app with error handlers
from trendsearth_ui.app import app as main_app


@pytest.fixture
def test_client():
    """Create a test client using the actual app with error handlers."""
    return main_app.server.test_client()


def test_400_bad_request_handler_for_dash_callback_empty_body(test_client):
    """Test 400 Bad Request handler for Dash callback endpoints with empty body."""
    # Simulate empty JSON request to Dash callback endpoint (exactly like the Rollbar error)
    response = test_client.post(
        "/_dash-update-component",
        data="",  # Empty data which should trigger JSON decode error
        content_type="application/json",
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert "Invalid or malformed request data" in data["message"]


def test_400_bad_request_handler_for_dash_callback_malformed_json(test_client):
    """Test 400 Bad Request handler for Dash callback endpoints with malformed JSON."""
    # Simulate malformed JSON request to Dash callback endpoint
    response = test_client.post(
        "/_dash-update-component",
        data="{'invalid': json}",  # Invalid JSON format
        content_type="application/json",
    )

    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert "Invalid or malformed request data" in data["message"]


def test_400_bad_request_handler_with_request_data_logging(test_client):
    """Test that the 400 handler logs request details including data preview."""
    # Mock the specific log_exception call to capture the log message
    with patch("trendsearth_ui.utils.logging_config.log_exception") as mock_log:
        # Simulate malformed JSON request exactly like the Rollbar error
        response = test_client.post(
            "/_dash-update-component",
            data="invalid json{",
            content_type="application/json",
            headers={"User-Agent": "Mozilla/5.0 Chrome", "Content-Length": "13"},
        )

        assert response.status_code == 400

        # Verify that log_exception was called with detailed request info
        mock_log.assert_called()
        log_call_args = mock_log.call_args[0]
        log_message = log_call_args[1]  # Second argument is the message

        assert "400 Bad Request" in log_message
        assert "/_dash-update-component" in log_message
        assert "POST" in log_message
        assert "application/json" in log_message
        assert "Content-Length: 13" in log_message
        assert "Mozilla/5.0 Chrome" in log_message
        assert "Data preview:" in log_message
        assert "invalid json{" in log_message


def test_405_method_not_allowed_handler_still_works(test_client):
    """Test that existing 405 handler still works properly."""
    # Try to POST to a GET-only endpoint
    response = test_client.post("/api-ui-health")

    assert response.status_code == 405
    data = json.loads(response.data)
    assert data["status"] == "error"
    assert "not allowed" in data["message"]


def test_error_handlers_are_registered(test_client):
    """Test that all error handlers are properly registered."""
    # Check that error handlers are registered on the Flask app
    error_handlers = main_app.server.error_handler_spec.get(None, {})

    # Check for the specific error codes we handle
    assert 400 in error_handlers  # Our new Bad Request handler
    assert 405 in error_handlers  # Method Not Allowed handler
    assert 500 in error_handlers  # Internal Server Error handler

    # The Exception handler is registered under the None key
    general_handlers = error_handlers.get(None, {})
    assert Exception in general_handlers  # General exception handler


def test_400_handler_returns_json_for_api_requests(test_client):
    """Test that 400 handler returns JSON for API-like requests."""
    # This tests the condition for API endpoints in the 400 handler
    response = test_client.post(
        "/_dash-update-component",  # Dash endpoints should get JSON response
        data="",
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.content_type.startswith("application/json")

    data = json.loads(response.data)
    assert "status" in data
    assert "message" in data
