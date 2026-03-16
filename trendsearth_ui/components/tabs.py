"""Tab content components for different sections of the dashboard."""

from dash import dcc, html
import dash_ag_grid as dag
import dash_bootstrap_components as dbc

from ..config import EXECUTIONS_REFRESH_INTERVAL, STATUS_REFRESH_INTERVAL
from ..i18n import gettext as _
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
        # Tell AG-Grid the scrollbar width so it reserves space even when OS
        # reports 0-width (overlay) scrollbars
        "scrollbarWidth": 12,
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
            }
        )
    else:
        # Desktop options - ensure horizontal scrolling works properly
        base_options.update(
            {
                "rowHeight": 32,
                "headerHeight": 32,
                "suppressColumnResize": False,
                # Render all columns so horizontal scroll container gets correct width
                "suppressColumnVirtualisation": True,
            }
        )

    return base_options


def create_responsive_table(table_id, table_type, style_data_conditional=None, height=None):
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

    # Allow individual table configurations to override default column behavior
    default_col_def = {
        "resizable": True,
        "sortable": True,
        "filter": True,
        "wrapText": True,
        "autoHeight": False,
    }

    default_col_def.update(config.get("default_col_def_overrides", {}))

    # Apply any grid option overrides before building the final config
    grid_options_overrides = config.get("grid_options_overrides")
    if grid_options_overrides:
        base_grid_options.update(grid_options_overrides)

    # Default to filling remaining viewport height
    if height is None:
        height = "calc(100vh - 180px)"

    # Base AG-Grid configuration
    base_config = {
        "id": table_id,
        "columnDefs": all_columns,
        "defaultColDef": default_col_def,
        "rowModelType": "infinite",
        "dashGridOptions": base_grid_options,
        "style": {
            "height": height,
            "width": "100%",
        },
        "className": "ag-theme-alpine responsive-table",
    }

    # Add style conditions if provided
    if style_data_conditional:
        base_config["getRowStyle"] = {"styleConditions": style_data_conditional}

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
                                _("Refresh Executions"),
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
                                    html.Span(_("Auto-refresh in:") + " ", className="me-2"),
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
                        dbc.ModalTitle(_("Cancel Execution")),
                        close_button=True,
                    ),
                    dbc.ModalBody(
                        [
                            html.P(
                                _("Are you sure you want to cancel this execution?"),
                                className="mb-3",
                            ),
                            html.Div(
                                [
                                    html.Strong(_("Execution ID:") + " "),
                                    html.Span(id="cancel-execution-id"),
                                ],
                                className="mb-2",
                            ),
                            html.Div(
                                [
                                    html.Strong(_("Script:") + " "),
                                    html.Span(id="cancel-execution-script"),
                                ],
                                className="mb-2",
                            ),
                            html.Div(
                                [
                                    html.Strong(_("Status:") + " "),
                                    html.Span(id="cancel-execution-status"),
                                ],
                                className="mb-3",
                            ),
                            dbc.Alert(
                                _("This action cannot be undone."),
                                color="warning",
                                className="mb-0",
                            ),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                _("Cancel"),
                                id="cancel-execution-close-btn",
                                color="secondary",
                                className="me-2",
                            ),
                            dbc.Button(
                                [
                                    html.I(className="fas fa-stop me-2"),
                                    _("Confirm Cancel"),
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
                    dbc.ModalHeader(dbc.ModalTitle(_("Cancellation Result")), close_button=True),
                    dbc.ModalBody(id="cancel-execution-result-body"),
                    dbc.ModalFooter(
                        dbc.Button(_("Close"), id="cancel-result-close-btn", color="secondary")
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
                                _("Refresh Users"),
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
                                _("Refresh Scripts"),
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
                    dbc.CardHeader(html.H4(_("Profile Settings"))),
                    dbc.CardBody(
                        [
                            dbc.Form(
                                [
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Label(_("Name")),
                                                    dbc.Input(
                                                        id="profile-name",
                                                        type="text",
                                                        placeholder=_("Enter your name"),
                                                        value=current_name,
                                                    ),
                                                ],
                                                width=6,
                                            ),
                                            dbc.Col(
                                                [
                                                    dbc.Label(_("Email")),
                                                    dbc.Input(
                                                        id="profile-email",
                                                        type="email",
                                                        placeholder=_("Enter your email"),
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
                                                    dbc.Label(_("Institution")),
                                                    dbc.Input(
                                                        id="profile-institution",
                                                        type="text",
                                                        placeholder=_("Enter your institution"),
                                                        value=current_institution,
                                                    ),
                                                ],
                                                width=6,
                                            ),
                                            dbc.Col(
                                                [
                                                    dbc.Label(_("Role")),
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
                                                        _("Update Profile"),
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
                    dbc.CardHeader(html.H4(_("Email Notifications"))),
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label(_("Execution Completion Notifications")),
                                            html.Div(
                                                [
                                                    dbc.Switch(
                                                        id="profile-email-notifications-switch",
                                                        label=_("Enable email notifications"),
                                                        value=user_data.get(
                                                            "email_notifications_enabled", True
                                                        )
                                                        if user_data
                                                        else True,
                                                        className="mb-2",
                                                    ),
                                                    html.Small(
                                                        _(
                                                            "Receive email notifications when your script executions finish, fail, or are cancelled."
                                                        ),
                                                        className="text-muted",
                                                    ),
                                                ],
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
                                            dbc.Alert(
                                                id="profile-email-notifications-alert",
                                                is_open=False,
                                                dismissable=True,
                                            ),
                                        ],
                                        width=12,
                                    ),
                                ]
                            ),
                        ]
                    ),
                ],
                className="mb-4",
            ),
            dbc.Card(
                [
                    dbc.CardHeader(html.H4(_("Google Earth Engine Account"))),
                    dbc.CardBody(
                        [
                            # Current credentials status
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.H6(_("Current Credentials Status")),
                                            html.Div(id="profile-gee-status-display"),
                                        ],
                                        width=12,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            html.Hr(),
                            # GEE Account Setup Options
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.H6(_("Setup Your GEE Account")),
                                            html.P(
                                                _(
                                                    "Choose one of the options below to configure your Google Earth Engine credentials:"
                                                ),
                                                className="text-muted",
                                            ),
                                        ],
                                        width=12,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # OAuth Setup Section
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Card(
                                                [
                                                    dbc.CardBody(
                                                        [
                                                            html.H6(
                                                                _(
                                                                    "Option 1: Connect Your GEE Account (OAuth)"
                                                                ),
                                                                className="mb-3",
                                                            ),
                                                            html.P(
                                                                _(
                                                                    "Connect your personal Google Earth Engine account using OAuth authentication."
                                                                ),
                                                                className="text-muted",
                                                            ),
                                                            dbc.Button(
                                                                _("Connect GEE Account"),
                                                                id="profile-gee-oauth-btn",
                                                                color="primary",
                                                                className="mb-2",
                                                            ),
                                                            dbc.Alert(
                                                                id="profile-gee-oauth-alert",
                                                                is_open=False,
                                                                dismissable=True,
                                                            ),
                                                        ]
                                                    )
                                                ],
                                                outline=True,
                                                color="primary",
                                            ),
                                        ],
                                        width=12,
                                        className="mb-3",
                                    ),
                                ]
                            ),
                            # Service Account Upload Section
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Card(
                                                [
                                                    dbc.CardBody(
                                                        [
                                                            html.H6(
                                                                _(
                                                                    "Option 2: Upload Service Account Key"
                                                                ),
                                                                className="mb-3",
                                                            ),
                                                            html.P(
                                                                _(
                                                                    "Upload a Google Cloud service account JSON key with Earth Engine access."
                                                                ),
                                                                className="text-muted",
                                                            ),
                                                            dcc.Upload(
                                                                id="profile-gee-service-account-upload",
                                                                children=dbc.Button(
                                                                    [
                                                                        html.I(
                                                                            className="fas fa-upload me-2"
                                                                        ),
                                                                        _(
                                                                            "Upload Service Account Key"
                                                                        ),
                                                                    ],
                                                                    color="secondary",
                                                                    outline=True,
                                                                ),
                                                                accept=".json",
                                                                max_size=1024 * 1024,  # 1MB max
                                                            ),
                                                            dbc.Alert(
                                                                id="profile-gee-service-account-alert",
                                                                is_open=False,
                                                                dismissable=True,
                                                            ),
                                                        ]
                                                    )
                                                ],
                                                outline=True,
                                                color="secondary",
                                            ),
                                        ],
                                        width=12,
                                        className="mb-3",
                                    ),
                                ]
                            ),
                            # Credential Management Actions
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.H6(_("Manage Credentials")),
                                            dbc.ButtonGroup(
                                                [
                                                    dbc.Button(
                                                        _("Test Credentials"),
                                                        id="profile-gee-test-btn",
                                                        color="info",
                                                        outline=True,
                                                        disabled=True,
                                                    ),
                                                    dbc.Button(
                                                        _("Delete Credentials"),
                                                        id="profile-gee-delete-btn",
                                                        color="danger",
                                                        outline=True,
                                                        disabled=True,
                                                    ),
                                                ],
                                                className="mb-2",
                                            ),
                                            dbc.Alert(
                                                id="profile-gee-management-alert",
                                                is_open=False,
                                                dismissable=True,
                                            ),
                                        ],
                                        width=12,
                                    ),
                                ],
                            ),
                        ]
                    ),
                ],
                className="mb-4",
            ),
            # Service Credentials Section
            dbc.Card(
                [
                    dbc.CardHeader(html.H4(_("Service Credentials"))),
                    dbc.CardBody(
                        [
                            html.P(
                                _(
                                    "Service credentials allow external applications to authenticate "
                                    "with the Trends.Earth API using the OAuth2 client credentials grant. "
                                    "The client secret is shown only once at creation time."
                                ),
                                className="text-muted",
                            ),
                            # Credentials table
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Button(
                                                [
                                                    html.I(className="fas fa-sync-alt me-2"),
                                                    _("Refresh"),
                                                ],
                                                id="service-creds-refresh-btn",
                                                color="secondary",
                                                outline=True,
                                                size="sm",
                                                className="mb-2",
                                            ),
                                        ],
                                        width="auto",
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Button(
                                                [
                                                    html.I(className="fas fa-plus me-2"),
                                                    _("New Credential"),
                                                ],
                                                id="service-creds-create-btn",
                                                color="primary",
                                                size="sm",
                                                className="mb-2",
                                            ),
                                        ],
                                        width="auto",
                                    ),
                                ],
                                className="mb-2",
                            ),
                            html.Div(id="service-creds-table-container"),
                            dbc.Alert(
                                id="service-creds-alert",
                                is_open=False,
                                dismissable=True,
                                className="mt-2",
                            ),
                        ]
                    ),
                ],
                className="mb-4",
            ),
            # Create Credential Modal
            dbc.Modal(
                [
                    dbc.ModalHeader(
                        dbc.ModalTitle(_("Create Service Credential")),
                        close_button=True,
                    ),
                    dbc.ModalBody(
                        [
                            dbc.Form(
                                [
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Label(_("Name") + " *"),
                                                    dbc.Input(
                                                        id="service-creds-name-input",
                                                        type="text",
                                                        placeholder=_("e.g. My CLI Tool"),
                                                    ),
                                                    dbc.FormText(
                                                        _(
                                                            "A descriptive label for this credential."
                                                        )
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
                                                    dbc.Label("Scopes"),
                                                    dbc.Checklist(
                                                        id="service-creds-scopes-input",
                                                        options=[
                                                            {
                                                                "label": "All (full access)",
                                                                "value": "all",
                                                            },
                                                            {
                                                                "label": "Execution: Read",
                                                                "value": "execution:read",
                                                            },
                                                            {
                                                                "label": "Execution: Write",
                                                                "value": "execution:write",
                                                            },
                                                            {
                                                                "label": "Script: Read",
                                                                "value": "script:read",
                                                            },
                                                            {
                                                                "label": "Script: Write",
                                                                "value": "script:write",
                                                            },
                                                            {
                                                                "label": "User: Read",
                                                                "value": "user:read",
                                                            },
                                                            {
                                                                "label": "User: Write",
                                                                "value": "user:write",
                                                            },
                                                            {
                                                                "label": "Boundary: Read",
                                                                "value": "boundary:read",
                                                            },
                                                            {
                                                                "label": "GEE: Read",
                                                                "value": "gee:read",
                                                            },
                                                            {
                                                                "label": "GEE: Write",
                                                                "value": "gee:write",
                                                            },
                                                            {
                                                                "label": "Stats: Read",
                                                                "value": "stats:read",
                                                            },
                                                        ],
                                                        value=["all"],
                                                        inline=False,
                                                        className="mt-1",
                                                    ),
                                                    dbc.FormText(
                                                        "Select scopes to restrict access. "
                                                        "'All' grants full access."
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
                                                    dbc.Label("Expires in Days"),
                                                    dbc.Input(
                                                        id="service-creds-expires-input",
                                                        type="number",
                                                        placeholder="Leave blank for no expiry",
                                                        min=1,
                                                    ),
                                                    dbc.FormText(
                                                        "Optional. Credential will expire after this many days."
                                                    ),
                                                ],
                                                width=12,
                                            ),
                                        ],
                                        className="mb-3",
                                    ),
                                ]
                            ),
                            dbc.Alert(
                                id="service-creds-create-alert",
                                is_open=False,
                                dismissable=True,
                            ),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "Cancel",
                                id="service-creds-create-cancel-btn",
                                color="secondary",
                                outline=True,
                            ),
                            dbc.Button(
                                "Create",
                                id="service-creds-create-confirm-btn",
                                color="primary",
                            ),
                        ]
                    ),
                ],
                id="service-creds-create-modal",
                is_open=False,
                centered=True,
            ),
            # New Credential Secret Modal (one-time display)
            dbc.Modal(
                [
                    dbc.ModalHeader(
                        dbc.ModalTitle("Credential Created — Save Your Secret"),
                        close_button=False,
                    ),
                    dbc.ModalBody(
                        [
                            dbc.Alert(
                                [
                                    html.I(className="fas fa-exclamation-triangle me-2"),
                                    html.Strong("Important: "),
                                    "Copy your client secret now. It will not be shown again.",
                                ],
                                color="warning",
                                className="mb-3",
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Client ID"),
                                            dbc.Input(
                                                id="service-creds-new-client-id",
                                                type="text",
                                                readonly=True,
                                                className="font-monospace",
                                            ),
                                        ],
                                        width=12,
                                        className="mb-3",
                                    ),
                                ]
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Client Secret"),
                                            dbc.InputGroup(
                                                [
                                                    dbc.Input(
                                                        id="service-creds-new-secret",
                                                        type="text",
                                                        readonly=True,
                                                        className="font-monospace",
                                                    ),
                                                    dbc.Button(
                                                        html.I(className="fas fa-copy"),
                                                        id="service-creds-copy-secret-btn",
                                                        color="secondary",
                                                        outline=True,
                                                        title="Copy to clipboard",
                                                    ),
                                                ]
                                            ),
                                            dbc.FormText(
                                                "Store this secret securely — it cannot be retrieved after closing this dialog."
                                            ),
                                        ],
                                        width=12,
                                    ),
                                ]
                            ),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "I've saved my secret — Close",
                                id="service-creds-secret-close-btn",
                                color="success",
                            ),
                        ]
                    ),
                ],
                id="service-creds-secret-modal",
                is_open=False,
                centered=True,
                backdrop="static",
            ),
            # Revoke Confirmation Modal
            dbc.Modal(
                [
                    dbc.ModalHeader(
                        dbc.ModalTitle("Revoke Service Credential"),
                        close_button=True,
                    ),
                    dbc.ModalBody(
                        [
                            html.P("Are you sure you want to revoke this credential?"),
                            html.P(
                                id="service-creds-revoke-name",
                                className="fw-bold",
                            ),
                            html.P(
                                "Revoked credentials cannot be used to obtain new access tokens. "
                                "This action cannot be undone.",
                                className="text-muted",
                            ),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "Cancel",
                                id="service-creds-revoke-cancel-btn",
                                color="secondary",
                                outline=True,
                            ),
                            dbc.Button(
                                "Revoke",
                                id="service-creds-revoke-confirm-btn",
                                color="danger",
                            ),
                        ]
                    ),
                ],
                id="service-creds-revoke-modal",
                is_open=False,
                centered=True,
            ),
            # Hidden store for revoke target
            dcc.Store(id="service-creds-revoke-target", data=None),
            # Hidden store for scope mutual-exclusion (tracks previous value)
            dcc.Store(id="service-creds-scopes-prev", data=["all"]),
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
            # Delete Account Section
            dbc.Card(
                [
                    dbc.CardHeader(html.H4("Delete Account", className="text-danger")),
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.P(
                                                [
                                                    html.Strong("Warning: "),
                                                    "Deleting your account is permanent and cannot be undone. "
                                                    "All your data, including executions and scripts, will be permanently removed.",
                                                ],
                                                className="text-muted",
                                            ),
                                            dbc.Button(
                                                "Delete My Account",
                                                id="delete-account-btn",
                                                color="danger",
                                                outline=True,
                                            ),
                                            dbc.Alert(
                                                id="delete-account-alert",
                                                is_open=False,
                                                dismissable=True,
                                            ),
                                        ],
                                        width=12,
                                    ),
                                ]
                            ),
                        ]
                    ),
                ],
                className="mt-4 border-danger",
            ),
            # Delete Account Confirmation Modal
            dbc.Modal(
                [
                    dbc.ModalHeader(
                        dbc.ModalTitle("Confirm Account Deletion"),
                        close_button=True,
                    ),
                    dbc.ModalBody(
                        [
                            html.P(
                                "Are you sure you want to delete your account?",
                                className="fw-bold",
                            ),
                            html.P(
                                "This action is irreversible. All your data will be permanently deleted, including:",
                                className="text-muted",
                            ),
                            html.Ul(
                                [
                                    html.Li("All your execution history and logs"),
                                    html.Li("Any scripts you have created"),
                                    html.Li("Your Google Earth Engine credentials"),
                                    html.Li("Your account settings and profile"),
                                ],
                                className="text-muted",
                            ),
                            html.Hr(),
                            html.P(
                                "To confirm, type your email address below:",
                                className="mb-2",
                            ),
                            dbc.Input(
                                id="delete-account-confirm-email",
                                type="email",
                                placeholder="Enter your email address",
                                className="mb-3",
                            ),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "Cancel",
                                id="delete-account-cancel-btn",
                                color="secondary",
                                outline=True,
                            ),
                            dbc.Button(
                                "Delete My Account",
                                id="delete-account-confirm-btn",
                                color="danger",
                                disabled=True,
                            ),
                        ]
                    ),
                ],
                id="delete-account-modal",
                is_open=False,
                centered=True,
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
                                        children=f"{STATUS_REFRESH_INTERVAL // 1000}s",
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
            # Time-independent status information (not affected by time period tabs)
            dbc.Card(
                [
                    dbc.CardHeader(
                        html.H4(_("Current System Status"), id="current-system-status-title")
                    ),
                    dbc.CardBody(
                        [
                            dcc.Loading(
                                id="loading-status-summary",
                                children=[
                                    html.Div(
                                        id="status-summary",
                                        children=[
                                            # Skeleton loader for better perceived performance
                                            html.Div(
                                                [
                                                    html.Div(
                                                        [
                                                            html.Div(
                                                                className="skeleton-text skeleton-title mb-3"
                                                            ),
                                                            html.Div(
                                                                [
                                                                    html.Div(
                                                                        className="skeleton-stat",
                                                                        style={"width": "30%"},
                                                                    ),
                                                                    html.Div(
                                                                        className="skeleton-stat",
                                                                        style={"width": "30%"},
                                                                    ),
                                                                    html.Div(
                                                                        className="skeleton-stat",
                                                                        style={"width": "30%"},
                                                                    ),
                                                                ],
                                                                className="d-flex justify-content-between mb-3",
                                                            ),
                                                            html.Div(
                                                                className="skeleton-text skeleton-subtitle mb-2"
                                                            ),
                                                            html.Div(
                                                                [
                                                                    html.Div(
                                                                        className="skeleton-stat",
                                                                        style={"width": "20%"},
                                                                    ),
                                                                    html.Div(
                                                                        className="skeleton-stat",
                                                                        style={"width": "20%"},
                                                                    ),
                                                                ],
                                                                className="d-flex justify-content-between",
                                                            ),
                                                        ],
                                                        className="status-skeleton",
                                                    )
                                                ],
                                                className="p-3",
                                            )
                                        ],
                                    )
                                ],
                                type="default",
                                color="#007bff",
                            ),
                            html.Hr(),
                            html.H5(_("Deployment Information"), className="card-title mt-4"),
                            dcc.Loading(
                                id="loading-deployment-info",
                                children=[html.Div(id="deployment-info-summary")],
                                type="default",
                                color="#007bff",
                            ),
                            html.Hr(),
                            html.Div(id="cluster-status-title"),
                            dcc.Loading(
                                id="loading-cluster-info",
                                children=[html.Div(id="cluster-info-summary")],
                                type="default",
                                color="#007bff",
                            ),
                        ]
                    ),
                ],
                className="mb-4",
            ),
            # Time-dependent charts and statistics (affected by time period selection)
            dbc.Card(
                [
                    dbc.CardHeader(html.H4(_("System Status Trends"))),
                    dbc.CardBody(
                        [
                            # Time period selector tabs
                            html.Div(
                                [
                                    html.Ul(
                                        [
                                            html.Li(
                                                [
                                                    html.A(
                                                        _("Last 24 Hours"),
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
                                                        _("Last Week"),
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
                                                        _("Last Month"),
                                                        className="nav-link",
                                                        id="status-tab-month",
                                                        style={"cursor": "pointer"},
                                                    )
                                                ],
                                                className="nav-item",
                                            ),
                                            html.Li(
                                                [
                                                    html.A(
                                                        _("Last Year"),
                                                        className="nav-link",
                                                        id="status-tab-year",
                                                        style={"cursor": "pointer"},
                                                    )
                                                ],
                                                className="nav-item",
                                            ),
                                            html.Li(
                                                [
                                                    html.A(
                                                        _("All Time"),
                                                        className="nav-link",
                                                        id="status-tab-all",
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
                            # Enhanced statistics sections (SUPERADMIN only) - time-dependent
                            *(
                                [
                                    html.Div(
                                        [
                                            # Stats summary and charts share a single loader to simplify layout
                                            dcc.Loading(
                                                id="loading-stats-charts",
                                                children=[
                                                    html.Div(id="stats-summary-cards"),
                                                    html.Div(id="stats-additional-charts"),
                                                ],
                                                type="default",
                                                color="#007bff",
                                            ),
                                        ],
                                        className="mb-4",
                                    ),
                                    html.Div(
                                        [
                                            html.H6(
                                                "Countries with new user registrations",
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
                                ]
                                if is_admin_user
                                else []
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
                    _(
                        "Access denied. Administrator privileges required to access admin functions."
                    ),
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
                                    _("Administration Panel"),
                                ],
                                className="mb-4",
                            )
                        ]
                    )
                ]
            ),
            # Rate Limiting Management Section (ADMIN and SUPERADMIN)
            *(
                [
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                html.H4(
                                    [
                                        html.I(className="fas fa-tachometer-alt me-2"),
                                        _("Rate Limiting Management"),
                                    ]
                                )
                            ),
                            dbc.CardBody(
                                [
                                    # Rate Limiting Status Summary
                                    html.Div(
                                        [
                                            html.H5(
                                                _("Current & Historical Rate Limit Breaches"),
                                                className="mb-3",
                                            ),
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        dbc.Button(
                                                            [
                                                                html.I(
                                                                    className="fas fa-sync-alt me-2"
                                                                ),
                                                                _("Refresh Breaches"),
                                                            ],
                                                            id="refresh-rate-limit-breaches-btn",
                                                            color="primary",
                                                            className="mb-2",
                                                        ),
                                                        width="auto",
                                                    ),
                                                    dbc.Col(
                                                        dbc.Button(
                                                            [
                                                                html.I(
                                                                    className="fas fa-undo me-2"
                                                                ),
                                                                _("Cancel Selected Limit"),
                                                            ],
                                                            id="reset-selected-rate-limit-btn",
                                                            color="danger",
                                                            outline=True,
                                                            className="mb-2",
                                                            disabled=role != "SUPERADMIN",
                                                            style={
                                                                "display": "inline-flex"
                                                                if role == "SUPERADMIN"
                                                                else "none"
                                                            },
                                                        ),
                                                        width="auto",
                                                    ),
                                                    dbc.Col(
                                                        dbc.Button(
                                                            [
                                                                html.I(
                                                                    className="fas fa-refresh me-2"
                                                                ),
                                                                _("Reset All Rate Limits"),
                                                            ],
                                                            id="admin-reset-rate-limits-btn",
                                                            color="danger",
                                                            className="mb-2",
                                                        ),
                                                        width="auto",
                                                    ),
                                                    dbc.Col(
                                                        html.Div(
                                                            [
                                                                html.Span(
                                                                    id="rate-limit-breaches-total-count",
                                                                    children="Total: 0",
                                                                    className="text-muted fw-bold",
                                                                ),
                                                                html.Span(
                                                                    [
                                                                        " · ",
                                                                        _(
                                                                            "Active and historical events"
                                                                        ),
                                                                    ],
                                                                    className="text-muted ms-2",
                                                                ),
                                                            ],
                                                            className="d-flex align-items-center justify-content-end",
                                                        ),
                                                        width=True,
                                                    ),
                                                ],
                                                className="align-items-center mb-3 g-2",
                                            ),
                                            create_responsive_table(
                                                table_id="rate-limit-breaches-table",
                                                table_type="rate_limit_breaches",
                                                height="520px",
                                                style_data_conditional=[
                                                    {
                                                        "condition": "params.data && params.data.is_active",
                                                        "style": {
                                                            "backgroundColor": "#fff4e0",
                                                        },
                                                    },
                                                    {
                                                        "condition": "params.node && params.node.isSelected()",
                                                        "style": {
                                                            "boxShadow": "inset 0 0 0 2px #fd7e14",
                                                        },
                                                    },
                                                ],
                                            ),
                                            html.Div(
                                                [
                                                    html.Span(
                                                        [
                                                            html.I(
                                                                className="fas fa-circle text-warning me-2",
                                                            ),
                                                            _(
                                                                "Highlighted rows are active and can be cancelled individually."
                                                            ),
                                                        ],
                                                        className="text-muted small",
                                                    ),
                                                ],
                                                className="mt-2",
                                            ),
                                            dbc.Alert(
                                                id="admin-reset-rate-limits-alert",
                                                is_open=False,
                                                dismissable=True,
                                                duration=5000,
                                                className="mt-3",
                                            ),
                                        ],
                                        className="mb-4",
                                    ),
                                ]
                            ),
                        ],
                        className="mb-4",
                    ),
                ]
                if role in ("ADMIN", "SUPERADMIN")
                else []
            ),
            # News Management Section (ADMIN and SUPERADMIN)
            *(
                [
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                html.H4(
                                    [
                                        html.I(className="fas fa-newspaper me-2"),
                                        _("News Management"),
                                    ]
                                )
                            ),
                            dbc.CardBody(
                                [
                                    html.Div(
                                        [
                                            html.H5(
                                                _("Manage News Items"),
                                                className="mb-3",
                                            ),
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        dbc.Button(
                                                            [
                                                                html.I(
                                                                    className="fas fa-sync-alt me-2"
                                                                ),
                                                                _("Refresh"),
                                                            ],
                                                            id="admin-refresh-news-btn",
                                                            color="secondary",
                                                            outline=True,
                                                            className="mb-2",
                                                        ),
                                                        width="auto",
                                                    ),
                                                    dbc.Col(
                                                        dbc.Button(
                                                            [
                                                                html.I(
                                                                    className="fas fa-plus me-2"
                                                                ),
                                                                _("Create News Item"),
                                                            ],
                                                            id="admin-create-news-btn",
                                                            color="primary",
                                                            className="mb-2",
                                                        ),
                                                        width="auto",
                                                    ),
                                                    dbc.Col(
                                                        dbc.Button(
                                                            [
                                                                html.I(
                                                                    className="fas fa-edit me-2"
                                                                ),
                                                                _("Edit"),
                                                            ],
                                                            id="admin-edit-news-btn",
                                                            color="secondary",
                                                            outline=True,
                                                            className="mb-2",
                                                            disabled=True,
                                                        ),
                                                        width="auto",
                                                    ),
                                                    dbc.Col(
                                                        dbc.Button(
                                                            [
                                                                html.I(
                                                                    className="fas fa-trash me-2"
                                                                ),
                                                                _("Delete"),
                                                            ],
                                                            id="admin-delete-news-btn",
                                                            color="secondary",
                                                            outline=True,
                                                            className="mb-2",
                                                            disabled=True,
                                                        ),
                                                        width="auto",
                                                    ),
                                                ],
                                                className="align-items-center mb-3 g-2",
                                            ),
                                            # News Items Table
                                            html.Div(
                                                id="admin-news-table-container",
                                                children=[
                                                    dbc.Spinner(
                                                        html.Div(
                                                            id="admin-news-table",
                                                            children=_("Loading news items..."),
                                                        ),
                                                        color="primary",
                                                    ),
                                                ],
                                            ),
                                            # Store for selected news item
                                            dcc.Store(id="admin-selected-news-id"),
                                            # Interval to trigger initial news load
                                            dcc.Interval(
                                                id="admin-news-load-interval",
                                                interval=500,  # 500ms delay after render
                                                max_intervals=1,  # Only fire once
                                            ),
                                            dbc.Alert(
                                                id="admin-news-alert",
                                                is_open=False,
                                                dismissable=True,
                                                duration=5000,
                                                className="mt-3",
                                            ),
                                        ],
                                        className="mb-4",
                                    ),
                                ]
                            ),
                        ],
                        className="mb-4",
                    ),
                    # News Create/Edit Modal
                    dbc.Modal(
                        [
                            dbc.ModalHeader(
                                dbc.ModalTitle(
                                    id="admin-news-modal-title",
                                    children=_("Create News Item"),
                                ),
                                close_button=True,
                            ),
                            dbc.ModalBody(
                                [
                                    dbc.Form(
                                        [
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            dbc.Label(_("Title *")),
                                                            dbc.Input(
                                                                id="admin-news-title",
                                                                type="text",
                                                                placeholder=_("Enter news title"),
                                                                required=True,
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
                                                            dbc.Label(
                                                                [
                                                                    _(
                                                                        "Message (Markdown supported) *"
                                                                    ),
                                                                    html.I(
                                                                        className="fas fa-info-circle ms-2",
                                                                        id="admin-news-markdown-tooltip",
                                                                        style={"cursor": "pointer"},
                                                                    ),
                                                                ]
                                                            ),
                                                            dbc.Tooltip(
                                                                _(
                                                                    "Use Markdown formatting: **bold**, *italic*, [link](url), lists, etc. Will be converted to HTML."
                                                                ),
                                                                target="admin-news-markdown-tooltip",
                                                            ),
                                                            dbc.Textarea(
                                                                id="admin-news-message",
                                                                placeholder=_(
                                                                    "Enter news message using Markdown..."
                                                                ),
                                                                style={"height": "150px"},
                                                                required=True,
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
                                                            dbc.Label(_("Preview")),
                                                            html.Div(
                                                                id="admin-news-preview",
                                                                className="border rounded p-3 bg-light",
                                                                style={
                                                                    "minHeight": "100px",
                                                                    "maxHeight": "200px",
                                                                    "overflow": "auto",
                                                                },
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
                                                            dbc.Label(_("Link URL (optional)")),
                                                            dbc.Input(
                                                                id="admin-news-link-url",
                                                                type="url",
                                                                placeholder="https://example.com",
                                                            ),
                                                        ],
                                                        width=6,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            dbc.Label(_("Link Text (optional)")),
                                                            dbc.Input(
                                                                id="admin-news-link-text",
                                                                type="text",
                                                                placeholder=_("Read more..."),
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
                                                            dbc.Label(_("Target Platforms *")),
                                                            dcc.Dropdown(
                                                                id="admin-news-platforms",
                                                                options=[
                                                                    {
                                                                        "label": _("QGIS Plugin"),
                                                                        "value": "qgis_plugin",
                                                                    },
                                                                    {
                                                                        "label": _("Web App"),
                                                                        "value": "web",
                                                                    },
                                                                    {
                                                                        "label": _("API UI"),
                                                                        "value": "api_ui",
                                                                    },
                                                                ],
                                                                multi=True,
                                                                placeholder=_(
                                                                    "Select target platforms..."
                                                                ),
                                                                value=[
                                                                    "qgis_plugin",
                                                                    "web",
                                                                    "api_ui",
                                                                ],
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
                                                            dbc.Label(
                                                                [
                                                                    _("Target Roles (optional)"),
                                                                    html.I(
                                                                        className="fas fa-info-circle ms-2",
                                                                        id="admin-news-roles-tooltip",
                                                                        style={"cursor": "pointer"},
                                                                    ),
                                                                ]
                                                            ),
                                                            dbc.Tooltip(
                                                                _(
                                                                    "Leave empty to show to all users including unauthenticated. Select specific roles to restrict visibility."
                                                                ),
                                                                target="admin-news-roles-tooltip",
                                                            ),
                                                            dcc.Dropdown(
                                                                id="admin-news-roles",
                                                                options=[
                                                                    {
                                                                        "label": _("Regular Users"),
                                                                        "value": "USER",
                                                                    },
                                                                    {
                                                                        "label": _("Admins"),
                                                                        "value": "ADMIN",
                                                                    },
                                                                    {
                                                                        "label": _("Super Admins"),
                                                                        "value": "SUPERADMIN",
                                                                    },
                                                                ],
                                                                multi=True,
                                                                placeholder=_(
                                                                    "All users (no restriction)"
                                                                ),
                                                                value=[],
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
                                                            dbc.Label(_("News Type")),
                                                            dbc.Select(
                                                                id="admin-news-type",
                                                                options=[
                                                                    {
                                                                        "label": _("Announcement"),
                                                                        "value": "announcement",
                                                                    },
                                                                    {
                                                                        "label": _("Warning"),
                                                                        "value": "warning",
                                                                    },
                                                                    {
                                                                        "label": _("Release"),
                                                                        "value": "release",
                                                                    },
                                                                    {
                                                                        "label": _("Tip"),
                                                                        "value": "tip",
                                                                    },
                                                                    {
                                                                        "label": _("Maintenance"),
                                                                        "value": "maintenance",
                                                                    },
                                                                ],
                                                                value="announcement",
                                                            ),
                                                        ],
                                                        width=6,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            dbc.Label(_("Priority")),
                                                            dbc.Input(
                                                                id="admin-news-priority",
                                                                type="number",
                                                                value=0,
                                                                min=0,
                                                                max=100,
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
                                                            dbc.Label(
                                                                _("Min Plugin Version (optional)")
                                                            ),
                                                            dbc.Input(
                                                                id="admin-news-min-version",
                                                                type="text",
                                                                placeholder=_("e.g., 1.0.0"),
                                                            ),
                                                        ],
                                                        width=6,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            dbc.Label(
                                                                _("Max Plugin Version (optional)")
                                                            ),
                                                            dbc.Input(
                                                                id="admin-news-max-version",
                                                                type="text",
                                                                placeholder=_("e.g., 2.0.0"),
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
                                                            dbc.Label(_("Start Date (optional)")),
                                                            dcc.DatePickerSingle(
                                                                id="admin-news-start-date",
                                                                placeholder=_(
                                                                    "Select start date..."
                                                                ),
                                                                display_format="YYYY-MM-DD",
                                                            ),
                                                        ],
                                                        width=6,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            dbc.Label(_("End Date (optional)")),
                                                            dcc.DatePickerSingle(
                                                                id="admin-news-end-date",
                                                                placeholder=_("Select end date..."),
                                                                display_format="YYYY-MM-DD",
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
                                                            dbc.Checkbox(
                                                                id="admin-news-is-active",
                                                                label=_(
                                                                    "Active (visible to users)"
                                                                ),
                                                                value=True,
                                                            ),
                                                        ],
                                                        width=12,
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                        ]
                                    ),
                                    dbc.Alert(
                                        id="admin-news-modal-alert",
                                        is_open=False,
                                        dismissable=True,
                                        duration=5000,
                                    ),
                                ]
                            ),
                            dbc.ModalFooter(
                                [
                                    dbc.Button(
                                        _("Cancel"),
                                        id="admin-news-cancel-btn",
                                        color="secondary",
                                        className="me-2",
                                    ),
                                    dbc.Button(
                                        _("Save"),
                                        id="admin-news-save-btn",
                                        color="primary",
                                    ),
                                ]
                            ),
                        ],
                        id="admin-news-modal",
                        size="lg",
                        is_open=False,
                    ),
                    # Delete Confirmation Modal
                    dbc.Modal(
                        [
                            dbc.ModalHeader(
                                dbc.ModalTitle(_("Confirm Delete")),
                                close_button=True,
                            ),
                            dbc.ModalBody(
                                _(
                                    "Are you sure you want to delete this news item? This action cannot be undone."
                                )
                            ),
                            dbc.ModalFooter(
                                [
                                    dbc.Button(
                                        _("Cancel"),
                                        id="admin-news-delete-cancel-btn",
                                        color="secondary",
                                        className="me-2",
                                    ),
                                    dbc.Button(
                                        _("Delete"),
                                        id="admin-news-delete-confirm-btn",
                                        color="danger",
                                    ),
                                ]
                            ),
                        ],
                        id="admin-news-delete-modal",
                        is_open=False,
                    ),
                ]
                if role in ("ADMIN", "SUPERADMIN")
                else []
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
                                        _("Create New User"),
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
                                                            dbc.Label(_("Name *")),
                                                            dbc.Input(
                                                                id="admin-new-user-name",
                                                                type="text",
                                                                placeholder=_("Enter full name"),
                                                                required=True,
                                                            ),
                                                        ],
                                                        width=6,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            dbc.Label(_("Email *")),
                                                            dbc.Input(
                                                                id="admin-new-user-email",
                                                                type="email",
                                                                placeholder=_(
                                                                    "Enter email address"
                                                                ),
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
                                                            dbc.Label(_("Password *")),
                                                            dbc.Input(
                                                                id="admin-new-user-password",
                                                                type="password",
                                                                placeholder=_(
                                                                    "Set password for user"
                                                                ),
                                                                required=True,
                                                            ),
                                                        ],
                                                        width=6,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            dbc.Label(_("Confirm Password *")),
                                                            dbc.Input(
                                                                id="admin-new-user-confirm-password",
                                                                type="password",
                                                                placeholder=_("Confirm password"),
                                                                required=True,
                                                            ),
                                                        ],
                                                        width=6,
                                                    ),
                                                ],
                                                className="mb-2",
                                            ),
                                            html.Div(
                                                id="admin-new-user-password-requirements",
                                                children=[
                                                    html.Small(
                                                        _("Password requirements:"),
                                                        className="text-muted d-block mb-1",
                                                    ),
                                                    html.Ul(
                                                        [
                                                            html.Li(
                                                                _("At least 12 characters"),
                                                                id="admin-new-user-req-length",
                                                                className="text-muted",
                                                            ),
                                                            html.Li(
                                                                _("Uppercase letter (A-Z)"),
                                                                id="admin-new-user-req-uppercase",
                                                                className="text-muted",
                                                            ),
                                                            html.Li(
                                                                _("Lowercase letter (a-z)"),
                                                                id="admin-new-user-req-lowercase",
                                                                className="text-muted",
                                                            ),
                                                            html.Li(
                                                                _("Number (0-9)"),
                                                                id="admin-new-user-req-number",
                                                                className="text-muted",
                                                            ),
                                                            html.Li(
                                                                _(
                                                                    "Special character (!@#$%^&*()-_=+[]{}|;:,.<>?/)"
                                                                ),
                                                                id="admin-new-user-req-special",
                                                                className="text-muted",
                                                            ),
                                                            html.Li(
                                                                _("Passwords match"),
                                                                id="admin-new-user-req-match",
                                                                className="text-muted",
                                                            ),
                                                        ],
                                                        className="small mb-0 ps-3",
                                                        style={"listStyleType": "none"},
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            dbc.Label(_("Institution")),
                                                            dbc.Input(
                                                                id="admin-new-user-institution",
                                                                type="text",
                                                                placeholder=_(
                                                                    "Enter institution/organization"
                                                                ),
                                                            ),
                                                        ],
                                                        width=6,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            dbc.Label(_("Country")),
                                                            dcc.Dropdown(
                                                                id="admin-new-user-country",
                                                                options=[],
                                                                placeholder=_("Select country..."),
                                                                searchable=True,
                                                                clearable=True,
                                                                className="dash-dropdown",
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
                                                            dbc.Label(_("Role *")),
                                                            dbc.Select(
                                                                id="admin-new-user-role",
                                                                options=[
                                                                    {
                                                                        "label": _("User"),
                                                                        "value": "USER",
                                                                    },
                                                                    {
                                                                        "label": _("Admin"),
                                                                        "value": "ADMIN",
                                                                    },
                                                                    {
                                                                        "label": _("Super Admin"),
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
                                                                    _("Create User"),
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
                                                                    _("Clear Form"),
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
                            dbc.Alert(
                                [
                                    html.I(className="fas fa-info-circle me-2"),
                                    "Upload a .tar.gz archive containing your script and a ",
                                    html.Code("configuration.json"),
                                    " file. The script name and metadata are read from the configuration file.",
                                ],
                                color="info",
                                className="mb-3",
                            ),
                            dbc.Form(
                                [
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Label("Script Archive (.tar.gz) *"),
                                                    dcc.Upload(
                                                        id="admin-script-upload",
                                                        children=html.Div(
                                                            [
                                                                html.I(
                                                                    className="fas fa-cloud-upload-alt me-2"
                                                                ),
                                                                "Drag and Drop or ",
                                                                html.A("Select Script Archive"),
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
                                                        accept=".tar.gz,.gz",
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
                            ),
                        ]
                    ),
                ],
                className="mb-4",
            ),
        ]
    )
