#!/usr/bin/env python3
"""Test script to debug login issues."""

import os

import pytest
import requests

from trendsearth_ui.config import API_BASE, AUTH_URL
from trendsearth_ui.utils import get_user_info


@pytest.mark.skip(reason="Interactive test - requires manual credentials")
def test_login():
    """Test the login process step by step."""
    print("Testing Trends.Earth API login...")
    print(f"AUTH_URL: {AUTH_URL}")
    print(f"API_BASE: {API_BASE}")

    # Test credentials - use environment variables for CI
    test_email = os.getenv("TEST_EMAIL")
    test_password = os.getenv("TEST_PASSWORD")

    if not test_email or not test_password:
        pytest.skip("TEST_EMAIL and TEST_PASSWORD environment variables required")

    print("\n1. Testing login endpoint...")
    auth_data = {"email": test_email, "password": test_password}

    print("\n1. Testing login endpoint...")
    auth_data = {"email": test_email, "password": test_password}

    try:
        resp = requests.post(f"{AUTH_URL}/login", json=auth_data, timeout=10)
        print(f"   Status code: {resp.status_code}")
        print(f"   Response headers: {dict(resp.headers)}")

        if resp.status_code == 200:
            data = resp.json()
            print(f"   Response data keys: {list(data.keys())}")
            token = data.get("access_token")
            print(f"   Token present: {bool(token)}")

            if token:
                print(f"   Token (first 20 chars): {token[:20]}...")

                print("\n2. Testing user info retrieval...")
                user_data = get_user_info(token)
                print(f"   User data: {user_data}")

                if user_data:
                    role = user_data.get("role", "USER")
                    print(f"   User role: {role}")
                    print("✅ Login process successful!")
                else:
                    print("❌ Failed to retrieve user information")
            else:
                print("❌ No access token in response")
        else:
            print(f"❌ Login failed with status {resp.status_code}")
            try:
                error_data = resp.json()
                print(f"   Error response: {error_data}")
            except Exception:
                print(f"   Response text: {resp.text}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    test_login()
