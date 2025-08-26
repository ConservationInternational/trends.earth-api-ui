"""Custom filter components for AG Grid tables to replace enterprise features."""

from dash import dcc, html
import dash_bootstrap_components as dbc


def create_checkbox_filter(filter_id, options, placeholder="Filter by values...", label=None):
    """Create a custom checkbox filter dropdown.

    Args:
        filter_id: Unique ID for the filter component
        options: List of string values to create checkboxes for
        placeholder: Placeholder text for the dropdown
        label: Optional label for the filter

    Returns:
        A dash component with checkbox filtering functionality
    """
    checkbox_items = []
    for option in options:
        checkbox_items.append(
            html.Div(
                [
                    dbc.Checkbox(
                        id=f"{filter_id}-checkbox-{option}",
                        value=False,
                        className="me-2",
                    ),
                    html.Label(
                        option,
                        htmlFor=f"{filter_id}-checkbox-{option}",
                        className="form-check-label me-3",
                        style={"cursor": "pointer"},
                    ),
                ],
                className="d-flex align-items-center mb-2",
            )
        )

    dropdown_content = [
        html.Div(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            dbc.Button(
                                "Select All",
                                id=f"{filter_id}-select-all",
                                size="sm",
                                color="primary",
                                outline=True,
                                className="me-2",
                            ),
                            width="auto",
                        ),
                        dbc.Col(
                            dbc.Button(
                                "Clear All",
                                id=f"{filter_id}-clear-all",
                                size="sm",
                                color="secondary",
                                outline=True,
                            ),
                            width="auto",
                        ),
                    ],
                    className="mb-2",
                    justify="start",
                )
            ]
        ),
        html.Hr(className="my-2"),
        html.Div(
            checkbox_items,
            className="form-check-group",
            style={"maxHeight": "200px", "overflowY": "auto"},
        ),
        html.Hr(className="my-2"),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Button(
                        "Apply",
                        id=f"{filter_id}-apply",
                        size="sm",
                        color="success",
                        className="me-2",
                    ),
                    width="auto",
                ),
                dbc.Col(
                    dbc.Button(
                        "Reset",
                        id=f"{filter_id}-reset",
                        size="sm",
                        color="warning",
                    ),
                    width="auto",
                ),
            ],
            justify="start",
        ),
    ]

    filter_component = html.Div(
        [
            html.Label(label, className="form-label mb-1") if label else None,
            dbc.DropdownMenu(
                children=dropdown_content,
                id=f"{filter_id}-dropdown",
                label=placeholder,
                color="light",
                size="sm",
                className="custom-filter-dropdown",
                style={"width": "200px"},
                direction="down",
                menu_variant="light",
            ),
            # Store to track selected values
            dcc.Store(id=f"{filter_id}-selected", data=[]),
            # Store to track if filter is active
            dcc.Store(id=f"{filter_id}-active", data=False),
        ]
    )

    return filter_component


def get_filter_options():
    """Get the predefined filter options for each table column."""
    return {
        "executions": {"status": ["PENDING", "RUNNING", "SUCCESS", "FAILED", "CANCELLED"]},
        "users": {"role": ["USER", "ADMIN", "SUPERADMIN"]},
        "scripts": {
            "access_control": ["unrestricted", "role_restricted", "user_restricted"],
            "status": ["UPLOADED", "PUBLISHED", "UNPUBLISHED", "FAILED"],
        },
    }


def create_table_filters(table_type):
    """Create all custom filters for a specific table type.

    Args:
        table_type: One of 'executions', 'users', 'scripts'

    Returns:
        List of filter components for the table
    """
    filters = []

    if table_type == "executions":
        # Only create status filter for executions
        filter_component = create_checkbox_filter(
            filter_id="executions-status-filter",
            options=["PENDING", "RUNNING", "SUCCESS", "FAILED", "CANCELLED"],
            placeholder="Filter status...",
            label="Status Filter",
        )
        filters.append(filter_component)
    elif table_type == "users":
        # Only create role filter for users
        filter_component = create_checkbox_filter(
            filter_id="users-role-filter",
            options=["USER", "ADMIN", "SUPERADMIN"],
            placeholder="Filter role...",
            label="Role Filter",
        )
        filters.append(filter_component)
    # Skip scripts for now to avoid complexity

    return filters


def register_filter_callbacks(app):
    """Register callbacks for all custom filters."""
    from dash import Input, Output, State, no_update

    # Register callbacks for executions status filter
    @app.callback(
        [
            Output("executions-status-filter-checkbox-PENDING", "value"),
            Output("executions-status-filter-checkbox-RUNNING", "value"),
            Output("executions-status-filter-checkbox-SUCCESS", "value"),
            Output("executions-status-filter-checkbox-FAILED", "value"),
            Output("executions-status-filter-checkbox-CANCELLED", "value"),
        ],
        Input("executions-status-filter-select-all", "n_clicks"),
        prevent_initial_call=True,
    )
    def executions_status_select_all(n_clicks):
        if n_clicks:
            return [True, True, True, True, True]
        return [no_update, no_update, no_update, no_update, no_update]

    @app.callback(
        [
            Output("executions-status-filter-checkbox-PENDING", "value", allow_duplicate=True),
            Output("executions-status-filter-checkbox-RUNNING", "value", allow_duplicate=True),
            Output("executions-status-filter-checkbox-SUCCESS", "value", allow_duplicate=True),
            Output("executions-status-filter-checkbox-FAILED", "value", allow_duplicate=True),
            Output("executions-status-filter-checkbox-CANCELLED", "value", allow_duplicate=True),
        ],
        Input("executions-status-filter-clear-all", "n_clicks"),
        prevent_initial_call=True,
    )
    def executions_status_clear_all(n_clicks):
        if n_clicks:
            return [False, False, False, False, False]
        return [no_update, no_update, no_update, no_update, no_update]

    @app.callback(
        [
            Output("executions-status-filter-selected", "data"),
            Output("executions-status-filter-active", "data"),
            Output("executions-status-filter-dropdown", "label"),
        ],
        Input("executions-status-filter-apply", "n_clicks"),
        [
            State("executions-status-filter-checkbox-PENDING", "value"),
            State("executions-status-filter-checkbox-RUNNING", "value"),
            State("executions-status-filter-checkbox-SUCCESS", "value"),
            State("executions-status-filter-checkbox-FAILED", "value"),
            State("executions-status-filter-checkbox-CANCELLED", "value"),
        ],
        prevent_initial_call=True,
    )
    def executions_status_apply(n_clicks, pending, running, success, failed, cancelled):
        if n_clicks:
            options = ["PENDING", "RUNNING", "SUCCESS", "FAILED", "CANCELLED"]
            checkbox_values = [pending, running, success, failed, cancelled]
            selected = [options[i] for i, checked in enumerate(checkbox_values) if checked]
            is_active = len(selected) > 0 and len(selected) < len(options)

            if len(selected) == 0:
                label = "Filter status..."
            elif len(selected) == len(options):
                label = "Filter status... (All)"
            else:
                label = f"Filter status... ({len(selected)} selected)"

            return selected, is_active, label
        return no_update, no_update, no_update

    @app.callback(
        [
            Output("executions-status-filter-checkbox-PENDING", "value", allow_duplicate=True),
            Output("executions-status-filter-checkbox-RUNNING", "value", allow_duplicate=True),
            Output("executions-status-filter-checkbox-SUCCESS", "value", allow_duplicate=True),
            Output("executions-status-filter-checkbox-FAILED", "value", allow_duplicate=True),
            Output("executions-status-filter-checkbox-CANCELLED", "value", allow_duplicate=True),
            Output("executions-status-filter-selected", "data", allow_duplicate=True),
            Output("executions-status-filter-active", "data", allow_duplicate=True),
            Output("executions-status-filter-dropdown", "label", allow_duplicate=True),
        ],
        Input("executions-status-filter-reset", "n_clicks"),
        prevent_initial_call=True,
    )
    def executions_status_reset(n_clicks):
        if n_clicks:
            return [False, False, False, False, False, [], False, "Filter status..."]
        return [
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
            no_update,
        ]

    # Register callbacks for users role filter
    @app.callback(
        [
            Output("users-role-filter-checkbox-USER", "value"),
            Output("users-role-filter-checkbox-ADMIN", "value"),
            Output("users-role-filter-checkbox-SUPERADMIN", "value"),
        ],
        Input("users-role-filter-select-all", "n_clicks"),
        prevent_initial_call=True,
    )
    def users_role_select_all(n_clicks):
        if n_clicks:
            return [True, True, True]
        return [no_update, no_update, no_update]

    @app.callback(
        [
            Output("users-role-filter-checkbox-USER", "value", allow_duplicate=True),
            Output("users-role-filter-checkbox-ADMIN", "value", allow_duplicate=True),
            Output("users-role-filter-checkbox-SUPERADMIN", "value", allow_duplicate=True),
        ],
        Input("users-role-filter-clear-all", "n_clicks"),
        prevent_initial_call=True,
    )
    def users_role_clear_all(n_clicks):
        if n_clicks:
            return [False, False, False]
        return [no_update, no_update, no_update]

    @app.callback(
        [
            Output("users-role-filter-selected", "data"),
            Output("users-role-filter-active", "data"),
            Output("users-role-filter-dropdown", "label"),
        ],
        Input("users-role-filter-apply", "n_clicks"),
        [
            State("users-role-filter-checkbox-USER", "value"),
            State("users-role-filter-checkbox-ADMIN", "value"),
            State("users-role-filter-checkbox-SUPERADMIN", "value"),
        ],
        prevent_initial_call=True,
    )
    def users_role_apply(n_clicks, user, admin, superadmin):
        if n_clicks:
            options = ["USER", "ADMIN", "SUPERADMIN"]
            checkbox_values = [user, admin, superadmin]
            selected = [options[i] for i, checked in enumerate(checkbox_values) if checked]
            is_active = len(selected) > 0 and len(selected) < len(options)

            if len(selected) == 0:
                label = "Filter role..."
            elif len(selected) == len(options):
                label = "Filter role... (All)"
            else:
                label = f"Filter role... ({len(selected)} selected)"

            return selected, is_active, label
        return no_update, no_update, no_update

    @app.callback(
        [
            Output("users-role-filter-checkbox-USER", "value", allow_duplicate=True),
            Output("users-role-filter-checkbox-ADMIN", "value", allow_duplicate=True),
            Output("users-role-filter-checkbox-SUPERADMIN", "value", allow_duplicate=True),
            Output("users-role-filter-selected", "data", allow_duplicate=True),
            Output("users-role-filter-active", "data", allow_duplicate=True),
            Output("users-role-filter-dropdown", "label", allow_duplicate=True),
        ],
        Input("users-role-filter-reset", "n_clicks"),
        prevent_initial_call=True,
    )
    def users_role_reset(n_clicks):
        if n_clicks:
            return [False, False, False, [], False, "Filter role..."]
        return [no_update, no_update, no_update, no_update, no_update, no_update]

    # For now, skip scripts filters to avoid complexity
    # TODO: Add scripts filters in a future iteration
