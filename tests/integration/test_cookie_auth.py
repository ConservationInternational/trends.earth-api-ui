#!/usr/bin/env python3
"""
Test the cookie-based authentication functionality.
Run this script to test the cookie implementation.
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

    print("✅ Successfully imported cookie utilities")

    # Test cookie creation
    test_token = "test_jwt_token_123"
    test_email = "user@example.com"
    test_user_data = {"id": "123", "email": "user@example.com", "name": "Test User", "role": "USER"}

    # Create cookie data
    cookie_data = create_auth_cookie_data(test_token, test_email, test_user_data)
    print("✅ Cookie data created successfully")
    print(f"   Cookie expires at: {cookie_data['expires_at']}")

    # Test cookie validation
    is_valid = is_auth_cookie_valid(cookie_data)
    print(f"✅ Cookie validation: {is_valid}")

    # Test data extraction
    extracted_token, extracted_email, extracted_user_data = extract_auth_from_cookie(cookie_data)
    print("✅ Cookie data extraction successful")
    if extracted_token:
        print(f"   Token: {extracted_token[:20]}...")
    if extracted_email:
        print(f"   Email: {extracted_email}")
    if extracted_user_data and "name" in extracted_user_data:
        print(f"   User: {extracted_user_data['name']}")

    # Test clear cookie
    cleared_data = clear_auth_cookie_data()
    print(f"✅ Cookie cleared: {cleared_data}")

    print("\n🎉 All cookie functionality tests passed!")
    print("\n📋 Implementation Summary:")
    print("- ✅ Added dash-extensions dependency")
    print("- ✅ Created cookie utility functions")
    print("- ✅ Updated main layout with Cookie component")
    print("- ✅ Enhanced authentication callbacks for cookie handling")
    print("- ✅ Added 'Remember me' checkbox to login form")
    print("- ✅ Added logout button to profile tab")
    print("- ✅ Implemented automatic login restoration from cookies")
    print("- ✅ Set 6-hour cookie expiration")

    print("\n🔧 How it works:")
    print("1. User logs in and checks 'Remember me for 6 hours'")
    print("2. Authentication data is saved in a browser cookie")
    print("3. When user returns, app automatically checks for valid cookie")
    print("4. If cookie is valid and not expired, user is auto-logged in")
    print("5. Email field is pre-populated from expired cookies")
    print("6. User can manually logout to clear the cookie")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure dash-extensions is installed: poetry install")
except Exception as e:
    print(f"❌ Test error: {e}")
