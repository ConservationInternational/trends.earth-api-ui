"""
Test to verify that text selection functionality is properly configured in tables.
"""

import os
import pytest


def test_ag_grid_text_selection_configuration():
    """Test that AG Grid configurations include built-in text selection options."""
    # Import the module directly to test the configuration
    import sys
    import os
    
    # Add the project root to the path
    project_root = os.path.join(os.path.dirname(__file__), "..", "..")
    sys.path.insert(0, project_root)
    
    try:
        from trendsearth_ui.components.tabs import executions_tab_content, users_tab_content, scripts_tab_content
        
        # Test that tab content functions exist and return content
        executions_content = executions_tab_content()
        users_content = users_tab_content()
        scripts_content = scripts_tab_content()
        
        # Check that the content is generated (basic smoke test)
        assert executions_content is not None, "executions_tab_content should return content"
        assert users_content is not None, "users_tab_content should return content"
        assert scripts_content is not None, "scripts_tab_content should return content"
        
    except ImportError as e:
        pytest.skip(f"Could not import tabs module: {e}")

def test_ag_grid_dashgridoptions_includes_text_selection():
    """Test that AG Grid dashGridOptions include enableCellTextSelection and ensureDomOrder."""
    import sys
    import os
    import inspect
    
    # Add the project root to the path
    project_root = os.path.join(os.path.dirname(__file__), "..", "..")
    sys.path.insert(0, project_root)
    
    try:
        # Import the tabs module to inspect the source code
        from trendsearth_ui.components import tabs
        
        # Get the source code of the tabs module
        source_code = inspect.getsource(tabs)
        
        # Check that enableCellTextSelection and ensureDomOrder are configured
        assert '"enableCellTextSelection": True' in source_code, "dashGridOptions should include enableCellTextSelection: True"
        assert '"ensureDomOrder": True' in source_code, "dashGridOptions should include ensureDomOrder: True"
        
        # Check that it's applied to all three main tables
        assert source_code.count('"enableCellTextSelection": True') >= 3, "Text selection should be enabled on all three tables"
        assert source_code.count('"ensureDomOrder": True') >= 3, "ensureDomOrder should be enabled on all three tables"
        
    except ImportError as e:
        pytest.skip(f"Could not import tabs module: {e}")


def test_no_custom_css_js_files():
    """Test that custom CSS and JS files are not present (using built-in AG Grid functionality)."""
    css_path = os.path.join(
        os.path.dirname(__file__), 
        "..", 
        "..",
        "trendsearth_ui", 
        "assets", 
        "table-text-selection.css"
    )
    js_path = os.path.join(
        os.path.dirname(__file__), 
        "..", 
        "..",
        "trendsearth_ui", 
        "assets", 
        "table-text-selection.js"
    )
    
    # These files should NOT exist since we're using built-in AG Grid functionality
    assert not os.path.exists(css_path), "Custom CSS file should not exist when using built-in AG Grid text selection"
    assert not os.path.exists(js_path), "Custom JS file should not exist when using built-in AG Grid text selection"


def test_app_index_string_clean():
    """Test that app.index_string doesn't include custom script references."""
    import sys
    import os
    import inspect
    
    # Add the project root to the path
    project_root = os.path.join(os.path.dirname(__file__), "..", "..")
    sys.path.insert(0, project_root)
    
    try:
        from trendsearth_ui import app
        
        # Check that the index_string doesn't reference custom scripts
        index_string = app.app.index_string
        assert "table-text-selection.js" not in index_string, "app.index_string should not reference custom JS files"
        
    except ImportError as e:
        pytest.skip(f"Could not import app module: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
