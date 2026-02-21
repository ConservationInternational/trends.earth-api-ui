"""Profile and password change callbacks."""

import logging

from dash import Input, Output, State, no_update
import requests  # noqa: F401

from ..components import login_layout

logger = logging.getLogger(__name__)


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
                    logger.debug("Could not parse API error response", exc_info=True)
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

        # Validate password meets API requirements:
        # - At least 12 characters
        # - At least one uppercase letter
        # - At least one lowercase letter
        # - At least one digit
        # - At least one special character
        import re

        if len(new_password) < 12:
            return (
                "Password must be at least 12 characters long.",
                "danger",
                True,
                no_update,
                no_update,
                no_update,
            )

        if not re.search(r"[A-Z]", new_password):
            return (
                "Password must include an uppercase letter.",
                "danger",
                True,
                no_update,
                no_update,
                no_update,
            )

        if not re.search(r"[a-z]", new_password):
            return (
                "Password must include a lowercase letter.",
                "danger",
                True,
                no_update,
                no_update,
                no_update,
            )

        if not re.search(r"\d", new_password):
            return (
                "Password must include a number.",
                "danger",
                True,
                no_update,
                no_update,
                no_update,
            )

        special_chars = r"!@#$%^&*()\-_=+\[\]{}|;:,.<>?/"
        if not re.search(f"[{special_chars}]", new_password):
            return (
                "Password must include a special character (!@#$%^&*()-_=+[]{}|;:,.<>?/).",
                "danger",
                True,
                no_update,
                no_update,
                no_update,
            )

        password_data = {"old_password": current_password, "new_password": new_password}

        try:
            logger.debug(
                "Attempting password change for user: %s", user_data.get("email", "unknown")
            )

            from ..utils.helpers import make_authenticated_request

            resp = make_authenticated_request(
                "/user/me/change-password",
                token,
                method="PATCH",
                json=password_data,
                timeout=10,
            )

            if resp.status_code == 200:
                logger.debug("Password changed successfully")
                # Clear password fields on success
                return "Password changed successfully!", "success", True, "", "", ""
            else:
                logger.warning("Password change failed with status: %s", resp.status_code)
                error_msg = "Failed to change password."
                try:
                    error_data = resp.json()
                    # Check for both "detail" and "msg" keys as API may return either
                    error_msg = error_data.get("detail", error_data.get("msg", error_msg))
                    logger.debug("API error response: %s", error_data)
                except Exception:
                    logger.debug("Could not parse password change response", exc_info=True)
                # Add status code to error message for debugging
                error_msg += f" (Status: {resp.status_code})"
                return error_msg, "danger", True, no_update, no_update, no_update

        except Exception as e:
            logger.exception("Network error during password change: %s", e)
            return f"Network error: {str(e)}", "danger", True, no_update, no_update, no_update

    @app.callback(
        [
            Output("profile-email-notifications-alert", "children"),
            Output("profile-email-notifications-alert", "color"),
            Output("profile-email-notifications-alert", "is_open"),
            Output("user-store", "data", allow_duplicate=True),
        ],
        [Input("profile-email-notifications-switch", "value")],
        [
            State("token-store", "data"),
            State("user-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def update_email_notifications(enabled, token, user_data):
        """Update user email notification preferences."""
        if token is None or user_data is None:
            return no_update, no_update, no_update, no_update

        # Check if the value actually changed from what's stored
        # This prevents showing success message on initial page load
        current_value = user_data.get("email_notifications_enabled", True)
        if enabled == current_value:
            return no_update, no_update, no_update, no_update

        try:
            from ..utils.helpers import make_authenticated_request

            # Update email notifications setting
            resp = make_authenticated_request(
                "/user/me",
                token,
                method="PATCH",
                json={"email_notifications_enabled": enabled},
                timeout=10,
            )

            if resp.status_code == 200:
                # Update the user data in store
                updated_data = resp.json().get("data", user_data)

                status_text = "enabled" if enabled else "disabled"
                return (
                    [
                        f"Email notifications {status_text} successfully!",
                    ],
                    "success",
                    True,
                    updated_data,
                )
            else:
                error_msg = "Failed to update email notification settings."
                try:
                    error_data = resp.json()
                    error_msg = error_data.get("detail", error_msg)
                except Exception:
                    logger.debug("Could not parse API error response", exc_info=True)
                return error_msg, "danger", True, no_update

        except Exception as e:
            logger.exception("Error updating email notifications: %s", e)
            return f"Network error: {str(e)}", "danger", True, no_update

    # Delete Account Callbacks
    @app.callback(
        Output("delete-account-modal", "is_open"),
        [
            Input("delete-account-btn", "n_clicks"),
            Input("delete-account-cancel-btn", "n_clicks"),
            Input("delete-account-confirm-btn", "n_clicks"),
        ],
        [State("delete-account-modal", "is_open")],
        prevent_initial_call=True,
    )
    def toggle_delete_account_modal(_open_clicks, _cancel_clicks, _confirm_clicks, _is_open):
        """Toggle the delete account confirmation modal."""
        from dash import ctx

        if not ctx.triggered:
            return no_update

        trigger_id = ctx.triggered_id

        if trigger_id == "delete-account-btn":
            # Open modal when delete button clicked
            return True
        elif trigger_id in ["delete-account-cancel-btn", "delete-account-confirm-btn"]:
            # Close modal when cancel or confirm clicked
            return False

        return no_update

    @app.callback(
        Output("delete-account-confirm-btn", "disabled"),
        [Input("delete-account-confirm-email", "value")],
        [State("user-store", "data")],
        prevent_initial_call=True,
    )
    def validate_delete_confirmation(email_input, user_data):
        """Enable delete button only when email matches."""
        if not user_data or not email_input:
            return True

        user_email = user_data.get("email", "")
        # Enable button only if email matches exactly
        return email_input.strip().lower() != user_email.lower()

    @app.callback(
        [
            Output("delete-account-alert", "children"),
            Output("delete-account-alert", "color"),
            Output("delete-account-alert", "is_open"),
            Output("token-store", "data", allow_duplicate=True),
            Output("user-store", "data", allow_duplicate=True),
            Output("role-store", "data", allow_duplicate=True),
            Output("delete-account-confirm-email", "value"),
            Output("page-content", "children", allow_duplicate=True),
            Output("tab-content", "children", allow_duplicate=True),
        ],
        [Input("delete-account-confirm-btn", "n_clicks")],
        [
            State("delete-account-confirm-email", "value"),
            State("token-store", "data"),
            State("user-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def delete_account(n_clicks, confirm_email, token, user_data):
        """Delete user account after confirmation."""
        if not n_clicks or not token or not user_data:
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
            )

        user_email = user_data.get("email", "")

        # Double-check email confirmation
        if confirm_email.strip().lower() != user_email.lower():
            return (
                "Email confirmation does not match. Please try again.",
                "danger",
                True,
                no_update,
                no_update,
                no_update,
                "",
                no_update,
                no_update,
            )

        try:
            from ..utils.helpers import make_authenticated_request

            logger.info("User %s requested account deletion", user_email)

            resp = make_authenticated_request(
                "/user/me",
                token,
                method="DELETE",
                timeout=30,  # Longer timeout for deletion
            )

            if resp.status_code == 200:
                logger.info("Account deletion successful for user: %s", user_email)
                # Clear user data and token, redirect to login page
                return (
                    "Your account has been deleted.",
                    "success",
                    True,
                    None,  # Clear token
                    None,  # Clear user data
                    None,  # Clear role
                    "",
                    login_layout(),  # Redirect to login page
                    [],  # Clear tab content
                )
            elif resp.status_code == 403:
                logger.warning("Account deletion forbidden for user: %s", user_email)
                return (
                    "Admin accounts cannot be deleted through self-service. "
                    "Please contact a system administrator.",
                    "warning",
                    True,
                    no_update,
                    no_update,
                    no_update,
                    "",
                    no_update,
                    no_update,
                )
            else:
                logger.warning(
                    "Account deletion failed with status %s for user: %s",
                    resp.status_code,
                    user_email,
                )
                error_msg = "Failed to delete account."
                try:
                    error_data = resp.json()
                    error_msg = error_data.get("detail", error_data.get("msg", error_msg))
                except Exception:
                    logger.debug("Could not parse API error response", exc_info=True)
                # Avoid duplicate "try again" if message already contains it
                if "try again" not in error_msg.lower():
                    error_msg = f"{error_msg} Please try again."
                return (
                    error_msg,
                    "danger",
                    True,
                    no_update,
                    no_update,
                    no_update,
                    "",
                    no_update,
                    no_update,
                )

        except Exception as e:
            logger.exception("Network error during account deletion: %s", e)
            return (
                f"Network error: {str(e)}",
                "danger",
                True,
                no_update,
                no_update,
                no_update,
                "",
                no_update,
                no_update,
            )


# Legacy callback decorators for backward compatibility (these won't be executed)
