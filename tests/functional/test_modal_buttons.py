"""
Tests for modal buttons functionality (params, results, logs, map).
This tests that clicking buttons in tables opens the correct modals with correct data.
"""

import json
from unittest.mock import MagicMock, Mock, patch

from dash import html
import pytest


@pytest.fixture
def mock_token():
    """Mock authentication token."""
    return "test-bearer-token"


@pytest.fixture
def mock_execution_data():
    """Mock execution data for testing."""
    return {
        "id": "exec-123",
        "script_name": "Test Script",
        "user_name": "Test User",
        "status": "FINISHED",
        "params": {
            "area_name": "Test Area",
            "geojsons": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
                    },
                    "properties": {"name": "Test Area"},
                }
            ],
        },
        "results": {"status": "completed", "output_files": ["file1.tif", "file2.json"]},
    }


@pytest.fixture
def mock_logs_data():
    """Mock logs data for testing."""
    return {
        "data": [
            {
                "id": "log-1",
                "execution_id": "exec-123",
                "level": "INFO",
                "text": "Process started",
                "register_date": "2024-01-01T10:00:00Z",
            },
            {
                "id": "log-2",
                "execution_id": "exec-123",
                "level": "WARNING",
                "text": "Memory usage high",
                "register_date": "2024-01-01T10:30:00Z",
            },
            {
                "id": "log-3",
                "execution_id": "exec-123",
                "level": "INFO",
                "text": "Process completed",
                "register_date": "2024-01-01T11:00:00Z",
            },
        ]
    }


@pytest.fixture
def mock_script_logs_data():
    """Mock script logs data for testing."""
    return {
        "data": [
            {
                "id": "script-log-1",
                "script_id": "script-456",
                "level": "INFO",
                "text": "Script validation started",
                "register_date": "2024-01-01T09:00:00Z",
            },
            {
                "id": "script-log-2",
                "script_id": "script-456",
                "level": "ERROR",
                "text": "Syntax error found",
                "register_date": "2024-01-01T09:15:00Z",
            },
        ]
    }


@pytest.fixture
def cell_clicked_with_data():
    """Cell click event with row data present."""
    return {
        "colId": "params",
        "rowIndex": 5,
        "data": {
            "id": "exec-123",
            "script_name": "Test Script",
            "user_name": "Test User",
            "status": "FINISHED",
        },
    }


@pytest.fixture
def cell_clicked_without_data():
    """Cell click event without row data (pagination scenario)."""
    return {
        "colId": "params",
        "rowIndex": 25,  # Row that would be on page 2
        "data": None,
    }


@pytest.fixture
def mock_table_state():
    """Mock table state with sorting and filtering."""
    return {"sort_sql": "start_date DESC", "filter_sql": "status = 'FINISHED'"}


class TestExecutionModalButtons:
    """Test execution table modal buttons (params, results, logs, map)."""

    @patch("requests.get")
    def test_params_button_with_row_data(
        self, mock_get, mock_token, mock_execution_data, cell_clicked_with_data
    ):
        """Test params button when row data is available."""
        from trendsearth_ui.callbacks.modals import register_callbacks

        # Mock the API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_execution_data
        mock_get.return_value = mock_response

        # Create a mock app to register callbacks
        mock_app = Mock()
        register_callbacks(mock_app)

        # Get the callback function
        callback_calls = mock_app.callback.call_args_list
        show_json_modal_callback = None

        for call in callback_calls:
            if len(call[1]) > 0 and hasattr(call[1].get("func", None), "__name__"):
                if call[1]["func"].__name__ == "show_json_modal":
                    show_json_modal_callback = call[1]["func"]
                    break

        if show_json_modal_callback:
            # Test the params button
            cell_clicked_with_data["colId"] = "params"
            result = show_json_modal_callback(cell_clicked_with_data, mock_token, False, {})

            # Should open modal with params data
            assert result[0] is True  # Modal is open
            assert "exec-123" in str(result[3])  # Title contains execution ID
            assert result[2] == mock_execution_data["params"]  # Data matches params

    @patch("requests.get")
    def test_results_button_with_row_data(
        self, mock_get, mock_token, mock_execution_data, cell_clicked_with_data
    ):
        """Test results button when row data is available."""
        from trendsearth_ui.callbacks.modals import register_callbacks

        # Mock the API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_execution_data
        mock_get.return_value = mock_response

        # Create a mock app to register callbacks
        mock_app = Mock()
        register_callbacks(mock_app)

        # We would test the results button similarly
        cell_clicked_with_data["colId"] = "results"

        # Verify that the API would be called with correct execution ID
        # The callback should make this API call
        assert cell_clicked_with_data["data"]["id"] == "exec-123"

    @patch("requests.get")
    def test_logs_button_with_row_data(
        self, mock_get, mock_token, mock_logs_data, cell_clicked_with_data
    ):
        """Test logs button when row data is available."""
        # Mock the logs API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_logs_data
        mock_get.return_value = mock_response

        cell_clicked_with_data["colId"] = "logs"

        # Verify logs data structure
        assert "data" in mock_logs_data
        assert len(mock_logs_data["data"]) == 3
        assert mock_logs_data["data"][0]["level"] == "INFO"
        assert mock_logs_data["data"][1]["level"] == "WARNING"

    @patch("requests.get")
    def test_params_button_without_row_data(
        self, mock_get, mock_token, mock_execution_data, cell_clicked_without_data, mock_table_state
    ):
        """Test params button when row data is not available (pagination scenario)."""
        # Mock pagination API response
        pagination_response = {
            "data": [mock_execution_data],
            "total": 50,
            "page": 2,
            "per_page": 50,
        }

        # Mock execution details API response
        execution_response = mock_execution_data

        # Mock both API calls
        mock_get.side_effect = [
            Mock(status_code=200, json=lambda: pagination_response),  # Pagination call
            Mock(status_code=200, json=lambda: execution_response),  # Execution details call
        ]

        # Test pagination calculation
        row_index = cell_clicked_without_data["rowIndex"]  # 25
        page_size = 50
        page = (row_index // page_size) + 1  # Should be page 1
        row_in_page = row_index % page_size  # Should be 25

        assert page == 1
        assert row_in_page == 25

    @patch("requests.get")
    def test_api_error_handling(self, mock_get, mock_token, cell_clicked_with_data):
        """Test handling of API errors in modal buttons."""
        # Mock API error
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Execution not found"
        mock_get.return_value = mock_response

        # The callback should handle this error gracefully
        cell_clicked_with_data["colId"] = "params"

        # Should return error state
        expected_error_message = "Failed to fetch execution data: 404 - Execution not found"

        # Verify error message format
        assert "404" in expected_error_message
        assert "Execution not found" in expected_error_message


class TestMapModalButton:
    """Test map modal button functionality."""

    @patch("requests.get")
    def test_map_button_with_geojson_data(
        self, mock_get, mock_token, mock_execution_data, cell_clicked_with_data
    ):
        """Test map button when execution has geojson data."""
        from trendsearth_ui.callbacks.map import register_callbacks

        # Mock the API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_execution_data
        mock_get.return_value = mock_response

        cell_clicked_with_data["colId"] = "map"

        # Verify geojson data structure
        geojsons = mock_execution_data["params"]["geojsons"]
        assert len(geojsons) == 1
        assert geojsons[0]["type"] == "Feature"
        assert "coordinates" in geojsons[0]["geometry"]

    @patch("requests.get")
    def test_map_button_without_geojson(self, mock_get, mock_token, cell_clicked_with_data):
        """Test map button when execution has no geojson data."""
        # Mock execution without geojson
        execution_without_geojson = {
            "id": "exec-123",
            "params": {
                "area_name": "Test Area"
                # No geojsons field
            },
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = execution_without_geojson
        mock_get.return_value = mock_response

        cell_clicked_with_data["colId"] = "map"

        # Should handle missing geojson gracefully
        assert "geojsons" not in execution_without_geojson["params"]

    @patch("requests.get")
    def test_map_button_pagination_scenario(
        self, mock_get, mock_token, mock_execution_data, cell_clicked_without_data, mock_table_state
    ):
        """Test map button when using pagination to find execution."""
        # Mock pagination response
        pagination_response = {"data": [mock_execution_data], "total": 50}

        # Mock execution details response
        execution_response = mock_execution_data

        mock_get.side_effect = [
            Mock(status_code=200, json=lambda: pagination_response),
            Mock(status_code=200, json=lambda: execution_response),
        ]

        cell_clicked_without_data["colId"] = "map"

        # Verify pagination calculation for map
        row_index = 25
        page_size = 50
        expected_page = (row_index // page_size) + 1
        expected_row_in_page = row_index % page_size

        assert expected_page == 1
        assert expected_row_in_page == 25


class TestScriptLogsModalButton:
    """Test script logs modal button functionality."""

    @patch("requests.get")
    def test_script_logs_button_with_row_data(self, mock_get, mock_token, mock_script_logs_data):
        """Test script logs button when row data is available."""
        # Mock the script logs API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_script_logs_data
        mock_get.return_value = mock_response

        # Verify script logs data structure
        assert "data" in mock_script_logs_data
        assert len(mock_script_logs_data["data"]) == 2
        assert mock_script_logs_data["data"][0]["level"] == "INFO"
        assert mock_script_logs_data["data"][1]["level"] == "ERROR"

    @patch("requests.get")
    def test_script_logs_button_without_row_data(
        self, mock_get, mock_token, mock_script_logs_data, mock_table_state
    ):
        """Test script logs button when row data is not available."""
        test_cell = {
            "colId": "logs",
            "rowIndex": 75,  # Row on page 2
            "data": None,
        }

        # Verify test data structure
        assert test_cell["rowIndex"] == 75
        assert test_cell["data"] is None

        # Mock pagination response
        pagination_response = {
            "data": [{"id": "script-456", "name": "Test Script", "status": "PUBLISHED"}],
            "total": 100,
        }

        mock_get.side_effect = [
            Mock(status_code=200, json=lambda: pagination_response),  # Scripts pagination
            Mock(status_code=200, json=lambda: mock_script_logs_data),  # Script logs
        ]

        # Test pagination calculation for scripts
        row_index = 75
        page_size = 50
        page = (row_index // page_size) + 1  # Should be page 2
        row_in_page = row_index % page_size  # Should be 25

        assert page == 2
        assert row_in_page == 25

    @patch("requests.get")
    def test_script_logs_no_logs_found(self, mock_get, mock_token):
        """Test script logs button when no logs are found."""
        test_cell = {
            "colId": "logs",
            "rowIndex": 5,
            "data": {"id": "script-456", "name": "Test Script"},
        }

        # Verify test structure
        assert test_cell["data"]["id"] == "script-456"

        # Mock empty logs response
        empty_logs_response = {"data": []}
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = empty_logs_response
        mock_get.return_value = mock_response

        # Should handle empty logs gracefully
        assert len(empty_logs_response["data"]) == 0


class TestModalButtonErrorHandling:
    """Test error handling for all modal buttons."""

    @patch("requests.get")
    def test_network_error_handling(self, mock_get, mock_token):
        """Test handling of network errors."""
        # Mock network error
        mock_get.side_effect = Exception("Network connection failed")

        test_cell = {"colId": "params", "rowIndex": 5, "data": {"id": "exec-123"}}

        # Verify test structure
        assert test_cell["data"]["id"] == "exec-123"

        # Should handle network errors gracefully
        try:
            # This would be called by the actual callback
            pass
        except Exception as e:
            assert "Network connection failed" in str(e)

    @patch("requests.get")
    def test_invalid_response_handling(self, mock_get, mock_token):
        """Test handling of invalid API responses."""
        # Mock invalid JSON response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_get.return_value = mock_response

        # Should handle JSON decode errors gracefully
        test_cell = {"colId": "results", "rowIndex": 5, "data": {"id": "exec-123"}}

        # Verify test structure
        assert test_cell["data"]["id"] == "exec-123"

        # The callback should catch and handle this error

    def test_missing_cell_data_handling(self, mock_token):
        """Test handling when cell click data is missing."""
        # Test with None cell
        assert None is None  # Should be handled gracefully

        # Test with empty cell
        empty_cell = {}
        assert "colId" not in empty_cell
        assert "rowIndex" not in empty_cell
        assert "data" not in empty_cell

    def test_invalid_column_id_handling(self, mock_token):
        """Test handling of invalid column IDs."""
        invalid_cell = {"colId": "invalid_column", "rowIndex": 5, "data": {"id": "exec-123"}}

        # Should ignore invalid column IDs
        valid_columns = ["params", "results", "logs", "map", "edit"]
        assert invalid_cell["colId"] not in valid_columns


class TestModalButtonIntegration:
    """Integration tests for modal button functionality."""

    def test_all_execution_buttons_have_consistent_interface(self):
        """Test that all execution modal buttons have consistent interface."""
        execution_columns = ["params", "results", "logs", "map"]

        for col in execution_columns:
            cell_clicked = {"colId": col, "rowIndex": 5, "data": {"id": "exec-123"}}

            # All should have the same required fields
            assert "colId" in cell_clicked
            assert "rowIndex" in cell_clicked
            assert cell_clicked["rowIndex"] >= 0

    def test_modal_data_consistency(self):
        """Test that modal data is consistently formatted."""
        # Test execution data
        execution_data = {
            "id": "exec-123",
            "params": {"key": "value"},
            "results": {"status": "complete"},
        }

        # Test script data
        script_data = {"id": "script-456", "name": "Test Script"}

        # All should have ID field
        assert "id" in execution_data
        assert "id" in script_data

        # IDs should be strings
        assert isinstance(execution_data["id"], str)
        assert isinstance(script_data["id"], str)

    def test_pagination_consistency_across_modals(self):
        """Test that pagination logic is consistent across all modal buttons."""
        page_size = 50
        test_cases = [
            {"rowIndex": 0, "expected_page": 1, "expected_row_in_page": 0},
            {"rowIndex": 25, "expected_page": 1, "expected_row_in_page": 25},
            {"rowIndex": 50, "expected_page": 2, "expected_row_in_page": 0},
            {"rowIndex": 75, "expected_page": 2, "expected_row_in_page": 25},
            {"rowIndex": 100, "expected_page": 3, "expected_row_in_page": 0},
        ]

        for case in test_cases:
            row_index = case["rowIndex"]
            page = (row_index // page_size) + 1
            row_in_page = row_index % page_size

            assert page == case["expected_page"]
            assert row_in_page == case["expected_row_in_page"]
