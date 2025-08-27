"""
Integration tests for table column filter functionality.
These tests verify that the column filter configuration is properly implemented.
"""

import pytest

from trendsearth_ui.components.tabs import create_responsive_table
from trendsearth_ui.utils.mobile_utils import get_mobile_column_config


class TestTableColumnFilterIntegration:
    """Integration tests for table column filters."""

    def test_executions_table_has_filter_config(self):
        """Test that executions table has proper filter configuration."""
        # Create the executions table
        table_div = create_responsive_table("executions-table", "executions")

        # Verify the table has data-testid attribute
        assert getattr(table_div, "data-testid", None) == "executions-table"

        # Get the AG-Grid component (first child)
        ag_grid = table_div.children[0]

        # Verify column definitions include filters
        column_defs = ag_grid.columnDefs

        # Find status column and verify it has set filter
        status_col = next((col for col in column_defs if col["field"] == "status"), None)
        assert status_col is not None
        assert status_col["filter"] == "agSetColumnFilter"
        assert "filterParams" in status_col
        assert status_col["filterParams"]["values"] == [
            "PENDING",
            "RUNNING",
            "SUCCESS",
            "FAILED",
            "CANCELLED",
        ]

        # Find duration column and verify it has number filter
        duration_col = next((col for col in column_defs if col["field"] == "duration"), None)
        assert duration_col is not None
        assert duration_col["filter"] == "agNumberColumnFilter"
        assert "filterParams" in duration_col

        # Find date columns and verify they have date filters
        start_date_col = next((col for col in column_defs if col["field"] == "start_date"), None)
        assert start_date_col is not None
        assert start_date_col["filter"] == "agDateColumnFilter"

    def test_scripts_table_has_filter_config(self):
        """Test that scripts table has proper filter configuration."""
        # Create the scripts table
        table_div = create_responsive_table("scripts-table", "scripts")

        # Verify the table has data-testid attribute
        assert getattr(table_div, "data-testid", None) == "scripts-table"

        # Get the AG-Grid component (first child)
        ag_grid = table_div.children[0]

        # Verify column definitions include filters
        column_defs = ag_grid.columnDefs

        # Find status column and verify it has set filter
        status_col = next((col for col in column_defs if col["field"] == "status"), None)
        assert status_col is not None
        assert status_col["filter"] == "agSetColumnFilter"
        assert "filterParams" in status_col
        assert status_col["filterParams"]["values"] == [
            "UPLOADED",
            "PUBLISHED",
            "UNPUBLISHED",
            "FAILED",
        ]

        # Find access control column and verify it has set filter
        access_col = next((col for col in column_defs if col["field"] == "access_control"), None)
        assert access_col is not None
        assert access_col["filter"] == "agSetColumnFilter"
        assert "filterParams" in access_col
        assert access_col["filterParams"]["values"] == [
            "unrestricted",
            "role_restricted",
            "user_restricted",
        ]

    def test_users_table_has_filter_config(self):
        """Test that users table has proper filter configuration."""
        # Create the users table
        table_div = create_responsive_table("users-table", "users")

        # Verify the table has data-testid attribute
        assert getattr(table_div, "data-testid", None) == "users-table"

        # Get the AG-Grid component (first child)
        ag_grid = table_div.children[0]

        # Verify column definitions include filters
        column_defs = ag_grid.columnDefs

        # Find role column and verify it has set filter
        role_col = next((col for col in column_defs if col["field"] == "role"), None)
        assert role_col is not None
        assert role_col["filter"] == "agSetColumnFilter"
        assert "filterParams" in role_col
        assert role_col["filterParams"]["values"] == ["USER", "ADMIN", "SUPERADMIN"]

        # Find date columns and verify they have date filters
        created_col = next((col for col in column_defs if col["field"] == "created_at"), None)
        assert created_col is not None
        assert created_col["filter"] == "agDateColumnFilter"

    def test_all_tables_have_data_testid(self):
        """Test that all tables have proper data-testid attributes for testing."""
        table_types = ["executions", "scripts", "users"]

        for table_type in table_types:
            table_id = f"{table_type}-table"
            table_div = create_responsive_table(table_id, table_type)

            # Verify data-testid is set correctly
            assert getattr(table_div, "data-testid", None) == table_id

            # Verify the table container has the right class
            assert "table-container" in table_div.className

    def test_filter_configuration_consistency(self):
        """Test that filter configurations are consistent with column config."""
        config = get_mobile_column_config()

        for table_type in ["executions", "scripts", "users"]:
            table_div = create_responsive_table(f"{table_type}-table", table_type)
            ag_grid = table_div.children[0]

            # Get expected columns from config
            expected_columns = (
                config[table_type]["primary_columns"] + config[table_type]["secondary_columns"]
            )

            # Verify all expected columns are in the table
            actual_fields = {col["field"] for col in ag_grid.columnDefs}
            expected_fields = {col["field"] for col in expected_columns}

            assert actual_fields == expected_fields, f"Column mismatch in {table_type} table"

            # Verify filter configurations match
            for expected_col in expected_columns:
                actual_col = next(
                    (col for col in ag_grid.columnDefs if col["field"] == expected_col["field"]),
                    None,
                )
                assert actual_col is not None

                # If expected column has filter, verify it's set correctly
                if "filter" in expected_col:
                    assert actual_col["filter"] == expected_col["filter"]

                    if "filterParams" in expected_col:
                        assert actual_col["filterParams"] == expected_col["filterParams"]

    def test_set_filter_buttons_configuration(self):
        """Test that set filters have proper button configuration."""
        config = get_mobile_column_config()

        for table_type in ["executions", "scripts", "users"]:
            columns = config[table_type]["primary_columns"]

            for col in columns:
                if col.get("filter") == "agSetColumnFilter":
                    filter_params = col.get("filterParams", {})

                    # Verify set filters have proper button configuration
                    assert "buttons" in filter_params
                    assert "clear" in filter_params["buttons"]
                    assert "apply" in filter_params["buttons"]

                    # Verify other useful set filter options
                    assert filter_params.get("selectAllOnMiniFilter") is True
                    assert filter_params.get("closeOnApply") is True

    def test_number_filter_configuration(self):
        """Test that number filters have proper configuration."""
        config = get_mobile_column_config()

        # Check duration column in executions table
        exec_columns = config["executions"]["primary_columns"]
        duration_col = next((col for col in exec_columns if col["field"] == "duration"), None)

        assert duration_col is not None
        assert duration_col["filter"] == "agNumberColumnFilter"

        filter_params = duration_col.get("filterParams", {})
        assert "allowedCharPattern" in filter_params
        assert filter_params["suppressAndOrCondition"] is True

        # Verify valueGetter is configured for proper filtering
        assert "valueGetter" in duration_col

    def test_filter_testability_attributes(self):
        """Test that tables have attributes needed for reliable testing."""
        table_types = ["executions", "scripts", "users"]

        for table_type in table_types:
            table_id = f"{table_type}-table"
            table_div = create_responsive_table(table_id, table_type)

            # Verify data-testid is present for playwright testing
            assert hasattr(table_div, "data-testid")
            assert getattr(table_div, "data-testid") == table_id

            # Verify scroll hint has proper ID for testing
            scroll_hint = table_div.children[1]
            assert scroll_hint.id == f"{table_id}-scroll-hint"
            assert "table-scroll-hint" in scroll_hint.className
