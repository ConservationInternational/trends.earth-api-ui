"""Initialize callbacks package."""

# Import all callback modules to register them
from . import auth, edit, executions, map, modals, profile, refresh, status, tabs


def register_all_callbacks(app):
    """Register all callbacks with the Dash app."""
    # Import each module and call its register function
    auth.register_callbacks(app)
    tabs.register_callbacks(app)
    executions.register_callbacks(app)
    modals.register_callbacks(app)
    map.register_callbacks(app)
    profile.register_callbacks(app)
    edit.register_callbacks(app)
    refresh.register_callbacks(app)
    status.register_callbacks(app)


__all__ = [
    "register_all_callbacks",
    "auth",
    "tabs",
    "executions",
    "modals",
    "map",
    "profile",
    "edit",
    "refresh",
    "status",
]
