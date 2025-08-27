"""Helper functions for the status dashboard."""

import logging

from dash import html
import requests

from trendsearth_ui.config import get_api_base

logger = logging.getLogger(__name__)


def fetch_deployment_info(api_environment):
    """Fetch deployment information from the API's health endpoint."""
    try:
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
                ]
            )
    except requests.exceptions.RequestException as e:
        logger.warning(f"Could not fetch deployment info: {e}")
    return html.Div("Deployment information not available.", className="text-muted")


def fetch_swarm_info():
    """Fetch Docker Swarm information."""
    # This is a placeholder as the swarm info endpoint might not be available
    # in all environments.
    return "Swarm info not available in this environment.", ""


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
