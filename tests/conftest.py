"""Test configuration and fixtures for the Trends.Earth API Dashboard."""

from datetime import datetime
import json
import os

# Import the application modules
import sys
from unittest.mock import Mock, patch

import dash
from dash import Dash
import dash_bootstrap_components as dbc
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from trendsearth_ui.callbacks import register_all_callbacks
from trendsearth_ui.components import create_main_layout
from trendsearth_ui.config import API_BASE, APP_TITLE, AUTH_URL


@pytest.fixture
def dash_app():
    """Create a Dash app instance for testing."""
    app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.title = APP_TITLE
    app.layout = create_main_layout()
    register_all_callbacks(app)
    return app


@pytest.fixture
def mock_token():
    """Mock authentication token."""
    return "mock_jwt_token_12345"


@pytest.fixture
def mock_user_data():
    """Mock user data."""
    return {
        "id": "user123",
        "name": "Test User",
        "email": "test@example.com",
        "institution": "Test Institution",
        "country": "Test Country",
        "role": "USER",
    }


@pytest.fixture
def mock_admin_data():
    """Mock admin user data."""
    return {
        "id": "admin123",
        "name": "Admin User",
        "email": "admin@example.com",
        "institution": "Admin Institution",
        "country": "Admin Country",
        "role": "ADMIN",
    }


@pytest.fixture
def mock_execution_data():
    """Mock execution data."""
    return {
        "id": "exec123",
        "script_id": "script123",
        "user_id": "user123",
        "status": "RUNNING",
        "progress": 50,
        "start_date": "2025-06-21T10:00:00Z",
        "end_date": None,
        "params": {
            "geojsons": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
                    },
                    "properties": {},
                }
            ]
        },
        "results": None,
    }


@pytest.fixture
def mock_script_data():
    """Mock script data."""
    return {
        "id": "script123",
        "name": "Test Script",
        "description": "A test script for testing",
        "status": "PUBLISHED",
        "created_date": "2025-06-21T09:00:00Z",
    }


@pytest.fixture
def mock_log_data():
    """Mock log data."""
    return [
        {"register_date": "2025-06-21T10:00:00Z", "level": "INFO", "text": "Starting execution"},
        {"register_date": "2025-06-21T10:01:00Z", "level": "INFO", "text": "Processing data"},
        {"register_date": "2025-06-21T10:02:00Z", "level": "DEBUG", "text": "Debug information"},
    ]


@pytest.fixture
def mock_geojson_data():
    """Mock GeoJSON data for testing map functionality."""
    return {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
        "properties": {"name": "Test Area"},
    }


@pytest.fixture
def mock_api_response():
    """Mock API response structure."""

    def _mock_response(data, total=None, status_code=200):
        response = Mock()
        response.status_code = status_code
        response.json.return_value = {
            "data": data,
            "total": total or (len(data) if isinstance(data, list) else 1),
        }
        response.text = json.dumps({"data": data})
        return response

    return _mock_response


@pytest.fixture
def mock_requests():
    """Mock requests module for API calls."""
    with (
        patch("requests.get") as mock_get,
        patch("requests.post") as mock_post,
        patch("requests.patch") as mock_patch,
        patch("requests.put") as mock_put,
    ):
        yield {"get": mock_get, "post": mock_post, "patch": mock_patch, "put": mock_put}
