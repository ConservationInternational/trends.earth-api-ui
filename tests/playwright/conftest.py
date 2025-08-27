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
    max_retries = 30  # Increase retries for reliability
    for i in range(max_retries):
        try:
            response = requests.get(f"{base_url}/api-ui-health", timeout=10)
            if response.status_code == 200:
                print(f"✅ Server ready after {i + 1} attempts")
                break
        except requests.exceptions.RequestException:
            if i == max_retries - 1:
                print(f"❌ Server failed to start after {max_retries} attempts")
                raise
            time.sleep(0.5)  # Wait shorter between retries

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
    # First navigate to the page
    page.goto(live_server)

    # Wait for initial page load
    page.wait_for_timeout(1000)

    # Create mock auth cookie data that matches what the app expects
    from datetime import datetime, timedelta
    import json

    # Mock auth data structure that matches create_auth_cookie_data
    expiration = datetime.now() + timedelta(days=30)
    auth_cookie_data = {
        "access_token": "mock_token_12345",
        "refresh_token": "mock_refresh_token_67890",
        "email": "test@example.com",
        "user_data": {
            "id": "test_user_123",
            "name": "Test User",
            "email": "test@example.com",
            "role": "ADMIN",
        },
        "api_environment": "production",
        "expires_at": expiration.isoformat(),
        "created_at": datetime.now().isoformat(),
    }

    # Set the HTTP cookie that the app recognizes
    cookie_value = json.dumps(auth_cookie_data)

    # Add the cookie to the browser context
    page.context.add_cookies(
        [
            {
                "name": "auth_token",
                "value": cookie_value,
                "domain": "127.0.0.1",
                "path": "/",
                "httpOnly": True,
                "secure": False,
                "sameSite": "Lax",
            }
        ]
    )

    # Reload page to trigger authentication check with cookie
    page.reload()

    # Wait for authentication to process and dashboard to load
    # Use a more reliable wait for dashboard content
    try:
        page.wait_for_selector("[data-testid='dashboard-content']", timeout=15000)
    except Exception as e:
        # If dashboard doesn't load, check if we're still on login page
        if page.locator("h4:has-text('Login')").is_visible():
            raise RuntimeError("Authentication failed - still on login page") from e
        else:
            raise RuntimeError(f"Dashboard content not found: {e}") from e

    return page


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context for testing."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
    }
