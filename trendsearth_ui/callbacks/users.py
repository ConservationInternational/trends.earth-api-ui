"""Users table callbacks."""

from dash import Input, Output, State

from ..utils import parse_date


def register_callbacks(app):
    """Register users table callbacks."""

    @app.callback(
        Output("users-table", "getRowsResponse"),
        [Input("users-table", "getRowsRequest"), Input("users-table-refresh-trigger", "data")],
        [State("users-raw-data", "data"), State("role-store", "data")],
        prevent_initial_call=True,
    )
    def get_users_rows(request, _refresh_trigger, users_data, role):
        """Get users data for ag-grid with infinite row model."""
        try:
            if not request or not users_data:
                return {"rowData": [], "rowCount": 0}

            start_row = request.get("startRow", 0)
            end_row = request.get("endRow", 100)
            sort_model = request.get("sortModel", [])
            filter_model = request.get("filterModel", {})

            # Create table data with edit buttons for admin users
            is_admin = role == "ADMIN"
            table_data = []

            for user in users_data:
                row = user.copy()
                # Parse dates
                for date_col in ["created_at", "updated_at"]:
                    if date_col in row:
                        row[date_col] = parse_date(row.get(date_col))
                # Add edit button for admin users
                if is_admin:
                    row["edit"] = "Edit"
                table_data.append(row)

            # Apply sorting
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

            # Apply filtering
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

            # Apply pagination
            total_rows = len(table_data)
            page_data = table_data[start_row:end_row]

            return {"rowData": page_data, "rowCount": total_rows}

        except Exception as e:
            print(f"Error in get_users_rows: {str(e)}")
            return {"rowData": [], "rowCount": 0}

    @app.callback(
        Output("users-table", "getRowsResponse", allow_duplicate=True),
        Input("refresh-users-btn", "n_clicks"),
        State("users-raw-data", "data"),
        State("role-store", "data"),
        prevent_initial_call=True,
    )
    def refresh_users_table(n_clicks, users_data, role):
        """Manually refresh the users table."""
        if not n_clicks or not users_data:
            return {"rowData": [], "rowCount": 0}

        # Create table data with edit buttons for admin users
        is_admin = role == "ADMIN"
        table_data = []

        for user in users_data:
            row = user.copy()
            # Parse dates
            for date_col in ["created_at", "updated_at"]:
                if date_col in row:
                    row[date_col] = parse_date(row.get(date_col))
            # Add edit button for admin users
            if is_admin:
                row["edit"] = "Edit"
            table_data.append(row)

        # Sort by email by default
        table_data = sorted(table_data, key=lambda x: x.get("email", ""))

        # Return first page
        page_data = table_data[:100]
        return {"rowData": page_data, "rowCount": len(table_data)}
