"""Manual tab switching callbacks to replace dbc.Tabs functionality."""

import logging

from dash import Input, Output, callback_context

from ..utils.helpers import ADMIN_ROLES

logger = logging.getLogger(__name__)

# (output_id, allowed_roles) pairs
_TAB_CONFIGS = [
    ("admin-tab-li", ADMIN_ROLES),
    ("profile-openeo-section", ADMIN_ROLES),
    ("users-tab-li", ADMIN_ROLES),
    ("status-tab-li", ADMIN_ROLES),
    ("scripts-tab-li", ADMIN_ROLES),
    ("bulk-email-tab-li", ("SUPERADMIN",)),
]


def _make_tab_toggle(allowed_roles):
    def toggle(role, token):
        if not token:
            return {"display": "none"}
        return {"display": "block"} if role in allowed_roles else {"display": "none"}

    return toggle


def register_callbacks(app):
    """Register manual tab switching callbacks."""

    for output_id, allowed_roles in _TAB_CONFIGS:
        app.callback(
            Output(output_id, "style"),
            [
                Input("role-store", "data"),
                Input("token-store", "data"),
            ],
            prevent_initial_call=False,
        )(_make_tab_toggle(allowed_roles))

    @app.callback(
        [
            Output("executions-tab-btn", "className"),
            Output("users-tab-btn", "className"),
            Output("scripts-tab-btn", "className"),
            Output("admin-tab-btn", "className"),
            Output("status-tab-btn", "className"),
            Output("profile-tab-btn", "className"),
            Output("bulk-email-tab-btn", "className"),
            Output("active-tab-store", "data"),
        ],
        [
            Input("executions-tab-btn", "n_clicks"),
            Input("users-tab-btn", "n_clicks"),
            Input("scripts-tab-btn", "n_clicks"),
            Input("admin-tab-btn", "n_clicks"),
            Input("status-tab-btn", "n_clicks"),
            Input("profile-tab-btn", "n_clicks"),
            Input("bulk-email-tab-btn", "n_clicks"),
        ],
        prevent_initial_call=False,  # Allow initial call to set default tab
    )
    def switch_tabs(*_clicks):
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
            "bulk-email-tab-btn": "bulk-email",
        }

        # Get the active tab
        active_tab = tab_map.get(trigger_id, "executions")

        # Set classes for nav links
        nav_classes = []
        for btn_id in [
            "executions-tab-btn",
            "users-tab-btn",
            "scripts-tab-btn",
            "admin-tab-btn",
            "status-tab-btn",
            "profile-tab-btn",
            "bulk-email-tab-btn",
        ]:
            tab_key = tab_map[btn_id]
            if tab_key == active_tab:
                nav_classes.append("nav-link active")
            else:
                nav_classes.append("nav-link")

        logger.debug("Tab switched to: %s", active_tab)

        # Return all classes and active tab
        return (
            nav_classes[0],
            nav_classes[1],
            nav_classes[2],
            nav_classes[3],
            nav_classes[4],
            nav_classes[5],
            nav_classes[6],
            active_tab,
        )
