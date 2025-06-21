import dash
from dash import dcc, html, Output, Input, State
import dash_bootstrap_components as dbc
import requests
from dash import dash_table
import json
import dash_ag_grid as dag
from datetime import datetime
import flask
from flask import send_from_directory

API_BASE = "https://api.trends.earth/api/v1"
AUTH_URL = "https://api.trends.earth/auth"

server = flask.Flask(__name__)
app = dash.Dash(
    __name__,
    server=server,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)
app.title = "Trends.Earth API Dashboard"

@server.route('/health')
def health_check():
    return {'status': 'healthy'}, 200

@server.route('/favicon.ico')
def favicon():
    return send_from_directory(server.root_path, 'favicon.ico', mimetype='image/vnd.microsoft.icon')

def parse_date(date_str):
    if not date_str:
        return None
    try:
        # Handle ISO format with Z and potential microseconds
        if isinstance(date_str, str) and date_str.endswith("Z"):
            date_str = date_str[:-1] + "+00:00"
        dt = datetime.fromisoformat(date_str)
        # Return in ISO format without timezone info for ag-grid
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return date_str # Return original if parsing fails

def safe_table_data(data, column_ids=None):
    if not data:
        return data
    newdata = []
    for i, row in enumerate(data):
        newrow = {}
        for k in (column_ids or row.keys()):
            v = row.get(k, "")
            if k in ("params", "results"):
                newrow[k] = f"Show {k.capitalize()}"
            elif isinstance(v, (dict, list)):
                newrow[k] = json.dumps(v)
            else:
                newrow[k] = v
        newrow["_row"] = i
        newdata.append(newrow)
    return newdata

def get_user_info(token):
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{API_BASE}/user/me", headers=headers)
    if resp.status_code == 200:
        user_data = resp.json().get("data", {})
        return user_data
    resp = requests.get(f"{API_BASE}/user", headers=headers)
    if resp.status_code == 200:
        users = resp.json().get("data", [])
        if users:
            user_data = users[0]
            return user_data
    return {}

app.layout = dbc.Container(
    [
        html.H1("Trends.Earth API Dashboard"),
        html.Div(id="page-content"),
        dcc.Store(id="token-store"),
        dcc.Store(id="role-store"),
        dcc.Store(id="user-store"),
        dcc.Store(id="json-modal-data"),
        dcc.Store(id="scripts-raw-data"),
        dcc.Store(id="users-raw-data"),
        dcc.Store(id="current-log-context"),  # Store current log context for refresh
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle(id="json-modal-title")),
                dbc.ModalBody([
                    html.Div([
                        dbc.Row([
                            dbc.Col([
                                dbc.ButtonGroup([
                                    dbc.Button("Refresh Logs", id="refresh-logs-btn", color="primary", style={"display": "none"}),
                                    dbc.Button("Download JSON", id="download-json-btn", color="secondary"),
                                ]),
                            ], width="auto"),
                            dbc.Col([
                                html.Div([
                                    html.Span("Auto-refresh in: ", className="me-2", style={"display": "none"}, id="logs-countdown-label"),
                                    html.Span(id="logs-countdown", children="10s", className="badge bg-info", style={"display": "none"})
                                ], className="d-flex align-items-center")
                            ], width="auto"),
                        ], className="justify-content-between mb-3"),
                    ]),
                    html.Div(id="json-modal-body"),
                    dcc.Download(id="download-json"),
                    dcc.Interval(
                        id="logs-refresh-interval",
                        interval=10*1000,  # 10 seconds
                        n_intervals=0,
                        disabled=True
                    ),
                    dcc.Interval(
                        id="logs-countdown-interval",
                        interval=1000,  # 1 second for countdown
                        n_intervals=0,
                        disabled=True
                    )
                ]),
            ],
            id="json-modal",
            size="xl",
            is_open=False,
        ),
    ],
    fluid=True,
)

def login_layout():
    return dbc.Row(
        [
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader(
                            html.Div([
                                html.Img(
                                    src="https://docs.trends.earth/en/latest/_images/trends_earth_logo_bl_1200.png",
                                    alt="Trends.Earth Logo",
                                    style={"height": "60px", "marginBottom": "15px"}
                                ),
                                html.H4("Login")
                            ], className="text-center")
                        ),
                        dbc.CardBody(
                            [
                                dbc.Form([
                                    dbc.Row([
                                        dbc.Label("Email", width=3),
                                        dbc.Col(dbc.Input(id="login-email", type="email", placeholder="Enter email"), width=9),
                                    ], className="mb-3"),
                                    dbc.Row([
                                        dbc.Label("Password", width=3),
                                        dbc.Col(dbc.Input(id="login-password", type="password", placeholder="Enter password"), width=9),
                                    ], className="mb-3"),
                                    dbc.Button("Login", id="login-btn", color="primary", className="mt-2"),
                                ]),
                                html.Hr(),
                                dbc.Alert(
                                    id="login-alert",
                                    is_open=False,
                                    dismissable=True,
                                    duration=4000,
                                ),
                            ]
                        ),
                    ],
                    style={"maxWidth": "400px"},
                ),
                width=6,
                className="mx-auto mt-4"
            ),
        ]
    )

def dashboard_layout():
    return [
        dbc.Alert(
            id="alert",
            is_open=False,
            dismissable=True,
            duration=4000,
        ),
        dbc.Collapse(
            dbc.Tabs(
                [
                    dbc.Tab(label="Executions", tab_id="executions"),
                    dbc.Tab(label="Users", tab_id="users"),
                    dbc.Tab(label="Scripts", tab_id="scripts"),
                    dbc.Tab(label="Profile", tab_id="profile"),
                ],
                id="tabs",
                active_tab="executions",  # Default to executions
            ),
            id="main-panel",
            is_open=True
        ),
        html.Div(id="tab-content"),
    ]

@app.callback(
    Output("page-content", "children"),
    Output("token-store", "clear_data"),
    Input("token-store", "data"),
)
def display_page(token):
    if not token:
        return login_layout(), True
    return dashboard_layout(), False

@app.callback(
    Output("token-store", "data"),
    Output("role-store", "data"),
    Output("user-store", "data"),
    Output("login-alert", "children"),
    Output("login-alert", "color"),
    Output("login-alert", "is_open"),
    Input("login-btn", "n_clicks"),
    State("login-email", "value"),
    State("login-password", "value"),
    prevent_initial_call=True,
)
def login_api(n, email, password):
    if not email or not password:
        return dash.no_update, dash.no_update, dash.no_update, "Please enter email and password.", "danger", True
    try:
        resp = requests.post(
            AUTH_URL,
            json={"email": email, "password": password},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("access_token") or data.get("token")
            if not token:
                return dash.no_update, dash.no_update, dash.no_update, "No token returned.", "danger", True
            user_info = get_user_info(token)
            role = user_info.get("role", "USER")
            return token, role, user_info, "Login successful!", "success", True
        else:
            msg = ""
            try:
                msg = resp.json().get("msg")
            except Exception:
                msg = resp.text
            return dash.no_update, dash.no_update, dash.no_update, f"Login failed: {msg}", "danger", True
    except Exception as e:
        return dash.no_update, dash.no_update, dash.no_update, f"Network error: {str(e)}", "danger", True

@app.callback(
    Output("tab-content", "children"),
    Output("scripts-raw-data", "data"),
    Output("users-raw-data", "data"),
    Input("tabs", "active_tab"),
    State("token-store", "data"),
    State("role-store", "data"),
    State("user-store", "data"),
    prevent_initial_call=True,
)
def render_tab(tab, token, role, user_data):
    if not token:
        return html.Div("Please login first."), None, None
    headers = {"Authorization": f"Bearer {token}"}
    is_admin = (role == "ADMIN")

    # Fetch scripts and users for joins
    scripts = []
    users = []
    try:
        resp_scripts = requests.get(f"{API_BASE}/script", headers=headers)
        if resp_scripts.status_code == 200:
            scripts = resp_scripts.json().get("data", [])
    except Exception:
        pass
    try:
        resp_users = requests.get(f"{API_BASE}/user", headers=headers)
        if resp_users.status_code == 200:
            users = resp_users.json().get("data", [])
    except Exception:
        pass

    if tab == "scripts":
        filtered_scripts = scripts
        if not filtered_scripts:
            return html.Div([
                html.Div("No scripts found.")
            ]), scripts, users
        user_col = None
        if filtered_scripts and 'user_id' in filtered_scripts[0]:
            user_col = 'user_id'
        elif filtered_scripts and 'author_id' in filtered_scripts[0]:
            user_col = 'author_id'
        cols = []
        if filtered_scripts:
            if "name" in filtered_scripts[0]:
                cols.append({"name": "Script Name", "id": "name"})
            if user_col:
                cols.append({"name": "User Name", "id": "user_name"})
            for k in filtered_scripts[0].keys():
                if k not in ("name", user_col):
                    cols.append({"name": k, "id": k})
            # Add logs column for scripts
            cols.append({"name": "Logs", "id": "logs"})
        table_data = []
        user_id_to_name = {u.get("id"): u.get("name") for u in users or []}
        for s in filtered_scripts:
            row = s.copy()
            if user_col:
                row["user_name"] = user_id_to_name.get(row.get(user_col), "")
            for date_col in ['start_date', 'end_date', 'created_at', 'updated_at']:
                if date_col in row:
                    row[date_col] = parse_date(row.get(date_col))
            # Add logs action button
            row["logs"] = "Show Logs"
            table_data.append(row)
        table_data = safe_table_data(table_data, [c["id"] for c in cols])
        table_data = sorted(table_data, key=lambda x: x.get("name", ""))
        style_data_conditional = [
            {"condition": "params.data.status == 'SUCCESS'", "style": {"backgroundColor": "#D1E7DD"}},
            {"condition": "params.data.status == 'FAIL'", "style": {"backgroundColor": "#F8D7DA"}},
        ]
        column_defs = [{"headerName": c["name"], "field": c["id"]} for c in cols]
        for c in column_defs:
            if c['field'] == 'name':
                c['sort'] = 'asc'
            if c['field'] in ('start_date', 'end_date', 'created_at', 'updated_at'):
                c['filter'] = 'agDateColumnFilter'
            if c['field'] == 'logs':
                c['sortable'] = False
                c['filter'] = False
        return html.Div([
            dbc.Row([
                dbc.Col([
                    dbc.Button("Refresh Scripts", id="refresh-scripts-btn", color="primary", className="mb-3"),
                ], width="auto"),
            ]),
            dag.AgGrid(
                columnDefs=column_defs,
                rowData=table_data,
                id="scripts-table",
                defaultColDef={"sortable": True, "resizable": True, "filter": True},
                columnSize="sizeToFit",
                dashGridOptions={"pagination": True, "paginationPageSize": 50},
                getRowStyle={"styleConditions": style_data_conditional}
            )
        ]), scripts, users

    elif tab == "executions":
        column_defs = [
            {"headerName": "Script Name", "field": "script_name"},
            {"headerName": "User Email", "field": "user_email"},
            {"headerName": "Status", "field": "status"},
            {"headerName": "Start Date", "field": "start_date", "filter": "agDateColumnFilter"},
            {"headerName": "End Date", "field": "end_date", "filter": "agDateColumnFilter"},
            {"headerName": "Progress", "field": "progress"},
            {"headerName": "ID", "field": "id"},
            {"headerName": "Params", "field": "params", "sortable": False, "filter": False},
            {"headerName": "Results", "field": "results", "sortable": False, "filter": False},
            {"headerName": "Logs", "field": "logs", "sortable": False, "filter": False},
        ]
        
        style_data_conditional = [
            {"condition": "params.data.status === 'FAILED'", "style": {"backgroundColor": "#F8D7DA"}},
            {"condition": "params.data.status === 'FINISHED'", "style": {"backgroundColor": "#D1E7DD"}},
            {"condition": "params.data.status === 'RUNNING'", "style": {"backgroundColor": "#CCE5FF"}},
        ]

        return html.Div([
            dbc.Row([
                dbc.Col([
                    dbc.Button("Refresh Executions", id="refresh-executions-btn", color="primary", className="mb-3"),
                ], width="auto"),
                dbc.Col([
                    html.Div([
                        html.Span("Auto-refresh in: ", className="me-2"),
                        html.Span(id="executions-countdown", children="30s", className="badge bg-secondary")
                    ], className="d-flex align-items-center")
                ], width="auto"),
            ], className="justify-content-between"),
            dag.AgGrid(
                id="executions-table",
                columnDefs=column_defs,
                defaultColDef={"resizable": True, "sortable": True, "filter": True},
                columnSize="sizeToFit",
                rowModelType="infinite",
                dashGridOptions={
                    "cacheBlockSize": 50,
                    "maxBlocksInCache": 2,
                    "blockLoadDebounceMillis": 500,
                    "purgeClosedRowNodes": True,
                    "maxConcurrentDatasourceRequests": 1,
                },
                getRowStyle={"styleConditions": style_data_conditional},
                style={"height": "800px"}
            ),
            dcc.Interval(
                id="executions-auto-refresh-interval",
                interval=30*1000,  # 30 seconds
                n_intervals=0
            ),
            dcc.Interval(
                id="executions-countdown-interval",
                interval=1000,  # 1 second for countdown
                n_intervals=0
            )
        ]), scripts, users

    elif tab == "users":
        filtered_users = users
        if not filtered_users:
            return html.Div([
                html.Div("No users found.")
            ]), scripts, users
        user_keys = list(filtered_users[0].keys())
        cols = []
        if "email" in user_keys:
            cols.append({"name": "Email", "id": "email"})
        if "name" in user_keys:
            cols.append({"name": "Name", "id": "name"})
        for k in user_keys:
            if k not in ("email", "name"):
                cols.append({"name": k, "id": k})
        if is_admin:
            cols.append({"name": "Edit", "id": "edit", "presentation": "markdown"})
        
        for u in filtered_users:
            for date_col in ['created_at', 'updated_at']:
                if date_col in u:
                    u[date_col] = parse_date(u.get(date_col))
            if is_admin:
                u["edit"] = f"[Edit](#)"

        table_data = safe_table_data(filtered_users, [c["id"] for c in cols])
        table_data = sorted(table_data, key=lambda x: x.get("email", ""))
        column_defs = [{"headerName": c["name"], "field": c["id"]} for c in cols]
        for c in column_defs:
            if c['field'] == 'email':
                c['sort'] = 'asc'
            if c['field'] in ('created_at', 'updated_at'):
                c['filter'] = 'agDateColumnFilter'
        return html.Div([
            dbc.Row([
                dbc.Col([
                    dbc.Button("Refresh Users", id="refresh-users-btn", color="primary", className="mb-3"),
                ], width="auto"),
            ]),
            dag.AgGrid(
                columnDefs=column_defs,
                rowData=table_data,
                id="users-table",
                defaultColDef={"sortable": True, "resizable": True, "filter": True},
                columnSize="sizeToFit",
                dashGridOptions={"pagination": True, "paginationPageSize": 50},
            )
        ]), scripts, users

    elif tab == "profile":
        # Get current user data for pre-populating form
        current_name = ""
        current_email = ""
        current_institution = ""
        current_role = ""
        
        if user_data and isinstance(user_data, dict):
            current_name = user_data.get("name", "")
            current_email = user_data.get("email", "")
            current_institution = user_data.get("institution", "")
            current_role = user_data.get("role", "")
        else:
            print(f"No valid user_data for profile form: {user_data}")
        
        return html.Div([
            dbc.Card([
                dbc.CardHeader(html.H4("Profile Settings")),
                dbc.CardBody([
                    dbc.Form([
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Name"),
                                dbc.Input(id="profile-name", type="text", placeholder="Enter your name", value=current_name),
                            ], width=6),
                            dbc.Col([
                                dbc.Label("Email"),
                                dbc.Input(id="profile-email", type="email", placeholder="Enter your email", disabled=True, value=current_email),
                            ], width=6),
                        ], className="mb-3"),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Institution"),
                                dbc.Input(id="profile-institution", type="text", placeholder="Enter your institution", value=current_institution),
                            ], width=6),
                            dbc.Col([
                                dbc.Label("Role"),
                                dbc.Input(id="profile-role", type="text", disabled=True, value=current_role),
                            ], width=6),
                        ], className="mb-3"),
                        dbc.Row([
                            dbc.Col([
                                dbc.Button("Update Profile", id="update-profile-btn", color="primary", className="me-2"),
                                dbc.Alert(id="profile-update-alert", is_open=False, dismissable=True),
                            ], width=12),
                        ], className="mb-4"),
                    ])
                ])
            ], className="mb-4"),
            dbc.Card([
                dbc.CardHeader(html.H4("Change Password")),
                dbc.CardBody([
                    dbc.Form([
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Current Password"),
                                dbc.Input(id="current-password", type="password", placeholder="Enter current password"),
                            ], width=12),
                        ], className="mb-3"),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("New Password"),
                                dbc.Input(id="new-password", type="password", placeholder="Enter new password"),
                            ], width=6),
                            dbc.Col([
                                dbc.Label("Confirm New Password"),
                                dbc.Input(id="confirm-password", type="password", placeholder="Confirm new password"),
                            ], width=6),
                        ], className="mb-3"),
                        dbc.Row([
                            dbc.Col([
                                dbc.Button("Change Password", id="change-password-btn", color="secondary"),
                                dbc.Alert(id="password-change-alert", is_open=False, dismissable=True),
                            ], width=12),
                        ]),
                    ])
                ])
            ])
        ]), scripts, users

    return html.Div("Unknown tab."), scripts, users

@app.callback(
    Output("executions-table", "getRowsResponse"),
    Input("executions-table", "getRowsRequest"),
    State("token-store", "data"),
    State("scripts-raw-data", "data"),
    State("users-raw-data", "data"),
    prevent_initial_call=True,
)
def get_execution_rows(request, token, scripts, users):
    try:
        if not request or not token:
            return {"rowData": [], "rowCount": 0}

        start_row = request.get("startRow", 0)
        end_row = request.get("endRow", 10000)
        page_size = end_row - start_row
        page = (start_row // page_size) + 1

        # Handle sorting
        sort_model = request.get("sortModel", [])
        filter_model = request.get("filterModel", {})

        params = {
            "page": page,
            "per_page": page_size,
            "exclude": "params,results",
        }

        # Add sorting to API request if supported
        if sort_model:
            sort_item = sort_model[0]  # Take first sort
            sort_field = sort_item.get("colId")
            sort_dir = sort_item.get("sort")
            
            # Map frontend field names to API field names
            field_mapping = {
                "script_name": "script_id",
                "user_email": "user_id",
                "status": "status",
                "start_date": "start_date",
                "end_date": "end_date", 
                "progress": "progress",
                "id": "id"
            }
            
            api_field = field_mapping.get(sort_field, sort_field)
            if sort_dir == "desc":
                # The API expects descending order with a leading dash
                params["sort"] = f"-{api_field}"
            else:
                params["sort"] = api_field

        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{API_BASE}/execution", params=params, headers=headers)

        if resp.status_code != 200:
            return {"rowData": [], "rowCount": 0}

        result = resp.json()
        executions = result.get("data", [])
        total_rows = result.get("total", 0)

        script_id_to_name = {s.get("id"): s.get("name") for s in scripts or []}
        user_id_to_email = {u.get("id"): u.get("email") for u in users or []}

        tabledata = []
        for exec_row in executions:
            row = exec_row.copy()
            row["script_name"] = script_id_to_name.get(row.get("script_id"), "")
            row["user_email"] = user_id_to_email.get(row.get("user_id"), "")
            row["params"] = "Show Params"
            row["results"] = "Show Results"
            row["logs"] = "Show Logs"
            for date_col in ['start_date', 'end_date']:
                if date_col in row:
                    row[date_col] = parse_date(row.get(date_col))
            tabledata.append(row)

        # Apply client-side filtering for fields that can't be filtered server-side
        if filter_model:
            filtered_data = []
            for row in tabledata:
                include_row = True
                for field, filter_config in filter_model.items():
                    filter_type = filter_config.get("filterType", "text")
                    filter_value = filter_config.get("filter", "").lower()
                    
                    if not filter_value:
                        continue
                        
                    row_value = str(row.get(field, "")).lower()
                    
                    if filter_type == "text":
                        condition = filter_config.get("type", "contains")
                        if condition == "contains" and filter_value not in row_value:
                            include_row = False
                            break
                        elif condition == "equals" and filter_value != row_value:
                            include_row = False
                            break
                        elif condition == "startsWith" and not row_value.startswith(filter_value):
                            include_row = False
                            break
                    elif filter_type == "date":
                        # For date filtering, we'd need more complex logic
                        # This is a simplified version
                        if filter_value not in row_value:
                            include_row = False
                            break
                            
                if include_row:
                    filtered_data.append(row)
            tabledata = filtered_data

        return {"rowData": tabledata, "rowCount": total_rows}
    
    except Exception as e:
        print(f"Error in get_execution_rows: {str(e)}")
        return {"rowData": [], "rowCount": 0}

@app.callback(
    Output("json-modal", "is_open"),
    Output("json-modal-body", "children"),
    Output("json-modal-data", "data"),
    Output("json-modal-title", "children"),
    Output("refresh-logs-btn", "style"),
    Output("logs-refresh-interval", "disabled"),
    Output("current-log-context", "data"),
    Input("executions-table", "cellClicked"),
    State("token-store", "data"),
    State("json-modal", "is_open"),
    prevent_initial_call=True,
)
def show_json_modal(cell, token, is_open):
    if not cell:
        return is_open, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    
    col = cell.get("colId")
    if col not in ("params", "results", "logs"):
        return is_open, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    # For infinite row model, we need to get the row data differently
    # We'll use the rowIndex to fetch from our current data
    row_index = cell.get("rowIndex")
    
    if row_index is None:
        return True, "Could not get row index.", None, "Error", {"display": "none"}, True, None

    # We need to make a request to get the row data since cellClicked doesn't provide it
    # Let's use a different approach - get all data and find the right row
    headers = {"Authorization": f"Bearer {token}"}
    
    # Calculate which page this row is on
    page_size = 50  # This should match your cacheBlockSize
    page = (row_index // page_size) + 1
    row_in_page = row_index % page_size
    
    params = {
        "page": page,
        "per_page": page_size,
        "exclude": "params,results",
    }
    
    resp = requests.get(f"{API_BASE}/execution", params=params, headers=headers)
    if resp.status_code != 200:
        return True, f"Failed to fetch execution data: {resp.text}", None, "Error", {"display": "none"}, True, None
    
    result = resp.json()
    executions = result.get("data", [])
    
    if row_in_page >= len(executions):
        return True, f"Row index {row_in_page} out of range for page {page}", None, "Error", {"display": "none"}, True, None
    
    execution = executions[row_in_page]
    exec_id = execution.get("id")
    
    if not exec_id:
        return True, f"Could not get execution ID from row data. Row: {execution}", None, "Error", {"display": "none"}, True, None

    if col == "logs":
        # Fetch logs from a different endpoint
        resp = requests.get(f"{API_BASE}/execution/{exec_id}/log", headers=headers)
        if resp.status_code != 200:
            return True, f"Failed to fetch execution logs: {resp.text}", None, "Execution Logs", {"display": "none"}, True, None
        
        logs_data = resp.json().get("data", [])
        if not logs_data:
            return True, "No logs found for this execution.", None, "Execution Logs", {"display": "none"}, True, None
        
        # Parse and format logs for display
        if isinstance(logs_data, list):
            parsed_logs = []
            for log in logs_data:
                if isinstance(log, dict):
                    register_date = log.get("register_date", "")
                    level = log.get("level", "")
                    text = log.get("text", "")
                    
                    # Parse and format the date
                    formatted_date = parse_date(register_date) or register_date
                    
                    # Create formatted log line
                    log_line = f"{formatted_date} - {level} - {text}"
                    parsed_logs.append((register_date, log_line))
                else:
                    # Fallback for non-dict log entries
                    parsed_logs.append(("", str(log)))
            
            # Sort by register_date in descending order
            parsed_logs.sort(key=lambda x: x[0], reverse=True)
            logs_content = "\n".join([log_line for _, log_line in parsed_logs])
        else:
            logs_content = str(logs_data)
        
        log_context = {"type": "execution", "id": exec_id, "status": execution.get("status")}
        
        # Disable auto-refresh if execution is finished
        disable_refresh = execution.get("status") in ["FINISHED", "FAILED"]
        
        return True, html.Pre(logs_content, style={"whiteSpace": "pre-wrap", "fontSize": "12px"}), logs_data, "Execution Logs", {"display": "inline-block"}, disable_refresh, log_context
    else:
        # Handle params and results as before
        resp = requests.get(f"{API_BASE}/execution/{exec_id}", headers=headers)
        if resp.status_code != 200:
            return True, f"Failed to fetch execution details: {resp.text}", None, "Error", {"display": "none"}, True, None
        
        execution_data = resp.json().get("data", {})
        json_data = execution_data.get(col)

        if json_data is None:
            return True, f"'{col}' not found in execution data.", None, "Error", {"display": "none"}, True, None

        title = f"Execution {col.capitalize()}"
        return True, dcc.Loading(render_json_tree(json_data)), json_data, title, {"display": "none"}, True, None

def render_json_tree(data, level=0, parent_id="root"):
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            return html.Code(repr(data))
    if isinstance(data, dict):
        items = []
        for k, v in data.items():
            node_id = f"{parent_id}-{k}"
            if isinstance(v, (dict, list)):
                items.append(html.Details([
                    html.Summary(str(k)),
                    render_json_tree(v, level+1, node_id)
                ], open=(level < 1)))
            else:
                items.append(html.Div([
                    html.Span(f"{k}: "),
                    html.Code(repr(v))
                ], style={"marginLeft": f"{level*20}px"}))
        return html.Div(items)
    elif isinstance(data, list):
        items = []
        for idx, v in enumerate(data):
            node_id = f"{parent_id}-{idx}"
            if isinstance(v, (dict, list)):
                items.append(html.Details([
                    html.Summary(f"[{idx}]"),
                    render_json_tree(v, level+1, node_id)
                ], open=(level < 1)))
            else:
                items.append(html.Div([
                    html.Span(f"[{idx}]: "),
                    html.Code(repr(v))
                ], style={"marginLeft": f"{level*20}px"}))
        return html.Div(items)
    else:
        return html.Code(repr(data))

@app.callback(
    Output("download-json", "data"),
    Input("download-json-btn", "n_clicks"),
    State("json-modal-data", "data"),
    prevent_initial_call=True,
)
def download_json(n, json_data):
    if n and json_data is not None:
        try:
            json_str = json.dumps(json_data, indent=2)
        except Exception:
            json_str = str(json_data)
        return dict(content=json_str, filename="data.json")
    return dash.no_update

@app.callback(
    Output("json-modal", "is_open", allow_duplicate=True),
    Output("json-modal-body", "children", allow_duplicate=True),
    Output("json-modal-data", "data", allow_duplicate=True),
    Output("json-modal-title", "children", allow_duplicate=True),
    Output("refresh-logs-btn", "style", allow_duplicate=True),
    Output("logs-refresh-interval", "disabled", allow_duplicate=True),
    Output("current-log-context", "data", allow_duplicate=True),
    Input("scripts-table", "cellClicked"),
    State("token-store", "data"),
    State("json-modal", "is_open"),
    State("scripts-raw-data", "data"),
    prevent_initial_call=True,
)
def show_script_logs_modal(cell, token, is_open, scripts_data):
    if not cell:
        return is_open, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    
    col = cell.get("colId")
    if col != "logs":
        return is_open, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    row_index = cell.get("rowIndex")
    
    if row_index is None or not scripts_data:
        return True, "Could not get script data.", None, "Error", {"display": "none"}, True, None

    if row_index >= len(scripts_data):
        return True, f"Row index {row_index} out of range", None, "Error", {"display": "none"}, True, None
    
    script = scripts_data[row_index]
    script_id = script.get("id")
    
    if not script_id:
        return True, f"Could not get script ID from row data. Row: {script}", None, "Error", {"display": "none"}, True, None

    headers = {"Authorization": f"Bearer {token}"}
    
    # Fetch logs for the script
    resp = requests.get(f"{API_BASE}/script/{script_id}/log", headers=headers)
    if resp.status_code != 200:
        return True, f"Failed to fetch script logs: {resp.text}", None, "Script Logs", {"display": "none"}, True, None
    
    logs_data = resp.json().get("data", [])
    if not logs_data:
        return True, "No logs found for this script.", None, "Script Logs", {"display": "none"}, True, None
    
    # Parse and format logs for display
    if isinstance(logs_data, list):
        parsed_logs = []
        for log in logs_data:
            if isinstance(log, dict):
                register_date = log.get("register_date", "")
                level = log.get("level", "")
                text = log.get("text", "")
                
                # Parse and format the date
                formatted_date = parse_date(register_date) or register_date
                
                # Create formatted log line
                log_line = f"{formatted_date} - {level} - {text}"
                parsed_logs.append((register_date, log_line))
            else:
                # Fallback for non-dict log entries
                parsed_logs.append(("", str(log)))
        
        # Sort by register_date in descending order
        parsed_logs.sort(key=lambda x: x[0], reverse=True)
        logs_content = "\n".join([log_line for _, log_line in parsed_logs])
    else:
        logs_content = str(logs_data)
    
    log_context = {"type": "script", "id": script_id}
    return True, html.Pre(logs_content, style={"whiteSpace": "pre-wrap", "fontSize": "12px"}), logs_data, "Script Logs", {"display": "inline-block"}, False, log_context

@app.callback(
    Output("json-modal-body", "children", allow_duplicate=True),
    Output("json-modal-data", "data", allow_duplicate=True),
    Output("logs-countdown-interval", "n_intervals", allow_duplicate=True),
    [Input("refresh-logs-btn", "n_clicks"),
     Input("logs-refresh-interval", "n_intervals")],
    [State("current-log-context", "data"),
     State("token-store", "data"),
     State("json-modal", "is_open")],
    prevent_initial_call=True,
)
def refresh_logs(refresh_clicks, n_intervals, log_context, token, modal_open):
    if not modal_open or not log_context or not token:
        return dash.no_update, dash.no_update, dash.no_update
    
    headers = {"Authorization": f"Bearer {token}"}
    log_type = log_context.get("type")
    log_id = log_context.get("id")
    
    if not log_type or not log_id:
        return dash.no_update, dash.no_update
    
    # Fetch logs based on type
    if log_type == "execution":
        resp = requests.get(f"{API_BASE}/execution/{log_id}/log", headers=headers)
    elif log_type == "script":
        resp = requests.get(f"{API_BASE}/script/{log_id}/log", headers=headers)
    else:
        return dash.no_update, dash.no_update, dash.no_update
    
    if resp.status_code != 200:
        return html.Pre(f"Failed to fetch logs: {resp.text}", 
                       style={"whiteSpace": "pre-wrap", "fontSize": "12px", "color": "red"}), None, dash.no_update
    
    logs_data = resp.json().get("data", [])
    if not logs_data:
        return html.Pre("No logs found.", 
                       style={"whiteSpace": "pre-wrap", "fontSize": "12px"}), None, dash.no_update
    
    # Parse and format logs for display
    if isinstance(logs_data, list):
        parsed_logs = []
        for log in logs_data:
            if isinstance(log, dict):
                register_date = log.get("register_date", "")
                level = log.get("level", "")
                text = log.get("text", "")
                
                # Parse and format the date
                formatted_date = parse_date(register_date) or register_date
                
                # Create formatted log line
                log_line = f"{formatted_date} - {level} - {text}"
                parsed_logs.append((register_date, log_line))
            else:
                # Fallback for non-dict log entries
                parsed_logs.append(("", str(log)))
        
        # Sort by register_date in descending order
        parsed_logs.sort(key=lambda x: x[0], reverse=True)
        logs_content = "\n".join([log_line for _, log_line in parsed_logs])
    else:
        logs_content = str(logs_data)
    
    return html.Pre(logs_content, style={"whiteSpace": "pre-wrap", "fontSize": "12px"}), logs_data, 0

@app.callback(
    Output("logs-refresh-interval", "disabled", allow_duplicate=True),
    Output("refresh-logs-btn", "style", allow_duplicate=True),
    Output("logs-countdown-interval", "disabled", allow_duplicate=True),
    Output("logs-countdown-label", "style", allow_duplicate=True),
    Output("logs-countdown", "style", allow_duplicate=True),
    Input("json-modal", "is_open"),
    State("current-log-context", "data"),
    prevent_initial_call=True,
)
def toggle_refresh_interval(is_open, log_context):
    if not is_open:
        # Modal is closed, disable interval and hide button/countdown
        return True, {"display": "none"}, True, {"display": "none"}, {"display": "none"}
    elif log_context and log_context.get("type") in ["execution", "script"]:
        # For executions, check if status is finished to disable auto-refresh
        if (log_context.get("type") == "execution" and 
            log_context.get("status") in ["FINISHED", "FAILED"]):
            # Execution is finished, disable auto-refresh but show manual refresh button
            return True, {"display": "inline-block"}, True, {"display": "none"}, {"display": "none"}
        else:
            # Modal is open and showing logs for running execution or script, enable interval and show button/countdown
            return False, {"display": "inline-block"}, False, {"display": "inline"}, {"display": "inline"}
    else:
        # Modal is open but not showing logs, disable interval and hide button/countdown
        return True, {"display": "none"}, True, {"display": "none"}, {"display": "none"}

@app.callback(
    Output("tab-content", "children", allow_duplicate=True),
    Output("scripts-raw-data", "data", allow_duplicate=True),
    Output("users-raw-data", "data", allow_duplicate=True),
    [Input("refresh-scripts-btn", "n_clicks"),
     Input("refresh-users-btn", "n_clicks"),
     Input("refresh-executions-btn", "n_clicks")],
    [State("tabs", "active_tab"),
     State("token-store", "data"),
     State("role-store", "data")],
    prevent_initial_call=True,
)
def refresh_table_data(refresh_scripts_clicks, refresh_users_clicks, refresh_executions_clicks, 
                       active_tab, token, role):
    if not token:
        return dash.no_update, dash.no_update, dash.no_update
    
    # Determine which button was clicked
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update, dash.no_update
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Only refresh if the clicked button matches the active tab
    if (button_id == "refresh-scripts-btn" and active_tab != "scripts") or \
       (button_id == "refresh-users-btn" and active_tab != "users") or \
       (button_id == "refresh-executions-btn" and active_tab != "executions"):
        return dash.no_update, dash.no_update, dash.no_update
    
    headers = {"Authorization": f"Bearer {token}"}
    is_admin = (role == "ADMIN")

    # Fetch fresh scripts and users data
    scripts = []
    users = []
    try:
        resp_scripts = requests.get(f"{API_BASE}/script", headers=headers)
        if resp_scripts.status_code == 200:
            scripts = resp_scripts.json().get("data", [])
    except Exception:
        pass
    try:
        resp_users = requests.get(f"{API_BASE}/user", headers=headers)
        if resp_users.status_code == 200:
            users = resp_users.json().get("data", [])
    except Exception:
        pass

    # Generate fresh table content based on active tab
    if active_tab == "scripts":
        filtered_scripts = scripts
        if not filtered_scripts:
            return html.Div([
                dbc.Row([
                    dbc.Col([
                        dbc.Button("Refresh Scripts", id="refresh-scripts-btn", color="primary", className="mb-3"),
                    ], width="auto"),
                ]),
                html.Div("No scripts found.")
            ]), scripts, users
        
        user_col = None
        if filtered_scripts and 'user_id' in filtered_scripts[0]:
            user_col = 'user_id'
        elif filtered_scripts and 'author_id' in filtered_scripts[0]:
            user_col = 'author_id'
        
        cols = []
        if filtered_scripts:
            if "name" in filtered_scripts[0]:
                cols.append({"name": "Script Name", "id": "name"})
            if user_col:
                cols.append({"name": "User Name", "id": "user_name"})
            for k in filtered_scripts[0].keys():
                if k not in ("name", user_col):
                    cols.append({"name": k, "id": k})
            cols.append({"name": "Logs", "id": "logs"})
        
        table_data = []
        user_id_to_name = {u.get("id"): u.get("name") for u in users or []}
        for s in filtered_scripts:
            row = s.copy()
            if user_col:
                row["user_name"] = user_id_to_name.get(row.get(user_col), "")
            for date_col in ['start_date', 'end_date', 'created_at', 'updated_at']:
                if date_col in row:
                    row[date_col] = parse_date(row.get(date_col))
            row["logs"] = "Show Logs"
            table_data.append(row)
        
        table_data = safe_table_data(table_data, [c["id"] for c in cols])
        table_data = sorted(table_data, key=lambda x: x.get("name", ""))
        
        style_data_conditional = [
            {"condition": "params.data.status == 'SUCCESS'", "style": {"backgroundColor": "#D1E7DD"}},
            {"condition": "params.data.status == 'FAIL'", "style": {"backgroundColor": "#F8D7DA"}},
        ]
        
        column_defs = [{"headerName": c["name"], "field": c["id"]} for c in cols]
        for c in column_defs:
            if c['field'] == 'name':
                c['sort'] = 'asc'
            if c['field'] in ('start_date', 'end_date', 'created_at', 'updated_at'):
                c['filter'] = 'agDateColumnFilter'
            if c['field'] == 'logs':
                c['sortable'] = False
                c['filter'] = False
        
        return html.Div([
            dbc.Row([
                dbc.Col([
                    dbc.Button("Refresh Scripts", id="refresh-scripts-btn", color="primary", className="mb-3"),
                ], width="auto"),
            ]),
            dag.AgGrid(
                columnDefs=column_defs,
                rowData=table_data,
                id="scripts-table",
                defaultColDef={"sortable": True, "resizable": True, "filter": True},
                columnSize="sizeToFit",
                dashGridOptions={"pagination": True, "paginationPageSize": 50},
                getRowStyle={"styleConditions": style_data_conditional}
            )
        ]), scripts, users

    elif active_tab == "users":
        filtered_users = users
        if not filtered_users:
            return html.Div([
                dbc.Row([
                    dbc.Col([
                        dbc.Button("Refresh Users", id="refresh-users-btn", color="primary", className="mb-3"),
                    ], width="auto"),
                ]),
                html.Div("No users found.")
            ]), scripts, users
        
        user_keys = list(filtered_users[0].keys())
        cols = []
        if "email" in user_keys:
            cols.append({"name": "Email", "id": "email"})
        if "name" in user_keys:
            cols.append({"name": "Name", "id": "name"})
        for k in user_keys:
            if k not in ("email", "name"):
                cols.append({"name": k, "id": k})
        if is_admin:
            cols.append({"name": "Edit", "id": "edit", "presentation": "markdown"})
        
        for u in filtered_users:
            for date_col in ['created_at', 'updated_at']:
                if date_col in u:
                    u[date_col] = parse_date(u.get(date_col))
            if is_admin:
                u["edit"] = f"[Edit](#)"

        table_data = safe_table_data(filtered_users, [c["id"] for c in cols])
        table_data = sorted(table_data, key=lambda x: x.get("email", ""))
        
        column_defs = [{"headerName": c["name"], "field": c["id"]} for c in cols]
        for c in column_defs:
            if c['field'] == 'email':
                c['sort'] = 'asc'
            if c['field'] in ('created_at', 'updated_at'):
                c['filter'] = 'agDateColumnFilter'
        
        return html.Div([
            dbc.Row([
                dbc.Col([
                    dbc.Button("Refresh Users", id="refresh-users-btn", color="primary", className="mb-3"),
                ], width="auto"),
            ]),
            dag.AgGrid(
                columnDefs=column_defs,
                rowData=table_data,
                id="users-table",
                defaultColDef={"sortable": True, "resizable": True, "filter": True},
                columnSize="sizeToFit",
                dashGridOptions={"pagination": True, "paginationPageSize": 50},
            )
        ]), scripts, users

    elif active_tab == "executions":
        # For executions, we just need to return the table structure
        # The infinite row model will automatically refresh when the callback triggers
        column_defs = [
            {"headerName": "Script Name", "field": "script_name"},
            {"headerName": "User Email", "field": "user_email"},
            {"headerName": "Status", "field": "status"},
            {"headerName": "Start Date", "field": "start_date", "filter": "agDateColumnFilter"},
            {"headerName": "End Date", "field": "end_date", "filter": "agDateColumnFilter"},
            {"headerName": "Progress", "field": "progress"},
            {"headerName": "ID", "field": "id"},
            {"headerName": "Params", "field": "params", "sortable": False, "filter": False},
            {"headerName": "Results", "field": "results", "sortable": False, "filter": False},
            {"headerName": "Logs", "field": "logs", "sortable": False, "filter": False},
        ]
        
        style_data_conditional = [
            {"condition": "params.data.status === 'FAILED'", "style": {"backgroundColor": "#F8D7DA"}},
            {"condition": "params.data.status === 'FINISHED'", "style": {"backgroundColor": "#D1E7DD"}},
            {"condition": "params.data.status === 'RUNNING'", "style": {"backgroundColor": "#CCE5FF"}},
        ]

        return html.Div([
            dbc.Row([
                dbc.Col([
                    dbc.Button("Refresh Executions", id="refresh-executions-btn", color="primary", className="mb-3"),
                ], width="auto"),
                dbc.Col([
                    html.Div([
                        html.Span("Auto-refresh in: ", className="me-2"),
                        html.Span(id="executions-countdown", children="30s", className="badge bg-secondary")
                    ], className="d-flex align-items-center")
                ], width="auto"),
            ], className="justify-content-between"),
            dag.AgGrid(
                id="executions-table",
                columnDefs=column_defs,
                defaultColDef={"resizable": True, "sortable": True, "filter": True},
                columnSize="sizeToFit",
                rowModelType="infinite",
                dashGridOptions={
                    "cacheBlockSize": 50,
                    "maxBlocksInCache": 2,
                    "blockLoadDebounceMillis": 500,
                    "purgeClosedRowNodes": True,
                    "maxConcurrentDatasourceRequests": 1,
                },
                getRowStyle={"styleConditions": style_data_conditional},
                style={"height": "800px"}
            ),
            dcc.Interval(
                id="executions-auto-refresh-interval",
                interval=30*1000,  # 30 seconds
                n_intervals=0
            ),
            dcc.Interval(
                id="executions-countdown-interval",
                interval=1000,  # 1 second for countdown
                n_intervals=0
            )
        ]), scripts, users

    return dash.no_update, dash.no_update, dash.no_update

@app.callback(
    Output("executions-table", "getRowsResponse", allow_duplicate=True),
    Output("executions-countdown-interval", "n_intervals"),
    Input("refresh-executions-btn", "n_clicks"),
    [State("token-store", "data"),
     State("scripts-raw-data", "data"),
     State("users-raw-data", "data")],
    prevent_initial_call=True,
)
def refresh_executions_table(n_clicks, token, scripts, users):
    if not n_clicks or not token:
        return dash.no_update, dash.no_update
    
    # For infinite row model, we need to trigger a refresh by clearing the cache
    # This is done by returning a fresh response for the first page
    headers = {"Authorization": f"Bearer {token}"}
    
    params = {
        "page": 1,
        "per_page": 50,
        "exclude": "params,results",
    }
    
    resp = requests.get(f"{API_BASE}/execution", params=params, headers=headers)
    
    if resp.status_code != 200:
        return {"rowData": [], "rowCount": 0}, dash.no_update

    result = resp.json()
    executions = result.get("data", [])
    total_rows = result.get("total", 0)

    script_id_to_name = {s.get("id"): s.get("name") for s in scripts or []}
    user_id_to_email = {u.get("id"): u.get("email") for u in users or []}

    tabledata = []
    for exec_row in executions:
        row = exec_row.copy()
        row["script_name"] = script_id_to_name.get(row.get("script_id"), "")
        row["user_email"] = user_id_to_email.get(row.get("user_id"), "")
        row["params"] = "Show Params"
        row["results"] = "Show Results"
        row["logs"] = "Show Logs"
        for date_col in ['start_date', 'end_date']:
            if date_col in row:
                row[date_col] = parse_date(row.get(date_col))
        tabledata.append(row)

    # Reset countdown timer to 0 when manually refreshed
    return {"rowData": tabledata, "rowCount": total_rows}, 0

@app.callback(
    Output("executions-table", "getRowsResponse", allow_duplicate=True),
    Input("executions-auto-refresh-interval", "n_intervals"),
    [State("token-store", "data"),
     State("scripts-raw-data", "data"),
     State("users-raw-data", "data"),
     State("tabs", "active_tab")],
    prevent_initial_call=True,
)
def auto_refresh_executions_table(n_intervals, token, scripts, users, active_tab):
    # Only refresh if executions tab is active
    if active_tab != "executions" or not token:
        return dash.no_update
    
    headers = {"Authorization": f"Bearer {token}"}
    
    params = {
        "page": 1,
        "per_page": 50,
        "exclude": "params,results",
    }
    
    resp = requests.get(f"{API_BASE}/execution", params=params, headers=headers)
    
    if resp.status_code != 200:
        return {"rowData": [], "rowCount": 0}

    result = resp.json()
    executions = result.get("data", [])
    total_rows = result.get("total", 0)

    script_id_to_name = {s.get("id"): s.get("name") for s in scripts or []}
    user_id_to_email = {u.get("id"): u.get("email") for u in users or []}

    tabledata = []
    for exec_row in executions:
        row = exec_row.copy()
        row["script_name"] = script_id_to_name.get(row.get("script_id"), "")
        row["user_email"] = user_id_to_email.get(row.get("user_id"), "")
        row["params"] = "Show Params"
        row["results"] = "Show Results"
        row["logs"] = "Show Logs"
        for date_col in ['start_date', 'end_date']:
            if date_col in row:
                row[date_col] = parse_date(row.get(date_col))
        tabledata.append(row)

    return {"rowData": tabledata, "rowCount": total_rows}

@app.callback(
    Output("executions-countdown", "children"),
    Input("executions-countdown-interval", "n_intervals"),
    State("tabs", "active_tab"),
    prevent_initial_call=True,
)
def update_executions_countdown(n_intervals, active_tab):
    if active_tab != "executions":
        return dash.no_update
    
    # Calculate remaining seconds (30 second cycle)
    remaining = 30 - (n_intervals % 30)
    return f"{remaining}s"

@app.callback(
    Output("logs-countdown", "children"),
    Output("logs-refresh-interval", "n_intervals", allow_duplicate=True),
    [Input("logs-countdown-interval", "n_intervals"),
     Input("refresh-logs-btn", "n_clicks")],
    [State("json-modal", "is_open"),
     State("current-log-context", "data")],
    prevent_initial_call=True,
)
def update_logs_countdown(countdown_intervals, refresh_clicks, modal_open, log_context):
    ctx = dash.callback_context
    
    # If modal is not open or not showing logs, don't update
    if not modal_open or not log_context or not log_context.get("type") in ["execution", "script"]:
        return dash.no_update, dash.no_update
    
    # If execution is finished, don't update countdown (auto-refresh is disabled)
    if (log_context.get("type") == "execution" and 
        log_context.get("status") in ["FINISHED", "FAILED"]):
        return dash.no_update, dash.no_update
    
    # If refresh button was clicked, reset countdown to 10 and trigger refresh
    if ctx.triggered and ctx.triggered[0]['prop_id'] == 'refresh-logs-btn.n_clicks':
        return "10s", 0
    
    # Calculate remaining seconds (10 second cycle)
    remaining = 10 - (countdown_intervals % 10)
    return f"{remaining}s", dash.no_update

# Profile update callback
@app.callback(
    [Output("profile-update-alert", "children"),
     Output("profile-update-alert", "color"),
     Output("profile-update-alert", "is_open"),
     Output("user-store", "data", allow_duplicate=True)],
    [Input("update-profile-btn", "n_clicks")],
    [State("profile-name", "value"),
     State("profile-institution", "value"),
     State("token-store", "data"),
     State("user-store", "data")],
    prevent_initial_call=True,
)
def update_profile(n_clicks, name, institution, token, user_data):
    if not n_clicks or not token or not user_data:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
    
    if not name:
        return "Name is required.", "danger", True, dash.no_update
    
    headers = {"Authorization": f"Bearer {token}"}
    update_data = {
        "name": name,
        "institution": institution or ""
    }
    
    try:
        user_id = user_data.get("id")
        if not user_id:
            return "User ID not found in user data.", "danger", True, dash.no_update
        
        resp = requests.patch(
            f"{API_BASE}/user/me",
            json=update_data,
            headers=headers,
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
                pass
            return error_msg, "danger", True, dash.no_update
            
    except Exception as e:
        return f"Network error: {str(e)}", "danger", True, dash.no_update

# Password change callback
@app.callback(
    [Output("password-change-alert", "children"),
     Output("password-change-alert", "color"),
     Output("password-change-alert", "is_open"),
     Output("current-password", "value"),
     Output("new-password", "value"),
     Output("confirm-password", "value")],
    [Input("change-password-btn", "n_clicks")],
    [State("current-password", "value"),
     State("new-password", "value"),
     State("confirm-password", "value"),
     State("token-store", "data"),
     State("user-store", "data")],
    prevent_initial_call=True,
)
def change_password(n_clicks, current_password, new_password, confirm_password, token, user_data):
    if not n_clicks or not token or not user_data:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    
    if not current_password or not new_password or not confirm_password:
        return "All password fields are required.", "danger", True, dash.no_update, dash.no_update, dash.no_update
    
    if new_password != confirm_password:
        return "New passwords do not match.", "danger", True, dash.no_update, dash.no_update, dash.no_update
    
    if len(new_password) < 6:
        return "Password must be at least 6 characters long.", "danger", True, dash.no_update, dash.no_update, dash.no_update
    
    headers = {"Authorization": f"Bearer {token}"}
    password_data = {
        "current_password": current_password,
        "new_password": new_password
    }
    
    try:
        user_id = user_data.get("id")
        resp = requests.put(
            f"{API_BASE}/user/{user_id}/password",
            json=password_data,
            headers=headers,
            timeout=10,
        )
        
        if resp.status_code == 200:
            # Clear password fields on success
            return "Password changed successfully!", "success", True, "", "", ""
        else:
            error_msg = "Failed to change password."
            try:
                error_data = resp.json()
                error_msg = error_data.get("msg", error_msg)
            except Exception:
                pass
            return error_msg, "danger", True, dash.no_update, dash.no_update, dash.no_update
            
    except Exception as e:
        return f"Network error: {str(e)}", "danger", True, dash.no_update, dash.no_update, dash.no_update