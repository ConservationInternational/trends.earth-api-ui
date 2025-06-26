"""
Offline test version of the app to isolate network-related hanging issues.
This version disables external API calls and uses mock data.
"""

import dash
from dash import Input, Output, State, dcc, html
import dash_bootstrap_components as dbc
import flask

from trendsearth_ui.components import login_layout

# Create server and app
server = flask.Flask(__name__)
app = dash.Dash(
    __name__,
    server=server,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)

app.title = "Trends.Earth API Dashboard - Offline Test"


@server.route("/health")
def health_check():
    return {"status": "healthy"}, 200


# Simple offline layout
def offline_dashboard():
    return [
        dbc.Alert("Running in offline mode - API calls disabled", color="warning"),
        html.H2("Dashboard"),
        html.P("This is a test version running without external API calls."),
        dbc.Button("Test Button", id="test-btn", color="primary"),
        html.Div(id="test-output"),
    ]


# Main layout
app.layout = dbc.Container(
    [
        html.H1("Trends.Earth API Dashboard - Offline Test"),
        html.Div(id="page-content"),
        dcc.Store(id="token-store"),
        dcc.Store(id="role-store"),
        dcc.Store(id="user-store"),
    ],
    fluid=True,
)


# Simple callbacks without API calls
@app.callback(
    Output("page-content", "children"),
    Input("token-store", "data"),
)
def display_page(token):
    """Display login or offline dashboard."""
    if not token:
        return login_layout()
    return offline_dashboard()


@app.callback(
    Output("test-output", "children"),
    Input("test-btn", "n_clicks"),
    prevent_initial_call=True,
)
def handle_button_click(n_clicks):
    """Test callback that doesn't make API calls."""
    return f"Button clicked {n_clicks} times!"


# Mock login (no API call)
@app.callback(
    Output("token-store", "data"),
    Output("role-store", "data"),
    Output("user-store", "data"),
    Output("login-alert", "children"),
    Output("login-alert", "color"),
    Output("login-alert", "is_open"),
    Input("login-btn", "n_clicks"),
    State("login-email", "value"),
    State("login-password", "value"),
    prevent_initial_call=True,
)
def mock_login(_n, email, password):
    """Mock login without API calls."""
    if not email or not password:
        return None, None, None, "Please enter both email and password.", "warning", True

    # Mock successful login
    mock_token = "mock_token_123"
    mock_role = "ADMIN"
    mock_user = {"email": email, "role": "ADMIN", "name": "Test User"}

    return mock_token, mock_role, mock_user, "Mock login successful!", "success", True


def main():
    """Main entry point for offline test."""
    print("Starting Offline Test App...")
    print("This version disables API calls to test if network issues cause hanging.")
    print("Access the app at: http://127.0.0.1:8052")
    app.run(debug=True, host="127.0.0.1", port=8052)


if __name__ == "__main__":
    main()
