"""Tab rendering callbacks."""

from dash import Input, Output, State, html

from ..components import (
    executions_tab_content,
    profile_tab_content,
    scripts_tab_content,
    status_tab_content,
    users_tab_content,
)


def register_callbacks(app):
    """Register tab rendering callbacks."""

    @app.callback(
        Output("tab-content", "children"),
        Input("active-tab-store", "data"),
        Input("user-store", "data"),
        State("token-store", "data"),
        State("role-store", "data"),
        State("user-store", "data"),
    )
    def render_tab(tab, _, token, role, user_data):
        from dash import no_update

        # Check if tab-content exists in the layout
        # This is a workaround: if the callback is triggered before dashboard is loaded, just return no_update
        try:
            # Dash 2.x: callback_context.states contains all State values, but we can't directly check layout
            # Instead, check if the tab-content is present in the DOM by checking the trigger and token
            if not token or tab is None:
                return no_update
        except Exception:
            return no_update

        # Handle initial load when stores might not be populated yet
        if not token:
            return html.Div("Please login to view content.")

        # Set default tab if none provided
        if not tab:
            tab = "executions"  # Default to executions tab

        # Profile tab: always re-render with latest user_data
        if tab == "profile":
            return profile_tab_content(user_data or {})
        elif tab == "scripts":
            return scripts_tab_content()
        elif tab == "executions":
            return executions_tab_content()
        elif tab == "users":
            return users_tab_content()
        elif tab == "status":
            return status_tab_content(role == "ADMIN")
        return html.Div("Unknown tab.")

    # Remove the now-unnecessary update_profile_tab_on_user_change callback


# Legacy callback decorators for backward compatibility (these won't be executed)
