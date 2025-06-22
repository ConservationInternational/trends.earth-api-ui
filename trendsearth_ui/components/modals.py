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
                                                ],
                                                value="USER",
                                            ),
                                        ],
                                        width=6,
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
