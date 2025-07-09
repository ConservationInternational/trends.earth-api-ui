"""Timezone detection and management callbacks."""

from dash import Input, Output, callback, clientside_callback, dcc, html


def register_callbacks(app):
    """Register timezone-related callbacks with the app."""

    # Clientside callback to detect user's timezone using URL navigation
    try:
        clientside_callback(
            """
            function(pathname) {
                const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
                return userTimezone;
            }
            """,
            Output("user-timezone-store", "data"),
            Input("url", "pathname"),
            prevent_initial_call=False,
            app=app,
        )
    except Exception as e:
        print(f"Error registering timezone clientside callback: {e}")

    @callback(
        Output("timezone-detection-status", "children"),
        Input("user-timezone-store", "data"),
        prevent_initial_call=False,
    )
    def update_timezone_status(timezone_data):
        """Update the timezone detection status."""
        if timezone_data and timezone_data != "UTC":
            # Clear status cache when timezone changes so status updates immediately
            try:
                from . import status

                if hasattr(status, "_status_cache"):
                    status._status_cache["summary"]["data"] = None
                    status._status_cache["charts"]["data"] = {}
            except ImportError:
                pass  # Status module may not be available

        if timezone_data:
            return html.Div(
                [
                    html.Span("✓ ", className="text-success"),
                    html.Span(f"Timezone detected: {timezone_data}", className="text-muted small"),
                ],
                style={"display": "none"},
            )  # Hidden but can be shown for debugging
        return html.Div(
            "Detecting timezone...", className="text-muted small", style={"display": "none"}
        )


def get_timezone_components():
    """Get the timezone detection components to be added to the app layout.

    Returns:
        List of components for timezone detection
    """
    return [
        # Store for user's timezone
        dcc.Store(id="user-timezone-store", data="UTC"),
        # Status indicator (hidden by default)
        html.Div(id="timezone-detection-status", style={"display": "none"}),
    ]
