"""Profile and password change callbacks."""

import logging

from dash import Input, Output, State, no_update

from ..components import login_layout
from ..i18n import gettext as _

logger = logging.getLogger(__name__)


def register_callbacks(app):
    """Register profile and password change callbacks."""

    # Callbacks for conditional field visibility
    @app.callback(
        Output("profile-sector-other-col", "style"),
        [Input("profile-sector", "value")],
    )
    def toggle_profile_sector_other(sector_value):
        """Show/hide sector other field based on selection."""
        if sector_value == "other":
            return {"display": "block"}
        return {"display": "none"}

    @app.callback(
        Output("profile-purpose-other-col", "style"),
        [Input("profile-purpose", "value")],
    )
    def toggle_profile_purpose_other(purpose_value):
        """Show/hide purpose other field based on selection."""
        if purpose_value == "other":
            return {"display": "block"}
        return {"display": "none"}

    @app.callback(
        Output("profile-gender-description-col", "style"),
        [Input("profile-gender", "value")],
    )
    def toggle_profile_gender_description(gender_value):
        """Show/hide gender description field based on selection."""
        if gender_value == "self_describe":
            return {"display": "block"}
        return {"display": "none"}

    # Callback to load country options
    @app.callback(
        Output("profile-country", "options"),
        [Input("profile-countries-store", "data")],
    )
    def update_profile_country_options(countries_data):
        """Update country dropdown options from store."""
        if not countries_data:
            return []
        return countries_data

    @app.callback(
        Output("profile-countries-store", "data"),
        [Input("token-store", "data")],
    )
    def load_profile_countries(token):
        """Load country options for the profile form."""
        from ..utils.boundaries_utils import get_country_options

        # Use production environment by default
        api_environment = "production"
        logger.debug("Fetching countries for profile (environment: %s)", api_environment)
        return get_country_options(api_environment=api_environment, token=token)

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
            State("profile-role-title", "value"),
            State("profile-institution", "value"),
            State("profile-country", "value"),
            State("profile-sector", "value"),
            State("profile-sector-other", "value"),
            State("profile-purpose", "value"),
            State("profile-purpose-other", "value"),
            State("profile-gender", "value"),
            State("profile-gender-description", "value"),
            State("token-store", "data"),
            State("user-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def update_profile(
        n_clicks,
        name,
        role_title,
        institution,
        country,
        sector,
        sector_other,
        purpose,
        purpose_other,
        gender,
        gender_description,
        token,
        user_data,
    ):
        """Update user profile information."""
        if not n_clicks or not token or not user_data:
            return no_update, no_update, no_update, no_update

        # Validate required fields
        if not name:
            return _("Name is required."), "warning", True, no_update

        if not institution:
            return _("Organization is required."), "warning", True, no_update

        if not sector:
            return _("Please select your sector."), "warning", True, no_update

        if sector == "other" and not sector_other:
            return _("Please specify your sector."), "warning", True, no_update

        if not purpose:
            return _("Please select your purpose of use."), "warning", True, no_update

        if purpose == "other" and not purpose_other:
            return _("Please specify your purpose of use."), "warning", True, no_update

        if not country:
            return _("Please select your country."), "warning", True, no_update

        if gender == "self_describe" and not gender_description:
            return _("Please describe your gender identity."), "warning", True, no_update

        # Build update payload
        update_data = {
            "name": name,
            "institution": institution,
            "country": country,
            "sector": sector,
            "purpose_of_use": purpose,
        }

        # Add optional/conditional fields
        if role_title:
            update_data["role_title"] = role_title
        else:
            update_data["role_title"] = ""

        if sector == "other" and sector_other:
            update_data["sector_other"] = sector_other
        else:
            update_data["sector_other"] = ""

        if purpose == "other" and purpose_other:
            update_data["purpose_of_use_other"] = purpose_other
        else:
            update_data["purpose_of_use_other"] = ""

        if gender:
            update_data["gender_identity"] = gender
            if gender == "self_describe" and gender_description:
                update_data["gender_identity_description"] = gender_description
            else:
                update_data["gender_identity_description"] = ""
        else:
            update_data["gender_identity"] = ""
            update_data["gender_identity_description"] = ""

        try:
            user_id = user_data.get("id")
            if not user_id:
                return _("User ID not found in user data."), "danger", True, no_update

            from ..utils.helpers import make_authenticated_request

            logger.debug("Submitting profile update with payload: %s", update_data)

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
                return _("Profile updated successfully!"), "success", True, updated_user_data
            else:
                logger.warning("Profile update failed with status: %s", resp.status_code)
                error_msg = _("Failed to update profile.")
                try:
                    error_data = resp.json()
                    logger.warning("Profile update error response: %s", error_data)
                    error_msg = error_data.get("detail", error_data.get("msg", error_msg))
                except Exception:
                    logger.debug("Could not parse API error response", exc_info=True)
                return error_msg, "danger", True, no_update

        except Exception as e:
            logger.exception("Network error during profile update: %s", e)
            return _("Network error: {error}").format(error=str(e)), "danger", True, no_update

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
                _("All password fields are required."),
                "danger",
                True,
                no_update,
                no_update,
                no_update,
            )

        if new_password != confirm_password:
            return _("New passwords do not match."), "danger", True, no_update, no_update, no_update

        # Validate password meets API requirements:
        # - At least 12 characters
        # - At least one uppercase letter
        # - At least one lowercase letter
        # - At least one digit
        # - At least one special character
        import re

        if len(new_password) < 12:
            return (
                _("Password must be at least 12 characters long."),
                "danger",
                True,
                no_update,
                no_update,
                no_update,
            )

        if not re.search(r"[A-Z]", new_password):
            return (
                _("Password must include an uppercase letter."),
                "danger",
                True,
                no_update,
                no_update,
                no_update,
            )

        if not re.search(r"[a-z]", new_password):
            return (
                _("Password must include a lowercase letter."),
                "danger",
                True,
                no_update,
                no_update,
                no_update,
            )

        if not re.search(r"\d", new_password):
            return (
                _("Password must include a number."),
                "danger",
                True,
                no_update,
                no_update,
                no_update,
            )

        special_chars = r"!@#$%^&*()\-_=+\[\]{}|;:,.<>?/"
        if not re.search(f"[{special_chars}]", new_password):
            return (
                _("Password must include a special character (!@#$%^&*()-_=+[]{}|;:,.<>?/)."),
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
                return _("Password changed successfully!"), "success", True, "", "", ""
            else:
                logger.warning("Password change failed with status: %s", resp.status_code)
                error_msg = _("Failed to change password.")
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
            return (
                _("Network error: {error}").format(error=str(e)),
                "danger",
                True,
                no_update,
                no_update,
                no_update,
            )

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

                status_text = _("enabled") if enabled else _("disabled")
                return (
                    _("Email notifications {status} successfully!").format(status=status_text),
                    "success",
                    True,
                    updated_data,
                )
            else:
                error_msg = _("Failed to update email notification settings.")
                try:
                    error_data = resp.json()
                    error_msg = error_data.get("detail", error_msg)
                except Exception:
                    logger.debug("Could not parse API error response", exc_info=True)
                return error_msg, "danger", True, no_update

        except Exception as e:
            logger.exception("Error updating email notifications: %s", e)
            return _("Network error: {error}").format(error=str(e)), "danger", True, no_update

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
                _("Email confirmation does not match. Please try again."),
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
                    _("Your account has been deleted."),
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
                    _("Admin accounts cannot be deleted through self-service. ")
                    + _("Please contact a system administrator."),
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
                error_msg = _("Failed to delete account.")
                try:
                    error_data = resp.json()
                    error_msg = error_data.get("detail", error_data.get("msg", error_msg))
                except Exception:
                    logger.debug("Could not parse API error response", exc_info=True)
                # Avoid duplicate "try again" if message already contains it
                if "try again" not in error_msg.lower():
                    error_msg = (
                        _("Please try again.").format()
                        if error_msg == _("Failed to delete account.")
                        else f"{error_msg} " + _("Please try again.")
                    )
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
                _("Network error: {error}").format(error=str(e)),
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
