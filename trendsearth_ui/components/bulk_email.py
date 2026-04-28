"""Bulk Email tab component.

This tab is only visible to SUPERADMIN users who are also on the
BULK_EMAIL_APPROVED_SENDERS list.
"""

from dash import dcc, html
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc

_EMAIL_COLORS = [
    "#000000",
    "#434343",
    "#666666",
    "#999999",
    "#cc0000",
    "#e06666",
    "#ff9900",
    "#ffd966",
    "#00aa00",
    "#6aa84f",
    "#1155cc",
    "#6fa8dc",
    "#674ea7",
    "#a64d79",
]


def bulk_email_tab_content(_role=None):
    """Return the Bulk Email tab content."""
    return html.Div(
        [
            html.H3("Bulk Email", className="mb-4"),
            # -------------------------------------------------------
            # Section 1 â€” Recipient Groups
            # -------------------------------------------------------
            dbc.Card(
                [
                    dbc.CardHeader(html.H5("Recipient Groups", className="mb-0")),
                    dbc.CardBody(
                        [
                            # New group form
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
                                            )
                                        ],
                                        width="auto",
                                        className="d-flex align-items-center",
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # Preview grid
                            dag.AgGrid(
                                id="bulk-email-preview-grid",
                                columnDefs=[
                                    {"field": "email", "headerName": "Email"},
                                    {"field": "name", "headerName": "Name"},
                                    {"field": "role", "headerName": "Role"},
                                ],
                                rowData=[],
                                style={"height": "200px"},
                                className="ag-theme-alpine mb-3",
                            ),
                            dbc.Alert(
                                id="bulk-email-rlist-alert",
                                is_open=False,
                                dismissable=True,
                            ),
                            html.Hr(),
                            html.H6("Saved Groups"),
                            # Saved groups grid
                            dag.AgGrid(
                                id="bulk-email-rlist-grid",
                                columnDefs=[
                                    {
                                        "field": "name",
                                        "headerName": "Name",
                                        "flex": 2,
                                    },
                                    {
                                        "field": "estimated_count",
                                        "headerName": "Est. Recipients",
                                        "flex": 1,
                                    },
                                    {
                                        "field": "created_by",
                                        "headerName": "Created By",
                                        "flex": 1,
                                    },
                                    {
                                        "field": "created_at",
                                        "headerName": "Created",
                                        "flex": 1,
                                    },
                                ],
                                rowData=[],
                                style={"height": "200px"},
                                className="ag-theme-alpine",
                                dashGridOptions={"animateRows": True, "rowSelection": "single"},
                            ),
                            dbc.Button(
                                "Delete Selected Group",
                                id="bulk-email-delete-rlist-btn",
                                color="danger",
                                size="sm",
                                className="mt-2",
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
                            # Load existing draft
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.Select(
                                            id="bulk-email-load-draft-select",
                                            options=[],
                                            placeholder="Select a draft to load...",
                                        ),
                                        width=6,
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
                                                    "New / Clear",
                                                    id="bulk-email-clear-draft-btn",
                                                    color="outline-secondary",
                                                    size="sm",
                                                ),
                                            ]
                                        ),
                                        width="auto",
                                        className="d-flex align-items-center",
                                    ),
                                    dbc.Col(
                                        html.Small(
                                            id="bulk-email-draft-mode-label",
                                            className="text-muted fst-italic",
                                        ),
                                        width="auto",
                                        className="d-flex align-items-center",
                                    ),
                                ],
                                className="mb-3",
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
                            # HTML email body
                            dbc.Label("Email Body"),
                            dmc.RichTextEditor(
                                id="bulk-email-html-source",
                                html="",
                                debounce=500,
                                extensions=[
                                    "StarterKit",
                                    "Superscript",
                                    "Subscript",
                                    "Highlight",
                                    "Table",
                                    "TableCell",
                                    "TableHeader",
                                    "TableRow",
                                    {"TextAlign": {"types": ["heading", "paragraph"]}},
                                    "Color",
                                    "TextStyle",
                                    "Image",
                                ],
                                toolbar={
                                    "sticky": True,
                                    "controlsGroups": [
                                        [
                                            "Bold",
                                            "Italic",
                                            "Underline",
                                            "Strikethrough",
                                            "ClearFormatting",
                                            "Highlight",
                                            "Code",
                                        ],
                                        ["H1", "H2", "H3", "H4"],
                                        ["Blockquote", "Hr", "BulletList", "OrderedList"],
                                        ["Subscript", "Superscript"],
                                        ["Link", "Unlink"],
                                        ["AlignLeft", "AlignCenter", "AlignJustify", "AlignRight"],
                                        [
                                            {"ColorPicker": {"colors": _EMAIL_COLORS}},
                                            "UnsetColor",
                                        ],
                                        ["Image"],
                                        [
                                            {
                                                "CustomControl": {
                                                    "aria-label": "Insert table",
                                                    "title": "Insert table",
                                                    "children": html.Span(
                                                        "⊞", style={"fontSize": "14px"}
                                                    ),
                                                    "onClick": {"function": "insertTable"},
                                                }
                                            },
                                            {
                                                "CustomControl": {
                                                    "aria-label": "Add column before",
                                                    "title": "Add column before",
                                                    "children": html.Span(
                                                        "←|", style={"fontSize": "11px"}
                                                    ),
                                                    "onClick": {"function": "addColumnBefore"},
                                                }
                                            },
                                            {
                                                "CustomControl": {
                                                    "aria-label": "Add column after",
                                                    "title": "Add column after",
                                                    "children": html.Span(
                                                        "|→", style={"fontSize": "11px"}
                                                    ),
                                                    "onClick": {"function": "addColumnAfter"},
                                                }
                                            },
                                            {
                                                "CustomControl": {
                                                    "aria-label": "Delete column",
                                                    "title": "Delete column",
                                                    "children": html.Span(
                                                        "✕|", style={"fontSize": "11px"}
                                                    ),
                                                    "onClick": {"function": "deleteColumn"},
                                                }
                                            },
                                            {
                                                "CustomControl": {
                                                    "aria-label": "Add row after",
                                                    "title": "Add row after",
                                                    "children": html.Span(
                                                        "—↓", style={"fontSize": "11px"}
                                                    ),
                                                    "onClick": {"function": "addRowAfter"},
                                                }
                                            },
                                            {
                                                "CustomControl": {
                                                    "aria-label": "Delete row",
                                                    "title": "Delete row",
                                                    "children": html.Span(
                                                        "✕—", style={"fontSize": "11px"}
                                                    ),
                                                    "onClick": {"function": "deleteRow"},
                                                }
                                            },
                                            {
                                                "CustomControl": {
                                                    "aria-label": "Delete table",
                                                    "title": "Delete table",
                                                    "children": html.Span(
                                                        "✕⊞", style={"fontSize": "11px"}
                                                    ),
                                                    "onClick": {"function": "deleteTable"},
                                                }
                                            },
                                        ],
                                        ["Undo", "Redo"],
                                        ["SourceCode"],
                                    ],
                                },
                                style={"minHeight": "300px"},
                            ),
                            # Live preview
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.Strong("Preview (sample substitutions):"),
                                            html.Div(
                                                id="bulk-email-preview-html",
                                                style={
                                                    "border": "1px solid #dee2e6",
                                                    "borderRadius": "4px",
                                                    "padding": "12px",
                                                    "minHeight": "100px",
                                                    "background": "#fff",
                                                },
                                            ),
                                        ],
                                        width=12,
                                    )
                                ],
                                className="mb-3",
                            ),
                            dbc.Button(
                                "Save Draft",
                                id="bulk-email-save-draft-btn",
                                color="success",
                            ),
                            dbc.Alert(
                                id="bulk-email-composer-alert",
                                is_open=False,
                                dismissable=True,
                                className="mt-2",
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
            dbc.Card(
                [
                    dbc.CardHeader(html.H5("Bulk Email History", className="mb-0")),
                    dbc.CardBody(
                        [
                            dbc.Button(
                                "Refresh",
                                id="bulk-email-history-refresh-btn",
                                color="outline-secondary",
                                size="sm",
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
