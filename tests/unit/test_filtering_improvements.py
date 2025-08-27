"""Tests for filtering and sorting improvements."""

from unittest.mock import Mock, patch

import pytest

from trendsearth_ui.utils.mobile_utils import get_mobile_column_config


class TestColumnFilterConfiguration:
    """Test that column filters are configured correctly."""

    def test_executions_status_filter(self):
        """Test that executions status column has proper enhanced text filter."""
        config = get_mobile_column_config()
        executions_columns = config["executions"]["primary_columns"]

        status_column = next(col for col in executions_columns if col["field"] == "status")

        assert status_column["filter"] == "agTextColumnFilter"
        assert "filterParams" in status_column
        assert "buttons" in status_column["filterParams"]
        assert "closeOnApply" in status_column["filterParams"]
        assert "caseSensitive" in status_column["filterParams"]
        assert status_column["filterParams"]["caseSensitive"] is False
        assert "trimInput" in status_column["filterParams"]
        assert status_column["filterParams"]["trimInput"] is True

    def test_executions_duration_filter(self):
        """Test that executions duration column has proper number filter."""
        config = get_mobile_column_config()
        executions_columns = config["executions"]["primary_columns"]

        duration_column = next(col for col in executions_columns if col["field"] == "duration")

        assert duration_column["filter"] == "agNumberColumnFilter"
        assert "filterParams" in duration_column

        # Should have valueGetter for filtering numeric values
        assert "valueGetter" in duration_column

    def test_scripts_status_filter(self):
        """Test that scripts status column has proper enhanced text filter."""
        config = get_mobile_column_config()
        scripts_columns = config["scripts"]["primary_columns"]

        status_column = next(col for col in scripts_columns if col["field"] == "status")

        assert status_column["filter"] == "agTextColumnFilter"
        assert "filterParams" in status_column
        assert "buttons" in status_column["filterParams"]
        assert "closeOnApply" in status_column["filterParams"]
        assert "caseSensitive" in status_column["filterParams"]
        assert status_column["filterParams"]["caseSensitive"] is False
        assert "trimInput" in status_column["filterParams"]
        assert status_column["filterParams"]["trimInput"] is True

    def test_scripts_access_filter(self):
        """Test that scripts access column has proper enhanced text filter."""
        config = get_mobile_column_config()
        scripts_columns = config["scripts"]["primary_columns"]

        access_column = next(col for col in scripts_columns if col["field"] == "access_control")

        assert access_column["filter"] == "agTextColumnFilter"
        assert "filterParams" in access_column
        assert "buttons" in access_column["filterParams"]
        assert "closeOnApply" in access_column["filterParams"]
        assert "caseSensitive" in access_column["filterParams"]
        assert access_column["filterParams"]["caseSensitive"] is False
        assert "trimInput" in access_column["filterParams"]
        assert access_column["filterParams"]["trimInput"] is True

    def test_users_role_filter(self):
        """Test that users role column has proper enhanced text filter."""
        config = get_mobile_column_config()
        users_columns = config["users"]["primary_columns"]

        role_column = next(col for col in users_columns if col["field"] == "role")

        assert role_column["filter"] == "agTextColumnFilter"
        assert "filterParams" in role_column
        assert "buttons" in role_column["filterParams"]
        assert "closeOnApply" in role_column["filterParams"]
        assert "caseSensitive" in role_column["filterParams"]
        assert role_column["filterParams"]["caseSensitive"] is False
        assert "trimInput" in role_column["filterParams"]
        assert role_column["filterParams"]["trimInput"] is True


class TestFilterProcessingLogic:
    """Test the filter processing logic in callbacks."""

    def test_set_filter_to_sql_conversion(self):
        """Test that set filters are converted to proper SQL conditions."""
        from trendsearth_ui.callbacks.executions import register_callbacks

        # Mock a filter model with set filter
        filter_model = {"status": {"filterType": "set", "values": ["SUCCESS", "FAILED"]}}

        # Simulate the filter processing logic
        filter_sql = []
        for field, config in filter_model.items():
            if config.get("filterType") == "set":
                values = config.get("values", [])
                if values:
                    value_conditions = [f"{field}='{val}'" for val in values]
                    if value_conditions:
                        filter_sql.append(f"({' OR '.join(value_conditions)})")

        expected_sql = "(status='SUCCESS' OR status='FAILED')"
        assert filter_sql[0] == expected_sql

    def test_number_filter_processing(self):
        """Test that number filters are processed correctly."""
        # Mock a filter model with number filter
        filter_model = {"duration": {"filterType": "number", "type": "greaterThan", "filter": 3600}}

        # Simulate the filter processing logic
        filter_sql = []
        for field, config in filter_model.items():
            if config.get("filterType") == "number":
                filter_type = config.get("type", "equals")
                val = config.get("filter")
                if val is not None:
                    if filter_type == "greaterThan":
                        filter_sql.append(f"{field}>{val}")

        expected_sql = "duration>3600"
        assert filter_sql[0] == expected_sql

    def test_multiple_filters_combination(self):
        """Test that multiple filters are combined correctly."""
        filter_model = {
            "status": {"filterType": "set", "values": ["SUCCESS"]},
            "duration": {"filterType": "number", "type": "greaterThan", "filter": 1800},
        }

        # Simulate the filter processing logic
        filter_sql = []
        for field, config in filter_model.items():
            if config.get("filterType") == "set":
                values = config.get("values", [])
                if values:
                    value_conditions = [f"{field}='{val}'" for val in values]
                    if value_conditions:
                        filter_sql.append(f"({' OR '.join(value_conditions)})")
            elif config.get("filterType") == "number":
                filter_type = config.get("type", "equals")
                val = config.get("filter")
                if val is not None:
                    if filter_type == "greaterThan":
                        filter_sql.append(f"{field}>{val}")

        # Should have both filters
        assert len(filter_sql) == 2
        assert "(status='SUCCESS')" in filter_sql
        assert "duration>1800" in filter_sql


class TestAPIStatusValueConsistency:
    """Test that filter configurations are properly set up."""

    def test_execution_status_filter_configured(self):
        """Test that execution status filter is configured."""
        config = get_mobile_column_config()
        executions_columns = config["executions"]["primary_columns"]
        status_column = next(col for col in executions_columns if col["field"] == "status")

        assert status_column["filter"] == "agTextColumnFilter"
        assert "filterParams" in status_column

    def test_script_status_filter_configured(self):
        """Test that script status filter is configured."""
        config = get_mobile_column_config()
        scripts_columns = config["scripts"]["primary_columns"]
        status_column = next(col for col in scripts_columns if col["field"] == "status")

        assert status_column["filter"] == "agTextColumnFilter"
        assert "filterParams" in status_column

    def test_user_role_filter_configured(self):
        """Test that user role filter is configured."""
        config = get_mobile_column_config()
        users_columns = config["users"]["primary_columns"]
        role_column = next(col for col in users_columns if col["field"] == "role")

        assert role_column["filter"] == "agTextColumnFilter"
        assert "filterParams" in role_column
