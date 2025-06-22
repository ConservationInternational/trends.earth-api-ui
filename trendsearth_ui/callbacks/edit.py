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
        [State("users-raw-data", "data"), State("role-store", "data")],
        prevent_initial_call=True,
    )
    def open_edit_user_modal(cell_clicked, users_data, role):
        """Open edit user modal from user table."""
        if not cell_clicked or role != "ADMIN":
            return False, None, "", "", "", "", "USER"

        if cell_clicked.get("colId") == "edit":
            # Get the row data from the clicked event
            row_data = cell_clicked.get("data", {})
            if row_data and ("id" in row_data or "email" in row_data):
                # Find the full user data by id (preferred) or email
                user = None
                if users_data:
                    if "id" in row_data:
                        user_id = row_data.get("id")
                        for u in users_data:
                            if u.get("id") == user_id:
                                user = u
                                break
                    elif "email" in row_data:
                        user_email = row_data.get("email")
                        for u in users_data:
                            if u.get("email") == user_email:
                                user = u
                                break

                if user:
                    return (
                        True,  # Open modal
                        user,  # Store user data
                        user.get("name", ""),
                        user.get("email", ""),
                        user.get("institution", ""),
                        user.get("country", ""),
                        user.get("role", "USER"),
                    )

        return False, None, "", "", "", "", "USER"

    @app.callback(
        [
            Output("edit-script-modal", "is_open"),
            Output("edit-script-data", "data"),
            Output("edit-script-name", "value"),
            Output("edit-script-description", "value"),
            Output("edit-script-status", "value"),
        ],
        [Input("scripts-table", "cellClicked")],
        [State("scripts-raw-data", "data"), State("role-store", "data")],
        prevent_initial_call=True,
    )
    def open_edit_script_modal(cell_clicked, scripts_data, role):
        """Open edit script modal from scripts table."""
        if not cell_clicked or role != "ADMIN":
            return False, None, "", "", "DRAFT"

        if cell_clicked.get("colId") == "edit":
            # Get the row data from the clicked event
            row_data = cell_clicked.get("data", {})
            if row_data and ("id" in row_data or "name" in row_data):
                # Find the full script data by id (preferred) or name
                script = None
                if scripts_data:
                    if "id" in row_data:
                        script_id = row_data.get("id")
                        for s in scripts_data:
                            if s.get("id") == script_id:
                                script = s
                                break
                    elif "name" in row_data:
                        script_name = row_data.get("name")
                        for s in scripts_data:
                            if s.get("name") == script_name:
                                script = s
                                break

                if script:
                    return (
                        True,  # Open modal
                        script,  # Store script data
                        script.get("name", ""),
                        script.get("description", ""),
                        script.get("status", "DRAFT"),
                    )

        return False, None, "", "", "DRAFT"

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


# Legacy callback decorators for backward compatibility (these won't be executed)
