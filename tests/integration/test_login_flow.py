"""
Test script to simulate login process and check for issues
"""

import os
import sys

import dash
from dash import html
import dash_bootstrap_components as dbc

from trendsearth_ui.callbacks.auth import register_callbacks
from trendsearth_ui.components.layout import login_layout

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Create a minimal test app
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)

# Set up layout with login form
app.layout = html.Div(
    [
        html.H1("Login Test"),
        login_layout(),
        html.Div(
            id="debug-info",
            style={"margin-top": "20px", "padding": "10px", "background-color": "#f0f0f0"},
        ),
    ]
)

# Register the auth callbacks
try:
    register_callbacks(app)
    print("✅ Auth callbacks registered successfully")
except Exception as e:
    print(f"❌ Error registering callbacks: {e}")
    import traceback

    traceback.print_exc()


# Add a debug callback
@app.callback(
    dash.Output("debug-info", "children"),
    dash.Input("login-btn", "n_clicks"),
    prevent_initial_call=True,
)
def debug_info(n_clicks):
    """Debug callback to show button clicks."""
    return f"Login button clicked {n_clicks} times. Check console for auth callback output."


if __name__ == "__main__":
    print("🚀 Starting Login Test App...")
    print("📱 Access at: http://127.0.0.1:8053")
    print("🔍 Try logging in and check both browser and console output")
    app.run(debug=True, host="127.0.0.1", port=8053)
