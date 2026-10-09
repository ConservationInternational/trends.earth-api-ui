"""Regression tests for stale browser session recovery."""

from datetime import UTC, datetime, timedelta
import json
from unittest.mock import Mock, patch

from dash import no_update
from flask import Response, g
import pytest
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import Timeout

from trendsearth_ui.app import app
from trendsearth_ui.utils.cookies import create_auth_cookie_data
from trendsearth_ui.utils.helpers import (
    RefreshTokenRejected,
    make_authenticated_request,
    refresh_access_token,
)


def callback(name):
    return next(
        entry["callback"].__wrapped__
        for entry in app.callback_map.values()
        if "callback" in entry and entry["callback"].__wrapped__.__name__ == name
    )


@pytest.fixture
def session_cookie():
    return create_auth_cookie_data(
        "expired-access", "refresh-token", "user@example.com", {"role": "USER"}
    )


def test_expired_cookie_cannot_restore_dashboard(session_cookie):
    session_cookie["expires_at"] = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    response = Response()
    with (
        app.server.test_request_context(
            "/", headers={"Cookie": "auth_token=" + json.dumps(session_cookie)}
        ),
        patch("trendsearth_ui.callbacks.auth.callback_context") as context,
        patch("trendsearth_ui.callbacks.auth.get_user_info") as user_info,
    ):
        context.response = response
        context.triggered = []
        result = callback("display_page")("/", "", None, "production")

    assert result[1] is True
    assert result[2:5] == (None, None, None)
    user_info.assert_not_called()
    assert "auth_token=;" in response.headers["Set-Cookie"]


def test_transient_refresh_failure_does_not_clear_session(session_cookie):
    response = Response()
    with (
        app.server.test_request_context(
            "/", headers={"Cookie": "auth_token=" + json.dumps(session_cookie)}
        ),
        patch("trendsearth_ui.callbacks.auth.callback_context") as context,
        patch("trendsearth_ui.callbacks.auth.should_refresh_token", return_value=True),
        patch(
            "trendsearth_ui.callbacks.auth.refresh_access_token",
            return_value=(None, None, None),
        ),
    ):
        context.response = response
        result = callback("proactive_token_refresh")(1, "expired-access", {"role": "USER"})

    assert result == (no_update, no_update)
    assert "Set-Cookie" not in response.headers


@pytest.mark.parametrize("status", [401, 403])
def test_api_rejection_is_distinct_from_temporary_failure(status):
    with patch("trendsearth_ui.utils.helpers.get_session") as session:
        session.return_value.post.return_value = Mock(status_code=status)
        with pytest.raises(RefreshTokenRejected):
            refresh_access_token("refresh-token")


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_api_temporary_failure_is_retryable(status, caplog):
    with patch("trendsearth_ui.utils.helpers.get_session") as session:
        session.return_value.post.return_value = Mock(status_code=status)
        assert refresh_access_token("refresh-token") == (None, None, None)
    assert f"HTTP {status}" in caplog.text
    assert "refresh-token" not in caplog.text


@pytest.mark.parametrize("error", [Timeout(), RequestsConnectionError()])
def test_network_failure_is_retryable(error, caplog):
    with patch("trendsearth_ui.utils.helpers.get_session") as session:
        session.return_value.post.side_effect = error
        assert refresh_access_token("refresh-token") == (None, None, None)
    assert "preserving session for retry" in caplog.text


def test_missing_refresh_credential_is_rejected():
    with pytest.raises(RefreshTokenRejected):
        refresh_access_token("")


def test_refresh_success_returns_rotated_credentials():
    with patch("trendsearth_ui.utils.helpers.get_session") as session:
        session.return_value.post.return_value = Mock(
            status_code=200,
            json=Mock(
                return_value={
                    "access_token": "new-access",
                    "refresh_token": "new-refresh",
                    "expires_in": 3600,
                }
            ),
        )
        assert refresh_access_token("old-refresh") == ("new-access", 3600, "new-refresh")
        assert session.return_value.post.call_args.kwargs["timeout"] == 10


@pytest.mark.parametrize("body", [{}, {"access_token": "new-access"}])
def test_incomplete_refresh_response_is_not_success(body, caplog):
    with patch("trendsearth_ui.utils.helpers.get_session") as session:
        session.return_value.post.return_value = Mock(status_code=200, json=Mock(return_value=body))
        assert refresh_access_token("refresh-token") == (None, None, None)
    assert "missing" in caplog.text


@pytest.mark.parametrize("name", ["auto_refresh_token", "proactive_token_refresh"])
def test_rejected_refresh_clears_cookie_and_token(name, session_cookie):
    response = Response()
    with (
        app.server.test_request_context(
            "/", headers={"Cookie": "auth_token=" + json.dumps(session_cookie)}
        ),
        patch("trendsearth_ui.callbacks.auth.callback_context") as context,
        patch("trendsearth_ui.callbacks.auth.should_refresh_token", return_value=True),
        patch(
            "trendsearth_ui.callbacks.auth.refresh_access_token",
            side_effect=RefreshTokenRejected("Refresh credential rejected"),
        ),
    ):
        context.response = response
        args = (
            ("expired-access",)
            if name == "auto_refresh_token"
            else (1, "expired-access", {"role": "USER"})
        )
        result = callback(name)(*args)

    assert result is None if name == "auto_refresh_token" else result == (None, None)
    assert "auth_token=;" in response.headers["Set-Cookie"]
    assert "Expires=Thu, 01 Jan 1970" in response.headers["Set-Cookie"]
    assert "HttpOnly" in response.headers["Set-Cookie"]
    assert "Path=/" in response.headers["Set-Cookie"]


@pytest.mark.parametrize("raw_cookie", ["not-json", "[]", "{}", '{"expires_at": null}'])
def test_malformed_cookie_is_removed(raw_cookie):
    response = Response()
    with (
        app.server.test_request_context("/", headers={"Cookie": "auth_token=" + raw_cookie}),
        patch("trendsearth_ui.callbacks.auth.callback_context") as context,
        patch("trendsearth_ui.callbacks.auth.get_user_info") as user_info,
    ):
        context.response = response
        context.triggered = []
        result = callback("display_page")("/", "", None, "production")
    assert result[1] is True
    assert result[2:5] == (None, None, None)
    assert "auth_token=;" in response.headers["Set-Cookie"]
    user_info.assert_not_called()


@pytest.mark.parametrize("rejected", [True, False])
def test_cookie_restoration_never_hydrates_failed_refresh(session_cookie, rejected):
    response = Response()
    with (
        app.server.test_request_context(
            "/", headers={"Cookie": "auth_token=" + json.dumps(session_cookie)}
        ),
        patch("trendsearth_ui.callbacks.auth.callback_context") as context,
        patch("trendsearth_ui.callbacks.auth.should_refresh_token", return_value=True),
        patch("trendsearth_ui.callbacks.auth.get_user_info") as user_info,
        patch("trendsearth_ui.callbacks.auth.refresh_access_token") as refresh,
    ):
        context.response = response
        context.triggered = []
        if rejected:
            refresh.side_effect = RefreshTokenRejected()
        else:
            refresh.return_value = (None, None, None)
        result = callback("display_page")("/", "", None, "production")

    assert result[2:5] == (None, None, None)
    assert result[0].children[0].role == "alert"
    assert ("Set-Cookie" in response.headers) is rejected
    user_info.assert_not_called()


def test_cookie_restoration_refreshes_before_hydrating(session_cookie):
    response = Response()
    with (
        app.server.test_request_context(
            "/", headers={"Cookie": "auth_token=" + json.dumps(session_cookie)}
        ),
        patch("trendsearth_ui.callbacks.auth.callback_context") as context,
        patch("trendsearth_ui.callbacks.auth.should_refresh_token", return_value=True),
        patch(
            "trendsearth_ui.callbacks.auth.refresh_access_token",
            return_value=("new-access", 3600, "new-refresh"),
        ),
        patch(
            "trendsearth_ui.callbacks.auth.get_user_info", return_value={"role": "ADMIN"}
        ) as user_info,
    ):
        context.response = response
        context.triggered = []
        result = callback("display_page")("/", "", None, "production")
    assert result[2] == "new-access"
    assert result[3] == "ADMIN"
    assert "new-refresh" in response.headers["Set-Cookie"]
    user_info.assert_called_once()
    assert user_info.call_args.args[0] == "new-access"


def test_cleared_token_shows_login_without_restoring_cookie(session_cookie):
    response = Response()
    with (
        app.server.test_request_context(
            "/", headers={"Cookie": "auth_token=" + json.dumps(session_cookie)}
        ),
        patch("trendsearth_ui.callbacks.auth.callback_context") as context,
        patch("trendsearth_ui.callbacks.auth.get_user_info") as user_info,
    ):
        context.response = response
        context.triggered = [{"prop_id": "token-store.data"}]
        result = callback("display_page")(
            "/", "", None, "production", [{"props": {"id": "main-panel"}}]
        )
    assert result[0] is not no_update
    assert result[0].children[0].role == "alert"
    assert result[2:5] == (None, None, None)
    assert "auth_token=;" in response.headers["Set-Cookie"]
    user_info.assert_not_called()


def test_failed_login_preserves_its_alert():
    with (
        app.server.test_request_context("/"),
        patch("trendsearth_ui.callbacks.auth.callback_context") as context,
    ):
        context.triggered = [{"prop_id": "token-store.data"}]
        result = callback("display_page")("/", "", None, "production")
    assert result[0] is no_update


def test_token_rotation_does_not_replace_dashboard():
    with (
        app.server.test_request_context("/"),
        patch("trendsearth_ui.callbacks.auth.callback_context") as context,
    ):
        context.triggered = [{"prop_id": "token-store.data"}]
        result = callback("display_page")(
            "/", "", "new-access", "production", [{"props": {"id": "main-panel"}}]
        )
    assert result[0] is no_update
    assert result[2:5] == (no_update, no_update, no_update)


def post_callback(client, name, values, changed):
    key, entry = next(
        (key, entry)
        for key, entry in app.callback_map.items()
        if "callback" in entry and entry["callback"].__wrapped__.__name__ == name
    )
    outputs = entry["output"]
    output_list = outputs if isinstance(outputs, list) else [outputs]
    output_specs = [
        {"id": output.component_id, "property": output.component_property} for output in output_list
    ]
    return client.post(
        "/_dash-update-component",
        json={
            "output": key,
            "outputs": output_specs if isinstance(outputs, list) else output_specs[0],
            "inputs": [
                {**item, "value": values.get(item["id"] + "." + item["property"])}
                for item in entry["inputs"]
            ],
            "state": [
                {**item, "value": values.get(item["id"] + "." + item["property"])}
                for item in entry["state"]
            ],
            "changedPropIds": [changed],
        },
    )


def test_http_rejection_deletes_cookie_and_returns_to_login(session_cookie):
    client = app.server.test_client()
    client.set_cookie("auth_token", json.dumps(session_cookie))
    with (
        patch("trendsearth_ui.callbacks.auth.should_refresh_token", return_value=True),
        patch(
            "trendsearth_ui.callbacks.auth.refresh_access_token",
            side_effect=RefreshTokenRejected(),
        ),
    ):
        response = post_callback(
            client,
            "proactive_token_refresh",
            {
                "token-refresh-interval.n_intervals": 1,
                "token-store.data": "expired-access",
                "user-store.data": {"role": "USER"},
            },
            "token-refresh-interval.n_intervals",
        )
    assert response.status_code == 200
    assert response.json["response"]["token-store"]["data"] is None
    assert response.json["response"]["user-store"]["data"] is None
    assert client.get_cookie("auth_token") is None
    response = post_callback(
        client,
        "display_page",
        {
            "url.pathname": "/",
            "url.search": "",
            "token-store.data": None,
            "api-environment-store.data": "production",
            "page-content.children": [{"props": {"id": "main-panel"}}],
        },
        "token-store.data",
    )
    assert response.status_code == 200
    assert "login-btn" in response.get_data(as_text=True)
    assert response.json["response"]["role-store"]["data"] is None


def test_tab_render_is_triggered_when_dashboard_mounts():
    entry = next(
        entry
        for entry in app.callback_map.values()
        if "callback" in entry and entry["callback"].__wrapped__.__name__ == "render_tab"
    )
    assert {"id": "tabs-nav", "property": "id"} in entry["inputs"]
    content, _ = entry["callback"].__wrapped__(
        "executions", "valid-access", "tabs-nav", {"role": "USER"}, "USER"
    )
    assert content is not no_update


def test_authenticated_request_rejection_expires_cookie(session_cookie):
    rejected_response = Mock(status_code=401, text="token expired")
    with (
        app.server.test_request_context(
            "/", headers={"Cookie": "auth_token=" + json.dumps(session_cookie)}
        ),
        patch("trendsearth_ui.utils.helpers.get_session") as session,
        patch(
            "trendsearth_ui.utils.helpers.refresh_access_token",
            side_effect=RefreshTokenRejected(),
        ),
        patch("trendsearth_ui.utils.jwt_helpers.should_refresh_token", return_value=True),
    ):
        session.return_value.get.return_value = rejected_response
        assert make_authenticated_request("/user/me", "expired-access") is rejected_response
        response = app.server.process_response(Response())
    assert "auth_token=;" in response.headers["Set-Cookie"]


def test_request_cookie_updates_are_persisted():
    with app.server.test_request_context("/"):
        g.updated_auth_cookie = '{"access_token":"new-access","refresh_token":"new-refresh"}'
        response = app.server.process_response(Response())
    assert "new-refresh" in response.headers["Set-Cookie"]


def test_cookie_invalidation_wins_over_pending_update():
    with app.server.test_request_context("/"):
        g.updated_auth_cookie = '{"refresh_token":"rejected-refresh"}'
        g.auth_cookie_invalid = True
        response = app.server.process_response(Response())
    assert "auth_token=;" in response.headers["Set-Cookie"]
    assert "rejected-refresh" not in response.headers["Set-Cookie"]
