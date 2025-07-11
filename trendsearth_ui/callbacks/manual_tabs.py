"""Manual tab switching callbacks to replace dbc.Tabs functionality."""

from dash import Input, Output, callback_context


def register_callbacks(app):
    """Register manual tab switching callbacks."""

    @app.callback(
        Output("admin-tab-li", "style"),
        [
            Input("role-store", "data"),
            Input("token-store", "data"),
        ],
        prevent_initial_call=False,  # Allow initial call to show admin tab on dashboard load
    )
    def toggle_admin_tab_visibility(role, token):
        """Show/hide admin tab based on user role."""
        # Guard: Skip if not logged in (prevents execution after logout)
        if not token:
            return {"display": "none"}

        if role in ["ADMIN", "SUPERADMIN"]:
            return {"display": "block"}
        else:
            return {"display": "none"}

    @app.callback(
        Output("users-tab-li", "style"),
        [
            Input("role-store", "data"),
            Input("token-store", "data"),
        ],
        prevent_initial_call=False,  # Allow initial call to show users tab on dashboard load
    )
    def toggle_users_tab_visibility(role, token):
        """Show/hide users tab based on user role."""
        # Guard: Skip if not logged in (prevents execution after logout)
        if not token:
            return {"display": "none"}

        if role == "SUPERADMIN":
            return {"display": "block"}
        else:
            return {"display": "none"}

    @app.callback(
        Output("status-tab-li", "style"),
        [
            Input("role-store", "data"),
            Input("token-store", "data"),
        ],
        prevent_initial_call=False,  # Allow initial call to show status tab on dashboard load
    )
    def toggle_status_tab_visibility(role, token):
        """Show/hide status tab based on user role."""
        # Guard: Skip if not logged in (prevents execution after logout)
        if not token:
            return {"display": "none"}

        if role in ["ADMIN", "SUPERADMIN"]:
            return {"display": "block"}
        else:
            return {"display": "none"}

    @app.callback(
        Output("scripts-tab-li", "style"),
        [
            Input("role-store", "data"),
            Input("token-store", "data"),
        ],
        prevent_initial_call=False,  # Allow initial call to show scripts tab on dashboard load
    )
    def toggle_scripts_tab_visibility(role, token):
        """Show/hide scripts tab based on user role."""
        # Guard: Skip if not logged in (prevents execution after logout)
        if not token:
            return {"display": "none"}

        if role in ["ADMIN", "SUPERADMIN"]:
            return {"display": "block"}
        else:
            return {"display": "none"}

    @app.callback(
        [
            Output("executions-tab-btn", "className"),
            Output("users-tab-btn", "className"),
            Output("scripts-tab-btn", "className"),
            Output("admin-tab-btn", "className"),
            Output("status-tab-btn", "className"),
            Output("profile-tab-btn", "className"),
            Output("active-tab-store", "data"),
        ],
        [
            Input("executions-tab-btn", "n_clicks"),
            Input("users-tab-btn", "n_clicks"),
            Input("scripts-tab-btn", "n_clicks"),
            Input("admin-tab-btn", "n_clicks"),
            Input("status-tab-btn", "n_clicks"),
            Input("profile-tab-btn", "n_clicks"),
        ],
        prevent_initial_call=False,  # Allow initial call to set default tab
    )
    def switch_tabs(
        _exec_clicks, _users_clicks, _scripts_clicks, _admin_clicks, _status_clicks, _profile_clicks
    ):
        """Handle tab switching by updating button classes and active tab store."""
        ctx = callback_context
        if not ctx.triggered:
            # Set default tab when no user interaction yet
            return (
                "nav-link active",
                "nav-link",
                "nav-link",
                "nav-link",
                "nav-link",
                "nav-link",
                "executions",
            )

        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

        # Define tab mapping
        tab_map = {
            "executions-tab-btn": "executions",
            "users-tab-btn": "users",
            "scripts-tab-btn": "scripts",
            "admin-tab-btn": "admin",
            "status-tab-btn": "status",
            "profile-tab-btn": "profile",
        }

        # Get the active tab
        active_tab = tab_map.get(trigger_id, "executions")

        # Set classes - active tab gets "nav-link active", others get "nav-link"
        classes = []
        for btn_id in [
            "executions-tab-btn",
            "users-tab-btn",
            "scripts-tab-btn",
            "admin-tab-btn",
            "status-tab-btn",
            "profile-tab-btn",
        ]:
            if btn_id == trigger_id:
                classes.append("nav-link active")
            else:
                classes.append("nav-link")

        print(f"🔄 Tab switched to: {active_tab}")

        return classes[0], classes[1], classes[2], classes[3], classes[4], classes[5], active_tab
