"""
Test script to debug the tab display issue after login
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

# Simple test layout mimicking the dashboard structure
app.layout = dbc.Container(
    [
        html.H1("🔍 Tab Display Issue Test"),
        # Simulate the dashboard layout
        html.Div(
            [
                html.H3("Dashboard Layout:"),
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
            ],
            id="dashboard-content",
        ),
        html.Hr(),
        html.Div(id="debug-info"),
        # Simulate stores
        dcc.Store(id="token-store", data="fake-token"),
        dcc.Store(id="role-store", data="USER"),
        dcc.Store(id="user-store", data={"email": "test@example.com"}),
    ],
    fluid=True,
)


# Test callback WITHOUT prevent_initial_call
@app.callback(
    Output("tab-content", "children"),
    Input("tabs", "active_tab"),
    State("token-store", "data"),
    State("role-store", "data"),
    State("user-store", "data"),
    # NOTE: No prevent_initial_call=True here!
)
def render_tab(tab, token, role, user_data):
    """Render the content for the active tab."""
    if not token:
        return html.Div("Please login to view content.")

    if not tab:
        return html.Div("Loading...")

    if tab == "executions":
        return html.Div(
            [
                html.H4("Executions Tab Content"),
                html.P("This is the executions tab - it should be visible by default!"),
            ]
        )
    elif tab == "users":
        return html.Div(
            [
                html.H4("Users Tab Content"),
                html.P("This is the users tab content."),
            ]
        )
    # Add other tabs as needed
    else:
        return html.Div(f"Content for {tab} tab")


# Debug callback to show what's happening
@app.callback(
    Output("debug-info", "children"),
    Input("tabs", "active_tab"),
    State("token-store", "data"),
)
def debug_info(active_tab, token):
    return html.Div(
        [
            html.H4("Debug Info:"),
            html.P(f"Active tab: {active_tab}"),
            html.P(f"Token exists: {bool(token)}"),
            html.P(
                "If you see the tabs above but no content below them, then the issue is with prevent_initial_call=True in the tabs callback."
            ),
        ]
    )


if __name__ == "__main__":
    print("Testing tab display issue...")
    print("Open http://127.0.0.1:8051 to see the test")
    app.run(debug=True, host="127.0.0.1", port=8051)
