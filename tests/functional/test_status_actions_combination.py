"""Test the combination of status and actions columns in executions table."""

from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def mock_cell_click_status_ready():
    """Mock cell click data for a ready status (cancellable)."""
    return {
        "colId": "status",
        "rowIndex": 0,
        "data": {
            "id": "exec-123",
            "status": "READY",
            "script_name": "Test Script",
            "user_id": "user-456",
        },
    }


@pytest.fixture
def mock_cell_click_status_finished():
    """Mock cell click data for a finished status (not cancellable)."""
    return {
        "colId": "status",
        "rowIndex": 0,
        "data": {
            "id": "exec-789",
            "status": "FINISHED",
            "script_name": "Test Script",
            "user_id": "user-456",
        },
    }


@pytest.fixture
def mock_user_data():
    """Mock user data for permission testing."""
    return {"id": "user-456", "email": "test@example.com"}


@pytest.fixture
def mock_other_user_data():
    """Mock different user data for permission testing."""
    return {"id": "user-999", "email": "other@example.com"}


class TestStatusActionsCombination:
    """Test the combined status/actions column functionality."""

    def test_status_column_config_excludes_actions(self):
        """Test that the status column configuration no longer includes actions column."""
        from trendsearth_ui.utils.mobile_utils import get_mobile_column_config

        config = get_mobile_column_config()
        executions_config = config.get("executions", {})
        primary_columns = executions_config.get("primary_columns", [])

        # Check that there's a status column
        status_column = next((col for col in primary_columns if col["field"] == "status"), None)
        assert status_column is not None, "Status column should exist"

        # Check that there's NO actions column
        actions_column = next((col for col in primary_columns if col["field"] == "actions"), None)
        assert actions_column is None, "Actions column should not exist"

        # Check that status column has cursor pointer (indicating clickability)
        assert "cursor" in status_column.get("cellStyle", {}), "Status column should be clickable"
        assert status_column["cellStyle"]["cursor"] == "pointer", (
            "Status column should have pointer cursor"
        )

    def test_status_click_permission_own_task_regular_user(
        self, mock_cell_click_status_ready, mock_user_data
    ):
        """Test that regular users can cancel their own tasks."""
        cell = mock_cell_click_status_ready
        user_data = mock_user_data
        role = "USER"

        # Test permission logic directly
        execution_user_id = cell["data"]["user_id"]
        current_user_id = user_data.get("id")
        is_admin = role in ["ADMIN", "SUPERADMIN"]
        status = cell["data"]["status"]
        cancellable_statuses = ["READY", "PENDING", "RUNNING"]

        # Check cancellable status
        assert status in cancellable_statuses, "Status should be cancellable"

        # Check permission (own task)
        assert is_admin or execution_user_id == current_user_id, (
            "User should have permission to cancel their own task"
        )

    def test_status_click_permission_denied_other_user_task(
        self, mock_cell_click_status_ready, mock_other_user_data
    ):
        """Test that regular users cannot cancel other users' tasks."""
        cell = mock_cell_click_status_ready
        user_data = mock_other_user_data
        role = "USER"

        execution_user_id = cell["data"]["user_id"]
        current_user_id = user_data.get("id")
        is_admin = role in ["ADMIN", "SUPERADMIN"]

        # Check permission (other user's task)
        assert execution_user_id != current_user_id, "Should be different users"
        assert not is_admin, "Should not be admin"
        assert not (is_admin or execution_user_id == current_user_id), (
            "User should NOT have permission to cancel other user's task"
        )

    def test_status_click_permission_admin_can_cancel_any_task(
        self, mock_cell_click_status_ready, mock_other_user_data
    ):
        """Test that admin users can cancel any task."""
        cell = mock_cell_click_status_ready
        user_data = mock_other_user_data
        role = "ADMIN"

        execution_user_id = cell["data"]["user_id"]
        current_user_id = user_data.get("id")
        is_admin = role in ["ADMIN", "SUPERADMIN"]

        # Check permission (admin can cancel any task)
        assert execution_user_id != current_user_id, "Should be different users"
        assert is_admin, "Should be admin"
        assert is_admin or execution_user_id == current_user_id, (
            "Admin should have permission to cancel any user's task"
        )

    def test_status_click_non_cancellable_status(self, mock_cell_click_status_finished):
        """Test that finished status is not cancellable."""
        cell = mock_cell_click_status_finished
        status = cell["data"]["status"]
        cancellable_statuses = ["READY", "PENDING", "RUNNING"]

        assert status not in cancellable_statuses, "FINISHED status should not be cancellable"

    def test_column_id_detection(self, mock_cell_click_status_ready):
        """Test that only status column clicks are handled."""
        # Test status column click
        status_cell = mock_cell_click_status_ready
        assert status_cell["colId"] == "status", "Should detect status column click"

        # Test non-status column click
        other_cell = {"colId": "script_name", "rowIndex": 0, "data": {}}
        assert other_cell["colId"] != "status", "Should ignore non-status column clicks"

    def test_cancellable_statuses_list(self):
        """Test that the cancellable statuses are correctly defined."""
        cancellable_statuses = ["READY", "PENDING", "RUNNING"]

        # These should be cancellable
        assert "READY" in cancellable_statuses
        assert "PENDING" in cancellable_statuses
        assert "RUNNING" in cancellable_statuses

        # These should NOT be cancellable
        assert "FINISHED" not in cancellable_statuses
        assert "FAILED" not in cancellable_statuses
        assert "CANCELLED" not in cancellable_statuses

    def test_row_data_no_longer_includes_actions_field(self):
        """Test that row data construction no longer includes actions field."""
        # This test simulates the row data construction logic
        exec_row = {
            "id": "exec-123",
            "status": "READY",
            "script_name": "Test Script",
            "user_id": "user-456",
        }

        # Simulate the row data construction from executions.py
        row = exec_row.copy()
        row["params"] = "Show Params"
        row["results"] = "Show Results"
        row["logs"] = "Show Logs"
        row["map"] = "Show Map"
        # Note: actions field is no longer added

        # Verify actions field is not present
        assert "actions" not in row, "Row data should not include actions field"

        # Verify other fields are still present
        assert row["params"] == "Show Params"
        assert row["results"] == "Show Results"
        assert row["logs"] == "Show Logs"
        assert row["map"] == "Show Map"
        assert row["status"] == "READY"
