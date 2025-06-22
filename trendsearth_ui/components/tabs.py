"""Tab content components for different sections of the dashboard."""

from dash import dcc, html
import dash_ag_grid as dag
import dash_bootstrap_components as dbc

from ..config import DEFAULT_PAGE_SIZE, EXECUTIONS_REFRESH_INTERVAL, STATUS_REFRESH_INTERVAL
from ..utils import parse_date, safe_table_data


def executions_tab_content():
    """Create the executions tab content."""
    column_defs = [
        {"headerName": "Script Name", "field": "script_name"},
        {"headerName": "User Email", "field": "user_email"},
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


def users_tab_content(users, is_admin):
    """Create the users tab content."""
    if not users:
        return html.Div([html.Div("No users found.")])

    user_keys = list(users[0].keys())
    cols = []
    if "email" in user_keys:
        cols.append({"name": "Email", "id": "email"})
    if "name" in user_keys:
        cols.append({"name": "Name", "id": "name"})
    for k in user_keys:
        if k not in ("email", "name"):
            cols.append({"name": k, "id": k})
    if is_admin:
        cols.append({"name": "Edit", "id": "edit"})

    for u in users:
        for date_col in ["created_at", "updated_at"]:
            if date_col in u:
                u[date_col] = parse_date(u.get(date_col))
        if is_admin:
            u["edit"] = "Edit"

    table_data = safe_table_data(users, [c["id"] for c in cols])
    table_data = sorted(table_data, key=lambda x: x.get("email", ""))
    column_defs = [{"headerName": c["name"], "field": c["id"]} for c in cols]
    for c in column_defs:
        if c["field"] == "email":
            c["sort"] = "asc"
        if c["field"] in ("created_at", "updated_at"):
            c["filter"] = "agDateColumnFilter"
        if c["field"] == "edit":
            c["sortable"] = False
            c["filter"] = False

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
                ]
            ),
            dag.AgGrid(
                columnDefs=column_defs,
                rowData=table_data,
                id="users-table",
                defaultColDef={"sortable": True, "resizable": True, "filter": True},
                columnSize="sizeToFit",
                dashGridOptions={"pagination": True, "paginationPageSize": DEFAULT_PAGE_SIZE},
            ),
        ]
    )


def scripts_tab_content(scripts, users, is_admin):
    """Create the scripts tab content."""
    if not scripts:
        return html.Div([html.Div("No scripts found.")])

    user_col = None
    if scripts and "user_id" in scripts[0]:
        user_col = "user_id"
    elif scripts and "author_id" in scripts[0]:
        user_col = "author_id"

    cols = []
    if scripts:
        if "name" in scripts[0]:
            cols.append({"name": "Script Name", "id": "name"})
        if user_col:
            cols.append({"name": "User Name", "id": "user_name"})
        for k in scripts[0]:
            if k not in ("name", user_col):
                cols.append({"name": k, "id": k})
        # Add logs column for scripts
        cols.append({"name": "Logs", "id": "logs"})
        # Add edit column for admin users
        if is_admin:
            cols.append({"name": "Edit", "id": "edit"})

    table_data = []
    user_id_to_name = {u.get("id"): u.get("name") for u in users or []}
    for s in scripts:
        row = s.copy()
        if user_col:
            row["user_name"] = user_id_to_name.get(row.get(user_col), "")
        for date_col in ["start_date", "end_date", "created_at", "updated_at"]:
            if date_col in row:
                row[date_col] = parse_date(row.get(date_col))
        # Add logs action button
        row["logs"] = "Show Logs"
        # Add edit button for admin users
        if is_admin:
            row["edit"] = "Edit"
        table_data.append(row)

    table_data = safe_table_data(table_data, [c["id"] for c in cols])
    table_data = sorted(table_data, key=lambda x: x.get("name", ""))

    style_data_conditional = [
        {"condition": "params.data.status == 'SUCCESS'", "style": {"backgroundColor": "#D1E7DD"}},
        {"condition": "params.data.status == 'FAIL'", "style": {"backgroundColor": "#F8D7DA"}},
    ]

    column_defs = [{"headerName": c["name"], "field": c["id"]} for c in cols]
    for c in column_defs:
        if c["field"] == "name":
            c["sort"] = "asc"
        if c["field"] in ("start_date", "end_date", "created_at", "updated_at"):
            c["filter"] = "agDateColumnFilter"
        if c["field"] == "logs":
            c["sortable"] = False
            c["filter"] = False
        if c["field"] == "edit":
            c["sortable"] = False
            c["filter"] = False

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
                ]
            ),
            dag.AgGrid(
                columnDefs=column_defs,
                rowData=table_data,
                id="scripts-table",
                defaultColDef={"sortable": True, "resizable": True, "filter": True},
                columnSize="sizeToFit",
                dashGridOptions={"pagination": True, "paginationPageSize": DEFAULT_PAGE_SIZE},
                getRowStyle={"styleConditions": style_data_conditional},
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
                                                        disabled=True,
                                                        value=current_email,
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
