"""Unit tests for utility functions in the utils package."""

from datetime import datetime
import json
from unittest.mock import Mock, patch

import pytest

from trendsearth_ui.config import API_BASE
from trendsearth_ui.utils.helpers import (
    get_user_info,
    parse_date,
    safe_table_data,
)
from trendsearth_ui.utils.http_client import DEFAULT_ACCEPT_ENCODING


class TestParseDateFunction:
    """Test the parse_date utility function."""

    def test_parse_date_with_valid_iso_format(self):
        """Test parsing a valid ISO format date."""
        date_str = "2025-06-21T10:30:00Z"
        result = parse_date(date_str)
        assert result == "2025-06-21 10:30 UTC"

    def test_parse_date_with_microseconds(self):
        """Test parsing ISO format with microseconds."""
        date_str = "2025-06-21T10:30:00.123456Z"
        result = parse_date(date_str)
        assert result == "2025-06-21 10:30 UTC"

    def test_parse_date_with_none(self):
        """Test parsing None returns None."""
        result = parse_date(None)
        assert result is None

    def test_parse_date_with_empty_string(self):
        """Test parsing empty string returns None."""
        result = parse_date("")
        assert result is None

    def test_parse_date_with_timezone(self):
        """Test parsing date with custom timezone."""
        date_str = "2025-06-21T10:30:00Z"
        result = parse_date(date_str, "America/New_York")
        # UTC 10:30 should be 06:30 in EDT (UTC-4 in summer)
        assert result is not None
        assert "06:30" in result
        assert "EDT" in result or "EST" in result

    def test_parse_date_with_invalid_format(self):
        """Test parsing invalid format returns original string."""
        invalid_date = "not-a-date"
        result = parse_date(invalid_date)
        assert result == invalid_date


class TestSafeTableDataFunction:
    """Test the safe_table_data utility function."""

    def test_safe_table_data_with_empty_list(self):
        """Test safe_table_data with empty list."""
        result = safe_table_data([])
        assert result == []

    def test_safe_table_data_with_none(self):
        """Test safe_table_data with None."""
        result = safe_table_data(None)
        assert result == []

    def test_safe_table_data_with_valid_data(self):
        """Test safe_table_data with valid data."""
        data = [
            {"id": 1, "name": "Test", "status": "active"},
            {"id": 2, "name": "Test2", "status": "inactive"},
        ]
        result = safe_table_data(data)
        assert len(result) == 2
        assert all(isinstance(row, dict) for row in result)

    def test_safe_table_data_with_column_filter(self):
        """Test safe_table_data with column filtering."""
        data = [
            {"id": 1, "name": "Test", "status": "active", "extra": "data"},
            {"id": 2, "name": "Test2", "status": "inactive", "extra": "data2"},
        ]
        column_ids = ["id", "name"]
        result = safe_table_data(data, column_ids)

        assert len(result) == 2
        for row in result:
            assert "id" in row
            assert "name" in row
            assert "status" not in row
            assert "extra" not in row


class TestGetUserInfoFunction:
    """Test the get_user_info utility function."""

    @patch("trendsearth_ui.utils.helpers.requests.get")
    def test_get_user_info_success(self, mock_get, mock_user_data):
        """Test successful user info retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": mock_user_data}
        mock_get.return_value = mock_response

        token = "test_token"
        result = get_user_info(token)

        assert result == mock_user_data
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[0][0] == f"{API_BASE}/user/me"
        headers = call_args[1]["headers"]
        assert headers["Authorization"] == f"Bearer {token}"
        assert headers["Accept-Encoding"] == DEFAULT_ACCEPT_ENCODING
        assert call_args[1]["timeout"] == 10

    @patch("trendsearth_ui.utils.helpers.requests.get")
    def test_get_user_info_failure(self, mock_get):
        """Test user info retrieval failure."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        token = "invalid_token"
        result = get_user_info(token)

        assert result is None

    @patch("trendsearth_ui.utils.helpers.requests.get")
    def test_get_user_info_exception(self, mock_get):
        """Test user info retrieval with exception."""
        mock_get.side_effect = Exception("Network error")

        token = "test_token"
        result = get_user_info(token)

        assert result is None
