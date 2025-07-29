"""Utility functions for the Trends.Earth API Dashboard."""

from datetime import datetime
import json
from typing import Optional

import requests

from ..config import API_BASE, AUTH_URL
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


def get_user_info(token, api_base=None):
    """Get user information from API with improved error handling."""
    if not token:
        print("❌ get_user_info: No token provided")
        return None

    # Use provided api_base or fallback to default
    base_url = api_base or API_BASE
    headers = {"Authorization": f"Bearer {token}"}

    print(f"🔍 get_user_info: Using API base URL: {base_url}")
    print(f"🔍 get_user_info: Token length: {len(token)} characters")

    try:
        # Try /user/me endpoint first
        me_url = f"{base_url}/user/me"
        print(f"🌐 get_user_info: Attempting GET request to {me_url}")

        resp = requests.get(me_url, headers=headers, timeout=10)
        print(f"📊 get_user_info: /user/me response status: {resp.status_code}")

        if resp.status_code == 200:
            try:
                response_json = resp.json()
                print(
                    f"✅ get_user_info: /user/me response JSON keys: {list(response_json.keys()) if isinstance(response_json, dict) else 'Not a dict'}"
                )
                user_data = response_json.get("data", {})
                if user_data:
                    print("✅ get_user_info: Successfully retrieved user data from /user/me")
                    print(
                        f"🔍 get_user_info: User data keys: {list(user_data.keys()) if isinstance(user_data, dict) else 'Not a dict'}"
                    )
                    return user_data
                else:
                    print("⚠️ get_user_info: /user/me returned empty data field")
            except ValueError as e:
                print(f"❌ get_user_info: Failed to parse /user/me JSON response: {e}")
                print(f"🔍 get_user_info: Raw response text: {resp.text[:500]}...")
        else:
            print(f"❌ get_user_info: /user/me failed with status {resp.status_code}")
            print(f"🔍 get_user_info: Error response text: {resp.text[:500]}...")

        # Try /user endpoint as fallback
        user_url = f"{base_url}/user"
        print(f"🌐 get_user_info: Attempting fallback GET request to {user_url}")

        resp = requests.get(user_url, headers=headers, timeout=10)
        print(f"📊 get_user_info: /user response status: {resp.status_code}")

        if resp.status_code == 200:
            try:
                response_json = resp.json()
                print(
                    f"✅ get_user_info: /user response JSON keys: {list(response_json.keys()) if isinstance(response_json, dict) else 'Not a dict'}"
                )
                users = response_json.get("data", [])
                print(
                    f"🔍 get_user_info: Found {len(users) if isinstance(users, list) else 'non-list'} users in response"
                )

                if users and isinstance(users, list) and len(users) > 0:
                    user_data = users[0]
                    print(
                        "✅ get_user_info: Successfully retrieved user data from /user (first user)"
                    )
                    print(
                        f"🔍 get_user_info: User data keys: {list(user_data.keys()) if isinstance(user_data, dict) else 'Not a dict'}"
                    )
                    return user_data
                else:
                    print("⚠️ get_user_info: /user returned empty or invalid users array")
            except ValueError as e:
                print(f"❌ get_user_info: Failed to parse /user JSON response: {e}")
                print(f"🔍 get_user_info: Raw response text: {resp.text[:500]}...")
        else:
            print(f"❌ get_user_info: /user failed with status {resp.status_code}")
            print(f"🔍 get_user_info: Error response text: {resp.text[:500]}...")

    except requests.exceptions.Timeout:
        print("⏰ get_user_info: Timeout occurred while fetching user info")
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"🌐 get_user_info: Connection error occurred while fetching user info: {e}")
        return None
    except Exception as e:
        print(f"💥 get_user_info: Unexpected error fetching user info: {e}")
        import traceback

        print(f"🔍 get_user_info: Stack trace: {traceback.format_exc()}")
        return None

    print("❌ get_user_info: All attempts to retrieve user info failed")
    return None


def refresh_access_token(
    refresh_token: str, api_environment: str = None
) -> tuple[Optional[str], Optional[int]]:
    """Refresh access token using refresh token.

    Args:
        refresh_token: Valid refresh token
        api_environment: API environment to use for refresh

    Returns:
        Tuple of (new_access_token, expires_in) or (None, None) if refresh failed
    """
    if not refresh_token:
        return None, None

    # Import here to avoid circular imports
    from ..config import get_auth_url

    # Get the auth URL for the specified environment
    auth_url = get_auth_url(api_environment)

    try:
        refresh_data = {"refresh_token": refresh_token}
        resp = requests.post(f"{auth_url}/refresh", json=refresh_data, timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            access_token = data.get("access_token")
            expires_in = data.get("expires_in")
            print("✅ Access token refreshed successfully")
            return access_token, expires_in
        else:
            print(f"❌ Token refresh failed with status: {resp.status_code}")
            return None, None

    except requests.exceptions.Timeout:
        print("⏰ Token refresh request timed out")
        return None, None
    except requests.exceptions.ConnectionError:
        print("❌ Connection error during token refresh")
        return None, None
    except Exception as e:
        print(f"💥 Error during token refresh: {str(e)}")
        return None, None


def logout_user(access_token: str, refresh_token: str = None, api_environment: str = None) -> bool:
    """Logout user by revoking refresh token.

    Args:
        access_token: Current access token
        refresh_token: Refresh token to revoke (optional, will be sent in body if provided)
        api_environment: API environment to use for logout

    Returns:
        True if logout successful, False otherwise
    """
    if not access_token:
        return False

    # Import here to avoid circular imports
    from ..config import get_auth_url

    # Get the auth URL for the specified environment
    auth_url = get_auth_url(api_environment)

    try:
        headers = {"Authorization": f"Bearer {access_token}"}

        # Prepare request body with refresh token if provided
        logout_data = {}
        if refresh_token:
            logout_data["refresh_token"] = refresh_token

        resp = requests.post(
            f"{auth_url}/logout",
            headers=headers,
            json=logout_data if logout_data else None,
            timeout=10,
        )

        if resp.status_code == 200:
            print("✅ User logged out successfully")
            return True
        else:
            print(f"❌ Logout failed with status: {resp.status_code}")
            return False

    except requests.exceptions.Timeout:
        print("⏰ Logout request timed out")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Connection error during logout")
        return False
    except Exception as e:
        print(f"💥 Error during logout: {str(e)}")
        return False


def logout_all_devices(access_token: str) -> bool:
    """Logout user from all devices by revoking all refresh tokens.

    Args:
        access_token: Current access token

    Returns:
        True if logout successful, False otherwise
    """
    if not access_token:
        return False

    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = requests.post(f"{AUTH_URL}/logout-all", headers=headers, timeout=10)

        if resp.status_code == 200:
            print("✅ User logged out from all devices successfully")
            return True
        else:
            print(f"❌ Logout from all devices failed with status: {resp.status_code}")
            return False

    except requests.exceptions.Timeout:
        print("⏰ Logout all devices request timed out")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Connection error during logout from all devices")
        return False
    except Exception as e:
        print(f"💥 Error during logout from all devices: {str(e)}")
        return False


def make_authenticated_request(
    url: str, token: str, method: str = "GET", **kwargs
) -> requests.Response:
    """Make an authenticated API request with automatic token refresh on authentication failure.

    Args:
        url: The API endpoint URL (can be relative like '/script/123/log' or full URL)
        token: Current access token
        method: HTTP method (GET, POST, etc.)
        **kwargs: Additional arguments to pass to requests

    Returns:
        requests.Response object
    """
    from ..config import get_current_api_base

    # If URL is relative (starts with /), prepend the current API base
    full_url = get_current_api_base() + url if url.startswith("/") else url

    headers = kwargs.get("headers", {})
    headers["Authorization"] = f"Bearer {token}"
    kwargs["headers"] = headers

    # Make the initial request
    resp = getattr(requests, method.lower())(full_url, **kwargs)

    # If authentication failed, try to refresh the token and retry
    # Look for 401 Unauthorized or 422 with signature-related errors
    if resp.status_code in [401, 422] and "signature" in resp.text.lower():
        import json

        from flask import request

        from .jwt_helpers import should_refresh_token

        print(
            f"🔄 Authentication failed for {method} {full_url} (status: {resp.status_code}), attempting token refresh..."
        )

        # Check if the token actually needs refreshing (might be an API issue, not token expiry)
        if not should_refresh_token(token, buffer_minutes=1):
            print("⚠️ Token appears to still be valid, API authentication issue may be server-side")
            return resp  # Return original response if token seems fine

        # Try to get refresh token from cookie
        refresh_token = None
        api_environment = None
        cookie_data = None
        try:
            auth_cookie = request.cookies.get("auth_token")
            if auth_cookie:
                cookie_data = json.loads(auth_cookie)
                if cookie_data and isinstance(cookie_data, dict):
                    refresh_token = cookie_data.get("refresh_token")
                    api_environment = cookie_data.get("api_environment", "production")
        except Exception as e:
            print(f"Error reading refresh token from cookie: {e}")

        if refresh_token:
            new_access_token, expires_in = refresh_access_token(refresh_token, api_environment)
            if new_access_token:
                print(f"✅ Token refreshed successfully, retrying {method} {full_url}...")

                # Update cookie with new access token to maintain session
                try:
                    from flask import g

                    from ..config import get_current_api_base
                    from .cookies import create_auth_cookie_data

                    if cookie_data:
                        email = cookie_data.get("email")
                        user_data = cookie_data.get("user_data")

                        # Store the updated cookie data in flask.g for later use
                        new_cookie_data = create_auth_cookie_data(
                            new_access_token, refresh_token, email, user_data, api_environment
                        )
                        g.updated_auth_cookie = json.dumps(new_cookie_data)
                        print("📝 Prepared updated cookie data for session maintenance")
                except Exception as e:
                    print(f"Error preparing updated cookie: {e}")

                # Retry with new token
                headers["Authorization"] = f"Bearer {new_access_token}"
                kwargs["headers"] = headers
                resp = getattr(requests, method.lower())(full_url, **kwargs)
            else:
                print("❌ Token refresh failed")
        else:
            print("❌ No refresh token available")

    return resp
