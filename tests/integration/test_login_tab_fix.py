"""
Comprehensive test to verify the tab display fix after login
"""

import dash
from dash import Input, Output, State, callback, dcc, html, no_update
import dash_bootstrap_components as dbc
import flask

# Create Flask server and Dash app
server = flask.Flask(__name__)
app = dash.Dash(
    __name__,
    server=server,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)

# Test layout that simulates the real app flow
app.layout = dbc.Container(
    [
        html.H1("🔍 Login Flow & Tab Display Test"),
        # Simulate authentication area
        dbc.Card(
            [
                dbc.CardBody(
                    [
                        html.H4("Authentication Status"),
                        html.Div(id="auth-status"),
                        dbc.Button("Simulate Login", id="simulate-login", color="success"),
                        dbc.Button(
                            "Simulate Logout",
                            id="simulate-logout",
                            color="danger",
                            className="ms-2",
                        ),
                    ]
                )
            ],
            className="mb-3",
        ),
        # Main page content area
        html.Div(id="page-content"),
        # Stores (simulating the real app)
        dcc.Store(id="token-store"),
        dcc.Store(id="role-store"),
        dcc.Store(id="user-store"),
        dcc.Store(id="scripts-raw-data"),
        dcc.Store(id="users-raw-data"),
    ],
    fluid=True,
)


def create_dashboard_layout():
    """Simulate the dashboard layout."""
    return [
        html.H3("Dashboard (After Login)"),
        dbc.Alert(id="alert", is_open=False),
        dbc.Collapse(
            dbc.Tabs(
                [
                    dbc.Tab(label="Executions", tab_id="executions"),
                    dbc.Tab(label="Users", tab_id="users"),
                    dbc.Tab(label="Scripts", tab_id="scripts"),
                    dbc.Tab(label="Status", tab_id="status"),
                    dbc.Tab(label="Profile", tab_id="profile"),
                ],
                id="tabs",
                active_tab="executions",
            ),
            id="main-panel",
            is_open=True,
        ),
        html.Div(id="tab-content"),
        html.Hr(),
        html.Div(id="debug-info"),
    ]


def create_login_layout():
    """Simulate the login layout."""
    return html.Div(
        [
            html.H3("Login Page"),
            html.P("Click 'Simulate Login' to test the dashboard display."),
        ]
    )


# Simulate the auth callback
@app.callback(
    Output("page-content", "children"),
    Output("auth-status", "children"),
    Input("token-store", "data"),
)
def display_page(token):
    """Display login or dashboard based on authentication status."""
    if not token:
        return create_login_layout(), "❌ Not logged in"
    return create_dashboard_layout(), "✅ Logged in successfully"


# Simulate the login/logout actions
@app.callback(
    Output("token-store", "data"),
    Output("role-store", "data"),
    Output("user-store", "data"),
    Input("simulate-login", "n_clicks"),
    Input("simulate-logout", "n_clicks"),
)
def handle_auth(login_clicks, logout_clicks):
    """Handle simulated authentication."""
    ctx = dash.callback_context
    if not ctx.triggered:
        return None, None, None

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger_id == "simulate-login":
        return "fake-token-123", "USER", {"email": "test@example.com", "name": "Test User"}
    elif trigger_id == "simulate-logout":
        return None, None, None

    return None, None, None


# The FIXED tab callback (without prevent_initial_call=True)
@app.callback(
    Output("tab-content", "children"),
    Output("scripts-raw-data", "data"),
    Output("users-raw-data", "data"),
    Output("debug-info", "children"),
    Input("tabs", "active_tab"),
    State("token-store", "data"),
    State("role-store", "data"),
    State("user-store", "data"),
    # NOTE: No prevent_initial_call=True - this is the key fix!
)
def render_tab(tab, token, role, user_data):
    """Render the content for the active tab."""
    debug_info = [
        html.H5("Debug Info:"),
        html.P(f"Active tab: {tab}"),
        html.P(f"Token: {bool(token)}"),
        html.P(f"Role: {role}"),
        html.P(f"User data: {bool(user_data)}"),
    ]

    if not token:
        return html.Div("Please login to view content."), [], [], debug_info

    # Set default tab if none provided
    if not tab:
        tab = "executions"

    # Handle case where role might not be set yet
    is_admin = (role == "ADMIN") if role else False  # noqa: F841

    if tab == "executions":
        content = html.Div(
            [
                html.H4("✅ Executions Tab Content"),
                html.P("This should be visible immediately after login!"),
                dbc.Table(
                    [
                        html.Thead(
                            [
                                html.Tr(
                                    [
                                        html.Th("Script Name"),
                                        html.Th("Status"),
                                        html.Th("User"),
                                    ]
                                )
                            ]
                        ),
                        html.Tbody(
                            [
                                html.Tr(
                                    [
                                        html.Td("Sample Script"),
                                        html.Td("FINISHED"),
                                        html.Td("test@example.com"),
                                    ]
                                )
                            ]
                        ),
                    ]
                ),
            ]
        )
    elif tab == "profile":
        user_email = user_data.get("email", "Unknown") if user_data else "Unknown"
        content = html.Div(
            [
                html.H4("Profile Tab Content"),
                html.P(f"User: {user_email}"),
            ]
        )
    else:
        content = html.Div(
            [
                html.H4(f"{tab.title()} Tab Content"),
                html.P(f"Content for the {tab} tab."),
            ]
        )

    return content, [], [], debug_info


if __name__ == "__main__":
    print("🚀 Testing login flow and tab display...")
    print("📋 Steps to test:")
    print("1. Open http://127.0.0.1:8052")
    print("2. Click 'Simulate Login'")
    print("3. Check if you see the dashboard with tabs AND the executions content")
    print("4. If you see both tabs and content, the fix works!")
    app.run(debug=True, host="127.0.0.1", port=8052)
