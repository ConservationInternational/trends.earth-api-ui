"""Initialize callbacks package."""

import importlib

from . import status


def register_all_callbacks(app):
    """Register all callbacks with the Dash app."""
    # First register status callbacks directly
    status.register_callbacks(app)

    # Use importlib to dynamically import other modules to avoid circular imports
    callback_modules = [
        "auth",
        "manual_tabs",  # Add manual tabs before tabs
        "tabs",
        "executions",
        "users",  # Add users table callbacks
        "scripts",  # Add scripts table callbacks
        "modals",
        "map",
        "profile",
        "edit",
        "refresh",
    ]

    for module_name in callback_modules:
        try:
            # Use importlib to import the module
            module = importlib.import_module(f".{module_name}", package="trendsearth_ui.callbacks")
            if hasattr(module, "register_callbacks"):
                module.register_callbacks(app)
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
