"""Tests for logging configuration."""

import logging
import os
from unittest.mock import MagicMock, patch

import pytest

from trendsearth_ui.utils.logging_config import (
    get_logger,
    log_error,
    log_exception,
    log_warning,
    setup_logging,
)


def test_setup_logging_without_rollbar():
    """Test logging setup without Rollbar token."""
    with patch.dict(os.environ, {}, clear=True):
        # Clear any existing handlers to ensure clean test
        logger = logging.getLogger("trendsearth_ui")
        logger.handlers.clear()

        logger = setup_logging()
        assert logger.name == "trendsearth_ui"
        assert logger.level == logging.INFO
        assert len(logger.handlers) >= 1  # At least console handler


def test_setup_logging_with_rollbar():
    """Test logging setup with Rollbar token."""
    with (
        patch("rollbar.init") as mock_rollbar_init,
        patch("trendsearth_ui.utils.logging_config.EnhancedRollbarHandler") as mock_rollbar_handler,
    ):
        mock_handler = MagicMock()
        # Configure the mock handler to have a proper level attribute
        mock_handler.level = logging.WARNING
        mock_rollbar_handler.return_value = mock_handler

        # Clear any existing handlers to ensure clean test
        logger = logging.getLogger("trendsearth_ui")
        logger.handlers.clear()

        logger = setup_logging("test_token")

        # Verify Rollbar was initialized
        mock_rollbar_init.assert_called_once()

        # Verify handler was added
        mock_rollbar_handler.assert_called_once()
        assert mock_handler in logger.handlers


def test_setup_logging_rollbar_failure():
    """Test logging setup when Rollbar initialization fails."""
    with patch("rollbar.init", side_effect=Exception("Rollbar error")):
        # Clear any existing handlers to ensure clean test
        logger = logging.getLogger("trendsearth_ui")
        logger.handlers.clear()

        logger = setup_logging("test_token")
        assert logger.name == "trendsearth_ui"
        # Should still work even if Rollbar fails


def test_get_logger():
    """Test getting the configured logger."""
    logger = get_logger()
    assert logger.name == "trendsearth_ui"


def test_log_functions():
    """Test log wrapper functions with enhanced context."""
    with (
        patch("rollbar._initialized", True),
        patch("rollbar.report_exc_info") as mock_exc_info,
        patch("rollbar.report_message") as mock_message,
    ):
        logger = MagicMock()

        # Test log_exception
        log_exception(logger, "Test exception")
        logger.exception.assert_called_with("Test exception", exc_info=True)
        mock_exc_info.assert_called_once()

        # Verify that enhanced context was included
        call_args = mock_exc_info.call_args[1]  # Get keyword arguments
        extra_data = call_args["extra_data"]
        assert "function_name" in extra_data
        assert "filename" in extra_data
        assert "line_number" in extra_data
        assert "environment" in extra_data
        assert extra_data["message"] == "Test exception"

        # Test log_error with additional context
        log_error(logger, "Test error", {"key": "value"})
        logger.error.assert_called_with("Test error")

        # Verify enhanced context includes both automatic and provided data
        call_args = mock_message.call_args[1]  # Get keyword arguments
        extra_data = call_args["extra_data"]
        assert extra_data["key"] == "value"  # User-provided data
        assert "function_name" in extra_data  # Automatic context
        assert "filename" in extra_data
        assert "line_number" in extra_data
        assert "environment" in extra_data
        assert extra_data["message"] == "Test error"

        # Test log_warning with no additional context
        log_warning(logger, "Test warning")
        logger.warning.assert_called_with("Test warning")

        # Verify enhanced context is still added even with no user data
        call_args = mock_message.call_args[1]  # Get keyword arguments
        extra_data = call_args["extra_data"]
        assert "function_name" in extra_data
        assert "environment" in extra_data
        assert extra_data["message"] == "Test warning"


def test_environment_variables():
    """Test that environment variables are properly used."""
    with (
        patch.dict(
            os.environ,
            {
                "LOG_LEVEL": "DEBUG",
                "DEPLOYMENT_ENVIRONMENT": "staging",
                "GIT_COMMIT": "abc123",
                "GIT_BRANCH": "feature/test",
            },
        ),
        patch("rollbar.init") as mock_rollbar_init,
    ):
        # Clear any existing handlers to ensure clean test
        logger = logging.getLogger("trendsearth_ui")
        logger.handlers.clear()

        setup_logging("test_token")

        # Verify environment variables were passed to Rollbar
        mock_rollbar_init.assert_called_once()
        call_args = mock_rollbar_init.call_args[1]  # Get keyword arguments
        assert call_args["environment"] == "staging"
        assert call_args["code_version"] == "abc123"
        assert call_args["branch"] == "feature/test"
