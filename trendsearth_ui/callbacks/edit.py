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
        [
            State("users-raw-data", "data"),
            State("role-store", "data"),
            State("users-table", "getRowsRequest"),
        ],
        prevent_initial_call=True,
    )
    def open_edit_user_modal(cell_clicked, users_data, role, last_request):
        """Open edit user modal from user table."""
        print(f"🔧 USER EDIT CALLBACK TRIGGERED: cell_clicked={cell_clicked}, role={role}")
        if not cell_clicked or role != "ADMIN":
            return False, None, "", "", "", "", "USER"
        if cell_clicked.get("colId") != "edit":
            return False, None, "", "", "", "", "USER"

        # 1. Use row data from cellClicked if present
        row_data = cell_clicked.get("data")
        if row_data and "id" in row_data:
            user = row_data
        else:
            # 2. Fallback: reconstruct the current page/block and use rowIndex within it
            row_index = cell_clicked.get("rowIndex")
            if row_index is None or not last_request or not users_data:
                return False, None, "", "", "", "", "USER"
            from ..utils import parse_date

            is_admin = role == "ADMIN"
            table_data = []
            for user_data in users_data:
                row = user_data.copy()
                for date_col in ["created_at", "updated_at"]:
                    if date_col in row:
                        row[date_col] = parse_date(row.get(date_col))
                if is_admin:
                    row["edit"] = "Edit"
                table_data.append(row)
            sort_model = last_request.get("sortModel", [])
            filter_model = last_request.get("filterModel", {})
            if sort_model:
                sort_item = sort_model[0]
                sort_field = sort_item.get("colId")
                sort_dir = sort_item.get("sort")
                reverse = sort_dir == "desc"
                if sort_field:
                    table_data = sorted(
                        table_data,
                        key=lambda x: str(x.get(sort_field, "")).lower(),
                        reverse=reverse,
                    )
            if filter_model:
                filtered_data = []
                for row in table_data:
                    include_row = True
                    for field, filter_config in filter_model.items():
                        if "filter" in filter_config:
                            filter_value = filter_config["filter"].lower()
                            row_value = str(row.get(field, "")).lower()
                            if filter_value not in row_value:
                                include_row = False
                                break
                    if include_row:
                        filtered_data.append(row)
                table_data = filtered_data
            start_row = last_request.get("startRow", 0)
            end_row = last_request.get("endRow", len(table_data))
            page_data = table_data[start_row:end_row]
            if row_index < len(page_data):
                user = page_data[row_index]
            else:
                return False, None, "", "", "", "", "USER"
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
            State("scripts-raw-data", "data"),
            State("users-raw-data", "data"),
            State("role-store", "data"),
            State("scripts-table", "getRowsRequest"),
        ],
        prevent_initial_call=True,
    )
    def open_edit_script_modal(cell_clicked, scripts_data, users_data, role, last_request):
        print(f"🔧 SCRIPT EDIT CALLBACK TRIGGERED: cell_clicked={cell_clicked}, role={role}")
        if not cell_clicked or role != "ADMIN":
            return False, None, "", "", "DRAFT"
        if cell_clicked.get("colId") != "edit":
            return False, None, "", "", "DRAFT"
        row_data = cell_clicked.get("data")
        if row_data and "id" in row_data:
            script = row_data
        else:
            row_index = cell_clicked.get("rowIndex")
            if row_index is None or not last_request or not scripts_data or not users_data:
                return False, None, "", "", "DRAFT"
            from ..utils import parse_date

            is_admin = role == "ADMIN"
            user_id_to_name = {u.get("id"): u.get("name") for u in users_data or []}
            user_col = None
            if scripts_data and "user_id" in scripts_data[0]:
                user_col = "user_id"
            elif scripts_data and "author_id" in scripts_data[0]:
                user_col = "author_id"
            table_data = []
            for script_data in scripts_data:
                row = script_data.copy()
                if user_col:
                    row["user_name"] = user_id_to_name.get(row.get(user_col), "")
                for date_col in ["start_date", "end_date", "created_at", "updated_at"]:
                    if date_col in row:
                        row[date_col] = parse_date(row.get(date_col))
                row["logs"] = "Show Logs"
                if is_admin:
                    row["edit"] = "Edit"
                table_data.append(row)
            sort_model = last_request.get("sortModel", [])
            filter_model = last_request.get("filterModel", {})
            if sort_model:
                sort_item = sort_model[0]
                sort_field = sort_item.get("colId")
                sort_dir = sort_item.get("sort")
                reverse = sort_dir == "desc"
                if sort_field:
                    table_data = sorted(
                        table_data,
                        key=lambda x: str(x.get(sort_field, "")).lower(),
                        reverse=reverse,
                    )
            if filter_model:
                filtered_data = []
                for row in table_data:
                    include_row = True
                    for field, filter_config in filter_model.items():
                        if "filter" in filter_config:
                            filter_value = filter_config["filter"].lower()
                            row_value = str(row.get(field, "")).lower()
                            if filter_value not in row_value:
                                include_row = False
                                break
                    if include_row:
                        filtered_data.append(row)
                table_data = filtered_data
            start_row = last_request.get("startRow", 0)
            end_row = last_request.get("endRow", len(table_data))
            page_data = table_data[start_row:end_row]
            if row_index < len(page_data):
                script = page_data[row_index]
            else:
                return False, None, "", "", "DRAFT"
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
            Output("users-raw-data", "data", allow_duplicate=True),
            Output("edit-user-data", "data", allow_duplicate=True),
            Output("users-table-refresh-trigger", "data", allow_duplicate=True),
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
            State("users-table-refresh-trigger", "data"),
        ],
        prevent_initial_call=True,
    )
    def save_user_edits(
        n_clicks, user_data, name, email, institution, country, role, token, refresh_count
    ):
        """Save user edits to the API and refresh the table from backend."""
        if not n_clicks or not user_data or not token:
            return no_update, no_update, no_update, no_update
        import requests

        from ..config import API_BASE

        user_id = user_data.get("id")
        if not user_id:
            return no_update, no_update, no_update, no_update
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
            users_resp = requests.get(f"{API_BASE}/user", headers=headers, timeout=10)
            if users_resp.status_code == 200:
                users_list = users_resp.json().get("data", [])
            else:
                users_list = None
            updated_user = resp.json().get("data", update_data)
            # Increment refresh trigger
            new_refresh = (refresh_count or 0) + 1
            return False, users_list, updated_user, new_refresh
        else:
            print(f"Failed to update user: {resp.status_code} {resp.text}")
            return no_update, no_update, no_update, no_update

    @app.callback(
        [
            Output("edit-script-modal", "is_open", allow_duplicate=True),
            Output("scripts-raw-data", "data", allow_duplicate=True),
            Output("edit-script-data", "data", allow_duplicate=True),
            Output("scripts-table-refresh-trigger", "data", allow_duplicate=True),
        ],
        [Input("save-edit-script", "n_clicks")],
        [
            State("edit-script-data", "data"),
            State("edit-script-name", "value"),
            State("edit-script-description", "value"),
            State("edit-script-status", "value"),
            State("token-store", "data"),
            State("scripts-table-refresh-trigger", "data"),
        ],
        prevent_initial_call=True,
    )
    def save_script_edits(n_clicks, script_data, name, description, status, token, refresh_count):
        """Save script edits to the API and refresh the table from backend."""
        if not n_clicks or not script_data or not token:
            return no_update, no_update, no_update, no_update
        import requests

        from ..config import API_BASE

        script_id = script_data.get("id")
        if not script_id:
            return no_update, no_update, no_update, no_update
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
            scripts_resp = requests.get(f"{API_BASE}/script", headers=headers, timeout=10)
            if scripts_resp.status_code == 200:
                scripts_list = scripts_resp.json().get("data", [])
            else:
                scripts_list = None
            updated_script = resp.json().get("data", update_data)
            new_refresh = (refresh_count or 0) + 1
            return False, scripts_list, updated_script, new_refresh
        else:
            print(f"Failed to update script: {resp.status_code} {resp.text}")
            return no_update, no_update, no_update, no_update


# Legacy callback decorators for backward compatibility (these won't be executed)
