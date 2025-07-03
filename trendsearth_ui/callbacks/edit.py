"""Edit modal callbacks for users and scripts."""

from dash import Input, Output, State, no_update


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
        ],
        [Input("users-table", "cellClicked")],
        [State("role-store", "data")],
        prevent_initial_call=True,
    )
    def open_edit_user_modal(cell_clicked, role):
        """Open edit user modal from user table."""
        print(f"🔧 USER EDIT CALLBACK TRIGGERED: cell_clicked={cell_clicked}, role={role}")
        if not cell_clicked or role != "ADMIN":
            return False, None, "", "", "", "", "USER"
        if cell_clicked.get("colId") != "edit":
            return False, None, "", "", "", "", "USER"

        # Get row data directly from the cell click event
        row_data = cell_clicked.get("data")
        if not row_data or "id" not in row_data:
            print("❌ No row data found in cell click event")
            return False, None, "", "", "", "", "USER"

        user = row_data
        print(f"✅ Found user data: {user.get('id')} - {user.get('email')}")

        return (
            True,
            user,
            user.get("name", ""),
            user.get("email", ""),
            user.get("institution", ""),
            user.get("country", ""),
            user.get("role", "USER"),
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
        [State("role-store", "data")],
        prevent_initial_call=True,
    )
    def open_edit_script_modal(cell_clicked, role):
        print(f"🔧 SCRIPT EDIT CALLBACK TRIGGERED: cell_clicked={cell_clicked}, role={role}")
        if not cell_clicked or role != "ADMIN":
            return False, None, "", "", "DRAFT"
        if cell_clicked.get("colId") != "edit":
            return False, None, "", "", "DRAFT"

        # Get row data directly from the cell click event
        row_data = cell_clicked.get("data")
        if not row_data or "id" not in row_data:
            print("❌ No row data found in cell click event")
            return False, None, "", "", "DRAFT"

        script = row_data
        print(f"✅ Found script data: {script.get('id')} - {script.get('name')}")

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
        import requests

        from ..config import API_BASE

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
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.patch(
            f"{API_BASE}/user/{user_id}",
            json=update_data,
            headers=headers,
            timeout=10,
        )

        if resp.status_code == 200:
            print(f"✅ User {user_id} updated successfully")
            # Close modal and trigger table refresh
            return False, (current_refresh_clicks or 0) + 1
        else:
            print(f"❌ Failed to update user: {resp.status_code} {resp.text}")
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
        import requests

        from ..config import API_BASE

        script_id = script_data.get("id")
        if not script_id:
            return no_update, no_update

        update_data = {
            "name": name,
            "description": description,
            "status": status,
        }
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.patch(
            f"{API_BASE}/script/{script_id}",
            json=update_data,
            headers=headers,
            timeout=10,
        )

        if resp.status_code == 200:
            print(f"✅ Script {script_id} updated successfully")
            # Close modal and trigger table refresh
            return False, (current_refresh_clicks or 0) + 1
        else:
            print(f"❌ Failed to update script: {resp.status_code} {resp.text}")
            return no_update, no_update


# Legacy callback decorators for backward compatibility (these won't be executed)
