"""
Example of how to use mock data generation functions in Playwright tests.
This demonstrates the usage of the mock data functions for API mocking.
"""

from playwright.sync_api import Page, Route
import pytest

from tests.playwright.conftest import (
    generate_mock_executions_data,
    generate_mock_scripts_data,
    generate_mock_status_data,
    generate_mock_users_data,
    skip_if_no_browsers,
)


@pytest.mark.playwright
@skip_if_no_browsers
class TestMockDataUsageExamples:
    """Examples of how to use mock data functions in Playwright tests."""

    def test_mock_data_fixtures_usage(
        self, mock_executions_data, mock_scripts_data, mock_users_data, mock_status_data
    ):
        """Test that mock data fixtures work correctly."""
        # Test executions data fixture
        assert "data" in mock_executions_data
        assert len(mock_executions_data["data"]) == 10  # default count
        assert mock_executions_data["total"] == 30  # count * 3

        # Test scripts data fixture
        assert "data" in mock_scripts_data
        assert len(mock_scripts_data["data"]) == 10  # default count

        # Test users data fixture
        assert "data" in mock_users_data
        assert len(mock_users_data["data"]) == 10  # default count

        # Test status data fixture
        assert "data" in mock_status_data
        assert "executions" in mock_status_data["data"]

    def test_direct_function_usage(self):
        """Test using the functions directly with custom parameters."""
        # Generate custom amount of data
        executions = generate_mock_executions_data(count=5, page=2, per_page=25)
        assert len(executions["data"]) == 5
        assert executions["page"] == 2
        assert executions["per_page"] == 25

        # Generate different amounts for different entities
        scripts = generate_mock_scripts_data(count=15)
        assert len(scripts["data"]) == 15

        users = generate_mock_users_data(count=8)
        assert len(users["data"]) == 8

    def test_api_route_mocking_example(self, page: Page, live_server):
        """Example of how to use mock data for API route interception."""

        def handle_executions_route(route: Route):
            """Mock the executions API endpoint."""
            mock_data = generate_mock_executions_data(count=20)
            route.fulfill(json=mock_data)

        def handle_scripts_route(route: Route):
            """Mock the scripts API endpoint."""
            mock_data = generate_mock_scripts_data(count=15)
            route.fulfill(json=mock_data)

        def handle_users_route(route: Route):
            """Mock the users API endpoint."""
            mock_data = generate_mock_users_data(count=25)
            route.fulfill(json=mock_data)

        def handle_status_route(route: Route):
            """Mock the status API endpoint."""
            mock_data = generate_mock_status_data()
            route.fulfill(json=mock_data)

        # Set up route handlers for API endpoints
        page.route("**/api/v1/executions**", handle_executions_route)
        page.route("**/api/v1/scripts**", handle_scripts_route)
        page.route("**/api/v1/users**", handle_users_route)
        page.route("**/api/v1/status**", handle_status_route)

        # Navigate to page - API calls will be intercepted and return mock data
        page.goto(live_server)

        # The page should now load with mock data
        # This is just an example - actual test would verify specific UI elements
        assert page.locator("body").is_visible()

    def test_mock_data_content_variety(self):
        """Test that mock data provides good variety for UI testing."""
        executions = generate_mock_executions_data(count=50)

        # Should have various statuses for testing different UI states
        statuses = [exec["status"] for exec in executions["data"]]
        unique_statuses = set(statuses)
        assert len(unique_statuses) > 1, "Should have multiple execution statuses"

        # Should have various script names
        script_names = [exec["script_name"] for exec in executions["data"]]
        unique_script_names = set(script_names)
        assert len(unique_script_names) > 1, "Should have multiple script names"

        # Progress values should vary
        progress_values = [exec["progress"] for exec in executions["data"]]
        unique_progress = set(progress_values)
        assert len(unique_progress) > 1, "Should have varied progress values"
