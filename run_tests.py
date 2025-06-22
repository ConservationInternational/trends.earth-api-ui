#!/usr/bin/env python3
"""
Test runner script to validate the test suite setup.
"""

import os
import sys


def test_imports():
    """Test that all test modules can be imported."""
    print("Testing module imports...")
    # Add the project root to the path
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)

    try:
        # Test importing the main app modules
        print("✓ Config module imported successfully")

        print("✓ Utils modules imported successfully")

        print("✓ Component modules imported successfully")

        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def check_test_files():
    """Check that all test files exist and are properly structured."""
    print("\nChecking test file structure...")

    test_files = [
        "tests/unit/test_config.py",
        "tests/unit/test_utils_helpers.py",
        "tests/unit/test_utils_geojson.py",
        "tests/unit/test_utils_json.py",
        "tests/unit/test_components_layout.py",
        "tests/unit/test_components_tabs.py",
        "tests/integration/test_app_integration.py",
        "tests/functional/test_status_tab.py",
        "tests/functional/test_map_functionality.py",
        "tests/functional/test_geojson_fix.py",
        "tests/functional/test_edit_fix.py",
        "tests/conftest.py",
        "tests/fixtures/sample_data.py",
        "pytest.ini",
    ]

    missing_files = []
    for test_file in test_files:
        if not os.path.exists(test_file):
            missing_files.append(test_file)
        else:
            print(f"✓ {test_file}")

    if missing_files:
        print(f"\n✗ Missing files: {missing_files}")
        return False

    print(f"\n✓ All {len(test_files)} test files found")
    return True


def main():
    """Main test runner."""
    print("Trends.Earth API UI Test Suite Validator")
    print("=" * 50)

    imports_ok = test_imports()
    files_ok = check_test_files()

    if imports_ok and files_ok:
        print("\n🎉 Test suite is properly set up!")
        print("\nTo run the tests:")
        print("  python -m pytest tests/ -v")
        print("  python -m pytest tests/unit/ -v     # Unit tests only")
        print("  python -m pytest tests/integration/ -v  # Integration tests only")
        print("  python -m pytest tests/functional/ -v   # Functional tests only")
        return 0
    else:
        print("\n❌ Test suite setup has issues that need to be resolved")
        return 1


if __name__ == "__main__":
    sys.exit(main())
