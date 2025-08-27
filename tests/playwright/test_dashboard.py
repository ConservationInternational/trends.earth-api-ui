"""
Dashboard functionality tests using Playwright.
Tests dashboard tabs, navigation, and core dashboard features.
"""

from playwright.sync_api import Page, expect
import pytest


@pytest.mark.playwright
class TestDashboardNavigation:
    """Test dashboard navigation and tab functionality."""

    def test_dashboard_tabs_visible(self, authenticated_page: Page):
        """Test that all main dashboard tabs are visible."""
        # Wait for dashboard to load
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)

        # Check main tabs
        expect(authenticated_page.locator("text=Status")).to_be_visible()
        expect(authenticated_page.locator("text=Executions")).to_be_visible()
        expect(authenticated_page.locator("text=Scripts")).to_be_visible()
        expect(authenticated_page.locator("text=Users")).to_be_visible()
        expect(authenticated_page.locator("text=Profile")).to_be_visible()

    def test_tab_navigation(self, authenticated_page: Page):
        """Test navigation between dashboard tabs."""
        # Wait for dashboard to load
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)

        # Test clicking on different tabs
        tabs_to_test = ["Status", "Executions", "Scripts", "Users", "Profile"]

        for tab_name in tabs_to_test:
            tab = authenticated_page.locator(f"text={tab_name}").first
            if tab.is_visible():
                tab.click()

                # Wait for tab content to load
                authenticated_page.wait_for_timeout(1000)

                # Verify tab is active/selected (checking for common active indicators)
                # The exact selector depends on the UI framework being used
                # Just verify that content area is visible after click
                content_area = authenticated_page.locator(
                    "[data-testid='tab-content'], .tab-content, [role='tabpanel']"
                )
                expect(content_area).to_be_visible()

    def test_default_tab_active(self, authenticated_page: Page):
        """Test that a default tab is active on dashboard load."""
        # Wait for dashboard to load
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)

        # Should have some tab content visible by default
        content_area = authenticated_page.locator(
            "[data-testid='tab-content'], .tab-content, [role='tabpanel']"
        )
        expect(content_area).to_be_visible()


@pytest.mark.playwright
class TestStatusTab:
    """Test Status tab functionality."""

    def test_status_tab_loads(self, authenticated_page: Page):
        """Test that Status tab loads and shows expected content."""
        # Wait for dashboard and navigate to Status tab
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)

        status_tab = authenticated_page.locator("text=Status").first
        if status_tab.is_visible():
            status_tab.click()
            authenticated_page.wait_for_timeout(2000)

            # Should show status-related content
            # Look for common status indicators
            status_indicators = [
                "text=API Status",
                "text=System Status",
                "text=Health",
                ".status-card",
                ".status-indicator",
                "[data-testid='status-content']",
            ]

            # At least one status indicator should be visible
            found_indicator = False
            for indicator in status_indicators:
                if authenticated_page.locator(indicator).first.is_visible():
                    found_indicator = True
                    break

            # If no specific indicators, just check that content loaded
            if not found_indicator:
                expect(
                    authenticated_page.locator("[role='tabpanel'], .tab-content")
                ).to_be_visible()

    def test_status_refresh_functionality(self, authenticated_page: Page):
        """Test status refresh functionality if available."""
        # Wait for dashboard and navigate to Status tab
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)

        status_tab = authenticated_page.locator("text=Status").first
        if status_tab.is_visible():
            status_tab.click()
            authenticated_page.wait_for_timeout(2000)

            # Look for refresh button
            refresh_selectors = [
                "button:has-text('Refresh')",
                "[data-testid='refresh-button']",
                ".refresh-btn",
                "button[title*='refresh' i]",
            ]

            for selector in refresh_selectors:
                refresh_button = authenticated_page.locator(selector).first
                if refresh_button.is_visible():
                    refresh_button.click()
                    authenticated_page.wait_for_timeout(1000)
                    break


@pytest.mark.playwright
class TestExecutionsTab:
    """Test Executions tab functionality."""

    def test_executions_tab_loads(self, authenticated_page: Page):
        """Test that Executions tab loads and shows expected content."""
        # Wait for dashboard and navigate to Executions tab
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)

        executions_tab = authenticated_page.locator("text=Executions").first
        if executions_tab.is_visible():
            executions_tab.click()
            authenticated_page.wait_for_timeout(2000)

            # Should show executions-related content
            execution_indicators = [
                "table",
                ".ag-grid",
                ".data-table",
                "text=No executions",
                "[data-testid='executions-table']",
                "text=Loading",
            ]

            # At least one indicator should be visible
            found_indicator = False
            for indicator in execution_indicators:
                if authenticated_page.locator(indicator).first.is_visible():
                    found_indicator = True
                    break

            assert found_indicator, "Expected executions content not found"

    def test_executions_table_interaction(self, authenticated_page: Page):
        """Test executions table interactions if data is present."""
        # Wait for dashboard and navigate to Executions tab
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)

        executions_tab = authenticated_page.locator("text=Executions").first
        if executions_tab.is_visible():
            executions_tab.click()
            authenticated_page.wait_for_timeout(3000)

            # If table is present, test basic interactions
            table = authenticated_page.locator("table, .ag-grid").first
            if table.is_visible():
                # Test that table has some structure
                expect(table).to_be_visible()

                # Look for common table elements
                headers = authenticated_page.locator("th, .ag-header-cell")
                if headers.count() > 0:
                    expect(headers.first).to_be_visible()


@pytest.mark.playwright
class TestScriptsTab:
    """Test Scripts tab functionality."""

    def test_scripts_tab_loads(self, authenticated_page: Page):
        """Test that Scripts tab loads and shows expected content."""
        # Wait for dashboard and navigate to Scripts tab
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)

        scripts_tab = authenticated_page.locator("text=Scripts").first
        if scripts_tab.is_visible():
            scripts_tab.click()
            authenticated_page.wait_for_timeout(2000)

            # Should show scripts-related content
            script_indicators = [
                "table",
                ".ag-grid",
                ".data-table",
                "text=No scripts",
                "[data-testid='scripts-table']",
                "text=Loading",
            ]

            # At least one indicator should be visible
            found_indicator = False
            for indicator in script_indicators:
                if authenticated_page.locator(indicator).first.is_visible():
                    found_indicator = True
                    break

            assert found_indicator, "Expected scripts content not found"


@pytest.mark.playwright
class TestUsersTab:
    """Test Users tab functionality."""

    def test_users_tab_loads(self, authenticated_page: Page):
        """Test that Users tab loads and shows expected content."""
        # Wait for dashboard and navigate to Users tab
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)

        users_tab = authenticated_page.locator("text=Users").first
        if users_tab.is_visible():
            users_tab.click()
            authenticated_page.wait_for_timeout(2000)

            # Should show users-related content
            user_indicators = [
                "table",
                ".ag-grid",
                ".data-table",
                "text=No users",
                "[data-testid='users-table']",
                "text=Loading",
            ]

            # At least one indicator should be visible
            found_indicator = False
            for indicator in user_indicators:
                if authenticated_page.locator(indicator).first.is_visible():
                    found_indicator = True
                    break

            assert found_indicator, "Expected users content not found"


@pytest.mark.playwright
class TestProfileTab:
    """Test Profile tab functionality."""

    def test_profile_tab_loads(self, authenticated_page: Page):
        """Test that Profile tab loads and shows expected content."""
        # Wait for dashboard and navigate to Profile tab
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)

        profile_tab = authenticated_page.locator("text=Profile").first
        if profile_tab.is_visible():
            profile_tab.click()
            authenticated_page.wait_for_timeout(2000)

            # Should show profile-related content
            profile_indicators = [
                "form",
                "input[type='text']",
                "input[type='email']",
                "text=Profile",
                "text=User Information",
                "[data-testid='profile-form']",
                "text=Loading",
            ]

            # At least one indicator should be visible
            found_indicator = False
            for indicator in profile_indicators:
                if authenticated_page.locator(indicator).first.is_visible():
                    found_indicator = True
                    break

            assert found_indicator, "Expected profile content not found"

    def test_profile_form_interaction(self, authenticated_page: Page):
        """Test profile form interactions if available."""
        # Wait for dashboard and navigate to Profile tab
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)

        profile_tab = authenticated_page.locator("text=Profile").first
        if profile_tab.is_visible():
            profile_tab.click()
            authenticated_page.wait_for_timeout(2000)

            # Look for editable form fields
            text_inputs = authenticated_page.locator("input[type='text']")
            if text_inputs.count() > 0:
                first_input = text_inputs.first
                if first_input.is_enabled():
                    # Test interaction
                    original_value = first_input.input_value()
                    first_input.fill("Test Value")
                    expect(first_input).to_have_value("Test Value")

                    # Restore original value
                    if original_value:
                        first_input.fill(original_value)
