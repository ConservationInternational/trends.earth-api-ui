"""Tests for logging configuration."""

import logging
import os
from unittest.mock import MagicMock, patch

import pytest

from trendsearth_ui.utils.logging_config import (
    get_logger,
    is_rollbar_initialized,
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
    import trendsearth_ui.utils.logging_config as lc

    with (
        patch("rollbar.init") as mock_rollbar_init,
        patch.object(lc, "_attach_rollbar_handler") as mock_attach,
    ):
        # Clear any existing handlers to ensure clean test
        logger = logging.getLogger("trendsearth_ui")
        logger.handlers.clear()
        # Reset the module-level flag
        old_flag = lc._rollbar_initialized
        lc._rollbar_initialized = False

        try:
            logger = setup_logging("test_token")

            # Verify Rollbar was initialized
            mock_rollbar_init.assert_called_once()

            # Verify handler was attached
            assert mock_attach.called
            assert lc._rollbar_initialized is True
        finally:
            lc._rollbar_initialized = old_flag


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
    """Test log wrapper functions.

    The log_* helpers now delegate entirely to the standard logging module.
    Rollbar dispatch is handled by the EnhancedRollbarHandler attached to the
    parent logger, so we just verify the correct logger methods are called.
    """
    logger = MagicMock()

    # Test log_exception
    log_exception(logger, "Test exception")
    logger.exception.assert_called_with("Test exception", exc_info=True)

    # Test log_error with extra data
    log_error(logger, "Test error", {"key": "value"})
    logger.error.assert_called_with("Test error", extra={"extra_data": {"key": "value"}})

    # Test log_error without extra data
    log_error(logger, "Simple error")
    logger.error.assert_called_with("Simple error")

    # Test log_warning
    log_warning(logger, "Test warning")
    logger.warning.assert_called_with("Test warning")

    # Test log_warning with extra data
    log_warning(logger, "Warning with data", {"some": "context"})
    logger.warning.assert_called_with(
        "Warning with data", extra={"extra_data": {"some": "context"}}
    )


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
