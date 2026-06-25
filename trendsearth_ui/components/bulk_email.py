"""Bulk Email tab component.

This tab is only visible to SUPERADMIN users who are also on the
BULK_EMAIL_APPROVED_SENDERS list.
"""

from dash import dcc, html
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc

# ---------------------------------------------------------------------------
# Template Fields Panel helpers
# ---------------------------------------------------------------------------


def _news_item_row(index: int, item: dict | None = None) -> dbc.Card:
    """Return a card containing the fields for a single news item."""
    item = item or {}
    return dbc.Card(
        dbc.CardBody(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Title", html_for={"type": "news-title", "index": index}),
                                dbc.Input(
                                    id={"type": "news-title", "index": index},
                                    type="text",
                                    placeholder="News item title",
                                    value=item.get("title", ""),
                                ),
                            ],
                            width=12,
                            className="mb-2",
                        ),
                    ]
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label(
                                    "Summary",
                                    html_for={"type": "news-summary", "index": index},
                                ),
                                dbc.Textarea(
                                    id={"type": "news-summary", "index": index},
                                    placeholder="Brief summary of the news item",
                                    rows=2,
                                    value=item.get("summary", ""),
                                ),
                            ],
                            width=12,
                            className="mb-2",
                        ),
                    ]
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("URL", html_for={"type": "news-url", "index": index}),
                                dbc.Input(
                                    id={"type": "news-url", "index": index},
                                    type="url",
                                    placeholder="https://...",
                                    value=item.get("url", ""),
                                ),
                            ],
                            width=6,
                            className="mb-2",
                        ),
                        dbc.Col(
                            [
                                dbc.Label(
                                    "Image Alt Text",
                                    html_for={"type": "news-image-alt", "index": index},
                                ),
                                dbc.Input(
                                    id={"type": "news-image-alt", "index": index},
                                    type="text",
                                    placeholder="Describe the image (for accessibility)",
                                    value=item.get("image_alt", ""),
                                ),
                            ],
                            width=6,
                            className="mb-2",
                        ),
                    ]
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Image URL (auto-filled after upload)"),
                                dcc.Loading(
                                    dbc.Input(
                                        id={"type": "news-image-url", "index": index},
                                        type="url",
                                        placeholder="Uploaded image URL will appear here",
                                        disabled=False,
                                        style={"backgroundColor": "#f8f9fa"},
                                        value=item.get("image_url", ""),
                                    ),
                                    type="circle",
                                    delay_show=100,
                                ),
                            ],
                            width=8,
                            className="mb-2",
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Upload Image"),
                                dcc.Upload(
                                    id={"type": "news-image-upload", "index": index},
                                    children=dbc.Button(
                                        "Choose file",
                                        color="outline-secondary",
                                        size="sm",
                                        style={"width": "100%"},
                                    ),
                                    accept="image/*",
                                ),
                            ],
                            width=4,
                            className="mb-2 d-flex flex-column justify-content-end",
                        ),
                    ]
                ),
                dbc.Row(
                    dbc.Col(
                        dbc.Button(
                            "Remove news item",
                            id={"type": "news-item-delete", "index": index},
                            color="outline-danger",
                            size="sm",
                        ),
                        width="auto",
                    )
                ),
            ]
        ),
        className="mb-2",
    )


def _impact_item_row(index: int, text: str = "") -> dbc.Row:
    """Return a row containing the input + delete button for one impact item."""
    return dbc.Row(
        [
            dbc.Col(
                dbc.Input(
                    id={"type": "impact-item", "index": index},
                    type="text",
                    placeholder="e.g. All running analyses will be paused",
                    value=text,
                ),
                width=10,
            ),
            dbc.Col(
                dbc.Button(
                    "✕",
                    id={"type": "impact-item-delete", "index": index},
                    color="outline-danger",
                    size="sm",
                ),
                width=2,
            ),
        ],
        className="mb-2",
    )


def _template_fields_panel() -> html.Div:
    """Build the three collapsible template-field panels plus a placeholder."""
    return html.Div(
        [
            # --- No template selected ---
            dbc.Collapse(
                dbc.Alert(
                    "Select a template above and click 'Load Template' to fill in "
                    "structured fields, or switch to the Raw HTML tab to edit directly.",
                    color="light",
                    className="mb-0",
                ),
                id="bulk-email-no-template-panel",
                is_open=True,
            ),
            # --- News & Updates ---
            dbc.Collapse(
                html.Div(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Label("Issue Date"),
                                        dbc.Input(
                                            id="bulk-email-field-news-issue-date",
                                            type="text",
                                            placeholder="e.g. January 2025",
                                        ),
                                    ],
                                    width=4,
                                    className="mb-3",
                                ),
                            ]
                        ),
                        dbc.Row(
                            dbc.Col(
                                [
                                    dbc.Label("Intro Paragraph"),
                                    dbc.Textarea(
                                        id="bulk-email-field-news-intro",
                                        placeholder="Opening paragraph after greeting",
                                        rows=2,
                                    ),
                                ],
                                width=12,
                                className="mb-3",
                            )
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Label("Highlight Title"),
                                        dbc.Input(
                                            id="bulk-email-field-news-highlight-title",
                                            type="text",
                                            placeholder="Title inside the red highlight box",
                                        ),
                                    ],
                                    width=4,
                                    className="mb-3",
                                ),
                                dbc.Col(
                                    [
                                        dbc.Label("Highlight Body"),
                                        dbc.Textarea(
                                            id="bulk-email-field-news-highlight-body",
                                            placeholder="Body text inside the red highlight box",
                                            rows=2,
                                        ),
                                    ],
                                    width=8,
                                    className="mb-3",
                                ),
                            ]
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Label("Highlight Image URL (auto-filled after upload)"),
                                        dcc.Loading(
                                            dbc.Input(
                                                id="bulk-email-field-news-highlight-image-url",
                                                type="url",
                                                placeholder="Uploaded image URL will appear here",
                                                style={"backgroundColor": "#f8f9fa"},
                                            ),
                                            type="circle",
                                            delay_show=100,
                                        ),
                                        html.Small(
                                            "Optional — shown above highlight text. Leave blank to omit.",
                                            className="text-muted",
                                        ),
                                    ],
                                    width=8,
                                    className="mb-3",
                                ),
                                dbc.Col(
                                    [
                                        dbc.Label("Upload Highlight Image"),
                                        dcc.Upload(
                                            id="bulk-email-highlight-image-upload",
                                            children=dbc.Button(
                                                "Choose file",
                                                color="outline-secondary",
                                                size="sm",
                                                style={"width": "100%"},
                                            ),
                                            accept="image/*",
                                        ),
                                    ],
                                    width=4,
                                    className="mb-3 d-flex flex-column justify-content-end",
                                ),
                            ]
                        ),
                        html.H6("News Items", className="mt-2 mb-2"),
                        html.Div(id="bulk-email-news-items-container"),
                        dbc.Button(
                            "+ Add news item",
                            id="bulk-email-add-news-item-btn",
                            color="outline-secondary",
                            size="sm",
                            className="mt-1 mb-3",
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Label("Call to Action Button URL"),
                                        dbc.Input(
                                            id="bulk-email-field-news-cta-url",
                                            type="url",
                                            placeholder="https://trends.earth",
                                        ),
                                    ],
                                    width=6,
                                    className="mb-3",
                                ),
                                dbc.Col(
                                    [
                                        dbc.Label("Call to Action Button Label"),
                                        dbc.Input(
                                            id="bulk-email-field-news-cta-label",
                                            type="text",
                                            placeholder="Visit Trends.Earth",
                                        ),
                                    ],
                                    width=6,
                                    className="mb-3",
                                ),
                            ]
                        ),
                    ]
                ),
                id="bulk-email-news-fields-panel",
                is_open=False,
            ),
            # --- Engagement ---
            dbc.Collapse(
                html.Div(
                    [
                        dbc.Row(
                            dbc.Col(
                                [
                                    dbc.Label("Intro Paragraph"),
                                    dbc.Textarea(
                                        id="bulk-email-field-engagement-intro",
                                        placeholder="Opening paragraph after greeting",
                                        rows=3,
                                    ),
                                ],
                                width=12,
                                className="mb-3",
                            )
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Label("Topic / Survey Title"),
                                        dbc.Input(
                                            id="bulk-email-field-engagement-topic",
                                            type="text",
                                            placeholder="e.g. User Satisfaction Survey",
                                        ),
                                    ],
                                    width=12,
                                    className="mb-3",
                                ),
                            ]
                        ),
                        dbc.Row(
                            dbc.Col(
                                [
                                    dbc.Label("Description"),
                                    dbc.Textarea(
                                        id="bulk-email-field-engagement-description",
                                        placeholder="Describe what you want users to do",
                                        rows=3,
                                    ),
                                ],
                                width=12,
                                className="mb-3",
                            )
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Label("Button Label"),
                                        dbc.Input(
                                            id="bulk-email-field-engagement-btn-label",
                                            type="text",
                                            placeholder="e.g. Take the Survey",
                                        ),
                                    ],
                                    width=4,
                                    className="mb-3",
                                ),
                                dbc.Col(
                                    [
                                        dbc.Label("Button URL"),
                                        dbc.Input(
                                            id="bulk-email-field-engagement-btn-url",
                                            type="url",
                                            placeholder="https://...",
                                        ),
                                    ],
                                    width=8,
                                    className="mb-3",
                                ),
                            ]
                        ),
                    ]
                ),
                id="bulk-email-engagement-fields-panel",
                is_open=False,
            ),
            # --- System Update ---
            dbc.Collapse(
                html.Div(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Label("Date & Time Header"),
                                        dbc.Input(
                                            id="bulk-email-field-sysupdate-date-time",
                                            type="text",
                                            placeholder="e.g. Saturday, 15 February 2025",
                                        ),
                                    ],
                                    width=6,
                                    className="mb-3",
                                ),
                            ]
                        ),
                        dbc.Row(
                            dbc.Col(
                                [
                                    dbc.Label("Intro Paragraph"),
                                    dbc.Textarea(
                                        id="bulk-email-field-sysupdate-intro",
                                        placeholder="Opening sentence about the maintenance",
                                        rows=2,
                                    ),
                                ],
                                width=12,
                                className="mb-3",
                            )
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Label("Date & Time (UTC)"),
                                        dbc.Input(
                                            id="bulk-email-field-sysupdate-datetime-utc",
                                            type="text",
                                            placeholder="e.g. 2025-02-15 02:00 UTC",
                                        ),
                                    ],
                                    width=4,
                                    className="mb-3",
                                ),
                                dbc.Col(
                                    [
                                        dbc.Label("Duration"),
                                        dbc.Input(
                                            id="bulk-email-field-sysupdate-duration",
                                            type="text",
                                            placeholder="e.g. approximately 2 hours",
                                        ),
                                    ],
                                    width=4,
                                    className="mb-3",
                                ),
                                dbc.Col(
                                    [
                                        dbc.Label("Impact Summary"),
                                        dbc.Input(
                                            id="bulk-email-field-sysupdate-impact",
                                            type="text",
                                            placeholder="e.g. API and web interface",
                                        ),
                                    ],
                                    width=4,
                                    className="mb-3",
                                ),
                            ]
                        ),
                        html.H6("What to Expect (impact items)", className="mt-2 mb-2"),
                        html.Div(id="bulk-email-impact-items-container"),
                        dbc.Button(
                            "+ Add impact item",
                            id="bulk-email-add-impact-item-btn",
                            color="outline-secondary",
                            size="sm",
                            className="mt-1 mb-3",
                        ),
                    ]
                ),
                id="bulk-email-sysupdate-fields-panel",
                is_open=False,
            ),
        ]
    )


def bulk_email_tab_content(_role=None):
    """Return the Bulk Email tab content."""
    return html.Div(
        [
            html.H3("Bulk Email", className="mb-4"),
            # -------------------------------------------------------
            # Section 1 - Recipient Groups
            # -------------------------------------------------------
            dbc.Card(
                [
                    dbc.CardHeader(html.H5("Recipient Groups", className="mb-0")),
                    dbc.CardBody(
                        [
                            # Status alert -- always at top
                            dbc.Alert(
                                id="bulk-email-rlist-alert",
                                is_open=False,
                                dismissable=True,
                                className="mb-3",
                            ),
                            # Saved-group selector row (mirrors draft selector)
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.Select(
                                            id="bulk-email-load-rlist-select",
                                            options=[],
                                            placeholder="Select a saved group to load...",
                                        ),
                                        width=6,
                                    ),
                                    dbc.Col(
                                        dbc.ButtonGroup(
                                            [
                                                dbc.Button(
                                                    "Load",
                                                    id="bulk-email-load-rlist-btn",
                                                    color="secondary",
                                                    size="sm",
                                                ),
                                                dbc.Button(
                                                    "Copy",
                                                    id="bulk-email-copy-rlist-btn",
                                                    color="outline-secondary",
                                                    size="sm",
                                                ),
                                                dbc.Button(
                                                    "Delete",
                                                    id="bulk-email-delete-rlist-btn",
                                                    color="outline-danger",
                                                    size="sm",
                                                ),
                                                dbc.Button(
                                                    "New / Clear",
                                                    id="bulk-email-clear-rlist-btn",
                                                    color="outline-secondary",
                                                    size="sm",
                                                ),
                                            ]
                                        ),
                                        width="auto",
                                    ),
                                    dbc.Col(
                                        html.Small(
                                            id="bulk-email-rlist-mode-label",
                                            className="text-muted",
                                        ),
                                        className="d-flex align-items-center",
                                    ),
                                ],
                                className="mb-3",
                            ),
                            dcc.Store(id="bulk-email-loaded-rlist-id"),
                            # Filter form
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Group Name"),
                                            dbc.Input(
                                                id="bulk-email-rlist-name",
                                                type="text",
                                                placeholder="e.g. All active users",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Description (optional)"),
                                            dbc.Input(
                                                id="bulk-email-rlist-desc",
                                                type="text",
                                                placeholder="Short description",
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
                                            dbc.Label("Roles"),
                                            dbc.Checklist(
                                                id="bulk-email-rlist-roles",
                                                options=[
                                                    {"label": "USER", "value": "USER"},
                                                    {"label": "ADMIN", "value": "ADMIN"},
                                                    {
                                                        "label": "SUPERADMIN",
                                                        "value": "SUPERADMIN",
                                                    },
                                                ],
                                                value=["USER"],
                                                inline=True,
                                            ),
                                        ],
                                        width=4,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Email Verified"),
                                            dbc.Select(
                                                id="bulk-email-rlist-verified",
                                                options=[
                                                    {"label": "Any", "value": "any"},
                                                    {"label": "Yes", "value": "true"},
                                                    {"label": "No", "value": "false"},
                                                ],
                                                value="any",
                                            ),
                                        ],
                                        width=2,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Created After"),
                                            dbc.Input(
                                                id="bulk-email-rlist-min-created",
                                                type="date",
                                            ),
                                        ],
                                        width=3,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Created Before"),
                                            dbc.Input(
                                                id="bulk-email-rlist-max-created",
                                                type="date",
                                            ),
                                        ],
                                        width=3,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Last Active After"),
                                            dbc.Input(
                                                id="bulk-email-rlist-min-activity",
                                                type="date",
                                            ),
                                        ],
                                        width=3,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Last Active Before"),
                                            dbc.Input(
                                                id="bulk-email-rlist-max-activity",
                                                type="date",
                                            ),
                                        ],
                                        width=3,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Button(
                                                "Preview",
                                                id="bulk-email-preview-btn",
                                                color="secondary",
                                                className="me-2",
                                            ),
                                            dbc.Button(
                                                "Save Group",
                                                id="bulk-email-save-rlist-btn",
                                                color="primary",
                                            ),
                                        ],
                                        width="auto",
                                    ),
                                    dbc.Col(
                                        [
                                            html.Span(
                                                id="bulk-email-preview-count",
                                                className="badge bg-info ms-3",
                                                style={"fontSize": "1em"},
                                            ),
                                            html.Small(
                                                id="bulk-email-preview-source-label",
                                                className="text-muted ms-2",
                                            ),
                                        ],
                                        width="auto",
                                        className="d-flex align-items-center",
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Preview grid
                            dcc.Store(id="bulk-email-preview-filter-store", data=None),
                            dag.AgGrid(
                                id="bulk-email-preview-grid",
                                columnDefs=[
                                    {"field": "email", "headerName": "Email", "flex": 2},
                                    {"field": "name", "headerName": "Name", "flex": 1},
                                    {"field": "role", "headerName": "Role", "flex": 1},
                                    {
                                        "field": "email_verified",
                                        "headerName": "Verified",
                                        "flex": 1,
                                    },
                                    {"field": "created_at", "headerName": "Created", "flex": 1},
                                    {
                                        "field": "last_activity_at",
                                        "headerName": "Last Active",
                                        "flex": 1,
                                    },
                                ],
                                defaultColDef={
                                    "sortable": True,
                                    "filter": False,
                                    "resizable": True,
                                },
                                rowModelType="infinite",
                                dashGridOptions={"cacheBlockSize": 100},
                                style={"height": "300px"},
                                className="ag-theme-alpine",
                            ),
                        ]
                    ),
                ],
                className="mb-4",
            ),
            # -------------------------------------------------------
            # Section 2 â€” Email Composer
            # -------------------------------------------------------
            dbc.Card(
                [
                    dbc.CardHeader(html.H5("Email Composer", className="mb-0")),
                    dbc.CardBody(
                        [
                            # Stores for structured editor state
                            dcc.Store(id="bulk-email-active-template", data=""),
                            dcc.Store(id="bulk-email-news-items-store", data=[]),
                            dcc.Store(id="bulk-email-impact-items-store", data=[]),
                            dcc.Store(id="bulk-email-cm-sync-trigger", data=0),
                            # Tracks whether the user has switched to Raw HTML mode.
                            # Once True the Template Fields tab is locked.
                            dcc.Store(id="bulk-email-in-html-mode", data=False),
                            # Hidden textarea — backing store for the Monaco editor.
                            # Kept OUTSIDE the Raw-HTML tab panel so it is always
                            # in the DOM and has the current value when Monaco reads
                            # it on first mount.
                            dcc.Textarea(
                                id="bulk-email-html-source",
                                value="",
                                style={"display": "none"},
                            ),
                            # Open existing draft  ──OR──  Start from a template
                            dbc.Row(
                                [
                                    # ── Left: open an existing draft ──────────────────
                                    dbc.Col(
                                        [
                                            html.Small(
                                                "Open existing draft",
                                                className="text-muted fw-semibold d-block mb-1",
                                            ),
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        dbc.Select(
                                                            id="bulk-email-load-draft-select",
                                                            options=[],
                                                            placeholder="Select a draft...",
                                                        ),
                                                        width=True,
                                                    ),
                                                    dbc.Col(
                                                        dbc.ButtonGroup(
                                                            [
                                                                dbc.Button(
                                                                    "Load",
                                                                    id="bulk-email-load-draft-btn",
                                                                    color="secondary",
                                                                    size="sm",
                                                                ),
                                                                dbc.Button(
                                                                    "Copy",
                                                                    id="bulk-email-copy-draft-btn",
                                                                    color="outline-secondary",
                                                                    size="sm",
                                                                ),
                                                                dbc.Button(
                                                                    "Delete",
                                                                    id="bulk-email-delete-draft-btn",
                                                                    color="outline-danger",
                                                                    size="sm",
                                                                ),
                                                                dbc.Button(
                                                                    "New / Clear",
                                                                    id="bulk-email-clear-draft-btn",
                                                                    color="outline-secondary",
                                                                    size="sm",
                                                                ),
                                                            ]
                                                        ),
                                                        width="auto",
                                                    ),
                                                ],
                                                className="g-2 align-items-center",
                                            ),
                                            html.Small(
                                                id="bulk-email-draft-mode-label",
                                                className="text-muted fst-italic mt-1 d-block",
                                            ),
                                        ],
                                        width=7,
                                    ),
                                    # ── Divider ───────────────────────────────────────
                                    dbc.Col(
                                        html.Div(
                                            "or",
                                            className=(
                                                "text-muted fw-semibold text-center "
                                                "border-start h-100 ps-3"
                                            ),
                                            style={"paddingTop": "1.6rem"},
                                        ),
                                        width=1,
                                    ),
                                    # ── Right: start from a template ──────────────────
                                    dbc.Col(
                                        [
                                            html.Small(
                                                "Start from a template",
                                                className="text-muted fw-semibold d-block mb-1",
                                            ),
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        dbc.Select(
                                                            id="bulk-email-template-select",
                                                            options=[
                                                                {
                                                                    "label": "(no template)",
                                                                    "value": "",
                                                                },
                                                                {
                                                                    "label": "News & Updates",
                                                                    "value": "news",
                                                                },
                                                                {
                                                                    "label": "User Engagement",
                                                                    "value": "engagement",
                                                                },
                                                                {
                                                                    "label": "System Update / Maintenance",
                                                                    "value": "system_update",
                                                                },
                                                            ],
                                                            value="",
                                                            placeholder="Choose a template...",
                                                        ),
                                                        width=True,
                                                    ),
                                                    dbc.Col(
                                                        dbc.Button(
                                                            "Load Template",
                                                            id="bulk-email-load-template-btn",
                                                            color="outline-primary",
                                                            size="sm",
                                                        ),
                                                        width="auto",
                                                    ),
                                                ],
                                                className="g-2 align-items-center",
                                            ),
                                        ],
                                        width=4,
                                    ),
                                ],
                                className="mb-3 align-items-start",
                            ),
                            dcc.Store(id="bulk-email-loaded-draft-id"),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Draft Name"),
                                            dbc.Input(
                                                id="bulk-email-name",
                                                type="text",
                                                placeholder="e.g. Q2 Newsletter",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Subject Line"),
                                            dbc.Input(
                                                id="bulk-email-subject",
                                                type="text",
                                                placeholder="Email subject",
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
                                            dbc.Label("Email Category"),
                                            dbc.Select(
                                                id="bulk-email-category-select",
                                                options=[
                                                    {"label": "(none — send to all)", "value": ""},
                                                    {"label": "News & Updates", "value": "news"},
                                                    {
                                                        "label": "User Engagement",
                                                        "value": "engagement",
                                                    },
                                                    {
                                                        "label": "System Updates",
                                                        "value": "system_updates",
                                                    },
                                                ],
                                                value="",
                                            ),
                                            html.Small(
                                                "Only send to users subscribed to this category. "
                                                "Set to '(none)' to send to all users.",
                                                className="text-muted",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Editor tabs: Template Fields | Raw HTML
                            dbc.Label("Email Body"),
                            dmc.Tabs(
                                id="bulk-email-editor-tabs",
                                value="fields",
                                children=[
                                    dmc.TabsList(
                                        [
                                            dmc.TabsTab(
                                                "Template Fields",
                                                id="bulk-email-fields-tab",
                                                value="fields",
                                            ),
                                            dmc.TabsTab("Raw HTML", value="raw"),
                                        ]
                                    ),
                                    dmc.TabsPanel(
                                        _template_fields_panel(),
                                        value="fields",
                                        pt="md",
                                    ),
                                    dmc.TabsPanel(
                                        html.Div(
                                            [
                                                # Warning banner — only visible before HTML mode
                                                # is activated. Hidden once the user commits.
                                                dbc.Alert(
                                                    [
                                                        html.Strong("Read-only preview. "),
                                                        "This is the rendered HTML from your "
                                                        "template fields. To edit the HTML "
                                                        "directly, click the button below — "
                                                        "this will save both a "
                                                        "\u201c(templated)\u201d and an "
                                                        "\u201c(html)\u201d draft and lock "
                                                        "the Template Fields tab.",
                                                        dbc.Button(
                                                            "Enable HTML Editing\u2026",
                                                            id="bulk-email-enable-html-btn",
                                                            color="warning",
                                                            size="sm",
                                                            className="ms-3",
                                                        ),
                                                    ],
                                                    id="bulk-email-html-mode-banner",
                                                    color="warning",
                                                    className="mb-2 d-flex align-items-center",
                                                    is_open=True,
                                                ),
                                                html.Div(
                                                    [
                                                        dbc.Button(
                                                            "Format HTML",
                                                            id="bulk-email-format-html-btn",
                                                            color="outline-secondary",
                                                            size="sm",
                                                        ),
                                                    ],
                                                    className="d-flex align-items-center mb-2",
                                                ),
                                                # CodeMirror mounts into this div
                                                html.Div(
                                                    id="bulk-email-cm-container",
                                                    style={
                                                        "height": "700px",
                                                        "border": "1px solid #ced4da",
                                                        "borderRadius": "4px",
                                                    },
                                                ),
                                            ]
                                        ),
                                        value="raw",
                                        pt="md",
                                    ),
                                ],
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.Button(
                                            "Save Draft",
                                            id="bulk-email-save-draft-btn",
                                            color="success",
                                        ),
                                        width="auto",
                                    ),
                                ],
                                className="mt-2 mb-1 g-2",
                            ),
                            # Status alert — shown below Save button so it's near the action
                            dbc.Alert(
                                id="bulk-email-composer-alert",
                                is_open=False,
                                dismissable=True,
                                className="mt-2 mb-3",
                            ),
                            dcc.Store(id="bulk-email-preview-html"),
                            html.Hr(),
                            html.H6(
                                "Email Preview",
                                className="text-muted mt-2 mb-2",
                            ),
                            html.Small(
                                "This preview renders the actual HTML that will be sent. "
                                "Always verify here before sending.",
                                className="text-muted d-block mb-2",
                            ),
                            html.Iframe(
                                id="bulk-email-preview-frame",
                                srcDoc="<p style='color:#6c757d;padding:16px;'>"
                                "Load a template or draft to see a live preview here."
                                "</p>",
                                style={
                                    "width": "100%",
                                    "height": "700px",
                                    "border": "1px solid #dee2e6",
                                    "borderRadius": "4px",
                                },
                            ),
                        ]
                    ),
                ],
                className="mb-4",
            ),
            # -------------------------------------------------------
            # Section 3 â€” Send Bulk Email
            # -------------------------------------------------------
            dbc.Card(
                [
                    dbc.CardHeader(html.H5("Send Bulk Email", className="mb-0")),
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Select Draft"),
                                            dbc.Select(
                                                id="bulk-email-send-select",
                                                options=[],
                                                placeholder="Choose a draft...",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Select Recipient Group"),
                                            dbc.Select(
                                                id="bulk-email-send-rlist-select",
                                                options=[],
                                                placeholder="Choose a recipient group...",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Threshold info badge
                            html.Small(
                                id="bulk-email-threshold-info",
                                className="text-muted d-block mb-3",
                            ),
                            # Send buttons
                            dbc.ButtonGroup(
                                [
                                    dbc.Button(
                                        "Send Test to Self",
                                        id="bulk-email-send-test-self-btn",
                                        color="outline-secondary",
                                    ),
                                    dbc.Button(
                                        "Send Test to Superadmins",
                                        id="bulk-email-send-test-btn",
                                        color="secondary",
                                    ),
                                    dbc.Button(
                                        "Send Bulk Email",
                                        id="bulk-email-send-btn",
                                        color="danger",
                                    ),
                                ]
                            ),
                            dbc.Alert(
                                id="bulk-email-send-alert",
                                is_open=False,
                                dismissable=True,
                                className="mt-3",
                            ),
                            # Hidden store for pending bulk_email_id (428 flow)
                            dcc.Store(id="bulk-email-pending-id"),
                        ]
                    ),
                ],
                className="mb-4",
            ),
            # -------------------------------------------------------
            # Section 4 â€” Bulk Email History
            # -------------------------------------------------------
            dcc.Store(id="bulk-email-history-selected-id"),
            dbc.Card(
                [
                    dbc.CardHeader(html.H5("Bulk Email History", className="mb-0")),
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.Button(
                                            "Refresh",
                                            id="bulk-email-history-refresh-btn",
                                            color="outline-secondary",
                                            size="sm",
                                        ),
                                        width="auto",
                                    ),
                                    dbc.Col(
                                        dbc.Button(
                                            "Restore to Draft",
                                            id="bulk-email-restore-draft-btn",
                                            color="outline-warning",
                                            size="sm",
                                            disabled=True,
                                        ),
                                        width="auto",
                                    ),
                                ],
                                className="g-2 mb-2",
                            ),
                            dbc.Alert(
                                id="bulk-email-restore-draft-alert",
                                is_open=False,
                                dismissable=True,
                                className="mb-2",
                            ),
                            dag.AgGrid(
                                id="bulk-email-history-grid",
                                columnDefs=[
                                    {"field": "name", "headerName": "Name", "flex": 2},
                                    {
                                        "field": "subject",
                                        "headerName": "Subject",
                                        "flex": 3,
                                    },
                                    {
                                        "field": "status",
                                        "headerName": "Status",
                                        "flex": 1,
                                    },
                                    {
                                        "field": "recipient_count",
                                        "headerName": "Recipients",
                                        "flex": 1,
                                    },
                                    {
                                        "field": "sent_by",
                                        "headerName": "Sent By",
                                        "flex": 1,
                                    },
                                    {
                                        "field": "sent_at",
                                        "headerName": "Sent At",
                                        "flex": 1,
                                    },
                                ],
                                rowData=[],
                                style={"height": "300px"},
                                className="ag-theme-alpine",
                                dashGridOptions={"animateRows": True, "rowSelection": "single"},
                            ),
                        ]
                    ),
                ],
                className="mb-4",
            ),
        ],
        className="p-3",
    )
