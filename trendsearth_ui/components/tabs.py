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
        {"headerName": "User Email", "field": "user_email"},
        {"headerName": "User ID", "field": "user_id"},
        {"headerName": "Status", "field": "status"},
        {"headerName": "Start Date", "field": "start_date", "filter": "agDateColumnFilter"},
        {"headerName": "End Date", "field": "end_date", "filter": "agDateColumnFilter"},
        {"headerName": "Duration", "field": "duration"},
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
                    "enableCellTextSelection": True,
                    "ensureDomOrder": True,
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
        {"headerName": "User Email", "field": "email"},
        {"headerName": "User ID", "field": "id"},
        {"headerName": "Name", "field": "name"},
        {"headerName": "Institution", "field": "institution"},
        {"headerName": "Country", "field": "country"},
        {"headerName": "Role", "field": "role"},
        {"headerName": "Created At", "field": "created_at", "filter": "agDateColumnFilter"},
        {"headerName": "Updated At", "field": "updated_at", "filter": "agDateColumnFilter"},
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
                    "enableCellTextSelection": True,
                    "ensureDomOrder": True,
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
                    "enableCellTextSelection": True,
                    "ensureDomOrder": True,
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
                        [
                            dcc.Loading(
                                id="loading-status-summary",
                                children=[
                                    html.Div(
                                        id="status-summary",
                                        children=[
                                            html.Div(
                                                [
                                                    html.I(
                                                        className="fas fa-circle-notch fa-spin me-2"
                                                    ),
                                                    "Loading system status...",
                                                ],
                                                className="text-center text-muted p-3",
                                            )
                                        ],
                                    )
                                ],
                                type="default",
                                color="#007bff",
                            ),
                            html.Hr(),
                            html.H5("Deployment Information", className="card-title mt-4"),
                            dcc.Loading(
                                id="loading-deployment-info",
                                children=[html.Div(id="deployment-info-summary")],
                                type="default",
                                color="#007bff",
                            ),
                        ]
                    ),
                ],
                className="mb-4",
            ),
            # Status charts
            dbc.Card(
                [
                    dbc.CardHeader(html.H4("System Status Trends")),
                    dbc.CardBody(
                        [
                            html.Div(
                                [
                                    html.Ul(
                                        [
                                            html.Li(
                                                [
                                                    html.A(
                                                        "Last 24 Hours",
                                                        className="nav-link active",
                                                        id="status-tab-day",
                                                        **{"data-tab": "day"},
                                                        style={"cursor": "pointer"},
                                                    )
                                                ],
                                                className="nav-item",
                                            ),
                                            html.Li(
                                                [
                                                    html.A(
                                                        "Last Week",
                                                        className="nav-link",
                                                        id="status-tab-week",
                                                        **{"data-tab": "week"},
                                                        style={"cursor": "pointer"},
                                                    )
                                                ],
                                                className="nav-item",
                                            ),
                                            html.Li(
                                                [
                                                    html.A(
                                                        "Last Month",
                                                        className="nav-link",
                                                        id="status-tab-month",
                                                        **{"data-tab": "month"},
                                                        style={"cursor": "pointer"},
                                                    )
                                                ],
                                                className="nav-item",
                                            ),
                                        ],
                                        className="nav nav-tabs",
                                        id="status-time-tabs",
                                    ),
                                    # Hidden store to track active tab
                                    dcc.Store(id="status-time-tabs-store", data="day"),
                                ],
                                className="mb-3",
                            ),
                            dcc.Loading(
                                id="loading-status-charts",
                                children=[
                                    html.Div(
                                        id="status-charts",
                                        className="mt-3",
                                        children=[
                                            html.Div(
                                                [
                                                    html.I(className="fas fa-chart-line me-2"),
                                                    "Loading charts...",
                                                ],
                                                className="text-center text-muted p-4",
                                            )
                                        ],
                                    )
                                ],
                                type="default",
                                color="#007bff",
                            ),
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


def admin_tab_content(role, is_admin):
    """Create the admin tab content with forms for creating users and uploading scripts."""
    if not is_admin:
        return html.Div(
            [
                dbc.Alert(
                    "Access denied. Administrator privileges required to access admin functions.",
                    color="danger",
                )
            ]
        )

    return html.Div(
        [
            # Page Header
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H2(
                                [
                                    html.I(className="fas fa-user-shield me-2"),
                                    "Administration Panel",
                                ],
                                className="mb-4",
                            )
                        ]
                    )
                ]
            ),
            # Create New User Section (SUPERADMIN only)
            *(
                [
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                html.H4(
                                    [
                                        html.I(className="fas fa-user-plus me-2"),
                                        "Create New User",
                                    ]
                                )
                            ),
                            dbc.CardBody(
                                [
                                    dbc.Form(
                                        [
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            dbc.Label("Name *"),
                                                            dbc.Input(
                                                                id="admin-new-user-name",
                                                                type="text",
                                                                placeholder="Enter full name",
                                                                required=True,
                                                            ),
                                                        ],
                                                        width=6,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            dbc.Label("Email *"),
                                                            dbc.Input(
                                                                id="admin-new-user-email",
                                                                type="email",
                                                                placeholder="Enter email address",
                                                                required=True,
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
                                                            dbc.Label("Password *"),
                                                            dbc.Input(
                                                                id="admin-new-user-password",
                                                                type="password",
                                                                placeholder="Set password for user",
                                                                required=True,
                                                            ),
                                                        ],
                                                        width=6,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            dbc.Label("Confirm Password *"),
                                                            dbc.Input(
                                                                id="admin-new-user-confirm-password",
                                                                type="password",
                                                                placeholder="Confirm password",
                                                                required=True,
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
                                                                id="admin-new-user-institution",
                                                                type="text",
                                                                placeholder="Enter institution/organization",
                                                            ),
                                                        ],
                                                        width=6,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            dbc.Label("Country"),
                                                            dbc.Input(
                                                                id="admin-new-user-country",
                                                                type="text",
                                                                placeholder="Enter country",
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
                                                            dbc.Label("Role *"),
                                                            dbc.Select(
                                                                id="admin-new-user-role",
                                                                options=[
                                                                    {
                                                                        "label": "User",
                                                                        "value": "USER",
                                                                    },
                                                                    {
                                                                        "label": "Admin",
                                                                        "value": "ADMIN",
                                                                    },
                                                                    {
                                                                        "label": "Super Admin",
                                                                        "value": "SUPERADMIN",
                                                                    },
                                                                ],
                                                                value="USER",
                                                                required=True,
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
                                                                [
                                                                    html.I(
                                                                        className="fas fa-user-plus me-2"
                                                                    ),
                                                                    "Create User",
                                                                ],
                                                                id="admin-create-user-btn",
                                                                color="success",
                                                                className="me-2",
                                                            ),
                                                            dbc.Button(
                                                                [
                                                                    html.I(
                                                                        className="fas fa-eraser me-2"
                                                                    ),
                                                                    "Clear Form",
                                                                ],
                                                                id="admin-clear-user-form-btn",
                                                                color="secondary",
                                                                outline=True,
                                                            ),
                                                        ],
                                                        width=12,
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                            dbc.Alert(
                                                id="admin-create-user-alert",
                                                is_open=False,
                                                dismissable=True,
                                                duration=5000,
                                            ),
                                        ]
                                    )
                                ]
                            ),
                        ],
                        className="mb-4",
                    )
                ]
                if role == "SUPERADMIN"
                else []
            ),
            # Rate Limiting Reset Section (SUPERADMIN only)
            *(
                [
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                html.H4(
                                    [
                                        html.I(className="fas fa-tachometer-alt me-2"),
                                        "Rate Limiting Management",
                                    ]
                                )
                            ),
                            dbc.CardBody(
                                [
                                    # Rate Limiting Status Summary
                                    html.Div(
                                        [
                                            html.H5("System Status", className="mb-3"),
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            dbc.Card(
                                                                [
                                                                    dbc.CardBody(
                                                                        [
                                                                            html.H6(
                                                                                "Rate Limiting",
                                                                                className="card-title",
                                                                            ),
                                                                            html.H4(
                                                                                id="rate-limit-status",
                                                                                children="Loading...",
                                                                                className="text-primary",
                                                                            ),
                                                                        ]
                                                                    )
                                                                ],
                                                                className="text-center",
                                                            )
                                                        ],
                                                        width=3,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            dbc.Card(
                                                                [
                                                                    dbc.CardBody(
                                                                        [
                                                                            html.H6(
                                                                                "Storage Type",
                                                                                className="card-title",
                                                                            ),
                                                                            html.H4(
                                                                                id="rate-limit-storage",
                                                                                children="Loading...",
                                                                                className="text-info",
                                                                            ),
                                                                        ]
                                                                    )
                                                                ],
                                                                className="text-center",
                                                            )
                                                        ],
                                                        width=3,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            dbc.Card(
                                                                [
                                                                    dbc.CardBody(
                                                                        [
                                                                            html.H6(
                                                                                "Active Limits",
                                                                                className="card-title",
                                                                            ),
                                                                            html.H4(
                                                                                id="rate-limit-count",
                                                                                children="0",
                                                                                className="text-warning",
                                                                            ),
                                                                        ]
                                                                    )
                                                                ],
                                                                className="text-center",
                                                            )
                                                        ],
                                                        width=3,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            dbc.Button(
                                                                [
                                                                    html.I(
                                                                        className="fas fa-refresh me-2"
                                                                    ),
                                                                    "Refresh Status",
                                                                ],
                                                                id="refresh-rate-limit-status-btn",
                                                                color="outline-primary",
                                                                className="w-100",
                                                            ),
                                                        ],
                                                        width=3,
                                                    ),
                                                ],
                                                className="mb-4",
                                            ),
                                        ]
                                    ),
                                    # Active Rate Limits Table
                                    html.Div(
                                        [
                                            html.H5("Active Rate Limits", className="mb-3"),
                                            html.Div(
                                                id="rate-limits-table-container",
                                                children=[
                                                    html.Div(
                                                        [
                                                            html.I(
                                                                className="fas fa-spinner fa-spin me-2"
                                                            ),
                                                            "Loading active rate limits...",
                                                        ],
                                                        className="text-center text-muted p-4",
                                                    )
                                                ],
                                            ),
                                        ],
                                        className="mb-4",
                                    ),
                                    # Reset Rate Limits Section
                                    html.Hr(),
                                    html.H5("Reset Rate Limits", className="mb-3"),
                                    html.P(
                                        "Reset all rate limits for the API. This will clear all rate limiting restrictions for all users and endpoints.",
                                        className="mb-3",
                                    ),
                                    dbc.Button(
                                        [
                                            html.I(className="fas fa-refresh me-2"),
                                            "Reset All Rate Limits",
                                        ],
                                        id="admin-reset-rate-limits-btn",
                                        color="warning",
                                        className="me-2",
                                    ),
                                    dbc.Alert(
                                        id="admin-reset-rate-limits-alert",
                                        is_open=False,
                                        dismissable=True,
                                        duration=5000,
                                    ),
                                ]
                            ),
                        ],
                        className="mb-4",
                    ),
                ]
                if role == "SUPERADMIN"
                else []
            ),
            # Upload New Script Section
            dbc.Card(
                [
                    dbc.CardHeader(
                        html.H4(
                            [
                                html.I(className="fas fa-file-upload me-2"),
                                "Upload New Script",
                            ]
                        )
                    ),
                    dbc.CardBody(
                        [
                            dbc.Form(
                                [
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Label("Script Name *"),
                                                    dbc.Input(
                                                        id="admin-new-script-name",
                                                        type="text",
                                                        placeholder="Enter script name",
                                                        required=True,
                                                    ),
                                                ],
                                                width=6,
                                            ),
                                            dbc.Col(
                                                [
                                                    dbc.Label("Script Status"),
                                                    dbc.Select(
                                                        id="admin-new-script-status",
                                                        options=[
                                                            {"label": "Draft", "value": "DRAFT"},
                                                            {"label": "Active", "value": "ACTIVE"},
                                                            {
                                                                "label": "Inactive",
                                                                "value": "INACTIVE",
                                                            },
                                                        ],
                                                        value="DRAFT",
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
                                                    dbc.Label("Description"),
                                                    dbc.Textarea(
                                                        id="admin-new-script-description",
                                                        placeholder="Enter script description",
                                                        rows=3,
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
                                                    dbc.Label("Script File *"),
                                                    dcc.Upload(
                                                        id="admin-script-upload",
                                                        children=html.Div(
                                                            [
                                                                html.I(
                                                                    className="fas fa-cloud-upload-alt me-2"
                                                                ),
                                                                "Drag and Drop or ",
                                                                html.A("Select Script File"),
                                                            ]
                                                        ),
                                                        style={
                                                            "width": "100%",
                                                            "height": "80px",
                                                            "lineHeight": "80px",
                                                            "borderWidth": "2px",
                                                            "borderStyle": "dashed",
                                                            "borderRadius": "10px",
                                                            "textAlign": "center",
                                                            "marginBottom": "10px",
                                                            "cursor": "pointer",
                                                            "backgroundColor": "#f8f9fa",
                                                        },
                                                        multiple=False,
                                                        accept=".py,.js,.sh,.bat,.r,.ipynb",
                                                    ),
                                                    html.Div(
                                                        id="admin-script-upload-status",
                                                        className="text-muted small",
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
                                                    dbc.Button(
                                                        [
                                                            html.I(className="fas fa-upload me-2"),
                                                            "Upload Script",
                                                        ],
                                                        id="admin-upload-script-btn",
                                                        color="primary",
                                                        className="me-2",
                                                        disabled=True,
                                                    ),
                                                    dbc.Button(
                                                        [
                                                            html.I(className="fas fa-eraser me-2"),
                                                            "Clear Form",
                                                        ],
                                                        id="admin-clear-script-form-btn",
                                                        color="secondary",
                                                        outline=True,
                                                    ),
                                                ],
                                                width=12,
                                            ),
                                        ],
                                        className="mb-3",
                                    ),
                                    dbc.Alert(
                                        id="admin-upload-script-alert",
                                        is_open=False,
                                        dismissable=True,
                                        duration=5000,
                                    ),
                                ]
                            )
                        ]
                    ),
                ],
                className="mb-4",
            ),
        ]
    )
