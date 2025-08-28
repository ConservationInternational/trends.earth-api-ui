"""
Core application functionality tests using Playwright.
Tests basic app loading, navigation, and core features.
"""

from playwright.sync_api import Page, expect
import pytest

from .conftest import skip_if_no_browsers


@pytest.mark.playwright
@skip_if_no_browsers
class TestAppBasics:
    """Test basic application functionality."""

    def test_app_loads_successfully(self, app_page: Page):
        """Test that the application loads successfully."""
        # Should show login page initially
        expect(app_page.locator("h4:has-text('Login')")).to_be_visible()

        # Should have email and password fields (target specific inputs)
        expect(app_page.locator("#login-email")).to_be_visible()
        expect(app_page.locator("#login-password")).to_be_visible()

        # Should have login button
        expect(app_page.locator("#login-btn")).to_contain_text("Login")

    def test_app_title_and_meta(self, app_page: Page):
        """Test that app has correct title and meta tags."""
        expect(app_page).to_have_title("Trends.Earth API Dashboard")

        # Check meta description
        meta_description = app_page.locator("meta[name='description']")
        expect(meta_description).to_have_attribute(
            "content", "Trends.Earth API Dashboard - Manage scripts, users, and executions"
        )

    def test_health_endpoint_accessible(self, live_server):
        """Test that health endpoint is accessible."""
        import requests

        response = requests.get(f"{live_server}/api-ui-health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_favicon_loads(self, app_page: Page, live_server):
        """Test that favicon loads successfully."""
        # Navigate to favicon directly
        response = app_page.request.get(f"{live_server}/favicon.ico")
        assert response.status == 200

    def test_responsive_design(self, page: Page, live_server):
        """Test that app works on different screen sizes."""
        # Test mobile viewport
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(live_server)

        # Should still show login elements
        expect(page.locator("h4:has-text('Login')")).to_be_visible()
        expect(page.locator("#login-email")).to_be_visible()

        # Test tablet viewport
        page.set_viewport_size({"width": 768, "height": 1024})
        page.reload()

        # Should still work
        expect(page.locator("h4:has-text('Login')")).to_be_visible()

        # Test desktop viewport
        page.set_viewport_size({"width": 1920, "height": 1080})
        page.reload()

        # Should still work
        expect(page.locator("h4:has-text('Login')")).to_be_visible()


@pytest.mark.playwright
@skip_if_no_browsers
class TestNavigation:
    """Test application navigation."""

    def test_login_form_validation(self, app_page: Page):
        """Test login form validation."""
        # Try to submit empty form
        app_page.locator("#login-btn").click()

        # Should still be on login page (no navigation due to validation)
        expect(app_page.locator("h4")).to_contain_text("Login")

        # Fill in invalid email
        app_page.fill("input[type='email']", "invalid-email")
        app_page.fill("input[type='password']", "password123")
        app_page.locator("#login-btn").click()

        # Should still be on login page
        expect(app_page.locator("h4")).to_contain_text("Login")

    def test_login_form_elements(self, app_page: Page):
        """Test login form has all necessary elements."""
        # Check email field properties
        email_input = app_page.locator("input[type='email']")
        expect(email_input).to_have_attribute("placeholder", "Enter email")

        # Check password field properties
        password_input = app_page.locator("input[type='password']")
        expect(password_input).to_have_attribute("placeholder", "Enter password")

        # Check forgot password link
        expect(app_page.locator("text=Forgot your password?")).to_be_visible()

        # Check logo is present
        expect(app_page.locator("img")).to_be_visible()

    def test_dashboard_loads_with_auth(self, authenticated_page: Page):
        """Test that dashboard loads when authenticated."""
        # With mocked authentication, should see dashboard
        # Wait for dashboard to load
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)

        # Should see main dashboard elements
        expect(authenticated_page.locator("text=Dashboard")).to_be_visible()

        # Should see navigation tabs
        expect(authenticated_page.locator("#status-tab-btn")).to_be_visible()
        expect(authenticated_page.locator("#executions-tab-btn")).to_be_visible()
        expect(authenticated_page.locator("#scripts-tab-btn")).to_be_visible()
        expect(authenticated_page.locator("#users-tab-btn")).to_be_visible()
        expect(authenticated_page.locator("#profile-tab-btn")).to_be_visible()


@pytest.mark.playwright
@skip_if_no_browsers
class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_routes(self, page: Page, live_server):
        """Test that invalid routes are handled gracefully by showing the login page."""
        # Navigate to a non-existent route
        response = page.goto(f"{live_server}/this-route-does-not-exist")

        # For a SPA, the server should return 200 and the app shell
        assert response.status == 200, "Expected server to return 200 for an unknown route in a SPA"

        # The client-side router should handle the invalid route.
        # In our case, it should display the login page as a fallback.
        expect(page.locator("h4:has-text('Login')")).to_be_visible(
            timeout=5000
        )
        expect(page).to_have_url(f"{live_server}/this-route-does-not-exist")

    def test_javascript_enabled(self, app_page: Page):
        """Test that JavaScript is enabled and working."""
        # Check that page heading and inputs are interactive (requires JS)
        expect(app_page.locator("h4:has-text('Login')")).to_be_visible()
        expect(app_page.locator("#login-email")).to_be_enabled()
        expect(app_page.locator("#login-password")).to_be_enabled()
