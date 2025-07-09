"""Base layout components for the Trends.Earth API Dashboard."""

from dash import dcc, html
import dash_bootstrap_components as dbc

from ..callbacks.timezone import get_timezone_components
from ..config import APP_TITLE, LOGO_HEIGHT, LOGO_SQUARE_URL, LOGO_URL
from .modals import (
    delete_script_modal,
    delete_user_modal,
    edit_script_modal,
    edit_user_modal,
    json_modal,
    map_modal,
)


def create_main_layout():
    """Create the main application layout with all stores and modals."""
    # Get timezone detection components
    timezone_components = get_timezone_components()

    return dbc.Container(
        [
            html.Div(id="page-content"),
            html.Div(id="tab-content"),
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
            dcc.Store(
                id="executions-table-state"
            ),  # Store current sort/filter state for executions table
            dcc.Store(id="users-table-state"),  # Store current sort/filter state for users table
            dcc.Store(
                id="scripts-table-state"
            ),  # Store current sort/filter state for scripts table
            dcc.Store(
                id="executions-total-count-store", data=0
            ),  # Store total count for executions
            dcc.Store(id="users-total-count-store", data=0),  # Store total count for users
            dcc.Store(id="scripts-total-count-store", data=0),  # Store total count for scripts
            dcc.Store(id="active-tab-store", data="executions"),
            dcc.Store(id="delete-user-data"),  # Store data for user being deleted
            dcc.Store(id="delete-script-data"),  # Store data for script being deleted
            # Timezone detection components
            *timezone_components,
            # Modals
            json_modal(),
            edit_user_modal(),
            edit_script_modal(),
            map_modal(),
            delete_user_modal(),
            delete_script_modal(),
        ],
        fluid=True,
    )


def login_layout():
    """Create the login page layout."""
    return html.Div(
        [
            # Hidden store to prevent callback errors
            dcc.Store(id="active-tab-store", data=None, storage_type="memory"),
            dbc.Row(
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
                                                style={
                                                    "height": LOGO_HEIGHT,
                                                    "marginBottom": "15px",
                                                },
                                            ),
                                            html.H4("Login", style={"color": "white"}),
                                        ],
                                        className="text-center",
                                    ),
                                    style={"backgroundColor": "#495057"},
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
                                                                label="Remember me for 12 hours",
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
                                                    style={
                                                        "margin-top": "10px",
                                                        "min-height": "20px",
                                                    },
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
            ),
        ]
    )


def dashboard_layout():
    """Create the main dashboard layout."""
    layout = [
        # Top header with logout button
        dbc.Navbar(
            dbc.Container(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Img(
                                        src=LOGO_SQUARE_URL,
                                        height="40px",
                                        className="me-2",
                                    ),
                                    dbc.NavbarBrand(
                                        APP_TITLE,
                                        className="fw-bold",
                                    ),
                                ],
                                width="auto",
                            ),
                            dbc.Col(
                                [
                                    html.Div(
                                        [
                                            html.Span(
                                                id="header-user-info",
                                                className="me-3 text-muted",
                                            ),
                                            dbc.Button(
                                                [
                                                    html.I(className="fas fa-sign-out-alt me-2"),
                                                    "Logout",
                                                ],
                                                id="header-logout-btn",
                                                color="outline-secondary",
                                                size="sm",
                                            ),
                                        ],
                                        className="d-flex align-items-center justify-content-end",
                                    )
                                ],
                                width=True,
                            ),
                        ],
                        className="w-100 align-items-center",
                    )
                ],
                fluid=True,
            ),
            color="dark",
            dark=True,
            style={"backgroundColor": "#495057"},
            className="mb-3",
        ),
        dbc.Alert(
            id="alert",
            is_open=False,
            dismissable=True,
            duration=4000,
        ),
        # Collapsible main panel containing the tabs
        dbc.Collapse(
            html.Div(
                [
                    html.Ul(
                        [
                            html.Li(
                                [
                                    html.Button(
                                        "Executions",
                                        id="executions-tab-btn",
                                        className="nav-link active",
                                        **{"data-tab": "executions"},
                                    )
                                ],
                                className="nav-item",
                            ),
                            html.Li(
                                [
                                    html.Button(
                                        "Users",
                                        id="users-tab-btn",
                                        className="nav-link",
                                        **{"data-tab": "users"},
                                    )
                                ],
                                className="nav-item",
                            ),
                            html.Li(
                                [
                                    html.Button(
                                        "Scripts",
                                        id="scripts-tab-btn",
                                        className="nav-link",
                                        **{"data-tab": "scripts"},
                                    )
                                ],
                                className="nav-item",
                            ),
                            html.Li(
                                [
                                    html.Button(
                                        "Admin",
                                        id="admin-tab-btn",
                                        className="nav-link",
                                        **{"data-tab": "admin"},
                                    )
                                ],
                                className="nav-item",
                                id="admin-tab-li",
                                style={"display": "none"},  # Hidden by default
                            ),
                            html.Li(
                                [
                                    html.Button(
                                        "Status",
                                        id="status-tab-btn",
                                        className="nav-link",
                                        **{"data-tab": "status"},
                                    )
                                ],
                                className="nav-item",
                            ),
                            html.Li(
                                [
                                    html.Button(
                                        "Profile",
                                        id="profile-tab-btn",
                                        className="nav-link",
                                        **{"data-tab": "profile"},
                                    )
                                ],
                                className="nav-item",
                            ),
                        ],
                        className="nav nav-tabs",
                        id="tabs-nav",
                    ),
                ]
            ),
            id="main-panel",
            is_open=True,
        ),
        # Hidden store to track active tab
        dcc.Store(id="active-tab-store", data="executions"),
    ]
    print(f"🏗️ Dashboard layout created with {len(layout)} components:")
    for i, component in enumerate(layout):
        print(f"  {i}: {type(component).__name__} - {getattr(component, 'id', 'no id')}")
    return layout
