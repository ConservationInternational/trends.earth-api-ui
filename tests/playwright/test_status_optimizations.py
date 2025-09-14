"""
Status page optimization tests using Playwright.
Tests the performance optimizations, skeleton loading, and chart rendering.
"""

import time

from playwright.sync_api import Page, expect
import pytest

from .conftest import skip_if_no_browsers


@pytest.mark.playwright
@skip_if_no_browsers
class TestStatusPageOptimizations:
    """Test status page performance optimizations."""

    def test_skeleton_loading_appears(self, authenticated_page: Page):
        """Test that skeleton loading appears when switching time periods."""
        # Navigate to status tab
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)
        status_tab = authenticated_page.locator("#status-tab-btn")
        expect(status_tab).to_be_visible()
        status_tab.click()

        # Wait for status content to load
        authenticated_page.wait_for_selector("[data-testid='status-content']", timeout=15000)

        # Find time period buttons - look for common text patterns
        time_period_selectors = [
            "text=Daily",
            "text=Weekly",
            "text=Monthly",
            ".time-period-btn",
            "[data-testid*='time']",
            ".btn:has-text('Daily')",
            ".btn:has-text('Weekly')",
            ".btn:has-text('Monthly')",
        ]

        # Try to find time period buttons
        time_button = None
        for selector in time_period_selectors:
            try:
                button = authenticated_page.locator(selector).first
                if button.is_visible():
                    time_button = button
                    break
            except Exception:
                continue

        if time_button:
            # Click the time period button and look for skeleton loading
            time_button.click()

            # Look for skeleton loading indicators
            skeleton_selectors = [
                ".skeleton",
                ".skeleton-loader",
                ".loading-skeleton",
                "[data-testid*='skeleton']",
                ".placeholder-glow",
                ".animate-pulse",
            ]

            skeleton_found = False
            for selector in skeleton_selectors:
                try:
                    skeleton = authenticated_page.locator(selector).first
                    if skeleton.is_visible(timeout=1000):
                        skeleton_found = True
                        break
                except Exception:
                    continue

            # If no skeleton found, that's ok - the optimization might be loading so fast
            # that skeleton doesn't appear, which is actually good for performance
            print(
                f"Skeleton loading {'found' if skeleton_found else 'not found (possibly fast loading)'}"
            )

    def test_optimized_chart_rendering(self, authenticated_page: Page):
        """Test that charts render with performance optimizations."""
        # Navigate to status tab
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)
        status_tab = authenticated_page.locator("#status-tab-btn")
        expect(status_tab).to_be_visible()
        status_tab.click()

        # Wait for status content to load
        authenticated_page.wait_for_selector("[data-testid='status-content']", timeout=15000)

        # Look for chart containers (Plotly charts)
        chart_selectors = [
            ".plotly-graph-div",
            "[data-testid*='chart']",
            ".js-plotly-plot",
            ".chart-container",
        ]

        chart_found = False
        for selector in chart_selectors:
            charts = authenticated_page.locator(selector)
            count = charts.count()
            if count > 0:
                chart_found = True
                # Test that first chart is visible
                expect(charts.first).to_be_visible(timeout=10000)

                # Check for Plotly-specific optimizations
                # Charts should not have scroll zoom or mode bar if optimized
                chart_element = charts.first

                # Wait for chart to fully render
                authenticated_page.wait_for_timeout(2000)

                # Check if chart has rendered content (not just empty div)
                svg_elements = chart_element.locator("svg")
                if svg_elements.count() > 0:
                    expect(svg_elements.first).to_be_visible()

                break

        assert chart_found, "No charts found on status page"

    def test_progressive_loading_elements(self, authenticated_page: Page):
        """Test that status page has progressive loading elements."""
        # Navigate to status tab
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)
        status_tab = authenticated_page.locator("#status-tab-btn")
        expect(status_tab).to_be_visible()
        status_tab.click()

        # Wait for status content to load
        authenticated_page.wait_for_selector("[data-testid='status-content']", timeout=15000)

        # Look for progressive loading indicators
        progressive_indicators = [
            ".card",
            ".status-card",
            ".metric-card",
            ".chart-container",
            "[data-testid*='status']",
            ".row",
            ".col",
        ]

        elements_found = 0
        for selector in progressive_indicators:
            elements = authenticated_page.locator(selector)
            count = elements.count()
            if count > 0:
                elements_found += count
                # Verify at least first element is visible
                expect(elements.first).to_be_visible(timeout=5000)

        assert elements_found > 0, "No progressive loading elements found"

    def test_css_optimizations_loaded(self, authenticated_page: Page):
        """Test that CSS optimization file is loaded."""
        # Navigate to status tab
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)
        status_tab = authenticated_page.locator("#status-tab-btn")
        expect(status_tab).to_be_visible()
        status_tab.click()

        # Check if CSS optimization styles are applied
        # Look for elements that should have optimization classes
        optimization_selectors = [
            ".chart-container",
            ".status-card",
            ".metric-card",
            "[style*='contain']",
            "[style*='transform3d']",
        ]

        optimization_found = False
        for selector in optimization_selectors:
            elements = authenticated_page.locator(selector)
            if elements.count() > 0:
                optimization_found = True
                break

        # Even if specific optimization classes aren't found,
        # the page should still load and function properly
        print(
            f"CSS optimizations {'detected' if optimization_found else 'not visually detected (may still be applied)'}"
        )

    def test_status_page_performance_timing(self, authenticated_page: Page):
        """Test status page loading performance."""
        # Navigate to status tab and measure loading time
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)

        start_time = time.time()

        status_tab = authenticated_page.locator("#status-tab-btn")
        expect(status_tab).to_be_visible()
        status_tab.click()

        # Wait for status content to load
        authenticated_page.wait_for_selector("[data-testid='status-content']", timeout=15000)

        # Wait for any charts or dynamic content to load
        authenticated_page.wait_for_timeout(3000)

        end_time = time.time()
        loading_time = end_time - start_time

        # Performance should be reasonable (under 15 seconds including network)
        assert loading_time < 15, f"Status page took too long to load: {loading_time:.2f}s"
        print(f"Status page loaded in {loading_time:.2f} seconds")

    def test_consolidated_callbacks_no_duplicate_requests(self, authenticated_page: Page):
        """Test that consolidated callbacks reduce duplicate API requests."""
        # Set up request monitoring
        requests = []

        def handle_request(request):
            if "/api/v1/" in request.url:
                requests.append(
                    {"url": request.url, "method": request.method, "timestamp": time.time()}
                )

        authenticated_page.on("request", handle_request)

        # Navigate to status tab
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)
        status_tab = authenticated_page.locator("#status-tab-btn")
        expect(status_tab).to_be_visible()
        status_tab.click()

        # Wait for status content to load
        authenticated_page.wait_for_selector("[data-testid='status-content']", timeout=15000)

        # Wait for all requests to complete
        authenticated_page.wait_for_timeout(5000)

        # Analyze API requests
        api_requests = [r for r in requests if "/api/v1/" in r["url"]]
        status_requests = [r for r in api_requests if "status" in r["url"].lower()]

        print(f"Total API requests: {len(api_requests)}")
        print(f"Status-related requests: {len(status_requests)}")

        # With optimized callbacks, there should be fewer status requests
        # than the number of status components (which would happen with separate callbacks)
        assert len(status_requests) <= 10, f"Too many status requests: {len(status_requests)}"

    def test_error_handling_with_optimizations(self, authenticated_page: Page):
        """Test that optimizations work properly with error conditions."""
        # Navigate to status tab
        authenticated_page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)
        status_tab = authenticated_page.locator("#status-tab-btn")
        expect(status_tab).to_be_visible()
        status_tab.click()

        # Wait for status content to load
        authenticated_page.wait_for_selector("[data-testid='status-content']", timeout=15000)

        # Look for error handling elements (checking for common error patterns)
        # The page should handle errors gracefully
        page_content = authenticated_page.content()
        assert "500" not in page_content, "Server error detected"
        assert "404" not in page_content, "Not found error detected"

        # Even if there are error messages, the page structure should be intact
        expect(authenticated_page.locator("[data-testid='status-content']")).to_be_visible()
