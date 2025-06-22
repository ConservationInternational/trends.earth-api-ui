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
        Input("tabs", "active_tab"),
        State("token-store", "data"),
        State("role-store", "data"),
        State("user-store", "data"),
        prevent_initial_call=True,
    )
    def render_tab(tab, token, role, user_data):
        """Render the content for the active tab."""
        if not token:
            return html.Div("Please login to view content."), [], []

        is_admin = role == "ADMIN"
        # Fetch scripts and users for joins
        scripts, users = fetch_scripts_and_users(token)

        if tab == "scripts":
            content = scripts_tab_content(scripts, users, is_admin)
            return content, scripts, users

        elif tab == "executions":
            content = executions_tab_content()
            return content, scripts, users

        elif tab == "users":
            content = users_tab_content(users, is_admin)
            return content, scripts, users

        elif tab == "profile":
            content = profile_tab_content(user_data)
            return content, scripts, users

        elif tab == "status":
            content = status_tab_content(is_admin)
            return content, scripts, users

        return html.Div("Unknown tab."), scripts, users


# Legacy callback decorators for backward compatibility (these won't be executed)
