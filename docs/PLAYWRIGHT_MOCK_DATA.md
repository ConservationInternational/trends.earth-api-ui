# Mock Data Generation for Playwright Tests

This document describes the mock data generation functions added to support Playwright end-to-end testing in the Trends.Earth API UI.

## Overview

The mock data generation functions provide realistic test data that can be used to populate tables and UI components during Playwright tests. These functions generate data in the correct API response format with proper pagination, making them suitable for intercepting API calls and returning mock responses.

## Available Functions

### Core Functions

All functions are available in `tests/playwright/conftest.py`:

#### `generate_mock_executions_data(count=10, page=1, per_page=50)`
Generates mock execution data for the executions table.

**Returns:** API response with execution data including:
- `id`: Unique execution identifier
- `script_name`: Name of the executed script
- `user_name`: User who ran the execution
- `status`: Execution status (FINISHED, RUNNING, FAILED, QUEUED, CANCELLED)
- `start_date`: ISO timestamp when execution started
- `end_date`: ISO timestamp when execution ended (null for running executions)
- `progress`: Integer 0-100 representing completion percentage

#### `generate_mock_scripts_data(count=10, page=1, per_page=50)`
Generates mock script data for the scripts table.

**Returns:** API response with script data including:
- `id`: Unique script identifier
- `name`: Script name
- `user_name`: Script author
- `description`: Script description
- `status`: Script status (PUBLISHED, DRAFT, ARCHIVED, UNDER_REVIEW)
- `created_at`: ISO timestamp when script was created
- `updated_at`: ISO timestamp when script was last updated

#### `generate_mock_users_data(count=10, page=1, per_page=50)`
Generates mock user data for the users table.

**Returns:** API response with user data including:
- `id`: Unique user identifier
- `email`: User email address
- `name`: User full name
- `institution`: User's institution
- `country`: User's country
- `role`: User role (USER, ADMIN, MODERATOR, VIEWER)
- `created_at`: ISO timestamp when user was created
- `updated_at`: ISO timestamp when user was last updated

#### `generate_mock_status_data()`
Generates mock system status data for the status dashboard.

**Returns:** API response with status data including:
- `executions`: Statistics about executions (total, running, finished, failed)
- `users`: User statistics (total, active in 24h)
- `system`: System metrics (CPU usage, memory usage, uptime, version)
- `last_updated`: ISO timestamp of last update
- `timestamp`: Current timestamp

### Pytest Fixtures

The following fixtures are also available for direct use in tests:

- `mock_executions_data`: Returns default execution data (10 items)
- `mock_scripts_data`: Returns default script data (10 items)
- `mock_users_data`: Returns default user data (10 items)
- `mock_status_data`: Returns system status data

## Usage Examples

### Using Fixtures in Tests

```python
def test_executions_table(mock_executions_data):
    """Test that uses mock execution data."""
    assert len(mock_executions_data["data"]) == 10
    assert mock_executions_data["total"] == 30
```

### Using Functions Directly

```python
def test_custom_data_size():
    """Test with custom data size."""
    executions = generate_mock_executions_data(count=25, page=2, per_page=50)
    assert len(executions["data"]) == 25
    assert executions["page"] == 2
```

### API Route Interception

```python
def test_with_mocked_api(page: Page, live_server):
    """Test with intercepted API calls."""
    
    def handle_executions_route(route: Route):
        mock_data = generate_mock_executions_data(count=20)
        route.fulfill(json=mock_data)
    
    # Intercept API calls and return mock data
    page.route("**/api/v1/executions**", handle_executions_route)
    
    # Navigate to page - executions table will show mock data
    page.goto(live_server)
```

## Data Characteristics

### Realistic Variety
- Multiple different values for each field to test various UI states
- Random but consistent data generation
- Logical relationships (e.g., finished executions have 100% progress)

### API Compatibility
- Matches the exact format expected by the frontend components
- Includes proper pagination metadata
- Uses correct field names and data types

### Test-Friendly
- Deterministic enough for testing but varied enough to catch edge cases
- Configurable count and pagination parameters
- Includes edge cases (running vs finished executions, different roles, etc.)

## Response Format

All table data functions return responses in this format:

```json
{
  "data": [...],           // Array of items
  "total": 50,             // Total number of items (simulated)
  "page": 1,               // Current page number
  "per_page": 50           // Items per page
}
```

Status data returns:

```json
{
  "data": {
    "executions": { "total": 150, "running": 12, ... },
    "users": { "total": 45, "active_24h": 8 },
    "system": { "cpu_usage": 65, "memory_usage": 78, ... },
    "last_updated": "2024-01-01T12:00:00Z",
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

## Testing

The mock data functions are tested in:
- `tests/unit/test_mock_data_generation.py` - Core functionality tests
- `tests/unit/test_playwright_mock_data.py` - Playwright-specific tests
- `tests/playwright/test_mock_data_usage_example.py` - Usage examples

Run tests with:
```bash
poetry run python -m pytest tests/unit/test_mock_data_generation.py -v
poetry run python -m pytest tests/unit/test_playwright_mock_data.py -v
```