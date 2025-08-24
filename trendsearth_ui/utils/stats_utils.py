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
        return None

    try:
        headers = {"Authorization": f"Bearer {token}"}
        params = {"period": period}

        if include_sections:
            params["include"] = ",".join(include_sections)

        api_url = f"{get_api_base(api_environment)}/stats/dashboard"
        logger.info(f"Dashboard stats: Making request to {api_url} with params {params}")

        resp = requests.get(api_url, headers=headers, params=params, timeout=10)

        logger.info(f"Dashboard stats: Response status {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            logger.info(
                f"Dashboard stats: Success - received data with keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}"
            )
            # Cache the result
            set_cached_stats_data("dashboard", data, period, ttl=300)
            return data
        else:
            # Log the error for debugging with enhanced information
            error_text = resp.text[:500] if resp.text else "No response text"
            logger.error(f"Dashboard stats: Failed with status {resp.status_code} - {error_text}")

            # Return a structured error response instead of None to provide better feedback
            return {
                "error": True,
                "status_code": resp.status_code,
                "message": error_text,
                "data": {}
            }

    except Exception as e:
        # Log the error for debugging with enhanced information
        logger.error(f"Dashboard stats: Exception occurred - {str(e)}")
        # Return a structured error response instead of None
        return {
            "error": True,
            "status_code": "exception",
            "message": str(e),
            "data": {}
        }


def fetch_user_stats(
    token, api_environment="production", period="last_week", group_by="day", country=None
):
    """
    Fetch user statistics from the API.

    Args:
        token: JWT authentication token
        api_environment: API environment (production/staging)
        period: Time period (last_day, last_week, last_month, last_year, all)
        group_by: Grouping interval (day, week, month)
        country: Filter by specific country

    Returns:
        dict: User statistics data or None if error
    """
    import logging

    logger = logging.getLogger(__name__)

    # Create cache key based on parameters
    cache_period = f"{period}_{group_by}_{country or 'all'}"

    # Check cache first
    cached_data = get_cached_stats_data("users", cache_period)
    if cached_data is not None:
        logger.info(f"User stats: Returning cached data for period {cache_period}")
        return cached_data

    # Enhanced logging for debugging
    logger.info(
        f"User stats: Fetching data for period={period}, group_by={group_by}, country={country}, environment={api_environment}"
    )

    try:
        headers = {"Authorization": f"Bearer {token}"}
        params = {"period": period, "group_by": group_by}

        if country:
            params["country"] = country

        api_url = f"{get_api_base(api_environment)}/stats/users"
        logger.info(f"User stats: Making request to {api_url} with params {params}")

        resp = requests.get(api_url, headers=headers, params=params, timeout=10)

        logger.info(f"User stats: Response status {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            logger.info(
                f"User stats: Success - received data with keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}"
            )
            # Cache the result
            set_cached_stats_data("users", data, cache_period, ttl=300)
            return data
        else:
            # Log the error for debugging with enhanced information
            error_text = resp.text[:500] if resp.text else "No response text"
            logger.error(f"User stats: Failed with status {resp.status_code} - {error_text}")

            # Return a structured error response instead of None to provide better feedback
            return {
                "error": True,
                "status_code": resp.status_code,
                "message": error_text,
                "data": {}
            }

    except Exception as e:
        # Log the error for debugging with enhanced information
        logger.error(f"User stats: Exception occurred - {str(e)}")
        # Return a structured error response instead of None
        return {
            "error": True,
            "status_code": "exception",
            "message": str(e),
            "data": {}
        }


def fetch_execution_stats(
    token,
    api_environment="production",
    period="last_week",
    group_by="day",
    task_type=None,
    status=None,
):
    """
    Fetch execution statistics from the API.

    Args:
        token: JWT authentication token
        api_environment: API environment (production/staging)
        period: Time period (last_day, last_week, last_month, last_year, all)
        group_by: Grouping interval (hour, day, week, month)
        task_type: Filter by specific task type
        status: Filter by execution status (PENDING, RUNNING, FINISHED, FAILED, CANCELLED)

    Returns:
        dict: Execution statistics data or None if error
    """
    # Create cache key based on parameters
    cache_period = f"{period}_{group_by}_{task_type or 'all'}_{status or 'all'}"

    # Check cache first
    cached_data = get_cached_stats_data("executions", cache_period)
    if cached_data is not None:
        return cached_data

    try:
        headers = {"Authorization": f"Bearer {token}"}
        params = {"period": period, "group_by": group_by}

        if task_type:
            params["task_type"] = task_type
        if status:
            params["status"] = status

        resp = requests.get(
            f"{get_api_base(api_environment)}/stats/executions",
            headers=headers,
            params=params,
            timeout=10,
        )

        if resp.status_code == 200:
            data = resp.json()
            # Cache the result
            set_cached_stats_data("executions", data, cache_period, ttl=300)
            return data
        else:
            # Log the error for debugging
            import logging

            logger = logging.getLogger(__name__)
            error_text = resp.text[:500] if resp.text else "No response text"
            logger.error(
                f"Failed to fetch execution stats: {resp.status_code} - {error_text}"
            )

            # Return a structured error response instead of None
            return {
                "error": True,
                "status_code": resp.status_code,
                "message": error_text,
                "data": {}
            }

    except Exception as e:
        # Log the error for debugging
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Exception fetching execution stats: {str(e)}")

        # Return a structured error response instead of None
        return {
            "error": True,
            "status_code": "exception",
            "message": str(e),
            "data": {}
        }


def map_period_to_api_period(period):
    """
    Map UI time period to API period parameter.

    Args:
        period: UI period ("day", "week", "month")

    Returns:
        str: API period parameter
    """
    mapping = {"day": "last_day", "week": "last_week", "month": "last_month"}
    return mapping.get(period, "last_week")


def check_stats_access(token, api_environment="production"):
    """
    Check if the user has access to stats endpoints (SUPERADMIN only).

    Args:
        token: JWT authentication token
        api_environment: API environment (production/staging)

    Returns:
        tuple: (bool, str) - (access_granted, error_message)
    """
    import logging

    logger = logging.getLogger(__name__)

    # Enhanced logging for token debugging
    if not token:
        logger.warning("Stats access check: No token provided")
        return False, "No authentication token provided"

    # Log token information for debugging (without exposing the actual token)
    token_length = len(token) if token else 0
    token_segments = len(token.split(".")) if token else 0
    logger.info(f"Stats access check: Token length={token_length}, segments={token_segments}")

    # Validate token format before making API call
    if token_segments != 3:
        logger.warning(
            f"Stats access check: Invalid JWT format - expected 3 segments, got {token_segments}"
        )
        return False, f"Invalid JWT token format (has {token_segments} segments, expected 3)"

    try:
        headers = {"Authorization": f"Bearer {token}"}
        api_url = f"{get_api_base(api_environment)}/stats/health"
        logger.info(f"Stats access check: Making request to {api_url}")

        resp = requests.get(api_url, headers=headers, timeout=5)

        # Log the access check result for debugging
        logger.info(f"Stats access check: {resp.status_code} for /stats/health")

        if resp.status_code == 200:
            logger.info("Stats access check: Access granted")
            return True, "Access granted"
        elif resp.status_code == 401:
            error_detail = resp.text[:200] if resp.text else "Authentication required"
            logger.warning(f"Stats access denied: 401 - {error_detail}")
            return False, f"Authentication required: {error_detail}"
        elif resp.status_code == 403:
            error_detail = resp.text[:200] if resp.text else "SUPERADMIN privileges required"
            logger.warning(f"Stats access denied: 403 - {error_detail}")
            return False, f"SUPERADMIN privileges required: {error_detail}"
        elif resp.status_code == 422:
            error_detail = resp.text[:200] if resp.text else "Invalid token format"
            logger.warning(f"Stats access denied: 422 - {error_detail}")
            return False, f"Authentication error: {error_detail}"
        else:
            error_detail = (
                resp.text[:200] if resp.text else f"Server returned status {resp.status_code}"
            )
            logger.warning(f"Stats access denied: {resp.status_code} - {error_detail}")
            return False, f"Server error (status {resp.status_code}): {error_detail}"

    except Exception as e:
        # Log the error for debugging
        logger.warning(f"Exception checking stats access: {str(e)}")
        return False, f"Connection error: {str(e)}"
