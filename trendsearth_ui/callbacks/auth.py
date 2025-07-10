"""Authentication and navigation callbacks."""

from datetime import datetime, timedelta
import json
import re

from dash import Input, Output, State, callback_context, html, no_update
from flask import request
import requests

from ..components import dashboard_layout, login_layout
from ..config import API_BASE, AUTH_URL
from ..utils import (
    create_auth_cookie_data,
    extract_auth_from_cookie,
    get_user_info,
    is_auth_cookie_valid,
)


def register_callbacks(app):
    """Register authentication and navigation callbacks."""

    @app.callback(
        [
            Output("page-content", "children"),
            Output("token-store", "clear_data"),
            Output("token-store", "data", allow_duplicate=True),
            Output("role-store", "data", allow_duplicate=True),
            Output("user-store", "data", allow_duplicate=True),
        ],
        [
            Input("token-store", "data"),
            Input("url", "pathname"),  # Use URL pathname to trigger on page load
        ],
        prevent_initial_call="initial_duplicate",
    )
    def display_page(token, _pathname):
        """Display login or dashboard based on authentication status."""
        # Check if we have a valid token in store
        if token:
            print("✅ Token found in store, displaying dashboard layout")
            dashboard = dashboard_layout()
            print(f"🏗️ Dashboard layout created: {type(dashboard)}")
            return dashboard, False, no_update, no_update, no_update

        # If no token in store, check HTTP cookie for valid authentication
        cookie_data = None
        try:
            auth_cookie = request.cookies.get("auth_token")
            if auth_cookie:
                cookie_data = json.loads(auth_cookie)
        except Exception as e:
            print(f"Error reading auth cookie: {e}")
            cookie_data = None

        if cookie_data and is_auth_cookie_valid(cookie_data):
            stored_token, stored_email, stored_user_data = extract_auth_from_cookie(cookie_data)
            if stored_token and stored_user_data:
                print(f"🍪 Restored authentication from cookie for: {stored_email}")
                role = stored_user_data.get("role", "USER")
                return (dashboard_layout(), False, stored_token, role, stored_user_data)

        # No valid authentication found, show login page
        return login_layout(), True, None, None, None

    @app.callback(
        [
            Output("token-store", "data"),
            Output("role-store", "data"),
            Output("user-store", "data"),
            Output("login-alert", "children"),
            Output("login-alert", "color"),
            Output("login-alert", "is_open"),
        ],
        [Input("login-btn", "n_clicks")],
        [
            State("login-email", "value"),
            State("login-password", "value"),
            State("remember-me-checkbox", "value"),
        ],
        prevent_initial_call=True,
    )
    def login_api(_n, email, password, remember_me):
        """Handle login authentication."""
        print(f"🔐 Login attempt - Email: {email}, Button clicks: {_n}, Remember: {remember_me}")

        if not email or not password:
            print("⚠️ Missing email or password")
            return (None, None, None, "Please enter both email and password.", "warning", True)

        print(f"🌐 Attempting to connect to: {AUTH_URL}")
        try:
            auth_data = {"email": email, "password": password}
            resp = requests.post(AUTH_URL, json=auth_data, timeout=5)

            if resp.status_code == 200:
                print("✅ Login API response successful")
                data = resp.json()
                token = data.get("access_token")
                user_data = get_user_info(token)

                if user_data and token:
                    role = user_data.get("role", "USER")
                    print(f"✅ Login successful for user: {user_data.get('email', 'unknown')}")

                    # Set HTTP cookie if remember me is checked
                    if remember_me:
                        cookie_data = create_auth_cookie_data(token, email, user_data)
                        cookie_value = json.dumps(cookie_data)

                        # Access Flask response through callback context
                        ctx = callback_context
                        if hasattr(ctx, "response") and ctx.response:
                            expiration = datetime.now() + timedelta(hours=6)
                            ctx.response.set_cookie(
                                "auth_token",
                                cookie_value,
                                expires=expiration,
                                httponly=True,
                                secure=False,  # Set to True in production with HTTPS
                                samesite="Lax",
                            )
                            print("🍪 Set HTTP authentication cookie with 6-hour expiration")

                    return (token, role, user_data, "Login successful!", "success", True)
                else:
                    print("❌ Failed to retrieve user information")
                    return (
                        None,
                        None,
                        None,
                        "Failed to retrieve user information.",
                        "danger",
                        True,
                    )
            else:
                print(f"❌ Login failed with status code: {resp.status_code}")
                return (None, None, None, "Invalid credentials.", "danger", True)

        except requests.exceptions.Timeout:
            print("⏰ Login request timed out")
            return (
                None,
                None,
                None,
                "Login failed: Connection timeout. Please try again later.",
                "danger",
                True,
            )
        except requests.exceptions.ConnectionError:
            print("❌ Connection error during login")
            return (
                None,
                None,
                None,
                "Login failed: Cannot connect to authentication server. Please check the server status.",
                "danger",
                True,
            )
        except Exception as e:
            print(f"❌ Login error: {str(e)}")
            return (None, None, None, f"Login failed: {str(e)}", "danger", True)

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
        prevent_initial_call=True,
    )
    def logout_user(header_logout_clicks):
        """Handle user logout and clear authentication cookie."""
        if header_logout_clicks:
            print("🚪 User logging out - clearing authentication data")

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
        [Output("login-email", "value")],
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
                    return [email_value]

        return [""]

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

        # Add role badge
        role_color = "primary" if role == "ADMIN" else "secondary"
        role_text = role.title() if role else "User"

        return html.Div(
            [
                html.Span(f"Welcome, {display_name}", className="me-2"),
                html.Span(
                    role_text,
                    className=f"badge bg-{role_color}",
                ),
            ],
            className="d-flex align-items-center",
        )

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
        [State("forgot-password-email", "value")],
        prevent_initial_call=True,
    )
    def send_password_reset(n_clicks, email):
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
            print(f"🔐 Attempting password recovery for email: {email}")

            # Use the email as the user_id parameter in the endpoint
            resp = requests.post(
                f"{API_BASE}/user/{email}/recover-password",
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
