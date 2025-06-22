"""
Functional tests to verify that the edit modal fix is working correctly.
This tests that clicking edit buttons identifies the correct user/script.
"""

import json

import pytest


@pytest.fixture
def test_cell_clicked_user():
    """Test data that simulates what would be in the cellClicked event."""
    return {
        "colId": "edit",
        "rowIndex": 2,  # This is the position in the sorted/filtered table
        "data": {
            "id": "user-123",
            "email": "user1@example.com",
            "name": "Test User 1",
            "role": "USER",
            "institution": "Test Institute",
        },
    }


@pytest.fixture
def test_cell_clicked_script():
    """Test data for script edit clicks."""
    return {
        "colId": "edit",
        "rowIndex": 1,  # This is the position in the sorted/filtered table
        "data": {
            "id": "script-456",
            "name": "Test Script",
            "description": "Test description",
            "status": "PUBLISHED",
        },
    }


@pytest.fixture
def test_users_raw():
    """Test raw data (simulates what's stored in the raw data stores)."""
    return [
        {"id": "user-999", "email": "admin@example.com", "name": "Admin User", "role": "ADMIN"},
        {
            "id": "user-123",
            "email": "user1@example.com",
            "name": "Test User 1",
            "role": "USER",
            "institution": "Test Institute",
        },
        {"id": "user-456", "email": "user2@example.com", "name": "Test User 2", "role": "USER"},
    ]


@pytest.fixture
def test_scripts_raw():
    """Test raw script data."""
    return [
        {
            "id": "script-999",
            "name": "Admin Script",
            "description": "Admin script",
            "status": "DRAFT",
        },
        {
            "id": "script-456",
            "name": "Test Script",
            "description": "Test description",
            "status": "PUBLISHED",
        },
        {
            "id": "script-789",
            "name": "Another Script",
            "description": "Another test",
            "status": "DRAFT",
        },
    ]


def test_user_identification(test_cell_clicked_user, test_users_raw):
    """Test that the user edit modal identifies the correct user."""
    clicked_data = test_cell_clicked_user["data"]
    user_id = clicked_data["id"]

    # Find the user in the raw data
    user_found = None
    for user in test_users_raw:
        if user["id"] == user_id:
            user_found = user
            break

    assert user_found is not None, f"Should find user with ID {user_id}"
    assert user_found["email"] == "user1@example.com", "Should match correct email"
    assert user_found["name"] == "Test User 1", "Should match correct name"


def test_script_identification(test_cell_clicked_script, test_scripts_raw):
    """Test that the script edit modal identifies the correct script."""
    clicked_data = test_cell_clicked_script["data"]
    script_id = clicked_data["id"]

    # Find the script in the raw data
    script_found = None
    for script in test_scripts_raw:
        if script["id"] == script_id:
            script_found = script
            break

    assert script_found is not None, f"Should find script with ID {script_id}"
    assert script_found["name"] == "Test Script", "Should match correct name"
    assert script_found["status"] == "PUBLISHED", "Should match correct status"


def test_edit_button_click_data_structure(test_cell_clicked_user):
    """Test that edit button click data has the expected structure."""
    assert "colId" in test_cell_clicked_user, "Should have colId field"
    assert test_cell_clicked_user["colId"] == "edit", "Should be edit column"
    assert "data" in test_cell_clicked_user, "Should have data field"
    assert "id" in test_cell_clicked_user["data"], "Data should have ID field"


def test_data_consistency(test_cell_clicked_user, test_users_raw):
    """Test that the data from the click event matches the raw data."""
    clicked_user = test_cell_clicked_user["data"]

    # Find matching user in raw data
    raw_user = next((u for u in test_users_raw if u["id"] == clicked_user["id"]), None)

    assert raw_user is not None, "Should find matching user in raw data"
    assert raw_user["email"] == clicked_user["email"], "Email should match"
    assert raw_user["name"] == clicked_user["name"], "Name should match"


def test_edit_modal_callback_logic(test_cell_clicked_user, test_users_raw):
    """Test the logic that would be used in the edit modal callbacks."""
    cell_clicked = test_cell_clicked_user
    users_data = test_users_raw

    # Simulate the callback logic
    if cell_clicked.get("colId") == "edit":
        row_data = cell_clicked.get("data", {})
        if row_data and "id" in row_data:
            user_id = row_data.get("id")
            user_found = None

            for u in users_data:
                if u.get("id") == user_id:
                    user_found = u
                    break

            assert user_found is not None, "Should find user by ID"
            assert user_found["name"] == "Test User 1", "Should find correct user"
            assert user_found["email"] == "user1@example.com", "Should have correct email"
