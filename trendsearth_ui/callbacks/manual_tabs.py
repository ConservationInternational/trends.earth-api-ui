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
        Output("active-tab-store", "data"),
        [
            Input("executions-tab-btn", "n_clicks"),
            Input("users-tab-btn", "n_clicks"),
            Input("scripts-tab-btn", "n_clicks"),
            Input("admin-tab-btn", "n_clicks"),
            Input("status-tab-btn", "n_clicks"),
            Input("profile-tab-btn", "n_clicks"),
            Input("bulk-email-tab-btn", "n_clicks"),
        ],
        prevent_initial_call=True,  # Only react to real clicks; never overwrite persisted tab
    )
    def switch_tabs(*clicks):
        """Handle tab switching by updating the active tab store from a real click."""
        from dash import no_update

        # Guard: when the tab buttons first mount (they live inside dashboard_layout,
        # which is inserted dynamically after login), Dash treats every n_clicks going
        # from undefined to 0 as a simultaneous "change" and still invokes this callback
        # despite prevent_initial_call=True. Without this guard, ctx.triggered[0] would
        # arbitrarily pick the first button in the list (executions-tab-btn) and clobber
        # whatever tab was persisted in active-tab-store. Only proceed on a real click.
        if not any(clicks):
            return no_update

        ctx = callback_context
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

        active_tab = tab_map.get(trigger_id, "executions")
        logger.debug("Tab switched to: %s", active_tab)
        return active_tab

    @app.callback(
        [
            Output("executions-tab-btn", "className"),
            Output("users-tab-btn", "className"),
            Output("scripts-tab-btn", "className"),
            Output("admin-tab-btn", "className"),
            Output("status-tab-btn", "className"),
            Output("profile-tab-btn", "className"),
            Output("bulk-email-tab-btn", "className"),
        ],
        [
            Input("active-tab-store", "data"),
            Input("token-store", "data"),
        ],
        prevent_initial_call=False,
    )
    def sync_nav_highlight(active_tab, _token):
        """Set nav highlighting purely from the store's value (Input, not State), so it
        reacts correctly whether the store was just written by a real click or restored
        from persisted (session/local) storage on page load.

        token-store is included as a second Input purely to delay this callback's
        initial dispatch the same way render_tab is delayed: active-tab-store already
        exists in the static layout, so a callback depending on it alone fires in the
        earliest dispatch batch, before the Store's client-side localStorage hydration
        has necessarily completed. token-store is only populated later (after an async
        cookie round-trip), so waiting on it too guarantees hydration has already landed.
        """
        active_tab = active_tab or "executions"
        return tuple(
            "nav-link active" if tab == active_tab else "nav-link"
            for tab in [
                "executions",
                "users",
                "scripts",
                "admin",
                "status",
                "profile",
                "bulk-email",
            ]
        )
