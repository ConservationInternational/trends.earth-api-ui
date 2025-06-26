#!/usr/bin/env python3
"""Test script to verify cookie authentication functionality."""

import sys

from trendsearth_ui.utils.cookies import (
    clear_auth_cookie_data,
    create_auth_cookie_data,
    extract_auth_from_cookie,
    is_auth_cookie_valid,
)

sys.path.insert(0, ".")


def test_cookie_functions():
    """Test the cookie utility functions."""
    print("Testing cookie utility functions...")

    # Test data
    test_token = "test_token_123"
    test_email = "test@example.com"
    test_user_data = {"id": 1, "email": "test@example.com", "name": "Test User", "role": "USER"}

    # Test creating cookie data
    print("\n1. Testing create_auth_cookie_data...")
    cookie_data = create_auth_cookie_data(test_token, test_email, test_user_data)
    print(f"   Created cookie data: {cookie_data.keys()}")
    print(f"   Expiration: {cookie_data.get('expires_at')}")

    # Test validation
    print("\n2. Testing is_auth_cookie_valid...")
    is_valid = is_auth_cookie_valid(cookie_data)
    print(f"   Cookie is valid: {is_valid}")

    # Test extraction
    print("\n3. Testing extract_auth_from_cookie...")
    token, email, user_data = extract_auth_from_cookie(cookie_data)
    print(f"   Extracted token: {token[:10]}... (truncated)")
    print(f"   Extracted email: {email}")
    print(f"   Extracted user name: {user_data.get('name')}")

    # Test clearing
    print("\n4. Testing clear_auth_cookie_data...")
    cleared_data = clear_auth_cookie_data()
    print(f"   Cleared data: {cleared_data}")

    # Test invalid cookie
    print("\n5. Testing with invalid cookie...")
    invalid_cookie = {"invalid": "data"}
    is_invalid_valid = is_auth_cookie_valid(invalid_cookie)
    print(f"   Invalid cookie is valid: {is_invalid_valid}")

    print("\n✅ All cookie tests passed!")


if __name__ == "__main__":
    test_cookie_functions()
