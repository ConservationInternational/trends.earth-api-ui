"""Helper functions for the status dashboard."""

from datetime import datetime
import logging
import time

from dash import html
import requests

from .http_client import apply_default_headers
from trendsearth_ui.config import get_api_base
from trendsearth_ui.utils.stats_visualizations import create_docker_swarm_status_table
from trendsearth_ui.utils.timezone_utils import format_local_time, get_safe_timezone

logger = logging.getLogger(__name__)


def _create_commit_link(commit_sha, repo_url):
    """Create a GitHub commit link from a commit SHA and repository URL."""
    if commit_sha != "unknown" and len(commit_sha) >= 7:
        return html.A(
            commit_sha[:7],
            href=f"{repo_url}/commit/{commit_sha}",
            target="_blank",
            className="text-primary",
        )
    else:
        return commit_sha


def _fetch_health_status(url, headers=None, timeout=10):
    """
    Fetch health status from a given URL with retry logic.

    Returns:
        tuple: (success: bool, data: dict, status_code: int, error_msg: str)
    """
    max_retries = 2
    retry_delay = 1  # seconds

    merged_headers = apply_default_headers(headers)

    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(url, headers=merged_headers, timeout=timeout)
            if resp.status_code == 200:
                return True, resp.json(), resp.status_code, None
            else:
                # Don't retry on client errors (4xx), only on server errors or network issues
                if resp.status_code < 500:
                    return False, None, resp.status_code, f"HTTP {resp.status_code}"
                # For 5xx errors, log and potentially retry
                if attempt < max_retries:
                    logger.warning(
                        f"Health check failed with {resp.status_code}, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries + 1})"
                    )
                    time.sleep(retry_delay)
                    continue
                return False, None, resp.status_code, f"HTTP {resp.status_code}"
        except requests.exceptions.Timeout:
            if attempt < max_retries:
                logger.warning(
                    f"Health check timeout for {url}, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries + 1})"
                )
                time.sleep(retry_delay)
                continue
            logger.warning(f"Health check timed out for {url} after {max_retries + 1} attempts")
            return False, None, 0, "Timeout"
        except requests.exceptions.ConnectionError:
            if attempt < max_retries:
                logger.warning(
                    f"Connection error for {url}, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries + 1})"
                )
                time.sleep(retry_delay)
                continue
            logger.warning(f"Connection failed for {url} after {max_retries + 1} attempts")
            return False, None, 0, "Connection Error"
        except Exception as e:
            # For other exceptions, retry if it might be transient
            if attempt < max_retries and (
                "timeout" in str(e).lower() or "connection" in str(e).lower()
            ):
                logger.warning(
                    f"Health check failed for {url}, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries + 1}): {e}"
                )
                time.sleep(retry_delay)
                continue
            logger.warning(f"Could not fetch health status from {url}: {e}")
            return False, None, 0, "Connection Error"

    return False, None, 0, "Connection Error"


def _create_service_info(
    service_name, deployment_prefix, success, data, status_code, error_msg, repo_url
):
    """
    Create service information display based on health check results.

    Args:
        service_name: Display name for the service (e.g., "Trends.Earth API")
        deployment_prefix: Prefix for deployment info (e.g., "API Deployment")
        success: Whether the health check succeeded
        data: Health check response data (if successful)
        status_code: HTTP status code
        error_msg: Error message (if failed)
        repo_url: GitHub repository URL for commit links
    """
    if success and data:
        deployment = data.get("deployment", {})
        commit_sha = deployment.get("commit_sha", "unknown")
        branch = deployment.get("branch", "unknown")
        environment = deployment.get("environment", "unknown")

        commit_link = _create_commit_link(commit_sha, repo_url)

        # Create status line with service-specific information
        status_parts = [f"Status: {data.get('status', 'unknown').upper()}"]
        if "database" in data:
            status_parts.append(f"DB: {data.get('database', 'unknown')}")

        return html.Div(
            [
                html.P(
                    [html.Strong(f"{service_name}: "), ", ".join(status_parts)],
                    className="mb-1",
                ),
                html.P(
                    [
                        html.Strong(f"{deployment_prefix}: "),
                        f"Branch: {branch}, Commit: ",
                        commit_link,
                        f", Env: {environment}",
                    ],
                    className="mb-1 small text-muted",
                ),
            ]
        )
    else:
        # Extract service type (e.g., "API" from "Trends.Earth API")
        service_type = service_name.split()[-1]  # Gets "API" or "UI"

        # Format error message to match expected test format
        if status_code > 0:
            message = f"{service_type} Health: Error ({status_code})"
        else:
            message = f"{service_type} Health: {error_msg}"

        return html.P(
            message,
            className="mb-1 text-warning" if status_code != 0 else "mb-1 text-danger",
        )


def fetch_deployment_info(api_environment, token=None):
    """Fetch deployment information from both API and UI health endpoints."""
    if not token:
        # Return basic environment info if no token available
        return html.Div(
            [
                html.P(f"Environment: {api_environment.title()}", className="mb-1"),
                html.P("API Status: Authentication required", className="mb-1 text-muted"),
                html.P("Please log in to view deployment status", className="mb-1 text-muted"),
            ]
        )

    # GitHub repository URLs for linking commits
    API_REPO_URL = "https://github.com/ConservationInternational/trends.earth-API"
    UI_REPO_URL = "https://github.com/ConservationInternational/trends.earth-api-ui"

    # Fetch API health info (public endpoint, no auth required)
    # API health endpoint is at the root level, not under /api/v1
    api_url = f"{get_api_base(api_environment).removesuffix('/api/v1')}/api-health"
    api_success, api_data, api_status, api_error = _fetch_health_status(api_url)

    api_info = _create_service_info(
        "Trends.Earth API",
        "API Deployment",
        api_success,
        api_data,
        api_status,
        api_error,
        API_REPO_URL,
    )

    # Fetch UI health info
    # Check if the UI is deployed on the same domain as the API
    ui_url = f"{get_api_base(api_environment).removesuffix('/api/v1')}/api-ui-health"

    ui_success, ui_data, ui_status, ui_error = _fetch_health_status(ui_url)

    ui_info = _create_service_info(
        "Trends.Earth UI", "UI Deployment", ui_success, ui_data, ui_status, ui_error, UI_REPO_URL
    )

    # Combine the information
    return html.Div(
        [
            html.P(f"Environment: {api_environment.title()}", className="mb-2 fw-bold"),
            api_info or html.P("API status unavailable", className="mb-1 text-muted"),
            ui_info or html.P("UI status unavailable", className="mb-1 text-muted"),
        ]
    )


def fetch_swarm_info(api_environment, token=None, user_timezone=None):
    """Fetch Docker Swarm information from the API's swarm status endpoint."""
    if not token:
        # Return basic info if no token available
        swarm_info = html.Div(
            [
                html.P("Authentication required", className="mb-1 text-muted"),
                html.P("Please log in to view swarm status", className="mb-1 text-muted"),
            ]
        )
        return swarm_info, " (Auth Required)"

    safe_timezone = get_safe_timezone(user_timezone)

    try:
        # Fetch raw swarm data from API
        headers = apply_default_headers({"Authorization": f"Bearer {token}"})
        swarm_url = f"{get_api_base(api_environment)}/status/swarm"
        resp = requests.get(
            swarm_url,
            headers=headers,
            timeout=5,
        )

        if resp.status_code == 200:
            swarm_response = resp.json()
            swarm_data = swarm_response.get("data", {})
            swarm_info = create_docker_swarm_status_table(swarm_data)
            cache_info = swarm_data.get("cache_info", {})
            cached_at_raw = cache_info.get("cached_at")

            swarm_cached_time = " (Live)"
            if isinstance(cached_at_raw, str) and cached_at_raw:
                try:
                    cached_dt = datetime.fromisoformat(cached_at_raw.replace("Z", "+00:00"))
                    formatted_time, tz_abbrev = format_local_time(cached_dt, safe_timezone)
                    if tz_abbrev and tz_abbrev != "UTC":
                        swarm_cached_time = f" (Updated: {formatted_time} {tz_abbrev})"
                    else:
                        iso_timestamp = cached_at_raw[:19] if "T" in cached_at_raw else formatted_time
                        swarm_cached_time = f" (Updated: {iso_timestamp})"
                except (ValueError, TypeError):
                    # Fallback to original string if parsing fails
                    swarm_cached_time = f" (Updated: {cached_at_raw[:19]})"
            return swarm_info, swarm_cached_time
        elif resp.status_code == 401:
            # Handle authentication error
            swarm_info = html.Div(
                [
                    html.P("Authentication failed", className="mb-1 text-warning"),
                    html.P("Please check your login status", className="mb-1 text-muted"),
                ]
            )
            return swarm_info, " (Auth Error)"
        elif resp.status_code == 403:
            # Handle permission error
            swarm_info = html.Div(
                [
                    html.P("Access denied", className="mb-1 text-warning"),
                    html.P(
                        "Admin privileges required for swarm status",
                        className="mb-1 text-muted",
                    ),
                ]
            )
            return swarm_info, " (Access Denied)"
        else:
            # Handle other errors
            swarm_info = html.Div(
                [
                    html.P(
                        f"Swarm Status: Error ({resp.status_code})",
                        className="mb-1 text-danger",
                    ),
                    html.P("Unable to retrieve swarm information", className="mb-1 text-muted"),
                ]
            )
            return swarm_info, " (Error)"
    except Exception as e:
        # Handle connection errors
        logger.error(f"Error fetching swarm data: {e}")
        swarm_info = html.Div(
            [
                html.P("Swarm Status: Connection Error", className="mb-1 text-danger"),
                html.P("Unable to reach swarm status endpoint", className="mb-1 text-muted"),
            ]
        )
        return swarm_info, " (Connection Error)"


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
    headers = apply_default_headers({"Authorization": f"Bearer {token}"})
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
