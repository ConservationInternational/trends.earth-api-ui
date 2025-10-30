"""Base layout components for the Trends.Earth API Dashboard."""

from dash import dcc, html
import dash_bootstrap_components as dbc

from ..callbacks.timezone import get_timezone_components
from ..config import (
    API_ENVIRONMENTS,
    APP_TITLE,
    DEFAULT_API_ENVIRONMENT,
    LOGO_HEIGHT,
    LOGO_SQUARE_URL,
    LOGO_URL,
)
from ..utils.mobile_utils import create_mobile_detection_components
from .modals import (
    access_control_modal,
    delete_script_modal,
    delete_user_modal,
    edit_script_modal,
    edit_user_modal,
    json_modal,
    map_modal,
    reset_rate_limits_modal,
)


def create_main_layout():
    """Create the main application layout with all stores and modals."""
    # Get timezone detection components
    timezone_components = get_timezone_components()

    # Get mobile detection components
    mobile_components = create_mobile_detection_components()

    return dbc.Container(
        [
            html.Div(id="page-content", children=login_layout()),
            html.Div(id="tab-content"),
            # URL component for navigation tracking
            dcc.Location(id="url", refresh=False),
            # Data stores
            dcc.Store(id="token-store"),
            dcc.Store(id="role-store"),
            dcc.Store(id="user-store"),
            dcc.Store(id="api-environment-store", data=DEFAULT_API_ENVIRONMENT),
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
            # Mobile detection components
            *mobile_components,
            # Modals
            json_modal(),
            edit_user_modal(),
            edit_script_modal(),
            access_control_modal(),
            map_modal(),
            delete_user_modal(),
            delete_script_modal(),
            reset_rate_limits_modal(),
        ],
        fluid=True,
    )


def login_layout():
    """Create the login page layout."""
    return html.Div(
        [
            # Stores are defined globally in the main layout; avoid duplicates here
            # Forgot password modal
            dbc.Modal(
                [
                    dbc.ModalHeader(
                        dbc.ModalTitle("Forgot Password"),
                        close_button=True,
                    ),
                    dbc.ModalBody(
                        [
                            # Form section (visible initially)
                            html.Div(
                                [
                                    html.P(
                                        "Enter your email address and we'll send you instructions to reset your password."
                                    ),
                                    dbc.Label("Email Address"),
                                    dbc.Input(
                                        id="forgot-password-email",
                                        type="email",
                                        placeholder="Enter your email address",
                                        className="mb-3",
                                    ),
                                ],
                                id="forgot-password-form",
                                style={"display": "block"},
                            ),
                            # Alert section (for messages)
                            dbc.Alert(
                                id="forgot-password-alert",
                                is_open=False,
                                dismissable=False,  # Don't allow dismissing
                                duration=None,  # Don't auto-dismiss
                            ),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            # Initial buttons (visible initially)
                            html.Div(
                                [
                                    dbc.Button(
                                        "Cancel",
                                        id="cancel-forgot-password",
                                        color="secondary",
                                        className="me-2",
                                    ),
                                    dbc.Button(
                                        "Send Reset Instructions",
                                        id="send-reset-btn",
                                        color="primary",
                                    ),
                                ],
                                id="forgot-password-initial-buttons",
                                style={"display": "block"},
                            ),
                            # Success button (hidden initially)
                            html.Div(
                                [
                                    dbc.Button(
                                        "OK",
                                        id="forgot-password-ok-btn",
                                        color="primary",
                                    ),
                                ],
                                id="forgot-password-success-buttons",
                                style={"display": "none"},
                            ),
                        ]
                    ),
                ],
                id="forgot-password-modal",
                is_open=False,
                centered=True,
                backdrop="static",
            ),
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
                                                        dbc.Label("API Environment", width=3),
                                                        dbc.Col(
                                                            dcc.Dropdown(
                                                                id="api-environment-dropdown",
                                                                options=[
                                                                    {
                                                                        "label": env_config[
                                                                            "display_name"
                                                                        ],
                                                                        "value": env_key,
                                                                    }
                                                                    for env_key, env_config in API_ENVIRONMENTS.items()
                                                                ],
                                                                value=DEFAULT_API_ENVIRONMENT,
                                                                clearable=False,
                                                                style={"fontSize": "14px"},
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
                                                                label="Remember me (keep me logged in)",
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
                                                    [
                                                        html.A(
                                                            "Forgot your password?",
                                                            id="forgot-password-link",
                                                            href="#",
                                                            className="text-primary",
                                                            style={
                                                                "textDecoration": "none",
                                                                "fontSize": "14px",
                                                            },
                                                        ),
                                                    ],
                                                    className="text-center mt-3",
                                                ),
                                                html.Div(
                                                    id="login-feedback",
                                                    style={
                                                        "marginTop": "10px",
                                                        "minHeight": "20px",
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
                                    html.Div(
                                        [
                                            html.Img(
                                                src=LOGO_SQUARE_URL,
                                                height="40px",
                                                className="me-2",
                                            ),
                                            dbc.NavbarBrand(
                                                APP_TITLE,
                                                className="fw-bold me-3",
                                            ),
                                            html.Div(
                                                id="environment-indicator",
                                                style={
                                                    "fontSize": "12px",
                                                    "color": "white",
                                                    "display": "flex",
                                                    "flexDirection": "column",
                                                    "alignItems": "flex-start",
                                                    "gap": "1px",
                                                },
                                            ),
                                        ],
                                        className="d-flex align-items-center",
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
            style={
                "backgroundColor": "#495057",
                "width": "100vw",
                "marginLeft": "calc(-50vw + 50%)",
                "marginRight": "calc(-50vw + 50%)",
            },
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
                    # Navigation tabs - responsive design with Bootstrap classes
                    html.Ul(
                        [
                            html.Li(
                                [
                                    html.Button(
                                        "Executions",
                                        id="executions-tab-btn",
                                        className="nav-link active",
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
                                    )
                                ],
                                className="nav-item",
                                id="users-tab-li",
                                style={
                                    "display": "none"
                                },  # Hidden by default, shown only for admin
                            ),
                            html.Li(
                                [
                                    html.Button(
                                        "Scripts",
                                        id="scripts-tab-btn",
                                        className="nav-link",
                                    )
                                ],
                                className="nav-item",
                                id="scripts-tab-li",
                                style={
                                    "display": "none"
                                },  # Hidden by default, shown only for admin
                            ),
                            html.Li(
                                [
                                    html.Button(
                                        "Admin",
                                        id="admin-tab-btn",
                                        className="nav-link",
                                    )
                                ],
                                className="nav-item",
                                id="admin-tab-li",
                                style={
                                    "display": "none"
                                },  # Hidden by default, shown only for admin
                            ),
                            html.Li(
                                [
                                    html.Button(
                                        "Status",
                                        id="status-tab-btn",
                                        className="nav-link",
                                    )
                                ],
                                className="nav-item",
                                id="status-tab-li",
                                style={
                                    "display": "none"
                                },  # Hidden by default, shown only for admin
                            ),
                            html.Li(
                                [
                                    html.Button(
                                        "Profile",
                                        id="profile-tab-btn",
                                        className="nav-link",
                                    )
                                ],
                                className="nav-item",
                            ),
                        ],
                        id="tabs-nav",
                        className="nav nav-tabs",
                        style={"flexWrap": "wrap"},
                    ),
                    # Tab content will be inserted here by callbacks
                    html.Div(id="tab-content-dynamic"),
                ],
                **{"data-testid": "dashboard-content"},
            ),
            id="main-panel",
            is_open=True,
        ),
        # Hidden stores are defined globally in the main layout; avoid duplicates here
        # Proactive token refresh interval (every 5 minutes)
        dcc.Interval(
            id="token-refresh-interval",
            interval=5 * 60 * 1000,  # 5 minutes in milliseconds
            n_intervals=0,
        ),
    ]
    print(f"🏗️ Dashboard layout created with {len(layout)} components:")
    for i, component in enumerate(layout):
        print(f"  {i}: {type(component).__name__} - {getattr(component, 'id', 'no id')}")
    return layout
