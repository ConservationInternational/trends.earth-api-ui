#!/usr/bin/env python3
"""Test script to verify no circular import issues in callbacks."""

import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.abspath("."))


def test_imports():
    """Test that all callback modules can be imported without circular imports."""

    print("Testing individual callback module imports...")

    # Test importing individual modules
    modules_to_test = [
        "trendsearth_ui.callbacks.auth",
        "trendsearth_ui.callbacks.edit",
        "trendsearth_ui.callbacks.executions",
        "trendsearth_ui.callbacks.map",
        "trendsearth_ui.callbacks.modals",
        "trendsearth_ui.callbacks.profile",
        "trendsearth_ui.callbacks.refresh",
        "trendsearth_ui.callbacks.status",
        "trendsearth_ui.callbacks.tabs",
    ]

    circular_import_found = False
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"✅ {module} - OK")
        except ImportError as e:
            if "circular import" in str(e):
                print(f"❌ {module} - CIRCULAR IMPORT ERROR: {e}")
                circular_import_found = True
            else:
                print(f"⚠️  {module} - Import error (expected): {e}")
        except Exception as e:
            print(f"⚠️  {module} - Other error: {e}")

    print("\nTesting main callbacks import...")
    try:
        from trendsearth_ui.callbacks import register_all_callbacks

        print("✅ register_all_callbacks import - OK")
    except ImportError as e:
        if "circular import" in str(e):
            print(f"❌ register_all_callbacks - CIRCULAR IMPORT ERROR: {e}")
            circular_import_found = True
        else:
            print(f"⚠️  register_all_callbacks - Import error: {e}")
            # Non-circular import errors are okay for this test

    assert not circular_import_found, "Circular import issues found!"


if __name__ == "__main__":
    print("🔍 Testing callback imports for circular import issues...\n")

    try:
        test_imports()
        print("\n🎉 SUCCESS: No circular import issues detected!")
        sys.exit(0)
    except AssertionError:
        print("\n💥 FAILURE: Circular import issues found!")
        sys.exit(1)
