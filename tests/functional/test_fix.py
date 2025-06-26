"""
Simple test to verify the tab display fix
"""

import os
import sys

sys.path.insert(0, os.path.abspath("."))

try:
    from trendsearth_ui.callbacks.tabs import register_callbacks
    from trendsearth_ui.components.layout import dashboard_layout

    print("✅ Successfully imported components")

    # Test dashboard layout
    layout = dashboard_layout()
    print("✅ Dashboard layout created successfully")

    # Check if tabs are in the layout
    layout_str = str(layout)
    if '"executions"' in layout_str and 'id="tabs"' in layout_str:
        print("✅ Tabs found in dashboard layout")
    else:
        print("❌ Tabs not found in dashboard layout")

    if 'id="tab-content"' in layout_str:
        print("✅ Tab content div found in dashboard layout")
    else:
        print("❌ Tab content div not found in dashboard layout")

    print(f"Dashboard layout structure preview: {layout_str[:200]}...")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
