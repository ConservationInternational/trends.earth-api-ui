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
        expect(app_page.locator("h4")).to_contain_text("Login")

        # Should have email and password fields
        expect(app_page.locator("input[type='email']")).to_be_visible()
        expect(app_page.locator("input[type='password']")).to_be_visible()

        # Should have login button
        expect(app_page.locator("button")).to_contain_text("Login")

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
        expect(page.locator("h4")).to_contain_text("Login")
        expect(page.locator("input[type='email']")).to_be_visible()

        # Test tablet viewport
        page.set_viewport_size({"width": 768, "height": 1024})
        page.reload()

        # Should still work
        expect(page.locator("h4")).to_contain_text("Login")

        # Test desktop viewport
        page.set_viewport_size({"width": 1920, "height": 1080})
        page.reload()

        # Should still work
        expect(page.locator("h4")).to_contain_text("Login")


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
        expect(authenticated_page.locator("text=Status")).to_be_visible()
        expect(authenticated_page.locator("text=Executions")).to_be_visible()
        expect(authenticated_page.locator("text=Scripts")).to_be_visible()
        expect(authenticated_page.locator("text=Users")).to_be_visible()
        expect(authenticated_page.locator("text=Profile")).to_be_visible()


@pytest.mark.playwright
@skip_if_no_browsers
class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_routes(self, page: Page, live_server):
        """Test that invalid routes are handled gracefully."""
        # Navigate to non-existent route
        page.goto(f"{live_server}/invalid-route")

        # Should not crash - might redirect to login or show 404
        # Just check that page loads without JS errors
        page.wait_for_load_state()

        # Check for no JS errors in console
        messages = []
        page.on("console", lambda msg: messages.append(msg))
        page.reload()

        # Allow some time for any errors to appear
        page.wait_for_timeout(1000)

        # Filter out non-error messages
        errors = [msg for msg in messages if msg.type == "error"]

        # Should have no critical JS errors
        assert len(errors) == 0, f"Found JS errors: {[msg.text for msg in errors]}"

    def test_javascript_enabled(self, app_page: Page):
        """Test that JavaScript is enabled and working."""
        # Check that Dash components are rendered (requires JS)
        expect(app_page.locator("#_dash-app-content")).to_be_visible()

        # Test that page is interactive (not just static HTML)
        expect(app_page.locator("input[type='email']")).to_be_enabled()
        expect(app_page.locator("input[type='password']")).to_be_enabled()
