"""Cookie utility functions for authentication persistence."""

from datetime import UTC, datetime, timedelta


def create_auth_cookie_data(
    access_token: str,
    refresh_token: str,
    email: str,
    user_data: dict,
    api_environment: str = "production",
) -> dict:
    """Create cookie data structure with expiration timestamp.

    Args:
        access_token: JWT access token
        refresh_token: Refresh token for obtaining new access tokens
        email: User email address
        user_data: User information dictionary
        api_environment: API environment used for authentication

    Returns:
        Dictionary containing auth data with expiration timestamp
    """
    # Set expiration to 30 days from now for "remember me" functionality
    # This allows refresh tokens to keep users logged in for an extended period
    expiration = datetime.now(UTC) + timedelta(days=30)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "email": email,
        "user_data": user_data,
        "api_environment": api_environment,
        "expires_at": expiration.isoformat(),
        "created_at": datetime.now(UTC).isoformat(),
    }


def is_auth_cookie_valid(cookie_data: dict | None) -> bool:
    """Check if authentication cookie data is valid and not expired.

    Args:
        cookie_data: Cookie data dictionary or None

    Returns:
        True if cookie is valid and not expired, False otherwise
    """
    if not cookie_data or not isinstance(cookie_data, dict):
        return False

    required_fields = ["access_token", "refresh_token", "email", "user_data", "expires_at"]
    if not all(field in cookie_data for field in required_fields):
        return False

    try:
        expiration = datetime.fromisoformat(cookie_data["expires_at"])
        # Ensure both datetimes are timezone-aware for comparison
        now = datetime.now(UTC)
        if expiration.tzinfo is None:
            expiration = expiration.replace(tzinfo=UTC)
        return now < expiration
    except (ValueError, TypeError):
        return False


def extract_auth_from_cookie(
    cookie_data: dict | None,
) -> tuple[str | None, str | None, str | None, dict | None, str | None]:
    """Extract authentication data from cookie if valid.

    Args:
        cookie_data: Cookie data dictionary or None

    Returns:
        Tuple of (access_token, refresh_token, email, user_data, api_environment) or (None, None, None, None, None) if invalid
    """
    if not is_auth_cookie_valid(cookie_data):
        return None, None, None, None, None

    return (
        cookie_data.get("access_token"),
        cookie_data.get("refresh_token"),
        cookie_data.get("email"),
        cookie_data.get("user_data"),
        cookie_data.get("api_environment", "production"),  # Default to production if not set
    )


def clear_auth_cookie_data() -> dict:
    """Return data structure to clear authentication cookie.

    Returns:
        Empty dictionary to clear cookie
    """
    return {}
