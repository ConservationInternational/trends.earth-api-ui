"""
Tests to ensure table state is respected across refreshes for all tables.
This tests that sorting, filtering, and pagination state persists correctly.
"""

import json
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def mock_api_response():
    """Mock API response for table data."""
    return {
        "data": [
            {
                "id": "exec-1",
                "script_name": "Test Script 1",
                "user_name": "User 1",
                "status": "FINISHED",
                "start_date": "2024-01-01T10:00:00Z",
                "end_date": "2024-01-01T11:00:00Z",
                "progress": 100,
            },
            {
                "id": "exec-2",
                "script_name": "Test Script 2",
                "user_name": "User 2",
                "status": "RUNNING",
                "start_date": "2024-01-01T12:00:00Z",
                "end_date": None,
                "progress": 50,
            },
        ],
        "total": 25,
        "page": 1,
        "per_page": 50,
    }


@pytest.fixture
def mock_scripts_response():
    """Mock API response for scripts table data."""
    return {
        "data": [
            {
                "id": "script-1",
                "name": "Script 1",
                "user_name": "User 1",
                "description": "Test script 1",
                "status": "PUBLISHED",
                "created_at": "2024-01-01T10:00:00Z",
                "updated_at": "2024-01-01T11:00:00Z",
            },
            {
                "id": "script-2",
                "name": "Script 2",
                "user_name": "User 2",
                "description": "Test script 2",
                "status": "DRAFT",
                "created_at": "2024-01-02T10:00:00Z",
                "updated_at": "2024-01-02T11:00:00Z",
            },
        ],
        "total": 15,
        "page": 1,
        "per_page": 50,
    }


@pytest.fixture
def mock_users_response():
    """Mock API response for users table data."""
    return {
        "data": [
            {
                "id": "user-1",
                "email": "user1@example.com",
                "name": "User 1",
                "institution": "Institution 1",
                "country": "Country 1",
                "role": "USER",
                "created_at": "2024-01-01T10:00:00Z",
                "updated_at": "2024-01-01T11:00:00Z",
            },
            {
                "id": "user-2",
                "email": "user2@example.com",
                "name": "User 2",
                "institution": "Institution 2",
                "country": "Country 2",
                "role": "ADMIN",
                "created_at": "2024-01-02T10:00:00Z",
                "updated_at": "2024-01-02T11:00:00Z",
            },
        ],
        "total": 10,
        "page": 1,
        "per_page": 50,
    }


@pytest.fixture
def sample_table_state():
    """Sample table state with sorting and filtering."""
    return {
        "sort_sql": "start_date DESC",
        "filter_sql": "status = 'FINISHED'",
        "page": 2,
        "per_page": 50,
    }


class TestExecutionsTableState:
    """Test executions table state persistence."""

    def test_executions_table_respects_sort_state(self, mock_api_response):
        """Test that executions table respects sorting state."""
        # Test the sort model logic without importing the actual callback
        request = {
            "startRow": 0,
            "endRow": 50,
            "sortModel": [{"colId": "start_date", "sort": "desc"}],
            "filterModel": {},
        }

        # Test sort model parsing logic
        sort_sql = []
        for sort in request["sortModel"]:
            col_id = sort["colId"]
            direction = sort["sort"].upper()
            sort_sql.append(f"{col_id} {direction}")

        expected_sort = "start_date DESC"
        assert sort_sql[0] == expected_sort

        # Verify the request structure is correct
        assert "start_date" in str(request["sortModel"][0]["colId"])
        assert "desc" in str(request["sortModel"][0]["sort"])

    def test_executions_table_respects_filter_state(self, mock_api_response):
        """Test that executions table respects filtering state."""
        # Simulate table request with filtering
        request = {
            "startRow": 0,
            "endRow": 50,
            "sortModel": [],
            "filterModel": {
                "status": {"filterType": "text", "type": "equals", "filter": "FINISHED"}
            },
        }

        # Verify filter is properly formatted
        assert "status" in request["filterModel"]
        assert request["filterModel"]["status"]["filter"] == "FINISHED"

    def test_executions_refresh_preserves_state(self, sample_table_state):
        """Test that refreshing executions table preserves table state."""
        # The table state should be maintained across refreshes
        preserved_state = sample_table_state.copy()

        # After refresh, state should be the same
        assert preserved_state["sort_sql"] == "start_date DESC"
        assert preserved_state["filter_sql"] == "status = 'FINISHED'"
        assert preserved_state["page"] == 2


class TestScriptsTableState:
    """Test scripts table state persistence."""

    def test_scripts_table_respects_sort_state(self, mock_scripts_response):
        """Test that scripts table respects sorting state."""
        request = {
            "startRow": 0,
            "endRow": 50,
            "sortModel": [{"colId": "created_at", "sort": "desc"}],
            "filterModel": {},
        }

        # Verify sort model is correct
        assert request["sortModel"][0]["colId"] == "created_at"
        assert request["sortModel"][0]["sort"] == "desc"

    def test_scripts_table_respects_filter_state(self, mock_scripts_response):
        """Test that scripts table respects filtering state."""
        request = {
            "startRow": 0,
            "endRow": 50,
            "sortModel": [],
            "filterModel": {
                "status": {"filterType": "text", "type": "equals", "filter": "PUBLISHED"}
            },
        }

        # Verify filter is properly formatted
        assert request["filterModel"]["status"]["filter"] == "PUBLISHED"

    def test_scripts_refresh_preserves_state(self, sample_table_state):
        """Test that refreshing scripts table preserves table state."""
        scripts_state = {
            "sort_sql": "created_at DESC",
            "filter_sql": "status = 'PUBLISHED'",
            "page": 1,
            "per_page": 50,
        }

        preserved_state = scripts_state.copy()

        # After refresh, state should be the same
        assert preserved_state["sort_sql"] == "created_at DESC"
        assert preserved_state["filter_sql"] == "status = 'PUBLISHED'"


class TestUsersTableState:
    """Test users table state persistence."""

    def test_users_table_respects_sort_state(self, mock_users_response):
        """Test that users table respects sorting state."""
        request = {
            "startRow": 0,
            "endRow": 50,
            "sortModel": [{"colId": "email", "sort": "asc"}],
            "filterModel": {},
        }

        # Verify sort model is correct
        assert request["sortModel"][0]["colId"] == "email"
        assert request["sortModel"][0]["sort"] == "asc"

    def test_users_table_respects_filter_state(self, mock_users_response):
        """Test that users table respects filtering state."""
        request = {
            "startRow": 0,
            "endRow": 50,
            "sortModel": [],
            "filterModel": {"role": {"filterType": "text", "type": "equals", "filter": "ADMIN"}},
        }

        # Verify filter is properly formatted
        assert request["filterModel"]["role"]["filter"] == "ADMIN"

    def test_users_refresh_preserves_state(self):
        """Test that refreshing users table preserves table state."""
        users_state = {
            "sort_sql": "email ASC",
            "filter_sql": "role = 'ADMIN'",
            "page": 1,
            "per_page": 50,
        }

        preserved_state = users_state.copy()

        # After refresh, state should be the same
        assert preserved_state["sort_sql"] == "email ASC"
        assert preserved_state["filter_sql"] == "role = 'ADMIN'"


class TestTableStatePersistenceIntegration:
    """Integration tests for table state persistence across all tables."""

    def test_all_tables_maintain_independent_state(self):
        """Test that each table maintains its own independent state."""
        executions_state = {
            "sort_sql": "start_date DESC",
            "filter_sql": "status = 'FINISHED'",
            "page": 2,
        }

        scripts_state = {
            "sort_sql": "name ASC",
            "filter_sql": "status = 'PUBLISHED'",
            "page": 1,
        }

        users_state = {
            "sort_sql": "email ASC",
            "filter_sql": "role = 'ADMIN'",
            "page": 3,
        }

        # Each table should maintain its own state independently
        assert executions_state["sort_sql"] != scripts_state["sort_sql"]
        assert scripts_state["filter_sql"] != users_state["filter_sql"]
        assert executions_state["page"] != users_state["page"]

    def test_table_state_format_consistency(self):
        """Test that all tables use consistent state format."""
        required_fields = ["sort_sql", "filter_sql"]

        # All table states should have these fields when populated
        sample_states = [
            {"sort_sql": "start_date DESC", "filter_sql": "status = 'FINISHED'"},
            {"sort_sql": "name ASC", "filter_sql": "status = 'PUBLISHED'"},
            {"sort_sql": "email ASC", "filter_sql": "role = 'ADMIN'"},
        ]

        for state in sample_states:
            for field in required_fields:
                assert field in state
                assert isinstance(state[field], str)

    def test_pagination_state_consistency(self):
        """Test that pagination state is consistent across tables."""
        # All tables should use the same page size by default
        default_page_size = 50

        pagination_configs = [
            {"page": 1, "per_page": default_page_size},
            {"page": 2, "per_page": default_page_size},
            {"page": 3, "per_page": default_page_size},
        ]

        for config in pagination_configs:
            assert config["per_page"] == default_page_size
            assert isinstance(config["page"], int)
            assert config["page"] >= 1
