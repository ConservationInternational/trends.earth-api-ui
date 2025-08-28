"""
Test to verify the JavaScript console filtering fix in app.py.
"""

import re


def test_app_index_string_has_safe_shouldfilter():
    """Test that the shouldFilter function in app.index_string safely handles undefined arguments."""
    import os
    import sys

    # Add the project root to the path
    project_root = os.path.join(os.path.dirname(__file__), "..", "..")
    sys.path.insert(0, project_root)

    try:
        from trendsearth_ui import app

        # Get the index string
        index_string = app.app.index_string

        # Check that the shouldFilter function exists
        assert "function shouldFilter(args)" in index_string, (
            "shouldFilter function should be present in index_string"
        )

        # Check that it has the safety check for undefined/null args
        assert "if (!args || typeof args.length !== 'number')" in index_string, (
            "shouldFilter should check for undefined/null args before using join"
        )

        # Check that it returns false for invalid args
        assert "return false;" in index_string, (
            "shouldFilter should return false for invalid arguments"
        )

        # Verify the complete pattern exists (safety check before Array.prototype.join.call)
        pattern = re.compile(
            r"function shouldFilter\(args\)\s*\{\s*try\s*\{\s*"
            r".*?if\s*\(\s*!args\s*\|\|\s*typeof\s+args\.length\s*!==\s*['\"]number['\"]\s*\)",
            re.DOTALL,
        )
        assert pattern.search(index_string), (
            "shouldFilter should have safety check before calling Array.prototype.join.call"
        )

    except ImportError as e:
        import pytest

        pytest.skip(f"Could not import app module: {e}")


def test_app_index_string_console_error_wrapper():
    """Test that console.error is properly wrapped with the fixed shouldFilter function."""
    import os
    import sys

    # Add the project root to the path
    project_root = os.path.join(os.path.dirname(__file__), "..", "..")
    sys.path.insert(0, project_root)

    try:
        from trendsearth_ui import app

        # Get the index string
        index_string = app.app.index_string

        # Check that console.error is wrapped
        assert "console.error = function ()" in index_string, "console.error should be wrapped"

        # Check that it calls shouldFilter with arguments
        assert "if (shouldFilter(arguments))" in index_string, (
            "console.error wrapper should call shouldFilter with arguments"
        )

        # Check that console.warn is also wrapped
        assert "console.warn = function ()" in index_string, "console.warn should also be wrapped"

    except ImportError as e:
        import pytest

        pytest.skip(f"Could not import app module: {e}")


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
