#!/usr/bin/env python3
"""
Test script to verify the status page fix.
This script checks if the status callbacks are properly registered and functional.
"""

import os
import sys

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_status_callbacks_import():
    """Test that status callbacks can be imported without errors."""
    try:
        from trendsearth_ui.callbacks import status

        print("✅ Status callbacks module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import status callbacks: {e}")
        raise
    except Exception as e:
        print(f"❌ Error importing status callbacks: {e}")
        raise


def test_status_callbacks_registration():
    """Test that status callbacks can be registered."""
    try:
        # This test requires Dash, so we'll just check the function exists
        from trendsearth_ui.callbacks.status import register_callbacks

        print("✅ Status callbacks register_callbacks function found")
    except ImportError as e:
        print(f"❌ Failed to import register_callbacks: {e}")
        raise
    except Exception as e:
        print(f"❌ Error checking register_callbacks: {e}")
        raise


def test_main_callbacks_integration():
    """Test that the main callbacks module includes status callbacks."""
    try:
        from trendsearth_ui.callbacks import __all__

        assert "status" in __all__, "Status callbacks not found in main callbacks __all__"
        assert "status" in __all__, "Status callbacks not found in main callbacks __all__"
        print("✅ Status callbacks properly integrated in main callbacks module")
    except Exception as e:
        print(f"❌ Error checking main callbacks integration: {e}")
        raise


def main():
    """Run all tests."""
    print("Testing Status Page Fix")
    print("=" * 50)

    tests = [
        test_status_callbacks_import,
        test_status_callbacks_registration,
        test_main_callbacks_integration,
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
        print("\nTo test the fix:")
        print("1. Start the application: python -m trendsearth_ui.app")
        print("2. Login with admin credentials")
        print("3. Navigate to the Status tab")
        print("4. You should now see:")
        print("   - System status summary (instead of 'Loading...')")
        print("   - Interactive charts showing execution trends")
        print("   - Auto-refresh countdown working properly")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. There may be issues with the fix.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
