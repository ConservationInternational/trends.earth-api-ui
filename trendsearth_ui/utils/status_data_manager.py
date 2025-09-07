"""Centralized status data management for optimized API calls and caching."""

from datetime import datetime, timezone
import logging
from typing import Any, Optional

from cachetools import TTLCache
import requests

from ..config import get_api_base
from .stats_utils import (
    fetch_dashboard_stats,
    fetch_execution_stats,
    fetch_scripts_count,
    fetch_user_stats,
    get_optimal_grouping_for_period,
)
from .status_helpers import (
    fetch_deployment_info,
    fetch_swarm_info,
    get_fallback_summary,
    is_status_endpoint_available,
)

logger = logging.getLogger(__name__)

# Centralized cache for all status-related data
_status_data_cache = TTLCache(maxsize=50, ttl=60)  # 1-minute TTL for status data
_stats_data_cache = TTLCache(maxsize=50, ttl=300)  # 5-minute TTL for stats data


class StatusDataManager:
    """Centralized manager for status page data to minimize API calls and optimize caching."""

    @staticmethod
    def get_cache_key(data_type: str, **kwargs) -> str:
        """Generate cache key for different types of status data."""
        key_parts = [data_type]
        for k, v in sorted(kwargs.items()):
            if v is not None:
                key_parts.append(f"{k}={v}")
        return "_".join(key_parts)

    @staticmethod
    def get_cached_data(cache_key: str, cache_type: str = "status") -> Optional[Any]:
        """Get data from appropriate cache."""
        cache = _status_data_cache if cache_type == "status" else _stats_data_cache
        return cache.get(cache_key)

    @staticmethod
    def set_cached_data(cache_key: str, data: Any, cache_type: str = "status") -> None:
        """Set data in appropriate cache."""
        cache = _status_data_cache if cache_type == "status" else _stats_data_cache
        cache[cache_key] = data

    @staticmethod
    def fetch_consolidated_status_data(
        token: str,
        api_environment: str,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """
        Fetch all status-related data in one consolidated call.

        Returns:
            dict: Contains summary, deployment, swarm, and basic stats data
        """
        cache_key = StatusDataManager.get_cache_key(
            "consolidated_status", api_environment=api_environment
        )

        # Check cache first unless forced refresh
        if not force_refresh:
            cached_data = StatusDataManager.get_cached_data(cache_key)
            if cached_data is not None:
                logger.info("Returning cached consolidated status data")
                return cached_data

        logger.info("Fetching fresh consolidated status data")

        # Initialize result structure
        result = {
            "summary": None,
            "deployment": None,
            "swarm": None,
            "status_endpoint_available": False,
            "latest_status": None,
            "error": None,
        }

        try:
            # Fetch deployment and swarm info (these are fast and can be done in parallel)
            result["deployment"] = fetch_deployment_info(api_environment, token)
            result["swarm"], swarm_cached_time = fetch_swarm_info(api_environment, token)

            # Check if status endpoint is available
            result["status_endpoint_available"] = is_status_endpoint_available(
                token, api_environment
            )

            if not result["status_endpoint_available"]:
                result["summary"] = get_fallback_summary()
                StatusDataManager.set_cached_data(cache_key, result)
                return result

            # Fetch latest status data with optimized parameters
            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.get(
                f"{get_api_base(api_environment)}/status",
                headers=headers,
                params={
                    "per_page": 1,
                    "sort": "-timestamp",
                    "exclude": "metadata,logs",  # Exclude large fields for performance
                },
                timeout=5,
            )

            if resp.status_code == 200:
                status_data = resp.json().get("data", [])
                if status_data:
                    result["latest_status"] = status_data[0]
                    # Generate summary from status data will be done by caller
                    result["summary"] = "SUCCESS"  # Indicator that we have valid data
                else:
                    result["summary"] = "NO_DATA"
            else:
                result["error"] = f"Status API error: {resp.status_code}"
                result["summary"] = "API_ERROR"

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching consolidated status data: {e}")
            result["error"] = str(e)
            result["summary"] = "REQUEST_ERROR"

        # Cache the result
        StatusDataManager.set_cached_data(cache_key, result)
        return result

    @staticmethod
    def fetch_consolidated_stats_data(
        token: str,
        api_environment: str,
        time_period: str,
        role: str,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """
        Fetch all stats-related data for SUPERADMIN users.

        Returns:
            dict: Contains dashboard stats, user stats, execution stats, and scripts count
        """
        if role != "SUPERADMIN":
            return {"error": "Insufficient permissions", "requires_superadmin": True}

        # Map UI time period to API period
        api_period_map = {"day": "last_day", "week": "last_week", "month": "last_month"}
        api_period = api_period_map.get(time_period, "last_day")

        cache_key = StatusDataManager.get_cache_key(
            "consolidated_stats", api_environment=api_environment, period=api_period
        )

        # Check cache first unless forced refresh
        if not force_refresh:
            cached_data = StatusDataManager.get_cached_data(cache_key, cache_type="stats")
            if cached_data is not None:
                logger.info(f"Returning cached consolidated stats data for period {api_period}")
                return cached_data

        logger.info(f"Fetching fresh consolidated stats data for period {api_period}")

        # Initialize result structure
        result = {
            "dashboard_stats": None,
            "user_stats": None,
            "execution_stats": None,
            "scripts_count": 0,
            "api_period": api_period,
            "error": None,
        }

        try:
            # Get optimal grouping for time series data
            user_group_by, execution_group_by = get_optimal_grouping_for_period(api_period)

            # Fetch all stats data in parallel-ready manner
            # (Note: These calls have their own caching, so we benefit from both levels)
            result["dashboard_stats"] = fetch_dashboard_stats(
                token,
                api_environment,
                api_period,
                include_sections=["summary", "trends", "geographic", "tasks"],
            )

            result["user_stats"] = fetch_user_stats(
                token, api_environment, api_period, group_by=user_group_by
            )

            result["execution_stats"] = fetch_execution_stats(
                token, api_environment, api_period, group_by=execution_group_by
            )

            result["scripts_count"] = fetch_scripts_count(token, api_environment)

            logger.info(f"Successfully fetched consolidated stats data for period {api_period}")

        except Exception as e:
            logger.error(f"Error fetching consolidated stats data: {e}")
            result["error"] = str(e)

        # Cache the result
        StatusDataManager.set_cached_data(cache_key, result, cache_type="stats")
        return result

    @staticmethod
    def fetch_time_series_status_data(
        token: str,
        api_environment: str,
        time_period: str,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """
        Fetch optimized time series status data for charts with enhanced caching and preprocessing.

        Returns:
            dict: Contains time series data, metadata for chart generation, and optimization info
        """
        cache_key = StatusDataManager.get_cache_key(
            "time_series_status", api_environment=api_environment, period=time_period
        )

        # Check cache first unless forced refresh
        if not force_refresh:
            cached_data = StatusDataManager.get_cached_data(cache_key)
            if cached_data is not None:
                logger.info(f"Returning cached time series data for period {time_period}")
                return cached_data

        logger.info(f"Fetching fresh time series data for period {time_period}")

        # Calculate time range for API query with optimized parameters
        from datetime import timedelta

        end_time = datetime.now(timezone.utc)
        if time_period == "month":
            start_time = end_time - timedelta(days=30)
            max_points = 720  # ~1 point per hour for 30 days
        elif time_period == "week":
            start_time = end_time - timedelta(days=7)
            max_points = 336  # ~1 point per 30 minutes for 7 days
        else:  # Default to day
            start_time = end_time - timedelta(days=1)
            max_points = 288  # ~1 point per 5 minutes for 24 hours

        # Format for API query
        start_iso = start_time.isoformat()
        end_iso = end_time.isoformat()

        result = {
            "data": [],
            "time_period": time_period,
            "start_time": start_iso,
            "end_time": end_iso,
            "max_points": max_points,
            "optimization_applied": False,
            "error": None,
        }

        try:
            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.get(
                f"{get_api_base(api_environment)}/status",
                headers=headers,
                params={
                    "start_date": start_iso,
                    "end_date": end_iso,
                    "per_page": max_points,  # Adaptive limit based on time period
                    "sort": "timestamp",  # Sort by timestamp ascending
                    "exclude": "metadata,logs",  # Exclude large fields for performance
                },
                timeout=15,  # Longer timeout for time series data
            )
            resp.raise_for_status()

            status_data = resp.json().get("data", [])

            # Apply optimization if we have too many data points
            if len(status_data) > max_points:
                # Apply intelligent sampling to reduce data points while preserving trends
                optimized_data = StatusDataManager._optimize_time_series_data(
                    status_data, max_points, time_period
                )
                result["data"] = optimized_data
                result["optimization_applied"] = True
                logger.info(
                    f"Applied time series optimization: {len(status_data)} -> {len(optimized_data)} points"
                )
            else:
                result["data"] = status_data

            logger.info(
                f"Successfully fetched {len(result['data'])} time series records for period {time_period}"
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching time series status data: {e}")
            result["error"] = str(e)

        # Cache the result
        StatusDataManager.set_cached_data(cache_key, result)
        return result

    @staticmethod
    def _optimize_time_series_data(
        data: list[dict], target_points: int, _time_period: str
    ) -> list[dict]:
        """
        Optimize time series data by intelligently sampling to reduce data points while preserving trends.

        Args:
            data: List of status data dictionaries
            target_points: Target number of data points
            _time_period: Time period for context-aware optimization (unused for now)

        Returns:
            list: Optimized data with reduced points
        """
        if len(data) <= target_points:
            return data

        # Sort by timestamp to ensure proper ordering
        sorted_data = sorted(data, key=lambda x: x.get("timestamp", ""))

        # Use systematic sampling with some randomization to preserve key events
        step = len(sorted_data) / target_points
        optimized_data = []

        for i in range(target_points):
            index = int(i * step)
            if index < len(sorted_data):
                optimized_data.append(sorted_data[index])

        # Always include the most recent data point
        if sorted_data and sorted_data[-1] not in optimized_data:
            optimized_data[-1] = sorted_data[-1]

        return optimized_data

    @staticmethod
    def invalidate_cache(pattern: str = None) -> int:
        """
        Invalidate cached data.

        Args:
            pattern: Optional pattern to match cache keys for selective invalidation

        Returns:
            int: Number of cache entries cleared
        """
        cleared_count = 0

        for cache in [_status_data_cache, _stats_data_cache]:
            if pattern is None:
                cleared_count += len(cache)
                cache.clear()
            else:
                keys_to_remove = [k for k in cache if pattern in k]
                for key in keys_to_remove:
                    del cache[key]
                cleared_count += len(keys_to_remove)

        logger.info(f"Invalidated {cleared_count} cache entries")
        return cleared_count
