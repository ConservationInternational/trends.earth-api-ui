"""Initialize callbacks package."""


def register_all_callbacks(app):
    """Register all callbacks with the Dash app."""
    # Import each module only when needed to avoid circular imports
    from . import auth
    from . import tabs
    from . import executions
    from . import modals
    from . import map
    from . import profile
    from . import edit
    from . import refresh
    from . import status
    
    # Register all callbacks
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
]
