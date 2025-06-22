"""Sample test data fixtures."""

from datetime import datetime, timedelta
import json

# Sample user data
SAMPLE_USER = {
    "id": "user_123",
    "name": "Test User",
    "email": "test.user@example.com",
    "institution": "Test University",
    "country": "Test Country",
    "role": "USER",
    "created_date": "2025-06-01T10:00:00Z",
}

SAMPLE_ADMIN = {
    "id": "admin_123",
    "name": "Admin User",
    "email": "admin@example.com",
    "institution": "Admin Institution",
    "country": "Admin Country",
    "role": "ADMIN",
    "created_date": "2025-06-01T09:00:00Z",
}

# Sample script data
SAMPLE_SCRIPT = {
    "id": "script_123",
    "name": "Land Degradation Analysis",
    "description": "Analyze land degradation trends using NDVI data",
    "status": "PUBLISHED",
    "created_date": "2025-06-15T14:30:00Z",
    "updated_date": "2025-06-20T16:45:00Z",
    "author_id": "admin_123",
}

SAMPLE_DRAFT_SCRIPT = {
    "id": "script_456",
    "name": "Water Quality Assessment",
    "description": "Assess water quality changes over time",
    "status": "DRAFT",
    "created_date": "2025-06-18T11:20:00Z",
    "updated_date": "2025-06-21T09:15:00Z",
    "author_id": "admin_123",
}

# Sample execution data
SAMPLE_EXECUTION = {
    "id": "exec_123",
    "script_id": "script_123",
    "user_id": "user_123",
    "status": "RUNNING",
    "progress": 65,
    "start_date": "2025-06-21T08:00:00Z",
    "end_date": None,
    "params": {
        "start_year": 2020,
        "end_year": 2024,
        "geojsons": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
                },
                "properties": {"name": "Test Area 1"},
            }
        ],
    },
    "results": None,
}

SAMPLE_FINISHED_EXECUTION = {
    "id": "exec_456",
    "script_id": "script_123",
    "user_id": "user_123",
    "status": "FINISHED",
    "progress": 100,
    "start_date": "2025-06-20T14:00:00Z",
    "end_date": "2025-06-20T16:30:00Z",
    "params": {
        "start_year": 2019,
        "end_year": 2023,
        "geojsons": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[2, 2], [3, 2], [3, 3], [2, 3], [2, 2]]],
                },
                "properties": {"name": "Test Area 2"},
            }
        ],
    },
    "results": {
        "degradation_percentage": 15.7,
        "total_area_km2": 1250.5,
        "trend": "declining",
        "confidence": 0.85,
    },
}

SAMPLE_FAILED_EXECUTION = {
    "id": "exec_789",
    "script_id": "script_123",
    "user_id": "user_123",
    "status": "FAILED",
    "progress": 30,
    "start_date": "2025-06-19T10:00:00Z",
    "end_date": "2025-06-19T10:45:00Z",
    "params": {"start_year": 2020, "end_year": 2024, "geojsons": []},
    "results": None,
    "error": "Invalid geometry: no areas provided",
}

# Sample log data
SAMPLE_LOGS = [
    {
        "id": "log_001",
        "execution_id": "exec_123",
        "register_date": "2025-06-21T08:00:00Z",
        "level": "INFO",
        "text": "Starting execution of Land Degradation Analysis",
    },
    {
        "id": "log_002",
        "execution_id": "exec_123",
        "register_date": "2025-06-21T08:01:00Z",
        "level": "INFO",
        "text": "Loading satellite data for period 2020-2024",
    },
    {
        "id": "log_003",
        "execution_id": "exec_123",
        "register_date": "2025-06-21T08:05:00Z",
        "level": "DEBUG",
        "text": "Processing 156 satellite images",
    },
    {
        "id": "log_004",
        "execution_id": "exec_123",
        "register_date": "2025-06-21T08:15:00Z",
        "level": "INFO",
        "text": "Calculating NDVI trends for test area",
    },
    {
        "id": "log_005",
        "execution_id": "exec_123",
        "register_date": "2025-06-21T08:30:00Z",
        "level": "WARNING",
        "text": "Cloud coverage >30% in 12 images, using alternative processing",
    },
]

SAMPLE_ERROR_LOGS = [
    {
        "id": "log_101",
        "execution_id": "exec_789",
        "register_date": "2025-06-19T10:00:00Z",
        "level": "INFO",
        "text": "Starting execution",
    },
    {
        "id": "log_102",
        "execution_id": "exec_789",
        "register_date": "2025-06-19T10:01:00Z",
        "level": "ERROR",
        "text": "Validation failed: no geometry provided",
    },
    {
        "id": "log_103",
        "execution_id": "exec_789",
        "register_date": "2025-06-19T10:01:30Z",
        "level": "ERROR",
        "text": "Execution terminated due to invalid input",
    },
]

# Sample GeoJSON data
SAMPLE_GEOJSON_POINT = {
    "type": "Feature",
    "geometry": {
        "type": "Point",
        "coordinates": [12.4924, 41.8902],  # Rome coordinates
    },
    "properties": {"name": "Rome", "country": "Italy"},
}

SAMPLE_GEOJSON_POLYGON = {
    "type": "Feature",
    "geometry": {
        "type": "Polygon",
        "coordinates": [[[12.0, 41.5], [13.0, 41.5], [13.0, 42.0], [12.0, 42.0], [12.0, 41.5]]],
    },
    "properties": {"name": "Test Region", "area_km2": 1250.5},
}

SAMPLE_GEOJSON_COLLECTION = {
    "type": "FeatureCollection",
    "features": [SAMPLE_GEOJSON_POINT, SAMPLE_GEOJSON_POLYGON],
}

# Sample API responses
SAMPLE_API_RESPONSE_SUCCESS = {
    "data": [SAMPLE_EXECUTION, SAMPLE_FINISHED_EXECUTION],
    "total": 2,
    "page": 1,
    "per_page": 50,
}

SAMPLE_API_RESPONSE_EMPTY = {"data": [], "total": 0, "page": 1, "per_page": 50}

SAMPLE_API_ERROR_RESPONSE = {"error": "Unauthorized", "message": "Invalid or expired token"}

# Mock authentication responses
SAMPLE_LOGIN_SUCCESS = {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600,
}

SAMPLE_LOGIN_FAILURE = {"error": "invalid_credentials", "message": "Invalid email or password"}

# Test data collections
SAMPLE_USERS_LIST = [SAMPLE_USER, SAMPLE_ADMIN]
SAMPLE_SCRIPTS_LIST = [SAMPLE_SCRIPT, SAMPLE_DRAFT_SCRIPT]
SAMPLE_EXECUTIONS_LIST = [SAMPLE_EXECUTION, SAMPLE_FINISHED_EXECUTION, SAMPLE_FAILED_EXECUTION]


# Helper functions for test data
def create_execution_with_status(status, execution_id=None):
    """Create a sample execution with specific status."""
    exec_data = SAMPLE_EXECUTION.copy()
    exec_data["status"] = status
    if execution_id:
        exec_data["id"] = execution_id

    if status == "FINISHED":
        exec_data["progress"] = 100
        exec_data["end_date"] = "2025-06-21T10:00:00Z"
        exec_data["results"] = SAMPLE_FINISHED_EXECUTION["results"]
    elif status == "FAILED":
        exec_data["progress"] = 30
        exec_data["end_date"] = "2025-06-21T09:30:00Z"
        exec_data["error"] = "Processing failed"

    return exec_data


def create_user_with_role(role, user_id=None):
    """Create a sample user with specific role."""
    user_data = SAMPLE_USER.copy()
    user_data["role"] = role
    if user_id:
        user_data["id"] = user_id

    if role == "ADMIN":
        user_data.update(
            {"name": "Admin User", "email": "admin@example.com", "institution": "Admin Institution"}
        )

    return user_data


def create_api_response(data, total=None, status_code=200):
    """Create a mock API response."""
    if total is None:
        total = len(data) if isinstance(data, list) else 1

    return {"status_code": status_code, "data": data, "total": total, "page": 1, "per_page": 50}
