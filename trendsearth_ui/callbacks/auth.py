"""Authentication and navigation callbacks."""

from datetime import datetime, timedelta
import json

from dash import Input, Output, State, callback_context, no_update
from flask import request
import requests

from ..components import dashboard_layout, login_layout
from ..config import AUTH_URL
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
        ],
        [Input("logout-btn", "n_clicks")],
        prevent_initial_call=True,
    )
    def logout_user(_n):
        """Handle user logout and clear authentication cookie."""
        if _n:
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

            return True
        return no_update

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
