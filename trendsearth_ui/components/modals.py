"""Modal components for the application."""

from dash import dcc, html
import dash_bootstrap_components as dbc


def json_modal():
    """Create the JSON/logs modal."""
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle(id="json-modal-title")),
            dbc.ModalBody(
                [
                    html.Div(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.ButtonGroup(
                                                [
                                                    dbc.Button(
                                                        "Refresh Logs",
                                                        id="refresh-logs-btn",
                                                        color="primary",
                                                        style={"display": "none"},
                                                    ),
                                                    dbc.Button(
                                                        "Download JSON",
                                                        id="download-json-btn",
                                                        color="secondary",
                                                    ),
                                                ]
                                            ),
                                        ],
                                        width="auto",
                                    ),
                                    dbc.Col(
                                        [
                                            html.Div(
                                                [
                                                    html.Span(
                                                        "Auto-refresh in: ",
                                                        className="me-2",
                                                        style={"display": "none"},
                                                        id="logs-countdown-label",
                                                    ),
                                                    html.Span(
                                                        id="logs-countdown",
                                                        children="10s",
                                                        className="badge bg-info",
                                                        style={"display": "none"},
                                                    ),
                                                ],
                                                className="d-flex align-items-center",
                                            )
                                        ],
                                        width="auto",
                                    ),
                                ],
                                className="justify-content-between mb-3",
                            ),
                        ]
                    ),
                    html.Div(id="json-modal-body"),
                    dcc.Download(id="download-json"),
                    dcc.Interval(
                        id="logs-refresh-interval",
                        interval=10 * 1000,  # 10 seconds
                        n_intervals=0,
                        disabled=True,
                    ),
                    dcc.Interval(
                        id="logs-countdown-interval",
                        interval=1000,  # 1 second for countdown
                        n_intervals=0,
                        disabled=True,
                    ),
                ]
            ),
        ],
        id="json-modal",
        size="xl",
        is_open=False,
    )


def edit_user_modal():
    """Create the edit user modal."""
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Edit User")),
            dbc.ModalBody(
                [
                    dbc.Form(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Name"),
                                            dbc.Input(
                                                id="edit-user-name",
                                                type="text",
                                                placeholder="Enter name",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Email"),
                                            dbc.Input(
                                                id="edit-user-email",
                                                type="email",
                                                placeholder="Enter email",
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
                                                id="edit-user-institution",
                                                type="text",
                                                placeholder="Enter institution",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Country"),
                                            dbc.Input(
                                                id="edit-user-country",
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
                                            dbc.Label("Role"),
                                            dbc.Select(
                                                id="edit-user-role",
                                                options=[
                                                    {"label": "User", "value": "USER"},
                                                    {"label": "Admin", "value": "ADMIN"},
                                                    {"label": "Super Admin", "value": "SUPERADMIN"},
                                                ],
                                                value="USER",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Email Notifications"),
                                            html.Div(
                                                [
                                                    dbc.Switch(
                                                        id="edit-user-email-notifications-switch",
                                                        value=True,
                                                        className="mb-1",
                                                    ),
                                                    html.Small(
                                                        "Execution completion emails",
                                                        className="text-muted",
                                                    ),
                                                ],
                                            ),
                                        ],
                                        width=6,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            html.Hr(),
                            html.H5("Google Earth Engine Credentials", className="mb-3"),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.Div(
                                                [
                                                    html.H6("Current Status"),
                                                    html.Div(
                                                        id="edit-user-gee-status-display",
                                                        className="mb-3",
                                                    ),
                                                ]
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
                                            html.H6("Admin Actions"),
                                            dbc.ButtonGroup(
                                                [
                                                    dbc.Button(
                                                        "Test Credentials",
                                                        id="edit-user-gee-test-btn",
                                                        color="info",
                                                        outline=True,
                                                        size="sm",
                                                        disabled=True,
                                                    ),
                                                    dbc.Button(
                                                        "Delete Credentials",
                                                        id="edit-user-gee-delete-btn",
                                                        color="danger",
                                                        outline=True,
                                                        size="sm",
                                                        disabled=True,
                                                    ),
                                                ],
                                                className="mb-2",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            html.H6("Upload Service Account"),
                                            dcc.Upload(
                                                id="edit-user-gee-service-account-upload",
                                                children=dbc.Button(
                                                    [
                                                        html.I(className="fas fa-upload me-2"),
                                                        "Upload for User",
                                                    ],
                                                    color="secondary",
                                                    outline=True,
                                                    size="sm",
                                                ),
                                                accept=".json",
                                                max_size=1024 * 1024,  # 1MB max
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
                                            dbc.Alert(
                                                id="edit-user-gee-alert",
                                                is_open=False,
                                                dismissable=True,
                                            ),
                                        ],
                                        width=12,
                                    ),
                                ]
                            ),
                            html.Hr(),
                            html.H5("Change Password", className="mb-3"),
                            dbc.Alert(
                                id="admin-password-change-alert",
                                dismissable=True,
                                is_open=False,
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("New Password"),
                                            dbc.Input(
                                                id="admin-new-password",
                                                type="password",
                                                placeholder="Enter new password",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Confirm Password"),
                                            dbc.Input(
                                                id="admin-confirm-password",
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
                                                id="admin-change-password-btn",
                                                color="warning",
                                                outline=True,
                                            ),
                                        ],
                                        width="auto",
                                    ),
                                ],
                                className="mb-3",
                            ),
                        ]
                    )
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button("Cancel", id="cancel-edit-user", className="me-1", outline=True),
                    dbc.Button(
                        [html.I(className="fas fa-trash me-2"), "Delete User"],
                        id="delete-edit-user",
                        color="danger",
                        className="me-auto",
                        outline=True,
                    ),
                    dbc.Button("Save Changes", id="save-edit-user", color="primary"),
                ]
            ),
        ],
        id="edit-user-modal",
        is_open=False,
    )


def edit_script_modal():
    """Create the edit script modal."""
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Edit Script")),
            dbc.ModalBody(
                [
                    dbc.Form(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Script Name"),
                                            dbc.Input(
                                                id="edit-script-name",
                                                type="text",
                                                placeholder="Enter script name",
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
                                            dbc.Label("Description"),
                                            dbc.Textarea(
                                                id="edit-script-description",
                                                placeholder="Enter description",
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
                                            dbc.Label("Status"),
                                            dbc.Select(
                                                id="edit-script-status",
                                                options=[
                                                    {"label": "Published", "value": "PUBLISHED"},
                                                    {"label": "Draft", "value": "DRAFT"},
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
                                            dbc.Label("Upload New Script File (optional)"),
                                            dcc.Upload(
                                                id="edit-script-upload",
                                                children=html.Div(
                                                    ["Drag and Drop or ", html.A("Select Files")]
                                                ),
                                                style={
                                                    "width": "100%",
                                                    "height": "60px",
                                                    "lineHeight": "60px",
                                                    "borderWidth": "1px",
                                                    "borderStyle": "dashed",
                                                    "borderRadius": "5px",
                                                    "textAlign": "center",
                                                    "margin": "10px",
                                                },
                                                multiple=False,
                                            ),
                                        ],
                                        width=12,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            html.Hr(),
                            html.H6("Access Control", className="mb-3"),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Button(
                                                [
                                                    html.I(className="fas fa-shield-alt me-2"),
                                                    "Manage Access Control",
                                                ],
                                                id="open-access-control",
                                                color="info",
                                                outline=True,
                                                className="w-100",
                                            ),
                                            dbc.FormText(
                                                "Click to view and modify script access permissions"
                                            ),
                                        ],
                                        width=12,
                                    ),
                                ],
                                className="mb-3",
                            ),
                        ]
                    )
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button("Cancel", id="cancel-edit-script", className="me-1", outline=True),
                    dbc.Button(
                        [
                            html.I(className="fas fa-trash me-2"),
                            "Delete Script",
                        ],
                        id="delete-edit-script",
                        color="danger",
                        className="me-1",
                        outline=True,
                    ),
                    dbc.Button("Save Changes", id="save-edit-script", color="primary"),
                ]
            ),
        ],
        id="edit-script-modal",
        is_open=False,
    )


def map_modal():
    """Create the map modal."""
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Execution Area Map")),
            dbc.ModalBody(
                [
                    html.Div(id="map-container", style={"height": "600px"}),
                    html.Div(id="map-info", className="mt-3"),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button("Close", id="close-map-modal", color="secondary"),
                ]
            ),
        ],
        id="map-modal",
        size="xl",
        is_open=False,
    )


def delete_user_modal():
    """Create the delete user confirmation modal."""
    return dbc.Modal(
        [
            dbc.ModalHeader(
                dbc.ModalTitle(
                    [
                        html.I(className="fas fa-exclamation-triangle text-warning me-2"),
                        "Confirm User Deletion",
                    ]
                )
            ),
            dbc.ModalBody(
                [
                    html.P(
                        [
                            "Are you sure you want to delete the user ",
                            html.Strong(id="delete-user-name", children=""),
                            " (",
                            html.Strong(id="delete-user-email", children=""),
                            ")?",
                        ]
                    ),
                    dbc.Alert(
                        [
                            html.I(className="fas fa-exclamation-triangle me-2"),
                            html.Strong("Warning: "),
                            "This action cannot be undone. All user data and associated executions will be permanently deleted.",
                        ],
                        color="warning",
                        className="mb-0",
                    ),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button(
                        "Cancel",
                        id="cancel-delete-user",
                        color="secondary",
                        className="me-2",
                    ),
                    dbc.Button(
                        [html.I(className="fas fa-trash me-2"), "Delete User"],
                        id="confirm-delete-user",
                        color="danger",
                    ),
                ]
            ),
        ],
        id="delete-user-modal",
        is_open=False,
    )


def delete_script_modal():
    """Create the delete script confirmation modal."""
    return dbc.Modal(
        [
            dbc.ModalHeader(
                dbc.ModalTitle(
                    [
                        html.I(className="fas fa-exclamation-triangle text-warning me-2"),
                        "Delete Script",
                    ]
                )
            ),
            dbc.ModalBody(
                [
                    html.P(
                        [
                            "Are you sure you want to delete the script ",
                            html.Strong(id="delete-script-name", children=""),
                            "?",
                        ]
                    ),
                    html.P(
                        [
                            html.Strong("Warning: "),
                            "This action cannot be undone. All data associated with this script will be permanently removed.",
                        ],
                        className="text-danger",
                    ),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button(
                        "Cancel",
                        id="cancel-delete-script",
                        color="secondary",
                        className="me-2",
                    ),
                    dbc.Button(
                        [html.I(className="fas fa-trash me-2"), "Delete Script"],
                        id="confirm-delete-script",
                        color="danger",
                    ),
                ]
            ),
        ],
        id="delete-script-modal",
        is_open=False,
    )


def access_control_modal():
    """Create the access control modal for scripts."""
    return dbc.Modal(
        [
            dbc.ModalHeader(
                dbc.ModalTitle(
                    [
                        html.I(className="fas fa-shield-alt me-2"),
                        "Script Access Control",
                    ]
                )
            ),
            dbc.ModalBody(
                [
                    dcc.Store(id="access-control-script-data"),
                    dbc.Alert(
                        id="access-control-alert",
                        is_open=False,
                        dismissable=True,
                    ),
                    html.Div(
                        [
                            html.H6("Current Access Settings", className="mb-3"),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Script Name"),
                                            html.P(
                                                id="access-control-script-name", className="fw-bold"
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Access Status"),
                                            html.P(id="access-control-status", className="fw-bold"),
                                        ],
                                        width=6,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            html.Hr(),
                            html.H6("Modify Access Settings", className="mb-3"),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Access Type"),
                                            dbc.RadioItems(
                                                id="access-control-type",
                                                options=[
                                                    {
                                                        "label": "Open (All authenticated users)",
                                                        "value": "unrestricted",
                                                    },
                                                    {
                                                        "label": "Role-based restrictions",
                                                        "value": "role_restricted",
                                                    },
                                                    {
                                                        "label": "User-specific restrictions",
                                                        "value": "user_restricted",
                                                    },
                                                    {
                                                        "label": "Role and User restrictions",
                                                        "value": "role_and_user_restricted",
                                                    },
                                                ],
                                                value="unrestricted",
                                                className="mb-3",
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
                                            dbc.Label("Allowed Roles"),
                                            dcc.Dropdown(
                                                id="access-control-roles",
                                                options=[
                                                    {"label": "User", "value": "USER"},
                                                    {"label": "Admin", "value": "ADMIN"},
                                                    {"label": "Super Admin", "value": "SUPERADMIN"},
                                                ],
                                                multi=True,
                                                placeholder="Select roles (leave empty to remove role restrictions)",
                                            ),
                                            dbc.FormText(
                                                "Only users with these roles can access the script"
                                            ),
                                        ],
                                        width=12,
                                    ),
                                ],
                                className="mb-3",
                                id="access-control-roles-section",
                                style={"display": "none"},
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Allowed Users"),
                                            html.Div(
                                                id="current-selected-users",
                                                className="mb-2",
                                                children=[
                                                    dbc.Alert(
                                                        "No users currently selected",
                                                        color="light",
                                                        className="mb-0 text-muted small",
                                                    )
                                                ],
                                            ),
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            dbc.InputGroup(
                                                                [
                                                                    dbc.Input(
                                                                        id="user-search-input",
                                                                        placeholder="Type user name or email to search...",
                                                                        debounce=True,
                                                                    ),
                                                                    dbc.Button(
                                                                        [
                                                                            html.I(
                                                                                className="fas fa-search me-1"
                                                                            ),
                                                                            "Search",
                                                                        ],
                                                                        id="user-search-btn",
                                                                        color="primary",
                                                                        outline=True,
                                                                    ),
                                                                ]
                                                            ),
                                                        ],
                                                        width=12,
                                                    ),
                                                ],
                                                className="mb-2",
                                            ),
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            html.Div(
                                                                dbc.Spinner(
                                                                    html.Div(
                                                                        id="user-search-spinner"
                                                                    ),
                                                                    size="sm",
                                                                    color="primary",
                                                                ),
                                                                id="user-search-loading",
                                                                style={"display": "none"},
                                                            ),
                                                        ],
                                                        width=12,
                                                    ),
                                                ],
                                                className="mb-2",
                                            ),
                                            dcc.Dropdown(
                                                id="access-control-users",
                                                options=[],
                                                multi=True,
                                                searchable=False,
                                                placeholder="Search for users above, then select from results...",
                                                optionHeight=50,
                                                maxHeight=200,
                                            ),
                                            dbc.FormText(
                                                "Search for users by name or email, then select specific users that can access the script"
                                            ),
                                        ],
                                        width=12,
                                    ),
                                ],
                                className="mb-3",
                                id="access-control-users-section",
                                style={"display": "none"},
                            ),
                        ]
                    ),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button(
                        "Cancel", id="cancel-access-control", className="me-1", outline=True
                    ),
                    dbc.Button(
                        "Clear All Restrictions",
                        id="clear-access-restrictions",
                        color="warning",
                        className="me-1",
                        outline=True,
                    ),
                    dbc.Button("Save Changes", id="save-access-control", color="primary"),
                ]
            ),
        ],
        id="access-control-modal",
        is_open=False,
        size="lg",
    )


def reset_rate_limits_modal():
    """Create the rate limiting reset confirmation modal."""
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("⚠️ Reset Rate Limits")),
            dbc.ModalBody(
                [
                    html.Div(
                        [
                            html.H5(
                                "Warning: This action cannot be undone!",
                                className="text-danger mb-3",
                            ),
                            html.P(
                                "You are about to reset all rate limits for the entire API system. This will:",
                                className="mb-2",
                            ),
                            html.Ul(
                                [
                                    html.Li("Clear all current rate limiting restrictions"),
                                    html.Li(
                                        "Allow all users to make unlimited requests temporarily"
                                    ),
                                    html.Li("Reset all rate limit counters to zero"),
                                    html.Li("Potentially increase server load significantly"),
                                ],
                                className="mb-3",
                            ),
                            dbc.Alert(
                                [
                                    html.I(className="fas fa-exclamation-triangle me-2"),
                                    "This is a system-wide operation that affects all users and should only be used in emergency situations or for maintenance purposes.",
                                ],
                                color="warning",
                                className="mb-3",
                            ),
                            html.P(
                                "Are you sure you want to proceed?", className="fw-bold text-center"
                            ),
                        ]
                    )
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button(
                        "Cancel",
                        id="cancel-reset-rate-limits",
                        color="secondary",
                        className="me-2",
                    ),
                    dbc.Button(
                        [html.I(className="fas fa-refresh me-2"), "Reset Rate Limits"],
                        id="confirm-reset-rate-limits",
                        color="danger",
                    ),
                ]
            ),
        ],
        id="reset-rate-limits-modal",
        is_open=False,
    )


def reset_individual_rate_limit_modal():
    """Create the individual rate limit reset confirmation modal."""
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("⚠️ Reset Individual Rate Limit")),
            dbc.ModalBody(
                [
                    html.Div(
                        [
                            html.H5(
                                "Reset this rate limit?",
                                className="text-warning mb-3",
                            ),
                            # Rate limit details will be populated by callback
                            html.Div(
                                id="individual-rate-limit-details",
                                className="mb-3",
                            ),
                            html.P(
                                "This will:",
                                className="mb-2",
                            ),
                            html.Ul(
                                [
                                    html.Li(
                                        "Clear all rate limit counters for this specific identifier"
                                    ),
                                    html.Li(
                                        "Allow this user/IP to start fresh with new request counters"
                                    ),
                                    html.Li("Not affect other active rate limits"),
                                ],
                                className="mb-3",
                            ),
                            dbc.Alert(
                                [
                                    html.I(className="fas fa-info-circle me-2"),
                                    "This action only resets the rate limit for the selected user or IP address. The rate limiting system will continue to track new requests.",
                                ],
                                color="info",
                                className="mb-3",
                            ),
                            html.P(
                                "Are you sure you want to proceed?", className="fw-bold text-center"
                            ),
                        ]
                    )
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button(
                        "Cancel",
                        id="cancel-reset-individual-rate-limit",
                        color="secondary",
                        className="me-2",
                    ),
                    dbc.Button(
                        [html.I(className="fas fa-undo me-2"), "Reset This Limit"],
                        id="confirm-reset-individual-rate-limit",
                        color="warning",
                    ),
                ]
            ),
        ],
        id="reset-individual-rate-limit-modal",
        is_open=False,
    )
