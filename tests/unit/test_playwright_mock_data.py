"""Tests for Playwright mock data functions without requiring Playwright browsers."""

import os

# Import the functions directly to test them without Playwright setup
import sys

import pytest

# Add the tests directory to the path so we can import from playwright conftest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "playwright"))

# Mock the playwright.sync_api import to avoid browser setup
import unittest.mock

with unittest.mock.patch.dict("sys.modules", {"playwright.sync_api": unittest.mock.MagicMock()}):
    from conftest import (
        generate_mock_executions_data,
        generate_mock_scripts_data,
        generate_mock_status_data,
        generate_mock_users_data,
    )


class TestPlaywrightMockDataFunctions:
    """Test mock data functions for Playwright without browser setup."""

    def test_generate_mock_executions_data_returns_valid_api_response(self):
        """Test that executions mock data matches API response format."""
        data = generate_mock_executions_data(count=5)

        # Check API response structure
        assert isinstance(data, dict)
        assert "data" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data

        # Check data content
        assert isinstance(data["data"], list)
        assert len(data["data"]) == 5
        assert data["page"] == 1
        assert data["per_page"] == 50
        assert data["total"] == 15  # count * 3

        # Check execution item structure
        for execution in data["data"]:
            assert "id" in execution
            assert "script_name" in execution
            assert "user_name" in execution
            assert "status" in execution
            assert "start_date" in execution
            assert "progress" in execution
            assert execution["start_date"].endswith("Z")
            assert isinstance(execution["progress"], int)
            assert 0 <= execution["progress"] <= 100

    def test_generate_mock_scripts_data_returns_valid_api_response(self):
        """Test that scripts mock data matches API response format."""
        data = generate_mock_scripts_data(count=8)

        # Check API response structure
        assert isinstance(data, dict)
        assert "data" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data

        # Check data content
        assert len(data["data"]) == 8
        assert data["total"] == 16  # count * 2

        # Check script item structure
        for script in data["data"]:
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
                assert field in script
            assert script["created_at"].endswith("Z")
            assert script["updated_at"].endswith("Z")

    def test_generate_mock_users_data_returns_valid_api_response(self):
        """Test that users mock data matches API response format."""
        data = generate_mock_users_data(count=6)

        # Check API response structure
        assert isinstance(data, dict)
        assert "data" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data

        # Check data content
        assert len(data["data"]) == 6
        assert data["total"] == 24  # count * 4

        # Check user item structure
        for user in data["data"]:
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
                assert field in user
            assert "@example.com" in user["email"]
            assert user["created_at"].endswith("Z")
            assert user["updated_at"].endswith("Z")

    def test_generate_mock_status_data_returns_valid_api_response(self):
        """Test that status mock data matches API response format."""
        data = generate_mock_status_data()

        # Check API response structure
        assert isinstance(data, dict)
        assert "data" in data

        status_data = data["data"]
        assert "executions" in status_data
        assert "users" in status_data
        assert "system" in status_data
        assert "last_updated" in status_data
        assert "timestamp" in status_data

        # Check executions stats
        executions = status_data["executions"]
        assert all(field in executions for field in ["total", "running", "finished", "failed"])
        assert all(isinstance(executions[field], int) for field in executions)

        # Check users stats
        users = status_data["users"]
        assert all(field in users for field in ["total", "active_24h"])
        assert all(isinstance(users[field], int) for field in users)

        # Check system stats
        system = status_data["system"]
        assert all(field in system for field in ["cpu_usage", "memory_usage", "uptime", "version"])

    def test_mock_data_pagination_customization(self):
        """Test that pagination parameters can be customized."""
        data = generate_mock_executions_data(count=12, page=3, per_page=20)

        assert data["page"] == 3
        assert data["per_page"] == 20
        assert len(data["data"]) == 12
        assert data["total"] == 36  # count * 3

    def test_mock_data_provides_variety_for_testing(self):
        """Test that mock data provides sufficient variety for UI testing."""
        # Test with larger dataset to ensure variety
        executions = generate_mock_executions_data(count=30)

        # Collect unique values
        statuses = {exec["status"] for exec in executions["data"]}
        script_names = {exec["script_name"] for exec in executions["data"]}
        user_names = {exec["user_name"] for exec in executions["data"]}

        # Should have multiple different values for variety in UI
        assert len(statuses) > 1, "Should have multiple execution statuses"
        assert len(script_names) > 1, "Should have multiple script names"
        assert len(user_names) > 1, "Should have multiple user names"

        # Check scripts variety
        scripts = generate_mock_scripts_data(count=20)
        script_statuses = {script["status"] for script in scripts["data"]}
        assert len(script_statuses) > 1, "Should have multiple script statuses"

        # Check users variety
        users = generate_mock_users_data(count=20)
        user_roles = {user["role"] for user in users["data"]}
        user_institutions = {user["institution"] for user in users["data"]}
        assert len(user_roles) > 1, "Should have multiple user roles"
        assert len(user_institutions) > 1, "Should have multiple institutions"

    def test_mock_data_logical_consistency(self):
        """Test that generated data maintains logical consistency."""
        executions = generate_mock_executions_data(count=50)

        for execution in executions["data"]:
            status = execution["status"]
            progress = execution["progress"]
            end_date = execution["end_date"]

            # Finished executions should have 100% progress and end date
            if status == "FINISHED":
                assert progress == 100, "Finished executions should have 100% progress"
                assert end_date is not None, "Finished executions should have end date"

            # Running executions should not have end date and partial progress
            elif status == "RUNNING":
                assert end_date is None, "Running executions should not have end date"
                assert 0 < progress < 100, "Running executions should have partial progress"

            # All executions should have valid progress range
            assert 0 <= progress <= 100, "Progress should be 0-100"
