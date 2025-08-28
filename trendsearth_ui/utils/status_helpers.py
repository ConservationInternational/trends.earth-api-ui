"""Helper functions for the status dashboard."""

import logging

from dash import html
import requests

from trendsearth_ui.config import get_api_base

logger = logging.getLogger(__name__)


def fetch_deployment_info(api_environment, token=None):
    """Fetch deployment information from the API's health endpoint."""
    if not token:
        # Return basic environment info if no token available
        return html.Div(
            [
                html.P(f"Environment: {api_environment.title()}", className="mb-1"),
                html.P("API Status: Authentication required", className="mb-1 text-muted"),
                html.P("Please log in to view health status", className="mb-1 text-muted"),
            ]
        )

    try:
        # Use the documented /api/v1/stats/health endpoint
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(
            f"{get_api_base(api_environment)}/stats/health",
            headers=headers,
            timeout=5,
        )

        if resp.status_code == 200:
            return html.Div(
                [
                    html.P(f"Environment: {api_environment.title()}", className="mb-1"),
                    html.P("Health Status: OK", className="mb-1 text-success"),
                    html.P("Stats Service: Available", className="mb-1 text-success"),
                ]
            )
        elif resp.status_code == 401:
            return html.Div(
                [
                    html.P(f"Environment: {api_environment.title()}", className="mb-1"),
                    html.P("Authentication failed", className="mb-1 text-warning"),
                    html.P("Please check your login status", className="mb-1 text-muted"),
                ]
            )
        elif resp.status_code == 403:
            return html.Div(
                [
                    html.P(f"Environment: {api_environment.title()}", className="mb-1"),
                    html.P("Access denied", className="mb-1 text-warning"),
                    html.P("Admin privileges required", className="mb-1 text-muted"),
                ]
            )
        else:
            return html.Div(
                [
                    html.P(f"Environment: {api_environment.title()}", className="mb-1"),
                    html.P(
                        f"Health Status: Error ({resp.status_code})", className="mb-1 text-danger"
                    ),
                    html.P("Stats service unavailable", className="mb-1 text-muted"),
                ]
            )

    except requests.exceptions.RequestException as e:
        logger.warning(f"Could not fetch deployment info: {e}")
        return html.Div(
            [
                html.P(f"Environment: {api_environment.title()}", className="mb-1"),
                html.P("API Status: Connection Error", className="mb-1 text-danger"),
                html.P("Unable to reach stats service", className="mb-1 text-muted"),
            ]
        )


def fetch_swarm_info(api_environment, token=None):
    """Fetch Docker Swarm information from the API's swarm status endpoint."""
    if not token:
        return html.Div(
            [
                html.P("Swarm information requires authentication", className="mb-1 text-muted"),
                html.P("Please log in to view swarm status", className="mb-1 text-muted"),
            ]
        ), " (Auth Required)"

    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(
            f"{get_api_base(api_environment)}/status/swarm",
            headers=headers,
            timeout=5,
        )

        if resp.status_code == 200:
            data = resp.json().get("data", {})

            # Check if swarm is active
            swarm_active = data.get("swarm_active", False)
            error = data.get("error")
            cache_info = data.get("cache_info", {})
            cached_at = cache_info.get("cached_at", "")

            if not swarm_active or error:
                # Handle non-swarm or error cases
                error_msg = error or "Not in swarm mode"
                return html.Div(
                    [
                        html.P(f"Swarm Status: {error_msg}", className="mb-1 text-warning"),
                        html.P(f"Total Nodes: {data.get('total_nodes', 0)}", className="mb-1"),
                        html.P(
                            f"Cache Updated: {cached_at[:19] if cached_at else 'N/A'}",
                            className="mb-1 text-muted",
                        ),
                    ]
                ), " (Inactive)"

            # Display swarm information
            total_nodes = data.get("total_nodes", 0)
            total_managers = data.get("total_managers", 0)
            total_workers = data.get("total_workers", 0)
            nodes = data.get("nodes", [])

            info_lines = [
                html.P("Swarm Active: Yes", className="mb-1 text-success"),
                html.P(f"Total Nodes: {total_nodes}", className="mb-1"),
                html.P(f"Managers: {total_managers}, Workers: {total_workers}", className="mb-1"),
            ]

            # Add node details if available
            if nodes:
                active_nodes = [n for n in nodes if n.get("state") == "ready"]
                info_lines.append(
                    html.P(f"Active Nodes: {len(active_nodes)}/{total_nodes}", className="mb-1")
                )

                # Show resource usage if available
                total_cpu = sum(n.get("cpu_count", 0) for n in nodes)
                total_memory = sum(n.get("memory_gb", 0) for n in nodes)
                if total_cpu > 0 or total_memory > 0:
                    info_lines.append(
                        html.P(
                            f"Total Resources: {total_cpu} CPUs, {total_memory:.1f}GB",
                            className="mb-1",
                        )
                    )

            if cached_at:
                info_lines.append(
                    html.P(f"Cache Updated: {cached_at[:19]}", className="mb-1 text-muted")
                )

            return html.Div(info_lines), " (Live)"

        elif resp.status_code == 401:
            return html.Div(
                [
                    html.P("Authentication failed", className="mb-1 text-warning"),
                    html.P("Please check your login status", className="mb-1 text-muted"),
                ]
            ), " (Auth Error)"
        elif resp.status_code == 403:
            return html.Div(
                [
                    html.P("Access denied", className="mb-1 text-warning"),
                    html.P(
                        "Admin privileges required for swarm status", className="mb-1 text-muted"
                    ),
                ]
            ), " (Access Denied)"
        else:
            return html.Div(
                [
                    html.P(
                        f"Swarm Status: Error ({resp.status_code})", className="mb-1 text-danger"
                    ),
                    html.P("Unable to retrieve swarm information", className="mb-1 text-muted"),
                ]
            ), " (Error)"

    except requests.exceptions.RequestException as e:
        logger.warning(f"Could not fetch swarm info: {e}")
        return html.Div(
            [
                html.P("Swarm Status: Connection Error", className="mb-1 text-danger"),
                html.P("Unable to reach swarm status endpoint", className="mb-1 text-muted"),
            ]
        ), " (Connection Error)"


def get_fallback_summary():
    """Provide a fallback summary if the main status endpoint fails."""
    return html.Div(
        [
            "System status is currently unavailable. Please try again later.",
        ],
        className="text-center text-warning p-3",
    )


def is_status_endpoint_available(token, api_environment):
    """Check if the /status endpoint is available and returns data."""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get(
            f"{get_api_base(api_environment)}/status",
            headers=headers,
            params={"per_page": 1},
            timeout=3,
        )
        return resp.status_code == 200 and resp.json().get("data")
    except requests.exceptions.RequestException:
        return False
