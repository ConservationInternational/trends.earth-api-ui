"""Bulk Email tab component.

This tab is only visible to SUPERADMIN users who are also on the
BULK_EMAIL_APPROVED_SENDERS list.
"""

from dash import dcc, html
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc

from ..i18n import gettext as _

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
            html.H3(_("Bulk Email"), className="mb-4"),
            # -------------------------------------------------------
            # Section 1 - Recipient Groups
            # -------------------------------------------------------
            dbc.Card(
                [
                    dbc.CardHeader(html.H5(_("Recipient Groups"), className="mb-0")),
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
                                            placeholder=_("Select a saved group to load..."),
                                        ),
                                        width=6,
                                    ),
                                    dbc.Col(
                                        dbc.ButtonGroup(
                                            [
                                                dbc.Button(
                                                    _("Load"),
                                                    id="bulk-email-load-rlist-btn",
                                                    color="secondary",
                                                    size="sm",
                                                ),
                                                dbc.Button(
                                                    _("Copy"),
                                                    id="bulk-email-copy-rlist-btn",
                                                    color="outline-secondary",
                                                    size="sm",
                                                ),
                                                dbc.Button(
                                                    _("Delete"),
                                                    id="bulk-email-delete-rlist-btn",
                                                    color="outline-danger",
                                                    size="sm",
                                                ),
                                                dbc.Button(
                                                    _("New / Clear"),
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
                                            dbc.Label(_("Group Name")),
                                            dbc.Input(
                                                id="bulk-email-rlist-name",
                                                type="text",
                                                placeholder=_("e.g. All active users"),
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label(_("Description (optional)")),
                                            dbc.Input(
                                                id="bulk-email-rlist-desc",
                                                type="text",
                                                placeholder=_("Short description"),
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
                                            dbc.Label(_("Roles")),
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
                                            dbc.Label(_("Email Verified")),
                                            dbc.Select(
                                                id="bulk-email-rlist-verified",
                                                options=[
                                                    {"label": _("Any"), "value": "any"},
                                                    {"label": _("Yes"), "value": "true"},
                                                    {"label": _("No"), "value": "false"},
                                                ],
                                                value="any",
                                            ),
                                        ],
                                        width=2,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label(_("Created After")),
                                            dbc.Input(
                                                id="bulk-email-rlist-min-created",
                                                type="date",
                                            ),
                                        ],
                                        width=3,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label(_("Created Before")),
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
                                            dbc.Label(_("Last Active After")),
                                            dbc.Input(
                                                id="bulk-email-rlist-min-activity",
                                                type="date",
                                            ),
                                        ],
                                        width=3,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label(_("Last Active Before")),
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
                                                _("Preview"),
                                                id="bulk-email-preview-btn",
                                                color="secondary",
                                                className="me-2",
                                            ),
                                            dbc.Button(
                                                _("Save Group"),
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
                                    {"field": "email", "headerName": _("Email"), "flex": 2},
                                    {"field": "name", "headerName": _("Name"), "flex": 1},
                                    {"field": "role", "headerName": _("Role"), "flex": 1},
                                    {
                                        "field": "email_verified",
                                        "headerName": _("Verified"),
                                        "flex": 1,
                                    },
                                    {"field": "created_at", "headerName": _("Created"), "flex": 1},
                                    {
                                        "field": "last_activity_at",
                                        "headerName": _("Last Active"),
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
                    dbc.CardHeader(html.H5(_("Email Composer"), className="mb-0")),
                    dbc.CardBody(
                        [
                            # Status alert — shown at the top so it's always visible
                            dbc.Alert(
                                id="bulk-email-composer-alert",
                                is_open=False,
                                dismissable=True,
                                className="mb-3",
                            ),
                            # Load existing draft
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.Select(
                                            id="bulk-email-load-draft-select",
                                            options=[],
                                            placeholder=_("Select a draft to load..."),
                                        ),
                                        width=6,
                                    ),
                                    dbc.Col(
                                        dbc.ButtonGroup(
                                            [
                                                dbc.Button(
                                                    _("Load"),
                                                    id="bulk-email-load-draft-btn",
                                                    color="secondary",
                                                    size="sm",
                                                ),
                                                dbc.Button(
                                                    _("Copy"),
                                                    id="bulk-email-copy-draft-btn",
                                                    color="outline-secondary",
                                                    size="sm",
                                                ),
                                                dbc.Button(
                                                    _("Delete"),
                                                    id="bulk-email-delete-draft-btn",
                                                    color="outline-danger",
                                                    size="sm",
                                                ),
                                                dbc.Button(
                                                    _("New / Clear"),
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
                            # Load template
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.Select(
                                            id="bulk-email-template-select",
                                            options=[
                                                {"label": _("(no template)"), "value": ""},
                                                {"label": _("News and updates"), "value": "news"},
                                                {
                                                    "label": _("User Engagement"),
                                                    "value": "engagement",
                                                },
                                                {
                                                    "label": _("System Update / Maintenance"),
                                                    "value": "system_update",
                                                },
                                            ],
                                            value="",
                                            placeholder=_("Load a template..."),
                                        ),
                                        width=6,
                                    ),
                                    dbc.Col(
                                        dbc.Button(
                                            "Load Template",
                                            id="bulk-email-load-template-btn",
                                            color="outline-primary",
                                            size="sm",
                                        ),
                                        width="auto",
                                        className="d-flex align-items-center",
                                    ),
                                ],
                                className="mb-3",
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label(_("Draft Name")),
                                            dbc.Input(
                                                id="bulk-email-name",
                                                type="text",
                                                placeholder=_("e.g. Q2 Newsletter"),
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label(_("Subject Line")),
                                            dbc.Input(
                                                id="bulk-email-subject",
                                                type="text",
                                                placeholder=_("Email subject"),
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
                                            dbc.Label(_("Email Category")),
                                            dbc.Select(
                                                id="bulk-email-category-select",
                                                options=[
                                                    {
                                                        "label": _("(none — send to all)"),
                                                        "value": "",
                                                    },
                                                    {
                                                        "label": _("News and updates"),
                                                        "value": "news",
                                                    },
                                                    {
                                                        "label": _("User Engagement"),
                                                        "value": "engagement",
                                                    },
                                                    {
                                                        "label": _("System Updates"),
                                                        "value": "system_updates",
                                                    },
                                                ],
                                                value="",
                                            ),
                                            html.Small(
                                                _(
                                                    "Only send to users subscribed to this category. "
                                                    "Set to '(none)' to send to all users."
                                                ),
                                                className="text-muted",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            # HTML email body
                            dbc.Label(_("Email Body")),
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
                                    "TableRow",
                                    "TableHeader",
                                    "TableCell",
                                    {"TextAlign": {"types": ["heading", "paragraph"]}},
                                    "TextStyle",
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
                                            {
                                                "CustomControl": {
                                                    "aria-label": "Insert table",
                                                    "title": "Insert table",
                                                    "children": "⊞",
                                                    "onClick": {"function": "insertTable"},
                                                }
                                            },
                                            {
                                                "CustomControl": {
                                                    "aria-label": "Add column before",
                                                    "title": "Add column before",
                                                    "children": "←|",
                                                    "onClick": {"function": "addColumnBefore"},
                                                }
                                            },
                                            {
                                                "CustomControl": {
                                                    "aria-label": "Add column after",
                                                    "title": "Add column after",
                                                    "children": "|→",
                                                    "onClick": {"function": "addColumnAfter"},
                                                }
                                            },
                                            {
                                                "CustomControl": {
                                                    "aria-label": "Delete column",
                                                    "title": "Delete column",
                                                    "children": "✕|",
                                                    "onClick": {"function": "deleteColumn"},
                                                }
                                            },
                                            {
                                                "CustomControl": {
                                                    "aria-label": "Add row after",
                                                    "title": "Add row after",
                                                    "children": "—↓",
                                                    "onClick": {"function": "addRowAfter"},
                                                }
                                            },
                                            {
                                                "CustomControl": {
                                                    "aria-label": "Delete row",
                                                    "title": "Delete row",
                                                    "children": "✕—",
                                                    "onClick": {"function": "deleteRow"},
                                                }
                                            },
                                            {
                                                "CustomControl": {
                                                    "aria-label": "Delete table",
                                                    "title": "Delete table",
                                                    "children": "✕⊞",
                                                    "onClick": {"function": "deleteTable"},
                                                }
                                            },
                                        ],
                                        ["Undo", "Redo"],
                                        ["SourceCode"],
                                    ],
                                },
                                style={"minHeight": "750px"},
                            ),
                            dbc.Button(
                                _("Save Draft"),
                                id="bulk-email-save-draft-btn",
                                color="success",
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
                    dbc.CardHeader(html.H5(_("Send Bulk Email"), className="mb-0")),
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label(_("Select Draft")),
                                            dbc.Select(
                                                id="bulk-email-send-select",
                                                options=[],
                                                placeholder=_("Choose a draft..."),
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label(_("Select Recipient Group")),
                                            dbc.Select(
                                                id="bulk-email-send-rlist-select",
                                                options=[],
                                                placeholder=_("Choose a recipient group..."),
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
                                        _("Send Test to Self"),
                                        id="bulk-email-send-test-self-btn",
                                        color="outline-secondary",
                                    ),
                                    dbc.Button(
                                        _("Send Test to Superadmins"),
                                        id="bulk-email-send-test-btn",
                                        color="secondary",
                                    ),
                                    dbc.Button(
                                        _("Send Bulk Email"),
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
                    dbc.CardHeader(html.H5(_("Bulk Email History"), className="mb-0")),
                    dbc.CardBody(
                        [
                            dbc.Button(
                                _("Refresh"),
                                id="bulk-email-history-refresh-btn",
                                color="outline-secondary",
                                size="sm",
                                className="mb-2",
                            ),
                            dag.AgGrid(
                                id="bulk-email-history-grid",
                                columnDefs=[
                                    {"field": "name", "headerName": _("Name"), "flex": 2},
                                    {
                                        "field": "subject",
                                        "headerName": _("Subject"),
                                        "flex": 3,
                                    },
                                    {
                                        "field": "status",
                                        "headerName": _("Status"),
                                        "flex": 1,
                                    },
                                    {
                                        "field": "recipient_count",
                                        "headerName": _("Recipients"),
                                        "flex": 1,
                                    },
                                    {
                                        "field": "sent_by",
                                        "headerName": _("Sent By"),
                                        "flex": 1,
                                    },
                                    {
                                        "field": "sent_at",
                                        "headerName": _("Sent At"),
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
