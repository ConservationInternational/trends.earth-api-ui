"""Unit tests for JSON utility functions."""

import json

from trendsearth_ui.utils.json_utils import render_json_tree


class TestRenderJSONTree:
    """Test the render_json_tree utility function."""

    def test_render_simple_dict(self):
        """Test rendering a simple dictionary."""
        data = {"key": "value", "number": 42}
        result = render_json_tree(data)

        # Should return a Dash component with enhanced viewer
        assert hasattr(result, "children")
        assert isinstance(result.children, list)
        # Should have controls, tree container, and trigger elements when interactive is enabled (default)
        assert len(result.children) == 3  # Controls + tree container + trigger elements

    def test_render_nested_dict(self):
        """Test rendering nested dictionaries."""
        data = {"outer": {"inner": "value", "nested": {"deep": "data"}}, "simple": "value"}
        result = render_json_tree(data)

        # Should return a Dash component with nested structure
        assert hasattr(result, "children")
        assert isinstance(result.children, list)

    def test_render_list(self):
        """Test rendering a list."""
        data = ["item1", "item2", {"nested": "object"}]
        result = render_json_tree(data)

        # Should return a Dash component
        assert hasattr(result, "children")
        assert isinstance(result.children, list)

    def test_render_nested_list(self):
        """Test rendering nested lists."""
        data = [["nested", "list"], {"object": "in list"}, "simple item"]
        result = render_json_tree(data)

        # Should return a Dash component
        assert hasattr(result, "children")
        assert isinstance(result.children, list)

    def test_render_simple_values(self):
        """Test rendering simple values."""
        # Test string
        result = render_json_tree("simple string")
        assert hasattr(result, "children")

        # Test number
        result = render_json_tree(42)
        assert hasattr(result, "children")

        # Test boolean
        result = render_json_tree(True)
        assert hasattr(result, "children")

        # Test None
        result = render_json_tree(None)
        assert hasattr(result, "children")

    def test_render_json_string_parsing(self):
        """Test rendering JSON string (should be parsed)."""
        json_string = json.dumps({"key": "value", "number": 42})
        result = render_json_tree(json_string)

        # Should parse the JSON and render the resulting object
        assert hasattr(result, "children")
        assert isinstance(result.children, list)

    def test_render_invalid_json_string_handling(self):
        """Test rendering invalid JSON string."""
        invalid_json = "not valid json {"
        result = render_json_tree(invalid_json)

        # Should handle the invalid JSON gracefully
        assert hasattr(result, "children")

    def test_render_empty_structures_display(self):
        """Test rendering empty structures."""
        # Empty dict
        result = render_json_tree({})
        assert hasattr(result, "children")

        # Empty list
        result = render_json_tree([])
        assert hasattr(result, "children")

    def test_render_with_level_variations(self):
        """Test rendering with different level parameters."""
        data = {"nested": {"deep": "value"}}

        # Test with level 0 (default)
        result_0 = render_json_tree(data, level=0)
        assert hasattr(result_0, "children")

        # Test with level 1
        result_1 = render_json_tree(data, level=1)
        assert hasattr(result_1, "children")

        # Test with level 2
        result_2 = render_json_tree(data, level=2)
        assert hasattr(result_2, "children")

    def test_render_with_parent_id_variations(self):
        """Test rendering with different parent_id parameters."""
        data = {"key": "value"}

        # Test with default parent_id
        result_default = render_json_tree(data)
        assert hasattr(result_default, "children")

        # Test with custom parent_id
        result_custom = render_json_tree(data, parent_id="custom-parent")
        assert hasattr(result_custom, "children")

    def test_render_with_interactive_disabled(self):
        """Test rendering with interactive features disabled."""
        data = {"key": "value", "number": 42}
        result = render_json_tree(data, enable_interactive=False)

        # Should return a simpler structure without controls
        assert hasattr(result, "children")
        # When interactive is disabled, it should not have the control panel

    def test_render_complex_mixed_data(self):
        """Test rendering complex mixed data structure."""
        data = {
            "users": [
                {"id": 1, "name": "User 1", "active": True},
                {"id": 2, "name": "User 2", "active": False},
            ],
            "metadata": {"total": 2, "page": 1, "filters": ["active", "recent"]},
            "simple_field": "value",
            "number_field": 42,
            "null_field": None,
        }

        result = render_json_tree(data)
        assert hasattr(result, "children")
        assert isinstance(result.children, list)
        # Complex structure should create multiple child components
        assert len(result.children) > 0

    def test_render_with_copy_buttons(self):
        """Test that copy buttons are rendered for values."""
        data = {"key": "value"}
        result = render_json_tree(data)

        # Convert to string to check for copy button elements
        result_str = str(result)
        assert "json-copy-btn" in result_str
        assert "fa-copy" in result_str

    def test_render_type_badges(self):
        """Test that type badges are rendered for complex structures."""
        data = {"object": {"nested": "value"}, "array": [1, 2, 3]}
        result = render_json_tree(data)

        # Convert to string to check for badge elements
        result_str = str(result)
        assert "badge" in result_str
        assert "object" in result_str
        assert "array" in result_str
        result = render_json_tree("simple string")
        assert hasattr(result, "children")

        # Test number
        result = render_json_tree(42)
        assert hasattr(result, "children")

        # Test boolean
        result = render_json_tree(True)
        assert hasattr(result, "children")

        # Test None
        result = render_json_tree(None)
        assert hasattr(result, "children")

    def test_render_json_string(self):
        """Test rendering JSON string (should be parsed)."""
        json_string = json.dumps({"key": "value", "number": 42})
        result = render_json_tree(json_string)

        # Should parse the JSON and render the resulting object
        assert hasattr(result, "children")
        assert isinstance(result.children, list)

    def test_render_invalid_json_string(self):
        """Test rendering invalid JSON string."""
        invalid_json = "not valid json {"
        result = render_json_tree(invalid_json)

        # Should handle the invalid JSON gracefully
        assert hasattr(result, "children")

    def test_render_empty_structures(self):
        """Test rendering empty structures."""
        # Empty dict
        result = render_json_tree({})
        assert hasattr(result, "children")

        # Empty list
        result = render_json_tree([])
        assert hasattr(result, "children")

    def test_render_with_level_parameter(self):
        """Test rendering with different level parameters."""
        data = {"nested": {"deep": "value"}}

        # Test with level 0 (default)
        result_0 = render_json_tree(data, level=0)
        assert hasattr(result_0, "children")

        # Test with level 1
        result_1 = render_json_tree(data, level=1)
        assert hasattr(result_1, "children")

        # Test with level 2
        result_2 = render_json_tree(data, level=2)
        assert hasattr(result_2, "children")

    def test_render_with_parent_id_parameter(self):
        """Test rendering with different parent_id parameters."""
        data = {"key": "value"}

        # Test with default parent_id
        result_default = render_json_tree(data)
        assert hasattr(result_default, "children")

        # Test with custom parent_id
        result_custom = render_json_tree(data, parent_id="custom-parent")
        assert hasattr(result_custom, "children")

    def test_render_complex_mixed_structure(self):
        """Test rendering complex mixed data structure."""
        data = {
            "users": [
                {"id": 1, "name": "User 1", "active": True},
                {"id": 2, "name": "User 2", "active": False},
            ],
            "metadata": {"total": 2, "page": 1, "filters": ["active", "recent"]},
            "simple_field": "value",
            "number_field": 42,
            "null_field": None,
        }

        result = render_json_tree(data)
        assert hasattr(result, "children")
        assert isinstance(result.children, list)
        # Complex structure should create multiple child components
        assert len(result.children) > 0
