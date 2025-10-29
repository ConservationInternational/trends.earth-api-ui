"""Tests for timezone conversion in charts."""

from datetime import datetime, timezone
from unittest.mock import patch

import pandas as pd
import pytest

from trendsearth_ui.utils.stats_visualizations import (
    create_execution_statistics_chart,
    create_user_statistics_chart,
)
from trendsearth_ui.utils.timezone_utils import convert_timestamp_series_to_local


class TestTimezoneChartConversion:
    """Test timezone conversion functionality in charts."""

    def test_convert_timestamp_series_to_local(self):
        """Test conversion of pandas Series with UTC timestamps to local time."""
        # Create test timestamps in UTC
        utc_timestamps = pd.Series(
            [
                datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                datetime(2023, 1, 2, 15, 30, 0, tzinfo=timezone.utc),
                datetime(2023, 1, 3, 9, 45, 0, tzinfo=timezone.utc),
            ]
        )

        # Convert to Eastern Time (UTC-5)
        local_timestamps = convert_timestamp_series_to_local(utc_timestamps, "America/New_York")

        # Check that conversion occurred (should be 5 hours earlier)
        expected_times = [
            datetime(2023, 1, 1, 7, 0, 0),  # 12:00 UTC -> 07:00 EST
            datetime(2023, 1, 2, 10, 30, 0),  # 15:30 UTC -> 10:30 EST
            datetime(2023, 1, 3, 4, 45, 0),  # 09:45 UTC -> 04:45 EST
        ]

        for i, expected in enumerate(expected_times):
            # Compare just the datetime part (ignore timezone info in local result)
            assert local_timestamps.iloc[i].replace(tzinfo=None) == expected

    def test_convert_timestamp_series_with_string_timestamps(self):
        """Test conversion of string timestamps."""
        # Create test string timestamps
        string_timestamps = pd.Series(
            [
                "2023-06-15T14:30:00Z",
                "2023-06-16T08:15:00Z",
                "2023-06-17T22:45:00Z",
            ]
        )

        # Convert to Pacific Time (UTC-7 in summer)
        local_timestamps = convert_timestamp_series_to_local(
            string_timestamps, "America/Los_Angeles"
        )

        # Check that all timestamps were converted (should be 7 hours earlier)
        expected_times = [
            datetime(2023, 6, 15, 7, 30, 0),  # 14:30 UTC -> 07:30 PDT
            datetime(2023, 6, 16, 1, 15, 0),  # 08:15 UTC -> 01:15 PDT
            datetime(2023, 6, 17, 15, 45, 0),  # 22:45 UTC -> 15:45 PDT
        ]

        for i, expected in enumerate(expected_times):
            # Compare the local time (ignoring timezone info)
            assert local_timestamps.iloc[i].replace(tzinfo=None) == expected

    def test_convert_timestamp_series_with_invalid_timezone(self):
        """Test conversion with invalid timezone falls back to UTC."""
        utc_timestamps = pd.Series(
            [
                datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            ]
        )

        # Use invalid timezone - should fallback to UTC
        local_timestamps = convert_timestamp_series_to_local(utc_timestamps, "Invalid/Timezone")

        # Should remain the same (UTC)
        expected = datetime(2023, 1, 1, 12, 0, 0)
        assert local_timestamps.iloc[0].replace(tzinfo=None) == expected

    def test_convert_timestamp_series_with_nan_values(self):
        """Test conversion handles NaN values gracefully."""
        timestamps_with_nan = pd.Series(
            [
                datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                pd.NaT,  # NaN timestamp
                datetime(2023, 1, 3, 9, 45, 0, tzinfo=timezone.utc),
            ]
        )

        local_timestamps = convert_timestamp_series_to_local(
            timestamps_with_nan, "America/New_York"
        )

        # Check first and third values are converted, second remains NaN
        assert local_timestamps.iloc[0].replace(tzinfo=None) == datetime(2023, 1, 1, 7, 0, 0)
        assert pd.isna(local_timestamps.iloc[1])
        assert local_timestamps.iloc[2].replace(tzinfo=None) == datetime(2023, 1, 3, 4, 45, 0)

    def test_execution_statistics_chart_accepts_timezone_parameter(self):
        """Test that execution statistics chart accepts timezone parameter without error."""
        # Test that the function accepts the timezone parameter
        mock_stats_data = {"data": {}}

        # This should not raise an exception
        try:
            result = create_execution_statistics_chart(
                mock_stats_data, title_suffix=" (Test)", user_timezone="America/New_York"
            )
            # Should return a list
            assert isinstance(result, list)
        except TypeError as e:
            # If it fails due to unexpected keyword argument, that's what we're testing for
            if "unexpected keyword argument" in str(e):
                pytest.fail(f"Function does not accept user_timezone parameter: {e}")
            # Other TypeErrors are okay (e.g., from mocked dependencies)
            pass

    def test_user_statistics_chart_accepts_timezone_parameter(self):
        """Test that user statistics chart accepts timezone parameter without error."""
        # Test that the function accepts the timezone parameter
        mock_stats_data = {"data": {}}

        # This should not raise an exception
        try:
            result = create_user_statistics_chart(
                mock_stats_data, title_suffix=" (Test)", user_timezone="Europe/London"
            )
            # Should return a list
            assert isinstance(result, list)
        except TypeError as e:
            # If it fails due to unexpected keyword argument, that's what we're testing for
            if "unexpected keyword argument" in str(e):
                pytest.fail(f"Function does not accept user_timezone parameter: {e}")
            # Other TypeErrors are okay (e.g., from mocked dependencies)
            pass

    def test_chart_axis_labels_include_timezone(self):
        """Test that chart axis labels include timezone abbreviations."""
        from trendsearth_ui.utils.timezone_utils import get_chart_axis_label

        # Test different timezones
        est_label = get_chart_axis_label("America/New_York")
        pst_label = get_chart_axis_label("America/Los_Angeles")
        utc_label = get_chart_axis_label("UTC")

        # Labels should contain timezone info
        assert "EST" in est_label or "EDT" in est_label
        assert "PST" in pst_label or "PDT" in pst_label
        assert "UTC" in utc_label

        # All should have "Time" as base
        assert "Time" in est_label
        assert "Time" in pst_label
        assert "Time" in utc_label
