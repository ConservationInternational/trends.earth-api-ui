"""Modal components for the application."""

from dash import dcc, html
import dash_bootstrap_components as dbc

from ..i18n import gettext as _


def csv_export_modal():
    """Create the shared CSV export modal with date filtering controls."""
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle(_("Export as CSV"))),
            dbc.ModalBody(
                [
                    dbc.Alert(
                        id="csv-export-error-alert",
                        color="danger",
                        is_open=False,
                        dismissable=True,
                    ),
                    html.P(
                        _(
                            "Optionally filter by date range before exporting. "
                            "Leave blank to export all records."
                        )
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label(_("Filter date field")),
                                    dbc.Select(
                                        id="csv-export-date-field",
                                        options=[],
                                        value=None,
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
                                    dbc.Label(_("From (inclusive)")),
                                    dbc.Input(
                                        id="csv-export-date-from",
                                        type="date",
                                        placeholder="YYYY-MM-DD",
                                    ),
                                ],
                                width=6,
                            ),
                            dbc.Col(
                                [
                                    dbc.Label(_("To (inclusive)")),
                                    dbc.Input(
                                        id="csv-export-date-to",
                                        type="date",
                                        placeholder="YYYY-MM-DD",
                                    ),
                                ],
                                width=6,
                            ),
                        ],
                        className="mb-2",
                    ),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button(
                        _("Cancel"),
                        id="csv-export-cancel-btn",
                        color="secondary",
                        className="me-2",
                    ),
                    dbc.Button(
                        _("Export CSV"),
                        id="csv-export-confirm-btn",
                        color="primary",
                    ),
                ]
            ),
        ],
        id="csv-export-modal",
        is_open=False,
        backdrop="static",
    )


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
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Max Concurrent Executions"),
                                            dbc.Input(
                                                id="edit-user-max-concurrent-executions",
                                                type="number",
                                                min=1,
                                                step=1,
                                                placeholder="Default (3)",
                                            ),
                                            html.Small(
                                                "Leave empty to use system default",
                                                className="text-muted",
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
                                                id="edit-user-gee-service-account-alert",
                                                is_open=False,
                                                dismissable=True,
                                            ),
                                            dbc.Alert(
                                                id="edit-user-gee-management-alert",
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
                                className="mb-2",
                            ),
                            html.Div(
                                id="admin-password-requirements",
                                children=[
                                    html.Small(
                                        "Password requirements:",
                                        className="text-muted d-block mb-1",
                                    ),
                                    html.Ul(
                                        [
                                            html.Li(
                                                "At least 12 characters",
                                                id="admin-req-length",
                                                className="text-muted",
                                            ),
                                            html.Li(
                                                "Uppercase letter (A-Z)",
                                                id="admin-req-uppercase",
                                                className="text-muted",
                                            ),
                                            html.Li(
                                                "Lowercase letter (a-z)",
                                                id="admin-req-lowercase",
                                                className="text-muted",
                                            ),
                                            html.Li(
                                                "Number (0-9)",
                                                id="admin-req-number",
                                                className="text-muted",
                                            ),
                                            html.Li(
                                                "Special character (!@#$%^&*()-_=+[]{}|;:,.<>?/)",
                                                id="admin-req-special",
                                                className="text-muted",
                                            ),
                                            html.Li(
                                                "Passwords match",
                                                id="admin-req-match",
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
                                    dbc.Col(
                                        [
                                            dbc.Label("Uses GEE"),
                                            dbc.Checkbox(
                                                id="edit-script-uses-gee",
                                                value=True,
                                                label="Requires Google Earth Engine",
                                            ),
                                        ],
                                        width=6,
                                        className="d-flex flex-column justify-content-center",
                                    ),
                                ],
                                className="mb-3",
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Upload New Script Archive (optional)"),
                                            dcc.Upload(
                                                id="edit-script-upload",
                                                children=html.Div(
                                                    [
                                                        html.I(
                                                            className="fas fa-cloud-upload-alt me-2"
                                                        ),
                                                        "Drag and Drop or ",
                                                        html.A("Select .tar.gz Archive"),
                                                    ]
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
                                                accept=".tar.gz,.gz",
                                            ),
                                            dbc.FormText(
                                                "Upload a new .tar.gz archive to update the script code. "
                                                "The archive must contain a configuration.json file."
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
                                    "This is a system-wide operation that affects all users and should only be used for emergency or maintenance purposes.",
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


def bulk_email_verify_modal():
    """Modal for 2FA-style verification when a large bulk email send is requested.

    Shown when the backend returns HTTP 428 because recipient count exceeds
    BULK_EMAIL_MAX_RECIPIENTS. The user must request and submit a 6-digit OTP.
    """
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle(id="bulk-email-verify-modal-title")),
            dbc.ModalBody(
                [
                    html.P(
                        "A large number of recipients were detected.  "
                        "A verification code has been (or will be) sent to your email address.",
                        id="bulk-email-verify-modal-body",
                    ),
                    dbc.Label("Enter 6-digit verification code"),
                    dbc.Input(
                        id="bulk-email-verify-code",
                        type="text",
                        maxLength=6,
                        placeholder="123456",
                        autocomplete="one-time-code",
                    ),
                    dbc.Alert(
                        id="bulk-email-verify-modal-alert",
                        is_open=False,
                        dismissable=True,
                        className="mt-2",
                    ),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button(
                        "Request Code",
                        id="bulk-email-request-code-btn",
                        color="secondary",
                        className="me-2",
                    ),
                    dbc.Button(
                        "Confirm Send",
                        id="bulk-email-verify-submit",
                        color="primary",
                        className="me-2",
                    ),
                    dbc.Button(
                        "Cancel",
                        id="bulk-email-verify-cancel",
                        color="light",
                    ),
                ]
            ),
        ],
        id="bulk-email-verify-modal",
        is_open=False,
        centered=True,
        backdrop="static",
    )


def bulk_email_switch_html_modal():
    """
    Warning modal shown when the user tries to switch from Template Fields
    to Raw HTML.  Switching is one-way: once the user confirms, the Fields
    tab is locked for the current session.

    On confirmation, two drafts are auto-saved via the server callback:
    * "<name> (templated)" — structured fields version preserved for reference
    * "<name> (html)"       — rendered HTML version the user continues editing
    """
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("⚠️ Switch to Raw HTML?")),
            dbc.ModalBody(
                [
                    html.P(
                        "Once you switch to Raw HTML, the Template Fields tab will be "
                        "locked for this session. Edits made in the HTML editor cannot "
                        "be read back into structured fields."
                    ),
                    html.P("Two drafts will be saved automatically:", className="mb-1"),
                    html.Ul(
                        [
                            html.Li(
                                [
                                    html.Strong("(templated)"),
                                    " — the current Template Fields version, preserved for reference.",
                                ]
                            ),
                            html.Li(
                                [
                                    html.Strong("(html)"),
                                    " — the rendered HTML version you will continue editing.",
                                ]
                            ),
                        ],
                        className="mb-2",
                    ),
                    html.P(
                        "If no template is active, only the (html) draft will be saved.",
                        className="text-muted small",
                    ),
                    dbc.Alert(
                        id="bulk-email-switch-modal-alert",
                        is_open=False,
                        color="danger",
                        className="mt-2 mb-0",
                        dismissable=True,
                    ),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button(
                        "Switch & Save",
                        id="bulk-email-confirm-html-mode-btn",
                        color="primary",
                    ),
                    dbc.Button(
                        "Cancel",
                        id="bulk-email-cancel-html-mode-btn",
                        color="secondary",
                        className="ms-2",
                        n_clicks=0,
                    ),
                ]
            ),
        ],
        id="bulk-email-switch-html-modal",
        is_open=False,
        centered=True,
        backdrop="static",
    )


def bulk_email_restore_draft_modal():
    """Confirmation modal shown before restoring a SENT/FAILED email to draft."""
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Restore to Draft?")),
            dbc.ModalBody(
                [
                    html.P(
                        "This will create a new Draft copy of the selected bulk email "
                        "with the same subject and content. "
                        "The original sent email and its history will remain unchanged."
                    ),
                    html.P(
                        "This action does NOT unsend any emails that were already delivered.",
                        className="text-danger fw-semibold mb-0",
                    ),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button(
                        "Restore to Draft",
                        id="bulk-email-restore-draft-confirm-btn",
                        color="warning",
                    ),
                    dbc.Button(
                        "Cancel",
                        id="bulk-email-restore-draft-cancel-btn",
                        color="secondary",
                        className="ms-2",
                        n_clicks=0,
                    ),
                ]
            ),
        ],
        id="bulk-email-restore-draft-modal",
        is_open=False,
        centered=True,
        backdrop="static",
    )


def bulk_email_recipient_groups_help_modal():
    """Help modal for the Recipient Groups section of the Bulk Email page."""
    return dbc.Modal(
        [
            dbc.ModalHeader(
                dbc.ModalTitle(
                    [html.I(className="bi bi-question-circle-fill me-2"), "Recipient Groups — Help"]
                ),
                close_button=False,
            ),
            dbc.ModalBody(
                [
                    html.P(
                        "Use this section to define and save the set of users who will receive a "
                        "bulk email. You can filter by role, email verification status, and "
                        "account activity dates."
                    ),
                    html.Hr(),
                    html.H6("Saved Groups", className="fw-bold"),
                    html.P(
                        "Select a previously saved group from the dropdown and click Load to "
                        "restore its filters. Saved groups let you reuse common recipient "
                        "definitions without re-entering filters each time."
                    ),
                    html.H6("Load / Copy / Delete / New buttons", className="fw-bold"),
                    html.Ul(
                        [
                            html.Li(
                                [
                                    html.Strong("Load"),
                                    " — applies the selected saved group's filters to the form.",
                                ]
                            ),
                            html.Li(
                                [
                                    html.Strong("Copy"),
                                    " — duplicates the selected group under a new name (you will be prompted to enter the new name).",
                                ]
                            ),
                            html.Li(
                                [
                                    html.Strong("Delete"),
                                    " — permanently removes the selected saved group.",
                                ]
                            ),
                            html.Li(
                                [
                                    html.Strong("New / Clear"),
                                    " — resets all filter fields and clears the group selection so you can start fresh.",
                                ]
                            ),
                        ]
                    ),
                    html.H6("Group Name & Description", className="fw-bold"),
                    html.P(
                        "Enter a descriptive Group Name before clicking Save Group. The optional "
                        "Description field is for your own reference. Neither field is visible to "
                        "email recipients."
                    ),
                    html.H6("Filters", className="fw-bold"),
                    html.Ul(
                        [
                            html.Li(
                                [
                                    html.Strong("Roles"),
                                    " — check one or more roles (USER, ADMIN, SUPERADMIN) to restrict recipients to users with those roles.",
                                ]
                            ),
                            html.Li(
                                [
                                    html.Strong("Email Verified"),
                                    " — filter to only verified accounts, only unverified accounts, or any.",
                                ]
                            ),
                            html.Li(
                                [
                                    html.Strong("Created After / Before"),
                                    " — include only users whose accounts were created within a date range.",
                                ]
                            ),
                            html.Li(
                                [
                                    html.Strong("Last Active After / Before"),
                                    " — include only users who were last active within a date range. Useful for targeting recently active or inactive users.",
                                ]
                            ),
                        ]
                    ),
                    html.H6("Preview", className="fw-bold"),
                    html.P(
                        "Click Preview to count matching users and populate the recipients table "
                        "below. The preview does not send anything — it simply shows who would "
                        "receive the email given the current filters. The table uses infinite "
                        "scrolling and loads results in pages as you scroll, so all matching "
                        "users can be reviewed regardless of count."
                    ),
                    html.H6("Save Group", className="fw-bold"),
                    html.P(
                        "Click Save Group to store the current filter settings under the given "
                        "Group Name. The saved group will appear in the dropdown and in the "
                        "Send Bulk Email section when selecting recipients."
                    ),
                ]
            ),
            dbc.ModalFooter(
                dbc.Button(
                    "Close",
                    id="bulk-email-recipient-groups-help-close",
                    color="secondary",
                    n_clicks=0,
                )
            ),
        ],
        id="bulk-email-recipient-groups-help-modal",
        is_open=False,
        size="lg",
        centered=True,
        scrollable=True,
    )


def bulk_email_composer_help_modal():
    """Help modal for the Email Composer section of the Bulk Email page."""
    return dbc.Modal(
        [
            dbc.ModalHeader(
                dbc.ModalTitle(
                    [html.I(className="bi bi-question-circle-fill me-2"), "Email Composer — Help"]
                ),
                close_button=False,
            ),
            dbc.ModalBody(
                [
                    html.P(
                        "Use this section to create and edit the email you will send. Emails are "
                        "saved as Drafts so you can work on them over multiple sessions before "
                        "sending."
                    ),
                    html.Hr(),
                    html.H6("Drafts", className="fw-bold"),
                    html.P(
                        "Select an existing draft from the dropdown to load it. You can also "
                        "create a new draft by clicking New / Clear to reset all fields and then "
                        "filling in the form."
                    ),
                    html.Ul(
                        [
                            html.Li(
                                [
                                    html.Strong("Load"),
                                    " — fills all composer fields from the selected saved draft.",
                                ]
                            ),
                            html.Li(
                                [
                                    html.Strong("Copy"),
                                    " — saves a duplicate of the current draft under a new name.",
                                ]
                            ),
                            html.Li(
                                [
                                    html.Strong("Delete"),
                                    " — permanently removes the selected saved draft.",
                                ]
                            ),
                            html.Li(
                                [
                                    html.Strong("New / Clear"),
                                    " — resets all composer fields so you can start a new draft from scratch.",
                                ]
                            ),
                        ]
                    ),
                    html.H6("Templates", className="fw-bold"),
                    html.P(
                        "Select a template from the Template dropdown and click Load Template to "
                        "pre-populate the Template Fields tab with standard content. Templates "
                        "provide a starting point; you can edit all fields after loading."
                    ),
                    html.H6("Draft Name", className="fw-bold"),
                    html.P(
                        "An internal label used to identify this draft in the Draft dropdown and "
                        "in the Bulk Email History table. It is not visible to email recipients."
                    ),
                    html.H6("Subject Line", className="fw-bold"),
                    html.P("The email subject line that recipients will see in their inbox."),
                    html.H6("Email Category", className="fw-bold"),
                    html.P(
                        "A category tag used to classify the type of email for internal tracking "
                        "purposes. It does not affect delivery."
                    ),
                    html.H6("Template Fields tab", className="fw-bold"),
                    html.P(
                        "Fill in the structured fields to compose the email body. Three collapsible "
                        "sections are available:"
                    ),
                    html.Ul(
                        [
                            html.Li(
                                [
                                    html.Strong("News & Updates"),
                                    " — headline news items with title, summary, URL, and optional image.",
                                ]
                            ),
                            html.Li(
                                [
                                    html.Strong("Engagement"),
                                    " — a call-to-action block with a topic, description, and button link.",
                                ]
                            ),
                            html.Li(
                                [
                                    html.Strong("System Update"),
                                    " — information about a scheduled maintenance window or system change.",
                                ]
                            ),
                        ]
                    ),
                    html.H6("Raw HTML tab", className="fw-bold"),
                    html.P(
                        [
                            html.Strong("Warning: "),
                            "Switching to Raw HTML locks the Template Fields tab for the current "
                            "session. Before switching, two drafts are automatically saved: one "
                            "preserving the templated version and one with the rendered HTML. "
                            "Use the Format HTML button to auto-indent the HTML code for "
                            "readability.",
                        ]
                    ),
                    html.H6("Save Draft", className="fw-bold"),
                    html.P(
                        "Click Save Draft to persist all changes and regenerate the Email Preview "
                        "below the composer. Always save before navigating to the Send Bulk "
                        "Email section — only saved drafts appear in the Send dropdown."
                    ),
                    html.H6("Email Preview", className="fw-bold"),
                    html.P(
                        "A live rendered preview of the email exactly as recipients will see it. "
                        "The preview is regenerated every time you click Save Draft."
                    ),
                ]
            ),
            dbc.ModalFooter(
                dbc.Button(
                    "Close",
                    id="bulk-email-composer-help-close",
                    color="secondary",
                    n_clicks=0,
                )
            ),
        ],
        id="bulk-email-composer-help-modal",
        is_open=False,
        size="lg",
        centered=True,
        scrollable=True,
    )


def bulk_email_send_help_modal():
    """Help modal for the Send Bulk Email section of the Bulk Email page."""
    return dbc.Modal(
        [
            dbc.ModalHeader(
                dbc.ModalTitle(
                    [html.I(className="bi bi-question-circle-fill me-2"), "Send Bulk Email — Help"]
                ),
                close_button=False,
            ),
            dbc.ModalBody(
                [
                    html.P(
                        "Use this section to send a saved draft to a saved recipient group. "
                        "Always review the draft using the test send options before sending to "
                        "a large group."
                    ),
                    html.Hr(),
                    html.H6("Select Draft", className="fw-bold"),
                    html.P(
                        "Choose the draft you want to send from the dropdown. Only drafts with "
                        "status DRAFT appear here. If your draft is not listed, return to the "
                        "Email Composer and click Save Draft."
                    ),
                    html.H6("Select Recipient Group", className="fw-bold"),
                    html.P(
                        "Choose the saved recipient group who will receive the email. If no groups "
                        "are listed, return to the Recipient Groups section, define your filters, "
                        "and click Save Group."
                    ),
                    html.H6("Send Test to Self", className="fw-bold"),
                    html.P(
                        "Sends one copy of the selected draft to your own email address. Use this "
                        "to review formatting, links, and content before a wider send."
                    ),
                    html.H6("Send Test to Superadmins", className="fw-bold"),
                    html.P(
                        "Sends a copy of the draft to all users with the SUPERADMIN role. Use this "
                        "to share the email with your team for review before the bulk send."
                    ),
                    html.H6("Send Bulk Email", className="fw-bold"),
                    html.P(
                        "Initiates sending the selected draft to all users in the selected "
                        "recipient group. This action cannot be undone."
                    ),
                    html.P(
                        [
                            html.Strong("Large-send verification: "),
                            "If the recipient count exceeds the configured threshold, a 6-digit "
                            "verification code will be sent to your email address. You must enter "
                            "that code in the confirmation dialog to proceed. This is a safeguard "
                            "against accidental bulk sends.",
                        ]
                    ),
                    dbc.Alert(
                        [
                            html.I(className="fas fa-exclamation-triangle me-2"),
                            html.Strong("Best practice: "),
                            "Always send a test to yourself first and carefully review the Email "
                            "Preview before clicking Send Bulk Email.",
                        ],
                        color="warning",
                        className="mb-0",
                    ),
                ]
            ),
            dbc.ModalFooter(
                dbc.Button(
                    "Close",
                    id="bulk-email-send-help-close",
                    color="secondary",
                    n_clicks=0,
                )
            ),
        ],
        id="bulk-email-send-help-modal",
        is_open=False,
        size="lg",
        centered=True,
        scrollable=True,
    )


def bulk_email_history_help_modal():
    """Help modal for the Bulk Email History section of the Bulk Email page."""
    return dbc.Modal(
        [
            dbc.ModalHeader(
                dbc.ModalTitle(
                    [
                        html.I(className="bi bi-question-circle-fill me-2"),
                        "Bulk Email History — Help",
                    ]
                ),
                close_button=False,
            ),
            dbc.ModalBody(
                [
                    html.P(
                        "This section shows a record of all bulk emails that have been sent, "
                        "including their status and delivery details."
                    ),
                    html.Hr(),
                    html.H6("History Table", className="fw-bold"),
                    html.P("Each row represents one bulk email send. The columns show:"),
                    html.Ul(
                        [
                            html.Li(
                                [
                                    html.Strong("Name"),
                                    " — the draft name used when the email was sent.",
                                ]
                            ),
                            html.Li([html.Strong("Subject"), " — the email subject line."]),
                            html.Li(
                                [
                                    html.Strong("Status"),
                                    " — the current delivery status: ",
                                    html.Em("Sent"),
                                    " (fully delivered), ",
                                    html.Em("Failed"),
                                    " (delivery error), or ",
                                    html.Em("Pending"),
                                    " (in progress).",
                                ]
                            ),
                            html.Li(
                                [
                                    html.Strong("Recipients"),
                                    " — the number of users the email was sent to.",
                                ]
                            ),
                            html.Li(
                                [
                                    html.Strong("Sent By"),
                                    " — the email address of the admin who triggered the send.",
                                ]
                            ),
                            html.Li(
                                [
                                    html.Strong("Sent At"),
                                    " — the date and time when the send was initiated.",
                                ]
                            ),
                        ]
                    ),
                    html.H6("Refresh", className="fw-bold"),
                    html.P(
                        "Click Refresh to reload the history table with the latest data from "
                        "the server. Use this to check whether a pending send has completed."
                    ),
                    html.H6("Restore to Draft", className="fw-bold"),
                    html.P(
                        "Select a row in the table, then click Restore to Draft to create a new "
                        "Draft copy of that email with the same subject and HTML body. This is "
                        "useful for resending a previous email or using it as the basis for a "
                        "new one."
                    ),
                    html.P(
                        "Restoring to a draft does not modify or unsend the original email — "
                        "the history record remains unchanged.",
                        className="text-muted small mb-0",
                    ),
                ]
            ),
            dbc.ModalFooter(
                dbc.Button(
                    "Close",
                    id="bulk-email-history-help-close",
                    color="secondary",
                    n_clicks=0,
                )
            ),
        ],
        id="bulk-email-history-help-modal",
        is_open=False,
        size="lg",
        centered=True,
        scrollable=True,
    )
