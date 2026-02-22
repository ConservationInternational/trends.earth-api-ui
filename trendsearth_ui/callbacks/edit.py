"""Edit modal callbacks for users and scripts."""

import logging

from dash import Input, Output, State, no_update

from ..config import get_api_base
from ..utils import get_user_info
from ..utils.helpers import make_authenticated_request
from ._table_helpers import RowResolutionError, resolve_row_data

logger = logging.getLogger(__name__)


def register_callbacks(app):
    """Register edit modal callbacks."""

    @app.callback(
        [
            Output("edit-user-modal", "is_open"),
            Output("edit-user-data", "data"),
            Output("edit-user-name", "value"),
            Output("edit-user-email", "value"),
            Output("edit-user-institution", "value"),
            Output("edit-user-country", "value"),
            Output("edit-user-role", "value"),
            Output("admin-new-password", "value"),
            Output("admin-confirm-password", "value"),
            Output("edit-user-modal-user-id", "data"),
            Output("edit-user-email-notifications-switch", "value"),
        ],
        [Input("users-table", "cellClicked")],
        [
            State("role-store", "data"),
            State("token-store", "data"),
            State("users-table-state", "data"),
        ],
        prevent_initial_call=True,
    )
    def open_edit_user_modal(cell_clicked, role, token, table_state):
        """Open edit user modal from user table.

        Access rules:
        - SUPERADMIN: Can open edit modal for any user
        - ADMIN: Can open edit modal for non-SUPERADMIN users only
        """
        logger.debug("User edit callback triggered: cell_clicked=%s, role=%s", cell_clicked, role)
        # Only ADMIN and SUPERADMIN can edit users
        if not cell_clicked or role not in ("ADMIN", "SUPERADMIN"):
            return False, None, "", "", "", "", "USER", "", "", None, True
        if cell_clicked.get("colId") != "edit":
            return False, None, "", "", "", "", "USER", "", "", None, True
        try:
            user = resolve_row_data(cell_clicked, token, table_state, "/user")
        except RowResolutionError as exc:
            logger.debug("Row resolution error: %s", exc)
            return False, None, "", "", "", "", "USER", "", "", None, True
        else:
            logger.debug("Found user data: %s - %s", user.get("id"), user.get("email"))

        # ADMIN cannot edit SUPERADMIN users
        target_user_role = user.get("role", "USER")
        if role == "ADMIN" and target_user_role == "SUPERADMIN":
            logger.debug("ADMIN cannot edit SUPERADMIN users")
            return False, None, "", "", "", "", "USER", "", "", None, True

        return (
            True,
            user,
            user.get("name", ""),
            user.get("email", ""),
            user.get("institution", ""),
            user.get("country", ""),
            user.get("role", "USER"),
            "",  # Clear admin password field
            "",  # Clear admin confirm password field
            user.get("id"),  # Set user ID for admin sub-callbacks
            user.get("email_notifications_enabled", True),  # Set notification switch
        )

    @app.callback(
        [
            Output("edit-script-modal", "is_open"),
            Output("edit-script-data", "data"),
            Output("edit-script-name", "value"),
            Output("edit-script-description", "value"),
            Output("edit-script-status", "value"),
        ],
        [Input("scripts-table", "cellClicked")],
        [
            State("role-store", "data"),
            State("token-store", "data"),
            State("scripts-table-state", "data"),
        ],
        prevent_initial_call=True,
    )
    def open_edit_script_modal(cell_clicked, role, token, table_state):
        logger.debug("Script edit callback triggered: cell_clicked=%s, role=%s", cell_clicked, role)
        if not cell_clicked or role not in ["ADMIN", "SUPERADMIN"]:
            return False, None, "", "", "DRAFT"
        if cell_clicked.get("colId") != "edit":
            return False, None, "", "", "DRAFT"

        try:
            script = resolve_row_data(
                cell_clicked,
                token,
                table_state,
                "/script",
                include="user_name",
            )
        except RowResolutionError as exc:
            logger.debug("Row resolution error: %s", exc)
            return False, None, "", "", "DRAFT"
        else:
            logger.debug("Found script data: %s - %s", script.get("id"), script.get("name"))

        return (
            True,
            script,
            script.get("name", ""),
            script.get("description", ""),
            script.get("status", "DRAFT"),
        )

    @app.callback(
        Output("edit-user-modal", "is_open", allow_duplicate=True),
        [Input("cancel-edit-user", "n_clicks")],
        prevent_initial_call=True,
    )
    def close_edit_user_modal(n_clicks):
        """Close edit user modal."""
        if n_clicks:
            return False
        return no_update

    @app.callback(
        Output("edit-script-modal", "is_open", allow_duplicate=True),
        [Input("cancel-edit-script", "n_clicks")],
        prevent_initial_call=True,
    )
    def close_edit_script_modal(n_clicks):
        """Close edit script modal."""
        if n_clicks:
            return False
        return no_update

    @app.callback(
        [
            Output("edit-user-modal", "is_open", allow_duplicate=True),
            Output("refresh-users-btn", "n_clicks", allow_duplicate=True),
        ],
        [Input("save-edit-user", "n_clicks")],
        [
            State("edit-user-data", "data"),
            State("edit-user-name", "value"),
            State("edit-user-email", "value"),
            State("edit-user-institution", "value"),
            State("edit-user-country", "value"),
            State("edit-user-role", "value"),
            State("token-store", "data"),
            State("refresh-users-btn", "n_clicks"),
        ],
        prevent_initial_call=True,
    )
    def save_user_edits(
        n_clicks, user_data, name, email, institution, country, role, token, current_refresh_clicks
    ):
        """Save user edits to the API and trigger table refresh."""
        if not n_clicks or not user_data or not token:
            return no_update, no_update

        user_id = user_data.get("id")
        if not user_id:
            return no_update, no_update

        update_data = {
            "name": name,
            "email": email,
            "institution": institution,
            "country": country,
            "role": role,
        }
        resp = make_authenticated_request(
            f"/user/{user_id}",
            token,
            method="PATCH",
            json=update_data,
            timeout=10,
        )

        if resp.status_code == 200:
            logger.debug("User %s updated successfully", user_id)
            # Close modal and trigger table refresh
            return False, (current_refresh_clicks or 0) + 1
        else:
            logger.warning("Failed to update user: %s %s", resp.status_code, resp.text)
            return no_update, no_update

    @app.callback(
        [
            Output("edit-script-modal", "is_open", allow_duplicate=True),
            Output("refresh-scripts-btn", "n_clicks", allow_duplicate=True),
        ],
        [Input("save-edit-script", "n_clicks")],
        [
            State("edit-script-data", "data"),
            State("edit-script-name", "value"),
            State("edit-script-description", "value"),
            State("edit-script-status", "value"),
            State("token-store", "data"),
            State("refresh-scripts-btn", "n_clicks"),
        ],
        prevent_initial_call=True,
    )
    def save_script_edits(
        n_clicks, script_data, name, description, status, token, current_refresh_clicks
    ):
        """Save script edits to the API and trigger table refresh."""
        if not n_clicks or not script_data or not token:
            return no_update, no_update

        script_id = script_data.get("id")
        if not script_id:
            return no_update, no_update

        update_data = {
            "name": name,
            "description": description,
            "status": status,
        }
        resp = make_authenticated_request(
            f"/script/{script_id}",
            token,
            method="PATCH",
            json=update_data,
            timeout=10,
        )

        if resp.status_code == 200:
            logger.debug("Script %s updated successfully", script_id)
            # Close modal and trigger table refresh
            return False, (current_refresh_clicks or 0) + 1
        else:
            logger.warning("Failed to update script: %s %s", resp.status_code, resp.text)
            return no_update, no_update

    @app.callback(
        [
            Output("delete-user-modal", "is_open"),
            Output("delete-user-name", "children"),
            Output("delete-user-email", "children"),
            Output("delete-user-data", "data"),
        ],
        [Input("delete-edit-user", "n_clicks")],
        [State("edit-user-data", "data"), State("role-store", "data")],
        prevent_initial_call=True,
    )
    def open_delete_user_modal(delete_clicks, user_data, role):
        """Open delete user confirmation modal."""
        if not delete_clicks or role != "SUPERADMIN" or not user_data:
            return False, "", "", None

        return (
            True,
            user_data.get("name", "Unknown"),
            user_data.get("email", "Unknown"),
            user_data,
        )

    @app.callback(
        Output("delete-user-modal", "is_open", allow_duplicate=True),
        [Input("cancel-delete-user", "n_clicks")],
        prevent_initial_call=True,
    )
    def close_delete_user_modal(cancel_clicks):
        """Close delete user modal."""
        if cancel_clicks:
            return False
        return no_update

    @app.callback(
        [
            Output("delete-user-modal", "is_open", allow_duplicate=True),
            Output("edit-user-modal", "is_open", allow_duplicate=True),
            Output("refresh-users-btn", "n_clicks", allow_duplicate=True),
        ],
        [Input("confirm-delete-user", "n_clicks")],
        [
            State("delete-user-data", "data"),
            State("token-store", "data"),
            State("role-store", "data"),
            State("refresh-users-btn", "n_clicks"),
            State("api-environment-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def confirm_delete_user(
        confirm_clicks, user_data, token, role, current_refresh_clicks, api_environment
    ):
        """Confirm and execute user deletion."""
        if not confirm_clicks or role != "SUPERADMIN" or not user_data or not token:
            return no_update, no_update, no_update

        user_id = user_data.get("id")
        if not user_id:
            logger.debug("No user ID found for deletion")
            return no_update, no_update, no_update

        api_base = get_api_base(api_environment)
        current_user = get_user_info(token, api_base)
        if not current_user or current_user.get("role") != "SUPERADMIN":
            logger.warning("Unauthorized delete attempt blocked")
            return no_update, no_update, no_update

        try:
            resp = make_authenticated_request(
                f"/user/{user_id}", token, method="DELETE", timeout=10
            )

            if resp.status_code in [200, 204]:
                logger.debug("User %s deleted successfully", user_id)
                # Close both modals and refresh users table
                return False, False, (current_refresh_clicks or 0) + 1
            else:
                logger.warning("Failed to delete user: %s %s", resp.status_code, resp.text)
                # Close delete modal but keep edit modal open
                return False, no_update, no_update

        except Exception as e:
            logger.exception("Error deleting user: %s", e)
            # Close delete modal but keep edit modal open
            return False, no_update, no_update

    @app.callback(
        [
            Output("delete-script-modal", "is_open"),
            Output("delete-script-data", "data"),
            Output("delete-script-name", "children"),
        ],
        [Input("delete-edit-script", "n_clicks")],
        [
            State("edit-script-data", "data"),
            State("role-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def open_delete_script_modal(n_clicks, script_data, role):
        """Open delete script confirmation modal."""
        if not n_clicks or role not in ["ADMIN", "SUPERADMIN"] or not script_data:
            return False, None, ""

        script_name = script_data.get("name", "Unknown Script")
        return True, script_data, script_name

    @app.callback(
        Output("delete-script-modal", "is_open", allow_duplicate=True),
        [Input("cancel-delete-script", "n_clicks")],
        prevent_initial_call=True,
    )
    def close_delete_script_modal(n_clicks):
        """Close delete script confirmation modal."""
        if n_clicks:
            return False
        return no_update

    @app.callback(
        [
            Output("delete-script-modal", "is_open", allow_duplicate=True),
            Output("edit-script-modal", "is_open", allow_duplicate=True),
            Output("refresh-scripts-btn", "n_clicks", allow_duplicate=True),
        ],
        [Input("confirm-delete-script", "n_clicks")],
        [
            State("delete-script-data", "data"),
            State("token-store", "data"),
            State("role-store", "data"),
            State("refresh-scripts-btn", "n_clicks"),
        ],
        prevent_initial_call=True,
    )
    def delete_script(n_clicks, script_data, token, role, current_refresh_clicks):
        """Delete script after confirmation."""
        if not n_clicks or role not in ["ADMIN", "SUPERADMIN"] or not script_data or not token:
            return no_update, no_update, no_update

        script_id = script_data.get("id")
        if not script_id:
            return False, no_update, no_update

        try:
            resp = make_authenticated_request(
                f"/script/{script_id}", token, method="DELETE", timeout=10
            )

            if resp.status_code in [200, 204]:
                logger.debug("Script %s deleted successfully", script_id)
                # Close both modals and refresh scripts table
                return False, False, (current_refresh_clicks or 0) + 1
            else:
                logger.warning("Failed to delete script: %s %s", resp.status_code, resp.text)
                # Close delete modal but keep edit modal open
                return False, no_update, no_update

        except Exception as e:
            logger.exception("Error deleting script: %s", e)
            # Close delete modal but keep edit modal open
            return False, no_update, no_update

    @app.callback(
        [
            Output("admin-password-change-alert", "children"),
            Output("admin-password-change-alert", "color"),
            Output("admin-password-change-alert", "is_open"),
            Output("admin-new-password", "value", allow_duplicate=True),
            Output("admin-confirm-password", "value", allow_duplicate=True),
        ],
        [Input("admin-change-password-btn", "n_clicks")],
        [
            State("admin-new-password", "value"),
            State("admin-confirm-password", "value"),
            State("edit-user-data", "data"),
            State("token-store", "data"),
            State("role-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def admin_change_password(n_clicks, new_password, confirm_password, user_data, token, role):
        """Change password for another user (admin only).

        Access rules:
        - SUPERADMIN: Can change any user's password
        - ADMIN: Can change passwords for non-SUPERADMIN users only
        """
        if not n_clicks or not token or not user_data:
            return no_update, no_update, no_update, no_update, no_update

        # Check if current user has permission to change passwords
        if role not in ("ADMIN", "SUPERADMIN"):
            return (
                "You do not have permission to change passwords.",
                "danger",
                True,
                no_update,
                no_update,
            )

        # Check if ADMIN is trying to change SUPERADMIN password
        target_user_role = user_data.get("role", "USER")
        if role == "ADMIN" and target_user_role == "SUPERADMIN":
            return (
                "Administrators cannot change superadmin passwords.",
                "danger",
                True,
                no_update,
                no_update,
            )

        if not new_password or not confirm_password:
            return (
                "Both password fields are required.",
                "danger",
                True,
                no_update,
                no_update,
            )

        if new_password != confirm_password:
            return "Passwords do not match.", "danger", True, no_update, no_update

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
            )

        if not re.search(r"[A-Z]", new_password):
            return (
                "Password must include an uppercase letter.",
                "danger",
                True,
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
            )

        if not re.search(r"\d", new_password):
            return (
                "Password must include a number.",
                "danger",
                True,
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
            )

        user_id = user_data.get("id")
        if not user_id:
            return "User ID not found.", "danger", True, no_update, no_update

        password_data = {"new_password": new_password}

        try:
            logger.debug(
                "%s attempting password change for user: %s",
                role,
                user_data.get("email", "unknown"),
            )

            resp = make_authenticated_request(
                f"/user/{user_id}/change-password",
                token,
                method="PATCH",
                json=password_data,
                timeout=10,
            )

            if resp.status_code == 200:
                logger.debug("Password changed successfully by admin")
                # Clear password fields on success
                return "Password changed successfully!", "success", True, "", ""
            else:
                logger.warning("Password change failed with status: %s", resp.status_code)
                error_msg = "Failed to change password."
                try:
                    error_data = resp.json()
                    # Check for both "msg" and "detail" keys as API may return either
                    error_msg = error_data.get("detail", error_data.get("msg", error_msg))
                    logger.debug("API error response: %s", error_data)
                except Exception:
                    logger.debug("Could not parse password change response", exc_info=True)
                # Add status code to error message for debugging
                error_msg += f" (Status: {resp.status_code})"
                return error_msg, "danger", True, no_update, no_update

        except Exception as e:
            logger.exception("Network error during admin password change: %s", e)
            return f"Network error: {str(e)}", "danger", True, no_update, no_update

    # Real-time password validation callback for admin password change
    @app.callback(
        [
            Output("admin-req-length", "className"),
            Output("admin-req-uppercase", "className"),
            Output("admin-req-lowercase", "className"),
            Output("admin-req-number", "className"),
            Output("admin-req-special", "className"),
            Output("admin-req-match", "className"),
        ],
        [
            Input("admin-new-password", "value"),
            Input("admin-confirm-password", "value"),
        ],
        prevent_initial_call=True,
    )
    def validate_admin_password_requirements(password, confirm_password):
        """Validate password requirements in real-time and update UI indicators."""
        import re

        if not password:
            # Return all as muted when no password entered
            return ["text-muted"] * 6

        special_chars = r"!@#$%^&*()\-_=+\[\]{}|;:,.<>?/"

        # Check each requirement
        has_length = len(password) >= 12
        has_upper = bool(re.search(r"[A-Z]", password))
        has_lower = bool(re.search(r"[a-z]", password))
        has_number = bool(re.search(r"\d", password))
        has_special = bool(re.search(f"[{special_chars}]", password))
        passwords_match = bool(password and confirm_password and password == confirm_password)

        # Return success (green) or danger (red) class for each requirement
        return [
            "text-success" if has_length else "text-danger",
            "text-success" if has_upper else "text-danger",
            "text-success" if has_lower else "text-danger",
            "text-success" if has_number else "text-danger",
            "text-success" if has_special else "text-danger",
            "text-success" if passwords_match else "text-danger",
        ]


# Legacy callback decorators for backward compatibility (these won't be executed)
