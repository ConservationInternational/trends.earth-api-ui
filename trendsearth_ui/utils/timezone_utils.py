"""Timezone utilities for converting UTC times to user's local timezone."""

from datetime import datetime, timezone
from typing import Optional
import zoneinfo


def get_timezone_from_name(timezone_name: str) -> Optional[zoneinfo.ZoneInfo]:
    """Get timezone object from timezone name.

    Args:
        timezone_name: IANA timezone name (e.g., 'America/New_York')

    Returns:
        ZoneInfo object or None if invalid
    """
    try:
        return zoneinfo.ZoneInfo(timezone_name)
    except (zoneinfo.ZoneInfoNotFoundError, ValueError):
        return None


def convert_utc_to_local(utc_dt: datetime, user_timezone: str) -> tuple[datetime, str]:
    """Convert UTC datetime to user's local timezone.

    Args:
        utc_dt: UTC datetime (should be timezone-aware or will be assumed UTC)
        user_timezone: IANA timezone name (e.g., 'America/New_York')

    Returns:
        Tuple of (local_datetime, timezone_abbreviation)
    """
    # Ensure UTC datetime is timezone-aware
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    elif utc_dt.tzinfo != timezone.utc:
        # Convert to UTC if not already
        utc_dt = utc_dt.astimezone(timezone.utc)

    # Get user's timezone
    user_tz = get_timezone_from_name(user_timezone)
    if user_tz is None:
        # Fallback to UTC if timezone is invalid
        return utc_dt.replace(tzinfo=None), "UTC"

    # Convert to user's timezone
    local_dt = utc_dt.astimezone(user_tz)

    # Get timezone abbreviation
    tz_abbrev = local_dt.strftime("%Z")
    if not tz_abbrev:
        # Fallback to offset format if abbreviation not available
        tz_abbrev = local_dt.strftime("%z")
        if len(tz_abbrev) == 5:  # Format +0000
            tz_abbrev = f"UTC{tz_abbrev[:3]}:{tz_abbrev[3:]}"

    return local_dt.replace(tzinfo=None), tz_abbrev


def format_local_time(
    utc_dt: datetime, user_timezone: str, include_seconds: bool = True
) -> tuple[str, str]:
    """Format UTC datetime as local time string.

    Args:
        utc_dt: UTC datetime
        user_timezone: IANA timezone name
        include_seconds: Whether to include seconds in the format

    Returns:
        Tuple of (formatted_local_time, timezone_abbreviation)
    """
    local_dt, tz_abbrev = convert_utc_to_local(utc_dt, user_timezone)

    time_format = "%Y-%m-%d %H:%M:%S" if include_seconds else "%Y-%m-%d %H:%M"

    formatted_time = local_dt.strftime(time_format)
    return formatted_time, tz_abbrev


def get_chart_axis_label(user_timezone: str, base_label: str = "Time") -> str:
    """Get chart axis label with timezone abbreviation.

    Args:
        user_timezone: IANA timezone name
        base_label: Base label text (default: "Time")

    Returns:
        Formatted axis label with timezone
    """
    # Create a sample datetime to get the timezone abbreviation
    sample_dt = datetime.now(timezone.utc)
    _, tz_abbrev = convert_utc_to_local(sample_dt, user_timezone)

    return f"{base_label} ({tz_abbrev})"


def convert_timestamp_series_to_local(timestamps_series, user_timezone: str):
    """Convert a pandas Series of timestamps from UTC to local timezone.

    Args:
        timestamps_series: pandas Series containing UTC timestamps
        user_timezone: IANA timezone name

    Returns:
        pandas Series with converted local timestamps
    """
    import logging

    import pandas as pd

    logger = logging.getLogger(__name__)
    local_timestamps = []
    safe_timezone = get_safe_timezone(user_timezone)
    failed_conversions = 0

    logger.info(f"Converting {len(timestamps_series)} timestamps to {safe_timezone}")

    for i, timestamp in enumerate(timestamps_series):
        if pd.isna(timestamp):
            local_timestamps.append(timestamp)
        else:
            try:
                # Ensure we have a datetime object
                if isinstance(timestamp, str):
                    dt_utc = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                elif hasattr(timestamp, "to_pydatetime"):
                    dt_utc = timestamp.to_pydatetime()
                else:
                    dt_utc = timestamp

                local_dt, _ = convert_utc_to_local(dt_utc, safe_timezone)
                local_timestamps.append(local_dt)
            except (ValueError, TypeError) as e:
                # If conversion fails, keep original timestamp
                failed_conversions += 1
                logger.warning(f"Failed to convert timestamp at index {i}: {timestamp}, error: {e}")
                local_timestamps.append(timestamp)

    if failed_conversions > 0:
        logger.warning(
            f"Failed to convert {failed_conversions} out of {len(timestamps_series)} timestamps"
        )

    result = pd.Series(local_timestamps, index=timestamps_series.index)
    logger.info(f"Timezone conversion complete. Result length: {len(result)}")
    return result


def is_valid_timezone(timezone_name: str) -> bool:
    """Check if timezone name is valid.

    Args:
        timezone_name: IANA timezone name

    Returns:
        True if valid, False otherwise
    """
    return get_timezone_from_name(timezone_name) is not None


# Default timezone fallback
DEFAULT_TIMEZONE = "UTC"


def get_safe_timezone(timezone_name: Optional[str]) -> str:
    """Get a safe timezone name, falling back to default if invalid.

    Args:
        timezone_name: IANA timezone name or None

    Returns:
        Valid timezone name
    """
    if timezone_name and is_valid_timezone(timezone_name):
        return timezone_name
    return DEFAULT_TIMEZONE
