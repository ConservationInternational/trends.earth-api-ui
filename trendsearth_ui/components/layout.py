"""Base layout components for the Trends.Earth API Dashboard."""

import logging

from dash import dcc, html
import dash_bootstrap_components as dbc

from ..callbacks.timezone import get_timezone_components
from ..config import (
    APP_TITLE,
    DEFAULT_API_ENVIRONMENT,
    LOGO_SQUARE_URL,
    LOGO_URL,
)
from ..i18n import gettext as _
from ..i18n.dash_i18n import create_language_controls, create_language_selector
from ..utils.mobile_utils import create_mobile_detection_components
from .modals import (
    access_control_modal,
    delete_script_modal,
    delete_user_modal,
    edit_script_modal,
    edit_user_modal,
    json_modal,
    map_modal,
    reset_individual_rate_limit_modal,
    reset_rate_limits_modal,
)
from .news import create_news_banner

logger = logging.getLogger(__name__)


# =============================================================================
# Shared dropdown options for registration and profile forms
# =============================================================================
# These functions return translated dropdown options. They must be called at
# render time (inside layout functions) so that translations are evaluated
# with the current request's language context.


def get_sector_options():
    """Get sector dropdown options with translations.

    Returns:
        list: Sector options for dcc.Dropdown or dbc.Select.
    """
    return [
        {"label": "", "value": ""},
        {"label": _("Government - Environment/Natural Resources"), "value": "gov_environment"},
        {"label": _("Government - Agriculture"), "value": "gov_agriculture"},
        {"label": _("Government - Land Management/Planning"), "value": "gov_land_management"},
        {"label": _("Government - Other"), "value": "gov_other"},
        {"label": _("International/Multilateral Organization"), "value": "international_org"},
        {"label": _("NGO - Development/Aid"), "value": "ngo_development"},
        {"label": _("NGO - Community-Based"), "value": "ngo_community"},
        {"label": _("NGO - Conservation"), "value": "ngo_conservation"},
        {"label": _("NGO - Other"), "value": "ngo_other"},
        {"label": _("Academic/Research Institution"), "value": "academic"},
        {"label": _("Consulting/Professional Services"), "value": "consulting"},
        {"label": _("Private Sector - Agriculture/Forestry"), "value": "private_agri_forestry"},
        {"label": _("Private Sector - Other"), "value": "private_other"},
        {"label": _("Independent Researcher"), "value": "independent_researcher"},
        {"label": _("Student"), "value": "student"},
        {"label": _("Other"), "value": "other"},
    ]


def get_purpose_options():
    """Get purpose of use dropdown options with translations.

    Returns:
        list: Purpose options for dcc.Dropdown or dbc.Select.
    """
    return [
        {"label": "", "value": ""},
        {"label": _("National/International Reporting (UNCCD, SDGs, etc.)"), "value": "reporting"},
        {"label": _("Academic Research"), "value": "academic_research"},
        {"label": _("Policy Development & Planning"), "value": "policy_planning"},
        {"label": _("Land Restoration/Management Planning"), "value": "land_restoration"},
        {"label": _("Project Monitoring & Evaluation"), "value": "project_monitoring"},
        {"label": _("Environmental Impact Assessment"), "value": "environmental_assessment"},
        {"label": _("Agriculture/Forestry Planning"), "value": "agriculture_forestry"},
        {"label": _("Teaching & Education"), "value": "teaching_education"},
        {"label": _("Conservation Planning"), "value": "conservation_planning"},
        {"label": _("Commercial Services/Products"), "value": "commercial"},
        {"label": _("Community/Grassroots Initiatives"), "value": "community_initiatives"},
        {"label": _("Other"), "value": "other"},
    ]


def get_gender_options():
    """Get gender identity dropdown options with translations.

    Returns:
        list: Gender options for dcc.Dropdown or dbc.Select.
    """
    return [
        {"label": "", "value": ""},
        {"label": _("Woman"), "value": "woman"},
        {"label": _("Man"), "value": "man"},
        {"label": _("Non-binary"), "value": "non_binary"},
        {"label": _("Prefer to self-describe"), "value": "self_describe"},
        {"label": _("Prefer not to say"), "value": "prefer_not_to_say"},
    ]


def create_main_layout():
    """Create the main application layout with all stores and modals."""
    # Get timezone detection components
    timezone_components = get_timezone_components()

    # Get mobile detection components
    mobile_components = create_mobile_detection_components()

    return dbc.Container(
        [
            html.Div(id="page-content", children=login_layout()),
            html.Div(id="tab-content"),
            # URL component for navigation tracking
            dcc.Location(id="url", refresh=False),
            # Data stores
            dcc.Store(id="token-store"),
            dcc.Store(id="role-store"),
            dcc.Store(id="user-store"),
            dcc.Store(id="api-environment-store", data=DEFAULT_API_ENVIRONMENT),
            dcc.Store(id="json-modal-data"),
            dcc.Store(id="scripts-raw-data"),
            dcc.Store(id="users-raw-data"),
            dcc.Store(id="current-log-context"),
            dcc.Store(id="edit-user-data"),
            dcc.Store(id="edit-user-modal-user-id"),  # Derived user ID for admin edit sub-callbacks
            dcc.Store(id="edit-script-data"),
            dcc.Store(
                id="executions-table-state"
            ),  # Store current sort/filter state for executions table
            dcc.Store(id="users-table-state"),  # Store current sort/filter state for users table
            dcc.Store(
                id="scripts-table-state"
            ),  # Store current sort/filter state for scripts table
            dcc.Store(
                id="rate-limit-breaches-table-state"
            ),  # Store current sort/filter state for rate limit breaches
            dcc.Store(
                id="executions-total-count-store", data=0
            ),  # Store total count for executions
            dcc.Store(id="users-total-count-store", data=0),  # Store total count for users
            dcc.Store(id="scripts-total-count-store", data=0),  # Store total count for scripts
            dcc.Store(
                id="rate-limit-breaches-total-count-store", data=0
            ),  # Store total count for rate limit breaches
            dcc.Store(id="active-tab-store", data="executions"),
            dcc.Store(id="user-store-cookie-sync"),  # Hidden sink for cookie sync callback
            dcc.Store(id="gee-oauth-redirect-url"),  # Holds external OAuth URL for JS redirect
            dcc.Store(id="delete-user-data"),  # Store data for user being deleted
            dcc.Store(id="delete-script-data"),  # Store data for script being deleted
            dcc.Store(id="selected-rate-limit-data"),  # Store data for selected rate limit to reset
            # Timezone detection components
            *timezone_components,
            # Mobile detection components
            *mobile_components,
            # Language controls for i18n
            *create_language_controls(),
            # Modals
            json_modal(),
            edit_user_modal(),
            edit_script_modal(),
            access_control_modal(),
            map_modal(),
            delete_user_modal(),
            delete_script_modal(),
            reset_rate_limits_modal(),
            reset_individual_rate_limit_modal(),
        ],
        fluid=True,
    )


def login_layout():
    """Create the login page layout."""
    return html.Div(
        [
            # Stores are defined globally in the main layout; avoid duplicates here
            # Forgot password modal
            dbc.Modal(
                [
                    dbc.ModalHeader(
                        dbc.ModalTitle(_("Forgot Password")),
                        close_button=True,
                    ),
                    dbc.ModalBody(
                        [
                            # Form section (visible initially)
                            html.Div(
                                [
                                    html.P(
                                        _(
                                            "Enter your email address and we'll send you instructions to reset your password."
                                        )
                                    ),
                                    dbc.Label(_("Email Address")),
                                    dbc.Input(
                                        id="forgot-password-email",
                                        type="email",
                                        placeholder=_("Enter your email address"),
                                        className="mb-3",
                                    ),
                                ],
                                id="forgot-password-form",
                                style={"display": "block"},
                            ),
                            # Alert section (for messages)
                            dbc.Alert(
                                id="forgot-password-alert",
                                is_open=False,
                                dismissable=False,  # Don't allow dismissing
                                duration=None,  # Don't auto-dismiss
                            ),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            # Initial buttons (visible initially)
                            html.Div(
                                [
                                    dbc.Button(
                                        _("Cancel"),
                                        id="cancel-forgot-password",
                                        color="secondary",
                                        className="me-2",
                                    ),
                                    dbc.Button(
                                        _("Send Reset Instructions"),
                                        id="send-reset-btn",
                                        color="primary",
                                    ),
                                ],
                                id="forgot-password-initial-buttons",
                                style={"display": "block"},
                            ),
                            # Success button (hidden initially)
                            html.Div(
                                [
                                    dbc.Button(
                                        _("OK"),
                                        id="forgot-password-ok-btn",
                                        color="primary",
                                    ),
                                ],
                                id="forgot-password-success-buttons",
                                style={"display": "none"},
                            ),
                        ]
                    ),
                ],
                id="forgot-password-modal",
                is_open=False,
                centered=True,
                backdrop="static",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        html.Div(
                                            [
                                                html.Img(
                                                    src=LOGO_URL,
                                                    alt="Trends.Earth Logo",
                                                    style={
                                                        "maxWidth": "100%",
                                                        "width": "450px",
                                                        "height": "auto",
                                                        "marginBottom": "15px",
                                                    },
                                                ),
                                                html.H4(_("Login"), style={"color": "white"}),
                                            ],
                                            className="text-center",
                                        ),
                                        style={
                                            "backgroundColor": "#495057",
                                            "padding": "20px",
                                        },
                                    ),
                                    dbc.CardBody(
                                        [
                                            # Language selector just above the form
                                            html.Div(
                                                create_language_selector(id_prefix="login-lang"),
                                                className="mb-3",
                                            ),
                                            dbc.Form(
                                                [
                                                    dbc.Row(
                                                        [
                                                            dbc.Label(_("Email"), width=4),
                                                            dbc.Col(
                                                                dbc.Input(
                                                                    id="login-email",
                                                                    type="email",
                                                                    placeholder=_("Enter email"),
                                                                ),
                                                                width=8,
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    dbc.Row(
                                                        [
                                                            dbc.Label(_("Password"), width=4),
                                                            dbc.Col(
                                                                dbc.Input(
                                                                    id="login-password",
                                                                    type="password",
                                                                    placeholder=_("Enter password"),
                                                                ),
                                                                width=8,
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    # Hidden input to maintain callback compatibility
                                                    # API environment is now auto-detected from subdomain
                                                    html.Div(
                                                        dcc.Input(
                                                            id="api-environment-dropdown",
                                                            type="hidden",
                                                            value="",
                                                        ),
                                                        style={"display": "none"},
                                                    ),
                                                    dbc.Row(
                                                        [
                                                            dbc.Col(
                                                                dbc.Checkbox(
                                                                    id="remember-me-checkbox",
                                                                    label=_(
                                                                        "Remember me (keep me logged in)"
                                                                    ),
                                                                    value=True,
                                                                ),
                                                                width=12,
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    dbc.Button(
                                                        _("Login"),
                                                        id="login-btn",
                                                        color="primary",
                                                        className="mt-2",
                                                        n_clicks=0,
                                                        style={"width": "100%"},
                                                    ),
                                                    dbc.Button(
                                                        _("Register"),
                                                        id="register-btn",
                                                        color="secondary",
                                                        outline=True,
                                                        className="mt-2",
                                                        n_clicks=0,
                                                        style={"width": "100%"},
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.A(
                                                                _("Forgot your password?"),
                                                                id="forgot-password-link",
                                                                href="#",
                                                                className="text-primary",
                                                                style={
                                                                    "textDecoration": "none",
                                                                    "fontSize": "14px",
                                                                },
                                                            ),
                                                        ],
                                                        className="text-center mt-3",
                                                    ),
                                                    html.Div(
                                                        id="login-feedback",
                                                        style={
                                                            "marginTop": "10px",
                                                            "minHeight": "20px",
                                                        },
                                                    ),
                                                ]
                                            ),
                                            html.Hr(),
                                            dbc.Alert(
                                                id="login-alert",
                                                is_open=False,
                                                dismissable=True,
                                                duration=None,
                                            ),
                                            html.Div(
                                                [
                                                    html.A(
                                                        _("Privacy Policy"),
                                                        href="https://www.conservation.org/policies/privacy",
                                                        target="_blank",
                                                        className="text-muted",
                                                        style={
                                                            "textDecoration": "none",
                                                            "fontSize": "12px",
                                                        },
                                                    ),
                                                    html.Span(
                                                        " | ",
                                                        className="text-muted",
                                                        style={"fontSize": "12px"},
                                                    ),
                                                    html.A(
                                                        _("Terms of Use"),
                                                        href="https://www.conservation.org/policies/terms-of-use",
                                                        target="_blank",
                                                        className="text-muted",
                                                        style={
                                                            "textDecoration": "none",
                                                            "fontSize": "12px",
                                                        },
                                                    ),
                                                ],
                                                className="text-center mt-3",
                                            ),
                                            html.Div(
                                                html.A(
                                                    "trends.earth",
                                                    href="https://trends.earth",
                                                    target="_blank",
                                                    className="text-muted",
                                                    style={
                                                        "textDecoration": "none",
                                                        "fontSize": "12px",
                                                    },
                                                ),
                                                className="text-center mt-1",
                                            ),
                                        ]
                                    ),
                                ],
                                style={"maxWidth": "400px"},
                            ),
                        ],
                        width="auto",
                        className="mx-auto mt-4",
                    ),
                ],
                className="justify-content-center",
            ),
        ]
    )


def reset_password_layout(token=None, api_environment="production"):
    """Create the password reset page layout.

    This page is shown when users click the password reset link from their email.
    They can enter a new password here.

    Args:
        token: The password reset token from the URL
        api_environment: The API environment to use
    """
    return html.Div(
        [
            # Forgot password modal placeholder (needed for consistent page structure)
            dbc.Modal(id="forgot-password-modal", is_open=False),
            dbc.Container(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Div(
                                        [
                                            html.Div(
                                                html.Img(
                                                    src=LOGO_URL,
                                                    style={
                                                        "maxWidth": "100%",
                                                        "width": "450px",
                                                        "height": "auto",
                                                    },
                                                ),
                                                style={
                                                    "backgroundColor": "#495057",
                                                    "padding": "20px 30px",
                                                    "textAlign": "center",
                                                    "display": "flex",
                                                    "justifyContent": "center",
                                                    "alignItems": "center",
                                                },
                                                className="mb-4",
                                            ),
                                            html.H4(
                                                _("Set Your New Password"),
                                                className="mb-4",
                                            ),
                                            html.P(
                                                _("Enter your new password below."),
                                                className="text-muted mb-4",
                                            ),
                                            # Language selector
                                            html.Div(
                                                create_language_selector(id_prefix="reset-lang"),
                                                className="mb-3",
                                            ),
                                            # Hidden stores for token and environment
                                            dcc.Store(
                                                id="reset-password-token",
                                                data=token,
                                            ),
                                            dcc.Store(
                                                id="reset-password-api-env",
                                                data=api_environment,
                                            ),
                                            dbc.Form(
                                                [
                                                    dbc.Row(
                                                        [
                                                            dbc.Label(_("New Password"), width=4),
                                                            dbc.Col(
                                                                dbc.Input(
                                                                    id="reset-new-password",
                                                                    type="password",
                                                                    placeholder=_(
                                                                        "Enter new password"
                                                                    ),
                                                                ),
                                                                width=8,
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    dbc.Row(
                                                        [
                                                            dbc.Label(
                                                                _("Confirm Password"), width=4
                                                            ),
                                                            dbc.Col(
                                                                dbc.Input(
                                                                    id="reset-confirm-password",
                                                                    type="password",
                                                                    placeholder=_(
                                                                        "Confirm new password"
                                                                    ),
                                                                ),
                                                                width=8,
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    html.Div(
                                                        id="password-requirements",
                                                        children=[
                                                            html.Small(
                                                                _("Password requirements:"),
                                                                className="text-muted d-block mb-1",
                                                            ),
                                                            html.Ul(
                                                                [
                                                                    html.Li(
                                                                        _("At least 12 characters"),
                                                                        id="req-length",
                                                                        className="text-muted",
                                                                    ),
                                                                    html.Li(
                                                                        _("Uppercase letter (A-Z)"),
                                                                        id="req-uppercase",
                                                                        className="text-muted",
                                                                    ),
                                                                    html.Li(
                                                                        _("Lowercase letter (a-z)"),
                                                                        id="req-lowercase",
                                                                        className="text-muted",
                                                                    ),
                                                                    html.Li(
                                                                        _("Number (0-9)"),
                                                                        id="req-number",
                                                                        className="text-muted",
                                                                    ),
                                                                    html.Li(
                                                                        _(
                                                                            "Special character (!@#$%^&*()-_=+[]{}|;:,.<>?/)"
                                                                        ),
                                                                        id="req-special",
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
                                                                        _("Set Password"),
                                                                        id="reset-password-submit-btn",
                                                                        color="primary",
                                                                        className="w-100",
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
                                                                        _("Back to Login"),
                                                                        id="reset-password-back-btn",
                                                                        color="link",
                                                                        className="w-100",
                                                                        href="/",
                                                                    ),
                                                                ],
                                                                width=12,
                                                            ),
                                                        ],
                                                    ),
                                                ]
                                            ),
                                            dbc.Alert(
                                                id="reset-password-alert",
                                                is_open=False,
                                                dismissable=True,
                                                duration=None,
                                            ),
                                            html.Hr(),
                                            html.Div(
                                                [
                                                    html.A(
                                                        _("Privacy Policy"),
                                                        href="https://www.conservation.org/policies/privacy",
                                                        target="_blank",
                                                        className="text-muted",
                                                        style={
                                                            "textDecoration": "none",
                                                            "fontSize": "12px",
                                                        },
                                                    ),
                                                    html.Span(
                                                        " | ",
                                                        className="text-muted",
                                                        style={"fontSize": "12px"},
                                                    ),
                                                    html.A(
                                                        _("Terms of Use"),
                                                        href="https://www.conservation.org/policies/terms-of-use",
                                                        target="_blank",
                                                        className="text-muted",
                                                        style={
                                                            "textDecoration": "none",
                                                            "fontSize": "12px",
                                                        },
                                                    ),
                                                ],
                                                className="text-center mt-3",
                                            ),
                                            html.Div(
                                                html.A(
                                                    "trends.earth",
                                                    href="https://trends.earth",
                                                    target="_blank",
                                                    className="text-muted",
                                                    style={
                                                        "textDecoration": "none",
                                                        "fontSize": "12px",
                                                    },
                                                ),
                                                className="text-center mt-1",
                                            ),
                                        ]
                                    ),
                                ],
                                style={"maxWidth": "450px"},
                                width=6,
                                className="mx-auto mt-4",
                            ),
                        ]
                    ),
                ]
            ),
        ]
    )


def gee_oauth_callback_layout(code=None, state=None, api_environment="production"):
    """Create the GEE OAuth callback page layout.

    This page is shown after Google redirects the user back following OAuth
    authorization.  It auto-processes the code/state parameters and reports
    success or failure.

    Args:
        code: The authorization code returned by Google
        state: The CSRF state token returned by Google
        api_environment: The API environment to use
    """
    has_params = bool(code and state)

    return html.Div(
        [
            # Modal placeholder for consistent page structure
            dbc.Modal(id="forgot-password-modal", is_open=False),
            dbc.Container(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Div(
                                        [
                                            html.Div(
                                                html.Img(
                                                    src=LOGO_URL,
                                                    style={
                                                        "maxWidth": "100%",
                                                        "width": "450px",
                                                        "height": "auto",
                                                    },
                                                ),
                                                style={
                                                    "backgroundColor": "#495057",
                                                    "padding": "20px 30px",
                                                    "textAlign": "center",
                                                    "display": "flex",
                                                    "justifyContent": "center",
                                                    "alignItems": "center",
                                                },
                                                className="mb-4",
                                            ),
                                            html.H4(
                                                _("Connect Google Earth Engine"),
                                                className="mb-4",
                                            ),
                                            # Hidden stores for code, state, environment
                                            dcc.Store(
                                                id="gee-oauth-callback-code",
                                                data=code,
                                            ),
                                            dcc.Store(
                                                id="gee-oauth-callback-state",
                                                data=state,
                                            ),
                                            dcc.Store(
                                                id="gee-oauth-callback-api-env",
                                                data=api_environment,
                                            ),
                                            # Auto-process trigger: fires once after a short
                                            # delay so token-store is populated first
                                            dcc.Interval(
                                                id="gee-oauth-auto-process",
                                                interval=600,
                                                max_intervals=1 if has_params else 0,
                                                n_intervals=0,
                                            ),
                                            # Interval that triggers the GCP project fetch
                                            # after OAuth succeeds.  Starts disabled;
                                            # process_gee_oauth_callback enables it.
                                            dcc.Interval(
                                                id="gee-project-load-interval",
                                                interval=500,
                                                max_intervals=0,
                                                n_intervals=0,
                                                disabled=True,
                                            ),
                                            # Processing status area
                                            html.Div(
                                                id="gee-oauth-processing-container",
                                                children=(
                                                    html.Div(
                                                        [
                                                            dbc.Spinner(
                                                                size="sm",
                                                                color="primary",
                                                                type="border",
                                                                spinner_class_name="me-2",
                                                            ),
                                                            html.Span(
                                                                _(
                                                                    "Connecting your Google"
                                                                    " Earth Engine account…"
                                                                ),
                                                                className="text-muted",
                                                            ),
                                                        ],
                                                        className="d-flex align-items-center mb-3",
                                                    )
                                                    if has_params
                                                    else dbc.Alert(
                                                        _(
                                                            "Invalid callback — missing"
                                                            " authorization parameters."
                                                        ),
                                                        color="danger",
                                                        className="mb-3",
                                                    )
                                                ),
                                            ),
                                            dbc.Alert(
                                                id="gee-oauth-callback-alert",
                                                is_open=False,
                                                dismissable=True,
                                                duration=None,
                                                className="mb-3",
                                            ),
                                            # Project selection — hidden until OAuth
                                            # succeeds and GCP projects are fetched.
                                            html.Div(
                                                id="gee-project-selection-container",
                                                style={"display": "none"},
                                                children=[
                                                    html.Hr(),
                                                    html.H6(
                                                        _("Select your GEE Cloud Project"),
                                                        className="mb-2",
                                                    ),
                                                    html.P(
                                                        _(
                                                            "Select the Google Cloud "
                                                            "project where Earth Engine "
                                                            "API is enabled. API usage "
                                                            "will be billed to this "
                                                            "project."
                                                        ),
                                                        className="text-muted small mb-3",
                                                    ),
                                                    dcc.Dropdown(
                                                        id="gee-project-dropdown",
                                                        placeholder=_("Select a project…"),
                                                        clearable=False,
                                                        className="mb-2",
                                                    ),
                                                    # Manual fallback — shown when the
                                                    # project list is empty or failed to load.
                                                    html.Div(
                                                        id="gee-project-manual-container",
                                                        style={"display": "none"},
                                                        children=[
                                                            html.P(
                                                                [
                                                                    html.I(
                                                                        className="fas fa-exclamation-triangle me-1 text-warning"
                                                                    ),
                                                                    _(
                                                                        "Could not load your project list."
                                                                        " Enter your GCP project ID manually:"
                                                                    ),
                                                                ],
                                                                className="small text-muted mb-1",
                                                            ),
                                                            dbc.Input(
                                                                id="gee-project-manual-input",
                                                                placeholder="my-gcp-project-id",
                                                                type="text",
                                                                debounce=True,
                                                                className="mb-2",
                                                            ),
                                                            html.P(
                                                                _(
                                                                    "Find your project ID in the"
                                                                    " Google Cloud Console."
                                                                ),
                                                                className="text-muted",
                                                                style={"fontSize": "11px"},
                                                            ),
                                                        ],
                                                    ),
                                                    dbc.Button(
                                                        _("Save Project"),
                                                        id="gee-project-save-btn",
                                                        color="primary",
                                                        className="w-100 mb-3",
                                                    ),
                                                    dbc.Alert(
                                                        id="gee-project-save-alert",
                                                        is_open=False,
                                                        dismissable=True,
                                                    ),
                                                ],
                                            ),
                                            html.Hr(),
                                            dbc.Button(
                                                _("Back to App"),
                                                id="gee-oauth-back-btn",
                                                color="link",
                                                className="w-100",
                                                href="/",
                                            ),
                                            html.Hr(),
                                            html.Div(
                                                [
                                                    html.A(
                                                        _("Privacy Policy"),
                                                        href="https://www.conservation.org/policies/privacy",
                                                        target="_blank",
                                                        className="text-muted",
                                                        style={
                                                            "textDecoration": "none",
                                                            "fontSize": "12px",
                                                        },
                                                    ),
                                                    html.Span(
                                                        " | ",
                                                        className="text-muted",
                                                        style={"fontSize": "12px"},
                                                    ),
                                                    html.A(
                                                        _("Terms of Use"),
                                                        href="https://www.conservation.org/policies/terms-of-use",
                                                        target="_blank",
                                                        className="text-muted",
                                                        style={
                                                            "textDecoration": "none",
                                                            "fontSize": "12px",
                                                        },
                                                    ),
                                                ],
                                                className="text-center mt-3",
                                            ),
                                            html.Div(
                                                html.A(
                                                    "trends.earth",
                                                    href="https://trends.earth",
                                                    target="_blank",
                                                    className="text-muted",
                                                    style={
                                                        "textDecoration": "none",
                                                        "fontSize": "12px",
                                                    },
                                                ),
                                                className="text-center mt-1",
                                            ),
                                        ]
                                    ),
                                ],
                                style={"maxWidth": "450px"},
                                width=6,
                                className="mx-auto mt-4",
                            ),
                        ]
                    ),
                ]
            ),
        ]
    )


def registration_layout():
    """Create the user registration page layout.

    Note: API environment is now auto-detected from the request subdomain.
    """
    # Get dropdown options from shared helper functions
    # Note: These functions use _() (gettext) for immediate translation - returns regular strings
    # that are JSON serializable, unlike lazy_gettext which returns LazyString
    sector_options = get_sector_options()
    purpose_options = get_purpose_options()
    gender_options = get_gender_options()

    return html.Div(
        [
            dbc.Container(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Div(
                                        [
                                            html.Div(
                                                html.Img(
                                                    src=LOGO_URL,
                                                    style={
                                                        "maxWidth": "100%",
                                                        "width": "450px",
                                                        "height": "auto",
                                                    },
                                                ),
                                                style={
                                                    "backgroundColor": "#495057",
                                                    "padding": "20px 30px",
                                                    "textAlign": "center",
                                                    "display": "flex",
                                                    "justifyContent": "center",
                                                    "alignItems": "center",
                                                },
                                                className="mb-4",
                                            ),
                                            html.H4(
                                                _("Create Your Account"),
                                                className="mb-4 text-center",
                                            ),
                                            html.P(
                                                _(
                                                    "After registration, you'll receive an email to verify your address and set your password."
                                                ),
                                                className="text-muted text-center mb-4",
                                                style={"fontSize": "14px"},
                                            ),
                                            # Language selector
                                            html.Div(
                                                create_language_selector(id_prefix="register-lang"),
                                                className="mb-3",
                                            ),
                                            html.P(
                                                [
                                                    html.Span("* ", style={"color": "red"}),
                                                    _("Required field"),
                                                ],
                                                className="text-muted mb-3",
                                                style={"fontSize": "12px"},
                                            ),
                                            dbc.Form(
                                                [
                                                    # Email
                                                    dbc.Row(
                                                        [
                                                            dbc.Label(
                                                                [
                                                                    html.Strong(_("Email")),
                                                                    html.Span(
                                                                        " *",
                                                                        style={"color": "red"},
                                                                    ),
                                                                ],
                                                                width=4,
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Input(
                                                                        id="register-email",
                                                                        type="email",
                                                                        placeholder=_(
                                                                            "Enter your email address"
                                                                        ),
                                                                    ),
                                                                ],
                                                                width=8,
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    # Name
                                                    dbc.Row(
                                                        [
                                                            dbc.Label(
                                                                [
                                                                    html.Strong(_("Full Name")),
                                                                    html.Span(
                                                                        " *",
                                                                        style={"color": "red"},
                                                                    ),
                                                                ],
                                                                width=4,
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Input(
                                                                        id="register-name",
                                                                        type="text",
                                                                        placeholder=_(
                                                                            "Enter your full name"
                                                                        ),
                                                                    ),
                                                                ],
                                                                width=8,
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    # Role/Title
                                                    dbc.Row(
                                                        [
                                                            dbc.Label(_("Role/Title"), width=4),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Input(
                                                                        id="register-role-title",
                                                                        type="text",
                                                                        placeholder=_(
                                                                            "Your job title (optional)"
                                                                        ),
                                                                    ),
                                                                ],
                                                                width=8,
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    # Institution/Organization
                                                    dbc.Row(
                                                        [
                                                            dbc.Label(
                                                                [
                                                                    html.Strong(_("Organization")),
                                                                    html.Span(
                                                                        " *",
                                                                        style={"color": "red"},
                                                                    ),
                                                                ],
                                                                width=4,
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Input(
                                                                        id="register-institution",
                                                                        type="text",
                                                                        placeholder=_(
                                                                            "Your organization"
                                                                        ),
                                                                    ),
                                                                ],
                                                                width=8,
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    # Sector
                                                    dbc.Row(
                                                        [
                                                            dbc.Label(
                                                                [
                                                                    html.Strong(_("Sector")),
                                                                    html.Span(
                                                                        " *",
                                                                        style={"color": "red"},
                                                                    ),
                                                                ],
                                                                width=4,
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dcc.Dropdown(
                                                                        id="register-sector",
                                                                        options=sector_options,
                                                                        placeholder=_(
                                                                            "Select your sector"
                                                                        ),
                                                                        clearable=True,
                                                                        style={"fontSize": "14px"},
                                                                    ),
                                                                ],
                                                                width=8,
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    # Sector Other (conditional)
                                                    dbc.Row(
                                                        [
                                                            dbc.Label(_("Please specify"), width=4),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Input(
                                                                        id="register-sector-other",
                                                                        type="text",
                                                                        placeholder=_(
                                                                            "Please specify your sector"
                                                                        ),
                                                                    ),
                                                                ],
                                                                width=8,
                                                            ),
                                                        ],
                                                        id="register-sector-other-row",
                                                        className="mb-3",
                                                        style={"display": "none"},
                                                    ),
                                                    # Purpose of Use
                                                    dbc.Row(
                                                        [
                                                            dbc.Label(
                                                                [
                                                                    html.Strong(
                                                                        _("Purpose of Use")
                                                                    ),
                                                                    html.Span(
                                                                        " *",
                                                                        style={"color": "red"},
                                                                    ),
                                                                ],
                                                                width=4,
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dcc.Dropdown(
                                                                        id="register-purpose",
                                                                        options=purpose_options,
                                                                        placeholder=_(
                                                                            "Select your purpose of use"
                                                                        ),
                                                                        clearable=True,
                                                                        style={"fontSize": "14px"},
                                                                    ),
                                                                ],
                                                                width=8,
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    # Purpose Other (conditional)
                                                    dbc.Row(
                                                        [
                                                            dbc.Label(_("Please specify"), width=4),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Input(
                                                                        id="register-purpose-other",
                                                                        type="text",
                                                                        placeholder=_(
                                                                            "Please specify your purpose"
                                                                        ),
                                                                    ),
                                                                ],
                                                                width=8,
                                                            ),
                                                        ],
                                                        id="register-purpose-other-row",
                                                        className="mb-3",
                                                        style={"display": "none"},
                                                    ),
                                                    # Country
                                                    dbc.Row(
                                                        [
                                                            dbc.Label(
                                                                [
                                                                    html.Strong(_("Country")),
                                                                    html.Span(
                                                                        " *",
                                                                        style={"color": "red"},
                                                                    ),
                                                                ],
                                                                width=4,
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dcc.Dropdown(
                                                                        id="register-country",
                                                                        placeholder=_(
                                                                            "Select your country"
                                                                        ),
                                                                        clearable=True,
                                                                        style={"fontSize": "14px"},
                                                                    ),
                                                                    dcc.Store(
                                                                        id="register-countries-store"
                                                                    ),
                                                                ],
                                                                width=8,
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    # Gender Identity
                                                    dbc.Row(
                                                        [
                                                            dbc.Label(
                                                                _("Gender Identity"), width=4
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dcc.Dropdown(
                                                                        id="register-gender",
                                                                        options=gender_options,
                                                                        placeholder=_(
                                                                            "Select (optional)"
                                                                        ),
                                                                        clearable=True,
                                                                        style={"fontSize": "14px"},
                                                                    ),
                                                                ],
                                                                width=8,
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    # Gender note
                                                    html.P(
                                                        _(
                                                            "We collect gender identity information to comply with donor reporting requirements and to assess equitable participation in capacity development and tool access. Providing this information is voluntary; your selection will not affect your access to the tool."
                                                        ),
                                                        className="text-muted mb-3",
                                                        style={"fontSize": "12px"},
                                                    ),
                                                    # Gender Description (conditional)
                                                    dbc.Row(
                                                        [
                                                            dbc.Label(
                                                                _("Please describe"), width=4
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Input(
                                                                        id="register-gender-description",
                                                                        type="text",
                                                                        placeholder=_(
                                                                            "Please describe"
                                                                        ),
                                                                    ),
                                                                ],
                                                                width=8,
                                                            ),
                                                        ],
                                                        id="register-gender-description-row",
                                                        className="mb-3",
                                                        style={"display": "none"},
                                                    ),
                                                    # Hidden password inputs to satisfy callback dependencies
                                                    html.Div(
                                                        [
                                                            dbc.Input(
                                                                id="register-password",
                                                                type="hidden",
                                                                value="",
                                                            ),
                                                            dbc.Input(
                                                                id="register-password-confirm",
                                                                type="hidden",
                                                                value="",
                                                            ),
                                                        ],
                                                        style={"display": "none"},
                                                    ),
                                                    # Hidden input to maintain callback compatibility
                                                    # API environment is now auto-detected from subdomain
                                                    html.Div(
                                                        dcc.Input(
                                                            id="register-api-environment",
                                                            type="hidden",
                                                            value="",
                                                        ),
                                                        style={"display": "none"},
                                                    ),
                                                    # GEE License Acknowledgment
                                                    html.Div(
                                                        [
                                                            html.P(
                                                                [
                                                                    html.Strong(
                                                                        _(
                                                                            "Do you acknowledge that some Trends.Earth features use Google Earth Engine, and, depending on your use, you may be required to have in place a commercial license to use Google Earth Engine?"
                                                                        )
                                                                    ),
                                                                    html.Span(
                                                                        " *",
                                                                        style={"color": "red"},
                                                                    ),
                                                                ],
                                                                className="mb-2",
                                                            ),
                                                            html.P(
                                                                [
                                                                    _(
                                                                        "Google Earth Engine (GEE) imposes restrictions on commercial use. For more details see the "
                                                                    ),
                                                                    html.A(
                                                                        _(
                                                                            "Google Earth Engine Terms of Use"
                                                                        ),
                                                                        href="https://earthengine.google.com/terms/",
                                                                        target="_blank",
                                                                    ),
                                                                    _(
                                                                        " . Conservation International does not provide or manage commercial GEE licenses. Users are solely responsible for ensuring their use of GEE complies with Google's commercial licensing requirements. Access to this tool does not grant or imply the provision of commercial licensing."
                                                                    ),
                                                                ],
                                                                className="text-muted mb-3",
                                                                style={"fontSize": "12px"},
                                                            ),
                                                            html.Div(
                                                                dbc.Checkbox(
                                                                    id="register-gee-acknowledged",
                                                                    label=_("Yes, I acknowledge"),
                                                                    value=False,
                                                                ),
                                                                className="mb-3 d-flex justify-content-center",
                                                            ),
                                                        ],
                                                        style={
                                                            "border": "1px solid #dee2e6",
                                                            "borderRadius": "5px",
                                                            "padding": "15px",
                                                            "marginBottom": "15px",
                                                        },
                                                    ),
                                                    # Alert for validation messages (above button so visible without scrolling)
                                                    dbc.Alert(
                                                        id="register-alert",
                                                        is_open=False,
                                                        dismissable=True,
                                                        duration=None,
                                                    ),
                                                    dbc.Row(
                                                        [
                                                            dbc.Col(
                                                                [
                                                                    dbc.Button(
                                                                        _("Create Account"),
                                                                        id="register-submit-btn",
                                                                        color="primary",
                                                                        className="w-100",
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
                                                                        _("Back to Login"),
                                                                        id="register-back-btn",
                                                                        color="link",
                                                                        className="w-100",
                                                                    ),
                                                                ],
                                                                width=12,
                                                            ),
                                                        ],
                                                    ),
                                                ]
                                            ),
                                            html.Hr(),
                                            html.Div(
                                                [
                                                    html.A(
                                                        _("Privacy Policy"),
                                                        href="https://www.conservation.org/policies/privacy",
                                                        target="_blank",
                                                        className="text-muted",
                                                        style={
                                                            "textDecoration": "none",
                                                            "fontSize": "12px",
                                                        },
                                                    ),
                                                    html.Span(
                                                        " | ",
                                                        className="text-muted",
                                                        style={"fontSize": "12px"},
                                                    ),
                                                    html.A(
                                                        _("Terms of Use"),
                                                        href="https://www.conservation.org/policies/terms-of-use",
                                                        target="_blank",
                                                        className="text-muted",
                                                        style={
                                                            "textDecoration": "none",
                                                            "fontSize": "12px",
                                                        },
                                                    ),
                                                ],
                                                className="text-center mt-3",
                                            ),
                                            html.Div(
                                                html.A(
                                                    "trends.earth",
                                                    href="https://trends.earth",
                                                    target="_blank",
                                                    className="text-muted",
                                                    style={
                                                        "textDecoration": "none",
                                                        "fontSize": "12px",
                                                    },
                                                ),
                                                className="text-center mt-1",
                                            ),
                                        ]
                                    ),
                                ],
                                style={"maxWidth": "600px"},
                                width=6,
                                className="mx-auto mt-4",
                            ),
                        ]
                    ),
                ]
            ),
        ],
        style={
            "height": "100vh",
            "overflowY": "auto",
            "paddingBottom": "40px",
        },
    )


def update_profile_standalone_layout(token=None, api_environment=None, lang=None):
    """Create the standalone profile update page layout.

    This page allows users to update their profile via a direct URL with JWT token,
    without needing to log in through the normal flow. If no token is provided,
    a login form is shown first, and on successful login, the profile form is displayed.

    Args:
        token: JWT token from URL query parameter
        api_environment: API environment (production/staging)
        lang: Language code from URL query parameter (e.g., 'en', 'es', 'fr')
    """
    # Get dropdown options from shared helper functions (same as registration form)
    sector_options = get_sector_options()
    purpose_options = get_purpose_options()
    gender_options = get_gender_options()

    return html.Div(
        [
            # Hidden stores for token, language, and user data
            dcc.Store(id="standalone-profile-token", data=token),
            dcc.Store(id="standalone-profile-api-env", data=api_environment or "production"),
            dcc.Store(id="standalone-profile-lang", data=lang),
            dcc.Store(id="standalone-profile-user-data", data=None),
            dcc.Store(id="standalone-profile-countries-store", data=None),
            dbc.Container(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Div(
                                        [
                                            html.Div(
                                                html.Img(
                                                    src=LOGO_URL,
                                                    style={
                                                        "maxWidth": "100%",
                                                        "width": "450px",
                                                        "height": "auto",
                                                    },
                                                ),
                                                style={
                                                    "backgroundColor": "#495057",
                                                    "padding": "20px 30px",
                                                    "textAlign": "center",
                                                    "display": "flex",
                                                    "justifyContent": "center",
                                                    "alignItems": "center",
                                                },
                                                className="mb-4",
                                            ),
                                            html.H4(
                                                _("Update Your Profile"),
                                                className="mb-4 text-center",
                                            ),
                                            # Language selector
                                            html.Div(
                                                create_language_selector(
                                                    id_prefix="standalone-profile-lang"
                                                ),
                                                className="mb-3",
                                            ),
                                            # Login form container (shown when no token is provided)
                                            html.Div(
                                                id="standalone-profile-login-container",
                                                style={"display": "none"},
                                                children=[
                                                    html.P(
                                                        _("Please log in to update your profile."),
                                                        className="text-muted mb-3 text-center",
                                                    ),
                                                    dbc.Form(
                                                        [
                                                            dbc.Row(
                                                                [
                                                                    dbc.Label(_("Email"), width=4),
                                                                    dbc.Col(
                                                                        dbc.Input(
                                                                            id="standalone-profile-login-email",
                                                                            type="email",
                                                                            placeholder=_(
                                                                                "Enter email"
                                                                            ),
                                                                        ),
                                                                        width=8,
                                                                    ),
                                                                ],
                                                                className="mb-3",
                                                            ),
                                                            dbc.Row(
                                                                [
                                                                    dbc.Label(
                                                                        _("Password"), width=4
                                                                    ),
                                                                    dbc.Col(
                                                                        dbc.Input(
                                                                            id="standalone-profile-login-password",
                                                                            type="password",
                                                                            placeholder=_(
                                                                                "Enter password"
                                                                            ),
                                                                        ),
                                                                        width=8,
                                                                    ),
                                                                ],
                                                                className="mb-3",
                                                            ),
                                                            dbc.Button(
                                                                _("Login"),
                                                                id="standalone-profile-login-btn",
                                                                color="primary",
                                                                className="mt-2 w-100",
                                                                n_clicks=0,
                                                            ),
                                                            dbc.Alert(
                                                                id="standalone-profile-login-alert",
                                                                is_open=False,
                                                                dismissable=True,
                                                                className="mt-3",
                                                            ),
                                                        ]
                                                    ),
                                                ],
                                            ),
                                            # Loading indicator for initial data fetch
                                            html.Div(
                                                dbc.Spinner(
                                                    html.Div(_("Loading profile...")),
                                                    color="primary",
                                                    size="sm",
                                                ),
                                                id="standalone-profile-loading",
                                                className="text-center my-3",
                                            ),
                                            # Alert for error messages (shown when token is invalid)
                                            dbc.Alert(
                                                id="standalone-profile-error-alert",
                                                is_open=False,
                                                color="danger",
                                            ),
                                            # Main form container (hidden until user data is loaded)
                                            html.Div(
                                                id="standalone-profile-form-container",
                                                style={"display": "none"},
                                                children=[
                                                    html.P(
                                                        [
                                                            html.Span("* ", style={"color": "red"}),
                                                            _("Required field"),
                                                        ],
                                                        className="text-muted mb-3",
                                                        style={"fontSize": "12px"},
                                                    ),
                                                    # Email (display only)
                                                    dbc.Row(
                                                        [
                                                            dbc.Label(
                                                                html.Strong(_("Email")),
                                                                width=4,
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Input(
                                                                        id="standalone-profile-email",
                                                                        type="email",
                                                                        disabled=True,
                                                                    ),
                                                                    html.Small(
                                                                        _(
                                                                            "Email cannot be changed"
                                                                        ),
                                                                        className="text-muted",
                                                                    ),
                                                                ],
                                                                width=8,
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    # Name
                                                    dbc.Row(
                                                        [
                                                            dbc.Label(
                                                                [
                                                                    html.Strong(_("Full Name")),
                                                                    html.Span(
                                                                        " *",
                                                                        style={"color": "red"},
                                                                    ),
                                                                ],
                                                                width=4,
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Input(
                                                                        id="standalone-profile-name",
                                                                        type="text",
                                                                        placeholder=_(
                                                                            "Enter your full name"
                                                                        ),
                                                                    ),
                                                                ],
                                                                width=8,
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    # Role/Title
                                                    dbc.Row(
                                                        [
                                                            dbc.Label(_("Role/Title"), width=4),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Input(
                                                                        id="standalone-profile-role-title",
                                                                        type="text",
                                                                        placeholder=_(
                                                                            "Your job title (optional)"
                                                                        ),
                                                                    ),
                                                                ],
                                                                width=8,
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    # Organization
                                                    dbc.Row(
                                                        [
                                                            dbc.Label(
                                                                [
                                                                    html.Strong(_("Organization")),
                                                                    html.Span(
                                                                        " *",
                                                                        style={"color": "red"},
                                                                    ),
                                                                ],
                                                                width=4,
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Input(
                                                                        id="standalone-profile-institution",
                                                                        type="text",
                                                                        placeholder=_(
                                                                            "Your organization"
                                                                        ),
                                                                    ),
                                                                ],
                                                                width=8,
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    # Sector
                                                    dbc.Row(
                                                        [
                                                            dbc.Label(
                                                                [
                                                                    html.Strong(_("Sector")),
                                                                    html.Span(
                                                                        " *",
                                                                        style={"color": "red"},
                                                                    ),
                                                                ],
                                                                width=4,
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dcc.Dropdown(
                                                                        id="standalone-profile-sector",
                                                                        options=sector_options,
                                                                        placeholder=_(
                                                                            "Select your sector"
                                                                        ),
                                                                        clearable=True,
                                                                        style={"fontSize": "14px"},
                                                                    ),
                                                                ],
                                                                width=8,
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    # Sector Other (conditional)
                                                    dbc.Row(
                                                        [
                                                            dbc.Label(_("Please specify"), width=4),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Input(
                                                                        id="standalone-profile-sector-other",
                                                                        type="text",
                                                                        placeholder=_(
                                                                            "Please specify your sector"
                                                                        ),
                                                                    ),
                                                                ],
                                                                width=8,
                                                            ),
                                                        ],
                                                        id="standalone-profile-sector-other-row",
                                                        className="mb-3",
                                                        style={"display": "none"},
                                                    ),
                                                    # Purpose of Use
                                                    dbc.Row(
                                                        [
                                                            dbc.Label(
                                                                [
                                                                    html.Strong(
                                                                        _("Purpose of Use")
                                                                    ),
                                                                    html.Span(
                                                                        " *",
                                                                        style={"color": "red"},
                                                                    ),
                                                                ],
                                                                width=4,
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dcc.Dropdown(
                                                                        id="standalone-profile-purpose",
                                                                        options=purpose_options,
                                                                        placeholder=_(
                                                                            "Select your purpose of use"
                                                                        ),
                                                                        clearable=True,
                                                                        style={"fontSize": "14px"},
                                                                    ),
                                                                ],
                                                                width=8,
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    # Purpose Other (conditional)
                                                    dbc.Row(
                                                        [
                                                            dbc.Label(_("Please specify"), width=4),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Input(
                                                                        id="standalone-profile-purpose-other",
                                                                        type="text",
                                                                        placeholder=_(
                                                                            "Please specify your purpose"
                                                                        ),
                                                                    ),
                                                                ],
                                                                width=8,
                                                            ),
                                                        ],
                                                        id="standalone-profile-purpose-other-row",
                                                        className="mb-3",
                                                        style={"display": "none"},
                                                    ),
                                                    # Country
                                                    dbc.Row(
                                                        [
                                                            dbc.Label(
                                                                [
                                                                    html.Strong(_("Country")),
                                                                    html.Span(
                                                                        " *",
                                                                        style={"color": "red"},
                                                                    ),
                                                                ],
                                                                width=4,
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dcc.Dropdown(
                                                                        id="standalone-profile-country",
                                                                        placeholder=_(
                                                                            "Select your country"
                                                                        ),
                                                                        clearable=True,
                                                                        style={"fontSize": "14px"},
                                                                    ),
                                                                ],
                                                                width=8,
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    # Gender Identity
                                                    dbc.Row(
                                                        [
                                                            dbc.Label(
                                                                _("Gender Identity"), width=4
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dcc.Dropdown(
                                                                        id="standalone-profile-gender",
                                                                        options=gender_options,
                                                                        placeholder=_(
                                                                            "Select (optional)"
                                                                        ),
                                                                        clearable=True,
                                                                        style={"fontSize": "14px"},
                                                                    ),
                                                                ],
                                                                width=8,
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    # Gender note
                                                    html.P(
                                                        _(
                                                            "We collect gender identity information to comply with donor reporting requirements and to assess equitable participation in capacity development and tool access. Providing this information is voluntary; your selection will not affect your access to the tool."
                                                        ),
                                                        className="text-muted mb-3",
                                                        style={"fontSize": "12px"},
                                                    ),
                                                    # Gender Description (conditional)
                                                    dbc.Row(
                                                        [
                                                            dbc.Label(
                                                                _("Please describe"), width=4
                                                            ),
                                                            dbc.Col(
                                                                [
                                                                    dbc.Input(
                                                                        id="standalone-profile-gender-description",
                                                                        type="text",
                                                                        placeholder=_(
                                                                            "Please describe"
                                                                        ),
                                                                    ),
                                                                ],
                                                                width=8,
                                                            ),
                                                        ],
                                                        id="standalone-profile-gender-description-row",
                                                        className="mb-3",
                                                        style={"display": "none"},
                                                    ),
                                                    # GEE License Acknowledgment
                                                    html.Div(
                                                        [
                                                            html.P(
                                                                [
                                                                    html.Strong(
                                                                        _(
                                                                            "Do you acknowledge that some Trends.Earth features use Google Earth Engine, and, depending on your use, you may be required to have in place a commercial license to use Google Earth Engine?"
                                                                        )
                                                                    ),
                                                                    html.Span(
                                                                        " *",
                                                                        style={"color": "red"},
                                                                    ),
                                                                ],
                                                                className="mb-2",
                                                            ),
                                                            html.P(
                                                                [
                                                                    _(
                                                                        "Google Earth Engine (GEE) imposes restrictions on commercial use. For more details see the "
                                                                    ),
                                                                    html.A(
                                                                        _(
                                                                            "Google Earth Engine Terms of Use"
                                                                        ),
                                                                        href="https://earthengine.google.com/terms/",
                                                                        target="_blank",
                                                                    ),
                                                                    _(
                                                                        " . Conservation International does not provide or manage commercial GEE licenses. Users are solely responsible for ensuring their use of GEE complies with Google's commercial licensing requirements. Access to this tool does not grant or imply the provision of commercial licensing."
                                                                    ),
                                                                ],
                                                                className="text-muted mb-3",
                                                                style={"fontSize": "12px"},
                                                            ),
                                                            html.Div(
                                                                dbc.Checkbox(
                                                                    id="standalone-profile-gee-acknowledged",
                                                                    label=_("Yes, I acknowledge"),
                                                                    value=False,
                                                                ),
                                                                className="mb-3 d-flex justify-content-center",
                                                            ),
                                                        ],
                                                        style={
                                                            "border": "1px solid #dee2e6",
                                                            "borderRadius": "5px",
                                                            "padding": "15px",
                                                            "marginBottom": "15px",
                                                        },
                                                    ),
                                                    # Success/Error alert for form submission
                                                    dbc.Alert(
                                                        id="standalone-profile-submit-alert",
                                                        is_open=False,
                                                        dismissable=True,
                                                        duration=None,
                                                    ),
                                                    # Submit button
                                                    dbc.Row(
                                                        [
                                                            dbc.Col(
                                                                [
                                                                    dbc.Button(
                                                                        _("Update Profile"),
                                                                        id="standalone-profile-submit-btn",
                                                                        color="primary",
                                                                        className="w-100",
                                                                    ),
                                                                ],
                                                                width=12,
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                ],
                                            ),
                                            html.Hr(),
                                            html.Div(
                                                [
                                                    html.A(
                                                        _("Privacy Policy"),
                                                        href="https://www.conservation.org/policies/privacy",
                                                        target="_blank",
                                                        className="text-muted",
                                                        style={
                                                            "textDecoration": "none",
                                                            "fontSize": "12px",
                                                        },
                                                    ),
                                                    html.Span(
                                                        " | ",
                                                        className="text-muted",
                                                        style={"fontSize": "12px"},
                                                    ),
                                                    html.A(
                                                        _("Terms of Use"),
                                                        href="https://www.conservation.org/policies/terms-of-use",
                                                        target="_blank",
                                                        className="text-muted",
                                                        style={
                                                            "textDecoration": "none",
                                                            "fontSize": "12px",
                                                        },
                                                    ),
                                                ],
                                                className="text-center mt-3",
                                            ),
                                            html.Div(
                                                html.A(
                                                    "trends.earth",
                                                    href="https://trends.earth",
                                                    target="_blank",
                                                    className="text-muted",
                                                    style={
                                                        "textDecoration": "none",
                                                        "fontSize": "12px",
                                                    },
                                                ),
                                                className="text-center mt-1",
                                            ),
                                        ]
                                    ),
                                ],
                                style={"maxWidth": "600px"},
                                width=6,
                                className="mx-auto mt-4",
                            ),
                        ]
                    ),
                ]
            ),
        ],
        style={
            "height": "100vh",
            "overflowY": "auto",
            "paddingBottom": "40px",
        },
    )


def dashboard_layout():
    """Create the main dashboard layout."""
    layout = [
        # Top header with logout button
        dbc.Navbar(
            dbc.Container(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Div(
                                        [
                                            html.Img(
                                                src=LOGO_SQUARE_URL,
                                                height="40px",
                                                className="me-2",
                                            ),
                                            dbc.NavbarBrand(
                                                APP_TITLE,
                                                className="fw-bold me-3",
                                            ),
                                            html.Div(
                                                id="environment-indicator",
                                                style={
                                                    "fontSize": "12px",
                                                    "color": "white",
                                                    "display": "flex",
                                                    "flexDirection": "column",
                                                    "alignItems": "flex-start",
                                                    "gap": "1px",
                                                },
                                            ),
                                        ],
                                        className="d-flex align-items-center",
                                    ),
                                ],
                                width="auto",
                            ),
                            dbc.Col(
                                [
                                    html.Div(
                                        [
                                            html.Span(
                                                id="header-user-info",
                                                className="me-3 text-muted",
                                            ),
                                            # Language selector dropdown
                                            create_language_selector(),
                                            dbc.Button(
                                                [
                                                    html.I(className="fas fa-sign-out-alt me-2"),
                                                    _("Logout"),
                                                ],
                                                id="header-logout-btn",
                                                color="outline-secondary",
                                                size="sm",
                                            ),
                                        ],
                                        className="d-flex align-items-center justify-content-end",
                                    )
                                ],
                                width=True,
                            ),
                        ],
                        className="w-100 align-items-center",
                    )
                ],
                fluid=True,
            ),
            color="dark",
            dark=True,
            style={
                "backgroundColor": "#495057",
                "width": "100vw",
                "marginLeft": "calc(-50vw + 50%)",
                "marginRight": "calc(-50vw + 50%)",
            },
            className="mb-3",
        ),
        dbc.Alert(
            id="alert",
            is_open=False,
            dismissable=True,
            duration=4000,
        ),
        # News banner for announcements
        create_news_banner(),
        # Collapsible main panel containing the tabs
        dbc.Collapse(
            html.Div(
                [
                    # Navigation tabs - responsive design with Bootstrap classes
                    html.Ul(
                        [
                            html.Li(
                                [
                                    html.Button(
                                        _("Executions"),
                                        id="executions-tab-btn",
                                        className="nav-link active",
                                    )
                                ],
                                className="nav-item",
                            ),
                            html.Li(
                                [
                                    html.Button(
                                        _("Users"),
                                        id="users-tab-btn",
                                        className="nav-link",
                                    )
                                ],
                                className="nav-item",
                                id="users-tab-li",
                                style={
                                    "display": "none"
                                },  # Hidden by default, shown only for admin
                            ),
                            html.Li(
                                [
                                    html.Button(
                                        _("Scripts"),
                                        id="scripts-tab-btn",
                                        className="nav-link",
                                    )
                                ],
                                className="nav-item",
                                id="scripts-tab-li",
                                style={
                                    "display": "none"
                                },  # Hidden by default, shown only for admin
                            ),
                            html.Li(
                                [
                                    html.Button(
                                        _("Admin"),
                                        id="admin-tab-btn",
                                        className="nav-link",
                                    )
                                ],
                                className="nav-item",
                                id="admin-tab-li",
                                style={
                                    "display": "none"
                                },  # Hidden by default, shown only for admin
                            ),
                            html.Li(
                                [
                                    html.Button(
                                        _("Status"),
                                        id="status-tab-btn",
                                        className="nav-link",
                                    )
                                ],
                                className="nav-item",
                                id="status-tab-li",
                                style={
                                    "display": "none"
                                },  # Hidden by default, shown only for admin
                            ),
                            html.Li(
                                [
                                    html.Button(
                                        _("Profile"),
                                        id="profile-tab-btn",
                                        className="nav-link",
                                    )
                                ],
                                className="nav-item",
                            ),
                        ],
                        id="tabs-nav",
                        className="nav nav-tabs",
                        style={"flexWrap": "wrap"},
                    ),
                    # Tab content will be inserted here by callbacks
                    html.Div(id="tab-content-dynamic"),
                ],
                **{"data-testid": "dashboard-content"},
            ),
            id="main-panel",
            is_open=True,
        ),
        # Hidden stores are defined globally in the main layout; avoid duplicates here
        # Proactive token refresh interval (every 5 minutes)
        dcc.Interval(
            id="token-refresh-interval",
            interval=5 * 60 * 1000,  # 5 minutes in milliseconds
            n_intervals=0,
        ),
    ]
    logger.debug("Dashboard layout created with %d components", len(layout))
    for i, component in enumerate(layout):
        logger.debug(
            "  %d: %s - %s", i, type(component).__name__, getattr(component, "id", "no id")
        )
    return layout
