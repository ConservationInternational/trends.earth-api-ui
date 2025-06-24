"""
Functional tests for the Status tab functionality.
"""

import pytest

from trendsearth_ui.components import create_main_layout


def test_app_structure(dash_app):
    """Test if the app loads and has the expected structure."""
    # Check if app object exists
    assert dash_app is not None, "App object should exist"

    # Check if the app layout contains expected components
    layout = dash_app.layout
    layout_str = str(layout)

    # Check for main structural components (tabs are added dynamically via callbacks)
    assert "page-content" in layout_str, "App should have page-content div"
    assert "Store" in layout_str, "App should have data stores"


def test_status_tab_presence(dash_app):
    """Test that the Status tab is present in the dashboard layout."""
    layout = create_main_layout()
    layout_str = str(layout)

    # Check if Status-related content is in the layout
    # This might need adjustment based on actual implementation
    assert "status" in layout_str.lower() or "Status" in layout_str, (
        "Status tab should be in the dashboard layout"
    )


def test_admin_access_components(dash_app):
    """Test that admin-specific components are present in the layout."""
    layout = create_main_layout()
    layout_str = str(layout)

    # Check for components that would be admin-only
    # This is a structural test to ensure admin features exist
    assert "modal" in layout_str.lower() or "Modal" in layout_str, "Admin modals should be present"
    print("- Automatic data refresh after successful edits")
    print("- Proper error handling and user feedback")
    print("- Secure admin-only access to edit functionality")
    print("\nTo use the Status tab:")
    print("1. Start the app using: python -m trendsearth_ui.app")
    print("2. Login with admin credentials")
    print("3. Click on the 'Status' tab")
    print("4. View system status and execution trends")
    print("\nTo use the Edit functionality:")
    print("1. Login as an admin user")
    print("2. Go to the 'Users' or 'Scripts' tab")
    print("3. Click the 'Edit' button in any row")
    print("4. Modify the fields in the modal dialog")
    print("5. Click 'Save Changes' to apply edits")
