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


def test_rate_limit_breaches_initial_prefetch(monkeypatch):
    """Initial grid load should prefetch historical rows even with tiny requests."""

    active_limits = [
        {
            "key": "user:123",
            "identifier": "user:123",
            "type": "user",
            "occurred_at": "2025-11-02T10:00:00+00:00",
            "expires_at": "2025-11-02T10:15:00+00:00",
            "limit": 5,
            "current_count": 5,
            "time_window_seconds": 3600,
            "retry_after_seconds": 300,
            "limit_definition": "5 per hour",
            "user_info": {
                "email": "user@example.com",
                "name": "Example User",
                "role": "USER",
            },
        }
    ]

    events = [
        {
            "id": f"event-{idx}",
            "occurred_at": f"2025-11-{idx + 1:02d}T09:00:00+00:00",
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

    def fake_make_request(url: str, token: str, params: dict[str, Any] | None = None, **_: Any):
        assert params is not None
        assert params.get("per_page", 0) >= admin.DEFAULT_PAGE_SIZE
        return _StubResponse(
            {
                "data": {
                    "events": events,
                    "active_limits": active_limits,
                    "total": len(events),
                }
            }
        )

    monkeypatch.setattr(admin, "make_authenticated_request", fake_make_request)

    request_payload = {"startRow": 0, "endRow": 1}
    response, state, total = admin._query_rate_limit_breaches(
        request_payload,
        token="token",
        role="SUPERADMIN",
        user_timezone="UTC",
    )

    expected_total = len(events) + len(active_limits)

    assert state["page_size"] >= admin.DEFAULT_PAGE_SIZE
    assert response["rowCount"] == expected_total
    assert len(response["rowData"]) == expected_total

    active_rows = [row for row in response["rowData"] if row.get("is_active")]
    assert len(active_rows) == len(active_limits)
    assert any(not row.get("is_active") for row in response["rowData"])
    assert total == expected_total
