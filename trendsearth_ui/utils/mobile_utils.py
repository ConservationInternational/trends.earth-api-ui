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
                {"headerName": "Script", "field": "script_name", "width": 150, "pinned": "left"},
                {"headerName": "Status", "field": "status", "width": 100, "pinned": "left"},
                {
                    "headerName": "Start",
                    "field": "start_date",
                    "width": 120,
                    "filter": "agDateColumnFilter",
                },
            ],
            "secondary_columns": [
                {"headerName": "User", "field": "user_name", "width": 120},
                {"headerName": "Email", "field": "user_email", "width": 180},
                {
                    "headerName": "End",
                    "field": "end_date",
                    "width": 120,
                    "filter": "agDateColumnFilter",
                },
                {"headerName": "Duration", "field": "duration", "width": 100},
                {"headerName": "ID", "field": "id", "width": 80},
                {"headerName": "User ID", "field": "user_id", "width": 80},
                {
                    "headerName": "Params",
                    "field": "params",
                    "width": 80,
                    "sortable": False,
                    "filter": False,
                },
                {
                    "headerName": "Results",
                    "field": "results",
                    "width": 80,
                    "sortable": False,
                    "filter": False,
                },
                {
                    "headerName": "Logs",
                    "field": "logs",
                    "width": 80,
                    "sortable": False,
                    "filter": False,
                },
                {
                    "headerName": "Map",
                    "field": "map",
                    "width": 80,
                    "sortable": False,
                    "filter": False,
                },
            ],
        },
        "users": {
            "primary_columns": [
                {"headerName": "Email", "field": "email", "width": 200, "pinned": "left"},
                {"headerName": "Name", "field": "name", "width": 150, "pinned": "left"},
                {"headerName": "Role", "field": "role", "width": 100},
            ],
            "secondary_columns": [
                {"headerName": "Institution", "field": "institution", "width": 180},
                {"headerName": "Country", "field": "country", "width": 120},
                {
                    "headerName": "Created",
                    "field": "created_at",
                    "width": 120,
                    "filter": "agDateColumnFilter",
                },
                {
                    "headerName": "Updated",
                    "field": "updated_at",
                    "width": 120,
                    "filter": "agDateColumnFilter",
                },
                {"headerName": "ID", "field": "id", "width": 80},
                {
                    "headerName": "Edit",
                    "field": "edit",
                    "width": 80,
                    "sortable": False,
                    "filter": False,
                },
            ],
        },
        "scripts": {
            "primary_columns": [
                {"headerName": "Name", "field": "name", "width": 150, "pinned": "left"},
                {"headerName": "Status", "field": "status", "width": 100, "pinned": "left"},
                {"headerName": "User", "field": "user_name", "width": 120},
            ],
            "secondary_columns": [
                {"headerName": "Description", "field": "description", "width": 200},
                {
                    "headerName": "Created",
                    "field": "created_at",
                    "width": 120,
                    "filter": "agDateColumnFilter",
                },
                {
                    "headerName": "Updated",
                    "field": "updated_at",
                    "width": 120,
                    "filter": "agDateColumnFilter",
                },
                {"headerName": "ID", "field": "id", "width": 80},
                {
                    "headerName": "Logs",
                    "field": "logs",
                    "width": 80,
                    "sortable": False,
                    "filter": False,
                },
                {
                    "headerName": "Edit",
                    "field": "edit",
                    "width": 80,
                    "sortable": False,
                    "filter": False,
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
        "suppressHorizontalScroll": False,
        "suppressColumnVirtualisation": False,
    }

    if is_mobile:
        # Mobile-specific options
        base_options.update(
            {
                "suppressColumnVirtualisation": True,  # Show all columns, allow horizontal scroll
                "suppressHorizontalScroll": False,  # Enable horizontal scrolling
                "alwaysShowHorizontalScroll": True,  # Always show horizontal scroll bar
                "suppressRowVirtualisation": False,  # Keep row virtualization for performance
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
