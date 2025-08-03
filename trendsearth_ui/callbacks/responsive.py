"""Responsive design callbacks for mobile device handling."""

from dash import Input, Output, no_update

from ..utils.mobile_utils import get_responsive_grid_options


def register_responsive_callbacks(app):
    """Register callbacks for responsive design features."""

    @app.callback(
        [
            Output("executions-table", "dashGridOptions", allow_duplicate=True),
            Output("users-table", "dashGridOptions", allow_duplicate=True),
            Output("scripts-table", "dashGridOptions", allow_duplicate=True),
        ],
        Input("is-mobile-store", "data"),
        prevent_initial_call=True,
    )
    def update_table_grid_options(is_mobile):
        """Update table grid options based on mobile detection."""
        if is_mobile is None:
            return no_update, no_update, no_update

        grid_options = get_responsive_grid_options(is_mobile=is_mobile)
        return grid_options, grid_options, grid_options

    @app.callback(
        Output("tabs-nav", "className", allow_duplicate=True),
        Input("is-mobile-store", "data"),
        prevent_initial_call=True,
    )
    def update_tab_navigation_class(is_mobile):
        """Update tab navigation class for mobile."""
        if is_mobile is None:
            return no_update

        tab_class = "nav nav-tabs"
        if is_mobile:
            tab_class += " multi-row"
        return tab_class

    @app.callback(
        [
            Output("executions-table-scroll-hint", "style", allow_duplicate=True),
            Output("users-table-scroll-hint", "style", allow_duplicate=True),
            Output("scripts-table-scroll-hint", "style", allow_duplicate=True),
        ],
        Input("is-mobile-store", "data"),
        prevent_initial_call=True,
    )
    def update_scroll_hints(is_mobile):
        """Show/hide scroll hints based on device type."""
        if is_mobile is None:
            return no_update, no_update, no_update

        hint_style = {"display": "block"} if is_mobile else {"display": "none"}
        return hint_style, hint_style, hint_style
