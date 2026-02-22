"""Tests for rate limiting management data loading."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from trendsearth_ui.callbacks import admin


@dataclass
class _StubResponse:
    payload: dict[str, Any]
    status_code: int = 200

    def json(self) -> dict[str, Any]:
        return self.payload


def test_rate_limit_breaches_loads_data(monkeypatch):
    """Grid load should pass params via ``build_aggrid_request_params`` and render rows."""

    events = [
        {
            "id": f"event-{idx}",
            "occurred_at": f"2025-11-{idx + 1:02d}T09:00:00+00:00",
            "expires_at": "2025-11-02T10:15:00+00:00" if idx == 0 else None,
            "limit_key": f"user:123:{idx}",
            "endpoint": "/api/test",
            "method": "GET",
            "limit_definition": "5 per hour",
            "limit_count": 5,
            "time_window_seconds": 3600,
            "retry_after_seconds": 60,
            "rate_limit_type": "user",
            "user_email": "user@example.com",
        }
        for idx in range(5)
    ]

    captured_params: list[dict[str, Any]] = []

    def fake_make_request(url: str, token: str, params: dict[str, Any] | None = None, **_: Any):
        assert params is not None
        captured_params.append(dict(params))
        return _StubResponse({"data": events, "total": len(events)})

    monkeypatch.setattr(admin, "make_authenticated_request", fake_make_request)

    request_payload = {"startRow": 0, "endRow": 100}
    response, state, total = admin._query_rate_limit_breaches(
        request_payload,
        token="token",
        role="SUPERADMIN",
        user_timezone="UTC",
    )

    # Verify API was called with standard page/per_page params
    assert len(captured_params) == 1
    assert "page" in captured_params[0]
    assert "per_page" in captured_params[0]

    # Verify standard table_state keys are present (from build_table_state)
    assert "sort_model" in state
    assert "filter_model" in state

    # Verify response shape
    assert response["rowCount"] == len(events)
    assert len(response["rowData"]) == len(events)
    assert total == len(events)

    # Verify row formatting
    for row in response["rowData"]:
        assert "status_display" in row
        assert row["status_display"] in ("Active", "Historical")


def test_rate_limit_breaches_sort_remapping(monkeypatch):
    """UI display field names should be remapped to API column names for sorting."""

    captured_params: list[dict[str, Any]] = []

    def fake_make_request(url: str, token: str, params: dict[str, Any] | None = None, **_: Any):
        captured_params.append(dict(params or {}))
        return _StubResponse({"data": [], "total": 0})

    monkeypatch.setattr(admin, "make_authenticated_request", fake_make_request)

    request_payload = {
        "startRow": 0,
        "endRow": 100,
        "sortModel": [{"colId": "identifier_display", "sort": "asc"}],
    }
    admin._query_rate_limit_breaches(
        request_payload, token="tok", role="ADMIN", user_timezone="UTC"
    )

    assert len(captured_params) == 1
    # "identifier_display" should be remapped to "limit_key" in the sort param
    sort_param = captured_params[0].get("sort", "")
    assert "limit_key" in sort_param
    assert "identifier_display" not in sort_param


def test_rate_limit_breaches_status_filter(monkeypatch):
    """Status filter should be sent as a dedicated ``status`` query param."""

    captured_params: list[dict[str, Any]] = []

    def fake_make_request(url: str, token: str, params: dict[str, Any] | None = None, **_: Any):
        captured_params.append(dict(params or {}))
        return _StubResponse({"data": [], "total": 0})

    monkeypatch.setattr(admin, "make_authenticated_request", fake_make_request)

    request_payload = {
        "startRow": 0,
        "endRow": 100,
        "filterModel": {
            "status_display": {
                "filterType": "set",
                "values": ["Active"],
            },
        },
    }
    admin._query_rate_limit_breaches(
        request_payload, token="tok", role="ADMIN", user_timezone="UTC"
    )

    assert len(captured_params) == 1
    assert captured_params[0].get("status") == "active"


def test_rate_limit_breaches_text_filter_as_sql(monkeypatch):
    """Text filters should be sent as a unified ``filter`` param (SQL-style)."""

    captured_params: list[dict[str, Any]] = []

    def fake_make_request(url: str, token: str, params: dict[str, Any] | None = None, **_: Any):
        captured_params.append(dict(params or {}))
        return _StubResponse({"data": [], "total": 0})

    monkeypatch.setattr(admin, "make_authenticated_request", fake_make_request)

    request_payload = {
        "startRow": 0,
        "endRow": 100,
        "filterModel": {
            "user_email": {
                "filterType": "text",
                "type": "contains",
                "filter": "example.com",
            },
        },
    }
    admin._query_rate_limit_breaches(
        request_payload, token="tok", role="ADMIN", user_timezone="UTC"
    )

    assert len(captured_params) == 1
    filter_param = captured_params[0].get("filter", "")
    assert "user_email" in filter_param
    assert "example.com" in filter_param
