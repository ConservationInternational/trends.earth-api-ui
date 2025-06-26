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
    )
    def render_tab(tab, token, role, user_data):
        """Render the content for the active tab."""
        # Handle initial load when stores might not be populated yet
        if not token:
            return html.Div("Please login to view content."), [], []

        # Set default tab if none provided
        if not tab:
            tab = "executions"  # Default to executions tab

        # Handle case where role might not be set yet
        is_admin = (role == "ADMIN") if role else False
        
        # Only fetch data if we have a valid token and tab
        try:
            scripts, users = fetch_scripts_and_users(token)
        except Exception as e:
            print(f"Error fetching data: {e}")
            scripts, users = [], []

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
            # Pass user_data even if it's None - the profile_tab_content handles it
            content = profile_tab_content(user_data or {})
            return content, scripts, users

        elif tab == "status":
            content = status_tab_content(is_admin)
            return content, scripts, users

        return html.Div("Unknown tab."), scripts, users


# Legacy callback decorators for backward compatibility (these won't be executed)
