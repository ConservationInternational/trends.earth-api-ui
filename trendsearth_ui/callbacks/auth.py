"""Authentication and navigation callbacks."""

from dash import Input, Output, State, callback_context, no_update
import requests

from ..components import dashboard_layout, login_layout
from ..config import AUTH_URL
from ..utils import (
    get_user_info,
    create_auth_cookie_data,
    extract_auth_from_cookie,
    is_auth_cookie_valid,
    clear_auth_cookie_data,
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
            Output("login-email", "value", allow_duplicate=True),
        ],
        [
            Input("token-store", "data"),
            Input("auth-cookie", "data"),
        ],
        prevent_initial_call=False,
    )
    def display_page(token, cookie_data):
        """Display login or dashboard based on authentication status."""
        ctx = callback_context
        
        # Check if we have a valid token in store
        if token:
            return dashboard_layout(), False, no_update, no_update, no_update, no_update
        
        # If no token in store, check cookie for valid authentication
        if cookie_data and is_auth_cookie_valid(cookie_data):
            stored_token, stored_email, stored_user_data = extract_auth_from_cookie(cookie_data)
            if stored_token and stored_user_data:
                print(f"🍪 Restored authentication from cookie for: {stored_email}")
                role = stored_user_data.get("role", "USER")
                return (
                    dashboard_layout(), 
                    False, 
                    stored_token, 
                    role, 
                    stored_user_data,
                    stored_email
                )
        
        # No valid authentication found, show login page
        # If cookie has email but expired, pre-populate email field
        email_value = ""
        if cookie_data and isinstance(cookie_data, dict):
            email_value = cookie_data.get("email", "")
        
        return login_layout(), True, None, None, None, email_value

    @app.callback(
        [
            Output("token-store", "data"),
            Output("role-store", "data"),
            Output("user-store", "data"),
            Output("login-alert", "children"),
            Output("login-alert", "color"),
            Output("login-alert", "is_open"),
            Output("auth-cookie", "data"),
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
            return (
                None, None, None, 
                "Please enter both email and password.", 
                "warning", True, no_update
            )

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
                    
                    # Create cookie data if remember me is checked
                    cookie_data = no_update
                    if remember_me:
                        cookie_data = create_auth_cookie_data(token, email, user_data)
                        print(f"🍪 Created authentication cookie with 6-hour expiration")
                    
                    return (
                        token, role, user_data, 
                        "Login successful!", "success", True,
                        cookie_data
                    )
                else:
                    print("❌ Failed to retrieve user information")
                    return (
                        None, None, None, 
                        "Failed to retrieve user information.", "danger", True,
                        no_update
                    )
            else:
                print(f"❌ Login failed with status code: {resp.status_code}")
                return (
                    None, None, None, 
                    "Invalid credentials.", "danger", True,
                    no_update
                )

        except requests.exceptions.Timeout:
            print("⏰ Login request timed out")
            return (
                None, None, None,
                "Login failed: Connection timeout. Please try again later.",
                "danger", True, no_update
            )
        except requests.exceptions.ConnectionError:
            print("❌ Connection error during login")
            return (
                None, None, None,
                "Login failed: Cannot connect to authentication server. Please check the server status.",
                "danger", True, no_update
            )
        except Exception as e:
            print(f"❌ Login error: {str(e)}")
            return (
                None, None, None, 
                f"Login failed: {str(e)}", "danger", True,
                no_update
            )

    @app.callback(
        [
            Output("auth-cookie", "data", allow_duplicate=True),
            Output("token-store", "clear_data", allow_duplicate=True),
        ],
        [Input("logout-btn", "n_clicks")],
        prevent_initial_call=True,
    )
    def logout_user(_n):
        """Handle user logout and clear authentication cookie."""
        if _n:
            print("🚪 User logging out - clearing authentication data")
            return clear_auth_cookie_data(), True
        return no_update, no_update
