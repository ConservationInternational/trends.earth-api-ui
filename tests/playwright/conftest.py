"""
Playwright configuration and fixtures for Trends.Earth API UI tests.
"""

import threading
import time

from playwright.sync_api import Page
import pytest
import requests

from trendsearth_ui.app import app


def pytest_configure(config):
    """Configure pytest for playwright tests."""
    # Register the playwright marker to avoid warnings
    config.addinivalue_line("markers", "playwright: Playwright end-to-end tests")

    # Check if playwright browsers are available - FAIL if not available
    try:
        from playwright.sync_api import sync_playwright

        # Try to check if browsers are available
        try:
            with sync_playwright() as p:
                try:
                    browser = p.chromium.launch(headless=True)
                    browser.close()
                    print("✅ Playwright browsers are available and ready")
                except Exception as e:
                    print(f"❌ Playwright browsers not available: {e}")
                    print("💡 Run 'playwright install chromium' to install browsers")
                    raise RuntimeError(f"Playwright browsers not available: {e}") from e
        except Exception as e:
            print(f"❌ Playwright browser check failed: {e}")
            raise RuntimeError(f"Playwright browser check failed: {e}") from e

    except ImportError as e:
        print("❌ Playwright not installed")
        raise ImportError("Playwright not installed - required for playwright tests") from e


@pytest.fixture(scope="session")
def live_server():
    """Start the Dash app in a separate thread for testing."""
    import threading
    import time

    from werkzeug.serving import make_server

    # Start server in a separate thread
    server = make_server("127.0.0.1", 8050, app.server, threaded=True)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    # Wait for server to be ready
    time.sleep(2)

    # Check if server is responding
    base_url = "http://127.0.0.1:8050"
    max_retries = 10
    for i in range(max_retries):
        try:
            response = requests.get(f"{base_url}/api-ui-health", timeout=5)
            if response.status_code == 200:
                break
        except requests.exceptions.RequestException:
            if i == max_retries - 1:
                raise
            time.sleep(1)

    yield base_url

    # Shutdown server
    server.shutdown()


@pytest.fixture
def app_page(page: Page, live_server):
    """Navigate to the app main page."""
    page.goto(live_server)
    return page


@pytest.fixture
def authenticated_page(page: Page, live_server):
    """Navigate to app and simulate authentication (mocked)."""
    page.goto(live_server)

    # Mock authentication by setting local storage
    page.evaluate("""
        localStorage.setItem('auth_token', 'mock_token_12345');
        localStorage.setItem('user_role', 'ADMIN');
        localStorage.setItem('user_data', JSON.stringify({
            id: 'test_user_123',
            name: 'Test User',
            email: 'test@example.com',
            role: 'ADMIN'
        }));
    """)

    # Refresh to load with authentication
    page.reload()
    return page


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context for testing."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
    }
