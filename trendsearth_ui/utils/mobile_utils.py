"""Utilities for mobile device detection and responsive design."""

from dash import Input, Output, clientside_callback, dcc, html

TRUNCATED_CELL_STYLE = {
    "whiteSpace": "nowrap",
    "overflow": "hidden",
    "textOverflow": "ellipsis",
}

# Fields that are only available to admin/superadmin users
ADMIN_ONLY_FIELDS = {"user_name", "user_email", "docker_logs", "batch_logs"}


def create_mobile_detection_components():
    """Create components for mobile device detection."""
    return [
        # Store to track if device is mobile
        dcc.Store(id="is-mobile-store", data=False),
        # Store to track screen size
        dcc.Store(id="screen-size-store", data={"width": 1920, "height": 1080}),
        # Interval to check window size (only runs once on load)
        dcc.Interval(
            id="window-size-interval",
            interval=1000,  # 1 second
            n_intervals=0,
            max_intervals=1,  # Only run once
        ),
        # Hidden div to trigger clientside callbacks
        html.Div(id="window-size-trigger", style={"display": "none"}),
    ]


def get_executions_columns_for_role(role: str | None) -> list[dict]:
    """Get executions table columns filtered by user role.

    Args:
        role: User role (ADMIN, SUPERADMIN, USER, or None)

    Returns:
        List of column definitions appropriate for the user's role
    """
    config = get_mobile_column_config().get("executions", {})
    primary_cols = config.get("primary_columns", [])
    secondary_cols = config.get("secondary_columns", [])
    all_columns = primary_cols + secondary_cols

    # Filter out admin-only columns for non-admin users
    if role not in ["ADMIN", "SUPERADMIN"]:
        all_columns = [col for col in all_columns if col.get("field") not in ADMIN_ONLY_FIELDS]

    return all_columns


def get_mobile_column_config():
    """Get mobile-optimized column configurations for AG-Grid tables."""
    return {
        "executions": {
            "primary_columns": [
                {
                    "headerName": "Script",
                    "field": "script_name",
                    "width": 200,
                    "pinned": "left",
                    "cellStyle": {**TRUNCATED_CELL_STYLE, "fontSize": "10px"},
                    "tooltipField": "script_name",
                    "resizable": True,
                },
                {
                    "headerName": "User",
                    "field": "user_name",
                    "width": 150,
                    "cellStyle": {**TRUNCATED_CELL_STYLE, "fontSize": "12px"},
                    "tooltipField": "user_name",
                    "resizable": True,
                },
                {
                    "headerName": "Email",
                    "field": "user_email",
                    "width": 250,
                    "cellStyle": {**TRUNCATED_CELL_STYLE, "fontSize": "12px"},
                    "tooltipField": "user_email",
                    "resizable": True,
                },
                {
                    "headerName": "Start",
                    "field": "start_date",
                    "width": 160,
                    "filter": "agDateColumnFilter",
                    "cellStyle": {**TRUNCATED_CELL_STYLE, "fontSize": "12px"},
                    "tooltipField": "start_date",
                    "resizable": True,
                },
                {
                    "headerName": "End",
                    "field": "end_date",
                    "width": 160,
                    "filter": "agDateColumnFilter",
                    "cellStyle": {**TRUNCATED_CELL_STYLE, "fontSize": "12px"},
                    "tooltipField": "end_date",
                    "resizable": True,
                    "sort": "desc",
                    "sortIndex": 0,
                },
                {
                    "headerName": "Duration",
                    "field": "duration",
                    "width": 120,
                    "cellStyle": {"fontSize": "12px"},
                    "resizable": True,
                },
                {
                    "headerName": "Status",
                    "field": "status",
                    "width": 120,
                    "cellStyle": {"fontSize": "12px", "cursor": "pointer"},
                    "resizable": True,
                    "filter": "agTextColumnFilter",
                    "filterParams": {
                        "buttons": ["clear", "apply"],
                        "closeOnApply": True,
                        "caseSensitive": False,
                        "trimInput": True,
                        "debounceMs": 500,
                    },
                },
            ],
            "secondary_columns": [
                {
                    "headerName": "ID",
                    "field": "id",
                    "width": 100,
                    "cellStyle": {**TRUNCATED_CELL_STYLE, "fontSize": "11px"},
                    "tooltipField": "id",
                    "resizable": True,
                },
                {
                    "headerName": "User ID",
                    "field": "user_id",
                    "width": 100,
                    "cellStyle": {**TRUNCATED_CELL_STYLE, "fontSize": "11px"},
                    "tooltipField": "user_id",
                    "resizable": True,
                },
                {
                    "headerName": "Params",
                    "field": "params",
                    "width": 100,
                    "sortable": False,
                    "filter": False,
                    "cellStyle": {**TRUNCATED_CELL_STYLE, "fontSize": "11px"},
                    "resizable": True,
                },
                {
                    "headerName": "Results",
                    "field": "results",
                    "width": 100,
                    "sortable": False,
                    "filter": False,
                    "cellStyle": {"fontSize": "11px"},
                    "resizable": True,
                },
                {
                    "headerName": "Logs",
                    "field": "logs",
                    "width": 100,
                    "sortable": False,
                    "filter": False,
                    "cellStyle": {"fontSize": "11px"},
                    "resizable": True,
                },
                {
                    "headerName": "Docker Logs",
                    "field": "docker_logs",
                    "width": 130,
                    "sortable": False,
                    "filter": False,
                    "cellStyle": {"fontSize": "11px", "whiteSpace": "nowrap"},
                    "resizable": True,
                },
                {
                    "headerName": "Batch Logs",
                    "field": "batch_logs",
                    "width": 130,
                    "sortable": False,
                    "filter": False,
                    "cellStyle": {"fontSize": "11px", "whiteSpace": "nowrap"},
                    "resizable": True,
                },
                {
                    "headerName": "Map",
                    "field": "map",
                    "width": 100,
                    "sortable": False,
                    "filter": False,
                    "cellStyle": {"fontSize": "11px"},
                    "resizable": True,
                },
            ],
        },
        "users": {
            "primary_columns": [
                {
                    "headerName": "Email",
                    "field": "email",
                    "width": 250,
                    "pinned": "left",
                    "cellStyle": {**TRUNCATED_CELL_STYLE, "fontSize": "12px"},
                    "tooltipField": "email",
                    "resizable": True,
                },
                {
                    "headerName": "Name",
                    "field": "name",
                    "width": 180,
                    "cellStyle": {**TRUNCATED_CELL_STYLE, "fontSize": "12px"},
                    "tooltipField": "name",
                    "resizable": True,
                },
                {
                    "headerName": "Institution",
                    "field": "institution",
                    "width": 200,
                    "cellStyle": {**TRUNCATED_CELL_STYLE, "fontSize": "12px"},
                    "tooltipField": "institution",
                    "resizable": True,
                },
                {
                    "headerName": "Country",
                    "field": "country",
                    "width": 150,
                    "cellStyle": {**TRUNCATED_CELL_STYLE, "fontSize": "12px"},
                    "tooltipField": "country",
                    "resizable": True,
                },
                {
                    "headerName": "Role",
                    "field": "role",
                    "width": 120,
                    "cellStyle": {"fontSize": "12px"},
                    "resizable": True,
                    "filter": "agTextColumnFilter",
                    "filterParams": {
                        "buttons": ["clear", "apply"],
                        "closeOnApply": True,
                        "caseSensitive": False,
                        "trimInput": True,
                        "debounceMs": 500,
                    },
                },
                {
                    "headerName": "Last Activity",
                    "field": "last_activity_at",
                    "width": 150,
                    "filter": "agDateColumnFilter",
                    "cellStyle": {**TRUNCATED_CELL_STYLE, "fontSize": "12px"},
                    "tooltipField": "last_activity_at",
                    "resizable": True,
                },
                {
                    "headerName": "Verified",
                    "field": "email_verified",
                    "width": 100,
                    "cellStyle": {"fontSize": "12px", "textAlign": "center"},
                    "resizable": True,
                    "sortable": False,
                    "filter": False,
                },
                {
                    "headerName": "Verified At",
                    "field": "email_verified_at",
                    "width": 150,
                    "filter": "agDateColumnFilter",
                    "cellStyle": {**TRUNCATED_CELL_STYLE, "fontSize": "12px"},
                    "tooltipField": "email_verified_at",
                    "resizable": True,
                },
            ],
            "secondary_columns": [
                {
                    "headerName": "Created",
                    "field": "created_at",
                    "width": 150,
                    "filter": "agDateColumnFilter",
                    "cellStyle": {**TRUNCATED_CELL_STYLE, "fontSize": "12px"},
                    "tooltipField": "created_at",
                    "resizable": True,
                },
                {
                    "headerName": "Updated",
                    "field": "updated_at",
                    "width": 150,
                    "filter": "agDateColumnFilter",
                    "cellStyle": {**TRUNCATED_CELL_STYLE, "fontSize": "12px"},
                    "tooltipField": "updated_at",
                    "resizable": True,
                },
                {
                    "headerName": "ID",
                    "field": "id",
                    "width": 100,
                    "cellStyle": {**TRUNCATED_CELL_STYLE, "fontSize": "11px"},
                    "tooltipField": "id",
                    "resizable": True,
                },
                {
                    "headerName": "Edit",
                    "field": "edit",
                    "width": 100,
                    "sortable": False,
                    "filter": False,
                    "cellStyle": {"fontSize": "11px"},
                },
            ],
        },
        "scripts": {
            "primary_columns": [
                {
                    "headerName": "Name",
                    "field": "name",
                    "width": 200,
                    "pinned": "left",
                    "cellStyle": {**TRUNCATED_CELL_STYLE, "fontSize": "10px"},
                    "tooltipField": "name",
                    "resizable": True,
                },
                {
                    "headerName": "Slug",
                    "field": "slug",
                    "width": 180,
                    "cellStyle": {**TRUNCATED_CELL_STYLE, "fontSize": "11px"},
                    "tooltipField": "slug",
                    "resizable": True,
                    "filter": "agTextColumnFilter",
                    "filterParams": {
                        "buttons": ["clear", "apply"],
                        "closeOnApply": True,
                        "caseSensitive": False,
                        "trimInput": True,
                        "debounceMs": 500,
                    },
                },
                {
                    "headerName": "Access",
                    "field": "access_control",
                    "width": 100,
                    "cellStyle": {"fontSize": "11px", "textAlign": "center", "cursor": "pointer"},
                    "resizable": True,
                    "sortable": False,
                    "filter": False,
                },
                {
                    "headerName": "Status",
                    "field": "status",
                    "width": 120,
                    "cellStyle": {"fontSize": "12px"},
                    "resizable": True,
                    "filter": "agTextColumnFilter",
                    "filterParams": {
                        "buttons": ["clear", "apply"],
                        "closeOnApply": True,
                        "caseSensitive": False,
                        "trimInput": True,
                        "debounceMs": 500,
                    },
                },
                {
                    "headerName": "Environment",
                    "field": "environment",
                    "width": 180,
                    "cellStyle": {**TRUNCATED_CELL_STYLE, "fontSize": "11px"},
                    "tooltipField": "environment",
                    "resizable": True,
                    "filter": "agTextColumnFilter",
                    "filterParams": {
                        "buttons": ["clear", "apply"],
                        "closeOnApply": True,
                        "caseSensitive": False,
                        "trimInput": True,
                        "debounceMs": 500,
                    },
                },
                {
                    "headerName": "Env Version",
                    "field": "environment_version",
                    "width": 130,
                    "cellStyle": {**TRUNCATED_CELL_STYLE, "fontSize": "11px"},
                    "tooltipField": "environment_version",
                    "resizable": True,
                    "filter": "agTextColumnFilter",
                    "filterParams": {
                        "buttons": ["clear", "apply"],
                        "closeOnApply": True,
                        "caseSensitive": False,
                        "trimInput": True,
                        "debounceMs": 500,
                    },
                },
                {
                    "headerName": "Compute",
                    "field": "compute_type",
                    "width": 110,
                    "cellStyle": {"fontSize": "11px"},
                    "resizable": True,
                    "sortable": False,
                    "filter": False,
                },
                {
                    "headerName": "Created",
                    "field": "created_at",
                    "width": 150,
                    "filter": "agDateColumnFilter",
                    "cellStyle": {**TRUNCATED_CELL_STYLE, "fontSize": "12px"},
                    "tooltipField": "created_at",
                    "resizable": True,
                },
                {
                    "headerName": "Updated",
                    "field": "updated_at",
                    "width": 150,
                    "filter": "agDateColumnFilter",
                    "cellStyle": {**TRUNCATED_CELL_STYLE, "fontSize": "12px"},
                    "tooltipField": "updated_at",
                    "resizable": True,
                },
            ],
            "secondary_columns": [
                {
                    "headerName": "User",
                    "field": "user_name",
                    "width": 150,
                    "cellStyle": {**TRUNCATED_CELL_STYLE, "fontSize": "11px"},
                    "tooltipField": "user_name",
                    "resizable": True,
                },
                {
                    "headerName": "User Email",
                    "field": "user_email",
                    "width": 200,
                    "cellStyle": {**TRUNCATED_CELL_STYLE, "fontSize": "11px"},
                    "tooltipField": "user_email",
                    "resizable": True,
                    "filter": "agTextColumnFilter",
                    "filterParams": {
                        "buttons": ["clear", "apply"],
                        "closeOnApply": True,
                        "caseSensitive": False,
                        "trimInput": True,
                        "debounceMs": 500,
                    },
                },
                {
                    "headerName": "Description",
                    "field": "description",
                    "width": 200,
                    "cellStyle": {**TRUNCATED_CELL_STYLE, "fontSize": "11px"},
                    "tooltipField": "description",
                    "resizable": True,
                    "filter": False,
                },
                {
                    "headerName": "ID",
                    "field": "id",
                    "width": 100,
                    "cellStyle": {**TRUNCATED_CELL_STYLE, "fontSize": "11px"},
                    "tooltipField": "id",
                    "resizable": True,
                },
                {
                    "headerName": "Logs",
                    "field": "logs",
                    "width": 100,
                    "sortable": False,
                    "filter": False,
                    "cellStyle": {"fontSize": "11px"},
                },
                {
                    "headerName": "Edit",
                    "field": "edit",
                    "width": 100,
                    "sortable": False,
                    "filter": False,
                    "cellStyle": {"fontSize": "11px"},
                },
            ],
        },
        "rate_limit_events": {
            "primary_columns": [
                {
                    "headerName": "Occurred",
                    "field": "occurred_at",
                    "width": 180,
                    "filter": "agDateColumnFilter",
                    "sort": "desc",
                    "sortIndex": 0,
                },
                {
                    "headerName": "Type",
                    "field": "rate_limit_type",
                    "width": 120,
                    "filter": False,
                },
                {
                    "headerName": "Endpoint",
                    "field": "endpoint",
                    "width": 220,
                    "filter": False,
                    "tooltipField": "endpoint",
                    "cellStyle": TRUNCATED_CELL_STYLE,
                },
                {
                    "headerName": "Method",
                    "field": "method",
                    "width": 90,
                    "filter": False,
                },
                {
                    "headerName": "User Email",
                    "field": "user_email",
                    "width": 220,
                    "filter": False,
                    "tooltipField": "user_email",
                    "cellStyle": TRUNCATED_CELL_STYLE,
                },
                {
                    "headerName": "Role",
                    "field": "user_role",
                    "width": 120,
                    "filter": False,
                },
                {
                    "headerName": "IP Address",
                    "field": "ip_address",
                    "width": 150,
                    "filter": False,
                },
                {
                    "headerName": "Limit",
                    "field": "limit_definition",
                    "width": 200,
                    "filter": False,
                    "tooltipField": "limit_definition",
                    "cellStyle": TRUNCATED_CELL_STYLE,
                },
                {
                    "headerName": "Count",
                    "field": "limit_count_display",
                    "width": 110,
                    "filter": False,
                },
                {
                    "headerName": "Window",
                    "field": "time_window_display",
                    "width": 110,
                    "filter": False,
                },
                {
                    "headerName": "Retry After",
                    "field": "retry_after_display",
                    "width": 130,
                    "filter": False,
                },
            ],
            "secondary_columns": [
                {
                    "headerName": "User ID",
                    "field": "user_id",
                    "width": 160,
                    "filter": False,
                    "tooltipField": "user_id",
                    "cellStyle": TRUNCATED_CELL_STYLE,
                },
                {
                    "headerName": "Limiter Key",
                    "field": "limit_key",
                    "width": 220,
                    "filter": False,
                    "tooltipField": "limit_key",
                    "cellStyle": TRUNCATED_CELL_STYLE,
                },
                {
                    "headerName": "User Agent",
                    "field": "user_agent",
                    "width": 260,
                    "filter": False,
                    "tooltipField": "user_agent",
                    "cellStyle": TRUNCATED_CELL_STYLE,
                },
                {
                    "headerName": "Event ID",
                    "field": "id",
                    "width": 260,
                    "filter": False,
                    "tooltipField": "id",
                    "cellStyle": TRUNCATED_CELL_STYLE,
                },
            ],
            "default_col_def_overrides": {
                "wrapText": False,
            },
            "grid_options_overrides": {
                "rowHeight": 44,
            },
        },
        "rate_limit_breaches": {
            "primary_columns": [
                {
                    "headerName": "Status",
                    "field": "status_display",
                    "width": 120,
                    "sortable": True,
                    "filter": "agSetColumnFilter",
                    "filterParams": {
                        "values": ["Active", "Historical"],
                    },
                    "pinned": "left",
                },
                {
                    "headerName": "Occurred",
                    "field": "occurred_at",
                    "width": 180,
                    "sortable": True,
                    "filter": "agDateColumnFilter",
                    "sort": "desc",
                    "sortIndex": 0,
                },
                {
                    "headerName": "Expires",
                    "field": "expires_at_display",
                    "width": 160,
                    "sortable": True,
                    "filter": False,
                },
                {
                    "headerName": "Identifier",
                    "field": "identifier_display",
                    "width": 220,
                    "sortable": True,
                    "filter": "agTextColumnFilter",
                    "tooltipField": "identifier_display",
                    "cellStyle": TRUNCATED_CELL_STYLE,
                },
                {
                    "headerName": "Email",
                    "field": "user_email",
                    "width": 220,
                    "sortable": True,
                    "filter": "agTextColumnFilter",
                    "tooltipField": "user_email",
                    "cellStyle": TRUNCATED_CELL_STYLE,
                },
                {
                    "headerName": "Role",
                    "field": "user_role",
                    "width": 120,
                    "sortable": True,
                    "filter": "agTextColumnFilter",
                },
                {
                    "headerName": "Endpoint",
                    "field": "endpoint",
                    "width": 220,
                    "sortable": True,
                    "filter": "agTextColumnFilter",
                    "tooltipField": "endpoint",
                    "cellStyle": TRUNCATED_CELL_STYLE,
                },
                {
                    "headerName": "Method",
                    "field": "method",
                    "width": 90,
                    "sortable": True,
                    "filter": "agTextColumnFilter",
                },
                {
                    "headerName": "Limit",
                    "field": "limit_definition",
                    "width": 200,
                    "filter": False,
                    "tooltipField": "limit_definition",
                    "cellStyle": TRUNCATED_CELL_STYLE,
                },
                {
                    "headerName": "Usage",
                    "field": "limit_count_display",
                    "width": 140,
                    "filter": False,
                },
                {
                    "headerName": "Window",
                    "field": "time_window_display",
                    "width": 110,
                    "filter": False,
                },
                {
                    "headerName": "Retry After",
                    "field": "retry_after_display",
                    "width": 130,
                    "filter": False,
                },
            ],
            "secondary_columns": [
                {
                    "headerName": "IP Address",
                    "field": "ip_address",
                    "width": 160,
                    "filter": False,
                    "tooltipField": "ip_address",
                    "cellStyle": TRUNCATED_CELL_STYLE,
                },
                {
                    "headerName": "Limiter Key",
                    "field": "limit_key",
                    "width": 220,
                    "filter": False,
                    "tooltipField": "limit_key",
                    "cellStyle": TRUNCATED_CELL_STYLE,
                },
                {
                    "headerName": "Rate Limit Type",
                    "field": "rate_limit_type",
                    "width": 150,
                    "filter": False,
                },
                {
                    "headerName": "Event ID",
                    "field": "id",
                    "width": 220,
                    "filter": False,
                    "tooltipField": "id",
                    "cellStyle": TRUNCATED_CELL_STYLE,
                },
            ],
            "default_col_def_overrides": {
                "wrapText": False,
                "sortable": False,
            },
            "grid_options_overrides": {
                "rowHeight": 46,
                "rowSelection": "single",
                "suppressRowClickSelection": False,
            },
        },
    }


def register_mobile_callbacks():
    """Register clientside callbacks for mobile detection."""

    # Clientside callback to detect mobile device and screen size
    clientside_callback(
        """
        function(n_intervals) {
            if (n_intervals === 0) {
                return [false, {width: 1920, height: 1080}];
            }

            const width = window.innerWidth;
            const height = window.innerHeight;

            // Detect mobile device based on screen width and user agent
            const isMobile = width <= 768 ||
                           /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);

            return [isMobile, {width: width, height: height}];
        }
        """,
        [Output("is-mobile-store", "data"), Output("screen-size-store", "data")],
        [Input("window-size-interval", "n_intervals")],
    )
