#!/usr/bin/env python3
"""
Simple test script to verify the Dash app can start without errors.
This script imports the app and validates it can be initialized.
"""

import sys
import traceback


def test_app_startup():
    """Test if the app can be imported and initialized without errors."""
    try:
        print("Testing app startup...")

        # Import the main app module
        from trendsearth_ui.app import app, server

        print("✅ App imported successfully")

        # Test that the app has a layout
        assert app.layout is not None, "App layout is None"
        print("✅ App layout created successfully")

        # Test that the server is configured
        assert server is not None, "Flask server is None"
        print("✅ Flask server configured successfully")

        print("✅ All startup tests passed!")

    except ImportError as e:
        print(f"❌ Import error: {e}")
        traceback.print_exc()
        raise
    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
        traceback.print_exc()
        raise
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        traceback.print_exc()
        raise


if __name__ == "__main__":
    success = test_app_startup()
    sys.exit(0 if success else 1)
