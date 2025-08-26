"""Tests for executions duration_raw fix."""

import pytest
from unittest.mock import patch
from trendsearth_ui.callbacks.executions import process_execution_data, format_duration


class TestProcessExecutionData:
    """Test the process_execution_data function."""

    def test_process_execution_data_adds_duration_raw(self):
        """Test that duration_raw is added to execution data."""
        executions = [
            {
                "id": "exec1",
                "script_name": "test_script",
                "duration": 3661,  # 1 hour 1 minute 1 second
                "start_date": "2025-01-01T12:00:00Z",
                "end_date": "2025-01-01T13:01:01Z",
            }
        ]
        
        result = process_execution_data(executions, "USER", "UTC")
        
        # Check that duration_raw was added to original data
        assert executions[0]["duration_raw"] == 3661
        
        # Check that processed data has required fields
        assert len(result) == 1
        assert result[0]["duration"] == "1:01:01"  # Formatted
        assert result[0]["params"] == "Show Params"
        assert result[0]["results"] == "Show Results"
        assert result[0]["logs"] == "Show Logs"
        assert result[0]["map"] == "Show Map"

    def test_process_execution_data_handles_missing_duration(self):
        """Test that missing duration is handled gracefully."""
        executions = [
            {
                "id": "exec1",
                "script_name": "test_script",
                "start_date": "2025-01-01T12:00:00Z",
                # No duration field
            }
        ]
        
        result = process_execution_data(executions, "USER", "UTC")
        
        # Check that duration_raw was not added when duration is missing
        assert "duration_raw" not in executions[0]
        
        # Check that processed data still works
        assert len(result) == 1
        assert result[0]["params"] == "Show Params"

    def test_process_execution_data_handles_null_duration(self):
        """Test that null duration is handled gracefully."""
        executions = [
            {
                "id": "exec1",
                "script_name": "test_script",
                "duration": None,
                "start_date": "2025-01-01T12:00:00Z",
            }
        ]
        
        result = process_execution_data(executions, "USER", "UTC")
        
        # Check that duration_raw was not added when duration is None
        assert "duration_raw" not in executions[0]
        
        # Check that processed data still works
        assert len(result) == 1
        assert result[0]["duration"] == "-"  # Formatted as dash

    def test_process_execution_data_admin_fields(self):
        """Test that admin users get docker_logs field."""
        executions = [
            {
                "id": "exec1",
                "script_name": "test_script",
                "duration": 60,
            }
        ]
        
        # Test admin user
        result_admin = process_execution_data(executions, "ADMIN", "UTC")
        assert "docker_logs" in result_admin[0]
        assert result_admin[0]["docker_logs"] == "Show Docker Logs"
        
        # Test regular user
        result_user = process_execution_data(executions, "USER", "UTC")
        assert "docker_logs" not in result_user[0]

    def test_process_execution_data_preserves_other_fields(self):
        """Test that other fields are preserved in processed data."""
        executions = [
            {
                "id": "exec1",
                "script_name": "test_script", 
                "status": "SUCCESS",
                "user_id": "user123",
                "custom_field": "custom_value",
                "duration": 120,
            }
        ]
        
        result = process_execution_data(executions, "USER", "UTC")
        
        assert result[0]["id"] == "exec1"
        assert result[0]["script_name"] == "test_script"
        assert result[0]["status"] == "SUCCESS"
        assert result[0]["user_id"] == "user123"
        assert result[0]["custom_field"] == "custom_value"


class TestFormatDuration:
    """Test the format_duration function."""

    def test_format_duration_normal_cases(self):
        """Test normal duration formatting."""
        assert format_duration(0) == "-"
        assert format_duration(None) == "-"
        assert format_duration(59) == "0:00:59"
        assert format_duration(60) == "0:01:00"
        assert format_duration(3600) == "1:00:00"
        assert format_duration(3661) == "1:01:01"
        assert format_duration(7200) == "2:00:00"

    def test_format_duration_string_input(self):
        """Test duration formatting with string input."""
        assert format_duration("3600") == "1:00:00"
        assert format_duration("3661.5") == "1:01:01"

    def test_format_duration_invalid_input(self):
        """Test duration formatting with invalid input."""
        assert format_duration("invalid") == "-"
        assert format_duration([]) == "-"
        assert format_duration({}) == "-"