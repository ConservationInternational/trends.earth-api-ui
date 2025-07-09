"""Edit modal callbacks for users and scripts."""

from dash import Input, Output, State, no_update
import requests

from ..config import API_BASE


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
        [
            State("role-store", "data"),
            State("token-store", "data"),
            State("users-table-state", "data"),
        ],
        prevent_initial_call=True,
    )
    def open_edit_user_modal(cell_clicked, role, token, table_state):
        """Open edit user modal from user table."""
        print(f"🔧 USER EDIT CALLBACK TRIGGERED: cell_clicked={cell_clicked}, role={role}")
        if not cell_clicked or role != "ADMIN":
            return False, None, "", "", "", "", "USER"
        if cell_clicked.get("colId") != "edit":
            return False, None, "", "", "", "", "USER"

        # Try to get row data from cell click event first
        row_data = cell_clicked.get("data")
        user_id = None

        if row_data:
            user_id = row_data.get("id")
            user = row_data

        # If we don't have row data or user_id, fall back to pagination approach
        if not user_id:
            row_index = cell_clicked.get("rowIndex")
            if row_index is None:
                print("❌ No row index found in cell click event")
                return False, None, "", "", "", "", "USER"

            # Calculate which page this row is on
            headers = {"Authorization": f"Bearer {token}"}
            page_size = 50  # This should match your cacheBlockSize
            page = (row_index // page_size) + 1
            row_in_page = row_index % page_size

            params = {"page": page, "per_page": page_size}

            # Apply the same sort and filter that the table is currently using
            if table_state:
                if table_state.get("sort_sql"):
                    params["sort"] = table_state["sort_sql"]
                if table_state.get("filter_sql"):
                    params["filter"] = table_state["filter_sql"]

            resp = requests.get(f"{API_BASE}/user", params=params, headers=headers)
            if resp.status_code != 200:
                print(f"❌ Failed to fetch user data: {resp.text}")
                return False, None, "", "", "", "", "USER"

            result = resp.json()
            users = result.get("data", [])
            if row_in_page >= len(users):
                print(f"❌ Row index {row_in_page} out of range for page {page}")
                return False, None, "", "", "", "", "USER"

            user = users[row_in_page]
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
        [
            State("role-store", "data"),
            State("token-store", "data"),
            State("scripts-table-state", "data"),
        ],
        prevent_initial_call=True,
    )
    def open_edit_script_modal(cell_clicked, role, token, table_state):
        print(f"🔧 SCRIPT EDIT CALLBACK TRIGGERED: cell_clicked={cell_clicked}, role={role}")
        if not cell_clicked or role != "ADMIN":
            return False, None, "", "", "DRAFT"
        if cell_clicked.get("colId") != "edit":
            return False, None, "", "", "DRAFT"

        # Try to get row data from cell click event first
        row_data = cell_clicked.get("data")
        script_id = None

        if row_data:
            script_id = row_data.get("id")
            script = row_data

        # If we don't have row data or script_id, fall back to pagination approach
        if not script_id:
            row_index = cell_clicked.get("rowIndex")
            if row_index is None:
                print("❌ No row index found in cell click event")
                return False, None, "", "", "DRAFT"

            # Calculate which page this row is on
            headers = {"Authorization": f"Bearer {token}"}
            page_size = 50  # This should match your cacheBlockSize
            page = (row_index // page_size) + 1
            row_in_page = row_index % page_size

            params = {"page": page, "per_page": page_size, "include": "user_name"}

            # Apply the same sort and filter that the table is currently using
            if table_state:
                if table_state.get("sort_sql"):
                    params["sort"] = table_state["sort_sql"]
                if table_state.get("filter_sql"):
                    params["filter"] = table_state["filter_sql"]

            resp = requests.get(f"{API_BASE}/script", params=params, headers=headers)
            if resp.status_code != 200:
                print(f"❌ Failed to fetch script data: {resp.text}")
                return False, None, "", "", "DRAFT"

            result = resp.json()
            scripts = result.get("data", [])

            if row_in_page >= len(scripts):
                print(f"❌ Row index {row_in_page} out of range for page {page}")
                return False, None, "", "", "DRAFT"

            script = scripts[row_in_page]
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
        if not delete_clicks or role != "ADMIN" or not user_data:
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
        ],
        prevent_initial_call=True,
    )
    def confirm_delete_user(confirm_clicks, user_data, token, role, current_refresh_clicks):
        """Confirm and execute user deletion."""
        if not confirm_clicks or role != "ADMIN" or not user_data or not token:
            return no_update, no_update, no_update

        user_id = user_data.get("id")
        if not user_id:
            print("❌ No user ID found for deletion")
            return no_update, no_update, no_update

        try:
            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.delete(f"{API_BASE}/user/{user_id}", headers=headers, timeout=10)

            if resp.status_code in [200, 204]:
                print(f"✅ User {user_id} deleted successfully")
                # Close both modals and refresh users table
                return False, False, (current_refresh_clicks or 0) + 1
            else:
                print(f"❌ Failed to delete user: {resp.status_code} {resp.text}")
                # Close delete modal but keep edit modal open
                return False, no_update, no_update

        except Exception as e:
            print(f"❌ Error deleting user: {e}")
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
        if not n_clicks or role != "ADMIN" or not script_data:
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
        if not n_clicks or role != "ADMIN" or not script_data or not token:
            return no_update, no_update, no_update

        script_id = script_data.get("id")
        if not script_id:
            return False, no_update, no_update

        try:
            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.delete(f"{API_BASE}/script/{script_id}", headers=headers, timeout=10)

            if resp.status_code in [200, 204]:
                print(f"✅ Script {script_id} deleted successfully")
                # Close both modals and refresh scripts table
                return False, False, (current_refresh_clicks or 0) + 1
            else:
                print(f"❌ Failed to delete script: {resp.status_code} {resp.text}")
                # Close delete modal but keep edit modal open
                return False, no_update, no_update

        except Exception as e:
            print(f"❌ Error deleting script: {e}")
            # Close delete modal but keep edit modal open
            return False, no_update, no_update


# Legacy callback decorators for backward compatibility (these won't be executed)
