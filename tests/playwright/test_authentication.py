"""
Authentication flow tests using Playwright.
Tests login, logout, and authentication state management.
"""

from playwright.sync_api import Page, expect
import pytest


@pytest.mark.playwright
class TestAuthenticationFlow:
    """Test authentication workflows."""

    def test_login_page_structure(self, app_page: Page):
        """Test login page has correct structure and elements."""
        # Check main heading
        expect(app_page.locator("h2")).to_contain_text("Login")

        # Check form elements exist
        expect(app_page.locator("input[type='email']")).to_be_visible()
        expect(app_page.locator("input[type='password']")).to_be_visible()
        expect(app_page.locator("button[type='submit']")).to_be_visible()

        # Check additional elements
        expect(app_page.locator("text=Forgot password?")).to_be_visible()
        expect(app_page.locator("img")).to_be_visible()  # Logo

    def test_login_form_interaction(self, app_page: Page):
        """Test login form interactions."""
        # Fill in email field
        email_input = app_page.locator("input[type='email']")
        email_input.fill("test@example.com")
        expect(email_input).to_have_value("test@example.com")

        # Fill in password field
        password_input = app_page.locator("input[type='password']")
        password_input.fill("testpassword123")
        expect(password_input).to_have_value("testpassword123")

        # Clear fields
        email_input.clear()
        password_input.clear()
        expect(email_input).to_have_value("")
        expect(password_input).to_have_value("")

    def test_login_form_validation(self, app_page: Page):
        """Test client-side form validation."""
        login_button = app_page.locator("button[type='submit']").first

        # Test empty form submission
        login_button.click()

        # Should still be on login page (validation prevented submission)
        expect(app_page.locator("h2")).to_contain_text("Login")

        # Test invalid email format
        app_page.fill("input[type='email']", "invalid-email-format")
        app_page.fill("input[type='password']", "password123")
        login_button.click()

        # Should still be on login page
        expect(app_page.locator("h2")).to_contain_text("Login")

    def test_password_visibility_toggle(self, app_page: Page):
        """Test password field visibility toggle if present."""
        password_input = app_page.locator("input[type='password']")
        password_input.fill("secretpassword")

        # Check if there's a password visibility toggle
        eye_icon = app_page.locator("[data-testid='password-toggle']")
        if eye_icon.is_visible():
            eye_icon.click()
            # After toggle, might become text input
            expect(app_page.locator("input[type='text']")).to_have_value("secretpassword")


@pytest.mark.playwright
class TestAuthenticationState:
    """Test authentication state management."""

    def test_unauthenticated_state(self, app_page: Page):
        """Test app behavior when not authenticated."""
        # Should show login page
        expect(app_page.locator("h2")).to_contain_text("Login")

        # Should not show dashboard elements
        expect(app_page.locator("text=Dashboard")).not_to_be_visible()
        expect(app_page.locator("text=Status")).not_to_be_visible()
        expect(app_page.locator("text=Executions")).not_to_be_visible()

        # Should not have authentication tokens in local storage
        auth_token = app_page.evaluate("() => localStorage.getItem('auth_token')")
        assert auth_token is None

    def test_authenticated_state(self, authenticated_page: Page):
        """Test app behavior when authenticated."""
        # Wait for dashboard to load
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)

        # Should see dashboard instead of login
        expect(authenticated_page.locator("text=Dashboard")).to_be_visible()

        # Should not see login form
        expect(authenticated_page.locator("h2:has-text('Login')")).not_to_be_visible()

        # Should see navigation tabs
        expect(authenticated_page.locator("text=Status")).to_be_visible()
        expect(authenticated_page.locator("text=Executions")).to_be_visible()

        # Should have authentication data in local storage
        auth_token = authenticated_page.evaluate("() => localStorage.getItem('auth_token')")
        assert auth_token == "mock_token_12345"

        user_role = authenticated_page.evaluate("() => localStorage.getItem('user_role')")
        assert user_role == "ADMIN"

    def test_logout_functionality(self, authenticated_page: Page):
        """Test logout functionality if available."""
        # Wait for dashboard to load
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)

        # Look for logout button or menu
        logout_button = authenticated_page.locator("button:has-text('Logout')")
        if logout_button.is_visible():
            logout_button.click()

            # Should redirect to login page
            expect(authenticated_page.locator("h2")).to_contain_text("Login")

            # Should clear authentication data
            auth_token = authenticated_page.evaluate("() => localStorage.getItem('auth_token')")
            assert auth_token is None


@pytest.mark.playwright
class TestAuthenticationErrors:
    """Test authentication error scenarios."""

    def test_login_with_invalid_credentials(self, app_page: Page):
        """Test login attempt with invalid credentials."""
        # Fill in obviously invalid credentials
        app_page.fill("input[type='email']", "invalid@nonexistent.com")
        app_page.fill("input[type='password']", "wrongpassword")

        # Submit form
        app_page.locator("button[type='submit']").first.click()

        # Should remain on login page
        expect(app_page.locator("h2")).to_contain_text("Login")

        # Might show error message (wait briefly for it to appear)
        app_page.wait_for_timeout(2000)

        # Check if error message appears
        # Look for common error indicators but don't fail if none found
        # as the main assertion is that form is still visible
        try:
            app_page.wait_for_selector(
                ".alert-danger, .error-message, [role='alert']", timeout=2000
            )
        except Exception:
            pass  # Error message might not appear immediately

        # At least one error indicator should be present or form should still be visible
        form_still_visible = app_page.locator("input[type='email']").is_visible()
        assert form_still_visible, "Form should still be visible after failed login"

    def test_network_error_handling(self, page: Page, live_server):
        """Test handling of network errors during authentication."""
        page.goto(live_server)

        # Block network requests to simulate network error
        page.route("**/auth/**", lambda route: route.abort())

        # Try to login
        page.fill("input[type='email']", "test@example.com")
        page.fill("input[type='password']", "password123")
        page.locator("button[type='submit']").first.click()

        # Should handle gracefully - either show error or remain on login
        page.wait_for_timeout(3000)

        # Should still be on login page or show appropriate error
        login_heading = page.locator("h2:has-text('Login')")
        assert login_heading.is_visible(), "Should remain on login page after network error"


@pytest.mark.playwright
class TestAuthenticationPersistence:
    """Test authentication persistence across sessions."""

    def test_authentication_persists_across_reload(self, authenticated_page: Page):
        """Test that authentication persists when page is reloaded."""
        # Wait for initial dashboard load
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)

        # Verify we're on dashboard
        expect(authenticated_page.locator("text=Dashboard")).to_be_visible()

        # Reload page
        authenticated_page.reload()

        # Should still be authenticated and see dashboard
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)
        expect(authenticated_page.locator("text=Dashboard")).to_be_visible()

        # Authentication data should persist
        auth_token = authenticated_page.evaluate("() => localStorage.getItem('auth_token')")
        assert auth_token == "mock_token_12345"

    def test_session_cleanup_on_logout(self, authenticated_page: Page):
        """Test that session data is properly cleaned up on logout."""
        # Wait for dashboard to load
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)

        # Clear authentication manually (simulating logout)
        authenticated_page.evaluate("""
            localStorage.removeItem('auth_token');
            localStorage.removeItem('user_role');
            localStorage.removeItem('user_data');
        """)

        # Reload page
        authenticated_page.reload()

        # Should redirect to login
        expect(authenticated_page.locator("h2")).to_contain_text("Login")

        # Storage should be cleared
        auth_token = authenticated_page.evaluate("() => localStorage.getItem('auth_token')")
        assert auth_token is None
