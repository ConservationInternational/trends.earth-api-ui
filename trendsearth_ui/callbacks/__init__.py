"""Initialize callbacks package."""

import importlib
import logging

from ..utils.custom_filters import register_filter_callbacks
from ..utils.mobile_utils import register_mobile_callbacks
from . import status

logger = logging.getLogger(__name__)


def register_all_callbacks(app):
    """Register all callbacks with the Dash app."""
    # First register mobile detection callbacks
    register_mobile_callbacks()

    # Register custom filter callbacks
    register_filter_callbacks(app)

    # Register status callbacks
    status.register_callbacks(app)

    # Use importlib to dynamically import other modules to avoid circular imports
    callback_modules = [
        "timezone",  # Add timezone first for early detection
        "responsive",  # Add responsive callbacks early
        "auth",
        "manual_tabs",  # Add manual tabs before tabs
        "tabs",
        "executions",
        "users",  # Add users table callbacks
        "scripts",  # Add scripts table callbacks
        "admin",  # Add admin callbacks
        "modals",
        "map",
        "profile",
        "gee_credentials",  # Add GEE credentials callbacks
        "edit",
        "refresh",
    ]

    for module_name in callback_modules:
        try:
            # Use importlib to import the module
            module = importlib.import_module(f".{module_name}", package="trendsearth_ui.callbacks")
            if hasattr(module, "register_callbacks"):
                module.register_callbacks(app)
            elif hasattr(module, "register_responsive_callbacks"):
                module.register_responsive_callbacks(app)
            else:
                logger.warning("Module %s does not have register_callbacks function", module_name)
        except ImportError as e:
            logger.warning("Could not import %s callbacks: %s", module_name, e)
        except Exception as e:
            logger.error("Error registering %s callbacks: %s", module_name, e)


__all__ = [
    "register_all_callbacks",
    "status",
]
