"""Authentication and navigation callbacks."""

from dash import Input, Output, State, callback, no_update
import requests

from ..components import dashboard_layout, login_layout
from ..config import AUTH_URL
from ..utils import get_user_info


def register_callbacks(app):
    """Register authentication and navigation callbacks."""

    @app.callback(
        Output("page-content", "children"),
        Output("token-store", "clear_data"),
        Input("token-store", "data"),
    )
    def display_page(token):
        """Display login or dashboard based on authentication status."""
        if not token:
            return login_layout(), True
        return dashboard_layout(), False

    @app.callback(
        Output("token-store", "data"),
        Output("role-store", "data"),
        Output("user-store", "data"),
        Output("login-alert", "children"),
        Output("login-alert", "color"),
        Output("login-alert", "is_open"),
        Input("login-btn", "n_clicks"),
        State("login-email", "value"),
        State("login-password", "value"),
        prevent_initial_call=True,
    )
    def login_api(_n, email, password):
        """Handle login authentication."""
        if not email or not password:
            return None, None, None, "Please enter both email and password.", "warning", True

        try:
            auth_data = {"email": email, "password": password}
            resp = requests.post(f"{AUTH_URL}/login", json=auth_data, timeout=10)

            if resp.status_code == 200:
                data = resp.json()
                token = data.get("access_token")
                user_data = get_user_info(token)

                if user_data and token:
                    role = user_data.get("role", "USER")
                    return token, role, user_data, "Login successful!", "success", True
                else:
                    return None, None, None, "Failed to retrieve user information.", "danger", True
            else:
                return None, None, None, "Invalid credentials.", "danger", True

        except Exception as e:
            return None, None, None, f"Login failed: {str(e)}", "danger", True


# Legacy callback decorators for backward compatibility (these won't be executed)
@callback(
    Output("page-content", "children"),
    Output("token-store", "clear_data"),
    Input("token-store", "data"),
)
def display_page_legacy(token):
    """Display login or dashboard based on authentication status."""
    if not token:
        return login_layout(), True
    return dashboard_layout(), False


@callback(
    Output("token-store", "data"),
    Output("role-store", "data"),
    Output("user-store", "data"),
    Output("login-alert", "children"),
    Output("login-alert", "color"),
    Output("login-alert", "is_open"),
    Input("login-btn", "n_clicks"),
    State("login-email", "value"),
    State("login-password", "value"),
    prevent_initial_call=True,
)
def login_api_legacy(_n, email, password):
    """Handle login API request."""
    if not email or not password:
        return no_update, no_update, no_update, "Please enter email and password.", "danger", True
    try:
        resp = requests.post(
            AUTH_URL,
            json={"email": email, "password": password},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("access_token") or data.get("token")
            if not token:
                return no_update, no_update, no_update, "No token returned.", "danger", True
            user_info = get_user_info(token)
            role = user_info.get("role", "USER")
            return token, role, user_info, "Login successful!", "success", True
        else:
            msg = ""
            try:
                msg = resp.json().get("msg")
            except Exception:
                msg = resp.text
            return no_update, no_update, no_update, f"Login failed: {msg}", "danger", True
    except Exception as e:
        return no_update, no_update, no_update, f"Network error: {str(e)}", "danger", True
