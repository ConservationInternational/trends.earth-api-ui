"""Responsive design callbacks for mobile device handling."""

from dash import Input, Output, no_update

from ..utils.mobile_utils import get_responsive_grid_options


def register_responsive_callbacks(app):
    """Register callbacks for responsive design features."""

    # Separate callbacks for each table to handle missing components gracefully
    @app.callback(
        Output("executions-table", "dashGridOptions", allow_duplicate=True),
        Input("is-mobile-store", "data"),
        prevent_initial_call=True,
    )
    def update_executions_table_grid_options(is_mobile):
        """Update executions table grid options based on mobile detection."""
        if is_mobile is None:
            return no_update
        try:
            return get_responsive_grid_options(is_mobile=is_mobile)
        except Exception:
            return no_update

    @app.callback(
        Output("users-table", "dashGridOptions", allow_duplicate=True),
        Input("is-mobile-store", "data"),
        prevent_initial_call=True,
    )
    def update_users_table_grid_options(is_mobile):
        """Update users table grid options based on mobile detection."""
        if is_mobile is None:
            return no_update
        try:
            return get_responsive_grid_options(is_mobile=is_mobile)
        except Exception:
            return no_update

    @app.callback(
        Output("scripts-table", "dashGridOptions", allow_duplicate=True),
        Input("is-mobile-store", "data"),
        prevent_initial_call=True,
    )
    def update_scripts_table_grid_options(is_mobile):
        """Update scripts table grid options based on mobile detection."""
        if is_mobile is None:
            return no_update
        try:
            return get_responsive_grid_options(is_mobile=is_mobile)
        except Exception:
            return no_update

    # Individual callbacks for each table scroll hint to avoid missing component errors
    @app.callback(
        Output("executions-table-scroll-hint", "style", allow_duplicate=True),
        Input("is-mobile-store", "data"),
        prevent_initial_call=True,
    )
    def update_executions_scroll_hint(is_mobile):
        """Show/hide executions table scroll hint based on device type."""
        if is_mobile is None:
            return no_update
        return {"display": "block"} if is_mobile else {"display": "none"}

    @app.callback(
        Output("users-table-scroll-hint", "style", allow_duplicate=True),
        Input("is-mobile-store", "data"),
        prevent_initial_call=True,
    )
    def update_users_scroll_hint(is_mobile):
        """Show/hide users table scroll hint based on device type."""
        if is_mobile is None:
            return no_update
        return {"display": "block"} if is_mobile else {"display": "none"}

    @app.callback(
        Output("scripts-table-scroll-hint", "style", allow_duplicate=True),
        Input("is-mobile-store", "data"),
        prevent_initial_call=True,
    )
    def update_scripts_scroll_hint(is_mobile):
        """Show/hide scripts table scroll hint based on device type."""
        if is_mobile is None:
            return no_update
        return {"display": "block"} if is_mobile else {"display": "none"}
