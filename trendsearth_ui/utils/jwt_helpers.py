"""JWT token utility functions for debugging token expiration issues."""

import base64
from datetime import datetime, timedelta, timezone
import json
from typing import Any, Optional


def should_refresh_token(access_token: str, buffer_minutes: int = 5) -> bool:
    """Check if an access token should be refreshed based on its expiration.

    Args:
        access_token: JWT access token to check
        buffer_minutes: Minutes before expiration to trigger refresh (default: 5)

    Returns:
        True if token should be refreshed, False otherwise
    """
    if not access_token:
        return True  # No token, needs refresh

    exp_time = get_token_expiration(access_token)
    if exp_time is None:
        # Can't determine expiration, be safe and refresh
        return True

    now = datetime.now(timezone.utc)
    buffer_time = exp_time - timedelta(minutes=buffer_minutes)

    # Refresh if we're within the buffer time or already expired
    should_refresh = now >= buffer_time

    if should_refresh:
        time_left = (exp_time - now).total_seconds() / 60
        print(f"🔄 Token should be refreshed - {time_left:.1f} minutes until expiry")

    return should_refresh


def decode_jwt_payload(token: str) -> Optional[dict[str, Any]]:
    """Decode JWT token payload without verification (for debugging only).

    Args:
        token: JWT token string

    Returns:
        Decoded payload dictionary or None if decode fails
    """
    if not token:
        return None

    try:
        # JWT tokens have 3 parts separated by dots: header.payload.signature
        parts = token.split(".")
        if len(parts) != 3:
            return None

        # The payload is the second part (index 1)
        payload_part = parts[1]

        # Add padding if needed (base64 requires length to be multiple of 4)
        padding = len(payload_part) % 4
        if padding:
            payload_part += "=" * (4 - padding)

        # Decode from base64
        decoded_bytes = base64.urlsafe_b64decode(payload_part)
        payload = json.loads(decoded_bytes)

        return payload

    except Exception as e:
        print(f"Error decoding JWT payload: {e}")
        return None


def get_token_expiration(token: str) -> Optional[datetime]:
    """Get the expiration time of a JWT token.

    Args:
        token: JWT token string

    Returns:
        Expiration datetime (UTC) or None if not found/invalid
    """
    payload = decode_jwt_payload(token)
    if not payload:
        return None

    exp_timestamp = payload.get("exp")
    if not exp_timestamp:
        return None

    try:
        # Convert Unix timestamp to datetime (UTC)
        return datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
    except Exception as e:
        print(f"Error converting expiration timestamp: {e}")
        return None


def is_token_expired(token: str) -> bool:
    """Check if a JWT token is expired.

    Args:
        token: JWT token string

    Returns:
        True if token is expired, False if still valid, None if unable to determine
    """
    exp_time = get_token_expiration(token)
    if exp_time is None:
        return None

    now = datetime.now(timezone.utc)
    return now >= exp_time


def get_token_info(token: str) -> dict[str, Any]:
    """Get comprehensive information about a JWT token.

    Args:
        token: JWT token string

    Returns:
        Dictionary with token information
    """
    info = {
        "valid": False,
        "payload": None,
        "exp_timestamp": None,
        "exp_datetime": None,
        "exp_local": None,
        "is_expired": None,
        "time_until_expiry": None,
        "issued_at": None,
        "subject": None,
        "issuer": None,
    }

    try:
        payload = decode_jwt_payload(token)
        if not payload:
            return info

        info["valid"] = True
        info["payload"] = payload

        # Expiration info
        if "exp" in payload:
            exp_timestamp = payload["exp"]
            info["exp_timestamp"] = exp_timestamp

            exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            info["exp_datetime"] = exp_datetime
            info["exp_local"] = exp_datetime.astimezone()

            now = datetime.now(timezone.utc)
            info["is_expired"] = now >= exp_datetime

            if not info["is_expired"]:
                time_diff = exp_datetime - now
                info["time_until_expiry"] = {
                    "total_seconds": time_diff.total_seconds(),
                    "minutes": time_diff.total_seconds() / 60,
                    "hours": time_diff.total_seconds() / 3600,
                    "readable": str(time_diff).split(".")[0],  # Remove microseconds
                }

        # Other standard JWT claims
        if "iat" in payload:
            iat_timestamp = payload["iat"]
            iat_datetime = datetime.fromtimestamp(iat_timestamp, tz=timezone.utc)
            info["issued_at"] = iat_datetime.astimezone()

        info["subject"] = payload.get("sub")
        info["issuer"] = payload.get("iss")

    except Exception as e:
        print(f"Error getting token info: {e}")

    return info


def debug_token_expiration(access_token: str, refresh_token: str = None) -> None:
    """Debug token expiration information (prints detailed info).

    Args:
        access_token: Access token to analyze
        refresh_token: Optional refresh token to analyze
    """
    print("🔍 JWT Token Analysis")
    print("=" * 50)

    if access_token:
        print("\n📄 ACCESS TOKEN:")
        access_info = get_token_info(access_token)

        if access_info["valid"]:
            print("   ✅ Valid JWT structure")
            if access_info["exp_datetime"]:
                print(f"   ⏰ Expires: {access_info['exp_local']}")
                if access_info["is_expired"]:
                    print("   ❌ STATUS: EXPIRED")
                else:
                    print("   ✅ STATUS: VALID")
                    exp_info = access_info["time_until_expiry"]
                    print(f"   ⏳ Time until expiry: {exp_info['readable']}")
                    print(f"   📊 Minutes remaining: {exp_info['minutes']:.1f}")
            else:
                print("   ⚠️  No expiration claim found")

            if access_info["issued_at"]:
                print(f"   📅 Issued: {access_info['issued_at']}")

            if access_info["subject"]:
                print(f"   👤 Subject: {access_info['subject']}")
        else:
            print("   ❌ Invalid JWT structure")

    if refresh_token:
        print("\n🔄 REFRESH TOKEN:")
        refresh_info = get_token_info(refresh_token)

        if refresh_info["valid"]:
            print("   ✅ Valid JWT structure")
            if refresh_info["exp_datetime"]:
                print(f"   ⏰ Expires: {refresh_info['exp_local']}")
                if refresh_info["is_expired"]:
                    print("   ❌ STATUS: EXPIRED")
                else:
                    print("   ✅ STATUS: VALID")
                    exp_info = refresh_info["time_until_expiry"]
                    print(f"   ⏳ Time until expiry: {exp_info['readable']}")
                    print(f"   📊 Hours remaining: {exp_info['hours']:.1f}")
            else:
                print("   ⚠️  No expiration claim found")
        else:
            print("   ❌ Invalid JWT structure")

    print("=" * 50)
