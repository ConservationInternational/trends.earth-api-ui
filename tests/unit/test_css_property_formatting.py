"""Test for CSS property formatting to prevent React infinite loops."""

import pytest
from trendsearth_ui.components.layout import login_layout


class TestCSSPropertyFormatting:
    """Test that CSS properties use camelCase to prevent React errors."""

    def test_login_layout_css_properties(self):
        """Test that login layout uses camelCase CSS properties."""
        layout = login_layout()
        layout_str = str(layout)
        
        # These kebab-case properties should not be present (they cause React errors)
        forbidden_properties = [
            'margin-top',
            'min-height', 
            'white-space',
            'background-color',
            'max-width'
        ]
        
        for prop in forbidden_properties:
            assert prop not in layout_str, f"Found invalid kebab-case CSS property '{prop}' - should be camelCase"
        
        # These camelCase properties should be present
        assert 'marginTop' in layout_str, "Expected camelCase 'marginTop' property not found"
        assert 'minHeight' in layout_str, "Expected camelCase 'minHeight' property not found"

    def test_no_react_error_causing_styles(self):
        """Test that layout doesn't contain CSS properties that cause React Error #130."""
        layout = login_layout()
        layout_str = str(layout)
        
        # These are the specific properties that were causing the infinite loop
        assert 'margin-top' not in layout_str, "margin-top causes React Error #130 - use marginTop instead"
        assert 'min-height' not in layout_str, "min-height causes React Error #130 - use minHeight instead"
        
        # Verify the correct camelCase versions are present
        assert 'marginTop' in layout_str, "marginTop property should be present"
        assert 'minHeight' in layout_str, "minHeight property should be present"