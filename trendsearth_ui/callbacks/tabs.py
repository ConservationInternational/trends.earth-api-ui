"""Tab rendering callbacks."""

from dash import Input, Output, State, html

from ..components import (
    executions_tab_content,
    profile_tab_content,
    scripts_tab_content,
    status_tab_content,
    users_tab_content,
)
from ..utils import fetch_scripts_and_users


def register_callbacks(app):
    """Register tab rendering callbacks."""

    @app.callback(
        Output("tab-content", "children"),
        Output("scripts-raw-data", "data"),
        Output("users-raw-data", "data"),
        Input("active-tab-store", "data"),
        Input("user-store", "data"),
        State("token-store", "data"),
        State("role-store", "data"),
        State("user-store", "data"),
    )
    def render_tab(tab, _, token, role, user_data):
        import dash
        from dash import no_update

        # Check if tab-content exists in the layout
        # This is a workaround: if the callback is triggered before dashboard is loaded, just return no_update
        try:
            # Dash 2.x: callback_context.states contains all State values, but we can't directly check layout
            # Instead, check if the tab-content is present in the DOM by checking the trigger and token
            if not token or tab is None:
                return no_update, no_update, no_update
        except Exception:
            return no_update, no_update, no_update

        ctx = dash.callback_context
        trigger = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

        # Handle initial load when stores might not be populated yet
        if not token:
            return html.Div("Please login to view content."), [], []

        # Set default tab if none provided
        if not tab:
            tab = "executions"  # Default to executions tab

        # Fetch scripts and users only if tab changes
        scripts, users = [], []
        if trigger == "active-tab-store":
            try:
                scripts, users = fetch_scripts_and_users(token)
            except Exception:
                scripts, users = [], []

        # Profile tab: always re-render with latest user_data
        if tab == "profile":
            return profile_tab_content(user_data or {}), scripts, users
        elif tab == "scripts":
            return scripts_tab_content(scripts, users, role == "ADMIN"), scripts, users
        elif tab == "executions":
            return executions_tab_content(), scripts, users
        elif tab == "users":
            return users_tab_content(users, role == "ADMIN"), scripts, users
        elif tab == "status":
            return status_tab_content(role == "ADMIN"), scripts, users
        return html.Div("Unknown tab."), scripts, users

    # Remove the now-unnecessary update_profile_tab_on_user_change callback


# Legacy callback decorators for backward compatibility (these won't be executed)
