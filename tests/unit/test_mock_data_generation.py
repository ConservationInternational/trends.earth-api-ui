"""Tests for mock data generation functions used in Playwright tests."""

import pytest

from tests.playwright.conftest import (
    generate_mock_executions_data,
    generate_mock_scripts_data,
    generate_mock_status_data,
    generate_mock_users_data,
)


class TestMockDataGeneration:
    """Test mock data generation functions."""

    def test_generate_mock_executions_data_structure(self):
        """Test that mock executions data has correct structure."""
        data = generate_mock_executions_data(count=5)

        # Check response structure
        assert "data" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data

        # Check pagination values
        assert data["page"] == 1
        assert data["per_page"] == 50
        assert data["total"] == 15  # count * 3
        assert len(data["data"]) == 5

        # Check execution item structure
        execution = data["data"][0]
        required_fields = ["id", "script_name", "user_name", "status", "start_date", "progress"]
        for field in required_fields:
            assert field in execution, f"Missing required field: {field}"

        # Check data types
        assert isinstance(execution["progress"], int)
        assert execution["status"] in ["FINISHED", "RUNNING", "FAILED", "QUEUED", "CANCELLED"]

    def test_generate_mock_scripts_data_structure(self):
        """Test that mock scripts data has correct structure."""
        data = generate_mock_scripts_data(count=3)

        # Check response structure
        assert "data" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data

        # Check pagination values
        assert len(data["data"]) == 3
        assert data["total"] == 6  # count * 2

        # Check script item structure
        script = data["data"][0]
        required_fields = [
            "id",
            "name",
            "user_name",
            "description",
            "status",
            "created_at",
            "updated_at",
        ]
        for field in required_fields:
            assert field in script, f"Missing required field: {field}"

        # Check data types and values
        assert script["status"] in ["PUBLISHED", "DRAFT", "ARCHIVED", "UNDER_REVIEW"]
        assert script["created_at"].endswith("Z")
        assert script["updated_at"].endswith("Z")

    def test_generate_mock_users_data_structure(self):
        """Test that mock users data has correct structure."""
        data = generate_mock_users_data(count=4)

        # Check response structure
        assert "data" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data

        # Check pagination values
        assert len(data["data"]) == 4
        assert data["total"] == 16  # count * 4

        # Check user item structure
        user = data["data"][0]
        required_fields = [
            "id",
            "email",
            "name",
            "institution",
            "country",
            "role",
            "created_at",
            "updated_at",
        ]
        for field in required_fields:
            assert field in user, f"Missing required field: {field}"

        # Check data types and values
        assert user["role"] in ["USER", "ADMIN", "MODERATOR", "VIEWER"]
        assert "@example.com" in user["email"]
        assert user["created_at"].endswith("Z")
        assert user["updated_at"].endswith("Z")

    def test_generate_mock_status_data_structure(self):
        """Test that mock status data has correct structure."""
        data = generate_mock_status_data()

        # Check response structure
        assert "data" in data
        status_info = data["data"]

        # Check main sections
        assert "executions" in status_info
        assert "users" in status_info
        assert "system" in status_info
        assert "last_updated" in status_info
        assert "timestamp" in status_info

        # Check executions section
        executions = status_info["executions"]
        exec_fields = ["total", "running", "finished", "failed"]
        for field in exec_fields:
            assert field in executions, f"Missing executions field: {field}"
            assert isinstance(executions[field], int)

        # Check users section
        users = status_info["users"]
        user_fields = ["total", "active_24h"]
        for field in user_fields:
            assert field in users, f"Missing users field: {field}"
            assert isinstance(users[field], int)

        # Check system section
        system = status_info["system"]
        system_fields = ["cpu_usage", "memory_usage", "uptime", "version"]
        for field in system_fields:
            assert field in system, f"Missing system field: {field}"

        # Check timestamp format
        assert status_info["last_updated"].endswith("Z")
        assert status_info["timestamp"].endswith("Z")

    def test_custom_pagination_parameters(self):
        """Test that custom pagination parameters work correctly."""
        data = generate_mock_executions_data(count=8, page=2, per_page=25)

        assert data["page"] == 2
        assert data["per_page"] == 25
        assert len(data["data"]) == 8
        assert data["total"] == 24  # count * 3

    def test_mock_data_variability(self):
        """Test that generated data has reasonable variability."""
        # Generate multiple datasets and check for variability
        data1 = generate_mock_executions_data(count=10)
        data2 = generate_mock_executions_data(count=10)

        # Should have different values (at least some variance)
        statuses1 = [item["status"] for item in data1["data"]]
        statuses2 = [item["status"] for item in data2["data"]]

        # Not all statuses should be identical (very low probability)
        assert statuses1 != statuses2 or len(set(statuses1)) > 1

    def test_data_consistency_within_items(self):
        """Test that data within items is logically consistent."""
        data = generate_mock_executions_data(count=20)

        for execution in data["data"]:
            # If status is FINISHED, should have end_date and 100% progress
            if execution["status"] == "FINISHED":
                assert execution["end_date"] is not None
                assert execution["progress"] == 100

            # If status is RUNNING, should not have end_date
            if execution["status"] == "RUNNING":
                assert execution["end_date"] is None
                assert 0 < execution["progress"] < 100

            # Progress should be within valid range
            assert 0 <= execution["progress"] <= 100
