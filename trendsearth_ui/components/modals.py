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
                                ],
                                className="mb-3",
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
