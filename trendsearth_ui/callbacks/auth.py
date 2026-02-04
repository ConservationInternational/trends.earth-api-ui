"""Authentication and navigation callbacks."""

from datetime import datetime, timedelta
import hmac
import json
import os
import re
from urllib.parse import parse_qs

from dash import Input, Output, State, callback_context, html, no_update
from flask import request
import requests

from ..components import dashboard_layout, login_layout, registration_layout, reset_password_layout
from ..config import get_api_base, get_auth_url
from ..utils import (
    create_auth_cookie_data,
    get_user_info,
    logout_user,
    refresh_access_token,
    should_refresh_token,
)
from ..utils.http_client import apply_default_headers
from ..utils.logging_config import get_logger, log_exception

# Get the configured logger
logger = get_logger()

_SECURE_COOKIE_ENVIRONMENTS = {"production", "staging"}
_MOCK_AUTH_FLAG_VALUES = {"1", "true", "yes"}


def _is_mock_auth_enabled(search_query: str | None) -> bool:
    """Return True when mock authentication bypass is allowed."""

    if not search_query:
        return False

    if os.environ.get("ENABLE_MOCK_AUTH", "").lower() not in _MOCK_AUTH_FLAG_VALUES:
        return False

    env = os.environ.get("DEPLOYMENT_ENVIRONMENT", "").lower()
    if env in _SECURE_COOKIE_ENVIRONMENTS:
        return False

    params = parse_qs(search_query[1:] if search_query.startswith("?") else search_query)

    if params.get("mock_auth", ["0"])[0].lower() not in _MOCK_AUTH_FLAG_VALUES:
        return False

    secret = os.environ.get("MOCK_AUTH_TOKEN", "")
    if not secret:
        return False

    provided_token = params.get("mock_auth_token", [""])[0]
    if not provided_token:
        return False

    try:
        return hmac.compare_digest(provided_token, secret)
    except Exception:
        return False


def _should_use_secure_cookie() -> bool:
    """Determine if cookies must be marked secure."""
    env = os.environ.get("DEPLOYMENT_ENVIRONMENT", "").lower()
    if env in _SECURE_COOKIE_ENVIRONMENTS:
        return True

    forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
    if "https" in forwarded_proto.lower():
        return True

    return request.is_secure


def _set_auth_cookie(response, value: str, expires):
    """Set auth cookie with consistent security flags."""
    if not response:
        return

    response.set_cookie(
        "auth_token",
        value,
        expires=expires,
        httponly=True,
        secure=_should_use_secure_cookie(),
        samesite="Lax",
    )


def register_callbacks(app):
    """Register authentication and navigation callbacks."""

    @app.callback(
        [
            Output("page-content", "children"),
            Output("token-store", "clear_data"),
            Output("token-store", "data"),
            Output("role-store", "data"),
            Output("user-store", "data"),
            Output("api-environment-store", "data"),
        ],
        [
            Input("url", "pathname"),
            Input("url", "search"),
            Input("token-store", "data"),
        ],
        [
            State("api-environment-store", "data"),
        ],
    )
    def display_page(_pathname, search, token, current_api_environment):
        """
        Display login or dashboard. This is the central callback for auth.
        It checks for a token in the store, then falls back to checking the
        auth cookie, ensuring a single, reliable path for session initialization.
        """
        # Check if this is a password reset page request
        if _pathname and _pathname.startswith("/reset-password"):
            # Extract token from query parameters
            reset_token = None
            api_env = current_api_environment or "production"
            if search:
                params = parse_qs(search[1:] if search.startswith("?") else search)
                reset_token = params.get("token", [None])[0]
                # Also check for environment parameter
                env_param = params.get("env", [None])[0]
                if env_param:
                    api_env = env_param

            return (
                reset_password_layout(token=reset_token, api_environment=api_env),
                True,  # Clear auth stores for this public page
                None,
                None,
                None,
                api_env,
            )

        if _is_mock_auth_enabled(search):
            logger.debug("Auth bypass enabled via secure mock auth configuration")
            user_data = {
                "id": "test_user_123",
                "name": "Test User",
                "email": "test@example.com",
                "role": "ADMIN",
            }
            logger.debug("Returning mock authenticated dashboard layout")
            return (
                dashboard_layout(),
                False,
                "mock_token_12345",
                "ADMIN",
                user_data,
                (current_api_environment or "production"),
            )

        # If a token is already in the dcc.Store, user is authenticated
        if token:
            return (
                dashboard_layout(),
                False,
                no_update,
                no_update,
                no_update,
                current_api_environment or "production",
            )

        # If no token in store, try to initialize session from the cookie
        try:
            import json as _json

            from flask import request as _request

            auth_cookie = _request.cookies.get("auth_token")
            if auth_cookie:
                cookie_data = _json.loads(auth_cookie)
                if isinstance(cookie_data, dict):
                    access_token = cookie_data.get("access_token")
                    user_data = cookie_data.get("user_data") or {}
                    role = user_data.get("role") if isinstance(user_data, dict) else None
                    api_env = cookie_data.get("api_environment") or (
                        current_api_environment or "production"
                    )

                    # If cookie has a valid token, hydrate stores and show dashboard
                    if access_token:
                        return (
                            dashboard_layout(),
                            False,
                            access_token,
                            role,
                            user_data,
                            api_env,
                        )
        except Exception as e:
            log_exception(logger, f"Cookie processing failed in display_page: {e}")

        # If all checks fail, show the login page
        return (
            login_layout(),
            True,  # Clear stores
            None,
            None,
            None,
            (current_api_environment or "production"),
        )

    @app.callback(
        [
            Output("token-store", "data", allow_duplicate=True),
            Output("role-store", "data", allow_duplicate=True),
            Output("user-store", "data", allow_duplicate=True),
            Output("api-environment-store", "data", allow_duplicate=True),
            Output("login-alert", "children"),
            Output("login-alert", "color"),
            Output("login-alert", "is_open"),
        ],
        [Input("login-btn", "n_clicks")],
        [
            State("login-email", "value"),
            State("login-password", "value"),
            State("remember-me-checkbox", "value"),
            State("api-environment-dropdown", "value"),
            State("url", "search"),
        ],
        prevent_initial_call=True,
    )
    def login_api(_n, email, password, remember_me, api_environment, search):
        """Handle login authentication."""
        logger.debug(
            "Login attempt - Email: %s, Button clicks: %s, Remember: %s, Environment: %s",
            email,
            _n,
            remember_me,
            api_environment,
        )

        if _is_mock_auth_enabled(search):
            logger.debug(
                "Secure mock auth mode detected in login_api - skipping credential exchange"
            )
            return (
                None,
                None,
                None,
                None,
                "",
                "success",
                False,
            )

        if not email or not password:
            logger.debug("Missing email or password")
            return (
                None,
                None,
                None,
                None,
                "Please enter both email and password.",
                "warning",
                True,
            )

        # Get the AUTH_URL for the selected environment
        auth_url = get_auth_url(api_environment)
        api_base = get_api_base(api_environment)

        logger.debug("Attempting to connect to: %s", auth_url)
        try:
            auth_data = {"email": email, "password": password}
            resp = requests.post(
                auth_url,
                headers=apply_default_headers(),
                json=auth_data,
                timeout=5,
            )

            if resp.status_code == 200:
                logger.debug("Login API response successful")
                try:
                    data = resp.json()
                    logger.debug(
                        "Login: Auth response JSON keys: %s",
                        list(data.keys()) if isinstance(data, dict) else "Not a dict",
                    )
                except ValueError as e:
                    logger.warning("Login: Failed to parse auth response JSON: %s", e)
                    logger.debug("Login: Raw auth response: %s...", resp.text[:500])
                    return (
                        None,
                        None,
                        None,
                        None,
                        "Login failed: Invalid response format.",
                        "danger",
                        True,
                    )

                access_token = data.get("access_token")
                refresh_token = data.get("refresh_token")

                logger.debug("Login: Received access_token: %s", "Yes" if access_token else "No")
                logger.debug("Login: Received refresh_token: %s", "Yes" if refresh_token else "No")
                logger.debug(
                    "Login: Access token length: %s", len(access_token) if access_token else 0
                )

                # Use the API base for the selected environment to get user info
                logger.debug("Login: About to call get_user_info with api_base: %s", api_base)
                user_data = get_user_info(access_token, api_base)

                logger.debug(
                    "Login: get_user_info returned: %s",
                    "Valid data" if user_data else "None/Empty",
                )

                if user_data and access_token and refresh_token:
                    role = user_data.get("role", "USER")
                    logger.debug("Login successful for user: %s", user_data.get("email", "unknown"))

                    # Set HTTP cookie if remember me is checked
                    if remember_me:
                        cookie_data = create_auth_cookie_data(
                            access_token, refresh_token, email, user_data, api_environment
                        )
                        cookie_value = json.dumps(cookie_data)

                        # Access Flask response through callback context
                        ctx = callback_context
                        if hasattr(ctx, "response") and ctx.response:
                            expiration = datetime.now() + timedelta(days=30)
                            _set_auth_cookie(ctx.response, cookie_value, expiration)
                            logger.debug("Set HTTP authentication cookie with 30-day expiration")

                    return (
                        access_token,
                        role,
                        user_data,
                        api_environment,
                        "Login successful!",
                        "success",
                        True,
                    )
                else:
                    logger.warning("Failed to retrieve user information")
                    logger.debug("Login failure analysis:")
                    logger.debug("   - user_data: %s", "Present" if user_data else "Missing/None")
                    logger.debug(
                        "   - access_token: %s", "Present" if access_token else "Missing/None"
                    )
                    logger.debug(
                        "   - refresh_token: %s", "Present" if refresh_token else "Missing/None"
                    )
                    if user_data:
                        logger.debug("   - user_data type: %s", type(user_data))
                        logger.debug("   - user_data content: %s", user_data)
                    return (
                        None,
                        None,
                        None,
                        None,
                        "Failed to retrieve user information.",
                        "danger",
                        True,
                    )
            else:
                logger.warning("Login failed with status code: %s", resp.status_code)
                return (None, None, None, None, "Invalid credentials.", "danger", True)

        except requests.exceptions.Timeout:
            logger.warning("Login request timed out")
            return (
                None,
                None,
                None,
                None,
                "Login failed: Connection timeout. Please try again later.",
                "danger",
                True,
            )
        except requests.exceptions.ConnectionError:
            logger.warning("Connection error during login attempt")
            return (
                None,
                None,
                None,
                None,
                "Login failed: Cannot connect to authentication server. Please check the server status.",
                "danger",
                True,
            )
        except Exception as e:
            log_exception(logger, f"Unexpected error during login: {str(e)}")
            return (None, None, None, None, f"Login failed: {str(e)}", "danger", True)

    @app.callback(
        [
            Output("token-store", "clear_data", allow_duplicate=True),
            Output("role-store", "clear_data", allow_duplicate=True),
            Output("user-store", "clear_data", allow_duplicate=True),
            Output("page-content", "children", allow_duplicate=True),
            Output("tab-content", "children", allow_duplicate=True),
        ],
        [
            Input("header-logout-btn", "n_clicks"),
        ],
        [
            State("token-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def logout_user_callback(header_logout_clicks, current_token):
        """Handle user logout and clear authentication cookie."""
        if header_logout_clicks:
            logger.debug("User logging out - clearing authentication data")

            # Extract refresh token and API environment from cookie for proper logout
            refresh_token_to_revoke = None
            api_environment = None
            try:
                auth_cookie = request.cookies.get("auth_token")
                if auth_cookie:
                    cookie_data = json.loads(auth_cookie)
                    if cookie_data and isinstance(cookie_data, dict):
                        refresh_token_to_revoke = cookie_data.get("refresh_token")
                        api_environment = cookie_data.get("api_environment", "production")
            except Exception as e:
                logger.debug("Error reading refresh token from cookie: %s", e)

            # Call logout API to revoke refresh token
            if current_token and refresh_token_to_revoke:
                logout_success = logout_user(
                    current_token, refresh_token_to_revoke, api_environment or "production"
                )
                if logout_success:
                    logger.debug("Successfully logged out from API")
                else:
                    logger.warning("API logout failed, but clearing local session anyway")

            # Clear HTTP cookie
            ctx = callback_context
            if hasattr(ctx, "response") and ctx.response:
                _set_auth_cookie(ctx.response, "", 0)
                logger.debug("Cleared HTTP authentication cookie")

            return (True, True, True, login_layout(), [])
        return (no_update, no_update, no_update, no_update, no_update)

    @app.callback(
        Output("login-email", "value"),
        [Input("page-content", "children")],
        prevent_initial_call=True,
    )
    def populate_login_email(page_content):
        """Pre-populate email field from expired cookie when login page is shown."""
        # Check if this is the login page being displayed
        if page_content and isinstance(page_content, dict):
            # Check if we have cookie data with an email to pre-populate
            cookie_data = None
            try:
                auth_cookie = request.cookies.get("auth_token")
                if auth_cookie:
                    cookie_data = json.loads(auth_cookie)
            except Exception as e:
                logger.debug("Error reading auth cookie for email population: %s", e)
                cookie_data = None

            if cookie_data and isinstance(cookie_data, dict):
                email_value = cookie_data.get("email", "")
                if email_value:
                    return email_value

        return ""

    @app.callback(
        Output("header-user-info", "children"),
        [
            Input("user-store", "data"),
            Input("role-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def update_header_user_info(user_data, role):
        """Update the user info display in the header."""
        if not user_data:
            return ""

        user_name = user_data.get("name", "")
        user_email = user_data.get("email", "")

        # Display name if available, otherwise email
        display_name = user_name if user_name else user_email

        # Add role badge with consistent styling
        role_text = "Super Admin" if role == "SUPERADMIN" else (role.title() if role else "User")

        return html.Div(
            [
                html.Span(f"Welcome, {display_name}", className="me-2 fw-bold text-white"),
                html.Span(
                    role_text,
                    className="badge",
                    style={"fontSize": "12px", "backgroundColor": "#6c757d", "color": "white"},
                ),
            ],
            className="d-flex align-items-center",
        )

    @app.callback(
        Output("environment-indicator", "children"),
        [Input("api-environment-store", "data"), Input("role-store", "data")],
        prevent_initial_call=True,
    )
    def update_environment_indicator(api_environment, role):
        """Update the environment indicator in the header to show both API and UI environments.

        Only visible to ADMIN and SUPERADMIN users.
        """
        # Hide environment indicator for non-admin users
        if role not in ["ADMIN", "SUPERADMIN"]:
            return ""

        if not api_environment:
            return ""

        # Get UI environment info
        from trendsearth_ui.utils.deployment_info import get_deployment_info

        ui_deployment = get_deployment_info()
        ui_environment = ui_deployment.get("environment", "unknown")

        # Format environment names
        api_env_display = api_environment.title() if api_environment else "Unknown"
        ui_env_display = ui_environment.title() if ui_environment else "Unknown"

        # Return badges showing both API and UI environments
        return [
            html.Span(
                f"API: {api_env_display}",
                className="badge",
                style={
                    "backgroundColor": "#6c757d" if api_environment != "production" else "#28a745",
                    "color": "white",
                    "fontSize": "11px",
                    "padding": "2px 6px",
                    "marginBottom": "1px",
                },
            ),
            html.Span(
                f"UI: {ui_env_display}",
                className="badge",
                style={
                    "backgroundColor": "#6c757d" if ui_environment != "production" else "#28a745",
                    "color": "white",
                    "fontSize": "11px",
                    "padding": "2px 6px",
                },
            ),
        ]

    @app.callback(
        Output("forgot-password-modal", "is_open"),
        [
            Input("forgot-password-link", "n_clicks"),
            Input("cancel-forgot-password", "n_clicks"),
            Input("forgot-password-ok-btn", "n_clicks"),
        ],
        [State("forgot-password-modal", "is_open")],
        prevent_initial_call=True,
    )
    def toggle_forgot_password_modal(_forgot_link_clicks, _cancel_clicks, _ok_clicks, is_open):
        """Toggle the forgot password modal."""
        ctx = callback_context
        if not ctx.triggered:
            return is_open

        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

        if trigger_id == "forgot-password-link":
            return True
        elif trigger_id in ["cancel-forgot-password", "forgot-password-ok-btn"]:
            return False

        return is_open

    @app.callback(
        [
            Output("forgot-password-alert", "children"),
            Output("forgot-password-alert", "color"),
            Output("forgot-password-alert", "is_open"),
            Output("forgot-password-email", "value"),
            Output("forgot-password-form", "style"),
            Output("forgot-password-initial-buttons", "style"),
            Output("forgot-password-success-buttons", "style"),
        ],
        [Input("send-reset-btn", "n_clicks")],
        [
            State("forgot-password-email", "value"),
            State("api-environment-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def send_password_reset(n_clicks, email, api_environment):
        """Send password reset instructions to user's email."""
        if not n_clicks:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update

        if not email:
            return (
                "Please enter your email address.",
                "warning",
                True,
                no_update,
                {"display": "block"},  # Keep form visible
                {"display": "block"},  # Keep initial buttons visible
                {"display": "none"},  # Keep success buttons hidden
            )

        # Validate email format
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            return (
                "Please enter a valid email address.",
                "warning",
                True,
                no_update,
                {"display": "block"},  # Keep form visible
                {"display": "block"},  # Keep initial buttons visible
                {"display": "none"},  # Keep success buttons hidden
            )

        try:
            logger.debug(
                "Attempting password recovery for email: %s (Environment: %s)",
                email,
                api_environment,
            )

            # Get the API base for the selected environment
            api_base = get_api_base(api_environment)

            # Use the email as the user_id parameter in the endpoint
            # Use legacy=false to send a secure reset link instead of emailing
            # the password directly
            resp = requests.post(
                f"{api_base}/user/{email}/recover-password?legacy=false",
                timeout=10,
            )

            if resp.status_code == 200:
                logger.debug("Password recovery email sent to: %s", email)
                return (
                    f"If an account exists with {email}, password recovery instructions have been sent. Please check your email.",
                    "success",
                    True,
                    "",  # Clear the email field
                    {"display": "none"},  # Hide form
                    {"display": "none"},  # Hide initial buttons
                    {"display": "block"},  # Show success buttons (OK button)
                )
            elif resp.status_code == 404:
                logger.debug("User not found with email: %s", email)
                # Return the same message as success to prevent email enumeration
                return (
                    f"If an account exists with {email}, password recovery instructions have been sent. Please check your email.",
                    "success",
                    True,
                    "",  # Clear the email field
                    {"display": "none"},  # Hide form
                    {"display": "none"},  # Hide initial buttons
                    {"display": "block"},  # Show success buttons (OK button)
                )
            else:
                logger.warning("Password recovery failed with status: %s", resp.status_code)
                error_msg = "Failed to send password recovery email."
                try:
                    error_data = resp.json()
                    error_msg = error_data.get("msg", error_msg)
                    logger.debug("API error response: %s", error_data)
                except Exception:
                    pass
                return (
                    f"{error_msg} Please try again later.",
                    "danger",
                    True,
                    no_update,
                    {"display": "block"},  # Keep form visible
                    {"display": "block"},  # Keep initial buttons visible
                    {"display": "none"},  # Keep success buttons hidden
                )

        except requests.exceptions.Timeout:
            logger.warning("Password recovery request timed out")
            return (
                "Request timed out. Please try again later.",
                "danger",
                True,
                no_update,
                {"display": "block"},  # Keep form visible
                {"display": "block"},  # Keep initial buttons visible
                {"display": "none"},  # Keep success buttons hidden
            )
        except requests.exceptions.ConnectionError:
            logger.warning("Connection error during password recovery")
            return (
                "Cannot connect to the server. Please check your internet connection and try again.",
                "danger",
                True,
                no_update,
                {"display": "block"},  # Keep form visible
                {"display": "block"},  # Keep initial buttons visible
                {"display": "none"},  # Keep success buttons hidden
            )
        except Exception as e:
            logger.exception("Error during password recovery: %s", e)
            return (
                f"An error occurred: {str(e)}. Please try again later.",
                "danger",
                True,
                no_update,
                {"display": "block"},  # Keep form visible
                {"display": "block"},  # Keep initial buttons visible
                {"display": "none"},  # Keep success buttons hidden
            )

    @app.callback(
        [
            Output("forgot-password-form", "style", allow_duplicate=True),
            Output("forgot-password-initial-buttons", "style", allow_duplicate=True),
            Output("forgot-password-success-buttons", "style", allow_duplicate=True),
            Output("forgot-password-alert", "is_open", allow_duplicate=True),
            Output("forgot-password-email", "value", allow_duplicate=True),
        ],
        [Input("forgot-password-modal", "is_open")],
        prevent_initial_call=True,
    )
    def reset_modal_state(is_open):
        """Reset modal state when it opens."""
        if is_open:
            # Reset to initial state when modal opens
            return (
                {"display": "block"},  # Show form
                {"display": "block"},  # Show initial buttons
                {"display": "none"},  # Hide success buttons
                False,  # Hide alert
                "",  # Clear email field
            )
        return no_update, no_update, no_update, no_update, no_update

    @app.callback(
        Output("forgot-password-modal", "is_open", allow_duplicate=True),
        [Input("forgot-password-ok-btn", "n_clicks")],
        prevent_initial_call=True,
    )
    def close_modal_on_ok(n_clicks):
        """Close the modal when OK button is clicked."""
        if n_clicks:
            return False
        return no_update

    @app.callback(
        [
            Output("token-store", "data", allow_duplicate=True),
        ],
        [
            Input("token-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def auto_refresh_token(current_token):
        """Automatically refresh access token when needed."""
        if not current_token:
            return no_update

        # Check if the JWT access token needs to be refreshed
        needs_refresh = should_refresh_token(current_token, buffer_minutes=5)

        if not needs_refresh:
            return no_update

        # Check if we have a refresh token and API environment in cookie
        refresh_token = None
        api_environment = None
        try:
            auth_cookie = request.cookies.get("auth_token")
            if auth_cookie:
                cookie_data = json.loads(auth_cookie)
                if cookie_data and isinstance(cookie_data, dict):
                    refresh_token = cookie_data.get("refresh_token")
                    api_environment = cookie_data.get("api_environment", "production")
        except Exception as e:
            logger.debug("Error reading refresh token from cookie: %s", e)
            return no_update

        if not refresh_token:
            return no_update

        # Try to refresh the token using the stored API environment
        new_access_token, expires_in = refresh_access_token(
            refresh_token, api_environment or "production"
        )
        if new_access_token and new_access_token != current_token:
            logger.debug("Auto-refreshed access token")

            # Update cookie with new access token
            try:
                auth_cookie = request.cookies.get("auth_token")
                if auth_cookie:
                    cookie_data = json.loads(auth_cookie)
                    if cookie_data:
                        email = cookie_data.get("email") or ""
                        user_data = cookie_data.get("user_data") or {}

                        ctx = callback_context
                        if hasattr(ctx, "response") and ctx.response:
                            new_cookie_data = create_auth_cookie_data(
                                new_access_token,
                                refresh_token,
                                email,
                                user_data,
                                api_environment or "production",
                            )
                            cookie_value = json.dumps(new_cookie_data)
                            expiration = datetime.now() + timedelta(days=30)
                            _set_auth_cookie(ctx.response, cookie_value, expiration)
            except Exception as e:
                logger.debug("Error updating cookie during auto-refresh: %s", e)

            return new_access_token

        return no_update

    @app.callback(
        [
            Output("token-store", "data", allow_duplicate=True),
            Output("user-store", "data", allow_duplicate=True),
        ],
        [
            Input("token-refresh-interval", "n_intervals"),
        ],
        [
            State("token-store", "data"),
            State("user-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def proactive_token_refresh(_n_intervals, current_token, user_data):
        """Proactively refresh access token every 5 minutes to keep users logged in."""
        # Skip token refresh in test mode (when using mock tokens)
        if current_token and current_token.startswith("mock_"):
            return no_update, no_update

        # Only run if we have a token and user data (user is logged in)
        if not current_token or not user_data:
            return no_update, no_update

        # Check if the JWT access token needs to be refreshed
        needs_refresh = should_refresh_token(current_token, buffer_minutes=5)

        if not needs_refresh:
            return no_update, no_update

        # Check if we have a refresh token and API environment in cookie
        refresh_token = None
        api_environment = None
        cookie_data = None
        try:
            auth_cookie = request.cookies.get("auth_token")
            if auth_cookie:
                cookie_data = json.loads(auth_cookie)
                if cookie_data and isinstance(cookie_data, dict):
                    refresh_token = cookie_data.get("refresh_token")
                    api_environment = cookie_data.get("api_environment", "production")

                    # Check if cookie itself has expired (30-day limit)
                    expires_at = cookie_data.get("expires_at")
                    if expires_at:
                        try:
                            cookie_expiration = datetime.fromisoformat(expires_at)
                            if datetime.now() >= cookie_expiration:
                                logger.debug("Cookie has expired, clearing session")
                                return None, None
                        except Exception as e:
                            logger.debug("Error parsing cookie expiration: %s", e)
        except Exception as e:
            logger.debug("Error reading refresh token from cookie during proactive refresh: %s", e)
            return no_update, no_update

        if not refresh_token:
            return no_update, no_update

        # Try to refresh the token proactively
        new_access_token, expires_in = refresh_access_token(
            refresh_token, api_environment or "production"
        )
        if new_access_token:
            if new_access_token != current_token:
                logger.debug("Proactively refreshed access token")

            # Always update cookie to extend session even if token didn't change
            try:
                if cookie_data:
                    email = cookie_data.get("email") or ""
                    stored_user_data = cookie_data.get("user_data") or {}

                    ctx = callback_context
                    if hasattr(ctx, "response") and ctx.response:
                        new_cookie_data = create_auth_cookie_data(
                            new_access_token,
                            refresh_token,
                            email,
                            stored_user_data,
                            api_environment or "production",
                        )
                        cookie_value = json.dumps(new_cookie_data)
                        expiration = datetime.now() + timedelta(days=30)
                        _set_auth_cookie(ctx.response, cookie_value, expiration)
            except Exception as e:
                logger.debug("Error updating cookie during proactive refresh: %s", e)

            return new_access_token, user_data
        else:
            # Refresh failed, user needs to log in again
            logger.warning("Proactive token refresh failed, clearing session")
            return None, None

        return no_update, no_update

    # Real-time password validation callback
    @app.callback(
        [
            Output("req-length", "className"),
            Output("req-uppercase", "className"),
            Output("req-lowercase", "className"),
            Output("req-number", "className"),
            Output("req-special", "className"),
        ],
        [Input("reset-new-password", "value")],
        prevent_initial_call=True,
    )
    def validate_password_requirements(password):
        """Validate password requirements in real-time and update UI indicators."""
        import re

        if not password:
            # Return all as muted when no password entered
            return ["text-muted"] * 5

        special_chars = r"!@#$%^&*()\-_=+\[\]{}|;:,.<>?/"

        # Check each requirement
        has_length = len(password) >= 12
        has_upper = bool(re.search(r"[A-Z]", password))
        has_lower = bool(re.search(r"[a-z]", password))
        has_number = bool(re.search(r"\d", password))
        has_special = bool(re.search(f"[{special_chars}]", password))

        # Return success (green) or danger (red) class for each requirement
        return [
            "text-success" if has_length else "text-danger",
            "text-success" if has_upper else "text-danger",
            "text-success" if has_lower else "text-danger",
            "text-success" if has_number else "text-danger",
            "text-success" if has_special else "text-danger",
        ]

    # Password reset with token callback
    @app.callback(
        [
            Output("reset-password-alert", "children"),
            Output("reset-password-alert", "color"),
            Output("reset-password-alert", "is_open"),
            Output("reset-new-password", "value"),
            Output("reset-confirm-password", "value"),
        ],
        [Input("reset-password-submit-btn", "n_clicks")],
        [
            State("reset-new-password", "value"),
            State("reset-confirm-password", "value"),
            State("reset-password-token", "data"),
            State("reset-password-api-env", "data"),
        ],
        prevent_initial_call=True,
    )
    def submit_password_reset(n_clicks, new_password, confirm_password, reset_token, api_env):
        """Handle password reset form submission."""
        if not n_clicks:
            return no_update, no_update, no_update, no_update, no_update

        # Validate inputs
        if not reset_token:
            return (
                "Invalid or missing reset token. Please request a new password reset.",
                "danger",
                True,
                no_update,
                no_update,
            )

        if not new_password or not confirm_password:
            return (
                "Please enter and confirm your new password.",
                "warning",
                True,
                no_update,
                no_update,
            )

        if new_password != confirm_password:
            return (
                "Passwords do not match. Please try again.",
                "danger",
                True,
                no_update,
                no_update,
            )

        if len(new_password) < 12:
            return (
                "Password must be at least 12 characters long.",
                "danger",
                True,
                no_update,
                no_update,
            )

        # Call the API to reset the password
        try:
            api_base = get_api_base(api_env or "production")
            logger.debug("Submitting password reset to %s", api_base)

            resp = requests.post(
                f"{api_base}/user/reset-password",
                json={"token": reset_token, "password": new_password},
                timeout=10,
            )

            if resp.status_code == 200:
                logger.debug("Password reset successful")
                return (
                    "Password reset successful! You can now log in with your new password.",
                    "success",
                    True,
                    "",  # Clear password field
                    "",  # Clear confirm field
                )
            elif resp.status_code == 404:
                logger.debug("Invalid or expired reset token")
                return (
                    "This reset link is invalid or has expired. Please request a new password reset.",
                    "danger",
                    True,
                    no_update,
                    no_update,
                )
            elif resp.status_code == 422:
                logger.debug("Password validation failed")
                error_msg = "Password does not meet requirements."
                try:
                    error_data = resp.json()
                    error_msg = error_data["detail"]
                except Exception:
                    pass
                return (
                    error_msg,
                    "danger",
                    True,
                    no_update,
                    no_update,
                )
            else:
                logger.warning("Password reset failed with status: %s", resp.status_code)
                error_msg = "Failed to reset password."
                try:
                    error_data = resp.json()
                    error_msg = error_data["detail"]
                except Exception:
                    pass
                return (
                    f"{error_msg} Please try again.",
                    "danger",
                    True,
                    no_update,
                    no_update,
                )

        except requests.exceptions.Timeout:
            logger.warning("Password reset request timed out")
            return (
                "Request timed out. Please try again.",
                "danger",
                True,
                no_update,
                no_update,
            )
        except requests.exceptions.ConnectionError:
            logger.warning("Connection error during password reset")
            return (
                "Cannot connect to the server. Please check your connection.",
                "danger",
                True,
                no_update,
                no_update,
            )
        except Exception as e:
            logger.exception("Error during password reset: %s", e)
            return (
                f"An error occurred: {str(e)}",
                "danger",
                True,
                no_update,
                no_update,
            )

    # Registration page navigation callbacks
    @app.callback(
        Output("page-content", "children", allow_duplicate=True),
        [Input("register-btn", "n_clicks")],
        [State("api-environment-dropdown", "value")],
        prevent_initial_call=True,
    )
    def navigate_to_register(n_clicks, api_environment):
        """Navigate to registration page when Register button is clicked."""
        if n_clicks:
            return registration_layout(api_environment or "production")
        return no_update

    @app.callback(
        Output("page-content", "children", allow_duplicate=True),
        [Input("register-back-btn", "n_clicks")],
        prevent_initial_call=True,
    )
    def navigate_back_to_login(n_clicks):
        """Navigate back to login page from registration."""
        if n_clicks:
            return login_layout()
        return no_update

    @app.callback(
        Output("register-country", "options"),
        [Input("register-api-environment", "value")],
        prevent_initial_call=False,
    )
    def fetch_countries_for_registration(api_environment):
        """Fetch countries from the boundary API for the registration dropdown."""
        try:
            api_base = get_api_base(api_environment or "production")
            logger.debug("Fetching countries from boundary API: %s", api_base)

            # Fetch boundaries at level 0 (countries)
            # Note: This endpoint requires authentication, but for registration
            # we'll attempt without auth first. If it fails, we use a fallback list.
            resp = requests.get(
                f"{api_base}/data/boundaries",
                params={"level": "0", "per_page": "300"},
                headers=apply_default_headers(),
                timeout=10,
            )

            if resp.status_code == 200:
                data = resp.json()
                countries = data.get("data", [])

                # Build dropdown options from boundary data
                options = []
                for country in countries:
                    iso_code = country.get("boundaryISO", "")
                    name = country.get("boundaryName", "")
                    if iso_code and name:
                        options.append({"label": name, "value": iso_code})

                # Sort by label (country name)
                options.sort(key=lambda x: x["label"])
                logger.debug("Loaded %d countries from boundary API", len(options))
                return options
            else:
                logger.warning(
                    "Failed to fetch countries from boundary API (status %d), using fallback",
                    resp.status_code,
                )
                return _get_fallback_country_options()

        except requests.exceptions.Timeout:
            logger.warning("Boundary API request timed out, using fallback country list")
            return _get_fallback_country_options()
        except requests.exceptions.ConnectionError:
            logger.warning("Cannot connect to boundary API, using fallback country list")
            return _get_fallback_country_options()
        except Exception as e:
            logger.exception("Error fetching countries: %s", e)
            return _get_fallback_country_options()

    # Registration form submission callback
    @app.callback(
        [
            Output("register-alert", "children"),
            Output("register-alert", "color"),
            Output("register-alert", "is_open"),
        ],
        [Input("register-submit-btn", "n_clicks")],
        [
            State("register-email", "value"),
            State("register-name", "value"),
            State("register-country", "value"),
            State("register-institution", "value"),
            State("register-api-environment", "value"),
        ],
        prevent_initial_call=True,
    )
    def submit_registration(n_clicks, email, name, country, institution, api_environment):
        """Handle user registration form submission.

        This uses the secure registration flow (legacy=false) where:
        1. User provides email and profile info only
        2. API creates account with temporary password
        3. User receives email with link to verify and set password
        """
        if not n_clicks:
            return no_update, no_update, no_update

        # Validate required fields
        if not email:
            return "Please enter your email address.", "warning", True

        if not name:
            return "Please enter your name.", "warning", True

        # Validate email format
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            return "Please enter a valid email address.", "warning", True

        try:
            api_base = get_api_base(api_environment or "production")
            logger.debug("Submitting registration to %s", api_base)

            # Build registration payload (no password - user sets it via email link)
            payload = {
                "email": email,
                "name": name,
                "role": "USER",
            }

            if country:
                payload["country"] = country

            if institution:
                payload["institution"] = institution

            # Use legacy=false to send secure reset link instead of emailing password
            resp = requests.post(
                f"{api_base}/user?legacy=false",
                json=payload,
                headers=apply_default_headers(),
                timeout=15,
            )

            if resp.status_code == 200:
                logger.debug("User registration successful for: %s", email)
                return (
                    "Account created successfully! Please check your email to verify your account, "
                    "then you can log in.",
                    "success",
                    True,
                )
            elif resp.status_code == 400:
                error_msg = "Registration failed."
                try:
                    error_data = resp.json()
                    error_msg = error_data.get("detail", error_data.get("msg", error_msg))
                except Exception:
                    pass
                logger.warning("Registration failed (400): %s", error_msg)
                return error_msg, "danger", True
            elif resp.status_code == 422:
                error_msg = "Validation failed."
                try:
                    error_data = resp.json()
                    error_msg = error_data.get("detail", error_msg)
                except Exception:
                    pass
                logger.warning("Registration validation failed (422): %s", error_msg)
                return error_msg, "danger", True
            elif resp.status_code == 429:
                logger.warning("Registration rate limit exceeded")
                return (
                    "Too many registration attempts. Please try again later.",
                    "danger",
                    True,
                )
            else:
                logger.warning("Registration failed with status: %s", resp.status_code)
                error_msg = "Registration failed."
                try:
                    error_data = resp.json()
                    error_msg = error_data.get("detail", error_data.get("msg", error_msg))
                except Exception:
                    pass
                return f"{error_msg} Please try again.", "danger", True

        except requests.exceptions.Timeout:
            logger.warning("Registration request timed out")
            return "Request timed out. Please try again.", "danger", True
        except requests.exceptions.ConnectionError:
            logger.warning("Connection error during registration")
            return (
                "Cannot connect to the server. Please check your connection.",
                "danger",
                True,
            )
        except Exception as e:
            logger.exception("Error during registration: %s", e)
            return f"An error occurred: {str(e)}", "danger", True


def _get_fallback_country_options():
    """Return a fallback list of common countries when API is unavailable."""
    # Common countries as fallback
    countries = [
        ("AFG", "Afghanistan"),
        ("ALB", "Albania"),
        ("DZA", "Algeria"),
        ("ARG", "Argentina"),
        ("AUS", "Australia"),
        ("AUT", "Austria"),
        ("BGD", "Bangladesh"),
        ("BEL", "Belgium"),
        ("BRA", "Brazil"),
        ("CAN", "Canada"),
        ("CHL", "Chile"),
        ("CHN", "China"),
        ("COL", "Colombia"),
        ("COD", "Democratic Republic of the Congo"),
        ("EGY", "Egypt"),
        ("ETH", "Ethiopia"),
        ("FRA", "France"),
        ("DEU", "Germany"),
        ("GHA", "Ghana"),
        ("IND", "India"),
        ("IDN", "Indonesia"),
        ("IRN", "Iran"),
        ("IRQ", "Iraq"),
        ("ITA", "Italy"),
        ("JPN", "Japan"),
        ("KEN", "Kenya"),
        ("MEX", "Mexico"),
        ("MAR", "Morocco"),
        ("MMR", "Myanmar"),
        ("NPL", "Nepal"),
        ("NLD", "Netherlands"),
        ("NGA", "Nigeria"),
        ("PAK", "Pakistan"),
        ("PER", "Peru"),
        ("PHL", "Philippines"),
        ("POL", "Poland"),
        ("RUS", "Russia"),
        ("SAU", "Saudi Arabia"),
        ("ZAF", "South Africa"),
        ("KOR", "South Korea"),
        ("ESP", "Spain"),
        ("SDN", "Sudan"),
        ("TZA", "Tanzania"),
        ("THA", "Thailand"),
        ("TUR", "Turkey"),
        ("UGA", "Uganda"),
        ("GBR", "United Kingdom"),
        ("USA", "United States"),
        ("VNM", "Vietnam"),
        ("ZWE", "Zimbabwe"),
    ]
    return [{"label": name, "value": code} for code, name in countries]
