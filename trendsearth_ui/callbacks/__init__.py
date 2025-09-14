"""Initialize callbacks package."""

import importlib

from ..utils.custom_filters import register_filter_callbacks
from ..utils.mobile_utils import register_mobile_callbacks
from . import status, status_optimized


def register_all_callbacks(app):
    """Register all callbacks with the Dash app."""
    # First register mobile detection callbacks
    register_mobile_callbacks()

    # Register custom filter callbacks
    register_filter_callbacks(app)

    # Register optimized status callbacks for better performance
    status_optimized.register_optimized_callbacks(app)

    # Register status callbacks for backward compatibility
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
                print(f"Warning: Module {module_name} does not have register_callbacks function")
        except ImportError as e:
            print(f"Warning: Could not import {module_name} callbacks: {e}")
        except Exception as e:
            print(f"Error registering {module_name} callbacks: {e}")


__all__ = [
    "register_all_callbacks",
    "status",
]
