"""Manual tab switching callbacks to replace dbc.Tabs functionality."""

from dash import Input, Output, callback_context, no_update


def register_callbacks(app):
    """Register manual tab switching callbacks."""

    @app.callback(
        [
            Output("executions-tab-btn", "className"),
            Output("users-tab-btn", "className"),
            Output("scripts-tab-btn", "className"),
            Output("status-tab-btn", "className"),
            Output("profile-tab-btn", "className"),
            Output("active-tab-store", "data"),
        ],
        [
            Input("executions-tab-btn", "n_clicks"),
            Input("users-tab-btn", "n_clicks"),
            Input("scripts-tab-btn", "n_clicks"),
            Input("status-tab-btn", "n_clicks"),
            Input("profile-tab-btn", "n_clicks"),
        ],
        prevent_initial_call=True,
    )
    def switch_tabs(exec_clicks, users_clicks, scripts_clicks, status_clicks, profile_clicks):  # noqa: ARG001
        """Handle tab switching by updating button classes and active tab store."""
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update, no_update, no_update, no_update

        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

        # Define tab mapping
        tab_map = {
            "executions-tab-btn": "executions",
            "users-tab-btn": "users",
            "scripts-tab-btn": "scripts",
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
            "status-tab-btn",
            "profile-tab-btn",
        ]:
            if btn_id == trigger_id:
                classes.append("nav-link active")
            else:
                classes.append("nav-link")

        print(f"🔄 Tab switched to: {active_tab}")

        return classes[0], classes[1], classes[2], classes[3], classes[4], active_tab
