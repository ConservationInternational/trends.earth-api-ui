"""Cookie utility functions for authentication persistence."""

from datetime import datetime, timedelta
from typing import Optional


def create_auth_cookie_data(token: str, email: str, user_data: dict) -> dict:
    """Create cookie data structure with expiration timestamp.

    Args:
        token: JWT access token
        email: User email address
        user_data: User information dictionary

    Returns:
        Dictionary containing auth data with expiration timestamp
    """
    # Set expiration to 6 hours from now
    expiration = datetime.now() + timedelta(hours=6)

    return {
        "token": token,
        "email": email,
        "user_data": user_data,
        "expires_at": expiration.isoformat(),
        "created_at": datetime.now().isoformat(),
    }


def is_auth_cookie_valid(cookie_data: Optional[dict]) -> bool:
    """Check if authentication cookie data is valid and not expired.

    Args:
        cookie_data: Cookie data dictionary or None

    Returns:
        True if cookie is valid and not expired, False otherwise
    """
    if not cookie_data or not isinstance(cookie_data, dict):
        return False

    required_fields = ["token", "email", "user_data", "expires_at"]
    if not all(field in cookie_data for field in required_fields):
        return False

    try:
        expiration = datetime.fromisoformat(cookie_data["expires_at"])
        return datetime.now() < expiration
    except (ValueError, TypeError):
        return False


def extract_auth_from_cookie(
    cookie_data: Optional[dict],
) -> tuple[Optional[str], Optional[str], Optional[dict]]:
    """Extract authentication data from cookie if valid.

    Args:
        cookie_data: Cookie data dictionary or None

    Returns:
        Tuple of (token, email, user_data) or (None, None, None) if invalid
    """
    if not is_auth_cookie_valid(cookie_data):
        return None, None, None

    return (cookie_data.get("token"), cookie_data.get("email"), cookie_data.get("user_data"))


def clear_auth_cookie_data() -> dict:
    """Return data structure to clear authentication cookie.

    Returns:
        Empty dictionary to clear cookie
    """
    return {}
