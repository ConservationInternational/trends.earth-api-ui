"""Utility functions for the Trends.Earth API Dashboard."""

from datetime import datetime
import json

import requests

from ..config import API_BASE
from .timezone_utils import format_local_time, get_safe_timezone


def parse_date(date_str, user_timezone="UTC"):
    """Parse date string and return formatted string for ag-grid with timezone conversion.

    Args:
        date_str: UTC date string from the API
        user_timezone: User's timezone (IANA timezone name)

    Returns:
        Formatted local time string or None/original string if parsing fails
    """
    if not date_str:
        return None
    try:
        # Handle ISO format with Z and potential microseconds
        if isinstance(date_str, str) and date_str.endswith("Z"):
            date_str = date_str[:-1] + "+00:00"
        dt_utc = datetime.fromisoformat(date_str)

        # Convert to user's local timezone
        safe_timezone = get_safe_timezone(user_timezone)
        local_time_str, tz_abbrev = format_local_time(dt_utc, safe_timezone, include_seconds=False)

        # Return formatted local time with timezone abbreviation
        return f"{local_time_str} {tz_abbrev}"
    except (ValueError, TypeError):
        return date_str  # Return original if parsing fails


def safe_table_data(data, column_ids=None):
    """Safely process table data for display."""
    if not data:
        return []
    newdata = []
    for i, row in enumerate(data):
        newrow = {}
        for k in column_ids or row.keys():
            v = row.get(k, "")
            if k in ("params", "results"):
                newrow[k] = f"Show {k.capitalize()}"
            elif isinstance(v, (dict, list)):
                newrow[k] = json.dumps(v)
            else:
                newrow[k] = v
        newrow["_row"] = i
        newdata.append(newrow)
    return newdata


def get_user_info(token):
    """Get user information from API with improved error handling."""
    if not token:
        return None

    headers = {"Authorization": f"Bearer {token}"}

    try:
        resp = requests.get(f"{API_BASE}/user/me", headers=headers, timeout=10)
        if resp.status_code == 200:
            user_data = resp.json().get("data", {})
            return user_data

        resp = requests.get(f"{API_BASE}/user", headers=headers, timeout=10)
        if resp.status_code == 200:
            users = resp.json().get("data", [])
            if users:
                user_data = users[0]
                return user_data
    except requests.exceptions.Timeout:
        print("Timeout occurred while fetching user info")
        return None
    except requests.exceptions.ConnectionError:
        print("Connection error occurred while fetching user info")
        return None
    except Exception as e:
        print(f"Error fetching user info: {e}")
        return None

    # Return None if both API calls failed
    return None
