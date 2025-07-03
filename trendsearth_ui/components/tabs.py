"""Tab content components for different sections of the dashboard."""

from dash import dcc, html
import dash_ag_grid as dag
import dash_bootstrap_components as dbc

from ..config import DEFAULT_PAGE_SIZE, EXECUTIONS_REFRESH_INTERVAL, STATUS_REFRESH_INTERVAL


def executions_tab_content():
    """Create the executions tab content."""
    column_defs = [
        {"headerName": "Script Name", "field": "script_name"},
        {"headerName": "User Name", "field": "user_name"},
        {"headerName": "Status", "field": "status"},
        {"headerName": "Start Date", "field": "start_date", "filter": "agDateColumnFilter"},
        {"headerName": "End Date", "field": "end_date", "filter": "agDateColumnFilter"},
        {"headerName": "Progress", "field": "progress"},
        {"headerName": "ID", "field": "id"},
        {"headerName": "Params", "field": "params", "sortable": False, "filter": False},
        {"headerName": "Results", "field": "results", "sortable": False, "filter": False},
        {"headerName": "Logs", "field": "logs", "sortable": False, "filter": False},
        {"headerName": "Map", "field": "map", "sortable": False, "filter": False},
    ]

    style_data_conditional = [
        {"condition": "params.data.status === 'FAILED'", "style": {"backgroundColor": "#F8D7DA"}},
        {"condition": "params.data.status === 'FINISHED'", "style": {"backgroundColor": "#D1E7DD"}},
        {"condition": "params.data.status === 'RUNNING'", "style": {"backgroundColor": "#CCE5FF"}},
    ]

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Button(
                                "Refresh Executions",
                                id="refresh-executions-btn",
                                color="primary",
                                className="mb-3",
                            ),
                        ],
                        width="auto",
                    ),
                    dbc.Col(
                        [
                            html.Div(
                                [
                                    html.Span("Auto-refresh in: ", className="me-2"),
                                    html.Span(
                                        id="executions-countdown",
                                        children="30s",
                                        className="badge bg-secondary",
                                    ),
                                ],
                                className="d-flex align-items-center",
                            )
                        ],
                        width="auto",
                    ),
                    dbc.Col(
                        [
                            html.Div(
                                [
                                    html.Span(
                                        id="executions-total-count",
                                        children="Total: 0",
                                        className="text-muted fw-bold",
                                    ),
                                ],
                                className="d-flex align-items-center justify-content-end",
                            )
                        ],
                        width=True,
                    ),
                ],
                className="justify-content-between",
            ),
            dag.AgGrid(
                id="executions-table",
                columnDefs=column_defs,
                defaultColDef={"resizable": True, "sortable": True, "filter": True},
                columnSize="sizeToFit",
                rowModelType="infinite",
                dashGridOptions={
                    "cacheBlockSize": DEFAULT_PAGE_SIZE,
                    "maxBlocksInCache": 2,
                    "blockLoadDebounceMillis": 500,
                    "purgeClosedRowNodes": True,
                    "maxConcurrentDatasourceRequests": 1,
                },
                getRowStyle={"styleConditions": style_data_conditional},
                style={"height": "800px"},
            ),
            dcc.Interval(
                id="executions-auto-refresh-interval",
                interval=EXECUTIONS_REFRESH_INTERVAL,
                n_intervals=0,
            ),
            dcc.Interval(
                id="executions-countdown-interval",
                interval=1000,  # 1 second for countdown
                n_intervals=0,
            ),
        ]
    )


def users_tab_content():
    """Create the users tab content."""
    column_defs = [
        {"headerName": "Email", "field": "email"},
        {"headerName": "Name", "field": "name"},
        {"headerName": "Institution", "field": "institution"},
        {"headerName": "Country", "field": "country"},
        {"headerName": "Role", "field": "role"},
        {"headerName": "Created At", "field": "created_at", "filter": "agDateColumnFilter"},
        {"headerName": "Updated At", "field": "updated_at", "filter": "agDateColumnFilter"},
        {"headerName": "ID", "field": "id"},
        {"headerName": "Edit", "field": "edit", "sortable": False, "filter": False},
    ]

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Button(
                                "Refresh Users",
                                id="refresh-users-btn",
                                color="primary",
                                className="mb-3",
                            ),
                        ],
                        width="auto",
                    ),
                    dbc.Col(
                        [
                            html.Div(
                                [
                                    html.Span(
                                        id="users-total-count",
                                        children="Total: 0",
                                        className="text-muted fw-bold",
                                    ),
                                ],
                                className="d-flex align-items-center justify-content-end",
                            )
                        ],
                        width=True,
                    ),
                ]
            ),
            dag.AgGrid(
                id="users-table",
                columnDefs=column_defs,
                defaultColDef={"resizable": True, "sortable": True, "filter": True},
                columnSize="sizeToFit",
                rowModelType="infinite",
                dashGridOptions={
                    "cacheBlockSize": DEFAULT_PAGE_SIZE,
                    "maxBlocksInCache": 2,
                    "blockLoadDebounceMillis": 500,
                    "purgeClosedRowNodes": True,
                    "maxConcurrentDatasourceRequests": 1,
                },
                style={"height": "800px"},
            ),
        ]
    )


def scripts_tab_content():
    """Create the scripts tab content."""
    column_defs = [
        {"headerName": "Script Name", "field": "name"},
        {"headerName": "User Name", "field": "user_name"},
        {"headerName": "Description", "field": "description"},
        {"headerName": "Status", "field": "status"},
        {"headerName": "Created At", "field": "created_at", "filter": "agDateColumnFilter"},
        {"headerName": "Updated At", "field": "updated_at", "filter": "agDateColumnFilter"},
        {"headerName": "ID", "field": "id"},
        {"headerName": "Logs", "field": "logs", "sortable": False, "filter": False},
        {"headerName": "Edit", "field": "edit", "sortable": False, "filter": False},
    ]

    style_data_conditional = [
        {
            "condition": "params.data.status === 'PUBLISHED'",
            "style": {"backgroundColor": "#D1E7DD"},
        },
        {"condition": "params.data.status === 'DRAFT'", "style": {"backgroundColor": "#FFF3CD"}},
        {"condition": "params.data.status === 'ARCHIVED'", "style": {"backgroundColor": "#F8D7DA"}},
    ]

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Button(
                                "Refresh Scripts",
                                id="refresh-scripts-btn",
                                color="primary",
                                className="mb-3",
                            ),
                        ],
                        width="auto",
                    ),
                    dbc.Col(
                        [
                            html.Div(
                                [
                                    html.Span(
                                        id="scripts-total-count",
                                        children="Total: 0",
                                        className="text-muted fw-bold",
                                    ),
                                ],
                                className="d-flex align-items-center justify-content-end",
                            )
                        ],
                        width=True,
                    ),
                ]
            ),
            dag.AgGrid(
                id="scripts-table",
                columnDefs=column_defs,
                defaultColDef={"resizable": True, "sortable": True, "filter": True},
                columnSize="sizeToFit",
                rowModelType="infinite",
                dashGridOptions={
                    "cacheBlockSize": DEFAULT_PAGE_SIZE,
                    "maxBlocksInCache": 2,
                    "blockLoadDebounceMillis": 500,
                    "purgeClosedRowNodes": True,
                    "maxConcurrentDatasourceRequests": 1,
                },
                getRowStyle={"styleConditions": style_data_conditional},
                style={"height": "800px"},
            ),
        ]
    )


def profile_tab_content(user_data):
    """Create the profile tab content."""
    # Get current user data for pre-populating form
    current_name = ""
    current_email = ""
    current_institution = ""
    current_role = ""

    if user_data and isinstance(user_data, dict):
        current_name = user_data.get("name", "")
        current_email = user_data.get("email", "")
        current_institution = user_data.get("institution", "")
        current_role = user_data.get("role", "")

    return html.Div(
        [
            dbc.Card(
                [
                    dbc.CardHeader(html.H4("Profile Settings")),
                    dbc.CardBody(
                        [
                            dbc.Form(
                                [
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Label("Name"),
                                                    dbc.Input(
                                                        id="profile-name",
                                                        type="text",
                                                        placeholder="Enter your name",
                                                        value=current_name,
                                                    ),
                                                ],
                                                width=6,
                                            ),
                                            dbc.Col(
                                                [
                                                    dbc.Label("Email"),
                                                    dbc.Input(
                                                        id="profile-email",
                                                        type="email",
                                                        placeholder="Enter your email",
                                                        value=current_email,
                                                        disabled=True,
                                                    ),
                                                ],
                                                width=6,
                                            ),
                                        ],
                                        className="mb-3",
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Label("Institution"),
                                                    dbc.Input(
                                                        id="profile-institution",
                                                        type="text",
                                                        placeholder="Enter your institution",
                                                        value=current_institution,
                                                    ),
                                                ],
                                                width=6,
                                            ),
                                            dbc.Col(
                                                [
                                                    dbc.Label("Role"),
                                                    dbc.Input(
                                                        id="profile-role",
                                                        type="text",
                                                        disabled=True,
                                                        value=current_role,
                                                    ),
                                                ],
                                                width=6,
                                            ),
                                        ],
                                        className="mb-3",
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Button(
                                                        "Update Profile",
                                                        id="update-profile-btn",
                                                        color="primary",
                                                        className="me-2",
                                                    ),
                                                    dbc.Button(
                                                        "Logout",
                                                        id="logout-btn",
                                                        color="danger",
                                                        className="me-2",
                                                    ),
                                                    dbc.Alert(
                                                        id="profile-update-alert",
                                                        is_open=False,
                                                        dismissable=True,
                                                    ),
                                                ],
                                                width=12,
                                            ),
                                        ],
                                        className="mb-4",
                                    ),
                                ]
                            )
                        ]
                    ),
                ],
                className="mb-4",
            ),
            dbc.Card(
                [
                    dbc.CardHeader(html.H4("Change Password")),
                    dbc.CardBody(
                        [
                            dbc.Form(
                                [
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Label("Current Password"),
                                                    dbc.Input(
                                                        id="current-password",
                                                        type="password",
                                                        placeholder="Enter current password",
                                                    ),
                                                ],
                                                width=12,
                                            ),
                                        ],
                                        className="mb-3",
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Label("New Password"),
                                                    dbc.Input(
                                                        id="new-password",
                                                        type="password",
                                                        placeholder="Enter new password",
                                                    ),
                                                ],
                                                width=6,
                                            ),
                                            dbc.Col(
                                                [
                                                    dbc.Label("Confirm New Password"),
                                                    dbc.Input(
                                                        id="confirm-password",
                                                        type="password",
                                                        placeholder="Confirm new password",
                                                    ),
                                                ],
                                                width=6,
                                            ),
                                        ],
                                        className="mb-3",
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Button(
                                                        "Change Password",
                                                        id="change-password-btn",
                                                        color="secondary",
                                                    ),
                                                    dbc.Alert(
                                                        id="password-change-alert",
                                                        is_open=False,
                                                        dismissable=True,
                                                    ),
                                                ],
                                                width=12,
                                            ),
                                        ]
                                    ),
                                ]
                            )
                        ]
                    ),
                ]
            ),
        ]
    )


def status_tab_content(is_admin):
    """Create the status tab content."""
    if not is_admin:
        return html.Div(
            [
                dbc.Alert(
                    "Access denied. Administrator privileges required to view system status.",
                    color="danger",
                )
            ]
        )

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Button(
                                "Refresh Status",
                                id="refresh-status-btn",
                                color="primary",
                                className="mb-3",
                            ),
                        ],
                        width="auto",
                    ),
                    dbc.Col(
                        [
                            html.Div(
                                [
                                    html.Span("Auto-refresh in: ", className="me-2"),
                                    html.Span(
                                        id="status-countdown",
                                        children="60s",
                                        className="badge bg-secondary",
                                    ),
                                ],
                                className="d-flex align-items-center",
                            )
                        ],
                        width="auto",
                    ),
                ],
                className="justify-content-between",
            ),
            # Status summary card
            dbc.Card(
                [
                    dbc.CardHeader(html.H4("System Status Summary")),
                    dbc.CardBody(
                        [html.Div(id="status-summary", children="Loading system status...")]
                    ),
                ],
                className="mb-4",
            ),
            # Status charts
            dbc.Card(
                [
                    dbc.CardHeader(html.H4("Execution Status Trends")),
                    dbc.CardBody(
                        [
                            dbc.Tabs(
                                [
                                    dbc.Tab(label="Last Hour", tab_id="hour", id="status-tab-hour"),
                                    dbc.Tab(
                                        label="Last 24 Hours", tab_id="day", id="status-tab-day"
                                    ),
                                    dbc.Tab(label="Last Week", tab_id="week", id="status-tab-week"),
                                ],
                                id="status-time-tabs",
                                active_tab="hour",
                            ),
                            html.Div(id="status-charts", className="mt-3"),
                        ]
                    ),
                ]
            ),
            # Auto-refresh intervals
            dcc.Interval(
                id="status-auto-refresh-interval", interval=STATUS_REFRESH_INTERVAL, n_intervals=0
            ),
            dcc.Interval(
                id="status-countdown-interval",
                interval=1000,  # 1 second for countdown
                n_intervals=0,
            ),
        ]
    )
