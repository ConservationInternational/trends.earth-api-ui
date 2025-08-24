"""Tab rendering callbacks."""

from dash import Input, Output, State, html

from ..components import (
    admin_tab_content,
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
        [
            Input("active-tab-store", "data"),
            Input("user-store", "data"),
        ],
        [
            State("token-store", "data"),
            State("role-store", "data"),
        ],
        prevent_initial_call=False,
    )
    def render_tab(tab, user_data, token, role):
        from dash import no_update

        # Guard: Skip if not logged in (prevents execution after logout)
        if not token:
            return no_update

        # Check if tab-content exists in the layout
        # This is a workaround: if the callback is triggered before dashboard is loaded, just return no_update
        try:
            # Dash 2.x: callback_context.states contains all State values, but we can't directly check layout
            # Instead, check if the tab-content is present in the DOM by checking the trigger and token
            if not token:
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
            # Only allow admin users to access scripts tab
            if role in ["ADMIN", "SUPERADMIN"]:
                return scripts_tab_content()
            else:
                return html.Div(
                    [
                        html.H4("Access Denied"),
                        html.P("Administrator privileges required to access script management."),
                    ]
                )
        elif tab == "executions":
            return executions_tab_content()
        elif tab == "users":
            # Only allow admin users to access users tab
            if role in ["ADMIN", "SUPERADMIN"]:
                return users_tab_content()
            else:
                return html.Div(
                    [
                        html.H4("Access Denied"),
                        html.P("Administrator privileges required to access user management."),
                    ]
                )
        elif tab == "admin":
            return admin_tab_content(role, role in ["ADMIN", "SUPERADMIN"])
        elif tab == "status":
            # Only allow admin users to access status tab
            if role in ["ADMIN", "SUPERADMIN"]:
                return status_tab_content(role in ["ADMIN", "SUPERADMIN"], role)
            else:
                return html.Div(
                    [
                        html.H4("Access Denied"),
                        html.P("Administrator privileges required to access system status."),
                    ]
                )
        return html.Div("Unknown tab.")

    # Remove the now-unnecessary update_profile_tab_on_user_change callback


# Legacy callback decorators for backward compatibility (these won't be executed)
