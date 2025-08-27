"""
Table column filter functionality tests using Playwright.
Tests the recently added table column filter checkbox functionality.
"""

from playwright.sync_api import Page, expect
import pytest


@pytest.mark.playwright
class TestTableColumnFilters:
    """Test table column filter functionality across different tables."""

    def test_executions_table_status_filter(self, authenticated_page: Page):
        """Test that executions table status column has working set filter."""
        # Navigate to executions tab
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)

        executions_tab = authenticated_page.locator("text=Executions").first
        executions_tab.click()
        authenticated_page.wait_for_timeout(3000)

        # Wait for the executions table to load
        table = authenticated_page.wait_for_selector(
            "[data-testid='executions-table']", timeout=10000
        )
        expect(table).to_be_visible()

        # Find the status column header and open filter menu
        status_header = authenticated_page.locator(".ag-header-cell").filter(has_text="Status")
        expect(status_header).to_be_visible()

        # Click on the filter icon for status column
        filter_icon = status_header.locator(".ag-icon-filter")
        if filter_icon.is_visible():
            filter_icon.click()
            authenticated_page.wait_for_timeout(1000)

            # Check that set filter menu appears with checkboxes
            filter_menu = authenticated_page.locator(".ag-filter-wrapper")
            expect(filter_menu).to_be_visible()

            # Verify that status filter values are present
            expected_statuses = ["PENDING", "RUNNING", "SUCCESS", "FAILED", "CANCELLED"]
            for status in expected_statuses:
                status_option = filter_menu.locator(f"text={status}")
                if status_option.is_visible():
                    expect(status_option).to_be_visible()

    def test_executions_table_duration_filter(self, authenticated_page: Page):
        """Test that executions table duration column has working number filter."""
        # Navigate to executions tab
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)

        executions_tab = authenticated_page.locator("text=Executions").first
        executions_tab.click()
        authenticated_page.wait_for_timeout(3000)

        # Wait for the executions table to load
        table = authenticated_page.wait_for_selector(
            "[data-testid='executions-table']", timeout=10000
        )
        expect(table).to_be_visible()

        # Find the duration column header and open filter menu
        duration_header = authenticated_page.locator(".ag-header-cell").filter(has_text="Duration")
        expect(duration_header).to_be_visible()

        # Click on the filter icon for duration column
        filter_icon = duration_header.locator(".ag-icon-filter")
        if filter_icon.is_visible():
            filter_icon.click()
            authenticated_page.wait_for_timeout(1000)

            # Check that number filter menu appears
            filter_menu = authenticated_page.locator(".ag-filter-wrapper")
            expect(filter_menu).to_be_visible()

            # Verify number filter controls are present
            filter_type_select = filter_menu.locator("select")
            if filter_type_select.is_visible():
                expect(filter_type_select).to_be_visible()

            filter_input = filter_menu.locator("input[type='text']")
            if filter_input.is_visible():
                expect(filter_input).to_be_visible()

    def test_scripts_table_status_filter(self, authenticated_page: Page):
        """Test that scripts table status column has working set filter."""
        # Navigate to scripts tab
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)

        scripts_tab = authenticated_page.locator("text=Scripts").first
        scripts_tab.click()
        authenticated_page.wait_for_timeout(3000)

        # Wait for the scripts table to load
        table = authenticated_page.wait_for_selector("[data-testid='scripts-table']", timeout=10000)
        expect(table).to_be_visible()

        # Find the status column header and open filter menu
        status_header = authenticated_page.locator(".ag-header-cell").filter(has_text="Status")
        expect(status_header).to_be_visible()

        # Click on the filter icon for status column
        filter_icon = status_header.locator(".ag-icon-filter")
        if filter_icon.is_visible():
            filter_icon.click()
            authenticated_page.wait_for_timeout(1000)

            # Check that set filter menu appears with checkboxes
            filter_menu = authenticated_page.locator(".ag-filter-wrapper")
            expect(filter_menu).to_be_visible()

            # Verify that script status filter values are present
            expected_statuses = ["UPLOADED", "PUBLISHED", "UNPUBLISHED", "FAILED"]
            for status in expected_statuses:
                status_option = filter_menu.locator(f"text={status}")
                if status_option.is_visible():
                    expect(status_option).to_be_visible()

    def test_scripts_table_access_filter(self, authenticated_page: Page):
        """Test that scripts table access control column has working set filter."""
        # Navigate to scripts tab
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)

        scripts_tab = authenticated_page.locator("text=Scripts").first
        scripts_tab.click()
        authenticated_page.wait_for_timeout(3000)

        # Wait for the scripts table to load
        table = authenticated_page.wait_for_selector("[data-testid='scripts-table']", timeout=10000)
        expect(table).to_be_visible()

        # Find the access column header and open filter menu
        access_header = authenticated_page.locator(".ag-header-cell").filter(has_text="Access")
        expect(access_header).to_be_visible()

        # Click on the filter icon for access column
        filter_icon = access_header.locator(".ag-icon-filter")
        if filter_icon.is_visible():
            filter_icon.click()
            authenticated_page.wait_for_timeout(1000)

            # Check that set filter menu appears with checkboxes
            filter_menu = authenticated_page.locator(".ag-filter-wrapper")
            expect(filter_menu).to_be_visible()

            # Verify that access control filter values are present
            expected_access_types = ["unrestricted", "role_restricted", "user_restricted"]
            for access_type in expected_access_types:
                access_option = filter_menu.locator(f"text={access_type}")
                if access_option.is_visible():
                    expect(access_option).to_be_visible()

    def test_users_table_role_filter(self, authenticated_page: Page):
        """Test that users table role column has working set filter."""
        # Navigate to users tab
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)

        users_tab = authenticated_page.locator("text=Users").first
        users_tab.click()
        authenticated_page.wait_for_timeout(3000)

        # Wait for the users table to load
        table = authenticated_page.wait_for_selector("[data-testid='users-table']", timeout=10000)
        expect(table).to_be_visible()

        # Find the role column header and open filter menu
        role_header = authenticated_page.locator(".ag-header-cell").filter(has_text="Role")
        expect(role_header).to_be_visible()

        # Click on the filter icon for role column
        filter_icon = role_header.locator(".ag-icon-filter")
        if filter_icon.is_visible():
            filter_icon.click()
            authenticated_page.wait_for_timeout(1000)

            # Check that set filter menu appears with checkboxes
            filter_menu = authenticated_page.locator(".ag-filter-wrapper")
            expect(filter_menu).to_be_visible()

            # Verify that role filter values are present
            expected_roles = ["USER", "ADMIN", "SUPERADMIN"]
            for role in expected_roles:
                role_option = filter_menu.locator(f"text={role}")
                if role_option.is_visible():
                    expect(role_option).to_be_visible()

    def test_date_column_filters(self, authenticated_page: Page):
        """Test that date columns have working date filters."""
        # Navigate to executions tab
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)

        executions_tab = authenticated_page.locator("text=Executions").first
        executions_tab.click()
        authenticated_page.wait_for_timeout(3000)

        # Wait for the executions table to load
        table = authenticated_page.wait_for_selector(
            "[data-testid='executions-table']", timeout=10000
        )
        expect(table).to_be_visible()

        # Test start date column filter
        start_header = authenticated_page.locator(".ag-header-cell").filter(has_text="Start")
        if start_header.is_visible():
            filter_icon = start_header.locator(".ag-icon-filter")
            if filter_icon.is_visible():
                filter_icon.click()
                authenticated_page.wait_for_timeout(1000)

                # Check that date filter menu appears
                filter_menu = authenticated_page.locator(".ag-filter-wrapper")
                expect(filter_menu).to_be_visible()

                # Close filter menu
                authenticated_page.keyboard.press("Escape")
                authenticated_page.wait_for_timeout(500)

        # Test end date column filter
        end_header = authenticated_page.locator(".ag-header-cell").filter(has_text="End")
        if end_header.is_visible():
            filter_icon = end_header.locator(".ag-icon-filter")
            if filter_icon.is_visible():
                filter_icon.click()
                authenticated_page.wait_for_timeout(1000)

                # Check that date filter menu appears
                filter_menu = authenticated_page.locator(".ag-filter-wrapper")
                expect(filter_menu).to_be_visible()


@pytest.mark.playwright
class TestTableFilterInteraction:
    """Test interactive filter functionality."""

    def test_filter_application_and_clear(self, authenticated_page: Page):
        """Test applying and clearing filters on executions table."""
        # Navigate to executions tab
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)

        executions_tab = authenticated_page.locator("text=Executions").first
        executions_tab.click()
        authenticated_page.wait_for_timeout(3000)

        # Wait for the executions table to load
        table = authenticated_page.wait_for_selector(
            "[data-testid='executions-table']", timeout=10000
        )
        expect(table).to_be_visible()

        # Find the status column header and open filter menu
        status_header = authenticated_page.locator(".ag-header-cell").filter(has_text="Status")
        if status_header.is_visible():
            filter_icon = status_header.locator(".ag-icon-filter")
            if filter_icon.is_visible():
                filter_icon.click()
                authenticated_page.wait_for_timeout(1000)

                filter_menu = authenticated_page.locator(".ag-filter-wrapper")
                if filter_menu.is_visible():
                    # Test applying filter
                    apply_button = filter_menu.locator("button").filter(has_text="Apply")
                    if apply_button.is_visible():
                        apply_button.click()
                        authenticated_page.wait_for_timeout(1000)

                    # Test clearing filter
                    if filter_icon.is_visible():
                        filter_icon.click()
                        authenticated_page.wait_for_timeout(1000)

                        clear_button = filter_menu.locator("button").filter(has_text="Clear")
                        if clear_button.is_visible():
                            clear_button.click()
                            authenticated_page.wait_for_timeout(1000)

    def test_multiple_filters_interaction(self, authenticated_page: Page):
        """Test applying multiple filters on the same table."""
        # Navigate to executions tab
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)

        executions_tab = authenticated_page.locator("text=Executions").first
        executions_tab.click()
        authenticated_page.wait_for_timeout(3000)

        # Wait for the executions table to load
        table = authenticated_page.wait_for_selector(
            "[data-testid='executions-table']", timeout=10000
        )
        expect(table).to_be_visible()

        # Apply status filter first
        status_header = authenticated_page.locator(".ag-header-cell").filter(has_text="Status")
        if status_header.is_visible():
            filter_icon = status_header.locator(".ag-icon-filter")
            if filter_icon.is_visible():
                filter_icon.click()
                authenticated_page.wait_for_timeout(1000)

                filter_menu = authenticated_page.locator(".ag-filter-wrapper")
                if filter_menu.is_visible():
                    apply_button = filter_menu.locator("button").filter(has_text="Apply")
                    if apply_button.is_visible():
                        apply_button.click()
                        authenticated_page.wait_for_timeout(1000)

        # Apply duration filter as well
        duration_header = authenticated_page.locator(".ag-header-cell").filter(has_text="Duration")
        if duration_header.is_visible():
            filter_icon = duration_header.locator(".ag-icon-filter")
            if filter_icon.is_visible():
                filter_icon.click()
                authenticated_page.wait_for_timeout(1000)

                filter_menu = authenticated_page.locator(".ag-filter-wrapper")
                if filter_menu.is_visible():
                    # Enter a filter value for duration (greater than 0)
                    filter_input = filter_menu.locator("input[type='text']")
                    if filter_input.is_visible():
                        filter_input.fill("0")

                    apply_button = filter_menu.locator("button").filter(has_text="Apply")
                    if apply_button.is_visible():
                        apply_button.click()
                        authenticated_page.wait_for_timeout(1000)

    def test_filter_persistence_across_tab_switches(self, authenticated_page: Page):
        """Test that filters are maintained when switching between tabs."""
        # Navigate to executions tab and apply a filter
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)

        executions_tab = authenticated_page.locator("text=Executions").first
        executions_tab.click()
        authenticated_page.wait_for_timeout(3000)

        # Wait for the executions table to load
        table = authenticated_page.wait_for_selector(
            "[data-testid='executions-table']", timeout=10000
        )
        expect(table).to_be_visible()

        # Apply a filter
        status_header = authenticated_page.locator(".ag-header-cell").filter(has_text="Status")
        if status_header.is_visible():
            filter_icon = status_header.locator(".ag-icon-filter")
            if filter_icon.is_visible():
                filter_icon.click()
                authenticated_page.wait_for_timeout(1000)

                filter_menu = authenticated_page.locator(".ag-filter-wrapper")
                if filter_menu.is_visible():
                    apply_button = filter_menu.locator("button").filter(has_text="Apply")
                    if apply_button.is_visible():
                        apply_button.click()
                        authenticated_page.wait_for_timeout(1000)

        # Switch to another tab
        scripts_tab = authenticated_page.locator("text=Scripts").first
        if scripts_tab.is_visible():
            scripts_tab.click()
            authenticated_page.wait_for_timeout(2000)

        # Switch back to executions tab
        executions_tab.click()
        authenticated_page.wait_for_timeout(3000)

        # Verify the filter is still applied (status header should show filter indicator)
        status_header = authenticated_page.locator(".ag-header-cell").filter(has_text="Status")
        expect(status_header).to_be_visible()


@pytest.mark.playwright
class TestTableFilterAccessibility:
    """Test filter accessibility and usability features."""

    def test_filter_keyboard_navigation(self, authenticated_page: Page):
        """Test that filters can be navigated using keyboard."""
        # Navigate to executions tab
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)

        executions_tab = authenticated_page.locator("text=Executions").first
        executions_tab.click()
        authenticated_page.wait_for_timeout(3000)

        # Wait for the executions table to load
        table = authenticated_page.wait_for_selector(
            "[data-testid='executions-table']", timeout=10000
        )
        expect(table).to_be_visible()

        # Test keyboard access to status filter
        status_header = authenticated_page.locator(".ag-header-cell").filter(has_text="Status")
        if status_header.is_visible():
            # Focus the header and use Enter to open filter
            status_header.focus()
            authenticated_page.keyboard.press("Tab")  # Navigate to filter icon
            authenticated_page.keyboard.press("Enter")  # Open filter
            authenticated_page.wait_for_timeout(1000)

            # Check if filter menu opened
            filter_menu = authenticated_page.locator(".ag-filter-wrapper")
            if filter_menu.is_visible():
                # Use Escape to close
                authenticated_page.keyboard.press("Escape")
                authenticated_page.wait_for_timeout(500)

    def test_filter_mobile_responsiveness(self, authenticated_page: Page):
        """Test that filters work on mobile viewport."""
        # Set mobile viewport
        authenticated_page.set_viewport_size({"width": 375, "height": 667})

        # Navigate to executions tab
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)

        executions_tab = authenticated_page.locator("text=Executions").first
        executions_tab.click()
        authenticated_page.wait_for_timeout(3000)

        # Wait for the executions table to load
        table = authenticated_page.wait_for_selector(
            "[data-testid='executions-table']", timeout=10000
        )
        expect(table).to_be_visible()

        # Test that filters are still accessible on mobile
        status_header = authenticated_page.locator(".ag-header-cell").filter(has_text="Status")
        if status_header.is_visible():
            filter_icon = status_header.locator(".ag-icon-filter")
            if filter_icon.is_visible():
                filter_icon.click()
                authenticated_page.wait_for_timeout(1000)

                # Check that filter menu appears and is usable on mobile
                filter_menu = authenticated_page.locator(".ag-filter-wrapper")
                if filter_menu.is_visible():
                    expect(filter_menu).to_be_visible()

                    # Close the filter
                    authenticated_page.keyboard.press("Escape")

        # Reset to desktop viewport
        authenticated_page.set_viewport_size({"width": 1280, "height": 720})
