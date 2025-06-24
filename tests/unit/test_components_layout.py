"""Unit tests for layout components."""

from unittest.mock import Mock, patch

from trendsearth_ui.components.layout import create_main_layout, dashboard_layout, login_layout


class TestCreateMainLayout:
    """Test the create_main_layout function."""

    def test_create_main_layout_structure(self):
        """Test that main layout has correct structure."""
        layout = create_main_layout()

        # Should be a Container
        assert hasattr(layout, "children")
        assert isinstance(layout.children, list)

        # Check for required components
        children_types = [type(child).__name__ for child in layout.children]

        # Should contain H1, Div, and multiple Store components
        assert "H1" in children_types
        assert "Div" in children_types
        assert "Store" in children_types

        # Should contain modals
        assert any("Modal" in str(type(child)) for child in layout.children)
    def test_main_layout_stores(self):
        """Test that main layout contains all required stores."""
        layout = create_main_layout()

        # Get all Store components (check component type, not just id)
        stores = [
            child
            for child in layout.children
            if hasattr(child, 'type') and child.type == 'Store'
        ]

        # Should have multiple stores for different data
        assert len(stores) >= 5  # At least token, role, user, scripts, users stores

        store_ids = [store.id for store in stores if hasattr(store, "id")]
        expected_stores = [
            "token-store",
            "role-store",
            "user-store",
            "scripts-raw-data",
            "users-raw-data",
        ]

        for expected_store in expected_stores:
            assert expected_store in store_ids


class TestLoginLayout:
    """Test the login_layout function."""

    def test_login_layout_structure(self):
        """Test that login layout has correct structure."""
        layout = login_layout()

        # Should be a Row component
        assert hasattr(layout, "children")
        assert isinstance(layout.children, list)

        # Should contain a Column with a Card
        col = layout.children[0]
        assert hasattr(col, "children")

        card = col.children
        assert hasattr(card, "children")

    def test_login_layout_form_elements(self):
        """Test that login layout contains required form elements."""
        layout = login_layout()

        # Convert to string to search for component IDs
        layout_str = str(layout)

        # Should contain login form elements
        assert "login-email" in layout_str
        assert "login-password" in layout_str
        assert "login-btn" in layout_str
        assert "login-alert" in layout_str

    def test_login_layout_logo(self):
        """Test that login layout contains logo."""
        layout = login_layout()
        layout_str = str(layout)

        # Should contain logo image
        assert "trends_earth_logo" in layout_str or "Trends.Earth Logo" in layout_str


class TestDashboardLayout:
    """Test the dashboard_layout function."""

    def test_dashboard_layout_structure(self):
        """Test that dashboard layout has correct structure."""
        layout = dashboard_layout()

        # Should be a list of components
        assert isinstance(layout, list)
        assert len(layout) > 0

    def test_dashboard_layout_tabs(self):
        """Test that dashboard layout contains tabs."""
        layout = dashboard_layout()
        layout_str = str(layout)

        # Should contain tab structure
        assert "tabs" in layout_str.lower()
        assert "tab-content" in layout_str

        # Should contain expected tabs
        expected_tabs = ["executions", "users", "scripts", "status", "profile"]
        for tab in expected_tabs:
            assert tab in layout_str.lower()

    def test_dashboard_layout_alert(self):
        """Test that dashboard layout contains alert component."""
        layout = dashboard_layout()
        layout_str = str(layout)

        # Should contain alert for notifications
        assert "alert" in layout_str.lower()

    def test_dashboard_layout_collapse(self):
        """Test that dashboard layout contains collapsible panel."""
        layout = dashboard_layout()
        layout_str = str(layout)

        # Should contain main panel that can be collapsed
        assert "main-panel" in layout_str


class TestLayoutIntegration:
    """Test integration between layout components."""

    def test_layouts_are_compatible(self):
        """Test that all layouts can be created without errors."""
        # All layout functions should execute without errors
        main = create_main_layout()
        login = login_layout()
        dashboard = dashboard_layout()

        assert main is not None
        assert login is not None
        assert dashboard is not None

    def test_main_layout_can_contain_other_layouts(self):
        """Test that main layout structure can accommodate other layouts."""
        main = create_main_layout()

        # Main layout should have a page-content div that can hold other layouts
        layout_str = str(main)
        assert "page-content" in layout_str

        # The page-content should be able to receive other layouts
        page_content = None
        for child in main.children:
            if hasattr(child, "id") and child.id == "page-content":
                page_content = child
                break

        assert page_content is not None
