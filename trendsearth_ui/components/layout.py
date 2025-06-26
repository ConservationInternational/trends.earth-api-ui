"""Base layout components for the Trends.Earth API Dashboard."""

from dash import dcc, html
import dash_bootstrap_components as dbc

from ..config import APP_TITLE, LOGO_HEIGHT, LOGO_URL
from .modals import edit_script_modal, edit_user_modal, json_modal, map_modal


def create_main_layout():
    """Create the main application layout with all stores and modals."""
    return dbc.Container(
        [
            html.H1(APP_TITLE),
            html.Div(id="page-content"),
            # URL component for navigation tracking
            dcc.Location(id="url", refresh=False),
            # Data stores
            dcc.Store(id="token-store"),
            dcc.Store(id="role-store"),
            dcc.Store(id="user-store"),
            dcc.Store(id="json-modal-data"),
            dcc.Store(id="scripts-raw-data"),
            dcc.Store(id="users-raw-data"),
            dcc.Store(id="current-log-context"),
            dcc.Store(id="edit-user-data"),
            dcc.Store(id="edit-script-data"),
            # Modals
            json_modal(),
            edit_user_modal(),
            edit_script_modal(),
            map_modal(),
        ],
        fluid=True,
    )


def login_layout():
    """Create the login page layout."""
    return dbc.Row(
        [
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader(
                            html.Div(
                                [
                                    html.Img(
                                        src=LOGO_URL,
                                        alt="Trends.Earth Logo",
                                        style={"height": LOGO_HEIGHT, "marginBottom": "15px"},
                                    ),
                                    html.H4("Login"),
                                ],
                                className="text-center",
                            )
                        ),
                        dbc.CardBody(
                            [
                                dbc.Form(
                                    [
                                        dbc.Row(
                                            [
                                                dbc.Label("Email", width=3),
                                                dbc.Col(
                                                    dbc.Input(
                                                        id="login-email",
                                                        type="email",
                                                        placeholder="Enter email",
                                                    ),
                                                    width=9,
                                                ),
                                            ],
                                            className="mb-3",
                                        ),
                                        dbc.Row(
                                            [
                                                dbc.Label("Password", width=3),
                                                dbc.Col(
                                                    dbc.Input(
                                                        id="login-password",
                                                        type="password",
                                                        placeholder="Enter password",
                                                    ),
                                                    width=9,
                                                ),
                                            ],
                                            className="mb-3",
                                        ),
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    dbc.Checkbox(
                                                        id="remember-me-checkbox",
                                                        label="Remember me for 6 hours",
                                                        value=True,
                                                    ),
                                                    width=12,
                                                ),
                                            ],
                                            className="mb-3",
                                        ),
                                        dbc.Button(
                                            "Login",
                                            id="login-btn",
                                            color="primary",
                                            className="mt-2",
                                            n_clicks=0,
                                            style={"width": "100%"},
                                        ),
                                        html.Div(
                                            id="login-feedback",
                                            style={"margin-top": "10px", "min-height": "20px"},
                                        ),
                                    ]
                                ),
                                html.Hr(),
                                dbc.Alert(
                                    id="login-alert",
                                    is_open=False,
                                    dismissable=True,
                                    duration=4000,
                                ),
                            ]
                        ),
                    ],
                    style={"maxWidth": "400px"},
                ),
                width=6,
                className="mx-auto mt-4",
            ),
        ]
    )


def dashboard_layout():
    """Create the main dashboard layout."""
    return [
        dbc.Alert(
            id="alert",
            is_open=False,
            dismissable=True,
            duration=4000,
        ),
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
                active_tab="executions",  # Default to executions
            ),
            id="main-panel",
            is_open=True,
        ),
        html.Div(id="tab-content"),
    ]
