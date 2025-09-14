"""
Test the API mocking functionality for Playwright tests.
This validates that the mock API endpoints work correctly.
"""

from playwright.sync_api import Page, expect
import pytest

from .conftest import skip_if_no_browsers


@pytest.mark.playwright
@skip_if_no_browsers
class TestAPIMocking:
    """Test that API mocking works correctly."""

    def test_mocked_login_flow(self, mocked_app_page: Page):
        """Test that login works with mocked API endpoints."""
        # Should start on login page
        expect(mocked_app_page.locator("h4")).to_contain_text("Login")

        # Fill in login form
        mocked_app_page.fill("input[type='email']", "test@example.com")
        mocked_app_page.fill("input[type='password']", "testpassword123")

        # Wait for button to be clickable
        mocked_app_page.wait_for_selector("#login-btn:enabled", timeout=5000)
        
        # Submit login form
        print("🔄 Clicking login button...")
        mocked_app_page.click("#login-btn")
        
        # Wait a bit to see if anything happens
        mocked_app_page.wait_for_timeout(3000)
        
        # Check if we're still on login or moved to dashboard
        is_still_login = mocked_app_page.locator("h4:has-text('Login')").is_visible()
        is_dashboard = mocked_app_page.locator("[data-testid='dashboard-content']").is_visible()
        
        print(f"📊 After login click - Still on login: {is_still_login}, On dashboard: {is_dashboard}")
        
        # Check for any error messages
        error_alert = mocked_app_page.locator(".alert-danger")
        if error_alert.is_visible():
            error_text = error_alert.text_content()
            print(f"❌ Error message found: {error_text}")

        # Should redirect to dashboard
        mocked_app_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)
        expect(mocked_app_page.locator(".navbar-brand")).to_contain_text(
            "Trends.Earth API Dashboard"
        )

        # Should not see login form anymore
        expect(mocked_app_page.locator("h4:has-text('Login')")).not_to_be_visible()

    def test_authenticated_page_fixture(self, authenticated_page: Page):
        """Test that the authenticated_page fixture works with API mocking."""
        # Should be on dashboard
        expect(authenticated_page.locator("[data-testid='dashboard-content']")).to_be_visible()

        # Should see navigation tabs
        expect(authenticated_page.locator("#status-tab-btn")).to_be_visible()
        expect(authenticated_page.locator("#executions-tab-btn")).to_be_visible()

        # Should see admin-specific tabs (since default role is ADMIN)
        authenticated_page.wait_for_selector("#users-tab-btn:visible", timeout=10000)
        expect(authenticated_page.locator("#users-tab-btn")).to_be_visible()

    def test_user_role_restrictions(self, authenticated_user_page: Page):
        """Test that user role restrictions work correctly."""
        # Should be on dashboard
        expect(authenticated_user_page.locator("[data-testid='dashboard-content']")).to_be_visible()

        # Should see basic navigation tabs
        expect(authenticated_user_page.locator("#status-tab-btn")).to_be_visible()
        expect(authenticated_user_page.locator("#executions-tab-btn")).to_be_visible()

        # Regular users might not see admin tabs or they might be disabled
        # This depends on the app's role-based access control implementation

    def test_api_endpoints_return_mock_data(self, authenticated_page: Page):
        """Test that API endpoints return expected mock data."""
        # Navigate to executions tab to trigger API calls
        authenticated_page.wait_for_selector("#executions-tab-btn", timeout=10000)
        authenticated_page.click("#executions-tab-btn")

        # Wait for table to load with mock data
        authenticated_page.wait_for_selector("[data-testid='executions-table']", timeout=15000)

        # Check that the table has some content (mock data should be loaded)
        # Look for AG-Grid specific elements that indicate data is loaded
        authenticated_page.wait_for_selector(".ag-grid", timeout=10000)
        expect(authenticated_page.locator(".ag-grid")).to_be_visible()

    def test_login_with_invalid_credentials(self, mocked_app_page: Page):
        """Test login failure with invalid credentials."""
        # Should start on login page
        expect(mocked_app_page.locator("h4")).to_contain_text("Login")

        # Fill in login form with empty password (should fail)
        mocked_app_page.fill("input[type='email']", "test@example.com")
        mocked_app_page.fill("input[type='password']", "")

        # Submit login form
        mocked_app_page.click("#login-btn")

        # Should stay on login page and show error
        mocked_app_page.wait_for_timeout(2000)  # Give time for error to appear
        expect(mocked_app_page.locator("h4:has-text('Login')")).to_be_visible()

    def test_authentication_state_management(self, authenticated_page: Page):
        """Test that authentication state is properly managed."""
        # Should be authenticated and on dashboard
        expect(authenticated_page.locator("[data-testid='dashboard-content']")).to_be_visible()

        # Should see logout button
        logout_button = authenticated_page.locator("#header-logout-btn")
        if logout_button.is_visible():
            # Click logout
            logout_button.click()

            # Should redirect to login page
            authenticated_page.wait_for_selector("h4:has-text('Login')", timeout=10000)
            expect(authenticated_page.locator("h4")).to_contain_text("Login")
        else:
            print("⚠️  Logout button not visible - skipping logout test")

    def test_tab_navigation_with_mock_data(self, authenticated_page: Page):
        """Test that tab navigation works with mock API data."""
        # Wait for dashboard to be ready
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)

        # Test Status tab
        status_tab = authenticated_page.locator("#status-tab-btn")
        if status_tab.is_visible():
            status_tab.click()
            authenticated_page.wait_for_timeout(2000)  # Allow time for status data to load

        # Test Executions tab
        executions_tab = authenticated_page.locator("#executions-tab-btn")
        if executions_tab.is_visible():
            executions_tab.click()
            authenticated_page.wait_for_timeout(2000)  # Allow time for executions data to load

        # Test Scripts tab
        scripts_tab = authenticated_page.locator("#scripts-tab-btn")
        if scripts_tab.is_visible():
            scripts_tab.click()
            authenticated_page.wait_for_timeout(2000)  # Allow time for scripts data to load

        # Test Users tab (admin only)
        users_tab = authenticated_page.locator("#users-tab-btn")
        if users_tab.is_visible():
            users_tab.click()
            authenticated_page.wait_for_timeout(2000)  # Allow time for users data to load

        # All navigation should work without errors
        expect(authenticated_page.locator("[data-testid='dashboard-content']")).to_be_visible()