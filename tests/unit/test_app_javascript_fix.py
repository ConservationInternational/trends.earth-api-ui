"""Tests verifying the app index template avoids inline console scripts."""


def _get_project_root():
    import os

    return os.path.join(os.path.dirname(__file__), "..", "..")


def test_app_index_string_has_no_console_filter_script():
    """The index template should not embed inline console filtering JavaScript."""
    import os
    import sys

    project_root = _get_project_root()
    sys.path.insert(0, project_root)

    try:
        from trendsearth_ui import app

        index_string = app.app.index_string

        assert "function shouldFilter" not in index_string
        assert "console.error = function" not in index_string
        assert "console.warn = function" not in index_string

    except ImportError as exc:  # pragma: no cover - defensive
        import pytest

        pytest.skip(f"Could not import app module: {exc}")


def test_dash_renderer_asset_exists():
    """The Dash renderer should be initialized via a static asset."""
    import os
    from pathlib import Path

    asset_path = Path(_get_project_root()) / "trendsearth_ui" / "assets" / "dash_renderer.js"

    assert asset_path.exists(), "dash_renderer.js asset should exist"

    contents = asset_path.read_text(encoding="utf-8")
    assert "DashRenderer" in contents
    assert "window.__dash_renderer__" in contents


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
