"""Helper functions for the status dashboard."""

import logging

from dash import html
import requests

from trendsearth_ui.config import get_api_base

logger = logging.getLogger(__name__)


def fetch_deployment_info(api_environment, token=None):
    """Fetch deployment information from the API's health endpoint."""
    try:
        # First try the /api-health endpoint (usually public)
        resp = requests.get(
            f"{get_api_base(api_environment)}/api-health",
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            return html.Div(
                [
                    html.P(f"API Version: {data.get('version', 'N/A')}", className="mb-1"),
                    html.P(f"Environment: {data.get('environment', 'N/A')}", className="mb-1"),
                    html.P(f"Status: {data.get('status', 'N/A')}", className="mb-1"),
                ]
            )

        # If that fails, try the root health endpoint
        root_resp = requests.get(
            f"{get_api_base(api_environment).replace('/api/v1', '')}/api-ui-health",
            timeout=5,
        )
        if root_resp.status_code == 200:
            root_data = root_resp.json()
            deployment = root_data.get("deployment", {})
            return html.Div(
                [
                    html.P(
                        f"Environment: {deployment.get('environment', 'N/A')}", className="mb-1"
                    ),
                    html.P(f"Branch: {deployment.get('branch', 'N/A')}", className="mb-1"),
                    html.P(f"Status: {root_data.get('status', 'N/A')}", className="mb-1"),
                ]
            )

        # If both fail, try authenticated endpoint
        if token:
            headers = {"Authorization": f"Bearer {token}"}
            auth_resp = requests.get(
                f"{get_api_base(api_environment)}/health",
                headers=headers,
                timeout=5,
            )
            if auth_resp.status_code == 200:
                auth_data = auth_resp.json()
                return html.Div(
                    [
                        html.P(f"API Status: {auth_data.get('status', 'N/A')}", className="mb-1"),
                        html.P(f"Environment: {api_environment.title()}", className="mb-1"),
                        html.P(f"Timestamp: {auth_data.get('timestamp', 'N/A')}", className="mb-1"),
                    ]
                )

    except requests.exceptions.RequestException as e:
        logger.warning(f"Could not fetch deployment info: {e}")

    # Fallback with basic environment info
    return html.Div(
        [
            html.P(f"Environment: {api_environment.title()}", className="mb-1"),
            html.P("API Status: Unknown", className="mb-1 text-muted"),
            html.P("Deployment info not available", className="mb-1 text-muted"),
        ]
    )


def fetch_swarm_info():
    """Fetch Docker Swarm information."""
    # Try to get system information from local environment or API
    try:
        import os
        import platform

        # Get basic system information
        system_info = {
            "platform": platform.system(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
        }

        # Check for container environment indicators
        is_containerized = (
            os.path.exists("/.dockerenv")
            or os.environ.get("DOCKER_CONTAINER")
            or os.environ.get("KUBERNETES_SERVICE_HOST")
        )

        # Check for swarm/cluster environment variables
        cluster_info = []
        if os.environ.get("DOCKER_SWARM_MODE"):
            cluster_info.append(f"Swarm Mode: {os.environ.get('DOCKER_SWARM_MODE')}")
        if os.environ.get("KUBERNETES_SERVICE_HOST"):
            cluster_info.append("Kubernetes cluster detected")
        if os.environ.get("ECS_CONTAINER_METADATA_URI"):
            cluster_info.append("AWS ECS deployment")

        if is_containerized or cluster_info:
            info_lines = []
            if is_containerized:
                info_lines.append("Containerized environment detected")
            info_lines.extend(cluster_info)
            info_lines.append(
                f"Platform: {system_info['platform']} ({system_info['architecture']})"
            )

            return html.Div([html.P(line, className="mb-1") for line in info_lines]), " (Live)"
        else:
            return html.Div(
                [
                    html.P("Non-containerized environment", className="mb-1"),
                    html.P(
                        f"Platform: {system_info['platform']} ({system_info['architecture']})",
                        className="mb-1",
                    ),
                    html.P(f"Python: {system_info['python_version']}", className="mb-1"),
                ]
            ), " (Live)"

    except Exception as e:
        logger.warning(f"Could not fetch system info: {e}")
        return html.Div(
            [
                html.P("System information not available", className="mb-1 text-muted"),
                html.P("Unable to detect deployment environment", className="mb-1 text-muted"),
            ]
        ), " (Error)"


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
