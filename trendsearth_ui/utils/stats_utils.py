"""Utility functions for fetching and processing stats data from the API."""

import time

import requests

from ..config import get_api_base

# Cache for stats data with TTL
_stats_cache = {
    "dashboard": {"data": None, "timestamp": 0, "ttl": 300},  # 5 minutes
    "users": {"data": {}, "timestamp": 0, "ttl": 300},  # 5 minutes
    "executions": {"data": {}, "timestamp": 0, "ttl": 300},  # 5 minutes
}


def get_cached_stats_data(cache_key, period=None, ttl=None):
    """Get cached stats data if still valid."""
    cache_entry = _stats_cache.get(cache_key, {})
    if ttl is None:
        ttl = cache_entry.get("ttl", 300)

    current_time = time.time()

    # For data that varies by period, use period as sub-key
    if period:
        cache_data = cache_entry.get("data", {})
        if (
            isinstance(cache_data, dict)
            and period in cache_data
            and current_time - cache_entry.get("timestamp", 0) < ttl
        ):
            return cache_data[period]
    else:
        # For non-period specific data
        if (
            cache_entry.get("data") is not None
            and current_time - cache_entry.get("timestamp", 0) < ttl
        ):
            return cache_entry["data"]

    return None


def set_cached_stats_data(cache_key, data, period=None, ttl=None):
    """Set cached stats data with timestamp."""
    if cache_key not in _stats_cache:
        _stats_cache[cache_key] = {"data": {}, "timestamp": 0, "ttl": 300}

    if period:
        # For period-specific data, store under period sub-key
        if not isinstance(_stats_cache[cache_key]["data"], dict):
            _stats_cache[cache_key]["data"] = {}
        _stats_cache[cache_key]["data"][period] = data
    else:
        # For non-period specific data
        _stats_cache[cache_key]["data"] = data

    _stats_cache[cache_key]["timestamp"] = time.time()
    if ttl is not None:
        _stats_cache[cache_key]["ttl"] = ttl


def check_stats_access(role):
    """Check if the user role has access to statistics."""
    return role in ["ADMIN", "SUPERADMIN"]


def map_period_to_api_period(ui_period):
    """Map UI time period to API-compatible period string."""
    mapping = {"day": "last_day", "week": "last_week", "month": "last_month"}
    return mapping.get(ui_period, "last_week")


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

    # Check cache first
    cached_data = get_cached_stats_data("dashboard", period)
    if cached_data is not None:
        logger.info(f"Dashboard stats: Returning cached data for period {period}")
        return cached_data

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

    headers = {"Authorization": f"Bearer {token}"}
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
            set_cached_stats_data("dashboard", data, period)
            logger.info(f"Dashboard stats: Successfully fetched and cached data for {period}")
            return data
        elif resp.status_code == 401:
            logger.warning("Dashboard stats: Unauthorized access (401). Check token.")
            return {"error": "Unauthorized access"}
        elif resp.status_code == 403:
            logger.warning("Dashboard stats: Forbidden access (403). Check permissions.")
            return {"error": "Forbidden access"}
        else:
            logger.error(
                f"Dashboard stats: Failed to fetch data. Status: {resp.status_code}, Body: {resp.text}"
            )
            return {"error": f"API error with status code {resp.status_code}"}
    except requests.exceptions.RequestException as e:
        logger.error(f"Dashboard stats: Request failed: {e}")
        return {"error": f"Request failed: {e}"}


def fetch_user_stats(token, api_environment="production", period="last_week"):
    """
    Fetch user statistics from the API.

    Args:
        token: JWT authentication token
        api_environment: API environment (production/staging)
        period: Time period (last_day, last_week, last_month, last_year, all)

    Returns:
        dict: User statistics data or None if error
    """
    import logging

    logger = logging.getLogger(__name__)

    # Check cache first
    cached_data = get_cached_stats_data("users", period)
    if cached_data is not None:
        logger.info(f"User stats: Returning cached data for period {period}")
        return cached_data

    logger.info(f"User stats: Fetching data for period={period}, environment={api_environment}")
    if not token:
        logger.warning("User stats: No token provided")
        return {"error": "Authentication token not provided"}

    headers = {"Authorization": f"Bearer {token}"}
    params = {"period": period}

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
            set_cached_stats_data("users", data, period)
            logger.info(f"User stats: Successfully fetched and cached data for {period}")
            return data
        else:
            logger.error(
                f"User stats: Failed to fetch data. Status: {resp.status_code}, Body: {resp.text}"
            )
            return {"error": f"API error with status code {resp.status_code}"}
    except requests.exceptions.RequestException as e:
        logger.error(f"User stats: Request failed: {e}")
        return {"error": f"Request failed: {e}"}


def fetch_execution_stats(token, api_environment="production", period="last_week"):
    """
    Fetch execution statistics from the API.

    Args:
        token: JWT authentication token
        api_environment: API environment (production/staging)
        period: Time period (last_day, last_week, last_month, last_year, all)

    Returns:
        dict: Execution statistics data or None if error
    """
    import logging

    logger = logging.getLogger(__name__)

    # Check cache first
    cached_data = get_cached_stats_data("executions", period)
    if cached_data is not None:
        logger.info(f"Execution stats: Returning cached data for period {period}")
        return cached_data

    logger.info(
        f"Execution stats: Fetching data for period={period}, environment={api_environment}"
    )
    if not token:
        logger.warning("Execution stats: No token provided")
        return {"error": "Authentication token not provided"}

    headers = {"Authorization": f"Bearer {token}"}
    params = {"period": period}

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
            set_cached_stats_data("executions", data, period)
            logger.info(f"Execution stats: Successfully fetched and cached data for {period}")
            return data
        else:
            logger.error(
                f"Execution stats: Failed to fetch data. Status: {resp.status_code}, Body: {resp.text}"
            )
            return {"error": f"API error with status code {resp.status_code}"}
    except requests.exceptions.RequestException as e:
        logger.error(f"Execution stats: Request failed: {e}")
        return {"error": f"Request failed: {e}"}
