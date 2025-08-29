"""Unit tests for duration formatting in mobile utils."""

import pytest

from trendsearth_ui.utils.mobile_utils import get_mobile_column_config


class TestDurationFormatting:
    """Test duration column formatting configuration."""

    def test_duration_column_exists(self):
        """Test that duration column exists in executions configuration."""
        config = get_mobile_column_config()
        executions_config = config.get("executions", {})
        primary_columns = executions_config.get("primary_columns", [])

        # Find duration column
        duration_column = None
        for col in primary_columns:
            if col.get("headerName") == "Duration":
                duration_column = col
                break

        assert duration_column is not None, (
            "Duration column should exist in executions primary columns"
        )

    def test_duration_column_has_value_getter(self):
        """Test that duration column has valueGetter for duration_raw."""
        config = get_mobile_column_config()
        executions_config = config.get("executions", {})
        primary_columns = executions_config.get("primary_columns", [])

        # Find duration column
        duration_column = None
        for col in primary_columns:
            if col.get("headerName") == "Duration":
                duration_column = col
                break

        assert duration_column is not None
        assert "valueGetter" in duration_column, "Duration column should have valueGetter"

        value_getter = duration_column["valueGetter"]
        assert "function" in value_getter, "valueGetter should have function property"
        assert "duration_raw" in value_getter["function"], (
            "valueGetter should reference duration_raw"
        )

    def test_duration_column_has_value_formatter(self):
        """Test that duration column has valueFormatter for time formatting."""
        config = get_mobile_column_config()
        executions_config = config.get("executions", {})
        primary_columns = executions_config.get("primary_columns", [])

        # Find duration column
        duration_column = None
        for col in primary_columns:
            if col.get("headerName") == "Duration":
                duration_column = col
                break

        assert duration_column is not None
        assert "valueFormatter" in duration_column, "Duration column should have valueFormatter"

        value_formatter = duration_column["valueFormatter"]
        assert isinstance(value_formatter, dict), "valueFormatter should be a dict with function"
        assert "function" in value_formatter, "valueFormatter should have function key"

        formatter_function = value_formatter["function"]
        assert isinstance(formatter_function, str), "valueFormatter function should be a string"
        assert "Math.floor" in formatter_function, (
            "valueFormatter should have Math.floor for seconds calculation"
        )
        assert "3600" in formatter_function, "valueFormatter should handle hours (3600 seconds)"
        assert "60" in formatter_function, "valueFormatter should handle minutes (60 seconds)"

    def test_value_formatter_format_structure(self):
        """Test that valueFormatter has the correct structure for time formatting."""
        config = get_mobile_column_config()
        executions_config = config.get("executions", {})
        primary_columns = executions_config.get("primary_columns", [])

        # Find duration column
        duration_column = None
        for col in primary_columns:
            if col.get("headerName") == "Duration":
                duration_column = col
                break

        value_formatter = duration_column["valueFormatter"]["function"]

        # Check for time formatting logic
        assert "hours" in value_formatter, "Should calculate hours"
        assert "minutes" in value_formatter, "Should calculate minutes"
        assert "seconds" in value_formatter, "Should calculate seconds"
        assert ":" in value_formatter, "Should use colon separator for time format"

    def test_duration_column_basic_properties(self):
        """Test basic properties of duration column."""
        config = get_mobile_column_config()
        executions_config = config.get("executions", {})
        primary_columns = executions_config.get("primary_columns", [])

        # Find duration column
        duration_column = None
        for col in primary_columns:
            if col.get("headerName") == "Duration":
                duration_column = col
                break

        assert duration_column is not None
        assert duration_column["field"] == "duration"
        assert duration_column["headerName"] == "Duration"
        assert "flex" in duration_column
        assert "minWidth" in duration_column
        assert duration_column["resizable"] is True


class TestDurationFormatterLogic:
    """Test the JavaScript duration formatter logic by simulating it in Python."""

    def format_duration_python(self, total_seconds):
        """Python implementation of the JavaScript duration formatter for testing."""
        if not total_seconds or total_seconds == 0:
            return "-"

        total_seconds = int(total_seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"

    def test_zero_duration(self):
        """Test formatting of zero duration."""
        result = self.format_duration_python(0)
        assert result == "-"

    def test_none_duration(self):
        """Test formatting of None duration."""
        result = self.format_duration_python(None)
        assert result == "-"

    def test_seconds_only(self):
        """Test formatting of durations under 1 minute."""
        result = self.format_duration_python(45)
        assert result == "0:45"

    def test_minutes_and_seconds(self):
        """Test formatting of durations under 1 hour."""
        result = self.format_duration_python(125)  # 2 minutes 5 seconds
        assert result == "2:05"

        result = self.format_duration_python(3599)  # 59 minutes 59 seconds
        assert result == "59:59"

    def test_hours_minutes_seconds(self):
        """Test formatting of durations over 1 hour."""
        result = self.format_duration_python(3661)  # 1 hour 1 minute 1 second
        assert result == "1:01:01"

        result = self.format_duration_python(7323)  # 2 hours 2 minutes 3 seconds
        assert result == "2:02:03"

    def test_exact_hour(self):
        """Test formatting of exact hour durations."""
        result = self.format_duration_python(3600)  # 1 hour exactly
        assert result == "1:00:00"

        result = self.format_duration_python(7200)  # 2 hours exactly
        assert result == "2:00:00"

    def test_large_durations(self):
        """Test formatting of large durations."""
        result = self.format_duration_python(36061)  # 10 hours 1 minute 1 second
        assert result == "10:01:01"

        result = self.format_duration_python(90061)  # 25 hours 1 minute 1 second
        assert result == "25:01:01"

    def test_floating_point_seconds(self):
        """Test formatting of floating point durations (should be floored)."""
        result = self.format_duration_python(125.7)  # 2 minutes 5.7 seconds -> 2:05
        assert result == "2:05"

        result = self.format_duration_python(3661.9)  # 1 hour 1 minute 1.9 seconds -> 1:01:01
        assert result == "1:01:01"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
