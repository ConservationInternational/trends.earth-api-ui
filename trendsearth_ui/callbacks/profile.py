"""Profile and password change callbacks."""

from dash import Input, Output, State, no_update


def register_callbacks(app):
    """Register profile and password change callbacks."""

    @app.callback(
        [
            Output("profile-update-alert", "children"),
            Output("profile-update-alert", "color"),
            Output("profile-update-alert", "is_open"),
            Output("user-store", "data", allow_duplicate=True),
        ],
        [Input("update-profile-btn", "n_clicks")],
        [
            State("profile-name", "value"),
            State("profile-institution", "value"),
            State("token-store", "data"),
            State("user-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def update_profile(n_clicks, name, institution, token, user_data):
        """Update user profile information."""
        if not n_clicks or not token or not user_data:
            return no_update, no_update, no_update, no_update

        if not name:
            return "Name is required.", "danger", True, no_update

        update_data = {"name": name, "institution": institution or ""}

        try:
            user_id = user_data.get("id")
            if not user_id:
                return "User ID not found in user data.", "danger", True, no_update

            from ..utils.helpers import make_authenticated_request

            resp = make_authenticated_request(
                "/user/me",
                token,
                method="PATCH",
                json=update_data,
                timeout=10,
            )

            if resp.status_code == 200:
                # Update user data in store
                updated_user_data = user_data.copy()
                updated_user_data.update(update_data)
                return "Profile updated successfully!", "success", True, updated_user_data
            else:
                error_msg = "Failed to update profile."
                try:
                    error_data = resp.json()
                    error_msg = error_data.get("msg", error_msg)
                except Exception:
                    pass
                return error_msg, "danger", True, no_update

        except Exception as e:
            return f"Network error: {str(e)}", "danger", True, no_update

    @app.callback(
        [
            Output("password-change-alert", "children"),
            Output("password-change-alert", "color"),
            Output("password-change-alert", "is_open"),
            Output("current-password", "value"),
            Output("new-password", "value"),
            Output("confirm-password", "value"),
        ],
        [Input("change-password-btn", "n_clicks")],
        [
            State("current-password", "value"),
            State("new-password", "value"),
            State("confirm-password", "value"),
            State("token-store", "data"),
            State("user-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def change_password(
        n_clicks, current_password, new_password, confirm_password, token, user_data
    ):
        """Change user password."""
        if not n_clicks or not token or not user_data:
            return no_update, no_update, no_update, no_update, no_update, no_update

        if not current_password or not new_password or not confirm_password:
            return (
                "All password fields are required.",
                "danger",
                True,
                no_update,
                no_update,
                no_update,
            )

        if new_password != confirm_password:
            return "New passwords do not match.", "danger", True, no_update, no_update, no_update

        if len(new_password) < 6:
            return (
                "Password must be at least 6 characters long.",
                "danger",
                True,
                no_update,
                no_update,
                no_update,
            )

        password_data = {"old_password": current_password, "new_password": new_password}

        try:
            print(f"🔐 Attempting password change for user: {user_data.get('email', 'unknown')}")

            from ..utils.helpers import make_authenticated_request

            resp = make_authenticated_request(
                "/user/me/change-password",
                token,
                method="PATCH",
                json=password_data,
                timeout=10,
            )

            if resp.status_code == 200:
                print("✅ Password changed successfully")
                # Clear password fields on success
                return "Password changed successfully!", "success", True, "", "", ""
            else:
                print(f"❌ Password change failed with status: {resp.status_code}")
                error_msg = "Failed to change password."
                try:
                    error_data = resp.json()
                    error_msg = error_data.get("msg", error_msg)
                    print(f"🔍 API error response: {error_data}")
                except Exception:
                    pass
                # Add status code to error message for debugging
                error_msg += f" (Status: {resp.status_code})"
                return error_msg, "danger", True, no_update, no_update, no_update

        except Exception as e:
            print(f"💥 Network error during password change: {str(e)}")
            return f"Network error: {str(e)}", "danger", True, no_update, no_update, no_update


# Legacy callback decorators for backward compatibility (these won't be executed)
