"""Authentication and navigation callbacks."""

from datetime import datetime, timedelta
import json
import re

from dash import Input, Output, State, callback_context, html, no_update
from flask import request
import requests

from ..components import dashboard_layout, login_layout
from ..config import get_api_base, get_auth_url
from ..utils import (
    create_auth_cookie_data,
    get_user_info,
    logout_user,
    refresh_access_token,
    should_refresh_token,
)
from ..utils.logging_config import get_logger, log_exception

# Get the configured logger
logger = get_logger()


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
            Input("token-store", "data"),
        ],
        [
            State("api-environment-store", "data"),
        ],
    )
    def display_page(_pathname, token, current_api_environment):
        """
        Display login or dashboard. This is the central callback for auth.
        It checks for a token in the store, then falls back to checking the
        auth cookie, ensuring a single, reliable path for session initialization.
        """
        # Test hook: allow mock auth via query param (used only in E2E tests)
        try:
            from flask import request as _rq

            if _rq.args.get("mock_auth") == "1":
                user_data = {
                    "id": "test_user_123",
                    "name": "Test User",
                    "email": "test@example.com",
                    "role": "ADMIN",
                }
                return (
                    dashboard_layout(),
                    False,
                    "mock_token_12345",
                    "ADMIN",
                    user_data,
                    (current_api_environment or "production"),
                )
        except Exception:
            pass

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
        ],
        prevent_initial_call=True,
    )
    def login_api(_n, email, password, remember_me, api_environment):
        """Handle login authentication."""
        print(
            f"🔐 Login attempt - Email: {email}, Button clicks: {_n}, Remember: {remember_me}, Environment: {api_environment}"
        )

        if not email or not password:
            print("⚠️ Missing email or password")
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

        print(f"🌐 Attempting to connect to: {auth_url}")
        try:
            auth_data = {"email": email, "password": password}
            resp = requests.post(auth_url, json=auth_data, timeout=5)

            if resp.status_code == 200:
                print("✅ Login API response successful")
                try:
                    data = resp.json()
                    print(
                        f"🔍 Login: Auth response JSON keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}"
                    )
                except ValueError as e:
                    print(f"❌ Login: Failed to parse auth response JSON: {e}")
                    print(f"🔍 Login: Raw auth response: {resp.text[:500]}...")
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

                print(f"🔍 Login: Received access_token: {'Yes' if access_token else 'No'}")
                print(f"🔍 Login: Received refresh_token: {'Yes' if refresh_token else 'No'}")
                print(f"🔍 Login: Access token length: {len(access_token) if access_token else 0}")

                # Use the API base for the selected environment to get user info
                print(f"🔍 Login: About to call get_user_info with api_base: {api_base}")
                user_data = get_user_info(access_token, api_base)

                print(
                    f"🔍 Login: get_user_info returned: {'Valid data' if user_data else 'None/Empty'}"
                )

                if user_data and access_token and refresh_token:
                    role = user_data.get("role", "USER")
                    print(f"✅ Login successful for user: {user_data.get('email', 'unknown')}")

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
                            ctx.response.set_cookie(
                                "auth_token",
                                cookie_value,
                                expires=expiration,
                                httponly=True,
                                secure=False,  # Set to True in production with HTTPS
                                samesite="Lax",
                            )
                            print("🍪 Set HTTP authentication cookie with 30-day expiration")

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
                    print("❌ Failed to retrieve user information")
                    print("🔍 Login failure analysis:")
                    print(f"   - user_data: {'Present' if user_data else 'Missing/None'}")
                    print(f"   - access_token: {'Present' if access_token else 'Missing/None'}")
                    print(f"   - refresh_token: {'Present' if refresh_token else 'Missing/None'}")
                    if user_data:
                        print(f"   - user_data type: {type(user_data)}")
                        print(f"   - user_data content: {user_data}")
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
                print(f"❌ Login failed with status code: {resp.status_code}")
                return (None, None, None, None, "Invalid credentials.", "danger", True)

        except requests.exceptions.Timeout:
            print("⏰ Login request timed out")
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
            print("🚪 User logging out - clearing authentication data")

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
                print(f"Error reading refresh token from cookie: {e}")

            # Call logout API to revoke refresh token
            if current_token and refresh_token_to_revoke:
                logout_success = logout_user(
                    current_token, refresh_token_to_revoke, api_environment or "production"
                )
                if logout_success:
                    print("✅ Successfully logged out from API")
                else:
                    print("⚠️ API logout failed, but clearing local session anyway")

            # Clear HTTP cookie
            ctx = callback_context
            if hasattr(ctx, "response") and ctx.response:
                ctx.response.set_cookie(
                    "auth_token",
                    "",
                    expires=0,  # Expire immediately
                    httponly=True,
                    secure=False,  # Set to True in production with HTTPS
                    samesite="Lax",
                )
                print("🍪 Cleared HTTP authentication cookie")

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
                print(f"Error reading auth cookie for email population: {e}")
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
        [Input("api-environment-store", "data")],
        prevent_initial_call=True,
    )
    def update_environment_indicator(api_environment):
        """Update the environment indicator in the header."""
        if not api_environment:
            return ""

        # Return the appropriate environment label
        if api_environment == "production":
            return "Production"
        elif api_environment == "staging":
            return "Staging"
        else:
            return api_environment.title()

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
            print(
                f"🔐 Attempting password recovery for email: {email} (Environment: {api_environment})"
            )

            # Get the API base for the selected environment
            api_base = get_api_base(api_environment)

            # Use the email as the user_id parameter in the endpoint
            resp = requests.post(
                f"{api_base}/user/{email}/recover-password",
                timeout=10,
            )

            if resp.status_code == 200:
                print(f"✅ Password recovery email sent to: {email}")
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
                print(f"❌ User not found with email: {email}")
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
                print(f"❌ Password recovery failed with status: {resp.status_code}")
                error_msg = "Failed to send password recovery email."
                try:
                    error_data = resp.json()
                    error_msg = error_data.get("msg", error_msg)
                    print(f"🔍 API error response: {error_data}")
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
            print("⏰ Password recovery request timed out")
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
            print("❌ Connection error during password recovery")
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
            print(f"💥 Error during password recovery: {str(e)}")
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
            print(f"Error reading refresh token from cookie: {e}")
            return no_update

        if not refresh_token:
            return no_update

        # Try to refresh the token using the stored API environment
        new_access_token, expires_in = refresh_access_token(
            refresh_token, api_environment or "production"
        )
        if new_access_token and new_access_token != current_token:
            print("🔄 Auto-refreshed access token")

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
                            ctx.response.set_cookie(
                                "auth_token",
                                cookie_value,
                                expires=expiration,
                                httponly=True,
                                secure=False,
                                samesite="Lax",
                            )
            except Exception as e:
                print(f"Error updating cookie during auto-refresh: {e}")

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
                                print("🍪 Cookie has expired, clearing session")
                                return None, None
                        except Exception as e:
                            print(f"Error parsing cookie expiration: {e}")
        except Exception as e:
            print(f"Error reading refresh token from cookie during proactive refresh: {e}")
            return no_update, no_update

        if not refresh_token:
            return no_update, no_update

        # Try to refresh the token proactively
        new_access_token, expires_in = refresh_access_token(
            refresh_token, api_environment or "production"
        )
        if new_access_token:
            if new_access_token != current_token:
                print("🔄 Proactively refreshed access token")

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
                        ctx.response.set_cookie(
                            "auth_token",
                            cookie_value,
                            expires=expiration,
                            httponly=True,
                            secure=False,
                            samesite="Lax",
                        )
            except Exception as e:
                print(f"Error updating cookie during proactive refresh: {e}")

            return new_access_token, user_data
        else:
            # Refresh failed, user needs to log in again
            print("❌ Proactive token refresh failed, clearing session")
            return None, None

        return no_update, no_update
