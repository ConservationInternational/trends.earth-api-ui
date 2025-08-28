"""
Playwright configuration and fixtures for Trends.Earth API UI tests.
"""

import os
import threading
import time

from playwright.sync_api import Page
import pytest
import requests

from trendsearth_ui.app import app

# Perform the Playwright browser availability check at import-time so that
# skip markers created below see the correct state during collection.
try:
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            try:
                # Try using Playwright's own chromium first
                browser = p.chromium.launch(headless=True)
                browser.close()
                print("✅ Playwright chromium browser is available and ready")
                os.environ["PLAYWRIGHT_BROWSERS_AVAILABLE"] = "true"
            except Exception:
                # Fall back to system Chrome if available
                browser = p.chromium.launch(headless=True, channel="chrome")
                browser.close()
                print("✅ System Chrome browser is available and ready for Playwright")
                os.environ["PLAYWRIGHT_BROWSERS_AVAILABLE"] = "true"
    except Exception as e:  # pragma: no cover - environment dependent
        print(f"⚠️  Playwright browsers not available: {e}")
        print("💡 This is common in CI environments with firewall restrictions")
        print("💡 Playwright tests will be automatically skipped")
        print("💡 To install browsers locally, run: poetry run playwright install chromium")
        os.environ["PLAYWRIGHT_BROWSERS_AVAILABLE"] = "false"
except ImportError as e:
    # Playwright package itself is required for these tests
    print("❌ Playwright not installed")
    print("💡 Install with: poetry add --group dev pytest-playwright playwright")
    raise ImportError("Playwright not installed - required for playwright tests") from e


def pytest_configure(config):
    """Configure pytest for playwright tests."""
    # Register the playwright marker to avoid warnings
    config.addinivalue_line("markers", "playwright: Playwright end-to-end tests")


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    """Configure browser to use system Chrome when Playwright browsers not available."""
    if not browsers_available():
        # Skip tests if browsers are not available
        return browser_type_launch_args

    # Try to use system Chrome if Playwright's chromium is not available
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            # Test if Playwright's chromium works
            browser = p.chromium.launch(headless=True, **browser_type_launch_args)
            browser.close()
            return browser_type_launch_args
    except Exception:
        # Fall back to system Chrome
        return {**browser_type_launch_args, "channel": "chrome"}


def browsers_available():
    """Check if Playwright browsers are available."""
    return os.environ.get("PLAYWRIGHT_BROWSERS_AVAILABLE", "false").lower() == "true"


# Pytest skip marker for tests that require browsers
skip_if_no_browsers = pytest.mark.skipif(
    not browsers_available(),
    reason="Playwright browsers not available (common in CI environments with firewall restrictions)",
)


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
    """Navigate to app and simulate authentication by setting a cookie."""
    # Create mock auth cookie data that the app will recognize
    from datetime import datetime, timedelta
    import json

    from trendsearth_ui.utils import create_auth_cookie_data

    mock_user_data = {
        "id": "test_user_123",
        "name": "Test User",
        "email": "test@example.com",
        "role": "ADMIN",
    }
    cookie_data = create_auth_cookie_data(
        "mock_access_token_123",
        "mock_refresh_token_456",
        "test@example.com",
        mock_user_data,
        "production",
    )
    cookie_value = json.dumps(cookie_data)

    # Add the cookie to the browser context before navigating
    page.context.add_cookies(
        [
            {
                "name": "auth_token",
                "value": cookie_value,
                "domain": "127.0.0.1",
                "path": "/",
            }
        ]
    )

    # Navigate to the root of the app
    page.goto(live_server)

    # Wait for the dashboard to load, confirming authentication worked
    try:
        page.wait_for_selector("[data-testid='dashboard-content']", timeout=15000)

        # Wait for admin tabs to become visible (indicating auth stores are populated)
        # This ensures tab visibility callbacks have executed
        # We need to wait for both users and status tabs since they should both be visible for ADMIN role
        admin_tabs_visible = False
        max_attempts = 5  # Increased attempts for CI stability
        attempt = 0

        while not admin_tabs_visible and attempt < max_attempts:
            try:
                attempt += 1
                print(f"🔄 Checking admin tab visibility (attempt {attempt}/{max_attempts})")

                # First, verify the auth stores are populated by checking if authentication state is ready
                # This helps detect when the auth callback has run
                try:
                    # Try to access a Dash component to trigger a component update if needed
                    page.evaluate("window.dispatchEvent(new Event('resize'))")
                    page.wait_for_timeout(1000)  # Give time for callbacks to run
                except Exception:
                    pass  # Best effort to trigger updates

                # Wait for both critical admin tabs to be visible
                page.wait_for_selector("#users-tab-btn:visible", timeout=12000)
                page.wait_for_selector("#status-tab-btn:visible", timeout=12000)

                # Double check they're still visible (handle race conditions with token refresh)
                if (
                    page.locator("#users-tab-btn").is_visible()
                    and page.locator("#status-tab-btn").is_visible()
                ):
                    admin_tabs_visible = True
                    print("✅ Admin tabs are visible - authentication fully initialized")
                else:
                    print("⚠️  Admin tabs became hidden, retrying...")
                    page.wait_for_timeout(2000)  # Wait 2s before retry

            except Exception as e:
                if attempt >= max_attempts:
                    print(
                        f"⚠️  Admin tabs not visible after {max_attempts} attempts - tests may need to handle tab visibility"
                    )
                    print(f"    Last error: {e}")
                    # Don't fail here, some tests might not need admin tabs visible
                    break
                else:
                    print(f"⚠️  Attempt {attempt} failed, retrying... ({e})")
                    page.wait_for_timeout(3000)  # Wait 3s before retry
                    # Try refreshing the page to reinitialize auth if needed
                    if attempt >= 2:
                        print("🔄 Refreshing page to reinitialize authentication...")
                        page.reload()
                        page.wait_for_selector("[data-testid='dashboard-content']", timeout=15000)
                        page.wait_for_timeout(2000)  # Additional wait after reload

    except Exception as e:
        # If dashboard doesn't load, check if we're still on login page
        if page.locator("h4:has-text('Login')").is_visible():
            raise RuntimeError(
                "Authentication via cookie failed - app is still on the login page."
            ) from e
        else:
            raise RuntimeError(f"Dashboard content not found after setting auth cookie: {e}") from e

    return page


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context for testing."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
    }


def wait_for_ag_grid_table(page, table_testid, timeout=15000):
    """
    Reliably wait for an AG-Grid table to be fully loaded and ready for interaction.

    Args:
        page: Playwright page object
        table_testid: data-testid attribute of the table container
        timeout: Maximum time to wait in milliseconds

    Returns:
        True if table is ready, False if timeout
    """
    try:
        print(f"⏳ Waiting for AG-Grid table '{table_testid}' to load...")

        # Step 1: Wait for the table container
        page.wait_for_selector(f"[data-testid='{table_testid}']", timeout=timeout)
        print(f"✅ Table container '{table_testid}' found")

        # Step 2: Wait for AG-Grid to initialize inside the container
        page.wait_for_selector(f"[data-testid='{table_testid}'] .ag-grid", timeout=timeout)
        print(f"✅ AG-Grid component found in '{table_testid}'")

        # Step 3: Wait for headers to be present (indicates table structure is ready)
        page.wait_for_selector(f"[data-testid='{table_testid}'] .ag-header", timeout=timeout)
        print(f"✅ AG-Grid headers found in '{table_testid}'")

        # Step 4: Wait for any rows to appear or confirm empty state
        try:
            # Try to find either rows or the "no rows" overlay
            page.wait_for_selector(
                f"[data-testid='{table_testid}'] .ag-row, [data-testid='{table_testid}'] .ag-overlay-no-rows-center",
                timeout=5000,
            )
            print(f"✅ AG-Grid data loaded in '{table_testid}'")
        except Exception:
            # Table might be loading data, give it more time
            print(f"⏳ Waiting for data to load in '{table_testid}'...")
            page.wait_for_timeout(2000)

        # Step 5: Final stability wait
        page.wait_for_timeout(1000)  # Let any animations/renders complete
        print(f"✅ AG-Grid table '{table_testid}' is ready for interaction")
        return True

    except Exception as e:
        print(f"❌ Failed to load AG-Grid table '{table_testid}': {e}")
        return False


def navigate_to_tab_and_wait_for_table(page, tab_name, table_testid, timeout=20000):
    """
    Navigate to a specific tab and wait for its AG-Grid table to be ready.

    Args:
        page: Playwright page object
        tab_name: Name of the tab to click (e.g., "Executions", "Users", "Scripts")
        table_testid: data-testid attribute of the expected table
        timeout: Maximum time to wait

    Returns:
        True if successful, False if failed
    """
    try:
        print(f"🔄 Navigating to {tab_name} tab...")

        # Wait for dashboard to be ready
        page.wait_for_selector("[data-testid='dashboard-content']", timeout=10000)

        # Click the tab
        tab_locator = page.locator(f"text={tab_name}").first
        tab_locator.click()
        print(f"✅ Clicked {tab_name} tab")

        # Give tab switch time to process
        page.wait_for_timeout(1000)

        # Wait for the table to be ready
        success = wait_for_ag_grid_table(page, table_testid, timeout)
        if success:
            print(f"✅ {tab_name} tab and table are ready")
        else:
            print(f"⚠️  {tab_name} tab loaded but table is not ready")

        return success

    except Exception as e:
        print(f"❌ Failed to navigate to {tab_name} tab: {e}")
        return False


# Mock data generation functions for Playwright tests


def generate_mock_executions_data(count=10, page=1, per_page=50):
    """Generate mock execution data for Playwright tests."""
    from datetime import datetime, timedelta
    import random

    statuses = ["FINISHED", "RUNNING", "FAILED", "QUEUED", "CANCELLED"]
    script_names = [
        "Land Degradation Analysis",
        "Vegetation Index Calculation",
        "Soil Erosion Assessment",
        "Carbon Stock Monitoring",
        "Drought Impact Analysis",
        "Urban Expansion Detection",
        "Forest Change Detection",
        "Biodiversity Mapping",
        "Agricultural Productivity",
        "Water Quality Assessment",
    ]
    users = [
        "Alice Johnson",
        "Bob Smith",
        "Carol Davis",
        "David Wilson",
        "Emma Brown",
        "Frank Miller",
        "Grace Lee",
        "Henry Chen",
        "Isabel Garcia",
        "Jack Robinson",
    ]

    executions = []
    base_date = datetime(2024, 1, 1)

    for i in range(count):
        status = random.choice(statuses)
        start_date = base_date + timedelta(days=i, hours=random.randint(0, 23))
        end_date = None
        progress = 0

        if status == "FINISHED":
            end_date = start_date + timedelta(minutes=random.randint(30, 180))
            progress = 100
        elif status == "RUNNING":
            progress = random.randint(10, 90)
        elif status == "FAILED":
            end_date = start_date + timedelta(minutes=random.randint(5, 60))
            progress = random.randint(5, 50)

        execution = {
            "id": f"exec-{i + 1}",
            "script_name": random.choice(script_names),
            "user_name": random.choice(users),
            "status": status,
            "start_date": start_date.isoformat() + "Z",
            "end_date": end_date.isoformat() + "Z" if end_date else None,
            "progress": progress,
        }
        executions.append(execution)

    return {
        "data": executions,
        "total": count * 3,  # Simulate more total records than current page
        "page": page,
        "per_page": per_page,
    }


def generate_mock_scripts_data(count=10, page=1, per_page=50):
    """Generate mock script data for Playwright tests."""
    from datetime import datetime, timedelta
    import random

    statuses = ["PUBLISHED", "DRAFT", "ARCHIVED", "UNDER_REVIEW"]
    script_names = [
        "NDVI Time Series Analysis",
        "Land Cover Classification",
        "Soil Organic Carbon Estimation",
        "Precipitation Trend Analysis",
        "Deforestation Risk Assessment",
        "Agricultural Yield Prediction",
        "Wetland Monitoring System",
        "Urban Heat Island Detection",
        "Coastal Erosion Mapping",
        "Grassland Productivity Index",
    ]
    descriptions = [
        "Automated analysis of vegetation health indicators",
        "Machine learning-based land cover mapping",
        "Carbon stock assessment using satellite data",
        "Climate trend analysis for agricultural planning",
        "Early warning system for forest loss",
        "Crop yield forecasting model",
        "Wetland ecosystem health monitoring",
        "Urban temperature analysis tool",
        "Coastal change detection algorithm",
        "Grassland productivity monitoring system",
    ]
    users = [
        "Dr. Sarah Mitchell",
        "Prof. Michael Thompson",
        "Dr. Lisa Wang",
        "Dr. James Rodriguez",
        "Dr. Rachel Green",
        "Prof. David Kim",
        "Dr. Maria Santos",
        "Dr. Ahmed Hassan",
        "Dr. Jennifer Liu",
        "Dr. Carlos Mendez",
    ]

    scripts = []
    base_date = datetime(2024, 1, 1)

    for i in range(count):
        created_date = base_date + timedelta(days=i * 3, hours=random.randint(0, 23))
        updated_date = created_date + timedelta(days=random.randint(0, 30))

        script = {
            "id": f"script-{i + 1}",
            "name": script_names[i % len(script_names)],
            "user_name": users[i % len(users)],
            "description": descriptions[i % len(descriptions)],
            "status": random.choice(statuses),
            "created_at": created_date.isoformat() + "Z",
            "updated_at": updated_date.isoformat() + "Z",
        }
        scripts.append(script)

    return {
        "data": scripts,
        "total": count * 2,  # Simulate more total records than current page
        "page": page,
        "per_page": per_page,
    }


def generate_mock_users_data(count=10, page=1, per_page=50):
    """Generate mock user data for Playwright tests."""
    from datetime import datetime, timedelta
    import random

    roles = ["USER", "ADMIN", "MODERATOR", "VIEWER"]
    institutions = [
        "Conservation International",
        "World Wildlife Fund",
        "UNEP",
        "FAO",
        "CIAT",
        "CIFOR",
        "ICRAF",
        "NASA",
        "ESA",
        "USGS",
        "University of Oxford",
        "Stanford University",
        "MIT",
        "Harvard University",
        "Cambridge University",
    ]
    countries = [
        "United States",
        "United Kingdom",
        "Germany",
        "France",
        "Brazil",
        "Kenya",
        "South Africa",
        "India",
        "China",
        "Australia",
        "Canada",
        "Mexico",
        "Colombia",
        "Indonesia",
        "Philippines",
    ]

    first_names = [
        "Alice",
        "Bob",
        "Carol",
        "David",
        "Emma",
        "Frank",
        "Grace",
        "Henry",
        "Isabel",
        "Jack",
        "Karen",
        "Liam",
        "Maria",
        "Nathan",
        "Olivia",
        "Peter",
    ]
    last_names = [
        "Johnson",
        "Smith",
        "Davis",
        "Wilson",
        "Brown",
        "Miller",
        "Lee",
        "Chen",
        "Garcia",
        "Robinson",
        "Anderson",
        "Taylor",
        "Thomas",
        "Martinez",
        "Clark",
        "Lewis",
    ]

    users = []
    base_date = datetime(2023, 6, 1)

    for i in range(count):
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        name = f"{first_name} {last_name}"
        email = f"{first_name.lower()}.{last_name.lower()}@example.com"

        created_date = base_date + timedelta(days=i * 7, hours=random.randint(0, 23))
        updated_date = created_date + timedelta(days=random.randint(1, 60))

        user = {
            "id": f"user-{i + 1}",
            "email": email,
            "name": name,
            "institution": random.choice(institutions),
            "country": random.choice(countries),
            "role": random.choice(roles),
            "created_at": created_date.isoformat() + "Z",
            "updated_at": updated_date.isoformat() + "Z",
        }
        users.append(user)

    return {
        "data": users,
        "total": count * 4,  # Simulate more total records than current page
        "page": page,
        "per_page": per_page,
    }


def generate_mock_status_data():
    """Generate mock status/system data for Playwright tests."""
    from datetime import datetime
    import random

    # Generate mock system statistics
    current_time = datetime.now()

    # Mock execution statistics
    total_executions = random.randint(150, 300)
    running_executions = random.randint(5, 25)
    finished_executions = random.randint(100, 200)
    failed_executions = total_executions - running_executions - finished_executions

    # Mock user statistics
    total_users = random.randint(50, 150)
    active_users_24h = random.randint(10, 40)

    # Mock system metrics
    cpu_usage = random.randint(15, 85)
    memory_usage = random.randint(30, 90)

    status_data = {
        "data": {
            "executions": {
                "total": total_executions,
                "running": running_executions,
                "finished": finished_executions,
                "failed": failed_executions,
            },
            "users": {
                "total": total_users,
                "active_24h": active_users_24h,
            },
            "system": {
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "uptime": "15 days, 3 hours",
                "version": "v2.1.0",
            },
            "last_updated": current_time.isoformat() + "Z",
            "timestamp": current_time.isoformat() + "Z",
        }
    }

    return status_data


# Pytest fixtures for easy access to mock data in tests


@pytest.fixture
def mock_executions_data():
    """Fixture providing mock executions data for Playwright tests."""
    return generate_mock_executions_data()


@pytest.fixture
def mock_scripts_data():
    """Fixture providing mock scripts data for Playwright tests."""
    return generate_mock_scripts_data()


@pytest.fixture
def mock_users_data():
    """Fixture providing mock users data for Playwright tests."""
    return generate_mock_users_data()


@pytest.fixture
def mock_status_data():
    """Fixture providing mock status data for Playwright tests."""
    return generate_mock_status_data()
