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
            browser = p.chromium.launch(headless=True)
            browser.close()
            print("✅ Playwright browsers are available and ready")
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
