"""App Access tab component.

Lists per-application access requests/grants so ADMIN and SUPERADMIN users can
approve or revoke them, and lets SUPERADMIN users configure who is emailed
about new access requests for each application.
"""

from dash import dcc, html
import dash_bootstrap_components as dbc

from ..utils.helpers import is_superadmin

APP_ACCESS_STATUS_OPTIONS = [
    {"label": "Pending", "value": "pending"},
    {"label": "Active", "value": "active"},
    {"label": "Revoked", "value": "revoked"},
    {"label": "All", "value": "all"},
]


def _requests_card() -> dbc.Card:
    return dbc.Card(
        [
            dbc.CardHeader(html.H5("Access requests", className="mb-0")),
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("Application", html_for="app-access-app-filter"),
                                    dcc.Dropdown(
                                        id="app-access-app-filter",
                                        options=[],
                                        clearable=False,
                                        placeholder="Select an application",
                                    ),
                                ],
                                md=5,
                                className="mb-2",
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("Status", html_for="app-access-status-filter"),
                                    dcc.Dropdown(
                                        id="app-access-status-filter",
                                        options=APP_ACCESS_STATUS_OPTIONS,
                                        value="pending",
                                        clearable=False,
                                    ),
                                ],
                                md=4,
                                className="mb-2",
                            ),
                            dbc.Col(
                                dbc.Button(
                                    [html.I(className="fas fa-sync-alt me-1"), "Refresh"],
                                    id="app-access-refresh-btn",
                                    color="secondary",
                                    outline=True,
                                    n_clicks=0,
                                ),
                                md=3,
                                className="mb-2 d-flex align-items-end",
                            ),
                        ]
                    ),
                    dbc.Alert(
                        id="app-access-alert",
                        is_open=False,
                        dismissable=True,
                        className="mt-2",
                    ),
                    dbc.Input(
                        id="app-access-action-note",
                        type="text",
                        placeholder="Optional note recorded with approve/revoke actions",
                        className="mb-2",
                    ),
                    dcc.Loading(html.Div(id="app-access-requests-container")),
                ]
            ),
        ],
        className="mb-4",
    )


def _recipients_card(visible: bool) -> dbc.Card:
    return dbc.Card(
        [
            dbc.CardHeader(html.H5("Access request notification recipients", className="mb-0")),
            dbc.CardBody(
                [
                    html.P(
                        [
                            "Choose which admin or superadmin accounts are emailed when "
                            "someone requests access to the selected application. If no "
                            "one is listed, all superadmins are notified. Application "
                            "admins who can approve users for this application are always "
                            "notified in addition to the people listed here.",
                        ],
                        className="text-muted small",
                    ),
                    dbc.Label("Listed recipients", html_for="app-access-recipients-select"),
                    dcc.Dropdown(
                        id="app-access-recipients-select",
                        options=[],
                        value=[],
                        multi=True,
                        placeholder="No recipients listed (all superadmins are notified)",
                    ),
                    html.Div(id="app-access-recipients-candidates-status"),
                    html.Div(
                        dbc.Button(
                            "Save recipients",
                            id="app-access-recipients-save-btn",
                            color="primary",
                            className="mt-2",
                            n_clicks=0,
                            disabled=True,
                        ),
                    ),
                    dbc.Alert(
                        id="app-access-recipients-alert",
                        is_open=False,
                        dismissable=True,
                        className="mt-2",
                    ),
                    html.Hr(),
                    dcc.Loading(html.Div(id="app-access-recipients-summary")),
                ]
            ),
        ],
        id="app-access-recipients-card",
        className="mb-4",
        style={} if visible else {"display": "none"},
    )


def app_access_tab_content(role=None) -> html.Div:
    """Return the App Access tab layout.

    The recipients card is always part of the layout (so its callbacks have
    targets) but is hidden for non-superadmins; its callbacks also refuse to
    act for them.
    """
    return html.Div(
        [
            dcc.Store(id="app-access-apps-store", data=[]),
            dcc.Store(id="app-access-refresh-store", data=0),
            dcc.Store(id="app-access-recipient-candidates-store", data=[]),
            dcc.Store(id="app-access-recipients-listed-store", data=None),
            _requests_card(),
            _recipients_card(is_superadmin(role)),
        ],
        className="mt-3",
    )
