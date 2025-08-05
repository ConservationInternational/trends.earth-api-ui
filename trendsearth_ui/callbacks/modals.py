"""Modal callbacks for JSON display, logs, and downloads."""

from dash import ALL, Input, Output, State, html, no_update
import dash_bootstrap_components as dbc

from ..utils import parse_date, render_json_tree


def register_callbacks(app):
    @app.callback(
        Output("access-control-modal", "is_open", allow_duplicate=True),
        Output("access-control-script-data", "data", allow_duplicate=True),
        Output("access-control-script-name", "children", allow_duplicate=True),
        Output("access-control-status", "children", allow_duplicate=True),
        Output("access-control-type", "value", allow_duplicate=True),
        Output("access-control-roles", "value", allow_duplicate=True),
        Output("access-control-users", "value", allow_duplicate=True),
        Output("access-control-users", "options", allow_duplicate=True),
        Output("current-selected-users", "children", allow_duplicate=True),
        Output("access-control-roles-section", "style", allow_duplicate=True),
        Output("access-control-users-section", "style", allow_duplicate=True),
        Input("scripts-table", "cellClicked"),
        [
            State("token-store", "data"),
            State("access-control-modal", "is_open"),
            State("scripts-table-state", "data"),
        ],
        prevent_initial_call=True,
    )
    def show_access_control_modal(cell, token, is_open, table_state):
        """Show access control modal for script access control column clicks."""
        if not cell:
            return (
                is_open,
                no_update,
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

        col = cell.get("colId")
        if col != "access_control":
            return (
                is_open,
                no_update,
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

        row_data = cell.get("data")
        script_id = None
        script_name_from_row = None
        if row_data:
            script_id = row_data.get("id")
            script_name_from_row = row_data.get("name")

        if not script_id:
            row_index = cell.get("rowIndex")
            if row_index is None:
                return (
                    True,
                    None,
                    "Error",
                    "Could not get row index.",
                    "unrestricted",
                    [],
                    [],
                    [],
                    [],
                    {"display": "none"},
                    {"display": "none"},
                )
            try:
                from ..utils.helpers import make_authenticated_request

                page_size = 50
                page = (row_index // page_size) + 1
                row_in_page = row_index % page_size
                params = {"page": page, "per_page": page_size}
                if table_state:
                    if table_state.get("sort_sql"):
                        params["sort"] = table_state["sort_sql"]
                    if table_state.get("filter_sql"):
                        params["filter"] = table_state["filter_sql"]
                resp = make_authenticated_request("/script", token, params=params)
                if resp.status_code != 200:
                    return (
                        True,
                        None,
                        "Error",
                        f"Failed to fetch script data: {resp.status_code} - {resp.text}",
                        "unrestricted",
                        [],
                        [],
                        [],
                        [],
                        {"display": "none"},
                        {"display": "none"},
                    )
                result = resp.json()
                scripts = result.get("data", [])
                if row_in_page >= len(scripts):
                    return (
                        True,
                        None,
                        "Error",
                        f"Row index {row_in_page} out of range for page {page} (found {len(scripts)} scripts)",
                        "unrestricted",
                        [],
                        [],
                        [],
                        [],
                        {"display": "none"},
                        {"display": "none"},
                    )
                script = scripts[row_in_page]
                script_id = script.get("id")
                script_name_from_row = script.get("name")
            except Exception as e:
                return (
                    True,
                    None,
                    "Error",
                    f"Error fetching script data: {str(e)}",
                    "unrestricted",
                    [],
                    [],
                    [],
                    [],
                    {"display": "none"},
                    {"display": "none"},
                )

        if not script_id:
            return (
                True,
                None,
                "Error",
                "Could not get script ID.",
                "unrestricted",
                [],
                [],
                [],
                [],
                {"display": "none"},
                {"display": "none"},
            )

        try:
            from ..utils.helpers import make_authenticated_request

            # Get script data including access control information
            resp = make_authenticated_request(f"/script/{script_id}/access", token)
            if resp.status_code == 200:
                access_data = resp.json().get("data", {})
                script_name = script_name_from_row or access_data.get("script_name", "Script")

                # If we don't have script name from access data, try regular script endpoint
                if not script_name or script_name == "Script":
                    try:
                        script_resp = make_authenticated_request(f"/script/{script_id}", token)
                        if script_resp.status_code == 200:
                            script_data_resp = script_resp.json()
                            script_name = script_data_resp.get("name", "Script")
                    except Exception:
                        pass

                # Check if script has access restrictions
                restricted = access_data.get("restricted", False)
                allowed_roles = access_data.get("allowed_roles", [])
                allowed_users = access_data.get("allowed_users", [])

                if restricted:
                    status = "Restricted"
                    # Determine access type based on what restrictions are set
                    if allowed_roles and allowed_users:
                        # Both roles and users are set - use a new type for this
                        ac_type = "role_and_user_restricted"
                        roles = allowed_roles
                        users = allowed_users
                    elif allowed_roles:
                        ac_type = "role_restricted"
                        roles = allowed_roles
                        users = []
                    elif allowed_users:
                        ac_type = "user_restricted"
                        roles = []
                        users = allowed_users
                    else:
                        # Restricted but no specific restrictions - shouldn't happen but handle it
                        ac_type = "unrestricted"
                        roles = []
                        users = []
                else:
                    status = "Unrestricted"
                    ac_type = "unrestricted"
                    roles = []
                    users = []
            elif resp.status_code == 404:
                # 404 means no access control configured, so it's unrestricted
                # Get script name from regular script endpoint
                script_name = script_name_from_row if script_name_from_row else "Script"
                if not script_name_from_row:
                    try:
                        script_resp = make_authenticated_request(f"/script/{script_id}", token)
                        if script_resp.status_code == 200:
                            script_data_resp = script_resp.json()
                            script_name = script_data_resp.get("name", "Script")
                    except Exception:
                        pass
                status = "Unrestricted"
                ac_type = "unrestricted"
                roles = []
                users = []
            else:
                return (
                    True,
                    None,
                    "Error",
                    f"Failed to fetch script access data: {resp.status_code} - {resp.text}",
                    "unrestricted",
                    [],
                    [],
                    [],
                    [],
                    {"display": "none"},
                    {"display": "none"},
                )

            roles_section = (
                {"display": "block"}
                if ac_type in ["role_restricted", "role_and_user_restricted"]
                else {"display": "none"}
            )
            users_section = (
                {"display": "block"}
                if ac_type in ["user_restricted", "role_and_user_restricted"]
                else {"display": "none"}
            )
            # Users will be set as selected values in the dropdown, not as text
            users_selected = users if users else []

            # Create user options for the dropdown - need to fetch user details if we have user IDs
            users_options = []
            if users:
                try:
                    # Fetch user details using the same approach as user search
                    from ..utils.helpers import make_authenticated_request

                    # Get all users by querying with user IDs
                    all_user_data = {}
                    for user_id in users:
                        try:
                            # Use the same endpoint as search but filter by ID
                            user_resp = make_authenticated_request(
                                "/user",
                                token,
                                params={"per_page": 100, "filter": f"id='{user_id}'"},
                            )
                            if user_resp.status_code == 200:
                                user_data_resp = user_resp.json()
                                user_list = user_data_resp.get("data", [])
                                if user_list:
                                    user_data = user_list[0]  # Should be only one user
                                    user_name = user_data.get("name", "")
                                    user_email = user_data.get("email", "")

                                    if user_name and user_email:
                                        display_text = f"{user_name} ({user_email})"
                                    elif user_name:
                                        display_text = f"{user_name} (ID: {user_id})"
                                    elif user_email:
                                        display_text = f"{user_email} (ID: {user_id})"
                                    else:
                                        display_text = f"User ID: {user_id}"

                                    users_options.append({"label": display_text, "value": user_id})
                                    all_user_data[user_id] = user_data
                                else:
                                    # No user found, use fallback
                                    users_options.append(
                                        {"label": f"User ID: {user_id}", "value": user_id}
                                    )
                            else:
                                # API call failed, use fallback
                                users_options.append(
                                    {"label": f"User ID: {user_id}", "value": user_id}
                                )
                        except Exception as e:
                            print(f"Error fetching user {user_id}: {str(e)}")
                            # Fallback for this specific user
                            users_options.append({"label": f"User ID: {user_id}", "value": user_id})

                except Exception as e:
                    print(f"Error fetching user details: {str(e)}")
                    # Fallback if there's an error fetching user details
                    for user_id in users:
                        users_options.append({"label": f"User ID: {user_id}", "value": user_id})

            # Create current selected users display
            if users_options:
                selected_users_badges = []
                for user_option in users_options:
                    selected_users_badges.append(
                        dbc.Badge(
                            [
                                user_option["label"],
                                html.Span(
                                    " ×",
                                    className="ms-1",
                                    style={"cursor": "pointer", "fontWeight": "bold"},
                                    **{"data-user-id": user_option["value"]},
                                    id={
                                        "type": "remove-user-badge",
                                        "user_id": user_option["value"],
                                    },
                                ),
                            ],
                            color="secondary",
                            className="me-1 mb-1",
                            pill=True,
                        )
                    )
                current_users_display = selected_users_badges
            else:
                current_users_display = [
                    dbc.Alert(
                        "No users currently selected",
                        color="light",
                        className="mb-0 text-muted small",
                    )
                ]

            # Store script data including script_id for later use
            script_data = {"script_id": script_id, "script_name": script_name}

            return (
                True,
                script_data,
                script_name,
                status,
                ac_type,
                roles,
                users_selected,
                users_options,
                current_users_display,
                roles_section,
                users_section,
            )
        except Exception as e:
            return (
                True,
                None,
                "Error",
                f"Error fetching access control: {str(e)}",
                "unrestricted",
                [],
                [],
                [],
                [],
                {"display": "none"},
                {"display": "none"},
            )

    """Register modal-related callbacks."""

    @app.callback(
        Output("json-modal", "is_open", allow_duplicate=True),
        Output("json-modal-body", "children", allow_duplicate=True),
        Output("json-modal-data", "data", allow_duplicate=True),
        Output("json-modal-title", "children", allow_duplicate=True),
        Output("refresh-logs-btn", "style", allow_duplicate=True),
        Output("logs-refresh-interval", "disabled", allow_duplicate=True),
        Output("current-log-context", "data", allow_duplicate=True),
        Input("executions-table", "cellClicked"),
        [
            State("token-store", "data"),
            State("json-modal", "is_open"),
            State("executions-table-state", "data"),
            State("user-timezone-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def show_json_modal(cell, token, is_open, table_state, user_timezone):
        """Show JSON/logs modal for execution cell clicks."""
        if not cell:
            return is_open, no_update, no_update, no_update, no_update, no_update, no_update

        col = cell.get("colId")
        if col not in ("params", "results", "logs", "docker_logs"):
            return is_open, no_update, no_update, no_update, no_update, no_update, no_update

        # Try to get row data from cell click event first
        row_data = cell.get("data")
        execution_id = None

        if row_data:
            execution_id = row_data.get("id")
            # Add debug logging to understand when row_data is available
            print(f"DEBUG: Got execution_id {execution_id} from row_data for column {col}")

        # If we don't have execution_id from row data, fall back to pagination approach
        if not execution_id:
            print(f"DEBUG: No execution_id from row_data, falling back to pagination for column {col}")
            row_index = cell.get("rowIndex")
            if row_index is None:
                print(f"DEBUG: No row_index available in cell click event: {cell}")
                return (
                    True,
                    "Could not get row index from cell click event.",
                    None,
                    "Error",
                    {"display": "none"},
                    True,
                    None,
                )
            
            # Additional safety check for unreasonable row index values
            if row_index < 0 or row_index > 100000:  # Reasonable upper limit
                print(f"DEBUG: Unreasonable row_index value: {row_index}")
                return (
                    True,
                    f"Invalid row index: {row_index}. Please refresh the page and try again.",
                    None,
                    "Error",
                    {"display": "none"},
                    True,
                    None,
                )

            try:
                from ..utils.helpers import make_authenticated_request

                # Calculate which page this row is on
                page_size = 50  # This should match DEFAULT_PAGE_SIZE
                page = (row_index // page_size) + 1
                row_in_page = row_index % page_size

                # Use exclude=params,results for pagination since we'll fetch them separately
                params = {
                    "page": page,
                    "per_page": page_size,
                    "exclude": "params,results",
                    "include": "script_name,user_name,user_email,user_id,duration",
                }

                # Apply the same sort and filter that the table is currently using
                if table_state:
                    if table_state.get("sort_sql"):
                        params["sort"] = table_state["sort_sql"]
                    if table_state.get("filter_sql"):
                        params["filter"] = table_state["filter_sql"]

                print(f"DEBUG: Fallback pagination request for row_index {row_index}, page {page}, row_in_page {row_in_page}")
                resp = make_authenticated_request("/execution", token, params=params)
                if resp.status_code != 200:
                    return (
                        True,
                        f"Failed to fetch execution data: {resp.status_code} - {resp.text}",
                        None,
                        "Error",
                        {"display": "none"},
                        True,
                        None,
                    )

                result = resp.json()
                executions = result.get("data", [])

                if row_in_page >= len(executions):
                    return (
                        True,
                        f"Row index {row_in_page} out of range for page {page} (found {len(executions)} executions)",
                        None,
                        "Error",
                        {"display": "none"},
                        True,
                        None,
                    )

                execution_data = executions[row_in_page]
                execution_id = execution_data.get("id")
                
                # Add verification logging
                print(f"DEBUG: Found execution_id {execution_id} at row_index {row_index}, page {page}, row_in_page {row_in_page}")
                print(f"DEBUG: Execution data: script_name={execution_data.get('script_name')}, status={execution_data.get('status')}")

            except Exception as e:
                print(f"DEBUG: Exception in pagination fallback: {str(e)}")
                return (
                    True,
                    f"Error fetching execution data: {str(e)}",
                    None,
                    "Error",
                    {"display": "none"},
                    True,
                    None,
                )

        if not execution_id:
            print(f"DEBUG: Final check - no execution_id available for column {col}")
            return (
                True,
                "Could not get execution ID from row or pagination data.",
                None,
                "Error",
                {"display": "none"},
                True,
                None,
            )
        
        print(f"DEBUG: Proceeding to fetch {col} data for execution_id {execution_id}")
        
        # Verify the execution exists before fetching logs to prevent wrong execution issues
        try:
            from ..utils.helpers import make_authenticated_request
            
            verification_resp = make_authenticated_request(f"/execution/{execution_id}", token, params={"include": "id,script_name,status"})
            if verification_resp.status_code == 404:
                print(f"DEBUG: Execution {execution_id} not found - may be invalid ID")
                return (
                    True,
                    f"Execution {execution_id} not found. This may indicate a data synchronization issue.",
                    None,
                    "Error",
                    {"display": "none"},
                    True,
                    None,
                )
            elif verification_resp.status_code == 200:
                verification_data = verification_resp.json()
                # Handle API response structure
                if isinstance(verification_data, dict) and "data" in verification_data:
                    exec_info = verification_data["data"]
                else:
                    exec_info = verification_data
                print(f"DEBUG: Verified execution {execution_id}: script={exec_info.get('script_name')}, status={exec_info.get('status')}")
            else:
                print(f"DEBUG: Unexpected verification response: {verification_resp.status_code}")
        except Exception as e:
            print(f"DEBUG: Error verifying execution {execution_id}: {str(e)}")
            # Continue anyway, as verification failure shouldn't block the logs

        try:
            from ..utils.helpers import make_authenticated_request

            if col == "params":
                # Always fetch params from the individual execution endpoint
                resp = make_authenticated_request(
                    f"/execution/{execution_id}",
                    token,
                    params={"include": "params"},
                )
                if resp.status_code != 200:
                    return (
                        True,
                        f"Failed to fetch execution data: {resp.status_code} - {resp.text}",
                        None,
                        "Error",
                        {"display": "none"},
                        True,
                        None,
                    )
                execution = resp.json()
                # Handle API response structure - check if data is wrapped in a 'data' field
                if (
                    isinstance(execution, dict)
                    and "data" in execution
                    and execution.get("data") is not None
                ):
                    execution_data = execution["data"]
                else:
                    execution_data = execution
                params = execution_data.get("params", {})

                if not params:
                    return (
                        True,
                        html.P("No parameters found for this execution."),
                        {},
                        f"Execution {execution_id} - Parameters",
                        {"display": "none"},
                        True,
                        None,
                    )

                return (
                    True,
                    render_json_tree(params),
                    params,
                    f"Execution {execution_id} - Parameters",
                    {"display": "none"},
                    True,
                    None,
                )

            elif col == "results":
                # Always fetch results from the individual execution endpoint
                resp = make_authenticated_request(
                    f"/execution/{execution_id}",
                    token,
                    params={"include": "results"},
                )
                if resp.status_code != 200:
                    return (
                        True,
                        f"Failed to fetch execution data: {resp.status_code} - {resp.text}",
                        None,
                        "Error",
                        {"display": "none"},
                        True,
                        None,
                    )
                execution = resp.json()
                # Handle API response structure - check if data is wrapped in a 'data' field
                if (
                    isinstance(execution, dict)
                    and "data" in execution
                    and execution.get("data") is not None
                ):
                    execution_data = execution["data"]
                else:
                    execution_data = execution
                results = execution_data.get("results", {})

                if not results:
                    return (
                        True,
                        html.P("No results found for this execution."),
                        {},
                        f"Execution {execution_id} - Results",
                        {"display": "none"},
                        True,
                        None,
                    )

                return (
                    True,
                    render_json_tree(results),
                    results,
                    f"Execution {execution_id} - Results",
                    {"display": "none"},
                    True,
                    None,
                )

            elif col == "logs":
                from ..utils.helpers import make_authenticated_request

                # Get execution status from row data for auto-refresh control
                execution_status = None
                if row_data:
                    execution_status = row_data.get("status")

                # For logs, try the execution-specific endpoint first
                print(f"DEBUG: Fetching logs for execution {execution_id}")
                resp = make_authenticated_request(f"/execution/{execution_id}/log", token)

                if resp.status_code != 200:
                    # Fall back to general log endpoint with execution_id parameter
                    resp = make_authenticated_request(
                        "/log",
                        token,
                        params={
                            "execution_id": execution_id,
                            "per_page": 50,
                            "sort": "register_date",
                        },
                    )

                    if resp.status_code != 200:
                        return (
                            True,
                            f"Failed to fetch logs: {resp.status_code} - {resp.text}",
                            None,
                            f"Execution {execution_id} - Logs",
                            {"display": "none"},
                            True,
                            {
                                "execution_id": execution_id,
                                "type": "execution",
                                "id": execution_id,
                                "status": execution_status,
                                "user_timezone": user_timezone,
                            },
                        )

                result = resp.json()
                logs = result.get("data", [])

                if not logs:
                    log_content = html.P("No logs found for this execution.")
                else:
                    # Parse and format logs the same way as script logs
                    if isinstance(logs, list):
                        parsed_logs = []
                        for log in logs:
                            if isinstance(log, dict):
                                register_date = log.get("register_date", "")
                                level = log.get("level", "INFO")
                                text = log.get("text", "")

                                # Parse and format the date
                                formatted_date = (
                                    parse_date(register_date, user_timezone) or register_date
                                )

                                # Create formatted log line
                                log_line = f"{formatted_date} - {level} - {text}"
                                parsed_logs.append((register_date, log_line))
                            else:
                                # Fallback for non-dict log entries
                                parsed_logs.append(("", str(log)))

                        # Sort by register_date in descending order
                        parsed_logs.sort(key=lambda x: x[0], reverse=True)
                        logs_content = "\n".join([log_line for _, log_line in parsed_logs])
                        log_content = html.Pre(
                            logs_content,
                            style={
                                "whiteSpace": "pre-wrap",
                                "fontSize": "12px",
                                "fontFamily": "monospace",
                            },
                        )
                    else:
                        log_content = html.Pre(
                            str(logs),
                            style={
                                "whiteSpace": "pre-wrap",
                                "fontSize": "12px",
                                "fontFamily": "monospace",
                            },
                        )

                return (
                    True,
                    log_content,
                    None,
                    f"Execution {execution_id} - Logs",
                    {"display": "inline-block"},
                    False,
                    {
                        "execution_id": execution_id,
                        "type": "execution",
                        "log_type": "regular",
                        "id": execution_id,
                        "status": execution_status,
                        "user_timezone": user_timezone,
                    },
                )

            elif col == "docker_logs":
                from ..utils.helpers import make_authenticated_request

                # Get execution status from row data for auto-refresh control
                execution_status = None
                if row_data:
                    execution_status = row_data.get("status")

                try:
                    # For docker logs, use the specific docker logs endpoint with longer timeout
                    print(f"Fetching docker logs for execution {execution_id}")
                    resp = make_authenticated_request(
                        f"/execution/{execution_id}/docker-logs",
                        token,
                        timeout=30,  # 30 second timeout for docker logs
                    )
                    print(f"Docker logs API response: {resp.status_code}")

                    if resp.status_code == 403:
                        return (
                            True,
                            html.P(
                                "Access denied. Docker logs are only available to admin and superadmin users."
                            ),
                            None,
                            f"Execution {execution_id} - Docker Logs",
                            {"display": "none"},
                            True,
                            {
                                "execution_id": execution_id,
                                "type": "execution",
                                "id": execution_id,
                                "status": execution_status,
                                "user_timezone": user_timezone,
                            },
                        )
                    elif resp.status_code == 404:
                        return (
                            True,
                            html.P(
                                "Docker logs not found for this execution. The execution may not have docker logs available."
                            ),
                            None,
                            f"Execution {execution_id} - Docker Logs",
                            {"display": "none"},
                            True,
                            {
                                "execution_id": execution_id,
                                "type": "execution",
                                "id": execution_id,
                                "status": execution_status,
                                "user_timezone": user_timezone,
                            },
                        )
                    elif resp.status_code != 200:
                        error_text = f"HTTP {resp.status_code}"
                        try:
                            error_detail = resp.text[:200]  # Limit error text length
                            if error_detail:
                                error_text += f": {error_detail}"
                        except Exception:
                            pass
                        return (
                            True,
                            f"Failed to fetch docker logs: {error_text}",
                            None,
                            f"Execution {execution_id} - Docker Logs",
                            {"display": "none"},
                            True,
                            {
                                "execution_id": execution_id,
                                "type": "execution",
                                "id": execution_id,
                                "status": execution_status,
                                "user_timezone": user_timezone,
                            },
                        )

                except Exception as e:
                    print(f"Exception while fetching docker logs: {str(e)}")
                    return (
                        True,
                        f"Error fetching docker logs: {str(e)}",
                        None,
                        f"Execution {execution_id} - Docker Logs",
                        {"display": "none"},
                        True,
                        {
                            "execution_id": execution_id,
                            "type": "execution",
                            "id": execution_id,
                            "status": execution_status,
                            "user_timezone": user_timezone,
                        },
                    )

                result = resp.json()
                docker_logs = result.get("data", [])

                if not docker_logs:
                    log_content = html.P("No docker logs found for this execution.")
                else:
                    # Parse and format docker logs using the same format as regular logs
                    if isinstance(docker_logs, list):
                        parsed_logs = []
                        for log in docker_logs:
                            if isinstance(log, dict):
                                created_at = log.get("created_at", "")
                                text = log.get("text", "")

                                # Parse and format the date
                                formatted_date = parse_date(created_at, user_timezone) or created_at

                                # Create formatted log line
                                log_line = f"{formatted_date} - {text}"
                                parsed_logs.append((created_at, log_line))
                            else:
                                # Fallback for non-dict log entries
                                parsed_logs.append(("", str(log)))

                        # Sort by created_at in descending order
                        parsed_logs.sort(key=lambda x: x[0], reverse=True)
                        logs_content = "\n".join([log_line for _, log_line in parsed_logs])
                        log_content = html.Pre(
                            logs_content,
                            style={
                                "whiteSpace": "pre-wrap",
                                "fontSize": "12px",
                                "fontFamily": "monospace",
                            },
                        )
                    else:
                        log_content = html.Pre(
                            str(docker_logs),
                            style={
                                "whiteSpace": "pre-wrap",
                                "fontSize": "12px",
                                "fontFamily": "monospace",
                            },
                        )

                return (
                    True,
                    log_content,
                    None,
                    f"Execution {execution_id} - Docker Logs",
                    {"display": "inline-block"},
                    False,
                    {
                        "execution_id": execution_id,
                        "type": "execution",
                        "log_type": "docker",
                        "id": execution_id,
                        "status": execution_status,
                        "user_timezone": user_timezone,
                    },
                )

        except Exception as e:
            return (
                True,
                f"Error processing {col} data: {str(e)}",
                None,
                "Error",
                {"display": "none"},
                True,
                None,
            )

    @app.callback(
        Output("json-modal-body", "children", allow_duplicate=True),
        Input("refresh-logs-btn", "n_clicks"),
        [State("current-log-context", "data"), State("token-store", "data")],
        prevent_initial_call=True,
    )
    def refresh_logs_content(n_clicks, log_context, token):
        """Refresh logs content in modal."""
        if not n_clicks or not log_context or not token:
            return no_update

        execution_id = log_context.get("execution_id")
        log_type = log_context.get("log_type", "regular")
        if not execution_id:
            return html.P("No execution context available")

        try:
            from ..utils.helpers import make_authenticated_request

            # Use different endpoints based on log type
            if log_type == "docker":
                resp = make_authenticated_request(f"/execution/{execution_id}/docker-logs", token)
            else:
                resp = make_authenticated_request(f"/execution/{execution_id}/log", token)

            if resp.status_code != 200:
                log_type_name = "docker logs" if log_type == "docker" else "logs"
                return html.P(f"Failed to fetch {log_type_name}: {resp.status_code}")

            logs_data = resp.json()
            logs = logs_data.get("data", [])

            if not logs:
                log_type_name = "docker logs" if log_type == "docker" else "logs"
                return html.P(f"No {log_type_name} available")

            # Format logs based on type
            if log_type == "docker":
                # Docker logs format: created_at and text (same format as main docker logs display)
                if isinstance(logs, list):
                    parsed_logs = []
                    for log in logs:
                        if isinstance(log, dict):
                            created_at = log.get("created_at", "")
                            text = log.get("text", "")

                            # Parse and format the date
                            from ..utils import parse_date

                            formatted_date = (
                                parse_date(created_at, log_context.get("user_timezone"))
                                or created_at
                            )

                            # Create formatted log line
                            log_line = f"{formatted_date} - {text}"
                            parsed_logs.append((created_at, log_line))
                        else:
                            # Fallback for non-dict log entries
                            parsed_logs.append(("", str(log)))

                    # Sort by created_at in descending order
                    parsed_logs.sort(key=lambda x: x[0], reverse=True)
                    logs_content = "\n".join([log_line for _, log_line in parsed_logs])
                    log_content = html.Pre(
                        logs_content,
                        style={
                            "whiteSpace": "pre-wrap",
                            "fontSize": "12px",
                            "fontFamily": "monospace",
                        },
                    )
                else:
                    log_content = html.Pre(
                        str(logs),
                        style={
                            "whiteSpace": "pre-wrap",
                            "fontSize": "12px",
                            "fontFamily": "monospace",
                        },
                    )
            else:
                # Regular logs format: register_date, level, text (same format as main logs display)
                if isinstance(logs, list):
                    parsed_logs = []
                    for log in logs:
                        if isinstance(log, dict):
                            register_date = log.get("register_date", "")
                            level = log.get("level", "INFO")
                            text = log.get("text", "")

                            # Parse and format the date
                            from ..utils import parse_date

                            formatted_date = (
                                parse_date(register_date, log_context.get("user_timezone"))
                                or register_date
                            )

                            # Create formatted log line
                            log_line = f"{formatted_date} - {level} - {text}"
                            parsed_logs.append((register_date, log_line))
                        else:
                            # Fallback for non-dict log entries
                            parsed_logs.append(("", str(log)))

                    # Sort by register_date in descending order
                    parsed_logs.sort(key=lambda x: x[0], reverse=True)
                    logs_content = "\n".join([log_line for _, log_line in parsed_logs])
                    log_content = html.Pre(
                        logs_content,
                        style={
                            "whiteSpace": "pre-wrap",
                            "fontSize": "12px",
                            "fontFamily": "monospace",
                        },
                    )
                else:
                    log_content = html.Pre(
                        str(logs),
                        style={
                            "whiteSpace": "pre-wrap",
                            "fontSize": "12px",
                            "fontFamily": "monospace",
                        },
                    )

            return log_content

        except Exception as e:
            return html.P(f"Error fetching logs: {str(e)}")

    @app.callback(
        Output("download-json", "data"),
        Input("download-json-btn", "n_clicks"),
        State("json-modal-data", "data"),
        prevent_initial_call=True,
    )
    def download_json(n, json_data):
        """Download JSON data as file."""
        if n and json_data is not None:
            try:
                import json

                json_str = json.dumps(json_data, indent=2)
            except Exception:
                json_str = str(json_data)
            return {"content": json_str, "filename": "data.json"}
        return no_update

    @app.callback(
        Output("json-modal", "is_open", allow_duplicate=True),
        Output("json-modal-body", "children", allow_duplicate=True),
        Output("json-modal-data", "data", allow_duplicate=True),
        Output("json-modal-title", "children", allow_duplicate=True),
        Output("refresh-logs-btn", "style", allow_duplicate=True),
        Output("logs-refresh-interval", "disabled", allow_duplicate=True),
        Output("current-log-context", "data", allow_duplicate=True),
        Input("scripts-table", "cellClicked"),
        [
            State("token-store", "data"),
            State("json-modal", "is_open"),
            State("scripts-table-state", "data"),
            State("user-timezone-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def show_script_logs_modal(cell, token, is_open, table_state, user_timezone):
        """Show script logs modal using rowIndex and backend pagination (like executions)."""
        if not cell:
            return is_open, no_update, no_update, no_update, no_update, no_update, no_update

        col = cell.get("colId")
        if col != "logs":
            return is_open, no_update, no_update, no_update, no_update, no_update, no_update

        # Try to get row data from cell click event first
        row_data = cell.get("data")
        script_id = None

        if row_data:
            script_id = row_data.get("id")
            # Add debug logging to understand when row_data is available
            print(f"DEBUG: Got script_id {script_id} from row_data for logs")

        # If we don't have row data or script_id, fall back to pagination approach
        if not script_id:
            print(f"DEBUG: No script_id from row_data, falling back to pagination for script logs")
            row_index = cell.get("rowIndex")
            if row_index is None:
                print(f"DEBUG: No row_index available in script logs cell click event: {cell}")
                return (
                    True,
                    "Could not get row index.",
                    None,
                    "Error",
                    {"display": "none"},
                    True,
                    None,
                )
            
            # Additional safety check for unreasonable row index values
            if row_index < 0 or row_index > 100000:  # Reasonable upper limit
                print(f"DEBUG: Unreasonable row_index value in scripts: {row_index}")
                return (
                    True,
                    f"Invalid row index: {row_index}. Please refresh the page and try again.",
                    None,
                    "Error",
                    {"display": "none"},
                    True,
                    None,
                )

            try:
                from ..utils.helpers import make_authenticated_request

                # Calculate which page this row is on
                page_size = 50  # This should match DEFAULT_PAGE_SIZE
                page = (row_index // page_size) + 1
                row_in_page = row_index % page_size

                params = {"page": page, "per_page": page_size, "include": "user_name"}

                # Apply the same sort and filter that the table is currently using
                if table_state:
                    if table_state.get("sort_sql"):
                        params["sort"] = table_state["sort_sql"]
                    if table_state.get("filter_sql"):
                        params["filter"] = table_state["filter_sql"]

                print(f"DEBUG: Script logs fallback pagination request for row_index {row_index}, page {page}, row_in_page {row_in_page}")
                resp = make_authenticated_request("/script", token, params=params)
                if resp.status_code != 200:
                    return (
                        True,
                        f"Failed to fetch script data: {resp.status_code} - {resp.text}",
                        None,
                        "Error",
                        {"display": "none"},
                        True,
                        None,
                    )

                result = resp.json()
                scripts = result.get("data", [])
                if row_in_page >= len(scripts):
                    return (
                        True,
                        f"Row index {row_in_page} out of range for page {page} (found {len(scripts)} scripts)",
                        None,
                        "Error",
                        {"display": "none"},
                        True,
                        None,
                    )

                script = scripts[row_in_page]
                script_id = script.get("id")
                
                # Add verification logging
                print(f"DEBUG: Found script_id {script_id} at row_index {row_index}, page {page}, row_in_page {row_in_page}")
                print(f"DEBUG: Script data: name={script.get('name')}, user_name={script.get('user_name')}")

            except Exception as e:
                print(f"DEBUG: Exception in script pagination fallback: {str(e)}")
                return (
                    True,
                    f"Error fetching script data: {str(e)}",
                    None,
                    "Error",
                    {"display": "none"},
                    True,
                    None,
                )

        if not script_id:
            print(f"DEBUG: Final check - no script_id available for script logs")
            return True, "Could not get script ID.", None, "Error", {"display": "none"}, True, None

        print(f"DEBUG: Proceeding to fetch script logs for script_id {script_id}")

        try:
            from ..utils.helpers import make_authenticated_request

            # Get the logs for this script with automatic token refresh
            print(f"DEBUG: Fetching logs for script {script_id}")
            resp = make_authenticated_request(f"/script/{script_id}/log", token)

            if resp.status_code != 200:
                return (
                    True,
                    f"Failed to fetch script logs: {resp.status_code} - {resp.text}",
                    None,
                    "Script Logs",
                    {"display": "none"},
                    True,
                    None,
                )
            logs_data = resp.json().get("data", [])
            if not logs_data:
                return (
                    True,
                    "No logs found for this script.",
                    None,
                    "Script Logs",
                    {"display": "none"},
                    True,
                    None,
                )
            # Parse and format logs for display (same as execution logs)
            if isinstance(logs_data, list):
                parsed_logs = []
                for log in logs_data:
                    if isinstance(log, dict):
                        register_date = log.get("register_date", "")
                        level = log.get("level", "")
                        text = log.get("text", "")

                        # Parse and format the date
                        formatted_date = parse_date(register_date, user_timezone) or register_date

                        # Create formatted log line
                        log_line = f"{formatted_date} - {level} - {text}"
                        parsed_logs.append((register_date, log_line))
                    else:
                        # Fallback for non-dict log entries
                        parsed_logs.append(("", str(log)))

                # Sort by register_date in descending order
                parsed_logs.sort(key=lambda x: x[0], reverse=True)
                logs_content = "\n".join([log_line for _, log_line in parsed_logs])
                logs_display = html.Pre(
                    logs_content, style={"whiteSpace": "pre-wrap", "fontSize": "12px"}
                )
            else:
                logs_display = html.Pre(
                    str(logs_data), style={"whiteSpace": "pre-wrap", "fontSize": "12px"}
                )
            return (
                True,
                logs_display,
                logs_data,
                "Script Logs",
                {"display": "inline-block"},
                False,
                {"type": "script", "id": script_id, "status": "UNKNOWN"},
            )

        except Exception as e:
            return (
                True,
                f"Error processing script logs: {str(e)}",
                None,
                "Error",
                {"display": "none"},
                True,
                None,
            )

    @app.callback(
        Output("access-control-users", "options", allow_duplicate=True),
        Output("user-search-loading", "style", allow_duplicate=True),
        [
            Input("user-search-btn", "n_clicks"),
            Input("user-search-input", "n_submit"),
        ],
        [
            State("user-search-input", "value"),
            State("token-store", "data"),
        ],
        prevent_initial_call=True,
    )
    def search_users(_search_clicks, _input_submit, search_term, token):
        """Search for users by name or email (triggered by button click or Enter key)."""
        from dash import ctx

        # Check if either button was clicked or Enter was pressed
        if not ctx.triggered or not search_term or not token:
            return [], {"display": "none"}

        try:
            from ..utils.helpers import make_authenticated_request

            # Search by name (filter like)
            name_results = []
            try:
                name_resp = make_authenticated_request(
                    "/user",
                    token,
                    params={"per_page": 100, "filter": f"name like '%{search_term}%'"},
                )
                if name_resp.status_code == 200:
                    name_data = name_resp.json()
                    name_results = name_data.get("data", [])
            except Exception as e:
                print(f"Error searching by name: {str(e)}")

            # Search by email (filter like)
            email_results = []
            try:
                email_resp = make_authenticated_request(
                    "/user",
                    token,
                    params={"per_page": 100, "filter": f"email like '%{search_term}%'"},
                )
                if email_resp.status_code == 200:
                    email_data = email_resp.json()
                    email_results = email_data.get("data", [])
            except Exception as e:
                print(f"Error searching by email: {str(e)}")

            # Merge results and remove duplicates
            all_users = {}
            for user in name_results + email_results:
                user_id = user.get("id")
                if user_id:
                    all_users[user_id] = user

            # Create dropdown options
            options = []
            for user in all_users.values():
                user_id = user.get("id")
                name = user.get("name", "")
                email = user.get("email", "")

                if user_id:
                    if name and email:
                        label = f"{name} ({email})"
                    elif name:
                        label = f"{name} (ID: {user_id})"
                    elif email:
                        label = f"{email} (ID: {user_id})"
                    else:
                        label = f"User ID: {user_id}"

                    options.append({"label": label, "value": user_id})

            # Sort options by label for better UX
            options.sort(key=lambda x: x["label"])

            return options, {"display": "none"}

        except Exception as e:
            print(f"Error searching users: {str(e)}")
            return [], {"display": "none"}

    @app.callback(
        Output("user-search-input", "value", allow_duplicate=True),
        [
            Input("access-control-modal", "is_open"),
            Input("access-control-type", "value"),
        ],
        prevent_initial_call=True,
    )
    def clear_user_search_on_modal_change(_is_open, _access_type):
        """Clear user search input when modal opens or access type changes."""
        # Only clear the search input, preserve the user options and selections
        return ""

    # Legacy callback decorators for backward compatibility (these won't be executed)

    @app.callback(
        Output("access-control-roles-section", "style", allow_duplicate=True),
        Output("access-control-users-section", "style", allow_duplicate=True),
        Input("access-control-type", "value"),
        prevent_initial_call=True,
    )
    def update_access_control_sections(access_type):
        """Show/hide role and user sections based on access control type."""
        roles_style = (
            {"display": "block"}
            if access_type in ["role_restricted", "role_and_user_restricted"]
            else {"display": "none"}
        )
        users_style = (
            {"display": "block"}
            if access_type in ["user_restricted", "role_and_user_restricted"]
            else {"display": "none"}
        )
        return roles_style, users_style

    @app.callback(
        Output("access-control-modal", "is_open", allow_duplicate=True),
        Output("access-control-alert", "is_open", allow_duplicate=True),
        Output("access-control-alert", "children", allow_duplicate=True),
        Output("access-control-alert", "color", allow_duplicate=True),
        Output("refresh-scripts-btn", "n_clicks", allow_duplicate=True),
        Input("save-access-control", "n_clicks"),
        Input("cancel-access-control", "n_clicks"),
        [
            State("access-control-script-data", "data"),
            State("access-control-type", "value"),
            State("access-control-roles", "value"),
            State("access-control-users", "value"),
            State("token-store", "data"),
            State("access-control-modal", "is_open"),
            State("refresh-scripts-btn", "n_clicks"),
        ],
        prevent_initial_call=True,
    )
    def handle_access_control_save_cancel(
        save_clicks,
        _cancel_clicks,
        script_data,
        access_type,
        roles,
        users,
        token,
        _is_open,
        current_refresh_clicks,
    ):
        """Handle save and cancel actions for access control modal."""
        from dash import ctx, no_update

        if not ctx.triggered:
            return no_update, no_update, no_update, no_update, no_update

        button_id = ctx.triggered[0]["prop_id"].split(".")[0]

        if button_id == "cancel-access-control":
            return False, False, "", "info", no_update

        if button_id == "save-access-control" and save_clicks:
            if not script_data or not script_data.get("script_id"):
                return no_update, True, "Error: No script data available", "danger", no_update

            try:
                from ..utils.helpers import make_authenticated_request

                script_id = script_data["script_id"]

                # Use the correct endpoints and data format based on the API structure
                if access_type == "unrestricted":
                    # Clear all restrictions by calling the DELETE endpoint
                    resp = make_authenticated_request(
                        f"/script/{script_id}/access", token, method="DELETE"
                    )
                elif access_type == "role_restricted":
                    # Set roles using the roles endpoint, clear users
                    roles_data = {"roles": roles or []}
                    resp = make_authenticated_request(
                        f"/script/{script_id}/access/roles", token, method="PUT", json=roles_data
                    )
                    # Also clear users to ensure only roles are set
                    if resp.status_code == 200:
                        users_data = {"users": []}
                        make_authenticated_request(
                            f"/script/{script_id}/access/users",
                            token,
                            method="PUT",
                            json=users_data,
                        )
                elif access_type == "user_restricted":
                    # Set users using the users endpoint, clear roles
                    users_data = {"users": users or []}
                    resp = make_authenticated_request(
                        f"/script/{script_id}/access/users", token, method="PUT", json=users_data
                    )
                    # Also clear roles to ensure only users are set
                    if resp.status_code == 200:
                        roles_data = {"roles": []}
                        make_authenticated_request(
                            f"/script/{script_id}/access/roles",
                            token,
                            method="PUT",
                            json=roles_data,
                        )
                elif access_type == "role_and_user_restricted":
                    # Set both roles and users
                    roles_data = {"roles": roles or []}
                    users_data = {"users": users or []}

                    # Make both API calls
                    roles_resp = make_authenticated_request(
                        f"/script/{script_id}/access/roles", token, method="PUT", json=roles_data
                    )
                    users_resp = make_authenticated_request(
                        f"/script/{script_id}/access/users", token, method="PUT", json=users_data
                    )

                    # Consider it successful if both calls succeed
                    if roles_resp.status_code == 200 and users_resp.status_code == 200:
                        resp = roles_resp  # Use roles response for success handling
                    else:
                        # If either failed, use the failed response
                        resp = roles_resp if roles_resp.status_code != 200 else users_resp
                else:
                    # Default fallback - clear restrictions
                    resp = make_authenticated_request(
                        f"/script/{script_id}/access", token, method="DELETE"
                    )

                if resp.status_code in [200, 201]:
                    # Trigger table refresh by incrementing the refresh button clicks
                    refresh_clicks = (current_refresh_clicks or 0) + 1
                    action = "updated" if resp.status_code == 200 else "created"
                    return (
                        False,
                        True,
                        f"Access control settings {action} successfully!",
                        "success",
                        refresh_clicks,
                    )
                else:
                    return (
                        no_update,
                        True,
                        f"Failed to update access control: {resp.status_code} - {resp.text}",
                        "danger",
                        no_update,
                    )

            except Exception as e:
                return (
                    no_update,
                    True,
                    f"Error updating access control: {str(e)}",
                    "danger",
                    no_update,
                )

        return no_update, no_update, no_update, no_update, no_update

    @app.callback(
        Output("access-control-modal", "is_open", allow_duplicate=True),
        Output("access-control-alert", "is_open", allow_duplicate=True),
        Output("access-control-alert", "children", allow_duplicate=True),
        Output("access-control-alert", "color", allow_duplicate=True),
        Output("access-control-type", "value", allow_duplicate=True),
        Output("access-control-roles", "value", allow_duplicate=True),
        Output("access-control-users", "value", allow_duplicate=True),
        Output("refresh-scripts-btn", "n_clicks", allow_duplicate=True),
        Input("clear-access-restrictions", "n_clicks"),
        [
            State("access-control-script-data", "data"),
            State("token-store", "data"),
            State("access-control-modal", "is_open"),
            State("refresh-scripts-btn", "n_clicks"),
        ],
        prevent_initial_call=True,
    )
    def handle_clear_access_restrictions(
        clear_clicks, script_data, token, _is_open, current_refresh_clicks
    ):
        """Handle clearing all access restrictions."""
        if not clear_clicks:
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
            )

        if not script_data or not script_data.get("script_id"):
            return (
                no_update,
                True,
                "Error: No script data available",
                "danger",
                no_update,
                no_update,
                no_update,
                no_update,
            )

        try:
            from ..utils.helpers import make_authenticated_request

            script_id = script_data["script_id"]

            # Make the API request to delete access control restrictions using correct endpoint
            resp = make_authenticated_request(f"/script/{script_id}/access", token, method="DELETE")

            if resp.status_code == 200:
                # Trigger table refresh by incrementing the refresh button clicks
                refresh_clicks = (current_refresh_clicks or 0) + 1
                return (
                    no_update,
                    True,
                    "All access restrictions cleared successfully!",
                    "success",
                    "unrestricted",
                    [],
                    [],
                    refresh_clicks,
                )
            else:
                return (
                    no_update,
                    True,
                    f"Failed to clear restrictions: {resp.status_code} - {resp.text}",
                    "danger",
                    no_update,
                    no_update,
                    no_update,
                    no_update,
                )

        except Exception as e:
            return (
                no_update,
                True,
                f"Error clearing restrictions: {str(e)}",
                "danger",
                no_update,
                no_update,
                no_update,
                no_update,
            )

    @app.callback(
        Output("access-control-modal", "is_open", allow_duplicate=True),
        Input("open-access-control", "n_clicks"),
        State("edit-script-modal", "is_open"),
        prevent_initial_call=True,
    )
    def open_access_control_from_edit_modal(open_clicks, edit_modal_open):
        """Open access control modal from the edit script modal."""
        if not open_clicks or not edit_modal_open:
            return no_update
        return True

    # Clientside callback to provide visual feedback for search completion
    app.clientside_callback(
        """
        function(options) {
            // Simple feedback - just console log for now to avoid errors
            if (options && options.length > 0) {
                console.log('Search completed with', options.length, 'results');
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("user-search-btn", "style", allow_duplicate=True),
        Input("access-control-users", "options"),
        prevent_initial_call=True,
    )

    @app.callback(
        [
            Output("access-control-users", "value", allow_duplicate=True),
            Output("access-control-users", "options", allow_duplicate=True),
            Output("current-selected-users", "children", allow_duplicate=True),
        ],
        Input({"type": "remove-user-badge", "user_id": ALL}, "n_clicks"),
        [
            State("access-control-users", "value"),
            State("access-control-users", "options"),
        ],
        prevent_initial_call=True,
    )
    def remove_user_from_selection(n_clicks_list, current_users, current_options):
        """Remove a user from the selected users list when X is clicked on their badge."""
        from dash import callback_context

        if not callback_context.triggered or not any(n_clicks_list):
            return current_users or [], current_options or [], []

        # Get the user_id of the clicked badge
        triggered_id = callback_context.triggered[0]["prop_id"]
        user_id_to_remove = None

        # Parse the triggered ID to get the user_id
        import json

        try:
            parsed_id = json.loads(triggered_id.split(".")[0])
            user_id_to_remove = parsed_id.get("user_id")
        except (json.JSONDecodeError, IndexError):
            return current_users or [], current_options or [], []

        if not user_id_to_remove:
            return current_users or [], current_options or [], []

        # Remove the user from the selected users list
        updated_users = [user for user in (current_users or []) if user != user_id_to_remove]

        # Remove the user from the options list
        updated_options = [
            opt for opt in (current_options or []) if opt["value"] != user_id_to_remove
        ]

        # Create updated user badges display
        if updated_options:
            selected_users_badges = []
            for user_option in updated_options:
                selected_users_badges.append(
                    dbc.Badge(
                        [
                            user_option["label"],
                            html.Span(
                                " ×",
                                className="ms-1",
                                style={"cursor": "pointer", "fontWeight": "bold"},
                                id={"type": "remove-user-badge", "user_id": user_option["value"]},
                            ),
                        ],
                        color="secondary",
                        className="me-1 mb-1",
                        pill=True,
                    )
                )
            current_users_display = selected_users_badges
        else:
            current_users_display = [
                dbc.Alert(
                    "No users currently selected",
                    color="light",
                    className="mb-0 text-muted small",
                )
            ]

        return updated_users, updated_options, current_users_display
