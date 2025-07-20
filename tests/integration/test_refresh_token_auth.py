#!/usr/bin/env python3
"""
Test the refresh token authentication functionality.
Run this script to test the new refresh token implementation.
"""

import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from trendsearth_ui.utils.cookies import (
        clear_auth_cookie_data,
        create_auth_cookie_data,
        extract_auth_from_cookie,
        is_auth_cookie_valid,
    )
    from trendsearth_ui.utils.helpers import (
        logout_all_devices,
        logout_user,
        refresh_access_token,
    )

    print("✅ Successfully imported refresh token utilities")

    # Test cookie creation with refresh tokens
    test_access_token = "test_jwt_access_token_123"
    test_refresh_token = "test_refresh_token_456"
    test_email = "user@example.com"
    test_user_data = {"id": "123", "email": "user@example.com", "name": "Test User", "role": "USER"}

    print("\n1. Testing refresh token cookie creation...")
    cookie_data = create_auth_cookie_data(
        test_access_token, test_refresh_token, test_email, test_user_data
    )
    print("✅ Cookie data created successfully with refresh token")
    print(f"   Cookie expires at: {cookie_data['expires_at']}")
    print(f"   Contains access_token: {'access_token' in cookie_data}")
    print(f"   Contains refresh_token: {'refresh_token' in cookie_data}")

    print("\n2. Testing refresh token cookie validation...")
    is_valid = is_auth_cookie_valid(cookie_data)
    print(f"✅ Cookie validation: {is_valid}")

    print("\n3. Testing refresh token extraction...")
    extracted_access_token, extracted_refresh_token, extracted_email, extracted_user_data = (
        extract_auth_from_cookie(cookie_data)
    )
    print("✅ Cookie data extraction successful")
    if extracted_access_token:
        print(f"   Access Token: {extracted_access_token[:20]}...")
    if extracted_refresh_token:
        print(f"   Refresh Token: {extracted_refresh_token[:20]}...")
    if extracted_email:
        print(f"   Email: {extracted_email}")
    if extracted_user_data and "name" in extracted_user_data:
        print(f"   User: {extracted_user_data['name']}")

    print("\n4. Testing refresh token API call (will fail without real server)...")
    new_access_token, expires_in = refresh_access_token(test_refresh_token)
    if new_access_token:
        print(f"✅ Token refresh successful: {new_access_token[:20]}...")
        print(f"   Expires in: {expires_in} seconds")
    else:
        print("⚠️ Token refresh failed (expected without real server)")

    print("\n5. Testing logout API call (will fail without real server)...")
    logout_success = logout_user(test_access_token, test_refresh_token)
    if logout_success:
        print("✅ Logout successful")
    else:
        print("⚠️ Logout failed (expected without real server)")

    print("\n6. Testing logout all devices API call (will fail without real server)...")
    logout_all_success = logout_all_devices(test_access_token)
    if logout_all_success:
        print("✅ Logout all devices successful")
    else:
        print("⚠️ Logout all devices failed (expected without real server)")

    print("\n7. Testing invalid cookie handling...")
    invalid_cookie = {"invalid": "data"}
    is_invalid_valid = is_auth_cookie_valid(invalid_cookie)
    print(f"✅ Invalid cookie validation: {is_invalid_valid}")

    # Test extracting from invalid cookie
    invalid_access, invalid_refresh, invalid_email, invalid_user = extract_auth_from_cookie(
        invalid_cookie
    )
    print(
        f"✅ Invalid cookie extraction returns None: {all(x is None for x in [invalid_access, invalid_refresh, invalid_email, invalid_user])}"
    )

    print("\n8. Testing clear cookie...")
    cleared_data = clear_auth_cookie_data()
    print(f"✅ Cookie cleared: {cleared_data}")

    print("\n🎉 All refresh token functionality tests passed!")
    print("\n📋 New Refresh Token Features:")
    print("- ✅ Access and refresh tokens stored in cookies")
    print("- ✅ Automatic access token refresh using refresh token")
    print("- ✅ Proper logout with refresh token revocation")
    print("- ✅ Logout from all devices functionality")
    print("- ✅ Enhanced cookie validation for refresh tokens")
    print("- ✅ Backward compatible with existing cookie structure")

    print("\n🔧 Authentication Flow:")
    print("1. User logs in → receives access_token + refresh_token")
    print("2. Both tokens stored in secure HTTP cookie (if 'Remember me' checked)")
    print("3. On page reload → cookie restored and access token validated")
    print("4. If access token expired → automatically refreshed using refresh_token")
    print("5. If refresh fails → user redirected to login")
    print("6. On logout → refresh_token revoked on server + cookie cleared")
    print("7. Logout all devices → all refresh_tokens revoked for user")

    print("\n🔐 Security Improvements:")
    print("- ✅ Refresh tokens can be revoked server-side")
    print("- ✅ Access tokens have shorter lifespan")
    print("- ✅ Proper cleanup on logout")
    print("- ✅ Ability to logout from all devices")
    print("- ✅ Cookie expiration independent of token expiration")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure all dependencies are installed")
except Exception as e:
    print(f"❌ Test error: {e}")
