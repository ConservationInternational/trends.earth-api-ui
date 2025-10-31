"""Utility functions for fetching and processing stats data from the API.

NOTE: Caching is handled by StatusDataManager. These functions are pure API fetch utilities.
"""

import requests

from ..config import get_api_base
from .http_client import apply_default_headers
from .logging_config import get_logger, log_error


def check_stats_access(role):
    """Check if the user role has access to statistics."""
    return role == "SUPERADMIN"  # Only SUPERADMIN users can access stats endpoints


def map_period_to_api_period(ui_period):
    """Map UI time period to API-compatible period string."""
    mapping = {
        "day": "last_day",
        "week": "last_week",
        "month": "last_month",
        "year": "last_year",
        "all": "all",
    }
    return mapping.get(ui_period, "last_week")


def get_optimal_grouping_for_period(period):
    """
    Get optimal group_by parameter for the given time period.

    Args:
        period: Time period (last_day, last_week, last_month, last_year, all)

    Returns:
        tuple: (user_group_by, execution_group_by) optimal for the period

    Note:
        User stats API accepts: quarter_hour, hour, day, week, month
        Execution stats API accepts: hour, day, week, month
        We use compatible values to prevent API errors.
    """
    mapping = {
        "last_day": ("quarter_hour", "quarter_hour"),
        "last_week": ("hour", "hour"),
        "last_month": ("day", "day"),
        "last_year": ("week", "week"),
        "all": ("month", "month"),
    }
    return mapping.get(period, ("month", "month"))


def fetch_dashboard_stats(
    token, api_environment="production", period="last_week", include_sections=None
):
    """
    Fetch dashboard statistics from the API.

    Args:
        token: JWT authentication token
        api_environment: API environment (production/staging)
        period: Time period (last_day, last_week, last_month, last_year, all)
        include_sections: List of sections to include (summary, trends, geographic, tasks)

    Returns:
        dict: Dashboard statistics data or None if error
    """
    import logging

    logger = logging.getLogger(__name__)

    # Enhanced logging for debugging
    logger.info(
        f"Dashboard stats: Fetching data for period={period}, environment={api_environment}"
    )
    if token:
        token_length = len(token)
        token_segments = len(token.split("."))
        logger.info(f"Dashboard stats: token length={token_length}, segments={token_segments}")
    else:
        logger.warning("Dashboard stats: No token provided")
        return {"error": "Authentication token not provided"}

    headers = apply_default_headers({"Authorization": f"Bearer {token}"})
    params = {"period": period}

    if include_sections:
        params["include"] = ",".join(include_sections)

    try:
        resp = requests.get(
            f"{get_api_base(api_environment)}/stats/dashboard",
            headers=headers,
            params=params,
            timeout=15,  # Increased timeout for potentially large queries
        )

        # Log response status and headers for debugging
        logger.info(f"Dashboard stats: API response status: {resp.status_code}")
        logger.debug(f"Dashboard stats: API response headers: {resp.headers}")

        if resp.status_code == 200:
            data = resp.json()
            logger.info(f"Dashboard stats: Successfully fetched data for {period}")
            return data
        elif resp.status_code == 401:
            logger.warning("Dashboard stats: Unauthorized access (401). Check token.")
            return {"error": True, "message": "Unauthorized access", "status_code": 401}
        elif resp.status_code == 403:
            logger.warning("Dashboard stats: Forbidden access (403). Check permissions.")
            return {
                "error": True,
                "message": "Forbidden access - SUPERADMIN privileges required",
                "status_code": 403,
            }
        else:
            log_error(
                logger,
                f"Dashboard stats: Failed to fetch data. Status: {resp.status_code}, Body: {resp.text}",
            )
            return {
                "error": True,
                "message": f"API error with status code {resp.status_code}",
                "status_code": resp.status_code,
            }
    except requests.exceptions.RequestException as e:
        log_error(logger, f"Dashboard stats: Request failed: {e}")
        return {"error": True, "message": f"Request failed: {e}", "status_code": "network_error"}


def fetch_scripts_count(token, api_environment="production"):
    """
    Fetch total scripts count from the API.

    Args:
        token: JWT authentication token
        api_environment: API environment (production/staging)

    Returns:
        int: Total number of scripts or 0 if error
    """
    import logging

    logger = logging.getLogger(__name__)

    logger.info(f"Scripts count: Fetching data for environment={api_environment}")

    if not token:
        logger.warning("Scripts count: No token provided")
        return 0

    headers = apply_default_headers({"Authorization": f"Bearer {token}"})
    # Use pagination to get the total count without downloading all script data
    params = {"page": 1, "per_page": 1}  # Minimal data transfer

    try:
        resp = requests.get(
            f"{get_api_base(api_environment)}/script",
            headers=headers,
            params=params,
            timeout=10,
        )

        logger.info(f"Scripts count: API response status: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            # Extract total count from paginated response
            total_count = data.get("total", len(data.get("data", [])))
            logger.info(f"Scripts count: Successfully fetched {total_count} scripts")
            return total_count
        else:
            logger.warning(f"Scripts count: Failed to fetch. Status: {resp.status_code}")
            return 0
    except requests.exceptions.RequestException as e:
        log_error(logger, f"Scripts count: Request failed: {e}")
        return 0


def fetch_user_stats(
    token, api_environment="production", period="last_week", group_by=None, country=None
):
    """
    Fetch user statistics from the API.

    Args:
        token: JWT authentication token
        api_environment: API environment (production/staging)
        period: Time period (last_day, last_week, last_month, last_year, all)
        group_by: Grouping interval (day, week, month) for time series data
        country: Filter by specific country

    Returns:
        dict: User statistics data or None if error
    """
    logger = get_logger()

    logger.info(
        f"User stats: Fetching data for period={period}, group_by={group_by}, country={country}, environment={api_environment}"
    )
    if not token:
        logger.warning("User stats: No token provided")
        return {"error": "Authentication token not provided"}

    headers = apply_default_headers({"Authorization": f"Bearer {token}"})
    params = {"period": period}

    # Add optional parameters if provided
    if group_by:
        params["group_by"] = group_by
    if country:
        params["country"] = country

    try:
        resp = requests.get(
            f"{get_api_base(api_environment)}/stats/users",
            headers=headers,
            params=params,
            timeout=10,
        )

        logger.info(f"User stats: API response status: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            logger.info(
                f"User stats: Successfully fetched data for {period}, group_by {group_by}, country {country}"
            )
            return data
        elif resp.status_code == 401:
            logger.warning("User stats: Unauthorized access (401). Check token.")
            return {"error": True, "message": "Unauthorized access", "status_code": 401}
        elif resp.status_code == 403:
            logger.warning("User stats: Forbidden access (403). Check permissions.")
            return {
                "error": True,
                "message": "Forbidden access - SUPERADMIN privileges required",
                "status_code": 403,
            }
        else:
            log_error(
                logger,
                f"User stats: Failed to fetch data. Status: {resp.status_code}, Body: {resp.text}",
            )
            return {
                "error": True,
                "message": f"API error with status code {resp.status_code}",
                "status_code": resp.status_code,
            }
    except requests.exceptions.RequestException as e:
        log_error(logger, f"User stats: Request failed: {e}")
        return {"error": True, "message": f"Request failed: {e}", "status_code": "network_error"}


def fetch_execution_stats(
    token,
    api_environment="production",
    period="last_week",
    group_by=None,
    task_type=None,
    status=None,
):
    """
    Fetch execution statistics from the API.

    Args:
        token: JWT authentication token
        api_environment: API environment (production/staging)
        period: Time period (last_day, last_week, last_month, last_year, all)
        group_by: Grouping interval (hour, day, week, month) for time series data
        task_type: Filter by specific task type
        status: Filter by execution status (PENDING, RUNNING, FINISHED, FAILED, CANCELLED)

    Returns:
        dict: Execution statistics data or None if error
    """
    logger = get_logger()

    logger.info(
        f"Execution stats: Fetching data for period={period}, group_by={group_by}, task_type={task_type}, status={status}, environment={api_environment}"
    )
    if not token:
        logger.warning("Execution stats: No token provided")
        return {"error": "Authentication token not provided"}

    headers = apply_default_headers({"Authorization": f"Bearer {token}"})
    params = {"period": period}

    # Add optional parameters if provided
    if group_by:
        params["group_by"] = group_by
    if task_type:
        params["task_type"] = task_type
    if status:
        params["status"] = status

    try:
        resp = requests.get(
            f"{get_api_base(api_environment)}/stats/executions",
            headers=headers,
            params=params,
            timeout=10,
        )

        logger.info(f"Execution stats: API response status: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            logger.info(
                f"Execution stats: Successfully fetched data for {period}, group_by {group_by}, task_type {task_type}, status {status}"
            )
            return data
        elif resp.status_code == 401:
            logger.warning("Execution stats: Unauthorized access (401). Check token.")
            return {"error": True, "message": "Unauthorized access", "status_code": 401}
        elif resp.status_code == 403:
            logger.warning("Execution stats: Forbidden access (403). Check permissions.")
            return {
                "error": True,
                "message": "Forbidden access - SUPERADMIN privileges required",
                "status_code": 403,
            }
        else:
            log_error(
                logger,
                f"Execution stats: Failed to fetch data. Status: {resp.status_code}, Body: {resp.text}",
            )
            return {
                "error": True,
                "message": f"API error with status code {resp.status_code}",
                "status_code": resp.status_code,
            }
    except requests.exceptions.RequestException as e:
        log_error(logger, f"Execution stats: Request failed: {e}")
        return {"error": True, "message": f"Request failed: {e}", "status_code": "network_error"}
