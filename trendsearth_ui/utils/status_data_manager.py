"""Centralized status data management for optimized API calls and caching."""

from datetime import datetime, timezone
import logging
import math
from typing import Any, Optional

from cachetools import TTLCache
import requests

from ..config import get_api_base
from .boundaries_utils import clear_country_iso_cache, get_country_iso_resolver
from .http_client import apply_default_headers
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
from .timezone_utils import get_safe_timezone

logger = logging.getLogger(__name__)

# Centralized cache for all status-related data
_status_data_cache = TTLCache(
    maxsize=50, ttl=55
)  # Slightly under 1 minute to align with UI refresh cadence
_stats_data_cache = TTLCache(maxsize=50, ttl=300)  # 5-minute TTL for stats data


def _extract_summary_from_stats(stats_payload: Any) -> dict[str, Any]:
    """Safely extract the summary dictionary from a dashboard stats payload."""

    if not stats_payload or getattr(stats_payload, "get", None) is None:
        return {}

    if stats_payload.get("error"):
        return {}

    data_section = stats_payload.get("data", {})
    if not isinstance(data_section, dict):
        return {}

    summary = data_section.get("summary", {})
    return summary if isinstance(summary, dict) else {}


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
        user_timezone: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Fetch all status-related data in one consolidated call.

        Returns:
            dict: Contains summary, deployment, swarm, and basic stats data
        """
        safe_timezone = get_safe_timezone(user_timezone)

        cache_key = StatusDataManager.get_cache_key(
            "consolidated_status", api_environment=api_environment, timezone=safe_timezone
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
            swarm_info, swarm_cached_time = fetch_swarm_info(api_environment, token, safe_timezone)
            result["swarm"] = {
                "info": swarm_info,
                "cached_time": swarm_cached_time,
            }

            # Check if status endpoint is available
            result["status_endpoint_available"] = is_status_endpoint_available(
                token, api_environment
            )

            if not result["status_endpoint_available"]:
                result["summary"] = get_fallback_summary()
                StatusDataManager.set_cached_data(cache_key, result)
                return result

            # Fetch latest status data with optimized parameters
            headers = apply_default_headers({"Authorization": f"Bearer {token}"})
            resp = requests.get(
                f"{get_api_base(api_environment)}/status",
                headers=headers,
                params={
                    "per_page": 1,
                    "sort": "-timestamp",  # Descending order (newest first)
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
        api_period_map = {
            "day": "last_day",
            "week": "last_week",
            "month": "last_month",
            "year": "last_year",
            "all": "all",
        }
        api_period = api_period_map.get(time_period, "last_day")

        cache_key = StatusDataManager.get_cache_key(
            "consolidated_stats", api_environment=api_environment, period=api_period
        )

        # Check cache first unless forced refresh
        if not force_refresh:
            cached_data = StatusDataManager.get_cached_data(cache_key, cache_type="stats")
            if cached_data is not None:
                cached_execution_stats = cached_data.get("execution_stats")
                if isinstance(cached_execution_stats, dict) and cached_execution_stats.get("error"):
                    logger.warning(
                        "Cached execution stats for period %s contained an error response; refetching fresh data.",
                        api_period,
                    )
                else:
                    logger.info(f"Returning cached consolidated stats data for period {api_period}")
                    return cached_data

        logger.info(f"Fetching fresh consolidated stats data for period {api_period}")

        # Initialize result structure
        result = {
            "dashboard_stats": None,
            "dashboard_stats_all_time": None,
            "user_stats": None,
            "execution_stats": None,
            "scripts_count": 0,
            "api_period": api_period,
            "error": None,
            "total_executions_all_time": None,
            "total_users_all_time": None,
            "total_scripts_all_time": None,
        }

        try:
            # Get optimal grouping for time series data
            user_group_by, execution_group_by = get_optimal_grouping_for_period(api_period)

            # Fetch all stats data with comprehensive sections
            # (Note: These calls have their own caching, so we benefit from both levels)
            period_stats = fetch_dashboard_stats(
                token,
                api_environment,
                api_period,
                include_sections=None,  # Fetch all available sections for comprehensive stats
            )
            result["dashboard_stats"] = period_stats

            if api_period == "all":
                result["dashboard_stats_all_time"] = period_stats
            else:
                result["dashboard_stats_all_time"] = fetch_dashboard_stats(
                    token,
                    api_environment,
                    "all",
                    include_sections=["summary"],
                )

            summary_all_time = _extract_summary_from_stats(result["dashboard_stats_all_time"])

            result["total_executions_all_time"] = summary_all_time.get("total_executions")
            result["total_users_all_time"] = summary_all_time.get("total_users")
            # Prefer scripts count from summary if available; will fall back to scripts API below
            result["total_scripts_all_time"] = summary_all_time.get("total_scripts")

            result["user_stats"] = fetch_user_stats(
                token, api_environment, api_period, group_by=user_group_by
            )

            result["execution_stats"] = fetch_execution_stats(
                token, api_environment, api_period, group_by=execution_group_by
            )

            result["scripts_count"] = fetch_scripts_count(token, api_environment)
            if result["total_scripts_all_time"] is None:
                result["total_scripts_all_time"] = result["scripts_count"]

            resolver = get_country_iso_resolver(token, api_environment)
            if resolver is not None:
                result["country_iso_resolver"] = resolver
            else:
                logger.warning(
                    "Country ISO resolver unavailable for environment '%s'",
                    api_environment,
                )

            logger.info(f"Successfully fetched consolidated stats data for period {api_period}")

        except Exception as e:
            logger.error(f"Error fetching consolidated stats data: {e}")
            result["error"] = str(e)

        # Cache the result unless execution stats returned an error
        execution_stats = result.get("execution_stats")
        if isinstance(execution_stats, dict) and execution_stats.get("error"):
            logger.warning(
                "Skipping cache for consolidated stats period %s due to execution stats error response.",
                api_period,
            )
        else:
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
        Fetch time series status data for charts with enhanced caching and sufficient data points for full period coverage.

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

        # Calculate time range or aggregation strategy for the selected period
        from datetime import timedelta

        end_time = datetime.now(timezone.utc)
        use_aggregation = time_period in {"year", "all"}
        period_param: str | None = None
        group_by: str | None = None

        if time_period == "month":
            start_time = end_time - timedelta(days=30)
            target_points = 720  # Hourly resolution for 30 days
        elif time_period == "week":
            start_time = end_time - timedelta(days=7)
            target_points = 336  # ~2 points per hour for 7 days
        elif time_period == "year":
            start_time = end_time - timedelta(days=365)
            target_points = 12  # Monthly aggregation for year view
            use_aggregation = True
            period_param = "last_year"
            group_by = "month"
        elif time_period == "all":
            start_time = None
            target_points = 120  # Monthly aggregation; adjust as data grows
            use_aggregation = True
            period_param = "all"
            group_by = "month"
        else:  # Default to last day
            start_time = end_time - timedelta(days=1)
            target_points = 288  # ~1 point per 5 minutes for 24 hours

        request_limit: int | None = None
        if not use_aggregation:
            if start_time is not None:
                duration_seconds = max((end_time - start_time).total_seconds(), 0)
                base_interval_seconds = 300  # Approximate five-minute sampling cadence
                estimated_points = math.ceil(duration_seconds / base_interval_seconds) + 1
                estimated_points = max(estimated_points, target_points)
                # Cap to avoid excessive payloads while ensuring full coverage for month-scale views
                request_limit = min(estimated_points, 20000)
            else:
                request_limit = target_points

        start_iso = start_time.isoformat() if start_time else None
        end_iso = end_time.isoformat()

        result = {
            "data": [],
            "time_period": time_period,
            "start_time": start_iso,
            "end_time": end_iso,
            "target_points": target_points,
            "request_limit": request_limit,
            "optimization_applied": False,
            "error": None,
        }

        try:
            headers = apply_default_headers({"Authorization": f"Bearer {token}"})
            params: dict[str, Any] = {
                "sort": "timestamp" if use_aggregation else "-timestamp",
            }

            if use_aggregation:
                if period_param:
                    params["period"] = period_param
                if group_by:
                    params["group_by"] = group_by
                params["aggregate"] = "true"
            else:
                if start_iso:
                    params["start_date"] = start_iso
                params["end_date"] = end_iso
                if request_limit is not None:
                    params["per_page"] = request_limit

            resp = requests.get(
                f"{get_api_base(api_environment)}/status",
                headers=headers,
                params=params,
                timeout=15,  # Longer timeout for time series data
            )
            resp.raise_for_status()

            status_data = resp.json().get("data", [])

            if use_aggregation:
                result["data"] = status_data
                result["optimization_applied"] = False
                if status_data:
                    result["start_time"] = status_data[0].get("timestamp")
                    result["end_time"] = status_data[-1].get("timestamp")
                    result["request_limit"] = len(status_data)
                    result["target_points"] = len(status_data)
                logger.info(
                    f"Successfully fetched {len(status_data)} aggregated status records for period {time_period}"
                )
            else:
                # Apply smart sampling only if we have significantly more data than the target
                # This ensures we don't unnecessarily reduce data quality
                sampling_threshold = target_points * 1.5  # Only sample if 50% more than target
                if len(status_data) > sampling_threshold:
                    # Apply intelligent sampling to reduce data points while preserving trends
                    optimized_data = StatusDataManager._optimize_time_series_data(
                        status_data, target_points, time_period
                    )
                    result["data"] = optimized_data
                    result["optimization_applied"] = True
                    logger.info(
                        f"Applied selective time series optimization: {len(status_data)} -> {len(optimized_data)} points"
                    )
                else:
                    result["data"] = status_data
                    logger.info(
                        f"No optimization needed: {len(status_data)} points within acceptable range"
                    )

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
        data: list[dict], target_points: int, time_period: str
    ) -> list[dict]:
        """
        Optimize time series data by intelligently sampling to reduce data points while preserving trends.

        Uses a hybrid approach: systematic sampling for even distribution plus
        key point preservation for trend analysis.

        Args:
            data: List of status data dictionaries
            target_points: Target number of data points
            time_period: Time period for context-aware optimization

        Returns:
            list: Optimized data with reduced points
        """
        if len(data) <= target_points:
            return data

        # Sort by timestamp to ensure proper ordering
        sorted_data = sorted(data, key=lambda x: x.get("timestamp", ""))

        # Enhanced sampling strategy based on time period
        if time_period == "month":
            # For monthly data, use hourly sampling to preserve daily patterns
            optimized_data = StatusDataManager._sample_by_time_interval(
                sorted_data, target_points, "hourly"
            )
        elif time_period == "week":
            # For weekly data, use systematic sampling with trend preservation
            optimized_data = StatusDataManager._sample_with_trend_preservation(
                sorted_data, target_points
            )
        else:
            # For daily data, use simple systematic sampling
            optimized_data = StatusDataManager._systematic_sample(sorted_data, target_points)

        # Always include the most recent data point for real-time accuracy
        if sorted_data and sorted_data[-1] not in optimized_data:
            if len(optimized_data) > 0:
                optimized_data[-1] = sorted_data[-1]
            else:
                optimized_data.append(sorted_data[-1])

        return optimized_data

    @staticmethod
    def _systematic_sample(data: list[dict], target_points: int) -> list[dict]:
        """Simple systematic sampling with even distribution."""
        step = len(data) / target_points
        return [data[int(i * step)] for i in range(target_points) if int(i * step) < len(data)]

    @staticmethod
    def _sample_by_time_interval(
        data: list[dict], target_points: int, _interval: str
    ) -> list[dict]:
        """Sample data by time intervals (hourly, etc.) to preserve temporal patterns."""
        # For now, fall back to systematic sampling
        # In future, could implement actual time-interval based sampling
        return StatusDataManager._systematic_sample(data, target_points)

    @staticmethod
    def _sample_with_trend_preservation(data: list[dict], target_points: int) -> list[dict]:
        """Sample data while preserving important trend changes."""
        # For now, use systematic sampling
        # Future enhancement: detect significant changes in execution counts and preserve those points
        return StatusDataManager._systematic_sample(data, target_points)

    @staticmethod
    def invalidate_cache(pattern: Optional[str] = None) -> int:
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

        # Only clear the expensive boundaries resolver when explicitly requested or when
        # invalidating everything; manual status refreshes should continue reusing the
        # cached hierarchy until the TTL expires.
        if pattern is None or pattern == "boundaries":
            cleared_count += clear_country_iso_cache()

        logger.info(f"Invalidated {cleared_count} cache entries")
        return cleared_count

    @staticmethod
    def fetch_comprehensive_status_page_data(
        token: str,
        api_environment: str,
        time_period: str = "day",
        role: str = "USER",
        force_refresh: bool = False,
        user_timezone: str = "UTC",
    ) -> dict[str, Any]:
        """
        Fetch all data needed for the status page in optimized consolidated calls.

        This method consolidates multiple API calls to minimize request volume and
        improve page load performance by fetching related data together.

        Args:
            token: Authentication token
            api_environment: API environment (production/staging)
        time_period: Time period for stats data (day/week/month/year/all)
            role: User role for permission checks
            force_refresh: Whether to bypass cache

        Returns:
            dict: Comprehensive status page data including:
                - status_data: Latest status information
                - deployment_data: Deployment and health info
                - swarm_data: Docker swarm status
                - stats_data: Enhanced statistics (if SUPERADMIN)
                - time_series_data: Chart data
                - meta: Performance metadata
        """
        safe_timezone = get_safe_timezone(user_timezone)

        cache_key = StatusDataManager.get_cache_key(
            "comprehensive_status",
            api_environment=api_environment,
            time_period=time_period,
            role=role,
            timezone=safe_timezone,
        )

        # Check cache first unless forced refresh
        if not force_refresh:
            cached_data = StatusDataManager.get_cached_data(cache_key, cache_type="status")
            if cached_data is not None:
                logger.info("Returning cached comprehensive status page data")
                # Add cache hit metadata
                cached_data.setdefault("meta", {})["cache_hit"] = True
                return cached_data

        logger.info(
            f"Fetching fresh comprehensive status page data for period {time_period}, role {role}"
        )

        # Initialize result structure with performance metadata
        result = {
            "status_data": None,
            "deployment_data": None,
            "swarm_data": None,
            "stats_data": None,
            "time_series_data": None,
            "meta": {
                "cache_hit": False,
                "fetch_time": datetime.now(timezone.utc),
                "api_calls_made": [],
                "optimizations_applied": [],
            },
        }

        try:
            # 1. Fetch core status data (always needed)
            status_result = StatusDataManager.fetch_consolidated_status_data(
                token,
                api_environment,
                force_refresh=force_refresh,
                user_timezone=safe_timezone,
            )
            result["status_data"] = status_result
            result["meta"]["api_calls_made"].append("consolidated_status")

            # 2. Reuse deployment and swarm info gathered with consolidated status fetch
            deployment_from_status = status_result.get("deployment")
            if deployment_from_status is not None:
                result["deployment_data"] = deployment_from_status
                result["meta"]["optimizations_applied"].append("deployment_reused")
            else:
                result["deployment_data"] = fetch_deployment_info(api_environment, token)
                result["meta"]["api_calls_made"].append("deployment_info")

            swarm_from_status = status_result.get("swarm") or {}
            swarm_info = swarm_from_status.get("info")
            swarm_time = swarm_from_status.get("cached_time")

            if swarm_info is not None:
                result["swarm_data"] = {"info": swarm_info, "cached_time": swarm_time or ""}
                result["meta"]["optimizations_applied"].append("swarm_reused")
            else:
                fetched_swarm_info, fetched_swarm_time = fetch_swarm_info(
                    api_environment,
                    token,
                    user_timezone=safe_timezone,
                )
                result["swarm_data"] = {
                    "info": fetched_swarm_info,
                    "cached_time": fetched_swarm_time,
                }
                result["meta"]["api_calls_made"].append("swarm_info")

            # 3. Fetch stats data (only for SUPERADMIN)
            if role == "SUPERADMIN":
                stats_result = StatusDataManager.fetch_consolidated_stats_data(
                    token, api_environment, time_period, role, force_refresh=force_refresh
                )
                result["stats_data"] = stats_result
                result["meta"]["api_calls_made"].append("consolidated_stats")
                result["meta"]["optimizations_applied"].append("superadmin_stats_consolidated")

                if stats_result and not stats_result.get("error"):
                    summary_all_time = _extract_summary_from_stats(
                        stats_result.get("dashboard_stats_all_time")
                        or stats_result.get("dashboard_stats")
                    )

                    latest_status = result.get("status_data", {}).get("latest_status")
                    if latest_status is not None:
                        if summary_all_time:
                            total_users = summary_all_time.get("total_users")
                            if total_users is not None:
                                latest_status["users_count"] = total_users

                            total_executions = summary_all_time.get("total_executions")
                            if total_executions is not None:
                                latest_status["executions_count"] = total_executions

                            total_scripts = summary_all_time.get("total_scripts")
                            if total_scripts is not None:
                                latest_status["scripts_count"] = total_scripts

                        if stats_result.get("scripts_count") is not None:
                            latest_status["scripts_count"] = stats_result["scripts_count"]

            else:
                result["meta"]["optimizations_applied"].append("stats_skipped_for_non_superadmin")

            # 4. Fetch time series data with optimized parameters
            time_series_result = StatusDataManager.fetch_time_series_status_data(
                token, api_environment, time_period, force_refresh=force_refresh
            )
            result["time_series_data"] = time_series_result
            result["meta"]["api_calls_made"].append("time_series_status")

            # Add optimization metadata
            if time_series_result.get("optimization_applied"):
                result["meta"]["optimizations_applied"].append("time_series_sampling")

            result["meta"]["total_api_calls"] = len(result["meta"]["api_calls_made"])
            logger.info(
                f"Comprehensive fetch completed: {result['meta']['total_api_calls']} API calls"
            )

        except Exception as e:
            logger.error(f"Error fetching comprehensive status page data: {e}")
            result["error"] = str(e)
            result["meta"]["error"] = str(e)

        # Cache the result (excluding error cases)
        if not result.get("error"):
            StatusDataManager.set_cached_data(cache_key, result, cache_type="status")
            result["meta"]["optimizations_applied"].append("response_cached")

        return result
