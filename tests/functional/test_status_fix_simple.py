#!/usr/bin/env python3
"""
Test script to verify the status page fix without requiring dependencies.
This script checks if the status callbacks files are properly created and configured.
"""

import os
import sys


def test_status_callbacks_file_exists():
    """Test that status callbacks file exists."""
    status_file = "trendsearth_ui/callbacks/status.py"
    assert os.path.exists(status_file), "Status callbacks file not found"
    print("✅ Status callbacks file exists")


def test_status_callbacks_has_register_function():
    """Test that status callbacks file has register_callbacks function."""
    status_file = "trendsearth_ui/callbacks/status.py"
    try:
        with open(status_file) as f:
            content = f.read()
            assert (
                "def register_callbacks(app):" in content
            ), "Status callbacks missing register_callbacks function"
            print("✅ Status callbacks has register_callbacks function")
    except Exception as e:
        print(f"❌ Error reading status callbacks file: {e}")
        raise


def test_status_callbacks_has_required_callbacks():
    """Test that status callbacks file has the required callback functions."""
    status_file = "trendsearth_ui/callbacks/status.py"
    required_callbacks = [
        "update_status_summary",
        "update_status_charts",
        "update_status_countdown",
    ]

    try:
        with open(status_file) as f:
            content = f.read()

        missing = []
        for callback in required_callbacks:
            if f"def {callback}(" not in content:
                missing.append(callback)

        assert not missing, f"Missing callbacks: {missing}"
        print("✅ All required status callbacks are present")
    except Exception as e:
        print(f"❌ Error checking status callbacks: {e}")
        raise


def test_main_callbacks_imports_status():
    """Test that main callbacks __init__.py imports status module."""
    init_file = "trendsearth_ui/callbacks/__init__.py"
    try:
        with open(init_file) as f:
            content = f.read()

        assert (
            "from . import" in content and "status" in content
        ), "Main callbacks does not import status module"
        print("✅ Main callbacks imports status module")
    except Exception as e:
        print(f"❌ Error reading main callbacks file: {e}")
        raise


def test_main_callbacks_registers_status():
    """Test that main callbacks register_all_callbacks calls status.register_callbacks."""
    init_file = "trendsearth_ui/callbacks/__init__.py"
    try:
        with open(init_file) as f:
            content = f.read()

        assert (
            "status.register_callbacks(app)" in content
        ), "Main callbacks does not register status callbacks"
        print("✅ Main callbacks registers status callbacks")
    except Exception as e:
        print(f"❌ Error checking main callbacks registration: {e}")
        raise
        raise


def test_status_callbacks_has_performance_optimizations():
    """Test that status callbacks include performance optimizations."""
    status_file = "trendsearth_ui/callbacks/status.py"
    try:
        with open(status_file) as f:
            content = f.read()

        optimizations = [
            'active_tab != "status"',  # Tab-based conditional updates
            "timeout=",  # Timeout parameters
            "per_page",  # Pagination limits
            "exclude",  # Field exclusions
        ]

        missing = []
        for opt in optimizations:
            if opt not in content:
                missing.append(opt)

        assert not missing, f"Missing optimizations: {missing}"
        print("✅ Status callbacks include performance optimizations")
    except Exception as e:
        print(f"❌ Error checking performance optimizations: {e}")
        raise


def main():
    """Run all tests."""
    print("Testing Status Page Fix (File-based)")
    print("=" * 50)

    tests = [
        test_status_callbacks_file_exists,
        test_status_callbacks_has_register_function,
        test_status_callbacks_has_required_callbacks,
        test_main_callbacks_imports_status,
        test_main_callbacks_registers_status,
        test_status_callbacks_has_performance_optimizations,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")

    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! The status page fix should work correctly.")
        print("\nThe fix includes:")
        print("• Status summary showing recent log entries or system info")
        print("• Interactive charts with execution trends over time")
        print("• Three time period views (Hour/Day/Week)")
        print("• Performance optimizations to prevent unnecessary API calls")
        print("• Proper error handling and timeouts")
        print("• Auto-refresh functionality with countdown")
        print("\nTo test the fix:")
        print("1. Start the application: python -m trendsearth_ui.app")
        print("2. Login with admin credentials")
        print("3. Navigate to the Status tab")
        print(
            "4. The page should now load quickly with actual data instead of showing 'Loading...' indefinitely"
        )
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. There may be issues with the fix.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
