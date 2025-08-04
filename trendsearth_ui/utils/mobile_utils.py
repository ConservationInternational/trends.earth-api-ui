"""Utilities for mobile device detection and responsive design."""

from dash import Input, Output, clientside_callback, dcc, html


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


def get_mobile_column_config():
    """Get mobile-optimized column configurations for AG-Grid tables."""
    return {
        "executions": {
            "primary_columns": [
                {
                    "headerName": "Script",
                    "field": "script_name",
                    "flex": 2,
                    "minWidth": 200,
                    "pinned": "left",
                    "cellStyle": {"fontSize": "10px"},
                    "resizable": True,
                },
                {
                    "headerName": "User",
                    "field": "user_name",
                    "flex": 1.5,
                    "minWidth": 150,
                    "cellStyle": {"fontSize": "12px"},
                    "resizable": True,
                },
                {
                    "headerName": "Email",
                    "field": "user_email",
                    "flex": 2,
                    "minWidth": 250,
                    "cellStyle": {"fontSize": "12px"},
                    "resizable": True,
                },
                {
                    "headerName": "Start",
                    "field": "start_date",
                    "flex": 1.5,
                    "minWidth": 160,
                    "filter": "agDateColumnFilter",
                    "cellStyle": {"fontSize": "12px"},
                    "resizable": True,
                },
                {
                    "headerName": "End",
                    "field": "end_date",
                    "flex": 1.5,
                    "minWidth": 160,
                    "filter": "agDateColumnFilter",
                    "cellStyle": {"fontSize": "12px"},
                    "resizable": True,
                },
                {
                    "headerName": "Duration",
                    "field": "duration",
                    "flex": 1,
                    "minWidth": 120,
                    "cellStyle": {"fontSize": "12px"},
                    "resizable": True,
                },
                {
                    "headerName": "Status",
                    "field": "status",
                    "flex": 1,
                    "minWidth": 120,
                    "cellStyle": {"fontSize": "12px"},
                    "resizable": True,
                },
            ],
            "secondary_columns": [
                {
                    "headerName": "ID",
                    "field": "id",
                    "flex": 0.5,
                    "minWidth": 80,
                    "cellStyle": {"fontSize": "11px"},
                    "resizable": True,
                },
                {
                    "headerName": "User ID",
                    "field": "user_id",
                    "flex": 0.5,
                    "minWidth": 80,
                    "cellStyle": {"fontSize": "11px"},
                    "resizable": True,
                },
                {
                    "headerName": "Params",
                    "field": "params",
                    "flex": 1,
                    "minWidth": 100,
                    "sortable": False,
                    "filter": False,
                    "cellStyle": {"fontSize": "11px"},
                    "resizable": True,
                },
                {
                    "headerName": "Results",
                    "field": "results",
                    "flex": 1,
                    "minWidth": 100,
                    "sortable": False,
                    "filter": False,
                    "cellStyle": {"fontSize": "11px"},
                    "resizable": True,
                },
                {
                    "headerName": "Logs",
                    "field": "logs",
                    "flex": 1,
                    "minWidth": 100,
                    "sortable": False,
                    "filter": False,
                    "cellStyle": {"fontSize": "11px"},
                    "resizable": True,
                },
                {
                    "headerName": "Map",
                    "field": "map",
                    "flex": 1,
                    "minWidth": 100,
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
                    "flex": 2,
                    "minWidth": 250,
                    "pinned": "left",
                    "cellStyle": {"fontSize": "12px"},
                    "resizable": True,
                },
                {
                    "headerName": "Name",
                    "field": "name",
                    "flex": 1.5,
                    "minWidth": 180,
                    "cellStyle": {"fontSize": "12px"},
                    "resizable": True,
                },
                {
                    "headerName": "Institution",
                    "field": "institution",
                    "flex": 1.5,
                    "minWidth": 200,
                    "cellStyle": {"fontSize": "12px"},
                    "resizable": True,
                },
                {
                    "headerName": "Country",
                    "field": "country",
                    "flex": 1,
                    "minWidth": 150,
                    "cellStyle": {"fontSize": "12px"},
                    "resizable": True,
                },
                {
                    "headerName": "Created",
                    "field": "created_at",
                    "flex": 1,
                    "minWidth": 150,
                    "filter": "agDateColumnFilter",
                    "cellStyle": {"fontSize": "12px"},
                    "resizable": True,
                },
                {
                    "headerName": "Updated",
                    "field": "updated_at",
                    "flex": 1,
                    "minWidth": 150,
                    "filter": "agDateColumnFilter",
                    "cellStyle": {"fontSize": "12px"},
                    "resizable": True,
                },
                {
                    "headerName": "Role",
                    "field": "role",
                    "flex": 1,
                    "minWidth": 120,
                    "cellStyle": {"fontSize": "12px"},
                    "resizable": True,
                },
            ],
            "secondary_columns": [
                {"headerName": "ID", "field": "id", "width": 80, "cellStyle": {"fontSize": "11px"}},
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
                    "flex": 2,
                    "minWidth": 200,
                    "pinned": "left",
                    "cellStyle": {"fontSize": "10px"},
                    "resizable": True,
                },
                {
                    "headerName": "Access",
                    "field": "access_control",
                    "flex": 1,
                    "minWidth": 100,
                    "cellStyle": {"fontSize": "11px", "textAlign": "center", "cursor": "pointer"},
                    "resizable": True,
                },
                {
                    "headerName": "Status",
                    "field": "status",
                    "flex": 1,
                    "minWidth": 120,
                    "cellStyle": {"fontSize": "12px"},
                    "resizable": True,
                },
                {
                    "headerName": "Created",
                    "field": "created_at",
                    "flex": 1,
                    "minWidth": 150,
                    "filter": "agDateColumnFilter",
                    "cellStyle": {"fontSize": "12px"},
                    "resizable": True,
                },
                {
                    "headerName": "Updated",
                    "field": "updated_at",
                    "flex": 1,
                    "minWidth": 150,
                    "filter": "agDateColumnFilter",
                    "cellStyle": {"fontSize": "12px"},
                    "resizable": True,
                },
            ],
            "secondary_columns": [
                {
                    "headerName": "User",
                    "field": "user_name",
                    "flex": 1,
                    "minWidth": 150,
                    "cellStyle": {"fontSize": "11px"},
                    "resizable": True,
                },
                {
                    "headerName": "Description",
                    "field": "description",
                    "flex": 2,
                    "minWidth": 200,
                    "cellStyle": {"fontSize": "11px"},
                    "resizable": True,
                },
                {"headerName": "ID", "field": "id", "width": 80, "cellStyle": {"fontSize": "11px"}},
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
    }


def get_responsive_grid_options(is_mobile=False):
    """Get responsive AG-Grid options based on device type."""
    base_options = {
        "cacheBlockSize": 50,
        "maxBlocksInCache": 2,
        "blockLoadDebounceMillis": 500,
        "purgeClosedRowNodes": True,
        "maxConcurrentDatasourceRequests": 1,
        "enableCellTextSelection": True,
        "ensureDomOrder": True,
        "animateRows": False,  # Disable animations for better performance
        "suppressMenuHide": True,  # Keep menu visible
        "suppressColumnVirtualisation": False,
    }

    if is_mobile:
        # Mobile-specific options with AG-Grid responsive features
        base_options.update(
            {
                "suppressColumnVirtualisation": True,  # Show all columns, allow horizontal scroll
                "suppressHorizontalScroll": False,  # Enable horizontal scrolling
                "alwaysShowHorizontalScroll": True,  # Always show horizontal scroll bar
                "suppressRowVirtualisation": False,  # Keep row virtualization for performance
                "rowHeight": 40,  # Larger row height for touch targets
                "headerHeight": 36,  # Larger header height for touch targets
                "animateRows": False,  # Disable animations on mobile
                "suppressColumnMoveAnimation": True,  # Disable column move animations
                "suppressScrollOnNewData": True,  # Don't auto-scroll on new data
                "suppressDragLeaveHidesColumns": True,  # Don't hide columns when dragging
                "suppressColumnResize": False,  # Allow column resizing
                "suppressAutoSize": False,  # Allow auto-sizing
                "skipHeaderOnAutoSize": False,  # Include header when auto-sizing
                "suppressSizeToFit": False,  # Enable size to fit
            }
        )
    else:
        # Desktop options (no enterprise features)
        base_options.update(
            {
                "suppressHorizontalScroll": False,
                "rowHeight": 32,
                "headerHeight": 32,
                "suppressColumnResize": False,
            }
        )

    return base_options


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
