"""Logging configuration with Rollbar integration."""

import logging
import os
import sys
from typing import Optional

import rollbar
from rollbar.logger import RollbarHandler


def setup_logging(rollbar_token: Optional[str] = None) -> logging.Logger:
    """Set up logging with Rollbar integration if token is provided."""

    # Get logger for the application
    logger = logging.getLogger("trendsearth_ui")

    # Only configure if not already configured
    if logger.handlers:
        return logger

    # Set logging level
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # Create formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Add Rollbar handler if token is provided
    if rollbar_token:
        try:
            # Initialize Rollbar
            rollbar.init(
                access_token=rollbar_token,
                environment=os.environ.get("DEPLOYMENT_ENVIRONMENT", "development"),
                code_version=os.environ.get("GIT_COMMIT", "unknown"),
                branch=os.environ.get("GIT_BRANCH", "unknown"),
                capture_email=False,  # Don't capture email addresses for privacy
                capture_username=False,  # Don't capture usernames for privacy
                capture_ip=False,  # Don't capture IP addresses for privacy
                locals={
                    "enabled": False  # Don't capture local variables for security
                },
            )

            # Add Rollbar handler to logger
            rollbar_handler = RollbarHandler()
            rollbar_handler.setLevel(logging.WARNING)  # Only send warnings and errors to Rollbar
            logger.addHandler(rollbar_handler)

            logger.info("Rollbar logging initialized successfully")

        except Exception as e:
            logger.warning(f"Failed to initialize Rollbar: {e}")

    return logger


def get_logger() -> logging.Logger:
    """Get the configured logger instance."""
    return logging.getLogger("trendsearth_ui")


def log_exception(logger: logging.Logger, message: str, exc_info=True):
    """Log an exception with Rollbar integration."""
    logger.exception(message, exc_info=exc_info)

    # If Rollbar is configured, also report to Rollbar
    if rollbar._initialized:
        rollbar.report_exc_info(extra_data={"message": message})


def log_error(logger: logging.Logger, message: str, extra_data: dict = None):
    """Log an error with optional extra data."""
    logger.error(message)

    # If Rollbar is configured, also report to Rollbar
    if rollbar._initialized:
        rollbar.report_message(message, level="error", extra_data=extra_data or {})


def log_warning(logger: logging.Logger, message: str, extra_data: dict = None):
    """Log a warning with optional extra data."""
    logger.warning(message)

    # If Rollbar is configured, also report to Rollbar
    if rollbar._initialized:
        rollbar.report_message(message, level="warning", extra_data=extra_data or {})
