"""Logging configuration with Rollbar integration."""

import inspect
import logging
import os
import sys
from typing import Any, Optional

import rollbar
from rollbar.logger import RollbarHandler


class EnhancedRollbarHandler(RollbarHandler):
    """
    Enhanced Rollbar handler that automatically includes context for all log messages.
    """

    def emit(self, record):
        """Emit a log record with enhanced context."""
        try:
            # Get automatic context
            context = _get_automatic_context()

            # Add log record information
            context.update(
                {
                    "log_level": record.levelname,
                    "logger_name": record.name,
                    "timestamp": record.created,
                }
            )

            # If the record has extra context, include it
            if hasattr(record, "__dict__"):
                for key, value in record.__dict__.items():
                    if key not in [
                        "name",
                        "levelno",
                        "levelname",
                        "pathname",
                        "filename",
                        "module",
                        "lineno",
                        "funcName",
                        "created",
                        "msecs",
                        "relativeCreated",
                        "thread",
                        "threadName",
                        "processName",
                        "process",
                        "message",
                        "exc_info",
                        "exc_text",
                        "stack_info",
                        "getMessage",
                        "args",
                        "msg",
                    ]:
                        context[f"record_{key}"] = str(value)

            # Create a new record with enhanced extra_data
            enhanced_record = logging.LogRecord(
                name=record.name,
                level=record.levelno,
                pathname=record.pathname,
                lineno=record.lineno,
                msg=record.getMessage(),
                args=(),
                exc_info=record.exc_info,
            )

            # Add our context to the record
            if hasattr(enhanced_record, "extra_data"):
                enhanced_record.extra_data.update(context)
            else:
                enhanced_record.extra_data = context

            # Call the parent emit method with our enhanced record
            super().emit(enhanced_record)

        except Exception:
            # Don't let context enhancement break the actual logging
            super().emit(record)


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
            rollbar_handler = EnhancedRollbarHandler()
            rollbar_handler.setLevel(logging.WARNING)  # Only send warnings and errors to Rollbar
            logger.addHandler(rollbar_handler)

            logger.info("Rollbar logging initialized successfully")

        except Exception as e:
            logger.warning(f"Failed to initialize Rollbar: {e}")

    return logger


def get_logger() -> logging.Logger:
    """Get the configured logger instance."""
    return logging.getLogger("trendsearth_ui")


def _get_automatic_context() -> dict[str, Any]:
    """
    Automatically gather context information for error reporting.

    Returns:
        Dict with relevant context information for debugging
    """
    context = {}

    try:
        # Get the calling frame information
        frame = inspect.currentframe()
        if frame and frame.f_back and frame.f_back.f_back:
            caller_frame = frame.f_back.f_back
            context.update(
                {
                    "function_name": caller_frame.f_code.co_name,
                    "filename": caller_frame.f_code.co_filename,
                    "line_number": caller_frame.f_lineno,
                }
            )

            # Get local variables (excluding sensitive data)
            local_vars = caller_frame.f_locals.copy()
            filtered_vars = {}
            for key, value in local_vars.items():
                # Skip private variables and sensitive data
                if not key.startswith("_") and key.lower() not in [
                    "token",
                    "password",
                    "secret",
                    "key",
                ]:
                    # Convert complex objects to string representation
                    try:
                        if isinstance(value, (str, int, float, bool, list, dict)):
                            if isinstance(value, str) and len(value) > 200:
                                filtered_vars[key] = value[:200] + "..."
                            elif isinstance(value, (list, dict)):
                                filtered_vars[key] = (
                                    str(value)[:200] + "..." if len(str(value)) > 200 else value
                                )
                            else:
                                filtered_vars[key] = value
                        else:
                            filtered_vars[key] = str(type(value))
                    except Exception:
                        filtered_vars[key] = "<unable to serialize>"

            if filtered_vars:
                context["local_variables"] = filtered_vars

    except Exception:
        # Don't let context gathering fail the actual logging
        pass

    # Add environment information
    context.update(
        {
            "environment": os.environ.get("DEPLOYMENT_ENVIRONMENT", "development"),
            "git_commit": os.environ.get("GIT_COMMIT", "unknown"),
            "git_branch": os.environ.get("GIT_BRANCH", "unknown"),
        }
    )

    return context


def log_exception(logger: logging.Logger, message: str, exc_info=True):
    """Log an exception with Rollbar integration and automatic context."""
    logger.exception(message, exc_info=exc_info)

    # If Rollbar is configured, also report to Rollbar with automatic context
    if rollbar._initialized:
        context = _get_automatic_context()
        context["message"] = message
        rollbar.report_exc_info(extra_data=context)


def log_error(logger: logging.Logger, message: str, extra_data: dict = None):
    """Log an error with optional extra data and automatic context."""
    logger.error(message)

    # If Rollbar is configured, also report to Rollbar with enhanced context
    if rollbar._initialized:
        context = _get_automatic_context()
        if extra_data:
            context.update(extra_data)
        context["message"] = message
        rollbar.report_message(message, level="error", extra_data=context)


def log_warning(logger: logging.Logger, message: str, extra_data: dict = None):
    """Log a warning with optional extra data and automatic context."""
    logger.warning(message)

    # If Rollbar is configured, also report to Rollbar with enhanced context
    if rollbar._initialized:
        context = _get_automatic_context()
        if extra_data:
            context.update(extra_data)
        context["message"] = message
        rollbar.report_message(message, level="warning", extra_data=context)
