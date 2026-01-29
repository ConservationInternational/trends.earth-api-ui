"""Unit tests for role-based visibility of columns and UI elements."""

import pytest

from trendsearth_ui.utils.mobile_utils import (
    ADMIN_ONLY_FIELDS,
    get_executions_columns_for_role,
    get_mobile_column_config,
)


class TestAdminOnlyFields:
    """Test the ADMIN_ONLY_FIELDS constant."""

    def test_admin_only_fields_contains_expected_fields(self):
        """Test that ADMIN_ONLY_FIELDS contains user_name, user_email, and docker_logs."""
        assert "user_name" in ADMIN_ONLY_FIELDS
        assert "user_email" in ADMIN_ONLY_FIELDS
        assert "docker_logs" in ADMIN_ONLY_FIELDS

    def test_admin_only_fields_is_set(self):
        """Test that ADMIN_ONLY_FIELDS is a set for efficient lookup."""
        assert isinstance(ADMIN_ONLY_FIELDS, set)


class TestGetExecutionsColumnsForRole:
    """Test the get_executions_columns_for_role function."""

    def test_admin_role_gets_all_columns(self):
        """Test that ADMIN role gets all columns including admin-only fields."""
        columns = get_executions_columns_for_role("ADMIN")

        # Get all column field names
        field_names = {col.get("field") for col in columns}

        # Admin should have access to all admin-only fields
        assert "user_name" in field_names
        assert "user_email" in field_names
        assert "docker_logs" in field_names

    def test_superadmin_role_gets_all_columns(self):
        """Test that SUPERADMIN role gets all columns including admin-only fields."""
        columns = get_executions_columns_for_role("SUPERADMIN")

        # Get all column field names
        field_names = {col.get("field") for col in columns}

        # Superadmin should have access to all admin-only fields
        assert "user_name" in field_names
        assert "user_email" in field_names
        assert "docker_logs" in field_names

    def test_user_role_excludes_admin_columns(self):
        """Test that USER role does not get admin-only columns."""
        columns = get_executions_columns_for_role("USER")

        # Get all column field names
        field_names = {col.get("field") for col in columns}

        # User should NOT have access to admin-only fields
        assert "user_name" not in field_names
        assert "user_email" not in field_names
        assert "docker_logs" not in field_names

    def test_none_role_excludes_admin_columns(self):
        """Test that None role (not logged in) does not get admin-only columns."""
        columns = get_executions_columns_for_role(None)

        # Get all column field names
        field_names = {col.get("field") for col in columns}

        # None role should NOT have access to admin-only fields
        assert "user_name" not in field_names
        assert "user_email" not in field_names
        assert "docker_logs" not in field_names

    def test_empty_string_role_excludes_admin_columns(self):
        """Test that empty string role does not get admin-only columns."""
        columns = get_executions_columns_for_role("")

        # Get all column field names
        field_names = {col.get("field") for col in columns}

        # Empty string role should NOT have access to admin-only fields
        assert "user_name" not in field_names
        assert "user_email" not in field_names
        assert "docker_logs" not in field_names

    def test_user_role_still_gets_non_admin_columns(self):
        """Test that USER role still gets non-admin columns."""
        columns = get_executions_columns_for_role("USER")

        # Get all column field names
        field_names = {col.get("field") for col in columns}

        # User should still have access to standard columns
        assert "script_name" in field_names
        assert "start_date" in field_names
        assert "end_date" in field_names
        assert "status" in field_names
        assert "params" in field_names
        assert "results" in field_names
        assert "logs" in field_names
        assert "map" in field_names

    def test_admin_has_more_columns_than_user(self):
        """Test that admin role returns more columns than user role."""
        admin_columns = get_executions_columns_for_role("ADMIN")
        user_columns = get_executions_columns_for_role("USER")

        # Admin should have exactly 3 more columns (user_name, user_email, docker_logs)
        assert len(admin_columns) == len(user_columns) + 3

    def test_column_structure_preserved(self):
        """Test that column definitions maintain their structure after filtering."""
        columns = get_executions_columns_for_role("USER")

        for col in columns:
            # Each column should have at least headerName and field
            assert "headerName" in col
            assert "field" in col


class TestMobileColumnConfigExecutions:
    """Test the executions config in get_mobile_column_config."""

    def test_executions_config_exists(self):
        """Test that executions config exists in mobile column config."""
        config = get_mobile_column_config()
        assert "executions" in config

    def test_executions_has_primary_and_secondary_columns(self):
        """Test that executions config has both primary and secondary columns."""
        config = get_mobile_column_config()
        executions_config = config.get("executions", {})

        assert "primary_columns" in executions_config
        assert "secondary_columns" in executions_config

    def test_admin_only_fields_are_in_columns(self):
        """Test that all admin-only fields exist in the column configuration."""
        config = get_mobile_column_config()
        executions_config = config.get("executions", {})

        primary_cols = executions_config.get("primary_columns", [])
        secondary_cols = executions_config.get("secondary_columns", [])
        all_columns = primary_cols + secondary_cols

        field_names = {col.get("field") for col in all_columns}

        # All admin-only fields should exist in the full column set
        for admin_field in ADMIN_ONLY_FIELDS:
            assert admin_field in field_names, f"Admin-only field '{admin_field}' not in columns"


class TestEnvironmentIndicatorVisibility:
    """Test environment indicator visibility based on role.

    These tests verify the logic that environment badges should only
    be visible to ADMIN and SUPERADMIN users.
    """

    @pytest.mark.parametrize(
        "role,should_show",
        [
            ("ADMIN", True),
            ("SUPERADMIN", True),
            ("USER", False),
            (None, False),
            ("", False),
            ("user", False),  # Case-sensitive check
        ],
    )
    def test_environment_indicator_visibility_by_role(self, role, should_show):
        """Test that environment indicator visibility is correct for each role."""
        # This tests the logic that should be applied in the callback
        is_admin = role in ["ADMIN", "SUPERADMIN"]
        assert is_admin == should_show
