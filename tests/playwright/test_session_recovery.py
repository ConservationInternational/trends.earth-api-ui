"""Browser regressions for restoring stale authentication cookies."""

from datetime import UTC, datetime, timedelta
import json
from unittest.mock import Mock, patch

from playwright.sync_api import expect
import pytest

from trendsearth_ui.utils.cookies import create_auth_cookie_data
from trendsearth_ui.utils.helpers import RefreshTokenRejected

from .conftest import skip_if_no_browsers


@pytest.mark.playwright
@skip_if_no_browsers
@pytest.mark.parametrize("outcome", ["expired", "rejected", "temporary", "success"])
def test_stale_session_recovers_without_site_data_cleanup(page, live_server, outcome):
    cookie_data = create_auth_cookie_data(
        "expired-access",
        "old-refresh",
        "user@example.com",
        {"id": "user-123", "email": "user@example.com", "role": "USER"},
    )
    if outcome == "expired":
        cookie_data["expires_at"] = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    page.context.add_cookies(
        [{"name": "auth_token", "value": json.dumps(cookie_data), "url": live_server}]
    )
    page.add_init_script("localStorage.setItem('active-tab-store', JSON.stringify('profile'));")
    with (
        patch(
            "trendsearth_ui.callbacks.auth.should_refresh_token",
            side_effect=lambda token, **_kwargs: token == "expired-access",
        ),
        patch("trendsearth_ui.callbacks.auth.refresh_access_token") as refresh,
        patch(
            "trendsearth_ui.callbacks.auth.get_user_info",
            return_value=cookie_data["user_data"],
        ),
        patch(
            "requests.sessions.Session.request",
            return_value=Mock(
                status_code=200,
                json=Mock(return_value={"data": [], "total": 0}),
                text='{"data": [], "total": 0}',
                headers={},
            ),
        ),
    ):
        if outcome == "rejected":
            refresh.side_effect = RefreshTokenRejected()
        elif outcome == "temporary":
            refresh.return_value = (None, None, None)
        else:
            refresh.return_value = ("valid-access", 3600, "new-refresh")
        page.goto(live_server)
        if outcome == "success":
            expect(page.locator("[data-testid='dashboard-content']")).to_be_visible()
            expect(page.locator("#tab-content-dynamic")).not_to_be_empty()
            expect(page.locator("#profile-tab-btn")).to_have_class("nav-link active")
        else:
            expect(page.locator("#login-btn")).to_be_visible()
            expect(page.locator("[data-testid='dashboard-content']")).to_have_count(0)
            expect(page.get_by_role("alert").first).to_be_visible()
        cookies = {cookie["name"]: cookie["value"] for cookie in page.context.cookies()}
        if outcome in ("expired", "rejected"):
            assert "auth_token" not in cookies
        elif outcome == "temporary":
            assert json.loads(cookies["auth_token"])["refresh_token"] == "old-refresh"
        else:
            assert json.loads(cookies["auth_token"])["refresh_token"] == "new-refresh"
