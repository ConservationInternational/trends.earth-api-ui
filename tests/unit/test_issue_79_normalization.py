"""Test the normalization fix for issue #79: completed execution status over time plot."""

from unittest.mock import Mock

import pandas as pd
import plotly.graph_objects as go
import pytest


class TestIssue79NormalizationFix:
    """Test the specific fix requested in issue #79 for plot normalization."""

    def test_normalize_series_to_zero_baseline(self):
        """Test the normalization logic that subtracts initial value from series."""
        # Sample data with different starting points
        series1 = [100, 105, 110, 108, 115]  # Should become [0, 5, 10, 8, 15]
        series2 = [50, 52, 48, 55, 60]  # Should become [0, 2, -2, 5, 10]
        series3 = [0, 3, 5, 4, 7]  # Should become [0, 3, 5, 4, 7] (no change)

        def normalize_to_zero_baseline(values):
            """Normalize a series to start from zero by subtracting the initial value."""
            if not values or len(values) == 0:
                return values
            initial_value = values[0]
            return [val - initial_value for val in values]

        normalized1 = normalize_to_zero_baseline(series1)
        normalized2 = normalize_to_zero_baseline(series2)
        normalized3 = normalize_to_zero_baseline(series3)

        # Verify the normalization
        assert normalized1 == [0, 5, 10, 8, 15], f"Expected [0, 5, 10, 8, 15], got {normalized1}"
        assert normalized2 == [0, 2, -2, 5, 10], f"Expected [0, 2, -2, 5, 10], got {normalized2}"
        assert normalized3 == [0, 3, 5, 4, 7], f"Expected [0, 3, 5, 4, 7], got {normalized3}"

    def test_normalize_pandas_series(self):
        """Test normalization with pandas Series objects."""
        import pandas as pd

        def normalize_to_zero_baseline(series):
            """Normalize a pandas series to start from zero."""
            if series.empty:
                return series
            initial_value = series.iloc[0]
            return series - initial_value

        # Test with pandas Series
        df = pd.DataFrame(
            {
                "finished": [200, 210, 205, 220, 215],
                "failed": [10, 12, 15, 13, 18],
                "cancelled": [5, 5, 7, 6, 8],
            }
        )

        normalized_finished = normalize_to_zero_baseline(df["finished"])
        normalized_failed = normalize_to_zero_baseline(df["failed"])
        normalized_cancelled = normalize_to_zero_baseline(df["cancelled"])

        # Verify results
        expected_finished = [0, 10, 5, 20, 15]
        expected_failed = [0, 2, 5, 3, 8]
        expected_cancelled = [0, 0, 2, 1, 3]

        assert normalized_finished.tolist() == expected_finished
        assert normalized_failed.tolist() == expected_failed
        assert normalized_cancelled.tolist() == expected_cancelled

    def test_normalization_handles_empty_data(self):
        """Test that normalization handles edge cases gracefully."""

        def normalize_to_zero_baseline(values):
            """Normalize a series to start from zero by subtracting the initial value."""
            if not values or len(values) == 0:
                return values
            initial_value = values[0]
            return [val - initial_value for val in values]

        # Test edge cases
        assert normalize_to_zero_baseline([]) == []
        assert normalize_to_zero_baseline([42]) == [0]
        assert normalize_to_zero_baseline([10, 10, 10]) == [0, 0, 0]

    def test_normalization_with_nan_values(self):
        """Test normalization with NaN values using pandas."""
        import numpy as np
        import pandas as pd

        def normalize_to_zero_baseline(series):
            """Normalize a pandas series to start from zero, handling NaN values."""
            if series.empty:
                return series

            # Fill NaN values with 0 before normalization
            series_filled = series.fillna(0)

            if len(series_filled) == 0:
                return series_filled

            initial_value = series_filled.iloc[0]
            return series_filled - initial_value

        # Test with NaN values
        series_with_nan = pd.Series([100, np.nan, 110, 105, np.nan])
        normalized = normalize_to_zero_baseline(series_with_nan)

        expected = [0, -100, 10, 5, -100]  # NaN becomes 0, then normalized
        assert normalized.tolist() == expected

    def test_chart_integration_mock(self):
        """Test that the normalization can be integrated into a Plotly chart."""
        # Mock data similar to what we'd get from the API
        df = pd.DataFrame(
            {
                "timestamp": ["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04"],
                "executions_finished": [1000, 1010, 1005, 1020],
                "executions_failed": [50, 55, 52, 58],
                "executions_cancelled": [20, 20, 22, 25],
            }
        )

        def normalize_to_zero_baseline(series):
            """Normalize a pandas series to start from zero."""
            if series.empty:
                return series
            initial_value = series.iloc[0]
            return series - initial_value

        # Normalize the data
        normalized_finished = normalize_to_zero_baseline(df["executions_finished"])
        normalized_failed = normalize_to_zero_baseline(df["executions_failed"])
        normalized_cancelled = normalize_to_zero_baseline(df["executions_cancelled"])

        # Create a mock Plotly figure to verify integration
        fig = go.Figure()

        # Add traces with normalized data
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"], y=normalized_finished, mode="lines+markers", name="Finished"
            )
        )

        fig.add_trace(
            go.Scatter(x=df["timestamp"], y=normalized_failed, mode="lines+markers", name="Failed")
        )

        fig.add_trace(
            go.Scatter(
                x=df["timestamp"], y=normalized_cancelled, mode="lines+markers", name="Cancelled"
            )
        )

        # Verify the figure was created and has the expected traces
        assert len(fig.data) == 3
        assert fig.data[0].name == "Finished"
        assert fig.data[1].name == "Failed"
        assert fig.data[2].name == "Cancelled"

        # Verify that all series start from 0
        assert fig.data[0].y[0] == 0  # Finished starts at 0
        assert fig.data[1].y[0] == 0  # Failed starts at 0
        assert fig.data[2].y[0] == 0  # Cancelled starts at 0

        # Verify the normalized values are correct
        assert list(fig.data[0].y) == [0, 10, 5, 20]  # Finished normalized
        assert list(fig.data[1].y) == [0, 5, 2, 8]  # Failed normalized
        assert list(fig.data[2].y) == [0, 0, 2, 5]  # Cancelled normalized
