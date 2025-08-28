"""Tab content components for different sections of the dashboard."""

from dash import dcc, html
import dash_ag_grid as dag
import dash_bootstrap_components as dbc

from ..config import EXECUTIONS_REFRESH_INTERVAL, STATUS_REFRESH_INTERVAL
from ..utils.mobile_utils import get_mobile_column_config


def get_responsive_grid_options(is_mobile=False):
    """Get responsive AG-Grid options based on device type."""
    base_options = {
        "cacheBlockSize": 50,
        "maxBlocksInCache": 2,
        "blockLoadDebounceMillis": 500,
        "purgeClosedRowNodes": True,
        "maxConcurrentDatasourceRequests": 1,
        "enableCellTextSelection": True,
        "ensureDomOrder": True,
        "animateRows": False,  # Disable animations for better performance
        "suppressMenuHide": True,  # Keep menu visible
        "suppressColumnVirtualisation": False,
        # Force horizontal scroll to always be visible
        "suppressHorizontalScroll": False,
        "alwaysShowHorizontalScroll": True,
    }

    if is_mobile:
        # Mobile-specific options with AG-Grid responsive features
        base_options.update(
            {
                "suppressColumnVirtualisation": True,  # Show all columns, allow horizontal scroll
                "rowHeight": 40,  # Larger row height for touch targets
                "headerHeight": 36,  # Larger header height for touch targets
                "animateRows": False,  # Disable animations on mobile
                "suppressColumnMoveAnimation": True,  # Disable column move animations
                "suppressScrollOnNewData": True,  # Don't auto-scroll on new data
                "suppressDragLeaveHidesColumns": True,  # Don't hide columns when dragging
                "suppressColumnResize": False,  # Allow column resizing
                "suppressAutoSize": False,  # Allow auto-sizing
                "skipHeaderOnAutoSize": False,  # Include header when auto-sizing
                "suppressSizeToFit": False,  # Enable size to fit
            }
        )
    else:
        # Desktop options - ensure horizontal scrolling works properly
        base_options.update(
            {
                "rowHeight": 32,
                "headerHeight": 32,
                "suppressColumnResize": False,
                # Desktop-specific scrolling options
                "suppressColumnVirtualisation": False,
                "suppressSizeToFit": True,  # Disable auto-fit to allow horizontal scroll
            }
        )

    return base_options


def create_responsive_table(table_id, table_type, style_data_conditional=None, height="800px"):
    """Create a responsive AG-Grid table with mobile-optimized columns."""
    # Get column configuration
    column_config = get_mobile_column_config()
    config = column_config.get(table_type, {})

    # Combine primary and secondary columns
    primary_cols = config.get("primary_columns", [])
    secondary_cols = config.get("secondary_columns", [])
    all_columns = primary_cols + secondary_cols

    # Get base responsive grid options
    base_grid_options = get_responsive_grid_options(is_mobile=False)  # Default to desktop

    # Base AG-Grid configuration
    base_config = {
        "id": table_id,
        "columnDefs": all_columns,
        "defaultColDef": {
            "resizable": True,
            "sortable": True,
            "filter": True,
            "minWidth": 50,
            "suppressSizeToFit": True,  # Prevent auto-sizing that can hide scroll
            "wrapText": True,
            "autoHeight": False,
        },
        "columnSize": "sizeToFit"
        if not all_columns or len(all_columns) <= 5
        else None,  # Use autoSize for many columns
        "rowModelType": "infinite",
        "dashGridOptions": base_grid_options,
        "style": {
            "height": height,
            "width": "100%",
            "overflowX": "auto",  # Force horizontal scroll
            "overflowY": "auto",  # Force vertical scroll
        },
        "className": "ag-theme-alpine responsive-table",
    }

    # Add row styling based on status using getRowStyle in dashGridOptions
    if style_data_conditional:
        # Create a JavaScript function string that returns inline styles
        js_function_lines = []
        for cond in style_data_conditional:
            condition = cond.get("condition", "false")
            style = cond.get("style", {})

            if "params.data.status === '" in condition and style:
                status_value = condition.split("params.data.status === '")[1].split("'")[0]
                bg_color = style.get("backgroundColor", "")
                text_color = style.get("color", "")

                if bg_color and text_color:
                    js_function_lines.append(
                        f"if (params.data && params.data.status === '{status_value}') {{ "
                        f"return {{backgroundColor: '{bg_color}', color: '{text_color}'}}; }}"
                    )

        if js_function_lines:
            js_function = f"""
function(params) {{
    if (!params || !params.data) return null;
    {" ".join(js_function_lines)}
    return null;
}}
            """.strip()

            # Add to dashGridOptions instead of base_config
            base_grid_options["getRowStyle"] = js_function
            print(
                f"DEBUG: Added getRowStyle function with {len(js_function_lines)} conditions"
            )  # Debug output

    return html.Div(
        [
            dag.AgGrid(**base_config),
            # Mobile scroll hint
            html.Div(
                "← Scroll horizontally to view more columns →",
                className="table-scroll-hint",
                id=f"{table_id}-scroll-hint",
                style={"display": "none"},  # Hidden by default, shown by callback
            ),
        ],
        className="table-container",
        **{"data-testid": table_id},  # Add data-testid for playwright testing
        style={
            "width": "100%",
            "overflowX": "auto",  # Ensure container allows horizontal overflow
            "overflowY": "hidden",  # Container doesn't need vertical overflow
        },
    )


def executions_tab_content():
    """Create the executions tab content."""
    style_data_conditional = [
        {
            "condition": "params.data.status === 'FAILED'",
            "style": {"backgroundColor": "#F8D7DA", "color": "#721C24"},
        },
        {
            "condition": "params.data.status === 'FINISHED'",
            "style": {"backgroundColor": "#D1E7DD", "color": "#0F5132"},
        },
        {
            "condition": "params.data.status === 'RUNNING'",
            "style": {"backgroundColor": "#CCE5FF", "color": "#084298"},
        },
        {
            "condition": "params.data.status === 'READY'",
            "style": {"backgroundColor": "#FFF3CD", "color": "#664D03"},
        },
        {
            "condition": "params.data.status === 'PENDING'",
            "style": {"backgroundColor": "#E2E3E5", "color": "#495057"},
        },
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
            create_responsive_table(
                table_id="executions-table",
                table_type="executions",
                style_data_conditional=style_data_conditional,
            ),
            # Cancel execution confirmation modal
            dbc.Modal(
                [
                    dbc.ModalHeader(
                        dbc.ModalTitle("Cancel Execution"),
                        close_button=True,
                    ),
                    dbc.ModalBody(
                        [
                            html.P(
                                "Are you sure you want to cancel this execution?",
                                className="mb-3",
                            ),
                            html.Div(
                                [
                                    html.Strong("Execution ID: "),
                                    html.Span(id="cancel-execution-id"),
                                ],
                                className="mb-2",
                            ),
                            html.Div(
                                [
                                    html.Strong("Script: "),
                                    html.Span(id="cancel-execution-script"),
                                ],
                                className="mb-2",
                            ),
                            html.Div(
                                [
                                    html.Strong("Status: "),
                                    html.Span(id="cancel-execution-status"),
                                ],
                                className="mb-3",
                            ),
                            dbc.Alert(
                                "This action cannot be undone.",
                                color="warning",
                                className="mb-0",
                            ),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "Cancel",
                                id="cancel-execution-close-btn",
                                color="secondary",
                                className="me-2",
                            ),
                            dbc.Button(
                                [
                                    html.I(className="fas fa-stop me-2"),
                                    "Confirm Cancel",
                                ],
                                id="cancel-execution-confirm-btn",
                                color="danger",
                            ),
                        ]
                    ),
                ],
                id="cancel-execution-modal",
                is_open=False,
                backdrop="static",
                keyboard=False,
            ),
            # Alert for cancel operation feedback
            dbc.Alert(
                id="cancel-execution-alert",
                is_open=False,
                dismissable=True,
                duration=5000,
                style={"position": "fixed", "top": "20px", "right": "20px", "zIndex": 9999},
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
            # Store to hold execution data for cancel operation
            dcc.Store(id="cancel-execution-store"),
            # Store components for status filter (needed by callbacks)
            dcc.Store(id="executions-status-filter-selected", data=[]),
            dcc.Store(id="executions-status-filter-active", data=False),
            # Modal to display cancellation results
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle("Cancellation Result"), close_button=True),
                    dbc.ModalBody(id="cancel-execution-result-body"),
                    dbc.ModalFooter(
                        dbc.Button("Close", id="cancel-result-close-btn", color="secondary")
                    ),
                ],
                id="cancel-execution-result-modal",
                is_open=False,
                size="lg",
            ),
        ]
    )


def users_tab_content():
    """Create the users tab content."""
    return html.Div(
        [
            # Store for users role filter state
            dcc.Store(id="users-role-filter-selected", data=[]),
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
            create_responsive_table(table_id="users-table", table_type="users"),
        ]
    )


def scripts_tab_content():
    """Create the scripts tab content."""
    style_data_conditional = [
        {
            "condition": "params.data.status === 'PUBLISHED'",
            "style": {"backgroundColor": "#D1E7DD", "color": "#0F5132"},
        },
        {
            "condition": "params.data.status === 'DRAFT'",
            "style": {"backgroundColor": "#FFF3CD", "color": "#664D03"},
        },
        {
            "condition": "params.data.status === 'ARCHIVED'",
            "style": {"backgroundColor": "#F8D7DA", "color": "#721C24"},
        },
        {
            "condition": "params.data.status === 'SUCCESS'",
            "style": {"backgroundColor": "#D1E7DD", "color": "#0F5132"},
        },
        {
            "condition": "params.data.status === 'FAIL'",
            "style": {"backgroundColor": "#F8D7DA", "color": "#721C24"},
        },
        {
            "condition": "params.data.status === 'BUILDING'",
            "style": {"backgroundColor": "#CCE5FF", "color": "#084298"},
        },
        {
            "condition": "params.data.status === 'ACTIVE'",
            "style": {"backgroundColor": "#D1E7DD", "color": "#0F5132"},
        },
        {
            "condition": "params.data.status === 'INACTIVE'",
            "style": {"backgroundColor": "#E2E3E5", "color": "#495057"},
        },
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
            create_responsive_table(
                table_id="scripts-table",
                table_type="scripts",
                style_data_conditional=style_data_conditional,
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


def status_tab_content(is_admin, role=None):
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

    # Check if user is a superadmin for enhanced statistics (API requires SUPERADMIN)
    is_admin_user = role == "SUPERADMIN"

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
                            html.Hr(),
                            html.Div(id="swarm-status-title"),
                            dcc.Loading(
                                id="loading-swarm-info",
                                children=[html.Div(id="swarm-info-summary")],
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
                            # Enhanced statistics sections (SUPERADMIN only)
                            *(
                                [
                                    html.Div(
                                        [
                                            # System Overview
                                            html.Div(
                                                [
                                                    html.H5(
                                                        "System Overview", className="mb-3 mt-4"
                                                    ),
                                                    dcc.Loading(
                                                        id="loading-stats-summary",
                                                        children=[
                                                            html.Div(id="stats-summary-cards")
                                                        ],
                                                        type="default",
                                                        color="#007bff",
                                                    ),
                                                ],
                                                className="mb-4",
                                            ),
                                            html.Hr(),
                                            # User geographic map
                                            html.Div(
                                                [
                                                    html.H5(
                                                        "User Geographic Distribution",
                                                        className="mb-3",
                                                    ),
                                                    dcc.Loading(
                                                        id="loading-stats-map",
                                                        children=[html.Div(id="stats-user-map")],
                                                        type="default",
                                                        color="#007bff",
                                                    ),
                                                ],
                                                className="mb-4",
                                            ),
                                            html.Hr(),
                                            # Additional statistics charts
                                            html.Div(
                                                [
                                                    html.H5("Detailed Analytics", className="mb-3"),
                                                    dcc.Loading(
                                                        id="loading-stats-charts",
                                                        children=[
                                                            html.Div(id="stats-additional-charts")
                                                        ],
                                                        type="default",
                                                        color="#007bff",
                                                    ),
                                                ],
                                                className="mb-4",
                                            ),
                                            html.Hr(),
                                        ]
                                    )
                                ]
                                if is_admin_user
                                else []
                            ),
                            # Status trends charts
                            html.H5("System Status Trends", className="mb-3"),
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
                                                            {
                                                                "label": "Published",
                                                                "value": "PUBLISHED",
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
