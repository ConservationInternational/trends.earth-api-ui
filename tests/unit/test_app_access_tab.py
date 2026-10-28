"""Tests for the App Access tab (requests review + notification recipients)."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from dash import no_update
import pytest

from trendsearth_ui.callbacks import app_access_tab
from trendsearth_ui.callbacks.app_access_tab import (
    build_recipient_options,
    parse_app_access_deeplink,
    recipients_endpoint,
    render_recipients_summary,
    render_requests_table,
)
from trendsearth_ui.callbacks.manual_tabs import _TAB_CONFIGS
from trendsearth_ui.callbacks.users import app_label
from trendsearth_ui.components.app_access import app_access_tab_content

pytestmark = pytest.mark.unit

APPS = [
    {"app_key": "avoided_emissions", "label": "Avoided Emissions", "roles": ["member", "admin"]},
    {"app_key": "rio_coherence", "label": "Rio Coherence", "roles": ["viewer"]},
]


def _find_ids(component, acc=None):
    """Collect every component id in a Dash component tree."""
    acc = [] if acc is None else acc
    cid = getattr(component, "id", None)
    if cid is not None:
        acc.append(cid)
    children = getattr(component, "children", None)
    if isinstance(children, list | tuple):
        for child in children:
            _find_ids(child, acc)
    elif hasattr(children, "to_plotly_json"):
        _find_ids(children, acc)
    return acc


class _CapturingApp:
    def __init__(self):
        self.callbacks = {}

    def callback(self, *args, **kwargs):
        def decorator(func):
            self.callbacks[func.__name__] = func
            return func

        return decorator


@pytest.fixture
def callbacks():
    app = _CapturingApp()
    app_access_tab.register_callbacks(app)
    return app.callbacks


def _response(status, body):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = body
    resp.text = str(body)
    return resp


class TestDeeplinkParsing:
    def test_full_link(self):
        assert parse_app_access_deeplink(
            "?tab=app-access&app=avoided_emissions&status=pending"
        ) == {
            "app": "avoided_emissions",
            "status": "pending",
        }

    def test_other_tab_ignored(self):
        assert parse_app_access_deeplink("?tab=users") is None
        assert parse_app_access_deeplink("") is None
        assert parse_app_access_deeplink(None) is None

    def test_invalid_values_sanitized(self):
        assert parse_app_access_deeplink("?tab=app-access&app=../../x&status=bogus") == {
            "app": None,
            "status": "pending",
        }

    def test_url_encoded_values(self):
        parsed = parse_app_access_deeplink("?tab=app-access&app=rio_coherence_staging&status=all")
        assert parsed == {"app": "rio_coherence_staging", "status": "all"}


class TestRequestsTable:
    def test_no_app_selected(self):
        assert "Select an application" in str(render_requests_table([], APPS, None))

    def test_empty(self):
        assert "No matching" in str(render_requests_table([], APPS, "avoided_emissions"))

    def test_pending_row_has_approve_deny_and_role_choice(self):
        grants = [
            {
                "user_id": "u1",
                "app_key": "avoided_emissions",
                "status": "pending",
                "request_note": "Pilot partner",
                "requested_at": "2026-01-02T03:04:05",
                "user": {"name": "Ann", "email": "ann@example.org", "institution": "CI"},
            }
        ]
        table = render_requests_table(grants, APPS, "avoided_emissions", total=1)
        ids = _find_ids(table)
        key = {"user_id": "u1", "app_key": "avoided_emissions"}
        assert {"type": "app-access-approve-btn", **key} in ids
        assert {"type": "app-access-revoke-btn", **key} in ids
        assert {"type": "app-access-row-role", **key} in ids
        text = str(table)
        assert "ann@example.org" in text
        assert "Pilot partner" in text
        assert "Deny" in text

    def test_revoked_row_has_no_revoke_button(self):
        grants = [{"user_id": "u2", "app_key": "rio_coherence", "status": "revoked", "user": {}}]
        ids = _find_ids(render_requests_table(grants, APPS, "rio_coherence"))
        assert {
            "type": "app-access-revoke-btn",
            "user_id": "u2",
            "app_key": "rio_coherence",
        } not in ids
        assert "Restore" in str(render_requests_table(grants, APPS, "rio_coherence"))

    def test_truncation_notice(self):
        grants = [{"user_id": "u1", "app_key": "rio_coherence", "status": "pending"}]
        assert "Showing 1 of 5" in str(render_requests_table(grants, APPS, "rio_coherence", 5))


class TestRecipients:
    def test_options_include_candidates_and_flag_ineligible_listed(self):
        candidates = [
            {"id": "a1", "email": "admin@x.org", "name": "Admin", "role": "ADMIN"},
            {"id": "s1", "email": "super@x.org", "name": "Super", "role": "SUPERADMIN"},
        ]
        listed = [
            {"user_id": "s1", "email": "super@x.org", "eligible": True},
            {"user_id": "d1", "email": "demoted@x.org", "role": "USER", "eligible": False},
        ]
        options, value = build_recipient_options(candidates, listed)
        assert value == ["s1", "d1"]
        labels = {o["value"]: o["label"] for o in options}
        assert set(labels) == {"a1", "s1", "d1"}
        assert "no longer eligible" in labels["d1"]

    def test_summary_default_fallback(self):
        summary = str(
            render_recipients_summary(
                {
                    "using_default": True,
                    "auto_app_admins": [{"email": "appadmin@x.org"}],
                    "effective_recipients": ["super@x.org", "appadmin@x.org"],
                }
            )
        )
        assert "all superadmins are notified" in summary
        assert "appadmin@x.org" in summary

    def test_summary_listed(self):
        summary = str(
            render_recipients_summary(
                {"using_default": False, "auto_app_admins": [], "effective_recipients": ["a@x"]}
            )
        )
        assert "listed recipients" in summary
        assert "none" in summary


class TestWiring:
    def test_tab_visible_to_admins(self):
        assert ("app-access-tab-li", ("ADMIN", "SUPERADMIN")) in _TAB_CONFIGS

    def test_recipients_card_hidden_for_admin_shown_for_superadmin(self):
        def card_style(role):
            content = app_access_tab_content(role)
            card = next(
                c
                for c in content.children
                if getattr(c, "id", None) == "app-access-recipients-card"
            )
            return card.style

        assert card_style("ADMIN") == {"display": "none"}
        assert card_style("SUPERADMIN") == {}

    def test_staging_label(self):
        assert app_label("avoided_emissions_staging") == "Avoided Emissions (staging)"

    def test_recipients_endpoint(self):
        assert recipients_endpoint("avoided_emissions") == (
            "/admin/app-access/apps/avoided_emissions/notification-recipients"
        )


class TestDeeplinkCallback:
    SEARCH = "?tab=app-access&app=avoided_emissions&status=pending"

    def test_admin_opens_tab_once(self, callbacks):
        cb = callbacks["apply_app_access_deeplink"]
        tab, store = cb(self.SEARCH, "ADMIN", "tok", None)
        assert tab == "app-access"
        assert store["app"] == "avoided_emissions"
        assert store["applied"] is False
        # Re-firing (e.g. role re-set) with the same query must not override later tab clicks.
        assert cb(self.SEARCH, "ADMIN", "tok", store) == (no_update, no_update)

    def test_ignored_for_regular_users_and_logged_out(self, callbacks):
        cb = callbacks["apply_app_access_deeplink"]
        assert cb(self.SEARCH, "USER", "tok", None) == (no_update, no_update)
        assert cb(self.SEARCH, None, None, None) == (no_update, no_update)

    def test_init_applies_deeplink_filters(self, callbacks):
        deeplink = {"app": "rio_coherence", "status": "active", "search": "?x", "applied": False}
        with patch.object(app_access_tab, "_fetch_apps", return_value=APPS):
            apps, options, selected, status, store = callbacks["init_app_access_tab"](
                1, "tok", "ADMIN", deeplink
            )
        assert apps == APPS
        assert [o["value"] for o in options] == ["avoided_emissions", "rio_coherence"]
        assert selected == "rio_coherence"
        assert status == "active"
        assert store["applied"] is True

    def test_init_ignores_unknown_app(self, callbacks):
        deeplink = {"app": "nope", "status": "pending", "search": "?x", "applied": False}
        with patch.object(app_access_tab, "_fetch_apps", return_value=APPS):
            _apps, _opts, selected, status, _store = callbacks["init_app_access_tab"](
                1, "tok", "SUPERADMIN", deeplink
            )
        assert selected == "avoided_emissions"
        assert status == "pending"


class TestActions:
    def _ctx(self, trigger, value=1):
        return SimpleNamespace(triggered_id=trigger, triggered=[{"value": value}])

    def test_approve_posts_selected_role(self, callbacks):
        trigger = {
            "type": "app-access-approve-btn",
            "user_id": "u1",
            "app_key": "avoided_emissions",
        }
        role_ids = [
            {"type": "app-access-row-role", "user_id": "u1", "app_key": "avoided_emissions"}
        ]
        with (
            patch.object(app_access_tab, "callback_context", self._ctx(trigger)),
            patch.object(
                app_access_tab, "make_authenticated_request", return_value=_response(200, {})
            ) as req,
        ):
            msg, color, is_open, refresh = callbacks["apply_request_action"](
                [1], [None], ["admin"], role_ids, "ok", 2, "tok", "ADMIN"
            )
        assert (color, is_open, refresh) == ("success", True, 3)
        args, kwargs = req.call_args
        assert args[0] == "/admin/users/u1/app-access"
        assert kwargs["method"] == "POST"
        assert kwargs["json"] == {
            "app_key": "avoided_emissions",
            "status": "active",
            "role": "admin",
            "note": "ok",
        }

    def test_deny_deletes(self, callbacks):
        trigger = {"type": "app-access-revoke-btn", "user_id": "u1", "app_key": "rio_coherence"}
        with (
            patch.object(app_access_tab, "callback_context", self._ctx(trigger)),
            patch.object(
                app_access_tab, "make_authenticated_request", return_value=_response(200, {})
            ) as req,
        ):
            callbacks["apply_request_action"]([None], [1], [], [], None, 0, "tok", "SUPERADMIN")
        args, kwargs = req.call_args
        assert args[0] == "/admin/users/u1/app-access/rio_coherence"
        assert kwargs["method"] == "DELETE"

    def test_rerender_without_click_is_ignored(self, callbacks):
        trigger = {"type": "app-access-approve-btn", "user_id": "u1", "app_key": "rio_coherence"}
        with (
            patch.object(app_access_tab, "callback_context", self._ctx(trigger, None)),
            patch.object(app_access_tab, "make_authenticated_request") as req,
        ):
            result = callbacks["apply_request_action"](
                [None], [None], [], [], None, 0, "tok", "ADMIN"
            )
        assert result == (no_update,) * 4
        req.assert_not_called()


class TestSaveRecipients:
    def test_non_superadmin_rejected(self, callbacks):
        with patch.object(app_access_tab, "make_authenticated_request") as req:
            msg, color, _open, _refresh = callbacks["save_recipients"](
                1, "avoided_emissions", ["a1"], 0, "tok", "ADMIN"
            )
        assert color == "danger"
        req.assert_not_called()

    def test_put_replace_set(self, callbacks):
        with patch.object(
            app_access_tab, "make_authenticated_request", return_value=_response(200, {"data": {}})
        ) as req:
            msg, color, _open, refresh = callbacks["save_recipients"](
                1, "avoided_emissions", [], 4, "tok", "SUPERADMIN"
            )
        assert color == "success"
        assert "all superadmins" in msg
        assert refresh == 5
        _args, kwargs = req.call_args
        assert kwargs["method"] == "PUT"
        assert kwargs["json"] == {"user_ids": []}

    def test_invalid_users_reported(self, callbacks):
        body = {"status": 400, "detail": "Recipients must be admins", "invalid_user_ids": ["x1"]}
        with patch.object(
            app_access_tab, "make_authenticated_request", return_value=_response(400, body)
        ):
            msg, color, _open, refresh = callbacks["save_recipients"](
                1, "avoided_emissions", ["x1"], 0, "tok", "SUPERADMIN"
            )
        assert color == "danger"
        assert "x1" in msg
        assert refresh is no_update
