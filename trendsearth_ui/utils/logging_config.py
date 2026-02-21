"""Logging configuration with Rollbar integration."""

import inspect
import logging
import os
import sys
from typing import Any, Optional

import rollbar
from rollbar.logger import RollbarHandler

# Module-level flag to track whether Rollbar was successfully initialised.
# This avoids relying on the private ``rollbar._initialized`` attribute.
_rollbar_initialized: bool = False


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


def _attach_rollbar_handler(target_logger: logging.Logger) -> None:
    """Add an ``EnhancedRollbarHandler`` to *target_logger* if it doesn't already have one."""
    for h in target_logger.handlers:
        if isinstance(h, EnhancedRollbarHandler):
            return
    handler = EnhancedRollbarHandler()
    handler.setLevel(logging.WARNING)
    target_logger.addHandler(handler)


def setup_logging(rollbar_token: Optional[str] = None) -> logging.Logger:
    """Set up logging with Rollbar integration if token is provided."""
    global _rollbar_initialized  # noqa: PLW0603

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
            _rollbar_initialized = True

            # Add Rollbar handler to the application logger.
            # Child loggers (e.g. trendsearth_ui.callbacks.auth) propagate
            # to this parent automatically.
            _attach_rollbar_handler(logger)

            # Also attach the handler to Dash's internal logger so that
            # unhandled callback exceptions are forwarded to Rollbar.
            for dash_logger_name in ("dash", "dash.dash"):
                _attach_rollbar_handler(logging.getLogger(dash_logger_name))

            logger.info("Rollbar logging initialized successfully")

        except Exception as e:
            logger.warning(f"Failed to initialize Rollbar: {e}")

    return logger


def is_rollbar_initialized() -> bool:
    """Return ``True`` if Rollbar has been successfully initialised."""
    return _rollbar_initialized


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
    """Log an exception with Rollbar integration and automatic context.

    The ``EnhancedRollbarHandler`` attached to the *trendsearth_ui* logger
    (and propagated to by child loggers) automatically forwards WARNING+
    messages to Rollbar with enriched context, so there is no need to call
    ``rollbar.report_exc_info`` directly — doing so would create duplicate
    events in Rollbar.
    """
    logger.exception(message, exc_info=exc_info)


def log_error(logger: logging.Logger, message: str, extra_data: dict | None = None):
    """Log an error with optional extra data and automatic context.

    Rollbar dispatch happens automatically via the ``EnhancedRollbarHandler``.
    """
    if extra_data:
        logger.error(message, extra={"extra_data": extra_data})
    else:
        logger.error(message)


def log_warning(logger: logging.Logger, message: str, extra_data: dict | None = None):
    """Log a warning with optional extra data and automatic context.

    Rollbar dispatch happens automatically via the ``EnhancedRollbarHandler``.
    """
    if extra_data:
        logger.warning(message, extra={"extra_data": extra_data})
    else:
        logger.warning(message)
